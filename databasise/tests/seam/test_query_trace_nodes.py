"""11-10 Task 2 (LRAG-19, D-04, research Q4): ``embedder-index`` is the wiring's index recipe
(``recipe.embedding``), so query runs skip it: no arm's trace carries the node or spend from it.
It stays in every resolved wiring, so recipe identity, promotion classing and RUN-11 keep their
inputs, and the trace's wiring identity is still derived from the full resolved wiring.
"""

from __future__ import annotations

import hashlib
import json

import pytest
from databasise.clients.builder import build_clients
from databasise.identity.canon import canonicalise
from databasise.seam import engine as engine_module
from databasise.seam.corpus import IngestDocument
from databasise.seam.engine import Databasise
from databasise.seam.query import QueryObject
from databasise.tests.fixtures.v1_stub_server import (  # noqa: F401 - fixture
    real_v1,
    requires_v1,
)
from databasise.tests.seam._probes import counting_clients
from databasise.wirings.resolve import load_base, resolve_arm

_RECIPE_NODE = "embedder-index"
_QUERY_ARMS = ("naive", "hybrid", "local", "global")
_WS = "lrag-trace-nodes"
_TEXT = "UNIQalpha Corp builds bridges in UNIQalpha City."
_QUESTION = "What does UNIQalpha Corp build in UNIQalpha City?"


def _expected_instance_hash(arm: str, question: str) -> str:
    resolved = engine_module._inject_query(resolve_arm(arm), question)
    resolved = engine_module._inject_token_allowance(resolved, engine_module._DEFAULT_TOKEN_ALLOWANCE)
    return f"sha256:{hashlib.sha256(canonicalise(resolved)).hexdigest()}"


async def _assert_recipe_node_absent(engine: Databasise, arm: str, question: str) -> None:
    envelope = await engine._execute_resolved(QueryObject(text=question), resolve_arm(arm))
    trace = await engine.resolve_trace(envelope.trace_token, debug=True)

    node_ids = [node["node_id"] for node in trace["nodes"]]
    assert _RECIPE_NODE not in node_ids, (arm, node_ids)
    assert node_ids, arm
    # Spend comes only from the nodes the trace lists, none of which is the recipe node.
    spent = sum(entry.call_count for entry in envelope.token_accounting)
    assert spent == sum(node["tokens"]["call_count"] for node in trace["nodes"]), arm
    assert trace["wiring_instance_hash"] == _expected_instance_hash(arm, question), arm


@pytest.mark.parametrize("arm", _QUERY_ARMS)
def test_every_query_arm_still_lists_the_recipe_node(arm):
    resolved = resolve_arm(arm)
    assert _RECIPE_NODE in resolved["nodes"]
    assert resolved["recipe"] == {"embedding": _RECIPE_NODE}


def test_the_base_recipe_still_names_the_index_embedder():
    assert load_base()["recipe"] == {"embedding": _RECIPE_NODE}


def test_without_recipe_only_nodes_drops_only_an_undepended_recipe_node():
    resolved = resolve_arm("hybrid")
    run_copy = engine_module._without_recipe_only_nodes(resolved)

    assert set(run_copy["nodes"]) == set(resolved["nodes"]) - {_RECIPE_NODE}
    assert _RECIPE_NODE in resolved["nodes"]  # the full wiring is left untouched

    depended = json.loads(json.dumps(resolved))
    depended["nodes"]["generate"]["deps"] = [*depended["nodes"]["generate"]["deps"], _RECIPE_NODE]
    assert _RECIPE_NODE in engine_module._without_recipe_only_nodes(depended)["nodes"]


async def test_a_naive_query_on_a_populated_store_dispatches_no_recipe_node(synthetic_naive_store):
    engine = Databasise(
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients=counting_clients(synthetic_naive_store["query_vector"]),
    )
    await _assert_recipe_node_absent(engine, "naive", "Which films did Ed Wood direct?")


@requires_v1
async def test_no_lightrag_query_arm_traces_the_recipe_node_after_a_real_ingest(real_v1):  # noqa: F811
    engine = Databasise(
        store_root=real_v1.store_root, workspace=_WS, clients=build_clients(real_v1.client_env)
    )
    job = await engine.ingest(IngestDocument(document_id="tracedoc1", text=_TEXT))
    assert job.enqueued == 1

    for arm in _QUERY_ARMS:
        await _assert_recipe_node_absent(engine, arm, _QUESTION)
