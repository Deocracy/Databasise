# Spike Manifest

## Ideas

### melodyscribe
MelodyScribe: a micro-harness where one small local model (1B to 10B to start, D-MS-05) reads a sectioned input (the Score), emits the section embedding and a grammar-constrained op list in one pass, files the ops into graph / SQL / Folio stores through a validator, keeps reusable KV state, and serves a frontier model through one human-authored skill. Research base: `reference/micro-harnesses/`. These spikes settle the input/output contract and the three unknowns the rig must measure.

**Requirements:**
- Model-written skills (Folios) run sandboxed and are read only by MelodyScribe; the frontier reads one human-authored skill (D-MS-01, D-MS-02)
- The model never authors Score directives; directives come from the chunker or the frontier skill
- Model size is a rig variable; report the size-versus-accuracy curve before choosing (D-MS-05)
- Grammar constraints guarantee format only; accuracy comes from training and is measured on the rig
- No vendor benchmark settles anything; every verdict comes from a local measurement on the 20-document parity corpus
- Every measurement run holds the GPU lock so numbers are never taken under contention
- v0.1 defaults adopted overnight for the spec's open decisions, owner review pending: graph nodes filed by normalised name (alias merging is a revise concern); one generic `facts` table for SQL; `folio` ops allowed during bulk ingest under the sandbox rule; `doc_prefix` includes the chat-template system turn; `[EMB]`/`[RQ]` token ids chosen per model by spike 002 and recorded

## Spikes

| # | Idea | Name | Type | Validates | Verdict | Tags |
|---|------|------|------|-----------|---------|------|
| 001 | melodyscribe | score-io-model | standard | Given a Score with directives, when compiled, then every section maps to a deterministic token plan and every model output to a typed op with no ambiguous case | VALIDATED (toy tokenizer; real ids re-checked in 002) | score, compiler, schema, grammar |
| 002 | melodyscribe | one-pass-runtime | standard | Given llama-cpp-python with CUDA on legion and MiniCPM5-2B, when one decode runs over prefix+section+[EMB], then embeddings and logits come from the same call, ops decode under grammar, isolated sequences are neighbour-independent, and throughput is recorded | VALIDATED (reproduced by owner-side re-run) | llama.cpp, cuda, kv, embeddings |
| 003 | melodyscribe | op-emission-size-sweep | comparison | Given frontier-labelled ops for the corpus, when each model size emits ops under grammar with thinking off, then routing accuracy and tokens per paragraph per size | PENDING | size-sweep, accuracy, teacher |
| 004 | melodyscribe | self-embedding-parity | comparison | Given the corpus and its queries, when embedded by a dedicated 0.6B embedder, by untrained last-token states, and by a trained head over frozen states, then recall@k per method | PENDING | embeddings, recall, head |
| 005 | melodyscribe | kv-composition-quality | standard | Given a retrieved set, when composed as isolated KV modules versus full prefill versus shift reuse, then answer quality and TTFT per method | PENDING | kv, cacheblend, ttft |
