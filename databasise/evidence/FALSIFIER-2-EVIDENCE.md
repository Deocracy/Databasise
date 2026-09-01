# Falsifier 2 Evidence

Computed-vs-declared depth and execution_mode for each of MACH-01's named wirings, resolved against `default_registry()` and computed by `databasise.validator.depth.effective_depth` and `databasise.validator.execution_mode.derive_execution_mode` — the same functions the runner calls, never a reimplementation.

## w1-lightrag-query-side — Decomposed lightrag-local query side

Resolved against `default_registry()`'s Phase-1 entries (15 node(s)).

| node id | component | wiring kind | structural_depth | effective_depth | execution_mode | part effects | artifact_scope | blast-radius |
|---|---|---|---|---|---|---|---|---|
| assemble | lightrag/assembler-kg-context@0.1.0 | assembler | stage | stage | in-process | — | — | n/a |
| budget-entities | lightrag/truncator-token-budget@0.1.0 | grader-filter | stage | stage | in-process | — | — | n/a |
| budget-relations | lightrag/truncator-token-budget@0.1.0 | grader-filter | stage | stage | in-process | — | — | n/a |
| chunk-sel-kg | lightrag/chunk-selector-kg@0.1.0 | retriever | stage | stage | in-process | reads_kv, reads_vector | — | n/a |
| embedder-index | lightrag/embedder-index@0.1.0 | embedder | opaque | opaque | in-process | calls_embedding, writes_artifact | quarantined | permitted |
| embedder-query | lightrag/embedder-query@0.1.0 | embedder | stage | stage | in-process | calls_embedding | — | n/a |
| entity-hydrate-expand | lightrag/entity-hydrate-expand@0.1.0 | retriever | stage | stage | in-process | reads_graph | — | n/a |
| entity-lookup | lightrag/entity-lookup@0.1.0 | retriever | stage | stage | in-process | reads_vector | — | n/a |
| generate | lightrag/generator-llm@0.1.0 | generator | stage | stage | in-process | calls_llm | — | n/a |
| heading-backfill | lightrag/chunk-heading-backfiller@0.1.0 | grader-filter | stage | stage | in-process | reads_kv | — | n/a |
| join-chunks | lightrag/join-roundrobin@0.1.0 | join | stage | stage | in-process | — | — | n/a |
| join-entities | lightrag/join-roundrobin@0.1.0 | join | stage | stage | in-process | — | — | n/a |
| join-relations | lightrag/join-roundrobin@0.1.0 | join | stage | stage | in-process | — | — | n/a |
| keywords | lightrag/keyword-extractor@0.1.0 | rewriter | stage | stage | in-process | calls_llm | — | n/a |
| rerank | lightrag/reranker-cross-encoder@0.1.0 | ranker-reranker | stage | stage | in-process | calls_rerank | — | n/a |

**Divergence from declared structural_depth:**

No node's computed `effective_depth` diverges from its part's own `structural_depth`.

### CONTRACT §19.10 — boundary enumeration

Before applying §19.1–§19.6, the author MUST enumerate candidate boundaries by a stated, source-derived procedure — at minimum every point where the declared `effects[]` set changes, every point where a declared knob sits, and every point where a value crosses between operations. The enumeration below is recorded with this wiring's node set, so a second author can check the candidate set, not only the verdicts reached on it.

