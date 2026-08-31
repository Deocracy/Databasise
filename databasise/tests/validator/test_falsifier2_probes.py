"""The self-declaration and blast-radius probe suite (``databasise.evidence.falsifier2.PROBES``):
SELECTION.md Falsifier 1 limb (b) — the opaque-fed extractor's shared write must be refused — and
Falsifier 2's own no-self-declaration clause (02-CONTEXT.md D-03). Every refusal probe is paired
with a control that must not fire, so a check that has stopped firing surfaces here as a failed
test rather than as a quietly green suite. Asserts against the observed violation codes ``parse_wiring``
actually produces, resolved against ``probe_registry()`` — never against the production
``default_registry()``, which must never carry either probe-only part.
"""

from __future__ import annotations

import pytest

from databasise.evidence.falsifier2 import (
    EVIDENCE_WRITER_PROBE_PART,
    PROBES,
    SHARED_ARTIFACT_WRITER_PROBE_PART,
    probe_registry,
)
from databasise.parts.registry import default_registry
from databasise.validator.depth import effective_depth
from databasise.validator.parse import parse_wiring


def test_probe_case_table_has_at_least_seven_entries():
    """Meta-test: the probe suite carries all seven named probes (a, b1-b3, c1-c3)."""
    assert len(PROBES) >= 7


@pytest.mark.parametrize("probe", PROBES, ids=[p.probe_id for p in PROBES])
def test_probe_matches_its_expected_code_exactly(probe):
    """A control probe (``expected_code is None``) validates clean with zero violations; a
    refusal probe validates not-``ok`` with its expected code present among the observed codes.
    """
    parsed = parse_wiring(probe.doc, probe_registry())
    if probe.expected_code is None:
        assert parsed.report.ok is True
        assert parsed.report.violations == []
    else:
        assert parsed.report.ok is False
        observed_codes = {v.code for v in parsed.report.violations}
        assert probe.expected_code in observed_codes


def test_b3_blast_radius_refusal_names_the_downstream_extractor_node():
    """SELECTION.md Falsifier 1 limb (b): the opaque ``cbm`` node taints its downstream
    ``extract`` node to effective depth ``opaque``; the resulting blast-radius refusal must name
    ``extract`` (the node attempting the shared write), not ``cbm``.
    """
    probe = next(p for p in PROBES if p.probe_id == "b3-shared-write-tainted-to-opaque")
    parsed = parse_wiring(probe.doc, probe_registry())
    refusals = [v for v in parsed.report.violations if v.code == probe.expected_code]
    assert len(refusals) == 1
    assert refusals[0].pointer.split("/")[2] == "extract"
    assert "extract" in refusals[0].message


def test_c3_computes_query_side_effective_depth_opaque():
    """The control for the self-declaration pair: W3 unmodified still computes ``query-side``'s
    effective_depth as ``opaque`` (taint from the opaque ``ingest`` node) purely from wiring +
    registry — the computation governs whether or not an author ever attempts to state it.
    """
    probe = next(p for p in PROBES if p.probe_id == "c3-computed-depth-governs")
    parsed = parse_wiring(probe.doc, probe_registry())
    depths = effective_depth(parsed)
    assert depths["query-side"] == "opaque"


def test_probe_only_parts_never_leak_into_the_production_registry():
    """``probe_registry()`` is assembled fresh per call from ``default_registry()`` plus the two
    probe-only parts; the production ``default_registry()`` itself must never carry either one,
    so evidence about refusals never widens the machine's real capability surface.
    """
    keys = default_registry().keys()
    assert SHARED_ARTIFACT_WRITER_PROBE_PART.name_at_version not in keys
    assert EVIDENCE_WRITER_PROBE_PART.name_at_version not in keys
