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
