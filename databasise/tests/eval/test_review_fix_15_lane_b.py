"""Phase 15 review-fix checks for the eval and floor-store code (15-REVIEW.md, lane B findings)."""

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


def _score(text: str) -> float:
    return asyncio.run(
        aa_run.score_answer_level(
            llm_client=_Judge(text),
            prompt_template="{question} {gold_answer} {candidate_answer}",
            question_text="q",
            gold_answer="g",
            candidate_answer="c",
        )
    )


@pytest.mark.parametrize(
    ("text", "score"),
    [
        ("CORRECT", 1.0),
        ("CORRECT.", 1.0),
        ("**CORRECT**", 1.0),
        ("Verdict: CORRECT", 1.0),
        ("**Verdict:** PARTIAL", 0.5),
        ("INCORRECT - the candidate names the wrong year.", 0.0),
        ("CORRECT. The candidate is correct on every point.", 1.0),
    ],
)
def test_judge_verdict_parses_a_leading_verdict(text, score):
    """B-CR-01: the TOOL-12 forms still parse."""
    assert _score(text) == score


@pytest.mark.parametrize(
    "text",
    [
        "not correct",
        "Partially correct",
        "The answer is not CORRECT; verdict: INCORRECT",
        "- CORRECT — matches\n- PARTIAL — some\n- INCORRECT — wrong\nVerdict: INCORRECT",
        "CORRECT? No, INCORRECT.",
    ],
)
def test_judge_verdict_refuses_a_negated_or_echoed_verdict(text):
    """B-CR-01: a negation, a partial word or an echoed option list never scores as a verdict."""
    with pytest.raises(aa_run.UnparseableJudgeVerdictError):
        _score(text)


def _stub_spend_path(monkeypatch, tmp_path):
    """Patch every client, engine and store constructor on aa_run's --spend path to a stub."""
    monkeypatch.setattr(aa_run, "_EVAL_INGEST_STORE_ROOT", tmp_path / "eval-store")
    monkeypatch.setattr(aa_run, "_load_env_file", lambda path: {})
    monkeypatch.setattr(aa_run, "_build_clients", lambda env: {})
    monkeypatch.setattr(aa_run, "Databasise", lambda **kwargs: SimpleNamespace(store_root=tmp_path))
    monkeypatch.setattr(aa_run, "MultiNamespaceVectorStore", lambda **kwargs: None)


def test_a_repeated_family_is_estimated_and_run_once(monkeypatch, tmp_path, capsys):
    """B-WR-01: `--family X --family X` runs X once, matching the estimate."""
    _stub_spend_path(monkeypatch, tmp_path)
    seen: list[tuple[str, ...]] = []

    async def record_families(*, families, **kwargs):
        seen.append(tuple(families))
        raise aa_run.NoMintedBundleError("stop after recording the families")

    monkeypatch.setattr(aa_run, "_calibrate_all", record_families)
    assert aa_run.main(["--family", "answer_level", "--family", "answer_level", "--spend"]) == 1
    assert seen == [("answer_level",)]
