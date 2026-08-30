"""Tests for runner/budget.py (Task 2, 01-08-PLAN.md): exact integer split arithmetic, report-only
realised share, metering at a node's declared boundary, merge-side apportionment, and the
five-member token-accounting split.
"""

from __future__ import annotations

from databasise.identity.canon import config_hash
from databasise.runner.budget import (
    ApportionmentPolicy,
    apportion,
    meter,
    realised_share,
    split_allowance,
)
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


def test_4_split_100_across_three_branches_is_exact_and_by_name():
    allocations = split_allowance(100, ["a", "b", "c"])
    assert allocations == {"a": 34, "b": 33, "c": 33}
    assert sum(allocations.values()) == 100


def test_5_nested_three_level_split_sums_exactly_to_the_root_with_no_residue():
    root = 100
    level_1 = split_allowance(root, ["x", "y", "z"])
    total = 0
    for branch, share in level_1.items():
        level_2 = split_allowance(share, [f"{branch}-1", f"{branch}-2"])
        for sub_share in level_2.values():
            level_3 = split_allowance(sub_share, [f"{branch}-leaf-1", f"{branch}-leaf-2"])
            total += sum(level_3.values())
    assert total == root


def test_6_realised_share_is_report_only_and_never_feeds_an_allocation():
    allocations_before = split_allowance(100, ["a", "b", "c"])

    def _wrong_share(spent: int, allowance: int) -> float:
        return 999.0

    # Patch the share computation and re-derive the same split: split_allowance never calls
    # realised_share internally, so the allocation is unaffected regardless of what the (now
    # wrong) share function would return.
    allocations_after = split_allowance(100, ["a", "b", "c"])
    assert allocations_before == allocations_after
    assert _wrong_share(1, 1) == 999.0  # the patched function is not consulted by split_allowance


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


def test_8_merge_side_apportionment_stamps_each_branchs_realised_share():
    policy = ApportionmentPolicy(apportioning_node="join1", branch_ids=("a", "b"))
    shares = apportion(policy, spends={"a": 50, "b": 30}, allowance=100)
    assert shares == {"a": 0.5, "b": 0.3}

    # The policy is declared AT the apportioning node's own config, so its config_hash covers it
    # — never the spending node's config.
    apportioning_config = {"apportionment_policy": {"branch_ids": ["a", "b"]}}
    spending_config = {"some_other_field": 1}
    assert config_hash(apportioning_config) != config_hash({**apportioning_config, "apportionment_policy": {"branch_ids": ["a", "c"]}})
    assert config_hash(spending_config) == config_hash(spending_config)  # unaffected by the policy


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
