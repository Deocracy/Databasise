"""``codebase-memory-mcp`` — the second, differently-shaped opaque part admitted whole-engine
(05-06-PLAN.md Task 2), turning ``PARTS.md ## §X``'s already-run, source-level eleven-verdict
analysis into an executable §8 ``AdmissionRecord``. This module projects that analysis — it does
not re-derive it: each verdict's ``evidence`` string cites the corresponding row of §X's own table,
restated in this record's own words, plus this plan's own three additions §X could not itself
supply: a measured wall-clock ceiling (§8 condition 4 requires the *admitting machine* declare one;
the engine self-reports none), the version drift between the pinned clone §X's verdicts were
code-verified against and the binary actually installed on this machine, and a live tool-surface
comparison confirming the fifteen-tool set has not moved between the two.

Three of the eleven rows are **not** clean yeses, carried forward as such rather than rounded up:
condition 1 is evidence *for* the admission rule (the engine's own tool annotations are
demonstrably imprecise), condition 3 is an open question (``PARTS.md ## §R`` row ``N12``, restated
in ``network_namespace`` below), and conditions 7, 8, and the counting half of 9 are machine-side
obligations §X's source-level analysis cannot itself prove either way.
"""

from __future__ import annotations

import asyncio
import hashlib
import subprocess
from pathlib import Path
from typing import Any

from databasise.foreign.codebase_memory_mcp_adapter import (
    DEFAULT_CBM_BINARY,
    call_tool,
    normalise_to_item_kind,
)
from databasise.identity.canon import canonicalise
from databasise.parts.admission import (
    MANIFEST_SOURCE_CODE_INSPECTED,
    AdmissionRecord,
    ConditionVerdict,
)
from databasise.parts.schema import NodeContext
from databasise.runner.trace import TokenAccounting

# The pinned clone PARTS.md ## §X's eleven verdicts were code-verified against — the "verified
# against" side of the version-drift comparison this record's own manifest states.
PINNED_CLONE_SHA = "61b3b1b2"

# §8 condition 4: measured by running index_repository through the adapter against this
# repository's own databasise/ directory (05-06-PLAN.md Task 2 action A) — 2.88s cold-start
# wall-clock (fresh stdio handshake + full parse of ~177 Python files / 3204 nodes / 14401 edges),
# 1.52s warm. The engine self-reports no ceiling anywhere in its source or README (PARTS.md ## §X
# condition 4's own negative-result evidence) — a measurement is the only honest basis. Margin: a
# real target repository this engine indexes may be an order of magnitude or more larger than this
# project's own databasise/ directory; ~40x the measured cold-start duration gives headroom for
# that without being an arbitrary round number picked from convention.
CBM_MEASURED_INDEX_DURATION_SECONDS = 2.88
CBM_WALL_CLOCK_CEILING_SECONDS = 120.0


def _binary_sha256(binary: str | None) -> str:
    """A missing binary contributes an empty string rather than raising — this record must still
    import cleanly on a machine that has not installed the engine; the real
    ``ForeignEngineUnavailableError`` refusal is what surfaces the actual absence at run time."""
    if not binary:
        return ""
    try:
        return "sha256:" + hashlib.sha256(Path(binary).read_bytes()).hexdigest()
    except OSError:
        return ""


def _reported_version(binary: str | None) -> str:
    """The installed binary's own ``--version`` output — the "installed on this machine" side of
    the version-drift comparison. Empty string on any failure, matching :func:`_binary_sha256`'s
    own missing-binary tolerance."""
    if not binary:
        return ""
    try:
        result = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (result.stdout.strip() or result.stderr.strip())


_BINARY_SHA256 = _binary_sha256(DEFAULT_CBM_BINARY)
_REPORTED_VERSION = _reported_version(DEFAULT_CBM_BINARY)

