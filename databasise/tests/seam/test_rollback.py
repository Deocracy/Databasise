"""07-02-PLAN.md Task 1: Databasise.rollback() — an explicitly named semver target, and the two
ways it can be wrong (an unknown/foreign-alias version, or a tombstoned target).

Trace records are seeded through the same ``TraceStore.persist()`` path
``databasise/tests/seam/test_promote.py`` already established — never a hand-written ledger row.
naive/bypass are the same two real, already-registered LightRAG arms test_promote.py uses for its
own MAJOR-bump test: bypass's declared effects set differs from naive's, a real capability-surface
change with no fabricated wiring document.
"""

from __future__ import annotations

import inspect

import pytest

from databasise.ledger.ledger import Ledger
from databasise.seam.engine import Databasise
from databasise.seam.refusals import (
    DisagreeingPromotionTraceIdsError,
    EmptyPromotionTraceIdsError,
    InvalidChangeOriginError,
    UnknownGenerationVersionError,
)
from databasise.seam.selectors import _resolve_alias
from databasise.seam.trace_store import TraceStore, UnknownTraceReferenceError
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
    return Databasise(store_root=store_root, workspace="rollback-test")


def _row_count(store_root) -> int:
    return Ledger(store_root)._conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]


def _all_records(store_root):
    ledger = Ledger(store_root)
    cur = ledger._conn.execute("SELECT * FROM ledger ORDER BY id ASC")
    return [ledger._row_to_record(row) for row in cur.fetchall()]


async def test_rollback_repoints_the_alias_to_the_named_generation(store_root):
    engine = _engine(store_root)
    trace_naive = _seed_trace(store_root, "naive")
    trace_bypass = _seed_trace(store_root, "bypass")
    trace_rollback = _seed_trace(store_root, "naive")

    await engine.promote(_ALIAS, [trace_naive], "human_edit")
    await engine.promote(_ALIAS, [trace_bypass], "human_edit")

    await engine.rollback(_ALIAS, "1.0.0", [trace_rollback], "human_edit")

    assert _resolve_alias(_ALIAS, store_root=store_root) == resolve_arm("naive")


async def test_rollback_appends_rather_than_rewinds(store_root):
    engine = _engine(store_root)
    trace_naive = _seed_trace(store_root, "naive")
    trace_bypass = _seed_trace(store_root, "bypass")
    trace_rollback = _seed_trace(store_root, "naive")

    await engine.promote(_ALIAS, [trace_naive], "human_edit")
    await engine.promote(_ALIAS, [trace_bypass], "human_edit")
    before = _all_records(store_root)
    assert len(before) == 2

    await engine.rollback(_ALIAS, "1.0.0", [trace_rollback], "human_edit")

    after = _all_records(store_root)
    assert len(after) == 3
    assert after[0] == before[0]
    assert after[1] == before[1]
    assert len(Ledger(store_root).history("naive")) == 2  # original promote + rollback record
    assert len(Ledger(store_root).history("bypass")) == 1


async def test_rollback_record_parent_names_the_returned_to_mutation(store_root):
    engine = _engine(store_root)
    trace_naive = _seed_trace(store_root, "naive")
    trace_bypass = _seed_trace(store_root, "bypass")
    trace_rollback = _seed_trace(store_root, "naive")

    await engine.promote(_ALIAS, [trace_naive], "human_edit")
    await engine.promote(_ALIAS, [trace_bypass], "human_edit")
    await engine.rollback(_ALIAS, "1.0.0", [trace_rollback], "human_edit")

    record = Ledger(store_root).by_alias(_ALIAS)
    assert record.record_kind == "rollback"
    assert record.parent == "naive"
    assert record.targets_version == "1.0.0"


