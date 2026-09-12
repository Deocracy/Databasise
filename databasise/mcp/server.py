"""``databasise.mcp.server`` — the MCP server factory (05-07-PLAN.md Task 1, action A/E). Copies
``databasise.seam.rest``'s "thin adapter, provably" architecture to a second protocol: one
``Databasise`` instance, nine tool bodies that are each exactly deserialize-then-await-then-return,
and one shared refusal-to-tool-error mapper instead of one shared app-level exception handler.

**Resolved server API (`mcp` 2.2.0, read from the installed package this session — action A).**
`mcp`'s major version is 2.x, matching this plan's own precondition; ``FastMCP`` (the class name
every pre-2.x tutorial and most cached training knowledge names) was renamed to ``MCPServer`` in
this major version — ``from mcp.server.mcpserver import MCPServer`` is the resolved import path
(``mcp.server.fastmcp`` itself raises ``ModuleNotFoundError`` with a migration-guide pointer,
confirmed live this session against the installed package, not assumed from memory).
``MCPServer(name)`` constructs a server; the ``server.tool`` decorator, given a ``name=`` keyword,
registers an async (or sync) callable as a tool, inferring its input schema from the callable's own
type-annotated parameter —
a single Pydantic model parameter becomes the tool's one argument, exactly the shape
``IngestToolArgs``/``QueryToolArgs``/etc. in ``databasise.mcp.tools`` are built for.
``await server.list_tools()`` and ``await server.call_tool(name, arguments)`` are both async and
both confirmed live this session (``server.call_tool`` re-raises a tool's own ``ToolError``
directly rather than ever swallowing it into a ``CallToolResult`` — that wrapping into
``is_error=True`` happens one layer up, inside the wire-protocol handler this factory never calls
directly).

**The refusal mapper (action E).** Every tool body below is wrapped with :func:`_refusal_mapped`,
which catches ``SeamRefusalError`` — the single base class, not an enumerated subclass list, the
same generic catch ``databasise.seam.rest``'s single ``app.add_exception_handler(SeamRefusalError,
...)`` registration relies on — and re-raises it as a ``ToolError`` whose message is the JSON-
encoded refusal detail :func:`_refusal_detail` builds the same generic way ``rest.py``'s own
``_refusal_response`` does: every public (non-underscore-prefixed) attribute off ``vars(exc)``,
mirroring CR-03's private-attribute exclusion (``UnbudgetableParticipantError``'s own
``_internal_node_id`` is exactly why that rule exists).

**Status/resolve dispatch (action E).** ``status``'s four scopes and ``resolve``'s two scopes each
dispatch through an explicit ``dict[str, Callable]`` keyed by the scope literal — a mapping from a
literal to a bound method, never an ``if``/``elif`` chain routing on ``args.scope`` — so the
growth-invariant test's AST proof stays clean (no selector-resolution-shaped branching to mistake
for one).

**No FastAPI, ever.** This module imports nothing from ``fastapi`` — the MCP transport must not
require the ``rest`` extra (05-07-PLAN.md Task 1's own acceptance criterion).
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar

from databasise.mcp._sdk import import_sdk
from databasise.mcp.tools import (
    CompareToolArgs,
    DeleteToolArgs,
    IngestToolArgs,
    PromoteToolArgs,
    QueryToolArgs,
    ResolveToolArgs,
    RetireToolArgs,
    RollbackToolArgs,
    StatusToolArgs,
)
from databasise.parts.registry import PartRegistry
from databasise.seam.corpus import MAX_PAGE_SIZE, Page
from databasise.seam.engine import Databasise
from databasise.seam.refusals import PageSizeExceededError, SeamRefusalError

# Resolved through _sdk.import_sdk (module docstring) — never a bare `from mcp... import ...`,
# which reproduces a CWD-shadow circular import under `cd databasise && python -c ...` (the exact
# shape several of this plan's own acceptance criteria run).
MCPServer = import_sdk("mcp.server.mcpserver").MCPServer
ToolError = import_sdk("mcp.server.mcpserver.exceptions").ToolError

_ServerName = "databasise"

_T = TypeVar("_T")
_AsyncToolFn = Callable[[_T], Awaitable[dict[str, Any]]]


def _refusal_detail(exc: SeamRefusalError) -> dict[str, Any]:
    """Mirrors ``databasise.seam.rest._refusal_response``'s own generic ``vars(exc)`` dump — the
    refusal's own type name, message, and every public attribute; a leading-underscore attribute
    (CR-03) is skipped, never exposed."""
    detail: dict[str, Any] = {"refusal_type": type(exc).__name__, "message": str(exc)}
    for key, value in vars(exc).items():
        if key.startswith("_"):
            continue
        if hasattr(value, "model_dump"):
            value = value.model_dump()
        elif isinstance(value, BaseException):
            value = str(value)
        detail[key] = value
    return detail


def _refusal_mapped(fn: _AsyncToolFn) -> _AsyncToolFn:
    """The one shared mapper every tool body below is wrapped in (action E) — a
    ``SeamRefusalError`` raised anywhere inside ``fn`` surfaces as a ``ToolError`` carrying the
    refusal's own type name and public attributes as its JSON-encoded message, never as a
    successful result and never as an unnamed crash."""

    @wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return await fn(*args, **kwargs)
        except SeamRefusalError as exc:
            raise ToolError(json.dumps(_refusal_detail(exc))) from exc

    return wrapper


def _checked_page(limit: int, offset: int) -> Page:
    """Refuses ``limit`` above ``MAX_PAGE_SIZE`` by raising ``PageSizeExceededError`` directly,
    never by letting ``Page``'s own constructor and its ``model_validator`` raise it —
    see ``databasise.seam.rest._checked_page``'s own docstring for the exact pydantic-wrapping
    mechanism this mirrors (a validator-raised refusal is wrapped into a ``pydantic.ValidationError``
    at the construction call site, losing the original exception object). This transport needs its
    own copy rather than importing REST's: ``databasise/mcp/`` must not import ``fastapi``, and
    ``rest.py`` is guarded behind the ``rest`` extra, so importing from it would couple the MCP
    transport to the web stack, which 05-07-PLAN.md's own acceptance criterion forbids.
    """
    if limit > MAX_PAGE_SIZE:
        raise PageSizeExceededError(requested=limit, limit=MAX_PAGE_SIZE)
    return Page(limit=limit, offset=offset)


async def _status_job(engine: Databasise, args: StatusToolArgs) -> Any:
    if args.job_id is None:
        raise ToolError("status tool: scope 'job' requires a job_id")
    return await engine.get_job_status(args.job_id, _checked_page(args.limit, args.offset))


async def _status_corpus(engine: Databasise, args: StatusToolArgs) -> Any:
    return await engine.corpus_status(_checked_page(args.limit, args.offset))


async def _status_counts(engine: Databasise, args: StatusToolArgs) -> Any:
    del args
    return await engine.document_counts()


async def _status_health(engine: Databasise, args: StatusToolArgs) -> Any:
    del args
    return await engine.health()


# An explicit mapping from the scope literal to its handler — never branching logic (module
# docstring's "status/resolve dispatch" note). `counts`/`health` read no page and take no
# limit/offset (the REST routes for those two operations accept no limit parameter at all), so
# they are left unchecked here deliberately — adding a page check to them would create a
# divergence from REST rather than close one.
_STATUS_HANDLERS: dict[str, Callable[[Databasise, StatusToolArgs], Awaitable[Any]]] = {
    "job": _status_job,
    "corpus": _status_corpus,
    "counts": _status_counts,
    "health": _status_health,
}


async def _resolve_evidence_scope(engine: Databasise, args: ResolveToolArgs) -> dict[str, Any]:
    if args.evidence_ref is None:
        raise ToolError("resolve tool: scope 'evidence' requires an evidence_ref")
    return await engine.resolve_evidence(args.evidence_ref)


async def _resolve_trace_scope(engine: Databasise, args: ResolveToolArgs) -> dict[str, Any]:
    if args.trace_reference is None:
        raise ToolError("resolve tool: scope 'trace' requires a trace_reference")
    return await engine.resolve_trace(args.trace_reference, debug=args.debug)


_RESOLVE_HANDLERS: dict[str, Callable[[Databasise, ResolveToolArgs], Awaitable[dict[str, Any]]]] = {
    "evidence": _resolve_evidence_scope,
    "trace": _resolve_trace_scope,
}


def create_server(
    *,
    store_root: str | Path,
    workspace: str,
    registry: PartRegistry | None = None,
    clients: dict[str, Any] | None = None,
) -> MCPServer:
    """Builds one ``Databasise`` instance — the same object an in-process caller or the REST
    ``create_app`` would construct against the same ``store_root``/``workspace`` — and registers
    the five tools as thin adapters over it. ``server.engine`` holds the constructed instance
    directly (mirrors ``databasise.seam.rest``'s own ``app.state.engine``), reachable for a test's
    own identity assertion.
    """
    engine = Databasise(store_root=store_root, workspace=workspace, registry=registry, clients=clients)
    server = MCPServer(_ServerName)
    server.engine = engine

    @server.tool(name="ingest")
    @_refusal_mapped
    async def ingest_tool(args: IngestToolArgs) -> dict[str, Any]:
        job = await engine.ingest(args.to_ingest_document(), args.selector)
        return job.model_dump()

    @server.tool(name="query")
    @_refusal_mapped
    async def query_tool(args: QueryToolArgs) -> dict[str, Any]:
        envelope = await engine.query(args.query, args.selector)
        return envelope.model_dump()

    @server.tool(name="compare")
    @_refusal_mapped
    async def compare_tool(args: CompareToolArgs) -> dict[str, Any]:
        """API-08's comparison operation (06-03-PLAN.md) — a legitimate sixth tool under §18.5:
        comparison is not expressible as a §18.4 selector (a selector picks one arm; this call
        fans out over N of them in one request), and the roster grows by one for this one
        genuinely new operation, not by one name per modality — registering HippoRAG as a second
        modality added zero tools (see ``databasise.mcp.tools``'s own module docstring)."""
        result = await engine.compare(args.query, args.selectors)
        if isinstance(result, dict):
            return {key: envelope.model_dump() for key, envelope in result.items()}
        return result.model_dump()

    @server.tool(name="delete")
    @_refusal_mapped
    async def delete_tool(args: DeleteToolArgs) -> dict[str, Any]:
        outcome = await engine.delete_document(args.document_id, args.selector)
        return outcome.model_dump()

    @server.tool(name="status")
    @_refusal_mapped
    async def status_tool(args: StatusToolArgs) -> dict[str, Any]:
        handler = _STATUS_HANDLERS[args.scope]
        result = await handler(engine, args)
        return result.model_dump()

    @server.tool(name="resolve")
    @_refusal_mapped
    async def resolve_tool(args: ResolveToolArgs) -> dict[str, Any]:
        handler = _RESOLVE_HANDLERS[args.scope]
        result = await handler(engine, args)
        return result

    @server.tool(name="promote")
    @_refusal_mapped
    async def promote_tool(args: PromoteToolArgs) -> dict[str, Any]:
        """07-03-PLAN.md: reaches the identical ``Databasise.promote()`` REST's ``POST /promote``
        reaches — no per-tool try/except, ``_refusal_mapped`` already catches every Phase 7
        refusal generically via the ``SeamRefusalError`` base class."""
        outcome = await engine.promote(args.alias, args.trace_ids, args.change_origin, verb=args.verb)
        return outcome.model_dump()

    @server.tool(name="rollback")
    @_refusal_mapped
    async def rollback_tool(args: RollbackToolArgs) -> dict[str, Any]:
        outcome = await engine.rollback(args.alias, args.version, args.trace_ids, args.change_origin)
        return outcome.model_dump()

    @server.tool(name="retire")
    @_refusal_mapped
    async def retire_tool(args: RetireToolArgs) -> dict[str, Any]:
        outcome = await engine.retire(args.alias, args.version, args.trace_ids, args.change_origin)
        return outcome.model_dump()

    return server


__all__ = ["create_server"]
