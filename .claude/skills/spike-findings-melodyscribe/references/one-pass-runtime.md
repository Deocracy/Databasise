# One-Pass Runtime

Runtime blueprint for MelodyScribe: one `llama_decode` over `doc_prefix + section + [EMB]` returns the section embedding and the next-token logits from the same call, isolated sequences keep sections neighbour-independent, and prebuilt KV state removes the prefill slope from query TTFT. Evidence: spike 002 (VALIDATED, owner re-run) and spike 005 (PARTIAL, owner re-run), both on MiniCPM5-2B-Q8_0 on host legion, llama-cpp-python 0.3.35, CUDA.

## Requirements

Copied from `.planning/spikes/MANIFEST.md` (idea `melodyscribe`); only the four that bind the runtime:

- Model size is a rig variable; report the size-versus-accuracy curve before choosing (D-MS-05)
- No vendor benchmark settles anything; every verdict comes from a local measurement on the 20-document parity corpus
- Every measurement run holds the GPU lock so numbers are never taken under contention
- v0.1 defaults adopted overnight for the spec's open decisions, owner review pending: graph nodes filed by normalised name (alias merging is a revise concern); one generic `facts` table for SQL; `folio` ops allowed during bulk ingest under the sandbox rule; `doc_prefix` includes the chat-template system turn; `[EMB]`/`[RQ]` token ids chosen per model by spike 002 and recorded

## How to Build It

### 1. Environment: one shared venv, no NixOS change

`.planning/spikes/setup-env.sh` builds a Python 3.12 venv at `.planning/spikes/.venv` with `uv`, installs `llama-cpp-python` from the prebuilt CUDA wheel index (tries `cu125` first, then `cu124` down to `cu121`), then the pip NVIDIA runtime packages. No PyTorch in this venv.

```bash
# .planning/spikes/setup-env.sh
[ -d .venv ] || uv venv --python 3.12 .venv
for idx in cu125 cu124 cu123 cu122 cu121; do
  if uv pip install --python .venv/bin/python --extra-index-url "https://abetlen.github.io/llama-cpp-python/whl/$idx" "llama-cpp-python" 2>>.logs/setup.log; then echo "installed llama-cpp-python from $idx"; break; fi
done
uv pip install --python .venv/bin/python numpy faiss-cpu httpx jsonschema "nvidia-cuda-runtime-cu12==12.5.*" "nvidia-cublas-cu12==12.5.*" 2>>.logs/setup.log
```

Every process that imports `llama_cpp` must first `source .planning/spikes/env.sh`. It puts the driver `libcuda`, the nix-ld `libstdc++`, and the pip CUDA runtime and cuBLAS on the library path, and exports `$MELODYSCRIBE_PY` and `$MELODYSCRIBE_MODELS`:

```bash
# .planning/spikes/env.sh
_NV="$_SP/.venv/lib/python3.12/site-packages/nvidia"
export LD_LIBRARY_PATH="/run/opengl-driver/lib:/run/current-system/sw/share/nix-ld/lib:$_NV/cuda_runtime/lib:$_NV/cublas/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export MELODYSCRIBE_PY="$_SP/.venv/bin/python"
export MELODYSCRIBE_MODELS="$_SP/.models"
```

Models: `.planning/spikes/fetch-models.py` downloads the GGUF set into `.planning/spikes/.models` (resumable via HTTP Range, checks the `GGUF` magic). Q8_0 everywhere it fits so quantisation stays out of the size comparison: MiniCPM5-1B, MiniCPM5-2B, MiniCPM5-2.6B-DSpark, Qwen3-1.7B, Qwen3-4B, Qwen3-8B, Qwen3-Embedding-0.6B; `--moe` adds Qwen3-30B-A3B at Q4_K_M. The runtime spikes use `MiniCPM5-2B-Q8_0.gguf`.

