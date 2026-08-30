"""D-04's three declaration-only registry entries for the Falsifier-2 named wirings
(REQUIREMENTS.md MACH-01: the decomposed lightrag-local query side, the opaque
codebase-memory-mcp, and the half-decomposed full LightRAG). Each is schema + effects[] +
structural_depth + artifact_scope, with ``body`` set to ``None`` — Phase 2 computes over these
without waiting on Phase 3's real port. A ``None`` body makes a part un-executable, never a
silent no-op: see ``registry.dispatch()``'s explicit refusal.
"""

from __future__ import annotations

from databasise.parts.schema import Part

# The decomposed lightrag-local query side (MACH-01's first named wiring): stage structural
# depth, an effects set covering the 4-stage query pipeline's real capability use (KV/vector/
# graph reads plus LLM and embedding calls), no writes_artifact — the query side reads, it does
# not produce a registry-shaped artifact.
LIGHTRAG_QUERY_SIDE_PART = Part(
    name_at_version="lightrag/query-side@0.1.0",
    kind="subgraph",  # stands in for a decomposed multi-node wiring, not yet ported (Phase 3)
    structural_depth="stage",
    effects=["reads_kv", "reads_vector", "reads_graph", "calls_llm", "calls_embedding"],
    upstream_ref="v1/lightrag/operate.py",
    body=None,
    artifact_scope=None,
)

# The opaque codebase-memory-mcp part (MACH-01's second named wiring): opaque structural depth,
# declaring self_storage and fs — which is why it is legal at any depth: a self_storage write is
# never a shared write (CONTRACT §3's three-scope table).
CODEBASE_MEMORY_MCP_PART = Part(
    name_at_version="codebase-memory-mcp@0.1.0",
    kind="opaque",
    structural_depth="opaque",
    effects=["self_storage", "fs"],
    upstream_ref="external:codebase-memory-mcp",
    body=None,
    artifact_scope="self_storage",
)

# The half-decomposed full LightRAG (MACH-01's third named wiring): opaque structural depth for
# the ingest side, declaring calls_llm and writes_artifact with artifact_scope="quarantined",
# because an opaque node MAY write quarantined and MUST NOT write shared (CONTRACT §3).
LIGHTRAG_FULL_INGEST_PART = Part(
    name_at_version="lightrag/full-ingest@0.1.0",
    kind="opaque",
    structural_depth="opaque",
    effects=["calls_llm", "writes_artifact", "reads_kv", "reads_graph"],
    upstream_ref="v1/lightrag/pipeline.py",
    body=None,
    artifact_scope="quarantined",
)

DECLARED_ONLY_PARTS: tuple[Part, ...] = (
    LIGHTRAG_QUERY_SIDE_PART,
    CODEBASE_MEMORY_MCP_PART,
    LIGHTRAG_FULL_INGEST_PART,
)