| boundary_id | class | between | rationale |
|---|---|---|---|
| w1-lightrag-query-side-effects-rerank-assemble | effects-change | rerank -> assemble | declared effects[] differs across this dep edge; symmetric difference: ['calls_rerank'] |
| w1-lightrag-query-side-crossing-rerank-assemble | value-crossing | rerank -> assemble | 'assemble''s dep edge on 'rerank' is by construction a point where a value crosses between operations |
| w1-lightrag-query-side-crossing-join-entities-budget-entities | value-crossing | join-entities -> budget-entities | 'budget-entities''s dep edge on 'join-entities' is by construction a point where a value crosses between operations |
| w1-lightrag-query-side-crossing-join-relations-budget-relations | value-crossing | join-relations -> budget-relations | 'budget-relations''s dep edge on 'join-relations' is by construction a point where a value crosses between operations |
| w1-lightrag-query-side-effects-budget-entities-chunk-sel-kg | effects-change | budget-entities -> chunk-sel-kg | declared effects[] differs across this dep edge; symmetric difference: ['reads_kv', 'reads_vector'] |
| w1-lightrag-query-side-crossing-budget-entities-chunk-sel-kg | value-crossing | budget-entities -> chunk-sel-kg | 'chunk-sel-kg''s dep edge on 'budget-entities' is by construction a point where a value crosses between operations |
| w1-lightrag-query-side-effects-budget-relations-chunk-sel-kg | effects-change | budget-relations -> chunk-sel-kg | declared effects[] differs across this dep edge; symmetric difference: ['reads_kv', 'reads_vector'] |
| w1-lightrag-query-side-crossing-budget-relations-chunk-sel-kg | value-crossing | budget-relations -> chunk-sel-kg | 'chunk-sel-kg''s dep edge on 'budget-relations' is by construction a point where a value crosses between operations |
| w1-lightrag-query-side-effects-keywords-embedder-query | effects-change | keywords -> embedder-query | declared effects[] differs across this dep edge; symmetric difference: ['calls_embedding', 'calls_llm'] |
| w1-lightrag-query-side-crossing-keywords-embedder-query | value-crossing | keywords -> embedder-query | 'embedder-query''s dep edge on 'keywords' is by construction a point where a value crosses between operations |
| w1-lightrag-query-side-effects-entity-lookup-entity-hydrate-expand | effects-change | entity-lookup -> entity-hydrate-expand | declared effects[] differs across this dep edge; symmetric difference: ['reads_graph', 'reads_vector'] |
| w1-lightrag-query-side-crossing-entity-lookup-entity-hydrate-expand | value-crossing | entity-lookup -> entity-hydrate-expand | 'entity-hydrate-expand''s dep edge on 'entity-lookup' is by construction a point where a value crosses between operations |
| w1-lightrag-query-side-effects-embedder-query-entity-lookup | effects-change | embedder-query -> entity-lookup | declared effects[] differs across this dep edge; symmetric difference: ['calls_embedding', 'reads_vector'] |
| w1-lightrag-query-side-crossing-embedder-query-entity-lookup | value-crossing | embedder-query -> entity-lookup | 'entity-lookup''s dep edge on 'embedder-query' is by construction a point where a value crosses between operations |
| w1-lightrag-query-side-effects-assemble-generate | effects-change | assemble -> generate | declared effects[] differs across this dep edge; symmetric difference: ['calls_llm'] |
| w1-lightrag-query-side-crossing-assemble-generate | value-crossing | assemble -> generate | 'generate''s dep edge on 'assemble' is by construction a point where a value crosses between operations |
| w1-lightrag-query-side-effects-join-chunks-heading-backfill | effects-change | join-chunks -> heading-backfill | declared effects[] differs across this dep edge; symmetric difference: ['reads_kv'] |
| w1-lightrag-query-side-crossing-join-chunks-heading-backfill | value-crossing | join-chunks -> heading-backfill | 'heading-backfill''s dep edge on 'join-chunks' is by construction a point where a value crosses between operations |
| w1-lightrag-query-side-effects-chunk-sel-kg-join-chunks | effects-change | chunk-sel-kg -> join-chunks | declared effects[] differs across this dep edge; symmetric difference: ['reads_kv', 'reads_vector'] |
| w1-lightrag-query-side-crossing-chunk-sel-kg-join-chunks | value-crossing | chunk-sel-kg -> join-chunks | 'join-chunks''s dep edge on 'chunk-sel-kg' is by construction a point where a value crosses between operations |
| w1-lightrag-query-side-effects-entity-hydrate-expand-join-entities | effects-change | entity-hydrate-expand -> join-entities | declared effects[] differs across this dep edge; symmetric difference: ['reads_graph'] |
| w1-lightrag-query-side-crossing-entity-hydrate-expand-join-entities | value-crossing | entity-hydrate-expand -> join-entities | 'join-entities''s dep edge on 'entity-hydrate-expand' is by construction a point where a value crosses between operations |
| w1-lightrag-query-side-effects-entity-hydrate-expand-join-relations | effects-change | entity-hydrate-expand -> join-relations | declared effects[] differs across this dep edge; symmetric difference: ['reads_graph'] |
| w1-lightrag-query-side-crossing-entity-hydrate-expand-join-relations | value-crossing | entity-hydrate-expand -> join-relations | 'join-relations''s dep edge on 'entity-hydrate-expand' is by construction a point where a value crosses between operations |
| w1-lightrag-query-side-effects-heading-backfill-rerank | effects-change | heading-backfill -> rerank | declared effects[] differs across this dep edge; symmetric difference: ['calls_rerank', 'reads_kv'] |
| w1-lightrag-query-side-crossing-heading-backfill-rerank | value-crossing | heading-backfill -> rerank | 'rerank''s dep edge on 'heading-backfill' is by construction a point where a value crosses between operations |
| w1-knob-retriever | knob | retrieve -> refine | the retriever is a genuine substitution point: a different retrieval implementation (dense/sparse/hybrid) can replace parts-core/fake-retriever@1.0.0 without changing any other node's socket |
| w1-knob-llm-caller | knob | query-side -> generate | the LLM caller is a genuine substitution point: a different model/provider can replace parts-core/fake-llm-caller@1.0.0 without changing any other node's socket |

