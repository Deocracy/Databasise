"""04-05-PLAN.md Task 1 (+ Task 2): the optional REST transport (D-15/D-16/D-17, EMBED-02,
API-04, API-10, D-10). Task 1's tracer: an HTTP client posts a query object and receives the same
closed envelope an in-process caller receives, from a transport that holds no logic of its own —
proven behaviorally (the response's own answer/evidence fields carry real values written into the
test's own store fixture, never shape alone) and structurally (an AST walk over
`databasise/seam/rest.py`'s own source finds no call to the selector-resolution, redaction, or
envelope-assembly functions; a second AST walk over `databasise/__init__.py`/
`databasise/seam/__init__.py` finds no module-scope import reaching this optional module).

Task 2 extends this module with SSE streaming/non-streaming content equality, the four §18
operations' REST/in-process parity, the parametrized refusal-mapping proof (enumerated from
`SeamRefusalError`'s own subclass set, never a hand-maintained list), and the two-tier leak gate
run over a real REST response body.
"""

from __future__ import annotations

import ast
import inspect
import json

import pytest

# Skips this entire module cleanly (never a collection error) when the `rest` extra is not
# installed — the plan's own `<verify>` runs a bare `uv run pytest -q` with no extra active
# specifically to prove the embedded library needs no web stack; a collection error here would
# make that verification impossible to satisfy rather than merely skip the REST-specific tests.
pytest.importorskip("fastapi")

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.runner.trace import TokenAccounting
from databasise.seam import redact as redact_module
from databasise.seam import rest as rest_module
from databasise.seam import selectors as selectors_module
from databasise.seam.engine import Databasise
from databasise.seam.evidence import EvidenceRef, UnresolvableEvidenceReferenceError
from databasise.seam.query import QueryObject
from databasise.seam.redact import (
    assert_no_forbidden_keys,
    assert_no_forbidden_values,
    forbidden_identities,
)
from databasise.seam.refusals import (
    AmbiguousIngestPayloadError,
    DuplicateComparisonKeyError,
    EmptyComparisonRequestError,
    EmptyQueryObjectError,
    ForbiddenSelectorInputError,
    ForeignEngineRefusalError,
    MalformedBase64PayloadError,
    MutableStoreComparisonExcludedError,
    OversizedDocumentError,
    PageSizeExceededError,
    SeamRefusalError,
    UnconsumableQueryMemberError,
    UnknownDocumentError,
    UnknownJobError,
    UnsatisfiableSelectorError,
)
from databasise.seam.rest import create_app
from databasise.seam.tokens import UnbudgetableParticipantError
from databasise.seam.trace_store import UnknownTraceReferenceError
from databasise.tests._ast_helpers import called_names
from fastapi.testclient import TestClient

_STUB_COMPLETION = "This is a stub completion for the REST transport's tracer test."


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


def _stub_clients(synthetic_naive_store) -> dict[str, object]:
    return {
        "embedding": _StubEmbeddingClient(vector=synthetic_naive_store["query_vector"]),
        "llm": _StubLLMClient(),
    }


@pytest.fixture
def rest_app(synthetic_naive_store):
    return create_app(
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients=_stub_clients(synthetic_naive_store),
    )


@pytest.fixture
def client(rest_app):
    return TestClient(rest_app)


# --------------------------------------------------------------------------------------------- #
# Task 1: the tracer, and the two structural proofs (import guard, no-logic-in-the-transport).
# --------------------------------------------------------------------------------------------- #


def test_an_http_client_posts_a_query_and_receives_the_same_closed_envelope(client):
    response = client.post("/query", json={"query": {"text": "Which films did Ed Wood direct?"}})

    assert response.status_code == 200
    body = response.json()
    # Real values, never shape alone: the stub client's own configured completion text, and the
    # evidence reference id the test's own store fixture wrote in (databasise/tests/seam/conftest.py).
    assert body["answer"] == _STUB_COMPLETION
    assert [item["ref"] for item in body["evidence"]] == ["chunk-1"]


