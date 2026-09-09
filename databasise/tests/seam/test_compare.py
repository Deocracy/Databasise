"""06-03-PLAN.md Task 1: API-08's comparison surface (``Databasise.compare`` /
``databasise.seam.compare.compare_arms``) — one query object and N selectors return N envelopes
keyed by the caller's own selector values, through the identical ``_execute()`` path ``query()``
already uses, with no verdict and no internal identity anywhere in the response.

Drives a real two-arm comparison against LightRAG's naive arm and HippoRAG's base wiring, seeded
manually under one shared ``store_root``/workspace — mirroring
``databasise/tests/seam/conftest.py``'s own ``synthetic_naive_store`` and
``databasise/tests/parts_core/hipporag/conftest.py``'s own ``seeded_hipporag_store`` combined, so
one ``Databasise`` engine instance can resolve both arms for a real comparison call. RIG
§RUN.1/§RUN.2's own isolation guarantee already keeps the two arms' on-disk state disjoint (proven
by ``tests/seam/test_store_isolation.py``), so seeding both under one workspace is safe — never a
file copy, never a real network call.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.parts.registry import default_registry
from databasise.runner.trace import TokenAccounting
from databasise.seam import Databasise, QueryObject
from databasise.seam.compare import CAPABILITY_KEY_SEPARATOR, compare_arms
from databasise.seam.envelope import ResponseEnvelope
from databasise.seam.redact import assert_no_forbidden_keys, assert_no_forbidden_values
from databasise.seam.refusals import EmptyComparisonRequestError, UnsatisfiableSelectorError
from databasise.seam.selectors import _INSTANCE_HASH_PATTERN, Selector
from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import FaissVectorStore
from databasise.wirings.resolve import load_wiring, resolve_arm

_QUERY_TEXT = "What sat on the mat?"
_WORKSPACE = "compare-test"
_QUERY_VECTOR = [1.0, 0.0, 0.0]

# The naive arm's own smallest-satisfying capability — databasise/seam/selectors.py's own
# smallest-resolved-wiring-wins tie-break picks naive's 7 nodes over hybrid/local/global's 15-17
# and HippoRAG's own 8 for this capability set (verified this session: only naive/hybrid/local/
# global/hipporag declare reads_vector at all, and naive is the smallest of those).
_LIGHTRAG_CAPABILITY = ["reads_vector"]
# Mirrors test_cross_modality_run.py's own choice: only HippoRAG's 8-node wiring satisfies this at
# the smallest resolved size.
_HIPPORAG_CAPABILITY = ["reads_graph", "reads_kv"]

# §5's closed eight-verdict vocabulary (docs/system-model/CONTRACT.md §5, quoted in this plan's own
# must-have truths) — no promote/reject/adjudication verb belongs anywhere in an inspection-only
# comparison response (RIG.md ## §RUN.4).
_VERDICT_VOCABULARY = (
    "promote",
    "reject",
    "inconclusive",
    "insufficient-depth",
    "below-floor",
    "unconfirmed",
    "regression-veto",
    "straddle",
)


class _StubEmbeddingClient:
    def __init__(self, vector: list[float]):
        self.vector = vector

    async def embed(self, texts, **kwargs):
        return EmbeddingResult(
            vectors=[self.vector for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


class _StubLLMClient:
    """Serves both arms with one fixed response: HippoRAG's ``fact-filter`` node reads
    ``keep_ids`` out of the JSON text; LightRAG's ``generate`` node uses whatever text comes back
    as its own completion unchanged. Neither test in this module asserts on the answer's exact
    content beyond presence, so one shared stub covers both arms' happy paths."""

    async def chat(self, messages, **kwargs):
        return ChatResult(
            text=json.dumps({"keep_ids": ["f1", "f2"]}),
            tokens=TokenAccounting(
                prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"
            ),
            resolved_model_identity="stub-llm-model",
        )


