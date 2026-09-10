"""EMBED-01's smoke test: databasise installs and runs as a single self-contained process tree.

Covers plan 01-09 Task 1's <behavior> Tests 1-8. Process state is observed directly through
kernel interfaces (``/proc/self/task`` for threads/children, ``/proc/self/net/tcp{,6}`` for
listening sockets) rather than through a third-party process-inspection library — no such
dependency is added for this test module (its own acceptance criterion greps this file for that
library's name and expects zero matches).
"""

from __future__ import annotations

import inspect
import subprocess
import sys
import textwrap
from importlib.metadata import distribution

import pytest

# A wiring touching only the tracer's kv-writer/passthrough parts — SqliteKVStore never dispatches
# through loop.run_in_executor, so this wiring is safe for the "no new OS thread" claims (Tests 1
# and 4). Tests exercising graph/vector (which DO use run_in_executor internally) are scoped to
# Test 6 alone, which makes no thread-count claim.
_KV_ONLY_WIRING = {
    "nodes": {
        "produce": {"component": "core/passthrough@1.0.0", "kind": "stage", "deps": []},
        "store": {
            "component": "core/kv-writer@1.0.0",
            "kind": "stage",
            "effects": ["writes_kv"],
            "config": {"note": "embed-startup-smoke"},
            "deps": ["produce"],
        },
    }
}


def _task_count() -> int:
    """Thread/task count for this process, read from the kernel's own per-process task
    directory — the OS-level signal a spawned child process or thread would grow.
    """
    import os

    return len(os.listdir("/proc/self/task"))


def _listening_socket_count() -> int:
    """Count of sockets in the LISTEN state (hex code ``0A``) owned by this process, read
    directly from the kernel's own TCP tables for both address families.
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


def test_1_importing_the_package_spawns_no_child_process_or_thread():
    """Test 1: importing from a clean interpreter succeeds and the task count is unchanged."""
    script = textwrap.dedent(
        """
        import os

        def _task_count():
            return len(os.listdir("/proc/self/task"))

        before = _task_count()
        import databasise  # noqa: F401
        after = _task_count()

        assert after <= before, f"task count grew across import: {before} -> {after}"
        print("OK")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    assert result.stdout.strip() == "OK"


async def test_2_after_a_complete_wiring_run_no_new_listening_socket_is_owned(store_root):
    """Test 2: after import + a complete run, the listening-socket count has not grown. (A
    universal absolute zero is not asserted: the shared netns this process runs in may already
    show a pre-existing listening socket unrelated to databasise — the claim under test is that
    running a wiring adds none of its own.)
    """
    import databasise

    before = _listening_socket_count()
    await databasise.run_wiring(
        _KV_ONLY_WIRING,
        store_root=store_root,
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
    )
    after = _listening_socket_count()

    assert after <= before, f"listening socket count grew: {before} -> {after}"


async def test_3_every_path_under_the_store_root_is_a_regular_file_or_directory(store_root):
    """Test 3: no socket file, no named pipe among anything the run wrote under the store root —
    ``Path.is_file()``/``Path.is_dir()`` are false for a socket or FIFO, so requiring every path
    satisfy one of the two already proves neither is present.
    """
    import databasise

    await databasise.run_wiring(
        _KV_ONLY_WIRING,
        store_root=store_root,
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
    )

    paths = list(store_root.rglob("*"))
    assert paths, "the run wrote nothing under the store root"
    for path in paths:
        assert path.is_file() or path.is_dir(), f"{path} is neither a regular file nor a directory"


async def test_4_no_container_runtime_is_invoked_across_a_complete_run(store_root):
    """Test 4: the child/task count before and after a complete run is equal — no container
    runtime (which would show up as a new child process) was invoked.
    """
    import databasise

    before = _task_count()
    await databasise.run_wiring(
        _KV_ONLY_WIRING,
        store_root=store_root,
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
    )
    after = _task_count()

    assert after == before, f"task count changed across a complete run: {before} -> {after}"


