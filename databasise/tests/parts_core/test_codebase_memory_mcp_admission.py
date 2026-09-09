"""05-06-PLAN.md Tasks 1 and 2: the second, differently-shaped foreign engine's adapter (process
lifecycle, RPC, health, evidence normalization) and its §8 admission record (the eleven verdicts
as executable data, the measured ceiling, the version drift). One test per ``<behavior>`` bullet
in each task, guarded by ``pytest.mark.skipif`` for every live-engine test — every skip names the
missing binary explicitly, per the plan's own ``<precondition>``. The normalization tests run
without the binary, against captured raw payloads recorded from a real run
(``tests/fixtures/codebase_memory_mcp_raw_items.json``), so the typing rules stay tested even where
the engine is absent.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest
from databasise.foreign import codebase_memory_mcp_adapter as adapter
from databasise.parts.admission import cross_check_conditions, validate_admission
from databasise.parts.registry import PartRegistry, default_registry
from databasise.parts_core.codebase_memory_mcp import (
    CBM_KNOWN_TOOL_NAMES,
    CBM_MEASURED_INDEX_DURATION_SECONDS,
    CBM_WALL_CLOCK_CEILING_SECONDS,
    CODEBASE_MEMORY_MCP_ADMISSION,
)
from databasise.parts_core.declared_only import CODEBASE_MEMORY_MCP_PART

_FIXTURES_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "codebase_memory_mcp_raw_items.json"
_RAW_FIXTURES: dict[str, list[dict]] = json.loads(_FIXTURES_PATH.read_text(encoding="utf-8"))

_WIRING_PATH = Path(__file__).resolve().parents[2] / "wirings" / "codebase-memory-mcp.json"

# A live-engine test needs both the binary AND the `mcp` extra (databasise's own optional
# dependency, lazily imported by the adapter — see that module's own docstring/comment for why).
# Checking only the binary would let this skip fall through to a bare ModuleNotFoundError on a
# `uv run pytest -q` with no extras installed but the binary present on PATH.
_MCP_INSTALLED = importlib.util.find_spec("mcp") is not None
_NO_LIVE_ENGINE_REASON = (
    f"codebase-memory-mcp binary not found (DEFAULT_CBM_BINARY={adapter.DEFAULT_CBM_BINARY!r}) "
    f"or the 'mcp' extra is not installed (found={_MCP_INSTALLED}); install the binary and run "
    "`uv sync --extra mcp`"
)
_skip_without_binary = pytest.mark.skipif(
    adapter.DEFAULT_CBM_BINARY is None or not _MCP_INSTALLED, reason=_NO_LIVE_ENGINE_REASON
)
_skip_without_mcp = pytest.mark.skipif(
    not _MCP_INSTALLED, reason="the 'mcp' extra is not installed; run `uv sync --extra mcp`"
)


# ---------------------------------------------------------------------------
# Task 1: the adapter — process lifecycle, RPC, health, evidence normalization
# ---------------------------------------------------------------------------


@_skip_without_binary
def test_list_tools_against_the_live_engine_returns_the_engines_own_nonempty_tool_name_list():
    """The adapter never hardcodes tool names — it reads them live from the running engine."""
    tools = adapter.list_tools(timeout=60.0)
    names = sorted(tool["name"] for tool in tools)
    assert names
    assert names == sorted(CBM_KNOWN_TOOL_NAMES)


@_skip_without_binary
def test_call_tool_against_the_live_engine_returns_the_tools_result():
    items = adapter.call_tool("list_projects", {}, timeout=60.0)
    assert isinstance(items, list)
    assert items
    assert isinstance(items[0], dict)


@_skip_without_binary
def test_a_timeout_raises_a_named_refusal_carrying_the_tool_name_and_ceiling():
    with pytest.raises(adapter.CbmToolTimeoutError) as exc_info:
        adapter.call_tool("index_repository", {"repo_path": str(Path(__file__).resolve().parents[2])}, timeout=0.01)
    assert exc_info.value.tool_name == "index_repository"
    assert exc_info.value.timeout == 0.01


def test_a_nonexistent_binary_raises_foreign_engine_unavailable_error_naming_the_resolved_path():
    with pytest.raises(adapter.ForeignEngineUnavailableError) as exc_info:
        adapter.list_tools(binary="/nonexistent/definitely-not-a-real-binary", timeout=5.0)
    assert exc_info.value.attempted == "/nonexistent/definitely-not-a-real-binary"


@_skip_without_binary
def test_the_adapter_terminates_the_child_process_on_both_the_success_and_the_failure_path():
    """Provokes a timeout, then a success, then confirms no ``codebase-memory-mcp`` process this
    test process itself launched remains — counts only *direct children of this test process*
    (``pgrep -P <our pid>``), never a bare global count, since unrelated ``codebase-memory-mcp``
    instances may legitimately be running elsewhere on a developer machine at the same time."""

    def _own_child_count() -> int:
        result = subprocess.run(
            ["pgrep", "-P", str(os.getpid()), "-fc", "codebase-memory-mcp"],
            capture_output=True,
            text=True,
        )
        return int(result.stdout.strip() or "0")

    with pytest.raises(adapter.CbmToolTimeoutError):
        adapter.call_tool(
            "index_repository", {"repo_path": str(Path(__file__).resolve().parents[2])}, timeout=0.01
        )
    assert _own_child_count() == 0

    adapter.call_tool("list_projects", {}, timeout=60.0)
    assert _own_child_count() == 0


@_skip_without_mcp
def test_a_transport_failure_refusal_carries_both_endpoint_placements():
    """A binary that resolves and launches, but is not a real MCP server, fails during the
    handshake — a genuine cross-process transport failure, not a timeout and not an unresolved
    binary."""
    import shutil

    false_binary = shutil.which("false")
    if not false_binary:
        pytest.skip("no 'false' binary on PATH to use as a non-MCP-speaking process")

    with pytest.raises(adapter.CbmTransportError) as exc_info:
        adapter.list_tools(binary=false_binary, timeout=10.0)
    assert exc_info.value.tool_name == "list_tools"
    assert exc_info.value.cause
    assert "this process" in exc_info.value.machine_endpoint
    assert false_binary in exc_info.value.foreign_endpoint


def test_the_adapter_module_holds_no_admission_data():
    source = Path(adapter.__file__).read_text(encoding="utf-8")
    for forbidden in ("ConditionVerdict", "AdmissionRecord", "wall_clock_ceiling"):
        assert forbidden not in source


@pytest.mark.parametrize("tool_name", sorted(_RAW_FIXTURES.keys()))
def test_normalise_to_item_kind_maps_every_fixture_tool_to_a_seven_member_kind(tool_name):
    seven_members = {
        adapter.ITEM_KIND_CODE_SNIPPET,
        adapter.ITEM_KIND_GRAPH_PATH,
        adapter.ITEM_KIND_DERIVED_FINDING,
        "text_chunk",
        "fact_with_validity_interval",
        "page_image_ref",
        "sql_result_set",
    }
    for raw_item in _RAW_FIXTURES[tool_name]:
        record = adapter.normalise_to_item_kind(raw_item, tool_name)
        assert record["kind"] in seven_members
        assert record["tool_name"] == tool_name


def test_normalise_to_item_kind_raises_untyped_for_a_non_evidence_tool_name():
    with pytest.raises(adapter.UntypedForeignItemError) as exc_info:
        adapter.normalise_to_item_kind({"project": "x", "status": "ok"}, "manage_adr")
    assert exc_info.value.tool_name == "manage_adr"
    assert exc_info.value.item_keys == ["project", "status"]


def test_the_untyped_item_refusal_names_the_tool_and_the_offending_items_own_keys():
    for mutating_tool in ("delete_project", "manage_adr", "ingest_traces", "index_repository"):
        with pytest.raises(adapter.UntypedForeignItemError) as exc_info:
            adapter.normalise_to_item_kind({"a": 1, "b": 2}, mutating_tool)
        assert exc_info.value.tool_name == mutating_tool
        assert exc_info.value.item_keys == ["a", "b"]


def test_a_ref_the_adapter_cannot_resolve_is_tier_capped_below_t1():
    for tool_name, raw_items in _RAW_FIXTURES.items():
        for raw_item in raw_items:
            record = adapter.normalise_to_item_kind(raw_item, tool_name)
            assert record["tier"] == "below_T1"
            assert record["tier_reason"]


def test_get_code_snippet_fixture_derives_a_content_hash_from_its_own_source_field():
    records = [
        adapter.normalise_to_item_kind(item, "get_code_snippet")
        for item in _RAW_FIXTURES["get_code_snippet"]
    ]
    assert any(record["ref"] and record["ref"]["chunk_ref"]["content_hash"] for record in records)


async def test_a_cross_process_failure_is_recorded_on_the_nodes_trace_never_silently_dropped(monkeypatch):
    """§17's health-and-lifecycle rule, exercised end to end through the real scheduler: an
    interrupted/failed foreign-engine call must record the placement of both endpoints and the
    failure cause on the node's own trace, labeled halted per §9 — never silently dropped from the
    record. Monkeypatches ``codebase_memory_mcp.call_tool`` (the name that module actually calls)
    to raise a real ``CbmTransportError``, and drives the real, unmodified
    ``codebase-memory-mcp@0.1.0`` Part through ``parse_wiring``/``run_wiring`` — the same path
    ``databasise/wirings/codebase-memory-mcp.json`` resolves against."""
    import databasise.parts_core.codebase_memory_mcp as cbm_module
    from databasise.runner import scheduler as _scheduler
    from databasise.validator.parse import parse_wiring

    def _raise_transport_error(*args, **kwargs):
        raise adapter.CbmTransportError(
            tool_name="list_projects",
            cause="simulated cross-process failure",
            machine_endpoint="databasise.foreign.codebase_memory_mcp_adapter (this process)",
            foreign_endpoint="codebase-memory-mcp subprocess (/simulated/broken/path)",
        )

    monkeypatch.setattr(cbm_module, "call_tool", _raise_transport_error)

    registry = default_registry()
    wiring = json.loads(_WIRING_PATH.read_text(encoding="utf-8"))
    wiring["nodes"]["cbm"]["config"] = {"tool": "list_projects", "arguments": {}}

    parsed = parse_wiring(wiring, registry)
    assert parsed.report.ok, [v.code for v in parsed.report.violations]

    scheduled = await _scheduler.run_wiring(
        parsed, registry, stores={}, determinism_setting="cache-bypassed", concurrency_setting="sequential"
    )

    assert scheduled["degraded"] is True
    cbm_trace = next(node for node in scheduled["nodes"] if node.node_id == "cbm")
    assert cbm_trace.budget_state == "halted"
    assert cbm_trace.cross_process_failure_cause is not None
    assert "this process" in cbm_trace.cross_process_failure_cause
    assert "/simulated/broken/path" in cbm_trace.cross_process_failure_cause
    assert isinstance(scheduled["node_exceptions"]["cbm"], adapter.CbmTransportError)


# ---------------------------------------------------------------------------
# Task 2: the eleven verdicts as executable data, the measured ceiling, the version drift
# ---------------------------------------------------------------------------


def test_the_admission_record_carries_exactly_eleven_verdicts_each_citing_parts_md_section_x():
    verdicts = CODEBASE_MEMORY_MCP_ADMISSION.verdicts
    assert sorted(v.condition for v in verdicts) == list(range(1, 12))
    for verdict in verdicts:
        assert verdict.evidence.strip()
        assert "§X" in verdict.evidence or "PARTS.md" in verdict.evidence


def test_the_verdict_vocabulary_contains_a_non_satisfied_value_in_use():
    """§X says three of the eleven rows are not clean yeses — if all eleven read 'satisfied', this
    test must fail."""
    verdicts = {v.condition: v.verdict for v in CODEBASE_MEMORY_MCP_ADMISSION.verdicts}
    assert verdicts[1] != "satisfied"
    assert verdicts[3] == "open-question"
    assert verdicts[7] == "machine-side-obligation"
    assert verdicts[8] == "machine-side-obligation"
    assert verdicts[9] == "machine-side-obligation"
    assert len({v.verdict for v in CODEBASE_MEMORY_MCP_ADMISSION.verdicts}) > 1


def test_condition_3_names_the_r_row_n12_open_question_and_the_no_isolation_scope_decision():
    record = CODEBASE_MEMORY_MCP_ADMISSION
    assert "N12" in record.network_namespace
    assert "no OS-level" in record.network_namespace or "No OS-level" in record.network_namespace


def test_conditions_seven_eight_and_nine_carry_no_source_evidence_either_way():
    verdicts = {v.condition: v for v in CODEBASE_MEMORY_MCP_ADMISSION.verdicts}
    for condition in (7, 8, 9):
        assert verdicts[condition].verdict == "machine-side-obligation"


def test_the_ceiling_is_strictly_greater_than_the_measured_duration_and_the_basis_names_it():
    assert CBM_WALL_CLOCK_CEILING_SECONDS > CBM_MEASURED_INDEX_DURATION_SECONDS
    assert str(CBM_MEASURED_INDEX_DURATION_SECONDS) in CODEBASE_MEMORY_MCP_ADMISSION.wall_clock_ceiling_basis


def test_the_effects_gain_mutates_store_additively_and_keep_self_storage_and_fs():
    assert set(CODEBASE_MEMORY_MCP_PART.effects) == {"self_storage", "fs", "mutates_store"}
    assert CODEBASE_MEMORY_MCP_PART.artifact_scope == "self_storage"


def test_registering_the_part_succeeds_and_validate_admission_and_cross_check_conditions_pass():
    registry = default_registry()
    validate_admission(CODEBASE_MEMORY_MCP_PART, CODEBASE_MEMORY_MCP_PART.admission)

    wiring = json.loads(_WIRING_PATH.read_text(encoding="utf-8"))
    cross_check_conditions(
        CODEBASE_MEMORY_MCP_PART,
        CODEBASE_MEMORY_MCP_PART.admission,
        registry=registry,
        resolved_wiring=wiring,
    )

    fresh_registry = PartRegistry(seed_tracer_parts=False)
    fresh_registry.register(CODEBASE_MEMORY_MCP_PART)
    assert fresh_registry.get(CODEBASE_MEMORY_MCP_PART.name_at_version) is CODEBASE_MEMORY_MCP_PART


@_skip_without_binary
def test_the_live_tool_surface_matches_the_admission_records_known_tool_names():
    live_names = sorted(tool["name"] for tool in adapter.list_tools(timeout=60.0))
    assert live_names == sorted(CBM_KNOWN_TOOL_NAMES)


def test_falsifier2_evidence_for_w2_codebase_memory_mcp_is_regenerated_not_hand_edited():
    """``databasise/evidence/falsifier2.py``'s regenerated output must be byte-identical to the
    committed document — the effects-change repaired above changed the rendered row, so this
    proves the document was regenerated by running the script, never hand-edited to match."""
    from databasise.evidence.falsifier2 import EVIDENCE_PATH, render_markdown

    committed = EVIDENCE_PATH.read_text(encoding="utf-8")
    fresh = render_markdown()
    assert committed == fresh
    assert "mutates_store" in committed
