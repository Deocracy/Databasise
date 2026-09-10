"""Tests for databasise.eval.corpus_ingest (06-12-PLAN.md Task 1's <behavior> block).

Mirrors databasise/tests/seam/test_hipporag_write_path.py's own stub-client shape for the tracer
test (Test 1): openie's two-stage NER/triple extraction needs content-dispatched chat responses,
unlike test_compare.py's single fixed-response stub, which only ever serves fact-filter/generate at
query time. No network, no v1/ artifacts, no live client in any test here.
"""

from __future__ import annotations

import json

import pytest

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.eval import corpus_ingest
from databasise.eval.corpus_ingest import (
    CORPUS_DIR,
    IngestEstimate,
    LimitExceedsCorpusError,
    estimate,
    ingest_documents,
)
from databasise.parity.corpus import load_snapshot
from databasise.runner.trace import TokenAccounting
from databasise.seam import Databasise
from databasise.seam.corpus import IngestJob
from databasise.stores.vector import MultiNamespaceVectorStore

_WORKSPACE = "corpus-ingest-tracer-ws"
_QUERY_VECTOR = [1.0, 0.0, 0.0]
_SUBJECT, _PREDICATE, _OBJECT = "Subject", "relates-to", "Object"


class _StubEmbeddingClient:
    async def embed(self, texts, **kwargs):
        return EmbeddingResult(
            vectors=[_QUERY_VECTOR for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


class _StubIngestLLMClient:
    """Serves HippoRAG's index-side ``openie`` node: dispatches on prompt content, not call
    order, since ``openie`` makes two LLM calls (NER, then triple extraction) per chunk. Mirrors
    ``test_hipporag_write_path.py``'s own ``_StubIngestQueryLLMClient`` shape (that class's own
    docstring explains why content-based dispatch, not a stub-per-call-index, is required here).
    """

    async def chat(self, messages, **kwargs):
        content = messages[0]["content"]
        if "---Recognised Entities---" in content:
            text = json.dumps({"triples": [[_SUBJECT, _PREDICATE, _OBJECT]]})
        else:
            text = json.dumps({"entities": [_SUBJECT, _OBJECT]})
        return ChatResult(
            text=text,
            tokens=TokenAccounting(
                prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"
            ),
            resolved_model_identity="stub-llm-model",
        )


# --------------------------------------------------------------------------------------------- #
# Test 1 — the tracer: estimate -> bound -> ingest -> observable index, in one test.
# --------------------------------------------------------------------------------------------- #


async def test_estimate_then_ingest_lands_in_hipporags_own_namespaces(store_root):
    snapshot = load_snapshot(CORPUS_DIR)

    est = estimate(snapshot, limit=1, arm="hipporag")
    assert est.documents == 1
    assert est.bytes == len(snapshot.documents[0].text.encode("utf-8"))

    engine = Databasise(
        store_root=store_root,
        workspace=_WORKSPACE,
        clients={"embedding": _StubEmbeddingClient(), "llm": _StubIngestLLMClient()},
    )

    jobs = await ingest_documents(engine, snapshot, limit=1, arm="hipporag")

    assert len(jobs) == 1
    assert isinstance(jobs[0], IngestJob)

    vector_store = MultiNamespaceVectorStore(workspace=_WORKSPACE, store_root=store_root)
    assert list(vector_store.select("hipporag-chunks").iter_vectors())
    await vector_store.finalize()


# --------------------------------------------------------------------------------------------- #
# Test 2 — the default path spends nothing: no client, zero ingest calls.
# --------------------------------------------------------------------------------------------- #


def test_default_path_spends_nothing(monkeypatch, capsys):
    calls: list[tuple[int, str]] = []

    async def _spy_ingest_documents(engine, snapshot, *, limit, arm):
        calls.append((limit, arm))
        return []

    def _fail_if_constructed(**kwargs):
        raise AssertionError("Databasise must not be constructed in estimate-only mode")

    monkeypatch.setattr(corpus_ingest, "ingest_documents", _spy_ingest_documents)
    monkeypatch.setattr(corpus_ingest, "Databasise", _fail_if_constructed)

    exit_code = corpus_ingest.main(["--limit", "5"])

    assert exit_code == 0
    assert calls == []  # ingest_documents (and therefore Databasise.ingest) was never called

    out = capsys.readouterr().out
    assert '"documents": 5' in out
    assert "mode: estimate-only" in out


# --------------------------------------------------------------------------------------------- #
# Test 3 — the bound is enforced: --spend ingests exactly --limit documents, never the whole
# corpus, in the snapshot's own deterministic order.
# --------------------------------------------------------------------------------------------- #


def test_spend_flag_ingests_exactly_the_limit_never_the_whole_corpus(monkeypatch):
    ingested_ids: list[str] = []

    class _StubEngine:
        async def ingest(self, document, selector=None):
            ingested_ids.append(document.document_id or "")
            return IngestJob(job_id="stub-job", enqueued=1)

    monkeypatch.setattr(corpus_ingest, "_load_env_file", lambda path: {})
    monkeypatch.setattr(corpus_ingest, "_build_clients", lambda env: {"llm": None, "embedding": None})
    monkeypatch.setattr(corpus_ingest, "Databasise", lambda **kwargs: _StubEngine())

    exit_code = corpus_ingest.main(["--limit", "3", "--spend"])

    assert exit_code == 0
    assert len(ingested_ids) == 3

    snapshot = load_snapshot(CORPUS_DIR)
    expected_ids = [doc.id for doc in snapshot.documents[:3]]
    assert ingested_ids == expected_ids


# --------------------------------------------------------------------------------------------- #
# Test 4 — an over-large limit is refused by name, never silently clamped.
# --------------------------------------------------------------------------------------------- #


def test_limit_exceeding_corpus_size_is_refused_by_name(capsys):
    snapshot = load_snapshot(CORPUS_DIR)
    available = len(snapshot.documents)

    with pytest.raises(LimitExceedsCorpusError) as exc_info:
        estimate(snapshot, limit=available + 1, arm="lightrag")
    assert exc_info.value.requested == available + 1
    assert exc_info.value.available == available

    exit_code = corpus_ingest.main(["--limit", "100000"])
    assert exit_code == 1

    err = capsys.readouterr().err
    assert "100000" in err
    assert str(available) in err


# --------------------------------------------------------------------------------------------- #
# Test 5 — the projection labels its own bound, per arm.
# --------------------------------------------------------------------------------------------- #


def test_estimate_labels_its_own_bound_and_note_per_arm():
    snapshot = load_snapshot(CORPUS_DIR)

    lightrag_est = estimate(snapshot, limit=2, arm="lightrag")
    assert isinstance(lightrag_est, IngestEstimate)
    assert "document" in lightrag_est.bound.lower()
    assert "unbudgetable" in lightrag_est.note

    hipporag_est = estimate(snapshot, limit=2, arm="hipporag")
    assert "token" in hipporag_est.bound.lower()
    assert "allowance" in hipporag_est.bound.lower()