@pytest.fixture
async def dual_arm_store(store_root):
    """Seeds LightRAG's naive-arm store (mirrors ``tests/seam/conftest.py``'s own
    ``synthetic_naive_store``) and HippoRAG's base-wiring store (mirrors
    ``tests/parts_core/hipporag/conftest.py``'s own ``seeded_hipporag_store``) under one shared
    ``store_root``/workspace, so one ``Databasise`` engine instance can resolve both arms."""
    lightrag_vector = FaissVectorStore(namespace="chunks", workspace=_WORKSPACE, store_root=store_root)
    await lightrag_vector.upsert(
        ids=["chunk-1"],
        embeddings=np.array([_QUERY_VECTOR]),
        metadatas=[{"content": "Ed Wood directed several low-budget films."}],
    )
    await lightrag_vector.index_done_callback()
    await lightrag_vector.finalize()

    lightrag_kv = SqliteKVStore(namespace="text_chunks", workspace=_WORKSPACE, store_root=store_root)
    await lightrag_kv.upsert(
        {"chunk-1": {"content": "Ed Wood directed several low-budget films.", "file_path": "ed_wood.txt"}}
    )
    await lightrag_kv.index_done_callback()
    await lightrag_kv.finalize()

    graph_store = CozoGraphStore(namespace="hipporag-graph", workspace=_WORKSPACE, store_root=store_root)
    await graph_store.upsert_node("entity:cat", {})
    await graph_store.upsert_node("entity:mat", {})
    await graph_store.upsert_node("entity:sat", {})
    await graph_store.upsert_node("chunk:c1", {})
    await graph_store.upsert_node("chunk:c2", {})
    await graph_store.upsert_edge("entity:cat", "entity:mat", {"weight": 2.0})
    await graph_store.upsert_edge("entity:mat", "chunk:c1", {"weight": 1.0})
    await graph_store.upsert_edge("entity:cat", "chunk:c1", {"weight": 1.0})
    await graph_store.upsert_edge("chunk:c1", "chunk:c2", {"weight": 0.5})
    await graph_store.upsert_edge("entity:sat", "chunk:c2", {"weight": 1.0})
    await graph_store.index_done_callback()
    await graph_store.finalize()

    facts_store = FaissVectorStore(namespace="hipporag-facts", workspace=_WORKSPACE, store_root=store_root)
    await facts_store.upsert(
        ids=["f1", "f2"],
        embeddings=np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        metadatas=[
            {"entities": ["entity:cat", "entity:mat"]},
            {"entities": ["entity:sat"]},
        ],
    )
    await facts_store.index_done_callback()
    await facts_store.finalize()

    chunks_store = FaissVectorStore(namespace="hipporag-chunks", workspace=_WORKSPACE, store_root=store_root)
    await chunks_store.upsert(
        ids=["chunk:c1", "chunk:c2"],
        embeddings=np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        metadatas=[{}, {}],
    )
    await chunks_store.index_done_callback()
    await chunks_store.finalize()

    hipporag_kv = SqliteKVStore(namespace="hipporag-text-chunks", workspace=_WORKSPACE, store_root=store_root)
    await hipporag_kv.upsert(
        {
            "fact:f1": {"chunk_ids": ["chunk:c1"]},
            "fact:f2": {"chunk_ids": ["chunk:c2"]},
            "chunk:c1": {"content": "Cats sit on mats."},
            "chunk:c2": {"content": "The cat sat on the mat again."},
        }
    )
    await hipporag_kv.index_done_callback()
    await hipporag_kv.finalize()

    return {"store_root": store_root, "workspace": _WORKSPACE}


def _make_engine(dual_arm_store) -> Databasise:
    return Databasise(
        store_root=dual_arm_store["store_root"],
        workspace=dual_arm_store["workspace"],
        clients={
            "embedding": _StubEmbeddingClient(vector=_QUERY_VECTOR),
            "llm": _StubLLMClient(),
        },
    )


async def test_keyed_by_selector(dual_arm_store):
    engine = _make_engine(dual_arm_store)
    selectors = [Selector(capability=_LIGHTRAG_CAPABILITY), Selector(capability=_HIPPORAG_CAPABILITY)]

    result = await engine.compare(QueryObject(text=_QUERY_TEXT), selectors)

    expected_keys = {
        CAPABILITY_KEY_SEPARATOR.join(_LIGHTRAG_CAPABILITY),
        CAPABILITY_KEY_SEPARATOR.join(_HIPPORAG_CAPABILITY),
    }
    assert set(result.keys()) == expected_keys
    for envelope in result.values():
        assert isinstance(envelope, ResponseEnvelope)


async def test_single_selector_is_a_run(dual_arm_store):
    engine = _make_engine(dual_arm_store)

    result = await engine.compare(
        QueryObject(text=_QUERY_TEXT), [Selector(capability=_LIGHTRAG_CAPABILITY)]
    )

    assert isinstance(result, ResponseEnvelope)
    assert not isinstance(result, dict)