def test_databasise_and_databasise_seam_are_importable_with_no_web_framework_present():
    """AST walk over the source, not `sys.modules` manipulation (per the plan's own instruction)
    — the assertion is about what the module declares, not a fragile runtime state. Neither module
    may import the optional REST module at module scope, or a consumer without the `rest` extra
    installed gets a raw `ImportError` traceback the moment they `import databasise`."""
    import databasise
    import databasise.seam

    for module in (databasise, databasise.seam):
        tree = ast.parse(inspect.getsource(module))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "rest" not in alias.name.split("."), (
                        f"{module.__name__} imports {alias.name!r} at module scope"
                    )
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                assert "rest" not in module_name.split("."), (
                    f"{module.__name__} imports from {module_name!r} at module scope"
                )


def test_rest_module_calls_no_selector_resolution_redaction_or_envelope_assembly_function():
    """D-17's structural half: `rest.py` may hold `Selector`/`ResponseEnvelope` as type
    annotations (it must, to deserialize/serialize) but must never itself *call* the functions
    that resolve a selector, redact a run record, or assemble an envelope — those calls happen
    exactly once, inside `databasise.seam.engine`. The forbidden name set is read off the
    producing modules' own `__all__`, never a hand-restated list, so a rename there cannot make
    this test silently stop checking anything.

    ``called_names`` is imported from ``databasise.tests._ast_helpers`` (05-07-PLAN.md Task 2,
    action D) — the same function object ``test_tool_growth_invariant.py`` imports for the
    identical proof over ``databasise/mcp/``, never a second, independently maintained copy."""
    called = called_names(inspect.getsource(rest_module))

    forbidden = {"ResponseEnvelope"}
    forbidden.update(name for name in selectors_module.__all__ if name != "Selector")
    forbidden.update(redact_module.__all__)

    overlap = called & forbidden
    assert not overlap, f"databasise/seam/rest.py calls forbidden seam-logic function(s): {overlap}"


# --------------------------------------------------------------------------------------------- #
# Task 2: SSE streaming, the four §18 operations' REST/in-process parity, refusal mapping, leak.
# --------------------------------------------------------------------------------------------- #

_QUERY_BODY = {"query": {"text": "Which films did Ed Wood direct?"}}


def test_rest_module_uses_only_fastapis_native_sse_support_and_hand_formats_no_event_field():
    """FA-11/Pattern 4 (04-RESEARCH.md): no `sse-starlette` dependency, no manually formatted
    `data: ...` framing string — only FastAPI's own `fastapi.sse.EventSourceResponse`."""
    source = inspect.getsource(rest_module)
    assert "sse_starlette" not in source
    assert "fastapi.sse" in source
    assert '"data:' not in source and "'data:" not in source


def _parse_sse_events(body_text: str) -> list[dict]:
    """Every `data: <json>` line's decoded payload, in wire order — the minimal parser this
    module needs; not a general SSE client."""
    events: list[dict] = []
    for block in body_text.strip().split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: ") :]))
    return events


def test_the_streamed_events_assemble_to_the_same_content_the_non_streaming_endpoint_returns(client):
    non_streaming = client.post("/query", json=_QUERY_BODY).json()

    streamed = client.post("/query/stream", json=_QUERY_BODY)
    assert streamed.status_code == 200
    assert streamed.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse_events(streamed.text)
    evidence_events = [event for event in events if event["kind"] == "evidence"]
    final_events = [event for event in events if event["kind"] == "final"]
    assert len(final_events) == 1

    assert [event["evidence"]["ref"] for event in evidence_events] == [
        item["ref"] for item in non_streaming["evidence"]
    ]
    assert final_events[0]["answer"] == non_streaming["answer"]


