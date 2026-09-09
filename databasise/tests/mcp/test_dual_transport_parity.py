"""05-07-PLAN.md Task 1 (first half) + Task 3 (the three-way harness): the MCP transport's own
structural/behavior proofs, plus MCP-versus-REST-versus-in-process equality for every one of the
five tools — EMBED-02's one-seam-many-transports claim, proved against three call paths rather
than asserted for a third.

**No ``__init__.py`` in this directory — deliberate, documented deviation from the plan's literal
file list (05-07-PLAN.md Task 1 names ``databasise/tests/mcp/__init__.py``).** Making this
directory a Python package named ``mcp`` collides with the third-party SDK of the identical name:
pytest's default "prepend" import mode computes a test file's dotted module name by walking up
parent directories while an ``__init__.py`` exists, stopping at the first ancestor that lacks one.
``databasise/tests/`` itself has no ``__init__.py`` (confirmed — it is a namespace package, like
its sibling ``databasise/tests/fixtures/``), so adding one *only* to this leaf directory makes
pytest import this file as bare ``mcp.test_dual_transport_parity`` — registering ``sys.modules
["mcp"]`` as *this test package* for the rest of the process. Verified empirically this session:
with the ``__init__.py`` present, ``import mcp`` inside a test in this directory resolved to
``tests/mcp/__init__.py``, not the installed SDK; every other test in the suite that imports the
real ``mcp`` afterward (``databasise/foreign/codebase_memory_mcp_adapter.py``'s own lazy import,
05-06's admission tests) would then break. Omitting the ``__init__.py`` (mirroring
``databasise/tests/fixtures/``'s own precedent) fixes this: pytest imports this file as a bare,
uniquely-named top-level module (``test_dual_transport_parity``, no ``mcp.`` prefix), and
``import mcp`` anywhere in the process keeps resolving to the real SDK. This is a Rule 3 (auto-fix
blocking issue) deviation — recorded in this plan's own SUMMARY.md, not silently taken.
"""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

import pytest

# Skip cleanly (never a collection error) when either optional extra is absent. Deliberately NOT
# `pytest.importorskip("mcp")` for the mcp half: a bare top-level `import mcp` is exactly the
# statement the CWD-shadow (this file's own module docstring, and databasise/mcp/_sdk.py's own
# docstring) can resolve to *this project's own* `databasise/mcp/` package instead of skipping —
# `importorskip` would then see a "successfully imported" (but wrong) module and never skip at
# all, later crashing mid-collection when the genuinely-absent real SDK is needed for real
# (confirmed live this session: a genuinely bare `uv sync` with neither extra installed produced
# a collection *error*, not a clean skip, before this fix). Importing `databasise.mcp` directly
# instead reaches the real failure mode the moment the extra truly is absent (databasise/mcp's own
# init chain raises through `_sdk.import_sdk`), which a plain try/except correctly turns into a
# skip.
try:
    import databasise.mcp  # noqa: F401 - import-for-availability-check only
except ImportError:
    pytest.skip("the `mcp` extra is not installed", allow_module_level=True)

pytest.importorskip("fastapi")

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.mcp import TOOL_NAMES, create_server
from databasise.mcp._sdk import import_sdk
from databasise.runner.trace import TokenAccounting
from databasise.seam.corpus import MAX_PAGE_SIZE, IngestDocument
from databasise.seam.engine import Databasise
from databasise.seam.query import QueryObject
from databasise.seam.refusals import EmptyQueryObjectError
from databasise.seam.rest import create_app
from databasise.tests.seam.conftest import synthetic_naive_store  # noqa: F401 - fixture
from databasise.tests.seam.test_evidence_refs import (
    many_chunks_store,  # noqa: F401 - fixture
)
from databasise.tests.seam.test_rest_corpus_endpoints import (
    _ROUND_TRIP_STATUSES,
    _make_registry,
    _patch_status_and_health,
    _patch_status_sequence,
)
from fastapi.testclient import TestClient

ToolError = import_sdk("mcp.server.mcpserver.exceptions").ToolError

_QUERY_TEXT = "Which films did Ed Wood direct?"
_STUB_COMPLETION = "This is a stub completion for the MCP transport's parity tests."


