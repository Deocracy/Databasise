"""Score the spike-003 sweep (no GPU, no network; stdlib only).

Inputs: teacher.json + students/<arm>.json (identical 20 units everywhere).
For each student output: strict-parse the JSON (grammar should guarantee
shape; a parse failure is scored, never retried), resolve quotes, run v0.2
Proof. Metrics per arm, macro-averaged over the 20 docs:

- routing_exact: fraction of docs where the student's Proof-passing target
  SET equals the teacher's (graph/sql/none routing decision).
- subjval_recall: mean over docs of |teacher ops matched| / |teacher ops|,
  where a teacher op is matched iff some passing student op shares its
  target and its normalised subject AND value. (Empty teacher set: 1.0 iff
  student set is also empty.)
- op_f1: micro F1 over normalised (target, subject, pred/attr, value)
  tuples, pooled over all docs.
- proof_pass_rate: passing student ops / emitted student ops.
- parse_rate: outputs strict-parsing as {"ops":[...]} / 20.
- tokens_per_para: mean completion tokens per doc; secs_per_para likewise.

Writes results.json + one JSON line (ISO timestamp) to logs/score-<utc>.jsonl.
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FILE_SET, HERE, load_units, ops_validate  # noqa: E402
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


def main() -> None:
    argv = sys.argv[1:]
    merges: dict[str, str] = {}
    arms: list[str] = []
    out_path = HERE / "results.json"
    for a in argv:
        if a.startswith("--merge="):
            arm, _, fn = a.split("=", 1)[1].partition(":")
            merges[arm] = fn if fn.endswith(".json") else fn + ".json"
        elif a.startswith("--out="):
            out_path = HERE / a.split("=", 1)[1]
        else:
            arms.append(a)
    if not arms:
        arms = ["minicpm1b", "minicpm2b", "qwen1p7b", "qwen4b", "qwen8b"]
    units, corpus_hash = load_units()
    contents = dict(units)
    teacher = json.loads((HERE / "teacher.json").read_text())
    assert teacher["corpus_hash"] == corpus_hash, "teacher labels are for another corpus state"
    assert teacher.get("schema") == "ops.v0.2", "teacher labels are not v0.2"

    t_pass: dict[str, list[dict]] = {}
    for doc_id, lab in teacher["labels"].items():
        assert not lab.get("_teacher_failed"), f"teacher failed on {doc_id}; re-run teacher first"
        t_pass[doc_id] = lab["ops"]

    table = []
    for arm in arms:
        sdoc = json.loads((HERE / "students" / f"{arm}.json").read_text())
        assert sdoc["corpus_hash"] == corpus_hash, f"{arm}: corpus drift"
        outs = dict(sdoc["outputs"])
        merged_docs: list[str] = []
        if arm in merges:
            mdoc = json.loads((HERE / "students" / merges[arm]).read_text())
            assert mdoc["corpus_hash"] == corpus_hash, f"{merges[arm]}: corpus drift"
            for k, v in mdoc["outputs"].items():
                outs[k] = v
                merged_docs.append(k)
        n = len(units)
        route_hit, sv_recalls = 0, []
        tp = fp = fn = 0
        n_emitted = n_passing = 0
        n_parsed = 0
        toks, secs = [], []
        fail_reasons: dict[str, int] = {}
        per_doc = []
        for doc_id, content in units:
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
            # multiset intersection
            rest = list(skf)
            hit = 0
            for k in tk:
                if k in rest:
                    rest.remove(k)
                    hit += 1
            tp += hit
            fp += len(skf) - hit
            fn += len(tk) - hit
            per_doc.append({"doc": doc_id, "t_ops": len(t), "s_emitted": len(obj["ops"]) if parsed else None,
                            "s_passed": len(s), "parsed": parsed,
                            "route_hit": {x.get("target") for x in s} == {x.get("target") for x in t}})
        prec = tp / (tp + fp) if (tp + fp) else (1.0 if (tp + fn) == 0 else 0.0)
        rec = tp / (tp + fn) if (tp + fn) else 1.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        table.append({
            "arm": arm, "model_file": sdoc["model_file"], "n_docs": n,
            "merged_docs": merged_docs,
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
        })
    results = {"ts": now(), "corpus_hash": corpus_hash, "arms": table,
               "merges": merges}
    out_path.write_text(json.dumps(results, indent=1) + "\n")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with open(HERE / "logs" / f"score-{stamp}.jsonl", "w") as f:
        f.write(json.dumps({"ts": now(), "event": "score", "arms": [
            {k: v for k, v in a.items() if k != "per_doc"} for a in table]}) + "\n")
    print(f"{'arm':<10}{'route':>7}{'sv_rec':>8}{'op_f1':>7}{'parse':>7}{'proof':>7}{'tok/para':>9}{'s/para':>8}")
    for a in table:
        print(f"{a['arm']:<10}{a['routing_exact']:>7.3f}{a['subjval_recall']:>8.3f}"
              f"{a['op_f1']:>7.3f}{a['parse_rate']:>7.3f}{a['proof_pass_rate']:>7.3f}"
              f"{a['tokens_per_para']:>9.1f}{a['secs_per_para']:>8.2f}")


if __name__ == "__main__":
    sys.exit(main())
