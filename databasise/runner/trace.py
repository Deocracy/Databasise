"""D-10's run-record field stamping: ``RunRecord``, ``NodeTrace`` and ``TokenAccounting``
dataclasses matching ``docs/system-model/rig-trace.schema.json`` exactly.

Placeholder policy (explicitly marked, per this plan's own instructions): ``bundle_ref`` and
``corpus_snapshot_hash`` have no real eval bundle until Phase 2 (RIG-02's own bundle machinery),
so they carry the documented sentinel strings below rather than omitting the field and failing
the schema. ``tier``/``feed_tier`` likewise carry a documented ``T3`` placeholder for nodes that
never handle a scored evidence item — Phase 2 names the real evidence-tier mechanism. Every other
field (``arm_execution_order``, ``cache_hit``, ``guards_fired``, ``realised_budget_share``,
``determinism_setting``, ``concurrency_setting``) is a real value computed by this commit, per
D-10 — not a placeholder.
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
