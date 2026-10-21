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
    ConfoundedPassError,
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
# 15-16 (TOOL-12): the first whole-word verdict parses, however the judge dresses it
# --------------------------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ("CORRECT.", 1.0),
        ("**CORRECT**", 1.0),
        ("Verdict: CORRECT", 1.0),
        ("CORRECT—the answer matches", 1.0),
        ("INCORRECT", 0.0),
        ("**Partial**", 0.5),
    ],
)
async def test_the_four_verdict_shapes_parse_to_correct(response, expected):
    async def _score():
        return await score_answer_level(
            llm_client=_RecordingLLMClient(response),
            prompt_template="{question} {gold_answer} {candidate_answer}",
            question_text="q",
            gold_answer="g",
            candidate_answer="c",
        )

    try:
        outcome = await _score()
    except BaseException as caught:  # noqa: BLE001 - the assertion is on the captured value
        outcome = caught

    assert outcome == expected, f"{response!r}: {outcome!r}"


async def test_maybe_stays_an_unparseable_verdict():
    client = _RecordingLLMClient("MAYBE")
    try:
        outcome = await score_answer_level(
            llm_client=client,
            prompt_template="{question} {gold_answer} {candidate_answer}",
            question_text="q",
            gold_answer="g",
            candidate_answer="c",
        )
    except BaseException as caught:  # noqa: BLE001
        outcome = caught

    assert type(outcome).__name__ == "UnparseableJudgeVerdictError", repr(outcome)


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
# 15-16 (TOOL-12, D-13) — a pass records the traces' own wiring_instance_hash; a floor is only
# keyable when both passes saw exactly one
# --------------------------------------------------------------------------------------------- #


class _HashedStubEngine(_StubEngine):
    """Like ``_StubEngine`` but each trace record carries a ``wiring_instance_hash``; ``hashes`` is
    cycled per query so a test can make two distinct hashes appear."""

    def __init__(self, store_root: Path, hashes: list[str]) -> None:
        super().__init__(store_root)
        self._hashes = hashes

    async def query(self, query_object: QueryObject, selector=None):
        self.query_calls.append(query_object.text)
        instance_hash = self._hashes[(len(self.query_calls) - 1) % len(self._hashes)]
        token = self._trace_store.persist(
            {"wiring_instance_hash": instance_hash, "nodes": [{"node_id": "stub-node", "cache_hit": False}]}
        )
        return ResponseEnvelope(
            answer="a stub answer", evidence=[], trace_token=token, depth_label="stage", partial=False, degraded=False
        )


def _recorded_hashes(result):
    return getattr(result, "wiring_instance_hashes", None)


async def test_a_pass_records_the_traces_wiring_instance_hash(tmp_path):
    bundle = _make_bundle()
    instance_hash = f"sha256:{'e' * 64}"

    hashed = await run_one_pass(
        engine=_HashedStubEngine(tmp_path / "h", [instance_hash]),
        bundle=bundle,
        question_ids=("q1", "q2"),
        family_name=GOLD_PASSAGE_FAMILY,
        vector_store=_StubVectorStore({}),
    )
    plain = await run_one_pass(
        engine=_StubEngine(tmp_path / "p"),
        bundle=bundle,
        question_ids=("q1", "q2"),
        family_name=GOLD_PASSAGE_FAMILY,
        vector_store=_StubVectorStore({}),
    )

    assert _recorded_hashes(hashed) == (instance_hash,), _recorded_hashes(hashed)
    assert _recorded_hashes(plain) == (), _recorded_hashes(plain)


async def test_calibrate_family_keys_the_result_to_the_single_hash_both_passes_saw(tmp_path):
    instance_hash = f"sha256:{'e' * 64}"

    keyed = await calibrate_family(
        engine=_HashedStubEngine(tmp_path / "one", [instance_hash]),
        bundle=_make_bundle(),
        split_name="dev",
        family_name=GOLD_PASSAGE_FAMILY,
        vector_store=_StubVectorStore({}),
        n_resamples=50,
        seed=1,
    )
    mixed = await calibrate_family(
        engine=_HashedStubEngine(tmp_path / "two", [instance_hash, f"sha256:{'f' * 64}"]),
        bundle=_make_bundle(),
        split_name="dev",
        family_name=GOLD_PASSAGE_FAMILY,
        vector_store=_StubVectorStore({}),
        n_resamples=50,
        seed=1,
    )
    unhashed = await calibrate_family(
        engine=_StubEngine(tmp_path / "none"),
        bundle=_make_bundle(),
        split_name="dev",
        family_name=GOLD_PASSAGE_FAMILY,
        vector_store=_StubVectorStore({}),
        n_resamples=50,
        seed=1,
    )

    assert getattr(keyed, "wiring_instance_hash", "missing") == instance_hash
    assert getattr(mixed, "wiring_instance_hash", "missing") is None
    assert getattr(unhashed, "wiring_instance_hash", "missing") is None


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


