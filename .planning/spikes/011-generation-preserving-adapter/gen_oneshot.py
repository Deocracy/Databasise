"""One-shot op emission on the 5 TEST documents (GPU, train venv).

Usage: gen_oneshot.py <run_name> <spec>
<spec> one of: base | lora:<adapter_dir>
Greedy HF decode (do_sample=False, max_new_tokens=1024) of the spike-008
D1 one-shot prompt (INSTRUCTION + train-doc example block from opdata.py +
section + JSON marker; prompt truncation 3072) for the 5 queries-v1 test
documents only, then v0.2 resolve + spike-001 Proof against 003's
teacher.json. Metrics are 003's evaluate.py definitions restricted to the
5 test docs (routing_exact, subjval_recall, op_p/r/f1 over Proof-PASSING
ops only -- the KILT-gated joint metric: an op counts iff its quote is
verbatim AND it parses), plus parse_rate, Proof-pass, tokens per doc, and
the syntax-vs-grounding failure split:

  syntax:   schema, unparseable-output  (decoding-fixable per SynCode)
  grounding: evidence, value-type       (training-fixable: quotes, facts)

Writes results/oneshot_<label>_<run>.json. GPU lock for generate.
"""
from __future__ import annotations

import datetime
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data import HERE, REPO, load_docs  # noqa: E402
from common_eval import RESULTS, emit  # noqa: E402
from train_r import MODEL_DIR  # noqa: E402 (shared constants)
from opdata import load_teacher, oneshot_prompt, pick_example_doc  # noqa: E402

SPIKE003 = REPO / ".planning" / "spikes" / "003-op-emission-size-sweep"
sys.path.insert(0, str(SPIKE003))
sys.path.insert(0, str(REPO / ".planning" / "spikes" / "001-score-io-model"))
from common import FILE_SET  # noqa: E402 (read-only reuse)
import resolve as v02  # noqa: E402 (read-only reuse)
import ops_validate  # noqa: E402 (read-only reuse)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def norm(s):
    return " ".join(str(s).lower().split())


def subj_of(op):
    return op.get("s", op.get("subject", ""))


def pred_of(op):
    return op.get("p", op.get("attribute", ""))


def val_of(op):
    return op.get("o", op.get("value", ""))


def full_key(op):
    return (op.get("target"), norm(subj_of(op)), norm(pred_of(op)), norm(val_of(op)))


def sv_key(op):
    return (op.get("target"), norm(subj_of(op)), norm(val_of(op)))


SYNTAX_CATS = {"schema", "unparseable-output"}
GROUND_CATS = {"evidence", "value-type"}


def main() -> None:
    run_name, spec = sys.argv[1:3]
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if spec == "base":
        adapter, label = None, "oneshot-base"
    elif spec.startswith("lora:"):
        adapter = HERE / spec.split(":", 1)[1]
        label = f"oneshot-{adapter.name}"
    else:
        raise SystemExit(f"unknown spec {spec}")

    t0 = time.perf_counter()
    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR), trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        str(MODEL_DIR), torch_dtype=torch.bfloat16,
        trust_remote_code=True).cuda().eval()
    if adapter is not None:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, str(adapter)).cuda().eval()
    load_s = time.perf_counter() - t0
    emit(run_name, "model_loaded", model=label, load_s=round(load_s, 2))

    teacher, contents, corpus_hash = load_teacher()
    assert teacher["corpus_hash"] == corpus_hash
    t_pass = {d: lab["ops"] for d, lab in teacher["labels"].items()}
    example_doc = pick_example_doc(teacher)
    test_docs = ["conrad_brooks", "ed_wood_film", "meet_corliss_archer",
                 "shirley_temple", "woodson_arkansas"]
    assert example_doc not in test_docs

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = HERE / "logs" / f"{label}-{run_name}-{stamp}.jsonl"
    outs, toks = {}, []
    route_hit, sv_recalls = 0, []
    tp = fp = fn = 0
    n_emitted = n_passing = n_parsed = 0
    fail_reasons: dict[str, int] = {}
    with open(log_path, "w") as log:
        def ev(**f):
            log.write(json.dumps({"ts": now(), "arm": label, **f}) + "\n")
            log.flush()
        ev(event="load", seconds=round(load_s, 2), example_doc=example_doc)
        for doc_id in test_docs:
            content = contents[doc_id]
            prompt = oneshot_prompt(content, contents, example_doc)
            ids = tok(prompt, return_tensors="pt",
                      truncation=True, max_length=3072).to("cuda")
            t1 = time.perf_counter()
            with torch.no_grad():
                gen = model.generate(**ids, do_sample=False,
                                     max_new_tokens=1024,
                                     pad_token_id=tok.eos_token_id)
            dt = time.perf_counter() - t1
            text = tok.decode(gen[0][ids.input_ids.shape[1]:],
                              skip_special_tokens=True)
            try:
                obj = json.loads(text)
                parsed = (isinstance(obj, dict) and set(obj) == {"ops"}
                          and isinstance(obj["ops"], list))
            except Exception:  # noqa: BLE001
                parsed, obj = False, {"ops": []}
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
                s = []
                fail_reasons["unparseable-output"] = \
                    fail_reasons.get("unparseable-output", 0) + 1
            n_emitted += len(obj["ops"]) if parsed else 0
            n_passing += len(s)
            t = t_pass[doc_id]
            if {x.get("target") for x in s} == {x.get("target") for x in t}:
                route_hit += 1
            sk = {sv_key(x) for x in s}
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
            toks.append(len(tok.encode(text)))
            outs[doc_id] = {"text": text, "seconds": round(dt, 2),
                            "completion_tokens": len(tok.encode(text))}
            ev(event="decode", doc=doc_id, seconds=round(dt, 2),
               chars=len(text), parsed=parsed, passed=len(s),
               raw=text[:2000])
    n = len(test_docs)
    prec = tp / (tp + fp) if (tp + fp) else (1.0 if (tp + fn) == 0 else 0.0)
    rec = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    summary = {"arm": label, "n_docs": n, "example_doc": example_doc,
               "routing_exact": round(route_hit / n, 3),
               "subjval_recall": round(sum(sv_recalls) / n, 3),
               "op_p": round(prec, 3), "op_r": round(rec, 3),
               "op_f1": round(f1, 3),
               "parse_rate": round(n_parsed / n, 3),
               "proof_pass_rate": round(n_passing / n_emitted, 3) if n_emitted else 1.0,
               "n_emitted": n_emitted, "n_passed": n_passing,
               "fail_reasons": fail_reasons,
               "fail_syntax": sum(v for k, v in fail_reasons.items()
                                  if k in SYNTAX_CATS),
               "fail_grounding": sum(v for k, v in fail_reasons.items()
                                     if k in GROUND_CATS),
               "tokens_per_para": round(sum(toks) / n, 1),
               "secs_per_para": round(
                   sum(o["seconds"] for o in outs.values()) / n, 2)}
    (RESULTS / f"{label}_{run_name}.json").write_text(
        json.dumps({"summary": summary, "outputs": outs}, indent=1) + "\n")
    emit(run_name, "oneshot_scored",
         **{k: v for k, v in summary.items() if k != "arm"}, arm=label)
    print(f"{label}: route={summary['routing_exact']} "
          f"sv={summary['subjval_recall']} f1={summary['op_f1']} "
          f"parse={summary['parse_rate']} proof={summary['proof_pass_rate']} "
          f"({n_passing}/{n_emitted}) syn={summary['fail_syntax']} "
          f"grd={summary['fail_grounding']}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
