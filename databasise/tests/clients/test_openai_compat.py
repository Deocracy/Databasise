"""Behavior tests for ``OpenAICompatibleClient``. Every test reaches the SDK surface through a
stub double (``_StubOpenAIClient`` below), never a real ``openai.AsyncOpenAI`` — no endpoint is
reachable and no network call is made by this module.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from databasise.clients.openai_compat import (
    EmptyEmbeddingInputError,
    ModelIdentityMissingError,
    OpenAICompatibleClient,
)


class _StubChatCompletions:
    def __init__(self, response: Any) -> None:
        self._response = response
        self.captured_kwargs: dict[str, Any] | None = None

    async def create(self, **kwargs: Any) -> Any:
        self.captured_kwargs = kwargs
        return self._response


class _StubEmbeddings:
    def __init__(self, response: Any) -> None:
        self._response = response
        self.captured_kwargs: dict[str, Any] | None = None

    async def create(self, **kwargs: Any) -> Any:
        self.captured_kwargs = kwargs
        return self._response


class _StubOpenAIClient:
    """Mimics ``openai.AsyncOpenAI``'s ``chat.completions.create``/``embeddings.create``
    surface — the only two entry points ``OpenAICompatibleClient`` calls."""

    def __init__(self, *, chat_response: Any = None, embedding_response: Any = None) -> None:
        self.chat = SimpleNamespace(completions=_StubChatCompletions(chat_response))
        self.embeddings = _StubEmbeddings(embedding_response)


def _chat_response(*, model: str | None, cached_tokens: int = 0, tokenizer_id: str | None = None) -> Any:
    usage = SimpleNamespace(
        prompt_tokens=10,
        completion_tokens=4,
        prompt_tokens_details=SimpleNamespace(cached_tokens=cached_tokens),
    )
    if tokenizer_id is not None:
        usage.tokenizer_id = tokenizer_id
    return SimpleNamespace(
        model=model,
        usage=usage,
        choices=[SimpleNamespace(message=SimpleNamespace(content="a canned reply"))],
    )


def _embedding_response(*, model: str | None, count: int = 1) -> Any:
    usage = SimpleNamespace(prompt_tokens=6, completion_tokens=0, prompt_tokens_details=None)
    return SimpleNamespace(
        model=model,
        usage=usage,
        data=[SimpleNamespace(index=i, embedding=[0.1, 0.2, 0.3]) for i in range(count)],
    )


async def test_1_a_chat_call_returns_completion_text_populated_tokens_and_resolved_identity():
    stub = _StubOpenAIClient(chat_response=_chat_response(model="qwen/qwen3.7-flash"))
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-model", client=stub)

    result = await client.chat([{"role": "user", "content": "hi"}])

    assert result.text == "a canned reply"
    assert result.resolved_model_identity == "qwen/qwen3.7-flash"
    assert result.tokens.prompt_tokens == 10
    assert result.tokens.completion_tokens == 4
    assert result.tokens.call_count == 1
    # No tokenizer_id on the response -> counted_by falls back to resolved_model_identity.
    assert result.tokens.counted_by == "qwen/qwen3.7-flash"


async def test_2_resolved_model_identity_comes_from_the_response_not_the_requested_id():
    stub = _StubOpenAIClient(chat_response=_chat_response(model="actually-served-model"))
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-model", client=stub)

    result = await client.chat([{"role": "user", "content": "hi"}])

    assert result.resolved_model_identity == "actually-served-model"
    assert result.resolved_model_identity != "requested-model"


async def test_3_a_response_missing_the_model_field_raises_rather_than_falling_back():
    stub = _StubOpenAIClient(chat_response=_chat_response(model=None))
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-model", client=stub)

    with pytest.raises(ModelIdentityMissingError) as exc_info:
        await client.chat([{"role": "user", "content": "hi"}])

    assert exc_info.value.requested_model == "requested-model"


async def test_4_counted_by_prefers_a_provider_reported_tokenizer_identity_when_present():
    stub = _StubOpenAIClient(
        chat_response=_chat_response(model="served-model", tokenizer_id="fixture-tokenizer@1")
    )
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-model", client=stub)

    result = await client.chat([{"role": "user", "content": "hi"}])

    assert result.tokens.counted_by == "fixture-tokenizer@1"


async def test_5_an_embed_call_returns_vectors_populated_tokens_and_resolved_identity():
    stub = _StubOpenAIClient(embedding_response=_embedding_response(model="embed-model"))
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-embed", client=stub)

    result = await client.embed(["one text"])

    assert result.vectors == [[0.1, 0.2, 0.3]]
    assert result.resolved_model_identity == "embed-model"
    assert result.tokens.prompt_tokens == 6
    assert result.tokens.call_count == 1


async def test_6_an_embedding_response_missing_the_model_field_also_raises():
    stub = _StubOpenAIClient(embedding_response=_embedding_response(model=""))
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-embed", client=stub)

    with pytest.raises(ModelIdentityMissingError):
        await client.embed(["one text"])


# --------------------------------------------------------------------------------------------- #
# D-07 provider-routing pin pass-through (03-11-PLAN.md Task 2)
# --------------------------------------------------------------------------------------------- #

_PIN = {"provider": {"order": ["Alibaba"], "allow_fallbacks": False}}


async def test_7_a_client_constructed_with_a_pinned_routing_body_sends_it_on_chat():
    stub = _StubOpenAIClient(chat_response=_chat_response(model="served-model"))
    client = OpenAICompatibleClient(
        base_url="http://ignored", model="requested-model", client=stub, provider_routing_body=_PIN
    )

    await client.chat([{"role": "user", "content": "hi"}])

    assert stub.chat.completions.captured_kwargs["extra_body"] == _PIN


async def test_8_a_client_constructed_with_no_pin_sends_no_extra_body_key_at_all():
    stub = _StubOpenAIClient(chat_response=_chat_response(model="served-model"))
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-model", client=stub)

    await client.chat([{"role": "user", "content": "hi"}])

    assert "extra_body" not in stub.chat.completions.captured_kwargs


async def test_9_a_per_call_extra_body_kwarg_overrides_the_constructed_pin():
    stub = _StubOpenAIClient(chat_response=_chat_response(model="served-model"))
    client = OpenAICompatibleClient(
        base_url="http://ignored", model="requested-model", client=stub, provider_routing_body=_PIN
    )
    override = {"provider": {"order": ["OpenAI"]}}

    await client.chat([{"role": "user", "content": "hi"}], extra_body=override)

    assert stub.chat.completions.captured_kwargs["extra_body"] == override


async def test_10_the_pin_is_not_applied_to_embed_matching_v1_driver_scripts_own_behavior():
    """v1_driver_script.py's/run_parity_ingest.py's embedding call (``openai_embed.func``) never
    passes ``extra_body`` — only the chat call does. This asserts the two arms cannot diverge
    silently on that point.
    """
    stub = _StubOpenAIClient(embedding_response=_embedding_response(model="embed-model"))
    client = OpenAICompatibleClient(
        base_url="http://ignored",
        model="requested-embed",
        client=stub,
        provider_routing_body=_PIN,
    )

    await client.embed(["one text"])

    assert "extra_body" not in stub.embeddings.captured_kwargs


# --------------------------------------------------------------------------------------------- #
# 06-14-PLAN.md Task 2: EmptyEmbeddingInputError — one named refusal at the single method every
# embedding call site routes through, before any provider request is constructed.
# --------------------------------------------------------------------------------------------- #


async def test_11_embed_handed_a_zero_length_string_raises_before_reaching_the_provider():
    stub = _StubOpenAIClient(embedding_response=_embedding_response(model="embed-model"))
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-embed", client=stub)

    with pytest.raises(EmptyEmbeddingInputError):
        await client.embed(["ok", ""])

    assert stub.embeddings.captured_kwargs is None


async def test_12_embed_handed_a_whitespace_only_string_raises_the_same_error():
    stub = _StubOpenAIClient(embedding_response=_embedding_response(model="embed-model"))
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-embed", client=stub)

    for whitespace_only in (" ", "\t", "\n", "   \t\n  "):
        with pytest.raises(EmptyEmbeddingInputError):
            await client.embed(["ok", whitespace_only])

    assert stub.embeddings.captured_kwargs is None


async def test_13_embed_handed_an_empty_list_raises_the_same_error():
    stub = _StubOpenAIClient(embedding_response=_embedding_response(model="embed-model"))
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-embed", client=stub)

    with pytest.raises(EmptyEmbeddingInputError):
        await client.embed([])

    assert stub.embeddings.captured_kwargs is None


async def test_14_the_raised_error_names_the_offending_batch_index_as_a_reachable_attribute():
    stub = _StubOpenAIClient(embedding_response=_embedding_response(model="embed-model"))
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-embed", client=stub)

    with pytest.raises(EmptyEmbeddingInputError) as exc_info:
        await client.embed(["first ok", "second ok", "   "])

    assert exc_info.value.index == 2
    assert exc_info.value.batch_size == 3


async def test_15_embed_handed_ordinary_non_empty_strings_still_reaches_the_provider_unchanged():
    stub = _StubOpenAIClient(embedding_response=_embedding_response(model="embed-model", count=2))
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-embed", client=stub)

    result = await client.embed(["one text", "another text"])

    assert result.vectors == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]
    assert result.resolved_model_identity == "embed-model"
    assert stub.embeddings.captured_kwargs is not None
    assert stub.embeddings.captured_kwargs["input"] == ["one text", "another text"]


# --------------------------------------------------------------------------------------------- #
# 08-02-PLAN.md Task 1 (RUN-02, D-05): a response with no usage is one unbudgetable call, never a
# real spend recorded as zero. Present usage (even all zero) keeps counting by the resolved model.
# --------------------------------------------------------------------------------------------- #


def _no_usage(response: Any) -> Any:
    response.usage = None
    return response


async def test_16_a_chat_response_with_no_usage_counts_one_unbudgetable_call():
    from databasise.seam.tokens import UNBUDGETABLE_SENTINEL

    stub = _StubOpenAIClient(chat_response=_no_usage(_chat_response(model="served-model")))
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-model", client=stub)

    result = await client.chat([{"role": "user", "content": "hi"}])

    assert result.tokens.call_count == 1
    assert result.tokens.counted_by == "unbudgetable" == UNBUDGETABLE_SENTINEL
    assert (result.tokens.prompt_tokens, result.tokens.completion_tokens) == (0, 0)
    assert result.tokens.cached_read_tokens == 0


async def test_17_an_embed_response_with_no_usage_counts_one_unbudgetable_call():
    stub = _StubOpenAIClient(embedding_response=_no_usage(_embedding_response(model="embed-model")))
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-embed", client=stub)

    result = await client.embed(["one text"])

    assert result.tokens.call_count == 1
    assert result.tokens.counted_by == "unbudgetable"
    assert (result.tokens.prompt_tokens, result.tokens.completion_tokens) == (0, 0)
    assert result.tokens.cached_read_tokens == 0


async def test_18_a_present_all_zero_usage_still_counts_by_the_resolved_model():
    response = _chat_response(model="served-model")
    response.usage = SimpleNamespace(prompt_tokens=0, completion_tokens=0, prompt_tokens_details=None)
    stub = _StubOpenAIClient(chat_response=response)
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-model", client=stub)

    result = await client.chat([{"role": "user", "content": "hi"}])

    assert result.tokens.call_count == 1
    assert result.tokens.counted_by == "served-model"


async def test_19_a_usage_with_none_prompt_tokens_reports_zero_and_one_call():
    response = _chat_response(model="served-model")
    response.usage = SimpleNamespace(prompt_tokens=None, completion_tokens=3, prompt_tokens_details=None)
    stub = _StubOpenAIClient(chat_response=response)
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-model", client=stub)

    result = await client.chat([{"role": "user", "content": "hi"}])

    assert result.tokens.prompt_tokens == 0
    assert result.tokens.completion_tokens == 3
    assert result.tokens.call_count == 1


# --------------------------------------------------------------------------------------------- #
# 08-02-PLAN.md Task 2 (RUN-03, D-06): malformed responses raise named errors or are returned in
# input order, never passed on silently. The error classes are reached as ``openai_compat.<Name>``
# in the bodies so this file still collects on a tree that predates them.
# --------------------------------------------------------------------------------------------- #


def _chat_with_choices(choices: list[Any]) -> Any:
    response = _chat_response(model="served-model")
    response.choices = choices
    return response


async def test_20_empty_choices_raise_empty_choices_error():
    from databasise.clients import openai_compat

    stub = _StubOpenAIClient(chat_response=_chat_with_choices([]))
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-model", client=stub)

    with pytest.raises(openai_compat.EmptyChoicesError) as exc_info:
        await client.chat([{"role": "user", "content": "hi"}])

    assert exc_info.value.resolved_model_identity == "served-model"


async def test_21_none_content_raises_missing_completion_content_error():
    from databasise.clients import openai_compat

    choice = SimpleNamespace(message=SimpleNamespace(content=None), finish_reason="tool_calls")
    stub = _StubOpenAIClient(chat_response=_chat_with_choices([choice]))
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-model", client=stub)

    with pytest.raises(openai_compat.MissingCompletionContentError) as exc_info:
        await client.chat([{"role": "user", "content": "hi"}])

    assert exc_info.value.finish_reason == "tool_calls"
    assert exc_info.value.resolved_model_identity == "served-model"
    assert "tool_calls" in str(exc_info.value)


async def test_22_empty_string_content_is_returned_unchanged():
    choice = SimpleNamespace(message=SimpleNamespace(content=""), finish_reason="stop")
    stub = _StubOpenAIClient(chat_response=_chat_with_choices([choice]))
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-model", client=stub)

    result = await client.chat([{"role": "user", "content": "hi"}])

    assert result.text == ""


async def test_23_two_vectors_for_three_inputs_raise_embedding_batch_mismatch_error():
    from databasise.clients import openai_compat

    stub = _StubOpenAIClient(embedding_response=_embedding_response(model="embed-model", count=2))
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-embed", client=stub)

    with pytest.raises(openai_compat.EmbeddingBatchMismatchError) as exc_info:
        await client.embed(["a", "b", "c"])

    assert (exc_info.value.expected, exc_info.value.received) == (3, 2)


async def test_24_out_of_order_items_return_vectors_in_input_order():
    response = _embedding_response(model="embed-model", count=2)
    response.data = [
        SimpleNamespace(index=1, embedding=[2.0]),
        SimpleNamespace(index=0, embedding=[1.0]),
    ]
    stub = _StubOpenAIClient(embedding_response=response)
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-embed", client=stub)

    result = await client.embed(["first", "second"])

    assert result.vectors == [[1.0], [2.0]]


@pytest.mark.parametrize(
    "indices",
    [[0, 0], [0, None]],
    ids=["duplicate-index", "missing-index"],
)
async def test_25_duplicate_or_missing_indices_raise_embedding_batch_mismatch_error(indices):
    from databasise.clients import openai_compat

    items = []
    for position, index in enumerate(indices):
        item = SimpleNamespace(embedding=[float(position)])
        if index is not None:
            item.index = index
        items.append(item)
    response = _embedding_response(model="embed-model", count=2)
    response.data = items
    stub = _StubOpenAIClient(embedding_response=response)
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-embed", client=stub)

    with pytest.raises(openai_compat.EmbeddingBatchMismatchError) as exc_info:
        await client.embed(["first", "second"])

    assert exc_info.value.indices == indices
