"""07-01-PLAN.md Tasks 1-2: the operator-asserted promote() path — the tracer's one path from a
resolved trace id through to the already-tested alias-selector read contract
(``databasise/tests/seam/test_alias_registry.py``), plus every refusal that path cannot be correct
without.

Trace records are seeded through the same ``TraceStore.persist()`` path the engine's own
``_execute()`` uses (never a hand-written ledger row), but with a hand-built minimal record naming
exactly a real registered arm's own resolved node id set — the one query-invariant signal
``databasise.seam.promotion.resolve_single_arm`` actually reads (see that module's own docstring
for why ``wiring_id``/``arm_id``/``wiring_instance_hash`` cannot be used for this). This avoids
needing a full end-to-end query run (with its own graph/entity retrieval data) for every one of the
five LightRAG arms this file promotes.
"""

from __future__ import annotations

import inspect

import pytest

from databasise.ledger.ledger import Ledger
from databasise.parts.registry import default_registry
from databasise.seam.engine import Databasise
from databasise.seam.refusals import (
    DisagreeingPromotionTraceIdsError,
    EmptyPromotionTraceIdsError,
    InvalidChangeOriginError,
)
from databasise.seam.selectors import _resolve_alias
from databasise.seam.trace_store import TraceStore, UnknownTraceReferenceError
from databasise.wirings.resolve import all_wirings, resolve_arm

_ALIAS = "prod-lightrag"


def _seed_trace(store_root, arm_name: str) -> str:
    """Persist a minimal trace record naming exactly ``arm_name``'s own resolved node id set,
    through the same ``TraceStore.persist()`` path the engine uses — never a hand-written ledger
    row.
    """
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
    return Databasise(store_root=store_root, workspace="promote-test")


def _row_count(store_root) -> int:
    return Ledger(store_root)._conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]


# --------------------------------------------------------------------------------------------- #
# Task 1: end-to-end "the owner promotes a wiring and the alias resolves to it" — one path only
# --------------------------------------------------------------------------------------------- #


async def test_promote_appends_one_row_the_alias_selector_resolves(store_root):
    engine = _engine(store_root)
    trace_id = _seed_trace(store_root, "naive")

    await engine.promote(_ALIAS, [trace_id], "human_edit")

    record = Ledger(store_root).by_alias(_ALIAS)
    assert record is not None
    assert record.mutation_id == "naive"
    assert _resolve_alias(_ALIAS, store_root=store_root) == resolve_arm("naive")


async def test_first_promotion_mints_1_0_0(store_root):
    engine = _engine(store_root)
    trace_id = _seed_trace(store_root, "naive")

    result = await engine.promote(_ALIAS, [trace_id], "human_edit")

    assert result.version == "1.0.0"
    assert Ledger(store_root).by_alias(_ALIAS).minted_version == "1.0.0"


async def test_record_carries_change_origin_and_operator_asserted_provenance(store_root):
    engine = _engine(store_root)
    trace_id = _seed_trace(store_root, "naive")

    await engine.promote(_ALIAS, [trace_id], "human_edit")

    record = Ledger(store_root).by_alias(_ALIAS)
    assert record.change_origin == "human_edit"
    assert record.promotion_provenance == "operator_asserted"
    assert record.verdict is None
    assert record.tier_of_decision is None
    assert record.evidence_pointer is None
    assert record.promotion_trace_ids == [trace_id]


async def test_promotion_result_carries_no_internal_identity(store_root):
    engine = _engine(store_root)
    trace_id = _seed_trace(store_root, "naive")
    resolved_naive = resolve_arm("naive")

    result = await engine.promote(_ALIAS, [trace_id], "human_edit")

    # Derived live from the resolved wiring and the registry at test time — never a literal list
    # that could drift (mirrors test_tool_growth_invariant.py's own live-derivation convention).
    forbidden = set(default_registry().keys()) | set(resolved_naive.get("nodes", {}).keys())

    dumped = result.model_dump()
    assert set(dumped.keys()) == {
        "alias",
        "version",
        "record_kind",
        "provenance",
        "generation_ordinal",
    }
    serialized = str(dumped)
    for token in forbidden:
        assert token not in serialized, f"{token!r} leaked into the promotion result"


