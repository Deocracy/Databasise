"""Phase 15 review-fix checks for the parity CLIs (15-REVIEW-ITER3-A.md, lane A iteration 3)."""

from __future__ import annotations

import asyncio
import json
import os


def test_verify_import_refuses_a_kv_file_that_is_not_a_database(tmp_path):
    """ITER3-A-WR-01: a corrupt text_chunks kv.sqlite3 is a precondition refusal, not a DatabaseError traceback."""
    from databasise.parity.import_index import verify_import

    v1_dir = tmp_path / "v1"
    v1_dir.mkdir()
    (v1_dir / "kv_store_text_chunks.json").write_text(json.dumps({"chunk-1": {"content": "text"}}), encoding="utf-8")
    ns = tmp_path / "store" / "ws" / "text_chunks"
    ns.mkdir(parents=True)
    (ns / "kv.sqlite3").write_bytes(os.urandom(4096))

    result = asyncio.run(verify_import(v1_dir, tmp_path / "store", "ws"))
    assert result.status == "refused"
    assert [v.assertion for v in result.violations] == ["precondition"]
    assert "unreadable read-only" in result.violations[0].detail
