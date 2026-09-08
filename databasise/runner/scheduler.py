"""Structured-concurrency runner.

Claude's Discretion (01-02-PLAN.md ``<decisions_recorded_here>``): ``graphlib.TopologicalSorter``
for readiness bookkeeping plus one ``asyncio.TaskGroup`` per ready batch. No orchestrator, no
external scheduler, no metadata DB. Sort each ready batch by node id before dispatch (stated tie-
break): when nodes become ready together, order is by node id ascending — this is what makes
``arm_execution_order``/per-batch dispatch order reproducible across two runs of the same wiring.

D-09 (one-way door, confirmed 01-01-PLAN.md Task 4, recorded in 01-01-SUMMARY.md): **option-a**
selected — intra-node concurrency is bounded by a per-node ``asyncio.Semaphore``, sized from that
node's own declared ``config.max_concurrency`` (default 1 when absent), created fresh per node
per run and NEVER shared across nodes. D-11 rejects a process-wide concurrency cap explicitly:
one arm's fan-out must never throttle an unrelated arm beside it, contaminating Phase 6's
side-by-side comparison — so this module defines no module-level singleton, manager object, or
global limits dict. The v1 shape this rejects lives at ``v1/lightrag/kg/shared_storage.py:66``
(``_manager``), ``:111`` (``_global_concurrency_limits``), and ``:175`` (``class UnifiedLock``);
none of it is imported or re-derived here (D-11/D-14). A declared ``max_concurrency`` below 1 is
refused at validation, before any node is dispatched, naming the offending node id.

CONTRACT §9's V-7 repair holds that a node's own internal parallelism is its private
implementation detail — the machine meters and can halt the node only at its declared boundary,
it does not additionally schedule what happens inside the node. Consistent with that, the
semaphore this module creates is not used to gate the single outer call to a part's body; it is
exposed to the body as ``ctx._semaphore`` — a private, scheduler-owned extension attribute, not
part of ``NodeContext``'s frozen public schema (``databasise/parts/schema.py``, out of this
plan's lane) — so a body MAY voluntarily bound its own internal fan-out using the very semaphore
the runner already sized for it, though nothing requires a body to use it.

**Closing 01-04's two inherited gaps (01-04-SUMMARY.md "Known Gaps"), both in this plan:**

1. Declaration-only dispatch now goes through ``databasise.parts.registry.dispatch()`` (D-04),
   which raises ``DeclarationOnlyPartError`` naming the part rather than the previous silent
   ``inputs`` passthrough for a ``body is None`` Part.
2. Every node's ``ctx.stores`` is now a capability-scoped view built from
   ``databasise.parts_core.CapabilityScopedStores`` (deny-by-default, keyed by the **registry's
   own** declared ``effects`` — ``parsed.parts[node_id].effects``, never the wiring's
   self-declared ``WiringNode.effects``; see CR-01 below), wrapped by this module's
   ``_ScopedStoresView`` so existing bodies written against plain ``dict``-style subscript access
   (``ctx.stores["kv"]``) keep working while gaining the underlying deny-by-default enforcement —
   see ``_ScopedStoresView``'s own docstring for the exact mapping rule.

**Placement (D-08).** ``execution_mode`` is now derived via
``databasise.validator.execution_mode.derive_execution_mode`` (plan 01-03's hardened version,
with ``host()`` and a named ``UnimplementedPlacementError``) rather than the tracer-era duplicate
in ``databasise.validator.depth`` — the two modules independently define a function of this name;
this module intentionally uses the 01-03 one because it is the one that ships a real hosting
refusal. ``validator.depth.derive_execution_mode`` is left untouched (out of this plan's lane;
``tests/parts/test_reference_parts.py`` still imports it and is unaffected by this switch).

**CR-01 fix (containment/blast-radius must trust the registry, not the wiring).** A wiring
document is untrusted, author-supplied input (``validator/cycles.py``'s own "a hostile or merely
large wiring could declare..." framing). ``derive_execution_mode`` and the capability-scoped
store view below both read ``parsed.parts[node_id].effects``/``.kind`` — the resolved ``Part``'s
own registered declaration — never ``parsed.nodes[node_id].effects``/``.kind`` (the wiring's own,
self-declared, unverified fields). Reading the wiring's fields here would let an under-declaring
wiring silently route a node into ``in-process`` hosting, or grant it a store view scoped to
fewer effects than the wiring's node claims, and would let ``blast_radius_violations`` (see
``validator/blast_radius.py``) skip a node entirely by omitting ``writes_artifact`` on the node
while the registered Part still performs it — exactly the containment/blast-radius bypass
Falsifier 2 (this phase's gate) is meant to rule out. ``validator/parse.py``'s ``parse_wiring``
additionally refuses (``CODE_EFFECTS_EXCEED_PART``) any wiring node whose declared ``effects`` is
not a subset of its resolved Part's declared ``effects`` — a wiring MAY declare a narrower set
than the Part is capable of, but never a broader one.

**Cycles are data, not an exception (Test 10, closing a real bug).** The tracer-era code wrapped
only ``effective_depth()`` in a ``try/except graphlib.CycleError`` — but ``validator.depth``'s
current ``effective_depth`` is SCC-condensation-based (01-03) and no longer raises for cyclic
input, so that ``except`` clause has been dead code since 01-03 landed, while
``_resolve_identities()``'s own separate ``TopologicalSorter(...).static_order()`` call — which
DOES still raise ``graphlib.CycleError`` for a genuine dependency cycle — was left uncaught,
letting a cyclic wiring's exception propagate straight past the runner. This module now reads
``parsed.report.cycles`` (already computed once by ``validator.parse.parse_wiring``, independent
of dispatch) before touching identity resolution at all, so a cyclic wiring returns
``{"cycle": [...]}`` as data rather than raising, and never reaches ``_resolve_identities``.

**Partial outcomes are never discarded (CONTRACT §9).** "A run that halts on budget, or otherwise
completes only partially, MUST be traced, scored, and tier-labeled exactly as a completed run is;
it MUST NOT be discarded." Both a placement refusal mid-run (D-08) and a batch-internal node
failure (structured-concurrency semantics, ``except*``) are therefore surfaced as a **returned**
partial result (``partial=True``, a populated ``stop_reason``, the failing node's own trace stamp
preserved) rather than an exception propagated out of ``run_wiring`` — the refusal/failure is
real and recorded, but the run is not silently lost. Pre-flight refusals that mean the run never
starts at all (an empty ``nodes`` object or any other accumulated parse violation; a declared
``max_concurrency`` below 1) are the one case that DOES raise, before any node is dispatched,
because there is no partial progress to preserve at that point — "the run does not start" is
exactly that: nothing ran, so there is nothing to trace as a partial result.

**Metering is wired into the live dispatch path (Gap 2 / MACH-05, 01-10-PLAN.md).** The successful
dispatch path now meters through ``runner/budget.py``'s ``meter()`` at each node's own declared
boundary, reading the registry's own resolved ``Part.effects`` (``parsed.parts[node_id].effects``)
— never the wiring's self-declared ``WiringNode.effects`` — for the same CR-01 reason this module
already sources ``execution_mode`` and the capability-scoped store view: an under-declaring wiring
must not be able to meter a real LLM/rerank/embedding spend as zero. A node's own ``TokenAccounting``
and ``cache_hit`` are read from its body's own return value (``_body_report``), never assumed.
Declared data guards (``config.guards``) are validated pre-flight via ``runner/guards.py``'s
``declare_guard`` and evaluated post-dispatch via ``evaluate_guards``, stamping ``NodeTrace
.guards_fired`` in declaration order. A node whose realised spend exceeds its ``config
.token_allowance`` (DEC-A/DEC-B: an ordinary field on the node's own wiring ``config``, defaulting
to ``DEFAULT_TOKEN_ALLOWANCE=0`` when absent — a branch cannot spend what it was not handed,
CONTRACT §9) is stamped ``budget_state="halted"`` and the run is returned as a traced
``stop_reason="budget_halt"`` partial run — never a clean record, never a raised exception.

**Optional per-node touch recording (03-08-PLAN.md Task 1, D-15's storage-ownership audit).**
``run_wiring``/``_run_node`` accept an optional ``recorder`` callable, threaded to
``_ScopedStoresView``/``_ScopedClientsView`` — the two places that know both the requesting node
id and the requested store/client key, which is why recording belongs here and not in a proxy
wrapped around the raw ``stores``/``clients`` dicts (a raw-store proxy cannot attribute a call to
a node). On each successful resolution (``.require(effect)`` already succeeded — an undeclared
effect never reaches the recorder, since it raises first) the view calls
``recorder(node_id, kind, key)`` with ``kind`` one of ``"store"``/``"client"``. ``recorder``
defaults to ``None``, and both views skip the callback entirely when it is ``None`` — the default
path allocates nothing new and adds one cheap ``is not None`` branch, so no existing test's
behaviour changes. ``databasise/parity/storage_audit.py`` is the one caller that passes a real
recorder.
"""

