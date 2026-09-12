"""Spike 010 GPU ingest (run under flock; one model per process).

Modes (one process per invocation, model loaded once):
  onepass  MiniCPM5-2B: per section, embed() then grammar ops decode
           (one load, shared process = the one-pass arm).
  embed2b  MiniCPM5-2B embed-only (two-pass arm, part 1 of 2 loads).
  ops2b    MiniCPM5-2B grammar-ops-decode-only (two-pass arm, part 2).
  embed06  Qwen3-Embedding-0.6B: embed all ingest sections + all queries.
  embq2b   MiniCPM5-2B: embed all queries (for the 2B vector index).

Embedding recipe is spike 004's settled arm verbatim:
  2B: pooling LAST, no prefix, literal MARKER appended (arm B).
  0.6B: native pooling, no prefix, no marker (arm A).
Ops decode recipe is spike 003's student.py verbatim: raw completion,
v0.2 grammar file=graph,sql, temperature 0, seed 1234, cap 1024.

Usage:
  gpu_ingest.py <mode> [--variant whole|split] [--units i,j,..] [--tag NAME]
Writes vectors/<tag>_<mode>.json + logs/gpu-<tag>-<mode>-<utc>.jsonl.
"""

from __future__ import annotations

import datetime
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s10_common as C  # noqa: E402

MODEL_2B = "MiniCPM5-2B-Q8_0.gguf"
MODEL_06 = "Qwen3-Embedding-0.6B-Q8_0.gguf"
SEED = 1234
MAX_TOKENS = 1024
N_CTX_2B = 4096
N_CTX_EMB = 2048


def sections_for(variant, only=None):
    docs, corpus_hash = C.load_corpus()
    if only is not None:
        docs = [docs[i] for i in only]
    secs = []
    for doc_id, text in docs:
        chunks = C.chunk_whole(doc_id, text) if variant == "whole" \
            else C.chunk_split(doc_id, text)
        for sec_id, content in chunks:
            assert content.strip(), f"empty section {sec_id}"
            secs.append({"sec": sec_id, "doc": doc_id, "content": content})
    return secs, corpus_hash


