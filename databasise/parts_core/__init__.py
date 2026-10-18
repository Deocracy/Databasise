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

    def __init__(self, effect: str, declared: list[str], *, reason: str | None = None):
        self.effect = effect
        self.declared = list(declared)
        super().__init__(
            reason or f"undeclared effect {effect!r}; this part declared only {self.declared!r}"
        )


class StoreNotWiredError(RuntimeError):
    """Raised when a part's body reaches for a store backing a *declared* effect, but the run's
    ``stores`` dict simply has no entry for that store key (WR-01) — for example a run wired only
    ``"kv"`` while the part legitimately declares ``reads_vector``. Distinct from
    :class:`UndeclaredEffectError`: the effect itself is permitted, the backing store just is not
    wired for this run. Names both the effect and the missing store key rather than falling
    through to a silent ``None`` and a confusing downstream ``AttributeError`` — "refusals over
    silent fallbacks" (this codebase's own stated house style, e.g. ``stores/vector.py``'s
    faiss-import guard).
    """

    def __init__(self, effect: str, store_key: str):
        self.effect = effect
        self.store_key = store_key
        super().__init__(
            f"declared effect {effect!r} requires store {store_key!r}, but no store is wired "
            f"under that key for this run"
        )


# D-09: the one effect -> (store kind, access mode) table. Every Effect member is a key; a
# ``None`` value means no store backs the effect, so require() refuses it before any store lookup.
EFFECT_TO_STORE: dict[str, tuple[str, str] | None] = {
    "reads_kv": ("kv", "r"),
    "writes_kv": ("kv", "w"),
    "reads_vector": ("vector", "r"),
    "writes_vector": ("vector", "w"),
    "reads_graph": ("graph", "r"),
    "writes_graph": ("graph", "w"),
    "reads_lexical": None,
    "writes_lexical": None,
    "reads_blob": None,
    "writes_artifact": None,
    "mutates_store": None,
    "self_storage": None,
    "calls_llm": None,
    "calls_rerank": None,
    "calls_embedding": None,
    "net": None,
    "fs": None,
}

_READ_ALLOWLIST: dict[str, frozenset[str]] = {
    "kv": frozenset({"get_by_id", "get_by_ids", "filter_keys", "is_empty"}),
    "vector": frozenset({"select", "query", "score_all", "self_knn", "iter_vectors", "get_by_id"}),
    "graph": frozenset(
        {
            "has_node",
            "get_node",
            "has_edge",
            "get_edge",
            "node_degree",
            "get_node_edges",
            "export_to_igraph",
            "get_all_labels",
        }
    ),
}

# Commit, abort and teardown belong to the engine (D-07): no part may call them on any handle.
_ENGINE_ONLY: frozenset[str] = frozenset(
    {
        "index_done_callback",
        "drop_pending_index_ops",
        "finalize",
        "drop",
        "prepare",
        "commit_prepared",
        "abort_prepared",
    }
)


class _StoreProxy:
    """A part's view of one store (D-09). Mode ``"r"`` exposes only the kind's read allowlist;
    mode ``"w"`` exposes everything except the engine-only lifecycle methods. ``select`` returns
    the selected namespace wrapped in a proxy of the same kind and mode.
    """

    __slots__ = ("_target", "_kind", "_mode", "_declared")

    def __init__(self, target: Any, kind: str, mode: str, declared: list[str]) -> None:
        self._target = target
        self._kind = kind
        self._mode = mode
        self._declared = declared

    def __getattr__(self, name: str) -> Any:
        if name in _ENGINE_ONLY:
            raise UndeclaredEffectError(
                name, self._declared, reason=f"store method {name!r} is engine-only"
            )
        if self._mode == "r" and name not in _READ_ALLOWLIST[self._kind]:
            raise UndeclaredEffectError(f"writes_{self._kind}", self._declared)
        attr = getattr(self._target, name)
        if name == "select":
            return lambda *a, **kw: _StoreProxy(attr(*a, **kw), self._kind, self._mode, self._declared)
        return attr


class CapabilityScopedStores:
    """Wraps a run's raw ``stores`` dict, exposing a store handle for effect ``X`` only if
    ``X`` is present in the calling part's own declared ``effects``. Requesting an undeclared
    effect raises :class:`UndeclaredEffectError` rather than returning a no-op or null handle —
    a refusal, never a silent bypass. The effect resolves through :data:`EFFECT_TO_STORE`
    (D-09): an effect no store backs is refused without reading ``raw_stores``; a ``reads_*``
    effect returns a read-only allowlist proxy and a ``writes_*`` effect the writable handle,
    both with the lifecycle methods held back for the engine. A declared effect whose backing
    store isn't wired for this run raises :class:`StoreNotWiredError` (WR-01).
    """

    def __init__(self, raw_stores: dict[str, Any], declared_effects: list[Effect]):
        self._raw_stores = raw_stores
        self._declared_effects = list(declared_effects)

    def require(self, effect: Effect) -> Any:
        if effect not in self._declared_effects:
            raise UndeclaredEffectError(effect, self._declared_effects)
        entry = EFFECT_TO_STORE.get(effect)
        if entry is None:
            raise UndeclaredEffectError(
                effect, self._declared_effects, reason=f"no store backs effect {effect!r}"
            )
        kind, mode = entry
        try:
            target = self._raw_stores[kind]
        except KeyError:
            raise StoreNotWiredError(effect, kind) from None
        return _StoreProxy(target, kind, mode, self._declared_effects)


PARTS: tuple[Part, ...] = (
    PASSTHROUGH_PART,
    FAKE_RETRIEVER_PART,
    FAKE_LLM_CALLER_PART,
    FIXPOINT_BODY_PART,
)

__all__ = [
    "EFFECT_TO_STORE",
    "PARTS",
    "CapabilityScopedStores",
    "StoreNotWiredError",
    "UndeclaredEffectError",
]
