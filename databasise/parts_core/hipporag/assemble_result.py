"""``hipporag/result-assembler`` (HippoRAG 2 base wiring position ``assemble-result``,
PARTS.md ``## §H``) — selects the guard-chosen branch's items, hydrates each one's chunk text and
assembles the final context. Ported by search from ``hipporag/HippoRAG.py:501-507``.

Hydrates the selected items' chunk text from ``ctx.stores["kv"]`` (this node's own ``reads_kv``
effect), keyed by each item's own ``id`` — the bare chunk id ``chunk-embed`` writes and ``ppr`` emits. The
order is the selected branch's own emitted order (descending by score); this node performs no
independent re-sort.

**The §19.8 guard selection (06-07-PLAN.md Task 2).** This node's own ``deps`` are
``["ppr", "dpr-fallback", "fact-filter"]`` — a documented, deliberate divergence from the
illustrative ``docs/system-model/wirings/hipporag-base.json``'s ``["ppr", "dpr-fallback"]`` (see
``databasise/evidence/HIPPORAG-PORT-RECORD.md``): ``fact-filter`` is added so this node can read
the guard's own outcome (``guard_fired``) from ``ctx.inputs["fact-filter"]`` — the sanctioned
control channel — rather than resolving the run record mid-run, which is exactly what §11's
control-channel-is-a-read rule forbids. ``ppr`` and ``dpr-fallback`` both run unconditionally
(neither reads the guard itself); this node is where the choice is made: ``ppr``'s items when the
guard did not fire, ``dpr-fallback``'s when it did.

**Observability (D-21).** A fired guard makes the run ``degraded`` (``partial`` stays false) with the
node-free reason codes the scheduler stamps (``declared_fallback`` / ``fallback_path_taken``); the
per-node ``guards_fired`` field stays in the debug trace. This node only selects the branch.

**The one cut (Phase 12 D-20, HIPP-11).** After branch selection and before hydration this node keeps
the first ``config["top_k"]`` items (default 5, upstream ``qa_top_k``) of the selected branch, in
that branch's own order. On the PPR branch items scoring ``<= 0`` are dropped first; if none is
left, ``dpr-fallback``'s items stand in. That is a declared degradation (A-WR-05, D-21): the output
carries ``dpr_stand_in`` and ``base.json`` declares the ``empty_ppr_dpr_stand_in`` guard on this
node, so the scheduler reports the node's ``guards_fired`` and the run ``degraded`` with the
node-free ``declared_fallback`` / ``fallback_path_taken`` codes. The one cut
bounds both the answer (``qa`` reads these items) and the evidence (minted from them) on both
branches; dense passage retrieval itself is never cut, since ``reset-vector-join`` reuses it whole.

This node emits no ``completion``: the ``qa`` node (Phase 12 D-19) generates the answer from these
hydrated items; evidence still mints from this node's items.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part
from databasise.parts_core.hipporag.fact_filter import _GuardAwareResult

_NAME_AT_VERSION = "hipporag/result-assembler@0.1.0"


class _StandInResult(_GuardAwareResult):
    """The output, comparable to a bool sentinel through ``dpr_stand_in`` so the
    ``empty_ppr_dpr_stand_in`` guard in ``base.json`` can read it (same protocol as fact-filter's)."""

    _flag = "dpr_stand_in"


async def _assemble_result_body(ctx: NodeContext) -> dict[str, Any]:
    fact_filter_output = ctx.inputs["fact-filter"]
    guard_fired = bool(fact_filter_output.get("guard_fired", False))

    selected_output = ctx.inputs["dpr-fallback"] if guard_fired else ctx.inputs["ppr"]
    selected_items = list(selected_output.get("items", []))
    dpr_stand_in = False
    if not guard_fired:
        # An item PPR never reached scores exactly 0.0; it carries no evidence.
        selected_items = [item for item in selected_items if item["score"] > 0.0]
        if not selected_items:
            # A-WR-02: PPR reached nothing (all-zero reset, e.g. a one-chunk corpus), so the dense
            # items dpr-fallback computed in the same run answer, not an empty result.
            selected_items = list(ctx.inputs["dpr-fallback"].get("items", []))
            dpr_stand_in = bool(selected_items)
    top_k = int((ctx.config or {}).get("top_k", 5))
    if top_k < 1:  # A-WR-01: a negative cut would silently drop the last item
        raise ValueError(f"{ctx.node_id!r}: config.top_k must be >= 1, got {top_k}")
    selected_items = selected_items[:top_k]

    kv_store = ctx.stores["kv"]
    hydrated_items: list[dict[str, Any]] = []
    for item in selected_items:
        record = await kv_store.get_by_id(str(item["id"]))
        hydrated_items.append({**item, "content": str((record or {}).get("content", ""))})

    return _StandInResult(items=hydrated_items, dpr_stand_in=dpr_stand_in)


HIPPORAG_RESULT_ASSEMBLER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="assembler",
    structural_depth="opaque",
    effects=["reads_kv"],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_assemble_result_body,
)
