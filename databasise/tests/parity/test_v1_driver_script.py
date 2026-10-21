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


def _failure(metadata: dict[str, Any], message: str, content: str | None) -> dict[str, Any]:
    return _response(status="failure", metadata=metadata, message=message, content=content)


def test_a_v1_failure_exits_one_with_a_named_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rag = _StubRag(_failure({}, "Query failed: boom", None))
    driver = _load_driver(monkeypatch, rag)

    caught: BaseException | None = None
    try:
        asyncio.run(driver._run(_job(tmp_path)))
    except BaseException as exc:  # noqa: BLE001 - the type name is what is asserted
        caught = exc
    assert caught is not None, "a v1 failure came back as a result"
    assert type(caught).__name__ == "V1QueryFailedError", type(caught).__name__
    assert "boom" in str(caught)

    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(_job(tmp_path))))
    assert driver.main() == 1
    assert "V1QueryFailedError:" in capsys.readouterr().err


def test_no_results_is_an_empty_retrieval_with_the_fail_answer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rag = _StubRag(_failure({"failure_reason": "no_results", "mode": "hybrid"}, "none", "<fail text>"))
    driver = _load_driver(monkeypatch, rag)

    caught: BaseException | None = None
    result: dict[str, Any] = {}
    try:
        result = asyncio.run(driver._run(_job(tmp_path)))
    except BaseException as exc:  # noqa: BLE001
        caught = exc

    assert caught is None, repr(caught)
    assert (result.get("chunk_ids"), result.get("entity_ids"), result.get("relation_ids")) == ([], [], [])
    assert result.get("answer") == "<fail text>"


def test_absent_keywords_are_none_not_an_echo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    job = _job(tmp_path, hl_keywords=["caller-hl"], ll_keywords=["caller-ll"])

    absent = asyncio.run(_load_driver(monkeypatch, _StubRag(_response()))._run(job))
    assert absent.get("hl_keywords_used") is None, absent.get("hl_keywords_used")
    assert absent.get("ll_keywords_used") is None, absent.get("ll_keywords_used")

    empty = _response(metadata={"keywords": {"high_level": [], "low_level": []}})
    present = asyncio.run(_load_driver(monkeypatch, _StubRag(empty))._run(job))
    assert present.get("hl_keywords_used") == []
    assert present.get("ll_keywords_used") == []

    real = _response(metadata={"keywords": {"high_level": ["h"], "low_level": ["l"]}})
    got = asyncio.run(_load_driver(monkeypatch, _StubRag(real))._run(job))
    assert (got.get("hl_keywords_used"), got.get("ll_keywords_used")) == (["h"], ["l"])


def test_v1_arm_result_accepts_none_keywords() -> None:
    from databasise.parity.v1_arm import V1ArmResult

    result = V1ArmResult(
        chunk_ids=(),
        entity_ids=(),
        relation_ids=(),
        answer="a",
        hl_keywords_used=None,  # type: ignore[arg-type]
        ll_keywords_used=None,  # type: ignore[arg-type]
        wall_clock_seconds=0.0,
    )
    caught: BaseException | None = None
    as_dict: dict[str, Any] = {}
    try:
        as_dict = result.to_dict()
    except BaseException as exc:  # noqa: BLE001
        caught = exc
    assert caught is None, repr(caught)
    assert as_dict["hl_keywords_used"] is None, as_dict["hl_keywords_used"]
    assert as_dict["ll_keywords_used"] is None, as_dict["ll_keywords_used"]


def _capture(call: Any) -> tuple[Any, BaseException | None]:
    try:
        return call(), None
    except BaseException as exc:  # noqa: BLE001 - outcomes are asserted by type name and code
        return None, exc


def _forbid_launch(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    from databasise.parity import v1_arm

    launches: list[Any] = []

    def _recorder(*args: Any, **kwargs: Any) -> Any:
        launches.append(args)
        raise AssertionError("a subprocess was launched")

    monkeypatch.setattr(v1_arm.subprocess, "run", _recorder)
    return launches


def test_a_missing_env_file_is_refused_before_any_launch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from databasise.parity import v1_arm

    launches = _forbid_launch(monkeypatch)
    absent = tmp_path / "absent.env"
    interpreter = tmp_path / "python"
    interpreter.write_text("", encoding="utf-8")

    _, caught = _capture(lambda: v1_arm.run_v1_arm("hybrid", "q", env_path=absent, interpreter=interpreter))

    assert caught is not None, "run_v1_arm read a missing env file as empty"
    assert type(caught).__name__ == "MissingParityEnvError", repr(caught)
    assert str(absent) in str(caught)
    assert launches == []


def test_v1_arm_main_prints_one_named_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from databasise.parity import v1_arm

    launches = _forbid_launch(monkeypatch)
    absent = tmp_path / "absent.env"
    monkeypatch.setattr(v1_arm, "DEFAULT_V1_ENV_PARITY", absent)
    interpreter = tmp_path / "python"
    interpreter.write_text("", encoding="utf-8")
    monkeypatch.setattr(v1_arm, "DEFAULT_V1_INTERPRETER", interpreter)

    code, caught = _capture(lambda: v1_arm.main(["--mode", "hybrid", "--query", "q", "--spend"]))

    assert caught is None, repr(caught)
    assert code == 1
    lines = capsys.readouterr().err.strip().splitlines()
    assert len(lines) == 1, lines
    assert lines[0].startswith("MissingParityEnvError:"), lines[0]
    assert str(absent) in lines[0]
    assert launches == []


def test_v1_arm_main_without_spend_is_estimate_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from databasise.parity import v1_arm

    launches = _forbid_launch(monkeypatch)
    monkeypatch.setattr(v1_arm, "DEFAULT_V1_ENV_PARITY", tmp_path / "absent.env")

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("run_v1_arm was called without --spend")

    monkeypatch.setattr(v1_arm, "run_v1_arm", _must_not_run)

    code, caught = _capture(lambda: v1_arm.main(["--mode", "hybrid", "--query", "q"]))

    assert caught is None, repr(caught)
    assert code == 0
    out = capsys.readouterr().out
    assert "mode: estimate-only" in out, out
    assert "one v1 subprocess run" in out, out
    assert launches == []
