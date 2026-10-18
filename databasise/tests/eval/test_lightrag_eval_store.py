"""LRAG-15 (11-02-PLAN.md Task 2, D-03 as corrected by 11-RESEARCH.md Q6): an eval ingest with the
LightRAG arm stays inside the eval store, and ``aa_run`` queries that store with the arm it names.

The real-driver cases run ``corpus_ingest.main --spend --arm lightrag`` through the real v1 driver
and pipeline against the loopback stub model server (``tests/fixtures/v1_stub_server``), with
``_EVAL_INGEST_STORE_ROOT`` redirected to a temp dir in both eval modules and the env loader
replaced by the stub env, so no real env file is read and ``v1/.eval_corpus_store`` and
``v1/.corpus_working_dir`` are never written. The test asserts non-empty evidence, not a score:
``score_gold_passage`` reads ``document_id``, which LightRAG chunk records do not carry (TOOL-11).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

import databasise.parts_core.lightrag.full_ingest as full_ingest_module
from databasise.clients.builder import build_clients
from databasise.eval import aa_run, corpus_ingest
from databasise.eval.bundle import GOLD_PASSAGE_FAMILY
from databasise.eval.corpus_ingest import _ARM_CHOICES, _ARM_SELECTORS
from databasise.foreign import v1_corpus_adapter
from databasise.parity.corpus import CorpusDocument, CorpusSnapshot
from databasise.seam.engine import Databasise
from databasise.seam.query import QueryObject
from databasise.tests.eval.test_aa_run import _make_bundle, _StubEngine, _StubVectorStore
from databasise.tests.fixtures.v1_stub_server import real_v1, requires_v1  # noqa: F401 - fixture

_OPERATOR_CORPUS = Path(__file__).resolve().parents[3] / "v1" / ".corpus_working_dir"
_DOCS = (
    ("evaldoc1", "UNIQeva Corp runs the ferry from UNIQeva City."),
    ("evaldoc2", "UNIQevb Corp grows apples near UNIQevb City."),
)


def _listing(root: Path) -> dict[str, int]:
    if not root.exists():
        return {}
    return {str(p.relative_to(root)): p.stat().st_mtime_ns for p in root.rglob("*")}


def _snapshot() -> CorpusSnapshot:
    documents = tuple(CorpusDocument(id=i, title=i, text=t, sha256="0") for i, t in _DOCS)
    return CorpusSnapshot(documents=documents, queries=(), corpus_hash="0", queries_hash="0", source={})


@pytest.fixture
def eval_store(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "eval"
    for module in (corpus_ingest, aa_run):
        monkeypatch.setattr(module, "_EVAL_INGEST_STORE_ROOT", root)
    return root


@requires_v1
def test_eval_lightrag_ingest_stays_in_the_eval_store_and_aa_runs_arm_reads_it_back(
    real_v1, eval_store, monkeypatch  # noqa: F811
):
    calls: list[tuple[str, Any]] = []

    def _recording(op: str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        calls.append((op, kwargs.get("working_dir")))
        return v1_corpus_adapter.run_corpus_op(op, payload, **kwargs)

    monkeypatch.setattr(full_ingest_module, "run_corpus_op", _recording)
    monkeypatch.setattr(corpus_ingest, "load_snapshot", lambda corpus_dir: _snapshot())
    # Never the real parity env: the eval CLI gets the stub-local client env.
    monkeypatch.setattr(corpus_ingest, "_load_env_file", lambda path: dict(real_v1.client_env))
    operator_before = _listing(_OPERATOR_CORPUS)

    assert corpus_ingest.main(["--limit", "2", "--arm", "lightrag", "--spend"]) == 0
    expected_dir = str(eval_store / corpus_ingest._EVAL_INGEST_WORKSPACE / "lightrag-v1")
    assert calls == [("ingest", expected_dir), ("ingest", expected_dir)]
    assert (Path(expected_dir) / "kv_store_doc_status.json").is_file()
    assert _listing(_OPERATOR_CORPUS) == operator_before

    # The engine aa_run --spend builds, queried with the selector aa_run --arm lightrag maps to.
    engine = Databasise(
        store_root=aa_run._EVAL_INGEST_STORE_ROOT,
        workspace=aa_run._EVAL_INGEST_WORKSPACE,
        clients=build_clients(real_v1.client_env),
    )

    async def _query_and_resolve() -> tuple[Any, Any]:
        envelope = await engine.query(QueryObject(text="UNIQeva ferry"), aa_run._ARM_SELECTORS["lightrag"])
        assert envelope.evidence, "the LightRAG arm returned no evidence over the eval store"
        return envelope, await engine.resolve_evidence(envelope.evidence[0])

    _, record = asyncio.run(_query_and_resolve())
    assert record["full_doc_id"] in {doc_id for doc_id, _ in _DOCS}


class _SelectorRecordingEngine(_StubEngine):
    def __init__(self, store_root: Path) -> None:
        super().__init__(store_root)
        self.selectors: list[Any] = []

    async def query(self, query_object: QueryObject, selector=None):
        self.selectors.append(selector)
        return await super().query(query_object, selector)


async def test_run_one_pass_passes_the_arm_selector_to_every_query(tmp_path: Path):
    bundle = _make_bundle()
    engine = _SelectorRecordingEngine(tmp_path)
    common = {
        "engine": engine,
        "bundle": bundle,
        "question_ids": bundle.splits["dev"].question_ids,
        "family_name": GOLD_PASSAGE_FAMILY,
        "vector_store": _StubVectorStore({}),
    }

    await aa_run.run_one_pass(**common, selector=_ARM_SELECTORS["lightrag"])
    assert engine.selectors == [_ARM_SELECTORS["lightrag"]] * 3

    engine.selectors.clear()
    await aa_run.run_one_pass(**common)
    assert engine.selectors == [None] * 3


async def test_calibrate_family_threads_the_selector_into_both_passes(tmp_path: Path):
    engine = _SelectorRecordingEngine(tmp_path)
    await aa_run.calibrate_family(
        engine=engine,
        bundle=_make_bundle(),
        split_name="dev",
        family_name=GOLD_PASSAGE_FAMILY,
        vector_store=_StubVectorStore({}),
        n_resamples=200,
        seed=0,
        selector=_ARM_SELECTORS["hipporag"],
    )
    assert engine.selectors == [_ARM_SELECTORS["hipporag"]] * 6


def test_aa_run_arm_flag_parses_and_is_shown_in_the_projection(capsys):
    assert aa_run.main(["--split", "dev", "--arm", "lightrag"]) == 0
    out = capsys.readouterr().out
    assert '"arm": "lightrag"' in out
    assert "mode: estimate-only" in out

    assert aa_run.main(["--split", "dev"]) == 0
    assert '"arm": null' in capsys.readouterr().out


def test_aa_run_arm_outside_the_known_arms_is_an_argparse_error():
    assert "naive" not in _ARM_CHOICES
    with pytest.raises(SystemExit) as raised:
        aa_run.main(["--split", "dev", "--arm", "naive"])
    assert raised.value.code == 2


@pytest.mark.parametrize("argv, expected", [(["--arm", "lightrag"], _ARM_SELECTORS["lightrag"]), ([], None)])
def test_aa_run_spend_queries_the_eval_store_with_the_mapped_selector(monkeypatch, eval_store, argv, expected):
    built: dict[str, Any] = {}
    seen: list[Any] = []

    async def _calibrate(**kwargs):
        seen.append(kwargs["selector"])
        raise aa_run.ConfoundedPassError("q1", partial=True, degraded=False)  # stop after one call

    monkeypatch.setattr(aa_run, "_load_env_file", lambda path: {})
    monkeypatch.setattr(aa_run, "_build_clients", lambda env: {"llm": None})
    monkeypatch.setattr(aa_run, "Databasise", lambda **kwargs: built.update(kwargs))
    monkeypatch.setattr(aa_run, "MultiNamespaceVectorStore", lambda **kwargs: object())
    monkeypatch.setattr(aa_run, "calibrate_family", _calibrate)

    assert aa_run.main(["--split", "dev", "--spend", *argv]) == 1
    assert built["store_root"] == eval_store
    assert seen == [expected]