async def test_rest_streamed_events_equal_databasise_query_streams_in_process_output(
    synthetic_naive_store,
):
    """04-05-PLAN.md Task 2's own acceptance criterion, closing the gap 04-VERIFICATION.md found:
    the CR-01 fix left `post_query_stream` reimplementing `Databasise.query_stream()`'s own
    event-shaping inline instead of reusing it, so nothing proved the two stayed in sync (only
    REST-streaming-vs-REST-non-streaming content equality was tested, above). Both paths now
    iterate the identical `stream_envelope_events()` (`databasise/seam/engine.py`); this test is
    what would fail if a future edit made the two copies diverge again. Excludes only
    `trace_token` from the final event's comparison — the one field two independent runs
    legitimately mint differently (D-06), mirroring `test_dual_transport.py`'s own exclusion.
    """
    clients = _stub_clients(synthetic_naive_store)

    in_process_engine = Databasise(
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients=clients,
    )
    in_process_events = [
        event
        async for event in in_process_engine.query_stream(
            QueryObject(text=_QUERY_BODY["query"]["text"])
        )
    ]

    rest_app = create_app(
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients=clients,
    )
    rest_client = TestClient(rest_app)
    streamed = rest_client.post("/query/stream", json=_QUERY_BODY)
    assert streamed.status_code == 200
    rest_events = _parse_sse_events(streamed.text)

    assert rest_events and in_process_events
    assert len(rest_events) == len(in_process_events)
    for rest_event, in_process_event in zip(rest_events, in_process_events):
        assert rest_event["kind"] == in_process_event["kind"]
        if rest_event["kind"] != "final":
            assert rest_event == in_process_event
            continue
        # D-06: each run mints its own fresh, random trace_token — equal values here would mean
        # the token was not actually random, the opposite of what a passing test should prove.
        assert rest_event["trace_token"] and in_process_event["trace_token"]
        assert rest_event["trace_token"] != in_process_event["trace_token"]
        rest_compared = {k: v for k, v in rest_event.items() if k != "trace_token"}
        in_process_compared = {k: v for k, v in in_process_event.items() if k != "trace_token"}
        assert rest_compared == in_process_compared


def test_a_refusal_via_query_stream_returns_the_documented_non_success_response(client):
    """CR-01: before the fix, every SeamRefusalError raised inside `_execute()` crashed the ASGI
    task group with an unhandled ExceptionGroup instead of returning the 422 every other endpoint
    returns for the identical refusal, because the refusal fired lazily on the streaming
    generator's first iteration, after the SSE response had already begun. Mirrors the
    non-streaming refusal-mapping test's own expectation: a 422 carrying the refusal's own type."""
    response = client.post("/query/stream", json={"query": {}})

    assert response.status_code == 422
    body = response.json()
    assert body["refusal_type"] == "EmptyQueryObjectError"


async def test_evidence_dereference_endpoint_returns_what_the_in_process_operation_returns(
    client, rest_app
):
    query_response = client.post("/query", json=_QUERY_BODY).json()
    ref = query_response["evidence"][0]

    rest_resolved = client.post("/evidence/resolve", json=ref)
    assert rest_resolved.status_code == 200

    in_process_resolved = await rest_app.state.engine.resolve_evidence(EvidenceRef(**ref))
    assert rest_resolved.json() == in_process_resolved


async def test_trace_resolution_endpoint_returns_what_the_in_process_operation_returns(
    client, rest_app
):
    query_response = client.post("/query", json=_QUERY_BODY).json()
    trace_token = query_response["trace_token"]

    rest_resolved = client.post(
        "/trace/resolve", json={"trace_reference": trace_token, "debug": True}
    )
    assert rest_resolved.status_code == 200

    in_process_resolved = await rest_app.state.engine.resolve_trace(trace_token, debug=True)
    assert rest_resolved.json() == in_process_resolved