## w2-codebase-memory-mcp — Opaque codebase-memory-mcp arm

Resolved against `default_registry()`'s Phase-1 entries (3 node(s)).

| node id | component | wiring kind | structural_depth | effective_depth | execution_mode | part effects | artifact_scope | blast-radius |
|---|---|---|---|---|---|---|---|---|
| answer | parts-core/fake-llm-caller@1.0.0 | llm-caller | stage | opaque | in-process | calls_llm, writes_kv | — | n/a |
| cbm | codebase-memory-mcp@0.1.0 | opaque | opaque | opaque | subprocess | fs, self_storage | self_storage | n/a |
| normalise | parts-core/passthrough@1.0.0 | passthrough | stage | opaque | in-process | — | — | n/a |

**Divergence from declared structural_depth:**

Nodes whose computed `effective_depth` diverges from their part's own `structural_depth` (the taint rule overriding a declared depth): answer, normalise.

### CONTRACT §19.10 — boundary enumeration

Before applying §19.1–§19.6, the author MUST enumerate candidate boundaries by a stated, source-derived procedure — at minimum every point where the declared `effects[]` set changes, every point where a declared knob sits, and every point where a value crosses between operations. The enumeration below is recorded with this wiring's node set, so a second author can check the candidate set, not only the verdicts reached on it.

| boundary_id | class | between | rationale |
|---|---|---|---|
| w2-codebase-memory-mcp-effects-normalise-answer | effects-change | normalise -> answer | declared effects[] differs across this dep edge; symmetric difference: ['calls_llm', 'writes_kv'] |
| w2-codebase-memory-mcp-crossing-normalise-answer | value-crossing | normalise -> answer | 'answer''s dep edge on 'normalise' is by construction a point where a value crosses between operations |
| w2-codebase-memory-mcp-effects-cbm-normalise | effects-change | cbm -> normalise | declared effects[] differs across this dep edge; symmetric difference: ['fs', 'self_storage'] |
| w2-codebase-memory-mcp-crossing-cbm-normalise | value-crossing | cbm -> normalise | 'normalise''s dep edge on 'cbm' is by construction a point where a value crosses between operations |
| w2-knob-chunking-strategy | knob | cbm -> normalise | the machine-chunks-versus-native-chunking boundary SELECTION.md Falsifier 4 names: cbm can be run once consuming machine-produced chunks and once chunking natively, a genuine bypass/substitution point at its own boundary |

## w3-lightrag-half-decomposed — Half-decomposed full LightRAG

Resolved against `default_registry()`'s Phase-1 entries (16 node(s)).

