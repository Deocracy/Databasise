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
"""

from __future__ import annotations

import asyncio
import graphlib
import time
from typing import Any

from databasise.identity.canon import config_hash
from databasise.identity.env import environment_hash
from databasise.identity.instance import instance_hash
from databasise.parts.registry import PartRegistry, dispatch
from databasise.parts.schema import NodeContext
from databasise.parts_core import CapabilityScopedStores, UndeclaredEffectError
from databasise.runner.trace import NodeTrace, TokenAccounting
from databasise.validator.depth import effective_depth
from databasise.validator.execution_mode import (
    UnimplementedPlacementError,
    derive_execution_mode,
    host,
)
from databasise.validator.parse import ParsedWiring

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

    def __init__(self, scoped: CapabilityScopedStores, declared_effects: list[str]) -> None:
        self._scoped = scoped
        self._declared_effects = list(declared_effects)

    def __getitem__(self, store_key: str) -> Any:
        for effect in self._declared_effects:
            if effect.split("_", 1)[-1] == store_key:
                return self._scoped.require(effect)
        raise UndeclaredEffectError(f"*_{store_key}", self._declared_effects)


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


async def _run_node(
    node_id: str,
    parsed: ParsedWiring,
    stores: dict[str, Any],
    results: dict[str, Any],
    max_concurrency: int,
) -> tuple[str, Any, int]:
    node = parsed.nodes[node_id]
    part = parsed.parts[node_id]

    execution_mode = derive_execution_mode(part.effects, part.kind)
    try:
        host(execution_mode)  # succeeds for in-process; raises by name for the other three (D-08)
    except UnimplementedPlacementError as exc:
        raise NodePlacementRefusedError(node_id, execution_mode, exc) from exc

    # Per node per run, never shared (D-09/D-11). Not used to gate the outer body call below —
    # CONTRACT §9's V-7 repair treats a node's own internal fan-out as its private
    # implementation detail; the semaphore is exposed to the body (ctx._semaphore) for it to use
    # voluntarily, never enforced by the runner around the single outer call.
    semaphore = asyncio.Semaphore(max_concurrency)

    inputs = {dep: results[dep] for dep in parsed.deps.get(node_id, ())}
    scoped_stores = _ScopedStoresView(CapabilityScopedStores(stores, part.effects), part.effects)
    ctx = NodeContext(node_id=node_id, config=node.config, inputs=inputs, stores=scoped_stores)
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

    Returns a dict always carrying ``results``, ``nodes``, ``partial``, ``stop_reason``,
    ``degraded`` and ``degradation_reason`` — or, for a cyclic wiring, ``{"cycle": [...]}`` as
    data (see module docstring). A pre-flight refusal (empty ``nodes``, any other accumulated
    parse violation, or a declared ``max_concurrency`` below 1) raises before any node is
    dispatched — see module docstring for why that one case raises rather than returning.
    """
    if not parsed.report.ok:
        raise WiringRefusedError(parsed.report.violations)

    if parsed.report.cycles:
        return {"cycle": [sorted(c) for c in parsed.report.cycles]}

    # Pre-flight: every node's max_concurrency is validated before any node is dispatched, so a
    # defect discovered on, say, the fifth node of ten does not leave the first four already run.
    max_concurrencies = {
        node_id: _validated_max_concurrency(node_id, node.config)
        for node_id, node in parsed.nodes.items()
    }

    depths = effective_depth(parsed)
    identities = _resolve_identities(parsed)

    ts = graphlib.TopologicalSorter(dict(parsed.deps))
    ts.prepare()

    results: dict[str, Any] = {}
    node_traces: list[NodeTrace] = []
    partial = False
    stop_reason: str | None = None

    while ts.is_active():
        ready = sorted(ts.get_ready())
        node_failures: dict[str, NodeExecutionError] = {}
        tasks: dict[str, asyncio.Task] = {}
        try:
            async with asyncio.TaskGroup() as tg:
                tasks = {
                    node_id: tg.create_task(
                        _run_node(node_id, parsed, stores, results, max_concurrencies[node_id])
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
                continue

            task = tasks[node_id]
            if task.cancelled():
                # Cancelled by TaskGroup because a sibling in this same batch failed — not run,
                # so it gets no trace entry of its own; the batch-level failure above already
                # marks the whole run partial.
                continue

            # execution_mode is stamped on the trace only via host()'s refusal path today (D-08
            # implements in-process hosting only, so a successful dispatch is always in-process).
            _execution_mode, output, wall_clock_ms = task.result()
            results[node_id] = output
            # CR-01: keyed on the registry's own Part.effects, not the wiring's self-declared
            # WiringNode.effects. The capability-scoped store view above grants access from
            # part.effects, so a wiring that under-declares (parse_wiring permits a narrower
            # subset) would otherwise let a node mutate a store and still be stamped resumable.
            part = parsed.parts[node_id]
            resumable = not (set(part.effects) & _STORE_MUTATING_EFFECTS)
            node_traces.append(
                NodeTrace(
                    **_pending_node_trace(node_id, parsed, identities, depths),
                    wall_clock_ms=wall_clock_ms,
                    cache_hit=False,  # real value: Phase 1 has no cache to hit yet
                    guards_fired=[],  # real value: no data guards declared/fired in this tracer
                    budget_state="within_budget",  # real value: no budget halt occurred
                    realised_budget_share=1.0,  # real value: no budget cap wired into the live
                    # runner path yet (runner/budget.py, this same plan, standalone module —
                    # see 01-08-SUMMARY.md "Known Gaps") — every node ran to completion
                    cross_process_failure_cause=None,  # in-process only, no crossing failed
                    resumable=resumable,
                    tokens=TokenAccounting(),  # real zeros: no LLM/embedding/rerank call metered
                    # into the live path yet — see the same "Known Gaps" note above
                )
            )
            ts.done(node_id)

        if node_failures:
            # Partial outcomes are never discarded (CONTRACT §9) — return what was traced so far
            # rather than continuing to schedule further batches past a batch-internal failure.
            break

    return {
        "results": results,
        "nodes": node_traces,
        "partial": partial,
        "stop_reason": stop_reason,
        "degraded": partial,  # required-together per RIG §TR.3 — see runner/trace.py's own note
        "degradation_reason": stop_reason,
    }
