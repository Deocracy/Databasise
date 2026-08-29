# Databasise Engine Reality (what we're actually re-architecting)

## Requirements

- Decompose below the modality: modality = index recipe × query wiring
- Bi-temporal time-shift + contradiction detection must stay buildable (not preserved — they don't exist yet)
- Sourcerer's REST/MCP seam stays modality-agnostic

## Facts (all code-verified, spike 001)

1. **The engine is stock LightRAG 1.5.4 + one plugin file.** `lightrag/kg/cozo_impl.py` (977 lines) implements `BaseGraphStorage` (~18 async methods) over embedded CozoDB; registered in the same `STORAGES` table as Neo4j/NetworkX; selected by `LIGHTRAG_GRAPH_STORAGE` env var. Zero deltas in core files. Archive: `Databasise/_archives/sourcerer-lightrag_nonstripped_2026-06-26.tgz`.
2. **The fitting seam already exists, one level low.** `kg_query(query, knowledge_graph_inst, entities_vdb, relationships_vdb, text_chunks_db, ...)` receives storages as arguments; `llm_model_func`/`embedding_func`/`rerank_model_func` are injected dataclass fields. ~No concrete-backend leakage in 5,995 lines of operate.py. LightRAG's `base.py` contracts (StorageNameSpace → BaseVectorStorage/BaseKVStorage/BaseGraphStorage/DocStatusStorage) are a ready-made starting fitting.
3. **Query path is already componentized**: named 4-stage pipeline (Search → Truncate → Merge → Build-context), plain dict/list boundaries, ~794 lines total. **Index side is NOT**: ~1,786 lines welded to the entity/relation ontology (extract_entities, merge/upsert family). Retrieval work is cheap; extraction work is expensive.
4. **Temporal features are designed-but-unbuilt.** Zero occurrences of time_travel/as_of/bitemporal/contradiction. Cozo schema deliberately shaped for an additive `Validity` column ("Phase 6"). Nothing to preserve; only not-foreclose. Graphiti [code-verified] provides the liftable design: `valid_at/invalid_at` + `created_at/expired_at` per edge; contradiction invalidation is deterministic date arithmetic (`resolve_edge_contradictions()`).
5. **A comparison-rig precedent exists**: `tests/parity/run_substrate_parity.py` (571 + 1,225 lines) — same corpus, isolated working dir per backend, all 5 query modes, structural diffs (entity/relation sets, chunk refs), JSON verdicts. Generalize its axis from storage→modality; don't rewrite.
6. LightRAG's 5 query modes (naive/local/global/hybrid/mix) are 5 query wirings over ONE index recipe; PathRAG is a 6th (fork with identical index side). Artifact sharing across wirings is proven, not hoped.

## What to Avoid

- Don't treat the vendored `upstream-venv` copy as clean upstream (api_version 0313 vs fork's 0312) — true HKUDS diff still owed
- Don't port modalities as monoliths (~6,000-line cost each); cut below
- Don't assume Cozo supports zero-copy artifact branching — verify (open spike)

## Origin

Synthesized from spike 001. Sources: sources/001-modality-swap-viability/
