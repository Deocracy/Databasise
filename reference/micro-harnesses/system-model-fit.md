# MelodyScribe against the system model

Date: 2026-09-11. Maps MelodyScribe onto `docs/system-model/` clause by clause. Every ruling cites the section that governs it. Where the model forces a change to what the exploration assumed, the change is stated as a correction. Owner analysis unless a section is cited.

## 1. What MelodyScribe is, in contract vocabulary

**MelodyScribe is a modality: a wiring over machine-owned primitives. It is not a "harness".** The contract already uses "harness" for something else: a stackable wrapper selected independently of the modality it wraps, ordered by array position (CONTRACT §1, §18.4, §19.8; ANATOMY §E row `HARN`). Inside Databasise, say "the MelodyScribe modality" or "the MelodyScribe wiring". "Micro-harness" stays as the name of the research pattern outside the contract. **Correction to NAMING.md, applied.**

## 2. Namespace and component names

CONTRACT §0: component names are `namespace/name@semver`, the namespace set is fixed (`core`, `lightrag`, `hipporag`, further namespaces one per ported system), and creating a namespace is a contract-level change tied to the porting protocol (PARTS-07), never minted at wiring time.

So `melodyscribe/` exists only once the porting protocol has been run. Until then MelodyScribe can enter as an opaque node (section 4 below) without a namespace of its own. Component names once ported:

| Component | Name | Kind |
|---|---|---|
| The served model, generation role | `core/llm-minicpm5-2b@…` | machine-owned LLM client (role-addressable, CONTRACT §14) |
| The served model, embedding role | `core/embedder-melodyscribe-2b@…` | machine-owned embedding client wrapping `encode()` (CONTRACT §13.4 row 2, §14 G2) |
| Ingest node | `melodyscribe/transcriber@…` | primitive part, `calls_llm`, `writes_*` |
| Store router | `melodyscribe/filer@…` | primitive part, `writes_graph`, `writes_vector`, `writes_kv`, `writes_artifact` |
| Background refinement | `melodyscribe/reviser@…` | hosted as `fixpoint` (CONTRACT §2) |
| Query-side assembler | `melodyscribe/recaller@…` | primitive part, `reads_*`, `calls_llm` |

Fine-tuned model identity `MelodyScribe-2B-v0.1` is the `model_id` and `revision` inside those two `core` clients, not a component name.

## 3. The model is a machine-owned client, not part of the node

CONTRACT §8 condition 3: an opaque node's network namespace is denied and **the machine acts as the injected LLM provider in its place**; an engine that cannot accept the injected endpoint is admitted `unbudgetable`, and the envelope must then refuse to report a token number (§18.2). CONTRACT §9: budget encloses ingest; spend is tracked with `counted_by` (§4).

Consequence: if the 2B model ran inside the MelodyScribe node, MelodyScribe would be `unbudgetable`. If the model is served by the machine (Ollama or SGLang behind the injected endpoint) as two `core` clients, every MelodyScribe token is counted and the node declares `calls_llm` and `calls_embedding` like any other. **Ruling: the model is a `core` client.** The exploration's picture of "one model inside a sandbox" survives as a deployment fact (one process serves both roles) but not as a contract fact.

Self-embedding is admissible as stated: the embedding client's `EmbeddingSpace` id is a hash over `(model_id, revision, dim, metric, normalization, query_prefix, doc_prefix, pooling, namespace_text_convention)` (CONTRACT §4). A new `MelodyScribe-2B-v0.2` is a new space, which invalidates the namespace and forces re-embedding (ANATOMY §D `IDX → KV` BINDS row). That is the index-side mutation class, priced in section 8.

## 4. Entry rung: opaque, then decompose

The build ladder admits a part at opaque depth and lifts it by decomposition (CONTRACT §8 framing; §6 node-to-subgraph). The **Scriptorium sandbox is not a new regime**: SELECTION D4 rules one machine, no sandbox regime, no `regime` field. What the exploration called the sandbox is CONTRACT §8 condition 3 (network namespace denied) plus condition 5 (`storage: machine | self-contained`), which every opaque node already gets.

While opaque, the eleven §8 conditions apply, four of which shape MelodyScribe directly:

- excluded from the default selector until effective depth leaves `opaque` (cond. 7);
- TTL about 90 days, renewable only with a recorded reason in the ledger (cond. 8);
- writes `quarantined` only, never `shared` (§3);
- `as_of` refused unless the `temporal` capability is declared (cond. 11), which matters if MelodyScribe stores validity-interval facts.

If MelodyScribe is packaged as an MCP server, §17 governs the adapter (process lifecycle, evidence normalised to `ItemKind` at the boundary); `codebase-memory-mcp` is the precedent. The recommended path: enter opaque under §8, then port properly under PARTS-07 to earn the `melodyscribe/` namespace, `stage` depth, `shared` writes, and default-selector eligibility.

## 5. Stores: no sixth store, and the contract already placed SQL

Five native store types, no sixth (CONTRACT §14.2 repaired at V-2; ANATOMY §B "Stores — five, no sixth"). CONTRACT §15 gives the four-branch procedure for any new storage need, tried in fixed order.