from __future__ import annotations

import asyncio
import graphlib
import time
from collections.abc import Callable, Mapping
from typing import Any

from databasise.clients import CLIENT_EFFECT_TO_KEY, CapabilityScopedClients
from databasise.identity.canon import config_hash
from databasise.identity.env import environment_hash
from databasise.identity.instance import instance_hash
from databasise.parts.admission import MissingWallClockCeilingError
from databasise.parts.registry import PartRegistry, dispatch
from databasise.parts.schema import NodeContext
from databasise.parts_core import CapabilityScopedStores, UndeclaredEffectError
from databasise.runner.budget import meter, realised_share
from databasise.runner.guards import GuardDeclaration, declare_guard, evaluate_guards
from databasise.runner.trace import NodeTrace, TokenAccounting
from databasise.validator.depth import effective_depth
from databasise.validator.execution_mode import (
    UnimplementedPlacementError,
    derive_execution_mode,
    host,
)
from databasise.validator.parse import ParsedWiring

# DEC-B: an absent config.token_allowance means an allowance of 0, not an unbounded one — CONTRACT
# §9's "a branch cannot spend what it was not handed" (see this module's docstring's "Metering is
# wired into the live dispatch path" paragraph).
DEFAULT_TOKEN_ALLOWANCE = 0

