"""``databasise.seam.rest`` — the optional REST transport (D-15/D-16/D-17, EMBED-02, API-04,
ROADMAP criterion 5). Never imported at module scope by ``databasise/__init__.py`` or
``databasise/seam/__init__.py`` — only a consumer who has installed the ``rest`` extra, and who
explicitly imports this module, pays the FastAPI-absent cost (Pattern 3, 04-RESEARCH.md).

**05-04-PLAN.md Task 2: the corpus-side operations, over the identical thin-adapter shape.**
``POST /documents``, ``POST /documents/upload``, ``GET /jobs/{job_id}``,
``DELETE /documents/{document_id}``, ``GET /health``, ``GET /corpus`` and ``GET /corpus/counts``
carry every corpus-side operation (API-01, API-02, API-06) this transport now exposes — each body
is still exactly deserialize-then-await-then-return, the identical rule the query-side endpoints
above already prove. ``POST /documents`` and ``POST /documents/upload`` are two delivery shapes of
one §18 operation (``Databasise.ingest``) — the same relationship ``/query`` and ``/query/stream``
already have — so the surface has not grown an operation, only a second way to reach the same one.
The one route with more than one statement is the upload route (it must read the multipart file's
bytes before it can build an ``IngestDocument``); it still contains no selector resolution, no
redaction and no envelope assembly, so ``test_rest_transport.py``'s AST proof keeps passing over
the enlarged module.

**06-03-PLAN.md: ``POST /compare`` — API-08's comparison operation.** One awaited call to
``engine.compare(body.query, body.selectors)`` and a return, mirroring ``POST /query``'s own shape
exactly. The registered application-level ``SeamRefusalError`` handler already maps
``EmptyComparisonRequestError``/``UnsatisfiableSelectorError`` to the status ``_status_for``
assigns (422) with no per-route handling — see ``databasise/tests/seam/test_rest_transport.py``'s own
``_REFUSAL_FACTORIES``.

**Thin adapter, provably (D-17).** Every endpoint body below is exactly: deserialize the request
into the same ``QueryObject``/``Selector``/``EvidenceRef`` shapes an in-process caller constructs,
await the identical ``Databasise`` method an in-process caller awaits, and return the result for
FastAPI to serialize. No selector resolution, no redaction and no envelope assembly happens in
this module — those live in ``databasise.seam.engine``/``selectors``/``envelope``/``redact``, and
``databasise/tests/seam/test_rest_transport.py`` proves the absence by walking this module's own
AST rather than by convention. One application-level exception handler is registered on
``SeamRefusalError`` itself, and Starlette matches every subclass through the exception's MRO, so
a refusal type added later cannot silently fall through to a generic 500 (T-04-27).

**Exposure note (T-04-25 Spoofing, T-04-26 Denial of Service; disposition: transfer,
04-05-PLAN.md's threat register).** This app ships with no authentication, no authorization, no
TLS termination, and no rate limiting. No requirement in this phase's set (API-03, API-04, API-05,
API-10, API-11, EMBED-02, MACH-11) asks for any of them, and a partial auth story would be worse
than none — a consumer who trusted a half-built auth check would be worse off than one who knew
there was none. This is an optional, locally-bound embedded surface: binding, TLS termination,
connection-count/timeout/body-size limits and access control are the operator's own boundary, not
this module's. FastAPI's native ``EventSourceResponse`` (see the streaming endpoint below) handles
SSE keep-alive and buffering headers; it does not handle any of the above.

**09-01-PLAN.md (SEAM-02, D-01): one refusal body.** Every refusal reaches the client as the
top-level ``{refusal_type, message, <public attributes>}`` body with no ``detail`` wrapper. A
refusal raised inside a pydantic validator is unwrapped from ``ctx.error`` by the
``RequestValidationError`` handler; when one request carries both a schema error and a refusal,
the refusal body wins. FastAPI's own ``{detail: [...]}`` shape remains only for schema errors with
no refusal (wrong JSON types) and is the only other documented 4xx shape. The Phase 8 launcher
guards (TrustedHost 400, Origin 403 ``{"detail": "origin not allowed"}`` in
``launcher/serve_rest.py``) run before the seam and are transport guards that keep their own
shapes, not refusals (D-13). The refusal shape covers every refusal raised by ``create_app`` routes
and MCP tools.

**08-08-PLAN.md (RUN-08, D-12): ``create_app(cors_origins=...)``.** An explicit, opt-in CORS
allow-list of exact ``scheme://host[:port]`` origins so a browser console on another origin can
call this seam. Empty (the default) adds no middleware and the app behaves exactly as before.
Never ``*``, never credentials: seam authentication stays a separate, open decision.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

try:
    from fastapi import Depends, FastAPI, Form, Query, UploadFile
    from fastapi.exception_handlers import request_validation_exception_handler
    from fastapi.exceptions import RequestValidationError
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.requests import Request
    from fastapi.responses import JSONResponse, Response
    from fastapi.sse import EventSourceResponse
except ImportError as exc:  # pragma: no cover - exercised only without the `rest` extra installed
    raise ImportError(
        "databasise.seam.rest requires the optional REST transport dependencies. "
        "Install with: pip install 'databasise[rest]' (or `uv sync --extra rest`)."
    ) from exc

from pydantic import BaseModel, ConfigDict, StrictBool, ValidationError

from databasise import __version__
from databasise.parts.registry import PartRegistry
from databasise.seam.corpus import (
    CorpusStatus,
    DeletionOutcome,
    DocumentCounts,
    HealthReport,
    IngestDocument,
    IngestJob,
    JobStatus,
    checked_page,
)
from databasise.seam.engine import Databasise, stream_envelope_events
from databasise.seam.envelope import PromotionResult, ResponseEnvelope
from databasise.seam.evidence import EvidenceRef
from databasise.seam.query import QueryObject
from databasise.seam.refusals import (
    ForeignEngineRefusalError,
    MalformedSelectorPayloadError,
    SeamRefusalError,
    StoreBusyError,
    UnknownGenerationVersionError,
    UnknownJobError,
    UnknownTraceReferenceError,
    UnresolvableEvidenceReferenceError,
    refusal_body,
    refusal_from_errors,
)
from databasise.seam.selectors import Selector

# The HTTP status of every refusal comes from `_status_for` alone (09-02-PLAN.md, SEAM-04, D-03;
# Phase 10 D-02). Three caller-facing statuses: 409 when a store is busy (StoreBusyError: another
# process holds it; the input is fine, retry later); 404 for the four lookups of a caller-supplied
# reference that names nothing: a trace reference, a job id, an evidence reference and a generation
# version; 422 for every other refusal ("the request, as given, cannot be satisfied"). Faults stay
# 502/503 (below). A 2xx is never possible, the one
# property T-04-27's mitigation depends on. 404 never discloses whether an internal identity
# (wiring, arm, node) exists: all four lookups are of the caller's own references.
_NOT_FOUND_REFUSALS: tuple[type[SeamRefusalError], ...] = (
    UnknownTraceReferenceError,
    UnknownJobError,
    UnresolvableEvidenceReferenceError,
    UnknownGenerationVersionError,
)


# A ForeignEngineRefusalError is a machine fault, never a caller refusal (09-05-PLAN.md, SEAM-05,
# SEAM-06, D-04): 503 when v1 is unavailable (missing interpreter, timeout, or a v1 configuration
# that lacks a key or names an unsupported backend, Phase 11 D-12); 502 for every other class, i.e.
# an engine run, a store (StoreFault) or the v1 engine failed, stopped early (RunIncomplete) or
# returned malformed output. A consumer is never told to change input that was not at fault.
# EnvironmentDigestUnavailable (Phase 13 D-22): the environment digest could not be computed, so the
# engine cannot stamp a run identity; the engine is unavailable, not the input at fault.
_ENGINE_UNAVAILABLE = frozenset(
    {
        "MissingV1InterpreterError",
        "CorpusOpTimeoutError",
        "DriverUnavailable",
        "V1NotConfigured",
        "EnvironmentDigestUnavailable",
    }
)


def _status_for(exc: SeamRefusalError) -> int:
    if isinstance(exc, StoreBusyError):
        return 409
    if isinstance(exc, ForeignEngineRefusalError):
        return 503 if exc.failure_class in _ENGINE_UNAVAILABLE else 502
    return 404 if isinstance(exc, _NOT_FOUND_REFUSALS) else 422


class RefusalBody(BaseModel):
    """The documented refusal and fault body (``refusal_body``): ``refusal_type`` and ``message``
    plus the refusal's own public attributes (``failure_class`` and ``operation`` for a fault)."""

    model_config = ConfigDict(extra="allow")

    refusal_type: str
    message: str


