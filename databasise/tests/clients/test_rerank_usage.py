"""Sweep fix (phase 08): a negative ``usage.total_tokens`` from a rerank server is not a spend.

Mirrors the fixtures of ``tests/clients/test_rerank_client.py``. A negative total would flow
into ``meter()`` as a negative spend and a ``realised_budget_share`` below 0, which the frozen
trace schema (``evidence/rig-trace.databasise.schema.json``, minimum 0) forbids. D-05: an
unknowable spend is unbudgetable, not zero and not negative.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

URL = "https://rerank.example.test/v2/rerank"
DOCS = ["alpha", "beta", "gamma"]


def _client(handler):
    from databasise.clients.rerank import HttpRerankClient

    return HttpRerankClient(
        url=URL,
        model="rerank-test",
        binding="cohere",
        api_key="sk-rerank-test-key",
        transport=httpx.MockTransport(handler),
    )


def _respond(payload: Any):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return handler


def _results(*pairs: tuple[int, float]) -> list[dict[str, Any]]:
    return [{"index": i, "relevance_score": s} for i, s in pairs]


@pytest.mark.parametrize("total", [-1, -7, -(10**9)])
async def test_a_negative_usage_total_is_unbudgetable_not_a_negative_spend(total):
    handler = _respond(
        {"model": "m1", "results": _results((0, 1.0), (1, 0.5), (2, 0.1)), "usage": {"total_tokens": total}}
    )

    result = await _client(handler).rerank("q", DOCS)

    assert result.tokens.prompt_tokens == 0
    assert result.tokens.call_count == 1
    assert result.tokens.counted_by == "unbudgetable"


async def test_a_zero_usage_total_is_still_a_counted_spend():
    handler = _respond(
        {"model": "m1", "results": _results((0, 1.0), (1, 0.5), (2, 0.1)), "usage": {"total_tokens": 0}}
    )

    result = await _client(handler).rerank("q", DOCS)

    assert result.tokens.prompt_tokens == 0
    assert result.tokens.counted_by == "m1"
