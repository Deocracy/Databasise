"""RED: the append-only promotion ledger and its derived active pointer (CONTRACT §7/§6)."""

from __future__ import annotations

import sqlite3

import pytest
from databasise.ledger.ledger import Ledger, LedgerRecord


def _record(**overrides) -> LedgerRecord:
    base = {
        "mutation_id": "mut-1",
        "mutation_class": "retrieval-side",
        "parent": None,
        "arm_instance_hashes": ["a" * 64, "b" * 64],
        "effect_size": 0.12,
        "verdict": "promote",
        "evidence_pointer": "trace:abc123",
        "proposer_id": "operator@example",
        "depth_label": "stage",
        "tier_of_decision": "T1",
        "decomposition_ratio": None,
        "opaque_ttl_renewals": [],
        "parity_records": [],
        "promotion_provenance": "gate_adjudicated",
        "promotion_trace_ids": [],
        "change_origin": "human_edit",
        "record_kind": "promotion",
    }
    base.update(overrides)
    return LedgerRecord(**base)


def test_1_appending_a_record_returns_a_monotonically_increasing_integer_id(store_root):
    ledger = Ledger(store_root)

    id_1 = ledger.append(_record())
    id_2 = ledger.append(_record())

    assert isinstance(id_1, int)
    assert isinstance(id_2, int)
    assert id_2 > id_1


def test_2_every_section_7_field_is_storable_and_reads_back_identically(store_root):
    ledger = Ledger(store_root)
    record = _record(
        parent="mut-0",
        effect_size=0.5,
        decomposition_ratio=0.75,
        opaque_ttl_renewals=[{"reason": "still opaque", "renewed_at": "2026-01-01"}],
        parity_records=[{"metric": "accuracy", "delta": 0.0}],
        promotion_provenance="operator_asserted",
        promotion_trace_ids=["trace:1", "trace:2"],
    )

    ledger.append(record)
    [stored] = ledger.history(record.mutation_id)

    assert stored.mutation_id == record.mutation_id
    assert stored.mutation_class == record.mutation_class
    assert stored.parent == "mut-0"
    assert stored.arm_instance_hashes == record.arm_instance_hashes
    assert stored.effect_size == 0.5
    assert stored.verdict == record.verdict
    assert stored.evidence_pointer == record.evidence_pointer
    assert stored.proposer_id == record.proposer_id
    assert stored.depth_label == record.depth_label
    assert stored.tier_of_decision == record.tier_of_decision
    assert stored.decomposition_ratio == 0.75
    assert stored.opaque_ttl_renewals == [{"reason": "still opaque", "renewed_at": "2026-01-01"}]
    assert stored.parity_records == [{"metric": "accuracy", "delta": 0.0}]
    assert stored.promotion_provenance == "operator_asserted"
    assert stored.promotion_trace_ids == ["trace:1", "trace:2"]


def test_3_active_pointer_is_computed_by_a_query_not_a_column(store_root):
    ledger = Ledger(store_root)
    ledger.append(_record(mutation_id="mut-2", verdict="reject"))

    active = ledger.active_pointer("mut-2")
    assert active is not None
    assert active.verdict == "reject"

    # No column named for tracking "active" — assert by inspecting the field names on the
    # dataclass the module hands back, which is exactly the schema's own column set.
    field_names = {f for f in LedgerRecord.__dataclass_fields__}
    assert not any("active" in name.lower() for name in field_names)


def test_4_appending_a_second_record_changes_active_pointer_without_touching_the_first(
    store_root,
):
    ledger = Ledger(store_root)
    ledger.append(_record(mutation_id="mut-3", verdict="inconclusive"))
    first_history = ledger.history("mut-3")
    assert len(first_history) == 1

    ledger.append(_record(mutation_id="mut-3", verdict="promote"))

    assert ledger.active_pointer("mut-3").verdict == "promote"
    history = ledger.history("mut-3")
    assert len(history) == 2
    assert history[0].verdict == "inconclusive"  # first record unchanged


