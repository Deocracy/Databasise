"""15-16-PLAN.md Task 1 (TOOL-12, D-13): a persisted two-sided floor lifts the promotion gate for the
arm it was calibrated on, and for no other arm.

Stage 1 (no ``floors.db``, or no rows) is ``GateNotCalibratedError`` before any ledger access. Stage 2
looks a floor up for every ``wiring_instance_hash`` the resolved traces carry and checks it through
``CalibrationResult.floor_for``; a missing or stale floor is ``GateNotCalibratedError`` again. With a
valid floor RIG section F3.2 decides: retrieval-side is ``GateVerbNotBuiltError`` (no comparison runner
yet), the other two classes are ``MeasurementPostureRefusalError``; nothing is ever appended.

Refusal types are compared by name and the new store is resolved with ``importlib``, so the file collects
and fails by assertion on the phase-base code, where ``databasise.seam.floors_store`` does not exist.
"""

from __future__ import annotations

import importlib

import pytest

from databasise.eval.bundle import _list_version_numbers
from databasise.eval.remint import _COMMITTED_BUNDLE_ROOT
from databasise.ledger.ledger import Ledger
from databasise.seam.engine import Databasise
from databasise.seam.trace_store import TraceStore
from databasise.wirings.resolve import all_wirings

_GATE_VERBS = ["promote-next", "promote-now"]
_HASH_PRIOR = f"sha256:{'1' * 64}"
_HASH_LOCAL = f"sha256:{'2' * 64}"
_HASH_OTHER = f"sha256:{'3' * 64}"
_NEWEST_BUNDLE = f"bundle@v{max(_list_version_numbers(_COMMITTED_BUNDLE_ROOT))}"


def _seed_trace(store_root, arm_name: str, instance_hash: str | None) -> str:
    resolved = next(resolved for name, resolved in all_wirings() if name == arm_name)
    record = {
        "run_id": f"floor-run-{arm_name}-{instance_hash}",
        "wiring_id": resolved.get("wiring_id"),
        "arm_id": "seam",
        "nodes": [{"node_id": node_id} for node_id in sorted(resolved.get("nodes", {}))],
    }
    if instance_hash is not None:
        record["wiring_instance_hash"] = instance_hash
    return TraceStore(store_root).persist(record)


def _engine(store_root) -> Databasise:
    return Databasise(store_root=store_root, workspace="floor-test")


def _row_count(store_root) -> int:
    return Ledger(store_root)._conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]


def _no_ledger_files(store_root) -> bool:
    return not any((store_root / name).exists() for name in ("ledger.db", "ledger.db-wal", "ledger.db-shm"))


def _seed_floor(
    store_root,
    instance_hash: str,
    *,
    bundle_at_v: str = _NEWEST_BUNDLE,
    tier: str = "T1",
    metric: str = "gold_passage_recall",
) -> None:
    try:
        module = importlib.import_module("databasise.seam.floors_store")
    except ImportError:
        module = None
    store_cls = getattr(module, "FloorStore", None)
    row_cls = getattr(module, "FloorRow", None)
    assert store_cls is not None and row_cls is not None, "databasise.seam.floors_store has no FloorStore/FloorRow"
    store_cls(store_root).record(
        row_cls(
            wiring_instance_hash=instance_hash,
            bundle_at_v=bundle_at_v,
            tier=tier,
            metric=metric,
            determinism_setting="cache-bypassed",
            concurrency_setting="sequential",
            floor=0.05,
            n_questions=10,
            n_resamples=200,
            seed=1,
            created_at="2026-10-21T00:00:00+00:00",
        )
    )


async def _refusal(engine, alias, trace_ids, verb):
    try:
        await engine.promote(alias, trace_ids, "human_edit", verb=verb)
    except BaseException as caught:  # noqa: BLE001 - the assertion is on the captured type
        return caught
    return None


def _name(caught) -> str:
    return type(caught).__name__ if caught is not None else "no refusal"


async def _engine_with_prior_hybrid(store_root):
    """An engine whose alias ``a`` already points at hybrid, so hybrid -> local is retrieval-side."""
    engine = _engine(store_root)
    await engine.promote("a", [_seed_trace(store_root, "hybrid", _HASH_PRIOR)], "human_edit")
    return engine


