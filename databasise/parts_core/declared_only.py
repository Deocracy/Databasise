"""D-04's declaration-only registry entries for the Falsifier-2 named wirings (REQUIREMENTS.md
MACH-01: the opaque codebase-memory-mcp, and the half-decomposed full LightRAG). Each started as
schema + effects[] + structural_depth + artifact_scope, with ``body`` set to ``None`` — Phase 2
computed over these without waiting on Phase 3's real port. A ``None`` body makes a part
un-executable, never a silent no-op: see ``registry.dispatch()``'s explicit refusal.

03-08-PLAN.md Task 3: the third original entry here, ``lightrag/query-side`` (version ``0.1.0``,
the decomposed lightrag-local query side, MACH-01's first named wiring), is retired — Phase 3 ported its real
eighteen positions (``databasise/parts_core/lightrag/``), so the stand-in stub is gone entirely,
not merely dropped from ``DECLARED_ONLY_PARTS``: no reference to its name survives anywhere under
``databasise/`` (``databasise/evidence/wirings/w1-lightrag-query-side.json`` and
``w3-lightrag-half-decomposed.json`` were rewritten to resolve against the real ports instead).

05-01-PLAN.md Task 1: ``LIGHTRAG_FULL_INGEST_PART`` is no longer declaration-only — it now carries
a real ``body`` (``databasise.parts_core.lightrag.full_ingest.full_ingest_body``) and a real §8
``admission`` record (``LIGHTRAG_FULL_INGEST_ADMISSION``).

05-03-PLAN.md Task 1: ``LIGHTRAG_FULL_DELETE_PART`` joins it as a second real, executable
corpus-side port (§19.6's separate-port rule — same underlying v1 engine, different declared
effects). This module's own name is now partly historical: two of its three entries carry real
bodies and admission records, and only ``CODEBASE_MEMORY_MCP_PART`` remains genuinely
declaration-only (``body=None``) until plan 05-06 admits it. ``DECLARED_ONLY_PARTS``'s own name
and membership contract are unchanged — ``default_registry()`` and the Falsifier-2 evidence
wirings still resolve every entry named here, executable or not.
"""

from __future__ import annotations

from databasise.parts.schema import Part
from databasise.parts_core.lightrag.full_delete import (
    LIGHTRAG_FULL_DELETE_ADMISSION,
    full_delete_body,
)
from databasise.parts_core.lightrag.full_ingest import (
    LIGHTRAG_FULL_INGEST_ADMISSION,
    full_ingest_body,
)

# The opaque codebase-memory-mcp part (MACH-01's second named wiring): opaque structural depth,
# declaring self_storage and fs — which is why it is legal at any depth: a self_storage write is
# never a shared write (CONTRACT §3's three-scope table). Declaration-only until plan 05-06 admits
# it (body=None, no admission requirement for a declaration-only part — PartRegistry.register only
# enforces admission for an executable, body-carrying opaque part).
CODEBASE_MEMORY_MCP_PART = Part(
    name_at_version="codebase-memory-mcp@0.1.0",
    kind="opaque",
    structural_depth="opaque",
    effects=["self_storage", "fs"],
    upstream_ref="external:codebase-memory-mcp",
    body=None,
    artifact_scope="self_storage",
)

# The full LightRAG ingest core (MACH-01's third named wiring): opaque structural depth, declaring
# calls_llm and writes_artifact with artifact_scope="quarantined", because an opaque node MAY
# write quarantined and MUST NOT write shared (CONTRACT §3). Real, executable body + real §8
# admission record as of 05-01-PLAN.md Task 1 — no longer a declaration-only stub.
LIGHTRAG_FULL_INGEST_PART = Part(
    name_at_version="lightrag/full-ingest@0.1.0",
    kind="opaque",
    structural_depth="opaque",
    effects=["calls_llm", "writes_artifact", "reads_kv", "reads_graph"],
    upstream_ref="v1/lightrag/pipeline.py",
    body=full_ingest_body,
    artifact_scope="quarantined",
    admission=LIGHTRAG_FULL_INGEST_ADMISSION,
)

# The deleting sibling port (05-03-PLAN.md Task 1): same underlying v1 subprocess engine as
# LIGHTRAG_FULL_INGEST_PART, a different name_at_version and a different declared effect
# (mutates_store, not writes_artifact) — §19.6's separate-port rule. artifact_scope=None: this
# port registers no artifact at all, it mutates the corpus's existing store in place.
LIGHTRAG_FULL_DELETE_PART = Part(
    name_at_version="lightrag/full-delete@0.1.0",
    kind="opaque",
    structural_depth="opaque",
    effects=["mutates_store", "reads_kv", "reads_graph"],
    upstream_ref="v1/lightrag/lightrag.py",
    body=full_delete_body,
    artifact_scope=None,
    admission=LIGHTRAG_FULL_DELETE_ADMISSION,
)

# The two real, executable LightRAG corpus-side ports, factored out as their own tuple so a
# reader can see at a glance which entries here are "two ports of one engine" (05-03-SUMMARY.md)
# without that grouping being implicit in DECLARED_ONLY_PARTS's own flat member order.
LIGHTRAG_CORPUS_PARTS: tuple[Part, ...] = (LIGHTRAG_FULL_INGEST_PART, LIGHTRAG_FULL_DELETE_PART)

DECLARED_ONLY_PARTS: tuple[Part, ...] = (
    CODEBASE_MEMORY_MCP_PART,
    *LIGHTRAG_CORPUS_PARTS,
)
