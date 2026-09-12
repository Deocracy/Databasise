# Serving and Pipeline Order

Serving and pipeline blueprint for MelodyScribe: a K-slot wave scheduler over llama.cpp multi-sequence batches, the measured throughput curves for ingest and retrieval on one RTX 3080 Laptop 16 GB, the prompt and arrival ordering that maximises KV prefix reuse, and the assembled pipeline order with its parallel-worker rules. Evidence: spike 009 (VALIDATED, owner reproduction in progress) and spike 010 (PARTIAL, owner re-run equal on every retrieval and store number), both on MiniCPM5-2B-Q8_0 and Qwen3-Embedding-0.6B-Q8_0, llama-cpp-python 0.3.35, host legion. Runtime primitives (one decode, `seq_cp`, samplers, token policy) are in `.claude/skills/spike-findings-melodyscribe/references/one-pass-runtime.md`; this file does not repeat them.

## Requirements

Copied from `.planning/spikes/MANIFEST.md` (idea `melodyscribe`); only the three that bind serving and pipeline:

- Every measurement run holds the GPU lock so numbers are never taken under contention
- No vendor benchmark settles anything; every verdict comes from a local measurement on the 20-document parity corpus
- Model-written skills (Folios) run sandboxed and are read only by MelodyScribe; the frontier reads one human-authored skill (D-MS-01, D-MS-02)

## How to Build It

### (a) Serving: wave scheduler over llama.cpp multi-sequence batches (spike 009)

**Why true continuous batching is not expressible here.** In llama-cpp-python 0.3.35, `eval()` and `generate()` call `kv_cache_seq_rm(-1, ...)`, which wipes every sequence, so a K-slot scheduler must hand-roll raw `llama_batch` rows and sample through a persistent sampler (a fresh sampler per token restarts grammar state). The sampler API sees one output at a time, so per-slot grammars inside a lockstep multi-sequence decode cannot be expressed. Spike 009 therefore built two schedulers on one instance: SERIAL-GRAMMAR (batched prefill of a wave, then serial grammar decode per slot; the true op path) and PARALLEL-GREEDY (batched prefill, then lockstep greedy decode with full-buffer argmax; the batching ceiling, validity measured offline). Source: `.planning/spikes/009-batched-serving-and-cache-order/batchserve.py`, loops in `sweep.py`.

**Three build constraints found by bisect** (README Investigation Trail, `logs/dbg*.out`):

- A: never decode a token at an already-filled position; `llama_decode` returns -1. The bulk prefill covers prompt bodies only; each prompt's last token goes out in its own single-row call at its first-time position.
- B: with `embedding=True` (required for `n_seq_max > 1`) only the last decode output carries real logits; non-last outputs read embedding memory. Flip the C-side flag with `llama_set_embeddings(ctx, False)` after load. This keeps `n_seq_max > 1` and restores logits for every output. Never call `embed()` on the flipped instance; retrieval uses a separate 0.6B load.
- C: per-output readback (`get_logits_ith`, `sampler.sample(idx)`) is NULL on multi-output decodes (`GGML_ASSERT(logits != nullptr)`). The full `get_logits()` buffer (M x vocab, argmax per row) is the only safe multi-output read. Samplers only ever see single-output calls.

Load: `Llama(model_path=MiniCPM5-2B-Q8_0.gguf, n_gpu_layers=-1, n_ctx=16384, n_batch=2048, embedding=True)` then `set_generative`. `n_ctx=4096` failed at N=16/K=16 (`decode: failed to find a memory slot`, 16 sequences x about 380 positions); 16384 raised VRAM from 2.9 to 3.9 GB.