def test_5_the_declared_runtime_dependency_set_is_exactly_nine_and_none_is_a_db_client():
    """Test 5: read from the installed distribution's own metadata, not the project file — the
    claim is about the environment that actually runs. Phase 1's set of four grew to six in
    Phase 3 (03-01-PLAN.md Task 2): ``openai`` (D-06/D-07's LLM/embedding client primitive) and
    ``jsonpatch`` (D-13's RFC 6902 arm-patch application) are both new runtime dependencies, both
    approved through the package-legitimacy gate (03-01-SUMMARY.md). 06-01-PLAN.md grew the set to
    eight: ``igraph`` (whole-graph personalized PageRank, HippoRAG 2's ``ppr`` node) and ``numpy``
    (dense array math, ``reset-vector-join``/``ppr``) — both approved through the package-legitimacy
    gate (06-CHECKPOINT-ANSWERS.md), both landing in core per that checkpoint's own Open Question 4
    answer (HippoRAG 2 is a first-class modality, not an optional transport). 06-06-PLAN.md Task 1
    grew the set to nine: ``scipy`` (RIG §AA.1's paired bootstrap, MACH-03's A/A calibration) —
    also approved through the package-legitimacy gate (06-CHECKPOINT-ANSWERS.md 06-01 Task 1).

    04-05 (D-15): ``dist.requires`` now also lists the optional ``rest`` extra's own dependencies
    (``fastapi``, ``uvicorn``) — ``importlib.metadata`` includes every ``[project.optional
    -dependencies]`` entry in ``Requires-Dist``, each marked with its own ``; extra == "..."``
    environment marker. Those are excluded from the *unconditional* count below by construction
    (an extra-gated requirement is, by definition, not installed unless a consumer opts in) —
    this is the metadata-level proof of D-15's own claim that the embedded library's mandatory
    dependency set is unchanged by adding the optional REST transport.

    05-04-PLAN.md Task 2: a second optional extra, ``mcp`` (API-07's own optional dependency,
    ``mcp>=2.2.0``), joined ``rest`` — the assertion below widened from "every conditional
    requirement names the ``rest`` extra" to "every conditional requirement names a known optional
    extra", since a second legitimately-optional extra is not a violation of D-15's own claim
    (neither extra is ever installed unless a consumer opts in).
    """
    dist = distribution("databasise")
    requires = dist.requires or []

    unconditional = [req for req in requires if "extra ==" not in req]
    assert len(unconditional) == 9, f"expected exactly 9 unconditional runtime dependencies, got {unconditional}"

    names = {req.split(";")[0].split("[")[0].split("=")[0].split("<")[0].split(">")[0].strip().lower() for req in unconditional}
    assert names == {
        "pycozo", "faiss-cpu", "rfc8785", "pydantic", "openai", "jsonpatch", "igraph", "numpy", "scipy",
    }

    # D-15: every optional extra's own dependencies exist in the metadata, but only as
    # extra-gated (never unconditional) requirements — never installed unless a consumer opts in.
    conditional = [req for req in requires if "extra ==" in req]
    assert conditional, "expected the optional extras' dependencies to appear as extra-gated Requires-Dist entries"
    known_extras = {'extra == "rest"', 'extra == "mcp"'}
    assert all(any(marker in req for marker in known_extras) for req in conditional), conditional

    _separate_server_clients = ("psycopg", "pymongo", "redis", "neo4j", "pymilvus", "qdrant", "opensearch")
    for name in names:
        assert not any(client in name for client in _separate_server_clients), (
            f"{name!r} looks like a client for a separately-hosted database server"
        )