async def test_two_promotions_produce_two_ordered_rows(store_root):
    engine = _engine(store_root)
    trace_id_1 = _seed_trace(store_root, "naive")
    trace_id_2 = _seed_trace(store_root, "naive")

    result_1 = await engine.promote(_ALIAS, [trace_id_1], "human_edit")
    result_2 = await engine.promote(_ALIAS, [trace_id_2], "human_edit")

    assert result_2.generation_ordinal > result_1.generation_ordinal
    active = Ledger(store_root).by_alias(_ALIAS)
    assert active.minted_version == "1.1.0"  # second promotion, identical surface -> MINOR


async def test_ledger_rejects_update_and_delete_after_the_new_columns_land(store_root):
    """Regression guard extending databasise/tests/ledger/test_ledger.py's own trigger proof: a
    real promote() write against the four new columns still rejects UPDATE/DELETE."""
    import sqlite3

    engine = _engine(store_root)
    trace_id = _seed_trace(store_root, "naive")
    await engine.promote(_ALIAS, [trace_id], "human_edit")

    ledger = Ledger(store_root)
    with pytest.raises(sqlite3.IntegrityError):
        ledger._conn.execute("UPDATE ledger SET change_origin = 'machine_mutation'")
    with pytest.raises(sqlite3.IntegrityError):
        ledger._conn.execute("DELETE FROM ledger")


async def test_new_columns_round_trip(store_root):
    """A promote()-appended record survives append() -> by_alias() unchanged for all four new
    columns."""
    engine = _engine(store_root)
    trace_id = _seed_trace(store_root, "naive")

    await engine.promote(_ALIAS, [trace_id], "machine_mutation")

    record = Ledger(store_root).by_alias(_ALIAS)
    assert record.change_origin == "machine_mutation"
    assert record.record_kind == "promotion"
    assert record.minted_version == "1.0.0"
    assert record.targets_version is None


# --------------------------------------------------------------------------------------------- #
# Task 2: the refusals the derivation cannot be correct without
# --------------------------------------------------------------------------------------------- #


async def test_empty_trace_ids_refuses_before_any_write(store_root):
    engine = _engine(store_root)

    with pytest.raises(EmptyPromotionTraceIdsError):
        await engine.promote(_ALIAS, [], "human_edit")

    assert _row_count(store_root) == 0


async def test_single_trace_id_is_sufficient(store_root):
    engine = _engine(store_root)
    trace_id = _seed_trace(store_root, "naive")

    result = await engine.promote(_ALIAS, [trace_id], "human_edit")

    assert result.alias == _ALIAS


async def test_unknown_trace_id_refuses_by_name(store_root):
    engine = _engine(store_root)

    with pytest.raises(UnknownTraceReferenceError) as exc_info:
        await engine.promote(_ALIAS, ["never-minted-token"], "human_edit")

    assert exc_info.value.trace_reference == "never-minted-token"
    assert _row_count(store_root) == 0


async def test_disagreeing_trace_ids_refuse_rather_than_pick_one(store_root):
    engine = _engine(store_root)
    trace_naive = _seed_trace(store_root, "naive")
    trace_bypass = _seed_trace(store_root, "bypass")

    with pytest.raises(DisagreeingPromotionTraceIdsError) as exc_info:
        await engine.promote(_ALIAS, [trace_naive, trace_bypass], "human_edit")

    assert exc_info.value.trace_ids == [trace_naive, trace_bypass]
    message = str(exc_info.value)
    assert "naive" not in message
    assert "bypass" not in message
    assert _row_count(store_root) == 0


async def test_absent_change_origin_refuses_by_name(store_root):
    engine = _engine(store_root)
    trace_id = _seed_trace(store_root, "naive")

    with pytest.raises(InvalidChangeOriginError):
        await engine.promote(_ALIAS, [trace_id], None)

    assert _row_count(store_root) == 0


async def test_unrecognised_change_origin_refuses_by_name(store_root):
    engine = _engine(store_root)
    trace_id = _seed_trace(store_root, "naive")

    with pytest.raises(InvalidChangeOriginError):
        await engine.promote(_ALIAS, [trace_id], "guessed")

    assert _row_count(store_root) == 0


async def test_machine_mutation_change_origin_is_accepted(store_root):
    engine = _engine(store_root)
    trace_id = _seed_trace(store_root, "naive")

    await engine.promote(_ALIAS, [trace_id], "machine_mutation")

    assert Ledger(store_root).by_alias(_ALIAS).change_origin == "machine_mutation"


