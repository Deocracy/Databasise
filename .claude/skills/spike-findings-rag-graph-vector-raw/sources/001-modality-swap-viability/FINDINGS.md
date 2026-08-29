# Spike 001 — Modality Swap Viability (theoretical, read-only)

**Question:** Is it possible to make the RAG modality a swappable part inside Databasise, and if so what is the best way?

**Method:** Read-only inspection of `sourcerer-lightrag_nonstripped_2026-06-26.tgz` (the archived Databasise engine fork) extracted to scratchpad, compared against the vendored copy in `Databasise/upstream-venv`. No code written, no repo modified. Everything below is grounded in the archive; nothing rests on published benchmarks.

**Verdict: possible, and cheaper than assumed — because the machine/fitting architecture already exists in LightRAG. It is a *storage* fitting, not yet a *modality* fitting. The work is to invert one seam, not to build a new system.**

---

## 1. What the "LightRAG fork" actually is

It is not a fork of the logic. It is **stock LightRAG 1.5.4 plus one plugin file.**

| Check | Result |
|---|---|
| Files present in fork but not in the vendored copy | `lightrag/kg/cozo_impl.py`, `lightrag/kg/cozo_smoke.py` |
| Core files modified (`lightrag.py`, `operate.py`, `base.py`, `prompt.py`, `utils.py`) | **Zero line-count delta** — 4,469 / 5,995 / 1,068 / 767 / 5,033 lines on both sides |
| Custom code total | ~1,100 lines of implementation + ~3,700 lines of tests/parity harness |

`CozoGraphStorage` in [cozo_impl.py](.planning/spikes/001-modality-swap-viability/FINDINGS.md) subclasses `BaseGraphStorage` and implements its ~18 async methods against embedded CozoDB. It is registered in `lightrag/kg/__init__.py` through the same `STORAGES` / `STORAGE_IMPLEMENTATIONS` tables that register Neo4j, NetworkX and the rest, and selected at runtime by the `LIGHTRAG_GRAPH_STORAGE` environment variable.

**Implication:** whoever built this already worked *with* LightRAG's plugin seam rather than around it. That is the single most encouraging fact in the archive — the discipline the modality-swap needs is already the house style.

## 2. Correction: time-shift and contradiction detection are not built

This changes the plan, so it needs stating plainly. Across the entire archive:

- `time_travel`, `as_of`, `valid_at`, `bitemporal` — **zero occurrences**
- `contradiction` — **zero occurrences**
- `temporal` — one file

The `cozo_impl.py` module docstring says why: the schema was deliberately shaped so that adding a `Validity`-typed key column for "bi-temporal append-and-invalidate versioning" later is an **additive migration**, and it labels that work *deferred to Phase 6*.

So the abilities you described are **designed-for but unbuilt**. Two consequences, one bad and one good:

- The feature-preservation requirement in PROJECT.md was aimed at protecting something that does not yet exist. It should become a *forward* requirement: the fitting must not foreclose bi-temporal storage.
- There is nothing to preserve, so there is nothing to break. The riskiest coupling I flagged during brainstorming — features welded to LightRAG's entity/relation descriptions — **does not exist**. The temporal design lives in the Cozo storage layer, exactly where a machine-layer feature belongs, and it is paradigm-agnostic by construction.

## 3. The machine/fitting already exists — one level too low

LightRAG is already built as machine + injected parts. The evidence:

**Storage contracts** (`base.py`): `StorageNameSpace` → `BaseVectorStorage`, `BaseKVStorage`, `BaseGraphStorage`, `DocStatusStorage`. Four abstract contracts, all async.

**API clients are injected, not imported**: `llm_model_func`, `embedding_func`, `rerank_model_func` are all constructor fields on the `LightRAG` dataclass. The machine's LLM/embedding/reranker seam you wanted is already a seam.

**Query assembly is a free function over the contracts.** This is the decisive one:

```
async def kg_query(query, knowledge_graph_inst: BaseGraphStorage,
                   entities_vdb: BaseVectorStorage,
                   relationships_vdb: BaseVectorStorage,
                   text_chunks_db: BaseKVStorage,
                   query_param, global_config, hashing_kv, ...) -> QueryResult
```

The modality logic receives storages as *arguments*. A leak test for concrete backend names (`networkx|neo4j|cozo|milvus|qdrant|faiss|postgres|mongo`) finds 2 incidental matches in all 5,995 lines of `operate.py` and 4 in `lightrag.py` — effectively no leakage.

**What this means:** the paradigm logic is *already* decoupled from storage. The seam runs in the right place; it simply has only one part fitted into it, and the fitting is described as "a storage backend" rather than "a modality."

## 4. Where the real work is: the namespaces are paradigm-shaped

The honest counterweight. LightRAG's namespaces split cleanly into two groups:

**Paradigm-neutral (true shared machine layer):**
`full_docs`, `text_chunks`, `doc_status`, `llm_response_cache`

