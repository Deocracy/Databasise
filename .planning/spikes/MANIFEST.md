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
- Labelled data is teacher-generated with provenance and a fixed train/test split by document (`.planning/spikes/shared/`); nothing is hand-labelled and no spike trains on test documents
- Any adapter or merge reports generation retained: op emission Proof-pass rate and routing with the change on versus off
- Training and merging run in `.planning/spikes/.venv-train` on safetensors under `.models/hf/`; GGUF stays inference-only
- v0.1 defaults adopted overnight for the spec's open decisions, owner review pending: graph nodes filed by normalised name (alias merging is a revise concern); one generic `facts` table for SQL; `folio` ops allowed during bulk ingest under the sandbox rule; `doc_prefix` includes the chat-template system turn; `[EMB]`/`[RQ]` token ids chosen per model by spike 002 and recorded

## Spikes

| # | Idea | Name | Type | Validates | Verdict | Tags |
|---|------|------|------|-----------|---------|------|
| 001 | melodyscribe | score-io-model | standard | Given a Score with directives, when compiled, then every section maps to a deterministic token plan and every model output to a typed op with no ambiguous case | VALIDATED (toy tokenizer; real ids re-checked in 002) | score, compiler, schema, grammar |
| 002 | melodyscribe | one-pass-runtime | standard | Given llama-cpp-python with CUDA on legion and MiniCPM5-2B, when one decode runs over prefix+section+[EMB], then embeddings and logits come from the same call, ops decode under grammar, isolated sequences are neighbour-independent, and throughput is recorded | VALIDATED (reproduced by owner-side re-run) | llama.cpp, cuda, kv, embeddings |
| 003 | melodyscribe | op-emission-size-sweep | comparison | Given frontier-labelled ops for the corpus, when each model size emits ops under grammar with thinking off, then routing accuracy and tokens per paragraph per size | VALIDATED (reproduced: all 126 student decodes byte-identical and every metric equal on the owner re-run; 1B emits no ops, routing flat 0.30 to 0.45 across 2B to 8B pre-fine-tune, recall rises only with verbosity; quote evidence works where character offsets fail for every model) | size-sweep, accuracy, teacher |
| 004 | melodyscribe | self-embedding-parity | comparison | Given the corpus and its queries, when embedded by a dedicated 0.6B embedder, by untrained last-token states, and by a trained head over frozen states, then recall@k per method | PARTIAL (reproduced: dedicated 0.6B wins, untrained states anisotropic, linear head fails; contrastive adapter untested, needs 003's labels) | embeddings, recall, head |
| 005 | melodyscribe | kv-composition-quality | standard | Given a retrieved set, when composed as isolated KV modules versus full prefill versus shift reuse, then answer quality and TTFT per method | PARTIAL (reproduced: warm KV modules cut TTFT 2.4–8.5x relative but only 20–110 ms absolute at 2B; shift reuse no practical win; no quality difference beyond tie-flips; saved/loaded KV not bit-exact) | kv, cacheblend, ttft |
| 006 | melodyscribe | hybrid-embedder | comparison | Given teacher-generated query-passage pairs with a held-out split, when the 2B's [EMB] state is trained (LoRA contrastive; distillation to the 0.6B embedder) and when the 0.6B embedder is weight-merged with its generative base, then recall@k versus the dedicated embedder and generation retained per mixed model | PENDING | embeddings, adapter, merge, training |
| 007 | melodyscribe | embedding-prompt-sensitivity | comparison | Given the corpus and the shared query set, when embedded under different instruction, prefix, and marker designs on the 0.6B embedder and the 2B [EMB] state, then recall@k, MRR, and anisotropy per design | PENDING | embeddings, prompts, doc-prefix |
| 008 | melodyscribe | graph-prompt-design | comparison | Given spike 003's teacher labels, when the 2B and 4B emit ops under the v0.2 grammar with eight prompt designs, then routing, Proof-pass, recall, and tokens per paragraph per design | PENDING | prompts, graph, few-shot |
| 009 | melodyscribe | batched-serving-and-cache-order | comparison | Given N queued requests, when served with continuous batching and prefix-ordered prompts on one GPU, then throughput, TTFT, VRAM, and cache-hit fraction per N and slot count | PENDING | serving, batching, prefix-cache |
| 010 | melodyscribe | pipeline-order-end-to-end | standard | Given the corpus and query sets, when the harness runs end to end with W workers over graph, SQL, and vector stores, then documents per minute, recall per retrieval mode, payload tokens, and the effect of stage order and W | PENDING | pipeline, stores, workers |