async def test_a_floor_for_the_arms_own_hash_lifts_the_gate_to_not_built(store_root):
    engine = await _engine_with_prior_hybrid(store_root)
    local = _seed_trace(store_root, "local", _HASH_LOCAL)
    _seed_floor(store_root, _HASH_LOCAL)
    before = _row_count(store_root)

    caught = await _refusal(engine, "a", [local], "promote-next")

    assert _name(caught) == "GateVerbNotBuiltError", f"{_name(caught)}: {caught}"
    assert _row_count(store_root) == before


@pytest.mark.parametrize("verb", _GATE_VERBS)
async def test_a_floor_for_a_different_hash_still_refuses_as_not_calibrated(store_root, verb):
    engine = await _engine_with_prior_hybrid(store_root)
    local = _seed_trace(store_root, "local", _HASH_LOCAL)
    _seed_floor(store_root, _HASH_OTHER)  # a floor exists, but not for this arm's hash

    caught = await _refusal(engine, "a", [local], verb)

    assert _name(caught) == "GateNotCalibratedError", f"{_name(caught)}: {caught}"


async def test_every_hash_the_traces_carry_needs_its_own_floor(store_root):
    engine = await _engine_with_prior_hybrid(store_root)
    local_one = _seed_trace(store_root, "local", _HASH_LOCAL)
    local_two = _seed_trace(store_root, "local", _HASH_OTHER)
    _seed_floor(store_root, _HASH_LOCAL)

    caught = await _refusal(engine, "a", [local_one, local_two], "promote-next")

    assert _name(caught) == "GateNotCalibratedError", f"{_name(caught)}: {caught}"


async def test_a_trace_without_an_instance_hash_cannot_use_any_floor(store_root):
    engine = await _engine_with_prior_hybrid(store_root)
    local = _seed_trace(store_root, "local", None)
    _seed_floor(store_root, _HASH_LOCAL)

    caught = await _refusal(engine, "a", [local], "promote-next")

    assert _name(caught) == "GateNotCalibratedError", f"{_name(caught)}: {caught}"


async def test_a_stale_floor_still_refuses_as_not_calibrated(store_root):
    engine = await _engine_with_prior_hybrid(store_root)
    local = _seed_trace(store_root, "local", _HASH_LOCAL)
    _seed_floor(store_root, _HASH_LOCAL, bundle_at_v="bundle@v0")

    caught = await _refusal(engine, "a", [local], "promote-next")

    assert _name(caught) == "GateNotCalibratedError", f"{_name(caught)}: {caught}"


async def test_a_floor_calibrated_for_the_wrong_tier_is_stale(store_root):
    engine = _engine(store_root)
    bypass = _seed_trace(store_root, "bypass", _HASH_LOCAL)
    _seed_floor(store_root, _HASH_LOCAL)  # T1 / gold_passage_recall; answer-level needs T0

    caught = await _refusal(engine, "fresh", [bypass], "promote-next")

    assert _name(caught) == "GateNotCalibratedError", f"{_name(caught)}: {caught}"


@pytest.mark.parametrize(
    ("arm", "tier", "metric", "expected_class"),
    [
        ("bypass", "T0", "answer_level_correctness", "answer-level"),
        ("naive", "T1", "gold_passage_recall", "index-side"),
    ],
)
async def test_a_first_promotion_with_a_floor_meets_the_measurement_posture(
    store_root, arm, tier, metric, expected_class
):
    engine = _engine(store_root)
    trace = _seed_trace(store_root, arm, _HASH_LOCAL)
    _seed_floor(store_root, _HASH_LOCAL, tier=tier, metric=metric)

    caught = await _refusal(engine, "fresh", [trace], "promote-now")

    assert _name(caught) == "MeasurementPostureRefusalError", f"{_name(caught)}: {caught}"
    assert caught.mutation_class == expected_class
    assert _no_ledger_files(store_root), "a refused gate verb created ledger.db"


@pytest.mark.parametrize("verb", _GATE_VERBS)
async def test_a_fresh_root_still_refuses_and_creates_no_ledger_file(store_root, verb):
    engine = _engine(store_root)
    trace = _seed_trace(store_root, "naive", _HASH_LOCAL)

    caught = await _refusal(engine, "fresh", [trace], verb)

    assert _name(caught) == "GateNotCalibratedError", f"{_name(caught)}: {caught}"
    assert _no_ledger_files(store_root)
    assert not (store_root / "floors.db").exists()
