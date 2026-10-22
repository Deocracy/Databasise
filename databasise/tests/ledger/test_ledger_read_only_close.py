"""16-REVIEW-ITER2 WR-01: a read-only ledger handle decides its close checkpoint at close time."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from databasise.ledger.ledger import Ledger, LedgerRecord


def _record(alias: str, mutation_id: str) -> LedgerRecord:
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
        minted_version="1.0.0",
    )


def _seed(root: Path) -> bytes:
    with Ledger(root) as ledger:
        ledger.append(_record("a", "m1"))
    assert sorted(os.listdir(root)) == ["ledger.db"]
    return (root / "ledger.db").read_bytes()


def _open_and_read(root: Path) -> Ledger:
    handle = Ledger.open_existing(root, read_only=True)
    assert handle is not None
    assert [e.alias for e in handle.history_for_alias("a")] == ["a"]
    return handle


@pytest.mark.parametrize("a_closes_first", [True, False])
def test_overlapping_read_only_handles_leave_no_wal_or_shm(tmp_path: Path, a_closes_first: bool) -> None:
    before = _seed(tmp_path)
    a = _open_and_read(tmp_path)
    b = _open_and_read(tmp_path)
    first, last = (a, b) if a_closes_first else (b, a)
    first.close()
    last.close()
    assert sorted(os.listdir(tmp_path)) == ["ledger.db"]
    _open_and_read(tmp_path).close()  # the overlap does not leave the files for later reads
    assert sorted(os.listdir(tmp_path)) == ["ledger.db"]
    assert (tmp_path / "ledger.db").read_bytes() == before


def test_reader_closing_last_does_not_checkpoint_a_writers_frames(tmp_path: Path) -> None:
    _seed(tmp_path)
    reader = _open_and_read(tmp_path)
    with Ledger(tmp_path) as writer:
        writer.append(_record("b", "m2"))
    after_writer = (tmp_path / "ledger.db").read_bytes()
    reader.close()
    assert (tmp_path / "ledger.db").read_bytes() == after_writer
    check = _open_and_read(tmp_path)
    assert [e.alias for e in check.history_for_alias("b")] == ["b"]
    check.close()
