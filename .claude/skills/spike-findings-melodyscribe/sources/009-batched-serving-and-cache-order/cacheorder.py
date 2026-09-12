"""Spike 009 cache order: prefix sharing, segment order, continuation reuse.

GPU process (under flock via run.sh) on MiniCPM5-2B Q8. Compares, on
identical final token strings unless stated:
  prefix_once_vs_naive - batched prefill with the shared prefix computed
    once (seq_cp fan-out) vs full per-request prefill; first-token equality
    check + prefill wall + TTFT.
  instr_order - instruction-before-section vs section-before-instruction:
    exact shared-token fractions + tail TTFT after a prefix-once setup.
  sorted_vs_shuffled - 4 distinct shared prefixes x 2 sections: grouped
    (sorted, prefix-once per group) vs arrival order (shuffled, naive).
  continuation - after a real grammar op decode, recall-prompt first-token
    latency reusing the decoded KV vs cold full prefill.
  output_order - continuation TTFT after graph-first vs interleaved op text.
"""
from __future__ import annotations
import os
import statistics
import sys
import time

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
sys.path.insert(0, os.path.join(D, "..", "003-op-emission-size-sweep"))
from common import load_units, INSTRUCTION  # noqa: E402
from v02_grammar import grammar_v02  # noqa: E402
from batchserve import (set_generative, emit, vram_used_mb, wave_prefill_naive,  # noqa: E402
                        wave_prefill, wave_prefill_prefix_once,
                        raw_decode_rows, slot_decode_grammar)

MODELS = os.environ["MELODYSCRIBE_MODELS"]
MODEL = os.path.join(MODELS, "MiniCPM5-2B-Q8_0.gguf")
GRAMMAR = grammar_v02()
CAP = 48
REPS = 3

SKILL = ("MelodyScribe filing skill v0.2. Targets graph and sql. "
         "Graph op needs subject, predicate, object, quote. "
         "Sql op needs subject, attribute, value, value_type, quote. "
         "Dates as ISO 8601 or a year, numbers as decimals. "
         "Emit {\"ops\":[...]} with at most 32 ops. ")
SYS = ("You are MelodyScribe, a precise information-extraction harness. "
       "Output JSON only, no prose. ")
DOC_PREFIX = "MelodyScribe ingest v0.1. File facts with evidence spans. "


def med(xs: list[float]) -> float:
    return statistics.median(xs)


