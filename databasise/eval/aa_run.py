"""The A/A calibration driver (MACH-03, Falsifier 5): the missing runnable piece between
`databasise/eval/calibration.py`'s pure statistical procedure and a real, run-derived floor.

**Exact invocation:**

    uv run python -m databasise.eval.aa_run --split dev [--family gold_passage] [--spend]

**Nothing here makes a live call by default.** Without ``--spend``, :func:`main` prints
:func:`estimate_calls`' real, computed call-count projection and returns, having constructed no
client, opened no store, and made no query — mirroring
``databasise/eval/corpus_ingest.py``'s own "estimate first, spend only on explicit opt-in"
contract exactly. With ``--spend``, it builds real clients from ``v1/.env.parity`` through
``databasise.parity.run_arm``'s own ``_build_clients``/``_load_env_file`` — the identical
construction path ``run_arm.py``/``corpus_ingest.py``/``remint.py`` already use — and runs each
requested `§EV.2` target family through :func:`calibrate_family` against the same store
``corpus_ingest.py``'s own ``--spend`` path ingests the eval-corpus into.

**This module is genuine, runnable code that has not been invoked for real in this environment.**
Its real invocation is gated behind 06-17's own blocking spend checkpoint — the same posture
``build_hipporag_index.py`` and ``corpus_ingest.py`` both declare in their own module docstrings.

**Two scorers, one driver, no second path to a floor.** :func:`score_gold_passage` (the `T1`
``gold_passage`` leg, retrieval-only, no judge) and :func:`score_answer_level` (the `T0`
``answer_level`` leg, one judge call per question per pass) are the two per-question scorers
`§EV.2`'s two target families need. :func:`run_one_pass` runs one arm once over a named split and
scores it with whichever scorer matches the requested family; :func:`calibrate_family` runs that
pass twice, feeds the two score mappings to ``calibration.paired_differences``, and hands the
result to ``calibration.calibrate_aa_floor`` — never catching that function's own
``UnusableFloorError``/``StaleNullError`` refusals, and never re-implementing them. Every
``NullIdentity`` field this module mints is read from the loaded bundle or the requested family's
own record — never a literal in this file.

**`PARTIAL` is scored `0.5` — this module's own declared assumption, not a value the committed
judge prompt states.** ``judge-prompt-v1.txt`` defines three verdicts (``CORRECT``/``PARTIAL``/
``INCORRECT``) but assigns no numeric weight to any of them; the midpoint is recorded here, as a
module constant with this comment, so a later reader prices it as a choice. A different weight
would shift both families' measured nulls; it would not invalidate the comparison between them,
since the same weight applies to both passes of both legs.

**`estimate_calls` is a call-count projection, never a token or currency figure.** This module
carries no measured per-question token figure to derive a spend estimate from, and inventing a
cost band here would be exactly the kind of fabricated-plausible-number substitution this
project's own conventions forbid (the same discipline ``FALSIFIER-5-EVIDENCE.md`` already states:
"No floor value is reported anywhere in this document ... even a placeholder ... would be exactly
the kind of fabricated-plausible-value substitution this project's own conventions forbid").
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from databasise.eval.bundle import (
    ANSWER_LEVEL_FAMILY,
    GOLD_PASSAGE_FAMILY,
    EvalBundle,
    load_bundle,
)
from databasise.eval.bundle import _list_version_numbers as _bundle_version_numbers
from databasise.eval.calibration import (
    CalibrationResult,
    NullIdentity,
    UnusableFloorError,
    calibrate_aa_floor,
    paired_differences,
)
from databasise.eval.corpus_ingest import _EVAL_INGEST_STORE_ROOT, _EVAL_INGEST_WORKSPACE
from databasise.eval.remint import _COMMITTED_BUNDLE_ROOT
from databasise.eval.remint import _JUDGE_PROMPT_PATH as JUDGE_PROMPT_PATH
from databasise.parity.run_arm import (
    DEFAULT_V1_ENV_PARITY,
    MissingParityEnvError,
    MissingParityEnvKeyError,
    _build_clients,
    _load_env_file,
)
from databasise.seam import Databasise
from databasise.seam.evidence import resolve_evidence_ref
from databasise.seam.query import QueryObject
from databasise.seam.refusals import SeamRefusalError
from databasise.seam.trace_store import TraceStore
from databasise.stores.vector import MultiNamespaceVectorStore

# NullIdentity.metric — stable, declared once, never inlined at a call site.
GOLD_PASSAGE_METRIC = "gold_passage_recall"
ANSWER_LEVEL_METRIC = "answer_level_correctness"

_METRIC_BY_FAMILY: dict[str, str] = {
    GOLD_PASSAGE_FAMILY: GOLD_PASSAGE_METRIC,
    ANSWER_LEVEL_FAMILY: ANSWER_LEVEL_METRIC,
}

# The committed judge prompt's three verdicts (judge-prompt-v1.txt), mapped to a numeric score.
# PARTIAL's weight of 0.5 is this module's own declared assumption — see module docstring.
VERDICT_SCORES: dict[str, float] = {
    "CORRECT": 1.0,
    "PARTIAL": 0.5,
    "INCORRECT": 0.0,
}

_DEFAULT_FAMILIES: tuple[str, ...] = (GOLD_PASSAGE_FAMILY, ANSWER_LEVEL_FAMILY)
_UNCALIBRATABLE_SPLITS: tuple[str, ...] = ("holdout", "sealed")


class UnparseableJudgeVerdictError(RuntimeError):
    """Raised by :func:`score_answer_level` when the judge's response does not parse to one of
    :data:`VERDICT_SCORES`'s three known verdicts. Carries the raw response text on
    ``response_text`` — in ``databasise.clients.openai_compat.ModelIdentityMissingError``'s own
    house shape (specifics on an attribute, a constructed message, a docstring explaining why).

    Refuses rather than defaulting to a score because an unparseable verdict is an unknown, and
    scoring an unknown as ``INCORRECT`` would silently widen the measured null with fabricated
    failures — the precise direction that makes a promotion floor too permissive.
    """

    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        super().__init__(
            f"judge response {response_text!r} does not parse to a known verdict "
            f"({', '.join(sorted(VERDICT_SCORES))}) — refusing to substitute a default score for a "
            "verdict the scorer could not parse: scoring an unknown as INCORRECT would silently "
            "widen the measured null with fabricated failures, which is the precise direction that "
            "makes a promotion floor too permissive"
        )


class SplitNotCalibratableError(ValueError):
    """Raised for an unknown split name, and for ``holdout``/``sealed`` by name — those two
    partitions carry their own recorded-use protocol (``record_holdout_use``, ``open_sealed``)
    whose event vocabulary does not include an A/A calibration, so reading them here would spend a
    one-shot opening on a null.
    """

    def __init__(self, split_name: str, *, reason: str) -> None:
        self.split_name = split_name
        super().__init__(f"SplitNotCalibratableError: split {split_name!r} cannot be A/A calibrated — {reason}")


@dataclass(frozen=True)
class PassResult:
    """One A/A pass over a named split: the question-id-to-score mapping the §AA.1 procedure
    needs, plus the node traces of every run this pass made — the §AA.2 cache-bypass precondition
    is checked from these traces, never asserted.
    """

    scores: dict[str, float]
    node_traces: tuple[Any, ...]


@dataclass(frozen=True)
class AARunResult:
    """The observed, computed outcome of a real ``--spend`` A/A run — every field a real value
    read from the run's own accounting, mirroring ``build_hipporag_index.IndexBuildResult``'s own
    shape. Carries no field for a value this run did not produce.
    """

    bundle_version: str
    split: str
    question_ids: tuple[str, ...]
    results_by_family: dict[str, CalibrationResult]
    n_resamples: int
    seed: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_version": self.bundle_version,
            "split": self.split,
            "question_ids": list(self.question_ids),
            "results_by_family": {
                name: {
                    "identity": asdict(result.identity),
                    "floor": result.floor,
                    "n_questions": result.n_questions,
                    "n_resamples": result.n_resamples,
                    "seed": result.seed,
                }
                for name, result in self.results_by_family.items()
            },
            "n_resamples": self.n_resamples,
            "seed": self.seed,
        }


# --------------------------------------------------------------------------------------------- #
# The two per-question scorers
# --------------------------------------------------------------------------------------------- #


def score_gold_passage(envelope: Any, *, gold_document_ids: Sequence[str], vector_store: Any) -> float:
    """The `T1` `gold_passage` leg: recall over the gold set, not precision over the returned set
    — the fraction of ``gold_document_ids`` represented among ``envelope``'s own resolved
    evidence. Resolves each ``EvidenceRef`` through ``resolve_evidence_ref`` — never by
    reconstructing a store handle of its own. An empty ``evidence`` list returns ``0.0`` without
    touching the store. Lets :class:`~databasise.seam.evidence.UnresolvableEvidenceReferenceError`
    propagate — a reference the store lost is a broken run, not a low score. No top-k truncation
    and no score threshold: the arm already decided what it returned, and re-filtering here would
    key the null to a parameter the bundle does not name.

    WR-01 gap closure: an empty ``gold_document_ids`` (a bundle-authoring mistake, not malicious
    input — ``_check_family_covers_questions`` only checks a question id is present in
    ``family.targets``, never that its value is non-empty) raises a named ``ValueError`` rather
    than crashing on a bare ``ZeroDivisionError`` — this module's own "refuse by name, never crash
    opaquely" house style, applied to the one path that was left unguarded.
    """
    gold_ids = list(gold_document_ids)
    if not gold_ids:
        raise ValueError(
            "score_gold_passage: gold_document_ids is empty — cannot compute a recall fraction "
            "with zero gold documents"
        )

    if not envelope.evidence:
        return 0.0

    resolved_document_ids: set[str] = set()
    for ref in envelope.evidence:
        record = resolve_evidence_ref(ref, vector_store)
        resolved_document_ids.add(str(record["document_id"]))

    matched = sum(1 for doc_id in gold_ids if str(doc_id) in resolved_document_ids)
    return matched / len(gold_ids)


async def score_answer_level(
    *,
    llm_client: Any,
    prompt_template: str,
    question_text: str,
    gold_answer: str,
    candidate_answer: str,
) -> float:
    """The `T0` `answer_level` leg: format the committed judge prompt with the three named
    placeholders, make exactly one ``llm_client.chat`` call, and map the returned verdict to a
    number via :data:`VERDICT_SCORES`. Matches the verdict as the first whole word of the
    stripped, upper-cased response — a judge that appends a sentence still parses — with no
    fuzzier recovery attempted: a prompt that says "and nothing else" is entitled to be taken at
    its word. No retry, no fallback model, no cache. Raises
    :class:`UnparseableJudgeVerdictError` on a miss, carrying the raw (unstripped) response text.
    """
    prompt = prompt_template.format(
        question=question_text, gold_answer=gold_answer, candidate_answer=candidate_answer
    )
    result = await llm_client.chat([{"role": "user", "content": prompt}])

    stripped = result.text.strip()
    words = stripped.split()
    verdict = words[0].upper() if words else ""
    if verdict not in VERDICT_SCORES:
        raise UnparseableJudgeVerdictError(result.text)
    return VERDICT_SCORES[verdict]


# --------------------------------------------------------------------------------------------- #
# Split/family validation — shared by estimate_calls, run_one_pass and calibrate_family so the
# dry-run projection and the real run agree on what is calibratable without a second check path
# --------------------------------------------------------------------------------------------- #


def _resolve_split(bundle: EvalBundle, split_name: str) -> tuple[str, ...]:
    if split_name in _UNCALIBRATABLE_SPLITS:
        raise SplitNotCalibratableError(
            split_name,
            reason=(
                "'holdout' and 'sealed' carry a recorded-use protocol (record_holdout_use, "
                "open_sealed) whose event vocabulary does not include an A/A calibration, so "
                "reading them here would spend a one-shot opening on a null"
            ),
        )
    if split_name not in bundle.splits:
        raise SplitNotCalibratableError(
            split_name, reason=f"bundle {bundle.version!r} carries no split named {split_name!r}"
        )
    return bundle.splits[split_name].question_ids


def _check_family_covers_questions(bundle: EvalBundle, family_name: str, question_ids: Sequence[str]) -> None:
    family = next((f for f in bundle.target_families if f.name == family_name), None)
    if family is None:
        raise ValueError(f"bundle {bundle.version!r} carries no target family {family_name!r}")

    missing_targets = [qid for qid in question_ids if qid not in family.targets]
    if missing_targets:
        raise ValueError(
            f"question id(s) {missing_targets} in the requested split are absent from family "
            f"{family_name!r}'s own targets"
        )
    if family_name == ANSWER_LEVEL_FAMILY:
        missing_answers = [qid for qid in question_ids if qid not in bundle.gold_answers]
        if missing_answers:
            raise ValueError(
                f"question id(s) {missing_answers} in the requested split are absent from bundle "
                f"{bundle.version!r}'s gold_answers"
            )


# --------------------------------------------------------------------------------------------- #
# run_one_pass — one arm run, once, over a named split's question ids
# --------------------------------------------------------------------------------------------- #


async def run_one_pass(
    *,
    engine: Any,
    bundle: EvalBundle,
    question_ids: Sequence[str],
    family_name: str,
    llm_client: Any = None,
    vector_store: Any = None,
) -> PassResult:
    """Run ``engine`` once over ``question_ids`` (in sorted order), scoring each returned envelope
    with whichever of the two per-question scorers matches ``family_name``. Refuses (``ValueError``,
    via :func:`_check_family_covers_questions`) before any query runs if a question id is absent
    from the family's own targets or gold answers. Refuses (``RuntimeError``) by name if any
    envelope reports ``partial`` or ``degraded`` true — a confounded pass cannot calibrate a null,
    the same refusal-at-the-report-layer discipline
    ``databasise.parity.run_cross_modality.DegradedCrossModalityRunError`` already applies. For
    each envelope, resolves its ``trace_token`` through a fresh :class:`TraceStore` opened on
    ``engine``'s own ``store_root`` and accumulates that run record's ``nodes`` into
    ``PassResult.node_traces`` — the §AA.2 precondition input.
    """
    _check_family_covers_questions(bundle, family_name, question_ids)

    question_by_id = {q.id: q for q in bundle.questions}
    family = next(f for f in bundle.target_families if f.name == family_name)
    prompt_template = JUDGE_PROMPT_PATH.read_text(encoding="utf-8") if family_name == ANSWER_LEVEL_FAMILY else None

    trace_store = TraceStore(engine.store_root)
    scores: dict[str, float] = {}
    node_traces: list[Any] = []

    for question_id in sorted(question_ids):
        question = question_by_id.get(question_id)
        if question is None:
            raise ValueError(
                f"run_one_pass: question id {question_id!r} is not present in bundle "
                f"{bundle.version!r}'s own questions"
            )

        envelope = await engine.query(QueryObject(text=question.text))

        if envelope.partial or envelope.degraded:
            raise RuntimeError(
                f"run_one_pass: question {question_id!r} reported partial={envelope.partial!r} "
                f"degraded={envelope.degraded!r} — a confounded pass cannot calibrate a null"
            )

        if family_name == GOLD_PASSAGE_FAMILY:
            score = score_gold_passage(
                envelope, gold_document_ids=family.targets[question_id], vector_store=vector_store
            )
        else:
            score = await score_answer_level(
                llm_client=llm_client,
                prompt_template=prompt_template,
                question_text=question.text,
                gold_answer=bundle.gold_answers[question_id],
                candidate_answer=envelope.answer,
            )

        scores[question_id] = score

        if envelope.trace_token is not None:
            record = trace_store.resolve(envelope.trace_token)
            node_traces.extend(record.get("nodes", []))

    return PassResult(scores=scores, node_traces=tuple(node_traces))


# --------------------------------------------------------------------------------------------- #
# calibrate_family — the paired calibration itself, never a second path to a floor
# --------------------------------------------------------------------------------------------- #


async def calibrate_family(
    *,
    engine: Any,
    bundle: EvalBundle,
    split_name: str,
    family_name: str,
    llm_client: Any = None,
    vector_store: Any = None,
    n_resamples: int | None = None,
    seed: int | None = None,
) -> CalibrationResult:
    """Run ``family_name`` twice over ``split_name``'s question ids, feed the two score mappings
    to ``paired_differences``, and hand the diffs plus both passes' node traces to
    ``calibrate_aa_floor`` with a ``NullIdentity`` built entirely from ``bundle``'s and the
    family's own recorded fields. Never catches ``UnusableFloorError``, ``StaleNullError`` or
    ``paired_differences``' unequal-set ``ValueError`` — every one of them is a refusal this
    module exists to preserve, and swallowing any of them would produce a number nobody could
    trust.
    """
    question_ids = _resolve_split(bundle, split_name)
    _check_family_covers_questions(bundle, family_name, question_ids)

    run_a = await run_one_pass(
        engine=engine,
        bundle=bundle,
        question_ids=question_ids,
        family_name=family_name,
        llm_client=llm_client,
        vector_store=vector_store,
    )
    run_b = await run_one_pass(
        engine=engine,
        bundle=bundle,
        question_ids=question_ids,
        family_name=family_name,
        llm_client=llm_client,
        vector_store=vector_store,
    )

    metric = _METRIC_BY_FAMILY[family_name]
    diffs = paired_differences(run_a.scores, run_b.scores, metric)

    family = next(f for f in bundle.target_families if f.name == family_name)
    identity = NullIdentity(
        bundle_at_v=bundle.version,
        tier=family.tier,
        metric=metric,
        determinism_setting=bundle.determinism_setting,
        concurrency_setting=bundle.concurrency_setting,
    )

    kwargs: dict[str, Any] = {}
    if n_resamples is not None:
        kwargs["n_resamples"] = n_resamples

    return calibrate_aa_floor(
        diffs,
        identity=identity,
        run_a_nodes=run_a.node_traces,
        run_b_nodes=run_b.node_traces,
        seed=seed,
        **kwargs,
    )


# --------------------------------------------------------------------------------------------- #
# estimate_calls — a real, computed call-count projection, never a token/currency figure
# --------------------------------------------------------------------------------------------- #


def estimate_calls(bundle: EvalBundle, *, split_name: str, families: Sequence[str]) -> dict[str, Any]:
    """The question count, the two passes, and — per requested family — the number of engine
    queries and judge calls a real run would make. ``gold_passage`` makes zero judge calls;
    ``answer_level`` makes one per question per pass. A call-count projection, not a token or
    currency figure — see module docstring for why no cost band is attached.
    """
    question_ids = _resolve_split(bundle, split_name)
    n_questions = len(question_ids)

    per_family: dict[str, dict[str, int]] = {}
    for family_name in families:
        _check_family_covers_questions(bundle, family_name, question_ids)
        judge_calls_per_pass = n_questions if family_name == ANSWER_LEVEL_FAMILY else 0
        per_family[family_name] = {
            "engine_queries": n_questions * 2,
            "judge_calls": judge_calls_per_pass * 2,
        }

    return {
        "bundle_version": bundle.version,
        "split": split_name,
        "n_questions": n_questions,
        "passes": 2,
        "per_family": per_family,
        "note": (
            "a call-count projection, not a token or currency figure — this module carries no "
            "measured per-question token figure to derive one from"
        ),
    }


# --------------------------------------------------------------------------------------------- #
# main — dry-run by default
# --------------------------------------------------------------------------------------------- #


def _default_bundle_version(bundle_root: Path) -> str:
    numbers = _bundle_version_numbers(bundle_root)
    if not numbers:
        raise ValueError(f"no minted bundle found at {bundle_root}")
    return f"bundle@v{max(numbers)}"


def main(argv: list[str] | None = None) -> int:
    """``uv run python -m databasise.eval.aa_run --split dev [--family gold_passage] [--spend]``
    — the exact invocation this module's own docstring names. Without ``--spend``: prints
    :func:`estimate_calls`' real projection and returns 0, constructing no client, opening no
    store, and making no query. With ``--spend``: prints the identical projection first, then
    builds real clients from ``v1/.env.parity``, constructs one ``Databasise`` against the same
    store ``corpus_ingest.py``'s own ``--spend`` path ingests the eval-corpus into, runs each
    requested family through :func:`calibrate_family`, and prints the resulting
    :class:`AARunResult` as indented JSON. Exit codes: 0 on a completed run (estimate-only or
    real), 1 on any named refusal, with the refusal's message on stderr.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-version", default=None)
    parser.add_argument("--split", default="dev")
    parser.add_argument("--family", action="append", choices=list(_DEFAULT_FAMILIES), default=None)
    parser.add_argument("--n-resamples", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--spend", action="store_true", default=False)
    args = parser.parse_args(argv)

    families = tuple(args.family) if args.family else _DEFAULT_FAMILIES

    try:
        bundle_version = args.bundle_version or _default_bundle_version(_COMMITTED_BUNDLE_ROOT)
        bundle = load_bundle(_COMMITTED_BUNDLE_ROOT, bundle_version)
        projection = estimate_calls(bundle, split_name=args.split, families=families)
    except (SplitNotCalibratableError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(projection, indent=2))

    if not args.spend:
        print("mode: estimate-only")
        return 0

    try:
        env = _load_env_file(DEFAULT_V1_ENV_PARITY)
        clients = _build_clients(env)
    except (MissingParityEnvError, MissingParityEnvKeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    engine = Databasise(
        store_root=_EVAL_INGEST_STORE_ROOT,
        workspace=_EVAL_INGEST_WORKSPACE,
        clients=clients,
    )
    vector_store = MultiNamespaceVectorStore(
        workspace=_EVAL_INGEST_WORKSPACE, store_root=_EVAL_INGEST_STORE_ROOT
    )

    results_by_family: dict[str, CalibrationResult] = {}
    try:
        for family_name in families:
            results_by_family[family_name] = asyncio.run(
                calibrate_family(
                    engine=engine,
                    bundle=bundle,
                    split_name=args.split,
                    family_name=family_name,
                    llm_client=clients.get("llm"),
                    vector_store=vector_store,
                    n_resamples=args.n_resamples,
                    seed=args.seed,
                )
            )
    except (
        SplitNotCalibratableError,
        UnparseableJudgeVerdictError,
        UnusableFloorError,
        RuntimeError,  # WR-02: run_one_pass's own confounded (partial/degraded) pass refusal
        SeamRefusalError,  # WR-02: any refusal the real engine.query() call itself raises
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    first_result = next(iter(results_by_family.values()))
    result = AARunResult(
        bundle_version=bundle.version,
        split=args.split,
        question_ids=tuple(bundle.splits[args.split].question_ids),
        results_by_family=results_by_family,
        n_resamples=first_result.n_resamples,
        seed=args.seed,
    )
    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "ANSWER_LEVEL_METRIC",
    "GOLD_PASSAGE_METRIC",
    "JUDGE_PROMPT_PATH",
    "VERDICT_SCORES",
    "AARunResult",
    "PassResult",
    "SplitNotCalibratableError",
    "UnparseableJudgeVerdictError",
    "calibrate_family",
    "estimate_calls",
    "main",
    "run_one_pass",
    "score_answer_level",
    "score_gold_passage",
]
