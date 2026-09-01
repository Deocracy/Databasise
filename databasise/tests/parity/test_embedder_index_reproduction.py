"""D-03's validation for ``lightrag/embedder-index`` (03-04-PLAN.md Task 3): running the part
over a sample of real chunk ids reproduces v1's own stored vectors for that same chunk text,
within a stated cosine-similarity threshold — never by re-indexing the corpus (D-01).

**Similarity threshold: 0.999.** Both sides L2-normalise (v1's Faiss store on write,
``databasise/stores/vector.py``'s own normalisation), and ``databasise/parity/import_index.py``'s
own measurement against the real Task 2 build (4096-dim ``qwen/qwen3-embedding-8b`` vectors)
found per-component float32 renormalisation noise up to ~1e-5. For a unit vector, a perturbation
of that magnitude across 4096 components moves cosine similarity by roughly
``0.5 * 4096 * (1e-5)**2 ≈ 2e-7`` — six orders of magnitude below this test's 0.999 threshold. A
genuinely wrong id-to-text pairing, a stale embedding, or a real re-embedding bug produces a
similarity nowhere near that noise floor (typically well under 0.9 for unrelated text), so 0.999
stays sensitive to a real divergence while carrying enormous headroom past measured noise.

This is where §L.1's substantive difference gets priced rather than assumed: feeding the store a
precomputed vector (this port's shape — ``embedder-index`` calls the embedding client directly,
never a store-internal fallback) supersedes v1's own store-internal embedding fallback path
(``v1/lightrag/kg/nano_vector_db_impl.py``'s upsert-time embedding call when a document arrives
with no precomputed vector). Both sides embed the *same* text through the *same* model in this
test, so a passing comparison prices that substitution as a no-op on output, not merely assumed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest
from databasise.parity.run_arm import _load_env_file
from databasise.parts.schema import NodeContext
from databasise.parts_core.lightrag.embedder_index import LIGHTRAG_EMBEDDER_INDEX_PART
from databasise.wirings.resolve import load_base

_SIMILARITY_THRESHOLD = 0.999
_SAMPLE_SIZE = 3


@dataclass(frozen=True)
class ReproductionViolation:
    """One chunk id whose reproduced vector fell below threshold — never a bare assertion
    failure, per this project's own three-state/named-result house style (mirrors
    ``databasise/parity/import_index.py``'s ``Violation``).
    """

    chunk_id: str
    similarity: float


def _cosine_similarity(a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> float:
    a_arr = np.asarray(a, dtype="float64")
    b_arr = np.asarray(b, dtype="float64")
    denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if denom == 0.0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / denom)


def _below_threshold_violations(
    reproduced: dict[str, list[float]],
    v1_vectors: dict[str, np.ndarray],
    threshold: float,
) -> list[ReproductionViolation]:
    violations = []
    for chunk_id, vector in reproduced.items():
        similarity = _cosine_similarity(vector, v1_vectors[chunk_id])
        if similarity < threshold:
            violations.append(ReproductionViolation(chunk_id=chunk_id, similarity=similarity))
    return violations


def _v1_chunk_vectors(v1_working_dir: Path, chunk_ids: list[str]) -> dict[str, np.ndarray]:
    """Read v1's own stored vectors for exactly ``chunk_ids`` out of its Faiss ``chunks`` index —
    the same ``faiss.read_index`` + ``reconstruct`` technique
    ``databasise/parity/import_index.py`` uses, never a re-embedding.
    """
    import faiss  # type: ignore[import-untyped]

    index_path = v1_working_dir / "faiss_index_chunks.index"
    meta_path = Path(str(index_path) + ".meta.json")
    index = faiss.read_index(str(index_path))
    meta: dict[str, dict] = json.loads(meta_path.read_text(encoding="utf-8"))

    wanted = set(chunk_ids)
    vectors: dict[str, np.ndarray] = {}
    for fid_str, record in meta.items():
        chunk_id = record["__id__"]
        if chunk_id in wanted:
            vectors[chunk_id] = index.reconstruct(int(fid_str))
    return vectors


def _v1_chunk_texts(v1_working_dir: Path, chunk_ids: list[str]) -> dict[str, str]:
    kv_path = v1_working_dir / "kv_store_text_chunks.json"
    data: dict[str, dict] = json.loads(kv_path.read_text(encoding="utf-8"))
    return {chunk_id: data[chunk_id]["content"] for chunk_id in chunk_ids if chunk_id in data}


# --------------------------------------------------------------------------------------------- #
# Offline: recipe identification + the no-sample path (runs with no endpoint, on any machine)
# --------------------------------------------------------------------------------------------- #


def test_base_wiring_names_embedder_index_as_the_recipe_embedding_node():
    """criterion 1's other half: the port *identifies* its one index-recipe node, not merely
    authors it."""
    base = load_base()
    assert base["recipe"]["embedding"] == "embedder-index"


class _UnreachableEmbeddingClient:
    """Any call fails the test outright — used to prove the no-sample path makes zero calls."""

    async def embed(self, texts, **kwargs):
        raise AssertionError(f"embedder-index made an embedding call with no sample configured: {texts!r}")


async def test_embedder_index_with_no_sample_makes_no_call_and_emits_an_empty_artifact():
    ctx = NodeContext(
        node_id="embedder-index",
        config={},
        inputs={},
        stores={},
        clients={"embedding": _UnreachableEmbeddingClient()},
    )

    result = await LIGHTRAG_EMBEDDER_INDEX_PART.body(ctx)

    assert result["artifact"] == {"vectors": {}}
    assert result["artifact_scope"] == "quarantined"


# --------------------------------------------------------------------------------------------- #
# Failure-reporting shape: a below-threshold chunk is named, not a bare assertion
# --------------------------------------------------------------------------------------------- #


def test_below_threshold_violations_names_the_offending_chunk_id_and_its_similarity():
    reproduced = {"chunk-a": [1.0, 0.0, 0.0], "chunk-b": [1.0, 0.0, 0.0]}
    v1_vectors = {
        "chunk-a": np.array([1.0, 0.0, 0.0]),  # identical direction -> similarity 1.0
        "chunk-b": np.array([0.0, 1.0, 0.0]),  # orthogonal -> similarity 0.0, below threshold
    }

    violations = _below_threshold_violations(reproduced, v1_vectors, _SIMILARITY_THRESHOLD)

    assert len(violations) == 1
    assert violations[0].chunk_id == "chunk-b"
    assert violations[0].similarity == pytest.approx(0.0, abs=1e-9)


def test_below_threshold_violations_is_empty_when_every_vector_matches():
    reproduced = {"chunk-a": [1.0, 0.0, 0.0]}
    v1_vectors = {"chunk-a": np.array([1.0, 0.0, 0.0])}

    assert _below_threshold_violations(reproduced, v1_vectors, _SIMILARITY_THRESHOLD) == []


# --------------------------------------------------------------------------------------------- #
# Real Task 2 build + live embedding endpoint — skip-guarded, the actual D-03 validation
# --------------------------------------------------------------------------------------------- #


async def test_embedder_index_reproduces_v1_stored_vectors_on_a_sample(
    v1_index_dir, v1_env_parity_path
):
    from databasise.clients.openai_compat import OpenAICompatibleClient

    env = _load_env_file(v1_env_parity_path)
    embedding_client = OpenAICompatibleClient(
        base_url=env["EMBEDDING_BINDING_HOST"],
        model=env["EMBEDDING_MODEL"],
        api_key=env["EMBEDDING_BINDING_API_KEY"],
    )

    kv_path = v1_index_dir / "kv_store_text_chunks.json"
    v1_chunks: dict[str, dict] = json.loads(kv_path.read_text(encoding="utf-8"))
    sample_ids = sorted(v1_chunks.keys())[:_SAMPLE_SIZE]
    assert sample_ids, "the real Task 2 build's text_chunks KV is unexpectedly empty"

    texts = _v1_chunk_texts(v1_index_dir, sample_ids)
    v1_vectors = _v1_chunk_vectors(v1_index_dir, sample_ids)
    assert set(v1_vectors.keys()) == set(sample_ids)

    sample_config = [{"chunk_id": cid, "text": texts[cid]} for cid in sample_ids]
    ctx = NodeContext(
        node_id="embedder-index",
        config={"sample": sample_config},
        inputs={},
        stores={},
        clients={"embedding": embedding_client},
    )

    result = await LIGHTRAG_EMBEDDER_INDEX_PART.body(ctx)
    reproduced = result["artifact"]["vectors"]
    assert set(reproduced.keys()) == set(sample_ids)
    assert result["tokens"].call_count > 0

    violations = _below_threshold_violations(reproduced, v1_vectors, _SIMILARITY_THRESHOLD)
    assert not violations, [
        f"chunk {v.chunk_id!r}: measured similarity {v.similarity:.6f} < {_SIMILARITY_THRESHOLD}"
        for v in violations
    ]