def test_the_rest_response_body_passes_both_leak_gate_tiers_via_the_imported_redact_module(client):
    """The gate imported from ``databasise.seam.redact`` — never a second, REST-local copy of it
    (D-17's anti-pattern)."""
    response = client.post("/query", json=_QUERY_BODY)
    assert response.status_code == 200
    trace_token = response.json()["trace_token"]

    debug_record = client.post(
        "/trace/resolve", json={"trace_reference": trace_token, "debug": True}
    ).json()

    high_entropy, low_entropy = forbidden_identities(debug_record)

    for value in high_entropy:
        assert value not in response.text, f"high-entropy identity {value!r} leaked into the REST response"

    parsed_response = json.loads(response.text)
    assert_no_forbidden_keys(parsed_response, low_entropy)
    assert_no_forbidden_values(parsed_response, low_entropy)


def test_the_trace_resolve_endpoints_non_debug_output_passes_both_leak_gate_tiers(client):
    """CR-05: the gate run above exercises the `/query` response body and the debug=True trace
    record — the `/trace/resolve {"debug": false}` output (the seam's third §18 operation's own
    *default*, consumer-facing shape) was never run through the gate at all."""
    response = client.post("/query", json=_QUERY_BODY)
    assert response.status_code == 200
    trace_token = response.json()["trace_token"]

    debug_record = client.post(
        "/trace/resolve", json={"trace_reference": trace_token, "debug": True}
    ).json()
    non_debug_response = client.post(
        "/trace/resolve", json={"trace_reference": trace_token, "debug": False}
    )
    assert non_debug_response.status_code == 200

    high_entropy, low_entropy = forbidden_identities(debug_record)

    for value in high_entropy:
        assert value not in non_debug_response.text, (
            f"high-entropy identity {value!r} leaked into the non-debug /trace/resolve response"
        )

    non_debug_body = json.loads(non_debug_response.text)
    assert_no_forbidden_keys(non_debug_body, low_entropy)
    assert_no_forbidden_values(non_debug_body, low_entropy)


# --------------------------------------------------------------------------------------------- #
# T-04-27: every seam refusal maps to a non-success response carrying its own named value, never
# a generic 500 — enumerated from SeamRefusalError's own subclass set at test time.
# --------------------------------------------------------------------------------------------- #

# One factory per known refusal type, keyed by class — a plausible instance this test can raise
# and inspect. If a later phase adds a subclass without adding a factory here, the parametrized
# test below fails loudly (a missing dict key) rather than silently skipping it — the same
# "cannot silently fall through" property the plan requires of the production handler, applied to
# this test's own coverage.
_REFUSAL_FACTORIES: dict[type[SeamRefusalError], object] = {
    EmptyQueryObjectError: lambda: EmptyQueryObjectError(QueryObject()),
    EmptyComparisonRequestError: lambda: EmptyComparisonRequestError(),
    DuplicateComparisonKeyError: lambda: DuplicateComparisonKeyError(key="reads_vector"),
    MutableStoreComparisonExcludedError: lambda: MutableStoreComparisonExcludedError(
        component="codebase-memory-mcp@0.1.0"
    ),
    UnconsumableQueryMemberError: lambda: UnconsumableQueryMemberError("embedding"),
    UnsatisfiableSelectorError: lambda: UnsatisfiableSelectorError(
        selector_kind="capability", requested=["reads_space"]
    ),
    ForbiddenSelectorInputError: lambda: ForbiddenSelectorInputError(
        member_name="alias", value="a" * 64
    ),
    UnknownTraceReferenceError: lambda: UnknownTraceReferenceError("bogus-token"),
    UnbudgetableParticipantError: lambda: UnbudgetableParticipantError("some-node"),
    UnresolvableEvidenceReferenceError: lambda: UnresolvableEvidenceReferenceError(
        EvidenceRef(ref="missing", namespace="chunks", kind="text_chunk")
    ),
    ForeignEngineRefusalError: lambda: ForeignEngineRefusalError(
        operation="ingest", cause=RuntimeError("stub subprocess failure")
    ),
    AmbiguousIngestPayloadError: lambda: AmbiguousIngestPayloadError(set_members=["text", "raw"]),
    OversizedDocumentError: lambda: OversizedDocumentError(actual_bytes=100, limit_bytes=10),
    UnknownDocumentError: lambda: UnknownDocumentError(document_id="../escape"),
    UnknownJobError: lambda: UnknownJobError(job_id="no-such-job"),
    PageSizeExceededError: lambda: PageSizeExceededError(requested=101, limit=100),
    MalformedBase64PayloadError: lambda: MalformedBase64PayloadError(field="raw_base64"),
}


