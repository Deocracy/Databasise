"""Phase 15 review-fix checks for the parity CLIs (15-REVIEW.md, lane A findings)."""

from __future__ import annotations

import asyncio
import importlib.util
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
