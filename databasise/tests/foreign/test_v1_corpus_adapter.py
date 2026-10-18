"""11-07-PLAN.md Task 2 (LRAG-05, D-11, research Q2): adapter faults are readable in the server log
and named for callers.

Fake driver scripts run through the real ``run_corpus_op`` under this interpreter; the torn-file
and bad-page cases run the real driver under v1's interpreter (skipped only when it is absent).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from databasise.evidence import f07_report
from databasise.foreign import (
    CorpusOpBusyError,
    CorpusOpMalformedOutputError,
    CorpusOpSubprocessError,
    run_corpus_op,
    v1_corpus_adapter,
)
from databasise.seam import engine as engine_module
from databasise.seam.engine import Databasise
from databasise.seam.refusals import StoreBusyError
from databasise.seam.rest import create_app
from databasise.tests.fixtures.v1_stub_server import real_v1, requires_v1  # noqa: F401

_STATUS_ROUTES = ("/corpus", "/corpus/counts", "/jobs/x")
_BUSY_DRIVER = (
    "sys.stderr.write('Traceback\\n  File \"/home/x/store/ws/lightrag-v1/kv_store_doc_status.json\"\\n')\n"
    "sys.stdout.write('{\"error\": \"doc_status_unreadable\"}')\n"
    "sys.exit(4)\n"
)


def _driver(tmp_path: Path, body: str) -> Path:
    script = tmp_path / "fake_driver.py"
    script.write_text("import sys\n" + body, encoding="utf-8")
    return script


def _run(tmp_path: Path, body: str) -> dict[str, Any]:
    return run_corpus_op(
        "status",
        {"track_id": None},
        timeout=30.0,
        interpreter=Path(sys.executable),
        driver_script=_driver(tmp_path, body),
        env_path=tmp_path / "absent.env",
    )


@pytest.fixture
def client_with_driver(tmp_path, monkeypatch):
    """A REST client whose every corpus call runs ``body`` as the driver, through the real adapter."""

    def _make(body: str) -> TestClient:
        monkeypatch.setattr(v1_corpus_adapter, "DEFAULT_V1_INTERPRETER", Path(sys.executable))
        monkeypatch.setattr(v1_corpus_adapter, "DEFAULT_V1_DRIVER_SCRIPT", _driver(tmp_path, body))
        monkeypatch.setattr(v1_corpus_adapter, "DEFAULT_V1_ENV_PARITY", tmp_path / "absent.env")
        app = create_app(store_root=tmp_path / "store", workspace="ws")
        return TestClient(app, raise_server_exceptions=False)

    return _make


def test_the_stderr_tail_keeps_the_exception_line(tmp_path):
    body = "sys.stderr.write('x' * 3000 + '\\nValueError: boom\\n')\nsys.exit(1)\n"
    with pytest.raises(CorpusOpSubprocessError) as raised:
        _run(tmp_path, body)
    assert "ValueError: boom" in str(raised.value)
    assert "ValueError: boom" in raised.value.stderr
    assert len(str(raised.value)) < 2100


def test_non_json_stdout_is_a_named_malformed_output_error(tmp_path, client_with_driver):
    body = "sys.stdout.write('not json')\n"
    with pytest.raises(CorpusOpMalformedOutputError):
        _run(tmp_path, body)

    response = client_with_driver(body).get("/corpus")
    assert response.status_code == 502, response.text
    assert response.json()["failure_class"] == "MalformedDriverOutput"


def test_exit_4_is_a_busy_error(tmp_path):
    with pytest.raises(CorpusOpBusyError):
        _run(tmp_path, _BUSY_DRIVER)


@pytest.mark.parametrize("route", _STATUS_ROUTES)
def test_an_unreadable_doc_status_file_is_a_409_corpus_busy(client_with_driver, route):
    response = client_with_driver(_BUSY_DRIVER).get(route)
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["refusal_type"] == "StoreBusyError"
    assert body["store_kind"] == "corpus"
    assert "/home/" not in response.text and "lightrag-v1" not in response.text


def test_a_failing_ingest_never_shows_stderr_paths_or_hosts(client_with_driver):
    body = (
        "sys.stderr.write('Traceback\\n  File \"/home/x/secret.py\"\\n"
        "ConnectionError: http://10.0.0.1:8080\\n')\nsys.exit(1)\n"
    )
    response = client_with_driver(body).post("/documents", json={"document": {"text": "x"}})
    assert response.status_code == 502, response.text
    assert response.json()["failure_class"] == "CorpusOpSubprocessError"
    assert "/home/x/secret.py" not in response.text and "http://10.0.0.1" not in response.text


def test_a_negative_limit_is_a_422_before_any_driver_call(tmp_path, monkeypatch):
    calls: list[Any] = []
    monkeypatch.setattr(engine_module, "run_corpus_op", lambda *a, **k: calls.append(a) or {})
    client = TestClient(create_app(store_root=tmp_path / "store", workspace="ws"))

    response = client.get("/corpus?limit=-1")
    assert response.status_code == 422, response.text
    assert response.json()["refusal_type"] == "PageBoundsError"
    assert calls == []


@requires_v1
def test_the_real_driver_names_its_own_page_refusal_in_the_tail(real_v1):  # noqa: F811
    with pytest.raises(CorpusOpSubprocessError) as raised:
        run_corpus_op(
            "status",
            {"track_id": None, "limit": -1, "offset": 0},
            timeout=120.0,
            working_dir=real_v1.store_root / "ws" / "lightrag-v1",
        )
    assert "InvalidPageRequestError" in str(raised.value)


@requires_v1
async def test_a_torn_doc_status_file_makes_corpus_status_busy(real_v1):  # noqa: F811
    working_dir = real_v1.store_root / "ws" / "lightrag-v1"
    working_dir.mkdir(parents=True)
    (working_dir / "kv_store_doc_status.json").write_text("{not json", encoding="utf-8")

    with pytest.raises(StoreBusyError) as raised:
        await Databasise(store_root=real_v1.store_root, workspace="ws").corpus_status()
    assert raised.value.store_kind == "corpus"


def test_the_adapter_and_f07_docstrings_are_true():
    assert "05-03/05-04" not in (v1_corpus_adapter.__doc__ or "")
    assert "builds v1's facade" not in Path(v1_corpus_adapter.__file__).read_text(encoding="utf-8")
    assert "already owns for delete_project" not in Path(f07_report.__file__).read_text(encoding="utf-8")
