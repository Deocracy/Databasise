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
        "list_ids",  # the operator chunk page (16-07) pages ids through the engine; a part has iter_vectors
    }
)


_PROXY_SLOTS: frozenset[str] = frozenset({"_target", "_kind", "_mode", "_declared"})

# Mutators of any store kind. A read proxy refuses them with UndeclaredEffectError even where its own
# kind lacks the method (a part asking a graph for ``upsert`` is writing, not misspelling).
_WRITE_VOCABULARY: frozenset[str] = frozenset(
    {"upsert", "delete", "delete_by_ids", "upsert_node", "upsert_edge", "delete_node", "delete_edge",
     "ensure_index"}
)


class _StoreProxy:
    """A part's view of one store (D-09). Mode ``"r"`` exposes only the kind's read allowlist;
    mode ``"w"`` exposes everything except the engine-only lifecycle methods. ``select`` returns
    the selected namespace wrapped in a proxy of the same kind and mode.

    **Threat model (iteration-2 WR-04, D-09 intent: misuse prevention).** The proxy stops accidental
    misuse by admitted, in-process parts: a part cannot reach a lifecycle method, a private store
    attribute or a write on a read handle by the ordinary route. It is not a sandbox against hostile
    code. Python offers no seal against code that tries (``proxy.<method>.__self__``,
    ``__globals__``, ``object.__setattr__``, the public ``unwrap_store_handle``), and those routes are
    deliberately not chased. Untrusted part code needs a process boundary, not this class.
    """

    __slots__ = ("_target", "_kind", "_mode", "_declared")

    def __init__(self, target: Any, kind: str, mode: str, declared: list[str]) -> None:
        # Phase 10 review WR-02: every access goes through object.__getattribute__ / __setattr__, and
        # the proxy exposes no private state of its own or of the target.
        for slot, value in (("_target", target), ("_kind", kind), ("_mode", mode), ("_declared", declared)):
            object.__setattr__(self, slot, value)

    def __getattribute__(self, name: str) -> Any:
        get = object.__getattribute__
        declared = get(self, "_declared")
        if name.startswith("__"):
            return get(self, name)
        kind, mode, target = get(self, "_kind"), get(self, "_mode"), get(self, "_target")
        refusal = None
        if name.startswith("_"):
            refusal = UndeclaredEffectError(name, declared, reason=f"store attribute {name!r} is not exposed")
        elif name in _ENGINE_ONLY:
            refusal = UndeclaredEffectError(name, declared, reason=f"store method {name!r} is engine-only")
        elif mode == "r" and name not in _READ_ALLOWLIST[kind]:
            refusal = UndeclaredEffectError(f"writes_{kind}", declared)
        if refusal is not None:
            # Iteration-2 IN-02: a name the target does not have is an AttributeError, so hasattr and
            # getattr-with-default work; a real but withheld attribute stays an UndeclaredEffectError.
            if name not in _PROXY_SLOTS | _WRITE_VOCABULARY and not hasattr(target, name):
                raise AttributeError(f"{type(target).__name__!r} object has no attribute {name!r}")
            raise refusal
        attr = getattr(target, name)
        if name == "select":
            return lambda *a, **kw: _StoreProxy(attr(*a, **kw), kind, mode, declared)
        return attr

    def __setattr__(self, name: str, value: Any) -> None:
        raise UndeclaredEffectError(
            name, object.__getattribute__(self, "_declared"), reason="a store handle is read-only"
        )

    def __delattr__(self, name: str) -> None:
        raise UndeclaredEffectError(
            name, object.__getattribute__(self, "_declared"), reason="a store handle is read-only"
        )


def unwrap_store_handle(proxy: Any) -> Any:
    """Return the raw store behind a capability proxy. For tests and engine only: a part body must
    never call this, because the raw store carries the lifecycle and writer methods the proxy
    withholds. Nothing enforces that: the proxy guards against accidental misuse by admitted,
    in-process parts, not against hostile code (see :class:`_StoreProxy`, iteration-2 WR-04)."""
    return object.__getattribute__(proxy, "_target")


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
    "unwrap_store_handle",
]