| node id | component | wiring kind | structural_depth | effective_depth | execution_mode | part effects | artifact_scope | blast-radius |
|---|---|---|---|---|---|---|---|---|
| assemble | lightrag/assembler-kg-context@0.1.0 | assembler | stage | opaque | in-process | — | — | n/a |
| budget-entities | lightrag/truncator-token-budget@0.1.0 | grader-filter | stage | opaque | in-process | — | — | n/a |
| budget-relations | lightrag/truncator-token-budget@0.1.0 | grader-filter | stage | opaque | in-process | — | — | n/a |
| chunk-sel-kg | lightrag/chunk-selector-kg@0.1.0 | retriever | stage | opaque | in-process | reads_kv, reads_vector | — | n/a |
| embedder-index | lightrag/embedder-index@0.1.0 | embedder | opaque | opaque | in-process | calls_embedding, writes_artifact | quarantined | permitted |
| embedder-query | lightrag/embedder-query@0.1.0 | embedder | stage | opaque | in-process | calls_embedding | — | n/a |
| entity-hydrate-expand | lightrag/entity-hydrate-expand@0.1.0 | retriever | stage | opaque | in-process | reads_graph | — | n/a |
| entity-lookup | lightrag/entity-lookup@0.1.0 | retriever | stage | opaque | in-process | reads_vector | — | n/a |
| generate | lightrag/generator-llm@0.1.0 | generator | stage | opaque | in-process | calls_llm | — | n/a |
| heading-backfill | lightrag/chunk-heading-backfiller@0.1.0 | grader-filter | stage | opaque | in-process | reads_kv | — | n/a |
| ingest | lightrag/full-ingest@0.1.0 | opaque | opaque | opaque | subprocess | calls_llm, reads_graph, reads_kv, writes_artifact | quarantined | permitted |
| join-chunks | lightrag/join-roundrobin@0.1.0 | join | stage | opaque | in-process | — | — | n/a |
| join-entities | lightrag/join-roundrobin@0.1.0 | join | stage | opaque | in-process | — | — | n/a |
| join-relations | lightrag/join-roundrobin@0.1.0 | join | stage | opaque | in-process | — | — | n/a |
| keywords | lightrag/keyword-extractor@0.1.0 | rewriter | stage | opaque | in-process | calls_llm | — | n/a |
| rerank | lightrag/reranker-cross-encoder@0.1.0 | ranker-reranker | stage | opaque | in-process | calls_rerank | — | n/a |

**Divergence from declared structural_depth:**

Nodes whose computed `effective_depth` diverges from their part's own `structural_depth` (the taint rule overriding a declared depth): assemble, budget-entities, budget-relations, chunk-sel-kg, embedder-query, entity-hydrate-expand, entity-lookup, generate, heading-backfill, join-chunks, join-entities, join-relations, keywords, rerank.

### CONTRACT §19.10 — boundary enumeration

Before applying §19.1–§19.6, the author MUST enumerate candidate boundaries by a stated, source-derived procedure — at minimum every point where the declared `effects[]` set changes, every point where a declared knob sits, and every point where a value crosses between operations. The enumeration below is recorded with this wiring's node set, so a second author can check the candidate set, not only the verdicts reached on it.

