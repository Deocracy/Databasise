"""Repeat probe for spike 008 (GPU process: run under flock).

Usage: probe_repeat.py <arm> <doc1,doc2,...>
  arm: minicpm2b | qwen4b

Loads the arm's GGUF once (same settings as student8.py) and re-decodes the
D0 prompt for the named docs exactly once each. Compares byte-for-byte with
students/D0_<arm>.json (this run) and spike-003 students/<arm>.json, logs both
comparisons plus the first-divergence offset, and writes
students/D0_<arm>_rep2.json. Purpose: measure run-to-run greedy-decode
agreement (the noise floor under every design delta).
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from student8 import ARMS, MAX_TOKENS, TEMPERATURE, SEED, N_CTX  # noqa: E402


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def first_div(a: str, b: str) -> int | None:
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return None if len(a) == len(b) else min(len(a), len(b))


def main() -> None:
    import prompts
    from prompts import HERE, SPIKE003, split_docs
    sys.path.insert(0, str(SPIKE003))
    from common import load_units
    from v02_grammar import grammar_v02
    from llama_cpp import Llama, LlamaGrammar

    arm = sys.argv[1]
    assert arm in ARMS, arm
    docs = sys.argv[2].split(",")
    models_dir = __import__("os").environ.get(
        "MELODYSCRIBE_MODELS", str(HERE.parent / ".models"))
    units, corpus_hash = load_units()
    contents = dict(units)
    examples, scored = split_docs()
    assert set(docs) <= set(scored), "probe only on scored docs"

    grammar = LlamaGrammar.from_string(grammar_v02(), verbose=False)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = HERE / "logs" / f"probe-repeat-{arm}-{stamp}.jsonl"
    log_path.parent.mkdir(exist_ok=True)
    (HERE / "students").mkdir(exist_ok=True)

    llm = Llama(model_path=str(Path(models_dir) / ARMS[arm]),
                n_gpu_layers=-1, n_ctx=N_CTX, verbose=False)
    cur = json.loads((HERE / "students" / f"D0_{arm}.json").read_text())
    old = json.loads((SPIKE003 / "students" / f"{arm}.json").read_text())
    assert cur["corpus_hash"] == corpus_hash == old["corpus_hash"]
    out = {"arm": f"D0_{arm}_rep2", "design": "D0-repeat", "model_file": ARMS[arm],
           "corpus_hash": corpus_hash, "temperature": TEMPERATURE, "seed": SEED,
           "max_tokens": MAX_TOKENS, "chat_template": False,
           "grammar": "score-io-v0.2-spike003 file=graph,sql",
           "schema": "ops.v0.2", "example_docs": examples, "outputs": {}}
    with open(log_path, "w") as log:
        def emit(ev: dict):
            ev = {"ts": now(), "arm": arm, **ev}
            log.write(json.dumps(ev) + "\n")
            log.flush()

        for doc_id in docs:
            prompt = prompts.build_prompt("D0", contents[doc_id], contents, examples)
            res = llm.create_completion(prompt, grammar=grammar,
                                        max_tokens=MAX_TOKENS,
                                        temperature=TEMPERATURE, seed=SEED)
            text = res["choices"][0]["text"]
            use = res.get("usage", {})
            out["outputs"][doc_id] = {
                "text": text, "prompt_tokens": use.get("prompt_tokens"),
                "completion_tokens": use.get("completion_tokens"), "think_tag": False}
            emit({"event": "repeat-decode", "doc": doc_id,
                  "eq_this_run": text == cur["outputs"][doc_id]["text"],
                  "eq_003": text == old["outputs"][doc_id]["text"],
                  "div_this_run": first_div(text, cur["outputs"][doc_id]["text"]),
                  "div_003": first_div(text, old["outputs"][doc_id]["text"]),
                  "chars": len(text),
                  "completion_tokens": use.get("completion_tokens"),
                  "raw": text[:4000]})
    (HERE / "students" / f"D0_{arm}_rep2.json").write_text(
        json.dumps(out, indent=1) + "\n")
    print(f"probe arm={arm} docs={len(docs)} log={log_path}")


if __name__ == "__main__":
    sys.exit(main())
