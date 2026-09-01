"""Criterion 1's own conformance test: the unpatched ``mix`` base parses clean, and each of the
five arms (``naive``, ``bypass``, ``hybrid``, ``local``, ``global``) resolves to exactly the node
id set its own committed patch file declares in ``resulting_node_id_set``, parses clean, and
computes the expected ``execution_mode``/``effective_depth`` — over the real validator functions
(``databasise.validator.depth.effective_depth``, ``databasise.validator.execution_mode.
derive_execution_mode``, ``databasise.validator.blast_radius.blast_radius_violations``), never a
reimplementation, exactly the discipline ``databasise/evidence/falsifier2.py`` already follows for
the committed Falsifier 2 evidence.

Until 03-06-PLAN.md landed, the unpatched base could not even parse (eleven of its eighteen
components were unregistered) — this is the first plan where criterion 1 is checkable in full,
independent of any arm.
"""

from __future__ import annotations

from databasise.parts.registry import default_registry
from databasise.validator.blast_radius import blast_radius_violations
from databasise.validator.depth import effective_depth
from databasise.validator.execution_mode import derive_execution_mode
from databasise.validator.parse import ParsedWiring, parse_wiring
from databasise.wirings.resolve import declared_node_ids, load_base, resolve_arm

_ARM_NAMES: tuple[str, ...] = ("naive", "bypass", "hybrid", "local", "global")

# §L.1's eighteen published base-wiring positions (databasise/wirings/lightrag/base.json's own
# eighteen `nodes` keys) — the count criterion 1 checks the union below against.
_EIGHTEEN_POSITIONS = frozenset(load_base()["nodes"].keys())


def _parse(doc: dict) -> ParsedWiring:
    return parse_wiring(doc, default_registry())


def test_the_base_wiring_declares_exactly_eighteen_positions():
    """Sanity precondition for the union assertion below — not itself criterion 1's check, but a
    named guard so a wiring edit that silently changes the position count fails loudly here rather
    than corrupting the union assertion's own expected number.
    """
    assert len(_EIGHTEEN_POSITIONS) == 18


def test_the_unpatched_mix_base_parses_with_zero_violations():
    parsed = _parse(load_base())
    assert parsed.report.ok, [v.code for v in parsed.report.violations]


def test_every_arm_resolves_to_exactly_its_own_published_node_id_set():
    for arm_name in _ARM_NAMES:
        resolved = _parse(resolve_arm(arm_name))
        assert set(resolved.nodes.keys()) == set(declared_node_ids(arm_name)), arm_name


def test_every_arm_parses_with_zero_violations():
    for arm_name in _ARM_NAMES:
        parsed = _parse(resolve_arm(arm_name))
        assert parsed.report.ok, (arm_name, [v.code for v in parsed.report.violations])


def test_every_node_in_the_base_and_every_arm_derives_in_process_execution_mode():
    for doc in (load_base(), *(resolve_arm(name) for name in _ARM_NAMES)):
        parsed = _parse(doc)
        for node_id, part in parsed.parts.items():
            mode = derive_execution_mode(part.effects, part.kind)
            assert mode == "in-process", (node_id, mode)


def test_every_node_effective_depth_is_stage_except_embedder_index_which_is_opaque():
    for doc in (load_base(), *(resolve_arm(name) for name in _ARM_NAMES)):
        parsed = _parse(doc)
        depths = effective_depth(parsed)
        for node_id, depth in depths.items():
            expected = "opaque" if node_id == "embedder-index" else "stage"
            assert depth == expected, (node_id, depth)


def test_blast_radius_reports_nothing_for_the_base_or_any_arm():
    for doc in (load_base(), *(resolve_arm(name) for name in _ARM_NAMES)):
        parsed = _parse(doc)
        depths = effective_depth(parsed)
        assert blast_radius_violations(parsed, depths) == []


def test_the_union_of_node_ids_across_all_five_arms_plus_the_base_equals_the_eighteen_positions():
    ids: set[str] = set(load_base()["nodes"].keys())
    for arm_name in _ARM_NAMES:
        ids |= set(declared_node_ids(arm_name))
    assert ids == _EIGHTEEN_POSITIONS


def test_the_success_line_the_plans_acceptance_criteria_names():
    """Mirrors 03-06-PLAN.md Task 3's own acceptance-criteria script verbatim (as a pytest case
    rather than a standalone ``python -c`` invocation) — the ``mix`` arm re-uses the already-parsed
    base rather than resolving a nonexistent ``arm-mix`` patch file, exactly as the plan's own
    script does.
    """
    registry = default_registry()
    r = parse_wiring(load_base(), registry)
    assert r.report.ok, [v.code for v in r.report.violations]
    ids: set[str] = set()
    for arm in ("mix", "hybrid", "local", "global", "naive", "bypass"):
        p = parse_wiring(resolve_arm(arm), registry) if arm != "mix" else r
        assert p.report.ok, (arm, [v.code for v in p.report.violations])
        ids |= set(p.nodes)
    assert len(ids) == 18, sorted(ids)
