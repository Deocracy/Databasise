"""``hipporag/result-assembler`` (HippoRAG 2 base wiring position ``assemble-result``,
PARTS.md ``## §H``) — selects the guard-chosen branch's items, hydrates each one's chunk text and
assembles the final context. Ported by search from ``hipporag/HippoRAG.py:501-507``.

Hydrates the selected items' chunk text from ``ctx.stores["kv"]`` (this node's own ``reads_kv``
effect), keyed by each item's own ``id`` — the same graph vertex name / chunk id the fixture and
``ppr``'s own readback share. Orders by ``config["order_policy"]``'s declared value
(``"hipporag-doc-score-order"``) — which, at this position, IS the selected branch's own emitted
order (descending by score); this node performs no independent re-sort, since re-sorting an
already score-ordered input would silently discard the very ordering ``order_policy`` names.

**The §19.8 guard selection (06-07-PLAN.md Task 2).** This node's own ``deps`` are
``["ppr", "dpr-fallback", "fact-filter"]`` — a documented, deliberate divergence from the
illustrative ``docs/system-model/wirings/hipporag-base.json``'s ``["ppr", "dpr-fallback"]`` (see
``databasise/evidence/HIPPORAG-PORT-RECORD.md``): ``fact-filter`` is added so this node can read
the guard's own outcome (``guard_fired``) from ``ctx.inputs["fact-filter"]`` — the sanctioned
control channel — rather than resolving the run record mid-run, which is exactly what §11's
control-channel-is-a-read rule forbids. ``ppr`` and ``dpr-fallback`` both run unconditionally
(neither reads the guard itself); this node is where the choice is made: ``ppr``'s items when the
guard did not fire, ``dpr-fallback``'s when it did.

**Observability, resolved (06-07-PLAN.md Task 2).** ``## §H``'s ``Arms:`` field states the guard's
firing is observable per query through §18.2's existing envelope machinery, with no new field
minted. ``runner/trace.py``'s honesty invariant makes ``degraded`` unusable for this purpose —
``degraded``/``partial`` are a required-together pair naming an unhealthy run, and ``RunRecord``
refuses a record where they disagree, so labelling a completed guarded run ``degraded`` would
either be refused outright or make a real degradation indistinguishable from an ordinary declared
fallback. The channel actually used is the run record's own per-node ``guards_fired`` field (RIG
§TR.1, already stamped by the scheduler), reached by a caller through the envelope's existing
``trace_token`` -> ``resolve_trace`` path — satisfying "no new envelope field is minted" exactly.

**Named limitation, per 06-01-PLAN.md's own instruction:** HippoRAG 2's base wiring has no
generator position among its thirteen (PARTS.md ``## §H``) — ``completion`` therefore carries
assembled context (the hydrated chunk texts, joined), never a generated answer. This is a content
difference at the envelope's ``answer`` field, not an envelope-field difference; plan 06-03 records
it against F-14.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "hipporag/result-assembler@0.1.0"


async def _assemble_result_body(ctx: NodeContext) -> dict[str, Any]:
    fact_filter_output = ctx.inputs["fact-filter"]
    guard_fired = bool(fact_filter_output.get("guard_fired", False))

    selected_output = ctx.inputs["dpr-fallback"] if guard_fired else ctx.inputs["ppr"]
    selected_items = list(selected_output.get("items", []))

    kv_store = ctx.stores["kv"]
    hydrated_items: list[dict[str, Any]] = []
    contents: list[str] = []
    for item in selected_items:
        record = await kv_store.get_by_id(str(item["id"]))
        content = str((record or {}).get("content", ""))
        hydrated_items.append({**item, "content": content})
        if content:
            contents.append(content)

    return {"items": hydrated_items, "completion": "\n\n".join(contents)}


HIPPORAG_RESULT_ASSEMBLER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="assembler",
    structural_depth="opaque",
    effects=["reads_kv"],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_assemble_result_body,
)
