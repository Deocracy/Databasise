"""Drives one real end-to-end arm run against the plan 03-02-imported v2 store namespace and the
plan 03-01 client primitives (03-04-PLAN.md Task 2's arm driver).

Deliberately does **not** call ``databasise.run_wiring`` (the public composer in
``databasise/__init__.py``): that composer hardcodes a single ``kv``-only store at a fixed
``TRACER_WORKSPACE``/``TRACER_KV_NAMESPACE`` pair (its own module docstring: "This tracer proves
the store lifecycle end-to-end with one hardcoded namespace/workspace pair"), which is exactly
wrong for a parity run that must read the real imported index. This module instead drives
``databasise.runner.scheduler.run_wiring`` directly — the same function the composer itself calls
— with its own kv/vector/graph store assembly at the namespace ``databasise.parity.import_index``
imported into, and stamps its own ``RunRecord`` the same way the composer does but with
``arm_id=arm_name`` (the composer always stamps ``arm_id="base"``).

Client construction reads ``v1/.env.parity`` (D-07's pinned run configuration, the same file
``v1/scripts/run_parity_ingest.py`` reads) through ``databasise.clients.builder`` (the one shipped
builder, shared with the ``databasise-rest`` launcher; its stdlib ``KEY=VALUE`` parser needs no
``python-dotenv`` dependency). The old underscore names are re-exported below. Both ``store_root``/
``workspace`` and ``clients`` accept an explicit override so a test can drive this module against
a synthetic store and a stub client double with no real index and no network reachable — the
stub-client path is the one every machine must be able to run (see
``databasise/tests/parity/test_naive_arm_end_to_end.py``).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
import uuid
from pathlib import Path
from typing import Any

# Re-exports (08-01, RUN-05): the builder moved to databasise.clients.builder; the old names stay
# bound here so every importer and monkeypatch seam keeps working, and the exception classes keep
# their identity.
# isort: off
from databasise.clients.builder import (  # noqa: F401
    BUILDER_REFUSALS,
    PROVIDER_ROUTING_ENV_KEY as _PROVIDER_ROUTING_ENV_KEY,
    REQUIRED_ENV_KEYS as _REQUIRED_ENV_KEYS,
    MissingParityEnvError,
    MissingParityEnvKeyError,
    UnparseableProviderRoutingError,
    UnsupportedRerankBindingError,
    build_clients as _build_clients,
    load_env_file as _load_env_file,
    parse_provider_routing_body as _parse_provider_routing_body,
)
# isort: on
from databasise.identity.canon import canonicalise
from databasise.parity import import_index
from databasise.parity.import_index import DEFAULT_STORE_ROOT
from databasise.parity.import_index import _import_workspace as _parity_workspace
from databasise.parts.registry import PartRegistry, default_registry
from databasise.runner import scheduler as _scheduler
from databasise.runner.trace import RunRecord
from databasise.store_lock import StoreLockedError, store_lock
from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import MultiNamespaceVectorStore
from databasise.validator.parse import parse_wiring
from databasise.wirings.resolve import resolve_arm

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_V1_ENV_PARITY = _REPO_ROOT / "v1" / ".env.parity"

# The v1-native per-kind names the imported store set is keyed by (databasise/parity/import_index.py).
_TEXT_CHUNKS_KIND = "text_chunks"
_GRAPH_KIND = "chunk_entity_relation"

_EXECUTOR_VERSION = "databasise@0.1.0"
_DETERMINISM_SETTING = "cache-bypassed"
_CONCURRENCY_SETTING = "sequential"


def _build_stores(
    store_root: Path, workspace: str, resolved: dict[str, Any] | None = None
) -> dict[str, Any]:
    """kv/vector/graph, all three, at the namespace plan 03-02 imported into — even an arm that
    touches only a subset (``naive`` never reaches ``graph``) gets every store wired, since
    ``CapabilityScopedStores`` already denies access to anything a node's own effects don't
    declare; wiring all three here once is simpler than special-casing per arm.

    ``"vector"`` binds a :class:`MultiNamespaceVectorStore`, not a single namespace's
    ``FaissVectorStore`` directly — one raw handle previously served every vector-reading node
    (``entity-lookup``, ``relation-lookup``, ``chunk-vector``, ``chunk-sel-kg``) the same ``chunks``
    index regardless of which namespace each position is actually defined over. Each of those
    parts now selects its own namespace (``entities``/``relationships``/``chunks``) off this handle
    before reading.

    06-01-PLAN.md: ``kv``/``graph`` read their namespace from the resolved wiring's own declared
    ``store_namespaces`` when ``resolved`` is supplied — the same declaration
    ``databasise.seam.engine._build_stores`` reads, so this harness and the seam cannot drift
    apart. Falls back to ``_TEXT_CHUNKS_KIND``/``_GRAPH_KIND`` (the values LightRAG's own base now
    declares under ``store_namespaces`` too) when ``resolved`` is absent.
    """
    store_namespaces = (resolved or {}).get("store_namespaces") or {}
    kv_namespace = store_namespaces.get("kv", _TEXT_CHUNKS_KIND)
    graph_namespace = store_namespaces.get("graph", _GRAPH_KIND)
    return {
        "kv": SqliteKVStore(namespace=kv_namespace, workspace=workspace, store_root=store_root),
        "vector": MultiNamespaceVectorStore(workspace=workspace, store_root=store_root),
        "graph": CozoGraphStore(namespace=graph_namespace, workspace=workspace, store_root=store_root),
    }


def _inject_query(resolved: dict[str, Any], query: str) -> dict[str, Any]:
    """Stamp the user's query text onto every resolved node whose config reads one
    (``keywords``, ``embedder-query``, ``generate`` — see those modules' own docstrings for why
    each needs its own copy rather than reading a sibling node's output). ``keywords`` was missing
    from this list before CR-01's fix: its own ``_keywords_body`` reads ``config.get("query", "")``
    directly, so without this stamp the query text it extracts keywords from (and — post CR-01 —
    the ``"query"`` it hands to ``embedder-query``) was always the empty string in every real run,
    not just when ``keywords`` is pinned. A no-op for a node the resolved arm does not contain
    (e.g. ``bypass`` removes ``embedder-query``, ``naive``/``bypass`` remove ``keywords``).
    """
    nodes = resolved.get("nodes", {})
    for node_id in ("keywords", "embedder-query", "generate"):
        if node_id not in nodes:
            continue
        config = dict(nodes[node_id].get("config") or {})
        config["query"] = query
        nodes[node_id]["config"] = config
    return resolved


# DEC-B (runner/scheduler.py): an absent config.token_allowance defaults to an allowance of 0, so
# every node this arm dispatches that declares calls_llm/calls_rerank/calls_embedding would
# budget-halt on its very first real token spent, truncating the run to whichever node(s)
# happened to be in the first ready batch (CONTRACT §9 traces that halt honestly rather than
# hiding it, but a one-node "run" is not what this tracer exists to prove). This driver is the
# one caller that actually needs the full arm to complete, so it is the one that sets a real,
# generous per-node allowance — never the published wiring itself (which stays byte-identical to
# the checked docs/system-model source, per databasise/wirings/lightrag/README.md's "three edits,
# and only these three").
_DEFAULT_TOKEN_ALLOWANCE = 1_000_000


def _inject_token_allowance(resolved: dict[str, Any], allowance: int) -> dict[str, Any]:
    """Set ``config.token_allowance`` on every resolved node that does not already declare one —
    an explicit per-node override in a future arm patch is never clobbered."""
    for node in resolved.get("nodes", {}).values():
        config = dict(node.get("config") or {})
        config.setdefault("token_allowance", allowance)
        node["config"] = config
    return resolved


async def run_arm(
    arm_name: str,
    query: str,
    *,
    registry: PartRegistry | None = None,
    store_root: Path | None = None,
    workspace: str | None = None,
    clients: dict[str, Any] | None = None,
    env_path: Path | None = None,
    token_allowance: int = _DEFAULT_TOKEN_ALLOWANCE,
) -> dict[str, Any]:
    """Resolve ``arm_name``, inject ``query`` and a per-node ``token_allowance``, wire it against
    the imported store namespace and the pinned OpenAI-compatible clients (unless overridden), and
    drive one real run through ``runner.scheduler.run_wiring`` directly.

    Returns ``{"run_record": <schema-valid dict>, "provided": {node_id: output, ...}}`` — the
    latter keyed by the resolved wiring's own ``provides`` list — or ``{"cycle": [...]}`` for a
    cyclic wiring (never reached by any of this phase's five arms, but the same contract
    ``databasise.run_wiring`` itself upholds).

    ``clients``/``store_root``/``workspace`` are override points for tests: passing them bypasses
    real client construction and the real imported-store lookup entirely, so a test can exercise
    this whole function with a stub client double and a synthetic store set — no network, no real
    index, runs on any machine.
    """
    if registry is None:
        registry = default_registry()

    resolved = resolve_arm(arm_name)
    resolved = _inject_query(resolved, query)
    resolved = _inject_token_allowance(resolved, token_allowance)
    parsed = parse_wiring(resolved, registry)

    resolved_workspace = workspace if workspace is not None else _parity_workspace()
    resolved_store_root = store_root if store_root is not None else DEFAULT_STORE_ROOT
    stores = _build_stores(resolved_store_root, resolved_workspace, resolved)

    resolved_clients = clients
    if resolved_clients is None:
        env = _load_env_file(env_path or DEFAULT_V1_ENV_PARITY)
        resolved_clients = _build_clients(env)

    try:
        scheduled = await _scheduler.run_wiring(
            parsed,
            registry,
            stores,
            determinism_setting=_DETERMINISM_SETTING,
            concurrency_setting=_CONCURRENCY_SETTING,
            clients=resolved_clients,
        )
    finally:
        for store in stores.values():
            await store.finalize()

    if "cycle" in scheduled:
        return {"cycle": scheduled["cycle"]}

    wiring_bytes = canonicalise(resolved)
    wiring_instance_hash = f"sha256:{hashlib.sha256(wiring_bytes).hexdigest()}"
    wiring_id = resolved.get("wiring_id") or (
        f"wiring:{hashlib.sha256(wiring_bytes).hexdigest()[:16]}"
    )

    record = RunRecord(
        run_id=str(uuid.uuid4()),
        wiring_id=wiring_id,
        wiring_instance_hash=wiring_instance_hash,
        arm_id=arm_name,
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
    return {"run_record": record.to_dict(), "provided": provided}


def main(argv: list[str] | None = None) -> int:
    """``uv run python -m databasise.parity.run_arm --arm naive --query "..."`` — prints the run
    record as JSON and the ``provides`` node's output, following the committed-and-re-runnable
    evidence style ``databasise/evidence/falsifier2.py`` establishes.
    """
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", required=True, choices=["naive", "bypass", "hybrid", "local", "global"])
    parser.add_argument("--query", required=True)
    args = parser.parse_args(argv)

    try:
        with store_lock(import_index.DEFAULT_STORE_ROOT):  # D-03
            result = asyncio.run(run_arm(args.arm, args.query))
    except (StoreLockedError, *BUILDER_REFUSALS) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