def main() -> None:
    from s10_common import MARKER  # noqa

    mode = sys.argv[1]
    variant = "whole"
    only = None
    tag = mode
    for a in sys.argv[2:]:
        if a.startswith("--variant="):
            variant = a.split("=", 1)[1]
        elif a.startswith("--units="):
            only = [int(x) for x in a.split("=", 1)[1].split(",") if x != ""]
        elif a.startswith("--tag="):
            tag = a.split("=", 1)[1]
    assert variant in ("whole", "split"), variant

    out_dir = C.HERE / "vectors"
    out_dir.mkdir(exist_ok=True)
    log_dir = C.HERE / "logs"
    log_dir.mkdir(exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = log_dir / f"gpu-{tag}-{stamp}.jsonl"
    log_fh = open(log_path, "w")
    models_dir = os.environ.get("MELODYSCRIBE_MODELS", str(C.HERE.parent / ".models"))

    if mode in ("onepass", "embed2b", "ops2b", "embq2b"):
        from llama_cpp import Llama, LlamaGrammar, LLAMA_POOLING_TYPE_LAST
        import sys as _s
        _s.path.insert(0, str(C.SPIKE003))
        from v02_grammar import grammar_v02

        secs, corpus_hash = sections_for(variant, only)
        queries = []
        if mode in ("onepass", "embq2b"):
            queries = [(q["id"], q["q"]) for q in C.load_queries_v1()]
            queries += [(q["id"], q["question"]) for q in C.load_hotpot_queries()]

        t0 = time.perf_counter()
        if mode == "embq2b":
            llm = Llama(model_path=os.path.join(models_dir, MODEL_2B),
                        n_ctx=N_CTX_EMB, n_gpu_layers=-1, embedding=True,
                        pooling_type=LLAMA_POOLING_TYPE_LAST, verbose=False)
        else:
            # dual-use instance (spike 002 `dual_use`): generate + embed.
            llm = Llama(model_path=os.path.join(models_dir, MODEL_2B),
                        n_ctx=N_CTX_2B, n_gpu_layers=-1, embedding=True,
                        pooling_type=LLAMA_POOLING_TYPE_LAST, verbose=False)
        load_s = time.perf_counter() - t0
        C.emit(log_fh, "load", mode=mode, variant=variant, model=MODEL_2B,
               n_embd=int(llm.n_embd()), pooling=int(llm.pooling_type()),
               seconds=round(load_s, 2))

        rec = {"mode": mode, "variant": variant, "model": MODEL_2B,
               "corpus_hash": corpus_hash, "seed": SEED,
               "max_tokens": MAX_TOKENS, "load_seconds": round(load_s, 2),
               "sections": {}, "queries": {}}
        grammar = None
        if mode in ("onepass", "ops2b"):
            grammar = LlamaGrammar.from_string(grammar_v02(), verbose=False)

        if mode in ("onepass", "embed2b"):
            for s in secs:
                t1 = time.perf_counter()
                vec = llm.embed(s["content"] + MARKER)
                dt = time.perf_counter() - t1
                rec["sections"].setdefault(s["sec"], {})["emb"] = list(vec[0] if isinstance(vec[0], list) else vec)
                rec["sections"][s["sec"]].update(
                    {"doc": s["doc"], "content": s["content"],
                     "emb_seconds": round(dt, 3)})
                C.emit(log_fh, "embed", sec=s["sec"], seconds=round(dt, 3),
                       dim=len(rec["sections"][s["sec"]]["emb"]))
        if mode in ("onepass", "ops2b"):
            for s in secs:
                prompt = C.student_prompt(s["content"])
                t1 = time.perf_counter()
                res = llm.create_completion(
                    prompt, grammar=grammar, max_tokens=MAX_TOKENS,
                    temperature=0.0, seed=SEED)
                dt = time.perf_counter() - t1
                text = res["choices"][0]["text"]
                usage = res.get("usage", {})
                e = rec["sections"].setdefault(s["sec"], {})
                e.update({"doc": s["doc"], "content": s["content"],
                          "text": text,
                          "prompt_tokens": usage.get("prompt_tokens"),
                          "completion_tokens": usage.get("completion_tokens"),
                          "ops_seconds": round(dt, 2),
                          "think_tag": ("<think" in text.lower())})
                C.emit(log_fh, "decode", sec=s["sec"], seconds=round(dt, 2),
                       prompt_tokens=usage.get("prompt_tokens"),
                       completion_tokens=usage.get("completion_tokens"),
                       chars=len(text))
        if mode in ("onepass", "embq2b"):
            qvecs = {}
            t1 = time.perf_counter()
            for qid, qtext in queries:
                v = llm.embed(qtext + MARKER)
                qvecs[qid] = list(v[0] if isinstance(v[0], list) else v)
            dt = time.perf_counter() - t1
            rec["queries"] = qvecs
            C.emit(log_fh, "queries_embedded", n=len(qvecs),
                   seconds=round(dt, 2))
        out = out_dir / f"{tag}_{mode}.json"
        out.write_text(json.dumps(rec) + "\n")
        print(f"mode={mode} variant={variant} sections={len(rec['sections'])} "
              f"queries={len(rec['queries'])} log={log_path} out={out}")

    elif mode == "embed06":
        from llama_cpp import Llama

        secs_w, corpus_hash = sections_for("whole", only)
        secs_s, _ = sections_for("split", only)
        queries = [(q["id"], q["q"]) for q in C.load_queries_v1()]
        queries += [(q["id"], q["question"]) for q in C.load_hotpot_queries()]
        texts = ([("sec|" + s["sec"], s["content"]) for s in secs_w]
                 + [("sec|" + s["sec"], s["content"]) for s in secs_s]
                 + [("q|" + qid, qt) for qid, qt in queries])
        t0 = time.perf_counter()
        llm = Llama(model_path=os.path.join(models_dir, MODEL_06),
                    n_ctx=N_CTX_EMB, n_gpu_layers=-1, embedding=True,
                    verbose=False)
        load_s = time.perf_counter() - t0
        C.emit(log_fh, "load", mode=mode, model=MODEL_06,
               n_embd=int(llm.n_embd()), pooling=int(llm.pooling_type()),
               seconds=round(load_s, 2))
        t1 = time.perf_counter()
        vecs = llm.embed([t for _, t in texts])
        dt = time.perf_counter() - t1
        C.emit(log_fh, "embedded", n=len(texts), seconds=round(dt, 2))
        rec = {"mode": mode, "model": MODEL_06, "corpus_hash": corpus_hash,
               "pooling": "native", "prefix": "", "marker": "none",
               "load_seconds": round(load_s, 2),
               "ids": [k for k, _ in texts],
               "vecs": [list(v) for v in vecs]}
        out = out_dir / f"{tag}_{mode}.json"
        out.write_text(json.dumps(rec) + "\n")
        print(f"mode={mode} n={len(texts)} log={log_path} out={out}")
    else:
        raise SystemExit(f"unknown mode {mode}")


if __name__ == "__main__":
    sys.exit(main())
