"""14-06-PLAN.md Task 1 (LEDG-03, D-05, D-08): every alias row resolves or refuses by name.

A row naming ``hipporag`` resolves to the HippoRAG wiring on every selector-taking route; a row
naming a wiring that does not resolve is a 422 ``UnsatisfiableSelectorError`` naming only the
caller's alias (no arm name, no row value, no "known arms"); a store root with no ``ledger.db``
refuses the same way and creates no file. The file imports only names that exist at the phase base
and copies its own stubs, so it collects and fails by assertion there.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.ledger.ledger import Ledger, LedgerRecord
from databasise.runner.trace import TokenAccounting
from databasise.seam.corpus import IngestDocument
from databasise.seam.engine import Databasise
from databasise.seam.query import QueryObject
from databasise.seam.refusals import SeamRefusalError
from databasise.seam.selectors import Selector, _resolve_alias
from databasise.seam.trace_store import TraceStore
from databasise.wirings.resolve import all_wirings

pytest.importorskip("fastapi")
from databasise.seam.rest import create_app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

_VECTOR = [1.0, 0.0, 0.0]
_TEXT = "Ed Wood directed several low-budget films."
_ARM_NAMES = [name for name, _ in all_wirings()]


class _StubEmbeddingClient:
    async def embed(self, texts, **kwargs):
        return EmbeddingResult(
            vectors=[_VECTOR for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


class _StubLLMClient:
    """Answers every HippoRAG index and query prompt; fact-filter keeps nothing."""

    async def chat(self, messages, **kwargs):
        content = messages[0]["content"]
        if "---Candidate Facts---" in content:
            text = json.dumps({"keep_ids": []})
        elif "---Recognised Entities---" in content:
            text = json.dumps({"triples": [["Ed Wood", "directed", "films"]]})
        else:
            text = json.dumps({"entities": ["Ed Wood", "films"]})
        return ChatResult(
            text=text,
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


def _clients() -> dict[str, object]:
    return {"embedding": _StubEmbeddingClient(), "llm": _StubLLMClient()}


def _row(alias: str, mutation_id: str) -> LedgerRecord:
    return LedgerRecord(
        mutation_id=mutation_id,
        mutation_class="retrieval-side",
        parent=None,
        arm_instance_hashes=[],
        effect_size=None,
        verdict="promote",
        evidence_pointer=None,
        proposer_id="test-fixture",
        depth_label="stage",
        tier_of_decision=None,
        decomposition_ratio=None,
        opaque_ttl_renewals=[],
        parity_records=[],
        promotion_provenance="operator_asserted",
        promotion_trace_ids=[],
        change_origin="human_edit",
        record_kind="promotion",
        alias=alias,
    )


def _store_with_rows(tmp_path: Path) -> Path:
    """A store root whose ledger holds ``h`` -> hipporag and ``x`` -> a name no wiring answers to."""
    root = tmp_path / "store_root"
    root.mkdir(parents=True)
    ledger = Ledger(root)
    ledger.append(_row("h", "hipporag"))
    ledger.append(_row("x", "nonexistent"))
    ledger.close()
    return root


def _engine(root: Path) -> Databasise:
    return Databasise(store_root=root, workspace="alias-resolution", clients=_clients())


async def _capture(awaitable) -> BaseException | None:
    try:
        await awaitable
    except Exception as caught:  # noqa: BLE001 - the assertion is on the captured type
        return caught
    return None


def _engine_calls(engine: Databasise, alias: str) -> dict[str, object]:
    selector = Selector(alias=alias)
    return {
        "query": lambda: engine.query(QueryObject(text="What did Ed Wood direct?"), selector),
        "ingest": lambda: engine.ingest(IngestDocument(document_id="doc1", text=_TEXT), selector),
        "delete_document": lambda: engine.delete_document("doc1", selector),
    }


def _rest_calls(client: TestClient, alias: str) -> dict[str, object]:
    selector = {"alias": alias}
    query = {"text": "What did Ed Wood direct?"}
    return {
        "POST /query": lambda: client.post("/query", json={"query": query, "selector": selector}),
        "POST /query/stream": lambda: client.post("/query/stream", json={"query": query, "selector": selector}),
        "POST /compare": lambda: client.post("/compare", json={"query": query, "selectors": [selector]}),
        "POST /documents": lambda: client.post(
            "/documents", json={"document": {"document_id": "doc1", "text": _TEXT}, "selector": selector}
        ),
        "POST /documents/upload": lambda: client.post(
            "/documents/upload",
            files={"file": ("note.txt", _TEXT.encode(), "text/plain")},
            data={"document_id": "doc2", "selector": json.dumps(selector)},
        ),
        "DELETE /documents/doc1": lambda: client.request("DELETE", "/documents/doc1", json={"selector": selector}),
    }


def _leaks(body: str) -> list[str]:
    found = [name for name in _ARM_NAMES if re.search(rf"\b{re.escape(name)}\b", body)]
    found += [phrase for phrase in ("known arms", "nonexistent") if phrase in body]
    return found


async def test_a_hipporag_alias_never_gives_a_500(tmp_path):
    root = _store_with_rows(tmp_path)
    engine = _engine(root)
    for name, call in _engine_calls(engine, "h").items():
        caught = await _capture(call())
        assert caught is None or isinstance(caught, SeamRefusalError), (
            f"engine.{name} under a hipporag alias raised {type(caught).__name__}: {caught}"
        )

    client = TestClient(create_app(store_root=root, workspace="alias-resolution", clients=_clients()),
                        raise_server_exceptions=False)
    for name, call in _rest_calls(client, "h").items():
        response = call()
        assert response.status_code != 500, f"{name} under a hipporag alias returned 500: {response.text}"
        assert "known arms" not in response.text, f"{name}: {response.text}"
        if response.status_code >= 400:
            assert "refusal_type" in response.json(), f"{name}: {response.text}"


async def test_an_unresolvable_alias_row_is_a_named_422(tmp_path):
    root = _store_with_rows(tmp_path)
    engine = _engine(root)
    for name, call in _engine_calls(engine, "x").items():
        caught = await _capture(call())
        assert type(caught).__name__ == "UnsatisfiableSelectorError", (
            f"engine.{name} under an unresolvable row gave {type(caught).__name__}: {caught}"
        )
        assert _leaks(str(caught)) == [], f"engine.{name}: {caught}"

    client = TestClient(create_app(store_root=root, workspace="alias-resolution", clients=_clients()),
                        raise_server_exceptions=False)
    for name, call in _rest_calls(client, "x").items():
        response = call()
        assert response.status_code == 422, f"{name} returned {response.status_code}: {response.text}"
        assert response.json().get("refusal_type") == "UnsatisfiableSelectorError", f"{name}: {response.text}"
        assert _leaks(response.text) == [], f"{name}: {response.text}"


async def test_the_mcp_tools_never_raise_an_unexpected_error_for_either_row(tmp_path):
    try:
        from databasise.mcp import create_server
        from databasise.mcp.server import RefusalToolError
    except ImportError:
        pytest.skip("the `mcp` extra is not installed")
    root = _store_with_rows(tmp_path)
    server = create_server(store_root=root, workspace="alias-resolution", clients=_clients())

    def tools(alias: str) -> dict[str, tuple[str, dict]]:
        selector = {"alias": alias}
        return {
            "query": ("query", {"args": {"query": {"text": "What did Ed Wood direct?"}, "selector": selector}}),
            "ingest": ("ingest", {"args": {"text": _TEXT, "document_id": "doc1", "selector": selector}}),
            "delete": ("delete", {"args": {"document_id": "doc1", "selector": selector}}),
        }

    for name, (tool, arguments) in tools("h").items():
        caught = await _capture(server.call_tool(tool, arguments))
        assert caught is None or isinstance(caught, RefusalToolError), (
            f"{name} under a hipporag alias raised {type(caught).__name__}: {caught}"
        )
    for name, (tool, arguments) in tools("x").items():
        caught = await _capture(server.call_tool(tool, arguments))
        assert isinstance(caught, RefusalToolError), f"{name} gave {type(caught).__name__}: {caught}"
        body = json.loads(str(caught))
        assert body["refusal_type"] == "UnsatisfiableSelectorError", f"{name}: {body}"
        assert _leaks(str(caught)) == [], f"{name}: {caught}"


async def test_promoting_a_hipporag_trace_creates_an_alias_that_resolves(tmp_path):
    root = tmp_path / "store_root"
    root.mkdir(parents=True)
    resolved = next(wiring for name, wiring in all_wirings() if name == "hipporag")
    node_ids = sorted(resolved.get("nodes", {}).keys())
    trace = TraceStore(root).persist(
        {
            "run_id": "fake-run-hipporag",
            "wiring_id": resolved.get("wiring_id"),
            "wiring_instance_hash": f"sha256:{'0' * 63}{len(node_ids) % 10}",
            "arm_id": "seam",
            "nodes": [{"node_id": node_id} for node_id in node_ids],
        }
    )
    promoted = await _capture(Databasise(store_root=root, workspace="alias-resolution").promote("p", [trace], "human_edit"))
    assert promoted is None, f"promote raised {type(promoted).__name__}: {promoted}"

    got, error = None, None
    try:
        got = _resolve_alias("p", store_root=root)
    except Exception as caught:  # noqa: BLE001
        error = caught
    assert error is None, f"_resolve_alias raised {type(error).__name__}: {error}"
    assert got == resolved


async def test_a_store_root_without_a_ledger_refuses_and_stays_empty(tmp_path):
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    caught = await _capture(_engine(fresh).query(QueryObject(text="anything"), Selector(alias="none")))
    assert type(caught).__name__ == "UnsatisfiableSelectorError", f"{type(caught).__name__}: {caught}"
    assert not (fresh / "ledger.db").exists(), "the alias read path created ledger.db"

    # Empty edge: a ledger holding rows for other aliases only refuses identically.
    other = _store_with_rows(tmp_path / "other")
    caught_other = await _capture(_engine(other).query(QueryObject(text="anything"), Selector(alias="none")))
    assert type(caught_other).__name__ == "UnsatisfiableSelectorError", f"{type(caught_other).__name__}"
    assert str(caught_other) == str(caught)
