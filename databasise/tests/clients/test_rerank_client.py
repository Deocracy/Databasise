"""08-05-PLAN.md Task 2: ``HttpRerankClient`` over the LightRAG v1 rerank bindings (cohere, jina,
aliyun; vLLM speaks the cohere shape) — offline, through ``httpx.MockTransport``.

The module under test is imported inside each test (never at module top) so the file collects on
the pre-phase tree and the cases fail inside their bodies (plan 08-10's fail-first run).
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
import pytest

URL = "https://rerank.example.test/v2/rerank"
KEY = "sk-rerank-test-key"
DOCS = ["alpha", "beta", "gamma"]


def _client(handler, *, binding: str = "cohere", api_key: str | None = KEY, **kwargs: Any):
    from databasise.clients.rerank import HttpRerankClient

    return HttpRerankClient(
        url=URL,
        model="rerank-test",
        binding=binding,
        api_key=api_key,
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


def _respond(payload: Any, *, status: int = 200):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if isinstance(payload, (bytes, str)):
            return httpx.Response(status, content=payload)
        return httpx.Response(status, json=payload)

    handler.seen = seen  # type: ignore[attr-defined]
    return handler


def _results(*pairs: tuple[int, float]) -> list[dict[str, Any]]:
    return [{"index": i, "relevance_score": s} for i, s in pairs]


# --------------------------------------------------------------------------------------------- #
# Request shapes
# --------------------------------------------------------------------------------------------- #


@pytest.mark.parametrize("binding", ["cohere", "jina"])
async def test_standard_binding_posts_model_query_documents_to_the_exact_url(binding):
    handler = _respond({"results": _results((0, 0.9), (1, 0.5), (2, 0.1))})

    await _client(handler, binding=binding).rerank("q", DOCS)

    (request,) = handler.seen
    assert str(request.url) == URL
    assert request.method == "POST"
    assert request.headers["authorization"] == f"Bearer {KEY}"
    assert request.headers["content-type"] == "application/json"
    assert json.loads(request.content) == {"model": "rerank-test", "query": "q", "documents": DOCS}


async def test_top_n_is_in_the_standard_body_only_when_passed():
    handler = _respond({"results": _results((2, 0.9), (0, 0.5))})

    await _client(handler).rerank("q", DOCS, top_n=2)

    assert json.loads(handler.seen[0].content)["top_n"] == 2


async def test_aliyun_binding_nests_input_and_parameters():
    handler = _respond({"output": {"results": _results((1, 0.8), (0, 0.2), (2, 0.1))}})

    await _client(handler, binding="aliyun").rerank("q", DOCS)

    assert json.loads(handler.seen[0].content) == {
        "model": "rerank-test",
        "input": {"query": "q", "documents": DOCS},
        "parameters": {},
    }


async def test_aliyun_top_n_goes_in_parameters():
    handler = _respond({"output": {"results": _results((1, 0.8), (0, 0.2))}})

    result = await _client(handler, binding="aliyun").rerank("q", DOCS, top_n=2)

    assert json.loads(handler.seen[0].content)["parameters"] == {"top_n": 2}
    assert result.ranked_indices == [1, 0]


async def test_no_api_key_sends_no_authorization_header():
    handler = _respond({"results": _results((0, 1.0), (1, 0.5), (2, 0.1))})

    await _client(handler, api_key=None).rerank("q", DOCS)

    assert "authorization" not in handler.seen[0].headers


# --------------------------------------------------------------------------------------------- #
# Ranking
# --------------------------------------------------------------------------------------------- #


async def test_out_of_order_results_rank_by_descending_score():
    handler = _respond({"results": _results((0, 0.1), (2, 0.9), (1, 0.5))})

    result = await _client(handler).rerank("q", DOCS)

    assert result.ranked_indices == [2, 1, 0]


async def test_tied_scores_break_by_ascending_original_index():
    handler = _respond({"results": _results((2, 0.5), (0, 0.5), (1, 0.9))})

    result = await _client(handler).rerank("q", DOCS)

    assert result.ranked_indices == [1, 0, 2]


async def test_top_n_accepts_exactly_that_many_results():
    handler = _respond({"results": _results((2, 0.9), (0, 0.4))})

    result = await _client(handler).rerank("q", DOCS, top_n=2)

    assert result.ranked_indices == [2, 0]


# --------------------------------------------------------------------------------------------- #
# Identity (owner-approved rerank-scoped exception) and token accounting
# --------------------------------------------------------------------------------------------- #


async def test_response_model_is_the_resolved_identity():
    handler = _respond({"model": "served-reranker-v2", "results": _results((0, 1.0), (1, 0.5), (2, 0.1))})

    result = await _client(handler).rerank("q", DOCS)

    assert result.resolved_model_identity == "served-reranker-v2"


@pytest.mark.parametrize("model", [{"name": "x"}, 7, ["m"], ""])
async def test_a_non_string_response_model_falls_back_to_the_configured_model(model):
    handler = _respond({"model": model, "results": _results((0, 1.0), (1, 0.5), (2, 0.1))})

    result = await _client(handler).rerank("q", DOCS)

    assert result.resolved_model_identity == "rerank-test"


@pytest.mark.parametrize("binding,payload_key", [("cohere", None), ("aliyun", "output")])
async def test_missing_response_model_falls_back_to_the_configured_model(binding, payload_key):
    results = _results((0, 1.0), (1, 0.5), (2, 0.1))
    payload = {"results": results} if payload_key is None else {"output": {"results": results}}

    result = await _client(_respond(payload), binding=binding).rerank("q", DOCS)

    assert result.resolved_model_identity == "rerank-test"


async def test_usage_total_tokens_is_the_prompt_token_count():
    handler = _respond(
        {"model": "m1", "results": _results((0, 1.0), (1, 0.5), (2, 0.1)), "usage": {"total_tokens": 42}}
    )

    result = await _client(handler).rerank("q", DOCS)

    assert result.tokens.prompt_tokens == 42
    assert result.tokens.call_count == 1
    assert result.tokens.counted_by == "m1"


async def test_aliyun_usage_is_read_too():
    handler = _respond(
        {"output": {"results": _results((0, 1.0), (1, 0.5), (2, 0.1))}, "usage": {"total_tokens": 7}}
    )

    result = await _client(handler, binding="aliyun").rerank("q", DOCS)

    assert result.tokens.prompt_tokens == 7


async def test_no_usage_is_unbudgetable_not_zero():
    handler = _respond({"results": _results((0, 1.0), (1, 0.5), (2, 0.1))})

    result = await _client(handler).rerank("q", DOCS)

    assert result.tokens.call_count == 1
    assert result.tokens.counted_by == "unbudgetable"
    assert result.tokens.prompt_tokens == 0


# --------------------------------------------------------------------------------------------- #
# Refusals
# --------------------------------------------------------------------------------------------- #


async def test_http_500_raises_rerank_response_error_with_the_status():
    from databasise.clients.rerank import RerankResponseError

    with pytest.raises(RerankResponseError) as exc_info:
        await _client(_respond({"error": "boom"}, status=500)).rerank("q", DOCS)

    assert exc_info.value.status_code == 500
    assert KEY not in str(exc_info.value)


@pytest.mark.parametrize(
    "payload",
    [
        b"<html>not json</html>",
        {"no_results": []},
        {"results": "nope"},
        {"results": [{"index": 0}]},
        {"results": [{"index": 0, "relevance_score": "high"}] * 1},
        {"results": _results((3, 0.9), (0, 0.5), (1, 0.1))},
        {"results": _results((-1, 0.9), (0, 0.5), (1, 0.1))},
        {"results": _results((0, 0.9), (0, 0.5), (1, 0.1))},
        {"results": _results((0, 0.9), (1, 0.5))},
        {"output": {"no": "results"}},
        b'{"results": [{"index": 0, "relevance_score": NaN}, {"index": 1, "relevance_score": 0.5}, {"index": 2, "relevance_score": 0.1}]}',
        b'{"results": [{"index": 0, "relevance_score": Infinity}, {"index": 1, "relevance_score": 0.5}, {"index": 2, "relevance_score": 0.1}]}',
    ],
)
async def test_malformed_or_incomplete_responses_are_refused_by_name(payload):
    from databasise.clients.rerank import RerankResponseError

    with pytest.raises(RerankResponseError):
        await _client(_respond(payload)).rerank("q", DOCS)


async def test_aliyun_response_without_output_results_is_refused():
    from databasise.clients.rerank import RerankResponseError

    with pytest.raises(RerankResponseError):
        await _client(_respond({"results": _results((0, 1.0))}), binding="aliyun").rerank("q", ["a"])


async def test_empty_documents_are_refused_before_any_request():
    from databasise.clients.rerank import EmptyRerankInputError

    handler = _respond({"results": []})

    with pytest.raises(EmptyRerankInputError):
        await _client(handler).rerank("q", [])

    assert handler.seen == []


async def test_unsupported_keyword_is_a_type_error_naming_it():
    handler = _respond({"results": []})

    with pytest.raises(TypeError, match="return_documents"):
        await _client(handler).rerank("q", DOCS, return_documents=True)

    assert handler.seen == []


def test_unsupported_binding_is_refused_without_echoing_the_value():
    from databasise.clients.rerank import (
        HttpRerankClient,
        UnsupportedRerankBindingError,
    )

    with pytest.raises(UnsupportedRerankBindingError) as exc_info:
        HttpRerankClient(url=URL, model="m", binding="secret-binding-marker")

    assert "secret-binding-marker" not in str(exc_info.value)


# --------------------------------------------------------------------------------------------- #
# The shipped part body drives the client
# --------------------------------------------------------------------------------------------- #


async def test_the_lightrag_rerank_part_body_reorders_items_by_the_client_ranking():
    from databasise.parts.schema import NodeContext
    from databasise.parts_core.lightrag.rerank import _rerank_body

    handler = _respond(
        {"model": "m1", "results": _results((0, 0.1), (2, 0.9), (1, 0.5)), "usage": {"total_tokens": 9}}
    )
    items = [{"content": "alpha"}, {"content": "beta"}, {"content": "gamma"}]
    ctx = NodeContext(
        node_id="rerank",
        config={"live_rerank": True, "query": "q"},
        inputs={"heading-backfill": {"items": items}},
        stores={},
        clients={"rerank": _client(handler)},
    )

    out = await _rerank_body(ctx)

    assert [i["content"] for i in out["items"]] == ["gamma", "beta", "alpha"]
    assert out["tokens"].prompt_tokens == 9
    assert json.loads(handler.seen[0].content)["documents"] == ["alpha", "beta", "gamma"]


# --------------------------------------------------------------------------------------------- #
# Live (owner-run only; never executed by the executor)
# --------------------------------------------------------------------------------------------- #


@pytest.mark.live
async def test_live_rerank_round_trip():
    from pathlib import Path

    from databasise.clients.builder import (
        RERANK_BINDING_ENV_KEY,
        RERANK_ENV_KEYS,
        load_env_file,
    )
    from databasise.clients.rerank import HttpRerankClient

    env_path = os.environ.get("DATABASISE_RERANK_ENV_FILE")
    if not env_path:
        pytest.skip("DATABASISE_RERANK_ENV_FILE is not set; point it at an env file holding the RERANK_* keys")
    env = load_env_file(Path(env_path))
    absent = [key for key in (RERANK_BINDING_ENV_KEY, *RERANK_ENV_KEYS) if not env.get(key) or env.get(key) == "null"]
    if absent:
        pytest.skip(f"the env file lacks: {', '.join(absent)}")

    client = HttpRerankClient(
        url=env["RERANK_BINDING_HOST"],
        model=env["RERANK_MODEL"],
        binding=env[RERANK_BINDING_ENV_KEY],
        api_key=env["RERANK_BINDING_API_KEY"],
    )
    result = await client.rerank("which is a fruit", ["a stone", "an apple", "a river"])

    assert sorted(result.ranked_indices) == [0, 1, 2]
    assert result.resolved_model_identity
