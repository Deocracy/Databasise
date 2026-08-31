"""D-04's four executable reference parts (passthrough, deterministic fake retriever, fake LLM
caller, fixpoint body) plus the capability-scoped store handle a part's body can use to enforce
deny-by-default (CONTRACT §2) at the part boundary itself, not only at the validator.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import Effect, Part
from databasise.parts_core.fake_llm_caller import FAKE_LLM_CALLER_PART
from databasise.parts_core.fake_retriever import FAKE_RETRIEVER_PART
from databasise.parts_core.fixpoint_body import FIXPOINT_BODY_PART
from databasise.parts_core.passthrough import PASSTHROUGH_PART


class UndeclaredEffectError(PermissionError):
    """Raised when a part's body reaches for a store/capability outside its own declared
    ``effects[]`` — deny-by-default enforced at the part boundary (CONTRACT §2), proving the
    rule reaches further than the validator alone.
    """

    def __init__(self, effect: str, declared: list[str]):
        self.effect = effect
        self.declared = list(declared)
        super().__init__(
            f"undeclared effect {effect!r}; this part declared only {self.declared!r}"
        )


class StoreNotWiredError(RuntimeError):
    """Raised when a part's body reaches for a store backing a *declared* effect, but the run's
    ``stores`` dict simply has no entry for that store key (WR-01) — for example a run wired only
    ``"kv"`` while the part legitimately declares ``reads_vector``. Distinct from
    :class:`UndeclaredEffectError`: the effect itself is permitted, the backing store just is not
    wired for this run. Names both the effect and the missing store key rather than falling
    through to a silent ``None`` and a confusing downstream ``AttributeError`` — "refusals over
    silent fallbacks" (this codebase's own stated house style, e.g. ``stores/lexical.py``'s FTS5
    availability check, ``stores/vector.py``'s faiss-import guard).
    """

    def __init__(self, effect: str, store_key: str):
        self.effect = effect
        self.store_key = store_key
        super().__init__(
            f"declared effect {effect!r} requires store {store_key!r}, but no store is wired "
            f"under that key for this run"
        )


class CapabilityScopedStores:
    """Wraps a run's raw ``stores`` dict, exposing a store handle for effect ``X`` only if
    ``X`` is present in the calling part's own declared ``effects``. Requesting an undeclared
    effect raises :class:`UndeclaredEffectError` rather than returning a no-op or null handle —
    a refusal, never a silent bypass. Requesting a declared effect whose backing store simply
    isn't wired for this run raises :class:`StoreNotWiredError` (WR-01) rather than returning
    ``None``.
    """

    def __init__(self, raw_stores: dict[str, Any], declared_effects: list[Effect]):
        self._raw_stores = raw_stores
        self._declared_effects = list(declared_effects)

    def require(self, effect: Effect) -> Any:
        if effect not in self._declared_effects:
            raise UndeclaredEffectError(effect, self._declared_effects)
        store_key = effect.split("_", 1)[-1]  # "reads_kv" -> "kv", "writes_vector" -> "vector"
        try:
            return self._raw_stores[store_key]
        except KeyError:
            raise StoreNotWiredError(effect, store_key) from None


PARTS: tuple[Part, ...] = (
    PASSTHROUGH_PART,
    FAKE_RETRIEVER_PART,
    FAKE_LLM_CALLER_PART,
    FIXPOINT_BODY_PART,
)

__all__ = ["PARTS", "CapabilityScopedStores", "StoreNotWiredError", "UndeclaredEffectError"]
