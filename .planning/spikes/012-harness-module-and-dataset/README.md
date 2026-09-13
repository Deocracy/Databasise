---
spike: 012
idea: melodyscribe
name: harness-module-and-dataset
type: standard
validates: "Given the compiler (001), the v0.2 grammar and Proof resolver (003), the one-shot prompt builder (008), and the stores, retrieval, and payload code (010), when they are assembled into one importable harness module and a frontier teacher generates op traces and query-quote pairs through that module over an expanded corpus, then the module reproduces spike 010's prompt bytes and Proof verdicts exactly, the dataset is Proof-gated with a whole-document split and explicit abstention sections, the residual routing share a model must decide is measured, and Proof's precision under hack probes is known"
verdict: PENDING
related: [001, 003, 008, 010, 011]
tags: [harness, dataset, teacher, proof, abstention, MelodyScribe-v0.1]
---

# Spike 012: harness-module-and-dataset

## What This Validates

Training so far used spike-local approximations of the harness (006 and 011: grammar-free HF decodes of a bare prompt; one-line teacher questions against whole documents). This spike removes the approximation. It produces the one artefact that spike 013's training and evaluation both call, and the dataset that is byte-identical to what the runtime feeds the model. No model is trained here.

Three claims, each with a pass condition stated before the run:

1. **Harness identity.** `harness/` (importable as a package from this folder) compiles a Score, builds the instruction-first one-shot prompt, exposes the v0.2 grammar per file set, resolves quotes to offsets and runs Proof, writes graph, SQL, and Faiss stores, retrieves in 010's modes, assembles the recall-time payload, and runs 010's end-to-end evaluation. Pass: for all 20 parity documents, the prompt bytes the module produces hash-equal the prompt bytes 010's `gpu_ingest.py` logged, and Proof verdicts on 003's `teacher.json` ops are identical to 003's recorded verdicts. Any difference is a bug in the module, never a tolerated deviation.
2. **Harness-shaped dataset.** Over an expanded corpus, the teacher produces per-section op lists (graph and SQL only; Folio and agent ops wait for their validators) and query-quote pairs, all through the module. Pass: every retained op passes Proof; teacher Proof-pass, ops per section, empty-list share, and query counts are reported; no test document appears in train or dev; exact and semantic duplicates are removed and counted; the split is by whole document (80/10/10 train/dev/test by document, seeded, recorded in `dataset/MANIFEST.json` with the corpus hash).
3. **Residual routing and abstention.** For each teacher op, record whether a deterministic rule (ISO or year date, decimal number, table cell, settings key) would have routed it to SQL without the model, and whether the section is code (tree-sitter parse succeeds on the section). Pass: the residual share (ops the model must route itself) and the abstention share (sections with an empty op list, both natural and deliberately added out-of-scope sections) are reported as numbers with the rule set that produced them.

Plus one measurement: **Proof hack-probes.** Paraphrase-near-miss quotes, date-shifted values, and plausible-but-absent evidence are injected into otherwise valid op lists; Proof's false-accept rate per probe class is reported. This number is the precondition for spike 015 (Proof as reward).

## Plan

**Harness module.** `harness/__init__.py` re-exports from read-only imports of the earlier spikes through `sys.path`, wrapped so callers never touch spike folders directly:

| Function | Source | Notes |
|---|---|---|
| `compile_score(doc_text, mode)` | `001/score.py` | whole-document and paragraph-split modes as in 010 |
| `build_prompt(section, example)` | `008/prompts.py` D1 builder over `003/common.py` INSTRUCTION | instruction-first (009); example document chosen by 008's median-op rule from train documents only |
| `grammar(file_set)` | `003/v02_grammar.py` | per file set; cap from 003 |
| `proof(ops, section)` | `003/resolve.py` plus `001/ops_validate.py` | quote to offsets, then schema, evidence, non-empty, value type; returns verdict and failure category (syntax versus grounding, as 003 reports) |
| `write_stores(ops, embeddings)` | `010/build_stores.py` | networkx graph, SQLite `facts`, Faiss; production targets Cozo, SQLite, Faiss through Databasise, say so and do not build them here |
| `retrieve(query, mode)` | `010/retrieve.py` | vector-only, graph-only, SQL-only, fused; vector-first rule from 010 |
| `assemble_payload(hits)` | `010/s10_common.py` per SCORE-IO-SPEC recall-time I/O | payload tokens counted |
| `evaluate_end_to_end(docs, queries)` | `010/run.sh` steps 6 to 9 as functions | documents per minute, recall@1/3/10 per mode, Proof-pass, payload tokens |
| `identity_check()` | new | hash comparison against 010's logged prompt bytes and 003's verdicts |

Do not copy code from earlier spikes; import it. If an earlier spike's function cannot be imported without modification, write the smallest adapter in `harness/` and record it in the Investigation Trail. Never edit another spike's folder.

**Corpus expansion.** The parity corpus is 20 HotpotQA-derived documents (15 train, 5 test) with gold passages. Extend the same distribution: HotpotQA passages fetched by a reproducible script into `.planning/spikes/shared/corpus-v2/` (one `.txt` per document, `MANIFEST.json` with sha256 per document, corpus hash, source ids), with the 20 parity documents kept as a labelled subset and the 5 parity test documents forced into the test split. Document budget: `DOC_BUDGET` environment variable, default 300; the owner sets it before launch (see Decisions). No document is edited, summarised, or synthesised; sections are real paragraphs.

