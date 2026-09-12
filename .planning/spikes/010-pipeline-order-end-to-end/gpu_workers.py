"""Spike 010 worker sweep (run under flock; ONE model process total).

W in (1,2,4,8) as asyncio tasks over one loaded MiniCPM5-2B process:
workers never load their own model (one-model-per-process rule). One
asyncio.Lock serialises model calls (llama-cpp-python is synchronous;
calls run via asyncio.to_thread); one lock per store serialises writes.

Subset: 6 documents (fixed indices) to bound GPU time; each W runs the
full per-doc pipeline (embed + grammar ops decode + Proof + store file).
Stores are rebuilt per W so conflicts/duplicates are attributable.

Writes logs/workers-<utc>.jsonl + results/workers.json.
Usage: gpu_workers.py [--units i,j,..] [--ws 1,2,4,8]
"""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s10_common as C  # noqa: E402

MODEL_2B = "MiniCPM5-2B-Q8_0.gguf"
SEED = 1234
MAX_TOKENS = 1024


def main() -> None:
    only = [0, 3, 7, 11, 15, 19]
    ws = [1, 2, 4, 8]
    for a in sys.argv[1:]:
        if a.startswith("--units="):
            only = [int(x) for x in a.split("=", 1)[1].split(",") if x != ""]
        elif a.startswith("--ws="):
            ws = [int(x) for x in a.split("=", 1)[1].split(",") if x != ""]

    from llama_cpp import Llama, LlamaGrammar, LLAMA_POOLING_TYPE_LAST
    import sys as _s
    _s.path.insert(0, str(C.SPIKE003))
    from v02_grammar import grammar_v02

    log_dir = C.HERE / "logs"
    res_dir = C.HERE / "results"
    log_dir.mkdir(exist_ok=True)
    res_dir.mkdir(exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = log_dir / f"workers-{stamp}.jsonl"
    log_fh = open(log_path, "w")
    models_dir = os.environ.get("MELODYSCRIBE_MODELS", str(C.HERE.parent / ".models"))

    docs, corpus_hash = C.load_corpus()
    docs = [docs[i] for i in only]
    units = [(d, t) for d, t in docs]  # whole variant

    t0 = time.perf_counter()
    llm = Llama(model_path=os.path.join(models_dir, MODEL_2B),
                n_ctx=4096, n_gpu_layers=-1, embedding=True,
                pooling_type=LLAMA_POOLING_TYPE_LAST, verbose=False)
    load_s = time.perf_counter() - t0
    grammar = LlamaGrammar.from_string(grammar_v02(), verbose=False)
    C.emit(log_fh, "load", model=MODEL_2B, seconds=round(load_s, 2),
           units=[d for d, _ in units])

    model_lock = asyncio.Lock()
    store_locks = {"graph": asyncio.Lock(), "sql": asyncio.Lock(),
                   "vector": asyncio.Lock()}

    def blocking_infer(doc_id, content):
        t1 = time.perf_counter()
        vec = llm.embed(content + C.MARKER)
        emb_s = time.perf_counter() - t1
        t2 = time.perf_counter()
        res = llm.create_completion(C.student_prompt(content), grammar=grammar,
                                    max_tokens=MAX_TOKENS, temperature=0.0,
                                    seed=SEED)
        dec_s = time.perf_counter() - t2
        return vec, res["choices"][0]["text"], emb_s, dec_s

    async def run_w(w):
        store = {"graph": [], "sql": [], "vecs": {},
                 "conflicts": 0, "dup_nodes": 0, "seen": set()}
        seen_lock = asyncio.Lock()

        async def one(doc_id, content):
            async with model_lock:
                vec, text, emb_s, dec_s = await asyncio.to_thread(
                    blocking_infer, doc_id, content)
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
                for op in proof["passed"]:
                    if op["target"] == "sql":
                        store["sql"].append(op)
            async with store_locks["vector"]:
                store["vecs"][doc_id] = True
            return {"doc": doc_id, "emb_s": round(emb_s, 3),
                    "dec_s": round(dec_s, 2),
                    "passed": len(proof["passed"]),
                    "failed": len(proof["failed"])}

        t1 = time.perf_counter()
        # limit concurrency to w with a semaphore (workers = tasks)
        sem = asyncio.Semaphore(w)

        async def bounded(doc_id, content):
            async with sem:
                return await one(doc_id, content)

        out = await asyncio.gather(*[bounded(d, t) for d, t in units])
        wall = time.perf_counter() - t1
        docs_pm = len(units) / wall * 60
        C.emit(log_fh, "w_run", w=w, wall_s=round(wall, 2),
               docs_per_min=round(docs_pm, 2),
               graph_ops=len(store["graph"]), sql_ops=len(store["sql"]),
               dup_nodes=store["dup_nodes"], conflicts=store["conflicts"])
        return {"w": w, "wall_s": round(wall, 2),
                "docs_per_min": round(docs_pm, 2),
                "graph_ops": len(store["graph"]), "sql_ops": len(store["sql"]),
                "dup_nodes": store["dup_nodes"], "conflicts": store["conflicts"],
                "per_doc": out}

    async def amain():
        return [await run_w(w) for w in ws]

    runs = asyncio.run(amain())
    (res_dir / "workers.json").write_text(json.dumps(
        {"units": [d for d, _ in units], "corpus_hash": corpus_hash,
         "load_seconds": round(load_s, 2), "runs": runs}, indent=1) + "\n")
    print(f"ws={ws} log={log_path}")
    for r in runs:
        print(f"W={r['w']}: wall={r['wall_s']}s docs/min={r['docs_per_min']} "
              f"graph={r['graph_ops']} sql={r['sql_ops']} dups={r['dup_nodes']}")


if __name__ == "__main__":
    sys.exit(main())
