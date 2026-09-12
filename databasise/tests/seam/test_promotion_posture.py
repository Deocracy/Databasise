"""07-01-PLAN.md Task 3: the verb ladder and the posture refusal that keeps the gate-adjudicated
path genuinely unreachable in this milestone (SC3, MACH-09).
"""

from __future__ import annotations

import typing

import pytest

from databasise.ledger.ledger import Ledger
from databasise.seam.engine import Databasise
from databasise.seam.promotion import _MEASUREMENT_POSTURE, PROMOTION_VERBS, MutationClass, PromotionVerb
from databasise.seam.refusals import (
    GateVerbNotBuiltError,
    MeasurementPostureRefusalError,
    UncalibratedFloorRefusalError,
    UnrecognisedPromotionVerbError,
)
from databasise.seam.trace_store import TraceStore
from databasise.wirings.resolve import all_wirings


def _seed_trace(store_root, arm_name: str) -> str:
    resolved = next(resolved for name, resolved in all_wirings() if name == arm_name)
    node_ids = sorted(resolved.get("nodes", {}).keys())
    fake_record = {
        "run_id": f"fake-run-{arm_name}",
        "wiring_id": resolved.get("wiring_id"),
        "wiring_instance_hash": f"sha256:{'0' * 64}",
        "arm_id": "seam",
        "nodes": [{"node_id": node_id} for node_id in node_ids],
    }
    return TraceStore(store_root).persist(fake_record)


def _engine(store_root) -> Databasise:
    return Databasise(store_root=store_root, workspace="posture-test")


def _row_count(store_root) -> int:
    return Ledger(store_root)._conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]


async def test_promote_next_refuses_at_answer_level_naming_the_posture(store_root):
    engine = _engine(store_root)
    # bypass's only node is "generate" -> a pure answer-level first promotion.
    trace_id = _seed_trace(store_root, "bypass")

    with pytest.raises(MeasurementPostureRefusalError) as exc_info:
        await engine.promote("fresh-alias-answer", [trace_id], "human_edit", verb="promote-next")

    message = str(exc_info.value)
    assert "answer-level" in message
    assert "F3.2" in message
    assert _row_count(store_root) == 0


async def test_promote_now_refuses_at_index_side_naming_the_posture(store_root):
    engine = _engine(store_root)
    # naive includes embedder-index (an index-recipe node) -> a pure index-side first promotion.
    trace_id = _seed_trace(store_root, "naive")

    with pytest.raises(MeasurementPostureRefusalError) as exc_info:
        await engine.promote("fresh-alias-index", [trace_id], "human_edit", verb="promote-now")

    message = str(exc_info.value)
    assert "index-side" in message
    assert "F3.2" in message
    assert _row_count(store_root) == 0


async def test_promote_next_refuses_at_retrieval_side_naming_the_missing_floor(store_root):
    engine = _engine(store_root)
    trace_hybrid = _seed_trace(store_root, "hybrid")
    trace_local = _seed_trace(store_root, "local")

    # hybrid establishes the active generation via the ordinary operator path.
    await engine.promote("floor-alias", [trace_hybrid], "human_edit")
    before = _row_count(store_root)

    # hybrid -> local differs only in retrieval nodes -> retrieval-side, on by default, but no
    # calibrated A/A floor exists.
    with pytest.raises(UncalibratedFloorRefusalError) as exc_info:
        await engine.promote("floor-alias", [trace_local], "human_edit", verb="promote-next")

    message = str(exc_info.value)
    assert "retrieval-side" in message
    assert "AA.2" in message
    assert _row_count(store_root) == before


@pytest.mark.parametrize("verb", ["check", "preview", "run"])
async def test_check_preview_run_refuse_as_not_built(store_root, verb):
    engine = _engine(store_root)
    trace_id = _seed_trace(store_root, "naive")

    with pytest.raises(GateVerbNotBuiltError) as exc_info:
        await engine.promote("any-alias", [trace_id], "human_edit", verb=verb)

    assert exc_info.value.verb == verb
    assert _row_count(store_root) == 0