def _all_seam_refusal_subclasses() -> list[type[SeamRefusalError]]:
    """Every currently-defined subclass of ``SeamRefusalError``, walked recursively (not just
    direct children) — this is what makes the enumeration match the plan's own instruction to
    walk the base class's subclasses rather than hand-maintain a list."""
    discovered: set[type[SeamRefusalError]] = set()
    frontier = list(SeamRefusalError.__subclasses__())
    while frontier:
        current = frontier.pop()
        if current in discovered:
            continue
        discovered.add(current)
        frontier.extend(current.__subclasses__())
    return sorted(discovered, key=lambda cls: cls.__name__)


def test_the_refusal_handler_is_registered_once_at_the_application_level(rest_app):
    """D-10/T-04-27: one application-level handler, registered on the base class — never a
    per-endpoint try/except (the plan's own prohibition)."""
    assert rest_app.exception_handlers.get(SeamRefusalError) is not None


@pytest.fixture
def probe_app(rest_app):
    """One test-only route added to the *same* production app instance the other tests in this
    module build — so the parametrized test below exercises the actual registered
    ``SeamRefusalError`` handler, never a re-implementation of it."""

    @rest_app.post("/_test/raise/{class_name}")
    async def _raise_named_refusal(class_name: str):
        for exc_cls, factory in _REFUSAL_FACTORIES.items():
            if exc_cls.__name__ == class_name:
                raise factory()
        raise AssertionError(f"no test factory registered for {class_name!r}")

    return rest_app


@pytest.mark.parametrize("exc_cls", _all_seam_refusal_subclasses())
def test_every_refusal_subclass_maps_to_a_non_success_status_carrying_its_named_value(
    probe_app, exc_cls
):
    assert exc_cls in _REFUSAL_FACTORIES, (
        f"{exc_cls.__name__} has no test factory registered in this module — a refusal type was "
        "added without extending this test, which is exactly the silent-fall-through this test "
        "exists to prevent"
    )
    response = TestClient(probe_app).post(f"/_test/raise/{exc_cls.__name__}")

    assert not (200 <= response.status_code < 300), (
        f"{exc_cls.__name__} mapped to a success status {response.status_code}"
    )
    body = response.json()
    assert body["refusal_type"] == exc_cls.__name__

    instance = _REFUSAL_FACTORIES[exc_cls]()
    for key, value in vars(instance).items():
        # CR-03: a leading-underscore attribute (UnbudgetableParticipantError's own
        # `_internal_node_id`) is deliberately never exposed in the response body — see
        # `_refusal_response`'s own docstring. Asserting its *absence* here, rather than skipping
        # it silently, is what keeps this generic test from re-enshrining the leak it was fixed to
        # prevent.
        if key.startswith("_"):
            assert key not in body, (
                f"{exc_cls.__name__}'s private attribute {key!r} leaked into the response body"
            )
            continue
        if isinstance(value, EvidenceRef | QueryObject):
            value = value.model_dump()
        elif isinstance(value, BaseException):
            # ForeignEngineRefusalError's own `cause` attribute — mirrors rest.py's own
            # _refusal_response stringification of a raw exception value (not JSON-serializable
            # as-is).
            value = str(value)
        assert body.get(key) == value, (
            f"{exc_cls.__name__}'s {key!r} attribute missing or mismatched in the response body"
        )