# D-15: a touch recorder is any callable of this shape — (node_id, kind, key) -> None, where kind
# is "store" or "client". Passed to run_wiring/_run_node and threaded to _ScopedStoresView/
# _ScopedClientsView (see module docstring's "Optional per-node touch recording" paragraph).
TouchRecorder = Callable[[str, str, str], None]

# 05-03-PLAN.md Task 2: the two store-touch kinds MACH-11 correlates (databasise.seam.engine
# ._mach11_events). TOUCH_KIND_OBSERVED is the pre-existing value _ScopedStoresView already
# emits for a machine-observed touch (a node whose store access crosses a handle the machine
# itself holds) — unchanged, both _mach11_events and test_mach11_event.py already read it.
# TOUCH_KIND_NODE_REPORTED is new: a node's own self-report via NodeContext.record_store_touch,
# for a mutation the machine holds no store handle to observe (an opaque node's subprocess-hosted
# store mutation). The two kinds are never merged — a reader can always tell which is which.
TOUCH_KIND_OBSERVED = "store"
TOUCH_KIND_NODE_REPORTED = "store-declared"

# Transient store-write members plus writes_artifact/mutates_store: per D-13's rule, a node
# carrying one of these has mutated a store on the completed portion of the run, so it can never
# count as a safe resume boundary regardless of any determinism stamp.
_STORE_MUTATING_EFFECTS = frozenset(
    {
        "writes_artifact",
        "mutates_store",
        "writes_kv",
        "writes_vector",
        "writes_graph",
        "writes_lexical",
    }
)


class WiringRefusedError(ValueError):
    """The run does not start: ``parsed.report`` carried at least one accumulated violation (an
    empty ``nodes`` object, an unknown component, a dangling dep, ...). Distinct from a cycle,
    which is legal content reported as data, never a refusal.
    """

    def __init__(self, violations: list[Any]):
        self.violations = list(violations)
        super().__init__(f"{len(self.violations)} wiring violation(s) refuse the run: {self.violations}")


class InvalidMaxConcurrencyError(ValueError):
    """A node declared ``config.max_concurrency`` below 1, OR (WR-04) a value ``int()`` cannot
    coerce at all (a string, a list, a dict, ...). Refused at validation, before any node is
    dispatched, naming the offending node id (D-09).
    """

    def __init__(self, node_id: str, value: Any):
        self.node_id = node_id
        self.value = value
        super().__init__(
            f"node {node_id!r} declares config.max_concurrency={value!r}; must be >= 1"
        )