| boundary_id | class | between | rationale |
|---|---|---|---|
| w3-lightrag-half-decomposed-effects-rerank-assemble | effects-change | rerank -> assemble | declared effects[] differs across this dep edge; symmetric difference: ['calls_rerank'] |
| w3-lightrag-half-decomposed-crossing-rerank-assemble | value-crossing | rerank -> assemble | 'assemble''s dep edge on 'rerank' is by construction a point where a value crosses between operations |
| w3-lightrag-half-decomposed-crossing-join-entities-budget-entities | value-crossing | join-entities -> budget-entities | 'budget-entities''s dep edge on 'join-entities' is by construction a point where a value crosses between operations |
| w3-lightrag-half-decomposed-crossing-join-relations-budget-relations | value-crossing | join-relations -> budget-relations | 'budget-relations''s dep edge on 'join-relations' is by construction a point where a value crosses between operations |
| w3-lightrag-half-decomposed-effects-budget-entities-chunk-sel-kg | effects-change | budget-entities -> chunk-sel-kg | declared effects[] differs across this dep edge; symmetric difference: ['reads_kv', 'reads_vector'] |
| w3-lightrag-half-decomposed-crossing-budget-entities-chunk-sel-kg | value-crossing | budget-entities -> chunk-sel-kg | 'chunk-sel-kg''s dep edge on 'budget-entities' is by construction a point where a value crosses between operations |
| w3-lightrag-half-decomposed-effects-budget-relations-chunk-sel-kg | effects-change | budget-relations -> chunk-sel-kg | declared effects[] differs across this dep edge; symmetric difference: ['reads_kv', 'reads_vector'] |
| w3-lightrag-half-decomposed-crossing-budget-relations-chunk-sel-kg | value-crossing | budget-relations -> chunk-sel-kg | 'chunk-sel-kg''s dep edge on 'budget-relations' is by construction a point where a value crosses between operations |
| w3-lightrag-half-decomposed-effects-keywords-embedder-query | effects-change | keywords -> embedder-query | declared effects[] differs across this dep edge; symmetric difference: ['calls_embedding', 'calls_llm'] |
| w3-lightrag-half-decomposed-crossing-keywords-embedder-query | value-crossing | keywords -> embedder-query | 'embedder-query''s dep edge on 'keywords' is by construction a point where a value crosses between operations |
| w3-lightrag-half-decomposed-effects-entity-lookup-entity-hydrate-expand | effects-change | entity-lookup -> entity-hydrate-expand | declared effects[] differs across this dep edge; symmetric difference: ['reads_graph', 'reads_vector'] |
| w3-lightrag-half-decomposed-crossing-entity-lookup-entity-hydrate-expand | value-crossing | entity-lookup -> entity-hydrate-expand | 'entity-hydrate-expand''s dep edge on 'entity-lookup' is by construction a point where a value crosses between operations |
| w3-lightrag-half-decomposed-effects-embedder-query-entity-lookup | effects-change | embedder-query -> entity-lookup | declared effects[] differs across this dep edge; symmetric difference: ['calls_embedding', 'reads_vector'] |
| w3-lightrag-half-decomposed-crossing-embedder-query-entity-lookup | value-crossing | embedder-query -> entity-lookup | 'entity-lookup''s dep edge on 'embedder-query' is by construction a point where a value crosses between operations |
| w3-lightrag-half-decomposed-effects-assemble-generate | effects-change | assemble -> generate | declared effects[] differs across this dep edge; symmetric difference: ['calls_llm'] |
| w3-lightrag-half-decomposed-crossing-assemble-generate | value-crossing | assemble -> generate | 'generate''s dep edge on 'assemble' is by construction a point where a value crosses between operations |
| w3-lightrag-half-decomposed-effects-join-chunks-heading-backfill | effects-change | join-chunks -> heading-backfill | declared effects[] differs across this dep edge; symmetric difference: ['reads_kv'] |
| w3-lightrag-half-decomposed-crossing-join-chunks-heading-backfill | value-crossing | join-chunks -> heading-backfill | 'heading-backfill''s dep edge on 'join-chunks' is by construction a point where a value crosses between operations |
| w3-lightrag-half-decomposed-effects-chunk-sel-kg-join-chunks | effects-change | chunk-sel-kg -> join-chunks | declared effects[] differs across this dep edge; symmetric difference: ['reads_kv', 'reads_vector'] |
| w3-lightrag-half-decomposed-crossing-chunk-sel-kg-join-chunks | value-crossing | chunk-sel-kg -> join-chunks | 'join-chunks''s dep edge on 'chunk-sel-kg' is by construction a point where a value crosses between operations |
| w3-lightrag-half-decomposed-effects-entity-hydrate-expand-join-entities | effects-change | entity-hydrate-expand -> join-entities | declared effects[] differs across this dep edge; symmetric difference: ['reads_graph'] |
| w3-lightrag-half-decomposed-crossing-entity-hydrate-expand-join-entities | value-crossing | entity-hydrate-expand -> join-entities | 'join-entities''s dep edge on 'entity-hydrate-expand' is by construction a point where a value crosses between operations |
| w3-lightrag-half-decomposed-effects-entity-hydrate-expand-join-relations | effects-change | entity-hydrate-expand -> join-relations | declared effects[] differs across this dep edge; symmetric difference: ['reads_graph'] |
| w3-lightrag-half-decomposed-crossing-entity-hydrate-expand-join-relations | value-crossing | entity-hydrate-expand -> join-relations | 'join-relations''s dep edge on 'entity-hydrate-expand' is by construction a point where a value crosses between operations |
| w3-lightrag-half-decomposed-effects-ingest-keywords | effects-change | ingest -> keywords | declared effects[] differs across this dep edge; symmetric difference: ['reads_graph', 'reads_kv', 'writes_artifact'] |
| w3-lightrag-half-decomposed-crossing-ingest-keywords | value-crossing | ingest -> keywords | 'keywords''s dep edge on 'ingest' is by construction a point where a value crosses between operations |
| w3-lightrag-half-decomposed-effects-heading-backfill-rerank | effects-change | heading-backfill -> rerank | declared effects[] differs across this dep edge; symmetric difference: ['calls_rerank', 'reads_kv'] |
| w3-lightrag-half-decomposed-crossing-heading-backfill-rerank | value-crossing | heading-backfill -> rerank | 'rerank''s dep edge on 'heading-backfill' is by construction a point where a value crosses between operations |
| w3-knob-ingest-query-boundary | knob | ingest -> query-side | the opaque ingest core's boundary against the decomposed query side: ingest can be replaced by a different ingest implementation, or bypassed by a pre-populated store, without changing query-side's own socket |

