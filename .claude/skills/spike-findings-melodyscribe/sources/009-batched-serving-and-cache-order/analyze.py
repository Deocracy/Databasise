"""Spike 009 analysis (CPU only): logs/*.jsonl -> results/table.json + summary.md."""
from __future__ import annotations
import json
import os

D = os.path.dirname(os.path.abspath(__file__))


def load(name: str) -> list[dict]:
    p = os.path.join(D, "logs", name)
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p) if l.strip()]


def main() -> int:
    os.makedirs(os.path.join(D, "results"), exist_ok=True)
    probe = load("probe.jsonl")
    sweep = load("sweep.jsonl")
    cache = load("cacheorder.jsonl")
    retr = load("retrieve.jsonl")

    def ev(rows, event, **kw):
        return [r for r in rows if r.get("event") == event
                and all(r.get(k) == v for k, v in kw.items())]

    out: dict = {}
    g = ev(probe, "grammar_decode")
    gr = ev(probe, "greedy_decode")
    e = ev(probe, "embed_q")
    out["probe"] = {
        "grammar_s": [r["seconds"] for r in g],
        "greedy_s": [r["seconds"] for r in gr],
        "embed_ms": [r["seconds"] * 1000 for r in e],
    }
    out["ingest_cells"] = [r for r in sweep if r.get("event") == "cell"]
    out["ksat"] = [r for r in sweep if r.get("event") == "ksat"]
    out["verify"] = ev(sweep, "verify")
    out["validity"] = ev(sweep, "validity")
    out["cache"] = [r for r in cache
                    if r.get("event") in ("fractions", "prefix_once_vs_naive",
                                          "sorted_vs_shuffled",
                                          "continuation", "output_order")]
    out["retrieval_cells"] = [r for r in retr if r.get("event") == "cell"]
    out["retrieval_verify"] = ev(retr, "verify_batch")
    out["retrieval_index"] = ev(retr, "index")
    out["retrieval_sanity"] = ev(retr, "recall_sanity")
    json.dump(out, open(os.path.join(D, "results", "table.json"), "w"),
              indent=1)

    L = []
    L.append("# Spike 009 results summary (generated; see table.json)")
    L.append("")
    L.append("## Ingest (MiniCPM5-2B Q8, v0.2 grammar, cap 48)")
    L.append("")
    L.append("| sched | N | K | wall_s | tok/s | req/s | ttft_p50_ms | "
             "ttft_p95_ms | vram_peak |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for c in out["ingest_cells"]:
        L.append(
            f"| {c['sched']} | {c['N']} | {c['K']} | {c['wall_s']} | "
            f"{c['tok_per_s']} | {c['req_per_s']} | {c['ttft_p50_ms']} | "
            f"{c['ttft_p95_ms']} | {c.get('vram_peak_mb')} |")
    L.append("")
    L.append("## Retrieval (Qwen3-Embedding-0.6B Q8 + Faiss top-10)")
    L.append("")
    L.append("| N | K | wall_s | q/s | ttft_p50_ms | ttft_p95_ms | vram |")
    L.append("|---|---|---|---|---|---|---|")
    for c in out["retrieval_cells"]:
        L.append(
            f"| {c['N']} | {c['K']} | {c['wall_s']} | {c['q_per_s']} | "
            f"{c['ttft_p50_ms']} | {c['ttft_p95_ms']} | "
            f"{c.get('vram_mb')} |")
    open(os.path.join(D, "results", "summary.md"), "w").write("\n".join(L)
                                                             + "\n")
    print("wrote results/table.json + results/summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
