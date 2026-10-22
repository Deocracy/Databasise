"""Phase 16 lane B review fixes for the operator read methods in ``databasise/seam/engine.py``."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from databasise.ledger.ledger import Ledger, LedgerRecord
from databasise.seam.corpus import Page
from databasise.seam.engine import Databasise


def _record(alias: str, version: str, mutation_id: str = "m1") -> LedgerRecord:
    return LedgerRecord(
        mutation_id=mutation_id,
        mutation_class="wiring",
        parent=None,
        arm_instance_hashes=["h"],
        effect_size=None,
        verdict=None,
        evidence_pointer=None,
        proposer_id="operator",
        depth_label=None,
        tier_of_decision=None,
        decomposition_ratio=None,
        opaque_ttl_renewals=[],
        parity_records=[],
        promotion_provenance="operator-asserted",
        promotion_trace_ids=["t"],
        change_origin="test",
        record_kind="promotion",
        alias=alias,
        minted_version=version,
    )


def _seed_ledger(root: Path) -> None:
    with Ledger(root) as ledger:
        ledger.append(_record("a", "1.0.0"))


def test_ledger_reads_leave_no_wal_or_shm_files(tmp_path: Path) -> None:
    # WR-01: the first read of a WAL ledger made -wal/-shm and the no-checkpoint close kept them
    _seed_ledger(tmp_path)
    engine = Databasise(store_root=tmp_path, workspace="ws")
    before = sorted(os.listdir(tmp_path))
    assert "ledger.db-wal" not in before
    assert [r["alias"] for r in asyncio.run(engine.ledger_aliases())] == ["a"]
    assert asyncio.run(engine.ledger_history("a", Page(limit=10, offset=0)))["total"] == 1
    assert sorted(os.listdir(tmp_path)) == before
