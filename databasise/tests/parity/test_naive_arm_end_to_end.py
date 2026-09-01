"""End-to-end coverage for 03-04-PLAN.md Task 2: arm resolution conformance against each patch
file's own ``resulting_node_id_set``, the fail-closed removal guarantee, ``parse_wiring``
acceptance for the ``naive`` arm, and a full seven-node ``naive`` run.

The stub-client run (``test_naive_arm_full_run_against_a_synthetic_store_with_stub_clients``) is
the non-negotiable one: it builds its own synthetic imported-store shape directly through the v2
stores' own public write paths (no ``v1/`` venv, no network) and must pass on any machine. The
live-endpoint run at the bottom is skip-guarded exactly like ``test_import_verification.py``'s own
real-build test — it exercises this same path for real once the plan 03-02 artifacts and
``v1/.env.parity`` exist on a given machine.
"""

from __future__ import annotations

import jsonpatch
import numpy as np
import pytest
from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.parts.registry import default_registry
from databasise.parity.run_arm import _inject_query, run_arm
from databasise.parity.run_comparison import _inject_pinned_keywords
from databasise.runner import scheduler
from databasise.runner.trace import TokenAccounting
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import FaissVectorStore
from databasise.validator.parse import parse_wiring
from databasise.wirings.resolve import declared_node_ids, load_base, resolve_arm, resolved_node_ids

_ALL_ARMS = ("naive", "bypass", "hybrid", "local", "global")


# --------------------------------------------------------------------------------------------- #
# Arm resolution conformance
# --------------------------------------------------------------------------------------------- #


@pytest.mark.parametrize("arm_name", _ALL_ARMS)
def test_resolved_node_ids_match_the_patch_files_own_resulting_node_id_set(arm_name):
    assert resolved_node_ids(arm_name) == set(declared_node_ids(arm_name))


def test_naive_arm_resolves_to_exactly_the_seven_documented_nodes():
    assert resolved_node_ids("naive") == {
        "embedder-query",
        "chunk-vector",
        "heading-backfill",
        "rerank",
        "assemble",
        "generate",
        "embedder-index",
    }


def test_bypass_arm_resolves_to_exactly_generate():
    assert resolved_node_ids("bypass") == {"generate"}


def test_a_patch_removing_a_node_absent_from_the_base_raises_rather_than_succeeding():
    """The fail-closed subtraction guarantee ``databasise/wirings/resolve.py`` exists to
    preserve: ``jsonpatch`` itself raises for a ``remove`` whose target does not exist, and
    ``resolve.py`` never catches or downgrades that.
    """
    base = load_base()
    bad_patch = [{"op": "remove", "path": "/nodes/does-not-exist-in-the-base"}]

    with pytest.raises(jsonpatch.JsonPatchConflict):
        jsonpatch.apply_patch(base, bad_patch)


# --------------------------------------------------------------------------------------------- #
# parse_wiring acceptance
# --------------------------------------------------------------------------------------------- #


def test_naive_arm_parses_clean_against_the_default_registry():
    registry = default_registry()
    parsed = parse_wiring(resolve_arm("naive"), registry)
    assert parsed.report.ok, [v.code for v in parsed.report.violations]


def test_bypass_arm_parses_clean_against_the_default_registry():
    registry = default_registry()
    parsed = parse_wiring(resolve_arm("bypass"), registry)
    assert parsed.report.ok, [v.code for v in parsed.report.violations]


def test_base_wiring_shape_recipe_and_derived_field_removal():
    """criterion 1's index-recipe identification and the derived-field removal, both asserted."""
    base = load_base()
    assert base["recipe"] == {"embedding": "embedder-index"}
    assert "artifact_scope" not in base["nodes"]["embedder-index"]
    assert len(base["nodes"]) == 18


# --------------------------------------------------------------------------------------------- #
# Stub-client double: the non-negotiable, runs-on-any-machine full run
# --------------------------------------------------------------------------------------------- #


