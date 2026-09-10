"""06-14-PLAN.md Task 1: closes WINDOWS.md entry id 3 / 06-VERIFICATION.md gap 1's first `missing`
item — the real code defect that refused 06-13 Task 1's real, spend-incurring HippoRAG index
build. ``build_hipporag_index.build_index`` now resolves HippoRAG's seven-position
``corpus-ingest`` wiring rather than its thirteen-position base wiring, so no query-side position
(``fact-score`` foremost — the node the 2026-09-10 refusal actually named) ever dispatches at
index time.

Every test in this module reaches a client double, never a reachable endpoint — no ``openai``
import, no real ``openai.AsyncOpenAI`` construction, no network call, no live spend. Mirrors
``databasise/tests/seam/test_hipporag_write_path.py``'s own stub-client, prompt-content-dispatch
style (the closest existing analog for driving HippoRAG's index-side node chain end to end).
"""

from __future__ import annotations

import json

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.parity.build_hipporag_index import IndexBuildResult, build_index
from databasise.parity.corpus import CorpusDocument, CorpusSnapshot
from databasise.parity.run_arm import _inject_query as _run_arm_inject_query
from databasise.runner.trace import TokenAccounting
from databasise.wirings.resolve import load_wiring

_SUBJECT, _PREDICATE, _OBJECT = "Ed Wood", "directed", "films"


class _RefusingOnEmptyBatchEmbeddingClient:
    """Raises ``AssertionError`` naming the offending batch position the moment it is handed a
    batch that is empty or that contains an item whose ``strip()`` is falsy — the double this
    test's whole point rests on. If any node the base wiring lists under ``consumes_query``
    dispatched during an index build (this module's own regression target), it would arrive with
    no query, hand this double a zero-length string, and fail the build here, reproducing the
    2026-09-10 provider ``400`` (``databasise/evidence/CROSS-MODALITY-EVIDENCE.md``) locally, at
    zero cost. Otherwise returns a deterministic, fixed-width unit-vector ``EmbeddingResult`` with
    a real ``TokenAccounting`` and a fixed ``resolved_model_identity``.
    """

    async def embed(self, texts, **kwargs):
        if not texts:
            raise AssertionError("embed() called with an empty batch — no offending index")
        for index, text in enumerate(texts):
            if not str(text).strip():
                raise AssertionError(
                    f"embed() called with an empty/whitespace-only item at batch index "
                    f"{index}: texts={texts!r}"
                )
        return EmbeddingResult(
            vectors=[[1.0, 0.0, 0.0, 0.0] for _ in texts],
            tokens=TokenAccounting(
                prompt_tokens=len(texts), call_count=1, counted_by="stub-embed@1"
            ),
            resolved_model_identity="stub-embed@1",
        )


class _StubOpenIEChatClient:
    """Serves ``openie``'s two-call-per-chunk NER-then-triples shape, dispatching on prompt
    content — mirrors ``test_hipporag_write_path.py``'s own ``_StubIngestQueryLLMClient``
    convention. Only the index-side ``openie`` node reaches this client in this module (the
    corpus-ingest wiring dispatches no query-side node), so no ``---Candidate Facts---`` branch is
    needed here.
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
                prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm@1"
            ),
            resolved_model_identity="stub-llm@1",
        )


def _synthetic_snapshot() -> CorpusSnapshot:
    """Two or three short, hand-authored documents — never the real 20-document fixture: this
    test drives the harness's own dispatch logic against a client double, not a real corpus, so a
    small synthetic snapshot keeps the run fast while still exercising every index-side position.
    """
    documents = (
        CorpusDocument(
            id="synth-doc-1",
            title="Synthetic Doc 1",
            text="Ed Wood directed several low-budget films in the 1950s.",
            sha256="synthetic-sha-1",
        ),
        CorpusDocument(
            id="synth-doc-2",
            title="Synthetic Doc 2",
            text="Bela Lugosi starred in many of Ed Wood's films.",
            sha256="synthetic-sha-2",
        ),
        CorpusDocument(
            id="synth-doc-3",
            title="Synthetic Doc 3",
            text="Plan 9 from Outer Space is one of Ed Wood's best-known films.",
            sha256="synthetic-sha-3",
        ),
    )
    return CorpusSnapshot(
        documents=documents,
        queries=(),
        corpus_hash="synthetic-corpus-hash",
        queries_hash="synthetic-queries-hash",
        source={"kind": "06-14-PLAN.md synthetic test fixture"},
    )


# --------------------------------------------------------------------------------------------- #
# Test 1: end-to-end — a HippoRAG index build completes against the refusing embedding double.
# --------------------------------------------------------------------------------------------- #


async def test_1_a_hipporag_index_build_completes_end_to_end_against_a_client_double_that_refuses_empty_input(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "databasise.parity.build_hipporag_index.load_snapshot", _synthetic_snapshot
    )
    clients = {
        "embedding": _RefusingOnEmptyBatchEmbeddingClient(),
        "llm": _StubOpenIEChatClient(),
    }

    result = await build_index(
        clients=clients,
        store_root=tmp_path,
        workspace="hipporag-index-build-test",
    )

    assert isinstance(result, IndexBuildResult)
    assert result.partial is False
    assert result.degraded is False
    assert result.graph_node_count > 0
    assert result.graph_edge_count > 0
    assert result.chunk_vector_count > 0
    assert result.entity_vector_count > 0
    assert result.fact_vector_count > 0


# --------------------------------------------------------------------------------------------- #
# Test 2: structural non-vacuity — the corpus-ingest wiring carries no query-side position.
# --------------------------------------------------------------------------------------------- #


def test_2_the_corpus_ingest_wirings_node_ids_are_disjoint_from_the_base_wirings_query_side_positions():
    base = load_wiring("hipporag")
    index_side = load_wiring("hipporag", variant="corpus-ingest")

    query_side_ids = set(base["consumes_query"])
    index_side_ids = set(index_side["nodes"])

    assert not (index_side_ids & query_side_ids)
    assert "fact-filter" not in index_side_ids
    assert "ppr" not in index_side_ids
    assert "assemble-result" not in index_side_ids


# --------------------------------------------------------------------------------------------- #
# Test 3: the root-cause pin — fact-score's empty deps, and run_arm's own _inject_query never
# reaches any of the base wiring's own query-side node ids.
# --------------------------------------------------------------------------------------------- #


def test_3_fact_score_has_empty_deps_and_run_arms_own_inject_query_never_stamps_a_base_wiring_query_side_node():
    base = load_wiring("hipporag")

    assert base["nodes"]["fact-score"]["deps"] == []

    resolved = _run_arm_inject_query(dict(base), "some real query text")
    query_side_ids = set(base["consumes_query"])
    for node_id in query_side_ids:
        config = resolved["nodes"][node_id].get("config") or {}
        assert "query" not in config
