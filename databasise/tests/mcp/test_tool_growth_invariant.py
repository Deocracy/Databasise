"""05-07-PLAN.md Task 2: §18.5's selector-versus-tool rule, enforced. The tool surface is pinned
(``TOOL_NAMES``), registering a second modality is proven to add nothing, the forbidden-vocabulary
check is derived at run time rather than hardcoded, the AST proof over ``databasise/mcp/`` reuses
``test_rest_transport.py``'s own helper rather than duplicating it, and this phase's own
``COVERAGE.md`` is cross-checked against the code rather than trusted from memory.

See ``databasise/tests/mcp/test_dual_transport_parity.py``'s own module docstring for why this
directory carries no ``__init__.py`` — the identical reasoning applies to this file.
"""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

import pytest

# Deliberately NOT `pytest.importorskip("mcp")` — see test_dual_transport_parity.py's own module
# docstring: a bare `import mcp` can resolve to this project's own `databasise/mcp/` package
# (the CWD-shadow), so `importorskip` never sees the ImportError it needs to skip on when the real
# SDK is genuinely absent. Importing `databasise.mcp` directly reaches the real failure through
# its own CWD-shadow-safe init chain (`databasise.mcp._sdk.import_sdk`).
try:
    import databasise.mcp as mcp_package_module
except ImportError:
    pytest.skip("the `mcp` extra is not installed", allow_module_level=True)
