"""Score spike 008 (no GPU, no network; stdlib only).

Inputs: spike-003 teacher.json + students/<DESIGN>_<arm>.json (16 scored docs
each). Same per-arm metrics as spike-003 evaluate.py, macro/micro-averaged
over the SCORED set only:

- routing_exact, subjval_recall, op_p/op_r/op_f1, parse_rate,
  proof_pass_rate, tokens_per_para, secs_per_para, fail_reasons, per_doc.

Plus a D0 reproduction check: D0_<arm> outputs must be byte-identical to
spike-003 students/<arm>.json on the scored docs (same prompt bytes, same
decode settings, greedy seed fixed).

Writes results.json + one JSON line (ISO timestamp) to logs/score-<utc>.jsonl.
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prompts  # noqa: E402
from prompts import HERE, SPIKE003, split_docs  # noqa: E402

sys.path.insert(0, str(SPIKE003))
from common import FILE_SET, load_units, ops_validate  # noqa: E402
import resolve as v02  # noqa: E402


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def norm(s: str) -> str:
    return " ".join(str(s).lower().split())


def subj_of(op: dict) -> str:
    return op.get("s", op.get("subject", ""))


def pred_of(op: dict) -> str:
    return op.get("p", op.get("attribute", ""))


def val_of(op: dict) -> str:
    return op.get("o", op.get("value", ""))


def full_key(op: dict) -> tuple:
    return (op.get("target"), norm(subj_of(op)), norm(pred_of(op)), norm(val_of(op)))


def sv_key(op: dict) -> tuple:
    return (op.get("target"), norm(subj_of(op)), norm(val_of(op)))


def score_outputs(outs: dict, t_pass: dict, contents: dict, docs: list[str]) -> dict:
    n = len(docs)
    route_hit, sv_recalls = 0, []
    tp = fp = fn = 0
    n_emitted = n_passing = 0
    n_parsed = 0
    toks, secs = [], []
    fail_reasons: dict[str, int] = {}
    per_doc = []
    for doc_id in docs:
        content = contents[doc_id]
        t = t_pass[doc_id]
        o = outs[doc_id]
        toks.append(o.get("completion_tokens") or 0)
        secs.append(o.get("seconds") or 0.0)
        try:
            obj = json.loads(o["text"])
            parsed = isinstance(obj, dict) and set(obj) == {"ops"} and isinstance(obj["ops"], list)
        except Exception:
            parsed = False
        n_parsed += parsed
        if parsed:
            res = v02.validate_v02(obj, FILE_SET, content, ops_validate)
            s = res["passed"]
            for v in res["verdicts"]:
                if not v["pass"]:
                    cat = (v["reasons"][0].split(":")[0]
                           if v["reasons"] else "unknown")
                    fail_reasons[cat] = fail_reasons.get(cat, 0) + 1
        else:
            res = {"passed": [], "failed": [{"_reasons": ["unparseable"]}], "verdicts": []}
            s = []
            fail_reasons["unparseable-output"] = fail_reasons.get("unparseable-output", 0) + 1
        n_emitted += len(obj["ops"]) if parsed else 0
        n_passing += len(s)
        if {x.get("target") for x in s} == {x.get("target") for x in t}:
            route_hit += 1
        sk = {sv_key(x) for x in s}
        if not t:
            sv_recalls.append(1.0 if not s else 0.0)
        else:
            sv_recalls.append(sum(1 for x in t if sv_key(x) in sk) / len(t))
        tk = [full_key(x) for x in t]
        skf = [full_key(x) for x in s]
        rest = list(skf)
        hit = 0
        for k in tk:
            if k in rest:
                rest.remove(k)
                hit += 1
        tp += hit
        fp += len(skf) - hit
        fn += len(tk) - hit
        per_doc.append({"doc": doc_id, "t_ops": len(t),
                        "s_emitted": len(obj["ops"]) if parsed else None,
                        "s_passed": len(s), "parsed": parsed,
                        "route_hit": {x.get("target") for x in s} == {x.get("target") for x in t}})
    prec = tp / (tp + fp) if (tp + fp) else (1.0 if (tp + fn) == 0 else 0.0)
    rec = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {
        "n_docs": n,
        "routing_exact": round(route_hit / n, 3),
        "subjval_recall": round(sum(sv_recalls) / n, 3),
        "op_p": round(prec, 3), "op_r": round(rec, 3), "op_f1": round(f1, 3),
        "parse_rate": round(n_parsed / n, 3),
        "proof_pass_rate": round(n_passing / n_emitted, 3) if n_emitted else 1.0,
        "n_emitted": n_emitted, "n_passed": n_passing,
        "fail_reasons": fail_reasons,
        "tokens_per_para": round(sum(toks) / n, 1),
        "secs_per_para": round(sum(secs) / n, 2),
        "total_completion_tokens": sum(toks),
        "per_doc": per_doc,
    }


def main() -> None:
    units, corpus_hash = load_units()
    contents = dict(units)
    examples, scored = split_docs()
    teacher = json.loads((SPIKE003 / "teacher.json").read_text())
    assert teacher["corpus_hash"] == corpus_hash, "teacher labels are for another corpus state"
    assert teacher.get("schema") == "ops.v0.2", "teacher labels are not v0.2"
    t_pass = {doc_id: lab["ops"] for doc_id, lab in teacher["labels"].items()}

    arms = ["minicpm2b", "qwen4b"]
    table = []
    repro = {}
    for arm in arms:
        s003 = json.loads((SPIKE003 / "students" / f"{arm}.json").read_text())
        assert s003["corpus_hash"] == corpus_hash, f"003 {arm}: corpus drift"
        for d in prompts.DESIGNS:
            sdoc = json.loads((HERE / "students" / f"{d}_{arm}.json").read_text())
            assert sdoc["corpus_hash"] == corpus_hash, f"{d}_{arm}: corpus drift"
            assert sdoc.get("schema") == "ops.v0.2", f"{d}_{arm}: wrong schema"
            m = score_outputs(sdoc["outputs"], t_pass, contents, scored)
            row = {"design": d, "arm": arm, "model_file": sdoc["model_file"], **m}
            think = sum(1 for doc in scored if sdoc["outputs"][doc].get("think_tag"))
            row["think_hits"] = think
            table.append(row)
            if d == "D0":
                same = sum(1 for doc in scored
                           if sdoc["outputs"][doc]["text"] == s003["outputs"][doc]["text"])
                repro[arm] = {"identical": same, "of": len(scored)}

    results = {"ts": now(), "corpus_hash": corpus_hash,
               "example_docs": examples, "scored_docs": scored,
               "d0_reproduction_vs_003": repro, "arms": table}
    (HERE / "results.json").write_text(json.dumps(results, indent=1) + "\n")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with open(HERE / "logs" / f"score-{stamp}.jsonl", "w") as f:
        f.write(json.dumps({"ts": now(), "event": "score",
                            "repro": repro,
                            "arms": [{k: v for k, v in a.items()
                                       if k != "per_doc"} for a in table]}) + "\n")
    print(f"examples={examples}")
    print(f"D0 reproduction vs 003: {repro}")
    print(f"{'design':<7}{'arm':<10}{'route':>7}{'sv_rec':>8}{'op_f1':>7}"
          f"{'parse':>7}{'proof':>7}{'tok/para':>9}{'s/para':>8}")
    for a in table:
        print(f"{a['design']:<7}{a['arm']:<10}{a['routing_exact']:>7.3f}"
              f"{a['subjval_recall']:>8.3f}{a['op_f1']:>7.3f}"
              f"{a['parse_rate']:>7.3f}{a['proof_pass_rate']:>7.3f}"
              f"{a['tokens_per_para']:>9.1f}{a['secs_per_para']:>8.2f}")


if __name__ == "__main__":
    sys.exit(main())
