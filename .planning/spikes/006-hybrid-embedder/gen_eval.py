"""Generation-retained: op emission under v0.2 Proof for mixed models (GPU).

Usage: gen_eval.py <run_name> <spec>
<spec> one of: minicpm_base | minicpm_lora:<adapter_dir> | qwen06_base |
qwen06_merged:<merged_dir>
Greedy HF decode (do_sample=False, max_new_tokens=1024) of the 20 spike-003
student prompts (INSTRUCTION bytes identical to 003's student.py), then
v0.2 resolve + spike-001 Proof against 003's teacher.json. Reports
routing_exact (target-set equality vs teacher, the 003 head-to-head metric),
parse_rate, Proof-pass rate, tokens/para. No llama-cpp grammar: adapters and
merged weights are HF-native with no GGUF path, so both sides (change on vs
off) run the same unconstrained decoder and Proof scores the difference.
GPU lock for generate; Proof on CPU. One model per process.
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

SPIKE003 = REPO / ".planning" / "spikes" / "003-op-emission-size-sweep"
sys.path.insert(0, str(SPIKE003))
sys.path.insert(0, str(REPO / ".planning" / "spikes" / "001-score-io-model"))
from common import FILE_SET, student_prompt  # noqa: E402 (read-only reuse)
import resolve as v02  # noqa: E402 (read-only reuse)
import ops_validate  # noqa: E402 (read-only reuse)

MINICPM = REPO / ".planning" / "spikes" / ".models" / "hf" / "openbmb__MiniCPM5-2B"
QWEN06 = REPO / ".planning" / "spikes" / ".models" / "hf" / "Qwen__Qwen3-0.6B"


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def norm(s):
    return " ".join(str(s).lower().split())


def main() -> None:
    run_name, spec = sys.argv[1:3]
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if spec == "minicpm_base":
        base_dir, adapter, label = MINICPM, None, "gen-minicpm-base"
    elif spec.startswith("minicpm_lora:"):
        base_dir, adapter = MINICPM, HERE / spec.split(":", 1)[1]
        label = f"gen-{adapter.name}"
    elif spec == "qwen06_base":
        base_dir, adapter, label = QWEN06, None, "gen-qwen06-base"
    elif spec.startswith("qwen06_merged:"):
        base_dir, adapter = HERE / spec.split(":", 1)[1], None
        label = f"gen-{Path(str(base_dir)).name}"
    else:
        raise SystemExit(f"unknown spec {spec}")
    base_dir = Path(str(base_dir))

    t0 = time.perf_counter()
    tok = AutoTokenizer.from_pretrained(str(base_dir), trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        str(base_dir), torch_dtype=torch.bfloat16,
        trust_remote_code=True).cuda().eval()
    if adapter is not None:
        from peft import PeftModel
        model = PeftModel.from_pretrained(
            model, str(adapter)).cuda().eval()
    load_s = time.perf_counter() - t0
    emit(run_name, "model_loaded", model=label, load_s=round(load_s, 2))

    teacher = json.loads((SPIKE003 / "teacher.json").read_text())
    assert teacher.get("schema") == "ops.v0.2"
    t_pass = {d: lab["ops"] for d, lab in teacher["labels"].items()}
    docs, corpus_hash = load_docs()
    assert teacher["corpus_hash"] == corpus_hash

    # Resume: greedy decoding is deterministic, so docs decoded in a killed
    # attempt are reloaded verbatim and skipped (logged as event=resumed).
    res_path = RESULTS / f"gen_{label}_{run_name}.json"
    outs = {}
    if res_path.exists():
        outs = json.loads(res_path.read_text()).get("outputs", {})
    docs = [(d, c) for d, c in docs if d not in outs]

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = HERE / "logs" / f"gen-{label}-{run_name}-{stamp}.jsonl"
    route_hit, n_emit, n_pass, n_parsed, toks = 0, 0, 0, 0, []
    # re-score resumed outputs so the summary covers all 20 docs
    all_docs, _ = load_docs()
    for doc_id, content in all_docs:
        if doc_id not in outs:
            continue
        o = outs[doc_id]
        toks.append(o["completion_tokens"])
        try:
            obj = json.loads(o["text"])
            parsed = (isinstance(obj, dict) and set(obj) == {"ops"}
                      and isinstance(obj["ops"], list))
        except Exception:  # noqa: BLE001
            parsed, obj = False, {"ops": []}
        n_parsed += parsed
        s = v02.validate_v02(obj, FILE_SET, content,
                             ops_validate)["passed"] if parsed else []
        n_emit += len(obj["ops"]) if parsed else 0
        n_pass += len(s)
        if {x.get("target") for x in s} == {x.get("target")
                                            for x in t_pass[doc_id]}:
            route_hit += 1
    with open(log_path, "w") as log:
        def ev(**f):
            log.write(json.dumps({"ts": now(), "arm": label, **f}) + "\n")
            log.flush()
        ev(event="load", seconds=round(load_s, 2))
        for doc_id, content in docs:
            prompt = student_prompt(content)
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
            else:
                s = []
            n_emit += len(obj["ops"]) if parsed else 0
            n_pass += len(s)
            toks.append(len(tok.encode(text)))
            outs[doc_id] = {"text": text, "seconds": round(dt, 2),
                            "completion_tokens": len(tok.encode(text))}
            if {x.get("target") for x in s} == {x.get("target")
                                                for x in t_pass[doc_id]}:
                route_hit += 1
            ev(event="decode", doc=doc_id, seconds=round(dt, 2),
               chars=len(text), parsed=parsed, passed=len(s),
               raw=text[:2000])
            (RESULTS / f"gen_{label}_{run_name}.json").write_text(
                json.dumps({"summary": {"arm": label, "partial": True,
                                        "n_docs_done": len(outs)},
                            "outputs": outs}) + "\n")
    n = 20
    summary = {"arm": label, "n_docs": n,
               "routing_exact": round(route_hit / n, 3),
               "parse_rate": round(n_parsed / n, 3),
               "proof_pass_rate": round(n_pass / n_emit, 3) if n_emit else 1.0,
               "n_emitted": n_emit, "n_passed": n_pass,
               "tokens_per_para": round(sum(toks) / n, 1),
               "secs_per_para": round(
                   sum(o["seconds"] for o in outs.values()) / n, 2)}
    (RESULTS / f"gen_{label}_{run_name}.json").write_text(
        json.dumps({"summary": summary, "outputs": outs}, indent=1) + "\n")
    emit(run_name, "gen_scored", **{k: v for k, v in summary.items()
                                    if k != "arm"}, arm=label)
    print(f"{label}: route={summary['routing_exact']} "
          f"parse={summary['parse_rate']} proof={summary['proof_pass_rate']} "
          f"({n_pass}/{n_emit}) tok/para={summary['tokens_per_para']} "
          f"s/para={summary['secs_per_para']}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