```python
# .planning/spikes/009-batched-serving-and-cache-order/batchserve.py
def set_generative(llm) -> None:
    import llama_cpp
    llama_cpp.llama_set_embeddings(llm._ctx.ctx, False)

def raw_decode_rows(llm, rows: list[tuple[int, int, int, bool]]) -> float:
    """Decode rows (seq, pos, tok, want_logit) chunked to n_batch."""
    cap = int(llm.n_batch)
    t = 0.0
    b = llm._batch.batch
    for c in range(0, len(rows), cap):
        chunk = rows[c:c + cap]
        llm._batch.reset()
        b.n_tokens = len(chunk)
        for i, (s, p, tok, lg) in enumerate(chunk):
            b.token[i] = tok
            b.pos[i] = p
            b.seq_id[i][0] = s
            b.n_seq_id[i] = 1
            b.logits[i] = lg
        t0 = time.perf_counter()
        llm._ctx.decode(llm._batch)  # raises on nonzero return
        t += time.perf_counter() - t0
        llm._batch.reset()
    return t

def wave_prefill(llm, prompts, first_seq=1):
    """Batched prefill of prompt BODIES (all but each prompt's last token)."""
    body = []
    for j, toks in enumerate(prompts):
        s = first_seq + j
        for i, tok in enumerate(toks[:-1]):
            body.append((s, i, tok, False))
    return raw_decode_rows(llm, body), [len(p) for p in prompts]

def slot_first(llm, slot, L, tok_last, sampler):
    """Last prompt token in a single-row call at its natural position, then one sample."""
    t0 = time.perf_counter()
    raw_decode_rows(llm, [(slot, L - 1, tok_last, True)])
    llm.n_tokens = L
    return int(sampler.sample(llm._ctx, -1)), time.perf_counter() - t0

def slot_decode_grammar(llm, slot, L, tok_last, grammar_text, cap, eos=1):
    """Serial grammar decode of one slot on its OWN sequence (no seq copy)."""
    sampler = fresh_grammar_sampler(llm, grammar_text)   # top_k=1, temp=0, GBNF
    first, ttft = slot_first(llm, slot, L, tok_last, sampler)
    out = [first]
    pos = L
    t1 = time.perf_counter()
    while len(out) < cap and out[-1] != eos:
        raw_decode_rows(llm, [(slot, pos, out[-1], True)])
        pos += 1
        llm.n_tokens = pos
        out.append(int(sampler.sample(llm._ctx, -1)))
    llm._sampler = None
    return llm.detokenize(out).decode("utf-8", errors="replace"), out, ttft, time.perf_counter() - t1

def read_all_argmax(llm, m: int) -> list[int]:
    """Argmax per row of the last decode's full logits buffer. The ONLY safe multi-output read."""
    buf = np.ctypeslib.as_array(llm._ctx.get_logits(), shape=(m * llm.n_vocab(),))
    return [int(np.argmax(buf[r * llm.n_vocab():(r + 1) * llm.n_vocab()])) for r in range(m)]

def wave_decode_parallel_greedy(llm, slots, lens, toks_last, cap, eos=1):
    """Lockstep batched greedy decode: one decode call per step advances every live slot."""
    sampler = fresh_greedy_sampler(llm)
    first_ids = [slot_first(llm, s, L, tl, sampler)[0] for s, L, tl in zip(slots, lens, toks_last)]
    llm._sampler = None
    live = [f != eos for f in first_ids]
    outs = [[f] for f in first_ids]
    cur, pos = list(first_ids), list(lens)
    while any(live) and max(len(o) for o in outs) < cap:
        order = [j for j, l in enumerate(live) if l]
        raw_decode_rows(llm, [(slots[j], pos[j], cur[j], True) for j in order])
        for r, j in enumerate(order):
            tok = read_all_argmax(llm, len(order))[r]
            outs[j].append(tok); cur[j] = tok; pos[j] += 1
            if tok == eos:
                live[j] = False
    return outs
```

The wave loop (`sweep.py`, `run_cell_A`): for each wave of K requests, `kv_cache_clear()`, `wave_prefill(wave)`, then `slot_decode_grammar(slot j+1, L, last token, GRAMMAR, cap)` per slot. `run_cell_B` replaces the per-slot loop with one `wave_decode_parallel_greedy` call. Each decode step carries the I4 cap (48 in the sweep). One unplaced id per request is counted in `gen_tok` (about 2 percent of generated tokens, under 0.5 percent of tok/s).

