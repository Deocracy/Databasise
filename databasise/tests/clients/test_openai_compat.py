"""Behavior tests for ``OpenAICompatibleClient``. Every test reaches the SDK surface through a
stub double (``_StubOpenAIClient`` below), never a real ``openai.AsyncOpenAI`` — no endpoint is
reachable and no network call is made by this module.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from databasise.clients.openai_compat import ModelIdentityMissingError, OpenAICompatibleClient


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


def _embedding_response(*, model: str | None) -> Any:
    usage = SimpleNamespace(prompt_tokens=6, completion_tokens=0, prompt_tokens_details=None)
    return SimpleNamespace(
        model=model,
        usage=usage,
        data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3])],
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
