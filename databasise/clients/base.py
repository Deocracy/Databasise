"""The calling convention every LLM/embedding/rerank client this codebase wires implements
(D-06/D-07): three ``typing.Protocol`` definitions plus the frozen result each returns.

No in-repo analog exists for this protocol set (03-PATTERNS.md "No Analog Found") — authored
fresh, following ``databasise/stores/base.py``'s ``StorageNameSpace`` docstring convention of
stating the calling contract a body relies on, rather than describing the type mechanically.

Every result dataclass below carries a ``tokens: TokenAccounting`` field (populated from the
provider's own usage accounting, per D-10's ``runner/trace.py`` field set — never assumed) and a
``resolved_model_identity: str`` field derived from what the response payload itself reports the
serving model to be, never from the model id the caller requested (Phase 1 D-12 / Phase 2 D-08:
"hash what is installed, never what is declared"). A client that cannot derive
``resolved_model_identity`` from its response MUST raise rather than substitute the requested id —
see ``databasise/clients/openai_compat.py``'s ``ModelIdentityMissingError``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from databasise.runner.trace import TokenAccounting


@dataclass(frozen=True)
class ChatResult:
    """What a :class:`LLMClient` call returns: the completion text plus the two fields every
    client result carries (see module docstring)."""

    text: str
    tokens: TokenAccounting
    resolved_model_identity: str


@dataclass(frozen=True)
class EmbeddingResult:
    """What an :class:`EmbeddingClient` call returns: one vector per input text, in the same
    order as the input, plus the two fields every client result carries."""

    vectors: list[list[float]]
    tokens: TokenAccounting
    resolved_model_identity: str


@dataclass(frozen=True)
class RerankResult:
    """What a :class:`RerankClient` call returns: the input document indices reordered by
    descending relevance (``ranked_indices[0]`` is the most relevant document's original index),
    plus the two fields every client result carries."""

    ranked_indices: list[int]
    tokens: TokenAccounting
    resolved_model_identity: str


class LLMClient(Protocol):
    """A part body reaches this only via ``ctx.clients["llm"]`` after
    ``CapabilityScopedClients.require("calls_llm")`` — never constructed or imported directly by
    a part body (D-06)."""

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> ChatResult: ...


class EmbeddingClient(Protocol):
    """A part body reaches this only via ``ctx.clients["embedding"]`` after
    ``CapabilityScopedClients.require("calls_embedding")``."""

    async def embed(self, texts: list[str], **kwargs: Any) -> EmbeddingResult: ...


class RerankClient(Protocol):
    """A part body reaches this only via ``ctx.clients["rerank"]`` after
    ``CapabilityScopedClients.require("calls_rerank")``."""

    async def rerank(self, query: str, documents: list[str], **kwargs: Any) -> RerankResult: ...


__all__ = [
    "ChatResult",
    "EmbeddingResult",
    "RerankResult",
    "LLMClient",
    "EmbeddingClient",
    "RerankClient",
]
