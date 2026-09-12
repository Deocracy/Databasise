"""Spike 009 ingest sweep: op emission under the v0.2 grammar, MiniCPM5-2B Q8.

GPU process (under flock via run.sh). One model load, then:
  verify  - 4 prompts: scheduler (a) serial-grammar and (b) parallel-greedy
            outputs byte-equal the K=1 public-path references. Abort if not.
  matrixA - SERIAL-GRAMMAR (batched prefill + serial grammar slot decode,
            the true op path): N,K cells; N=256,1024 at K=1 (decode is
            serial, so K cannot change wall -- the N=64 K-range is the
            evidence; see README).
  matrixB - PARALLEL-GREEDY (batched prefill + lockstep batched greedy
            decode, the batching ceiling): full N,K matrix + saturating K
            at N=256,1024.
  valid   - 12 units at cap 256, K=1: grammar vs greedy parse+Proof rates.
"""
from __future__ import annotations
import os
import statistics
import sys
import time

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
sys.path.insert(0, os.path.join(D, "..", "003-op-emission-size-sweep"))
from common import load_units, student_prompt  # noqa: E402
from v02_grammar import grammar_v02  # noqa: E402
from resolve import validate_v02  # noqa: E402
import ops_validate  # noqa: E402 (spike 001, via 003's path insert)
from batchserve import (set_generative, emit, vram_used_mb, wave_prefill,  # noqa: E402
                        slot_decode_grammar, wave_decode_parallel_greedy)

MODELS = os.environ["MELODYSCRIBE_MODELS"]
MODEL = os.path.join(MODELS, "MiniCPM5-2B-Q8_0.gguf")
GRAMMAR = grammar_v02()
CAP = 48
FILE_SET = ("graph", "sql")


def build_pool() -> tuple[list[str], list[str], str]:
    units, chash = load_units()
    paras = []
    for doc_id, text in units:
        body = text.split("\n", 1)[1] if "\n" in text else text
        for p in [x.strip().replace("\n", " ") for x in body.split("\n\n")]:
            if len(p) >= 200:
                paras.append(p[:600])
                break
    return [student_prompt(p) for p in paras], paras, chash


def pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * q))]


def run_cell_A(log, llm, reqs: list[list[int]], K: int, N: int,
               cap: int = CAP) -> dict:
    """Serial-grammar wave scheduler. Returns cell summary."""
    t_cell = time.perf_counter()
    ttfts: list[float] = []
    waits: list[float] = []
    gen_tok = 0
    pre_tok = sum(len(r) for r in reqs)
    pre_s = 0.0
    dec_s = 0.0
    vpeak = 0.0
    first_ids: list[int] = []
    for w in range(0, N, K):
        wave = reqs[w:w + K]
        t_w = time.perf_counter()
        llm._ctx.kv_cache_clear()
        t0 = time.perf_counter()
        _, lens = wave_prefill(llm, wave)
        pre_s += time.perf_counter() - t0
        for j, (t, L) in enumerate(zip(wave, lens)):
            text, ids, ttft, ds = slot_decode_grammar(
                llm, j + 1, L, t[-1], GRAMMAR, cap)
            dec_s += ds
            gen_tok += len(ids)
            now = time.perf_counter()
            waits.append(t_w - t_cell)
            ttfts.append(now - t_cell)
            if len(first_ids) < 8:
                first_ids.append(ids[0] if ids else -1)
        v = vram_used_mb()
        if v and v > vpeak:
            vpeak = v
    wall = time.perf_counter() - t_cell
    return {"sched": "serial-grammar", "N": N, "K": K, "wall_s": round(wall, 3),
            "prefill_s": round(pre_s, 3), "decode_s": round(dec_s, 3),
            "prompt_tok": pre_tok, "gen_tok": gen_tok,
            "tok_per_s": round((pre_tok + gen_tok) / wall, 1),
            "req_per_s": round(N / wall, 3),
            "ttft_p50_ms": round(pct(ttfts, 0.5) * 1000, 1),
            "ttft_p95_ms": round(pct(ttfts, 0.95) * 1000, 1),
            "wait_p50_ms": round(pct(waits, 0.5) * 1000, 1),
            "vram_peak_mb": vpeak, "first_ids": first_ids}


