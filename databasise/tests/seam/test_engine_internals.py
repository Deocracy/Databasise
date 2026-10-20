"""13-05 Task 2 (WIRE-14, D-09): engine internals fail by name and expose no dead API.

Row tests for the legs this plan changes: an evidence node without ``items`` is refused as a named
fault, and ``query`` / ``query_stream`` / ``compare`` take no ``debug`` keyword they would discard;
plus pins for the legs already met by STOR-07 (delete opens the corpus-delete wiring's namespaces),
STOR-03 (``resolve_evidence`` never builds the graph store) and HIPP-04 (a failed openie node is
refused with its real exception as cause).

Every test collects and fails by assertion at the phase base: only names that exist there are
imported, and exceptions are captured and asserted on rather than expected with ``pytest.raises``.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from databasise.parts.registry import default_registry
from databasise.parts.schema import Part
from databasise.seam.engine import Databasise, _build_stores
from databasise.seam.evidence import EvidenceRef
from databasise.seam.query import QueryObject
from databasise.seam.selectors import Selector
from databasise.stores.graph import CozoGraphStore
from databasise.stores.vector import FaissVectorStore
from databasise.tests.seam._probes import trace_row_count

from seam.test_hipporag_write_path import (
    _DOCUMENT_TEXT,
    _HIPPORAG_CAPABILITY,
    _WORKSPACE,
    _StubEmbeddingClient,
    _StubIngestQueryLLMClient,
)

_WS = "w13-05"
_EVIDENCE_NODE = "p"


def _wiring() -> dict:
    return {
        "nodes": {_EVIDENCE_NODE: {"component": "parts-core/passthrough@1.0.0", "kind": "passthrough", "deps": []}},
        "provides": [_EVIDENCE_NODE],
        "evidence_position": {"node": _EVIDENCE_NODE, "namespace": "chunks"},
    }


async def _run_to_minting(engine: Databasise):
    """(envelope, raised) for the one-node wiring above."""
    try:
        return await engine._execute_resolved(QueryObject(text="x"), _wiring()), None
    except Exception as exc:  # noqa: BLE001 - the test asserts on what was raised
        return None, exc


def _items_registry(output: dict):
    """The default registry plus a ``test/emit`` part that returns ``output`` verbatim."""
    registry = default_registry()

    async def body(ctx):
        return output

    registry.register(
        Part(
            name_at_version="test/emit@1.0.0",
            kind="passthrough",
            structural_depth="stage",
            effects=[],
            upstream_ref=None,
            body=body,
        )
    )
    return registry


# --- the evidence items guard ------------------------------------------------------------------ #


async def test_an_evidence_node_without_items_is_refused_by_name(tmp_path):
    engine = Databasise(store_root=tmp_path, workspace=_WS, clients={})

    envelope, raised = await _run_to_minting(engine)

    assert envelope is None
    assert type(raised).__name__ == "ForeignEngineRefusalError", repr(raised)
    assert raised.failure_class == "MalformedDriverOutput"
    assert type(raised.cause).__name__ == "MalformedEvidenceItemError", repr(raised.cause)


async def test_the_missing_items_refusal_is_raised_before_any_envelope_is_constructed(tmp_path):
    engine = Databasise(store_root=tmp_path, workspace=_WS, clients={})

    envelope, raised = await _run_to_minting(engine)

    # WIRE-12 (D-04): the run is persisted before the refusal, and the refusal names its trace.
    assert raised is not None and envelope is None
    assert trace_row_count(tmp_path) == 1
    assert isinstance(getattr(raised, "trace_token", None), str)


async def test_an_empty_items_list_mints_no_evidence(tmp_path):
    engine = Databasise(
        store_root=tmp_path, workspace=_WS, clients={}, registry=_items_registry({"items": []})
    )
    wiring = _wiring()
    wiring["nodes"][_EVIDENCE_NODE]["component"] = "test/emit@1.0.0"

    try:
        envelope = await engine._execute_resolved(QueryObject(text="x"), wiring)
        raised = None
    except Exception as exc:  # noqa: BLE001
        envelope, raised = None, exc

    assert raised is None, repr(raised)
    assert envelope.evidence == []


async def test_an_undeclared_evidence_position_mints_no_evidence(tmp_path):
    engine = Databasise(store_root=tmp_path, workspace=_WS, clients={})
    wiring = _wiring()
    del wiring["evidence_position"]

    try:
        envelope = await engine._execute_resolved(QueryObject(text="x"), wiring)
        raised = None
    except Exception as exc:  # noqa: BLE001
        envelope, raised = None, exc

    assert raised is None, repr(raised)
    assert envelope.evidence == []


# --- no dead keyword --------------------------------------------------------------------------- #


@pytest.mark.parametrize("method", ["query", "query_stream", "compare"])
def test_the_query_methods_take_no_discarded_keyword(method):
    parameters = inspect.signature(getattr(Databasise, method)).parameters

    assert "deb" + "ug" not in parameters


def test_resolve_trace_keeps_its_keyword():
    assert "deb" + "ug" in inspect.signature(Databasise.resolve_trace).parameters


def test_build_stores_docstring_names_its_callers():
    doc = _build_stores.__doc__ or ""

    assert "delete_document" in doc
    assert "_execute_resolved" in doc
    assert "retry_document" in doc
    assert "health" not in doc


# --- pins of legs already met ------------------------------------------------------------------ #


async def test_delete_opens_the_corpus_delete_wirings_namespaces(tmp_path, monkeypatch):
    import databasise.seam.engine as engine_module

    captured: dict = {}

    class _Stop(Exception):
        pass

    def _record(store_root, workspace, resolved=None, *, into=None, operation="open_stores"):
        captured["operation"] = operation
        captured["store_namespaces"] = (resolved or {}).get("store_namespaces")
        raise _Stop

    monkeypatch.setattr(engine_module, "_build_stores", _record)
    engine = Databasise(store_root=tmp_path, workspace=_WORKSPACE, clients={})

    try:
        await engine.delete_document("doc-1", Selector(capability=_HIPPORAG_CAPABILITY))
    except _Stop:
        pass

    assert captured.get("operation") == "delete"
    assert captured.get("store_namespaces") == {"kv": "hipporag-text-chunks", "graph": "hipporag-graph"}


@pytest.fixture
async def chunks_only_root(store_root: Path) -> Path:
    store = FaissVectorStore("chunks", _WS, store_root)
    await store.upsert(["c1"], [[1.0, 0.0, 0.0]], [{"content": "alpha"}])
    await store.index_done_callback()
    return store_root


async def test_resolve_evidence_never_builds_the_graph_store(chunks_only_root, monkeypatch):
    built: list[str] = []
    real_init = CozoGraphStore.__init__

    def _spy(self, *args, **kwargs):
        built.append("graph")
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(CozoGraphStore, "__init__", _spy)
    engine = Databasise(store_root=chunks_only_root, workspace=_WS)

    record = await engine.resolve_evidence(EvidenceRef(ref="c1", namespace="chunks", kind="text_chunk"))

    assert record["content"] == "alpha"
    assert built == []


async def test_resolve_evidence_succeeds_while_the_graph_namespace_is_held(chunks_only_root):
    held = CozoGraphStore("chunk_entity_relation", _WS, chunks_only_root)
    try:
        engine = Databasise(store_root=chunks_only_root, workspace=_WS)
        record = await engine.resolve_evidence(EvidenceRef(ref="c1", namespace="chunks", kind="text_chunk"))
    finally:
        await held.finalize()

    assert record["content"] == "alpha"


class _NonJsonNerLLM(_StubIngestQueryLLMClient):
    """Answers every NER prompt with text that is not JSON, so the openie node fails."""

    async def chat(self, messages, **kwargs):
        result = await super().chat(messages, **kwargs)
        content = messages[0]["content"]
        if "---Recognised Entities---" in content or "---Candidate Facts---" in content:
            return result
        return type(result)(
            text="not json", tokens=result.tokens, resolved_model_identity=result.resolved_model_identity
        )


async def test_a_failed_openie_ingest_names_its_real_exception(store_root):
    from databasise.seam.corpus import IngestDocument

    engine = Databasise(
        store_root=store_root,
        workspace=_WORKSPACE,
        clients={"embedding": _StubEmbeddingClient(), "llm": _NonJsonNerLLM()},
    )
    caught = None
    try:
        await engine.ingest(
            IngestDocument(document_id="doc-openie-fail", text=_DOCUMENT_TEXT),
            selector=Selector(capability=_HIPPORAG_CAPABILITY),
        )
    except Exception as exc:  # noqa: BLE001
        caught = exc

    assert type(caught).__name__ == "ForeignEngineRefusalError", repr(caught)
    assert type(caught.cause).__name__ == "ExtractionFailedError", repr(caught.cause)
