# Spike results (overnight run, 2026-09-12)

Five spikes built by Muse Spark 1.3 agents under `.planning/spikes/`, each reproduced by an owner-side re-run of its `run.sh` before the verdict entered the manifest. Every number below is in the spike's own `logs/`.

| # | Spike | Verdict | What it settled |
|---|---|---|---|
| 001 | score-io-model | VALIDATED | The Score compiler, the op grammar per file-set, and Proof pass 95/95 acceptance checks; token plans are deterministic and isolated-section token lists are byte-identical regardless of neighbours. Real-tokenizer check re-done in 002 |
| 002 | one-pass-runtime | VALIDATED | One `llama_decode` yields both the 2048-dim embedding and the logits; logits equal the greedy path; sequence copy is bit-exact; grammar-constrained ops parse where free decoding rambles; prefill about 3.7k tokens/s on MiniCPM5-2B Q8; reserved-token policy `emb=reserved:130080;rq=reserved:130081` |
| 003 | op-emission-size-sweep | pending | (filled when the sweep lands) |
| 004 | self-embedding-parity | PARTIAL | A dedicated 0.6B embedder beats untrained 2B last-token states by a wide margin (gold MRR 1.00 vs 0.31; self-query MRR 0.91 vs 0.55); the mechanism is anisotropy (pairwise cosine 0.91 to 0.95 vs 0.28); a ridge head over frozen states does not close the gap; contrastive adapter training with labelled query-passage pairs is the open test |
| 005 | kv-composition-quality | PARTIAL | Prebuilt chunk KV removes the prefill slope (TTFT 2.4x at 162 tokens, 8.5x at about 650) but the absolute saving is 20 to 110 ms at 2B scale; shift reuse saves about 1.1x; answer quality is equal up to greedy tie-flips; saved and reloaded KV state is not bit-exact and flips near-tie tokens on about a quarter of inputs |

## Signal for the build

1. **The one-pass mechanism is real at 2B** (002). Embedding and generation from the same decode, isolated sequences, copied prefixes, grammar ops: all measured, all reproducible.
2. **Untrained self-embedding is not usable** (004, confirming lane 1 of the deep research). The `[EMB]` state is neither the last-token state nor a good embedding without training. The dedicated 0.6B embedder is the durable-index baseline until a contrastive adapter beats it, which needs labelled pairs and is the next training spike.
3. **KV modules are second-order at this scale** (005), exactly as the efficiency design argued from the arithmetic. Keep runtime prefix reuse; do not build a persisted module store for the corpus. Any persisted-state path must budget the tie-flip noise; grammar-constrained op decoding is robust to it.
4. **Grammar buys format, not truth** (002): zero-shot ops are vacuous and one-shot ops fabricate evidence spans that Proof rejects. Accuracy is a training result, which 003 measures across sizes.
5. **Spec v0.2 candidate** (003's teacher log): even the frontier teacher fails Proof's evidence rule when evidence is a character span. Evidence should be a quoted substring the harness locates, with offsets computed harness-side.
6. **Runtime rules** now in `CONVENTIONS.md`: never prepend BOS for MiniCPM5; tokenize prefix and section as one string; `get_embeddings_ith` indexes outputs, not positions; reject empty sections; enforce context limits chunker-side; one model per process; every load under the GPU lock.
