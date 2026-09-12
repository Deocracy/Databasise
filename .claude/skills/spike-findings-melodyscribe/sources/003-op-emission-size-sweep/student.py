"""Student op emission for spike 003 (GPU process: run under flock).

Usage: student.py <arm> [--units i,j,k] [--repeat N]
  arm: one of minicpm1b minicpm2b qwen1p7b qwen4b qwen8b

Loads the arm's GGUF once with full GPU offload, then decodes every unit
(same prompt bytes, same GBNF grammar from spike 001, temperature 0,
fixed seed) via the completion API -- no chat template, so Qwen3 thinking
has no trigger (verified: every output scanned for think tags). Records
per-unit: raw text, completion/prompt tokens from llama.cpp usage,
wall seconds, grammar used. Appends one JSON line per decode (ISO
timestamp) to logs/student-<arm>-<utc>.jsonl and writes
students/<arm>.json.
"""

from __future__ import annotations

import datetime
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ARMS = {
    "minicpm1b": "MiniCPM5-1B-Q8_0.gguf",
    "minicpm2b": "MiniCPM5-2B-Q8_0.gguf",
    "qwen1p7b": "Qwen3-1.7B-Q8_0.gguf",
    "qwen4b": "Qwen3-4B-Q8_0.gguf",
    "qwen8b": "Qwen3-8B-Q8_0.gguf",
}

MAX_TOKENS = 1024
TEMPERATURE = 0.0
SEED = 1234
N_CTX = 4096

def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main() -> None:
    from common import FILE_SET, HERE, load_units, student_prompt
    from v02_grammar import grammar_v02
    from llama_cpp import Llama, LlamaGrammar

    arm = sys.argv[1]
    assert arm in ARMS, f"unknown arm {arm}; choose from {sorted(ARMS)}"
    only: list[int] | None = None
    repeat = 1
    use_chat = False
    max_tokens = MAX_TOKENS
    out_name = arm
    for a in sys.argv[2:]:
        if a.startswith("--units="):
            only = [int(x) for x in a.split("=", 1)[1].split(",") if x != ""]
        elif a.startswith("--repeat="):
            repeat = int(a.split("=", 1)[1])
        elif a == "--chat":
            use_chat = True
            out_name = arm + "_chat"
        elif a.startswith("--max-tokens="):
            max_tokens = int(a.split("=", 1)[1])
        elif a.startswith("--out="):
            out_name = a.split("=", 1)[1]

    models_dir = __import__("os").environ.get("MELODYSCRIBE_MODELS",
                                              str(HERE.parent / ".models"))
    units, corpus_hash = load_units()
    if only is not None:
        units = [(units[i][0], units[i][1]) for i in only]

    grammar_text = grammar_v02()
    grammar = LlamaGrammar.from_string(grammar_text, verbose=False)

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = HERE / "logs" / f"student-{arm}-{stamp}.jsonl"
    log_path.parent.mkdir(exist_ok=True)
    (HERE / "students").mkdir(exist_ok=True)

    t_load0 = time.perf_counter()
    llm = Llama(model_path=str(Path(models_dir) / ARMS[arm]),
                n_gpu_layers=-1, n_ctx=N_CTX, verbose=False)
    load_s = time.perf_counter() - t_load0

    out: dict = {"arm": out_name, "model_file": ARMS[arm], "corpus_hash": corpus_hash,
                 "temperature": TEMPERATURE, "seed": SEED, "max_tokens": max_tokens,
                 "chat_template": use_chat,
                 "grammar": "score-io-v0.2-spike003 file=graph,sql",
                 "schema": "ops.v0.2",
                 "load_seconds": round(load_s, 2),
                 "outputs": {}}
    think_hits = 0
    with open(log_path, "w") as log:
        def emit(ev: dict):
            ev = {"ts": now(), "arm": out_name, **ev}
            log.write(json.dumps(ev) + "\n")
            log.flush()

        emit({"event": "load", "model_file": ARMS[arm], "seconds": round(load_s, 2)})
        for idx, (doc_id, content) in enumerate(units):
            prompt = student_prompt(content)
            for rep in range(repeat):
                t0 = time.perf_counter()
                if use_chat:
                    res = llm.create_chat_completion(
                        [{"role": "user", "content": prompt}],
                        grammar=grammar, max_tokens=max_tokens,
                        temperature=TEMPERATURE, seed=SEED)
                    text = res["choices"][0]["message"]["content"] or ""
                else:
                    res = llm.create_completion(prompt, grammar=grammar,
                                                max_tokens=max_tokens,
                                                temperature=TEMPERATURE, seed=SEED)
                    text = res["choices"][0]["text"]
                dt = time.perf_counter() - t0
                usage = res.get("usage", {})
                think = "<think" in text.lower() or "<thinking" in text.lower()
                think_hits += bool(think)
                key = doc_id if repeat == 1 else f"{doc_id}#r{rep}"
                out["outputs"][key] = {
                    "text": text,
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "seconds": round(dt, 2),
                    "think_tag": think,
                }
                emit({"event": "decode", "doc": doc_id, "rep": rep,
                      "seconds": round(dt, 2),
                      "prompt_tokens": usage.get("prompt_tokens"),
                      "completion_tokens": usage.get("completion_tokens"),
                      "chars": len(text), "think_tag": think,
                      "raw": text[:4000]})
    (HERE / "students" / f"{out_name}.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"arm={out_name} units={len(units)} repeat={repeat} think_hits={think_hits} log={log_path}")


if __name__ == "__main__":
    sys.exit(main())
