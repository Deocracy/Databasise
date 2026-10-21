"""``databasise.mcp.server`` — the MCP server factory (05-07-PLAN.md Task 1, action A/E). Copies
``databasise.seam.rest``'s "thin adapter, provably" architecture to a second protocol: one
``Databasise`` instance, ten tool bodies that are each exactly deserialize-then-await-then-return,
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
both confirmed live this session. ``call_tool`` raises a tool's ``ToolError`` rather than returning
a ``CallToolResult``; the wrapping into ``is_error=True`` happens one layer up, in the
wire-protocol handler this factory never calls directly. ``call_tool`` is overridden exactly once,
below.

**The refusal mapper (09-04-PLAN.md, SEAM-03, D-02).** One place maps every refusal:
:class:`_DatabasiseServer` overrides ``MCPServer.call_tool``. The SDK wraps whatever a tool call
raises -- an argument-validation ``ValidationError`` or a body ``ToolError`` becomes
``ToolError("Error executing tool <name>: ...")``, any other body exception becomes
``UnexpectedToolError("Error executing tool <name>")`` -- so a refusal never reaches the caller
unwrapped. The override walks the ``__cause__`` chain (first refusal wins; a pydantic
``ValidationError`` is unwrapped through ``refusal_from_errors``, which finds a refusal a model
validator raised, e.g. ``IngestDocument``'s ``AmbiguousIngestPayloadError``) and re-raises it as
:class:`RefusalToolError` whose ``str()`` is exactly ``json.dumps(refusal_body(refusal))`` -- the
same body REST returns (``databasise.seam.refusals.refusal_body``). The SDK's wire handler turns
that into ``CallToolResult(is_error=True, content=[TextContent(text=str(exc))])``.

**What an MCP client receives (09-04-PLAN.md, D-02).**

- A refusal arrives as a ``CallToolResult`` with ``isError`` true and one text content whose text is
  the bare JSON object ``{"refusal_type": "<ClassName>", "message": "...", <public attributes>}``,
  the same body REST returns, with no ``Error executing tool <name>: `` prefix.
- An in-process ``server.call_tool`` raises :class:`RefusalToolError` (a ``ToolError``) carrying
  that same text.
- An argument schema error that carries no refusal keeps the SDK text
  ``Error executing tool <name>: <pydantic message>``.
- An unexpected crash keeps ``Error executing tool <name>`` with no reason.

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
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from databasise.mcp._sdk import import_sdk
from databasise.mcp.tools import (
    CompareToolArgs,
    DeleteToolArgs,
    IngestToolArgs,
    PromoteToolArgs,
    QueryToolArgs,
    ResolveToolArgs,
    RetireToolArgs,
    RetryToolArgs,
    RollbackToolArgs,
    StatusToolArgs,
)
from databasise.parts.registry import PartRegistry
from databasise.seam.compare import COMPARE_RESPONSE_SHAPE_RULE
from databasise.seam.corpus import checked_page
from databasise.seam.engine import Databasise
from databasise.seam.refusals import (
    MissingScopeArgumentError,
    SeamRefusalError,
    refusal_body,
    refusal_from_errors,
)

# Resolved through _sdk.import_sdk (module docstring) — never a bare `from mcp... import ...`,
# which reproduces a CWD-shadow circular import under `cd databasise && python -c ...` (the exact
# shape several of this plan's own acceptance criteria run).
MCPServer = import_sdk("mcp.server.mcpserver").MCPServer
ToolError = import_sdk("mcp.server.mcpserver.exceptions").ToolError

_ServerName = "databasise"


class RefusalToolError(ToolError):
    """A refusal on the MCP wire: ``str()`` is exactly the bare refusal JSON, no SDK prefix. It
    deliberately does not subclass ``UnexpectedToolError`` -- the SDK logs that one as a crash."""


def _find_refusal(exc: BaseException) -> SeamRefusalError | None:
    """The first ``SeamRefusalError`` on ``exc`` or its ``__cause__`` chain; a pydantic
    ``ValidationError`` on the chain is unwrapped through ``refusal_from_errors``."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, SeamRefusalError):
            return current
        if isinstance(current, ValidationError):
            found = refusal_from_errors(current.errors())
            if found is not None:
                return found
        current = current.__cause__
    return None


class _DatabasiseServer(MCPServer):
    async def call_tool(self, name: str, arguments: dict[str, Any], context: Any = None) -> Any:
        try:
            return await super().call_tool(name, arguments, context)
        except ToolError as exc:
            refusal = _find_refusal(exc)
            if refusal is None:
                raise
            raise RefusalToolError(json.dumps(refusal_body(refusal))) from exc


async def _status_job(engine: Databasise, args: StatusToolArgs) -> Any:
    if args.job_id is None:
        raise MissingScopeArgumentError(tool="status", scope="job", argument="job_id")
    return await engine.get_job_status(args.job_id, checked_page(args.limit, args.offset))


async def _status_corpus(engine: Databasise, args: StatusToolArgs) -> Any:
    return await engine.corpus_status(checked_page(args.limit, args.offset), args.selector)


async def _status_counts(engine: Databasise, args: StatusToolArgs) -> Any:
    return await engine.document_counts(args.selector)


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
        raise MissingScopeArgumentError(tool="resolve", scope="evidence", argument="evidence_ref")
    return await engine.resolve_evidence(args.evidence_ref)