async def test_rollback_mints_a_new_version_never_reuses_the_target(store_root):
    engine = _engine(store_root)
    trace_naive = _seed_trace(store_root, "naive")
    trace_bypass = _seed_trace(store_root, "bypass")
    trace_rollback = _seed_trace(store_root, "naive")

    await engine.promote(_ALIAS, [trace_naive], "human_edit")  # 1.0.0
    await engine.promote(_ALIAS, [trace_bypass], "human_edit")  # index-side diff -> 2.0.0

    result = await engine.rollback(_ALIAS, "1.0.0", [trace_rollback], "human_edit")

    # naive's surface differs from bypass's (the same diff that made the prior promotion a MAJOR
    # bump) -> another MAJOR bump off the current active generation's version (2.0.0) -> 3.0.0.
    assert result.version == "3.0.0"
    minted_versions = {r.minted_version for r in Ledger(store_root).history("naive")}
    minted_versions |= {r.minted_version for r in Ledger(store_root).history("bypass")}
    assert result.version not in (minted_versions - {result.version})


async def test_rollback_carries_no_verdict(store_root):
    engine = _engine(store_root)
    trace_naive = _seed_trace(store_root, "naive")
    trace_bypass = _seed_trace(store_root, "bypass")
    trace_rollback = _seed_trace(store_root, "naive")

    await engine.promote(_ALIAS, [trace_naive], "human_edit")
    await engine.promote(_ALIAS, [trace_bypass], "human_edit")
    await engine.rollback(_ALIAS, "1.0.0", [trace_rollback], "human_edit")

    record = Ledger(store_root).by_alias(_ALIAS)
    assert record.verdict is None
    assert record.tier_of_decision is None
    assert record.evidence_pointer is None
    assert record.effect_size is None
    assert record.promotion_provenance == "operator_asserted"
    assert record.promotion_trace_ids == [trace_rollback]


async def test_unknown_version_refuses_by_name(store_root):
    engine = _engine(store_root)
    trace_naive = _seed_trace(store_root, "naive")
    trace_rollback = _seed_trace(store_root, "naive")

    await engine.promote(_ALIAS, [trace_naive], "human_edit")

    with pytest.raises(UnknownGenerationVersionError) as exc_info:
        await engine.rollback(_ALIAS, "9.9.9", [trace_rollback], "human_edit")

    assert exc_info.value.alias == _ALIAS
    assert exc_info.value.version == "9.9.9"
    assert _row_count(store_root) == 1


async def test_version_minted_under_a_different_alias_refuses(store_root):
    engine = _engine(store_root)
    trace_x = _seed_trace(store_root, "naive")
    trace_y = _seed_trace(store_root, "naive")

    await engine.promote("alias-x", [trace_x], "human_edit")  # mints 1.0.0 under alias-x

    with pytest.raises(UnknownGenerationVersionError) as exc_info:
        await engine.rollback("alias-y", "1.0.0", [trace_y], "human_edit")

    message = str(exc_info.value)
    assert "alias-x" not in message
    assert exc_info.value.alias == "alias-y"
    assert exc_info.value.version == "1.0.0"
    assert _row_count(store_root) == 1


async def test_rollback_has_no_default_previous():
    params = inspect.signature(Databasise.rollback).parameters
    assert "version" in params
    assert params["version"].default is inspect.Parameter.empty


async def test_rollback_shares_promotes_trace_and_change_origin_refusals(store_root):
    engine = _engine(store_root)
    trace_naive = _seed_trace(store_root, "naive")
    trace_bypass = _seed_trace(store_root, "bypass")
    await engine.promote(_ALIAS, [trace_naive], "human_edit")

    with pytest.raises(EmptyPromotionTraceIdsError):
        await engine.rollback(_ALIAS, "1.0.0", [], "human_edit")

    with pytest.raises(UnknownTraceReferenceError):
        await engine.rollback(_ALIAS, "1.0.0", ["never-minted-token"], "human_edit")

    with pytest.raises(DisagreeingPromotionTraceIdsError):
        await engine.rollback(_ALIAS, "1.0.0", [trace_naive, trace_bypass], "human_edit")

    with pytest.raises(InvalidChangeOriginError):
        await engine.rollback(_ALIAS, "1.0.0", [trace_naive], None)

    assert _row_count(store_root) == 1  # only the original promote landed
