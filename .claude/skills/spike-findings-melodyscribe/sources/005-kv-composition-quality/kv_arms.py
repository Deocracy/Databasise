"""Spike 005: kv-composition-quality.

Three arms on IDENTICAL final token strings per (query, variant):
  full  - cold: reset(); generate(full)               -> joint prefill TTFT, exact quality
  warm  - prebuilt KV: reset(); eval(ctx); save; load; generate(q, reset=False)
          -> question-only prefill TTFT over prebuilt chunk KV (isolated-module
             warm-state proxy: chunk tokens are not re-prefilled at query time)
  shift - prefix reuse: run prev prompt sharing the prefix, then generate(full)
          with default reset=True -> llama-cpp-python reuses the longest common
          KV prefix via kv_cache_seq_rm (llama-server --cache-reuse semantics)

Quality: greedy decode (top_k=1), must_contain per query + token F1.
Timing: TTFT = wall time to first yielded token (suffix prefill + 1 decode).

One JSON object per line, key 'ev'. GPU work only; analysis is analyze.py.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import sys
import time

from llama_cpp import Llama  # noqa: E402

CORPUS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "..", "..", "databasise", "tests",
                           "fixtures", "corpus", "documents")
MANIFEST = os.path.join(os.path.dirname(CORPUS_DIR), "MANIFEST.json")


def load_corpus():
    """Stdlib mirror of databasise.parity.corpus.load_snapshot (same checks,
    no project deps): verifies per-doc sha256 + corpus hash, refuses drift."""
    m = json.load(open(MANIFEST, encoding="utf-8"))
    docs = {}
    for did in sorted(m["documents"]):
        p = os.path.join(CORPUS_DIR, did + ".txt")
        text = open(p, encoding="utf-8").read()
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if sha != m["documents"][did]["sha256"]:
            raise RuntimeError(f"corpus drift in {did}")
        docs[did] = (m["documents"][did]["title"], text)
    corpus_hash = hashlib.sha256(
        "\n".join(m["documents"][d]["sha256"] for d in sorted(m["documents"])
                  ).encode()).hexdigest()
    if corpus_hash != m["corpus_hash"]:
        raise RuntimeError("corpus-level hash mismatch")
    return docs, m["queries"], m["corpus_hash"]

MODELS = os.environ["MELODYSCRIBE_MODELS"]
MODEL_FILE = os.path.join(MODELS, "MiniCPM5-2B-Q8_0.gguf")
N_CTX = 8192
MAX_TOK = 64
REPS = 3

CTX_PREFIX = "Answer using only the context below. Do not copy the context back.\n\n"
# fixed distractors, unrelated to both HotpotQA queries (no nationality, no office)
DISTR = ["tyler_bates", "village_accountant", "woodson_arkansas",
         "lord_high_treasurer", "secretary_of_state_for_constitutional_affairs"]
DISTR1 = "tyler_bates"

MUST = {
    "q1": [r"\byes\b", r"american"],
    "q2": [r"chief of protocol"],
}


def ts() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def emit(**kw) -> None:
    print(json.dumps({"ts": ts(), **kw}), flush=True)


def block(title: str, text: str) -> str:
    return f"{title}\n{text.strip()}\n\n"


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


def score(qid: str, text: str) -> dict:
    norm = text.lower()
    pats = MUST[qid]
    hits = [bool(re.search(p, norm)) for p in pats]
    return {"must_hits": hits, "correct": all(hits)}


def main() -> int:
    docs, queries_raw, corpus_hash = load_corpus()
    queries = [(q["id"], q["question"], list(q["gold_document_ids"]))
               for q in queries_raw]
    emit(ev="meta", model=os.path.basename(MODEL_FILE), n_ctx=N_CTX,
         max_tok=MAX_TOK, reps=REPS, corpus_hash=corpus_hash,
         prefix=CTX_PREFIX)

    t0 = time.perf_counter()
    llm = Llama(model_path=MODEL_FILE, n_gpu_layers=-1, n_ctx=N_CTX,
                verbose=False)
    emit(ev="load", load_s=round(time.perf_counter() - t0, 3),
         n_vocab=llm.n_vocab())

    variants = ["gold-AB", "gold-BA", "gold+distr", "distr+gold", "single-1",
                "single-2", "distr-only", "empty", "dup", "long"]

    def titles_text(did):
        return docs[did]

    for qid, question, gold_ids in queries:
        for variant in variants:
            # rebuild with titles
            g1t, g1x = titles_text(gold_ids[0])
            g2t, g2x = titles_text(gold_ids[1])
            dt, dx = titles_text(DISTR1)
            B = lambda t, x: block(t, x)  # noqa: E731
            if variant == "gold-AB":
                ctx = CTX_PREFIX + B(g1t, g1x) + B(g2t, g2x)
            elif variant == "gold-BA":
                ctx = CTX_PREFIX + B(g2t, g2x) + B(g1t, g1x)
            elif variant == "gold+distr":
                ctx = CTX_PREFIX + B(g1t, g1x) + B(g2t, g2x) + B(dt, dx)
            elif variant == "distr+gold":
                ctx = CTX_PREFIX + B(dt, dx) + B(g1t, g1x) + B(g2t, g2x)
            elif variant == "single-1":
                ctx = CTX_PREFIX + B(g1t, g1x)
            elif variant == "single-2":
                ctx = CTX_PREFIX + B(g2t, g2x)
            elif variant == "distr-only":
                ctx = CTX_PREFIX + B(dt, dx)
            elif variant == "empty":
                ctx = CTX_PREFIX
            elif variant == "dup":
                ctx = CTX_PREFIX + B(g1t, g1x) + B(g1t, g1x) + B(g2t, g2x)
            elif variant == "long":
                ctx = CTX_PREFIX + B(g1t, g1x) + B(g2t, g2x)
                for did in DISTR[1:5]:
                    tt, tx = titles_text(did)
                    ctx += B(tt, tx)
            q = f"Question: {question}\nAnswer:"
            full_s = ctx + q
            full_toks = llm.tokenize(full_s.encode("utf-8"), add_bos=True,
                                     special=False)
            ctx_toks = llm.tokenize(ctx.encode("utf-8"), add_bos=True,
                                    special=False)
            # identical-inputs guard: ctx tokens must be a prefix of full tokens
            is_prefix = list(full_toks[:len(ctx_toks)]) == list(ctx_toks)
            emit(ev="tokens", qid=qid, variant=variant,
                 prompt_tok=len(full_toks), ctx_tok=len(ctx_toks),
                 q_tok=len(full_toks) - len(ctx_toks), is_prefix=is_prefix)
            if not is_prefix:
                emit(ev="error", qid=qid, variant=variant,
                     msg="ctx tokens not a prefix of full tokens; skipping warm/shift")
                # still run full arm (valid on its own)
                k = None
            else:
                k = len(ctx_toks)
            q_toks = list(full_toks[k:]) if k is not None else []

            # ---- arm FULL ----
            full_texts = []
            for r in range(REPS):
                llm.reset()
                ids, ttft, total = greedy_gen(llm, list(full_toks), reset=True)
                text = llm.detokenize(ids).decode("utf-8", errors="replace")
                full_texts.append(text)
                emit(ev="run", arm="full", qid=qid, variant=variant, rep=r,
                     ttft_s=round(ttft, 4), total_s=round(total, 4),
                     text=text, **score(qid, text))
            emit(ev="stability", arm="full", qid=qid, variant=variant,
                 identical=all(t == full_texts[0] for t in full_texts))

            if k is None:
                continue
            # ---- arm WARM (prebuilt chunk KV; question-only prefill) ----
            llm.reset()
            llm.eval(list(full_toks[:k]))
            saved = llm.save_state()
            for r in range(REPS):
                llm.load_state(saved)
                ids, ttft, total = greedy_gen(llm, q_toks, reset=False)
                text = llm.detokenize(ids).decode("utf-8", errors="replace")
                emit(ev="run", arm="warm", qid=qid, variant=variant, rep=r,
                     ttft_s=round(ttft, 4), total_s=round(total, 4),
                     text=text, match_full=(text == full_texts[0]),
                     **score(qid, text))

            # ---- arm SHIFT (prefix reuse from a differently-suffixed prompt) ----
            # prev shares CTX_PREFIX + first paragraph, then diverges
            first_para = ctx[len(CTX_PREFIX):].split("\n\n")[0]
            prev_s = CTX_PREFIX + first_para + "\n\nQuestion: Unrelated warmup?\nAnswer:"
            prev_toks = llm.tokenize(prev_s.encode("utf-8"), add_bos=True,
                                     special=False)
            for r in range(REPS):
                llm.reset()
                # populate KV with prev prompt (prefill + 1 token)
                ids0, _, _ = greedy_gen(llm, list(prev_toks), reset=True)
                _ = ids0
                # now the real prompt: longest-common-prefix KV is reused
                ids, ttft, total = greedy_gen(llm, list(full_toks), reset=True)
                text = llm.detokenize(ids).decode("utf-8", errors="replace")
                emit(ev="run", arm="shift", qid=qid, variant=variant, rep=r,
                     ttft_s=round(ttft, 4), total_s=round(total, 4),
                     text=text, match_full=(text == full_texts[0]),
                     **score(qid, text))

    # ---- length sweep (TTFT scaling; q1 gold + repeated distractor pad) ----
    qid, question, gold_ids = queries[0]
    g1t, g1x = titles_text(gold_ids[0])
    pad_para = titles_text(DISTR[2])[1] + " "
    for target in (256, 512, 1024, 2048):
        ctx = CTX_PREFIX + block(g1t, g1x)
        n = 0
        while True:
            probe = llm.tokenize((ctx + f"Question: {question}\nAnswer:").encode(),
                                 add_bos=True, special=False)
            if len(probe) >= target:
                break
            t, x = titles_text(DISTR[n % len(DISTR)])
            ctx += block(t, (x + " " + pad_para * 3).strip())
            n += 1
            if n > 40:
                break
        full_s = ctx + f"Question: {question}\nAnswer:"
        full_toks = list(llm.tokenize(full_s.encode(), add_bos=True,
                                      special=False))
        ctx_toks = list(llm.tokenize(ctx.encode(), add_bos=True,
                                     special=False))
        assert full_toks[:len(ctx_toks)] == ctx_toks, "sweep prefix mismatch"
        k = len(ctx_toks)
        for r in range(REPS):
            llm.reset()
            ids, ttft, total = greedy_gen(llm, full_toks, reset=True)
            text = llm.detokenize(ids).decode("utf-8", errors="replace")
            emit(ev="sweep", arm="full", target=target, rep=r,
                 prompt_tok=len(full_toks), ttft_s=round(ttft, 4),
                 total_s=round(total, 4), **score(qid, text))
        llm.reset()
        llm.eval(full_toks[:k])
        saved = llm.save_state()
        for r in range(REPS):
            llm.load_state(saved)
            ids, ttft, total = greedy_gen(llm, full_toks[k:], reset=False)
            emit(ev="sweep", arm="warm", target=target, rep=r,
                 prompt_tok=len(full_toks), q_tok=len(full_toks) - k,
                 ttft_s=round(ttft, 4), total_s=round(total, 4))

    # ---- partition probe: same tokens, different eval-split points ----
    # If greedy decode diverges depending on where the prefill was split,
    # batch-partition numerics (not method) explain warm/shift text deltas.
    qid, question, gold_ids = queries[0]
    g1t, g1x = titles_text(gold_ids[0])
    g2t, g2x = titles_text(gold_ids[1])
    pctx = CTX_PREFIX + block(g1t, g1x) + block(g2t, g2x)
    pq = f"Question: {question}\nAnswer:"
    ptoks = list(llm.tokenize((pctx + pq).encode(), add_bos=True,
                              special=False))
    ref_ids = None
    for split in ("oneshot", len(ptoks) // 3, len(ptoks) // 2,
                  2 * len(ptoks) // 3):
        llm.reset()
        if split == "oneshot":
            ids, _, _ = greedy_gen(llm, ptoks, reset=True)
        else:
            llm.eval(ptoks[:split])
            ids, _, _ = greedy_gen(llm, ptoks[split:], reset=False)
        if ref_ids is None:
            ref_ids = ids
        div = next((i for i, (a, b) in enumerate(zip(ref_ids, ids)) if a != b),
                   None if len(ids) == len(ref_ids) else min(len(ids), len(ref_ids)))
        emit(ev="parts", split=str(split), div_index=div,
             same_as_oneshot=(ids == ref_ids),
             text=llm.detokenize(ids).decode("utf-8", errors="replace"))

    # ---- state-path diagnostics: exact repeat (no reset) and warm w/o save/load ----
    llm.reset()
    ids_a, _, _ = greedy_gen(llm, ptoks, reset=True)
    text_a = llm.detokenize(ids_a).decode("utf-8", errors="replace")
    ids_b, _, _ = greedy_gen(llm, ptoks, reset=True)  # exact-hit path, no eval
    emit(ev="statepath", kind="exact_repeat_no_reset",
         same=(ids_b == ids_a), text=llm.detokenize(ids_b).decode("utf-8", errors="replace")[:200])
    k0 = len(list(llm.tokenize(pctx.encode(), add_bos=True, special=False)))
    llm.reset()
    llm.eval(ptoks[:k0])
    ids_c, _, _ = greedy_gen(llm, ptoks[k0:], reset=False)  # warm, no save/load
    emit(ev="statepath", kind="warm_no_saveload",
         same=(ids_c == ref_ids), text=llm.detokenize(ids_c).decode("utf-8", errors="replace")[:200])
    llm.reset()
    llm.eval(ptoks[:k0])
    saved0 = llm.save_state()
    llm.load_state(saved0)
    ids_d, _, _ = greedy_gen(llm, ptoks[k0:], reset=False)  # warm with save/load
    emit(ev="statepath", kind="warm_saveload",
         same=(ids_d == ref_ids), text=llm.detokenize(ids_d).decode("utf-8", errors="replace")[:200])

    emit(ev="done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
