---
spike: 002
idea: melodyscribe
name: one-pass-runtime
type: standard
validates: "Given llama-cpp-python with CUDA on legion and MiniCPM5-2B, when one decode runs over prefix+section+[EMB], then embeddings and logits come from the same call, ops decode under grammar, isolated sequences are neighbour-independent, and throughput is recorded"
verdict: VALIDATED
related: [001-score-io-model]
tags: [llama.cpp, cuda, kv, embeddings]
---

# Spike 002: one-pass-runtime

## What This Validates
Given llama-cpp-python with CUDA on legion and MiniCPM5-2B, when one decode runs over prefix+section+[EMB], then embeddings and logits come from the same call, ops decode under grammar, isolated sequences are neighbour-independent, and throughput is recorded.

## Research
Docs read, in order: `.planning/spikes/MANIFEST.md`, `001-score-io-model/SCORE-IO-SPEC.md` + `ops.schema.json`, `reference/micro-harnesses/README.md`, plus the two directly relevant notes: `runtime-one-pass.md` (routes A/B/C, prompt-layout rule, efficiency claim) and `score-format-and-cache.md` (directives, KV reuse).

Approaches compared:
1. **Route A — one `llama_decode`, read both** (chosen for the crux): context with `embedding=True`, one manual batch over `prefix+section+[EMB]` with all positions marked outputs, then `get_embeddings_ith` at `[EMB]` and `get_logits_ith` at the last position. Verified in `llama_cpp` 0.3.35: the C API (`llama_batch`, `llama_decode`, `llama_get_embeddings_ith`, `llama_get_logits_ith`, `llama_memory_seq_cp/rm`) is all reachable through `llama_cpp.llama_cpp` and the `Llama._ctx`/`Llama._batch` handles. No PyTorch, ~300 lines of plain Python.
2. **Route B — llama-server two requests** (rejected for the spike): zero custom code but the shared-slot-cache ledger item is unverifiable here, and it cannot prove same-call duality by construction.
3. **High-level `Llama` only** (used for the non-crux arms): `create_completion(..., grammar=...)` for ops decode, `.embed()` for the isolation/throughput arms. One `Llama(embedding=True)` instance serves both, so generation and embedding share weights, process, and GPU.
4. **Token policy** (SCORE-IO-SPEC §2, preferred option): reserved ids `emb=130080;rq=reserved:130081` from the unused tail block `130072..130559` (detokenize empty). The `⟦EMB⟧` fallback marker is 5 tokens (`[66719,121,78407,66719,122]`), so the reserved single-id form wins. RQ id fed live through one decode to prove it is path-safe.