from databasise.mcp import create_server
from databasise.mcp import server as mcp_server_module
from databasise.mcp import tools as mcp_tools_module
from databasise.mcp.tools import (
    TOOL_NAMES,
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
from databasise.parts.registry import default_registry
from databasise.parts.schema import Part
from databasise.seam import redact as redact_module
from databasise.seam import selectors as selectors_module
from databasise.seam.selectors import _ARM_NAMES as _PRODUCTION_ARM_NAMES
from databasise.tests._ast_helpers import called_names
from databasise.wirings.resolve import resolve_arm

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WIRINGS_ROOT = Path(__file__).resolve().parents[2] / "wirings"
_COVERAGE_PATH = (
    _REPO_ROOT / ".planning" / "phases" / "05-opaque-side-admission" / "COVERAGE.md"
)

_TOOL_ARG_MODELS = (
    IngestToolArgs,
    QueryToolArgs,
    DeleteToolArgs,
    StatusToolArgs,
    ResolveToolArgs,
    CompareToolArgs,
    PromoteToolArgs,
    RollbackToolArgs,
    RetireToolArgs,
)
_MCP_MODULES = (mcp_package_module, mcp_tools_module, mcp_server_module)


# --------------------------------------------------------------------------------------------- #
# A. The pinned surface.
# --------------------------------------------------------------------------------------------- #


async def test_the_registered_tool_set_equals_tool_names_as_a_set_and_by_count(tmp_path):
    server = create_server(store_root=tmp_path, workspace="growth-pin")
    names = [tool.name for tool in await server.list_tools()]
    assert set(names) == set(TOOL_NAMES)
    # 07-03-PLAN.md: grew from six to nine — `promote`/`rollback`/`retire` are three genuinely
    # new §18 operations, not one tool per modality (see databasise/mcp/tools.py's own module
    # docstring).
    assert len(names) == len(TOOL_NAMES) == 9


# --------------------------------------------------------------------------------------------- #
# B. The growth test, done for real — a second modality registered, the surface unchanged.
# --------------------------------------------------------------------------------------------- #


async def _second_modality_fixture_body(ctx):
    return {"node_id": ctx.node_id}


_SECOND_MODALITY_PART = Part(
    name_at_version="test-fixture/second-modality@1.0.0",
    kind="test-fixture-second-modality",
    structural_depth="opaque",
    effects=["reads_blob"],
    upstream_ref=None,
    body=_second_modality_fixture_body,
)

_SECOND_MODALITY_WIRING: dict = {
    "wiring_id": "second-modality-fixture",
    "wiring_version": "1",
    "nodes": {
        "second-modality-node": {
            "component": "test-fixture/second-modality@1.0.0",
            "kind": "test-fixture-second-modality",
            "effects": ["reads_blob"],
            "deps": [],
        }
    },
    "recipe": {},
    "harnesses": [],
    "provides": ["second-modality-node"],
}


async def test_registering_a_second_modality_leaves_the_tool_surface_byte_identical(tmp_path):
    registry_before = default_registry()
    keys_before = set(registry_before.keys())

    registry_after = default_registry()
    registry_after.register(_SECOND_MODALITY_PART)
    keys_after = set(registry_after.keys())

    # The registry must have genuinely grown — a test that asserts the surface is unchanged
    # without first changing the registry proves nothing (the plan's own acceptance criterion).
    assert keys_after > keys_before
    assert "test-fixture/second-modality@1.0.0" in keys_after - keys_before

    # And the new part is genuinely reachable through a §18.4 selector (capability), the same
    # override-candidates pattern test_selectors.py already uses for its own opaque fixture.
    resolved = selectors_module._resolve_capability(
        ["reads_blob"], registry=registry_after, candidates=[("second-modality-fixture", _SECOND_MODALITY_WIRING)]
    )
    assert resolved == _SECOND_MODALITY_WIRING

    server_before = create_server(store_root=tmp_path, workspace="growth-before", registry=registry_before)
    server_after = create_server(store_root=tmp_path, workspace="growth-after", registry=registry_after)

    names_before = sorted(tool.name for tool in await server_before.list_tools())
    names_after = sorted(tool.name for tool in await server_after.list_tools())

    assert names_before == names_after == sorted(TOOL_NAMES)


# --------------------------------------------------------------------------------------------- #
# C. The forbidden-vocabulary test — derived at run time, never hardcoded.
# --------------------------------------------------------------------------------------------- #


def _forbidden_vocabulary() -> set[str]:
    """Every registered part's own ``name_at_version``, every wiring id and node id reachable from
    ``databasise/wirings/`` (both the five production arms, resolved through ``resolve_arm`` so
    patches are applied, and every plain wiring JSON file), and any instance-hash-shaped value —
    derived live, never hand-restated, so a modality Phase 6 adds is checked automatically."""
    tokens: set[str] = set(default_registry().keys())

    for arm_name in _PRODUCTION_ARM_NAMES:
        resolved = resolve_arm(arm_name)
        wiring_id = resolved.get("wiring_id")
        if wiring_id:
            tokens.add(str(wiring_id))
        tokens.update(resolved.get("nodes", {}).keys())

    for json_path in _WIRINGS_ROOT.rglob("*.json"):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue  # a JSON Patch document (a list of ops), not a wiring dict — skip
        wiring_id = data.get("wiring_id")
        if wiring_id:
            tokens.add(str(wiring_id))
        nodes = data.get("nodes")
        if isinstance(nodes, dict):
            tokens.update(nodes.keys())

    return {token for token in tokens if token}


_INSTANCE_HASH_PATTERN = re.compile(r"^(sha256:)?[0-9a-f]{64}$", re.IGNORECASE)


def test_no_tool_name_or_argument_field_contains_a_forbidden_modality_or_identity_token():
    forbidden = _forbidden_vocabulary()
    haystacks = set(TOOL_NAMES)
    for model in _TOOL_ARG_MODELS:
        haystacks.update(model.model_fields.keys())

    for token in forbidden:
        lowered = token.lower()
        if not lowered:
            continue
        for haystack in haystacks:
            assert lowered not in haystack.lower(), (
                f"{haystack!r} contains forbidden modality/identity token {token!r}"
            )

    for haystack in haystacks:
        assert not _INSTANCE_HASH_PATTERN.match(haystack), (
            f"{haystack!r} is itself shaped like an internal instance hash"
        )


# --------------------------------------------------------------------------------------------- #
# D. The AST proof — reusing test_rest_transport.py's own shared helper, never a copy.
# --------------------------------------------------------------------------------------------- #


def test_databasise_mcp_calls_no_selector_resolution_redaction_or_envelope_assembly_function():
    forbidden = {"ResponseEnvelope"}
    forbidden.update(name for name in selectors_module.__all__ if name != "Selector")
    forbidden.update(redact_module.__all__)

    for module in _MCP_MODULES:
        called = called_names(inspect.getsource(module))
        overlap = called & forbidden
        assert not overlap, f"{module.__name__} calls forbidden seam-logic function(s): {overlap}"


def test_the_ast_helper_is_shared_with_test_rest_transport_not_duplicated():
    """Acceptance criterion: the same function object is used by ``test_rest_transport.py`` and
    this file — proven here by importing that module's own bound name (it imports
    ``called_names`` from ``databasise.tests._ast_helpers`` exactly as this file does) and
    asserting identity, not equality."""
    from databasise.tests.seam.test_rest_transport import (
        called_names as rest_transport_called_names,
    )

    assert rest_transport_called_names is called_names


# --------------------------------------------------------------------------------------------- #
# E. The coverage cross-check — this phase's own COVERAGE.md held equal to the code.
# --------------------------------------------------------------------------------------------- #

# A tool has no row of its own by name in COVERAGE.md's §18.5 operations table (its rows are named
# by *operation*, e.g. "job status (poll)") — this maps each such row to the tool(s) that reach it,
# declared once here so an added row or an added tool with no mapping fails loudly rather than
# silently passing.
_OPERATION_TO_TOOLS: dict[str, tuple[str, ...]] = {
    "query (non-streaming)": ("query",),
    "query (streaming, SSE)": ("query",),
    "evidence dereference": ("resolve",),
    "trace resolution": ("resolve",),
    "ingest (structured text + raw upload)": ("ingest",),
    "job status (poll)": ("status",),
    "delete document": ("delete",),
    "health": ("status",),
    "corpus status (paginated)": ("status",),
    "document counts": ("status",),
    "compare": ("compare",),
    "promote": ("promote",),
    "rollback": ("rollback",),
    "retire": ("retire",),
}


def _parse_markdown_table(markdown: str, header_prefix: str) -> list[list[str]]:
    """A minimal markdown-table parser: finds the first row starting with ``header_prefix``,
    skips the separator row beneath it, and returns every subsequent ``|``-delimited row (cells
    stripped) until a line that is no longer part of the table."""
    lines = markdown.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip().startswith(header_prefix)), None)
    assert start is not None, f"COVERAGE.md table starting {header_prefix!r} not found"

    rows: list[list[str]] = []
    for line in lines[start + 2 :]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            break
        rows.append([cell.strip() for cell in stripped.strip("|").split("|")])
    return rows