_FAULT_RESPONSES: dict[int | str, dict[str, Any]] = {
    502: {
        "model": RefusalBody,
        "description": (
            "Machine fault: an engine run, a store or the v1 engine failed, stopped early or returned "
            "malformed output (ForeignEngineRefusalError)"
        ),
    },
    503: {
        "model": RefusalBody,
        "description": "Machine fault: the v1 engine is unavailable (missing interpreter or timeout)",
    },
}


class _RequestModel(BaseModel):
    """The shared strict base for this module's own request DTOs — never the seam's own frozen
    models (``QueryObject``/``Selector``), which stay exactly as 04-01/04-03 declared them. These
    DTOs carry no logic: they exist only so FastAPI has a body shape to deserialize into.

    06-REVIEW.md WR-01: ``frozen=True``, mirroring ``databasise/mcp/tools.py``'s own
    ``_ToolArgs`` base. ``DeleteRequest``'s own module-level default (``DeleteRequest()`` on
    ``delete_document``'s ``body`` parameter) is a single mutable instance constructed once at
    route-registration time and reused as the default for every request that omits a body — the
    mutable-default-argument shape applied to a route handler. No route currently mutates a
    request DTO, so freezing every subclass here is a no-op today; it turns a future read-modify
    write on a shared default into an immediate, loud ``ValidationError`` instead of silently
    corrupting every subsequent no-body request in the same process."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class QueryRequest(_RequestModel):
    query: QueryObject
    selector: Selector | None = None


class CompareRequest(_RequestModel):
    """API-08's comparison request body (06-03-PLAN.md) — the same ``QueryObject`` ``QueryRequest``
    deserializes into, plus a list of ``Selector``s rather than one."""

    query: QueryObject
    selectors: list[Selector]


class TraceRequest(_RequestModel):
    trace_reference: str
    debug: StrictBool = False


class IngestRequest(_RequestModel):
    document: IngestDocument
    selector: Selector | None = None


class DeleteRequest(_RequestModel):
    """06-10-PLAN.md Task 2: an optional body on ``DELETE /documents/{document_id}`` — the
    document id itself stays a path parameter (unchanged), this carries only the §18.4 selector
    naming which fitted modality's index the delete reaches, the same optional member
    ``QueryRequest``/``IngestRequest`` already carry."""

    selector: Selector | None = None


class RetryRequest(_RequestModel):
    """11-08 (D-08): an optional body on ``POST /documents/{document_id}/retry``, carrying only
    the §18.4 selector, as ``DeleteRequest`` does."""

    selector: Selector | None = None


class PromoteRequest(_RequestModel):
    """07-03-PLAN.md Task 1: the operator-asserted promotion request body. Field names match
    ``Databasise.promote()``'s own parameter names exactly, so a reader comparing this body to the
    in-process call sees the identical vocabulary. ``change_origin`` defaults to ``None`` rather
    than being a required JSON key — an absent value still reaches ``Databasise.promote()``, which
    raises the named ``InvalidChangeOriginError`` refusal itself (D-08); this model adds no
    validation of its own beyond deserialization. ``verb`` is typed ``str``, so a non-string verb
    (JSON null, a number, an object) is a request validation error with FastAPI's ``detail``
    shape and no ``refusal_type``; only a string outside the six declared verbs reaches
    ``Databasise.promote()``, which raises the named ``UnrecognisedPromotionVerbError`` refusal
    itself (D-09, 07-04-PLAN.md) with the status ``_status_for`` assigns."""

    alias: str
    trace_ids: list[str]
    change_origin: str | None = None
    verb: str = "operator-asserted"


class RollbackRequest(_RequestModel):
    """07-03-PLAN.md Task 1: ``Databasise.rollback()``'s request body — ``version`` is required
    with no default, mirroring D-05's own rule that rollback names an explicit semver target."""

    alias: str
    version: str
    trace_ids: list[str]
    change_origin: str | None = None


