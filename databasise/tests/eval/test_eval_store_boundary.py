"""TOOL-11 (15-10-PLAN.md, D-12): the eval CLIs stay inside the eval store, refuse an empty index
before they spend, and score LightRAG evidence instead of crashing.

Row file: every helper is copied here (no import from another test file) and every name this phase
adds is resolved with ``getattr``, so the file collects and fails by assertion on pre-fix code. No
test reads a real env file: each ``--spend`` path patches the module's ``DEFAULT_V1_ENV_PARITY`` to a
temp path and stubs the clients.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import databasise.parts_core.lightrag.full_ingest as full_ingest_module
from databasise.eval import aa_run, corpus_ingest
from databasise.eval.bundle import (
    ANSWER_LEVEL_FAMILY,
    GOLD_PASSAGE_FAMILY,
    BundleQuestion,
    BundleSplit,
    EvalBundle,
    TargetFamily,
)
from databasise.seam.envelope import ResponseEnvelope
from databasise.seam.evidence import EvidenceRef
from databasise.seam.query import QueryObject
from databasise.seam.selectors import Selector
from databasise.seam.trace_store import TraceStore

_OPERATOR_CORPUS = Path(__file__).resolve().parents[3] / "v1" / ".corpus_working_dir"


def _make_bundle() -> EvalBundle:
    questions = (
        BundleQuestion(id="q1", text="Question one?"),
        BundleQuestion(id="q2", text="Question two?"),
        BundleQuestion(id="q3", text="Question three?"),
    )
    gold_answers = {"q1": "Answer one", "q2": "Answer two", "q3": "Answer three"}
    splits = {
        "dev": BundleSplit(name="dev", question_ids=("q1", "q2", "q3")),
        "holdout": BundleSplit(name="holdout", question_ids=()),
        "sealed": BundleSplit(name="sealed", question_ids=()),
    }
    target_families = (
        TargetFamily(name=GOLD_PASSAGE_FAMILY, tier="T1", targets={"q1": ["d1"], "q2": ["d2"], "q3": ["d3"]}),
        TargetFamily(name=ANSWER_LEVEL_FAMILY, tier="T0", targets=gold_answers),
    )
    return EvalBundle(
        version="bundle@v1",
        content_hash="deadbeef",
        questions=questions,
        gold_answers=gold_answers,
        judge_instance="stub-judge",
        judge_prompt_hash="deadbeef",
        corpus_snapshot_hash="deadbeef",
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
        splits=splits,
        split_proportions={"dev": 1.0, "holdout": 0.0, "sealed": 0.0},
        target_families=target_families,
    )


class _CountingEmbeddingClient:
    def __init__(self) -> None:
        self.calls = 0

    async def embed(self, texts, **kwargs):
        self.calls += 1
        raise AssertionError("no embedding call may be made on an empty eval index")


class _CountingEngine:
    """A ``Databasise`` double whose every query embeds the question first, as a real arm does."""

    def __init__(self, store_root: Path, clients: dict[str, Any]) -> None:
        self.store_root = store_root
        self.clients = clients
        self.query_calls: list[str] = []
        self._trace_store = TraceStore(store_root)

    async def query(self, query_object: QueryObject, selector=None):
        self.query_calls.append(query_object.text)
        await self.clients["embedding"].embed([query_object.text])
        token = self._trace_store.persist({"nodes": [{"node_id": "stub-node", "cache_hit": False}]})
        return ResponseEnvelope(
            answer="a stub answer",
            evidence=[],
            trace_token=token,
            depth_label="stage",
            partial=False,
            degraded=False,
        )


class _NoStore:
    def select(self, namespace: str):
        raise AssertionError("the empty-index refusal must come before any store read")


class _StubNamespaceStore:
    def __init__(self, records: dict[str, dict]) -> None:
        self._records = records

    def get_by_id(self, doc_id: str):
        return self._records.get(doc_id)


class _StubVectorStore:
    """Mimics ``MultiNamespaceVectorStore``'s ``select(namespace).get_by_id(ref)``."""

    def __init__(self, records: dict[str, dict]) -> None:
        self._namespace_store = _StubNamespaceStore(records)

    def select(self, namespace: str) -> _StubNamespaceStore:
        return self._namespace_store


