"""07-02-PLAN.md Task 2: Databasise.retire() — a tombstone on the same append-only path, and the
rule that nothing lifts it. ``test_never_lifted_repromotion_is_a_new_generation`` is the
load-bearing test here: it is what makes SC1's "tombstoned losers are never lifted" true against
the real write path, rather than only against a hand-seeded row.
"""

from __future__ import annotations

import sqlite3

import pytest

from databasise.ledger.ledger import Ledger
from databasise.seam.engine import Databasise
from databasise.seam.refusals import ActiveGenerationRetirementError, TombstonedGenerationError
from databasise.seam.selectors import _resolve_alias
from databasise.seam.trace_store import TraceStore
from databasise.wirings.resolve import all_wirings, resolve_arm

_ALIAS = "prod-lightrag"


def _seed_trace(store_root, arm_name: str) -> str:
    resolved = next(resolved for name, resolved in all_wirings() if name == arm_name)
    node_ids = sorted(resolved.get("nodes", {}).keys())
    fake_record = {
        "run_id": f"fake-run-{arm_name}",
        "wiring_id": resolved.get("wiring_id"),
        "wiring_instance_hash": f"sha256:{'0' * 63}{len(node_ids) % 10}",
        "arm_id": "seam",
        "nodes": [{"node_id": node_id} for node_id in node_ids],
    }
    return TraceStore(store_root).persist(fake_record)


def _engine(store_root) -> Databasise:
    return Databasise(store_root=store_root, workspace="retire-test")


def _row_count(store_root) -> int:
    return Ledger(store_root)._conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]


async def test_retire_appends_a_tombstone_record(store_root):
    engine = _engine(store_root)
    trace_naive = _seed_trace(store_root, "naive")
    trace_bypass = _seed_trace(store_root, "bypass")
    trace_retire = _seed_trace(store_root, "naive")

    await engine.promote(_ALIAS, [trace_naive], "human_edit")
    await engine.promote(_ALIAS, [trace_bypass], "human_edit")  # now active; naive is not

    await engine.retire(_ALIAS, "1.0.0", [trace_retire], "human_edit")

    record = Ledger(store_root).generation_state(_ALIAS, "1.0.0")
    assert record.record_kind == "tombstone"
    assert record.targets_version == "1.0.0"
    assert record.minted_version is None


async def test_retire_mints_no_version(store_root):
    engine = _engine(store_root)
    trace_naive = _seed_trace(store_root, "naive")
    trace_bypass = _seed_trace(store_root, "bypass")
    trace_retire = _seed_trace(store_root, "naive")

    await engine.promote(_ALIAS, [trace_naive], "human_edit")
    await engine.promote(_ALIAS, [trace_bypass], "human_edit")

    result = await engine.retire(_ALIAS, "1.0.0", [trace_retire], "human_edit")

    assert result.version == "1.0.0"  # the retired version reported, never a minted one
    assert Ledger(store_root).generation_state(_ALIAS, "1.0.0").minted_version is None


async def test_retire_carries_no_verdict(store_root):
    engine = _engine(store_root)
    trace_naive = _seed_trace(store_root, "naive")
    trace_bypass = _seed_trace(store_root, "bypass")
    trace_retire = _seed_trace(store_root, "naive")

    await engine.promote(_ALIAS, [trace_naive], "human_edit")
    await engine.promote(_ALIAS, [trace_bypass], "human_edit")
    await engine.retire(_ALIAS, "1.0.0", [trace_retire], "human_edit")

    record = Ledger(store_root).generation_state(_ALIAS, "1.0.0")
    assert record.verdict is None
    assert record.tier_of_decision is None
    assert record.promotion_provenance == "operator_asserted"
    assert record.promotion_trace_ids == [trace_retire]


async def test_retired_generation_reports_tombstoned(store_root):
    engine = _engine(store_root)
    trace_naive = _seed_trace(store_root, "naive")
    trace_bypass = _seed_trace(store_root, "bypass")
    trace_retire = _seed_trace(store_root, "naive")

    await engine.promote(_ALIAS, [trace_naive], "human_edit")
    await engine.promote(_ALIAS, [trace_bypass], "human_edit")
    await engine.retire(_ALIAS, "1.0.0", [trace_retire], "human_edit")

    assert Ledger(store_root).generation_state(_ALIAS, "1.0.0").record_kind == "tombstone"


