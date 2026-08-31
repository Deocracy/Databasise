# Falsifier 2 Evidence

Computed-vs-declared depth and execution_mode for each of MACH-01's named wirings, resolved against `default_registry()` and computed by `databasise.validator.depth.effective_depth` and `databasise.validator.execution_mode.derive_execution_mode` — the same functions the runner calls, never a reimplementation.

## w1-lightrag-query-side — Decomposed lightrag-local query side

Resolved against `default_registry()`'s Phase-1 entries (5 node(s)).

| node id | component | wiring kind | structural_depth | effective_depth | execution_mode | part effects | artifact_scope | blast-radius |
|---|---|---|---|---|---|---|---|---|
| assemble | parts-core/passthrough@1.0.0 | passthrough | stage | stage | in-process | — | — | n/a |
| generate | parts-core/fake-llm-caller@1.0.0 | llm-caller | stage | stage | in-process | calls_llm, writes_kv | — | n/a |
| query-side | lightrag/query-side@0.1.0 | subgraph | stage | stage | in-process | calls_embedding, calls_llm, reads_graph, reads_kv, reads_vector | — | n/a |
| refine | parts-core/fixpoint-body@1.0.0 | fixpoint | stage | stage | long-lived-service | — | — | n/a |
| retrieve | parts-core/fake-retriever@1.0.0 | retriever | stage | stage | in-process | reads_vector | — | n/a |

**Divergence from declared structural_depth:**

No node's computed `effective_depth` diverges from its part's own `structural_depth`.