class _StubEmbeddingClient:
    def __init__(self, vector: list[float]):
        self.vector = vector

    async def embed(self, texts, **kwargs):
        return EmbeddingResult(
            vectors=[self.vector for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


class _StubLLMClient:
    async def chat(self, messages, **kwargs):
        return ChatResult(
            text=_STUB_COMPLETION,
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


def _stub_clients(vector: list[float]) -> dict[str, object]:
    return {"embedding": _StubEmbeddingClient(vector=vector), "llm": _StubLLMClient()}


def _tool_json(result: Any) -> dict[str, Any]:
    """Every tool in this package returns a plain dict, rendered by the SDK as one JSON text
    content block (confirmed live this session against the installed 2.2.0 package) — parsed back
    here for comparison against the REST/in-process shapes."""
    text = "".join(getattr(item, "text", "") or "" for item in result.content)
    return json.loads(text)


def _tool_error_detail(exc: ToolError) -> dict[str, Any]:
    """``ToolError.__str__`` is ``"Error executing tool <name>: <original message>"`` (confirmed
    live this session); the original message here is always :func:`databasise.mcp.server
    ._refusal_detail`'s own JSON encoding — this reads it back from the first ``{``, robust to the
    tool name itself never containing one."""
    text = str(exc)
    return json.loads(text[text.index("{") :])


def _model_or_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else value.model_dump()


# --------------------------------------------------------------------------------------------- #
# Task 1 (first half): structural/behavior proofs the growth rule itself does not cover — that
# lives in test_tool_growth_invariant.py.
# --------------------------------------------------------------------------------------------- #


def test_databasise_mcp_and_mcp_bind_different_modules_in_the_same_process():
    """API-07's own must-have truth: ``databasise.mcp`` (this package) and ``mcp`` (the SDK) are
    two different modules, neither shadowing the other — absolute imports throughout this package
    keep them distinct."""
    import databasise.mcp as databasise_mcp_module

    import mcp as mcp_sdk_module

    assert databasise_mcp_module.__file__ != mcp_sdk_module.__file__
    assert not databasise_mcp_module.__name__.startswith(mcp_sdk_module.__name__ + ".")
    assert not mcp_sdk_module.__name__.startswith(databasise_mcp_module.__name__ + ".")


async def test_create_server_holds_exactly_one_databasise_instance_reachable_for_assertion(tmp_path):
    server = create_server(store_root=tmp_path, workspace="mcp-single-engine")
    assert isinstance(server.engine, Databasise)


async def test_the_registered_tool_set_equals_tool_names_and_has_five_members(tmp_path):
    server = create_server(store_root=tmp_path, workspace="mcp-tool-set")
    tools = await server.list_tools()
    assert sorted(tool.name for tool in tools) == sorted(TOOL_NAMES)
    assert len(TOOL_NAMES) == 5


async def test_ingest_tool_accepts_structured_text_and_base64_raw_shapes(tmp_path):
    server = create_server(store_root=tmp_path, workspace="mcp-ingest-shapes", registry=_make_registry())

    text_job = _tool_json(await server.call_tool("ingest", {"args": {"text": "hello world"}}))
    assert text_job["job_id"]
    assert text_job["enqueued"] == 1

    raw_job = _tool_json(
        await server.call_tool(
            "ingest",
            {
                "args": {
                    "raw_base64": base64.b64encode(b"raw doc bytes").decode("ascii"),
                    "content_type": "text/plain",
                }
            },
        )
    )
    assert raw_job["job_id"]
    assert raw_job["enqueued"] == 1


async def test_a_malformed_raw_base64_refuses_by_name_rather_than_crashing_the_tool(tmp_path):
    """G-05-2 / CR-01b reproduction: a malformed ``raw_base64`` argument must refuse by name
    through the shared mapper, never crash the tool as the SDK's generic ``UnexpectedToolError``.

    Parity note: REST has no base64 ingest shape at all (its raw path is a multipart upload), so
    this refusal has no REST counterpart to compare against. The parity claim proved here is the
    one ROADMAP criterion 5 actually makes — the MCP transport refuses cleanly by name where it
    previously crashed — not that two transports return an identical body for an argument only one
    of them accepts.
    """
    server = create_server(store_root=tmp_path, workspace="mcp-malformed-base64", registry=_make_registry())

    with pytest.raises(ToolError) as exc_info:
        await server.call_tool(
            "ingest", {"args": {"raw_base64": "not-valid-base64!!!", "file_name": "x.txt"}}
        )
    detail = _tool_error_detail(exc_info.value)
    assert detail["refusal_type"] == "MalformedBase64PayloadError"
    assert detail["field"] == "raw_base64"

    # The well-formed round trip still works — proves the refusal is about malformedness, not
    # about the raw shape being broken outright.
    well_formed_job = _tool_json(
        await server.call_tool(
            "ingest",
            {"args": {"raw_base64": base64.b64encode(b"well formed bytes").decode("ascii")}},
        )
    )
    assert well_formed_job["job_id"]


async def test_status_tool_scope_requirements_and_dispatch(tmp_path, monkeypatch):
    server = create_server(store_root=tmp_path, workspace="mcp-status-scopes")
    _patch_status_and_health(monkeypatch, documents=[], counts={"processed": 1})

    with pytest.raises(ToolError):
        # scope="job" requires a job_id — refused before any driver call.
        await server.call_tool("status", {"args": {"scope": "job"}})

    health = _tool_json(await server.call_tool("status", {"args": {"scope": "health"}}))
    assert health["status"] in ("ok", "degraded")

    counts = _tool_json(await server.call_tool("status", {"args": {"scope": "counts"}}))
    assert counts["by_status"] == {"processed": 1}


async def test_a_page_cap_violation_refuses_by_name_over_mcp_exactly_as_it_does_over_rest(tmp_path):
    """G-05-2 / CR-01a reproduction: a page-cap violation must refuse by the same named refusal
    over MCP that REST already returns for the identical request, never the SDK's generic
    ``UnexpectedToolError``. Compares the two transports' own values against each other rather than
    against a hardcoded literal, so this proves parity rather than restating two independent
    expectations."""
    workspace = "mcp-page-cap"
    server = create_server(store_root=tmp_path, workspace=workspace)
    rest_client = TestClient(create_app(store_root=tmp_path, workspace=workspace))

    with pytest.raises(ToolError) as exc_info:
        await server.call_tool("status", {"args": {"scope": "corpus", "limit": 999999}})
    mcp_detail = _tool_error_detail(exc_info.value)
    assert mcp_detail["refusal_type"] == "PageSizeExceededError"

    rest_response = rest_client.get("/corpus", params={"limit": 999999})
    assert rest_response.status_code == 422
    rest_detail = rest_response.json()
    assert rest_detail["refusal_type"] == "PageSizeExceededError"

    assert mcp_detail["requested"] == rest_detail["requested"] == 999999
    assert mcp_detail["limit"] == rest_detail["limit"]

    # scope="job" refuses identically — the pre-check runs before the job is ever looked up, so
    # an arbitrary/nonexistent job_id never reaches the driver.
    with pytest.raises(ToolError) as job_exc_info:
        await server.call_tool(
            "status", {"args": {"scope": "job", "job_id": "arbitrary-job-id", "limit": 999999}}
        )
    assert _tool_error_detail(job_exc_info.value)["refusal_type"] == "PageSizeExceededError"


async def test_the_page_cap_boundary_separates_rather_than_clamps_over_both_transports(
    tmp_path, monkeypatch
):
    """API-07's adjacency edge, resolved explicitly: a call at exactly ``MAX_PAGE_SIZE`` succeeds
    over both transports, and a call at ``MAX_PAGE_SIZE + 1`` is refused by name over both — the
    cap is a boundary that separates, never one that merges into a silent clamp."""
    workspace = "mcp-page-cap-boundary"
    _patch_status_and_health(monkeypatch, documents=[], counts={"processed": 1})
    server = create_server(store_root=tmp_path, workspace=workspace)
    rest_client = TestClient(create_app(store_root=tmp_path, workspace=workspace))

    at_cap = _tool_json(
        await server.call_tool("status", {"args": {"scope": "corpus", "limit": MAX_PAGE_SIZE}})
    )
    assert at_cap["counts"] == {"processed": 1}

    rest_at_cap = rest_client.get("/corpus", params={"limit": MAX_PAGE_SIZE})
    assert rest_at_cap.status_code == 200

    with pytest.raises(ToolError) as exc_info:
        await server.call_tool(
            "status", {"args": {"scope": "corpus", "limit": MAX_PAGE_SIZE + 1}}
        )
    assert _tool_error_detail(exc_info.value)["refusal_type"] == "PageSizeExceededError"

    rest_over_cap = rest_client.get("/corpus", params={"limit": MAX_PAGE_SIZE + 1})
    assert rest_over_cap.status_code == 422
    assert rest_over_cap.json()["refusal_type"] == "PageSizeExceededError"


async def test_resolve_tool_evidence_scope_returns_what_the_in_process_operation_returns(
    synthetic_naive_store,  # noqa: F811 - pytest fixture-by-parameter-name, imported above
):
    server = create_server(
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients=_stub_clients(synthetic_naive_store["query_vector"]),
    )
    envelope = await server.engine.query(QueryObject(text=_QUERY_TEXT))
    ref = envelope.evidence[0]

    tool_resolved = _tool_json(
        await server.call_tool("resolve", {"args": {"scope": "evidence", "evidence_ref": ref.model_dump()}})
    )
    in_process_resolved = await server.engine.resolve_evidence(ref)
    assert tool_resolved == in_process_resolved


async def test_every_seam_refusal_surfaces_as_a_tool_error_never_a_successful_result(tmp_path):
    server = create_server(store_root=tmp_path, workspace="mcp-refusal-mapping")

    with pytest.raises(ToolError) as exc_info:
        await server.call_tool("query", {"args": {"query": {}}})

    assert _tool_error_detail(exc_info.value)["refusal_type"] == "EmptyQueryObjectError"


async def test_two_concurrent_tool_calls_are_served_by_the_same_engine_object(tmp_path, monkeypatch):
    """The concurrency test compares two *captured* engine objects with ``is`` — captured from
    inside the actual method invocation the ``status``/``health`` tool call reaches, never merely
    the outer ``server.engine`` attribute (which would trivially always be the same object and
    prove nothing about whether a second engine gets constructed per call)."""
    server = create_server(store_root=tmp_path, workspace="mcp-concurrency")

    original_health = Databasise.health
    captured: list[Databasise] = []

    async def _spy_health(self: Databasise) -> Any:
        captured.append(self)
        return await original_health(self)

    monkeypatch.setattr(Databasise, "health", _spy_health)

    await asyncio.gather(
        server.call_tool("status", {"args": {"scope": "health"}}),
        server.call_tool("status", {"args": {"scope": "health"}}),
    )

    assert len(captured) == 2
    assert captured[0] is captured[1]
    assert captured[0] is server.engine


# --------------------------------------------------------------------------------------------- #
# Task 3: the three-way (MCP / REST / in-process) equality harness, parametrized over every tool.
# --------------------------------------------------------------------------------------------- #


async def _ingest_scenario(engine, rest_client, server):
    text = "hello world"
    mcp_dict = _tool_json(await server.call_tool("ingest", {"args": {"text": text}}))
    rest_dict = rest_client.post("/documents", json={"document": {"text": text}}).json()
    in_process_dict = _model_or_dict(await engine.ingest(IngestDocument(text=text)))
    return mcp_dict, rest_dict, in_process_dict, {"job_id"}


async def _query_scenario(engine, rest_client, server):
    mcp_dict = _tool_json(await server.call_tool("query", {"args": {"query": {"text": _QUERY_TEXT}}}))
    rest_dict = rest_client.post("/query", json={"query": {"text": _QUERY_TEXT}}).json()
    in_process_dict = _model_or_dict(await engine.query(QueryObject(text=_QUERY_TEXT)))
    return mcp_dict, rest_dict, in_process_dict, {"trace_token"}


async def _delete_scenario(engine, rest_client, server):
    mcp_dict = _tool_json(await server.call_tool("delete", {"args": {"document_id": "deadbeef"}}))
    rest_dict = rest_client.delete("/documents/deadbeef").json()
    in_process_dict = _model_or_dict(await engine.delete_document("deadbeef"))
    return mcp_dict, rest_dict, in_process_dict, set()


async def _status_scenario(engine, rest_client, server):
    mcp_dict = _tool_json(await server.call_tool("status", {"args": {"scope": "counts"}}))
    rest_dict = rest_client.get("/corpus/counts").json()
    in_process_dict = _model_or_dict(await engine.document_counts())
    return mcp_dict, rest_dict, in_process_dict, set()


async def _resolve_scenario(engine, rest_client, server):
    envelope = await engine.query(QueryObject(text=_QUERY_TEXT))
    ref = envelope.evidence[0]
    mcp_dict = _tool_json(
        await server.call_tool("resolve", {"args": {"scope": "evidence", "evidence_ref": ref.model_dump()}})
    )
    rest_dict = rest_client.post("/evidence/resolve", json=ref.model_dump()).json()
    in_process_dict = await engine.resolve_evidence(ref)
    return mcp_dict, rest_dict, in_process_dict, set()


_SCENARIOS = {
    "ingest": _ingest_scenario,
    "query": _query_scenario,
    "delete": _delete_scenario,
    "status": _status_scenario,
    "resolve": _resolve_scenario,
}


@pytest.mark.parametrize("tool_name", TOOL_NAMES)
async def test_mcp_rest_and_in_process_agree_for_every_tool(
    tool_name, tmp_path, synthetic_naive_store, monkeypatch  # noqa: F811 - fixture-by-name
):
    if tool_name in ("query", "resolve"):
        store_root = synthetic_naive_store["store_root"]
        workspace = synthetic_naive_store["workspace"]
        clients = _stub_clients(synthetic_naive_store["query_vector"])
        registry = None
    elif tool_name == "status":
        store_root, workspace, clients, registry = tmp_path, "parity-status", None, None
        _patch_status_and_health(monkeypatch, documents=[], counts={"processed": 1})
    else:
        store_root, workspace, clients, registry = tmp_path, f"parity-{tool_name}", None, _make_registry()

    engine = Databasise(store_root=store_root, workspace=workspace, registry=registry, clients=clients)
    rest_client = TestClient(
        create_app(store_root=store_root, workspace=workspace, registry=registry, clients=clients)
    )
    server = create_server(store_root=store_root, workspace=workspace, registry=registry, clients=clients)

    mcp_dict, rest_dict, in_process_dict, excluded = await _SCENARIOS[tool_name](engine, rest_client, server)

    compared_fields = [field for field in in_process_dict if field not in excluded]
    assert compared_fields, "the compared field set must never be vacuously empty"
    for field in compared_fields:
        assert mcp_dict[field] == rest_dict[field] == in_process_dict[field], (
            f"{tool_name!r} tool field {field!r} diverged across transports: "
            f"mcp={mcp_dict[field]!r} rest={rest_dict[field]!r} in_process={in_process_dict[field]!r}"
        )


async def test_evidence_reference_order_matches_across_all_three_transports_with_multiple_refs(
    many_chunks_store,  # noqa: F811 - pytest fixture-by-parameter-name, imported above
):
    """A single-reference fixture cannot detect a re-sort (05-07-PLAN.md Task 3, action B) —
    ``many_chunks_store`` (imported from ``test_evidence_refs.py``, never duplicated) yields ten."""
    store_root = many_chunks_store["store_root"]
    workspace = many_chunks_store["workspace"]
    clients = _stub_clients(many_chunks_store["query_vector"])

    engine = Databasise(store_root=store_root, workspace=workspace, clients=clients)
    in_process = await engine.query(QueryObject(text="anything"))
    in_process_order = [ref.ref for ref in in_process.evidence]
    assert len(in_process_order) >= 2

    rest_response = TestClient(
        create_app(store_root=store_root, workspace=workspace, clients=clients)
    ).post("/query", json={"query": {"text": "anything"}})
    rest_order = [item["ref"] for item in rest_response.json()["evidence"]]

    server = create_server(store_root=store_root, workspace=workspace, clients=clients)
    mcp_order = [
        item["ref"]
        for item in _tool_json(
            await server.call_tool("query", {"args": {"query": {"text": "anything"}}})
        )["evidence"]
    ]

    assert in_process_order == rest_order == mcp_order


async def test_an_empty_query_object_refuses_identically_across_all_three_transports(tmp_path):
    engine = Databasise(store_root=tmp_path, workspace="parity-refusal")
    with pytest.raises(EmptyQueryObjectError):
        await engine.query(QueryObject())

    rest_response = TestClient(
        create_app(store_root=tmp_path, workspace="parity-refusal")
    ).post("/query", json={"query": {}})
    assert rest_response.status_code == 422
    assert rest_response.json()["refusal_type"] == "EmptyQueryObjectError"

    server = create_server(store_root=tmp_path, workspace="parity-refusal")
    with pytest.raises(ToolError) as exc_info:
        await server.call_tool("query", {"args": {"query": {}}})
    assert _tool_error_detail(exc_info.value)["refusal_type"] == "EmptyQueryObjectError"


async def test_the_mcp_round_trip_observes_the_same_status_sequence_the_rest_round_trip_produces(
    store_root, monkeypatch
):
    """Replicates 05-04's own upload-poll-delete round trip over the ``ingest``/``status``/
    ``delete`` tools, importing ``_ROUND_TRIP_STATUSES`` from the same module the REST round trip
    reads it from (action E) — never a second literal copy."""
    _patch_status_sequence(monkeypatch)
    server = create_server(store_root=store_root, workspace="mcp-round-trip", registry=_make_registry())

    ingest_job = _tool_json(
        await server.call_tool(
            "ingest", {"args": {"text": "hello world", "document_id": "mcp-round-trip-doc"}}
        )
    )
    job_id = ingest_job["job_id"]

    observed_statuses: list[str] = []
    for _ in _ROUND_TRIP_STATUSES:
        status = _tool_json(await server.call_tool("status", {"args": {"scope": "job", "job_id": job_id}}))
        observed_statuses.append(status["documents"][0]["status"])

    assert observed_statuses == _ROUND_TRIP_STATUSES

    delete_outcome = _tool_json(
        await server.call_tool("delete", {"args": {"document_id": "mcp-round-trip-doc"}})
    )
    assert delete_outcome["status"] == "success"


async def test_the_delete_tool_called_twice_matches_the_rest_endpoints_own_two_call_sequence(
    tmp_path,
):
    """API-07's own must-have truth: the ``delete`` tool called twice on the same document id
    returns ``success`` then ``not_found``, matching the REST endpoint's own second-call result
    exactly. The stub registry reports a fixed status per registry instance (never real per-call
    state), so — mirroring ``test_rest_corpus_endpoints.py``'s own ``test_upload_poll_delete_round
    _trip``'s second-delete assertion — the second call is driven against a second registry
    explicitly configured for ``not_found``, the same technique that test uses for the REST
    transport."""
    document_id = "delete-twice-doc"

    success_server = create_server(
        store_root=tmp_path, workspace="mcp-delete-twice", registry=_make_registry()
    )
    first = _tool_json(await success_server.call_tool("delete", {"args": {"document_id": document_id}}))
    assert first["status"] == "success"

    not_found_server = create_server(
        store_root=tmp_path,
        workspace="mcp-delete-twice",
        registry=_make_registry(delete_status="not_found"),
    )
    second = _tool_json(
        await not_found_server.call_tool("delete", {"args": {"document_id": document_id}})
    )
    assert second["status"] == "not_found"

    # The identical two-call sequence over REST, for the identical assertion of what "matching"
    # means — not merely restated as a hardcoded pair of literals.
    rest_client_first = TestClient(
        create_app(store_root=tmp_path, workspace="mcp-delete-twice-rest", registry=_make_registry())
    )
    rest_first = rest_client_first.delete(f"/documents/{document_id}").json()
    rest_client_second = TestClient(
        create_app(
            store_root=tmp_path,
            workspace="mcp-delete-twice-rest",
            registry=_make_registry(delete_status="not_found"),
        )
    )
    rest_second = rest_client_second.delete(f"/documents/{document_id}").json()

    assert first["status"] == rest_first["status"] == "success"
    assert second["status"] == rest_second["status"] == "not_found"
