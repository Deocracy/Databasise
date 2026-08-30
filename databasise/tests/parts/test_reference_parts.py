"""Tests for D-04's four executable parts_core reference parts.

Covers plan 01-04's <behavior> Tests 1-6: passthrough relays inputs unchanged; the fake
retriever is deterministic and network-free; the fake LLM caller reports real TokenAccounting
and a genuine cache hit on a repeat call; the fixpoint body halts on its declared condition or
its round bound; and deny-by-default reaches the part boundary itself, not only the validator.
"""

from __future__ import annotations

import pytest

from databasise.parts.schema import NodeContext
from databasise.parts_core import CapabilityScopedStores, UndeclaredEffectError
from databasise.parts_core.fake_llm_caller import FAKE_LLM_CALLER_PART
from databasise.parts_core.fake_retriever import FAKE_RETRIEVER_PART
from databasise.parts_core.fixpoint_body import FIXPOINT_BODY_PART
from databasise.parts_core.passthrough import PASSTHROUGH_PART
from databasise.stores.kv import SqliteKVStore
from databasise.validator.depth import derive_execution_mode


async def test_1_passthrough_relays_inputs_unchanged_declares_no_effects_and_is_in_process():
    ctx = NodeContext(node_id="n1", config=None, inputs={"x": 1}, stores={})

    result = await PASSTHROUGH_PART.body(ctx)

    assert result == {"x": 1}
    assert PASSTHROUGH_PART.effects == []
    assert derive_execution_mode(PASSTHROUGH_PART.effects, PASSTHROUGH_PART.kind) == "in-process"


async def test_2_fake_retriever_is_deterministic_and_declares_reads_vector():
    ctx = NodeContext(node_id="n1", config={"query": "graph databases"}, inputs={}, stores={})

    result_1 = await FAKE_RETRIEVER_PART.body(ctx)
    result_2 = await FAKE_RETRIEVER_PART.body(ctx)

    assert result_1 == result_2
    assert result_1["results"]  # non-empty for a known fixture query, no network/model access
    assert FAKE_RETRIEVER_PART.effects == ["reads_vector"]


async def test_3_fake_llm_caller_declares_calls_llm_and_reports_separate_token_accounting(
    store_root,
):
    kv = SqliteKVStore(namespace="cache", workspace="test", store_root=store_root)
    ctx = NodeContext(node_id="n1", config={"prompt": "hello"}, inputs={}, stores={"kv": kv})

    result = await FAKE_LLM_CALLER_PART.body(ctx)
    tokens = result["tokens"]

    assert FAKE_LLM_CALLER_PART.effects == ["calls_llm"]
    assert tokens.prompt_tokens > 0
    assert tokens.completion_tokens > 0
    assert tokens.cached_read_tokens == 0  # first call: nothing cached yet
    assert tokens.call_count == 1
    assert tokens.counted_by != "none"
    await kv.finalize()


async def test_4_second_identical_call_to_the_fake_llm_caller_is_a_genuine_cache_hit(store_root):
    kv = SqliteKVStore(namespace="cache", workspace="test", store_root=store_root)
    ctx = NodeContext(node_id="n1", config={"prompt": "hello"}, inputs={}, stores={"kv": kv})

    first = await FAKE_LLM_CALLER_PART.body(ctx)
    second = await FAKE_LLM_CALLER_PART.body(ctx)

    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert second["tokens"].call_count == first["tokens"].call_count + 1
    await kv.finalize()


async def test_5_fixpoint_body_halts_on_its_declared_condition_or_at_the_round_bound():
    ctx_condition_met = NodeContext(
        node_id="n1", config={"halt_at": 3, "max_rounds": 10}, inputs={}, stores={}
    )
    result_condition_met = await FIXPOINT_BODY_PART.body(ctx_condition_met)
    assert result_condition_met == {"rounds_run": 3, "halted_on": "halt_condition_met"}

    ctx_never_true = NodeContext(
        node_id="n1", config={"halt_at": None, "max_rounds": 5}, inputs={}, stores={}
    )
    result_never_true = await FIXPOINT_BODY_PART.body(ctx_never_true)
    assert result_never_true == {"rounds_run": 5, "halted_on": "max_rounds_reached"}

    assert (
        derive_execution_mode(FIXPOINT_BODY_PART.effects, FIXPOINT_BODY_PART.kind) == "subprocess"
    )


def test_6_reference_part_cannot_reach_an_undeclared_effect():
    scoped = CapabilityScopedStores(
        {"kv": object(), "vector": object()}, FAKE_RETRIEVER_PART.effects
    )
    scoped.require("reads_vector")  # declared — succeeds

    with pytest.raises(UndeclaredEffectError):
        scoped.require("reads_kv")  # undeclared — refused at the part boundary itself
