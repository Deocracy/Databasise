"""04-02-PLAN.md Task 3: the envelope's token accounting is a per-``counted_by`` breakdown, never a
merged scalar (Pitfall 5); breakdown ordering is deterministic; a zero-token run still reports its
real ``counted_by`` values with real zero counts; and an ``unbudgetable`` participant raises a
named refusal instead of producing any envelope (D-08, §9).
"""

from __future__ import annotations

import pydantic
import pytest
from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.runner.trace import TokenAccounting
from databasise.seam import Databasise, QueryObject
from databasise.seam._base import _StrictModel
from databasise.seam.tokens import (
    UNBUDGETABLE_SENTINEL,
    TokenBreakdownEntry,
    UnbudgetableParticipantError,
)

_STUB_COMPLETION = "This is a stub completion for the token-accounting tests."


class _StubEmbeddingClient:
    """Reports a real, distinct ``counted_by`` ("stub-embed") with a real, nonzero count."""

    async def embed(self, texts, **kwargs):
        return EmbeddingResult(
            vectors=[[1.0, 0.0, 0.0] for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


class _StubLLMClient:
    """Reports a real, distinct ``counted_by`` ("stub-llm") with a real, nonzero count."""

    async def chat(self, messages, **kwargs):
        return ChatResult(
            text=_STUB_COMPLETION,
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


class _ZeroStubEmbeddingClient:
    """Reports the real ``counted_by`` ("stub-embed") but a real, honest zero count — distinct
    from the ``none`` sentinel a node that never called a tokenizer at all reports."""

    async def embed(self, texts, **kwargs):
        return EmbeddingResult(
            vectors=[[1.0, 0.0, 0.0] for _ in texts],
            tokens=TokenAccounting(prompt_tokens=0, completion_tokens=0, call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


class _ZeroStubLLMClient:
    async def chat(self, messages, **kwargs):
        return ChatResult(
            text=_STUB_COMPLETION,
            tokens=TokenAccounting(prompt_tokens=0, completion_tokens=0, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


class _UnbudgetableEmbeddingClient:
    """Mimics an admitted-``unbudgetable`` opaque participant (§8) — its own token spend cannot be
    counted at all, reported via the sentinel rather than any number."""

    async def embed(self, texts, **kwargs):
        return EmbeddingResult(
            vectors=[[1.0, 0.0, 0.0] for _ in texts],
            tokens=TokenAccounting(counted_by=UNBUDGETABLE_SENTINEL),
            resolved_model_identity="opaque-engine",
        )


def _engine_with(store: dict, *, embedding, llm) -> Databasise:
    return Databasise(
        store_root=store["store_root"],
        workspace=store["workspace"],
        clients={"embedding": embedding, "llm": llm},
    )


async def test_three_distinct_counted_by_values_produce_three_breakdown_entries(synthetic_naive_store):
    engine = _engine_with(synthetic_naive_store, embedding=_StubEmbeddingClient(), llm=_StubLLMClient())

    envelope = await engine.query(QueryObject(text="Which films did Ed Wood direct?"))

    entries_by_counted_by = {entry.counted_by: entry for entry in envelope.token_accounting}
    assert set(entries_by_counted_by) == {"none", "stub-embed", "stub-llm"}

    # "none": chunk-vector, heading-backfill, rerank, assemble, embedder-index — none of them call
    # a client in this wiring/config, so their real, honestly-reported tokens are all zero.
    none_entry = entries_by_counted_by["none"]
    assert (none_entry.prompt_tokens, none_entry.completion_tokens, none_entry.call_count) == (0, 0, 0)

    # "stub-embed": embedder-query only (the naive arm's embedder-index node has no configured
    # sample, so it never calls the embedding client at all — see embedder_index.py) — computed
    # from the values this test itself configured, never re-derived from the code under test.
    embed_entry = entries_by_counted_by["stub-embed"]
    assert (embed_entry.prompt_tokens, embed_entry.completion_tokens, embed_entry.call_count) == (1, 0, 1)

    # "stub-llm": generate only.
    llm_entry = entries_by_counted_by["stub-llm"]
    assert (llm_entry.prompt_tokens, llm_entry.completion_tokens, llm_entry.call_count) == (5, 4, 1)

    # Never merged: the three groups' counts are disjoint sums, not one blended total.
    assert none_entry.counted_by != embed_entry.counted_by != llm_entry.counted_by


async def test_a_zero_token_run_still_reports_its_real_counted_by_values_with_zero_counts(
    synthetic_naive_store,
):
    engine = _engine_with(
        synthetic_naive_store, embedding=_ZeroStubEmbeddingClient(), llm=_ZeroStubLLMClient()
    )

    envelope = await engine.query(QueryObject(text="anything"))

    assert {entry.counted_by for entry in envelope.token_accounting} == {"none", "stub-embed", "stub-llm"}
    for entry in envelope.token_accounting:
        assert entry.prompt_tokens == 0
        assert entry.completion_tokens == 0
        assert entry.cached_read_tokens == 0


async def test_breakdown_ordering_is_sorted_by_counted_by_and_stable_across_two_assemblies(
    synthetic_naive_store,
):
    engine = _engine_with(synthetic_naive_store, embedding=_StubEmbeddingClient(), llm=_StubLLMClient())

    first = await engine.query(QueryObject(text="anything"))
    second = await engine.query(QueryObject(text="anything"))

    order_1 = [entry.counted_by for entry in first.token_accounting]
    order_2 = [entry.counted_by for entry in second.token_accounting]
    assert order_1 == order_2 == sorted(order_1)


async def test_an_unbudgetable_participant_raises_the_named_refusal_and_no_envelope_is_produced(
    synthetic_naive_store,
):
    engine = _engine_with(
        synthetic_naive_store, embedding=_UnbudgetableEmbeddingClient(), llm=_StubLLMClient()
    )

    with pytest.raises(UnbudgetableParticipantError):
        await engine.query(QueryObject(text="anything"))


def test_token_breakdown_entry_declares_no_allowance_or_capacity_field():
    forbidden_substrings = ("allowance", "capacity", "budget_share")
    for field_name in TokenBreakdownEntry.model_fields:
        for forbidden in forbidden_substrings:
            assert forbidden not in field_name.lower(), (
                f"{field_name!r} looks like an allowance/capacity field — spend and capacity must "
                "stay in separate fields (§9)"
            )


def test_token_breakdown_entry_inherits_the_envelope_modules_strict_base():
    assert issubclass(TokenBreakdownEntry, _StrictModel)
    with pytest.raises(pydantic.ValidationError):
        TokenBreakdownEntry(counted_by="x", not_a_real_field="leak")


def test_a_fractional_float_in_a_count_field_raises_validation_error():
    with pytest.raises(pydantic.ValidationError):
        TokenBreakdownEntry(counted_by="x", prompt_tokens=3.5)