class InvalidTokenAllowanceError(ValueError):
    """A node declared ``config.token_allowance`` that ``int()`` cannot coerce at all (a string,
    a list, a dict, ...), OR (WR-01) a negative value — mirrors ``InvalidMaxConcurrencyError``'s
    constructor and message shape (the WR-04 lesson: a bare ``ValueError`` leaking out of
    ``int(...)`` is not this module's own named, actionable refusal). Refused at validation,
    before any node is dispatched, naming the offending node id.
    """

    def __init__(self, node_id: str, value: Any):
        self.node_id = node_id
        self.value = value
        super().__init__(
            f"node {node_id!r} declares config.token_allowance={value!r}; must be >= 0"
        )


class NodeExecutionError(RuntimeError):
    """Wraps any exception raised while dispatching one node's body, tagging it with the node id
    so a batch-level ``except*`` handler can attribute the failure to the right node without
    every possible underlying exception type having to carry that information itself.
    """

    def __init__(self, node_id: str, cause: BaseException):
        self.node_id = node_id
        self.cause = cause
        super().__init__(f"node {node_id!r} failed: {cause}")


class NodePlacementRefusedError(NodeExecutionError):
    """A node's derived ``execution_mode`` has no hosting yet (D-08). Carries the derived
    ``placement`` so the batch handler can still stamp it on that node's trace — "the refusal
    does not suppress the stamp."
    """

    def __init__(self, node_id: str, placement: str, cause: BaseException):
        self.placement = placement
        super().__init__(node_id, cause)


class _ScopedStoresView:
    """Wraps :class:`databasise.parts_core.CapabilityScopedStores` (deny-by-default,
    ``.require(effect)``) so a part body written against plain ``dict``-style subscript access —
    ``ctx.stores["kv"]``, the shape every existing reference part uses — keeps working, while the
    access is still routed through the underlying deny-by-default check.

    The mapping rule: a subscript key (a store name, e.g. ``"kv"``) resolves against the node's
    own declared ``effects`` by matching the effect's own suffix after its first underscore
    (``"writes_kv"`` / ``"reads_kv"`` both map to store key ``"kv"``, mirroring
    ``CapabilityScopedStores.require``'s own ``effect.split("_", 1)[-1]`` rule) — the first
    matching declared effect is the one checked. A store key with no matching declared effect
    raises :class:`UndeclaredEffectError`, exactly as calling ``.require()`` directly with an
    undeclared effect would.
    """

    def __init__(
        self,
        scoped: CapabilityScopedStores,
        declared_effects: list[str],
        node_id: str | None = None,
        recorder: TouchRecorder | None = None,
    ) -> None:
        self._scoped = scoped
        self._declared_effects = list(declared_effects)
        self._node_id = node_id
        self._recorder = recorder

    def __getitem__(self, store_key: str) -> Any:
        for effect in self._declared_effects:
            if effect.split("_", 1)[-1] == store_key:
                handle = self._scoped.require(effect)
                if self._recorder is not None:
                    self._recorder(self._node_id, TOUCH_KIND_OBSERVED, store_key)
                return handle
        raise UndeclaredEffectError(f"*_{store_key}", self._declared_effects)


class _ScopedClientsView:
    """Wraps :class:`databasise.clients.CapabilityScopedClients` (deny-by-default,
    ``.require(effect)``) so a part body written against plain ``dict``-style subscript access —
    ``ctx.clients["llm"]`` — routes through the underlying deny-by-default check, mirroring
    ``_ScopedStoresView``'s shape for the clients side (D-06).

    The mapping rule differs from ``_ScopedStoresView``'s own suffix-split rule: a subscript key
    (a client name, e.g. ``"llm"``) resolves against the node's own declared ``effects`` via the
    explicit ``CLIENT_EFFECT_TO_KEY`` dict imported from ``databasise.clients`` — not restated
    here — because the store side's ``effect.split("_", 1)[-1]`` suffix trick only works by
    coincidence of spelling and does not transfer to ``calls_embedding``/``calls_rerank``. A
    client key with no matching declared effect raises :class:`UndeclaredEffectError`, exactly as
    calling ``.require()`` directly with an undeclared effect would.
    """

    def __init__(
        self,
        scoped: CapabilityScopedClients,
        declared_effects: list[str],
        node_id: str | None = None,
        recorder: TouchRecorder | None = None,
    ) -> None:
        self._scoped = scoped
        self._declared_effects = list(declared_effects)
        self._node_id = node_id
        self._recorder = recorder

    def __getitem__(self, client_key: str) -> Any:
        for effect in self._declared_effects:
            if CLIENT_EFFECT_TO_KEY.get(effect) == client_key:
                handle = self._scoped.require(effect)
                if self._recorder is not None:
                    self._recorder(self._node_id, "client", client_key)
                return handle
        raise UndeclaredEffectError(f"calls_{client_key}", self._declared_effects)


