"""Spike 005 analysis (no GPU, stdlib only). Reads logs/run.jsonl, writes
results/table.json + results/summary.md, prints the head-to-head table."""
from __future__ import annotations

import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, REPO)
LOG = os.path.join(HERE, "logs", "run.jsonl")
RES = os.path.join(HERE, "results")


def med(xs):
    return round(statistics.median(xs), 4) if xs else None


def f1(pred: str, gold: str) -> float:
    p = pred.lower().split()
    g = gold.lower().split()
    if not p or not g:
        return 0.0
    from collections import Counter
    cp, cg = Counter(p), Counter(g)
    overlap = sum((cp & cg).values())
    if not overlap:
        return 0.0
    prec = overlap / len(p)
    rec = overlap / len(g)
    return round(2 * prec * rec / (prec + rec), 3)


def main() -> int:
    m = json.load(open(os.path.join(REPO, "databasise", "tests", "fixtures",
                                    "corpus", "MANIFEST.json"), encoding="utf-8"))
    gold_ans = {q["id"]: q["answer"] for q in m["queries"]}

    runs: list[dict] = []
    toks: dict = {}
    sweeps: list[dict] = []
    stabs: list[dict] = []
    parts: list[dict] = []
    statepaths: list[dict] = []
    with open(LOG, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            if o.get("ev") == "run":
                runs.append(o)
            elif o.get("ev") == "tokens":
                toks[(o["qid"], o["variant"])] = o
            elif o.get("ev") == "sweep":
                sweeps.append(o)
            elif o.get("ev") == "stability":
                stabs.append(o)
            elif o.get("ev") == "parts":
                parts.append(o)
            elif o.get("ev") == "statepath":
                statepaths.append(o)

    # head-to-head per (qid, variant, arm)
    table = []
    groups: dict[tuple, dict[str, list]] = {}
    for r in runs:
        groups.setdefault((r["qid"], r["variant"]), {}).setdefault(r["arm"], []).append(r)
    for (qid, variant), arms in sorted(groups.items()):
        row = {"qid": qid, "variant": variant,
               "prompt_tok": toks.get((qid, variant), {}).get("prompt_tok")}
        for arm in ("full", "warm", "shift"):
            rs = arms.get(arm, [])
            tt = [x["ttft_s"] for x in rs]
            row[arm] = {
                "n": len(rs),
                "ttft_med": med(tt),
                "ttft_all": tt,
                "correct_rate": round(sum(1 for x in rs if x["correct"]) / len(rs), 3) if rs else None,
                "match_full_rate": (round(sum(1 for x in rs if x.get("match_full")) / len(rs), 3)
                                    if arm != "full" and rs else None),
                "texts": [x["text"] for x in rs],
            }
            if arm == "full" and rs:
                row[arm]["answer"] = rs[0]["text"]
        f = row["full"]["ttft_med"] or 0
        row["warm_speedup"] = round(f / (row["warm"]["ttft_med"] or f), 2) if f else None
        row["shift_speedup"] = round(f / (row["shift"]["ttft_med"] or f), 2) if f else None
        table.append(row)

    # sweep fit: ttft ~ a + b*tok (least squares, stdlib)
    def fit(pts):
        n = len(pts)
        sx = sum(p[0] for p in pts)
        sy = sum(p[1] for p in pts)
        sxx = sum(p[0] * p[0] for p in pts)
        sxy = sum(p[0] * p[1] for p in pts)
        den = n * sxx - sx * sx
        b = (n * sxy - sx * sy) / den if den else 0.0
        a = (sy - b * sx) / n if n else 0.0
        return a, b

    sweep_pts = {"full": [], "warm": []}
    for s in sweeps:
        sweep_pts[s["arm"]].append((s["prompt_tok"], s["ttft_s"]))
    fits = {a: {"intercept_s": round(fit(p)[0], 4),
                "ms_per_tok": round(fit(p)[1] * 1000, 4),
                "n": len(p)} for a, p in sweep_pts.items()}

    # quality deltas of interest
    def correct(qid, variant):
        for row in table:
            if row["qid"] == qid and row["variant"] == variant:
                return row["full"]["correct_rate"]
        return None

    order = {}
    for qid in ("q1", "q2"):
        ab = next((r for r in table if r["qid"] == qid and r["variant"] == "gold-AB"), None)
        ba = next((r for r in table if r["qid"] == qid and r["variant"] == "gold-BA"), None)
        order[qid] = {
            "ab_correct": ab["full"]["correct_rate"] if ab else None,
            "ba_correct": ba["full"]["correct_rate"] if ba else None,
            "ab_eq_ba": (ab["full"]["texts"] == ba["full"]["texts"]) if (ab and ba) else None,
        }

    out = {"table": table, "ttft_fit": fits, "order_swap": order,
           "stability": stabs,
           "q2_f1_full_goldAB": [f1(t, gold_ans["q2"]) for t in
                                 next((r["full"]["texts"] for r in table
                                       if r["qid"] == "q2" and r["variant"] == "gold-AB"), [])]}
    os.makedirs(RES, exist_ok=True)
    with open(os.path.join(RES, "table.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)

    L = []
    L.append("# Spike 005 head-to-head (identical inputs per row)\n")
    L.append("| q | variant | tok | full TTFT | full ok | warm TTFT | warm x | warm=full | shift TTFT | shift x | shift=full |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in table:
        L.append(f"| {r['qid']} | {r['variant']} | {r['prompt_tok']} | "
                 f"{r['full']['ttft_med']} | {r['full']['correct_rate']} | "
                 f"{r['warm']['ttft_med']} | {r['warm_speedup']} | {r['warm']['match_full_rate']} | "
                 f"{r['shift']['ttft_med']} | {r['shift_speedup']} | {r['shift']['match_full_rate']} |")
    L.append("")
    L.append(f"TTFT fit full: {fits['full']['ms_per_tok']} ms/tok + "
             f"{fits['full']['intercept_s']} s intercept; "
             f"warm: {fits['warm']['ms_per_tok']} ms/tok + {fits['warm']['intercept_s']} s intercept.")
    L.append(f"Order swap: {json.dumps(order)}")
    L.append(f"Partition probe: {json.dumps([[p['split'], p['same_as_oneshot'], p['div_index']] for p in parts])}")
    L.append(f"State paths: {json.dumps([[s['kind'], s['same']] for s in statepaths])}")
    # q2 partial-credit: ambassador mention (gold fact family, not the exact office)
    for r in table:
        if r["qid"] == "q2":
            r["full"]["has_amb"] = any("ambassador" in t.lower() for t in r["full"]["texts"])
    L.append("q2 ambassador-mention (full): " + json.dumps(
        {r["variant"]: r["full"]["has_amb"] for r in table if r["qid"] == "q2"}))
    md = "\n".join(L) + "\n"
    with open(os.path.join(RES, "summary.md"), "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