class _StubEmbeddingClient:
    def __init__(self, vector: list[float]):
        self.vector = vector
        self.call_count = 0

    async def embed(self, texts, **kwargs):
        self.call_count += 1
        return EmbeddingResult(
            vectors=[self.vector for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


class _StubLLMClient:
    async def chat(self, messages, **kwargs):
        return ChatResult(
            text="This is a stub completion for the naive arm's end-to-end test.",
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


@pytest.fixture
async def synthetic_naive_store(store_root):
    """A minimal, synthetic imported-store shape at the ``chunks``/``text_chunks`` kinds
    ``databasise/parity/run_arm.py`` reads — built directly through the v2 stores' own public
    write paths (``FaissVectorStore.upsert``, ``SqliteKVStore.upsert``), never a file copy or a
    real v1 build. One chunk, one query-matching direction, enough for a full seven-node dispatch.
    """
    workspace = "naive-e2e-test"
    query_vector = [1.0, 0.0, 0.0]

    vector_store = FaissVectorStore(namespace="chunks", workspace=workspace, store_root=store_root)
    await vector_store.upsert(
        ids=["chunk-1"],
        embeddings=np.array([query_vector]),
        metadatas=[{"content": "Ed Wood directed several low-budget films."}],
    )
    await vector_store.index_done_callback()

    kv_store = SqliteKVStore(namespace="text_chunks", workspace=workspace, store_root=store_root)
    await kv_store.upsert(
        {"chunk-1": {"content": "Ed Wood directed several low-budget films.", "file_path": "ed_wood.txt"}}
    )
    await kv_store.index_done_callback()

    return {"store_root": store_root, "workspace": workspace, "query_vector": query_vector}


async def test_naive_arm_full_run_against_a_synthetic_store_with_stub_clients(
    synthetic_naive_store, assert_valid_trace
):
    embedding_client = _StubEmbeddingClient(vector=synthetic_naive_store["query_vector"])
    llm_client = _StubLLMClient()

    result = await run_arm(
        "naive",
        "Which films did Ed Wood direct?",
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients={"embedding": embedding_client, "llm": llm_client},
    )

    run_record = result["run_record"]
    assert_valid_trace(run_record)
    assert run_record["partial"] is False
    assert run_record["arm_id"] == "naive"

    node_ids = {node["node_id"] for node in run_record["nodes"]}
    assert node_ids == {
        "embedder-query",
        "chunk-vector",
        "heading-backfill",
        "rerank",
        "assemble",
        "generate",
        "embedder-index",
    }

    by_id = {node["node_id"]: node for node in run_record["nodes"]}
    assert by_id["embedder-query"]["tokens"]["call_count"] > 0
    assert by_id["generate"]["tokens"]["call_count"] > 0
    assert by_id["generate"]["tokens"]["prompt_tokens"] + by_id["generate"]["tokens"]["completion_tokens"] > 0

    assert result["provided"]["generate"]["completion"]


# --------------------------------------------------------------------------------------------- #
# CR-01 regression: embedder-query embeds the real query text for the hybrid arm's scheduler run
# --------------------------------------------------------------------------------------------- #


class _SpyEmbeddingClient:
    """Records every text list it is asked to embed, for CR-01's non-empty/query-text assertion."""

    def __init__(self, vector: list[float]):
        self.vector = vector
        self.calls: list[list[str]] = []

    async def embed(self, texts, **kwargs):
        self.calls.append(list(texts))
        return EmbeddingResult(
            vectors=[self.vector for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="spy-embed"),
            resolved_model_identity="spy-embed-model",
        )


async def test_hybrid_arm_embedder_query_embeds_the_real_query_text_via_run_wiring():
    """CR-01 regression: with ``keywords`` pinned (no LLM call) and a spy embedding client, the
    resolved ``hybrid`` arm — driven through the real ``databasise.runner.scheduler.run_wiring``
    path, not a hand-built ``NodeContext`` — must have its ``embedder-query`` node embed the
    actual query text, not the empty string ``keywords.py``'s pre-fix output shape produced for
    every arm keeping the ``keywords`` node. Downstream nodes (``entity-lookup``/
    ``relation-lookup``, ...) have no store access in this test and are expected to fail with
    ``StoreNotWiredError`` — the run is scored ``partial``, per this module's own "partial
    outcomes are never discarded" contract — but ``embedder-query``'s own result is captured
    before that failure, which is what this test asserts against.
    """
    query = "Which films did Ed Wood direct?"
    spy = _SpyEmbeddingClient(vector=[1.0, 0.0, 0.0])

    resolved = resolve_arm("hybrid")
    resolved = _inject_query(resolved, query)
    resolved = _inject_pinned_keywords(resolved, hl_keywords=["film direction"], ll_keywords=["Ed Wood"])

    registry = default_registry()
    parsed = parse_wiring(resolved, registry)
    assert parsed.report.ok, [v.code for v in parsed.report.violations]

    result = await scheduler.run_wiring(
        parsed,
        registry,
        stores={},
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
        clients={"embedding": spy},
    )

    embedder_query_output = result["results"]["embedder-query"]
    assert embedder_query_output["query"] == query
    assert embedder_query_output["query"] != ""
    assert spy.calls == [[query]]


# --------------------------------------------------------------------------------------------- #
# Real Task 2 build + live endpoints — skip-guarded, exercised only when both are present
# --------------------------------------------------------------------------------------------- #


async def test_real_naive_arm_run_against_the_imported_index_and_live_endpoints(
    v2_parity_store_dir, v1_env_parity_path, corpus_snapshot, assert_valid_trace
):
    query = corpus_snapshot.queries[0].question
    result = await run_arm("naive", query, env_path=v1_env_parity_path)

    run_record = result["run_record"]
    assert_valid_trace(run_record)
    assert run_record["partial"] is False

    by_id = {node["node_id"]: node for node in run_record["nodes"]}
    assert by_id["embedder-query"]["tokens"]["call_count"] > 0
    assert by_id["generate"]["tokens"]["call_count"] > 0