# Confirmed this session (05-06-PLAN.md Task 2 action C): calling list_tools() against the
# installed 0.10.8 binary returns exactly PARTS.md ## §X's own fifteen tool names — no new tool,
# none gone. The comparison is recorded in ADMISSION-CODEBASE-MEMORY-MCP.md; this constant is the
# same fifteen-name set §X's table already enumerates, restated here so a later re-check has a
# concrete baseline to diff against without re-reading the whole manifest document.
CBM_KNOWN_TOOL_NAMES: tuple[str, ...] = (
    "index_repository",
    "search_graph",
    "query_graph",
    "trace_path",
    "get_code_snippet",
    "get_graph_schema",
    "get_architecture",
    "search_code",
    "list_projects",
    "delete_project",
    "index_status",
    "check_index_coverage",
    "detect_changes",
    "manage_adr",
    "ingest_traces",
)


def _compute_environment_hash() -> str:
    """§8 condition 2's whole-resolved-runtime-closure rule for a single-binary, no-interpreter
    engine (PARTS.md ## §X condition 2: "no interpreter, no venv, no external SDK to hash
    separately" — the binary itself *is* the closure): a digest over the resolved binary path, its
    own SHA-256, and its self-reported version."""
    payload = {
        "binary_path": DEFAULT_CBM_BINARY or "",
        "binary_sha256": _BINARY_SHA256,
        "reported_version": _REPORTED_VERSION,
    }
    return "sha256:" + hashlib.sha256(canonicalise(payload)).hexdigest()


_VERSION_DRIFT_NOTE = (
    f"pinned clone codebase-memory-mcp@{PINNED_CLONE_SHA} (PARTS.md ## §X's code-verified basis) "
    f"vs installed {_REPORTED_VERSION or '(unknown — binary not found)'} at {DEFAULT_CBM_BINARY or '(none)'}"
)