Run pattern (`.planning/spikes/002-one-pass-runtime/run.sh`, `.planning/spikes/005-kv-composition-quality/run.sh`): vocab-only probes and analysis run without the lock; every model load runs under `flock /tmp/melodyscribe-gpu.lock` as one process that loads the model once and runs every arm. Output is one JSON object per line into `logs/`, llama.cpp stderr into a sibling file.

```bash
# .planning/spikes/002-one-pass-runtime/run.sh
"$MELODYSCRIBE_PY" "$D/tok_probe.py" 2>"$D/logs/stderr-$STAMP.log" | tee -a "$LOG" || exit 1
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$D/one_pass.py" 2>>"$D/logs/stderr-$STAMP.log" | tee -a "$LOG" || exit 1
```

### 2. Load one instance that both generates and embeds

Create the context with `embedding=True`. One `Llama` instance then serves `create_completion` and `embed` from the same weights, process, and GPU (spike 002 `dual_use` check). Pooling type reads back as `0` (NONE), so embedding reads are per-token `ith` reads, not pooled.

```python
# .planning/spikes/002-one-pass-runtime/one_pass.py
m = Llama(model_path=MODEL, n_gpu_layers=-1, n_ctx=4096, n_batch=512,
          embedding=True, verbose=False)
```

Measured (`logs/run-20260912T081153Z.jsonl`, the normative log): load 0.75 s, `n_embd` 2048, `n_vocab` 130560.

`has_embd` is the llama.cpp context flag that makes the same decode produce embeddings alongside logits: `has_logits = true; has_embd = cparams.embeddings;` (`src/llama-context.cpp` lines 2056-2057, cited in `reference/micro-harnesses/runtime-one-pass.md`). `llama_set_causal_attn` and `llama_set_embeddings` exist in the C API (`llama.h` lines 1007 and 1011, cited in `reference/micro-harnesses/runtime-and-training-stack.md`) and would allow a non-causal embedding mode on the same loaded model; neither spike called them. Everything measured below is causal attention, which is what the prompt-layout rule (prefix before section, instruction after) depends on.

### 3. Token policy and tokenisation

`tok_probe.py` (vocab-only load, no GPU) established for MiniCPM5-2B: vocab 130560, BOS=0, EOS=1, NL=220, chat template present (9060 chars). No single-token marker exists in the vocabulary (`⟦EMB⟧` tokenises to 5 ids: `[66719,121,78407,66719,122]`). The tail block `130072..130559` detokenises empty, so two reserved ids were adopted and recorded as the policy string that enters the embedding-space identity:

```python
# .planning/spikes/002-one-pass-runtime/one_pass.py
DOC_PREFIX = ("MelodyScribe ingest v0.1. File facts with evidence spans. ")
DOC_PREFIX_V = "score-io-v0.1+prefix-v1"
EMB_ID = 130080
RQ_ID = 130081
TOKEN_POLICY = f"emb=reserved:{EMB_ID};rq=reserved:{RQ_ID}"
```

Both ids were fed live: `[EMB]` in every one-decode, `[RQ]` in the `tokpolicy.rq_live` check (2048-dim state readable, cosine 0.3715 against the section-0 `[EMB]` state).

Tokenise prefix and section as one string. `tok(a) + tok(b) != tok(a + b)` because of boundary merges: prefix 18 tokens, sections 102/109/152, split sums 120/127/170 versus single-string 119/126/169 (`tokenize` check). Manual batches must use single-string ids or they will not match the `embed()` and `create_completion` paths.

```python
# .planning/spikes/002-one-pass-runtime/one_pass.py
def tok(m: Llama, s: str) -> list[int]:
    return m.tokenize(s.encode("utf-8"), add_bos=False, special=False)

prefix_ids = tok(m, DOC_PREFIX)
full_ids = [tok(m, DOC_PREFIX + s["content"]) for s in sections]
```

### 4. The one decode: embedding and logits from one call

Build one batch over `full_ids + [EMB_ID]` with every position marked as an output (`logits_all=True`), decode once, then read the embedding at the `[EMB]` index and the logits at the last index.