def _resolve_identities(parsed: ParsedWiring) -> dict[str, dict[str, str]]:
    """Bottom-up ``(name@version, config_hash, resolved_dependency_ids)`` per node.

    ``resolved_dependency_ids`` is the sorted list of each direct dependency's OWN
    ``instance_hash`` — never the raw dependency node id, since a wiring node id is a position,
    never an identity.
    """
    env = environment_hash()  # one resolved-closure digest per run, shared across every node
    order = list(graphlib.TopologicalSorter(dict(parsed.deps)).static_order())
    identities: dict[str, dict[str, str]] = {}
    for node_id in order:
        node = parsed.nodes[node_id]
        part = parsed.parts[node_id]
        resolved_dep_ids = sorted(
            identities[dep]["instance_hash"] for dep in parsed.deps.get(node_id, ())
        )
        c_hash = config_hash(node.config or {}, env=env)
        i_hash = instance_hash(part.name_at_version, c_hash, resolved_dep_ids)
        identities[node_id] = {"config_hash": c_hash, "instance_hash": i_hash}
    return identities


def _validated_max_concurrency(node_id: str, config: dict[str, Any] | None) -> int:
    """Extract and validate ``config.max_concurrency`` (D-09), defaulting to 1 when absent.
    Raises :class:`InvalidMaxConcurrencyError`, naming ``node_id``, for a declared value below 1
    OR (WR-04) for a declared value ``int()`` cannot coerce at all (a string, a list, a dict, ...)
    — this module's own documented "refused at validation, before any node is dispatched, naming
    the offending node id" contract must hold for that class of malformed input too, not just an
    in-range-but-negative one.
    """
    max_concurrency = 1
    if config:
        raw = config.get("max_concurrency", 1)
        try:
            max_concurrency = int(raw)
        except (TypeError, ValueError):
            raise InvalidMaxConcurrencyError(node_id, raw) from None
    if max_concurrency < 1:
        raise InvalidMaxConcurrencyError(node_id, max_concurrency)
    return max_concurrency


def _validated_token_allowance(node_id: str, config: dict[str, Any] | None) -> int:
    """Extract and validate ``config.token_allowance`` (DEC-A), defaulting to
    ``DEFAULT_TOKEN_ALLOWANCE`` (DEC-B) when absent. Raises :class:`InvalidTokenAllowanceError`,
    naming ``node_id``, for a declared value ``int()`` cannot coerce at all, OR (WR-01) a negative
    value — refused at validation, before any node is dispatched, mirroring
    ``_validated_max_concurrency``'s own WR-04-lesson shape for this sibling field.
    """
    raw = DEFAULT_TOKEN_ALLOWANCE
    if config:
        raw = config.get("token_allowance", DEFAULT_TOKEN_ALLOWANCE)
    try:
        allowance = int(raw)
    except (TypeError, ValueError):
        raise InvalidTokenAllowanceError(node_id, raw) from None
    if allowance < 0:
        raise InvalidTokenAllowanceError(node_id, allowance)
    return allowance


def _validated_guards(node_id: str, config: dict[str, Any] | None) -> list[GuardDeclaration]:
    """``config.guards`` (absent or falsy -> ``[]``) for ``node_id``, each entry constructed via
    ``declare_guard(**entry)``, letting :class:`~databasise.runner.guards.GuardDeclarationError`
    propagate — a malformed guard declaration (an inadmissible ``granularity``) refuses the run
    before any node is dispatched, the same pre-flight contract this module already gives
    ``max_concurrency`` and ``token_allowance`` (``node_id`` names the offending node in that
    propagated error via ``GuardDeclarationError``'s own ``guard_name``/``granularity`` fields).
    """
    raw_guards = (config or {}).get("guards") or []
    return [declare_guard(**entry) for entry in raw_guards]