## How to Run
```
.planning/spikes/002-one-pass-runtime/run.sh
```
Sources `.planning/spikes/env.sh` (mandatory before importing `llama_cpp`). Runs `tok_probe.py` (vocab-only, no GPU, no lock), then `one_pass.py` as a single process under `flock /tmp/melodyscribe-gpu.lock` (loads MiniCPM5-2B-Q8_0 once, runs every arm). Per-check JSON lines with ISO timestamps append to `logs/run-<utc>.jsonl`; llama.cpp stderr goes to `logs/stderr-<utc>.log`. Reuses `score.ops_instruction`, `grammar.grammar_for_subset`, `ops_validate.validate_ops` from spike 001 by path import, and the hash-verified parity corpus via path-loaded `databasise/parity/corpus.py` (never imports the `databasise` package chain, per 001's lesson).

## What to Expect
- Final log `logs/run-20260912T081153Z.jsonl`: every `check` line `ok:true` (for `grammar_head_to_head`/`fewshot_ops`/`bounds`, `ok` means the arm executed; the verdicts live in `parse_ok`/`proof_ok` fields).
- Head-to-head: grammar `3/3` Proof-ok vs free `0/3`, identical inputs.
- Wall time ~10 s total (load ~0.8 s); prefill ~3.7k tok/s.
- Intermediate `run-0804/0805/0806/0807/0809/0811` logs show the debugging path (wrong comparisons, two crashes, one vacuous-validator bug) — kept deliberately.

## Investigation Trail
1. **API survey (no GPU).** `Llama(..., embedding, logits_all)`, `LlamaGrammar.from_string` (takes 001's GBNF verbatim), `Llama._ctx`: `decode/get_embeddings_ith/get_logits_ith/kv_cache_seq_cp/kv_cache_seq_rm`, `Llama._batch.set_batch/add_sequence`. Route A is implementable without leaving `llama-cpp-python`.
2. **Tokenizer probe.** Vocab 130560; BOS=0, EOS=1; chat template present (9060 chars, tool-call template — `doc_prefix` v0.1 records a fixed string; template application is later work). No single-token marker exists (`⟦EMB⟧` = 5 tokens), but tail ids `130072..130559` detokenize empty: reserved block. Policy recorded as `emb=reserved:130080;rq=reserved:130081`. 001-I1 re-passes on real ids (byte-identical `E_i` lists, neighbours differ).
3. **Run-1 (080453): everything runs, two mismatches.** `cos(one_decode, embed)=0.23`, one-decode argmax `ing` vs greedy `ande`. Diagnosis: my manual batch omitted BOS while `embed()` adds it — different positions, different distributions. Also found corpus sections were 11–18 chars (split on `\n\n` hit stub chunks): fixed to first ≥200-char paragraph with recorded char spans.
4. **Run-2 (080552): BOS-myth phase.** Prepended BOS manually; argmax-vs-greedy compared logits *after* `[EMB]` with greedy after section end — conceptually wrong pair, correctly mismatched. Fixed by reading logits at the section-final position. Added `seq_copy` (`kv_cache_seq_cp` 0→1) and a one-shot few-shot ops arm.
5. **Run-3 (080653): crash + vocabulary lesson.** `m._batch.batch.seq_id[:] = 0` — ctypes array takes no slice; removed. `get_embeddings_ith` NULL on the seq-1 read: output index ≠ position index across sequences (one output ⇒ read index 0). Recorded as a runtime rule.
6. **BOS probe (focused, under lock): the tokenizer never emits id 0.** `tokenize(add_bos=True) == tokenize(add_bos=False)`, BOS in neither. Runs 2–3 therefore carried a spurious leading 0. Removed everywhere. Corollary, also verified: `tok(a)+tok(b) != tok(a+b)` (boundary merges, 1 token each here) — manual batches must use single-string ids, which now match `embed()` exactly.
7. **Run-4 (080928): alignment.** `align_no_emb` cos = 1.0 exactly; `argmax_eq_greedy` true; rerun determinism 1.0. New surprise: `seq_copy` cos = 0.9984, not 1.0. `chunking` control (same-seq P-then-S split, no copy) gives 0.9984 vs single and 1.0 vs copy: the deviation is the **split**, not the copy — `llama_memory_seq_cp` itself is bit-exact. Also: few-shot arm emitted 2 shape-valid ops with fabricated `[1,2]` spans that my checker called `proof_ok:true` — caught on review: `validate_ops` returns `{"ok", "verdicts"}`, and I read a nonexistent `"errors"` key (`None` ⇒ vacuous True). All pre-fix `proof_ok` readings discarded; empty `{"ops":[]}` arms re-verified legitimate (empty list truly validates).
8. **Run-5 (081121/081153): clean.** Fixed checker (`res["ok"]` + verdicts inline), re-ran: grammar `3/3`, free `0/3`, few-shot honestly `parse_ok:true, proof_ok:false` with Proof's per-op reasons quoted — Proof doing exactly its job. Added `tokpolicy.rq_live`: RQ id decodes, 2048-dim state readable.

## Results
**Verdict: VALIDATED.** One `llama_decode` over `prefix+section+[EMB]` yields both a 2048-dim embedding and 130560-dim logits (final log `run-20260912T081153Z.jsonl`):

| Claim | Evidence |
|---|---|
| Same call, both outputs | `one_decode`: one decode, `emb_dim=2048`, `logits_dim=130560`, decode 8 ms / 120 tokens |
| Logits == generation path | `argmax_at_section_end == greedy ids prompt` (`416/" The"`, `argmax_eq_greedy:true`) |
| Embedding == embed path | `align_no_emb` cos = 1.0 on identical ids; manual set_batch ≡ add_sequence (focused probe, 1.0) |
| Deterministic | rerun cos = 1.0; `embed-vs-embed` = 1.0 |
| Ops under grammar | `{"ops":[]}` 3/3 parse+Proof-ok under 001's GBNF; free arm 0/3 on identical inputs (rambling / non-JSON) |
| Neighbour independence | same string across generation history cos = 1.0; different sections 0.84/0.35 (content-sensitive, non-vacuous); 001-I1 byte-identical on real ids |
| Reusable KV (`seq_cp`) | copy(P)+section ≡ one-shot to cos 0.9984; `chunking` control proves the copy itself is bit-exact (1.0) and the 4th-decimal loss is the two-call split |
| Token policy recorded | `emb=reserved:130080;rq=reserved:130081`, both detok-empty, both fed live (EMB in every decode, RQ in `tokpolicy.rq_live`) |
| Throughput | load 0.8 s; prefill ~3.7k tok/s (417 tok / 0.11 s); grammar arm ~0.2 s vs free ~1.3 s per section (grammar stops at 3 tokens, free rambles 100+) |
| I4 bounded decode | `max_tokens=2` → `"{ "` → parse fails → Proof rejects, no crash; empty-prefix and 8000-char embeds return 2048-dim vectors |

Surprises and handoffs (not softened):
- **Untrained `[EMB]` space ≠ last-token space**: `cos(marker-state, last-token-state) ≈ 0.07`; pairwise structure partly preserved (01 highest in both: 0.87 vs 0.84) but pairs with section 2 diverge (0.43–0.50 vs 0.14). The marker id is usable and section-sensitive, but it is a *different* representation. Which recalls better is spike 004's measurement, not an assumption — do not treat them as interchangeable.
- **Zero-shot ops are vacuous, one-shot ops fabricate**: zero-shot always `{"ops":[]}` (valid, filable-nothing); one demo yields shape-valid ops with fabricated evidence spans that Proof rejects (`evidence span contains neither subject nor value`). Format is guaranteed; accuracy is entirely spike 003's problem. Do not cite this spike for routing accuracy.
- **Runtime rules for later spikes**: (a) never prepend BOS — this tokenizer emits none; (b) tokenize `prefix+section` as one string (boundary merges); (c) `get_embeddings_ith` indexes the i-th *output*, not position; (d) with `embedding=True`, completion calls print the `overriding` notice — harmless; (e) `validate_ops` returns `ok/verdicts`, and the pre-fix runs in `logs/` carry vacuous `proof_ok` fields — only `run-20260912T081153Z.jsonl` is normative for Proof verdicts.
- `n_ctx=4096, n_batch=512, n_gpu_layers=-1, pooling=NONE(0)`; `doc_prefix="MelodyScribe ingest v0.1. File facts with evidence spans. "` (`score-io-v0.1+prefix-v1`); corpus sections `a_kiss_for_corliss/adam_collis/charles_craft` with char spans in log.