## Self-declaration probes

SELECTION.md Falsifier 1 limb (b) and Falsifier 2's own no-self-declaration clause (02-CONTEXT.md D-03), demonstrated as paired refusal-and-control probes resolved against `probe_registry()` (`default_registry()` plus two probe-only parts never registered into the production registry). Every probe expecting a refusal is paired with a control that must not fire, so a check that has stopped firing surfaces as a failed probe rather than as a quietly green suite.

| probe_id | wiring shape | expected code | observed code | verdict |
|---|---|---|---|---|
| a-effects-exceed-part | cbm:codebase-memory-mcp@0.1.0 | effects-exceed-part | effects-exceed-part | fired as expected |
| b1-shared-write-at-stage | writer:probe/shared-artifact-writer@0.1.0 | — (control) | — | OK (no violation) |
| b2-shared-write-at-evidence | writer:probe/evidence-writer@0.1.0 | blast-radius-refusal | blast-radius-refusal | fired as expected |
| b3-shared-write-tainted-to-opaque | cbm:codebase-memory-mcp@0.1.0, extract:probe/shared-artifact-writer@0.1.0 | blast-radius-refusal | blast-radius-refusal | fired as expected |
| c1-self-declared-effective-depth | ingest:lightrag/full-ingest@0.1.0, keywords:lightrag/keyword-extractor@0.1.0, embedder-query:lightrag/embedder-query@0.1.0, entity-lookup:lightrag/entity-lookup@0.1.0, entity-hydrate-expand:lightrag/entity-hydrate-expand@0.1.0, join-entities:lightrag/join-roundrobin@0.1.0, join-relations:lightrag/join-roundrobin@0.1.0, budget-entities:lightrag/truncator-token-budget@0.1.0, budget-relations:lightrag/truncator-token-budget@0.1.0, chunk-sel-kg:lightrag/chunk-selector-kg@0.1.0, join-chunks:lightrag/join-roundrobin@0.1.0, heading-backfill:lightrag/chunk-heading-backfiller@0.1.0, rerank:lightrag/reranker-cross-encoder@0.1.0, assemble:lightrag/assembler-kg-context@0.1.0, generate:lightrag/generator-llm@0.1.0, embedder-index:lightrag/embedder-index@0.1.0 | self-declared-derivation | self-declared-derivation | fired as expected |
| c2-unknown-node-key | ingest:lightrag/full-ingest@0.1.0, keywords:lightrag/keyword-extractor@0.1.0, embedder-query:lightrag/embedder-query@0.1.0, entity-lookup:lightrag/entity-lookup@0.1.0, entity-hydrate-expand:lightrag/entity-hydrate-expand@0.1.0, join-entities:lightrag/join-roundrobin@0.1.0, join-relations:lightrag/join-roundrobin@0.1.0, budget-entities:lightrag/truncator-token-budget@0.1.0, budget-relations:lightrag/truncator-token-budget@0.1.0, chunk-sel-kg:lightrag/chunk-selector-kg@0.1.0, join-chunks:lightrag/join-roundrobin@0.1.0, heading-backfill:lightrag/chunk-heading-backfiller@0.1.0, rerank:lightrag/reranker-cross-encoder@0.1.0, assemble:lightrag/assembler-kg-context@0.1.0, generate:lightrag/generator-llm@0.1.0, embedder-index:lightrag/embedder-index@0.1.0 | invalid-node-schema | invalid-node-schema | fired as expected |
| c3-computed-depth-governs | ingest:lightrag/full-ingest@0.1.0, keywords:lightrag/keyword-extractor@0.1.0, embedder-query:lightrag/embedder-query@0.1.0, entity-lookup:lightrag/entity-lookup@0.1.0, entity-hydrate-expand:lightrag/entity-hydrate-expand@0.1.0, join-entities:lightrag/join-roundrobin@0.1.0, join-relations:lightrag/join-roundrobin@0.1.0, budget-entities:lightrag/truncator-token-budget@0.1.0, budget-relations:lightrag/truncator-token-budget@0.1.0, chunk-sel-kg:lightrag/chunk-selector-kg@0.1.0, join-chunks:lightrag/join-roundrobin@0.1.0, heading-backfill:lightrag/chunk-heading-backfiller@0.1.0, rerank:lightrag/reranker-cross-encoder@0.1.0, assemble:lightrag/assembler-kg-context@0.1.0, generate:lightrag/generator-llm@0.1.0, embedder-index:lightrag/embedder-index@0.1.0 | — (control) | — | OK (no violation) |

