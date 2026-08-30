"""End-to-end tracer: submit a wiring, run it, stamp a schema-valid run record.

Covers plan 01-02's <behavior> tests 1-7: the trivial two-node wiring drives every layer this
phase touches (identity, parts, validator, runner, stores, trace) on one proven path.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import textwrap
from pathlib import Path

from databasise.identity.canon import config_hash

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "wiring-tracer.json"


def _load_fixture() -> dict:
    with FIXTURE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


async def test_tracer_runs_end_to_end_and_produces_a_schema_valid_run_record(
    store_root, assert_valid_trace
):
    import databasise

    wiring_doc = _load_fixture()
    record = await databasise.run_wiring(
        wiring_doc,
        store_root=store_root,
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
    )

    assert_valid_trace(record)
    assert record["partial"] is False
    assert record["degraded"] is False
    assert record["stop_reason"] is None
    assert len(record["nodes"]) == 2


async def test_kv_node_write_is_readable_back_from_the_sqlite_store(store_root):
    import databasise
    from databasise.stores.kv import SqliteKVStore

    wiring_doc = _load_fixture()
    await databasise.run_wiring(
        wiring_doc,
        store_root=store_root,
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
    )

    verify_store = SqliteKVStore(
        namespace=databasise.TRACER_KV_NAMESPACE,
        workspace=databasise.TRACER_WORKSPACE,
        store_root=store_root,
    )
    value = await verify_store.get_by_id("store")
    await verify_store.finalize()

    assert value is not None
    assert value["node_id"] == "store"


async def test_instance_hash_is_a_64_char_lowercase_hex_digest_and_never_equals_node_id(
    store_root,
):
    import databasise

    wiring_doc = _load_fixture()
    record = await databasise.run_wiring(
        wiring_doc,
        store_root=store_root,
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
    )

    for node in record["nodes"]:
        h = node["instance_hash"]
        assert len(h) == 64
        assert h == h.lower()
        assert all(c in "0123456789abcdef" for c in h)
        assert h != node["node_id"]


async def test_identity_is_stable_across_runs_while_run_id_differs(store_root):
    import databasise

    wiring_doc = _load_fixture()
    record1 = await databasise.run_wiring(
        wiring_doc,
        store_root=store_root,
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
    )
    record2 = await databasise.run_wiring(
        wiring_doc,
        store_root=store_root,
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
    )

    hashes1 = {n["node_id"]: n["instance_hash"] for n in record1["nodes"]}
    hashes2 = {n["node_id"]: n["instance_hash"] for n in record2["nodes"]}
    assert hashes1 == hashes2
    assert record1["run_id"] != record2["run_id"]


async def test_mutating_one_nodes_config_changes_only_that_nodes_instance_hash(store_root):
    import databasise

    wiring_doc = _load_fixture()
    record_before = await databasise.run_wiring(
        wiring_doc,
        store_root=store_root,
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
    )

    mutated_doc = copy.deepcopy(wiring_doc)
    mutated_doc["nodes"]["store"]["config"]["note"] += "x"  # single-byte mutation
    record_after = await databasise.run_wiring(
        mutated_doc,
        store_root=store_root,
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
    )

    before = {n["node_id"]: n["instance_hash"] for n in record_before["nodes"]}
    after = {n["node_id"]: n["instance_hash"] for n in record_after["nodes"]}

    assert before["store"] != after["store"]
    assert before["pass"] == after["pass"]


def test_config_max_concurrency_is_covered_by_config_hash():
    base = {"max_concurrency": 2, "note": "tracer-fixture"}
    changed = {"max_concurrency": 3, "note": "tracer-fixture"}

    assert config_hash(base) != config_hash(changed)


def test_importing_databasise_spawns_no_child_process_or_listening_socket():
    script = textwrap.dedent(
        """
        import os

        def _listening_socket_count():
            count = 0
            for path in ("/proc/self/net/tcp", "/proc/self/net/tcp6"):
                try:
                    with open(path) as f:
                        lines = f.readlines()[1:]
                except FileNotFoundError:
                    continue
                for line in lines:
                    fields = line.split()
                    if len(fields) > 3 and fields[3] == "0A":
                        count += 1
            return count

        before_tasks = len(os.listdir("/proc/self/task"))
        before_sockets = _listening_socket_count()

        import databasise  # noqa: F401

        after_tasks = len(os.listdir("/proc/self/task"))
        after_sockets = _listening_socket_count()

        assert after_tasks <= before_tasks, f"task count grew: {before_tasks} -> {after_tasks}"
        # The netns this process shares may already show pre-existing listening sockets
        # (container-wide, not caused by this import) — the claim under test is that importing
        # databasise adds none of its own, i.e. the count does not grow across the import.
        assert after_sockets <= before_sockets, (
            f"listening socket count grew across import: before={before_sockets} "
            f"after={after_sockets}"
        )
        print("OK")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    assert result.stdout.strip() == "OK"