async def test_6_all_three_store_engines_are_reachable_with_no_network_constructor_params(store_root):
    """Test 6: a graph write, a vector upsert and a KV write all succeed inside one process, and
    none of the five store adapter constructors accepts a host/port/connection-string parameter.
    """
    from databasise.stores.blob import FilesystemBlobStore
    from databasise.stores.graph import CozoGraphStore
    from databasise.stores.kv import SqliteKVStore
    from databasise.stores.lexical import SqliteLexicalStore
    from databasise.stores.vector import FaissVectorStore

    graph = CozoGraphStore(namespace="ns", workspace="ws", store_root=store_root)
    vector = FaissVectorStore(namespace="ns", workspace="ws", store_root=store_root)
    kv = SqliteKVStore(namespace="ns", workspace="ws", store_root=store_root)

    await graph.upsert_node("n1", {"label": "x"})
    await graph.index_done_callback()
    assert await graph.has_node("n1")

    await vector.upsert(["v1"], [[1.0, 0.0, 0.0]])
    await vector.index_done_callback()
    results = await vector.query([1.0, 0.0, 0.0], top_k=1)
    assert results and results[0]["id"] == "v1"

    await kv.upsert({"k1": {"value": 1}})
    await kv.index_done_callback()
    stored = await kv.get_by_id("k1")
    assert stored is not None and stored["value"] == 1

    await graph.finalize()
    await kv.finalize()

    forbidden_params = {"host", "port", "connection_string", "dsn", "uri", "url"}
    for cls in (CozoGraphStore, FaissVectorStore, SqliteKVStore, SqliteLexicalStore, FilesystemBlobStore):
        params = set(inspect.signature(cls.__init__).parameters)
        overlap = params & forbidden_params
        assert not overlap, f"{cls.__name__}.__init__ accepts network parameter(s): {overlap}"


def test_7_a_forced_graph_store_load_failure_names_the_store_and_instantiates_no_alternative(
    store_root, monkeypatch
):
    """Test 7 (no-silent-fallback): forcing the graph store's construction to fail raises an
    error naming that specific embedded store, and no alternative store class is instantiated
    during the failure.
    """
    import databasise.stores.graph as graph_module
    import databasise.stores.kv as kv_module
    import databasise.stores.vector as vector_module

    def _boom(*_args, **_kwargs):
        raise RuntimeError("simulated CozoGraphStore graph-store construction failure")

    monkeypatch.setattr(graph_module, "CozoClient", _boom)

    instantiated: dict[str, bool] = {"vector": False, "kv": False}
    original_vector_init = vector_module.FaissVectorStore.__init__
    original_kv_init = kv_module.SqliteKVStore.__init__

    def _tracking_vector_init(self, *args, **kwargs):
        instantiated["vector"] = True
        return original_vector_init(self, *args, **kwargs)

    def _tracking_kv_init(self, *args, **kwargs):
        instantiated["kv"] = True
        return original_kv_init(self, *args, **kwargs)

    monkeypatch.setattr(vector_module.FaissVectorStore, "__init__", _tracking_vector_init)
    monkeypatch.setattr(kv_module.SqliteKVStore, "__init__", _tracking_kv_init)

    with pytest.raises(RuntimeError) as exc_info:
        graph_module.CozoGraphStore(namespace="ns", workspace="ws", store_root=store_root)

    assert "graph" in str(exc_info.value).lower() or "cozo" in str(exc_info.value).lower()
    assert instantiated["vector"] is False
    assert instantiated["kv"] is False


def test_8_execution_mode_is_derived_and_a_heavier_placement_refuses_hosting_by_name():
    """Test 8: EMBED-01's own derivation clause — a node whose declared effects imply a heavier
    placement derives it and refuses hosting by name, even though only in-process is implemented.
    """
    from databasise.validator.execution_mode import (
        UnimplementedPlacementError,
        derive_execution_mode,
        host,
    )

    mode = derive_execution_mode(["net"], "stage")
    assert mode == "long-lived-service"

    with pytest.raises(UnimplementedPlacementError):
        host(mode)

    # And the one placement Phase 1 does implement is unaffected by this refusal path.
    assert derive_execution_mode([], "stage") == "in-process"
    host("in-process")  # succeeds, no exception
