"""LEDG-11 (Phase 14, D-12): a wiring node whose kind differs from its registered Part's kind is
reported by name, and every shipped wiring parses clean.

"Raises" in the row text means this named report: ``parse_wiring`` reports violations and never
raises. Self-contained and limited to names that exist at 5d61a79^, so it can be run there to show
the failing-first state (the code is compared as a literal string for the same reason).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import databasise.wirings
from databasise.parts.registry import default_registry
from databasise.validator.parse import parse_wiring
from databasise.wirings.resolve import all_wirings, load_base

_WIRINGS_DIR = Path(databasise.wirings.__file__).parent


def test_a_kind_mismatch_is_reported_by_name():
    registry = default_registry()
    doc = copy.deepcopy(load_base())
    component = doc["nodes"]["keywords"]["component"]
    part_kind = registry.get(component).kind
    assert part_kind != "assembler", "pick a different wrong kind: the fixture matches the part"
    doc["nodes"]["keywords"]["kind"] = "assembler"

    try:
        report = parse_wiring(doc, registry).report
    except Exception as caught:  # noqa: BLE001 - the report, not a raise, is the contract
        raise AssertionError(f"parse_wiring raised {type(caught).__name__}: {caught}") from caught

    mismatches = [v for v in report.violations if v.code == "kind-mismatch"]
    assert mismatches, f"no kind-mismatch violation; got {[v.code for v in report.violations]}"
    violation = mismatches[0]
    assert violation.pointer.endswith("/kind"), violation.pointer
    for name in ("keywords", "assembler", part_kind):
        assert name in violation.message, f"{name!r} missing from {violation.message!r}"


def test_every_shipped_wiring_parses():
    registry = default_registry()
    documents = [
        (str(path.relative_to(_WIRINGS_DIR)), json.loads(path.read_text()))
        for path in sorted(_WIRINGS_DIR.rglob("*.json"))
    ]
    # An "operations" document is an arm patch, not a wiring.
    documents = [(name, doc) for name, doc in documents if "operations" not in doc]
    documents += [(f"all_wirings()[{name}]", doc) for name, doc in all_wirings()]
    assert documents, "no wiring documents found"
    for name, doc in documents:
        codes = [(v.code, v.pointer) for v in parse_wiring(doc, registry).report.violations]
        assert not codes, f"{name} does not parse: {codes}"