async def _resolve_trace_scope(engine: Databasise, args: ResolveToolArgs) -> dict[str, Any]:
    if args.trace_reference is None:
        raise MissingScopeArgumentError(tool="resolve", scope="trace", argument="trace_reference")
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
    every tool in ``databasise.mcp.tools.TOOL_NAMES`` (ten) as a thin adapter over it. ``server.engine`` holds the constructed instance
    directly (mirrors ``databasise.seam.rest``'s own ``app.state.engine``), reachable for a test's
    own identity assertion.
    """
    engine = Databasise(store_root=store_root, workspace=workspace, registry=registry, clients=clients)
    server = _DatabasiseServer(_ServerName)
    server.engine = engine

    @server.tool(
        name="ingest",
        description=(
            "Add one document to the corpus. Pass the document as text, or as raw_base64 for a "
            "binary file, with an optional document_id. An optional selector names which fitted "
            "modality's index receives it. Returns the ingest job record."
        ),
    )
    async def ingest_tool(args: IngestToolArgs) -> dict[str, Any]:
        job = await engine.ingest(args.to_ingest_document(), args.selector)
        return job.model_dump()

    @server.tool(
        name="query",
        description=(
            "Answer a query from the corpus. Requires query, the query object. An optional selector "
            "chooses which fitted modality answers. Returns the answer envelope with its evidence "
            "references and trace token."
        ),
    )
    async def query_tool(args: QueryToolArgs) -> dict[str, Any]:
        envelope = await engine.query(args.query, args.selector)
        return envelope.model_dump()

    # API-08's comparison operation, a legitimate extra tool under §18.5: comparison is not
    # expressible as a §18.4 selector (a selector picks one arm; this call fans out over N of them
    # in one request), and registering a second modality added zero tools (see
    # ``databasise.mcp.tools``'s module docstring). The published description carries
    # ``COMPARE_RESPONSE_SHAPE_RULE`` verbatim (D-10), so it cannot drift from REST.
    @server.tool(
        name="compare",
        description=(
            "Run one query against several selectors in one call. Requires query and selectors. "
            + COMPARE_RESPONSE_SHAPE_RULE
        ),
    )
    async def compare_tool(args: CompareToolArgs) -> dict[str, Any]:
        result = await engine.compare(args.query, args.selectors)
        if isinstance(result, dict):
            return {key: envelope.model_dump() for key, envelope in result.items()}
        return result.model_dump()

    @server.tool(
        name="delete",
        description=(
            "Remove one document from the corpus. Requires document_id. An optional selector names "
            "which fitted modality's index the delete reaches. Returns the delete outcome."
        ),
    )
    async def delete_tool(args: DeleteToolArgs) -> dict[str, Any]:
        outcome = await engine.delete_document(args.document_id, args.selector)
        return outcome.model_dump()

    # Reaches the identical ``Databasise.retry_document()`` REST's retry route reaches (D-08).
    @server.tool(
        name="retry",
        description=(
            "Reprocess one document left interrupted by a timed-out ingest. Requires document_id. An "
            "optional selector names which fitted modality's index the retry reaches. Returns the "
            "ingest job record."
        ),
    )
    async def retry_tool(args: RetryToolArgs) -> dict[str, Any]:
        job = await engine.retry_document(args.document_id, args.selector)
        return job.model_dump()

    @server.tool(
        name="status",
        description=(
            "Read bounded status. Requires scope: 'job' (needs job_id; paged by limit and offset), "
            "'corpus' (a paged document list), 'counts' (document counts) or 'health'. An optional "
            "selector applies to 'corpus' and 'counts'. Returns the status record for that scope."
        ),
    )
    async def status_tool(args: StatusToolArgs) -> dict[str, Any]:
        handler = _STATUS_HANDLERS[args.scope]
        result = await handler(engine, args)
        return result.model_dump()

    @server.tool(
        name="resolve",
        description=(
            "Follow a reference that query returned. Scope 'evidence' requires evidence_ref; scope "
            "'trace' requires trace_reference, with an optional debug flag. Returns the resolved record."
        ),
    )
    async def resolve_tool(args: ResolveToolArgs) -> dict[str, Any]:
        handler = _RESOLVE_HANDLERS[args.scope]
        result = await handler(engine, args)
        return result

    # Reaches the identical ``Databasise.promote()`` REST's ``POST /promote`` reaches. No per-tool
    # try/except: ``_DatabasiseServer.call_tool`` maps every refusal generically via the
    # ``SeamRefusalError`` base class.
    @server.tool(
        name="promote",
        description=(
            "Promote an alias to a new generation, recorded in the append-only generation history. "
            "Requires alias and trace_ids. Optional change_origin and verb (default "
            "'operator-asserted'). Returns the promotion outcome."
        ),
    )
    async def promote_tool(args: PromoteToolArgs) -> dict[str, Any]:
        outcome = await engine.promote(args.alias, args.trace_ids, args.change_origin, verb=args.verb)
        return outcome.model_dump()

    @server.tool(
        name="rollback",
        description=(
            "Return an alias to a named prior generation. Requires alias, version and trace_ids. "
            "Optional change_origin. Returns the rollback outcome."
        ),
    )
    async def rollback_tool(args: RollbackToolArgs) -> dict[str, Any]:
        outcome = await engine.rollback(args.alias, args.version, args.trace_ids, args.change_origin)
        return outcome.model_dump()

    @server.tool(
        name="retire",
        description=(
            "Retire one generation of an alias so it can no longer be made active. Requires alias, "
            "version and trace_ids. Optional change_origin. Returns the retirement outcome."
        ),
    )
    async def retire_tool(args: RetireToolArgs) -> dict[str, Any]:
        outcome = await engine.retire(args.alias, args.version, args.trace_ids, args.change_origin)
        return outcome.model_dump()

    return server


__all__ = ["create_server"]