async def test_major_bump_when_declared_surface_differs(store_root):
    """naive -> bypass: bypass's declared effects set is a strict, differing subset of naive's —
    a real capability-surface change, real registered arms, no fabricated wiring document."""
    engine = _engine(store_root)
    trace_naive = _seed_trace(store_root, "naive")
    trace_bypass = _seed_trace(store_root, "bypass")

    await engine.promote(_ALIAS, [trace_naive], "human_edit")
    result = await engine.promote(_ALIAS, [trace_bypass], "human_edit")

    assert result.version == "2.0.0"


async def test_minor_bump_when_it_does_not(store_root):
    """naive -> naive: an identical declared surface — a second promotion of the same arm."""
    engine = _engine(store_root)
    trace_1 = _seed_trace(store_root, "naive")
    trace_2 = _seed_trace(store_root, "naive")

    await engine.promote(_ALIAS, [trace_1], "human_edit")
    result = await engine.promote(_ALIAS, [trace_2], "human_edit")

    assert result.version == "1.1.0"


async def test_no_path_mints_a_patch(store_root):
    engine = _engine(store_root)
    trace_naive = _seed_trace(store_root, "naive")
    trace_bypass = _seed_trace(store_root, "bypass")
    trace_naive_again = _seed_trace(store_root, "naive")

    versions = [
        (await engine.promote(_ALIAS, [trace_naive], "human_edit")).version,
        (await engine.promote(_ALIAS, [trace_bypass], "human_edit")).version,
        (await engine.promote(_ALIAS, [trace_naive_again], "human_edit")).version,
    ]

    for version in versions:
        assert version.split(".")[-1] == "0", f"{version!r} minted a non-zero patch"


async def test_semver_mint_rule_is_derived_and_never_defaulted(store_root):
    """Supplementary to the exact-named MAJOR/MINOR/no-patch tests above: exercises the same rule
    under a name containing "semver"/"version" for coverage-filter discoverability."""
    engine = _engine(store_root)
    trace_id = _seed_trace(store_root, "naive")

    result = await engine.promote("semver-check-alias", [trace_id], "human_edit")

    assert result.version == "1.0.0"


async def test_mutation_class_is_derived_not_supplied(store_root):
    assert "mutation_class" not in inspect.signature(Databasise.promote).parameters

    engine = _engine(store_root)
    trace_naive = _seed_trace(store_root, "naive")
    trace_bypass = _seed_trace(store_root, "bypass")
    trace_hybrid = _seed_trace(store_root, "hybrid")
    trace_local = _seed_trace(store_root, "local")

    # naive -> bypass differs in an index-recipe node (embedder-index) -> index-side.
    await engine.promote("index-side-alias", [trace_naive], "human_edit")
    await engine.promote("index-side-alias", [trace_bypass], "human_edit")
    assert Ledger(store_root).by_alias("index-side-alias").mutation_class == "index-side"

    # hybrid -> local differs only in retrieval nodes (relation-lookup/relation-hydrate-expand)
    # -> retrieval-side.
    await engine.promote("retrieval-side-alias", [trace_hybrid], "human_edit")
    await engine.promote("retrieval-side-alias", [trace_local], "human_edit")
    assert Ledger(store_root).by_alias("retrieval-side-alias").mutation_class == "retrieval-side"


async def test_ledger_ordering_is_by_id_not_timestamp(store_root, monkeypatch):
    import databasise.ledger.ledger as ledger_module

    fixed_iso = "2026-01-01T00:00:00+00:00"

    class _FixedDatetime(ledger_module.datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ARG003 - matches datetime.now's own signature
            return ledger_module.datetime.fromisoformat(fixed_iso)

    monkeypatch.setattr(ledger_module, "datetime", _FixedDatetime)

    engine = _engine(store_root)
    trace_1 = _seed_trace(store_root, "naive")
    trace_2 = _seed_trace(store_root, "naive")

    await engine.promote(_ALIAS, [trace_1], "human_edit")
    await engine.promote(_ALIAS, [trace_2], "human_edit")

    ledger = Ledger(store_root)
    created_ats = [
        row[0]
        for row in ledger._conn.execute(
            "SELECT created_at FROM ledger WHERE mutation_id = 'naive' ORDER BY id ASC"
        ).fetchall()
    ]
    assert created_ats == [fixed_iso, fixed_iso]  # both rows share the identical timestamp

    active = ledger.by_alias(_ALIAS)
    assert active.minted_version == "1.1.0"  # the higher-id row, despite an identical created_at
    history = ledger.history("naive")
    assert len(history) == 2
    assert history[0].minted_version == "1.0.0"  # id ASC -> oldest first
    assert history[1].minted_version == "1.1.0"
