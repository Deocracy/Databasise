"""The one OpenAI-compatible LLM/embedding client implementation D-07 fixes: a caller-supplied
``base_url``/``model``/``api_key`` reaches OpenRouter, a local Ollama endpoint, or plain OpenAI
through the identical construction and code path — never a second implementation per provider.

No in-repo analog exists for an HTTP LLM/embedding client body (03-PATTERNS.md "No Analog
Found"); the only reused fragment is ``databasise/stores/vector.py``'s guarded-import idiom
(``try: import X / except ImportError: raise with the install command``), applied here to
``openai`` rather than degrading to a silent no-op SDK substitute.

``resolved_model_identity`` is read from the response payload's own ``model`` field — the model
the provider actually served, confirmed against the installed ``openai`` 3.6.0 SDK's
``ChatCompletion``/``CreateEmbeddingResponse`` schemas this session — never the model id this
client was constructed with (Phase 1 D-12 / Phase 2 D-08's "hash what is installed, never what is
declared"). A response whose ``model`` field is empty or absent raises
:class:`ModelIdentityMissingError` rather than substituting the requested id.

``TokenAccounting.counted_by`` is set to the provider-reported tokenizer identity when the
response's ``usage`` object carries one (a ``tokenizer_id`` attribute — no such field exists on
the real OpenAI SDK's ``CompletionUsage`` today, so this branch only fires against a
provider/proxy that adds one), and to ``resolved_model_identity`` otherwise.

06-14-PLAN.md: ``embed`` refuses an empty batch, or a batch containing a zero-length or
whitespace-only item, by raising :class:`EmptyEmbeddingInputError` before any request reaches the
provider. Seven call sites across this codebase reach this one method — three of them stamp an
unguarded ``str(config.get("query", ""))`` and one hands it a list that is empty whenever OpenIE
extracts nothing — so a guard here, at the single method they all route through, turns every one
of those seven into a diagnosable refusal instead of an opaque provider ``400`` (the exact failure
recorded in ``databasise/evidence/CROSS-MODALITY-EVIDENCE.md``'s "Real run attempted — refused"
section).
"""

from __future__ import annotations

from typing import Any

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.runner.trace import TokenAccounting

try:
    import openai  # type: ignore[import-untyped]
except ImportError as _openai_import_err:
    raise ImportError(
        "openai is required for OpenAICompatibleClient. Install with: "
        "pip install 'openai>=2.0.0,<4.0.0'"
    ) from _openai_import_err


class ModelIdentityMissingError(RuntimeError):
    """Raised when a response carries no ``model`` field to derive ``resolved_model_identity``
    from. Phase 1 D-12 / Phase 2 D-08's "hash what is installed, never what is declared" rule
    forbids falling back to the model id this client was constructed with — a response this
    malformed is refused by name rather than silently misreporting which model actually served
    the call.
    """

    def __init__(self, requested_model: str):
        self.requested_model = requested_model
        super().__init__(
            f"response for requested model {requested_model!r} carried no model field to derive "
            "resolved_model_identity from; refusing to substitute the requested id"
        )


class EmptyEmbeddingInputError(ValueError):
    """Raised by :meth:`OpenAICompatibleClient.embed` when handed an empty batch, or a batch
    containing an item whose ``str(...).strip()`` is falsy, before any request reaches the
    provider. Named after :class:`ModelIdentityMissingError`'s own shape: the specifics carried on
    attributes, a constructed message, a class docstring explaining why this refuses.

    A silent skip of the offending item is prohibited: :class:`~databasise.clients.base
    .EmbeddingResult`'s own contract promises one vector per input text, in the same order as the
    input, so dropping an item would return fewer vectors than inputs and every downstream
    ``vectors[0]`` / positional zip would silently bind to the wrong text — a worse failure than
    the provider ``400`` this refusal replaces.
    """

    def __init__(self, *, index: int | None, batch_size: int):
        self.index = index
        self.batch_size = batch_size
        if index is None:
            message = f"embed() was handed an empty batch (batch_size={batch_size})"
        else:
            message = (
                f"embed() batch item at index {index} is empty or whitespace-only "
                f"(batch_size={batch_size}); refusing before any provider request is constructed"
            )
        super().__init__(message)


