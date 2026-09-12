"""Spike 010 CPU worker control (no GPU, stdlib only).

Same asyncio structure as gpu_workers.py (W tasks, model lock, per-store
locks, streamed writes) but the "model" is an instant stub with a fixed
0.05 s sleep standing in for decode. Answers whether the harness itself
scales when the model is not the bottleneck (batched-serving future),
isolating harness overhead from GPU serialisation.

Writes results/workers_mock.json + logs/workers-mock-<utc>.jsonl.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s10_common as C  # noqa: E402

STUB_S = 0.05


def main() -> None:
    ws = [1, 2, 4, 8]
    for a in sys.argv[1:]:
        if a.startswith("--ws="):
            ws = [int(x) for x in a.split("=", 1)[1].split(",") if x != ""]

    log_dir = C.HERE / "logs"
    res_dir = C.HERE / "results"
    log_dir.mkdir(exist_ok=True)
    res_dir.mkdir(exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_fh = open(log_dir / f"workers-mock-{stamp}.jsonl", "w")

    docs, corpus_hash = C.load_corpus()
    # 60 pseudo-units (20 docs x 3) so W=8 has work to share
    units = [(d, t) for d, t in docs for _ in range(3)]

    model_lock = asyncio.Lock()
    store_locks = {"graph": asyncio.Lock(), "sql": asyncio.Lock()}

    def blocking_stub(doc_id, content):
        time.sleep(STUB_S)
        return {"ok": True}

    async def run_w(w):
        sem = asyncio.Semaphore(w)
        store = {"n": 0}

        async def one(doc_id, content):
            async with sem:
                async with model_lock:
                    await asyncio.to_thread(blocking_stub, doc_id, content)
                async with store_locks["graph"]:
                    store["n"] += 1

        t1 = time.perf_counter()
        await asyncio.gather(*[one(d, t) for d, t in units])
        wall = time.perf_counter() - t1
        C.emit(log_fh, "w_run_mock", w=w, wall_s=round(wall, 3),
               units=len(units), filed=store["n"])
        return {"w": w, "wall_s": round(wall, 3), "filed": store["n"]}

    async def amain():
        return [await run_w(w) for w in ws]

    runs = asyncio.run(amain())
    (res_dir / "workers_mock.json").write_text(json.dumps(
        {"units": len(units), "stub_s": STUB_S, "runs": runs}, indent=1))
    print(f"ws={ws}")
    for r in runs:
        print(f"W={r['w']}: wall={r['wall_s']}s filed={r['filed']}")


if __name__ == "__main__":
    sys.exit(main())