CODEBASE_MEMORY_MCP_ADMISSION = AdmissionRecord(
    part_name_at_version="codebase-memory-mcp@0.1.0",
    entry_path="whole-engine opaque node, hosted as a subprocess over the MCP stdio transport",
    storage="self-contained",
    wall_clock_ceiling_seconds=CBM_WALL_CLOCK_CEILING_SECONDS,
    wall_clock_ceiling_basis=(
        f"measured {CBM_MEASURED_INDEX_DURATION_SECONDS}s (cold-start) running index_repository "
        "through the adapter against this repository's own databasise/ directory "
        "(~177 Python files, 3204 nodes, 14401 edges); the engine self-reports no ceiling "
        "anywhere in its source or README (PARTS.md ## §X condition 4) — declared ceiling is "
        "~40x that measurement, headroom for a substantially larger target repository"
    ),
    feed_tier=(
        "n/a — index_repository takes a filesystem repo_path, no machine-produced feed "
        "(PARTS.md ## §X condition 6, §X.5's Falsifier-4 finding)"
    ),
    ttl_days=90,
    network_namespace=(
        "open question, not a clean yes (PARTS.md ## §X condition 3, ## §R row N12): zero LLM "
        "and zero outbound network calls confirmed across all fifteen tool handlers, but a "
        "loopback-bound HTTP UI server (127.0.0.1-only, same-origin CORS) exists inside the same "
        "OS process outside the MCP tool surface, and whether §8 condition 3's denial is scoped "
        "per-MCP-tool-call or per-OS-process is not settled by CONTRACT text. No OS-level "
        "network-namespace isolation is built this phase (05-RESEARCH.md Open Question 3, "
        "accepted as a scope boundary consistent with the project's no-Docker, local-NixOS "
        "constraint) — this admission carries the open question forward as its own caveat "
        "rather than as a closed condition."
    ),
    environment_hash=_compute_environment_hash(),
    manifest_source=MANIFEST_SOURCE_CODE_INSPECTED,
    verdicts=(
        ConditionVerdict(
            condition=1,
            verdict="confirms-the-rule",
            evidence=(
                "not a satisfied/failed condition but evidence for the rule itself: the "
                "engine's own tool self-report is demonstrably imprecise — ten of fifteen "
                "tools self-declare destructive_hint=True despite calling no mutation function, "
                "and only list_projects self-declares read_only_hint=True (confirmed live "
                "against the installed 0.10.8 binary this session, matching PARTS.md ## §X "
                "condition 1's own mcp.c:698-724 code-verified finding against the pinned "
                "clone). This manifest is built from code inspection (§X's handler-by-handler "
                f"scan), never from the engine's own self-report. {_VERSION_DRIFT_NOTE}."
            ),
        ),
        ConditionVerdict(
            condition=2,
            verdict="satisfied",
            evidence=(
                "environment_hash covers the whole resolved closure for this single-binary, "
                "no-interpreter engine: the resolved binary path, its own SHA-256 digest, and "
                "its self-reported version (PARTS.md ## §X condition 2: the engine vendors its "
                "own tree-sitter grammars and embedding model with no separate interpreter/venv "
                "to hash) — computed by this module's own _compute_environment_hash, "
                "independent of the ingest/delete ports' identically-shaped but differently-"
                "sourced functions."
            ),
        ),
        ConditionVerdict(
            condition=3,
            verdict="open-question",
            evidence=(
                "PARTS.md ## §X condition 3 and ## §R row N12, carried forward verbatim as this "
                "record's own network_namespace field states: zero LLM/network calls in any of "
                "the fifteen tool handlers, but a loopback-bound HTTP UI server exists in the "
                "same OS process outside the MCP tool surface, and per-call-vs-per-process "
                "denial scoping is not settled by §8's text. Recorded as open, not rounded to "
                "a yes."
            ),
        ),
        ConditionVerdict(
            condition=4,
            verdict="satisfied",
            evidence=(
                f"CBM_WALL_CLOCK_CEILING_SECONDS={CBM_WALL_CLOCK_CEILING_SECONDS} is declared "
                "here — the engine self-reports none (PARTS.md ## §X condition 4's own negative-"
                "result grep against the source and README) — and enforced by "
                "databasise.foreign.codebase_memory_mcp_adapter.call_tool's timeout= parameter, "
                "raising CbmToolTimeoutError on breach; databasise.validator.execution_mode.host "
                "refuses to host this placement at all without a positive ceiling."
            ),
        ),
        ConditionVerdict(
            condition=5,
            verdict="satisfied",
            evidence=(
                "storage='self-contained', confirmed live: the engine's own SQLite cache, "
                "bundled embeddings, and tree-sitter parse state never cross into this "
                "machine's artifact registry (PARTS.md ## §X condition 5, platform.c:535's "
                "cache-path evidence) — CODEBASE_MEMORY_MCP_PART.artifact_scope='self_storage', "
                "never 'shared', enforced by validate_admission's ForbiddenSharedScopeError."
            ),
        ),
        ConditionVerdict(
            condition=6,
            verdict="satisfied",
            evidence=(
                "vacuously satisfiable, re-confirmed live: index_repository's only input is a "
                "filesystem repo_path (confirmed by calling it directly against this "
                "repository's own databasise/ directory this session) — this engine never "
                "consumes a machine-produced feed at all, so it declares no consumed feed_tier "
                "(PARTS.md ## §X condition 6, §X.5's Falsifier-4 structural finding, carried "
                "forward unchanged by this drift check)."
            ),
        ),
        ConditionVerdict(
            condition=7,
            verdict="machine-side-obligation",
            evidence=(
                "policy-level, not source-evidenced (PARTS.md ## §X condition 7) — enforced by "
                "databasise.parts.admission.cross_check_conditions at registration time: the "
                "codebase-memory-mcp wiring's own provides node must be excluded from the "
                "default selector's candidate set (databasise.seam.selectors._is_default_eligible)."
            ),
        ),
        ConditionVerdict(
            condition=8,
            verdict="machine-side-obligation",
            evidence=(
                "policy-level ~90-day TTL/ledger mechanic, not source-evidenced (PARTS.md ## §X "
                "condition 8) — ttl_days=90 is declared on this record; renewal-with-reason "
                "ledger enforcement is the same machine-side mechanism the sibling LightRAG "
                "ports' admission records already rely on, not re-invented here."
            ),
        ),
        ConditionVerdict(
            condition=9,
            verdict="machine-side-obligation",
            evidence=(
                "the invocation shape half is satisfied, re-confirmed live: every one of the "
                "fifteen tools (unchanged from PARTS.md ## §X's own table — see "
                "CBM_KNOWN_TOOL_NAMES and this record's live tool-surface comparison in "
                "ADMISSION-CODEBASE-MEMORY-MCP.md) is an explicit, named MCP call with no "
                "implicit/ambient invocation path. The counting-and-non-promotion half — "
                "whether an explicit part_ref invocation is counted as data and never a "
                "promotion trigger — is a machine-side ledger mechanic with no source evidence "
                "either way, exactly as §X's own table records; not rounded up to a full yes."
            ),
        ),
        ConditionVerdict(
            condition=10,
            verdict="satisfied",
            evidence=(
                "enforced by databasise.parts.admission.cross_check_conditions: this part's "
                "artifact_scope='self_storage' can never be enumerated as an SA-1-shareable "
                "artifact by databasise.registry_artifact.index.ArtifactRegistry.discover — "
                "nothing this engine produces ever crosses into the machine's artifact registry "
                "(PARTS.md ## §X condition 10)."
            ),
        ),
        ConditionVerdict(
            condition=11,
            verdict="satisfied",
            evidence=(
                "re-confirmed live against the installed 0.10.8 binary's own input schemas this "
                "session: none of the fifteen tools' schemas carries an as_of/valid_at/interval "
                "parameter of any kind (PARTS.md ## §X condition 11's own negative-result scan, "
                "unaffected by the version drift since the tool surface has not moved) — and "
                "databasise.seam.query.QueryObject declares no 'as_of' member, structurally "
                "impossible to violate, checked at registration by cross_check_conditions."
            ),
        ),
    ),
)


