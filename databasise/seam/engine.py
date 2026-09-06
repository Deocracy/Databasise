"""``databasise.seam.engine`` — the async ``Databasise`` seam object (D-01), the phase's primary
noun. A caller reaches the engine with a §18.1 query object and receives a §18.2 closed
``ResponseEnvelope`` — no wiring name, arm name, node id or instance hash crossing the boundary in
either direction.

**Pattern 1 (04-RESEARCH.md): generalizing ``run_arm.py``'s call shape.** ``query()``'s body
follows ``databasise/parity/run_arm.py:run_arm``'s established sequence exactly — resolve, inject
query, inject a token allowance, parse, build stores, ``scheduler.run_wiring``, construct a
``RunRecord`` — the one difference being the wiring comes from selector resolution (§18.4) rather
than a hardcoded arm name, and the ``RunRecord`` is redacted into a closed envelope rather than
returned as the un-redacted dict ``run_arm`` returns. ``provides`` is read off the raw resolved
dict, never through ``ParsedWiring`` (Pitfall 1) — ``run_arm.py``'s own precedent.

**04-02: evidence references and the token breakdown.** Before the ``RunRecord`` (and the
scheduler's raw ``results`` dict) go out of scope, ``query()`` mints the envelope's ``evidence``
list from the naive arm's own retrieval position's output (``_EVIDENCE_RETRIEVAL_NODE_ID``,
preserving that node's own output order verbatim — Task 2's own no-re-sort rule) and assembles the
``token_accounting`` breakdown from every node's own ``TokenAccounting`` (``databasise.seam.tokens
.assemble_token_breakdown``). The breakdown assembly raises before any envelope is constructed if a
node reports the ``unbudgetable`` sentinel (D-08) — that exception is left to propagate out of
``query()`` unmodified.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any

from databasise.identity.canon import canonicalise
from databasise.parts.registry import PartRegistry, default_registry
from databasise.runner import scheduler as _scheduler
from databasise.runner.trace import RunRecord
from databasise.seam.envelope import ResponseEnvelope
from databasise.seam.evidence import (
    CHUNKS_NAMESPACE,
    EvidenceRef,
    mint_evidence_refs,
    resolve_evidence_ref,
)
from databasise.seam.query import QueryObject, check_consumable
from databasise.seam.selectors import Selector, resolve_selector
from databasise.seam.tokens import assemble_token_breakdown
from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import MultiNamespaceVectorStore
from databasise.validator.parse import parse_wiring

# The v1-native per-kind names the LightRAG wirings' kv/graph stores are keyed by — matching
# databasise/parity/run_arm.py's own _TEXT_CHUNKS_KIND/_GRAPH_KIND constants exactly.
_TEXT_CHUNKS_KIND = "text_chunks"
_GRAPH_KIND = "chunk_entity_relation"

# The naive arm's own retrieval position (databasise/wirings/lightrag/arm-naive.json-patch.json's
# "chunk-vector" node, kind "retriever") — the only arm the default selector resolves in this
# phase (04-03's alias/capability/harness selectors are the only other resolvable arms, and none
# lands in this plan). A future selector resolving a wiring with a differently-named or absent
# retrieval position is out of this plan's scope — mirrors the same hardcoded-node-id precedent
# already established by ``_inject_query``'s "keywords"/"embedder-query"/"generate" below.
_EVIDENCE_RETRIEVAL_NODE_ID = "chunk-vector"

_EXECUTOR_VERSION = "databasise@0.1.0"
_DETERMINISM_SETTING = "cache-bypassed"
_CONCURRENCY_SETTING = "sequential"

# Mirrors run_arm.py's _DEFAULT_TOKEN_ALLOWANCE/DEC-B note: an absent config.token_allowance
# defaults to 0 at the scheduler, budget-halting every node on its first spend. The seam is the
# one caller that needs a real run to complete, so it sets a real, generous per-node allowance —
# never the published wiring itself.
_DEFAULT_TOKEN_ALLOWANCE = 1_000_000


def _inject_query(resolved: dict[str, Any], query: str) -> dict[str, Any]:
    """Mirrors ``run_arm.py``'s own ``_inject_query`` exactly: stamps ``query`` onto every
    resolved node whose config reads one (``keywords``, ``embedder-query``, ``generate``) — a
    no-op for a node the resolved wiring does not contain."""
    nodes = resolved.get("nodes", {})
    for node_id in ("keywords", "embedder-query", "generate"):
        if node_id not in nodes:
            continue
        config = dict(nodes[node_id].get("config") or {})
        config["query"] = query
        nodes[node_id]["config"] = config
    return resolved


def _inject_token_allowance(resolved: dict[str, Any], allowance: int) -> dict[str, Any]:
    """Mirrors ``run_arm.py``'s own ``_inject_token_allowance`` exactly: sets
    ``config.token_allowance`` on every resolved node that does not already declare one."""
    for node in resolved.get("nodes", {}).values():
        config = dict(node.get("config") or {})
        config.setdefault("token_allowance", allowance)
        node["config"] = config
    return resolved


def _build_stores(store_root: Path, workspace: str) -> dict[str, Any]:
    """kv/vector/graph, all three, at the engine's own namespace/workspace — mirrors
    ``run_arm.py``'s own ``_build_stores`` exactly (see that module's docstring for why every arm
    gets every store wired regardless of which subset it actually touches)."""
    return {
        "kv": SqliteKVStore(namespace=_TEXT_CHUNKS_KIND, workspace=workspace, store_root=store_root),
        "vector": MultiNamespaceVectorStore(workspace=workspace, store_root=store_root),
        "graph": CozoGraphStore(namespace=_GRAPH_KIND, workspace=workspace, store_root=store_root),
    }


class Databasise:
    """The consumer-facing async seam object (D-01). Holds ``store_root``/``workspace``, an
    optional ``PartRegistry`` (defaulting to ``default_registry()``) and an optional ``clients``
    dict for test injection — the same override point ``run_arm.py`` already establishes."""

    def __init__(
        self,
        *,
        store_root: str | Path,
        workspace: str,
        registry: PartRegistry | None = None,
        clients: dict[str, Any] | None = None,
    ) -> None:
        self.store_root = Path(store_root)
        self.workspace = workspace
        self.registry = registry if registry is not None else default_registry()
        self.clients = clients

    async def query(
        self,
        query_object: QueryObject,
        selector: Selector | None = None,
        *,
        debug: bool = False,
    ) -> ResponseEnvelope:
        """§18.1 query object in, §18.2 closed envelope out. ``debug``'s node-by-node trace
        behind the trace reference is 04-04's deliverable — accepted here so the signature is
        stable across the phase, currently a no-op.
        """
        del debug
        check_consumable(query_object, self.registry)

        resolved = resolve_selector(selector, registry=self.registry)
        resolved = _inject_query(resolved, query_object.text or "")
        resolved = _inject_token_allowance(resolved, _DEFAULT_TOKEN_ALLOWANCE)
        parsed = parse_wiring(resolved, self.registry)

        stores = _build_stores(self.store_root, self.workspace)
        try:
            scheduled = await _scheduler.run_wiring(
                parsed,
                self.registry,
                stores,
                determinism_setting=_DETERMINISM_SETTING,
                concurrency_setting=_CONCURRENCY_SETTING,
                clients=self.clients,
            )
        finally:
            for store in stores.values():
                await store.finalize()

        if "cycle" in scheduled:
            # No selector this plan resolves can produce a cyclic wiring (the naive arm is
            # acyclic, proven by databasise/tests/parity's own conformance tests) — a genuine
            # occurrence is out of this plan's scope, not silently swallowed.
            raise RuntimeError("the seam does not yet support a cyclic resolved wiring")

        wiring_bytes = canonicalise(resolved)
        wiring_instance_hash = f"sha256:{hashlib.sha256(wiring_bytes).hexdigest()}"
        wiring_id = resolved.get("wiring_id") or (
            f"wiring:{hashlib.sha256(wiring_bytes).hexdigest()[:16]}"
        )

        # Constructed and consumed here only — never returned. RunRecord carries exactly the
        # internal identities (wiring_id, wiring_instance_hash, node_id, instance_hash) §18.2
        # forbids a consumer from receiving; the envelope below is what actually crosses the seam.
        record = RunRecord(
            run_id=str(uuid.uuid4()),
            wiring_id=wiring_id,
            wiring_instance_hash=wiring_instance_hash,
            arm_id="seam",
            arm_execution_order=0,
            executor_version=_EXECUTOR_VERSION,
            concurrency_setting=_CONCURRENCY_SETTING,
            determinism_setting=_DETERMINISM_SETTING,
            nodes=scheduled["nodes"],
            partial=scheduled["partial"],
            degraded=scheduled["degraded"],
            stop_reason=scheduled["stop_reason"],
            degradation_reason=scheduled["degradation_reason"],
        )

        provides = resolved.get("provides") or []
        provided = {node_id: scheduled["results"].get(node_id) for node_id in provides}

        answer = ""
        depth_label = "stage"
        for node in record.nodes:
            if node.node_id not in provides:
                continue
            depth_label = node.effective_depth
            output = provided.get(node.node_id)
            if isinstance(output, dict) and "completion" in output:
                answer = str(output["completion"])

        # Task 1/2 (04-02): mint evidence refs from the naive arm's own retrieval position, in its
        # own output order — no re-sort here (see _EVIDENCE_RETRIEVAL_NODE_ID's own docstring note
        # and this module's docstring). A wiring that never dispatches this node (none does today —
        # the default selector always resolves the naive arm) yields no retrieval output at all,
        # which mints to an empty list, never a refusal (the empty-evidence behavior Task 1 proves).
        retrieval_output = scheduled["results"].get(_EVIDENCE_RETRIEVAL_NODE_ID)
        retrieval_items = retrieval_output["items"] if isinstance(retrieval_output, dict) else []
        evidence = mint_evidence_refs(retrieval_items, namespace=CHUNKS_NAMESPACE)

        # Task 3 (04-02): raises UnbudgetableParticipantError before any envelope is constructed if
        # a node reports the unbudgetable sentinel (D-08) — left to propagate unmodified.
        token_accounting = assemble_token_breakdown(record.nodes)

        return ResponseEnvelope(
            answer=answer,
            evidence=evidence,
            depth_label=depth_label,
            partial=record.partial,
            degraded=record.degraded,
            stop_reason=record.stop_reason,
            degradation_reason=record.degradation_reason,
            token_accounting=token_accounting,
        )

    async def resolve_evidence(self, ref: EvidenceRef) -> dict[str, Any]:
        """The second §18 operation the seam exposes (§18.5 — per part kind, evidence, never per
        modality): resolves an evidence reference back through the same store handle it was minted
        from. Opens the store set the same way ``query`` does and finalizes it in a ``finally``
        block, mirroring ``query``'s own store lifecycle exactly.
        """
        stores = _build_stores(self.store_root, self.workspace)
        try:
            return resolve_evidence_ref(ref, stores["vector"])
        finally:
            for store in stores.values():
                await store.finalize()


__all__ = ["Databasise"]
