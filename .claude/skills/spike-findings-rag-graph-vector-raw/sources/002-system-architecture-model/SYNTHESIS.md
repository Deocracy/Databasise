# Synthesis — What the Fitting Must Be

Distilled from four parallel research passes (MODALITIES-GRAPH.md, MODALITIES-VECTOR-TREE.md, MODALITIES-AGENTIC.md, MODALITIES-CODE-AND-ALIEN.md), covering ~24 systems with claims tagged [code-verified] or [paper-claim]. This document is the input to the candidate-architecture drafting.

## 1. The universal core is smaller than assumed

CAG (no index, no retrieval) and codebase-memory-mcp (self-contained black box that only serves evidence) break every "obvious" pipeline assumption. The true universal core:

```
part.ingest(source)                       # source: documents | repo | stream | nothing
part implements at least one of:
  retrieve(question) -> Evidence
  answer(question)   -> Answer + trace
part.manifest                             # declared capabilities + required machine primitives
```

Everything else is a **declared capability**: build-index, rank, assemble, answer, temporal, multimodal, mutate, session-scoped, external-resource, self-contained-storage.

## 2. Storage vocabulary (machine side)

Five store types host everything surveyed:

1. **KV / linked-record store** — chunks, doc status, caches, parent-child hierarchies (RAPTOR's tree is KV + ANN, not a graph [code-verified])
2. **Vector store** — with declared sub-capabilities: `score_all()` brute-force scoring (HippoRAG 2 needs dense scoring of ALL facts, not top-k [code-verified]), multi-vector + MaxSim (ColBERT/ColPali), named namespaces (chunks/entities/facts/reports)
3. **Graph store** — with declared sub-capabilities: pointwise ops (LightRAG family) vs bulk-export for whole-graph algorithms — specifically PPR with per-node reset vectors + weighted edges + score readback (HippoRAG 2, Fast-GraphRAG both use igraph prpack [code-verified]) and community detection (MS GraphRAG, index-time only)
4. **Lexical / inverted index** — BM25 and hybrids; forces the contract to pass query *text*, not only embeddings [code-verified]
5. **Opaque blob** — engine-managed indexes (ColBERT/PLAID directories), media for multimodal, pickled artifacts. The escape hatch that keeps the machine honest about what it can't normalize.

Content-hash LLM caches are load-bearing for incremental rebuild (graph family) — machine-owned, not part-owned.

## 3. API-client seam (machine side)

Role-addressable LLM clients (extract / filter / map / reduce / answer may be different models), plus declared client capabilities:
- **logprobs** (Self-RAG, FLARE [code-verified]) — with prompt-mediated degradation paths
- **prefix-continued generation** (FLARE; ships a fixed-frequency fallback worth adopting)
- **embed / encode-multi / rerank**, declared per-phase (index-time vs query-time) so wiring is validated up front
- **VLM seam** for multimodal (separate from text LLM)

## 4. The three-tier shape: components → modalities → harnesses

- **Components** — ~7 primitive part types cover the space (retriever, grader/filter, rewriter, ranker, assembler, generator, external-tool). One recurring signature unifies rerank/fusion/window-replace/auto-merge: `List[ScoredNode] -> List[ScoredNode]` (the "candidate-set transformer" slot).
- **Modalities** — a named, *declared graph* of components (not a fixed linear pipeline: four of six agentic control-flow shapes can't be expressed linearly [code-verified]). Declared-graph-of-opaque-nodes keeps observability + swappability while staying Turing-complete — and is the representation a self-improving system can mutate and A/B.
- **Harnesses** — five of six agentic families are harnesses *over* modalities, not modalities (Self-CRAG nests CRAG over Self-RAG in published code). Harnesses wrap any part exposing the core, and stack. The harness is selectable, like the part.

**Budget is a first-class machine object** — every looping family hand-rolls max-steps/max-tokens today; self-generated modalities make machine-enforced budgets mandatory.

## 5. Index recipe × query wiring (the sharing rule)

A modality = (index recipe) × (query wiring). Proven consequences:
- PathRAG is a query wiring over LightRAG's index recipe [code-verified — identical index side]
- LightRAG itself is five query wirings (naive/local/global/hybrid/mix) over one recipe
- Artifact shareability = same or declared-compatible index recipe; the fitting tracks artifact provenance ("this graph was built by recipe X\@v; I can read X")
- Cheapest custom modality: new query wiring over an existing index ≈ days, zero re-index tokens
- Chunk-level artifacts (KV + chunk vectors) shareable across nearly all parts given the same chunker + embedder; paradigm-shaped artifacts (entity graphs vs phrase/passage graphs vs symbol graphs) are recipe-bound

## 6. Databasise-specific windfalls

1. **Graphiti solved the deferred features** [code-verified]: bi-temporal = `valid_at/invalid_at` + `created_at/expired_at` per edge; LLM extracts temporal bounds, but **contradiction invalidation is deterministic date arithmetic** (`resolve_edge_contradictions()`) — directly liftable into the Cozo layer, or Graphiti hosts as a temporal part. Two routes where the brief assumed zero.
2. LightRAG's `base.py` storage contracts are "essentially a ready-made fitting contract" (graph researcher) — the build inherits rather than invents.
3. codebase-memory-mcp proves the black-box extreme is hostable: self-contained storage, zero LLM, evidence-only, MCP surface. If the fitting holds it, the fitting is honest.

## 7. What the candidate architectures must now decide

The research settles what's *possible*; the architectures differ on what's *wise*. The live tensions:

1. **Where normalization stops** — force parts onto machine stores (comparable, heavy) vs allow self-contained-storage parts (cheap to host, opaque to compare)
2. **Extraction sharing** — one shared LLM-extraction component with per-part ontology config vs per-part extraction (index side is the expensive, entangled side)
3. **Declared graphs vs code parts** — full graph-execution engine (max observability/mutability) vs parts as async functions with manifests (min machine complexity)
4. **Temporal placement** — validity in the Cozo storage layer (machine) vs Graphiti-style temporal part (modality) vs both
5. **Comparison depth** — compare only at answer/evidence level (universal, shallow) vs at stage level (deep, only for machine-store parts)

Each candidate architecture is a position on these five axes. Red team attacks the positions.
