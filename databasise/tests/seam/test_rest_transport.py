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
    DisagreeingPromotionTraceIdsError,
    DuplicateComparisonKeyError,
    EmptyComparisonRequestError,
    EmptyPromotionTraceIdsError,
    EmptyQueryObjectError,
    ForbiddenSelectorInputError,
    ForeignEngineRefusalError,
    GateVerbNotBuiltError,
    InvalidChangeOriginError,
    MalformedBase64PayloadError,
    MalformedSelectorPayloadError,
    MeasurementPostureRefusalError,
    MutableStoreComparisonExcludedError,
    NoRawUploadPathForModalityError,
    NoWritePathForModalityError,
    OversizedDocumentError,
    PageSizeExceededError,
    SeamRefusalError,
    ActiveGenerationRetirementError,
    TombstonedGenerationError,
    UncalibratedFloorRefusalError,
    UnconsumableQueryMemberError,
    UnknownDocumentError,
    UnknownGenerationVersionError,
    UnknownJobError,
    UnsatisfiableSelectorError,
)
from databasise.ledger.ledger import Ledger, LedgerRecord
from databasise.parts.registry import default_registry
from databasise.seam.rest import create_app
from databasise.seam.tokens import UnbudgetableParticipantError
from databasise.seam.trace_store import TraceStore, UnknownTraceReferenceError
from databasise.tests._ast_helpers import called_names
from databasise.wirings.resolve import all_wirings, resolve_arm
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


def test_delete_request_default_body_is_frozen_and_cannot_be_silently_mutated():
    """06-REVIEW.md WR-01: ``DeleteRequest()``, used as ``delete_document``'s own module-level
    default ``body`` value, is a single mutable ``BaseModel`` instance constructed once at
    route-registration time and reused as the default for every request that omits a body.
    Unless the model is frozen, a future edit that reads then writes a field on that shared
    default would silently corrupt every subsequent no-body request in the same process. Fails
    without the fix: pydantic v2 permits attribute reassignment on a non-frozen ``BaseModel``."""
    import pydantic

    from databasise.seam.rest import DeleteRequest

    body = DeleteRequest()
    with pytest.raises(pydantic.ValidationError):
        body.selector = None


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
    NoWritePathForModalityError: lambda: NoWritePathForModalityError(operation="delete"),
    NoRawUploadPathForModalityError: lambda: NoRawUploadPathForModalityError(operation="ingest"),
    UnknownJobError: lambda: UnknownJobError(job_id="no-such-job"),
    PageSizeExceededError: lambda: PageSizeExceededError(requested=101, limit=100),
    MalformedBase64PayloadError: lambda: MalformedBase64PayloadError(field="raw_base64"),
    MalformedSelectorPayloadError: lambda: MalformedSelectorPayloadError(field="selector"),
    EmptyPromotionTraceIdsError: lambda: EmptyPromotionTraceIdsError(alias="some-alias"),
    DisagreeingPromotionTraceIdsError: lambda: DisagreeingPromotionTraceIdsError(
        trace_ids=["trace-1", "trace-2"]
    ),
    InvalidChangeOriginError: lambda: InvalidChangeOriginError(change_origin="guessed"),
    GateVerbNotBuiltError: lambda: GateVerbNotBuiltError(verb="check"),
    MeasurementPostureRefusalError: lambda: MeasurementPostureRefusalError(
        verb="promote-next", mutation_class="answer-level"
    ),
    UncalibratedFloorRefusalError: lambda: UncalibratedFloorRefusalError(
        verb="promote-next", mutation_class="retrieval-side"
    ),
    UnknownGenerationVersionError: lambda: UnknownGenerationVersionError(
        alias="some-alias", version="9.9.9"
    ),
    TombstonedGenerationError: lambda: TombstonedGenerationError(
        alias="some-alias", version="1.0.0"
    ),
    ActiveGenerationRetirementError: lambda: ActiveGenerationRetirementError(
        alias="some-alias", version="1.0.0"
    ),
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


