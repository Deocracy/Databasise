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

from databasise.eval import aa_run
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
from databasise.seam.trace_store import TraceStore


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
