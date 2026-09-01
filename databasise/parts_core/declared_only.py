"""D-04's declaration-only registry entries for the Falsifier-2 named wirings (REQUIREMENTS.md
MACH-01: the opaque codebase-memory-mcp, and the half-decomposed full LightRAG). Each is schema +
effects[] + structural_depth + artifact_scope, with ``body`` set to ``None`` — Phase 2 computes
over these without waiting on Phase 3's real port. A ``None`` body makes a part un-executable,
never a silent no-op: see ``registry.dispatch()``'s explicit refusal.

03-08-PLAN.md Task 3: the third original entry here, ``lightrag/query-side`` (version ``0.1.0``,
the decomposed lightrag-local query side, MACH-01's first named wiring), is retired — Phase 3 ported its real
eighteen positions (``databasise/parts_core/lightrag/``), so the stand-in stub is gone entirely,
not merely dropped from ``DECLARED_ONLY_PARTS``: no reference to its name survives anywhere under
``databasise/`` (``databasise/evidence/wirings/w1-lightrag-query-side.json`` and
``w3-lightrag-half-decomposed.json`` were rewritten to resolve against the real ports instead).
"""

from __future__ import annotations

from databasise.parts.schema import Part

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
    CODEBASE_MEMORY_MCP_PART,
    LIGHTRAG_FULL_INGEST_PART,
)
