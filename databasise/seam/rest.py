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
``EmptyComparisonRequestError``/``UnsatisfiableSelectorError`` to the documented 422 with no
per-route handling — see ``databasise/tests/seam/test_rest_transport.py``'s own
``_REFUSAL_FACTORIES``.

**Thin adapter, provably (D-17).** Every endpoint body below is exactly: deserialize the request
into the same ``QueryObject``/``Selector``/``EvidenceRef`` shapes an in-process caller constructs,
await the identical ``Databasise`` method an in-process caller awaits, and return the result for
FastAPI to serialize. No selector resolution, no redaction and no envelope assembly happens in
this module — those live in ``databasise.seam.engine``/``selectors``/``envelope``/``redact``, and
``databasise/tests/seam/test_rest_transport.py`` proves the absence by walking this module's own
AST rather than by convention. One application-level exception handler maps every
``SeamRefusalError`` subclass to a non-success response, enumerated at runtime from
``SeamRefusalError.__subclasses__()`` (transitively, via every seam module this app already
imports) rather than a hand-maintained list, so a refusal type added later cannot silently fall
through to a generic 500 (T-04-27).

**Exposure note (T-04-25 Spoofing, T-04-26 Denial of Service; disposition: transfer,
04-05-PLAN.md's threat register).** This app ships with no authentication, no authorization, no
TLS termination, and no rate limiting. No requirement in this phase's set (API-03, API-04, API-05,
API-10, API-11, EMBED-02, MACH-11) asks for any of them, and a partial auth story would be worse
than none — a consumer who trusted a half-built auth check would be worse off than one who knew
there was none. This is an optional, locally-bound embedded surface: binding, TLS termination,
connection-count/timeout/body-size limits and access control are the operator's own boundary, not
this module's. FastAPI's native ``EventSourceResponse`` (see the streaming endpoint below) handles
SSE keep-alive and buffering headers; it does not handle any of the above.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from fastapi import Depends, FastAPI, Form, Query, UploadFile
    from fastapi.requests import Request
    from fastapi.responses import JSONResponse
    from fastapi.sse import EventSourceResponse
except ImportError as exc:  # pragma: no cover - exercised only without the `rest` extra installed
    raise ImportError(
        "databasise.seam.rest requires the optional REST transport dependencies. "
        "Install with: pip install 'databasise[rest]' (or `uv sync --extra rest`)."
    ) from exc

from pydantic import BaseModel, ConfigDict, ValidationError

from databasise.parts.registry import PartRegistry
from databasise.seam.corpus import (
    MAX_PAGE_SIZE,
    CorpusStatus,
    DeletionOutcome,
    DocumentCounts,
    HealthReport,
    IngestDocument,
    IngestJob,
    JobStatus,
    Page,
)
from databasise.seam.engine import Databasise, stream_envelope_events
from databasise.seam.envelope import PromotionResult, ResponseEnvelope
from databasise.seam.evidence import EvidenceRef
from databasise.seam.query import QueryObject
from databasise.seam.refusals import (
    MalformedSelectorPayloadError,
    PageSizeExceededError,
    SeamRefusalError,
)
from databasise.seam.selectors import Selector

# Non-success, never a 2xx — the one property T-04-27's mitigation depends on. 422 (Unprocessable
# Content) is used uniformly for every refusal kind: the four §18.4/§18.1 refusal families below
# are all "the request, as given, cannot be satisfied," never a malformed-request 400 or a
# machine-fault 500.
_REFUSAL_STATUS_CODE = 422


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
    debug: bool = False


class IngestRequest(_RequestModel):
    document: IngestDocument
    selector: Selector | None = None


class DeleteRequest(_RequestModel):
    """06-10-PLAN.md Task 2: an optional body on ``DELETE /documents/{document_id}`` — the
    document id itself stays a path parameter (unchanged), this carries only the §18.4 selector
    naming which fitted modality's index the delete reaches, the same optional member
    ``QueryRequest``/``IngestRequest`` already carry."""

    selector: Selector | None = None


