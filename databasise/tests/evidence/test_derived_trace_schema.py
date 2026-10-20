"""D-12 (13-03-PLAN.md): the Databasise derived trace schema is the frozen
``docs/system-model/rig-trace.schema.json`` plus exactly the declared amendments, each recorded as
a RIG §R-form row in ``databasise/evidence/RIG-TRACE-DEVIATIONS.md``. The frozen schema and RIG.md
are never edited.

``AMENDMENTS`` is the single declared list (RFC 6902). The derived file must equal the frozen file
with it applied, so a silent edit to either file fails here.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import jsonpatch

_REPO = Path(__file__).resolve().parents[3]
_FROZEN = _REPO / "docs" / "system-model" / "rig-trace.schema.json"
_DERIVED = _REPO / "databasise" / "evidence" / "rig-trace.databasise.schema.json"
_RECORD = _REPO / "databasise" / "evidence" / "RIG-TRACE-DEVIATIONS.md"

_NODE = "/$defs/NodeTrace"
_REASON_CODES = [
    "node_failed",
    "placement_refused",
    "budget_halt",
    "cancelled",
    "declared_fallback",
    "fallback_path_taken",
    None,
]
_TIER_ENUM = ["T0", "T1", "T2", "T3", None]

AMENDMENTS: list[dict[str, Any]] = [
    {
        "op": "replace",
        "path": "/$id",
        "value": "https://databasise.local/evidence/rig-trace.databasise.schema.json",
    },
    {"op": "replace", "path": "/title", "value": "Databasise derived run trace record"},
    {
        "op": "replace",
        "path": "/description",
        "value": (
            "The Databasise derived run trace schema: docs/system-model/rig-trace.schema.json "
            "(frozen, unedited) plus the declared amendments in "
            "databasise/evidence/RIG-TRACE-DEVIATIONS.md, one row per amendment. A divergence from "
            "the frozen shape is recorded there, never resolved silently in this file alone."
        ),
    },
    {
        "op": "replace",
        "path": f"{_NODE}/properties/cache_hit",
        "value": {
            "type": ["boolean", "null"],
            "description": (
                "Per CONTRACT.md §5's D7 repair — arm execution order and per-node cache hit/miss "
                "MUST be stamped on the run record. Null where the part reported none."
            ),
        },
    },
    {
        "op": "replace",
        "path": f"{_NODE}/properties/tier",
        "value": {
            "type": ["string", "null"],
            "enum": _TIER_ENUM,
            "description": (
                "CONTRACT.md §4's evidence-item tier, machine-stamped from what arrived at the "
                "boundary. Null where no evidence-tier machinery measured it."
            ),
        },
    },
    {
        "op": "replace",
        "path": f"{_NODE}/properties/feed_tier",
        "value": {
            "type": ["string", "null"],
            "enum": _TIER_ENUM,
            "description": (
                "The tier this node's output feeds forward as, a pooling-key member alongside tier "
                "per CONTRACT.md §4. Null where no evidence-tier machinery measured it."
            ),
        },
    },
    {
        "op": "add",
        "path": f"{_NODE}/properties/status",
        "value": {
            "type": "string",
            "enum": ["completed", "failed", "cancelled", "not-scheduled"],
            "description": (
                "What became of this node in the run: it completed, it failed, it was cancelled "
                "with its batch, or it was never scheduled."
            ),
        },
    },
    {
        "op": "add",
        "path": f"{_NODE}/properties/execution_mode",
        "value": {
            "type": "string",
            "enum": ["in-process", "subprocess", "confined-unit", "long-lived-service"],
            "description": (
                "CONTRACT.md §3's derived placement, stamped whether or not the placement was hosted."
            ),
        },
    },
    {
        "op": "add",
        "path": f"{_NODE}/properties/spent",
        "value": {
            "type": ["integer", "null"],
            "minimum": 0,
            "description": "Metered token spend at this node's boundary; null where the node never completed.",
        },
    },
    {
        "op": "add",
        "path": f"{_NODE}/properties/allowance",
        "value": {
            "type": ["integer", "null"],
            "minimum": 0,
            "description": "The token allowance this node was handed; null where the node was never handed one.",
        },
    },
    {
        "op": "replace",
        "path": f"{_NODE}/required",
        "value": [
            "node_id",
            "instance_hash",
            "depth",
            "effective_depth",
            "tier",
            "feed_tier",
            "wall_clock_ms",
            "cache_hit",
            "guards_fired",
            "budget_state",
            "realised_budget_share",
            "cross_process_failure_cause",
            "resumable",
            "tokens",
            "status",
            "execution_mode",
            "spent",
            "allowance",
        ],
    },
    {
        "op": "replace",
        "path": "/properties/stop_reason",
        "value": {"type": ["string", "null"], "enum": _REASON_CODES},
    },
    {
        "op": "replace",
        "path": "/properties/degradation_reason",
        "value": {"type": ["string", "null"], "enum": _REASON_CODES},
    },
]

_SECTION_R_HEADER = [
    "#",
    "Clause",
    "Defect",
    "Repair direction",
    "Forcing requirement",
    "ANATOMY re-projection",
    "Status",
]


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _table_rows() -> list[list[str]]:
    """Every markdown table row of the record as a list of stripped cells (header first)."""
    try:
        text = _RECORD.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 - asserted on below
        raise AssertionError(f"the deviation record could not be read: {type(exc).__name__}") from None
    rows = []
    for line in text.splitlines():
        if line.startswith("|") and not re.match(r"^\|[\s:|-]+\|$", line):
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return rows


def test_the_derived_schema_is_the_frozen_schema_plus_the_declared_amendments():
    try:
        derived = _load(_DERIVED)
    except Exception as exc:  # noqa: BLE001 - asserted on below
        derived = None
        error = type(exc).__name__
    assert derived is not None, f"the derived schema could not be loaded: {error}"

    assert jsonpatch.apply_patch(_load(_FROZEN), AMENDMENTS) == derived


def test_every_amendment_has_a_deviation_row():
    rows = _table_rows()
    assert len(rows) > 1, "the deviation record has no table"
    pointers_in_rows = set()
    for row in rows[1:]:
        pointers_in_rows.update(re.findall(r"`(/[^`]+)`", row[1]))
    amended = {op["path"] for op in AMENDMENTS}

    assert amended - pointers_in_rows == set(), "amendments without a deviation row"
    assert pointers_in_rows - amended == set(), "deviation rows without an amendment"


def test_the_deviation_record_uses_the_rig_section_r_columns():
    rows = _table_rows()
    assert rows[0] == _SECTION_R_HEADER
    body = rows[1:]
    assert body, "the deviation record has no rows"
    for row in body:
        assert len(row) == len(_SECTION_R_HEADER), row
        assert all(cell for cell in row), f"empty cell in {row}"
        assert row[-1] == "recorded, no amendment", row


def test_the_frozen_files_are_unedited():
    result = subprocess.run(
        [
            "git",
            "-C",
            str(_REPO),
            "diff",
            "--quiet",
            "HEAD",
            "--",
            "docs/system-model/rig-trace.schema.json",
            "docs/system-model/RIG.md",
        ],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, "a frozen docs/system-model file differs from HEAD (D-12)"
