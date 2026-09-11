"""Tests for databasise.eval.aa_run (06-16-PLAN.md's <behavior> block, Tests 1-13).

No test in this module reaches a real provider, a real engine, or the network — every LLM client,
vector store and `Databasise` engine is a stub double defined here, in the style
`databasise/tests/clients/test_openai_compat.py` and `databasise/tests/eval/test_corpus_ingest.py`
already establish.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from databasise.clients.base import ChatResult
from databasise.eval import aa_run
from databasise.eval.aa_run import (
    GOLD_PASSAGE_METRIC,
    VERDICT_SCORES,
    PassResult,
    UnparseableJudgeVerdictError,
    calibrate_family,
    run_one_pass,
    score_answer_level,
    score_gold_passage,
)
from databasise.eval.bundle import (
    ANSWER_LEVEL_FAMILY,
    GOLD_PASSAGE_FAMILY,
    BundleQuestion,
    BundleSplit,
    EvalBundle,
    TargetFamily,
)
from databasise.eval.calibration import UnusableFloorError
from databasise.runner.trace import TokenAccounting
from databasise.seam.envelope import ResponseEnvelope
from databasise.seam.evidence import EvidenceRef, UnresolvableEvidenceReferenceError
from databasise.seam.query import QueryObject
from databasise.seam.trace_store import TraceStore

pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------------------------- #
# Shared stubs
# --------------------------------------------------------------------------------------------- #


class _StubNamespaceStore:
    def __init__(self, records: dict[str, dict], *, raise_if_called: bool = False) -> None:
        self._records = records
        self._raise_if_called = raise_if_called

    def get_by_id(self, doc_id: str):
        if self._raise_if_called:
            raise AssertionError("the store must not be called for an empty evidence list")
        return self._records.get(doc_id)


class _StubVectorStore:
    """Mimics ``MultiNamespaceVectorStore``'s own ``select(namespace).get_by_id(ref)`` surface —
    the only two calls ``resolve_evidence_ref`` makes."""

    def __init__(self, records: dict[str, dict], *, raise_if_called: bool = False) -> None:
        self._namespace_store = _StubNamespaceStore(records, raise_if_called=raise_if_called)

    def select(self, namespace: str) -> _StubNamespaceStore:
        return self._namespace_store


class _RecordingLLMClient:
    """Records every ``chat`` call and always returns the same canned verdict text."""

    def __init__(self, response_text: str) -> None:
        self._response_text = response_text
        self.calls: list[list[dict[str, str]]] = []

    async def chat(self, messages, **kwargs):
        self.calls.append(messages)
        return ChatResult(
            text=self._response_text,
            tokens=TokenAccounting(prompt_tokens=3, completion_tokens=1, call_count=1, counted_by="stub"),
            resolved_model_identity="stub-judge-model",
        )


def _make_bundle(
    *, determinism: str = "cache-bypassed", concurrency: str = "sequential"
) -> EvalBundle:
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
        TargetFamily(
            name=GOLD_PASSAGE_FAMILY,
            tier="T1",
            targets={"q1": ["d1"], "q2": ["d2"], "q3": ["d3"]},
        ),
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
        determinism_setting=determinism,
        concurrency_setting=concurrency,
        splits=splits,
        split_proportions={"dev": 1.0, "holdout": 0.0, "sealed": 0.0},
        target_families=target_families,
    )


class _StubEngine:
    """A minimal ``Databasise`` double: a ``store_root`` and a ``query()`` that persists a real
    node-trace record into a real :class:`TraceStore` at that root, so ``run_one_pass``'s own
    freshly-opened ``TraceStore`` can resolve the returned ``trace_token`` exactly as it would
    against a real engine.
    """

    def __init__(
        self,
        store_root: Path,
        *,
        answers: dict[str, str] | None = None,
        evidence_by_question: dict[str, list[EvidenceRef]] | None = None,
        cache_hit: bool = False,
    ) -> None:
        self.store_root = store_root
        self._trace_store = TraceStore(store_root)
        self.query_calls: list[str] = []
        self._answers = answers or {}
        self._evidence_by_question = evidence_by_question or {}
        self._cache_hit = cache_hit

    async def query(self, query_object: QueryObject, selector=None):
        text = query_object.text
        self.query_calls.append(text)
        token = self._trace_store.persist(
            {"nodes": [{"node_id": "stub-node", "cache_hit": self._cache_hit}]}
        )
        return ResponseEnvelope(
            answer=self._answers.get(text, "a stub answer"),
            evidence=self._evidence_by_question.get(text, []),
            trace_token=token,
            depth_label="stage",
            partial=False,
            degraded=False,
        )


def _envelope_with_evidence(refs: list[EvidenceRef]) -> ResponseEnvelope:
    return ResponseEnvelope(
        answer="unused", evidence=refs, trace_token=None, depth_label="stage", partial=False, degraded=False
    )


# --------------------------------------------------------------------------------------------- #
# Test 1 — score_gold_passage over 2/3, 0/n and n/n gold-id overlap
# --------------------------------------------------------------------------------------------- #


def test_score_gold_passage_returns_the_gold_recall_fraction():
    partial_store = _StubVectorStore({"c1": {"document_id": "doc-a"}, "c2": {"document_id": "doc-b"}})
    partial_envelope = _envelope_with_evidence(
        [
            EvidenceRef(ref="c1", namespace="chunks", kind="text_chunk"),
            EvidenceRef(ref="c2", namespace="chunks", kind="text_chunk"),
        ]
    )
    assert score_gold_passage(
        partial_envelope, gold_document_ids=["doc-a", "doc-b", "doc-c"], vector_store=partial_store
    ) == pytest.approx(2 / 3)

    no_match_store = _StubVectorStore({"c1": {"document_id": "doc-x"}})
    no_match_envelope = _envelope_with_evidence([EvidenceRef(ref="c1", namespace="chunks", kind="text_chunk")])
    assert score_gold_passage(no_match_envelope, gold_document_ids=["doc-a"], vector_store=no_match_store) == 0.0

    full_store = _StubVectorStore({"c1": {"document_id": "doc-a"}})
    full_envelope = _envelope_with_evidence([EvidenceRef(ref="c1", namespace="chunks", kind="text_chunk")])
    assert score_gold_passage(full_envelope, gold_document_ids=["doc-a"], vector_store=full_store) == 1.0


# --------------------------------------------------------------------------------------------- #
# Test 2 — empty evidence scores zero, no store call
# --------------------------------------------------------------------------------------------- #


def test_score_gold_passage_empty_evidence_scores_zero_and_touches_no_store():
    vector_store = _StubVectorStore({}, raise_if_called=True)
    envelope = _envelope_with_evidence([])
    score = score_gold_passage(envelope, gold_document_ids=["doc-a"], vector_store=vector_store)
    assert score == 0.0


# --------------------------------------------------------------------------------------------- #
# Test 3 — an unresolvable ref propagates, never a silent miss
# --------------------------------------------------------------------------------------------- #


def test_score_gold_passage_propagates_unresolvable_evidence_reference_error():
    vector_store = _StubVectorStore({})
    envelope = _envelope_with_evidence([EvidenceRef(ref="missing", namespace="chunks", kind="text_chunk")])
    with pytest.raises(UnresolvableEvidenceReferenceError):
        score_gold_passage(envelope, gold_document_ids=["doc-a"], vector_store=vector_store)


# --------------------------------------------------------------------------------------------- #
# Test 3b (WR-01 gap closure) — an empty gold_document_ids refuses by name, never a bare
# ZeroDivisionError, and never touches the store (raised before any evidence resolution).
# --------------------------------------------------------------------------------------------- #


def test_score_gold_passage_empty_gold_document_ids_raises_value_error_not_zero_division():
    vector_store = _StubVectorStore({}, raise_if_called=True)
    envelope = _envelope_with_evidence([EvidenceRef(ref="doc-a#0", namespace="chunks", kind="text_chunk")])
    with pytest.raises(ValueError, match="gold_document_ids is empty"):
        score_gold_passage(envelope, gold_document_ids=[], vector_store=vector_store)


# --------------------------------------------------------------------------------------------- #
# Test 4 — score_answer_level maps CORRECT/PARTIAL/INCORRECT, whitespace/case-insensitive
# --------------------------------------------------------------------------------------------- #


async def test_score_answer_level_formats_prompt_and_maps_verdicts():
    template = aa_run.JUDGE_PROMPT_PATH.read_text(encoding="utf-8")
    assert set(VERDICT_SCORES) == {"CORRECT", "PARTIAL", "INCORRECT"}

    for raw_verdict, expected in (("CORRECT", 1.0), ("  partial  \n", 0.5), ("incorrect", 0.0)):
        client = _RecordingLLMClient(raw_verdict)
        score = await score_answer_level(
            llm_client=client,
            prompt_template=template,
            question_text="What year?",
            gold_answer="1994",
            candidate_answer="It was 1994",
        )
        assert score == expected
        assert len(client.calls) == 1
        formatted = client.calls[0][0]["content"]
        assert "What year?" in formatted
        assert "1994" in formatted
        assert "It was 1994" in formatted


# --------------------------------------------------------------------------------------------- #
# Test 5 — an unparseable verdict refuses by name, never a default score
# --------------------------------------------------------------------------------------------- #


async def test_score_answer_level_raises_on_unparseable_verdict():
    client = _RecordingLLMClient("I cannot judge this")
    with pytest.raises(UnparseableJudgeVerdictError) as excinfo:
        await score_answer_level(
            llm_client=client,
            prompt_template="{question} {gold_answer} {candidate_answer}",
            question_text="q",
            gold_answer="g",
            candidate_answer="c",
        )
    assert excinfo.value.response_text == "I cannot judge this"


# --------------------------------------------------------------------------------------------- #
# Test 6 — run_one_pass: exactly the requested question ids, plus node traces, N query() calls
# --------------------------------------------------------------------------------------------- #


async def test_run_one_pass_returns_scores_for_exactly_the_question_ids_and_their_traces(tmp_path):
    bundle = _make_bundle()
    engine = _StubEngine(tmp_path)
    vector_store = _StubVectorStore({})

    result = await run_one_pass(
        engine=engine,
        bundle=bundle,
        question_ids=("q3", "q1", "q2"),
        family_name=GOLD_PASSAGE_FAMILY,
        vector_store=vector_store,
    )

    assert isinstance(result, PassResult)
    assert set(result.scores.keys()) == {"q1", "q2", "q3"}
    assert len(result.node_traces) == 3
    assert engine.query_calls == ["Question one?", "Question two?", "Question three?"]


# --------------------------------------------------------------------------------------------- #
# Test 7 — gold_passage never touches the judge
# --------------------------------------------------------------------------------------------- #


async def test_run_one_pass_gold_passage_makes_zero_chat_calls(tmp_path):
    bundle = _make_bundle()
    engine = _StubEngine(tmp_path)
    vector_store = _StubVectorStore({})
    llm_client = _RecordingLLMClient("CORRECT")

    await run_one_pass(
        engine=engine,
        bundle=bundle,
        question_ids=bundle.splits["dev"].question_ids,
        family_name=GOLD_PASSAGE_FAMILY,
        llm_client=llm_client,
        vector_store=vector_store,
    )

    assert llm_client.calls == []


# --------------------------------------------------------------------------------------------- #
# Test 8 — calibrate_family: identity assembled entirely from the bundle/family, never literals
# --------------------------------------------------------------------------------------------- #


async def test_calibrate_family_builds_identity_from_bundle_and_family(tmp_path):
    bundle = _make_bundle()
    engine = _StubEngine(tmp_path)
    vector_store = _StubVectorStore({})

    result = await calibrate_family(
        engine=engine,
        bundle=bundle,
        split_name="dev",
        family_name=GOLD_PASSAGE_FAMILY,
        vector_store=vector_store,
        n_resamples=50,
        seed=1,
    )

    assert result.identity.bundle_at_v == bundle.version
    assert result.identity.tier == "T1"
    assert result.identity.metric == GOLD_PASSAGE_METRIC
    assert result.identity.determinism_setting == bundle.determinism_setting
    assert result.identity.concurrency_setting == bundle.concurrency_setting


# --------------------------------------------------------------------------------------------- #
# Test 9 — UnusableFloorError propagates unchanged from a cache_hit-true trace
# --------------------------------------------------------------------------------------------- #


async def test_calibrate_family_propagates_unusable_floor_error_on_cache_hit(tmp_path):
    bundle = _make_bundle()
    engine = _StubEngine(tmp_path, cache_hit=True)
    vector_store = _StubVectorStore({})

    with pytest.raises(UnusableFloorError):
        await calibrate_family(
            engine=engine,
            bundle=bundle,
            split_name="dev",
            family_name=GOLD_PASSAGE_FAMILY,
            vector_store=vector_store,
        )


# --------------------------------------------------------------------------------------------- #
# Test 10 — a fixed seed reproduces the same floor twice
# --------------------------------------------------------------------------------------------- #


async def test_calibrate_family_is_reproducible_under_a_fixed_seed(tmp_path):
    bundle = _make_bundle()
    evidence_by_question = {
        "Question one?": [EvidenceRef(ref="c1", namespace="chunks", kind="text_chunk")],
        "Question two?": [],
        "Question three?": [],
    }
    vector_store = _StubVectorStore({"c1": {"document_id": "d1"}})

    engine_a = _StubEngine(tmp_path / "e1", evidence_by_question=evidence_by_question)
    engine_b = _StubEngine(tmp_path / "e2", evidence_by_question=evidence_by_question)

    first = await calibrate_family(
        engine=engine_a,
        bundle=bundle,
        split_name="dev",
        family_name=GOLD_PASSAGE_FAMILY,
        vector_store=vector_store,
        n_resamples=50,
        seed=42,
    )
    second = await calibrate_family(
        engine=engine_b,
        bundle=bundle,
        split_name="dev",
        family_name=GOLD_PASSAGE_FAMILY,
        vector_store=vector_store,
        n_resamples=50,
        seed=42,
    )
    assert first.floor == second.floor


# --------------------------------------------------------------------------------------------- #
# Test 11 — main() with no --spend prints a real projection and constructs no client
# --------------------------------------------------------------------------------------------- #


def test_main_default_path_constructs_no_client_and_prints_a_real_projection(monkeypatch, capsys):
    def _fail_if_constructed(**kwargs):
        raise AssertionError("Databasise must not be constructed without --spend")

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("_build_clients/_load_env_file must not be called without --spend")

    monkeypatch.setattr(aa_run, "Databasise", _fail_if_constructed)
    monkeypatch.setattr(aa_run, "_build_clients", _fail_if_called)
    monkeypatch.setattr(aa_run, "_load_env_file", _fail_if_called)

    exit_code = aa_run.main(["--split", "dev"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert '"split": "dev"' in out
    assert '"n_questions"' in out
    assert '"passes": 2' in out
    assert GOLD_PASSAGE_FAMILY in out
    assert ANSWER_LEVEL_FAMILY in out
    assert "mode: estimate-only" in out


# --------------------------------------------------------------------------------------------- #
# Test 12 — an unknown split, or a split not fully covered by a family, refuses by name
# --------------------------------------------------------------------------------------------- #


def test_main_refuses_unknown_split_or_split_not_covered_by_a_family(monkeypatch, capsys):
    exit_code = aa_run.main(["--split", "not-a-real-split"])
    assert exit_code != 0
    assert "not-a-real-split" in capsys.readouterr().err

    incomplete_bundle = _make_bundle()
    incomplete_family = TargetFamily(
        name=ANSWER_LEVEL_FAMILY, tier="T0", targets={"q1": "Answer one", "q2": "Answer two"}
    )
    incomplete_bundle = EvalBundle(
        **{
            **incomplete_bundle.__dict__,
            "target_families": (incomplete_bundle.target_families[0], incomplete_family),
        }
    )
    monkeypatch.setattr(aa_run, "load_bundle", lambda root, version: incomplete_bundle)
    monkeypatch.setattr(aa_run, "_default_bundle_version", lambda root: incomplete_bundle.version)

    exit_code = aa_run.main(["--split", "dev", "--family", ANSWER_LEVEL_FAMILY])
    assert exit_code != 0
    assert "q3" in capsys.readouterr().err


# --------------------------------------------------------------------------------------------- #
# Test 13 — holdout/sealed refuse by name; an A/A calibration is not their recorded-use event
# --------------------------------------------------------------------------------------------- #


def test_main_refuses_holdout_and_sealed_splits_by_name(capsys):
    for split_name in ("holdout", "sealed"):
        exit_code = aa_run.main(["--split", split_name])
        assert exit_code != 0
        err = capsys.readouterr().err
        assert split_name in err