class PromoteRequest(_RequestModel):
    """07-03-PLAN.md Task 1: the operator-asserted promotion request body. Field names match
    ``Databasise.promote()``'s own parameter names exactly, so a reader comparing this body to the
    in-process call sees the identical vocabulary. ``change_origin`` defaults to ``None`` rather
    than being a required JSON key — an absent value still reaches ``Databasise.promote()``, which
    raises the named ``InvalidChangeOriginError`` refusal itself (D-08); this model adds no
    validation of its own beyond deserialization. ``verb`` stays a plain ``str`` here by the
    identical rule stated above for ``change_origin`` (07-04-PLAN.md): an out-of-enum value is
    allowed to reach ``Databasise.promote()``, which raises the named
    ``UnrecognisedPromotionVerbError`` refusal itself (D-09) — so this endpoint's out-of-enum
    response is the same 422 carrying the same ``refusal_type`` as every other seam refusal,
    rather than a request-validation body that carries no refusal name."""

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


def _checked_page(limit: int, offset: int) -> Page:
    """[Rule 1 - Bug] Refuses ``limit`` above ``MAX_PAGE_SIZE`` by raising
    ``PageSizeExceededError`` directly, never by letting ``Page(limit=limit, offset=offset)``
    raise it — ``Page``'s own ``model_validator`` (05-04-PLAN.md Task 1) is designed for an
    in-process caller, and pydantic wraps a validator-raised exception into a
    ``pydantic.ValidationError`` at the construction call site (the same behaviour
    ``AmbiguousIngestPayloadError``'s own module docstring documents for ``IngestDocument``). A
    ``Page`` built by hand inside a route body, from raw query parameters FastAPI has already
    finished parsing, is *not* the same code path FastAPI's own request-body parsing uses — the
    wrapped ``ValidationError`` would propagate as an unmatched exception (Starlette's exception
    middleware matches by ``type(exc).__mro__`` against the registered ``SeamRefusalError``
    handler, and ``pydantic.ValidationError`` is not in that hierarchy), producing an unhandled
    500 instead of the documented 422. Raising the refusal here, before ``Page`` is ever
    constructed, keeps the 422/``requested``/``limit`` contract every other refusal in this module
    already has via ``_refusal_response``'s generic ``vars(exc)`` dump.
    """
    if limit > MAX_PAGE_SIZE:
        raise PageSizeExceededError(requested=limit, limit=MAX_PAGE_SIZE)
    return Page(limit=limit, offset=offset)


def _refusal_response(_request: Request, exc: SeamRefusalError) -> JSONResponse:
    """The one application-level exception handler for every ``SeamRefusalError`` subclass
    (T-04-27). Carries the refusal's own named attribute(s) — read generically off ``vars(exc)``
    rather than a hand-maintained per-type mapping, since every refusal in
    ``databasise.seam.refusals``/``evidence``/``tokens``/``trace_store`` already stores its own
    offending value on a named attribute in its constructor (house style, see
    ``databasise/seam/refusals.py``'s own module docstring).

    **CR-03: a leading-underscore attribute is never exposed.** Every refusal names only the
    consumer's own input, except ``UnbudgetableParticipantError`` (``databasise/seam/tokens.py``),
    which carries the machine's own internal node id on a private ``_internal_node_id`` attribute
    specifically so a generic ``vars(exc)`` dump like this one cannot leak it — the same convention
    any future refusal with an internal-only value should follow.
    """
    detail: dict[str, Any] = {"refusal_type": type(exc).__name__, "message": str(exc)}
    for key, value in vars(exc).items():
        if key.startswith("_"):
            continue
        if isinstance(value, BaseModel):
            value = value.model_dump()
        # 05-01-PLAN.md: ForeignEngineRefusalError's own `cause` attribute carries a raw
        # exception object (a foreign-engine subprocess failure) — not JSON-serializable as-is;
        # stringified here exactly like every other refusal's own message, never dropped.
        elif isinstance(value, BaseException):
            value = str(value)
        detail[key] = value
    return JSONResponse(status_code=_REFUSAL_STATUS_CODE, content=detail)


