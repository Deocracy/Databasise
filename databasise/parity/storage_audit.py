"""D-15's per-node storage-ownership audit (03-08-PLAN.md Task 1, CONTRACT §19's criterion 3):
drives a named arm through the same store/client assembly ``databasise/parity/run_arm.py`` uses,
with per-node touch recording enabled, then cross-checks each resolved node's recorded (store,
client) touches against that node's resolved ``Part.effects``, reporting one row per node with a
state of ``matched``, ``no-touch``, or ``over-declared``.

Deliberately reuses ``databasise.parity.run_arm``'s own underscore-prefixed store/client/env
helpers (``_build_stores``, ``_build_clients``, ``_load_env_file``, ``_inject_query``,
``_inject_token_allowance``) rather than calling ``run_arm.run_arm()`` as a black box: that public
entry point does not accept a touch recorder, and ``run_arm.py`` is not this plan's file to modify
(03-08-PLAN.md's own ``files_modified`` list). Reusing its helpers directly mirrors the precedent
``run_arm.py`` itself already set (``from databasise.parity.import_index import _import_workspace
as _parity_workspace``) for exactly this same cross-module-reuse-within-one-package shape.

Follows ``databasise/tools/check_import_boundary.py``'s own reporting convention: collect
``Violation``-shaped records, print one line each, exit 1 if any exist, exit 0 clean. A
``Violation`` here is a recorded touch with no corresponding declared handle — structurally
impossible given ``CapabilityScopedStores.require``/``CapabilityScopedClients.require``'s own
refuse-before-returning-a-handle guarantee (proven directly, not merely asserted, by
``databasise/tests/parity/test_storage_audit.py``'s own scheduler-level case), so a ``Violation``
here signals a bug in this audit's own bookkeeping, never the run's own correctness.

``matched``/``no-touch``/``over-declared`` are never refusals — they are the audit's three
legitimate per-node states, reported and counted separately in the summary line, never folded into
one pass/fail bit. §19.9's fallback-reachability rule makes some over-declaration correct by
design: ``rerank`` declares ``calls_rerank`` while configured as a pass-through (the published
naive arm sets no ``live_rerank``), and ``chunk-sel-kg`` declares ``reads_vector`` on a
weight-only configuration — both nodes correctly report as ``no-touch``/``over-declared``
respectively rather than being refused for under-using a capability their own contract entitles
them to hold in reserve.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from typing import Any

from databasise.clients import CLIENT_EFFECT_TO_KEY
from databasise.parity import run_arm as _run_arm
from databasise.parity.import_index import DEFAULT_STORE_ROOT
from databasise.parts.registry import PartRegistry, default_registry
from databasise.runner import scheduler as _scheduler
from databasise.runner.scheduler import TouchRecorder
from databasise.validator.parse import ParsedWiring, parse_wiring
from databasise.wirings.resolve import resolve_arm

_DEFAULT_QUERY = "storage-audit probe query"


@dataclass(frozen=True)
class Violation:
    """A recorded touch with no corresponding declared handle on that node — see module
    docstring: structurally impossible given the scheduler's own deny-by-default enforcement, so
    a Violation here signals an audit bookkeeping bug, never the run's own correctness.
    """

    node_id: str
    reference: str  # e.g. "store:vector" — the touched-but-undeclared handle


@dataclass(frozen=True)
class AuditRow:
    """One node's computed touch-vs-declaration row. ``touched``/``unused_effects`` are rendered
    as ``"<kind>:<key>"`` strings (e.g. ``"store:kv"``, ``"client:embedding"``) — the same handle
    shape ``_declared_handles`` computes.
    """

    node_id: str
    component: str
    declared_effects: tuple[str, ...]
    touched: tuple[str, ...]
    state: str  # "matched" | "no-touch" | "over-declared"
    unused_effects: tuple[str, ...]  # non-empty only when state == "over-declared"


def _declared_handles(effects: list[str]) -> frozenset[tuple[str, str]]:
    """Every ``(kind, key)`` handle ``effects`` permits, mirroring
    ``runner/scheduler.py``'s own ``_ScopedStoresView``/``_ScopedClientsView`` mapping rules
    exactly — a client-shaped effect maps through ``CLIENT_EFFECT_TO_KEY``, every other effect
    maps through the store side's own ``effect.split("_", 1)[-1]`` suffix rule. Never re-derived
    independently: this is the same computation the scheduler's own dispatch path performs on
    every ``ctx.stores[...]``/``ctx.clients[...]`` access.
    """
    handles: set[tuple[str, str]] = set()
    for effect in effects:
        if effect in CLIENT_EFFECT_TO_KEY:
            handles.add(("client", CLIENT_EFFECT_TO_KEY[effect]))
        else:
            handles.add(("store", effect.split("_", 1)[-1]))
    return frozenset(handles)


def _handle_str(handle: tuple[str, str]) -> str:
    kind, key = handle
    return f"{kind}:{key}"


def audit_run(
    parsed: ParsedWiring, touches: list[tuple[str, str, str]]
) -> tuple[list[AuditRow], list[Violation]]:
    """Cross-check every node in ``parsed.node_order`` against the touches a
    :data:`~databasise.runner.scheduler.TouchRecorder` collected during one real run.

    A node declaring no store/client-shaped effect at all (a pure transform, e.g. a join or
    truncator node) has nothing to own and is reported ``matched`` vacuously — the storage-
    ownership question this audit answers does not apply to it. Otherwise: no touches at all is
    ``no-touch``; every declared handle touched is ``matched``; some but not all declared handles
    touched is ``over-declared``, naming the unused ones. A touch outside the node's own declared
    handles cannot occur through the real scheduler path (proven separately, see module
    docstring) but is still checked for defensively and reported as a :class:`Violation`.
    """
    touched_by_node: dict[str, set[tuple[str, str]]] = {}
    for node_id, kind, key in touches:
        touched_by_node.setdefault(node_id, set()).add((kind, key))

    rows: list[AuditRow] = []
    violations: list[Violation] = []
    for node_id in parsed.node_order:
        part = parsed.parts[node_id]
        declared = _declared_handles(part.effects)
        touched = touched_by_node.get(node_id, set())

        undeclared = touched - declared
        for handle in sorted(undeclared):
            violations.append(Violation(node_id, _handle_str(handle)))

        if not declared:
            state, unused = "matched", frozenset()
        elif not touched:
            state, unused = "no-touch", frozenset()
        elif touched == declared:
            state, unused = "matched", frozenset()
        else:
            state, unused = "over-declared", declared - touched

        rows.append(
            AuditRow(
                node_id=node_id,
                component=part.name_at_version,
                declared_effects=tuple(sorted(part.effects)),
                touched=tuple(sorted(_handle_str(h) for h in touched)),
                state=state,
                unused_effects=tuple(sorted(_handle_str(h) for h in unused)),
            )
        )
    return rows, violations


async def run_audit(
    arm_name: str,
    query: str = _DEFAULT_QUERY,
    *,
    registry: PartRegistry | None = None,
    store_root: Any = None,
    workspace: str | None = None,
    clients: dict[str, Any] | None = None,
    env_path: Any = None,
    token_allowance: int = _run_arm._DEFAULT_TOKEN_ALLOWANCE,
) -> dict[str, Any]:
    """Resolve ``arm_name`` exactly as ``run_arm.run_arm`` does, but drive
    ``runner.scheduler.run_wiring`` with recording enabled and return the audit's rows/violations
    instead of a run record. ``clients``/``store_root``/``workspace``/``env_path`` are the same
    test override points ``run_arm.run_arm`` exposes, for the identical reason: a test can drive
    this whole function with a stub client double and a synthetic store — no network, no real
    index, runs on any machine.
    """
    if registry is None:
        registry = default_registry()

    resolved = resolve_arm(arm_name)
    resolved = _run_arm._inject_query(resolved, query)
    resolved = _run_arm._inject_token_allowance(resolved, token_allowance)
    parsed = parse_wiring(resolved, registry)

    resolved_workspace = workspace if workspace is not None else _run_arm._parity_workspace()
    resolved_store_root = store_root if store_root is not None else DEFAULT_STORE_ROOT
    stores = _run_arm._build_stores(resolved_store_root, resolved_workspace)

    resolved_clients = clients
    if resolved_clients is None:
        env = _run_arm._load_env_file(env_path or _run_arm.DEFAULT_V1_ENV_PARITY)
        resolved_clients = _run_arm._build_clients(env)

    touches: list[tuple[str, str, str]] = []

    def recorder(node_id: str, kind: str, key: str) -> None:
        touches.append((node_id, kind, key))

    try:
        scheduled = await _scheduler.run_wiring(
            parsed,
            registry,
            stores,
            determinism_setting=_run_arm._DETERMINISM_SETTING,
            concurrency_setting=_run_arm._CONCURRENCY_SETTING,
            clients=resolved_clients,
            recorder=recorder,
        )
    finally:
        for store in stores.values():
            await store.finalize()

    if "cycle" in scheduled:
        return {"cycle": scheduled["cycle"], "rows": [], "violations": [], "partial": False}

    rows, violations = audit_run(parsed, touches)
    return {"rows": rows, "violations": violations, "partial": scheduled["partial"]}


def _render_row(row: AuditRow) -> str:
    unused = f" unused={list(row.unused_effects)}" if row.unused_effects else ""
    return (
        f"{row.node_id} [{row.component}] state={row.state} "
        f"declared={list(row.declared_effects)} touched={list(row.touched)}{unused}"
    )


def _render_summary(rows: list[AuditRow]) -> str:
    counts = {"matched": 0, "no-touch": 0, "over-declared": 0}
    for row in rows:
        counts[row.state] += 1
    return (
        f"summary: {len(rows)} node(s) — matched={counts['matched']} "
        f"no-touch={counts['no-touch']} over-declared={counts['over-declared']}"
    )


def main(argv: list[str] | None = None) -> int:
    """``uv run python -m databasise.parity.storage_audit --arm naive`` — prints one row per
    resolved node plus a three-way summary line, following ``check_import_boundary.py``'s own
    clean-exit-0/violations-exit-1 convention (see module docstring).
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", required=True, choices=["naive", "bypass", "hybrid", "local", "global"])
    parser.add_argument("--query", default=_DEFAULT_QUERY)
    args = parser.parse_args(argv)

    try:
        result = asyncio.run(run_audit(args.arm, args.query))
    except _run_arm.MissingParityEnvError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    rows: list[AuditRow] = result["rows"]
    violations: list[Violation] = result["violations"]

    for row in rows:
        print(_render_row(row))
    print(_render_summary(rows))

    if violations:
        for v in violations:
            print(f"VIOLATION: {v.node_id}: {v.reference}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
