"""Structured-concurrency runner.

Claude's Discretion (01-02-PLAN.md ``<decisions_recorded_here>``): ``graphlib.TopologicalSorter``
for readiness bookkeeping. No orchestrator, no external scheduler, no metadata DB. **Nodes run one
at a time (D-17).** Each ready batch is sorted by node id (stated tie-break) and dispatched in that
order, one node body in flight at once, so the recorded ``concurrency_setting: sequential`` is true
(bundle@v1's A/A keying, RIG §AA.1). Intra-node concurrency through ``ctx._semaphore`` (below) is
unaffected. The first failed, cancelled or budget-halted node stops the run. **Every node of the
parsed wiring gets exactly one ``NodeTrace`` (D-13):** completed, failed, cancelled, or
not-scheduled for the nodes that never ran (dispatched nodes in dispatch order, then the rest
sorted by node id); recipe-only nodes the caller pruned (D-16) are not in ``parsed`` and get none.

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

**Placement (D-08, D-14).** ``execution_mode`` is derived via
``databasise.validator.execution_mode.derive_execution_mode`` (with ``host()`` and a named
``UnimplementedPlacementError``), the only placement source (the tracer-era copy in
``validator.depth`` is deleted). Every ``NodeTrace`` this module builds carries its node's
``execution_mode`` -- on the success path the placement ``_run_node`` hosted, on the failure path
the refused placement or the one derived from the registered part.

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
it MUST NOT be discarded." Both a placement refusal mid-run (D-08) and a node
failure are therefore surfaced as a **returned**
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
import math
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from databasise.clients import CLIENT_EFFECT_TO_KEY, CapabilityScopedClients
from databasise.foreign.v1_corpus_adapter import redact_secrets
from databasise.identity.canon import config_hash
from databasise.identity.env import environment_hash
from databasise.identity.instance import instance_hash
from databasise.parts.admission import MissingWallClockCeilingError
from databasise.parts.registry import PartRegistry, dispatch
from databasise.parts.schema import NodeContext
from databasise.parts_core import (
    EFFECT_TO_STORE,
    CapabilityScopedStores,
    UndeclaredEffectError,
)
from databasise.runner.budget import meter, realised_share
from databasise.runner.guards import GuardDeclaration, GuardDeclarationError, declare_guard, evaluate_guards
from databasise.runner.trace import (
    DEGRADATION_REASON_FALLBACK_PATH,
    REASON_BUDGET_HALT,
    REASON_CANCELLED,
    REASON_NODE_FAILED,
    REASON_PLACEMENT_REFUSED,
    STOP_REASON_DECLARED_FALLBACK,
    NodeTrace,
    TokenAccounting,
)
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

    def __init__(self, node_id: str, cause: BaseException, *, wall_clock_ms: int = 0):
        self.node_id = node_id
        self.cause = cause
        self.wall_clock_ms = wall_clock_ms  # D-13: measured from the start of dispatch; 0 if never started
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

    The mapping rule (D-09): a subscript key (a store kind, e.g. ``"kv"``) resolves against the
    node's own declared ``effects`` through the explicit ``EFFECT_TO_STORE`` table imported from
    ``databasise.parts_core``. Of the declared effects backed by that store, a write mode wins
    over a read mode whatever the declaration order (``["reads_kv", "writes_kv"]`` gets the
    writable handle), so a read-only node receives the read-only allowlist proxy and a writing
    node the writable one. A store key with no matching declared effect raises
    :class:`UndeclaredEffectError`, exactly as calling ``.require()`` directly with an
    undeclared effect would.

    Threat model (iteration-2 WR-04): the view and the proxies it hands out guard against accidental
    misuse by admitted, in-process parts. The raw stores stay in ordinary attributes
    (``_scoped``, ``_raw_stores``) that hostile code could read; this is not a sandbox.
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
        modes: dict[str, str] = {}
        for effect in self._declared_effects:
            entry = EFFECT_TO_STORE.get(effect)
            if entry is not None and entry[0] == store_key:
                modes.setdefault(entry[1], effect)
        effect = modes.get("w") or modes.get("r")
        if effect is None:
            raise UndeclaredEffectError(f"*_{store_key}", self._declared_effects)
        handle = self._scoped.require(effect)
        if self._recorder is not None:
            self._recorder(self._node_id, TOUCH_KIND_OBSERVED, store_key)
        return handle


class _ScopedClientsView:
    """Wraps :class:`databasise.clients.CapabilityScopedClients` (deny-by-default,
    ``.require(effect)``) so a part body written against plain ``dict``-style subscript access —
    ``ctx.clients["llm"]`` — routes through the underlying deny-by-default check, mirroring
    ``_ScopedStoresView``'s shape for the clients side (D-06).

    The mapping rule matches ``_ScopedStoresView``'s explicit-table rule: a subscript key (a
    client name, e.g. ``"llm"``) resolves against the node's own declared ``effects`` via the
    explicit ``CLIENT_EFFECT_TO_KEY`` dict imported from ``databasise.clients`` — not restated
    here — just as the store side resolves through ``EFFECT_TO_STORE``. A client key with no
    matching declared effect raises :class:`UndeclaredEffectError`, exactly as calling
    ``.require()`` directly with an undeclared effect would.
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
    OR (WR-04, D-07) for any declared value that is not a true ``int`` (a ``bool``, a float, a
    string, a list, a dict, ...), which is never coerced — so the documented "refused at
    validation, before any node is dispatched, naming the offending node id" contract holds for
    malformed input too.
    """
    max_concurrency = 1
    if config:
        raw = config.get("max_concurrency", 1)
        if not isinstance(raw, int) or isinstance(raw, bool):  # D-07: never coerce True, 2.7 or '100'
            raise InvalidMaxConcurrencyError(node_id, raw)
        max_concurrency = raw
    if max_concurrency < 1:
        raise InvalidMaxConcurrencyError(node_id, max_concurrency)
    return max_concurrency


def _validated_token_allowance(node_id: str, config: dict[str, Any] | None) -> int:
    """Extract and validate ``config.token_allowance`` (DEC-A), defaulting to
    ``DEFAULT_TOKEN_ALLOWANCE`` (DEC-B) when absent. Raises :class:`InvalidTokenAllowanceError`,
    naming ``node_id``, for a declared value that is not a true ``int`` (never coerced, D-07), OR
    (WR-01) a negative value — refused at validation, before any node is dispatched, mirroring
    ``_validated_max_concurrency``'s own WR-04-lesson shape for this sibling field.
    """
    raw = DEFAULT_TOKEN_ALLOWANCE
    if config:
        raw = config.get("token_allowance", DEFAULT_TOKEN_ALLOWANCE)
    if not isinstance(raw, int) or isinstance(raw, bool):  # D-07: never coerce True, 0.9 or '100'
        raise InvalidTokenAllowanceError(node_id, raw)
    allowance = raw
    if allowance < 0:
        raise InvalidTokenAllowanceError(node_id, allowance)
    return allowance


def _dependency_closure(node_id: str, deps: Mapping[str, Any]) -> set[str]:
    """``node_id`` plus every transitive dependency of it, over ``deps``."""
    seen: set[str] = set()
    pending = [node_id]
    while pending:
        current = pending.pop()
        if current not in seen:
            seen.add(current)
            pending.extend(deps.get(current, ()))
    return seen


def _validated_guards(
    node_id: str, config: dict[str, Any] | None, parsed: ParsedWiring
) -> list[GuardDeclaration]:
    """``config.guards`` (absent or falsy -> ``[]``) for ``node_id``, each entry constructed via
    ``declare_guard(**entry)``. A malformed declaration refuses the run before any node is
    dispatched (the same pre-flight contract as ``max_concurrency`` and ``token_allowance``) with a
    :class:`~databasise.runner.guards.GuardDeclarationError` carrying ``node_id`` (WIRE-08, D-19):
    an entry that is not a mapping, one with missing or extra keys, an inadmissible granularity, or
    an ``evaluating_node`` that is neither ``node_id`` nor in its transitive dependency closure
    over ``parsed.deps`` (the pruned wiring the engine runs), because only those outputs exist when
    the guard is evaluated.
    """
    raw_guards = (config or {}).get("guards") or []
    if not isinstance(raw_guards, list):  # 13 REVIEW B-WR-02: named, never a bare TypeError
        raise GuardDeclarationError(
            str(raw_guards), None, node_id=node_id, problem="config.guards must be a list of guard entries"
        )
    reachable = _dependency_closure(node_id, parsed.deps)
    guards: list[GuardDeclaration] = []
    for entry in raw_guards:
        if not isinstance(entry, Mapping):
            raise GuardDeclarationError(
                str(entry), None, node_id=node_id, problem="a guard entry must be a mapping"
            )
        try:
            guard = declare_guard(**entry)
        except TypeError:
            raise GuardDeclarationError(
                str(entry.get("name")),
                entry.get("granularity"),
                node_id=node_id,
                problem=f"guard entry keys {sorted(map(str, entry))} must be exactly "
                "name, evaluating_node, value_when_not_fired, granularity and signal",
            ) from None
        except GuardDeclarationError as exc:
            exc.node_id = node_id
            raise
        if guard.evaluating_node not in reachable:
            raise GuardDeclarationError(
                guard.name,
                guard.granularity,
                node_id=node_id,
                problem=f"guard {guard.name!r} evaluates {guard.evaluating_node!r}, which is neither "
                "the guarded node nor one of its dependencies",
            )
        guards.append(guard)
    return guards


def _body_report(output: Any) -> tuple[TokenAccounting, bool | None]:
    """The body's own self-reported ``TokenAccounting`` and cache-hit flag, read from its return
    value rather than assumed. When ``output`` is a ``Mapping`` and ``output.get("tokens")`` is
    genuinely a ``TokenAccounting`` instance, that object is returned as-is (the body owns it — no
    deep copy); otherwise a fresh, all-zero ``TokenAccounting()`` is returned. ``cache_hit`` is the
    mapping's own ``cache_hit`` only when it is a ``bool``; anything else (absent, or ``output`` not
    a ``Mapping``) is ``None`` — a part that reported no cache flag is not guessed to have missed
    (D-14). Guarded with ``isinstance`` on both checks — a body returning a list, a string, or
    ``None`` must not raise here.
    """
    cache_hit: bool | None = None
    if isinstance(output, Mapping):
        tokens = output.get("tokens")
        if not isinstance(tokens, TokenAccounting):
            tokens = TokenAccounting()
        reported = output.get("cache_hit")
        if isinstance(reported, bool):
            cache_hit = reported
    else:
        tokens = TokenAccounting()
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
        # ceil, so a sub-millisecond failure is not silently floored to a "never ran" 0
        elapsed_ms = math.ceil((time.monotonic() - start) * 1000)
        raise NodeExecutionError(node_id, exc, wall_clock_ms=elapsed_ms) from exc
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


@dataclass
class _NodeOutcome:
    """One dispatched node's trace and what the run does next (D-13)."""

    trace: NodeTrace
    completed: bool
    exception: BaseException | None = None
    stop_reason: str | None = None  # set when the run stops after this node