```python
# .planning/spikes/002-one-pass-runtime/one_pass.py
def one_decode(toks: list[int], emb_pos: int):
    m._ctx.kv_cache_clear()
    m._batch.set_batch(batch=toks, n_past=0, logits_all=True)
    t = time.time()
    m._ctx.decode(m._batch)
    ds = time.time() - t
    m._batch.reset()
    ev = np.ctypeslib.as_array(
        m._ctx.get_embeddings_ith(emb_pos),
        shape=(m.n_embd(),)).tolist()
    lg = np.ctypeslib.as_array(
        m._ctx.get_logits_ith(len(toks) - 1),
        shape=(m.n_vocab(),)).tolist()
    return ev, lg, ds

toks = full_ids[0] + [EMB_ID]
evec, logits, dec_s = one_decode(toks, len(toks) - 1)
```

`get_embeddings_ith(i)` and `get_logits_ith(i)` index the i-th output of the batch, not the i-th position. With `logits_all=True` on a single sequence the two coincide; with one output flagged in a later batch the read index is 0 (see step 5).

Measured on the normative log: decode 8.1 ms for 120 tokens; `emb_dim` 2048; `logits_dim` 130560; rerun cosine 1.0 (deterministic). The logits at the section-final position (index `len(toks) - 2`, before `[EMB]`) give argmax id 416 `" The"`, equal to the greedy first token from `create_completion` over the same ids without the marker (`argmax_eq_greedy: true`). The state at the section-final position from the manual batch has cosine 1.0 against `embed()`'s last per-token vector on identical ids (`align_no_emb`). Manual `set_batch` and `add_sequence` produce the same vector (focused probe, 1.0).

The `[EMB]` state is a different representation from the last-token state: cosine 0.0679 between them. Pairwise structure between sections is partly preserved. Do not treat the two as interchangeable; which one retrieves better is spike 004's measurement.

### 5. Isolated sequences: prefix copy, section append, free

Sections must embed as a function of `(doc_prefix, section)` only. The primitive is a KV prefix on sequence 0, `llama_memory_seq_cp` into a fresh sequence, the section appended under that sequence id, then `llama_memory_seq_rm` to free it. Spike 002 exercised this through `Llama._ctx` and a hand-written continuation batch:

```python
# .planning/spikes/002-one-pass-runtime/one_pass.py
P = full_ids[0]
S = [EMB_ID]
m._ctx.kv_cache_clear()
m._batch.set_batch(batch=P, n_past=0, logits_all=True)
m._ctx.decode(m._batch)
m._batch.reset()
m._ctx.kv_cache_seq_cp(0, 1, -1, -1)
b = m._batch.batch
m._batch.reset()
b.n_tokens = len(S)
for i, t in enumerate(S):
    b.token[i] = t
    b.pos[i] = len(P) + i
    b.seq_id[i][0] = 1
    b.n_seq_id[i] = 1
    b.logits[i] = True
m._ctx.decode(m._batch)
m._batch.reset()
ev_cp = np.ctypeslib.as_array(
    m._ctx.get_embeddings_ith(0),
    shape=(m.n_embd(),)).tolist()
m._ctx.kv_cache_seq_rm(1, -1, -1)
```

Measured: `copy(P) + section` versus the one-shot decode has cosine 0.998373 (`seq_copy`). The `chunking` control (same sequence, decode P then S, no copy) gives 0.998373 against one-shot and 1.0 against the copy. So the copy itself is bit-exact; the fourth-decimal loss belongs to splitting one prefill into two decode calls. Isolation holds at the `embed()` level too: the same string embeds to cosine 1.0 regardless of what generated before it, and a different section scores 0.835158 (`isolation`).

`llama_memory_seq_add` (position shift for placing a module at a new offset) is present in 0.3.35 (spike 005 API probe) but was not exercised by either spike. Composing several isolated modules into one query sequence therefore remains a design, not a measured path (see step 7).

### 6. Grammar-constrained op decode after the embedding read

