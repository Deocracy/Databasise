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
effects).

05-06-PLAN.md Task 2: ``CODEBASE_MEMORY_MCP_PART`` is admitted whole-engine — the second,
differently-shaped foreign engine — gaining a real ``body``
(``databasise.parts_core.codebase_memory_mcp.codebase_memory_mcp_body``) and a real §8
``admission`` record (``CODEBASE_MEMORY_MCP_ADMISSION``). Every entry this module declares now
carries a real body and admission record — ``DECLARED_ONLY_PARTS``'s own name is now purely
historical (D-04's original three Falsifier-2 wiring placeholders), not a live description of what
any entry still carries.

11-01-PLAN.md (D-01): ``LIGHTRAG_V1_INDEX_SYNC_PART`` joins ``LIGHTRAG_CORPUS_PARTS`` as the third
corpus-side part: the second node of both corpus wirings, mirroring v1's committed index into the
v2 stores (``databasise.parts_core.lightrag.v1_index_sync``).

11-03-PLAN.md (D-06): both corpus ports move to ``@0.2.0`` in one bump with fresh admission
records (``parts_core/lightrag/OPAQUE-BOUNDARY-RULE.md`` §2).
"""

from __future__ import annotations

from databasise.parts.schema import Part
from databasise.parts_core.codebase_memory_mcp import (
    CODEBASE_MEMORY_MCP_ADMISSION,
    codebase_memory_mcp_body,
)
from databasise.parts_core.lightrag.full_delete import (
    LIGHTRAG_FULL_DELETE_ADMISSION,
    full_delete_body,
)
from databasise.parts_core.lightrag.full_ingest import (
    LIGHTRAG_FULL_INGEST_ADMISSION,
    full_ingest_body,
)
from databasise.parts_core.lightrag.v1_index_sync import (
    LIGHTRAG_V1_INDEX_SYNC_ADMISSION,
    v1_index_sync_body,
)

# The opaque codebase-memory-mcp part (MACH-01's second named wiring): opaque structural depth.
# effects gains mutates_store additively (05-06-PLAN.md Task 2E) — PARTS.md ## §X's X1 repair
# landed mutates_store and the mutable-store capability for manage_adr/delete_project's real
# mutation surface, but this built stub still also declares self_storage and fs, which §X does
# not (§X declares mutates_store only). The two extra effects are over-declarations of the same
# self-contained-storage fact, which §2's deny-by-default rule permits (an over-declaration is
# never a wire-time refusal risk the way an under-declaration is), and they are retained because
# databasise/evidence/wirings/w2-codebase-memory-mcp.json and FALSIFIER-2-EVIDENCE.md pin them as
# committed Falsifier-2 evidence — this discrepancy is recorded, not silently resolved, in
# ADMISSION-CODEBASE-MEMORY-MCP.md.
CODEBASE_MEMORY_MCP_PART = Part(
    name_at_version="codebase-memory-mcp@0.1.0",
    kind="opaque",
    structural_depth="opaque",
    effects=["self_storage", "fs", "mutates_store"],
    upstream_ref="external:codebase-memory-mcp",
    body=codebase_memory_mcp_body,
    artifact_scope="self_storage",
    admission=CODEBASE_MEMORY_MCP_ADMISSION,
)

# The full LightRAG ingest core (MACH-01's third named wiring): opaque structural depth. @0.2.0
# (11-03, LRAG-03): v1 mutates its own per-workspace working dir (mutates_store) and writes no
# artifact, so writes_artifact and the quarantined scope are gone; the v2 rows are the
# lightrag/v1-index-sync node's.
LIGHTRAG_FULL_INGEST_PART = Part(
    name_at_version="lightrag/full-ingest@0.2.0",
    kind="opaque",
    structural_depth="opaque",
    effects=["calls_llm", "mutates_store", "reads_kv", "reads_graph"],
    upstream_ref="v1/lightrag/pipeline.py",
    body=full_ingest_body,
    artifact_scope=None,
    admission=LIGHTRAG_FULL_INGEST_ADMISSION,
)

# The deleting sibling port (05-03-PLAN.md Task 1): same underlying v1 subprocess engine as
# LIGHTRAG_FULL_INGEST_PART, its own name_at_version and admission record — §19.6's separate-port
# rule. artifact_scope=None: it mutates v1's existing store in place. @0.2.0 (11-03, LRAG-11):
# calls_llm, because a partial-rebuild delete reaches the LLM and is metered.
LIGHTRAG_FULL_DELETE_PART = Part(
    name_at_version="lightrag/full-delete@0.2.0",
    kind="opaque",
    structural_depth="opaque",
    effects=["calls_llm", "mutates_store", "reads_kv", "reads_graph"],
    upstream_ref="v1/lightrag/lightrag.py",
    body=full_delete_body,
    artifact_scope=None,
    admission=LIGHTRAG_FULL_DELETE_ADMISSION,
)

# 11-01-PLAN.md (D-01): the v1-to-v2 mirror, second node of both corpus wirings. Opaque because
# mutates_store on a non-opaque part derives the unhosted confined-unit placement; its body runs in
# the engine process and writes only through ctx.stores.
LIGHTRAG_V1_INDEX_SYNC_PART = Part(
    name_at_version="lightrag/v1-index-sync@0.1.0",
    kind="opaque",
    structural_depth="opaque",
    effects=["mutates_store", "writes_kv", "writes_vector", "writes_graph"],
    upstream_ref="v1/lightrag/kg/faiss_impl.py",
    body=v1_index_sync_body,
    artifact_scope=None,
    admission=LIGHTRAG_V1_INDEX_SYNC_ADMISSION,
)

# The real, executable LightRAG corpus-side parts: the two ports of one v1 engine
# (05-03-SUMMARY.md) plus the mirror that follows either of them, factored out as their own tuple
# so that grouping is not implicit in DECLARED_ONLY_PARTS's own flat member order.
LIGHTRAG_CORPUS_PARTS: tuple[Part, ...] = (
    LIGHTRAG_FULL_INGEST_PART,
    LIGHTRAG_FULL_DELETE_PART,
    LIGHTRAG_V1_INDEX_SYNC_PART,
)

# CODEBASE_MEMORY_MCP_PART is not here: no selector reaches it, so default_registry() does not admit
# it (14-07, LEDG-12, D-13). falsifier2.probe_registry() and tests that need it register it.
DECLARED_ONLY_PARTS: tuple[Part, ...] = (*LIGHTRAG_CORPUS_PARTS,)