Verify before any sweep (`verify.py`, `logs/verify.jsonl`): the scheduler's first token equals `create_completion` top-1 in 4/4 slots on both schedulers (logprob about -0.02 versus runner-up about -5); grammar full text 3/4 equal, the residual being split-prefill near-tie flips as in spike 005. `generate()` disagreed 0/4 and is the outlier, not the scheduler; `create_completion` is the production path.

**Ingest throughput, MiniCPM5-2B Q8, v0.2 grammar, cap 48** (`logs/sweep.jsonl`; full 30-cell table in `.planning/spikes/009-batched-serving-and-cache-order/README.md`; one run per cell, TTFT includes FIFO queue wait):

| sched | N | K | wall s | tok/s | req/s | TTFT p50 | TTFT p95 | VRAM MB |
|---|---|---|---|---|---|---|---|---|
| serial-grammar | 1 | 1 | 1.19 | 312 | 0.84 | 1.17 s | 1.17 s | 3739 |
| serial-grammar | 64 | 1 | 88.31 | 271 | 0.73 | 48.5 s | 84.4 s | 3795 |
| serial-grammar | 64 | 8 | 82.20 | 291 | 0.78 | 43.2 s | 78.4 s | 3795 |
| serial-grammar | 64 | 32 | 102.21 | 234 | 0.63 | 57.5 s | 97.7 s | 3883 |
| serial-grammar | 1024 | 1 | 1384.41 | 275 | 0.74 | 669 s | 1307 s | 3883 |
| parallel-greedy | 16 | 1 | 7.48 | 781 | 2.14 | 4.20 s | 7.46 s | 3883 |
| parallel-greedy | 16 | 4 | 2.94 | 1991 | 5.45 | 2.20 s | 2.92 s | 3883 |
| parallel-greedy | 16 | 8 | 2.51 | 2330 | 6.38 | 2.49 s | 2.49 s | 3883 |
| parallel-greedy | 16 | 16 | 2.36 | 2474 | 6.77 | 2.34 s | 2.34 s | 3885 |
| parallel-greedy | 64 | 32 | 13.28 | 1804 | 4.82 | 13.26 s | 13.26 s | 3887 |
| parallel-greedy | 1024 | 1 | 477.32 | 799 | 2.15 | 239 s | 454 s | 3887 |
| parallel-greedy | 1024 | 16 | 153.76 | 2479 | 6.66 | 79.2 s | 146.6 s | 3887 |

Read-off. Serial-grammar is flat in K (266 to 321 tok/s; decode is serial, K only batches the roughly 5 percent prefill share), so the recommended K for grammar ops is whatever fits, nominally 8 (291 tok/s at N=64, the `ksat` event). Parallel-greedy saturates at K=16 (about 2470 tok/s, about 6.6 req/s, stable from N=16 to N=1024) and regresses at K=32 (1804 tok/s). The 9x gap (275 versus 2479 tok/s) is CPU-side grammar filtering per token over the 130k vocabulary, not GPU work. Sizing probe (`logs/probe.jsonl`, 330-token prompt): grammar decode of 48 tokens 1.11 to 1.30 s, greedy prefill plus 48 tokens 0.39 to 0.40 s, so decode dominates ingest and prefill batching alone cannot move req/s.

Validity at cap 256, 12 units (`sweep.jsonl` `validity` event): grammar 4/12 pass Proof (0.333), greedy 0/12. Valid-op throughput today is 0.74 req/s x 0.33, about 0.24 valid op-lists/s, about 15 per minute. The greedy arm is a bound, not a path.

**Retrieval throughput, Qwen3-Embedding-0.6B Q8 plus Faiss top-10** (`logs/retrieve.jsonl`; `n_ctx=2048`, `n_batch=2048`, batched through the public `embed(list)`; batched versus single cosine 0.9991/0.9995; Faiss top-10 about 0.03 ms per query; recall@10 sanity 109/116 on the 19-vector index):

| N | K=1 q/s | K=4 q/s | K=16 q/s | K=64 q/s | TTFT p50 K=1 to K=16 |
|---|---|---|---|---|---|
| 4 | 136 | 334 | | | 8.0 ms to 2.9 ms |
| 16 | 141 | 389 | 773 | | 6.9 ms to 1.3 ms |
| 64 | 142 | 380 | 748 | 809 | 7.0 ms to 1.3 ms |
| 256 | 140 | 394 | 781 | 782 | 7.0 ms to 1.2 ms |
| 1024 | 143 | 389 | 766 | 790 | 6.9 ms to 1.3 ms |

