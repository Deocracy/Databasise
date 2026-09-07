"""``databasise.seam.rest`` — the optional REST transport (D-15/D-16/D-17, EMBED-02, API-04,
ROADMAP criterion 5). Never imported at module scope by ``databasise/__init__.py`` or
``databasise/seam/__init__.py`` — only a consumer who has installed the ``rest`` extra, and who
explicitly imports this module, pays the FastAPI-absent cost (Pattern 3, 04-RESEARCH.md).

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
    from fastapi import FastAPI
    from fastapi.requests import Request
    from fastapi.responses import JSONResponse
    from fastapi.sse import EventSourceResponse
except ImportError as exc:  # pragma: no cover - exercised only without the `rest` extra installed
    raise ImportError(
        "databasise.seam.rest requires the optional REST transport dependencies. "
        "Install with: pip install 'databasise[rest]' (or `uv sync --extra rest`)."
    ) from exc

from pydantic import BaseModel, ConfigDict

from databasise.parts.registry import PartRegistry
from databasise.seam.engine import Databasise
from databasise.seam.envelope import ResponseEnvelope
from databasise.seam.evidence import EvidenceRef
from databasise.seam.query import QueryObject
from databasise.seam.refusals import SeamRefusalError
from databasise.seam.selectors import Selector

# Non-success, never a 2xx — the one property T-04-27's mitigation depends on. 422 (Unprocessable
# Content) is used uniformly for every refusal kind: the four §18.4/§18.1 refusal families below
# are all "the request, as given, cannot be satisfied," never a malformed-request 400 or a
# machine-fault 500.
_REFUSAL_STATUS_CODE = 422


class _RequestModel(BaseModel):
    """The shared strict base for this module's own request DTOs — never the seam's own frozen
    models (``QueryObject``/``Selector``), which stay exactly as 04-01/04-03 declared them. These
    DTOs carry no logic: they exist only so FastAPI has a body shape to deserialize into."""

    model_config = ConfigDict(extra="forbid")


class QueryRequest(_RequestModel):
    query: QueryObject
    selector: Selector | None = None


class TraceRequest(_RequestModel):
    trace_reference: str
    debug: bool = False


def _refusal_response(_request: Request, exc: SeamRefusalError) -> JSONResponse:
    """The one application-level exception handler for every ``SeamRefusalError`` subclass
    (T-04-27). Carries the refusal's own named attribute(s) — read generically off ``vars(exc)``
    rather than a hand-maintained per-type mapping, since every refusal in
    ``databasise.seam.refusals``/``evidence``/``tokens``/``trace_store`` already stores its own
    offending value on a named attribute in its constructor (house style, see
    ``databasise/seam/refusals.py``'s own module docstring)."""
    detail: dict[str, Any] = {"refusal_type": type(exc).__name__, "message": str(exc)}
    for key, value in vars(exc).items():
        if isinstance(value, BaseModel):
            value = value.model_dump()
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

    @app.post("/query/stream", response_class=EventSourceResponse)
    async def post_query_stream(body: QueryRequest):
        async for event in engine.query_stream(body.query, body.selector):
            yield event

    @app.post("/evidence/resolve")
    async def post_resolve_evidence(ref: EvidenceRef) -> dict[str, Any]:
        return await engine.resolve_evidence(ref)

    @app.post("/trace/resolve")
    async def post_resolve_trace(body: TraceRequest) -> dict[str, Any]:
        return await engine.resolve_trace(body.trace_reference, debug=body.debug)

    return app


__all__ = ["create_app", "QueryRequest", "TraceRequest"]
