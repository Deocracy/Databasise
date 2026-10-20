"""13-09-PLAN.md (WIRE-09, D-20): the LightRAG keyword fall-through guards are removed.

``resolve_arm`` applies only a patch's ``operations``, so the top-level ``guards`` arrays in the
local and global arm patches were declarations nothing evaluated. D-20 removes them (and the
documentation claiming them); node-level ``config.guards`` (HippoRAG) is read by the scheduler
and stays.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import jsonpatch

from databasise.wirings.resolve import load_base, resolve_arm

_WIRINGS = Path(__file__).resolve().parents[2] / "wirings"


def _digest(doc: object) -> str:
    return hashlib.sha256(json.dumps(doc, sort_keys=True).encode("utf-8")).hexdigest()


def test_no_wiring_file_has_a_top_level_guards_key() -> None:
    offenders = []
    for path in sorted(_WIRINGS.rglob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and "guards" in doc:
            offenders.append(str(path.relative_to(_WIRINGS)))
    assert offenders == [], f"top-level guards arrays nothing evaluates: {offenders}"


def test_node_level_guards_stay_legitimate() -> None:
    base = json.loads((_WIRINGS / "hipporag" / "base.json").read_text(encoding="utf-8"))
    nodes = base["nodes"]
    for node_id in ("fact-filter", "assemble-result"):
        assert nodes[node_id]["config"].get("guards"), f"{node_id} lost its config.guards"


def test_the_resolved_local_and_global_arms_are_unchanged() -> None:
    for arm in ("local", "global"):
        patch_doc = json.loads((_WIRINGS / "lightrag" / f"arm-{arm}.json-patch.json").read_text(encoding="utf-8"))
        expected = jsonpatch.apply_patch(load_base(), patch_doc["operations"], in_place=False)
        assert _digest(resolve_arm(arm)) == _digest(expected), arm
        assert set(resolve_arm(arm)["nodes"]) == set(patch_doc["resulting_node_id_set"]), arm