def test_upload_with_malformed_selector_field_returns_422_not_a_raw_500(client):
    """CR-02 gap closure: before the fix, a malformed `selector` form field on
    `POST /documents/upload` raised a raw `pydantic.ValidationError` that escaped every
    registered handler, producing an unhandled 500 — a direct violation of this module's own
    "non-success, never a 2xx" / "422 used uniformly for every refusal kind" design contract.
    Reproduced against the real app + real `TestClient`, not a mock."""
    response = client.post(
        "/documents/upload",
        files={"file": ("doc.txt", b"hello world", "text/plain")},
        data={"selector": "{not valid json"},
    )

    assert response.status_code == 422, (
        f"expected 422 for a malformed selector field, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body["refusal_type"] == "MalformedSelectorPayloadError"


# --------------------------------------------------------------------------------------------- #
# 07-03-PLAN.md Task 1: POST /promote, /rollback, /retire — thin adapters over the identical
# Databasise methods 07-01/07-02 landed, proven in exact parity with the in-process call.
# --------------------------------------------------------------------------------------------- #


def _seed_trace(store_root, arm_name: str) -> str:
    """Persist a minimal trace record naming exactly ``arm_name``'s own resolved node id set,
    through the same ``TraceStore.persist()`` path the engine uses — mirrors
    ``tests/seam/test_promote.py``'s own helper of the identical name and shape."""
    resolved = next(resolved for name, resolved in all_wirings() if name == arm_name)
    node_ids = sorted(resolved.get("nodes", {}).keys())
    fake_record = {
        "run_id": f"fake-run-{arm_name}",
        "wiring_id": resolved.get("wiring_id"),
        "wiring_instance_hash": f"sha256:{'0' * 63}{len(node_ids) % 10}",
        "arm_id": "seam",
        "nodes": [{"node_id": node_id} for node_id in node_ids],
    }
    return TraceStore(store_root).persist(fake_record)


# The exclusion below is unavoidable, not a weakening of the plan's own "identical ledger records"
# instruction: TraceStore.persist() mints a fresh secrets.token_urlsafe() reference per call (D-06,
# databasise/seam/trace_store.py's own module docstring) — two independent stores can never
# literally share a trace token value, exactly why test_dual_transport.py already excludes the
# structurally identical `trace_token` field from its own envelope comparison.
_LEDGER_RECORD_EXCLUDED_FIELDS = frozenset({"promotion_trace_ids"})


async def test_post_promote_returns_the_same_result_as_the_in_process_call(tmp_path):
    rest_root = tmp_path / "rest-store"
    ip_root = tmp_path / "ip-store"
    rest_root.mkdir()
    ip_root.mkdir()
    alias = "promote-rest-parity-alias"

    rest_app = create_app(store_root=rest_root, workspace="promote-rest-parity")
    rest_trace = _seed_trace(rest_root, "naive")
    rest_response = TestClient(rest_app).post(
        "/promote",
        json={"alias": alias, "trace_ids": [rest_trace], "change_origin": "human_edit"},
    )
    assert rest_response.status_code == 200
    rest_body = rest_response.json()

    ip_engine = Databasise(store_root=ip_root, workspace="promote-ip-parity")
    ip_trace = _seed_trace(ip_root, "naive")
    ip_result = await ip_engine.promote(alias, [ip_trace], "human_edit")
    ip_body = ip_result.model_dump()

    compared_response_fields = [field for field in ip_body if field != "generation_ordinal"]
    assert compared_response_fields
    for field in compared_response_fields:
        assert rest_body[field] == ip_body[field], f"response field {field!r} diverged"

    rest_record = Ledger(rest_root).by_alias(alias)
    ip_record = Ledger(ip_root).by_alias(alias)
    compared_record_fields = [
        field
        for field in LedgerRecord.__dataclass_fields__
        if field not in _LEDGER_RECORD_EXCLUDED_FIELDS
    ]
    assert compared_record_fields
    for field in compared_record_fields:
        assert getattr(rest_record, field) == getattr(ip_record, field), (
            f"ledger record field {field!r} diverged"
        )


async def test_post_rollback_and_post_retire_round_trip(tmp_path):
    rest_root = tmp_path / "rollback-retire-rest-store"
    ip_root = tmp_path / "rollback-retire-ip-store"
    rest_root.mkdir()
    ip_root.mkdir()
    rollback_alias = "rollback-rest-parity-alias"
    retire_alias = "retire-rest-parity-alias"

    rest_app = create_app(store_root=rest_root, workspace="rollback-retire-rest-parity")
    rest_client = TestClient(rest_app)
    ip_engine = Databasise(store_root=ip_root, workspace="rollback-retire-ip-parity")

    # Rollback: two promotions (1.0.0, then 1.1.0 — same arm, MINOR bump), then roll back to
    # 1.0.0. Identically seeded in both stores.
    for root, engine_or_client, is_rest in ((rest_root, rest_client, True), (ip_root, ip_engine, False)):
        trace_1 = _seed_trace(root, "naive")
        trace_2 = _seed_trace(root, "naive")
        if is_rest:
            engine_or_client.post(
                "/promote",
                json={"alias": rollback_alias, "trace_ids": [trace_1], "change_origin": "human_edit"},
            )
            engine_or_client.post(
                "/promote",
                json={"alias": rollback_alias, "trace_ids": [trace_2], "change_origin": "human_edit"},
            )
        else:
            await engine_or_client.promote(rollback_alias, [trace_1], "human_edit")
            await engine_or_client.promote(rollback_alias, [trace_2], "human_edit")

    rest_rollback_trace = _seed_trace(rest_root, "naive")
    rest_rollback_response = rest_client.post(
        "/rollback",
        json={
            "alias": rollback_alias,
            "version": "1.0.0",
            "trace_ids": [rest_rollback_trace],
            "change_origin": "human_edit",
        },
    )
    assert rest_rollback_response.status_code == 200
    rest_rollback_body = rest_rollback_response.json()

    ip_rollback_trace = _seed_trace(ip_root, "naive")
    ip_rollback_result = await ip_engine.rollback(
        rollback_alias, "1.0.0", [ip_rollback_trace], "human_edit"
    )
    ip_rollback_body = ip_rollback_result.model_dump()

    for field in [f for f in ip_rollback_body if f != "generation_ordinal"]:
        assert rest_rollback_body[field] == ip_rollback_body[field], (
            f"rollback response field {field!r} diverged"
        )

    # Retire: promote "naive" (1.0.0) then "bypass" (2.0.0, MAJOR — a differing declared
    # surface), so the active generation is not the one being retired; retire targets 1.0.0.
    for root, engine_or_client, is_rest in ((rest_root, rest_client, True), (ip_root, ip_engine, False)):
        trace_naive = _seed_trace(root, "naive")
        trace_bypass = _seed_trace(root, "bypass")
        if is_rest:
            engine_or_client.post(
                "/promote",
                json={"alias": retire_alias, "trace_ids": [trace_naive], "change_origin": "human_edit"},
            )
            engine_or_client.post(
                "/promote",
                json={"alias": retire_alias, "trace_ids": [trace_bypass], "change_origin": "human_edit"},
            )
        else:
            await engine_or_client.promote(retire_alias, [trace_naive], "human_edit")
            await engine_or_client.promote(retire_alias, [trace_bypass], "human_edit")

    rest_retire_trace = _seed_trace(rest_root, "naive")
    rest_retire_response = rest_client.post(
        "/retire",
        json={
            "alias": retire_alias,
            "version": "1.0.0",
            "trace_ids": [rest_retire_trace],
            "change_origin": "human_edit",
        },
    )
    assert rest_retire_response.status_code == 200
    rest_retire_body = rest_retire_response.json()

    ip_retire_trace = _seed_trace(ip_root, "naive")
    ip_retire_result = await ip_engine.retire(retire_alias, "1.0.0", [ip_retire_trace], "human_edit")
    ip_retire_body = ip_retire_result.model_dump()

    for field in [f for f in ip_retire_body if f != "generation_ordinal"]:
        assert rest_retire_body[field] == ip_retire_body[field], (
            f"retire response field {field!r} diverged"
        )


_PHASE_7_REFUSAL_CLASSES = (
    EmptyPromotionTraceIdsError,
    DisagreeingPromotionTraceIdsError,
    InvalidChangeOriginError,
    MeasurementPostureRefusalError,
    UncalibratedFloorRefusalError,
    GateVerbNotBuiltError,
    UnknownGenerationVersionError,
    TombstonedGenerationError,
    ActiveGenerationRetirementError,
)


@pytest.mark.parametrize("exc_cls", _PHASE_7_REFUSAL_CLASSES)
def test_every_new_refusal_maps_to_non_2xx(probe_app, exc_cls):
    """07-03-PLAN.md Task 1's own named test: every one of Phase 7's nine refusal subclasses maps
    to a non-2xx REST response through the single pre-existing handler — narrower and
    explicitly-Phase-7-scoped than the exhaustive parametrized walk above, which already covers
    this set (and every other registered subclass) via `_REFUSAL_FACTORIES`."""
    response = TestClient(probe_app).post(f"/_test/raise/{exc_cls.__name__}")
    assert not (200 <= response.status_code < 300), (
        f"{exc_cls.__name__} mapped to a success status {response.status_code}"
    )
    assert response.json()["refusal_type"] == exc_cls.__name__


def test_promote_route_body_carries_no_logic(client):
    """The refusal response for a refusing /promote call is produced by the one registered
    `_refusal_response` handler, not a route-local except block — asserted by reconstructing the
    handler's own generic `vars(exc)` dump exactly and comparing it byte-for-byte against the real
    response body."""
    response = client.post(
        "/promote",
        json={"alias": "some-alias", "trace_ids": [], "change_origin": "human_edit"},
    )
    assert response.status_code == 422
    exc = EmptyPromotionTraceIdsError(alias="some-alias")
    expected = {"refusal_type": type(exc).__name__, "message": str(exc), "alias": exc.alias}
    assert response.json() == expected


async def test_rest_response_carries_no_internal_identity(tmp_path):
    """The forbidden-token set is derived live from the registry and the resolved "naive" wiring
    at test time — never a literal list — mirroring
    `tests/seam/test_promote.py::test_promotion_result_carries_no_internal_identity`'s own
    convention. Covers promote, rollback and retire together, one shared store."""
    store_root = tmp_path / "identity-store"
    store_root.mkdir()
    resolved_naive = resolve_arm("naive")
    forbidden = set(default_registry().keys()) | set(resolved_naive.get("nodes", {}).keys())

    app = create_app(store_root=store_root, workspace="promote-identity")
    client_ = TestClient(app)
    alias = "identity-alias"

    trace_1 = _seed_trace(store_root, "naive")
    promote_1 = client_.post(
        "/promote", json={"alias": alias, "trace_ids": [trace_1], "change_origin": "human_edit"}
    )
    trace_2 = _seed_trace(store_root, "naive")
    promote_2 = client_.post(
        "/promote", json={"alias": alias, "trace_ids": [trace_2], "change_origin": "human_edit"}
    )
    trace_3 = _seed_trace(store_root, "naive")
    rollback_response = client_.post(
        "/rollback",
        json={
            "alias": alias,
            "version": "1.0.0",
            "trace_ids": [trace_3],
            "change_origin": "human_edit",
        },
    )
    trace_4 = _seed_trace(store_root, "naive")
    retire_response = client_.post(
        "/retire",
        json={
            "alias": alias,
            "version": "1.1.0",
            "trace_ids": [trace_4],
            "change_origin": "human_edit",
        },
    )

    for response in (promote_1, promote_2, rollback_response, retire_response):
        assert response.status_code == 200
        serialized = response.text
        for token in forbidden:
            assert token not in serialized, f"{token!r} leaked into the REST promotion response"