class RetireRequest(_RequestModel):
    """07-03-PLAN.md Task 1: ``Databasise.retire()``'s request body — the identical shape as
    ``RollbackRequest`` (D-07: retire shares rollback's parameter family)."""

    alias: str
    version: str
    trace_ids: list[str]
    change_origin: str | None = None


def _refusal_response(_request: Request, exc: SeamRefusalError) -> JSONResponse:
    """The one application-level exception handler for every ``SeamRefusalError`` subclass
    (T-04-27). The body is built by ``databasise.seam.refusals.refusal_body``: the refusal's own
    named attribute(s), read generically off ``vars(exc)`` rather than a hand-maintained per-type
    mapping, since every refusal already stores its own offending value on a named attribute in
    its constructor (house style, see ``databasise/seam/refusals.py``'s own module docstring).

    **CR-03: a leading-underscore attribute is never exposed.** Every refusal names only the
    consumer's own input, except ``UnbudgetableParticipantError`` (``databasise/seam/tokens.py``),
    which carries the machine's own internal node id on a private ``_internal_node_id`` attribute
    specifically so a generic ``vars(exc)`` dump like this one cannot leak it — the same convention
    any future refusal with an internal-only value should follow.
    """
    return JSONResponse(status_code=_status_for(exc), content=refusal_body(exc))