def run_cell_B(log, llm, reqs: list[list[int]], K: int, N: int,
               cap: int = CAP, keep_text: bool = False) -> dict:
    """Parallel-greedy wave scheduler. Returns cell summary."""
    t_cell = time.perf_counter()
    ttfts: list[float] = []
    gen_tok = 0
    pre_tok = sum(len(r) for r in reqs)
    pre_s = 0.0
    dec_s = 0.0
    vpeak = 0.0
    texts: list[str] = []
    for w in range(0, N, K):
        wave = reqs[w:w + K]
        llm._ctx.kv_cache_clear()
        t0 = time.perf_counter()
        _, lens = wave_prefill(llm, wave)
        t_pre = time.perf_counter() - t0
        pre_s += t_pre
        slots = [j + 1 for j in range(len(wave))]
        outs, ds, first_ss = wave_decode_parallel_greedy(
            llm, slots, lens, [t[-1] for t in wave], cap)
        dec_s += ds
        t_end = time.perf_counter()
        for o in outs:
            gen_tok += len(o)
            ttfts.append(t_end - t_cell)
        if keep_text:
            texts.extend(llm.detokenize(o).decode(
                "utf-8", errors="replace") for o in outs)
        v = vram_used_mb()
        if v and v > vpeak:
            vpeak = v
    wall = time.perf_counter() - t_cell
    return {"sched": "parallel-greedy", "N": N, "K": K,
            "wall_s": round(wall, 3),
            "prefill_s": round(pre_s, 3), "decode_s": round(dec_s, 3),
            "prompt_tok": pre_tok, "gen_tok": gen_tok,
            "tok_per_s": round((pre_tok + gen_tok) / wall, 1),
            "req_per_s": round(N / wall, 3),
            "ttft_p50_ms": round(pct(ttfts, 0.5) * 1000, 1),
            "ttft_p95_ms": round(pct(ttfts, 0.95) * 1000, 1),
            "vram_peak_mb": vpeak,
            "texts": texts if keep_text else []}


