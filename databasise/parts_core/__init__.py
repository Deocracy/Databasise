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


class CapabilityScopedStores:
    """Wraps a run's raw ``stores`` dict, exposing a store handle for effect ``X`` only if
    ``X`` is present in the calling part's own declared ``effects``. Requesting an undeclared
    effect raises :class:`UndeclaredEffectError` rather than returning a no-op or null handle —
    a refusal, never a silent bypass.
    """

    def __init__(self, raw_stores: dict[str, Any], declared_effects: list[Effect]):
        self._raw_stores = raw_stores
        self._declared_effects = list(declared_effects)

    def require(self, effect: Effect) -> Any:
        if effect not in self._declared_effects:
            raise UndeclaredEffectError(effect, self._declared_effects)
        store_key = effect.split("_", 1)[-1]  # "reads_kv" -> "kv", "writes_vector" -> "vector"
        return self._raw_stores.get(store_key)


PARTS: tuple[Part, ...] = (
    PASSTHROUGH_PART,
    FAKE_RETRIEVER_PART,
    FAKE_LLM_CALLER_PART,
    FIXPOINT_BODY_PART,
)

__all__ = ["PARTS", "CapabilityScopedStores", "UndeclaredEffectError"]