def test_every_tool_has_a_coverage_row_and_every_both_transport_row_has_a_tool():
    """Every row in COVERAGE.md's §18.5 operations table maps to a known tool (or is deliberately
    tool-less, e.g. streaming — no MCP analog in this milestone), and every one of ``TOOL_NAMES``
    is reachable from at least one row whose ``transports`` column names ``MCP``."""
    markdown = _COVERAGE_PATH.read_text(encoding="utf-8")
    rows = _parse_markdown_table(markdown, "| operation | transports | plan |")
    assert rows, "no operations rows parsed from COVERAGE.md's §18.5 table"

    covered_tools: set[str] = set()
    for operation, transports, *_rest in rows:
        matched = next(
            (tools for key, tools in _OPERATION_TO_TOOLS.items() if key in operation), None
        )
        assert matched is not None, (
            f"COVERAGE.md operation row {operation!r} has no entry in _OPERATION_TO_TOOLS — "
            "update the mapping"
        )
        if "MCP" in transports:
            covered_tools.update(matched)

    assert covered_tools == set(TOOL_NAMES)


def test_compare_is_present_in_tool_names_and_absent_from_the_deliberately_absent_table():
    """06-03-PLAN.md landed `compare`: it is now present in `TOOL_NAMES` and its row moved out of
    COVERAGE.md's "deliberately absent" table into the §18.5 operations table (asserted by
    `test_every_tool_has_a_coverage_row_and_every_both_transport_row_has_a_tool` above) — the
    record and the code must state the same, current thing, never the retired Phase-5 state this
    test asserted before this plan."""
    markdown = _COVERAGE_PATH.read_text(encoding="utf-8")
    absent_rows = _parse_markdown_table(markdown, "| operation | decision | reason |")

    for operation, *_rest in absent_rows:
        assert "compare" not in operation.lower(), (
            "COVERAGE.md still lists `compare` as a deliberately absent operation, but it is "
            "present in TOOL_NAMES — the record and the code disagree"
        )

    assert "compare" in TOOL_NAMES