async def codebase_memory_mcp_body(ctx: NodeContext) -> dict[str, Any]:
    """Reads ``tool``/``arguments`` from ``ctx.config``, calls the adapter's ``call_tool`` under
    the declared ceiling (blocking — wrapped in ``asyncio.to_thread``, mirroring
    ``full_ingest_body``'s/``full_delete_body``'s own pattern for the sibling engine's blocking
    ``subprocess.run`` call), and returns each raw item normalized through
    :func:`normalise_to_item_kind`. Token spend is reported as a real, honest zero
    (``TokenAccounting()``, ``counted_by='none'``) rather than the sibling ports'
    ``'unbudgetable'`` sentinel: this engine has zero LLM calls anywhere in its fifteen-tool
    surface (condition 3's own evidence), so "no spend occurred" is the true fact here — not "spend
    occurred but was not exposed back to this caller," which is what ``'unbudgetable'`` means for
    the LightRAG ports.
    """
    config = ctx.config or {}
    tool_name = config.get("tool")
    if not tool_name:
        raise ValueError("codebase_memory_mcp_body requires ctx.config['tool']")
    arguments = config.get("arguments") or {}

    raw_items = await asyncio.to_thread(
        call_tool,
        tool_name,
        arguments,
        timeout=CBM_WALL_CLOCK_CEILING_SECONDS,
    )
    items = [normalise_to_item_kind(item, tool_name) for item in raw_items]

    return {
        "tool": tool_name,
        "items": items,
        "tokens": TokenAccounting(),
    }


__all__ = [
    "PINNED_CLONE_SHA",
    "CBM_MEASURED_INDEX_DURATION_SECONDS",
    "CBM_WALL_CLOCK_CEILING_SECONDS",
    "CBM_KNOWN_TOOL_NAMES",
    "CODEBASE_MEMORY_MCP_ADMISSION",
    "codebase_memory_mcp_body",
]
