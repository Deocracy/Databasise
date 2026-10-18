"""Phase 10 review WR-07: the read-only probes never open a Cozo client on a directory that is not a
RocksDB database, so they create no file; the error handling names the expected store and OS errors
and lets programming errors surface."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest

from databasise.stores import probes
from databasise.stores.graph import CozoGraphStore, _ClientRegistry
from databasise.stores.kv import SqliteKVStore
from databasise.stores.probes import probe_graph, probe_kv, probe_vector


def _tree(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


def test_an_empty_graph_directory_is_corrupted_and_nothing_is_created(tmp_path):
    (tmp_path / "graph.cozo").mkdir()
    before = _tree(tmp_path)

    assert probe_graph(tmp_path) == "corrupted"

    assert _tree(tmp_path) == before
    assert [key for key in _ClientRegistry._entries if key.startswith(str(tmp_path))] == []


def test_a_data_directory_without_current_is_corrupted_and_nothing_is_created(tmp_path):
    (tmp_path / "graph.cozo" / "data").mkdir(parents=True)
    before = _tree(tmp_path)

    assert probe_graph(tmp_path) == "corrupted"

    assert _tree(tmp_path) == before


def test_garbage_inside_the_graph_directory_is_corrupted_and_nothing_is_created(tmp_path):
    data = tmp_path / "graph.cozo" / "data"
    data.mkdir(parents=True)
    (data / "CURRENT").write_text("garbage")
    before = _tree(tmp_path)

    assert probe_graph(tmp_path) == "corrupted"

    assert _tree(tmp_path) == before


def test_a_garbage_graph_file_is_corrupted_and_nothing_is_created(tmp_path):
    (tmp_path / "graph.cozo").write_text("not a database")
    before = _tree(tmp_path)

    assert probe_graph(tmp_path) == "corrupted"

    assert _tree(tmp_path) == before


def test_a_missing_graph_is_absent(tmp_path):
    assert probe_graph(tmp_path) == "absent"
    assert _tree(tmp_path) == []


async def test_a_real_populated_graph_is_still_ok(tmp_path):
    store = CozoGraphStore("g", "ws", tmp_path)
    await store.upsert_node("n1", {"a": 1})
    await store.index_done_callback()
    await store.finalize()

    assert probe_graph(tmp_path / "ws" / "g") == "ok"


def test_a_zero_byte_kv_database_is_absent_not_corrupted_and_nothing_is_created(tmp_path):
    (tmp_path / "kv.sqlite3").write_bytes(b"")
    before = _tree(tmp_path)

    assert probe_kv(tmp_path) == "absent"

    assert _tree(tmp_path) == before


def test_a_garbage_kv_database_is_corrupted(tmp_path):
    (tmp_path / "kv.sqlite3").write_bytes(b"this is not a sqlite database" * 20)

    assert probe_kv(tmp_path) == "corrupted"


def test_a_permission_error_reading_a_vector_namespace_is_corrupted(tmp_path, monkeypatch):
    def _denied(_path):
        raise PermissionError("denied")

    monkeypatch.setattr(probes, "load_committed", _denied)

    assert probe_vector(tmp_path) == "corrupted"


def test_a_programming_error_in_a_probe_surfaces(tmp_path, monkeypatch):
    def _bug(_path):
        raise AttributeError("a bug, not a store state")

    monkeypatch.setattr(probes, "load_committed", _bug)

    with pytest.raises(AttributeError):
        probe_vector(tmp_path)


# --------------------------------------------------------------------------------------------- #
# Iteration-2 WR-02 and WR-03
# --------------------------------------------------------------------------------------------- #


async def _closed_kv(store_root: Path, workspace: str, namespace: str) -> Path:
    store = SqliteKVStore(namespace, workspace, store_root)
    await store.upsert({"a": {"x": 1}})
    await store.index_done_callback()
    await store.finalize()
    return next(Path(store_root).rglob("kv.sqlite3")).parent


async def test_a_relative_store_root_probes_a_real_kv_store_as_ok(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    directory = await _closed_kv(Path("rel_root"), "ws", "t")

    assert not directory.is_absolute()
    assert probe_kv(directory) == "ok"


async def test_health_with_a_relative_store_root_does_not_raise(tmp_path, monkeypatch):
    from databasise.tests.seam.test_health_probe import _WS, _engine

    monkeypatch.chdir(tmp_path)
    await _closed_kv(Path("rel_root"), _WS, "text_chunks")
    engine = _engine(Path("rel_root"), monkeypatch)

    report = await engine.health()

    assert report.stores["kv:text_chunks"] == "ok"


async def test_a_kv_wal_without_its_shm_is_probed_and_no_file_is_created(tmp_path):
    live = tmp_path / "live"
    live.mkdir()
    conn = sqlite3.connect(live / "kv.sqlite3")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE kv (id TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.execute("INSERT INTO kv VALUES ('a', '1')")
    conn.commit()
    restored = tmp_path / "restored"
    restored.mkdir()
    try:  # a backup or crash leftover: the database and its -wal, but no -shm
        shutil.copy(live / "kv.sqlite3", restored / "kv.sqlite3")
        shutil.copy(live / "kv.sqlite3-wal", restored / "kv.sqlite3-wal")
    finally:
        conn.close()
    before = _tree(restored)
    assert "kv.sqlite3-shm" not in before and "kv.sqlite3-wal" in before

    assert probe_kv(restored) == "ok"

    assert _tree(restored) == before


async def test_a_live_kv_store_whose_schema_is_still_in_the_wal_is_ok(tmp_path):
    store = SqliteKVStore("t", "ws", tmp_path)  # the table exists only in the unreplayed -wal
    try:
        assert probe_kv(next(tmp_path.rglob("kv.sqlite3")).parent) == "ok"
    finally:
        await store.finalize()


async def test_a_graph_without_its_manifest_file_is_corrupted_and_nothing_is_created(tmp_path):
    store = CozoGraphStore("g", "ws", tmp_path)
    await store.upsert_node("n1", {"a": 1})
    await store.index_done_callback()
    await store.finalize()
    directory = tmp_path / "ws" / "g"
    (directory / "graph.cozo" / "manifest").unlink()
    before = _tree(directory)

    assert probe_graph(directory) == "corrupted"

    assert _tree(directory) == before


async def test_health_on_a_graph_without_its_manifest_file_creates_no_file(store_root, monkeypatch):
    from databasise.tests.seam.test_health_probe import _WS, _engine

    graph_dir = store_root / _WS / "chunk_entity_relation"
    store = CozoGraphStore("chunk_entity_relation", _WS, store_root)
    await store.upsert_node("n1", {"a": 1})
    await store.index_done_callback()
    await store.finalize()
    (graph_dir / "graph.cozo" / "manifest").unlink()
    engine = _engine(store_root, monkeypatch)
    before = _tree(store_root)

    report = await engine.health()

    assert report.stores["graph:chunk_entity_relation"] == "corrupted"
    assert _tree(store_root) == before


async def test_health_on_an_empty_graph_directory_creates_no_file(store_root, monkeypatch):
    from databasise.tests.seam.test_health_probe import _WS, _engine

    graph_dir = store_root / _WS / "chunk_entity_relation" / "graph.cozo"
    graph_dir.mkdir(parents=True)
    engine = _engine(store_root, monkeypatch)  # its trace store creates trace.db at construction
    before = _tree(store_root)

    report = await engine.health()

    assert report.stores["graph:chunk_entity_relation"] == "corrupted"
    assert _tree(store_root) == before
