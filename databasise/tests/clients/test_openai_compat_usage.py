"""Phase 08 audit leftover (sibling of the rerank fix in ``clients/rerank.py``): a negative token
count on an OpenAI-compatible usage object is no count at all. It must behave exactly like a
missing usage -- one ``unbudgetable`` call, zero counts -- never a negative spend, because the
frozen trace schema (``evidence/rig-trace.databasise.schema.json``) requires ``prompt_tokens`` and
``realised_budget_share`` to be ``>= 0``. Same stub double as ``test_openai_compat.py``; no
network call is made.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from databasise.clients.openai_compat import OpenAICompatibleClient
from databasise.seam.tokens import UNBUDGETABLE_SENTINEL


class _StubCreate:
    def __init__(self, response: Any) -> None:
        self._response = response

    async def create(self, **kwargs: Any) -> Any:
        return self._response


class _StubOpenAIClient:
    def __init__(self, *, chat_response: Any = None, embedding_response: Any = None) -> None:
        self.chat = SimpleNamespace(completions=_StubCreate(chat_response))
        self.embeddings = _StubCreate(embedding_response)


def _usage(prompt: int = 10, completion: int = 4, cached: int | None = 0) -> SimpleNamespace:
    details = None if cached is None else SimpleNamespace(cached_tokens=cached)
    return SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion, prompt_tokens_details=details)


def _chat_response(usage: SimpleNamespace) -> Any:
    return SimpleNamespace(
        model="served-model",
        usage=usage,
        choices=[SimpleNamespace(message=SimpleNamespace(content="a canned reply"))],
    )


def _embedding_response(usage: SimpleNamespace) -> Any:
    return SimpleNamespace(
        model="embed-model", usage=usage, data=[SimpleNamespace(index=0, embedding=[0.1, 0.2, 0.3])]
    )


def _is_unbudgetable(tokens: Any) -> None:
    assert tokens.counted_by == UNBUDGETABLE_SENTINEL == "unbudgetable"
    assert tokens.call_count == 1
    assert (tokens.prompt_tokens, tokens.completion_tokens, tokens.cached_read_tokens) == (0, 0, 0)


@pytest.mark.parametrize(
    "usage",
    [_usage(prompt=-1), _usage(completion=-3), _usage(cached=-7)],
    ids=["negative-prompt", "negative-completion", "negative-cached"],
)
async def test_a_negative_chat_usage_count_is_one_unbudgetable_call(usage):
    stub = _StubOpenAIClient(chat_response=_chat_response(usage))
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-model", client=stub)

    result = await client.chat([{"role": "user", "content": "hi"}])

    _is_unbudgetable(result.tokens)


async def test_a_negative_embed_usage_count_is_one_unbudgetable_call():
    stub = _StubOpenAIClient(embedding_response=_embedding_response(_usage(prompt=-6, completion=0, cached=None)))
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-embed", client=stub)

    result = await client.embed(["one text"])

    _is_unbudgetable(result.tokens)


async def test_a_non_negative_usage_still_counts_by_the_resolved_model():
    stub = _StubOpenAIClient(chat_response=_chat_response(_usage(prompt=10, completion=4, cached=2)))
    client = OpenAICompatibleClient(base_url="http://ignored", model="requested-model", client=stub)

    result = await client.chat([{"role": "user", "content": "hi"}])

    assert result.tokens.counted_by == "served-model"
    assert (result.tokens.prompt_tokens, result.tokens.completion_tokens, result.tokens.cached_read_tokens) == (10, 4, 2)