def _body_report(output: Any) -> tuple[TokenAccounting, bool]:
    """The body's own self-reported ``TokenAccounting`` and cache-hit flag, read from its return
    value rather than assumed. When ``output`` is a ``Mapping`` and ``output.get("tokens")`` is
    genuinely a ``TokenAccounting`` instance, that object is returned as-is (the body owns it — no
    deep copy); otherwise a fresh, all-zero ``TokenAccounting()`` is returned. ``cache_hit`` is
    ``bool(output.get("cache_hit"))`` when ``output`` is a ``Mapping``, else ``False``. Guarded
    with ``isinstance`` on both checks — a body returning a list, a string, or ``None`` must not
    raise here.
    """
    if isinstance(output, Mapping):
        tokens = output.get("tokens")
        if not isinstance(tokens, TokenAccounting):
            tokens = TokenAccounting()
        cache_hit = bool(output.get("cache_hit"))
    else:
        tokens = TokenAccounting()
        cache_hit = False
    return tokens, cache_hit


async def _run_node(
    node_id: str,
    parsed: ParsedWiring,
    stores: dict[str, Any],
    results: dict[str, Any],
    max_concurrency: int,
    clients: dict[str, Any] | None = None,
    recorder: TouchRecorder | None = None,
) -> tuple[str, Any, int]:
    node = parsed.nodes[node_id]
    part = parsed.parts[node_id]

    execution_mode = derive_execution_mode(part.effects, part.kind)
    # 05-01-PLAN.md Task 1: the ceiling for a subprocess placement is sourced from the resolved
    # Part's own admission record (never the wiring's) — a ceiling-less subprocess node still
    # surfaces as a placement refusal on that node's trace, mirroring D-08's original in-process-
    # only refusal shape.
    wall_clock_ceiling_seconds = (
        part.admission.wall_clock_ceiling_seconds if part.admission is not None else None
    )
    try:
        host(execution_mode, wall_clock_ceiling_seconds=wall_clock_ceiling_seconds)
    except (UnimplementedPlacementError, MissingWallClockCeilingError) as exc:
        raise NodePlacementRefusedError(node_id, execution_mode, exc) from exc

    # Per node per run, never shared (D-09/D-11). Not used to gate the outer body call below —
    # CONTRACT §9's V-7 repair treats a node's own internal fan-out as its private
    # implementation detail; the semaphore is exposed to the body (ctx._semaphore) for it to use
    # voluntarily, never enforced by the runner around the single outer call.
    semaphore = asyncio.Semaphore(max_concurrency)

    inputs = {dep: results[dep] for dep in parsed.deps.get(node_id, ())}
    scoped_stores = _ScopedStoresView(
        CapabilityScopedStores(stores, part.effects), part.effects, node_id, recorder
    )
    scoped_clients = _ScopedClientsView(
        CapabilityScopedClients(clients or {}, part.effects), part.effects, node_id, recorder
    )
    ctx_kwargs: dict[str, Any] = dict(
        node_id=node_id,
        config=node.config,
        inputs=inputs,
        stores=scoped_stores,
        clients=scoped_clients,
    )
    if recorder is not None:
        # 05-03-PLAN.md Task 2: a node-reported store touch (NodeContext.record_store_touch) is
        # bound to this run's own recorder with the node-reported kind — never the machine-
        # observed kind _ScopedStoresView emits above. When no recorder is supplied for the run,
        # NodeContext's own no-op default (schema.py) is left in place unchanged.
        def _record_store_touch(key: str, _node_id: str = node_id) -> None:
            recorder(_node_id, TOUCH_KIND_NODE_REPORTED, key)

        ctx_kwargs["record_store_touch"] = _record_store_touch
    ctx = NodeContext(**ctx_kwargs)
    ctx._semaphore = semaphore  # type: ignore[attr-defined]  # scheduler-owned extension, see module docstring

    start = time.monotonic()
    try:
        output = await dispatch(part, ctx)  # closes 01-04's inherited gap 1 (D-04 refusal)
    except NodeExecutionError:
        raise
    except Exception as exc:
        raise NodeExecutionError(node_id, exc) from exc
    wall_clock_ms = int((time.monotonic() - start) * 1000)
    return execution_mode, output, wall_clock_ms


def _pending_node_trace(node_id: str, parsed: ParsedWiring, identities: dict, depths: dict) -> dict[str, Any]:
    """The fields common to every trace stamp this module produces for a node, whether it
    completed normally or failed — factored out so the failure path below does not have to
    duplicate the identity/depth lookups the success path already does.
    """
    part = parsed.parts[node_id]
    return {
        "node_id": node_id,
        "instance_hash": identities[node_id]["instance_hash"],
        "depth": part.structural_depth,
        "effective_depth": depths[node_id],
    }


