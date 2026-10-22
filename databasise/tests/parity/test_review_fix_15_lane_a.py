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


def test_import_index_verify_on_a_missing_store_root_writes_nothing(tmp_path, capsys):
    """A-WR-04: --verify --store-root <typo> takes no lock, so it creates no root or .engine.lock."""
    from databasise.parity import import_index

    typo = tmp_path / "typo"
    argv = ["--verify", "--store-root", str(typo), "--workspace", "ws", "--v1-working-dir", str(_v1_dir_with_one_chunk(tmp_path))]
    assert import_index.main(argv) == 1
    assert not typo.exists()
    assert "[refused] precondition" in capsys.readouterr().out


def test_v1_arm_subprocess_error_names_the_driver_failure_line():
    """A-WR-03: the message carries the driver's last non-log line, not v1's start-up INFO lines."""
    from databasise.parity.v1_arm import V1ArmSubprocessError

    log = ["INFO: start-up line " + "x" * 300] * 10
    stderr = "\n".join([*log, "ERROR: Query failed: boom", "V1QueryFailedError: boom"])
    exc = V1ArmSubprocessError(1, stderr)
    assert str(exc) == "v1 driver subprocess exited 1: V1QueryFailedError: boom"
    assert exc.stderr == stderr
    assert str(V1ArmSubprocessError(1, "  ")) == "v1 driver subprocess exited 1: (no stderr)"