def _chunk_envelope() -> ResponseEnvelope:
    return ResponseEnvelope(
        answer="unused",
        evidence=[EvidenceRef(ref="c1", namespace="chunks", kind="text_chunk")],
        trace_token=None,
        depth_label="stage",
        partial=False,
        degraded=False,
    )


def test_an_empty_hipporag_eval_index_is_refused_before_any_spend(tmp_path, monkeypatch, capsys):
    bundle = _make_bundle()
    embedding = _CountingEmbeddingClient()
    engines: list[_CountingEngine] = []

    def _engine_factory(**kwargs: Any) -> _CountingEngine:
        engine = _CountingEngine(tmp_path / "engine-traces", kwargs["clients"])
        engines.append(engine)
        return engine

    absent_env = tmp_path / "absent.env.parity"
    monkeypatch.setattr(aa_run, "_EVAL_INGEST_STORE_ROOT", tmp_path / "empty-eval-root")
    monkeypatch.setattr(aa_run, "DEFAULT_V1_ENV_PARITY", absent_env)
    monkeypatch.setattr(aa_run, "_load_env_file", lambda path: {})
    monkeypatch.setattr(aa_run, "_build_clients", lambda env: {"llm": None, "embedding": embedding})
    monkeypatch.setattr(aa_run, "Databasise", _engine_factory)
    monkeypatch.setattr(aa_run, "MultiNamespaceVectorStore", lambda **kwargs: _NoStore())
    monkeypatch.setattr(aa_run, "load_bundle", lambda root, version: bundle)
    monkeypatch.setattr(aa_run, "_default_bundle_version", lambda root: bundle.version)

    try:
        code = aa_run.main(["--split", "dev", "--arm", "hipporag", "--family", GOLD_PASSAGE_FAMILY, "--spend"])
    except BaseException as caught:  # noqa: BLE001 - the pre-fix run may end in any way; assert on it
        code = f"raised {type(caught).__name__}"

    err_lines = [line for line in capsys.readouterr().err.splitlines() if line.strip()]
    queries = sum(len(engine.query_calls) for engine in engines)
    assert code == 1, f"exit code {code!r}, {queries} engine queries, {embedding.calls} embedding calls"
    assert len(err_lines) == 1 and err_lines[0].startswith("EmptyEvalIndexError:"), err_lines
    assert queries == 0
    assert embedding.calls == 0


def test_a_populated_hipporag_eval_index_is_not_refused(tmp_path, monkeypatch):
    """The probe must pass on a populated namespace: ``load_committed`` returns entries."""
    seen: list[Path] = []

    class _Committed:
        entries = {"c1": object()}

    def _load_committed(dir_path):
        seen.append(Path(dir_path))
        return _Committed()

    monkeypatch.setattr(aa_run, "_EVAL_INGEST_STORE_ROOT", tmp_path / "eval")
    monkeypatch.setattr(aa_run, "load_committed", _load_committed, raising=False)
    probe_for = getattr(aa_run, "_eval_index_probe", None)
    assert probe_for is not None, "aa_run has no _eval_index_probe"
    probe_for("hipporag")()
    assert seen == [tmp_path / "eval" / aa_run._EVAL_INGEST_WORKSPACE / "hipporag-chunks"]


def _score(record: dict[str, Any], gold: list[str]) -> Any:
    try:
        return aa_run.score_gold_passage(
            _chunk_envelope(), gold_document_ids=gold, vector_store=_StubVectorStore({"c1": record})
        )
    except BaseException as caught:  # noqa: BLE001 - assert on the type below
        return caught


def test_lightrag_chunk_evidence_scores_by_full_doc_id():
    assert _score({"full_doc_id": "d1"}, ["d1", "d2"]) == 0.5


def test_evidence_with_no_document_key_is_a_named_refusal():
    outcome = _score({"content": "x"}, ["d1"])
    assert isinstance(outcome, BaseException), f"scored {outcome!r}"
    assert type(outcome).__name__ == "GoldPassageMappingError", type(outcome).__name__


def _listing(root: Path) -> dict[str, int]:
    if not root.exists():
        return {}
    return {str(p.relative_to(root)): p.stat().st_mtime_ns for p in root.rglob("*")}


