---
name: spike-findings-melodyscribe
description: Implementation blueprint from the MelodyScribe spikes. Requirements, proven patterns, measured numbers, and dead ends for building the MelodyScribe micro-harness (one small local model, sectioned Score input, one-pass embedding plus grammar-constrained ops, Proof validator, KV reuse). Auto-loaded during MelodyScribe implementation work.
---

<context>
## Project: MelodyScribe (inside Databasise 2.0)

MelodyScribe: a micro-harness where one small local model (1B to 10B to start, D-MS-05) reads a sectioned input (the Score), emits the section embedding and a grammar-constrained op list in one pass, files the ops into graph / SQL / Folio stores through a validator (Proof), keeps reusable KV state, and serves a frontier model through one human-authored skill. Research base: `reference/micro-harnesses/`. Under the Databasise contract it is a modality wiring, not a harness: the model is a `core` client (CONTRACT.md §8 condition 3), Scriptorium is §8 conditions 3 and 5, SQL is a §15 Branch 2 blob artifact, Folios are Branch 1 KV plus vector at `self_storage`, the reviser is `fixpoint`, and the EmbeddingSpace hash records doc_prefix, query_prefix, pooling, and the token policy.

Five spikes settled the input/output contract and the three unknowns the rig had to measure. Every verdict entered the manifest only after an owner-side re-run of the spike's `run.sh` reproduced it.

Spike sessions wrapped: 2026-09-12 (spikes 001, 002, 004, 005, then 003)
</context>

<requirements>
## Requirements

From the `melodyscribe` idea in `.planning/spikes/MANIFEST.md`:

- Model-written skills (Folios) run sandboxed and are read only by MelodyScribe; the frontier reads one human-authored skill (D-MS-01, D-MS-02)
- The model never authors Score directives; directives come from the chunker or the frontier skill
- Model size is a rig variable; report the size-versus-accuracy curve before choosing (D-MS-05)
- Grammar constraints guarantee format only; accuracy comes from training and is measured on the rig
- No vendor benchmark settles anything; every verdict comes from a local measurement on the 20-document parity corpus
- Every measurement run holds the GPU lock so numbers are never taken under contention
- v0.1 defaults adopted overnight for the spec's open decisions, owner review pending: graph nodes filed by normalised name (alias merging is a revise concern); one generic `facts` table for SQL; `folio` ops allowed during bulk ingest under the sandbox rule; `doc_prefix` includes the chat-template system turn; `[EMB]`/`[RQ]` token ids chosen per model by spike 002 and recorded

Added by the spikes (owner review pending where marked):

- Evidence in an op is a verbatim quote (3 to 256 characters) that the harness resolves to character offsets; character-offset evidence from the model is rejected (spec v0.2 candidate, spike 003; replaces SCORE-IO-SPEC §5 pending review)
- Every decode step carries a token cap: the grammar guarantees shape, only the cap guarantees termination (spike 003)
- The dedicated 0.6B embedder is the durable-index baseline until a trained adapter beats it on the rig; untrained last-token states are not embeddings (spike 004)
- Runtime prefix reuse stays; no persisted per-chunk KV module store for the corpus at 2B scale (spike 005)
- Never prepend BOS for MiniCPM5; tokenise prefix and section as one string; `llama_get_embeddings_ith` indexes the i-th output, not the position; reject empty sections; enforce context limits chunker-side; one model per process; every load under `flock /tmp/melodyscribe-gpu.lock` (spike 002)
</requirements>

<findings_index>
## Feature Areas

| Area | Reference | Key Finding |
|------|-----------|-------------|
| Score I/O contract | references/score-io-contract.md | Score XML, compilation to token plans, per-file-set grammar, and Proof pass 95/95 acceptance checks (001); evidence must be a quoted substring resolved harness-side, not model-emitted offsets (003, v0.2) |
| One-pass runtime | references/one-pass-runtime.md | One `llama_decode` yields the 2048-dim embedding and the logits; sequence copy is bit-exact; prefill about 3.7k tokens/s on MiniCPM5-2B Q8 (002). Prebuilt KV modules cut TTFT 2.4x to 8.5x relative but only 20 to 110 ms absolute at 2B; saved state is not bit-exact (005) |
| Model size and training | references/model-size-and-training.md | 1B emits no ops under greedy grammar decoding; routing accuracy is flat 0.30 to 0.45 from 2B to 8B pre-fine-tune while cost grows about a hundredfold (003). A dedicated 0.6B embedder beats untrained 2B states (gold MRR 1.00 vs 0.31) because the states are anisotropic; a ridge head does not fix it (004) |

## Source Files

Original spike source files (READMEs, scripts, schemas, the spec, the demo) are preserved in `sources/`; large logs, student outputs, and teacher labels stay in `.planning/spikes/NNN-*/`.
</findings_index>

<metadata>
## Processed Spikes

- 001-score-io-model (VALIDATED)
- 002-one-pass-runtime (VALIDATED)
- 003-op-emission-size-sweep (VALIDATED)
- 004-self-embedding-parity (PARTIAL: contrastive adapter untested)
- 005-kv-composition-quality (PARTIAL: absolute savings second-order at 2B)

Next project step: owner review of SCORE-IO-SPEC §10 open decisions and the v0.2 quote-evidence change, then the training spike (fine-tune on `teacher.json` labels, contrastive adapter with query-passage pairs) before any size is chosen. The digest is `reference/micro-harnesses/spike-results.md`.
</metadata>
