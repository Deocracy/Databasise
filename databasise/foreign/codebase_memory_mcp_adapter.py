"""``databasise.foreign.codebase_memory_mcp_adapter`` — CONTRACT §17's foreign-part adapter for
the MCP-served engine shape (05-06-PLAN.md Task 1): process lifecycle, the RPC channel, health, and
evidence normalization to §4's ``ItemKind`` union. Deliberately structured like
``databasise/foreign/v1_corpus_adapter.py`` (the sibling adapter for the subprocess-JSON-over-
stdin/stdout engine shape) so Falsifier 6's fixed-cost claim — one adapter shape reused across
differently-shaped foreign engines — is checkable from the diff between the two rather than merely
asserted. No admission data, no verdict text, no ceiling constant lives in this module — those
belong to ``databasise/parts_core/codebase_memory_mcp.py`` (Task 2's part module).

**Resolved client API (05-RESEARCH.md did not fetch ``mcp`` 2.2.0's docs; this plan reads the
installed package directly, per Task 1 action A).** ``mcp.ClientSession``, ``mcp.StdioServerParameters``
and ``mcp.client.stdio.stdio_client`` are the top-level client surface for a stdio-launched MCP
server: ``stdio_client(StdioServerParameters(command=..., args=...))`` is an async context manager
yielding ``(read_stream, write_stream)``; ``ClientSession(read, write)`` is a second async context
manager whose ``initialize()`` completes the MCP handshake, ``list_tools()`` returns a
``types.ListToolsResult`` (``.tools: list[types.Tool]``), and ``call_tool(name, arguments)``
returns a ``types.CallToolResult`` (``.content: list[TextContent]``,
``.structured_content: dict | None``, ``.is_error: bool``). ``stdio_client``'s own ``finally``
block always calls its internal ``_stop_server_process`` under a shielded cancel scope — reading
``mcp/client/stdio.py`` this session confirms the child process is terminated on both the normal
and the cancelled/timed-out exit path, which is why this module raises a timeout from *inside* the
``async with stdio_client(...): async with ClientSession(...):`` block rather than around it.

**A real, load-bearing finding from probing the live 0.10.8 binary this plan's own admission
record cites (evidence for condition 1's "self-report is imprecise" verdict, §X):** no tool
declares an MCP ``outputSchema`` at all (every tool's ``output_schema`` is empty), and only some
tools populate ``structured_content`` (a machine-parseable JSON dict) — ``get_code_snippet``,
``get_graph_schema``, ``list_projects``, ``index_status``, ``check_index_coverage`` and
``index_repository`` do; ``search_graph``, ``search_code``, ``get_architecture``, ``trace_path``
and ``detect_changes`` instead render a compact, custom, whitespace-delimited tabular text
convention inside plain ``TextContent`` — ``"<block>: <N>  (cols: <col1> <col2> ...)"`` followed by
one indented row per record, fields separated by single spaces with no field itself containing a
space. ``_parse_tool_text`` reads this *observed* convention where it matches; it is not a schema
the engine has committed to, and a block this convention does not match (``trace_path``'s nested
per-module grouping, ``detect_changes``'s ``"rows:"`` label) is left unparsed, never guessed at.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

from databasise.foreign._mcp_sdk_guard import import_real_mcp

if TYPE_CHECKING:
    from mcp import ClientSession

# The `mcp` PyPI package (databasise's own optional `mcp` extra, added 05-04-PLAN.md) is imported
# lazily, inside _run_with_session, never at module level: this module is reached from
# databasise.parts_core.codebase_memory_mcp, which default_registry() imports unconditionally —
# a module-level import here would make the whole registry (and therefore nearly the entire test
# suite) fail to import on a bare `uv run pytest` with no extras installed. Only actually calling
# list_tools()/call_tool() needs the extra; importing this module, or registering the Part, never
# does.

# §4's frozen ItemKind union has seven members; this engine's evidence-returning tools only ever
# populate three of them (never a text_chunk/fact_with_validity_interval/page_image_ref/
# sql_result_set shape) — bare string constants, matching seam/evidence.py's own
# TEXT_CHUNK_KIND/CHUNKS_NAMESPACE convention, since no Python ItemKind type exists anywhere in
# this codebase yet (FA-03's own declared shortfall).
ITEM_KIND_CODE_SNIPPET = "code_snippet"
ITEM_KIND_GRAPH_PATH = "graph_path"
ITEM_KIND_DERIVED_FINDING = "derived_finding"

# §4's ChunkRef shape, quoted verbatim from CONTRACT.md: (corpus_id, recipe@version, ordinal,
# content_hash). Falsifier 4's native leg (05-06-PLAN.md Task 3) records, per field, whether this
# engine's raw output supplies it, whether this adapter derives it, or whether it cannot be
# supplied at all — see FALSIFIER-4-EVIDENCE.md for the recorded disposition.
CHUNK_REF_FIELDS: tuple[str, ...] = ("corpus_id", "recipe_at_version", "ordinal", "content_hash")

_KNOWN_INSTALL_PATH = str(Path.home() / ".local" / "bin" / "codebase-memory-mcp")

# §17's Transport paragraph: the adapter resolves the binary once, at import time (a cheap PATH
# lookup, never a process launch) — mirrors DEFAULT_V1_INTERPRETER's own import-time Path
# resolution in v1_corpus_adapter.py.
DEFAULT_CBM_BINARY: str | None = shutil.which("codebase-memory-mcp") or (
    _KNOWN_INSTALL_PATH if Path(_KNOWN_INSTALL_PATH).is_file() else None
)

_CODE_SNIPPET_TOOLS = frozenset({"get_code_snippet", "search_code"})
_GRAPH_PATH_TOOLS = frozenset({"search_graph", "trace_path", "query_graph"})
_DERIVED_FINDING_TOOLS = frozenset(
    {
        "get_architecture",
        "get_graph_schema",
        "index_status",
        "check_index_coverage",
        "detect_changes",
        "list_projects",
    }
)

_BLOCK_HEADER_RE = re.compile(r"^(?P<block>[a-zA-Z_]+):\s*(?P<count>\d+)\s+\(cols:\s*(?P<cols>[^)]+)\)\s*$")


class ForeignEngineUnavailableError(RuntimeError):
    """§17's Transport paragraph: the ``codebase-memory-mcp`` binary does not resolve to anything
    executable — named rather than a bare ``FileNotFoundError``, matching
    ``v1_corpus_adapter.MissingV1InterpreterError``'s own house style."""

    def __init__(self, attempted: str):
        self.attempted = attempted
        super().__init__(
            f"codebase-memory-mcp binary not found (resolved to {attempted!r}); install it or "
            "set PATH so shutil.which('codebase-memory-mcp') can find it"
        )


