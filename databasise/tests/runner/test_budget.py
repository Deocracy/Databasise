"""Tests for runner/budget.py (Task 2, 01-08-PLAN.md): report-only realised share, metering at a
node's declared boundary, and the five-member token-accounting split. The split and apportion
helpers and their tests are gone (WIRE-18, D-17).
"""

from __future__ import annotations

from databasise.runner.budget import meter, realised_share
from databasise.runner.trace import TokenAccounting


def test_1_spend_exactly_at_allowance_is_within_budget():
    token = meter("n1", ["calls_llm"], allowance=100, tokens=TokenAccounting(prompt_tokens=60, completion_tokens=40))
    assert token.spent == 100
    assert token.state == "within_budget"


def test_2_spend_one_over_allowance_halts():
    token = meter("n1", ["calls_llm"], allowance=100, tokens=TokenAccounting(prompt_tokens=60, completion_tokens=41))
    assert token.spent == 101
    assert token.state == "halted"


def test_3_spend_one_under_allowance_is_within_budget_with_share_below_1():
    token = meter("n1", ["calls_llm"], allowance=100, tokens=TokenAccounting(prompt_tokens=60, completion_tokens=39))
    assert token.state == "within_budget"
    assert realised_share(token.spent, token.allowance) < 1.0


def test_7_multiplicative_fanout_accounts_for_the_product_not_the_sum():
    outer_width = 3
    inner_width = 4
    total_spent = 0
    for _outer in range(outer_width):
        for _inner in range(inner_width):
            token = meter("leaf", ["calls_llm"], allowance=10_000, tokens=TokenAccounting(prompt_tokens=1))
            total_spent += token.spent
    assert total_spent == outer_width * inner_width
    assert total_spent != outer_width + inner_width


def test_9_metering_location_only_the_declaring_node_accrues_spend():
    upstream = meter("expensive", ["calls_llm"], allowance=10_000, tokens=TokenAccounting(prompt_tokens=50, completion_tokens=10))
    downstream = meter("consumer", [], allowance=10_000, tokens=TokenAccounting())
    assert upstream.spent == 60
    assert downstream.spent == 0


def test_10_token_accounting_members_are_five_distinct_fields_never_aggregated():
    tokens = TokenAccounting(prompt_tokens=1, completion_tokens=2, cached_read_tokens=3, call_count=4, counted_by="tok@1")
    as_dict = tokens.to_dict()
    assert set(as_dict) == {"prompt_tokens", "completion_tokens", "cached_read_tokens", "call_count", "counted_by"}
    assert as_dict["prompt_tokens"] == 1
    assert as_dict["completion_tokens"] == 2
    assert as_dict["cached_read_tokens"] == 3
    assert as_dict["call_count"] == 4