def main() -> int:
    from llama_cpp import Llama, LlamaGrammar
    log = open(os.path.join(D, "logs", "sweep.jsonl"), "w")
    prompts, paras, chash = build_pool()
    emit(log, "pool", sections=len(prompts), corpus_hash=chash,
         cap=CAP, grammar="score-io-v0.2-spike003 file=graph,sql")

    t0 = time.perf_counter()
    llm = Llama(model_path=MODEL, n_gpu_layers=-1, n_ctx=16384, n_batch=2048,
                embedding=True, verbose=False)
    set_generative(llm)  # multi-output logits; never embed() here
    emit(log, "load", seconds=round(time.perf_counter() - t0, 3),
         vram_mb=vram_used_mb())

    def tok(s: str) -> list[int]:
        return llm.tokenize(s.encode(), add_bos=False, special=False)

    ptoks = [tok(p) for p in prompts]
    emit(log, "prompt_tokens", n=len(ptoks),
         p50=len(sorted(ptoks, key=len)[len(ptoks) // 2]),
         max=max(len(t) for t in ptoks))

    # ---- verify: scheduler == production path up to tie flips ----
    V = ptoks[:4]
    refs = []
    for p in prompts[:4]:
        r = llm.create_completion(
            p, grammar=LlamaGrammar.from_string(GRAMMAR, verbose=False),
            max_tokens=CAP, temperature=0.0, seed=11)
        refs.append(r["choices"][0]["text"])
    refs_f = []
    for p in prompts[:4]:
        r = llm.create_completion(p, max_tokens=CAP, temperature=0.0,
                                  seed=11)
        refs_f.append(r["choices"][0]["text"])

    def first_id(text: str) -> int:
        ids = llm.tokenize(text.encode(), add_bos=False, special=False)
        return ids[0] if ids else -1

    llm._ctx.kv_cache_clear()
    _, lens_v = wave_prefill(llm, V)
    got = []
    firsts_a = []
    for j, (t, L) in enumerate(zip(V, lens_v)):
        text, ids, _, _ = slot_decode_grammar(llm, j + 1, L, t[-1],
                                              GRAMMAR, CAP)
        got.append(text)
        firsts_a.append(ids[0] if ids else -1)
    eq_full_a = [a == b for a, b in zip(got, refs)]
    eq_first_a = [a == first_id(b) for a, b in zip(firsts_a, refs)]
    llm._ctx.kv_cache_clear()
    _, lens_b = wave_prefill(llm, V)
    outs, _, _ = wave_decode_parallel_greedy(llm, [1, 2, 3, 4], lens_b,
                                             [t[-1] for t in V], CAP)
    texts_b = [llm.detokenize(o).decode("utf-8", errors="replace")
               for o in outs]
    eq_full_b = [a == b for a, b in zip(texts_b, refs_f)]
    eq_first_b = [(o[0] if o else -1) == first_id(r)
                  for o, r in zip(outs, refs_f)]
    emit(log, "verify", full_a=eq_full_a, first_a=eq_first_a,
         full_b=eq_full_b, first_b=eq_first_b)
    if not (all(eq_first_a) and sum(eq_full_a) >= 3 and all(eq_first_b)):
        emit(log, "ABORT", ok=False,
             note="scheduler diverges from public path beyond tie noise")
        log.close()
        return 1

    def cycle(n: int) -> list[list[int]]:
        return [ptoks[i % len(ptoks)] for i in range(n)]

    # ---- matrix A: serial grammar ----
    cells_a = [(1, 1), (4, 1), (4, 4), (16, 1), (16, 4), (16, 8), (16, 16),
               (64, 1), (64, 4), (64, 8), (64, 16), (64, 32)]
    res_a = []
    for N, K in cells_a:
        s = run_cell_A(log, llm, cycle(N), K, N)
        res_a.append(s)
        emit(log, "cell", workload="ingest", **s)
    # Ksat for A at N=64 (argmax tok/s; ties -> smallest K)
    best_a = max(res_a[-5:], key=lambda s: s["tok_per_s"])
    ksata = min(s["K"] for s in res_a[-5:]
                if s["tok_per_s"] == best_a["tok_per_s"])
    emit(log, "ksat", sched="serial-grammar", K=ksata,
         table={s["K"]: s["tok_per_s"] for s in res_a[-5:]})
    for N in (256, 1024):
        s = run_cell_A(log, llm, cycle(N), 1, N)
        emit(log, "cell", workload="ingest", **s)

    # ---- matrix B: parallel greedy ----
    cells_b = [(1, 1), (4, 1), (4, 4), (16, 1), (16, 4), (16, 8), (16, 16),
               (64, 1), (64, 4), (64, 8), (64, 16), (64, 32)]
    res_b = []
    for N, K in cells_b:
        s = run_cell_B(log, llm, cycle(N), K, N, keep_text=(N <= 16))
        res_b.append(s)
        emit(log, "cell", workload="ingest", **{k: v for k, v in s.items()
                                                if k != "texts"})
    best_b = max(res_b[-5:], key=lambda s: s["tok_per_s"])
    ksatb = min(s["K"] for s in res_b[-5:]
                if s["tok_per_s"] == best_b["tok_per_s"])
    emit(log, "ksat", sched="parallel-greedy", K=ksatb,
         table={s["K"]: s["tok_per_s"] for s in res_b[-5:]})
    for N in (256, 1024):
        for K in (1, ksatb) if ksatb != 1 else (1,):
            s = run_cell_B(log, llm, cycle(N), K, N)
            emit(log, "cell", workload="ingest", **{k: v for k, v in s.items()
                                                    if k != "texts"})

    # ---- validity sample at cap 256 ----
    import json as _json
    gv = gr = 0
    n_v = 12
    for i in range(n_v):
        r = llm.create_completion(
            prompts[i % len(prompts)],
            grammar=LlamaGrammar.from_string(GRAMMAR, verbose=False),
            max_tokens=256, temperature=0.0, seed=11)
        try:
            obj = _json.loads(r["choices"][0]["text"])
            vr = validate_v02(obj, FILE_SET, paras[i % len(paras)], ops_validate)
            gv += vr.get("ok", False)
        except Exception:
            pass
    llm._ctx.kv_cache_clear()
    _twelve = [ptoks[i % len(ptoks)] for i in range(n_v)]
    _, lens12 = wave_prefill(llm, _twelve)
    outs, _, _ = wave_decode_parallel_greedy(llm, list(range(1, n_v + 1)),
                                             lens12,
                                             [t[-1] for t in _twelve], 256)
    for i, o in enumerate(outs):
        try:
            obj = _json.loads(llm.detokenize(o).decode("utf-8",
                                                       errors="replace"))
            vr = validate_v02(obj, FILE_SET, paras[i % len(paras)], ops_validate)
            gr += vr.get("ok", False)
        except Exception:
            pass
    emit(log, "validity", n=n_v, cap=256, grammar_ok=gv,
         greedy_ok=gr,
         grammar_rate=round(gv / n_v, 3), greedy_rate=round(gr / n_v, 3))
    log.close()
    print("SWEEP DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