def create_app(
    *,
    store_root: str | Path,
    workspace: str,
    registry: PartRegistry | None = None,
    clients: dict[str, Any] | None = None,
) -> FastAPI:
    """The application factory (D-17): builds one ``Databasise`` instance — the same object an
    in-process caller would construct against the same ``store_root``/``workspace`` — and wires
    every endpoint as a thin adapter over it. A test builds an app against a ``tmp_path`` store
    root and stub ``clients`` exactly as an in-process test would.
    """
    engine = Databasise(store_root=store_root, workspace=workspace, registry=registry, clients=clients)
    app = FastAPI(title="databasise", version="0.1.0")
    app.state.engine = engine
    app.add_exception_handler(SeamRefusalError, _refusal_response)

    @app.post("/query")
    async def post_query(body: QueryRequest) -> ResponseEnvelope:
        return await engine.query(body.query, body.selector)

    @app.post("/compare")
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
        ``_resolve_streamed_envelope``, so a refusal maps to the documented 422 before the first
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

    @app.post("/documents")
    async def post_documents(body: IngestRequest) -> IngestJob:
        return await engine.ingest(body.document, body.selector)

    @app.post("/documents/upload")
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

        CR-02 gap closure: this parse happens directly in the route body, never inside a pydantic
        validator, so a raw ``pydantic.ValidationError`` on malformed input is not itself a
        ``SeamRefusalError`` the registered handler can map — it must be caught and translated
        here, mirroring ``MalformedBase64PayloadError``'s own house pattern for exactly this
        "manually parsed field" situation.
        """
        raw = await file.read()
        document = IngestDocument(
            raw=raw,
            document_id=document_id,
            file_name=file.filename,
            content_type=file.content_type,
        )
        try:
            parsed_selector = Selector.model_validate_json(selector) if selector else None
        except ValidationError as exc:
            raise MalformedSelectorPayloadError(field="selector") from exc
        return await engine.ingest(document, parsed_selector)

    @app.get("/jobs/{job_id}")
    async def get_job_status(
        job_id: str,
        limit: int = Query(default=50),
        offset: int = Query(default=0, ge=0),
    ) -> JobStatus:
        return await engine.get_job_status(job_id, _checked_page(limit, offset))

    @app.delete("/documents/{document_id}")
    async def delete_document(document_id: str, body: DeleteRequest = DeleteRequest()) -> DeletionOutcome:
        """06-10-PLAN.md Task 2: ``body`` defaults to an empty ``DeleteRequest`` (``selector=None``)
        so a caller sending no body at all — every existing REST delete call — keeps working
        byte-for-byte; a caller sending ``{"selector": ...}`` names which fitted modality's index
        the delete reaches."""
        return await engine.delete_document(document_id, body.selector)

    @app.get("/health")
    async def get_health() -> HealthReport:
        return await engine.health()

    @app.get("/corpus")
    async def get_corpus(
        limit: int = Query(default=50),
        offset: int = Query(default=0, ge=0),
    ) -> CorpusStatus:
        return await engine.corpus_status(_checked_page(limit, offset))

    @app.get("/corpus/counts")
    async def get_corpus_counts() -> DocumentCounts:
        return await engine.document_counts()

    @app.post("/promote")
    async def post_promote(body: PromoteRequest) -> PromotionResult:
        return await engine.promote(body.alias, body.trace_ids, body.change_origin, verb=body.verb)

    @app.post("/rollback")
    async def post_rollback(body: RollbackRequest) -> PromotionResult:
        return await engine.rollback(body.alias, body.version, body.trace_ids, body.change_origin)

    @app.post("/retire")
    async def post_retire(body: RetireRequest) -> PromotionResult:
        return await engine.retire(body.alias, body.version, body.trace_ids, body.change_origin)

    return app


__all__ = [
    "QueryRequest",
    "CompareRequest",
    "TraceRequest",
    "IngestRequest",
    "DeleteRequest",
    "PromoteRequest",
    "RollbackRequest",
    "RetireRequest",
    "create_app",
]