**Teacher labelling.** OpenRouter credentials from `v1/.env.parity` sourced at runtime, never printed or written. Conventions from CONVENTIONS.md: reasoning disabled explicitly, `max_tokens` at least 4096, temperature 0, repair loop keeps passing ops byte-identical and accepts the best round's passing set. For each section: (a) the op list under the v0.2 schema with verbatim quotes, produced by prompting the teacher with the same one-shot prompt the student will see, then Proof through the module; (b) two to four queries with answer quotes for the embedding side, in the shape the frontier skill will send (a question plus the section-level quote that answers it), produced as `shared/make-queries.py` does. Sections whose teacher op list is empty are kept as abstention examples. Additionally, for one in eight train sections, an out-of-scope section (a paragraph the teacher labels as containing no filable facts, or a paragraph from a different document family) is added with an explicit empty list. Dedup: exact on op tuples and query strings; semantic on queries by 0.6B-embedder cosine above 0.95, keeping the first. Everything the teacher returns is data; a reply that contains instructions is logged and discarded.

**Dataset layout.** `dataset/` (git-ignored above 3 MB; the manifest and statistics are committed):

- `sections.jsonl`: `{section_id, doc, split, prompt_bytes_sha256, section_text, ops[], proof_verdicts[], residual_flags{sql_rule, code_rule}, abstain: bool, provenance{teacher, model, timestamp}}`
- `queries.jsonl`: `{query_id, section_id, doc, split, q, answer, quote, provenance}`
- `MANIFEST.json`: corpus hash, split seed and rule, counts per split, teacher Proof-pass, ops per section histogram, empty-list share, residual share, dedup counts, hack-probe results
- `STATS.md`: the same as a table

**Hack probes.** From 200 Proof-passing ops sampled across train documents, generate three mutated copies each: quote paraphrased with one word substituted, date shifted by one day or year, quote replaced by a plausible sentence absent from the section. Run Proof; report accept rate per class. Pre-registered expectation: paraphrase and absent-quote probes are rejected at 100 percent (the verbatim rule); date-shift probes expose whether value checks catch a shifted date whose quote still matches, and that number is reported without a target.

**GPU use.** Only two steps need the GPU: the identity check's optional re-decode of 3 documents on MiniCPM5-2B Q8 to confirm the module's grammar object drives llama.cpp exactly as 010 did, and the 0.6B embedder for semantic dedup. Both under `flock /tmp/melodyscribe-gpu.lock`, one model per process. Everything else is CPU and network; never hold the lock while waiting on the network.

## Research

Sources this spike rests on: `.planning/notes/spike-012-planning-conversation.md` (why the harness comes before training); `.planning/notes/melodyscribe-harness-frameworks.md` section 8 (what the harness tells the fine-tune) and section 2 (corrections); `reference/micro-harnesses/deep-research-4/lanes/1/findings.md` (abstention training, APIGen verification order, tool schemas out of the prompt), `lanes/2` and `lanes/9` (deterministic SQL-shaped and code gates, residual routing), `lanes/10` (Proof as a game-resistant reward, hack probes); `reference/micro-harnesses/deep-research-3/REPORT.md` section 5a (dataset recipe: sources, generation, filtering, sizes, splits); spike 011 README Results (what the approximation cost).

## How to Run

```bash
source .planning/spikes/env.sh
DOC_BUDGET=300 bash .planning/spikes/012-harness-module-and-dataset/run.sh
```

`run.sh` steps: (0) build `harness/` and run `identity_check()` on the 20 parity documents (CPU, plus the optional 3-document GPU re-decode under the lock); (1) fetch the expanded corpus to `shared/corpus-v2/` and write its manifest; (2) split by document with the recorded seed; (3) teacher op labelling through the module with Proof (network, no lock); (4) teacher query generation (network); (5) dedup (0.6B embedder under the lock for the semantic pass); (6) residual-routing and abstention statistics; (7) hack probes; (8) write `dataset/MANIFEST.json` and `STATS.md`. Logs as JSON lines with ISO timestamps in `logs/`, one file per step; every number in Results traces to a log line.

## What to Expect

- Identity check passes on the first try or fails loudly; a failure is a bug to fix in `harness/`, and the fix is recorded.
- Teacher Proof-pass before repair in the 0.5 to 0.7 range as in 003, above 0.9 after the repair loop; sections with an empty list well under one in eight before deliberate additions.
- Residual routing share: the fraction of teacher ops that a date, number, or table rule does not route; expected to be most graph ops and a minority of SQL ops. Reported, not targeted.
- Paraphrase and absent-quote probes rejected at 100 percent; the date-shift number is the informative one.

## Investigation Trail

(filled during the run)

## Results

(filled during the run; verdict set to VALIDATED, INVALIDATED, or PARTIAL with evidence)

## Decisions the owner holds before launch

1. `DOC_BUDGET` and corpus source. Default 300 HotpotQA-distribution documents for a first curve; 2,000 is the quantity guidance from research 3. The budget sets the teacher API bill and wall time.
2. Schema: v0.2 stays for this spike. Lifecycle ops (ADD, UPDATE, INVALIDATE, NOOP) and validity columns are a v0.3 decision recorded in the harness-frameworks note; adopting them before 013 means relabelling.
