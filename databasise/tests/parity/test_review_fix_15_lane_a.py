"""Phase 15 review-fix checks for the parity CLIs (15-REVIEW.md, lane A findings)."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

import databasise.parity as parity_pkg

_DRIVER_PATH = Path(parity_pkg.__file__).resolve().parent / "v1_driver_script.py"


@pytest.fixture
def driver(monkeypatch):
    """Load the v1 driver with stand-in v1 modules; v1 itself is never imported here."""
    stubs = {
        "lightrag": {"LightRAG": object},
        "lightrag.base": {"QueryParam": lambda **kw: types.SimpleNamespace(**kw)},
        "lightrag.llm": {},
        "lightrag.llm.openai": {"openai_complete_if_cache": None, "openai_embed": None},
        "lightrag.utils": {"EmbeddingFunc": None},
    }
    for name, attrs in stubs.items():
        module = types.ModuleType(name)
        for key, value in attrs.items():
            setattr(module, key, value)
        monkeypatch.setitem(sys.modules, name, module)
    spec = importlib.util.spec_from_file_location("_v1_driver_under_test", _DRIVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _job():
    return {"mode": "hybrid", "query": "q", "hl_keywords": [], "ll_keywords": [], "working_dir": "/nonexistent"}


def _fake_rag(response):
    class _Rag:
        async def aquery_llm(self, query, param):
            return response

        async def finalize_storages(self):
            return None

    async def _build(working_dir):
        return _Rag()

    return _build


def test_status_less_fail_response_is_an_empty_retrieval(driver, monkeypatch):
    """A-WR-02: v1's third shape (no status, no metadata, fail_response answer) is not an exception."""
    response = {"llm_response": {"content": "Sorry, no answer.", "response_iterator": None, "is_streaming": False}}
    monkeypatch.setattr(driver, "_build_rag", _fake_rag(response))
    result = asyncio.run(driver._run(_job()))
    assert result["chunk_ids"] == [] and result["entity_ids"] == [] and result["relation_ids"] == []
    assert result["answer"] == "Sorry, no answer."


def test_failure_status_with_empty_metadata_still_raises(driver, monkeypatch):
    """A-WR-02: v1's exception path (status failure, metadata {}) still exits through the named error."""
    response = {"status": "failure", "message": "Query failed: boom", "data": {}, "metadata": {}, "llm_response": {}}
    monkeypatch.setattr(driver, "_build_rag", _fake_rag(response))
    with pytest.raises(driver.V1QueryFailedError, match="boom"):
        asyncio.run(driver._run(_job()))


def _v1_dir_with_one_chunk(tmp_path):
    v1_dir = tmp_path / "v1"
    v1_dir.mkdir()
    (v1_dir / "kv_store_text_chunks.json").write_text(json.dumps({"chunk-1": {"content": "text"}}), encoding="utf-8")
    return v1_dir


def test_verify_import_creates_no_text_chunks_namespace(tmp_path):
    """A-WR-04: verifying a workspace with no text_chunks namespace reads, it never creates one."""
    from databasise.parity.import_index import verify_import

    store_root = tmp_path / "store"
    (store_root / "ws").mkdir(parents=True)
    result = asyncio.run(verify_import(_v1_dir_with_one_chunk(tmp_path), store_root, "ws"))
    assert result.status == "inconclusive"
    assert [v.assertion for v in result.violations] == ["chunk-text"]
    assert list((store_root / "ws").iterdir()) == []


def test_verify_import_reads_v2_chunk_text_without_rewriting_the_store(tmp_path):
    """A-WR-04: a committed v2 chunk is read back read-only and compared."""
    from databasise.parity.import_index import verify_import
    from databasise.stores.kv import SqliteKVStore

    store_root = tmp_path / "store"
    store = SqliteKVStore(namespace="text_chunks", workspace="ws", store_root=store_root)
    asyncio.run(store.upsert({"chunk-1": {"content": "text"}}))
    asyncio.run(store.index_done_callback())
    asyncio.run(store.finalize())
    before = sorted(p.name for p in (store_root / "ws" / "text_chunks").iterdir())
    result = asyncio.run(verify_import(_v1_dir_with_one_chunk(tmp_path), store_root, "ws"))
    assert result.status == "verified"
    assert sorted(p.name for p in (store_root / "ws" / "text_chunks").iterdir()) == before


def test_verify_import_refuses_a_missing_v1_index(tmp_path):
    """A-WR-05: a typo'd --v1-working-dir over an empty v2 workspace is refused, never verified."""
    from databasise.parity.import_index import verify_import

    store_root = tmp_path / "store"
    (store_root / "ws").mkdir(parents=True)
    result = asyncio.run(verify_import(tmp_path / "no-such-v1", store_root, "ws"))
    assert result.status == "refused"
    assert [v.assertion for v in result.violations] == ["precondition"]


def test_verify_import_flags_a_v2_graph_with_no_v1_graph(tmp_path, monkeypatch):
    """A-WR-05: the reverse of D-06 (v2 graph present, v1 graph absent) is a graph-topology violation."""
    from databasise.parity import import_index

    store_root = tmp_path / "store"
    (store_root / "ws").mkdir(parents=True)
    v1_dir = tmp_path / "v1"
    v1_dir.mkdir()
    monkeypatch.setattr(import_index, "_v2_graph", lambda root, ws: ({"a"}, set()))
    result = asyncio.run(import_index.verify_import(v1_dir, store_root, "ws"))
    assert result.status == "inconclusive"
    assert [v.assertion for v in result.violations] == ["graph-topology"]