def main() -> int:
    from llama_cpp import Llama, LlamaGrammar
    log = open(os.path.join(D, "logs", "cacheorder.jsonl"), "w")
    units, chash = load_units()
    paras = []
    for doc_id, text in units:
        body = text.split("\n", 1)[1] if "\n" in text else text
        for p in [x.strip().replace("\n", " ") for x in body.split("\n\n")]:
            if len(p) >= 200:
                paras.append(p[:600])
                break
    t0 = time.perf_counter()
    llm = Llama(model_path=MODEL, n_gpu_layers=-1, n_ctx=16384, n_batch=2048,
                embedding=True, verbose=False)
    set_generative(llm)  # multi-output logits; never embed() here
    emit(log, "load", seconds=round(time.perf_counter() - t0, 3),
         vram_mb=vram_used_mb())

    def tok(s: str) -> list[int]:
        return llm.tokenize(s.encode(), add_bos=False, special=False)

    P = tok(SYS + SKILL + DOC_PREFIX)
    P_str = SYS + SKILL + DOC_PREFIX
    T_after = [tok("Section:\n" + p + "\n\n" + INSTRUCTION + "\nJSON:\n")
               for p in paras[:8]]
    T_before = [tok(INSTRUCTION + "\nSection:\n" + p + "\nJSON:\n")
                for p in paras[:8]]
    FULL_after = [tok(P_str + "Section:\n" + p + "\n\n" + INSTRUCTION
                      + "\nJSON:\n") for p in paras[:8]]
    FULL_before = [tok(P_str + INSTRUCTION + "\nSection:\n" + p + "\nJSON:\n")
                   for p in paras[:8]]
    # junction artifact: P+T concat vs single-string ids (002 boundary
    # merges); both timing arms use the SAME concat ids, artifact quantified
    def lead_match(full, pre):
        n = 0
        for a, b in zip(full, pre):
            if a != b:
                break
            n += 1
        return n
    lead_after = [lead_match(FULL_after[i], P) for i in range(8)]
    lead_before = [lead_match(FULL_before[i], P) for i in range(8)]
    shared_before = len(tok(P_str + INSTRUCTION))
    emit(log, "fractions",
         prefix_toks=len(P),
         shared_before_toks=shared_before,
         shared_prefix_lead_match_after=lead_after,
         shared_prefix_lead_match_before=lead_before,
         tail_after_p50=sorted(len(t) for t in T_after)[4],
         tail_before_p50=sorted(len(t) for t in T_before)[4],
         shared_frac_after=round(len(P) / (len(P) + sum(
             len(t) for t in T_after) / len(T_after)), 4),
         shared_frac_before=round(shared_before / (shared_before + sum(
             len(t) for t in T_before) / len(T_before)), 4))

    # Both timing arms use the SAME concat ids (P+T); single-string FULL
    # rows exist only to quantify the junction artifact above.
    FULLc_after = [P + t for t in T_after]
    # ---- prefix-once vs naive, identical final strings ----
    for rep in range(REPS):
        llm._ctx.kv_cache_clear()
        t0 = time.perf_counter()
        _, lens_n = wave_prefill(llm, FULLc_after)
        t_naive = time.perf_counter() - t0
        first_naive = []
        for j, (f, L) in enumerate(zip(FULLc_after, lens_n)):
            first_naive.append(slot_decode_grammar(
                llm, j + 1, L, f[-1], GRAMMAR, 1)[1][0])
        llm._ctx.kv_cache_clear()
        t0 = time.perf_counter()
        t_setup, t_tails = wave_prefill_prefix_once(llm, P, T_after)
        t_po = time.perf_counter() - t0
        first_po = []
        for j, (f, L) in enumerate(zip(FULLc_after, lens_n)):
            first_po.append(slot_decode_grammar(
                llm, j + 1, L, f[-1], GRAMMAR, 1)[1][0])
        emit(log, "prefix_once_vs_naive", rep=rep,
             naive_prefill_s=round(t_naive, 4),
             po_setup_s=round(t_setup, 4), po_tails_s=round(t_tails, 4),
             po_total_s=round(t_po, 4),
             first_token_equal=[a == b for a, b in
                                zip(first_naive, first_po)],
             vram_mb=vram_used_mb())

    # ---- sorted vs shuffled prefixes ----
    P4 = [tok(SYS + SKILL + f"Corpus shard {k}. " + DOC_PREFIX)
          for k in range(4)]
    groups = [[(P4[k], T_after[2 * k]), (P4[k], T_after[2 * k + 1])]
              for k in range(4)]
    flat_sorted = [x for g in groups for x in g]
    flat_shuffled = [flat_sorted[i] for i in (0, 3, 6, 1, 4, 7, 2, 5)]
    full_of = lambda pr, t: pr + t  # noqa: E731
    t_sorted, t_shuf = [], []
    for rep in range(REPS):
        llm._ctx.kv_cache_clear()
        t0 = time.perf_counter()
        for g in groups:  # sorted: one prefix-once wave per group
            llm._ctx.kv_cache_clear()  # free previous group's slot KV
            wave_prefill_prefix_once(llm, g[0][0], [g[0][1], g[1][1]])
        t_sorted.append(time.perf_counter() - t0)
        llm._ctx.kv_cache_clear()
        t0 = time.perf_counter()
        wave_prefill_naive(llm, [full_of(pr, t)
                                 for pr, t in flat_shuffled])
        t_shuf.append(time.perf_counter() - t0)
    emit(log, "sorted_vs_shuffled", reps=REPS,
         sorted_s=round(med(t_sorted), 4), shuffled_s=round(med(t_shuf), 4),
         sorted_each=[round(x, 4) for x in t_sorted],
         shuffled_each=[round(x, 4) for x in t_shuf])

    # ---- continuation: reuse decoded KV vs cold prefill ----
    # slot_decode_grammar leaves (prompt + ops) KV on the slot's own
    # sequence (here slot 1); the reuse arm decodes R at new positions on a
    # snapshot of that sequence. No same-position re-decode anywhere.
    llm._ctx.kv_cache_clear()
    _, (L0,) = wave_prefill(llm, [FULL_after[0]])
    ops_text, ops_ids, _, _ = slot_decode_grammar(llm, 1, L0,
                                                  FULL_after[0][-1],
                                                  GRAMMAR, CAP)
    R = tok("\nRecall: Who is described? {\"recall\":[{\"source\":\"vector\","
            "\"k\":8}]}\nAnswer:\n")
    base = L0 + len(ops_ids) - 1  # first sampled tok is logits-only
    # reuse: per rep, rebuild (prompt + ops) with proven ops only (bulk
    # prefill + slot decode, no seq copy), then decode R at new positions
    # on the same sequence and sample the first continuation token.
    reuse_tt = []
    for rep in range(REPS):
        llm._ctx.kv_cache_clear()
        _, (Lb,) = wave_prefill(llm, [FULL_after[0]])
        _, oids, _, _ = slot_decode_grammar(llm, 1, Lb, FULL_after[0][-1],
                                            GRAMMAR, CAP)
        base_b = Lb + len(oids) - 1
        t0 = time.perf_counter()
        rows = [(1, base_b + i, tk, i == len(R) - 1)
                for i, tk in enumerate(R)]
        raw_decode_rows(llm, rows)
        llm.n_tokens = base_b + len(R)
        llm._sampler = llm._init_sampler(top_k=1, temp=0.0)
        llm.sample(top_k=1, temp=0.0, idx=None)
        reuse_tt.append(time.perf_counter() - t0)
        llm._sampler = None
    # cold: full (prompt + ops ids + R) prefill then first token
    cold_tt = []
    cold_full = FULL_after[0] + ops_ids + R
    for rep in range(REPS):
        llm._ctx.kv_cache_clear()
        t0 = time.perf_counter()
        raw_decode_rows(llm, [(3, i, tk, i == len(cold_full) - 1)
                              for i, tk in enumerate(cold_full)])
        llm.n_tokens = len(cold_full)
        llm._sampler = llm._init_sampler(top_k=1, temp=0.0)
        llm.sample(top_k=1, temp=0.0, idx=None)
        cold_tt.append(time.perf_counter() - t0)
        llm._sampler = None
    emit(log, "continuation", ops_len=len(ops_ids),
         reuse_ttft_s=[round(x, 4) for x in reuse_tt],
         cold_ttft_s=[round(x, 4) for x in cold_tt],
         reuse_med_s=round(med(reuse_tt), 4),
         cold_med_s=round(med(cold_tt), 4))

    # ---- output order: graph-first vs interleaved continuation ----
    import json as _json
    ops_gf = ('{"ops":[{"target":"graph","s":"Ed Wood","p":"directed","o":'
              '"Plan 9","quote":"Ed Wood directed Plan 9"},'
              '{"target":"sql","subject":"Ed Wood","attribute":"role",'
              '"value":"director","value_type":"text","quote":"Ed Wood"}]}')
    try:
        _o = _json.loads(ops_gf)
        inter = {"ops": [dict(_o["ops"][1]), dict(_o["ops"][0])]}
        ops_il = _json.dumps(inter)
    except Exception:
        ops_il = ops_gf
    tt_gf, tt_il = [], []
    for rep in range(REPS):
        for bucket, otext in (("gf", ops_gf), ("il", ops_il)):
            toks = FULL_after[1] + tok(otext) + R
            llm._ctx.kv_cache_clear()
            t0 = time.perf_counter()
            raw_decode_rows(llm, [(4, i, tk, i == len(toks) - 1)
                                  for i, tk in enumerate(toks)])
            llm.n_tokens = len(toks)
            llm._sampler = llm._init_sampler(top_k=1, temp=0.0)
            llm.sample(top_k=1, temp=0.0, idx=None)
            (tt_gf if bucket == "gf" else tt_il).append(
                time.perf_counter() - t0)
            llm._sampler = None
    emit(log, "output_order", graph_first_s=[round(x, 4) for x in tt_gf],
         interleaved_s=[round(x, 4) for x in tt_il])
    log.close()
    print("CACHEORDER DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