- **a-effects-exceed-part**: If this stopped firing, a wiring node could claim an effect its resolved part does not back — an unbounded capability claim admitted silently.
- **b1-shared-write-at-stage**: Control. If this fired, a legitimate shared-artifact write at effective depth stage would be wrongly refused.
- **b2-shared-write-at-evidence**: If this stopped firing, a shared-artifact write reachable only at effective depth evidence would escape the blast-radius rule.
- **b3-shared-write-tainted-to-opaque**: SELECTION.md Falsifier 1 limb (b). If this stopped firing, an opaque node could launder a shared-scope write through a downstream extractor by hiding behind the taint rule.
- **c1-self-declared-effective-depth**: If this stopped firing, an author's self-declared effective_depth would silently stand in for the computation MACH-01 requires.
- **c2-unknown-node-key**: If this classified as self-declared-derivation instead of invalid-node-schema, a typo and an attempted self-declaration would be indistinguishable by code alone.
- **c3-computed-depth-governs**: Control. If this fired, the computation itself would be broken on an ordinary wiring that carries no self-declaration at all.

## Falsifier 2 verdict

SELECTION.md's `## Falsifiers` list, item 2: "Depth cannot be computed statically. Over three real parts (decomposed `lightrag-local`, opaque `codebase-memory-mcp`, half-decomposed LightRAG), the validator cannot derive `depth` from wiring + registry without a self-declaration. Then D4 has no brake and D's regime was doing structural work."

**Result: Falsifier 2 did not fire.** Every `effective_depth` and `execution_mode` value in every wiring above was derived from that wiring's `nodes`/`deps` plus `default_registry()` alone, through `databasise.validator.depth.effective_depth` and `databasise.validator.execution_mode.derive_execution_mode` — no self-declared depth or execution_mode field was read from any wiring document. D4's brake holds. All three named wirings above compute without any self-declaration, and every self-declaration and blast-radius refusal probe fired with its expected code, each paired with a control that did not fire — the computation governs regardless of what a wiring author attempts to write.
