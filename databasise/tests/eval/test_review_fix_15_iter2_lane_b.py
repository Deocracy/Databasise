"""Phase 15 review-fix checks, iteration 2, lane B (15-REVIEW-ITER2-B.md)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from databasise.eval import aa_run


class _Judge:
    def __init__(self, text: str) -> None:
        self._text = text

    async def chat(self, messages):
        return SimpleNamespace(text=self._text)


def _score_with_committed_prompt(text: str) -> float:
    return asyncio.run(
        aa_run.score_answer_level(
            llm_client=_Judge(text),
            prompt_template=aa_run.JUDGE_PROMPT_PATH.read_text(encoding="utf-8"),
            question_text="q",
            gold_answer="g",
            candidate_answer="c",
        )
    )


@pytest.mark.parametrize(
    ("text", "score"),
    [
        ("CORRECT", 1.0),
        ("PARTIAL", 0.5),
        ("INCORRECT", 0.0),
        ("CORRECT — the candidate answer states the same fact(s) as the gold answer.", 1.0),
        ("INCORRECT — the candidate answer contradicts or omits the fact(s) the gold answer states.", 0.0),
        ("PARTIAL — the candidate answer is factually correct but incomplete relative to the gold answer.", 0.5),
        ("- PARTIAL - the candidate answer is factually correct but incomplete\nrelative to the gold answer", 0.5),
    ],
)
def test_every_verdict_form_the_committed_prompt_asks_for_parses(text, score):
    """B-ITER2-WR-01: a verdict alone, or followed by its own option-line definition, parses."""
    assert _score_with_committed_prompt(text) == score


@pytest.mark.parametrize(
    "text",
    [
        "not correct",
        "CORRECT, not INCORRECT",
        "INCORRECT. The candidate is not correct.",
        "PARTIAL — the candidate answer is factually correct but incomplete. Actually INCORRECT.",
        "- CORRECT — the candidate answer states the same fact(s) as the gold answer.\n"
        "- INCORRECT — the candidate answer contradicts or omits the fact(s) the gold answer states.\n"
        "- PARTIAL — the candidate answer is factually correct but incomplete relative to the gold answer.",
    ],
)
def test_a_negated_or_second_verdict_is_still_refused_with_the_committed_prompt(text):
    """B-ITER2-WR-01: only the chosen verdict's own definition is exempt; any other verdict word refuses."""
    with pytest.raises(aa_run.UnparseableJudgeVerdictError):
        _score_with_committed_prompt(text)


def _floor_row(**overrides):
    from databasise.seam.floors_store import FloorRow

    fields = dict(
        wiring_instance_hash="h1",
        bundle_at_v="bundle@v1",
        tier="T1",
        metric="gold_passage_recall",
        determinism_setting="d",
        concurrency_setting="c",
        floor=0.1,
        n_questions=3,
        n_resamples=10,
        seed=1,
        created_at="2026-10-21T00:00:00+00:00",
    )
    return FloorRow(**{**fields, **overrides})


class _LookupFaultFloors:
    def any_floor(self):
        return True

    def lookup(self, wiring_instance_hash):
        import sqlite3

        raise sqlite3.OperationalError("disk I/O error")


def test_a_floors_db_fault_in_stage_1_is_a_store_fault_refusal(tmp_path):
    """B-ITER2-WR-02: a WAL without its SHM makes a gate verb a StoreFault refusal, not a raw sqlite error."""
    from databasise.seam.engine import Databasise
    from databasise.seam.floors_store import FloorStore
    from databasise.seam.refusals import ForeignEngineRefusalError

    FloorStore(tmp_path).record(_floor_row())
    (tmp_path / "floors.db-wal").write_bytes(b"\0" * 64)
    engine = Databasise(store_root=tmp_path, workspace="w")
    for verb in ("promote-next", "promote-now"):
        with pytest.raises(ForeignEngineRefusalError) as excinfo:
            asyncio.run(engine.promote("alias", ["t"], "operator", verb=verb))
        assert (excinfo.value.operation, excinfo.value.failure_class) == ("promote", "StoreFault")
    assert not (tmp_path / "ledger.db").exists()


def test_a_floors_db_fault_in_stage_2_is_a_store_fault_refusal(tmp_path):
    """B-ITER2-WR-02: a lookup fault in _refuse_gate_verb is a StoreFault refusal, not GateNotCalibratedError."""
    from databasise.seam.engine import Databasise
    from databasise.seam.refusals import ForeignEngineRefusalError
    from databasise.wirings.resolve import wiring_for_name

    engine = Databasise(store_root=tmp_path, workspace="w")
    engine._floors = _LookupFaultFloors()
    resolved = wiring_for_name("naive")
    assert resolved is not None
    with pytest.raises(ForeignEngineRefusalError) as excinfo:
        engine._refuse_gate_verb("promote-next", "alias", resolved, ["h1"])
    assert (excinfo.value.operation, excinfo.value.failure_class) == ("promote", "StoreFault")


def test_a_changed_judge_never_re_seals_opened_questions(tmp_path):
    """B-ITER2-WR-03: after open_sealed, a fresh mint (new judge_instance) that would re-seal the opened ids refuses."""
    import hashlib

    from databasise.eval import remint
    from databasise.eval.bundle import SealedPartitionOpenedError, _list_version_numbers, mint_bundle, open_sealed
    from databasise.parity.corpus import load_snapshot

    root = tmp_path / "eval-bundles"
    snapshot = load_snapshot(remint.CORPUS_DIR)
    settings = dict(
        judge_prompt_hash=hashlib.sha256(remint._JUDGE_PROMPT_PATH.read_bytes()).hexdigest(),
        determinism_setting=remint._DETERMINISM_SETTING,
        concurrency_setting=remint._CONCURRENCY_SETTING,
    )
    first = mint_bundle(snapshot, root, judge_instance="judge@1", **settings)
    assert first.splits["sealed"].question_ids
    open_sealed(root, first.version, event="test opening")
    versions_before = _list_version_numbers(root)
    with pytest.raises(SealedPartitionOpenedError):
        mint_bundle(snapshot, root, judge_instance="judge@2", **settings)
    assert _list_version_numbers(root) == versions_before  # nothing written

    # An unopened root still mints fresh for a changed judge.
    other = tmp_path / "other-bundles"
    mint_bundle(snapshot, other, judge_instance="judge@1", **settings)
    assert not mint_bundle(snapshot, other, judge_instance="judge@2", **settings).sealed_opened