def test_import_index_verify_on_a_missing_store_root_writes_nothing(tmp_path, capsys):
    """A-WR-04: --verify --store-root <typo> takes no lock, so it creates no root or .engine.lock."""
    from databasise.parity import import_index

    typo = tmp_path / "typo"
    argv = ["--verify", "--store-root", str(typo), "--workspace", "ws", "--v1-working-dir", str(_v1_dir_with_one_chunk(tmp_path))]
    assert import_index.main(argv) == 1
    assert not typo.exists()
    assert "[refused] precondition" in capsys.readouterr().out


def test_a_refused_hipporag_build_leaves_the_unverified_marker(tmp_path, monkeypatch):
    """A-WR-06: a build its own verification refuses is marked on disk as unverified."""
    from databasise.parity import build_hipporag_index as bhi

    async def _cyclic(*args, **kwargs):
        return {"cycle": ["a", "b"]}

    monkeypatch.setattr(bhi._scheduler, "run_wiring", _cyclic)
    with pytest.raises(bhi.HippoRAGIndexBuildRefusedError):
        asyncio.run(bhi.build_index(store_root=tmp_path, workspace="ws", clients={}))
    assert bhi.unverified_build_marker(tmp_path, "ws").is_file()


def test_cross_modality_preflight_refuses_an_unverified_hipporag_build(tmp_path, monkeypatch):
    """A-WR-06: preflight refuses an index its builder did not verify, even when its chunks exist."""
    from databasise.parity import build_hipporag_index as bhi
    from databasise.parity import run_cross_modality as rcm

    monkeypatch.setattr(rcm, "_require_namespace", lambda *args, **kwargs: None)
    (tmp_path / "ws").mkdir()
    bhi.unverified_build_marker(tmp_path, "ws").write_text("{}", encoding="utf-8")
    with pytest.raises(rcm.MissingArmIndexError, match="did not pass its builder's verification"):
        rcm.preflight(store_root=tmp_path, workspace="ws")


@pytest.mark.parametrize(
    ("result", "code"),
    [
        ({"cycle": ["a", "b"]}, 3),
        ({"run_record": {"partial": True, "degraded": False}, "provided": {}}, 3),
        ({"run_record": {"partial": False, "degraded": True}, "provided": {}}, 3),
        ({"run_record": {"partial": False, "degraded": False}, "provided": {}}, 0),
    ],
)
def test_run_arm_exit_code_reports_an_inconclusive_run(result, code, tmp_path, monkeypatch):
    """A-WR-08: a cyclic, partial or degraded run exits 3 (D-03), a complete one 0."""
    from databasise.parity import import_index, run_arm

    async def _fake_run_arm(arm, query):
        return result

    monkeypatch.setattr(import_index, "DEFAULT_STORE_ROOT", tmp_path)
    monkeypatch.setattr(run_arm, "run_arm", _fake_run_arm)
    assert run_arm.main(["--arm", "naive", "--query", "q", "--spend"]) == code


def _drifted(*args, **kwargs):
    from databasise.parity.corpus import CorpusDriftError

    raise CorpusDriftError("document d1 digest mismatch")


def test_import_index_refuses_a_drifted_snapshot_by_name(tmp_path, monkeypatch, capsys):
    """A-WR-09: the snapshot read runs inside the refusal handler, so drift is one line and exit 1."""
    from databasise.parity import import_index

    monkeypatch.setattr(import_index, "_import_workspace", _drifted)
    assert import_index.main(["--verify", "--store-root", str(tmp_path)]) == 1
    assert capsys.readouterr().err.strip() == "CorpusDriftError: document d1 digest mismatch"


def test_import_index_refuses_a_corrupted_vector_store_by_name(tmp_path, monkeypatch, capsys):
    """A-WR-09: a VectorStoreCorruptedError from the run is a named refusal, not a traceback."""
    from databasise.parity import import_index
    from databasise.stores.vector import VectorStoreCorruptedError

    async def _corrupt(*args, **kwargs):
        raise VectorStoreCorruptedError(tmp_path / "vector.faiss", "sha256:a", "sha256:b")

    monkeypatch.setattr(import_index, "verify_import", _corrupt)
    assert import_index.main(["--verify", "--store-root", str(tmp_path), "--workspace", "ws"]) == 1
    assert capsys.readouterr().err.strip().startswith("VectorStoreCorruptedError: ")


def test_build_hipporag_index_estimate_refuses_a_drifted_snapshot_by_name(monkeypatch, capsys):
    """A-WR-09: the estimate-only path refuses drift by name instead of a traceback."""
    from databasise.parity import build_hipporag_index as bhi

    monkeypatch.setattr(bhi, "load_snapshot", _drifted)
    assert bhi.main([]) == 1
    assert capsys.readouterr().err.strip() == "CorpusDriftError: document d1 digest mismatch"


def test_v1_arm_subprocess_error_names_the_driver_failure_line():
    """A-WR-03: the message carries the driver's last non-log line, not v1's start-up INFO lines."""
    from databasise.parity.v1_arm import V1ArmSubprocessError

    log = ["INFO: start-up line " + "x" * 300] * 10
    stderr = "\n".join([*log, "ERROR: Query failed: boom", "V1QueryFailedError: boom"])
    exc = V1ArmSubprocessError(1, stderr)
    assert str(exc) == "v1 driver subprocess exited 1: V1QueryFailedError: boom"
    assert exc.stderr == stderr
    assert str(V1ArmSubprocessError(1, "  ")) == "v1 driver subprocess exited 1: (no stderr)"
