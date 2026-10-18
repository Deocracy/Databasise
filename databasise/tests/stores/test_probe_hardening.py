"""Phase 10 review WR-07: the read-only probes never open a Cozo client on a directory that is not a
RocksDB database, so they create no file; the error handling names the expected store and OS errors
and lets programming errors surface."""

from __future__ import annotations

from pathlib import Path

import pytest

from databasise.stores import probes
from databasise.stores.graph import CozoGraphStore, _ClientRegistry
from databasise.stores.probes import probe_graph, probe_kv, probe_vector


def _tree(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


def test_an_empty_graph_directory_is_corrupted_and_nothing_is_created(tmp_path):
    (tmp_path / "graph.cozo").mkdir()
    before = _tree(tmp_path)

    assert probe_graph(tmp_path) == "corrupted"

    assert _tree(tmp_path) == before
    assert not _ClientRegistry._entries


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


async def test_health_on_an_empty_graph_directory_creates_no_file(store_root, monkeypatch):
    from databasise.tests.seam.test_health_probe import _WS, _engine

    graph_dir = store_root / _WS / "chunk_entity_relation" / "graph.cozo"
    graph_dir.mkdir(parents=True)
    engine = _engine(store_root, monkeypatch)  # its trace store creates trace.db at construction
    before = _tree(store_root)

    report = await engine.health()

    assert report.stores["graph:chunk_entity_relation"] == "corrupted"
    assert _tree(store_root) == before
