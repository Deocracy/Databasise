"""Cozo RocksDB connectivity smoke test.

This is a standalone probe that proves cozo-embedded (RocksDB backend) can be
opened, written to, and read back in-process on this machine. It is throwaway
scaffolding — not the real CozoGraphStorage adapter.

Usage:
    python -m lightrag.kg.cozo_smoke

Exit code 0 = success. Non-zero = failure (exception propagates).

Key design choices (per Plan 01, D-P1.1-04 landmine 2):
    - All client.run() calls use dataframe=False so results are plain
      dict/list, not pandas DataFrames.  This validates the marshalling
      assumption the async pipeline (Plan 02) will rely on.
"""

import json
import os
import shutil
import sys
import tempfile

from pycozo.client import Client


def run_smoke(db_path: str) -> bool:
    """Open a RocksDB-backed Cozo database, round-trip a record, and return True.

    Args:
        db_path: Filesystem path for the RocksDB database directory.

    Returns:
        True on success.

    Raises:
        AssertionError: If the round-tripped value does not match the written value.
        Exception: Re-raised on any Cozo / OS error.
    """
    client = Client("rocksdb", db_path)

    try:
        # 1. Create a stored relation mirroring the Plan 02 node schema:
        #    nodes {id: String => attrs: Json}
        #
        # Note on dataframe=False: pycozo 0.7.6's Client.run() has no
        # 'dataframe' keyword argument. The return format is determined at
        # construction time: if pandas is importable the client wraps results
        # in a DataFrame; otherwise (or when Client is constructed without
        # enabling it) run() returns a plain dict {"headers": [...], "rows": [...]}.
        # We rely on this plain-dict path here — the adapter (Plan 02) will
        # ensure it gets the plain dict by checking the return type and
        # converting if needed (the D-P1.1-04 landmine: "wrap in run_in_executor,
        # pass dataframe=False or convert"). Since dataframe=False is not a
        # valid kwarg, explicit conversion is the correct mitigation pattern.
        client.run(":create nodes {id: String => attrs: Json}", {})

        # 2. Insert a row via :put with parameter binding
        test_id = "entity::smoke-test-node"
        test_attrs = {"label": "SmokeTest", "weight": 1.0, "source": "cozo_smoke.py"}
        client.run(
            "?[id, attrs] <- [[$id, $attrs]] :put nodes {id => attrs}",
            {"id": test_id, "attrs": test_attrs},
        )

        # 3. Read back with a *nodes{...} query; result is dict or DataFrame
        result = client.run(
            "?[id, attrs] := *nodes{id, attrs}, id = $id",
            {"id": test_id},
        )

        # Normalise result to plain dict if pandas returned a DataFrame
        if hasattr(result, "to_dict"):
            # DataFrame — convert to the same {"headers": [...], "rows": [...]} shape
            records = result.values.tolist()
            result = {"headers": list(result.columns), "rows": records}

        # result is a dict: {"headers": [...], "rows": [[val, val], ...]}
        rows = result.get("rows", [])
        assert len(rows) == 1, f"Expected 1 row, got {len(rows)}: {result}"

        returned_id = rows[0][0]
        returned_attrs = rows[0][1]

        assert returned_id == test_id, (
            f"id round-trip mismatch: wrote {test_id!r}, read {returned_id!r}"
        )

        # Cozo serialises Json columns; normalise both sides via json round-trip
        # to avoid any str-vs-dict type ambiguity in comparison.
        if isinstance(returned_attrs, str):
            returned_attrs = json.loads(returned_attrs)

        assert returned_attrs == test_attrs, (
            f"attrs round-trip mismatch:\n  wrote  {test_attrs!r}\n  read   {returned_attrs!r}"
        )

        # 4. Cleanup: drop the stored relation (Cozo system command ::remove)
        client.run("::remove nodes", {})

        return True

    finally:
        # 5. Close the client (RocksDB file handles released)
        client.close()


def main() -> None:
    """Entry point for `python -m lightrag.kg.cozo_smoke`."""
    tmp_dir = tempfile.mkdtemp(prefix="cozo_smoke_")
    db_path = os.path.join(tmp_dir, "smoke_test.db")

    try:
        print(f"[cozo_smoke] Opening RocksDB database at: {db_path}")
        ok = run_smoke(db_path)
        if ok:
            print("[cozo_smoke] SMOKE_OK — Cozo RocksDB create/put/query/teardown round-trip passed.")
    finally:
        # Remove the temp db directory regardless of outcome
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"[cozo_smoke] Temp directory cleaned up: {tmp_dir}")


if __name__ == "__main__":
    main()
    sys.exit(0)