# --------------------------------------------------------------------------------------------- #
# Test 14 (WR-01 gap closure) — the --spend path's except tuple actually catches
# ConfoundedPassError (run_one_pass's own confounded-pass refusal) and exits 1 with the refusal's
# message on stderr, rather than letting it propagate as an unhandled traceback.
# --------------------------------------------------------------------------------------------- #


def test_main_spend_path_catches_confounded_pass_error_and_exits_1(monkeypatch, capsys):
    async def _raise_confounded_pass(**kwargs):
        raise ConfoundedPassError("q1", partial=True, degraded=False)

    monkeypatch.setattr(aa_run, "_load_env_file", lambda path: {})
    monkeypatch.setattr(aa_run, "_build_clients", lambda env: {"llm": None})
    monkeypatch.setattr(aa_run, "Databasise", lambda **kwargs: object())
    monkeypatch.setattr(aa_run, "MultiNamespaceVectorStore", lambda **kwargs: object())
    monkeypatch.setattr(aa_run, "calibrate_family", _raise_confounded_pass)

    exit_code = aa_run.main(["--split", "dev", "--spend"])

    assert exit_code == 1
    err = capsys.readouterr().err
    assert "q1" in err
    assert "a confounded pass cannot calibrate a null" in err


# --------------------------------------------------------------------------------------------- #
# 15-10 (D-03, D-04, D-24) — the shared CLI contract. Every --spend path below patches the module's
# DEFAULT_V1_ENV_PARITY to a temp path and stubs the env loader, the clients and the engine.
# --------------------------------------------------------------------------------------------- #


_STUB_INSTANCE_HASH = f"sha256:{'c' * 64}"


def _stub_spend_path(monkeypatch, tmp_path, *, instance_hash: str | None = _STUB_INSTANCE_HASH):
    seen = {"clients": 0, "calibrate": []}

    async def _calibrate(**kwargs):
        from databasise.eval.calibration import CalibrationResult, NullIdentity

        seen["calibrate"].append(kwargs["family_name"])
        identity = NullIdentity("bundle@v1", "T1", "m", "cache-bypassed", "sequential")
        return CalibrationResult(
            identity=identity,
            floor=0.25,
            n_questions=3,
            n_resamples=10,
            seed=None,
            wiring_instance_hash=instance_hash,
        )

    def _build(env):
        seen["clients"] += 1
        return {"llm": None}

    monkeypatch.setattr(aa_run, "DEFAULT_V1_ENV_PARITY", tmp_path / "absent.env.parity")
    monkeypatch.setattr(aa_run, "_EVAL_INGEST_STORE_ROOT", tmp_path / "eval")
    monkeypatch.setattr(aa_run, "_load_env_file", lambda path: {})
    monkeypatch.setattr(aa_run, "_build_clients", _build)
    monkeypatch.setattr(aa_run, "Databasise", lambda **kwargs: object())
    monkeypatch.setattr(aa_run, "MultiNamespaceVectorStore", lambda **kwargs: object())
    monkeypatch.setattr(aa_run, "calibrate_family", _calibrate)
    return seen


def test_n_resamples_zero_exits_two_before_any_client(monkeypatch, tmp_path):
    seen = _stub_spend_path(monkeypatch, tmp_path)
    try:
        outcome = aa_run.main(["--split", "dev", "--n-resamples", "0", "--spend"])
    except BaseException as caught:  # noqa: BLE001 - argparse raises SystemExit
        outcome = caught
    assert isinstance(outcome, SystemExit) and outcome.code == 2, outcome
    assert seen["clients"] == 0