async def run_wiring(
    parsed: ParsedWiring,
    registry: PartRegistry,
    stores: dict[str, Any],
    *,
    determinism_setting: str,
    concurrency_setting: str,
    clients: dict[str, Any] | None = None,
    recorder: TouchRecorder | None = None,
) -> dict[str, Any]:
    """Drive readiness with ``graphlib.TopologicalSorter``; each ready batch is sorted by node id
    before dispatch (the stated tie-break — see module docstring), then runs inside one
    ``asyncio.TaskGroup``, whose structured-concurrency semantics cancel every sibling in the
    batch the instant one task raises, with no task left orphaned.

    ``registry`` is accepted for signature parity with the rest of this phase's call sites; every
    part this function dispatches is already resolved via ``parsed.parts`` by
    ``validator.parse.parse_wiring``, so the registry itself is not re-queried during execution.
    ``determinism_setting``/``concurrency_setting`` are threaded through for the caller (the
    public composer in ``databasise/__init__.py``) to stamp on the run-level record.
    ``clients`` (D-06) defaults to ``None`` — treated identically to an empty dict — so a run that
    passes no ``clients`` argument at all behaves exactly as before for every existing part.
    ``recorder`` (D-15) defaults to ``None`` — a run that passes none behaves exactly as before;
    see module docstring's "Optional per-node touch recording" paragraph.

    Returns a dict always carrying ``results``, ``nodes``, ``partial``, ``stop_reason``,
    ``degraded``, ``degradation_reason`` and ``node_exceptions`` (05-01-PLAN.md: the real
    underlying exception object a failed node's dispatch raised, keyed by node_id — additive,
    empty for a clean run) — or, for a cyclic wiring, ``{"cycle": [...]}`` as data (see module
    docstring). A pre-flight refusal (empty ``nodes``, any other accumulated parse violation, or a
    declared ``max_concurrency`` below 1) raises before any node is dispatched — see module
    docstring for why that one case raises rather than returning.
    """
    if not parsed.report.ok:
        raise WiringRefusedError(parsed.report.violations)

    if parsed.report.cycles:
        return {"cycle": [sorted(c) for c in parsed.report.cycles]}

    # Pre-flight: every node's max_concurrency/token_allowance/guards is validated before any node
    # is dispatched, so a defect discovered on, say, the fifth node of ten does not leave the
    # first four already run.
    max_concurrencies = {
        node_id: _validated_max_concurrency(node_id, node.config)
        for node_id, node in parsed.nodes.items()
    }
    token_allowances = {
        node_id: _validated_token_allowance(node_id, node.config)
        for node_id, node in parsed.nodes.items()
    }
    guards_by_node: dict[str, list[GuardDeclaration]] = {
        node_id: _validated_guards(node_id, node.config) for node_id, node in parsed.nodes.items()
    }

    depths = effective_depth(parsed)
    identities = _resolve_identities(parsed)

    ts = graphlib.TopologicalSorter(dict(parsed.deps))
    ts.prepare()

    results: dict[str, Any] = {}
    node_traces: list[NodeTrace] = []
    partial = False
    stop_reason: str | None = None
    budget_halted = False
    # 05-01-PLAN.md Task 1: the real underlying exception a failed node's dispatch raised (e.g. a
    # CorpusOpTimeoutError/CorpusOpSubprocessError from an opaque node's subprocess body), keyed by
    # node_id — additive to the returned dict. CONTRACT §9's "partial outcomes are never discarded"
    # rule means a per-node dispatch failure never propagates out of this function (see module
    # docstring); a caller that needs the *real* exception object (not merely its stringified
    # ``cross_process_failure_cause``) to build its own typed refusal reads it from here rather
    # than parsing NodeTrace's own prose string.
    node_exceptions: dict[str, BaseException] = {}

    while ts.is_active():
        ready = sorted(ts.get_ready())
        node_failures: dict[str, NodeExecutionError] = {}
        tasks: dict[str, asyncio.Task] = {}
        try:
            async with asyncio.TaskGroup() as tg:
                tasks = {
                    node_id: tg.create_task(
                        _run_node(
                            node_id,
                            parsed,
                            stores,
                            results,
                            max_concurrencies[node_id],
                            clients,
                            recorder,
                        )
                    )
                    for node_id in ready
                }
        except* NodeExecutionError as eg:
            for exc in eg.exceptions:
                node_failures[exc.node_id] = exc

        for node_id in ready:
            if node_id in node_failures:
                exc = node_failures[node_id]
                placement = getattr(exc, "placement", None)
                cause = (
                    f"NodePlacementRefusedError: execution_mode={placement!r} not hosted (D-08)"
                    if placement is not None
                    else f"NodeExecutionError: {exc.cause}"
                )
                node_exceptions[node_id] = exc.cause
                node_traces.append(
                    NodeTrace(
                        **_pending_node_trace(node_id, parsed, identities, depths),
                        wall_clock_ms=0,
                        cache_hit=False,
                        guards_fired=[],
                        # Closest of the schema's three enum values to "this node's execution did
                        # not complete" — not a claim that a token/step budget specifically was
                        # exceeded; `cross_process_failure_cause` names the real cause.
                        budget_state="halted",
                        realised_budget_share=0.0,
                        cross_process_failure_cause=cause,
                        resumable=False,
                        tokens=TokenAccounting(),
                    )
                )
                partial = True
                stop_reason = stop_reason or f"node {node_id!r}: {cause}"
                # WR-03: deliberately skips ts.done(node_id) — a failed node never calls it. Safe
                # only because node_failures being non-empty forces the unconditional `break`
                # below, so the sorter's now-inconsistent state (this node still "pending" from
                # its own perspective) is never read again via is_active()/get_ready(). A future
                # change that keeps scheduling past a partial batch failure must not rely on this
                # invariant without also fixing ts.done() bookkeeping here.
                continue

            task = tasks[node_id]
            if task.cancelled():
                # Cancelled by TaskGroup because a sibling in this same batch failed — not run,
                # so it gets no trace entry of its own; the batch-level failure above already
                # marks the whole run partial.
                # WR-03: same ts.done()-skip invariant as the node_failures branch above — safe
                # only because node_failures is guaranteed non-empty whenever a sibling triggers
                # cancellation, which forces the unconditional `break` below.
                continue

            # execution_mode is stamped on the trace only via host()'s refusal path today (D-08
            # implements in-process hosting only, so a successful dispatch is always in-process).
            _execution_mode, output, wall_clock_ms = task.result()
            results[node_id] = output
            # CR-01: keyed on the registry's own Part.effects, not the wiring's self-declared
            # WiringNode.effects. The capability-scoped store view above grants access from
            # part.effects, so a wiring that under-declares (parse_wiring permits a narrower
            # subset) would otherwise let a node mutate a store and still be stamped resumable —
            # and (Gap 2 fix) would otherwise let it meter a real LLM/rerank/embedding spend as
            # zero, which is the same bypass class CR-01 already closed for placement and store
            # scoping. meter() is therefore handed part.effects, never node.effects.
            part = parsed.parts[node_id]
            resumable = not (set(part.effects) & _STORE_MUTATING_EFFECTS)
            tokens, cache_hit = _body_report(output)
            token = meter(node_id, part.effects, token_allowances[node_id], tokens)
            guards_fired = evaluate_guards(guards_by_node[node_id], results)
            if token.state == "halted":
                budget_halted = True
                partial = True
                stop_reason = stop_reason or "budget_halt"  # RIG §LC.1's own vocabulary value
            node_traces.append(
                NodeTrace(
                    **_pending_node_trace(node_id, parsed, identities, depths),
                    wall_clock_ms=wall_clock_ms,
                    cache_hit=cache_hit,
                    guards_fired=guards_fired,
                    budget_state=token.state,
                    realised_budget_share=realised_share(token.spent, token.allowance),
                    cross_process_failure_cause=None,  # in-process only, no crossing failed
                    resumable=resumable,
                    tokens=tokens,
                )
            )
            ts.done(node_id)

        if node_failures or budget_halted:
            # Partial outcomes are never discarded (CONTRACT §9) — return what was traced so far
            # rather than continuing to schedule further batches past a batch-internal failure or
            # a budget halt. The already-completed nodes in this same batch (processed above,
            # including the halted one itself) already got their trace and ts.done(node_id); only
            # scheduling of further batches stops here.
            break

    return {
        "results": results,
        "nodes": node_traces,
        "partial": partial,
        "stop_reason": stop_reason,
        "degraded": partial,  # required-together per RIG §TR.3 — see runner/trace.py's own note
        "degradation_reason": stop_reason,
        "node_exceptions": node_exceptions,
    }