**Paradigm-shaped (LightRAG's ontology, not universal):**
`full_entities`, `full_relations`, `entity_chunks`, `relation_chunks`, vector stores `entities` / `relationships` / `chunks`, graph store `chunk_entity_relation`

Your instinct in conversation — shared KV, per-part graph and vector stores — matches this split almost exactly. The neutral four are precisely the KV/doc-status namespaces; everything entity/relation-flavoured is part-owned.

The fitting design question is therefore narrow and answerable: **does the contract expose "entities and relations," or does it expose "a graph of nodes and edges" and let the part decide what nodes mean?** The latter is correct — HippoRAG 2 uses passage nodes and synonym edges, not LightRAG's entity/relation ontology, and a contract that hard-codes entity semantics would refuse to hold it.

**One concrete technical risk, named now:** HippoRAG 2's retrieval runs Personalized PageRank over the whole graph. `BaseGraphStorage` is a per-node/per-edge async interface (`get_node`, `node_degree`, `get_node_edges`), so PPR through it becomes an N+1 call storm. `get_all_nodes` / `get_all_edges` exist (Cozo implements both), so a bulk-export capability is available — but the fitting must expose it as a **declared capability**, and parts that need whole-graph algorithms must be able to require it. This is the assumption most worth a real spike later.

## 5. The comparison rig already has a working precedent

`tests/parity/run_substrate_parity.py` (571 lines, plus a 1,225-line v1.1) is the harness you described for modalities, built one level down for storage backends. It:

1. holds the vector store fixed and varies the graph store (Cozo vs NetworkX),
2. ingests **the same fixed corpus** into an **isolated working directory per backend**,
3. runs all five query modes per backend,
4. captures entity sets, relation sets, answer text, and top-N referenced chunk IDs,
5. computes structural diffs and a prose-similarity score, and
6. writes machine-readable JSON plus a human summary, exiting non-zero past tolerance.

That is the side-by-side comparison design already validated in this codebase. Generalising it from "vary the storage" to "vary the modality" is an extension of an existing pattern, not a new invention — and it independently confirms the isolate-per-part, share-the-corpus model.

## 6. Best way — the recommendation

**Invert the existing seam rather than build a new machine.**

Today: the `LightRAG` object owns the storages and the modality logic is functions it calls.
Target: the machine owns the storages and the API clients, and the modality is the injected thing.

Mechanically this is the smaller move, because `kg_query` and its siblings already take storages as parameters — the dependency direction inside `operate.py` is already correct. What changes is ownership and registration: a `MODALITIES` registry mirroring the existing `STORAGES` registry, selected by config the same way `LIGHTRAG_GRAPH_STORAGE` selects a backend today.

The fitting contract, in shape:

- **Machine provides** — graph ops (`BaseGraphStorage`, plus a declared bulk-export capability), vector ops (`BaseVectorStorage`), KV ops (`BaseKVStorage`), doc status, and the three injected callables (LLM, embedding, rerank).
- **Part implements** — `index(chunks)`, `query(question, params) -> QueryResult`, `delete(doc_id)`.
- **Part declares** — which namespaces it owns, and which machine capabilities it requires.
- **Machine owns** — chunking, `full_docs` / `text_chunks` / `doc_status` / `llm_response_cache`, the REST+MCP surface Sourcerer consumes, and (later) the bi-temporal validity column.

`QueryResult` already carries `content`, `raw_data`, `reference_list` and `metadata` — a usable neutral output contract for side-by-side comparison, since references and retrieved-chunk IDs are what make the comparison meaningful rather than two answer strings.

**Why this beats a clean-sheet machine:** it inherits the storage backends, the API bindings, the server, and the parity harness — all of which are generic machinery you would otherwise rewrite. It also keeps Sourcerer's consumption seam intact, since the REST/MCP surface sits above the modality boundary.

## 7. Effort, honestly

| Work | Estimate | Confidence |
|---|---|---|
| Fitting contract design (the hard intellectual work) | 1–2 weeks | Medium |
| Seam inversion + `MODALITIES` registry | 1–2 weeks | Medium |
| Port LightRAG itself to the fitting (the reference part) | 2–3 weeks | Low-Medium — 5,995 lines of `operate.py` is the true scope |
| Port a second, differently-shaped part (HippoRAG 2) | 2–4 weeks | Low — PPR-over-abstract-graph is the unknown |
| Generalise the parity harness to modalities | ~1 week | High — extends working code |

The LightRAG port is the number to distrust; it is the one place where "it's just Python" hides five thousand lines of accumulated behaviour. Everything else is bounded by code that already exists and works.

**Cost note unchanged:** N parts on one corpus means N independent extraction passes, so parallel comparison costs roughly N× the indexing tokens on the same documents.

## 8. What this changes in PROJECT.md

1. Feature-preservation requirement → **forward-looking**: the fitting must not foreclose bi-temporal validity (which the Cozo schema was already shaped for). Nothing to preserve today.
2. Add a requirement: the fitting needs a **declared-capability** mechanism, because whole-graph algorithms cannot run efficiently through the per-node interface.
3. Add to Context: the archive is stock LightRAG 1.5.4 + `cozo_impl.py`; the vendored `upstream-venv` copy is near-identical (api_version 0313 vs the fork's 0312) and is not a clean upstream reference — a true upstream diff still wants a pull from HKUDS.
4. Key decision to log: **invert the existing seam, do not build a clean-sheet machine.**

## 9. Limits of this spike

- The vendored `upstream-venv` copy is not verified-clean upstream, so "zero core modifications" means "identical to the copy on this machine." A real diff against HKUDS `v1.5.4` would settle it. Line counts matching exactly across five large files makes undetected modification unlikely but not impossible.
- HippoRAG 2's source was **not** read. Every claim about what it needs from a fitting (PPR, passage nodes, synonym edges) comes from its published description and is unverified — the same standard of evidence this project rejects for benchmarks. Reading it is the next spike.
- The Databasise code *outside* the LightRAG fork was not available (only `upstream-venv` and this archive are present locally). If time-shift or contradiction logic was built there, it is not visible from here.

---
*Spike run 2026-08-10. Read-only. No code written, no repositories modified.*