def test_5_the_module_exposes_no_update_or_delete_callable(store_root):
    import databasise.ledger.ledger as ledger_module

    public_callables = [
        name
        for name in dir(ledger_module)
        if not name.startswith("_") and callable(getattr(ledger_module, name))
    ]
    assert not any("update" in name.lower() for name in public_callables)
    assert not any("delete" in name.lower() for name in public_callables)

    ledger = Ledger(store_root)
    public_methods = [
        name
        for name in dir(ledger)
        if not name.startswith("_") and callable(getattr(ledger, name))
    ]
    assert not any("update" in name.lower() for name in public_methods)
    assert not any("delete" in name.lower() for name in public_methods)


def test_6_update_and_delete_against_the_ledger_table_are_refused_by_a_database_level_trigger(
    store_root,
):
    ledger = Ledger(store_root)
    ledger.append(_record(mutation_id="mut-4"))

    with pytest.raises(sqlite3.IntegrityError):
        ledger._conn.execute("UPDATE ledger SET verdict = 'reject' WHERE mutation_id = 'mut-4'")

    with pytest.raises(sqlite3.IntegrityError):
        ledger._conn.execute("DELETE FROM ledger WHERE mutation_id = 'mut-4'")


async def test_7_running_a_wiring_does_not_append_to_the_ledger(store_root):
    import json
    from pathlib import Path

    import databasise

    ledger = Ledger(store_root)
    before = ledger._conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]

    fixture_path = (
        Path(__file__).resolve().parent.parent / "fixtures" / "wiring-tracer.json"
    )
    with fixture_path.open("r", encoding="utf-8") as f:
        wiring_doc = json.load(f)

    await databasise.run_wiring(
        wiring_doc,
        store_root=store_root,
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
    )

    after = ledger._conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
    assert after == before


def test_8_active_pointer_on_unknown_mutation_id_returns_none_and_on_a_single_record_returns_it(
    store_root,
):
    ledger = Ledger(store_root)

    assert ledger.active_pointer("no-such-mutation") is None

    ledger.append(_record(mutation_id="mut-5", verdict="promote"))
    only = ledger.active_pointer("mut-5")
    assert only is not None
    assert only.verdict == "promote"


# --------------------------------------------------------------------------------------------- #
# 07-01-PLAN.md Task 1: the four additive columns (change_origin, record_kind, minted_version,
# targets_version) round-trip and do not disturb the append-only triggers.
# --------------------------------------------------------------------------------------------- #


def test_new_columns_round_trip(store_root):
    ledger = Ledger(store_root)
    record = _record(
        mutation_id="mut-6",
        change_origin="machine_mutation",
        record_kind="rollback",
        minted_version="2.0.0",
        targets_version="1.0.0",
    )

    ledger.append(record)
    [stored] = ledger.history("mut-6")

    assert stored.change_origin == "machine_mutation"
    assert stored.record_kind == "rollback"
    assert stored.minted_version == "2.0.0"
    assert stored.targets_version == "1.0.0"


def test_ledger_rejects_update_and_delete_after_the_new_columns_land(store_root):
    ledger = Ledger(store_root)
    ledger.append(_record(mutation_id="mut-7"))

    with pytest.raises(sqlite3.IntegrityError):
        ledger._conn.execute(
            "UPDATE ledger SET change_origin = 'machine_mutation' WHERE mutation_id = 'mut-7'"
        )

    with pytest.raises(sqlite3.IntegrityError):
        ledger._conn.execute("DELETE FROM ledger WHERE mutation_id = 'mut-7'")


def test_generation_state_reads_minted_or_targeted_version(store_root):
    ledger = Ledger(store_root)
    assert ledger.generation_state("gen-alias", "1.0.0") is None

    ledger.append(
        _record(
            mutation_id="naive",
            alias="gen-alias",
            change_origin="human_edit",
            record_kind="promotion",
            minted_version="1.0.0",
        )
    )
    minted = ledger.generation_state("gen-alias", "1.0.0")
    assert minted is not None
    assert minted.minted_version == "1.0.0"

    ledger.append(
        _record(
            mutation_id="bypass",
            alias="gen-alias",
            change_origin="human_edit",
            record_kind="rollback",
            minted_version="2.0.0",
            targets_version="1.0.0",
        )
    )
    latest_for_1_0_0 = ledger.generation_state("gen-alias", "1.0.0")
    assert latest_for_1_0_0 is not None
    assert latest_for_1_0_0.record_kind == "rollback"
    assert latest_for_1_0_0.targets_version == "1.0.0"
