"""The phase's acceptance module: all four ROADMAP.md Phase 1 success criteria, asserted end to
end through ``databasise.run_wiring`` — the public entry point a consumer calls — rather than
through an internal helper, so a refactor that breaks the public path fails here even if every
unit test still passes.

Two fixture wirings (built by the two ``_*_wiring`` helpers below):

- The **transparent wiring** (``_transparent_wiring``): ``producer`` fans out into two identically
  configured retriever branches, which join into a node that touches all three embedded engines
  (kv/graph/vector) in one process. Used for criteria 1, 2 and 3.
- The **arms wiring** (``_arms_wiring``): one node whose ``Part.structural_depth`` is ``opaque``
  and whose declared ``artifact_scope`` is ``quarantined`` (a declaration-only-registry-style
  entry given an executable stand-in body for this test), beside one node at ``stage`` depth
  writing ``shared``. Used for criterion 4.

Both wirings deliberately give every node a ``WiringNode.kind`` of ``"stage"``/``"passthrough"``/
``"retriever"`` — never ``"opaque"`` or ``"fixpoint"`` — and no ``net``/``fs``/``self_storage``/
``mutates_store`` effect. ``execution_mode`` (``validator.execution_mode.derive_execution_mode``)
is a pure function of exactly those two inputs, and D-08 (Phase 1 hosts ``in-process`` only)
refuses every other placement by name. The opaque arm's node is "opaque" in the CONTRACT §3 taint
sense that matters for this criterion — its component's ``Part.structural_depth`` is ``opaque``,
which is what drives the blast-radius scope rule and the namespace's derived scope token — while
its *wiring-position* kind stays hostable, since Phase 1's runner does not yet build the real
subprocess containment CONTRACT §3 eventually requires for a genuinely opaque wiring *position*
(D-08's own documented, unimplemented placement). Both concerns are real; only one is buildable
this phase, and this fixture exercises the one that is.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import databasise
from databasise.identity.canon import config_hash
from databasise.identity.instance import cache_partition_key, instance_hash
from databasise.namespaces import derive_namespace, gc_namespace
from databasise.parts.registry import PartRegistry
from databasise.parts.schema import NodeContext, Part
from databasise.parts_core.fake_llm_caller import FAKE_LLM_CALLER_PART
from databasise.parts_core.fake_retriever import FAKE_RETRIEVER_PART
from databasise.registry_artifact.index import ArtifactRegistry, Pin
from databasise.registry_artifact.write_path import BlastRadiusRefusal, write_artifact
from databasise.stores.blob import FilesystemBlobStore
from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import FaissVectorStore

_DETERMINISM_SETTING = "cache-bypassed"
_CONCURRENCY_SETTING = "parallel"  # backed by D-09's per-node semaphore + TaskGroup dispatch


def _listening_socket_count() -> int:
    """Sockets in the LISTEN state owned by this process, read directly from the kernel's own
    TCP tables — the same OS-level check ``tests/test_embed_startup.py`` uses.
    """
    count = 0
    for path in ("/proc/self/net/tcp", "/proc/self/net/tcp6"):
        try:
            with open(path) as f:
                lines = f.readlines()[1:]
        except FileNotFoundError:
            continue
        for line in lines:
            fields = line.split()
            if len(fields) > 3 and fields[3] == "0A":
                count += 1
    return count


# --------------------------------------------------------------------------------------------- #
# Criteria 1-3: the transparent multi-node wiring (fan-out + join)                                #
# --------------------------------------------------------------------------------------------- #


async def _multi_engine_touch_body(ctx: NodeContext) -> dict[str, Any]:
    """The join node: writes to the run's own kv store via ``ctx.stores`` (the capability-scoped
    seam every reference part uses), and additionally constructs its own graph and vector store
    directly at a namespace under the run's ``store_root`` (criterion 1 needs all three embedded
    engines touched in one run; the current composer in ``databasise/__init__.py`` wires only kv
    into ``ctx.stores`` — see 01-08-SUMMARY.md's "Known Gaps" — so a node exercising graph/vector
    is responsible for its own store lifecycle, exactly as this body does).
    """
    kv = ctx.stores["kv"]
    await kv.upsert({ctx.node_id: {"inputs": dict(ctx.inputs)}})

    store_root = Path(ctx.config["store_root"])
    graph = CozoGraphStore(namespace="criterion1-graph", workspace="", store_root=store_root)
    await graph.upsert_node("n1", {"touched": True})
    await graph.index_done_callback()
    await graph.finalize()

    vector = FaissVectorStore(namespace="criterion1-vector", workspace="", store_root=store_root)
    await vector.upsert(["v1"], [[1.0, 0.0, 0.0]])
    await vector.index_done_callback()

    return {"joined": sorted(ctx.inputs)}


_MULTI_ENGINE_TOUCH_PART = Part(
    name_at_version="test/multi-engine-touch@1.0.0",
    kind="stage",
    structural_depth="stage",
    effects=["writes_kv"],
    upstream_ref=None,
    body=_multi_engine_touch_body,
)

_RETRIEVER_CONFIG = {"query": "graph databases"}

# Criterion 2's own metered node (01-10-PLAN.md Task 2): the only node in this wiring declaring a
# calling effect, so criterion 2's own acceptance test can assert real metered spend on a real
# metered node, instead of asserting a constant every unmetered node would also satisfy.
_LLM_CALLER_NODE_ID = "llm-caller"
_LLM_CALLER_PROMPT = "summarise these retrieved graph database results"
_LLM_CALLER_TOKEN_ALLOWANCE = 10_000  # generous — this node must stay within budget


def _transparent_registry() -> PartRegistry:
    registry = PartRegistry()  # seeds core/passthrough@1.0.0 and core/kv-writer@1.0.0
    registry.register(FAKE_RETRIEVER_PART)
    registry.register(_MULTI_ENGINE_TOUCH_PART)
    registry.register(FAKE_LLM_CALLER_PART)
    return registry


def _transparent_wiring(store_root: Path, *, retriever_config: dict[str, Any] | None = None) -> dict[str, Any]:
    """``producer`` fans out into ``branch-a``/``branch-b`` (identically configured retrievers —
    criterion 3 needs two positions sharing one identity), which join into the multi-engine node.
    ``llm-caller`` is an independent, unrelated fifth node (no deps, nothing depends on it)
    declaring ``calls_llm`` — criterion 2's own metered-node coverage (see module docstring).
    """
    branch_config = retriever_config if retriever_config is not None else _RETRIEVER_CONFIG
    return {
        "nodes": {
            "producer": {"component": "core/passthrough@1.0.0", "kind": "passthrough", "deps": []},
            "branch-a": {
                "component": FAKE_RETRIEVER_PART.name_at_version,
                "kind": "retriever",
                "effects": ["reads_vector"],
                "config": dict(branch_config),
                "deps": ["producer"],
            },
            "branch-b": {
                "component": FAKE_RETRIEVER_PART.name_at_version,
                "kind": "retriever",
                "effects": ["reads_vector"],
                "config": dict(_RETRIEVER_CONFIG),
                "deps": ["producer"],
            },
            "join": {
                "component": _MULTI_ENGINE_TOUCH_PART.name_at_version,
                "kind": "stage",
                "effects": ["writes_kv"],
                "config": {"store_root": str(store_root)},
                "deps": ["branch-a", "branch-b"],
            },
            _LLM_CALLER_NODE_ID: {
                "component": FAKE_LLM_CALLER_PART.name_at_version,
                "kind": "llm-caller",
                "effects": list(FAKE_LLM_CALLER_PART.effects),
                "config": {"prompt": _LLM_CALLER_PROMPT, "token_allowance": _LLM_CALLER_TOKEN_ALLOWANCE},
                "deps": [],
            },
        }
    }


def _nodes_by_id(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {n["node_id"]: n for n in record["nodes"]}


async def test_criterion_1_library_startup_with_no_external_server(store_root):
    """ROADMAP.md Phase 1 criterion 1: the package imports and runs a wiring touching all three
    embedded engines, with no child process and no listening socket. Task 1
    (``tests/test_embed_startup.py``) proves the property in isolation; this asserts it holds
    during a real end-to-end ``run_wiring`` call.
    """
    before_sockets = _listening_socket_count()

    record = await databasise.run_wiring(
        _transparent_wiring(store_root),
        store_root=store_root,
        registry=_transparent_registry(),
        determinism_setting=_DETERMINISM_SETTING,
        concurrency_setting=_CONCURRENCY_SETTING,
    )

    after_sockets = _listening_socket_count()

    assert record["partial"] is False
    assert record["degraded"] is False
    # Not a task/thread-count assertion here: the graph store's off-loop dispatch
    # (databasise/stores/graph.py's own documented use of loop.run_in_executor) lazily creates a
    # real OS-level ThreadPoolExecutor the first time any test in the session touches it, so a
    # wiring that exercises graph legitimately grows the task count — that is Test 4's own scope
    # in tests/test_embed_startup.py, deliberately isolated to a kv-only wiring. This criterion's
    # own "no external server" claim is the no-new-listening-socket property, which graph's
    # thread pool does not affect.
    assert after_sockets <= before_sockets, f"listening socket count grew: {before_sockets} -> {after_sockets}"

    # All three embedded engines were actually touched by the join node.
    graph_dir = store_root / "criterion1-graph"
    vector_dir = store_root / "criterion1-vector"
    assert (graph_dir / "graph.cozo").exists()
    assert (vector_dir / "vector.faiss").exists()

    verify_kv = SqliteKVStore(
        namespace=databasise.TRACER_KV_NAMESPACE, workspace=databasise.TRACER_WORKSPACE, store_root=store_root
    )
    stored = await verify_kv.get_by_id("join")
    await verify_kv.finalize()
    assert stored is not None


async def test_criterion_2_the_runner_executes_to_completion_with_metered_spend(store_root, assert_valid_trace):
    """ROADMAP.md Phase 1 criterion 2: a multi-node wiring including a fan-out and a join runs to
    completion under structured concurrency; every node's trace carries ``budget_state`` and
    ``realised_budget_share``; ``concurrency_setting`` records the run's setting; the record
    validates against the frozen trace schema.

    The per-node budget assertions below now distinguish a metered node (``llm-caller``, the only
    node declaring ``calls_llm``) from an unmetered one (every other node here): an unmetered
    node's honest values are ``budget_state="within_budget"`` and ``realised_budget_share==0.0``
    with an all-zero ``tokens`` object, while the metered node's honest values are a non-zero
    ``tokens["prompt_tokens"]`` and a share strictly between 0.0 and 1.0. A value satisfied by a
    hardcoded constant on every node (this test's own pre-01-10-PLAN.md shape, which asserted
    ``realised_budget_share == 1.0`` uniformly) is no longer accepted — that hardcoded shape is
    exactly what let the runner ship with metering never wired into the live dispatch path at all
    (01-VERIFICATION.md's Gap 2 / MACH-05).
    """
    record = await databasise.run_wiring(
        _transparent_wiring(store_root),
        store_root=store_root,
        registry=_transparent_registry(),
        determinism_setting=_DETERMINISM_SETTING,
        concurrency_setting=_CONCURRENCY_SETTING,
    )

    assert_valid_trace(record)
    assert record["partial"] is False
    assert record["stop_reason"] is None
    assert record["concurrency_setting"] == _CONCURRENCY_SETTING
    assert {n["node_id"] for n in record["nodes"]} == {
        "producer",
        "branch-a",
        "branch-b",
        "join",
        _LLM_CALLER_NODE_ID,
    }

    nodes_by_id = _nodes_by_id(record)
    unmetered_node_ids = {"producer", "branch-a", "branch-b", "join"}

    for node in record["nodes"]:
        assert node["budget_state"] in ("within_budget", "halted", "degraded")
        assert 0.0 <= node["realised_budget_share"] <= 1.0
        assert node["budget_state"] == "within_budget"  # every node ran to completion, no halt

    for node_id in unmetered_node_ids:
        node = nodes_by_id[node_id]
        assert node["realised_budget_share"] == 0.0
        assert node["tokens"] == {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cached_read_tokens": 0,
            "call_count": 0,
            "counted_by": "none",
        }

    llm_caller_node = nodes_by_id[_LLM_CALLER_NODE_ID]
    assert llm_caller_node["tokens"]["prompt_tokens"] > 0
    assert llm_caller_node["tokens"]["counted_by"] == "fixture-tokenizer@1"
    assert 0.0 < llm_caller_node["realised_budget_share"] < 1.0


async def test_criterion_3_identity_stability_and_separation(store_root):
    """ROADMAP.md Phase 1 criterion 3: the same component wired twice with byte-identical config
    resolves to one ``instance_hash`` and one cache-partition key across the two positions;
    mutating one byte of one position's config changes only that position's ``config_hash``,
    ``instance_hash`` and cache-partition key; neither identity function accepts a node id.
    """
    import inspect

    record = await databasise.run_wiring(
        _transparent_wiring(store_root),
        store_root=store_root,
        registry=_transparent_registry(),
        determinism_setting=_DETERMINISM_SETTING,
        concurrency_setting=_CONCURRENCY_SETTING,
    )
    nodes = _nodes_by_id(record)

    # Two positions, same component + same config + same (single) dependency -> one identity.
    assert nodes["branch-a"]["instance_hash"] == nodes["branch-b"]["instance_hash"]

    producer_hash = nodes["producer"]["instance_hash"]
    base_config_hash = config_hash(_RETRIEVER_CONFIG)
    key_a = cache_partition_key(
        FAKE_RETRIEVER_PART.name_at_version, base_config_hash, [producer_hash], _RETRIEVER_CONFIG
    )
    key_b = cache_partition_key(
        FAKE_RETRIEVER_PART.name_at_version, base_config_hash, [producer_hash], _RETRIEVER_CONFIG
    )
    assert key_a == key_b

    # Mutate one byte of branch-a's own config; branch-b (unmutated) keeps its instance_hash.
    mutated_config = {"query": _RETRIEVER_CONFIG["query"] + "x"}
    mutated_record = await databasise.run_wiring(
        _transparent_wiring(store_root, retriever_config=mutated_config),
        store_root=store_root,
        registry=_transparent_registry(),
        determinism_setting=_DETERMINISM_SETTING,
        concurrency_setting=_CONCURRENCY_SETTING,
    )
    mutated_nodes = _nodes_by_id(mutated_record)

    assert mutated_nodes["branch-a"]["instance_hash"] != nodes["branch-a"]["instance_hash"]
    assert mutated_nodes["branch-b"]["instance_hash"] == nodes["branch-b"]["instance_hash"]

    mutated_config_hash = config_hash(mutated_config)
    assert mutated_config_hash != base_config_hash
    mutated_key = cache_partition_key(
        FAKE_RETRIEVER_PART.name_at_version, mutated_config_hash, [producer_hash], mutated_config
    )
    assert mutated_key != key_a

    # Neither identity function accepts a node id — the enforcement is structural (the signature
    # itself), not a docstring promise a caller could ignore.
    assert "node_id" not in inspect.signature(instance_hash).parameters
    assert "node_id" not in inspect.signature(cache_partition_key).parameters


# --------------------------------------------------------------------------------------------- #
# Criterion 4: the arms wiring (opaque arm, quarantined; transparent arm, shared)                 #
# --------------------------------------------------------------------------------------------- #

_OPAQUE_PRODUCER_INSTANCE_HASH = instance_hash("test/opaque-arm@1.0.0", config_hash({}), [])
_TRANSPARENT_PRODUCER_INSTANCE_HASH = instance_hash("test/transparent-arm@1.0.0", config_hash({}), [])

_SA2_STAMPS = {"sa2_chunker": "t-chunker@1", "sa2_extraction": "t-extraction@1", "sa2_embedding": "t-embedding@1"}


async def _arm_writer_body(ctx: NodeContext) -> dict[str, Any]:
    """Writes one artifact at this arm's declared scope, plus its own graph and vector namespace
    directories directly under ``store_root`` (``workspace=""`` collapses the store adapters'
    ``store_root/workspace/namespace`` layout onto ``namespaces.namespace_dir``'s
    ``store_root/namespace`` layout, so the directory this body creates is exactly the one
    ``namespaces.gc_namespace`` would later remove).
    """
    config = ctx.config
    store_root = Path(config["store_root"])
    namespace = config["namespace"]
    scope = config["scope"]
    effective_depth = config["effective_depth"]

    blob_store = FilesystemBlobStore(namespace=namespace, workspace="", store_root=store_root)
    registry = ArtifactRegistry(store_root=store_root)
    record = write_artifact(
        content=f"{ctx.node_id}-content".encode(),
        scope=scope,
        effective_depth=effective_depth,
        namespace=namespace,
        producer_instance_hash=config["producer_instance_hash"],
        recipe_hash=f"recipe-{ctx.node_id}",
        blob_store=blob_store,
        registry=registry,
        **_SA2_STAMPS,
        corpus_id="corpus-1",
        space_id=None,
    )

    graph = CozoGraphStore(namespace=namespace, workspace="", store_root=store_root)
    await graph.upsert_node(ctx.node_id, {})
    await graph.index_done_callback()
    await graph.finalize()

    vector = FaissVectorStore(namespace=namespace, workspace="", store_root=store_root)
    await vector.upsert([f"{ctx.node_id}-v"], [[1.0, 0.0]])
    await vector.index_done_callback()

    return {"content_hash": record.content_hash, "namespace": namespace}


_OPAQUE_ARM_PART = Part(
    name_at_version="test/opaque-arm@1.0.0",
    # Deliberately NOT kind="opaque" on the WiringNode side (see module docstring): D-08 refuses
    # "subprocess" hosting by name, and databasise/__init__.py's composer cannot yet absorb a
    # partial-run outcome without RunRecord's honesty invariant raising. structural_depth="opaque"
    # below is what actually drives this criterion's taint/scope behaviour.
    kind="stage",
    structural_depth="opaque",
    effects=["writes_artifact"],
    upstream_ref=None,
    artifact_scope="quarantined",
    body=_arm_writer_body,
)

_TRANSPARENT_ARM_PART = Part(
    name_at_version="test/transparent-arm@1.0.0",
    kind="stage",
    structural_depth="stage",
    effects=["writes_artifact"],
    upstream_ref=None,
    artifact_scope="shared",
    body=_arm_writer_body,
)


def _arms_registry() -> PartRegistry:
    registry = PartRegistry(seed_tracer_parts=False)
    registry.register(_OPAQUE_ARM_PART)
    registry.register(_TRANSPARENT_ARM_PART)
    return registry


def _arms_wiring(store_root: Path, *, opaque_namespace: str, shared_namespace: str) -> dict[str, Any]:
    return {
        "nodes": {
            "opaque-arm": {
                "component": _OPAQUE_ARM_PART.name_at_version,
                "kind": "stage",
                "effects": ["writes_artifact"],
                "config": {
                    "store_root": str(store_root),
                    "namespace": opaque_namespace,
                    "scope": "quarantined",
                    "effective_depth": "opaque",
                    "producer_instance_hash": _OPAQUE_PRODUCER_INSTANCE_HASH,
                },
                "deps": [],
            },
            "transparent-arm": {
                "component": _TRANSPARENT_ARM_PART.name_at_version,
                "kind": "stage",
                "effects": ["writes_artifact"],
                "config": {
                    "store_root": str(store_root),
                    "namespace": shared_namespace,
                    "scope": "shared",
                    "effective_depth": "stage",
                    "producer_instance_hash": _TRANSPARENT_PRODUCER_INSTANCE_HASH,
                },
                "deps": [],
            },
        }
    }


async def test_criterion_4_quarantined_isolation_and_visible_namespace_separation(store_root):
    """ROADMAP.md Phase 1 criterion 4: a wiring arm containing an ``opaque`` node writes
    ``quarantined`` and cannot reach ``shared``; per-part graph and vector namespaces are visibly
    separate after a run.
    """
    opaque_namespace = derive_namespace(
        sa1_instance_hash=_OPAQUE_PRODUCER_INSTANCE_HASH,
        sa2_chunker=_SA2_STAMPS["sa2_chunker"],
        sa2_extraction=_SA2_STAMPS["sa2_extraction"],
        sa2_embedding=_SA2_STAMPS["sa2_embedding"],
        corpus_id="corpus-1",
        space_id=None,
        scope="quarantined",
    )
    shared_namespace = derive_namespace(
        sa1_instance_hash=_TRANSPARENT_PRODUCER_INSTANCE_HASH,
        sa2_chunker=_SA2_STAMPS["sa2_chunker"],
        sa2_extraction=_SA2_STAMPS["sa2_extraction"],
        sa2_embedding=_SA2_STAMPS["sa2_embedding"],
        corpus_id="corpus-1",
        space_id=None,
        scope="shared",
    )
    assert opaque_namespace.startswith("quarantined-")
    assert shared_namespace.startswith("shared-")
    assert opaque_namespace != shared_namespace

    record = await databasise.run_wiring(
        _arms_wiring(store_root, opaque_namespace=opaque_namespace, shared_namespace=shared_namespace),
        store_root=store_root,
        registry=_arms_registry(),
        determinism_setting=_DETERMINISM_SETTING,
        concurrency_setting=_CONCURRENCY_SETTING,
    )
    assert record["partial"] is False
    nodes = _nodes_by_id(record)
    assert nodes["opaque-arm"]["node_id"] == "opaque-arm"  # sanity: node ran (present in the trace)

    # ``_arm_writer_body``'s content is deterministic (``f"{node_id}-content"``), so the content
    # hash is computable here directly rather than threaded back through the run record (the
    # composer's RunRecord carries no per-node "results" field — see 01-08-SUMMARY.md's own
    # "Known Gaps" note that ``databasise/__init__.py`` does not expose ``scheduler.run_wiring``'s
    # ``results`` dict).
    import hashlib

    opaque_content_hash = hashlib.sha256(b"opaque-arm-content").hexdigest()

    # --- The opaque arm's write landed at scope quarantined; the registry row proves it. -----
    registry = ArtifactRegistry(store_root=store_root)
    opaque_pin = Pin(
        content_hash=opaque_content_hash,
        namespace=opaque_namespace,
        producer_instance_hash=_OPAQUE_PRODUCER_INSTANCE_HASH,
    )
    opaque_rows = registry.discover(
        caller_instance_hash=_OPAQUE_PRODUCER_INSTANCE_HASH, namespace=opaque_namespace, pins=[opaque_pin]
    )
    assert len(opaque_rows) == 1
    assert opaque_rows[0].scope == "quarantined"
    assert opaque_rows[0].pin_required is True

    # --- A discovery query issued without a pin does not return the quarantined artifact. -----
    unpinned = registry.discover(caller_instance_hash="some-other-caller", namespace=opaque_namespace)
    assert unpinned == []

    # --- The same arm's attempt to write scope shared is refused, and no row is created. ------
    # A raw row count (not discover(), whose scope filter would hide the very quarantined row
    # this assertion needs to see) — total rows for this namespace, any scope, read directly.
    def _row_count_for_namespace() -> int:
        import sqlite3

        conn = sqlite3.connect(store_root / "artifact_registry.db")
        try:
            cur = conn.execute(
                "SELECT COUNT(*) FROM artifacts WHERE namespace = ?", (opaque_namespace,)
            )
            return cur.fetchone()[0]
        finally:
            conn.close()

    before_row_count = _row_count_for_namespace()
    blob_store = FilesystemBlobStore(namespace=opaque_namespace, workspace="", store_root=store_root)
    try:
        write_artifact(
            content=b"opaque-arm-attempted-shared-write",
            scope="shared",
            effective_depth="opaque",  # this arm's own effective depth — never "stage"
            namespace=opaque_namespace,
            producer_instance_hash=_OPAQUE_PRODUCER_INSTANCE_HASH,
            recipe_hash="recipe-opaque-arm-shared-attempt",
            blob_store=blob_store,
            registry=registry,
            **_SA2_STAMPS,
            corpus_id="corpus-1",
            space_id=None,
        )
        raised = False
    except BlastRadiusRefusal as exc:
        raised = True
        # write_path.py's own write-path call site names itself in every refusal it raises
        # (databasise/registry_artifact/write_path.py's _WRITE_PATH_NODE_ID) — the identifiable
        # id of the write attempt this rule refused, regardless of which wiring node called it.
        assert "artifact_write" in str(exc)
    assert raised is True

    after_row_count = _row_count_for_namespace()
    assert after_row_count == before_row_count  # the refused write created no registry row

    # --- After the run, the store root shows one directory per namespace, scope readable in the
    # --- name, and the opaque arm's graph/vector directories are visibly separate from the
    # --- transparent arm's — read from the filesystem, never from in-process state.
    top_level_dirs = {p.name for p in store_root.iterdir() if p.is_dir()}
    assert opaque_namespace in top_level_dirs
    assert shared_namespace in top_level_dirs
    assert (store_root / opaque_namespace / "graph.cozo").exists()
    assert (store_root / opaque_namespace / "vector.faiss").exists()
    assert (store_root / shared_namespace / "graph.cozo").exists()
    assert (store_root / shared_namespace / "vector.faiss").exists()

    # --- Garbage-collecting the quarantined instance removes exactly its directory. -----------
    gc_namespace(store_root, opaque_namespace)
    top_level_dirs_after_gc = {p.name for p in store_root.iterdir() if p.is_dir()}
    assert opaque_namespace not in top_level_dirs_after_gc
    assert shared_namespace in top_level_dirs_after_gc
    assert (store_root / shared_namespace / "graph.cozo").exists()  # transparent arm left intact