class OpenAICompatibleClient:
    """Chat-completions + embeddings over any OpenAI-compatible endpoint (D-07): construct once
    with the target ``base_url``/``model``/``api_key`` and the identical code path reaches
    OpenRouter, a local Ollama endpoint, or plain OpenAI.

    ``client`` is an escape hatch for tests: pass a stub double exposing the same
    ``chat.completions.create``/``embeddings.create`` async surface as ``openai.AsyncOpenAI`` to
    exercise this class with no network reachable. Left ``None`` (the real-usage path), a real
    ``openai.AsyncOpenAI`` is constructed from ``base_url``/``api_key``.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str = "not-needed",
        client: Any | None = None,
        provider_routing_body: dict[str, Any] | None = None,
    ) -> None:
        self._model = model
        self._provider_routing_body = provider_routing_body
        self._client = client if client is not None else openai.AsyncOpenAI(
            base_url=base_url, api_key=api_key
        )

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> ChatResult:
        # D-07's pinned provider-routing body (OPENAI_LLM_EXTRA_BODY), matching
        # v1_driver_script.py's/run_parity_ingest.py's `extra_body=_extra_body(...)` on the chat
        # call only — never on embed() (see that pair's own `openai_embed.func` call, which never
        # passes extra_body). A caller-supplied `extra_body` kwarg wins over the constructed
        # default (setdefault, not overwrite) — the escape hatch tests already rely on stays open.
        # An absent pin adds no key at all, so a local Ollama configuration with no provider to
        # route sends none.
        if self._provider_routing_body is not None:
            kwargs.setdefault("extra_body", self._provider_routing_body)
        response = await self._client.chat.completions.create(
            model=self._model, messages=messages, **kwargs
        )
        resolved_model_identity = self._resolved_identity(getattr(response, "model", None))
        tokens = self._token_accounting(getattr(response, "usage", None), resolved_model_identity)
        text = response.choices[0].message.content
        return ChatResult(text=text, tokens=tokens, resolved_model_identity=resolved_model_identity)

    async def embed(self, texts: list[str], **kwargs: Any) -> EmbeddingResult:
        # 06-14-PLAN.md: refuse before any other work — an empty batch, or the first item whose
        # str(...).strip() is falsy, raises EmptyEmbeddingInputError rather than reaching the
        # provider. strip() truthiness over the decoded string, never a byte-length or bare len()
        # test: a string of spaces is what a provider rejects as too_small just as readily as a
        # zero-length one.
        if not texts:
            raise EmptyEmbeddingInputError(index=None, batch_size=0)
        for index, text in enumerate(texts):
            if not str(text).strip():
                raise EmptyEmbeddingInputError(index=index, batch_size=len(texts))

        response = await self._client.embeddings.create(model=self._model, input=texts, **kwargs)
        resolved_model_identity = self._resolved_identity(getattr(response, "model", None))
        tokens = self._token_accounting(getattr(response, "usage", None), resolved_model_identity)
        vectors = [item.embedding for item in response.data]
        return EmbeddingResult(
            vectors=vectors, tokens=tokens, resolved_model_identity=resolved_model_identity
        )

    def _resolved_identity(self, reported_model: str | None) -> str:
        if not reported_model:
            raise ModelIdentityMissingError(self._model)
        return reported_model

    def _token_accounting(self, usage: Any, resolved_model_identity: str) -> TokenAccounting:
        if usage is None:
            return TokenAccounting(counted_by=resolved_model_identity)

        details = getattr(usage, "prompt_tokens_details", None)
        cached_read_tokens = getattr(details, "cached_tokens", 0) or 0 if details is not None else 0
        tokenizer_id = getattr(usage, "tokenizer_id", None)

        return TokenAccounting(
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            cached_read_tokens=cached_read_tokens,
            call_count=1,
            counted_by=tokenizer_id or resolved_model_identity,
        )


__all__ = ["OpenAICompatibleClient", "ModelIdentityMissingError", "EmptyEmbeddingInputError"]
