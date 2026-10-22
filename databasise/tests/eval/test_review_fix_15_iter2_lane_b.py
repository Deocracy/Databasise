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