async def test_no_gate_verb_appends_a_row(store_root):
    engine = _engine(store_root)
    trace_naive = _seed_trace(store_root, "naive")
    trace_bypass = _seed_trace(store_root, "bypass")
    trace_hybrid = _seed_trace(store_root, "hybrid")
    trace_local = _seed_trace(store_root, "local")

    await engine.promote("floor-alias", [trace_hybrid], "human_edit")
    before = _row_count(store_root)

    attempts = [
        ("check", "any-alias", trace_naive),
        ("preview", "any-alias", trace_naive),
        ("run", "any-alias", trace_naive),
        ("promote-next", "fresh-answer-alias", trace_bypass),
        ("promote-now", "fresh-index-alias", trace_naive),
        ("promote-next", "floor-alias", trace_local),
    ]
    for verb, alias, trace_id in attempts:
        with pytest.raises((GateVerbNotBuiltError, MeasurementPostureRefusalError, UncalibratedFloorRefusalError)):
            await engine.promote(alias, [trace_id], "human_edit", verb=verb)

    assert _row_count(store_root) == before


async def test_posture_is_not_flippable_at_runtime(store_root, monkeypatch):
    """Every plausible flag name a future reader might wire the posture constant to — none of
    them changes which class refuses (D-11)."""
    for env_name in (
        "DATABASISE_MEASUREMENT_POSTURE",
        "MEASUREMENT_POSTURE",
        "DATABASISE_POSTURE",
        "PROMOTION_POSTURE",
    ):
        monkeypatch.setenv(env_name, "on")

    engine = _engine(store_root)
    trace_id = _seed_trace(store_root, "bypass")

    with pytest.raises(MeasurementPostureRefusalError):
        await engine.promote("fresh-alias-env", [trace_id], "human_edit", verb="promote-next")


def test_posture_constant_is_exactly_rig_f3_2():
    assert _MEASUREMENT_POSTURE == {
        "retrieval-side": True,
        "answer-level": False,
        "index-side": False,
    }
    # Every class derive_mutation_class's own declared return type can produce must have a
    # posture entry — derived from that Literal, not restated as a second literal list, so a
    # later fourth class landing in the type without a matching entry fails this assertion.
    assert set(_MEASUREMENT_POSTURE.keys()) == set(typing.get_args(MutationClass))


async def test_operator_asserted_verb_still_appends(store_root):
    engine = _engine(store_root)
    trace_id = _seed_trace(store_root, "naive")

    result = await engine.promote("operator-alias", [trace_id], "human_edit")

    assert result.record_kind == "promotion"
    assert Ledger(store_root).by_alias("operator-alias") is not None


@pytest.mark.parametrize(
    "verb",
    [
        "promote_next_typo",
        "Promote-Next",
        "promote_next",
        "",
        None,
        "operator asserted",
    ],
)
async def test_an_unrecognised_verb_refuses_by_name_before_any_trace_resolution(store_root, verb):
    """07-04-PLAN.md, closing 07-VERIFICATION.md's three `missing:` items and 07-REVIEW.md CR-01:
    any string outside PROMOTION_VERBS's six declared literals refuses by name, never crashes with
    a bare ValueError, and never normalises a near-miss into the literal it resembles."""
    engine = _engine(store_root)
    trace_id = _seed_trace(store_root, "naive")

    with pytest.raises(UnrecognisedPromotionVerbError) as exc_info:
        await engine.promote("any-alias", [trace_id], "human_edit", verb=verb)

    assert exc_info.value.verb == verb
    assert _row_count(store_root) == 0

    if verb == "promote_next_typo":
        # No menu: the message names only the caller's own out-of-enum value, never any of the
        # six declared literals it might otherwise be pattern-matched against.
        message = str(exc_info.value)
        for declared_verb in PROMOTION_VERBS:
            assert declared_verb not in message

        # Ordering proof (single case, per 07-04-PLAN.md's own instruction): the same out-of-enum
        # verb still refuses by name even when trace_ids carries an unresolvable token, proving the
        # verb guard runs before trace-id resolution (07-VERIFICATION.md's missing item 1) rather
        # than merely happening to run first because a valid trace was supplied.
        with pytest.raises(UnrecognisedPromotionVerbError) as exc_info_unresolvable:
            await engine.promote("any-alias", ["no-such-trace-token"], "human_edit", verb=verb)
        assert exc_info_unresolvable.value.verb == verb
        assert _row_count(store_root) == 0


def test_the_verb_guard_reads_the_enum_rather_than_a_second_list():
    """The drift guard (07-04-PLAN.md): fails the moment a seventh literal is added to
    PromotionVerb without PROMOTION_VERBS being derived from it automatically."""
    assert PROMOTION_VERBS == frozenset(typing.get_args(PromotionVerb))
    assert len(PROMOTION_VERBS) == 6
