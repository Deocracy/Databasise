"""D-10's run-record field stamping: ``RunRecord``, ``NodeTrace`` and ``TokenAccounting``
dataclasses matching ``docs/system-model/rig-trace.schema.json`` exactly. The two sentinel
constants below (``BUNDLE_REF_SENTINEL``, ``CORPUS_SNAPSHOT_HASH_SENTINEL``) are the ONLY
sentinel-carrying fields this module emits; every other field carries a real, computed value.

Placeholder policy (explicitly marked, per this plan's own instructions): ``bundle_ref`` and
``corpus_snapshot_hash`` have no real eval bundle until Phase 2 (RIG-02's own bundle machinery),
so they carry the documented sentinel strings below rather than omitting the field and failing
the schema. ``tier``/``feed_tier`` likewise carry a documented ``T3`` placeholder for nodes that
never handle a scored evidence item — Phase 2 names the real evidence-tier mechanism. Every other
field (``arm_execution_order``, ``cache_hit``, ``guards_fired``, ``realised_budget_share``,
``determinism_setting``, ``concurrency_setting``) is a real value computed by this commit, per
D-10 — not a placeholder.

**The honesty invariant (D-10, this plan's Task 3).** RIG.md §TR.3, quoted directly: "A run that
halted, ran partially, or ran degraded records ``stop_reason``, ``partial``, ``degraded`` and
``degradation_reason`` as a **required-together set**, never independently optional." The frozen
schema's own ``allOf``/``if``-``then`` rule enforces exactly this: a truthy ``partial`` requires
BOTH a non-empty ``stop_reason`` AND a non-empty ``degradation_reason``, and a truthy ``degraded``
requires the same pair — the schema does not treat ``partial`` and ``degraded`` as two
independently-triggerable flags with their own field requirements; a run that is partial without
being degraded (or vice versa) has no representable shape at all under the schema's own allOf
rule, since either flag alone already demands both reason fields. ``RunRecord.__post_init__``
below therefore refuses to construct any record where ``partial`` and ``degraded`` disagree, or
where either is true without both reason fields populated, or where either is false while a
reason field is populated — resolving what would otherwise read as three independent conditions
(the plan's own action text) into one required-together check, grounded directly in the schema's
own allOf clause and RIG.md §TR.3's own explicit "required-together set" wording, not invented
here. A node whose own ``budget_state`` is ``"halted"`` while the run reports ``partial=False`` is
refused for the same reason — CONTRACT §9's own rule that a budget-halted run "MUST be traced ...
exactly as a completed run is; it MUST NOT be discarded" presupposes the run is honestly marked
partial when it happened, not silently absorbed into a clean-looking record. A confounded run
serialised as clean is exactly the failure D-10 exists to prevent, and it is worse than a refusal
because it reads as settled rather than unsettled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

BUNDLE_REF_SENTINEL = "sentinel:no-eval-bundle-until-phase-2"
CORPUS_SNAPSHOT_HASH_SENTINEL = "sentinel:no-corpus-snapshot-until-phase-2"
TIER_PLACEHOLDER = "T3"  # documented placeholder: no scored evidence item flows through a tracer node


@dataclass
class TokenAccounting:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_read_tokens: int = 0
    call_count: int = 0
    counted_by: str = "none"  # real value: no tokenizer counted anything — no LLM call in this tracer

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cached_read_tokens": self.cached_read_tokens,
            "call_count": self.call_count,
            "counted_by": self.counted_by,
        }


@dataclass
class NodeTrace:
    node_id: str
    instance_hash: str
    depth: str
    effective_depth: str
    wall_clock_ms: int
    cache_hit: bool
    guards_fired: list[str]
    budget_state: str
    realised_budget_share: float
    cross_process_failure_cause: str | None
    resumable: bool
    tokens: TokenAccounting
    tier: str = TIER_PLACEHOLDER
    feed_tier: str = TIER_PLACEHOLDER

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "instance_hash": self.instance_hash,
            "depth": self.depth,
            "effective_depth": self.effective_depth,
            "tier": self.tier,
            "feed_tier": self.feed_tier,
            "wall_clock_ms": self.wall_clock_ms,
            "cache_hit": self.cache_hit,
            "guards_fired": list(self.guards_fired),
            "budget_state": self.budget_state,
            "realised_budget_share": self.realised_budget_share,
            "cross_process_failure_cause": self.cross_process_failure_cause,
            "resumable": self.resumable,
            "tokens": self.tokens.to_dict(),
        }


@dataclass
class RunRecord:
    run_id: str
    wiring_id: str
    wiring_instance_hash: str
    arm_id: str
    arm_execution_order: int
    executor_version: str
    concurrency_setting: str
    determinism_setting: str
    nodes: list[NodeTrace]
    bundle_ref: str = BUNDLE_REF_SENTINEL
    corpus_snapshot_hash: str = CORPUS_SNAPSHOT_HASH_SENTINEL
    stop_reason: str | None = None
    partial: bool = False
    degraded: bool = False
    degradation_reason: str | None = None

    def __post_init__(self) -> None:
        """The honesty invariant — see module docstring for the schema/RIG §TR.3 grounding."""
        flagged = self.partial or self.degraded
        if flagged:
            if self.partial != self.degraded:
                raise ValueError(
                    "partial and degraded are a required-together pair (RIG §TR.3 / the frozen "
                    f"schema's allOf rule): got partial={self.partial!r} degraded={self.degraded!r}"
                )
            if not self.stop_reason:
                raise ValueError(
                    "a partial/degraded run must carry a non-empty stop_reason (RIG §TR.3)"
                )
            if not self.degradation_reason:
                raise ValueError(
                    "a partial/degraded run must carry a non-empty degradation_reason (RIG §TR.3)"
                )
        else:
            if self.stop_reason is not None:
                raise ValueError(
                    "stop_reason must be None on a clean run (partial=False, degraded=False)"
                )
            if self.degradation_reason is not None:
                raise ValueError(
                    "degradation_reason must be None on a clean run (partial=False, degraded=False)"
                )

        for node in self.nodes:
            if node.budget_state == "halted" and not self.partial:
                raise ValueError(
                    f"node {node.node_id!r} reports budget_state='halted' but the run reports "
                    "partial=False — a budget-halted node's run must be traced as partial "
                    "(CONTRACT §9's 'MUST NOT be discarded' rule)"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "wiring_id": self.wiring_id,
            "wiring_instance_hash": self.wiring_instance_hash,
            "arm_id": self.arm_id,
            "arm_execution_order": self.arm_execution_order,
            "bundle_ref": self.bundle_ref,
            "corpus_snapshot_hash": self.corpus_snapshot_hash,
            "executor_version": self.executor_version,
            "concurrency_setting": self.concurrency_setting,
            "determinism_setting": self.determinism_setting,
            "stop_reason": self.stop_reason,
            "partial": self.partial,
            "degraded": self.degraded,
            "degradation_reason": self.degradation_reason,
            "nodes": [n.to_dict() for n in self.nodes],
        }
