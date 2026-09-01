"""Machine-owned LLM/embedding/rerank client primitives, deny-by-default scoped per-node (D-06).

``CapabilityScopedClients`` mirrors ``databasise.parts_core.CapabilityScopedStores`` structurally
(RESEARCH.md Pattern 1) — the same CR-01 concern the store side exists for (an under-declaring
wiring metering a real spend as zero) applies identically to a client call. ``UndeclaredEffectError``
is imported and reused from ``databasise.parts_core`` rather than redefined a second time; only
``ClientNotWiredError`` is new, as the sibling to ``StoreNotWiredError`` this side needs.

The store side's ``effect.split("_", 1)[-1]`` suffix trick does not transfer here: it works by
coincidence of spelling on the store side (``"reads_kv"`` -> ``"kv"``), but ``"calls_embedding"``
would split to ``"embedding"`` only because that happens to be the tail of the word, and
``"calls_rerank"`` to ``"rerank"`` likewise only by the same accident — an explicit dict states
the effect-to-client-key mapping instead of relying on that coincidence holding for every future
effect name.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import Effect
from databasise.parts_core import UndeclaredEffectError

# The one place this mapping is stated — every other module (runner/scheduler.py's
# _ScopedClientsView included) imports this dict rather than restating it.
_CLIENT_EFFECT_TO_KEY: dict[str, str] = {
    "calls_llm": "llm",
    "calls_embedding": "embedding",
    "calls_rerank": "rerank",
}


class ClientNotWiredError(RuntimeError):
    """Raised when a part's body reaches for a client backing a *declared* effect, but the run's
    ``clients`` dict simply has no entry for that client key — mirrors
    :class:`databasise.parts_core.StoreNotWiredError`'s exact refusal-with-both-names shape and
    house style ("refusals over silent fallbacks"). Distinct from
    :class:`~databasise.parts_core.UndeclaredEffectError`: the effect itself is permitted, the
    backing client just is not wired for this run.
    """

    def __init__(self, effect: str, client_key: str):
        self.effect = effect
        self.client_key = client_key
        super().__init__(
            f"declared effect {effect!r} requires client {client_key!r}, but no client is wired "
            f"under that key for this run"
        )


class CapabilityScopedClients:
    """Wraps a run's raw ``clients`` dict, exposing a client handle for effect ``X`` only if
    ``X`` is present in the calling part's own declared ``effects``. Requesting an undeclared
    effect raises :class:`~databasise.parts_core.UndeclaredEffectError`; requesting a declared
    effect whose backing client simply isn't wired for this run raises
    :class:`ClientNotWiredError` rather than returning ``None``.
    """

    def __init__(self, raw_clients: dict[str, Any], declared_effects: list[Effect]):
        self._raw_clients = raw_clients
        self._declared_effects = list(declared_effects)

    def require(self, effect: Effect) -> Any:
        if effect not in self._declared_effects:
            raise UndeclaredEffectError(effect, self._declared_effects)
        client_key = _CLIENT_EFFECT_TO_KEY.get(effect)
        if client_key is None:
            # A declared effect with no client-shaped mapping (e.g. "reads_kv") cannot be
            # fulfilled through the clients view at all — refused the same way an undeclared
            # effect would be, rather than leaking a raw KeyError from the dict lookup.
            raise UndeclaredEffectError(effect, self._declared_effects)
        try:
            return self._raw_clients[client_key]
        except KeyError:
            raise ClientNotWiredError(effect, client_key) from None


__all__ = [
    "CapabilityScopedClients",
    "ClientNotWiredError",
    "UndeclaredEffectError",
]