async def _validation_response(request: Request, exc: RequestValidationError) -> Response:
    """09-01-PLAN.md (SEAM-02, D-01): a refusal raised inside a pydantic validator reaches here
    wrapped in ``RequestValidationError``, with the original exception on ``ctx["error"]``; it is
    unwrapped and answered with the same body ``_refusal_response`` builds. A schema error carrying
    no refusal keeps FastAPI's own JSON-safe ``{detail: [...]}`` shape. ``exc.errors()`` is never
    passed to ``JSONResponse`` directly: ``ctx.error`` is an exception object. Holds no state, so
    concurrent requests cannot see each other's refusal."""
    refusal = refusal_from_errors(exc.errors())
    if refusal is None:
        return await request_validation_exception_handler(request, exc)
    return _refusal_response(request, refusal)


def _pydantic_validation_response(request: Request, exc: ValidationError) -> JSONResponse:
    """09-02-PLAN.md (SEAM-02, SEAM-07): a ``pydantic.ValidationError`` raised inside a route body
    (``IngestDocument(raw=...)`` on the upload route) carries the real refusal on ``ctx["error"]``;
    it is answered with the same body ``_refusal_response`` builds. One with no refusal inside is a
    server bug and is re-raised, so it stays a visible 500."""
    refusal = refusal_from_errors(exc.errors())
    if refusal is None:
        raise exc
    return _refusal_response(request, refusal)


