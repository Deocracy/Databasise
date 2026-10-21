"""07-01-PLAN.md Task 3 / 14-08-PLAN.md Task 3 (LEDG-08, D-04): the verb ladder, and the up-front
refusal that keeps the gate-adjudicated path genuinely unreachable (SC3, MACH-09).

``promote-next`` and ``promote-now`` are refused as ``GateNotCalibratedError`` for every arm, before
alias validation, trace resolution and any ledger access (so no ``ledger.db`` is created). The
per-class posture refusals stay in code for TOOL-12 and are unreachable from ``promote``. Refusal
types are compared by name, so the file collects at the phase base, where ``GateNotCalibratedError``
does not exist yet.
"""

from __future__ import annotations

import typing
from pathlib import Path

import pytest

from databasise.ledger.ledger import Ledger
from databasise.seam.engine import Databasise
from databasise.seam.promotion import _MEASUREMENT_POSTURE, PROMOTION_VERBS, MutationClass, PromotionVerb
from databasise.seam.refusals import GateVerbNotBuiltError, UnrecognisedPromotionVerbError
from databasise.seam.trace_store import TraceStore
from databasise.wirings.resolve import all_wirings

_ARM_NAMES = [name for name, _ in all_wirings()]
_GATE_VERBS = ["promote-next", "promote-now"]
_INVENTORY = Path(__file__).resolve().parents[3] / "docs" / "gui" / "API-INVENTORY.md"


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


def _no_ledger_files(store_root) -> bool:
    return not any((store_root / name).exists() for name in ("ledger.db", "ledger.db-wal", "ledger.db-shm"))


async def _refusal(engine, alias, trace_ids, verb, change_origin="human_edit"):
    """The exception ``engine.promote`` raised, or ``None``."""
    try:
        await engine.promote(alias, trace_ids, change_origin, verb=verb)
    except Exception as caught:  # noqa: BLE001 - the assertion is on the captured type
        return caught
    return None


def _assert_gate_refusal(caught, verb) -> None:
    assert type(caught).__name__ == "GateNotCalibratedError", f"{verb}: {type(caught).__name__}: {caught}"
    assert caught.verb == verb


@pytest.mark.parametrize("verb", _GATE_VERBS)
@pytest.mark.parametrize("arm", _ARM_NAMES)
async def test_gate_verbs_are_refused_up_front_for_every_arm(store_root, arm, verb):
    """LEDG-08 (D-04): one refusal for every arm, before any ledger access."""
    trace_id = _seed_trace(store_root, arm)

    caught = await _refusal(_engine(store_root), "fresh-alias", [trace_id], verb)

    _assert_gate_refusal(caught, verb)
    # The message carries the verb and nothing else: rebuilding the refusal from the verb alone
    # gives the same text, so no arm, class or posture can differ between arms.
    assert str(caught) == str(type(caught)(verb=verb))
    assert _no_ledger_files(store_root), "a refused gate verb created ledger.db"


@pytest.mark.parametrize("verb", _GATE_VERBS)
async def test_a_gate_verb_with_an_invalid_alias_is_refused_as_not_calibrated(store_root, verb):
    """The documented order: the gate refusal comes before alias validation."""
    caught = await _refusal(_engine(store_root), "", [_seed_trace(store_root, "naive")], verb)

    _assert_gate_refusal(caught, verb)
    assert _no_ledger_files(store_root)


@pytest.mark.parametrize("verb", _GATE_VERBS)
async def test_a_gate_verb_with_an_unresolvable_trace_is_refused_as_not_calibrated(store_root, verb):
    caught = await _refusal(_engine(store_root), "fresh-alias", ["no-such-trace"], verb, change_origin=None)

    _assert_gate_refusal(caught, verb)
    assert _no_ledger_files(store_root)


def test_the_inventory_states_the_gate_refusal():
    text = _INVENTORY.read_text()
    section = text[text.index("#### 3.5.1 POST /promote") : text.index("#### 3.5.2 POST /rollback")]

    assert "GateNotCalibratedError" in section
    assert "UncalibratedFloorRefusalError" not in section


async def test_a_pure_answer_level_first_promotion_is_refused_up_front(store_root):
    # bypass's only node is "generate" -> a pure answer-level first promotion.
    caught = await _refusal(_engine(store_root), "fresh-alias-answer", [_seed_trace(store_root, "bypass")], "promote-next")

    _assert_gate_refusal(caught, "promote-next")
    assert _no_ledger_files(store_root)


async def test_a_pure_index_side_first_promotion_is_refused_up_front(store_root):
    # naive includes embedder-index (an index-recipe node) -> a pure index-side first promotion.
    caught = await _refusal(_engine(store_root), "fresh-alias-index", [_seed_trace(store_root, "naive")], "promote-now")

    _assert_gate_refusal(caught, "promote-now")
    assert _no_ledger_files(store_root)


async def test_a_retrieval_side_change_is_refused_up_front_and_appends_nothing(store_root):
    engine = _engine(store_root)
    trace_hybrid = _seed_trace(store_root, "hybrid")
    trace_local = _seed_trace(store_root, "local")

    # hybrid establishes the active generation via the ordinary operator path.
    await engine.promote("floor-alias", [trace_hybrid], "human_edit")
    before = _row_count(store_root)

    # hybrid -> local differs only in retrieval nodes (retrieval-side), yet the gate is still refused.
    caught = await _refusal(engine, "floor-alias", [trace_local], "promote-next")

    _assert_gate_refusal(caught, "promote-next")
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
        caught = await _refusal(engine, alias, [trace_id], verb)
        assert type(caught).__name__ in {"GateVerbNotBuiltError", "GateNotCalibratedError"}, (
            f"{verb}: {type(caught).__name__}: {caught}"
        )

    assert _row_count(store_root) == before


async def test_the_gate_stays_refused_when_the_posture_constant_or_environment_changes(store_root, monkeypatch):
    """No plausible flag name changes the outcome (D-11), and flipping any class of the posture
    constant does not lift the up-front refusal either: only TOOL-12 lifts it."""
    for env_name in (
        "DATABASISE_MEASUREMENT_POSTURE",
        "MEASUREMENT_POSTURE",
        "DATABASISE_POSTURE",
        "PROMOTION_POSTURE",
    ):
        monkeypatch.setenv(env_name, "on")

    engine = _engine(store_root)
    trace_id = _seed_trace(store_root, "bypass")

    for flipped in (True, False):
        for mutation_class in _MEASUREMENT_POSTURE:
            monkeypatch.setitem(_MEASUREMENT_POSTURE, mutation_class, flipped)
        for verb in _GATE_VERBS:
            _assert_gate_refusal(await _refusal(engine, "fresh-alias-env", [trace_id], verb), verb)
    assert _no_ledger_files(store_root)


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
