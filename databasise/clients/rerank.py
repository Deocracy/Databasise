"""The one HTTP rerank client (08-05-PLAN.md, RUN-05, D-07): it mirrors the three request shapes
LightRAG v1 speaks (``v1/lightrag/rerank.py`` ``generic_rerank_api``; ``v1/env.example`` lines
128-165), so a rerank server that works for v1 works here.

``binding`` selects the shape, named as in v1's ``RERANK_BINDING``:

- ``cohere`` and ``jina`` (also vLLM, which v1 says uses the cohere binding): POST
  ``{model, query, documents[, top_n]}``; read ``results[{index, relevance_score}]``.
- ``aliyun``: POST ``{model, input: {query, documents}, parameters: {[top_n]}}``; read
  ``output.results[{index, relevance_score}]``.

``url`` is the full endpoint exactly as configured (v1's ``RERANK_BINDING_HOST`` convention): no
path is ever appended. Not built (COVERAGE.md OPT-OUT): v1's optional document chunking
(``RERANK_ENABLE_CHUNKING``), ``return_documents``, and TEI's native bare-list response.

Identity exception (owner decision, 2026-10-16, rerank-scoped): ``resolved_model_identity`` is the
response's ``model`` field when present, and otherwise the configured ``model``. This departs from
the "hash what is installed, never what is declared" rule in ``clients/base.py``, which the LLM and
embedding clients still follow unchanged. The owner approved it so Cohere and Aliyun, whose
responses carry no ``model``, can be used; the owner's words were: "Use a reranker the same way
lightrag uses it or any other."

Privacy: no message, log line or attribute here carries the request headers or the API key.
"""

from __future__ import annotations

import math
from typing import Any

from databasise.clients.base import RerankResult
from databasise.runner.trace import TokenAccounting

try:
    import httpx
except ImportError as _httpx_import_err:
    raise ImportError(
        "httpx is required for HttpRerankClient. Install with: pip install 'httpx>=0.27'"
    ) from _httpx_import_err

RERANK_BINDINGS = ("cohere", "jina", "aliyun")


class RerankResponseError(RuntimeError):
    """The rerank call failed or its response cannot be trusted: a non-200 status, a transport
    failure, a non-JSON body, or results that do not match the documents sent. ``reason`` states
    which; ``status_code`` is set for an HTTP status. The message holds no URL, header or key."""

    def __init__(self, reason: str, status_code: int | None = None):
        self.reason = reason
        self.status_code = status_code
        super().__init__(f"rerank response refused: {reason}")


class EmptyRerankInputError(ValueError):
    """Raised by :meth:`HttpRerankClient.rerank` for an empty documents list, before any request.
    A provider answers an empty list with an opaque 400 (as it does for empty embedding input)."""

    def __init__(self) -> None:
        super().__init__("rerank() was handed an empty documents list; refusing before any request")


class UnsupportedRerankBindingError(ValueError):
    """Raised for a rerank binding outside ``RERANK_BINDINGS``. ``key`` names where the value came
    from (``RERANK_BINDING`` for the env key); the value itself is withheld."""

    def __init__(self, key: str = "binding"):
        self.key = key
        super().__init__(
            f"{key} names an unsupported rerank binding; supported: {', '.join(RERANK_BINDINGS)}; "
            "value withheld"
        )


def _is_number(value: Any) -> bool:
    # math.isfinite: json accepts NaN/Infinity literals, and a NaN score has no defined sort position.
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


class HttpRerankClient:
    """A :class:`~databasise.clients.base.RerankClient` over HTTP. ``transport`` is the test seam
    (``httpx.MockTransport``); left ``None`` a real network transport is used."""

    def __init__(
        self,
        *,
        url: str,
        model: str,
        binding: str = "cohere",
        api_key: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 30.0,  # v1's RERANK_TIMEOUT default
    ) -> None:
        if binding not in RERANK_BINDINGS:
            raise UnsupportedRerankBindingError()
        self._url = url
        self._model = model
        self._binding = binding
        self._api_key = api_key
        self._transport = transport
        self._timeout = timeout

    async def rerank(
        self, query: str, documents: list[str], *, top_n: int | None = None, **kwargs: Any
    ) -> RerankResult:
        for name in kwargs:
            raise TypeError(f"HttpRerankClient.rerank() does not support {name!r}")
        if not documents:
            raise EmptyRerankInputError()

        headers = {"Content-Type": "application/json"}
        if self._api_key is not None:
            headers["Authorization"] = f"Bearer {self._api_key}"

        if self._binding == "aliyun":
            parameters = {} if top_n is None else {"top_n": top_n}
            payload: dict[str, Any] = {
                "model": self._model,
                "input": {"query": query, "documents": documents},
                "parameters": parameters,
            }
        else:
            payload = {"model": self._model, "query": query, "documents": documents}
            if top_n is not None:
                payload["top_n"] = top_n

        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=self._timeout) as http:
                response = await http.post(self._url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            # The exception text can carry the URL; only its class name is kept.
            raise RerankResponseError(f"transport failure ({type(exc).__name__})") from exc
        if response.status_code != 200:
            raise RerankResponseError(
                f"HTTP status {response.status_code}", status_code=response.status_code
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise RerankResponseError("body is not JSON") from exc
        if not isinstance(body, dict):
            raise RerankResponseError("body is not a JSON object")

        container = body.get("output") if self._binding == "aliyun" else body
        results = container.get("results") if isinstance(container, dict) else None
        if not isinstance(results, list):
            raise RerankResponseError("results is missing or not a list")
        ranked = self._validated_ranking(results, len(documents), top_n)

        model = body.get("model")
        identity = model if isinstance(model, str) and model else self._model
        return RerankResult(
            ranked_indices=ranked,
            tokens=self._token_accounting(body.get("usage"), identity),
            resolved_model_identity=identity,
        )

    @staticmethod
    def _validated_ranking(results: list[Any], n_documents: int, top_n: int | None) -> list[int]:
        pairs: list[tuple[int, float]] = []
        for entry in results:
            index = entry.get("index") if isinstance(entry, dict) else None
            score = entry.get("relevance_score") if isinstance(entry, dict) else None
            if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < n_documents:
                raise RerankResponseError("a result index is missing or out of range")
            if not _is_number(score):
                raise RerankResponseError("a result relevance_score is missing or not a number")
            pairs.append((index, score))
        indices = [index for index, _ in pairs]
        if len(set(indices)) != len(indices):
            raise RerankResponseError("a result index is duplicated")
        expected = n_documents if top_n is None else min(top_n, n_documents)
        if len(pairs) != expected:
            raise RerankResponseError(f"expected {expected} results, received {len(pairs)}")
        return [index for index, _ in sorted(pairs, key=lambda pair: (-pair[1], pair[0]))]

    @staticmethod
    def _token_accounting(usage: Any, identity: str) -> TokenAccounting:
        total = usage.get("total_tokens") if isinstance(usage, dict) else None
        if not isinstance(total, int) or isinstance(total, bool):
            # D-05: no reported usage means the spend is unknowable, not zero.
            return TokenAccounting(call_count=1, counted_by="unbudgetable")  # seam.tokens.UNBUDGETABLE_SENTINEL
        return TokenAccounting(prompt_tokens=total, call_count=1, counted_by=identity)


__all__ = [
    "RERANK_BINDINGS",
    "EmptyRerankInputError",
    "HttpRerankClient",
    "RerankResponseError",
    "UnsupportedRerankBindingError",
]