def _selector_field(raw: str | None) -> Selector | None:
    """The one parse of a selector carried as a JSON string (the upload form field and, since 12-09
    D-13, the ``/corpus`` query parameter): omitted, blank or ``null`` means no selector; valid JSON
    that breaks a selector rule returns that rule's own refusal, and anything else is
    ``MalformedSelectorPayloadError`` (422), never a 500."""
    if raw is None or raw.strip() in ("", "null"):
        return None
    try:
        return Selector.model_validate_json(raw)
    except ValidationError as exc:
        raise (refusal_from_errors(exc.errors()) or MalformedSelectorPayloadError(field="selector")) from exc


class InvalidCorsOriginError(ValueError):
    """A CORS origin that is not an exact ``scheme://host[:port]`` value (D-12)."""

    def __init__(self, origin: str) -> None:
        self.origin = origin
        super().__init__(
            f"invalid CORS origin {origin!r}: origins must be exact scheme://host[:port] values "
            "with no path, trailing slash, query or wildcard (D-12)"
        )


def validate_cors_origin(origin: str) -> str:
    """Returns ``origin`` unchanged when it is an exact ``http(s)://host[:port]`` origin, else raises
    :class:`InvalidCorsOriginError`. No normalisation: the browser's ``Origin`` header is matched
    byte for byte, so a trailing slash or a wildcard could never match and is refused instead."""
    if not re.fullmatch(r"https?://[^/\s*?#]+", origin):
        raise InvalidCorsOriginError(origin)
    return origin


