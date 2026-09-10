"""Builds HippoRAG 2's index over the Phase 3 parity corpus, for real, and verifies it before
reporting success (06-08-PLAN.md Task 1) — a one-time build harness in ``import_index.py``'s own
shape: build, then verify, then report; never report a build that has not been verified.

**Exact invocation (module docstring convention, mirroring ``build_corpus_fixture.py``):**

    uv run python -m databasise.parity.build_hipporag_index

This is a one-time build tool checked in beside its own documentation — not a runtime dependency,
not run by any test (mirrors ``build_corpus_fixture.py``'s own disposition). It loads the committed
Phase 3 parity corpus snapshot (``databasise/tests/fixtures/corpus/``), resolves HippoRAG 2's base
wiring, injects the corpus documents onto ``chunk-embed``'s own ``config["documents"]`` and a real
token allowance onto every node exactly as ``run_arm.py``'s own ``_inject_query``/
``_inject_token_allowance`` do for query time, builds real clients from ``v1/.env.parity`` through
``run_arm.py``'s own ``_build_clients``, builds the stores at HippoRAG's own declared
``store_namespaces``, and runs the wiring through ``runner.scheduler.run_wiring`` directly.

Adopts 03-11-PLAN.md's own hard-won guard: refuses a run whose extraction produced nothing. A
silently-empty OpenIE pass produces an index that looks built and retrieves nothing — the failure
that cost Phase 3 two gap-closure plans. Before reporting success, :func:`build_index` verifies the
graph namespace holds a non-zero node and edge count (with at least one ``entity:``-prefixed and
one ``chunk:``-prefixed vertex present — ``entity_fact_embed.py``'s own vertex-ref identity space),
the entity and fact vector namespaces hold non-zero entry counts, and the run reports
``partial=False``/``degraded=False``. Any failure is a refusal naming the specific check, never a
warning attached to a returned result.

**Deferred (06-08-SUMMARY.md, owner decision `defer-and-record-blocked`).** This module is genuine,
runnable code — not a stub — but has not been invoked for real in this environment: one real
invocation requires live credentials from ``v1/.env.parity`` (``qwen/qwen3.7-flash`` extraction,
``qwen/qwen3-embedding-8b`` embedding) and was not authorized during this plan's execution. See
``databasise/evidence/CROSS-MODALITY-EVIDENCE.md`` for the honest record of why, and the entry
criterion for the deferred run.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from databasise.identity.canon import canonicalise
from databasise.parity import import_index
from databasise.parity.corpus import load_snapshot
from databasise.parity.run_arm import (
    DEFAULT_V1_ENV_PARITY,
    MissingParityEnvError,
    MissingParityEnvKeyError,
    _build_clients,
    _build_stores,
    _CONCURRENCY_SETTING,
    _DEFAULT_TOKEN_ALLOWANCE,
    _DETERMINISM_SETTING,
    _EXECUTOR_VERSION,
    _inject_token_allowance,
    _load_env_file,
)
from databasise.parts.registry import PartRegistry, default_registry
from databasise.parts_core.hipporag.entity_fact_embed import (
    CHUNK_VERTEX_PREFIX,
    ENTITY_VERTEX_PREFIX,
)
from databasise.runner import scheduler as _scheduler
from databasise.runner.trace import RunRecord
from databasise.seam.tokens import assemble_token_breakdown
from databasise.validator.parse import parse_wiring
from databasise.wirings.resolve import load_wiring

_CHUNK_EMBED_NODE_ID = "chunk-embed"
_CHUNKS_NAMESPACE = "hipporag-chunks"
_ENTITIES_NAMESPACE = "hipporag-entities"
_FACTS_NAMESPACE = "hipporag-facts"


class MissingParityLightRAGIndexError(RuntimeError):
    """Raised when the Phase 3 v1-built LightRAG index is not present at ``store_root/workspace``
    — Task 1's own ``<precondition>``, the same condition ``run_comparison.py`` already asserts
    before any measured run, named rather than left to surface as a confusing empty-store result.
    """

    def __init__(self, expected_path: Path):
        self.expected_path = expected_path
        super().__init__(
            f"the Phase 3 v1-built LightRAG index is not present at {expected_path} — run "
            "databasise.parity.import_index first (03-02-PLAN.md Task 3)"
        )


class HippoRAGIndexBuildRefusedError(RuntimeError):
    """Raised when the post-build verification finds a partial/degraded run, a cyclic wiring, or
    an empty namespace — a silently-empty extraction pass looks built but retrieves nothing, the
    exact failure 03-11-PLAN.md's own guard exists to catch. Never a warning attached to a
    returned result: refusing to construct :class:`IndexBuildResult` at all is what makes "verify
    before reporting success" a real refusal rather than a caveat.
    """


@dataclass(frozen=True)
class IndexBuildResult:
    """The observed, verified outcome of one real HippoRAG index build — every field is a
    real, computed value read from the run's own accounting, never an estimate (Task 1's own
    acceptance criterion)."""

    corpus_hash: str
    workspace: str
    graph_node_count: int
    graph_edge_count: int
    chunk_vector_count: int
    entity_vector_count: int
    fact_vector_count: int
    token_spend: list[dict[str, Any]]
    duration_seconds: float
    partial: bool
    degraded: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "corpus_hash": self.corpus_hash,
            "workspace": self.workspace,
            "graph_node_count": self.graph_node_count,
            "graph_edge_count": self.graph_edge_count,
            "chunk_vector_count": self.chunk_vector_count,
            "entity_vector_count": self.entity_vector_count,
            "fact_vector_count": self.fact_vector_count,
            "token_spend": self.token_spend,
            "duration_seconds": self.duration_seconds,
            "partial": self.partial,
            "degraded": self.degraded,
        }


def _inject_documents(resolved: dict[str, Any], documents: list[dict[str, Any]]) -> dict[str, Any]:
    """Stamp the corpus documents onto ``chunk-embed``'s own ``config["documents"]`` — the single
    index-side entry point every one of HippoRAG's seven index-side positions is reachable from
    (``chunk-embed`` has no ``deps``; every other index-side node depends on it transitively).
    Mirrors ``run_arm.py``'s own ``_inject_query``/``_inject_token_allowance`` no-op convention for
    a node the resolved wiring does not contain.
    """
    nodes = resolved.get("nodes", {})
    if _CHUNK_EMBED_NODE_ID not in nodes:
        return resolved
    config = dict(nodes[_CHUNK_EMBED_NODE_ID].get("config") or {})
    config["documents"] = documents
    nodes[_CHUNK_EMBED_NODE_ID]["config"] = config
    return resolved


def _assert_preconditions(
    *, env_path: Path, store_root: Path, workspace: str
) -> dict[str, Any]:
    """Task 1's own ``<precondition>``: ``v1/.env.parity`` exists and carries every key
    ``_build_clients`` requires, and the Phase 3 v1-built LightRAG index is present at
    ``store_root/workspace``. Asserts both before any node is dispatched, naming the missing key
    or the missing store directory on failure. Returns the real clients built from the verified
    env, so the caller never constructs them twice.
    """
    env = _load_env_file(env_path)
    clients = _build_clients(env)
    lightrag_dir = Path(store_root) / workspace
    if not lightrag_dir.exists():
        raise MissingParityLightRAGIndexError(lightrag_dir)
    return clients


async def build_index(
    *,
    registry: PartRegistry | None = None,
    store_root: Path | None = None,
    workspace: str | None = None,
    clients: dict[str, Any] | None = None,
    env_path: Path | None = None,
    token_allowance: int = _DEFAULT_TOKEN_ALLOWANCE,
) -> IndexBuildResult:
    """Build, verify, and report — never report a build this function has not itself verified.

    ``clients``/``store_root``/``workspace`` are override points for tests, mirroring
    ``run_arm.run_arm``'s own convention: passing them bypasses real-client construction and the
    real-LightRAG-index precondition check entirely, so a test can exercise this function's build
    logic against a synthetic store and a stub client double.
    """
    if registry is None:
        registry = default_registry()

    resolved_store_root = store_root if store_root is not None else import_index.DEFAULT_STORE_ROOT
    resolved_workspace = workspace if workspace is not None else import_index._import_workspace()

    resolved_clients = clients
    if resolved_clients is None:
        resolved_clients = _assert_preconditions(
            env_path=env_path or DEFAULT_V1_ENV_PARITY,
            store_root=resolved_store_root,
            workspace=resolved_workspace,
        )

    snapshot = load_snapshot()
    documents = [{"document_id": doc.id, "text": doc.text} for doc in snapshot.documents]

    resolved = load_wiring("hipporag")
    resolved = _inject_documents(resolved, documents)
    resolved = _inject_token_allowance(resolved, token_allowance)
    parsed = parse_wiring(resolved, registry)

    stores = _build_stores(resolved_store_root, resolved_workspace, resolved)

    start = time.monotonic()
    try:
        scheduled = await _scheduler.run_wiring(
            parsed,
            registry,
            stores,
            determinism_setting=_DETERMINISM_SETTING,
            concurrency_setting=_CONCURRENCY_SETTING,
            clients=resolved_clients,
        )
        duration_seconds = time.monotonic() - start

        if "cycle" in scheduled:
            raise HippoRAGIndexBuildRefusedError(
                f"resolved HippoRAG wiring is cyclic: {scheduled['cycle']!r} — refusing to "
                "report a build"
            )

        wiring_bytes = canonicalise(resolved)
        wiring_instance_hash = f"sha256:{hashlib.sha256(wiring_bytes).hexdigest()}"
        wiring_id = resolved.get("wiring_id") or (
            f"wiring:{hashlib.sha256(wiring_bytes).hexdigest()[:16]}"
        )

        record = RunRecord(
            run_id=str(uuid.uuid4()),
            wiring_id=wiring_id,
            wiring_instance_hash=wiring_instance_hash,
            arm_id="hipporag-index-build",
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

        if record.partial or record.degraded:
            raise HippoRAGIndexBuildRefusedError(
                f"the index build reported partial={record.partial} degraded={record.degraded} "
                f"stop_reason={record.stop_reason!r} "
                f"degradation_reason={record.degradation_reason!r} — refusing to report success "
                "on a run that did not complete cleanly"
            )

        # Verify before reporting: read back the run's own persisted state, never trust the
        # scheduler's return value alone (03-11-PLAN.md's own guard against a silently-empty
        # extraction pass).
        await stores["vector"].index_done_callback()
        await stores["graph"].index_done_callback()

        graph = await stores["graph"].export_to_igraph()
        graph_node_count = graph.vcount()
        graph_edge_count = graph.ecount()
        vertex_names = graph.vs["name"] if graph_node_count else []
        has_entity_vertex = any(name.startswith(ENTITY_VERTEX_PREFIX) for name in vertex_names)
        has_chunk_vertex = any(name.startswith(CHUNK_VERTEX_PREFIX) for name in vertex_names)

        vector_store = stores["vector"]
        chunk_vector_count = len(list(vector_store.select(_CHUNKS_NAMESPACE).iter_vectors()))
        entity_vector_count = len(list(vector_store.select(_ENTITIES_NAMESPACE).iter_vectors()))
        fact_vector_count = len(list(vector_store.select(_FACTS_NAMESPACE).iter_vectors()))
    finally:
        for store in stores.values():
            await store.finalize()

    failures: list[str] = []
    if graph_node_count == 0:
        failures.append("graph node count is zero")
    if graph_edge_count == 0:
        failures.append("graph edge count is zero")
    if graph_node_count and not has_entity_vertex:
        failures.append(f"no {ENTITY_VERTEX_PREFIX!r}-prefixed vertex present")
    if graph_node_count and not has_chunk_vertex:
        failures.append(f"no {CHUNK_VERTEX_PREFIX!r}-prefixed vertex present")
    if entity_vector_count == 0:
        failures.append(f"vector namespace {_ENTITIES_NAMESPACE!r} is empty")
    if fact_vector_count == 0:
        failures.append(f"vector namespace {_FACTS_NAMESPACE!r} is empty")
    if failures:
        raise HippoRAGIndexBuildRefusedError(
            "the index build produced an empty extraction result — a silently-empty OpenIE pass "
            "looks built but retrieves nothing (03-11-PLAN.md's own guard, adopted here): "
            + "; ".join(failures)
        )

    token_spend = [entry.model_dump() for entry in assemble_token_breakdown(record.nodes)]

    return IndexBuildResult(
        corpus_hash=snapshot.corpus_hash,
        workspace=resolved_workspace,
        graph_node_count=graph_node_count,
        graph_edge_count=graph_edge_count,
        chunk_vector_count=chunk_vector_count,
        entity_vector_count=entity_vector_count,
        fact_vector_count=fact_vector_count,
        token_spend=token_spend,
        duration_seconds=duration_seconds,
        partial=record.partial,
        degraded=record.degraded,
    )


def main(argv: list[str] | None = None) -> int:
    """``uv run python -m databasise.parity.build_hipporag_index`` — the exact invocation this
    module's own docstring names. Exit codes: 0 on a verified build, 1 on any refusal (missing
    env/key, missing LightRAG index, an empty/partial/degraded run) — mirrors
    ``import_index.py``'s/``run_comparison.py``'s own "non-zero exit means something" convention.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)

    try:
        result = asyncio.run(build_index())
    except (
        MissingParityEnvError,
        MissingParityEnvKeyError,
        MissingParityLightRAGIndexError,
        HippoRAGIndexBuildRefusedError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