class CbmToolTimeoutError(RuntimeError):
    """§8 condition 4's wall-clock-ceiling refusal, restated at this MCP-specific boundary per
    §17: the tool call did not complete within ``timeout`` seconds — carries both the tool name
    and the declared timeout on named attributes."""

    def __init__(self, tool_name: str, timeout: float):
        self.tool_name = tool_name
        self.timeout = timeout
        super().__init__(f"codebase-memory-mcp tool {tool_name!r} exceeded its wall-clock ceiling of {timeout}s")


class CbmTransportError(RuntimeError):
    """§17's health-and-lifecycle rule: a cross-process transport failure MUST record the
    placement of both endpoints and the failure cause, so a placement-related failure is
    diagnosable from the trace alone. Carries the failure cause plus both endpoint placements on
    named attributes — never merely a wrapped, unnamed exception."""

    def __init__(self, *, tool_name: str, cause: str, machine_endpoint: str, foreign_endpoint: str):
        self.tool_name = tool_name
        self.cause = cause
        self.machine_endpoint = machine_endpoint
        self.foreign_endpoint = foreign_endpoint
        super().__init__(
            f"transport failure calling {tool_name!r}: {cause} "
            f"(machine_endpoint={machine_endpoint!r}, foreign_endpoint={foreign_endpoint!r})"
        )


class CbmToolCallError(RuntimeError):
    """The engine itself reported ``is_error=True`` for a call that transported cleanly — a tool
    argument mistake, not a transport failure; kept distinct from :class:`CbmTransportError` so a
    caller can tell "the RPC worked and the tool refused" from "the RPC itself failed"."""

    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        self.message = message
        super().__init__(f"codebase-memory-mcp tool {tool_name!r} returned an error: {message}")


class UntypedForeignItemError(RuntimeError):
    """§4's "kind MUST NOT be represented as a bare scalar field" / §17's "an untyped pass-through
    is exactly that failure, relocated to this boundary" rule: ``tool_name`` names a tool this
    adapter has no §4 ``ItemKind`` mapping for (a mutator or the index-build tool, never an
    evidence-returning one) — carries the tool name and the offending item's own keys, never a
    pass-through with a bare label."""

    def __init__(self, tool_name: str, raw_item: Any):
        self.tool_name = tool_name
        self.item_keys = sorted(raw_item.keys()) if isinstance(raw_item, dict) else []
        super().__init__(
            f"codebase-memory-mcp tool {tool_name!r} returned an item this adapter cannot type "
            f"to a §4 ItemKind member (item keys: {self.item_keys})"
        )