async def _dispatch_node(
    node_id: str,
    parsed: ParsedWiring,
    stores: dict[str, Any],
    results: dict[str, Any],
    max_concurrency: int,
    clients: dict[str, Any] | None,
    recorder: TouchRecorder | None,
    *,
    identities: dict,
    depths: dict,
    allowance: int,
    guards: list[GuardDeclaration],
) -> _NodeOutcome:
    """Dispatch one node and return its trace; nothing a node or a post-dispatch step does is
    raised (D-13), except a real cancellation of the run itself (D-26).
    """
    part = parsed.parts[node_id]
    started = time.monotonic()

    def _stopped_trace(
        status: str,
        execution_mode: str,
        wall_clock_ms: int,
        cause: str | None,
        budget_state: str,
        spent: int | None = None,
        tokens: TokenAccounting | None = None,
    ) -> NodeTrace:
        return NodeTrace(
            **_pending_node_trace(node_id, parsed, identities, depths),
            execution_mode=execution_mode,
            status=status,
            allowance=allowance,
            spent=spent,  # None unless the body completed and was metered before a later step failed
            wall_clock_ms=wall_clock_ms,
            cache_hit=None,
            guards_fired=[],
            budget_state=budget_state,
            realised_budget_share=0.0,
            cross_process_failure_cause=cause,
            resumable=False,
            tokens=tokens if tokens is not None else TokenAccounting(),
        )

    try:
        execution_mode, output, wall_clock_ms = await _run_node(
            node_id, parsed, stores, results, max_concurrency, clients, recorder
        )
    except NodeExecutionError as exc:
        placement = getattr(exc, "placement", None)
        cause = (
            f"NodePlacementRefusedError: execution_mode={placement!r} not hosted (D-08)"
            if placement is not None
            else f"NodeExecutionError: {type(exc.cause).__name__}: {redact_secrets(str(exc.cause))}"
        )
        # A refusal does not suppress the stamp (D-08): the refused placement when there is one,
        # else the placement derived from the registered part. "halted" is the closest of the
        # schema's budget_state values to "did not complete"; the cause names the real reason.
        trace = _stopped_trace(
            "failed",
            placement or derive_execution_mode(part.effects, part.kind),
            exc.wall_clock_ms,
            cause,
            "halted",
        )
        # D-05: the consumer-visible reason is a closed code; the node text stays in the trace.
        reason = REASON_NODE_FAILED if placement is None else REASON_PLACEMENT_REFUSED
        return _NodeOutcome(trace, False, exc.cause, reason)
    except asyncio.CancelledError:
        # D-26: a body that raises CancelledError while the run itself is not being cancelled is
        # traced; a real cancellation of the run propagates.
        current = asyncio.current_task()
        if current is not None and current.cancelling():
            raise
        elapsed_ms = math.ceil((time.monotonic() - started) * 1000)
        mode = derive_execution_mode(part.effects, part.kind)
        trace = _stopped_trace("cancelled", mode, elapsed_ms, None, "within_budget")
        return _NodeOutcome(trace, False, None, REASON_CANCELLED)

    results[node_id] = output
    try:
        # CR-01: keyed on the registry's own Part.effects, not the wiring's self-declared
        # WiringNode.effects. The capability-scoped store view above grants access from
        # part.effects, so a wiring that under-declares (parse_wiring permits a narrower
        # subset) would otherwise let a node mutate a store and still be stamped resumable —
        # and (Gap 2 fix) would otherwise let it meter a real LLM/rerank/embedding spend as
        # zero, which is the same bypass class CR-01 already closed for placement and store
        # scoping. meter() is therefore handed part.effects, never node.effects.
        resumable = not (set(part.effects) & _STORE_MUTATING_EFFECTS)
        token = None
        tokens, cache_hit = _body_report(output)
        token = meter(node_id, part.effects, allowance, tokens)
        guards_fired = evaluate_guards(guards, results)
        trace = NodeTrace(
            **_pending_node_trace(node_id, parsed, identities, depths),
            execution_mode=execution_mode,
            spent=token.spent,
            allowance=token.allowance,
            wall_clock_ms=wall_clock_ms,
            cache_hit=cache_hit,
            guards_fired=guards_fired,
            budget_state=token.state,
            realised_budget_share=realised_share(token.spent, token.allowance),
            cross_process_failure_cause=None,  # the node completed, so no crossing failed
            resumable=resumable,
            tokens=tokens,
        )
    except Exception as exc:  # noqa: BLE001 - any post-dispatch failure is recorded against the node
        # D-13: a bad report, a malformed token count, a guard comparison that raises: recorded
        # against this node, which no longer counts as having produced a result.
        results.pop(node_id, None)
        cause = f"NodeExecutionError: {type(exc).__name__}: {redact_secrets(str(exc))}"
        # 13 REVIEW B-WR-03 (CONTRACT §9): spend already reported and metered stays on the node.
        trace = _stopped_trace(
            "failed",
            execution_mode,
            wall_clock_ms,
            cause,
            "halted",
            spent=token.spent if token is not None else None,
            tokens=tokens if token is not None else None,  # a report meter() refused is not carried
        )
        return _NodeOutcome(trace, False, exc, REASON_NODE_FAILED)
    return _NodeOutcome(trace, True, None, REASON_BUDGET_HALT if token.state == "halted" else None)


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
    and its nodes are dispatched one at a time in that order (D-17 — see module docstring). The
    first failure or budget halt stops the run; nodes that never ran get ``not-scheduled`` traces.

    ``registry`` is accepted for signature parity with the rest of this phase's call sites; every
    part this function dispatches is already resolved via ``parsed.parts`` by
    ``validator.parse.parse_wiring``, so the registry itself is not re-queried during execution.
    ``determinism_setting``/``concurrency_setting`` are echoed unchanged in the result so the
    run-level record stamps what the run was given (D-17).
    ``clients`` (D-06) defaults to ``None`` — treated identically to an empty dict — so a run that
    passes no ``clients`` argument at all behaves exactly as before for every existing part.
    ``recorder`` (D-15) defaults to ``None`` — a run that passes none behaves exactly as before;
    see module docstring's "Optional per-node touch recording" paragraph.

    Returns a dict always carrying ``results``, ``nodes``, ``partial``, ``stop_reason``,
    ``degraded``, ``degradation_reason``, ``determinism_setting``, ``concurrency_setting`` and
    ``node_exceptions`` (05-01-PLAN.md: the real
    underlying exception object a failed node's dispatch raised, keyed by node_id — additive,
    empty for a clean run) — or, for a cyclic wiring, ``{"cycle": [...]}`` as data (see module
    docstring; the seam refuses a cyclic wiring earlier, so this return is a runner-level contract
    only).

    Raises, before any node is dispatched (WIRE-05; the seam translates each to a named refusal):

    - :class:`WiringRefusedError` when ``parsed.report`` carries any violation (an empty ``nodes``
      object, an unknown component, a dangling dependency, ...);
    - :class:`InvalidMaxConcurrencyError` or :class:`InvalidTokenAllowanceError` for a declared
      ``max_concurrency`` / ``token_allowance`` that is not a true ``int`` (a ``bool``, float or
      string is never coerced), a ``max_concurrency`` below 1, or a negative ``token_allowance``;
    - :class:`~databasise.runner.guards.GuardDeclarationError` (with ``node_id``) for a misdeclared
      guard: an entry that is not a mapping, has missing or extra keys or an inadmissible
      granularity, or names an ``evaluating_node`` that is neither the guarded node nor one of its
      transitive dependencies;
    - :class:`~databasise.identity.env.EnvironmentDigestError` when the environment digest cannot
      be computed.
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
        node_id: _validated_guards(node_id, node.config, parsed) for node_id, node in parsed.nodes.items()
    }

    depths = effective_depth(parsed)
    identities = _resolve_identities(parsed)

    ts = graphlib.TopologicalSorter(dict(parsed.deps))
    ts.prepare()

    results: dict[str, Any] = {}
    node_traces: list[NodeTrace] = []
    partial = False
    stop_reason: str | None = None
    # 05-01-PLAN.md Task 1: the real underlying exception a failed node's dispatch raised (e.g. a
    # CorpusOpTimeoutError/CorpusOpSubprocessError from an opaque node's subprocess body), keyed by
    # node_id — additive to the returned dict. CONTRACT §9's "partial outcomes are never discarded"
    # rule means a per-node dispatch failure never propagates out of this function (see module
    # docstring); a caller that needs the *real* exception object (not merely its stringified
    # ``cross_process_failure_cause``) to build its own typed refusal reads it from here rather
    # than parsing NodeTrace's own prose string.
    node_exceptions: dict[str, BaseException] = {}

    # D-17: one node at a time, in sorted node-id order within each ready batch, so the recorded
    # ``concurrency_setting: sequential`` is true. The first failure or budget halt stops the run;
    # every node that never ran gets a not-scheduled trace below.
    while ts.is_active() and not partial:
        for node_id in sorted(ts.get_ready()):
            outcome = await _dispatch_node(
                node_id,
                parsed,
                stores,
                results,
                max_concurrencies[node_id],
                clients,
                recorder,
                identities=identities,
                depths=depths,
                allowance=token_allowances[node_id],
                guards=guards_by_node[node_id],
            )
            node_traces.append(outcome.trace)
            if outcome.exception is not None:
                node_exceptions[node_id] = outcome.exception
            if outcome.completed:
                ts.done(node_id)
            if outcome.stop_reason is not None:
                partial = True
                stop_reason = outcome.stop_reason
                break  # the sorter is never read again, so a skipped ts.done() is safe

    # D-13: one trace per node of the parsed wiring. Nodes that never ran follow the dispatched
    # ones, sorted by node id.
    traced = {trace.node_id for trace in node_traces}
    for node_id in sorted(parsed.nodes.keys() - traced):
        part = parsed.parts[node_id]
        node_traces.append(
            NodeTrace(
                **_pending_node_trace(node_id, parsed, identities, depths),
                execution_mode=derive_execution_mode(part.effects, part.kind),
                status="not-scheduled",
                allowance=token_allowances[node_id],
                spent=None,
                wall_clock_ms=0,
                cache_hit=None,
                guards_fired=[],
                budget_state="within_budget",
                realised_budget_share=0.0,
                cross_process_failure_cause=None,
                resumable=False,
                tokens=TokenAccounting(),
            )
        )

    # D-21: a completed run whose guard fired took a declared degradation path -- degraded without
    # being partial. A partial run keeps its own stop_reason as the degradation_reason.
    degraded = partial or any(trace.guards_fired for trace in node_traces)
    if degraded and not partial:
        stop_reason = STOP_REASON_DECLARED_FALLBACK
        degradation_reason: str | None = DEGRADATION_REASON_FALLBACK_PATH
    else:
        degradation_reason = stop_reason
    return {
        "results": results,
        "nodes": node_traces,
        "partial": partial,
        "stop_reason": stop_reason,
        "degraded": degraded,
        "degradation_reason": degradation_reason,
        "node_exceptions": node_exceptions,
        "determinism_setting": determinism_setting,
        "concurrency_setting": concurrency_setting,
    }