async def test_zero_selectors_is_refused(dual_arm_store):
    engine = _make_engine(dual_arm_store)

    with pytest.raises(EmptyComparisonRequestError) as exc_info:
        await engine.compare(QueryObject(text=_QUERY_TEXT), [])

    message = str(exc_info.value)
    assert "EmptyComparisonRequestError" in message
    assert "lightrag" not in message.lower()
    assert "hipporag" not in message.lower()


async def test_no_verdict_leaks(dual_arm_store):
    engine = _make_engine(dual_arm_store)
    selectors = [Selector(capability=_LIGHTRAG_CAPABILITY), Selector(capability=_HIPPORAG_CAPABILITY)]

    result = await engine.compare(QueryObject(text=_QUERY_TEXT), selectors)
    serialized = json.dumps({key: envelope.model_dump() for key, envelope in result.items()})

    for verdict in _VERDICT_VOCABULARY:
        assert verdict not in serialized, f"forbidden verdict token {verdict!r} leaked into the comparison response"


async def test_no_internal_identity_leaks(dual_arm_store):
    engine = _make_engine(dual_arm_store)
    selectors = [Selector(capability=_LIGHTRAG_CAPABILITY), Selector(capability=_HIPPORAG_CAPABILITY)]

    result = await engine.compare(QueryObject(text=_QUERY_TEXT), selectors)

    # Derived live from the registry and the two resolved wirings at test time — never a
    # hand-written literal list (this plan's own acceptance criterion).
    registry = default_registry()
    lightrag_resolved = resolve_arm("naive")
    hipporag_resolved = load_wiring("hipporag")

    low_entropy: set[str] = {"provenance"}
    low_entropy.update(registry.keys())
    low_entropy.update(lightrag_resolved.get("nodes", {}).keys())
    low_entropy.update(hipporag_resolved.get("nodes", {}).keys())
    for resolved in (lightrag_resolved, hipporag_resolved):
        wiring_id = resolved.get("wiring_id")
        if wiring_id:
            low_entropy.add(str(wiring_id))
    low_entropy = {token for token in low_entropy if token}

    parsed = json.loads(json.dumps({key: envelope.model_dump() for key, envelope in result.items()}))

    assert_no_forbidden_keys(parsed, low_entropy)
    assert_no_forbidden_values(parsed, low_entropy)

    # Instance-hash-shaped values are high-entropy (never a real word) — a plain key/value-equality
    # walk above cannot catch one, since it would never coincidentally equal a short node id/wiring
    # id. Walked separately as a regex match over every string leaf.
    def _walk_for_instance_hash(obj: object) -> None:
        if isinstance(obj, dict):
            for value in obj.values():
                _walk_for_instance_hash(value)
        elif isinstance(obj, list):
            for item in obj:
                _walk_for_instance_hash(item)
        elif isinstance(obj, str):
            assert not _INSTANCE_HASH_PATTERN.match(obj), f"instance-hash-shaped value {obj!r} leaked"

    _walk_for_instance_hash(parsed)


async def test_selector_keys_are_not_normalised():
    """Two selectors whose values differ only in letter case produce two distinct keys and two
    separate runs — driven directly against ``compare_arms`` over a stub ``execute`` (rather than
    through real selector resolution, which would refuse an uppercase, unsatisfiable capability
    value before this behaviour could even be observed)."""
    lower = "reads_vector"
    upper = "READS_VECTOR"
    calls: list[str] = []

    async def _stub_execute(query_object: QueryObject, selector: Selector) -> ResponseEnvelope:
        del query_object
        calls.append(selector.capability[0])
        return ResponseEnvelope(answer="", depth_label="stage", partial=False, degraded=False)

    result = await compare_arms(
        _stub_execute,
        QueryObject(text=_QUERY_TEXT),
        [Selector(capability=[lower]), Selector(capability=[upper])],
    )

    assert set(result.keys()) == {lower, upper}
    assert calls == [lower, upper]


async def test_unsatisfiable_selector_refuses_the_whole_comparison(dual_arm_store):
    engine = _make_engine(dual_arm_store)
    selectors = [
        Selector(capability=_LIGHTRAG_CAPABILITY),
        Selector(capability=["reads_space"]),  # no registered wiring declares this capability
    ]

    with pytest.raises(UnsatisfiableSelectorError):
        await engine.compare(QueryObject(text=_QUERY_TEXT), selectors)