def create_app(
    *,
    store_root: str | Path,
    workspace: str,
    registry: PartRegistry | None = None,
    clients: dict[str, Any] | None = None,
    cors_origins: Sequence[str] = (),
    operator: bool = False,
) -> FastAPI:
    """The application factory (D-17): builds one ``Databasise`` instance — the same object an
    in-process caller would construct against the same ``store_root``/``workspace`` — and wires
    every endpoint as a thin adapter over it. A test builds an app against a ``tmp_path`` store
    root and stub ``clients`` exactly as an in-process test would.

    ``operator=True`` additionally mounts the operator read routes from
    ``databasise.seam.operator_rest``; without it none of them exists (16-01, D-01).
    """
    engine = Databasise(store_root=store_root, workspace=workspace, registry=registry, clients=clients)
    app = FastAPI(title="databasise", version=__version__)
    app.state.engine = engine
    app.add_exception_handler(SeamRefusalError, _refusal_response)
    app.add_exception_handler(RequestValidationError, _validation_response)
    app.add_exception_handler(ValidationError, _pydantic_validation_response)
    if cors_origins:
        origins = list(dict.fromkeys(validate_cors_origin(origin) for origin in cors_origins))
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Content-Type"],
        )

    @app.post("/query")
    async def post_query(body: QueryRequest) -> ResponseEnvelope:
        return await engine.query(body.query, body.selector)

    @app.post(
        "/compare",
        description=(
            "One selector returns a single envelope; two or more return a map keyed by each selector's "
            "rendered value (alias or harness string, capabilities joined with '+', or 'default'). A "
            "consumer tells them apart by the number of selectors it sent, never by inspecting keys, so "
            "a key named 'answer' cannot make a map look like an envelope. Keys are not prefixed. A key "
            "collision is refused before any arm runs."
        ),
    )
    async def post_compare(body: CompareRequest) -> Any:
        return await engine.compare(body.query, body.selectors)

    async def _resolve_streamed_envelope(body: QueryRequest) -> ResponseEnvelope:
        """CR-01: resolves the envelope eagerly, as a FastAPI dependency, so a
        ``SeamRefusalError`` is raised and caught *before* ``post_query_stream``'s own
        async-generator body starts running. ``post_query_stream`` is itself an async generator
        function (required for FastAPI's SSE detection to route it through
        ``EventSourceResponse``'s producer machinery) — the generator's body does not execute
        until the SSE producer starts consuming it, by which point the response has already begun
        and this module's app-level ``SeamRefusalError`` handler can no longer intercept anything
        raised inside it (see this module's own reproduction in 04-REVIEW.md CR-01). A FastAPI
        dependency, by contrast, is awaited synchronously during request dispatch, before the
        SSE branch runs at all — so a refusal raised here propagates through the same
        ``add_exception_handler(SeamRefusalError, ...)`` path every non-streaming endpoint uses.
        Calls the identical ``Databasise.query()`` an in-process caller awaits — never a private
        method, and never a second execution path from ``query_stream``'s own.
        """
        return await engine.query(body.query, body.selector)

    @app.post("/query/stream", response_class=EventSourceResponse)
    async def post_query_stream(
        envelope: ResponseEnvelope = Depends(_resolve_streamed_envelope),
    ):
        """Shapes the eagerly-resolved ``envelope`` with ``databasise.seam.engine``'s own
        ``stream_envelope_events`` -- the identical function ``Databasise.query_stream()`` shapes
        its own events with (see ``engine.py``'s module docstring, "CR-01 gap closure"). This
        endpoint never re-implements the shaping itself: resolution happens eagerly above (via
        ``_resolve_streamed_envelope``, so a refusal maps to the status ``_status_for`` assigns before the first
        SSE byte is written), and shaping is the one function both transports iterate.
        """
        for event in stream_envelope_events(envelope):
            yield event

    @app.post("/evidence/resolve")
    async def post_resolve_evidence(ref: EvidenceRef) -> dict[str, Any]:
        return await engine.resolve_evidence(ref)

    @app.post("/trace/resolve")
    async def post_resolve_trace(body: TraceRequest) -> dict[str, Any]:
        return await engine.resolve_trace(body.trace_reference, debug=body.debug)

    @app.post("/documents", responses=_FAULT_RESPONSES)
    async def post_documents(body: IngestRequest) -> IngestJob:
        return await engine.ingest(body.document, body.selector)

    @app.post("/documents/upload", responses=_FAULT_RESPONSES)
    async def post_documents_upload(
        file: UploadFile,
        document_id: str | None = Form(default=None),
        selector: str | None = Form(default=None),
    ) -> IngestJob:
        """The one route in this module with more than one statement (05-04-PLAN.md Task 2): it
        must read the uploaded file's bytes before an ``IngestDocument`` can be built — still no
        redaction and no envelope assembly, so ``test_rest_transport.py``'s AST proof keeps
        passing. The byte-size cap is enforced by ``IngestDocument``'s own validator refusing an
        oversized ``raw`` payload, never by a size branch written here.

        06-10-PLAN.md Task 2: ``selector`` arrives as a JSON-encoded form field (multipart form
        data has no native nested-object type, mirroring ``IngestToolArgs``'s own base64-for-bytes
        convention for the identical "no native shape" problem) — parsed via ``Selector``'s own
        ``model_validate_json``, never a hand-rolled parse.

        A blank ``document_id`` form field (exactly ``''``) means absent and the server mints the id
        (D-12), for the same reason as a blank selector field; any non-empty id goes through the
        token check and a malformed one is refused as ``InvalidDocumentIdError``.

        **Selector field rules (09-02-PLAN.md, SEAM-13, SEAM-02).** An omitted, empty,
        whitespace-only or ``null`` field means no selector, the same as ``selector: null`` on the
        JSON routes. Valid JSON that breaks a selector rule returns that rule's own refusal
        (``ForbiddenSelectorInputError`` for a hash-shaped alias, and so on), unwrapped from the
        ``ValidationError`` with ``refusal_from_errors``. ``MalformedSelectorPayloadError`` is only
        for unparseable JSON or a schema error that carries no refusal (``{"alias": 5}``); ``NULL``
        is not the JSON literal and is malformed. The parse is a pure function of the field, so
        concurrent uploads cannot see each other's selector.

        The selector parse happens in the route body, never inside a pydantic validator, so its
        ``ValidationError`` is translated here (mirroring ``MalformedBase64PayloadError``'s house
        pattern). The ``IngestDocument(...)`` construction is left unwrapped: its refusals (oversize,
        ambiguity) reach the client through the app-level ``pydantic.ValidationError`` handler.
        """
        raw = await file.read()
        document = IngestDocument(
            raw=raw,
            document_id=document_id or None,
            file_name=file.filename,
            content_type=file.content_type,
        )
        return await engine.ingest(document, _selector_field(selector))

    @app.get("/jobs/{job_id}", responses=_FAULT_RESPONSES)
    async def get_job_status(
        job_id: str,
        limit: int = Query(default=50),
        offset: int = Query(default=0),
    ) -> JobStatus:
        return await engine.get_job_status(job_id, checked_page(limit, offset))

    @app.delete("/documents/{document_id}", responses=_FAULT_RESPONSES)
    async def delete_document(document_id: str, body: DeleteRequest = DeleteRequest()) -> DeletionOutcome:
        """06-10-PLAN.md Task 2: ``body`` defaults to an empty ``DeleteRequest`` (``selector=None``)
        so a caller sending no body at all — every existing REST delete call — keeps working
        byte-for-byte; a caller sending ``{"selector": ...}`` names which fitted modality's index
        the delete reaches. A malformed ``document_id`` is refused as ``InvalidDocumentIdError``
        (422) before any wiring runs."""
        return await engine.delete_document(document_id, body.selector)

    @app.post("/documents/{document_id}/retry", responses=_FAULT_RESPONSES)
    async def retry_document(document_id: str, body: RetryRequest = RetryRequest()) -> IngestJob:
        """11-08 (D-08, LRAG-07): reprocess one interrupted document. A document that is not
        interrupted is ``DocumentNotInterruptedError`` (422), an id v1 does not hold is
        ``UnknownDocumentError`` (422), and a write in flight is ``StoreBusyError`` (409)."""
        return await engine.retry_document(document_id, body.selector)

    @app.get("/health")
    async def get_health() -> HealthReport:
        return await engine.health()

    @app.get("/corpus", responses=_FAULT_RESPONSES)
    async def get_corpus(
        limit: int = Query(default=50),
        offset: int = Query(default=0),
        selector: str | None = Query(default=None),
    ) -> CorpusStatus:
        """12-09 (D-13): ``selector`` is a JSON-encoded selector naming which modality's documents
        to list; absent, the listing is the LightRAG corpus exactly as before."""
        return await engine.corpus_status(checked_page(limit, offset), _selector_field(selector))

    @app.get("/corpus/counts", responses=_FAULT_RESPONSES)
    async def get_corpus_counts(selector: str | None = Query(default=None)) -> DocumentCounts:
        return await engine.document_counts(_selector_field(selector))

    @app.post("/promote")
    async def post_promote(body: PromoteRequest) -> PromotionResult:
        return await engine.promote(body.alias, body.trace_ids, body.change_origin, verb=body.verb)

    @app.post("/rollback")
    async def post_rollback(body: RollbackRequest) -> PromotionResult:
        return await engine.rollback(body.alias, body.version, body.trace_ids, body.change_origin)

    @app.post("/retire")
    async def post_retire(body: RetireRequest) -> PromotionResult:
        return await engine.retire(body.alias, body.version, body.trace_ids, body.change_origin)

    if operator:
        # Lazy: the default app object and its OpenAPI stay exactly as they were (D-01).
        from databasise.seam.operator_rest import add_operator_routes

        add_operator_routes(app, engine)

    return app


__all__ = [
    "QueryRequest",
    "CompareRequest",
    "TraceRequest",
    "IngestRequest",
    "DeleteRequest",
    "RetryRequest",
    "PromoteRequest",
    "RollbackRequest",
    "RetireRequest",
    "InvalidCorsOriginError",
    "create_app",
    "validate_cors_origin",
]
