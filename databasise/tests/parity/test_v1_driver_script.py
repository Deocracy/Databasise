"""The v1 parity arm's driver script and its harness-side wrapper (15-12-PLAN.md, TOOL-07, D-08).

The driver runs under v1's interpreter and imports ``lightrag`` at module level, so these tests load
it from its path with stub ``lightrag*`` modules in ``sys.modules`` and replace ``_build_rag`` with a
stub rag. No v1 interpreter, no env file and no provider call is involved (D-24).
"""

from __future__ import annotations

import asyncio
import importlib.util
import io
import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest

_DRIVER_PATH = Path(__file__).resolve().parents[2] / "parity" / "v1_driver_script.py"


class _QueryParam:
    def __init__(self, **kwargs: Any) -> None:
        self.__dict__.update(kwargs)


class _StubRag:
    """Counts the three query entry points; ``aquery_llm`` returns the configured response."""

    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.calls: list[str] = []

    async def aquery_llm(self, query: str, param: Any) -> dict[str, Any]:
        self.calls.append("aquery_llm")
        return self.response

    async def aquery(self, query: str, param: Any) -> str:
        self.calls.append("aquery")
        return "second-retrieval answer"

    async def aquery_data(self, query: str, param: Any) -> dict[str, Any]:
        self.calls.append("aquery_data")
        return {"status": "success", "data": {}, "metadata": {}}

    async def finalize_storages(self) -> None:
        return None


def _load_driver(monkeypatch: pytest.MonkeyPatch, rag: _StubRag) -> types.ModuleType:
    stubs: dict[str, types.ModuleType] = {
        name: types.ModuleType(name)
        for name in ("lightrag", "lightrag.base", "lightrag.llm", "lightrag.llm.openai", "lightrag.utils")
    }
    stubs["lightrag"].LightRAG = object  # type: ignore[attr-defined]
    stubs["lightrag.base"].QueryParam = _QueryParam  # type: ignore[attr-defined]
    stubs["lightrag.llm.openai"].openai_complete_if_cache = None  # type: ignore[attr-defined]
    stubs["lightrag.llm.openai"].openai_embed = None  # type: ignore[attr-defined]
    stubs["lightrag.utils"].EmbeddingFunc = object  # type: ignore[attr-defined]
    for name, module in stubs.items():
        monkeypatch.setitem(sys.modules, name, module)

    spec = importlib.util.spec_from_file_location("v1_driver_script_under_test", _DRIVER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    async def _build_rag(working_dir: str) -> _StubRag:
        return rag

    module._build_rag = _build_rag
    return module


def _response(
    *,
    status: str = "success",
    chunks: list[str] | None = None,
    content: str | None = "ans",
    metadata: dict[str, Any] | None = None,
    message: str = "",
) -> dict[str, Any]:
    return {
        "status": status,
        "message": message,
        "data": {"chunks": [{"chunk_id": c} for c in chunks or []], "entities": [], "relationships": []},
        "metadata": metadata or {},
        "llm_response": {"content": content, "response_iterator": None, "is_streaming": False},
    }


def _job(tmp_path: Path, **extra: Any) -> dict[str, Any]:
    return {"mode": "hybrid", "query": "q", "working_dir": str(tmp_path), **extra}


def test_an_unpinned_hybrid_job_calls_aquery_llm_once(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    rag = _StubRag(_response(chunks=["c1", "c2"], content="ans"))
    driver = _load_driver(monkeypatch, rag)

    result = asyncio.run(driver._run(_job(tmp_path)))

    assert rag.calls == ["aquery_llm"], rag.calls
    assert result["chunk_ids"] == ["c1", "c2"]
    assert result["answer"] == "ans"