def test_two_families_run_inside_one_event_loop(monkeypatch, tmp_path):
    import asyncio

    seen = _stub_spend_path(monkeypatch, tmp_path)
    runs: list[object] = []
    real_run = asyncio.run

    def _spy(coro, *args, **kwargs):
        runs.append(coro)
        return real_run(coro, *args, **kwargs)

    monkeypatch.setattr(aa_run.asyncio, "run", _spy)
    outcome = aa_run.main(["--split", "dev", "--spend"])
    assert outcome == 0
    assert seen["calibrate"] == [GOLD_PASSAGE_FAMILY, ANSWER_LEVEL_FAMILY]
    assert len(runs) == 1, f"asyncio.run was called {len(runs)} times"


def test_a_bare_value_error_is_not_mapped_to_exit_1(monkeypatch, capsys):
    def _boom(root, version):
        raise ValueError("x")

    monkeypatch.setattr(aa_run, "load_bundle", _boom)
    try:
        outcome = aa_run.main(["--split", "dev"])
    except BaseException as caught:  # noqa: BLE001
        outcome = caught
    assert isinstance(outcome, ValueError) and str(outcome) == "x", outcome

    named = getattr(aa_run, "NoMintedBundleError", None)
    assert named is not None, "aa_run has no NoMintedBundleError"

    def _no_bundle(root):
        raise named("no minted bundle found at /nowhere")

    monkeypatch.setattr(aa_run, "_default_bundle_version", _no_bundle)
    capsys.readouterr()
    assert aa_run.main(["--split", "dev"]) == 1
    err_lines = [line for line in capsys.readouterr().err.splitlines() if line.strip()]
    assert len(err_lines) == 1 and err_lines[0].startswith("NoMintedBundleError:"), err_lines


def test_both_eval_mains_print_the_shared_estimate_only_line(monkeypatch, capsys):
    from databasise.eval import corpus_ingest

    def _fail(*args, **kwargs):
        raise AssertionError("no env read, client or engine on the estimate-only path")

    for module in (aa_run, corpus_ingest):
        monkeypatch.setattr(module, "_load_env_file", _fail)
        monkeypatch.setattr(module, "_build_clients", _fail)
        monkeypatch.setattr(module, "Databasise", _fail)

    assert aa_run.main(["--split", "dev"]) == 0
    assert "mode: estimate-only" in capsys.readouterr().out.splitlines()
    assert corpus_ingest.main(["--limit", "1"]) == 0
    assert "mode: estimate-only" in capsys.readouterr().out.splitlines()


# --------------------------------------------------------------------------------------------- #
# 15-16 (TOOL-12, D-13) — --spend persists each family's floor under the eval store root
# --------------------------------------------------------------------------------------------- #


def _floor_store_class():
    import importlib

    try:
        module = importlib.import_module("databasise.seam.floors_store")
    except ImportError:
        module = None
    return getattr(module, "FloorStore", None)


def test_spend_persists_one_floor_per_family(monkeypatch, tmp_path, capsys):
    _stub_spend_path(monkeypatch, tmp_path)

    outcome = aa_run.main(["--split", "dev", "--spend", "--family", GOLD_PASSAGE_FAMILY])

    assert outcome == 0, capsys.readouterr().err
    store_cls = _floor_store_class()
    assert store_cls is not None, "databasise.seam.floors_store has no FloorStore"
    rows = store_cls(tmp_path / "eval").lookup(_STUB_INSTANCE_HASH)
    assert len(rows) == 1, rows
    row = rows[0]
    assert (row.bundle_at_v, row.tier, row.metric) == ("bundle@v1", "T1", "m")
    assert (row.determinism_setting, row.concurrency_setting) == ("cache-bypassed", "sequential")
    assert (row.floor, row.n_questions, row.n_resamples, row.seed) == (0.25, 3, 10, None)


def test_a_result_without_a_hash_is_refused_by_name(monkeypatch, tmp_path, capsys):
    _stub_spend_path(monkeypatch, tmp_path, instance_hash=None)

    outcome = aa_run.main(["--split", "dev", "--spend", "--family", GOLD_PASSAGE_FAMILY])

    assert outcome == 1
    err_lines = [line for line in capsys.readouterr().err.splitlines() if line.strip()]
    assert len(err_lines) == 1 and err_lines[0].startswith("UnkeyableFloorError:"), err_lines
    assert not (tmp_path / "eval" / "floors.db").exists()