Retrieval saturates at K 16 to 64 (770 to 810 q/s, TTFT about 1.3 ms); VRAM flat at 1371 MB. Saturation is host-call batching (one `embed()` per K queries), not GPU size.

**Cache order** (`logs/cacheorder.jsonl`, `cacheorder.py`, 3 reps, K=8):

- Token fractions: the shared prefix (system turn plus skill plus `doc_prefix`) is 105 tokens, 23.8 percent of a section-tail prompt with the instruction after the section. Putting the instruction before the section extends the cross-request shared run to 319 tokens, 48.8 percent. Instruction-first is the order that maximises cache hits (spike 008 measured the accuracy side: instruction-after helps the 4B and hurts the 2B, so the serving win and the accuracy verdict agree for the 2B).
- Prefix-once versus naive prefill: naive 0.73 to 0.81 s per wave, prefix-once 0.616 to 0.622 s (setup 0.0076 s plus tails 0.61 s), 15 to 24 percent off prefill; first tokens 8/8 equal in every rep. The prefix tokenises 104/105 identically in context (one junction merge, no behavioural effect).
- Prefix-grouped arrival (sorted, one prefix-once wave per group of 4 shard prefixes) versus shuffled naive: 0.60 to 0.71 s versus 0.77 s per 8 requests, about 21 percent.
- Continuation from decoded KV versus cold full prefill of prompt plus ops plus recall prompt: 14.6 ms versus 80.4 ms (5.5x, 66 ms absolute; second-order at 2B, consistent with spike 005's 20 to 110 ms verdict; no persisted-KV store justified).
- Output order (graph-first versus interleaved op text, cold continuation): 0.090 to 0.092 s versus 0.098 s. No practical effect; order freely.

```python
# .planning/spikes/009-batched-serving-and-cache-order/batchserve.py
def wave_prefill_prefix_once(llm, prefix, tails, first_seq=1):
    """Prefill the shared prefix once on seq 0, copy to K slots, then batched tail BODIES."""
    t0 = time.perf_counter()
    llm._ctx.kv_cache_seq_rm(0, -1, -1)
    raw_decode_rows(llm, [(0, i, tok, False) for i, tok in enumerate(prefix)])
    for j in range(len(tails)):
        llm._ctx.kv_cache_seq_cp(0, first_seq + j, -1, -1)
    llm._ctx.kv_cache_seq_rm(0, -1, -1)
    t_setup = time.perf_counter() - t0
    body = []
    for j, tail in enumerate(tails):
        for i, tok in enumerate(tail[:-1]):
            body.append((first_seq + j, len(prefix) + i, tok, False))
    return t_setup, raw_decode_rows(llm, body)

# .planning/spikes/009-batched-serving-and-cache-order/cacheorder.py (sorted arm)
for g in groups:                    # one prefix-once wave per shared-prefix group
    llm._ctx.kv_cache_clear()       # free the previous group's slot KV, else positions collide
    wave_prefill_prefix_once(llm, g[0][0], [g[0][1], g[1][1]])
```

Two crash fixes carried into that code: `kv_cache_clear()` between groups (stale slot KV collided positions, `llama_decode` -1), and the continuation base position is `L + len(ops) - 1` because `slot_decode_grammar` samples the last id logits-only and never places it; a one-position gap is refused by this build (`logs/dbg9.out`).

**Concurrency versus queue depth, stated plainly.** The 16 GB card is never the binding constraint at these sizes (ingest VRAM 3.7 to 3.9 GB at `n_ctx=16384`, retrieval 1.4 GB). True concurrency is K: 16 decode slots saturate ingest (about 6.6 greedy req/s, 0.78 grammar req/s) and 16 to 64 embed slots saturate retrieval (about 800 q/s). Everything beyond K is queue. "1000 agents" is a queue of 1000 over K=16 slots at about 44 sections per minute ingest (0.74 req/s x 60, one section per request; about 9 documents per minute at about 5 sections per document) and about 800 queries per second retrieval. TTFT at N much greater than K is queue wait, not service; service TTFT is about 1.2 s for a grammar op list, about 15 ms for a recall continuation, about 1.3 ms for a batched embed.

**Failed serving paths, recorded** (`logs/vllm.json`, `logs/vllm-run.err`):

- vLLM 0.29.0 in `.venv-vllm` installs and imports; the engine dies at init because triton hardcodes `/sbin/ldconfig`, absent on NixOS; `enforce_eager=True` does not avoid it. Spike 006 later bypassed the same call with `export TRITON_LIBCUDA_PATH=/run/opengl-driver/lib` (`.planning/spikes/006-hybrid-embedder/run.sh`), so that export is the fix to try before re-attempting the vLLM path. Needs `HF_HUB_OFFLINE=1 HF_OFFLINE=1`.
- Prebuilt `llama-server`: no binary on PATH; `llama_cpp.server` is single-slot Python. Skipped with reason.

### (b) Pipeline: assembled order and worker rules (spike 010)

Assembled order, run end to end on 20/20 documents (`.planning/spikes/010-pipeline-order-end-to-end/run.sh`): chunker (one unit per document) → Score with v0.1 defaults, compiled through spike 001's compiler (`s10_common.py`) → one pass on MiniCPM5-2B Q8 in one loaded process: `embed(content + "⟦EMB⟧")` with pooling LAST, then `create_completion` under the v0.2 grammar with spike 003's D0 instruction, greedy, seed 1234, cap 1024, `n_ctx=4096` → Proof (001 validator plus 003 quote resolver) → stores: graph as stdlib dicts keyed by normalised name with evidence edges, SQL as one sqlite `facts` table (subject, attribute, value, value_type, quote, doc), vectors in Faiss (two indexes: 2B `⟦EMB⟧` state and Qwen3-Embedding-0.6B, `n_ctx=2048`) → retrieval payload per `SCORE-IO-SPEC.md` recall-time I/O (recall-list JSON plus fenced top-3 blocks at 200 chars). Production targets Cozo, SQLite, and Faiss through Databasise; the spike did not build them.

Retrieval modes, 118 queries (116 `queries-v1` plus 2 HotpotQA), `results/retrieval.json`:

| mode | r@1 | r@3 | r@10 | MRR | latency median |
|---|---|---|---|---|---|
| vec06 whole | 0.6949 | 0.8856 | 0.9915 | 0.8014 | Faiss microseconds |
| vec2b whole | 0.1780 | 0.3517 | 0.6610 | 0.3226 | Faiss microseconds |
| vec06 split | 0.4619 | 0.6653 | 0.8814 | 0.6007 | Faiss microseconds |
| graph STU/SPL/TEA | 0.186/0.225/0.242 | 0.284/0.309/0.326 | 0.555/0.568/0.589 | 0.309/0.337/0.356 | 0.016 to 0.031 ms |
| sql STU/SPL/TEA | 0.102/0.140/0.153 | 0.220/0.254/0.246 | 0.517/0.551/0.555 | 0.240/0.273/0.279 | 0.016 to 0.034 ms |
| fused (any store set) | 0.6949 | 0.8686 | 0.9915 | about 0.798 | 0.005 ms |

Seven recommendations (`results/pipeline-order.md`), each with its number:

1. One loaded model process serves embed and ops. Two-pass (embed load, then decode load) gives identical vectors (cosine 1.000), identical ops (20/20), identical Proof (70 pass / 28 fail), same 161.4 s wall; the only delta is one extra load (0.85 s versus 1.67 s). Never pay a load per stage.
2. File ops streamed, per op as Proof passes it. Streamed and batched checksums are equal in all 6 variant pairs (STU-write `1bd50cb5b81e0958` both); write cost about 0.1 ms total, five orders below one op decode.
3. Merge entities at write time by normalised name. Revise found at most 1 alias pair on 20 documents (STU 17 nodes, SPL 22, TEA 34) and changed no retrieval number to 4 decimals. Keep revise as a periodic job.
4. Chunk whole documents. Title/body split drops vec06 r@3 from 0.8856 to 0.6653 (r@1 0.6949 to 0.4619, MRR 0.8014 to 0.6007); its extra ops (110 pass versus 70) move graph r@3 only 0.284 to 0.309 and sql 0.220 to 0.254.
5. W=1 worker per model process. Docs/min on the 6-document subset: W=1 5.67, W=2 5.33, W=4 5.28, W=8 5.06 (about 12 percent overhead at W=8); outputs identical at every W (17 graph / 3 sql / 2 duplicate keys). The stub control (60 pseudo-units, 0.05 s decode) ran 3.017/3.016/3.019/3.023 s, so harness and lock overhead is nil and the GPU is the whole bottleneck. Scale by processes and GPUs, not threads.
6. Do not fuse with flat bonuses; ship vector-first with graph and SQL as backoff. Rule tested: `score = 1/(vec_rank+1) + 0.15*graph_hit + 0.15*sql_hit` over `vec top-10 ∪ graph ∪ sql`. Fused r@3 0.8686 < vec06 0.8856, identically under STU, SPL, and TEA stores. Mechanism: a vec-#4 document (0.25 + 0.15 = 0.40) leapfrogs an unbonused vec-#3 (0.333); flips `janet_waldo#5` and `lord_high_treasurer#6`, both spurious subject-mention hits. Vec top-10 holds the gold on 117/118, so fusion headroom is 1 rescue against a measured downside of 2.
7. Keep the 0.6B embedder as the durable index. vec2b r@3 0.3517 versus vec06 0.8856 on 118 queries replicates spike 004's gap at 59x the query count.

Parallel-worker interaction rules, stated as build requirements (`results/pipeline-order.md`, `gpu_workers.py`):

- One model per process; workers are asyncio tasks sharing the process through one model lock; workers never load a model.
- One write lock per store (graph, sql, vector). Op keys are idempotent, `(norm subject, norm predicate, norm value)`, so retries and duplicate deliveries collapse; measured identical stores at W=1 to 8, zero write conflicts.
- Proof rejects never block the section embedding; duplicate and conflict counts are reported per run.
- Store checksums per run; streamed and batched must hash equal. This is the regression gate for the filing path.

```python
# .planning/spikes/010-pipeline-order-end-to-end/gpu_workers.py
model_lock = asyncio.Lock()
store_locks = {"graph": asyncio.Lock(), "sql": asyncio.Lock(), "vector": asyncio.Lock()}

async def one(doc_id, content):
    async with model_lock:
        vec, text, emb_s, dec_s = await asyncio.to_thread(blocking_infer, doc_id, content)
    proof = C.prove_section(text, content)
    async with store_locks["graph"]:
        for op in proof["passed"]:
            if op["target"] == "graph":
                key = (C.norm(op.get("s", op.get("subject", ""))),
                       C.norm(op.get("p", op.get("attribute", ""))),
                       C.norm(op.get("o", op.get("value", ""))))
                async with seen_lock:
                    if key in store["seen"]:
                        store["dup_nodes"] += 1
                    else:
                        store["seen"].add(key)
                store["graph"].append(op)
    async with store_locks["sql"]:
        store["sql"].extend(op for op in proof["passed"] if op["target"] == "sql")

sem = asyncio.Semaphore(w)   # W workers = W concurrent tasks over the one model lock
```

Payload: 118.9 to 119.7 words per query mean, 203 to 205 MiniCPM tokens at the measured fertility of 1.71 tokens per word (6736 prompt tokens / 3930 words on spike 003's exact D0 prompt bytes). Retrieval latency median 0.005 to 0.034 ms per mode on CPU. HotpotQA: q1 both gold documents at vec ranks 1 and 3; q2 at ranks 1 and 6.

### (c) Research guidance the spikes did not test

From `reference/micro-harnesses/deep-research-2/REPORT.md` section 1 (Q5, Q6) and section 5C. Each is a design input with no local number; treat as the next experiments, not as settled.

- Serving substrate: continuous batching plus paged KV blocks (Orca; PagedAttention 2309.06180), or a radix-tree KV layer when the shared unit is a forked program (SGLang RadixAttention 2312.07104). On this rig the llama.cpp wave scheduler is the floor; vLLM is untested until the triton fix above is tried.
- Prompt layout: skill plus schema plus section-type instruction byte-first in every prompt so one hash chain covers all workers (vLLM automatic prefix caching); salt the prefix namespace per tenant in multi-tenant setups. Spike 009's instruction-first result (48.8 percent shared) is the local confirmation.
- Scheduling: group section jobs by shared prefix with decode-ratio-first reordering for offline batches (BatchLLM 2412.03594; Preble 2407.00023); memory-centric token batching; chunked prefills so long sections never stall decodes (SARATHI 2308.16369; Sarathi-Serve 2403.02310); CacheBlend selective recompute for non-prefix reuse when order varies (2405.16444). Spike 009 measured prefix grouping (21 percent) but not decode-first reordering or chunked prefill.
- Speculative decoding (Medusa 2401.10774; EAGLE-2 2406.16858): default off until acceptance rate under grammar-constrained decoding is measured; the intersection is unstudied.
- Pipeline order (HippoRAG 2 2502.14802): extract offline, embed everything (chunks and triples), dense-seed, graph-walk, then LLM-filter. Never run an LLM reasoning loop per query on the serving path (IRCoT 2212.10509 is the cost baseline HippoRAG beats 10 to 30x).
- Incremental updates are union-merge, never rebuild (LightRAG 2410.05779); idempotency by content-hash chunk keys (nano-graphrag), which extends spike 010's op-key rule to the chunk level.
- Entity resolution is clustering after extraction, not during (KGGen 2502.09956), with definition-then-LLM-verify as the precision guard (EDC 2404.03868); communities are Leiden, not Louvain (1810.08473).
- Streaming graphs are episode-first with invalidate-not-delete bi-temporal edges (Zep/Graphiti 2501.13956).
- Retrieval payloads place the strongest evidence last (PathRAG 2502.14902). Spike 010's payload puts the top-3 blocks in rank order; reversing it is untested.
- Rank-gated or score-calibrated fusion (bonus only inside the vector top-k, or a trained ranker) is the open experiment that replaces the failed flat-bonus rule. HNSW by default with an IVF fallback, a sparse arm, Matryoshka truncation, and a distilled 0.3 to 1B reranker are the report's retrieval defaults; the corpus here (19 to 20 vectors) is too small to measure any of them.
- Report gap: no primary source reports documents per hour with hardware for any extraction pipeline, nor 0.3 to 2B concurrency on a 16 GB card. Spikes 009 and 010 are primary evidence, not replication.

## What to Avoid

- Do not read the parallel-greedy ceiling as an op path. It produced 0/12 Proof-valid op lists at cap 256; its 2470 tok/s bounds what batching can buy, nothing more.
- Do not run K=32. Parallel-greedy regresses from 2469 to 1804 tok/s (N=64), serial-grammar from 291 to 234 tok/s; batch-management overhead wins.
- Do not use threads or async workers as a scaling axis. W greater than 1 over one model process adds overhead only (5.67 to 5.06 docs/min from W=1 to W=8, identical outputs). Scale by processes and GPUs.
- Do not fuse retrieval with flat bonuses. The +0.15 rule lost 2 queries on 118 against vector-only and gained none, under every store set.
- Do not split one-paragraph documents into title and body sections. vec06 recall@3 drops from 0.886 to 0.665.
- Do not quote datacenter-GPU serving multiples as targets. Every published multiple in the research report was measured on 7B-plus models on datacenter cards; none reports 0.3 to 2B on 16 GB.
- Do not take timings from contended runs. Spikes 006, 008, and 010 shared the rig and a reboot happened mid-spike; every number here comes from a run holding `flock /tmp/melodyscribe-gpu.lock`, with queue waits reported separately from service times.
- Do not run a reasoning loop per query on the serving path (report Q6). Retrieval service time here is about 1.3 ms embed plus microseconds of Faiss; a per-query LLM loop is a different cost class.
- Do not use `eval()` or `generate()` inside a multi-slot scheduler; both wipe all sequences. Do not decode at a filled position, do not read `get_logits_ith` after a multi-output decode, and do not call `embed()` on an instance flipped with `llama_set_embeddings(ctx, False)`.
- Do not pay a model load per pipeline stage. One-pass and two-pass are output-identical; the reload is the only cost.
- Do not build a persisted KV store for recall continuations at 2B. The reuse saving is 66 ms absolute (14.6 versus 80.4 ms).
- Do not use the two-pass fertility placeholder (1.32) for payload token counts; the measured MiniCPM fertility on D0 prompt bytes is 1.71 tokens per word.

## Constraints

- Host: legion, NixOS, RTX 3080 Laptop 16 GB, driver 595; llama-cpp-python 0.3.35 from the cu125 wheel index; `.planning/spikes/.venv`; `source .planning/spikes/env.sh` before any `llama_cpp` import. One model per process; every load under `flock /tmp/melodyscribe-gpu.lock`; a batched server holds the lock for its whole run.
- VRAM per workload: ingest 3739 to 3887 MB (MiniCPM5-2B Q8, `n_ctx=16384`, `n_batch=2048`, K up to 32); retrieval 1371 MB flat (Qwen3-Embedding-0.6B Q8, `n_ctx=2048`). Spike 010 used `n_ctx=4096` for the 2B and 2048 for the 0.6B. The card is never capacity-bound at these sizes.
- Grammar cost: about 9x throughput (275 versus 2479 tok/s) located in CPU-side grammar filtering per token over the 130k vocabulary. Batching the decode with per-slot grammars needs a sampler the stack does not expose; fine-tuning first is the cheaper lever (validity 0.33 dominates economics before throughput does).
- Prompt sizes (spike 009 pool): 281 to 384 tokens, p50 323; shared prefix 105 tokens instruction-after, 319 tokens instruction-first.
- Documents per minute: 7.44 for whole-document one-pass ingest of 20 documents in spike 010 (161.4 s wall, load 0.85 s); 5.06 to 5.67 in the 6-document worker sweep; about 44 sections per minute at the serial-grammar 0.74 req/s of spike 009 (about 9 documents per minute at about 5 sections per document).
- Retrieval: about 800 q/s saturated (K 16 to 64), 140 q/s at K=1; payload about 204 tokens per query (203 to 205); retrieval latency median 0.005 to 0.034 ms per mode on CPU.
- Corpus and queries: 20 documents (hash `ac55d19e…`), 19 sections of at least 200 chars in the 009 pool (one per document, 600-char cap); 118 queries in spike 010 (116 `queries-v1` with one gold document each plus 2 HotpotQA with two gold each); 12 units for the 009 validity check.
- GPU time: spike 009 about 1.5 h under the lock (the N=1024 serial-grammar cell alone about 23 min); spike 010 about 16 min over 6 lock acquisitions.
- Owner re-run status: spike 010 reproduced on 2026-09-12 with all 139 retrieval and store numbers equal, ops and vectors reproduced, only wall-clock fields in `passes.json` and `workers.json` differing within a few percent. Spike 009 reproduction is in progress at the time of writing; the README tables above are the numbers of record until it lands, and `logs/` and `results/` under `.planning/spikes/009-batched-serving-and-cache-order/` may be rewritten by it.

## Origin

Synthesized from spikes: 009, 010; research: `reference/micro-harnesses/deep-research-2/REPORT.md` sections 1 (Q5, Q6) and 5C

Source files available in: sources/009-batched-serving-and-cache-order/, sources/010-pipeline-order-end-to-end/

Normative logs: `.planning/spikes/009-batched-serving-and-cache-order/logs/sweep.jsonl`, `cacheorder.jsonl`, `retrieve.jsonl`, `verify.jsonl`, `probe.jsonl`, `vllm.json` with `results/table.json` and `results/summary.md`; `.planning/spikes/010-pipeline-order-end-to-end/results/pipeline-order.md`, `retrieval.json`, `stores_report.json`, `passes.json`, `workers.json`, `workers_mock.json`. Shared rules in `.planning/spikes/CONVENTIONS.md`.
