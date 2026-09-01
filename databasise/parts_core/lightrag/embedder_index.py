"""``lightrag/embedder-index`` (naive arm position 7 of 7) — the port's one index-recipe node
(criterion 1, D-03; named by ``base.json``'s own ``recipe.embedding`` field). Has no ``deps``, so
it dispatches on every arm run that keeps it (every resolved arm except ``bypass``, which removes
it and sets ``recipe: {}``).

D-03: authored and registered with a real body, but does **not** re-index the corpus in this
phase — its config names an explicit sample of ``(chunk_id, text)`` pairs to embed (never a store
lookup: this Part's own declared effects are ``calls_embedding``/``writes_artifact``, not
``reads_kv``, so a run-time KV read has nowhere to attach). ``databasise/tests/parity/
test_embedder_index_reproduction.py`` (Task 3) is what feeds a real sample drawn from the
corpus snapshot and v1's own imported chunk text; a run with no sample configured makes no
embedding call and returns an empty artifact.

``artifact_scope="quarantined"`` is set on this Part (never on the wiring node — the wiring
document dropped that key entirely, see ``databasise/wirings/lightrag/README.md`` edit 2):
§L.2 records this node's effective depth as opaque, tainted by the undecomposed ingest core it
feeds, so its output is never eligible for ``shared`` scope (CONTRACT §3's three-scope table).
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import ArtifactScope, NodeContext, Part

_NAME_AT_VERSION = "lightrag/embedder-index@0.1.0"
_ARTIFACT_SCOPE: ArtifactScope = "quarantined"


async def _embedder_index_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    sample = config.get("sample") or []

    if not sample:
        return {"artifact": {"vectors": {}}, "artifact_scope": _ARTIFACT_SCOPE}

    client = ctx.clients["embedding"]
    texts = [str(entry["text"]) for entry in sample]
    result = await client.embed(texts)
    vectors = {
        str(entry["chunk_id"]): vector
        for entry, vector in zip(sample, result.vectors, strict=True)
    }
    return {
        "artifact": {"vectors": vectors},
        "artifact_scope": _ARTIFACT_SCOPE,
        "tokens": result.tokens,
        "resolved_model_identity": result.resolved_model_identity,
    }


LIGHTRAG_EMBEDDER_INDEX_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="embedder",
    structural_depth="opaque",
    effects=["calls_embedding", "writes_artifact"],
    upstream_ref="v1/lightrag/kg/nano_vector_db_impl.py",
    body=_embedder_index_body,
    artifact_scope=_ARTIFACT_SCOPE,
)