def test_lightrag_eval_ingest_uses_a_working_dir_under_the_eval_root(tmp_path, monkeypatch):
    calls: list[Any] = []

    def _spy(op: str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        calls.append((op, kwargs.get("working_dir")))
        return {"track_id": "t", "enqueued": 1, "usage": None}

    eval_root = tmp_path / "eval"
    absent_env = tmp_path / "absent.env.parity"
    monkeypatch.setattr(full_ingest_module, "run_corpus_op", _spy)
    monkeypatch.setattr(corpus_ingest, "_EVAL_INGEST_STORE_ROOT", eval_root)
    monkeypatch.setattr(corpus_ingest, "DEFAULT_V1_ENV_PARITY", absent_env)
    monkeypatch.setattr(corpus_ingest, "_load_env_file", lambda path: {})
    monkeypatch.setattr(corpus_ingest, "_build_clients", lambda env: {"llm": None, "embedding": None})
    before = _listing(_OPERATOR_CORPUS)

    try:
        corpus_ingest.main(["--limit", "1", "--arm", "lightrag", "--spend"])
    except BaseException:  # noqa: BLE001 - the stub clients may stop a later node; the spy already saw the dir
        pass

    assert calls, "the LightRAG ingest never reached the v1 corpus op"
    expected = str(eval_root / corpus_ingest._EVAL_INGEST_WORKSPACE / "lightrag-v1")
    assert all(working_dir == expected for _, working_dir in calls), calls
    assert _listing(_OPERATOR_CORPUS) == before


def test_aa_run_forwards_the_arm_selector(tmp_path, monkeypatch):
    seen: list[Any] = []

    async def _calibrate(**kwargs: Any):
        seen.append(kwargs.get("selector"))
        raise aa_run.ConfoundedPassError("q1", partial=True, degraded=False)

    monkeypatch.setattr(aa_run, "_EVAL_INGEST_STORE_ROOT", tmp_path / "eval")
    monkeypatch.setattr(aa_run, "DEFAULT_V1_ENV_PARITY", tmp_path / "absent.env.parity")
    monkeypatch.setattr(aa_run, "_load_env_file", lambda path: {})
    monkeypatch.setattr(aa_run, "_build_clients", lambda env: {"llm": None})
    monkeypatch.setattr(aa_run, "Databasise", lambda **kwargs: object())
    monkeypatch.setattr(aa_run, "MultiNamespaceVectorStore", lambda **kwargs: object())
    monkeypatch.setattr(aa_run, "calibrate_family", _calibrate)

    assert aa_run.main(["--split", "dev", "--arm", "lightrag", "--spend"]) == 1
    assert seen == [aa_run._ARM_SELECTORS["lightrag"]]


def test_aa_run_refuses_a_selector_that_resolves_to_another_arm_before_clients(tmp_path, monkeypatch, capsys):
    built: list[str] = []
    monkeypatch.setitem(aa_run._ARM_SELECTORS, "lightrag", Selector(capability=["reads_graph", "reads_kv"]))
    monkeypatch.setattr(aa_run, "_EVAL_INGEST_STORE_ROOT", tmp_path / "eval")
    monkeypatch.setattr(aa_run, "DEFAULT_V1_ENV_PARITY", tmp_path / "absent.env.parity")
    monkeypatch.setattr(aa_run, "_load_env_file", lambda path: {})
    monkeypatch.setattr(aa_run, "_build_clients", lambda env: built.append("clients") or {"llm": None})
    monkeypatch.setattr(aa_run, "Databasise", lambda **kwargs: built.append("engine") or object())
    monkeypatch.setattr(aa_run, "MultiNamespaceVectorStore", lambda **kwargs: object())

    async def _calibrate(**kwargs: Any):
        raise aa_run.ConfoundedPassError("q1", partial=True, degraded=False)

    monkeypatch.setattr(aa_run, "calibrate_family", _calibrate)
    try:
        code = aa_run.main(["--split", "dev", "--arm", "lightrag", "--spend"])
    except BaseException as caught:  # noqa: BLE001
        code = f"raised {type(caught).__name__}"
    err = capsys.readouterr().err
    assert code == 1, code
    assert "ArmSelectorMismatchError" in err, err
    assert built == []
