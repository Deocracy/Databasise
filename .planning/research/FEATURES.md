# Feature Research

**Domain:** Standalone embeddable RAG engine, API-only (REST + MCP), no UI
**Researched:** 2026-08-29
**Confidence:** MEDIUM (cross-checked web/GitHub/official-docs sources for R2R, LightRAG, Cognee, Microsoft GraphRAG, LlamaIndex, MCP design guidance, and Chroma/Qdrant/Weaviate; no single source is primary-vendor-authored for Databasise itself, so treat as directional, not contractual)

## Feature Landscape

### Table Stakes (Users Expect These)

Features every comparable product (R2R, LightRAG server, Cognee, GraphRAG servers, LlamaIndex-as-API) exposes. Missing these makes Databasise's §18 surface feel incomplete next to what integrators already assume a RAG engine does.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Document ingest endpoint (upload + structured payload) | Every competitor splits ingest into "raw file" and "already-parsed" paths (LightRAG: `/documents/upload` vs `/documents/ingest`; R2R: multimodal ingest; Cognee: `add`) | MEDIUM | Databasise's ingest core is already opaque (§BP rung 3); the API just needs to expose it, not restructure it |
| Ingest status / job polling | LightRAG's upload endpoint takes `async=true/false`; Cognee's pipeline is multi-stage (ECL) and long-running; R2R and Cognee both surface pipeline state | LOW | Needed the moment ingest is async — chunking + KG extraction is not instant, callers need to know "done" vs "still cognifying" |
| Document deletion / corpus mutation | Standard CRUD expectation; not explicitly detailed in the sources scanned but implied by every product having a document lifecycle (upload → index → **remove**) | LOW–MEDIUM | Deletion in graph-based modalities (LightRAG, HippoRAG 2) is harder than vector-only deletion — entities/edges may be shared across documents; flag for Falsifier/rung research, not just API design |
| Multiple named query modes | Universal pattern: LightRAG (naive/local/global/hybrid/mix), GraphRAG (global/local/DRIFT/basic), R2R (basic/advanced/custom) | MEDIUM | Databasise's modality-agnostic contract (§18) needs an equivalent selector that doesn't leak modality internals — the four selectors already specified in Active requirements are this table-stakes feature, already scoped |
| Streaming responses | LightRAG and R2R both support streaming RAG output for perceived-latency reduction | LOW–MEDIUM | Standard SSE/chunked response; MCP tool responses can stream too (tool progress notifications) — low cost given Python/FastAPI-adjacent stack |
| Citations / source attribution on every answer | R2R (auto citation IDs), LlamaIndex (CitationQueryEngine tied to source nodes) both treat this as core, not optional | MEDIUM | Directly maps to the "provenance" line in the milestone brief and to DR-04 (per-chunk provenance stamp) already tracked in PROJECT.md — this is not new scope, it's confirmation the market treats it as mandatory |
| Structured/JSON query response (not just prose) | Every product returns query results as structured objects (context nodes, citation list, mode used) alongside/instead of raw text, so callers can build their own UI | LOW | Matches Databasise's "no UI, closed envelope" posture well — the API's job is structured data, not presentation |
| Health/status and corpus introspection | Implicit across all products (you need to know what's indexed before you query it) | LOW | e.g., document count, index freshness — cheap, expected by any integrator wiring this into their own system |
| MCP tool parity with REST for the core verbs | Existing LightRAG MCP servers (community-built, 30+ tools) show MCP is expected to mirror ingest/query/status, not be a lesser surface | MEDIUM | Per MCP design guidance below: mirror the *capabilities*, not a 1:1 endpoint dump — curate to intention-level tools (e.g., `ingest_document`, `query`, `delete_document`, `get_status`), not one tool per REST route |

### Differentiators (Competitive Advantage)

Features that set Databasise apart. These align directly with the Core Value ("modalities swappable without consumers noticing, N modalities comparable on the rig") — competitors listed above are each locked to one modality's internals; none expose modality-swap or side-by-side comparison as a first-class API feature.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Side-by-side modality comparison (same corpus, two modalities, one call) | No competitor product researched (R2R, LightRAG, Cognee, GraphRAG, LlamaIndex) exposes "run this query against modality A and modality B, return both" as an API primitive — each is single-paradigm | HIGH | This is the product's actual thesis (§BP rung 4, comparison rig). Worth exposing as an API feature, not just an internal eval tool, since it's the differentiator competitors structurally cannot copy without a rewrite |
| A/B promotion of a modality/wiring (promote/rollback ledger) | CONTRACT already specifies a promote/rollback ledger — no competitor has "promote this configuration to production, with rollback" as a documented API concept; they ship one fixed pipeline | HIGH | Already a frozen contract primitive (per PROJECT.md); the differentiator is exposing it over §18, not inventing it |
| Trace/seam-level inspection (F-08 seam-level trace shape) | LightRAG/GraphRAG/R2R return an answer + citations; none expose the intermediate node-by-node execution trace of *which* fitted parts ran and what each produced | MEDIUM–HIGH | Valuable for debugging swapped modalities and for the eval/A-A calibration workflow; ties to the "known open items" F-08 already tracked — surfacing it via API (even read-only, behind a debug flag) is the differentiator, not a new build |
| Modality-agnostic invariant response envelope across arbitrary future modalities | Every competitor's API shape is coupled to its one paradigm (GraphRAG's global/local vocabulary leaks into its API; LightRAG's mode names leak into its query param) | MEDIUM (already contracted) | §18's closed envelope is the mechanism; the differentiator is that a third, unknown-today modality can be added later without a client-visible API change — competitors would need a breaking API version bump to add a new paradigm |
| Cost/budget-token accounting exposed per query | RIG §F3 affordability and budget tokens are already in the frozen contract vocabulary; no competitor researched exposes per-query cost/budget accounting as a citizen of the response envelope (most treat cost as billing-layer, not response-layer) | MEDIUM | Optional differentiator — only worth exposing if a caller needs to reason about cost per query (e.g., choosing which modality to route to) |

### Anti-Features (Commonly Requested, Often Problematic)

Features that look natural for a "RAG engine API" but conflict with the project's explicit scope (API-only, embeddable, no UI, no self-improving RAG this milestone).

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Any UI/dashboard/chat widget (even a minimal debug UI) | Every competitor (GraphRAG-Local-UI, LightRAG WebUI, R2R has a UI layer) ships one, so it feels like an omission not to | PROJECT.md explicitly excludes UI — v1 WebUI is not carried forward; "standalone means REST + MCP, every UI including Sourcerer is a client" | Ship the trace-inspection and comparison data as structured JSON; let Sourcerer or any other client render it |
| Docker/k8s deployment manifests as a first-class feature | R2R, Cognee, GraphRAG servers all lean on containerized deployment as the default onboarding path | PROJECT.md: "Docker/k8s deliverables" out of scope — embeddable-first, local NixOS runtime, no external DB servers | Keep install as a Python package; document embedding pattern (Cozo/Chroma-embedded-mode style), not a container |
| Automatic/self-improving modality mutation exposed via API | Once side-by-side comparison and promotion exist, "just let it auto-promote the best one" is an obvious next ask | PROJECT.md explicitly scopes this out this milestone: "the fitting enables it; building it is a later milestone" | Expose promote/rollback as an explicit, caller-invoked action only; no autonomous loop |
| One-tool-per-REST-endpoint MCP mirroring (30+ granular MCP tools, matching community LightRAG MCP servers) | Feels thorough — "cover every capability" | MCP design guidance is explicit: granular 1:1 tool dumps overwhelm the model's context and hurt tool-selection accuracy; "the number of tools you don't expose matters as much as the ones you do" | Curate to a small set of intention-level MCP tools (ingest, query, delete, status, compare) that internally call the same REST logic |
| Returning full corpus/index dumps through query or status tools | Debugging convenience — "just give me everything" | MCP guidance explicitly flags this as a bad pattern: giant resources overwhelm the model; also a data-exfiltration/cost risk over REST | Paginated, filtered, bounded responses only; status endpoint returns counts/metadata, not full document bodies |
| Trusting competitor-published benchmark numbers to decide which query-mode/feature to prioritize | R2R, GraphRAG, LightRAG all publish comparative numbers | PROJECT.md is explicit: "Trusting published benchmark numbers for decisions — only local measurement on the rig counts" — this applies to feature-prioritization research too, not just architecture | Where this research cites competitor claims, treat as market/feature-surface signal only, never as a performance claim to design around |

## Feature Dependencies

```
[Ingest endpoint (upload + structured)]
    └──requires──> [Ingest status/job polling]   (async ingest is not optional once graph extraction is in the loop)

[Document deletion]
    └──requires──> [Ingest endpoint]              (can't delete what was never given an identity at ingest)
    └──enhances──> [Corpus introspection/status]  (status should reflect post-deletion state)

[Named query modes (4 selectors)]
    └──requires──> [Modality-agnostic response envelope (§18)]   (mode names must not leak modality internals)

[Side-by-side modality comparison]
    └──requires──> [Named query modes]            (comparison runs the same query through 2+ wirings)
    └──requires──> [Runner/scheduler design]       (already a tracked open item, §H1 must-decide)

[A/B promotion + rollback ledger]
    └──requires──> [Side-by-side modality comparison]   (you can't promote what you haven't compared)
    └──enhances──> [Trace/seam-level inspection]         (promotion decisions are more trustworthy with a trace)

[Citations/provenance on every answer]
    └──requires──> [DR-04 per-chunk provenance stamp]    (already a tracked open item, first faced at rung 3)

[MCP tool surface]
    └──requires──> [REST surface's core verbs (ingest/query/delete/status)]  (MCP wraps the same logic, doesn't duplicate it)
    └──conflicts──> [One-tool-per-endpoint MCP mirroring]  (curated intention-level tools, not a 1:1 dump)
```

### Dependency Notes

- **Ingest status requires ingest endpoint:** trivial ordering, but matters for phase sequencing — status/polling should land in the same phase as ingest, not deferred, since LightRAG/Cognee/R2R all treat async ingest as inseparable from status.
- **Deletion requires ingest:** also flags a modality-specific risk — LightRAG/HippoRAG 2 store entities/edges that may be shared across documents in the graph store, so "delete document X" may need graph-aware garbage collection, not a simple row delete. This is a pitfall-adjacent dependency, not just an ordering one.
- **Named query modes require the §18 envelope:** this is already contracted (four selectors, invariance rule) — the dependency exists to confirm the roadmap should NOT expose ingest/query before the envelope shape is locked, or every subsequent feature inherits a leaky contract.
- **Side-by-side comparison requires the runner/scheduler:** PROJECT.md already flags runner/scheduler/storage-keying as an open §H1 item "first faced at rung 1" — this confirms comparison-as-API-feature cannot ship before that design lands, reinforcing existing phase ordering rather than introducing a new blocker.
- **Promotion requires comparison:** ordering constraint for roadmap — promote/rollback is a rung-4-adjacent feature (side-by-side is rung 4's proof point), so it belongs no earlier than the phase that proves two modalities run side-by-side.
- **MCP tools require, but must not mirror 1:1, the REST verbs:** the anti-feature (granular MCP dump) and the table-stakes feature (MCP parity with REST) are two sides of the same dependency — parity in *capability*, curation in *tool count*.

## MVP Definition

### Launch With (v1 — this milestone, §BP rungs 1–4)

- [ ] Document ingest (upload + structured) with async status — table stakes, every competitor has it, and LightRAG's own ingest core is already the opaque node being carried forward
- [ ] Document deletion — table stakes; flag graph-aware deletion as a research item for whichever rung first touches HippoRAG 2/LightRAG's shared-entity graph, not a v1.x deferral
- [ ] Four named query modes over the §18 envelope — already contracted, this is the "closed envelope" work already scoped
- [ ] Citations/provenance on every query response — table stakes and already tied to DR-04, which is already tracked as "first faced at rung 3"
- [ ] Corpus/status introspection (counts, freshness, per-modality index state) — cheap, table stakes, needed for the comparison rig itself to report state
- [ ] MCP surface with a small, curated tool set (ingest, query, delete, status) mirroring REST verbs — table stakes for an "API-only" product; curation avoids the anti-feature
- [ ] Side-by-side modality comparison endpoint — this is rung 4's actual proof point and the Core Value statement ("N modalities running side-by-side and comparable on the rig"); it is not deferrable, it is the milestone's success criterion

### Add After Validation (v1.x)

- [ ] A/B promotion + rollback ledger exposed over the API — the contract vocabulary exists now, but promotion-as-a-caller-invoked-action can follow once comparison is proven and trusted (trigger: comparison endpoint has run enough real queries to be trustworthy)
- [ ] Trace/seam-level inspection endpoint (F-08) — valuable once there's more than one modality to debug side-by-side; trigger: first time a comparison run produces a surprising result that needs explaining
- [ ] Cost/budget-token accounting per query — trigger: a caller actually needs to route by cost, not just correctness

### Future Consideration (v2+)

- [ ] Self-improving/auto-promotion loop — explicitly out of scope this milestone per PROJECT.md; defer until the fitting's manual promotion path is proven
- [ ] Any UI/dashboard — explicitly out of scope; defer indefinitely, this is a client concern (Sourcerer or others), not Databasise's

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|----------------------|----------|
| Ingest (upload + structured) + async status | HIGH | MEDIUM | P1 |
| Document deletion (graph-aware) | HIGH | MEDIUM–HIGH | P1 |
| Four named query modes over §18 envelope | HIGH | MEDIUM (contracted) | P1 |
| Citations/provenance per answer | HIGH | MEDIUM | P1 |
| Corpus/status introspection | MEDIUM | LOW | P1 |
| Curated MCP tool surface | HIGH | MEDIUM | P1 |
| Side-by-side modality comparison | HIGH | HIGH | P1 (Core Value / rung 4 proof point) |
| A/B promotion + rollback ledger via API | MEDIUM | MEDIUM | P2 |
| Trace/seam-level inspection endpoint | MEDIUM | MEDIUM–HIGH | P2 |
| Cost/budget-token accounting per query | LOW–MEDIUM | LOW–MEDIUM | P2 |
| Self-improving/auto-promotion | LOW (this milestone) | HIGH | P3 |
| Any UI | N/A (out of scope) | N/A | P3 (do not build) |

**Priority key:**
- P1: Must have for this milestone — either directly required by the Core Value statement or table stakes next to every comparable product
- P2: Should have, natural extension once P1 lands and is validated on the rig
- P3: Explicitly deferred or excluded per PROJECT.md

## Competitor Feature Analysis

| Feature | R2R | LightRAG server | GraphRAG (community servers) | Cognee | Databasise's Approach |
|---------|-----|------------------|-------------------------------|--------|------------------------|
| Query modes | basic/advanced/custom | naive/local/global/hybrid/mix | global/local/DRIFT/basic | 13+ modes incl. semantic graph, temporal | Four modality-agnostic selectors over one closed envelope — mode vocabulary doesn't leak the underlying modality, unlike all four competitors |
| Ingest | multimodal upload endpoint | `/documents/upload` (raw) + `/documents/ingest` (structured), async flag | varies by wrapper | 6-stage ECL pipeline, add/cognify | Upload + structured, async status; ingest core carried forward opaque per §BP rung 3, not rebuilt |
| Citations | auto citation IDs, streaming | not explicitly documented in sources scanned | not explicitly documented in sources scanned | not explicitly documented in sources scanned | Per-chunk provenance stamp (DR-04) — table stakes confirmed by R2R/LlamaIndex, formalized further than either |
| Cross-modality comparison | none (single paradigm) | none (single paradigm) | none (single paradigm) | none (single paradigm) | Side-by-side same-corpus comparison — the actual differentiator, no competitor researched has this |
| MCP surface | not primary interface | community-built (30+ tools, granular) | not researched | not primary interface | Curated, intention-level MCP tool set mirroring REST verbs, avoiding the granular-dump anti-pattern LightRAG's community MCP servers exhibit |
| Deployment posture | Docker-first | Docker/server-first | Docker/server-first | Docker/cloud-first | Embeddable in-process, no external DB servers, no Docker — closer to Chroma's embedded-mode posture than any RAG-engine competitor researched |

## Sources

- [R2R RAG Query docs](https://r2r-docs.sciphi.ai/api-and-sdks/retrieval/rag-app)
- [R2R GitHub (SciPhi-AI)](https://github.com/SciPhi-AI/r2r)
- [LightRAG API Server docs](https://github.com/HKUDS/LightRAG/blob/main/docs/LightRAG-API-Server.md)
- [LightRAG API Server — DeepWiki](https://deepwiki.com/HKUDS/LightRAG/4-api-server)
- [LightRAG Query Processing — DeepWiki](https://deepwiki.com/lanarich/LightRAG/2.3-query-processing)
- [lightragmcp — community MCP server, 30+ tools](https://github.com/lalitsuryan/lightragmcp)
- [Cognee GitHub (topoteretes)](https://github.com/topoteretes/cognee)
- [Cognee — Deploy REST API Server docs](https://docs.cognee.ai/guides/deploy-rest-api-server)
- [Cognee Python API Reference — DeepWiki](https://deepwiki.com/topoteretes/cognee/2.1-python-api-reference)
- [Microsoft GraphRAG](https://microsoft.github.io/graphrag/)
- [GraphRAG query methods discussion (local/global/DRIFT/basic)](https://github.com/microsoft/graphrag/discussions/721)
- [DRIFT Search: combining global and local search — Microsoft Research](https://www.microsoft.com/en-us/research/blog/introducing-drift-search-combining-global-and-local-search-methods-to-improve-quality-and-efficiency/)
- [graphrag-api (community FastAPI server)](https://github.com/noworneverev/graphrag-api)
- [LlamaIndex Citation Query Engine example](https://developers.llamaindex.ai/python/examples/workflow/citation_query_engine/)
- [MCP tool design strategy — AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/mcp-strategies/mcp-tool-strategy.html)
- [MCP tool design: practical approaches and tradeoffs — AWS ML Blog](https://aws.amazon.com/blogs/machine-learning/mcp-tool-design-practical-approaches-and-tradeoffs/)
- [MCP server tool design — Workato Docs](https://docs.workato.com/mcp/mcp-server-tool-design.html)
- [awslabs/mcp DESIGN_GUIDELINES.md](https://github.com/awslabs/mcp/blob/main/DESIGN_GUIDELINES.md)
- [Vector Database Comparison 2026 — Reintech](https://reintech.io/blog/vector-database-comparison-2026-pinecone-weaviate-milvus-qdrant-chroma)
- [ChromaDB vs Qdrant vs Weaviate — LocalAlternative](https://www.localalternative.io/compare/chromadb-vs-qdrant-vs-weaviate)

---
*Feature research for: standalone embeddable RAG engine, API-only (REST + MCP)*
*Researched: 2026-08-29*