async def test_rollback_to_a_retired_generation_refuses(store_root):
    engine = _engine(store_root)
    trace_naive = _seed_trace(store_root, "naive")
    trace_bypass = _seed_trace(store_root, "bypass")
    trace_retire = _seed_trace(store_root, "naive")
    trace_rollback = _seed_trace(store_root, "naive")

    await engine.promote(_ALIAS, [trace_naive], "human_edit")
    await engine.promote(_ALIAS, [trace_bypass], "human_edit")
    await engine.retire(_ALIAS, "1.0.0", [trace_retire], "human_edit")

    with pytest.raises(TombstonedGenerationError):
        await engine.rollback(_ALIAS, "1.0.0", [trace_rollback], "human_edit")


async def test_never_lifted_repromotion_is_a_new_generation(store_root):
    engine = _engine(store_root)
    trace_naive_1 = _seed_trace(store_root, "naive")
    trace_bypass = _seed_trace(store_root, "bypass")
    trace_retire = _seed_trace(store_root, "naive")
    trace_naive_2 = _seed_trace(store_root, "naive")

    first = await engine.promote(_ALIAS, [trace_naive_1], "human_edit")
    await engine.promote(_ALIAS, [trace_bypass], "human_edit")  # now active
    await engine.retire(_ALIAS, first.version, [trace_retire], "human_edit")

    second = await engine.promote(_ALIAS, [trace_naive_2], "human_edit")

    assert second.version != first.version
    assert Ledger(store_root).generation_state(_ALIAS, first.version).record_kind == "tombstone"
    assert _resolve_alias(_ALIAS, store_root=store_root) == resolve_arm("naive")


async def test_retiring_the_active_generation_refuses(store_root):
    engine = _engine(store_root)
    trace_naive = _seed_trace(store_root, "naive")
    trace_retire = _seed_trace(store_root, "naive")

    result = await engine.promote(_ALIAS, [trace_naive], "human_edit")

    with pytest.raises(ActiveGenerationRetirementError) as exc_info:
        await engine.retire(_ALIAS, result.version, [trace_retire], "human_edit")

    assert exc_info.value.alias == _ALIAS
    assert exc_info.value.version == result.version
    assert _resolve_alias(_ALIAS, store_root=store_root) == resolve_arm("naive")
    assert _row_count(store_root) == 1


async def test_alias_never_derives_from_a_retirement_record(store_root):
    engine = _engine(store_root)
    trace_naive = _seed_trace(store_root, "naive")
    trace_bypass = _seed_trace(store_root, "bypass")
    trace_retire = _seed_trace(store_root, "naive")

    await engine.promote(_ALIAS, [trace_naive], "human_edit")
    await engine.promote(_ALIAS, [trace_bypass], "human_edit")
    await engine.retire(_ALIAS, "1.0.0", [trace_retire], "human_edit")  # highest id now

    active = Ledger(store_root).by_alias(_ALIAS)
    assert active.record_kind != "tombstone"
    assert active.mutation_id == "bypass"


async def test_the_ledger_still_refuses_update_and_delete_for_tombstones(store_root):
    engine = _engine(store_root)
    trace_naive = _seed_trace(store_root, "naive")
    trace_bypass = _seed_trace(store_root, "bypass")
    trace_retire = _seed_trace(store_root, "naive")

    await engine.promote(_ALIAS, [trace_naive], "human_edit")
    await engine.promote(_ALIAS, [trace_bypass], "human_edit")
    await engine.retire(_ALIAS, "1.0.0", [trace_retire], "human_edit")

    ledger = Ledger(store_root)
    with pytest.raises(sqlite3.IntegrityError):
        ledger._conn.execute(
            "UPDATE ledger SET record_kind = 'promotion' WHERE record_kind = 'tombstone'"
        )
    with pytest.raises(sqlite3.IntegrityError):
        ledger._conn.execute("DELETE FROM ledger WHERE record_kind = 'tombstone'")