def _resolve_binary(binary: str | None) -> str:
    resolved = binary or DEFAULT_CBM_BINARY
    if resolved and (shutil.which(resolved) or Path(resolved).is_file()):
        return resolved
    raise ForeignEngineUnavailableError(resolved or binary or "codebase-memory-mcp")


def _unwrap(exc: BaseException) -> BaseException:
    """anyio's ``TaskGroup`` wraps every child-task failure — a real transport error, a timeout,
    or a cancellation — in a ``BaseExceptionGroup``; unwrap to the first leaf exception so the
    caller sees the real cause, never an opaque group wrapper."""
    seen: BaseException = exc
    while isinstance(seen, BaseExceptionGroup) and seen.exceptions:
        seen = seen.exceptions[0]
    return seen


def _parse_tool_text(text: str) -> list[dict[str, Any]]:
    """Reads this engine's own ``"<block>: <N>  (cols: <col1> <col2> ...)"`` table convention
    (module docstring) into row dicts, each carrying its own ``_block`` name. A block this
    convention does not match is simply not emitted — the caller falls back to a single
    ``_raw_text`` item rather than guessing at an undeclared shape."""
    rows: list[dict[str, Any]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        match = _BLOCK_HEADER_RE.match(lines[i].strip())
        if not match:
            i += 1
            continue
        block = match.group("block")
        columns = match.group("cols").split()
        i += 1
        while i < len(lines) and lines[i][:1] in (" ", "\t") and lines[i].strip():
            tokens = lines[i].strip().split()
            if len(tokens) == len(columns):
                row = dict(zip(columns, tokens, strict=True))
                row["_block"] = block
                rows.append(row)
            i += 1
    return rows


async def _run_with_session(binary: str | None, tool_name: str, timeout: float, call: Any) -> Any:
    """Shared lifecycle for :func:`list_tools`/:func:`call_tool`: resolve the binary, launch it
    over stdio, complete the handshake, run ``call(session)`` under ``timeout``, and terminate —
    always, on both the success and the failure path (module docstring's ``stdio_client`` note).

    Imports ``anyio``/``mcp`` lazily (module docstring's own note): only reaching this function —
    an actual call, never merely importing this module or registering the Part — requires the
    ``mcp`` extra to be installed. The binary is resolved *before* that import, so
    :class:`ForeignEngineUnavailableError` still fires cleanly for an unresolvable binary even
    when the ``mcp`` extra itself is not installed.

    Resolved via ``databasise.foreign._mcp_sdk_guard.import_real_mcp`` (05-07-PLAN.md's own fix,
    Rule 1) rather than a bare ``from mcp import ...`` — a sibling ``databasise/mcp/`` package
    introduced by that same plan shares this SDK's own top-level name, and a bare import can
    resolve to that package instead of the real SDK under some invocation shapes (see the guard
    module's own docstring).
    """
    resolved = _resolve_binary(binary)

    import anyio

    mcp_module = import_real_mcp("mcp")
    stdio_module = import_real_mcp("mcp.client.stdio")
    ClientSession = mcp_module.ClientSession
    StdioServerParameters = mcp_module.StdioServerParameters
    stdio_client = stdio_module.stdio_client

    params = StdioServerParameters(command=resolved, args=[])
    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                with anyio.fail_after(timeout):
                    return await call(session)
    except ForeignEngineUnavailableError:
        raise
    except BaseException as exc:  # noqa: BLE001 — unwrapped and re-raised by name immediately below
        unwrapped = _unwrap(exc)
        if isinstance(unwrapped, TimeoutError):
            raise CbmToolTimeoutError(tool_name, timeout) from exc
        raise CbmTransportError(
            tool_name=tool_name,
            cause=str(unwrapped) or type(unwrapped).__name__,
            machine_endpoint="databasise.foreign.codebase_memory_mcp_adapter (this process)",
            foreign_endpoint=f"codebase-memory-mcp subprocess ({resolved})",
        ) from exc


def list_tools(*, binary: str | None = None, timeout: float = 60.0) -> list[dict[str, Any]]:
    """Start the server over stdio, complete the MCP initialize handshake, enumerate tools,
    terminate the process, and return the tool records as plain dicts (``Tool.model_dump()`` —
    JSON-serializable, so a captured run is directly committable as a test fixture). Never
    hardcodes a tool name: the engine's own served surface is read live every call."""

    async def _call(session: ClientSession) -> list[dict[str, Any]]:
        result = await session.list_tools()
        return [tool.model_dump(mode="json") for tool in result.tools]

    return asyncio.run(_run_with_session(binary, "list_tools", timeout, _call))


def call_tool(
    name: str, arguments: dict[str, Any] | None = None, *, binary: str | None = None, timeout: float
) -> list[dict[str, Any]]:
    """The same lifecycle for one tool call. Prefers ``structured_content`` when the engine
    populates it (a single-item list carrying that dict); otherwise parses the text content's
    ``"cols:"`` table blocks (:func:`_parse_tool_text`) into row items; falls back to a single
    ``{"_raw_text": ...}`` item when neither shape is present. ``timeout`` is required, not
    optional — every call site declares §8 condition 4's wall-clock ceiling explicitly, restated
    for the MCP hosting shape per §17."""

    async def _call(session: ClientSession) -> list[dict[str, Any]]:
        result = await session.call_tool(name, arguments or {})
        if result.is_error:
            text = "; ".join(getattr(content, "text", "") or "" for content in result.content)
            raise CbmToolCallError(name, text)
        if result.structured_content is not None:
            return [dict(result.structured_content)]
        text = "".join(getattr(content, "text", "") or "" for content in result.content)
        rows = _parse_tool_text(text)
        return rows if rows else [{"_raw_text": text}]

    return asyncio.run(_run_with_session(binary, name, timeout, _call))


def normalise_to_item_kind(raw_item: dict[str, Any], tool_name: str) -> dict[str, Any]:
    """Map one raw item returned by ``tool_name`` to a §4 ``ItemKind`` member. Raises
    :class:`UntypedForeignItemError` for a tool this adapter has no evidence-kind mapping for
    (a mutator or the index-build tool — never a pass-through with a bare label).

    Every returned record's evidence tier is capped ``"below_T1"``: this engine supplies neither
    ``recipe_at_version`` nor ``ordinal`` for any tool (it declares no recipe/chunk-ordinal concept
    at all — ``PARTS.md ## §X``: ``"Recipe: n/a"``), so no item from this engine can ever satisfy
    §4's ``ChunkRef`` shape in full, regardless of which other fields a given call happens to
    supply. This is the structural finding, not a per-call gap — recorded here so it cannot be
    silently rounded up to ``T1`` on a call that happens to supply the other three fields.
    """
    if tool_name in _CODE_SNIPPET_TOOLS:
        kind = ITEM_KIND_CODE_SNIPPET
    elif tool_name in _GRAPH_PATH_TOOLS:
        kind = ITEM_KIND_GRAPH_PATH
    elif tool_name in _DERIVED_FINDING_TOOLS:
        kind = ITEM_KIND_DERIVED_FINDING
    else:
        raise UntypedForeignItemError(tool_name, raw_item)

    project = raw_item.get("project") if isinstance(raw_item, dict) else None
    chunk_ref: dict[str, str | None] = {
        "corpus_id": project,  # derived when the engine happens to echo a "project" field —
        # not echoed by get_code_snippet/search_graph/search_code's own raw output (FALSIFIER-4)
        "recipe_at_version": None,  # cannot be supplied — no recipe concept anywhere in this engine
        "ordinal": None,  # cannot be supplied — no chunk-ordinal concept anywhere in this engine
        "content_hash": None,
    }
    source = raw_item.get("source") if isinstance(raw_item, dict) else None
    if isinstance(source, str) and source:
        chunk_ref["content_hash"] = "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()

    ref: dict[str, Any] | None = None
    file_path = raw_item.get("file_path") or raw_item.get("file") if isinstance(raw_item, dict) else None
    if file_path:
        line_range: str | None = None
        if "start_line" in raw_item and "end_line" in raw_item:
            line_range = f"{raw_item['start_line']}-{raw_item['end_line']}"
        elif "lines" in raw_item:
            line_range = str(raw_item["lines"])
        ref = {"file_path": file_path, "line_range": line_range, "chunk_ref": chunk_ref}

    derived_from: tuple[str, ...] = ()
    if kind == ITEM_KIND_DERIVED_FINDING:
        derived_from = (f"cbm-project:{project or tool_name}",)

    missing_fields = tuple(field for field in CHUNK_REF_FIELDS if not chunk_ref.get(field))
    return {
        "kind": kind,
        "tool_name": tool_name,
        "ref": ref,
        "tier": "below_T1",
        "tier_reason": (
            f"ChunkRef fields unsupplied for this item: {list(missing_fields)} — this engine "
            "declares no recipe/corpus concept (PARTS.md ## §X: 'Recipe: n/a')"
        ),
        "derived_from": derived_from,
        "raw": raw_item,
    }


__all__ = [
    "ITEM_KIND_CODE_SNIPPET",
    "ITEM_KIND_GRAPH_PATH",
    "ITEM_KIND_DERIVED_FINDING",
    "CHUNK_REF_FIELDS",
    "DEFAULT_CBM_BINARY",
    "ForeignEngineUnavailableError",
    "CbmToolTimeoutError",
    "CbmTransportError",
    "CbmToolCallError",
    "UntypedForeignItemError",
    "list_tools",
    "call_tool",
    "normalise_to_item_kind",
]