| MelodyScribe store | Placement | Clause |
|---|---|---|
| Graph, vector, KV | existing store types | §14.2 |
| SQL ("birthday goes to SQL") | **already worked by the contract:** machine-store SQL lands on Branch 2, an opaque blob artifact (SQLite) plus sidecar manifest naming the schema; declares `writes_artifact`, `storage: machine` | §15.2, §15.3 |
| Folios (model-written `.md` skills) | Branch 1 passes: KV records keyed by slug plus vector entries for retrieval, no new store type. Scope `self_storage`: readable only by the producing instance, refcounted to it, GC'd on unpin | §15.1 Branch 1; §3 scope table |

The `self_storage` scope is the contract's own statement of decision D-MS-01 (Folios are loaded only by MelodyScribe). Nothing new is needed to enforce it; the validator already refuses any other node reading `self_storage`.

Evidence MelodyScribe returns maps onto the frozen `ItemKind` union without additions: `text_chunk`, `graph_path`, `fact_with_validity_interval`, `sql_result_set` (§4). A Folio returned as evidence is a `text_chunk`.

## 6. The revise pass is a fixpoint node under budget

CONTRACT §2: iterative components MUST be hosted as `fixpoint` nodes; the executor, not the component, owns every loop and its halt condition. §9: budget encloses ingest; degradation paths are declared in the manifest; partial runs are first-class.

So MelodyScribe's cyclical refinement is `melodyscribe/reviser` hosted as `fixpoint`, with the halt condition and the budget outside the component. A revise pass that rewrites graph or vector artifacts is a mutation and goes through §6 promotion and the ledger. This is the structural answer to the lost-fact-layer incident: a self-refining model cannot loop or overwrite outside the executor's control.

## 7. The seam: no `melodyscribe_*` tools

CONTRACT §18.5 (restated at ANATOMY §E row `SEAM`): a new MCP/REST tool is earned only by a genuinely new operation; a per-modality tool for an operation an existing tool already exposes is refused. §18.3 invariance rule: swapping the fitted modality changes no field a consumer sees. §18.4: a consumer selects a modality by stable alias, declared capability, harness name, or the default selector, never by wiring or node id.

**Correction to NAMING.md, applied:** `transcribe` and `recall` are the existing ingest and query operations; `file` is internal to the wiring and never a seam operation. None of them gets a `melodyscribe_` tool. The frontier model selects MelodyScribe through the stable alias `melodyscribe` on the existing tools. The MelodyScribe skill (the one human-authored SKILL.md) therefore documents the existing seam tools plus that selector, which makes it even cheaper than the exploration assumed. `revise` is the only candidate for a genuinely new operation (background consolidation with no query and no ingest), and it must be argued under §18.5 before it earns a tool; the default is that it stays internal, invoked through the existing run verbs.

## 8. Pricing a MelodyScribe promotion

RIG §F3.1 states the verdict per mutation class: retrieval-side affordable; answer-level opt-in and rate-limited; index-side not affordable outside the §F3.3 fallback ladder (about 84-117M tokens per recipe version at the 10,000-chunk anchor). §F3.2: measurement-gated promotion is OFF by default except retrieval-side scoring.

MelodyScribe's first promotion claim is index-side (a new embedder is a new recipe version, section 3), so it runs on rung 4, sub-corpus screening, labelled degraded, like any other index-side mutation. Two things are new and are recorded as questions, not decided:

- The cost model prices tokens as API spend. MelodyScribe's tokens are local compute. `counted_by` still applies; the price per token does not. Whether §CM needs a local-compute price class is a RIG question for the owner.
- The judge stays a frontier model (decision D-MS-03; `judge_instance` in the §4 pooling key). MelodyScribe never judges its own promotion.

## 9. Open questions for the owner, in decision order

1. Enter as an opaque node under §8 now, or wait and port under PARTS-07 with the `melodyscribe/` namespace? Recommendation: opaque now, port after the two rig experiments pass.
2. Does `revise` earn a seam tool under §18.5, or stay internal? Recommendation: internal.
3. Does a locally served model need a local-compute price class in RIG §CM, or is index-side rung 4 simply the posture? Recommendation: leave §F3 as is; record the question in RIG's open list.
4. Which `ItemKind` carries a Folio when it is returned as evidence: `text_chunk`, or is a Folio never evidence (only an internal instruction to MelodyScribe)? Recommendation: never evidence, which also keeps model-written text out of the frontier's context by construction.

5. One client call returning both an embedding and a generation has no declared capability flag yet (see `runtime-one-pass.md`). Candidate: a §14 capability-table addition beside `prefix_continuation` and `prompt_cache`. Until then the node declares both `calls_llm` and `calls_embedding`.

## Not read in this pass

SYSTEM-MODEL §PC (per-modality port cost) and §H1, PARTS.md, CATALOG.md, MODEL-RED-TEAM.md, CONTRACT §6 (promotion and decomposition mechanics), §19 (node granularity), and the SELECTION.md spike-005 amendment text. Port-cost estimation for MelodyScribe waits on §PC.