Ops decode under the GBNF that spike 001 generates from `ops.schema.json` for the file-set in use. Spike 002 ran this as a separate `create_completion` on the same instance; same-cache continuation from the one-decode is justified by `argmax_eq_greedy` (the one-decode logits are the generation path's logits) but was not itself the exercised code path.

```python
# .planning/spikes/002-one-pass-runtime/one_pass.py
grammar_text = grammar_for_subset(FILE_SET)
grammar = LlamaGrammar.from_string(grammar_text, verbose=False)
prompt = (DOC_PREFIX + s["content"] + "\n" + ops_instruction(FILE_SET))
g = m.create_completion(prompt, max_tokens=160, temperature=0.0,
                        seed=11, grammar=grammar)
```

Measured, identical inputs per section: grammar arm 3/3 parse and Proof-ok (`{"ops":[]}`), free arm 0/3 (rambling or non-JSON); grammar 0.18 to 0.21 s per section, free 1.31 to 1.34 s. Grammar guarantees shape only: zero-shot output is always the empty list, and a one-shot demo produced shape-valid ops with fabricated evidence spans that Proof rejected. Validate every decode with `validate_ops` and read `res["ok"]` plus `verdicts`; the cap check (`max_tokens=2` gives `"{ "`, parse fails, Proof rejects, no crash) is the I4 bound.

### 7. KV composition for query TTFT: what spike 005 measured

Spike 005 asked whether prebuilt chunk KV saves query latency and whether reuse paths change answers. It rejected a raw-ctypes multi-sequence build (about 200 lines for the verdict) and used the high-level API on `n_ctx=8192`, greedy `top_k=1`, 64 output tokens, 3 reps per cell, 2 HotpotQA queries by 10 retrieved-set variants, with the guard that context tokens are a byte-prefix of the full prompt tokens in every row.

```python
# .planning/spikes/005-kv-composition-quality/kv_arms.py
def greedy_gen(llm: Llama, tokens: list[int], reset: bool):
    """Generate MAX_TOK greedy tokens; return (token_ids, ttft_s, total_s)."""
    t0 = time.perf_counter()
    out: list[int] = []
    ttft = None
    gen = llm.generate(tokens, top_k=1, top_p=1.0, min_p=0.0, temp=0.0,
                       reset=reset)
    for tok in gen:
        if ttft is None:
            ttft = time.perf_counter() - t0
        out.append(int(tok))
        if len(out) >= MAX_TOK:
            break
    gen.close()
    return out, (ttft or 0.0), time.perf_counter() - t0
```

Three arms on identical final token strings per row:

- `full`: `llm.reset()` then `greedy_gen(full_toks, reset=True)`, cold joint prefill.
- `warm`: chunk KV built once with `eval`, saved with `save_state`, and per query `load_state` then question-only prefill. This is the warm state of an isolated module; the KV was built jointly, so it is a warm-reuse proxy, not a neighbour-blind build.
- `shift`: a differently suffixed prompt sharing the prefix populates the KV, then `generate(reset=True)` reuses the longest common prefix through `kv_cache_seq_rm` (llama-server `--cache-reuse` semantics).

```python
# .planning/spikes/005-kv-composition-quality/kv_arms.py
llm.reset()
llm.eval(list(full_toks[:k]))
saved = llm.save_state()
for r in range(REPS):
    llm.load_state(saved)
    ids, ttft, total = greedy_gen(llm, q_toks, reset=False)
```

Measured TTFT (medians of 3, `logs/run.jsonl`, table in `results/summary.md`; seconds in the source table, shown here in ms):

| prompt tokens | full | warm | warm ratio | shift | shift ratio |
|---|---|---|---|---|---|
| 31 (q1 empty) | 15 | 13 | 1.2x | 15 | 1.0x |
| 162 (q1 gold-AB) | 31 | 13 | 2.4x | 29 | 1.1x |
| 217 (q2 gold-AB) | 36 | 14 | 2.6x | 32 | 1.1x |
| 339 (q1 gold+distr) | 55 | 13 | 4.2x | 51 | 1.1x |
| 394 (q2 gold+distr) | 71 | 14 | 4.9x | 57 | 1.2x |
| 637 (q1 long) | 115 | 14 | 8.5x | 126 | 0.9x |
| 692 (q2 long) | 125 | 15 | 8.3x | 134 | 0.9x |

Length sweep (full, then warm): 650 tokens 119 ms / 13.5 ms; 1192 tokens 229 ms / 13.8 ms; 2093 tokens 449 ms / 14.5 ms. Least-squares fit: full 0.23 ms per prefill token, warm 0.0007 ms per token plus a 13 ms question-prefill-and-first-decode floor (`results/summary.md`: 0.2279 and 0.0006 ms/tok, warm intercept 0.0131 s). Absolute saving at rig scale: 20 to 110 ms. Shift reuse: 0.9x to 1.2x, no practical win, because only the shared prefix is skipped and the retrieved set dominates.

Answer equality: 14/20 rows are text-identical across all arms. The 6 differing rows flip single near-tie greedy tokens late in generation (first divergence at char 53 to 332 of about 300), in both directions, with correctness unchanged or flipped either way. Order swap (gold-AB versus gold-BA) never changes correctness on either query. The partition probe (same tokens, `eval` split at 3 different points versus one-shot) was identical in every case, so batch partitioning is not the cause; the state round-trip is.

### 8. State save and load

Spike 005 used the in-memory pair `save_state` / `load_state`. The design's cross-process path is `llama_state_seq_save_file` / `llama_state_seq_load_file` (`llama.h` lines 890 and 898, cited in `reference/micro-harnesses/score-format-and-cache.md`); its cost was not measured and warm TTFT above excludes it. State size is about 30 MB at 700 tokens. Both `save_state`/`load_state` and `seq_rm` prefix reuse are deterministic per input (3/3 reps identical, `stability` and `statepath` events clean) but are not bit-exact continuations of a cold prefill: they flip near-tie greedy tokens on about 25 percent of inputs. Any persisted-state path must budget this noise; grammar-constrained op decode is less exposed than free text.

## What to Avoid

- Do not prepend BOS for MiniCPM5. The tokenizer emits no id 0 under either `add_bos` setting (`tok.bos` check); runs 2 and 3 of spike 002 carried a spurious leading 0 and produced wrong comparisons.
- Do not tokenise prefix and section separately and concatenate. Boundary merges change the id list (one token off in every section measured). Tokenise `doc_prefix + section` as one string.
- Do not treat `get_embeddings_ith` or `get_logits_ith` as position-indexed. They index the i-th output of the batch; a continuation batch with one output flag reads at index 0. Reading at the position returned NULL in run 3.
- Do not compare logits after `[EMB]` with the greedy path after the section. The pair is conceptually wrong; compare at the section-final position.
- Do not use `--embeddings` mode on llama-server for a generative model. It is embedding-only (`.planning/spikes/CONVENTIONS.md`).
- Do not embed empty sections. Reject them before the decode; enforce context limits chunker-side, because both llama.cpp paths truncate silently past `n_ctx`.
- Do not load two models in one process. One model per process, and every load under `flock /tmp/melodyscribe-gpu.lock`.
- Do not report throughput or TTFT from a run that did not hold the GPU lock.
- Do not expect saved and reloaded KV state, or `seq_rm` prefix reuse, to be bit-exact. They are deterministic per input and flip near-tie tokens on about a quarter of inputs.
- Do not build a persisted KV module store for the corpus at 2B scale. The saving is 20 to 110 ms per query against about 43 KB of KV per token; `reference/micro-harnesses/efficiency-design.md` section 3 calls this second-order and spike 005 confirmed it. Keep runtime prefix reuse.
- Do not count shift reuse as a win. Measured 0.9x to 1.2x.
- Do not read `"errors"` from `validate_ops`. It returns `{"ok", "verdicts"}`; a missing key made `proof_ok` vacuously true in the pre-fix runs. Only `logs/run-20260912T081153Z.jsonl` is normative for spike 002 Proof verdicts.
- Do not cite spike 002 for routing accuracy. Zero-shot ops are vacuous and one-shot ops fabricate spans; accuracy is spike 003's result.
- Do not slice the ctypes `seq_id` array (`b.seq_id[:] = 0` crashed run 3); write per element.

## Constraints

- Host: legion, NixOS, RTX 3080 Laptop 16 GB VRAM, NVIDIA driver 595. No NixOS change: nix-ld plus the driver's `libcuda` cover the wheel.
- Stack: Python 3.12 venv at `.planning/spikes/.venv`; `llama-cpp-python` 0.3.35 from the `cu125` wheel index; `nvidia-cuda-runtime-cu12` 12.5.82; `nvidia-cublas-cu12` 12.5.3.2; `numpy`, `faiss-cpu`, `httpx`, `jsonschema`. No PyTorch.
- Model: `MiniCPM5-2B-Q8_0.gguf`, vocab 130560, BOS 0, EOS 1, NL 220, `n_embd` 2048, `n_gpu_layers=-1`.
- Context sizes used: spike 002 `n_ctx=4096`, `n_batch=512`, `pooling_type=0` (NONE); spike 005 `n_ctx=8192`, 64 output tokens, `top_k=1`.
- Token policy string, MiniCPM5-2B only: `emb=reserved:130080;rq=reserved:130081` (reserved tail block `130072..130559`, detokenises empty). Other models need their own probe and their own recorded string; the string is part of the embedding-space identity.
- `doc_prefix` v0.1: `"MelodyScribe ingest v0.1. File facts with evidence spans. "`, version tag `score-io-v0.1+prefix-v1`, 18 tokens. Chat-template application to the prefix is later work.
- Throughput (spike 002, under lock): load 0.75 s; prefill 3663 tokens/s (417 tokens in 0.114 s); one decode of 120 tokens 8.1 ms; grammar op decode about 0.2 s per section, free decode about 1.3 s; whole spike 8.5 s wall.
- Query TTFT (spike 005, under lock): full 15 to 126 ms at 31 to 692 prompt tokens, slope 0.23 ms per token; warm 13 to 15 ms flat; absolute saving 20 to 110 ms; ratios 2.4x at 162 tokens to 8.5x at about 650; sweep to 2093 tokens gives 449 ms full versus 14.5 ms warm. Warm excludes state load from disk (about 30 MB at 700 tokens).
- Quality: arms equal up to greedy tie-flips, 14/20 rows identical, 6 rows diverge late in both directions; no arm systematically better. Order swap never changes correctness.
- Embedding cosines: rerun 1.0; one-decode versus `embed()` on identical ids 1.0; `seq_cp` bit-exact (1.0 against the split control); two-call split 0.998373; `[EMB]` state versus last-token state 0.0679.
- Grammar head-to-head: 3/3 Proof-ok under grammar versus 0/3 free, identical inputs.
- Spike 005 verdict is PARTIAL: TTFT per method is solid; quality is bounded by one discriminating query (q1 is answerable from parametric memory) and a warm-reuse proxy rather than a true neighbour-blind module build.

## Origin

Synthesized from spikes: 002, 005

Source files available in: sources/002-one-pass-runtime/, sources/005-kv-composition-quality/, sources/env.sh, sources/setup-env.sh, sources/fetch-models.py

Normative logs: `.planning/spikes/002-one-pass-runtime/logs/run-20260912T081153Z.jsonl`; `.planning/spikes/005-kv-composition-quality/logs/run.jsonl` with `results/summary.md` and `results/table.json`. Design notes the spikes tested: `reference/micro-harnesses/runtime-one-pass.md`, `reference/micro-harnesses/score-format-and-cache.md`, `reference/micro-harnesses/efficiency-design.md`; cross-spike summary in `reference/micro-harnesses/spike-results.md`; shared rules in `.planning/spikes/CONVENTIONS.md`.
