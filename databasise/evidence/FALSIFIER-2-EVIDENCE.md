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

### CONTRACT §19.10 — boundary enumeration

Before applying §19.1–§19.6, the author MUST enumerate candidate boundaries by a stated, source-derived procedure — at minimum every point where the declared `effects[]` set changes, every point where a declared knob sits, and every point where a value crosses between operations. The enumeration below is recorded with this wiring's node set, so a second author can check the candidate set, not only the verdicts reached on it.

| boundary_id | class | between | rationale |
|---|---|---|---|
| w1-lightrag-query-side-effects-generate-assemble | effects-change | generate -> assemble | declared effects[] differs across this dep edge; symmetric difference: ['calls_llm', 'writes_kv'] |
| w1-lightrag-query-side-crossing-generate-assemble | value-crossing | generate -> assemble | 'assemble''s dep edge on 'generate' is by construction a point where a value crosses between operations |
| w1-lightrag-query-side-effects-query-side-generate | effects-change | query-side -> generate | declared effects[] differs across this dep edge; symmetric difference: ['calls_embedding', 'reads_graph', 'reads_kv', 'reads_vector', 'writes_kv'] |
| w1-lightrag-query-side-crossing-query-side-generate | value-crossing | query-side -> generate | 'generate''s dep edge on 'query-side' is by construction a point where a value crosses between operations |
| w1-lightrag-query-side-effects-retrieve-query-side | effects-change | retrieve -> query-side | declared effects[] differs across this dep edge; symmetric difference: ['calls_embedding', 'calls_llm', 'reads_graph', 'reads_kv'] |
| w1-lightrag-query-side-crossing-retrieve-query-side | value-crossing | retrieve -> query-side | 'query-side''s dep edge on 'retrieve' is by construction a point where a value crosses between operations |
| w1-lightrag-query-side-effects-refine-query-side | effects-change | refine -> query-side | declared effects[] differs across this dep edge; symmetric difference: ['calls_embedding', 'calls_llm', 'reads_graph', 'reads_kv', 'reads_vector'] |
| w1-lightrag-query-side-crossing-refine-query-side | value-crossing | refine -> query-side | 'query-side''s dep edge on 'refine' is by construction a point where a value crosses between operations |
| w1-lightrag-query-side-effects-retrieve-refine | effects-change | retrieve -> refine | declared effects[] differs across this dep edge; symmetric difference: ['reads_vector'] |
| w1-lightrag-query-side-crossing-retrieve-refine | value-crossing | retrieve -> refine | 'refine''s dep edge on 'retrieve' is by construction a point where a value crosses between operations |
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

Resolved against `default_registry()`'s Phase-1 entries (3 node(s)).

| node id | component | wiring kind | structural_depth | effective_depth | execution_mode | part effects | artifact_scope | blast-radius |
|---|---|---|---|---|---|---|---|---|
| assemble | parts-core/passthrough@1.0.0 | passthrough | stage | opaque | in-process | — | — | n/a |
| ingest | lightrag/full-ingest@0.1.0 | opaque | opaque | opaque | subprocess | calls_llm, reads_graph, reads_kv, writes_artifact | quarantined | permitted |
| query-side | lightrag/query-side@0.1.0 | subgraph | stage | opaque | in-process | calls_embedding, calls_llm, reads_graph, reads_kv, reads_vector | — | n/a |

**Divergence from declared structural_depth:**

Nodes whose computed `effective_depth` diverges from their part's own `structural_depth` (the taint rule overriding a declared depth): assemble, query-side.

### CONTRACT §19.10 — boundary enumeration

Before applying §19.1–§19.6, the author MUST enumerate candidate boundaries by a stated, source-derived procedure — at minimum every point where the declared `effects[]` set changes, every point where a declared knob sits, and every point where a value crosses between operations. The enumeration below is recorded with this wiring's node set, so a second author can check the candidate set, not only the verdicts reached on it.

| boundary_id | class | between | rationale |
|---|---|---|---|
| w3-lightrag-half-decomposed-effects-query-side-assemble | effects-change | query-side -> assemble | declared effects[] differs across this dep edge; symmetric difference: ['calls_embedding', 'calls_llm', 'reads_graph', 'reads_kv', 'reads_vector'] |
| w3-lightrag-half-decomposed-crossing-query-side-assemble | value-crossing | query-side -> assemble | 'assemble''s dep edge on 'query-side' is by construction a point where a value crosses between operations |
| w3-lightrag-half-decomposed-effects-ingest-query-side | effects-change | ingest -> query-side | declared effects[] differs across this dep edge; symmetric difference: ['calls_embedding', 'reads_vector', 'writes_artifact'] |
| w3-lightrag-half-decomposed-crossing-ingest-query-side | value-crossing | ingest -> query-side | 'query-side''s dep edge on 'ingest' is by construction a point where a value crosses between operations |
| w3-knob-ingest-query-boundary | knob | ingest -> query-side | the opaque ingest core's boundary against the decomposed query side: ingest can be replaced by a different ingest implementation, or bypassed by a pre-populated store, without changing query-side's own socket |

## Self-declaration probes

SELECTION.md Falsifier 1 limb (b) and Falsifier 2's own no-self-declaration clause (02-CONTEXT.md D-03), demonstrated as paired refusal-and-control probes resolved against `probe_registry()` (`default_registry()` plus two probe-only parts never registered into the production registry). Every probe expecting a refusal is paired with a control that must not fire, so a check that has stopped firing surfaces as a failed probe rather than as a quietly green suite.

| probe_id | wiring shape | expected code | observed code | verdict |
|---|---|---|---|---|
| a-effects-exceed-part | cbm:codebase-memory-mcp@0.1.0 | effects-exceed-part | effects-exceed-part | fired as expected |
| b1-shared-write-at-stage | writer:probe/shared-artifact-writer@0.1.0 | — (control) | — | OK (no violation) |
| b2-shared-write-at-evidence | writer:probe/evidence-writer@0.1.0 | blast-radius-refusal | blast-radius-refusal | fired as expected |
| b3-shared-write-tainted-to-opaque | cbm:codebase-memory-mcp@0.1.0, extract:probe/shared-artifact-writer@0.1.0 | blast-radius-refusal | blast-radius-refusal | fired as expected |
| c1-self-declared-effective-depth | ingest:lightrag/full-ingest@0.1.0, query-side:lightrag/query-side@0.1.0, assemble:parts-core/passthrough@1.0.0 | self-declared-derivation | self-declared-derivation | fired as expected |
| c2-unknown-node-key | ingest:lightrag/full-ingest@0.1.0, query-side:lightrag/query-side@0.1.0, assemble:parts-core/passthrough@1.0.0 | invalid-node-schema | invalid-node-schema | fired as expected |
| c3-computed-depth-governs | ingest:lightrag/full-ingest@0.1.0, query-side:lightrag/query-side@0.1.0, assemble:parts-core/passthrough@1.0.0 | — (control) | — | OK (no violation) |

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
