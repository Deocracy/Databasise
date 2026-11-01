"""Phase 08 audit leftover: ``tokens_from_usage`` (the ``lightrag/full-ingest`` node's accounting
from the v1 driver's ``usage["llm"]``) must treat a negative count like a missing usage -- the
``unbudgetable`` sentinel with the call count kept -- never ``int()`` it into a negative spend. The
frozen trace schema (``evidence/rig-trace.databasise.schema.json``) requires ``prompt_tokens`` and
``realised_budget_share`` to be ``>= 0``.
"""

from __future__ import annotations

import pytest

from databasise.parts_core.lightrag.full_ingest import tokens_from_usage


@pytest.mark.parametrize(
    "llm",
    [
        {"call_count": 2, "total_tokens": -5, "prompt_tokens": -5, "completion_tokens": 0},
        {"call_count": 2, "total_tokens": 5, "prompt_tokens": -1, "completion_tokens": 6},
        {"call_count": 2, "total_tokens": 5, "prompt_tokens": 6, "completion_tokens": -1},
    ],
    ids=["negative-total", "negative-prompt", "negative-completion"],
)
def test_a_negative_llm_count_is_unbudgetable_with_the_call_count_kept(llm):
    tokens = tokens_from_usage({"llm": llm})

    assert tokens.counted_by == "unbudgetable"
    assert tokens.call_count == 2
    assert (tokens.prompt_tokens, tokens.completion_tokens) == (0, 0)


def test_a_non_negative_llm_usage_still_counts():
    tokens = tokens_from_usage({"llm": {"call_count": 1, "total_tokens": 7, "prompt_tokens": 5, "completion_tokens": 2}})

    assert tokens.counted_by == "v1-subprocess"
    assert (tokens.prompt_tokens, tokens.completion_tokens, tokens.call_count) == (5, 2, 1)
