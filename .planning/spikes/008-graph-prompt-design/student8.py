"""Student op emission for spike 008 (GPU process: run under flock).

Usage: student8.py <arm> [--units i,j,k]
  arm: minicpm2b | qwen4b

Loads the arm's GGUF once with full GPU offload (n_gpu_layers=-1, n_ctx=4096),
then decodes the SCORED docs under each of the 8 prompt designs (D0..D7) with
the v0.2 GBNF grammar, greedy (temperature 0, seed 1234), 1024-token cap, raw
completion -- exactly the spike-003 decode settings, so D0 must reproduce 003
on the scored subset. D3 is two-step: an entity list under the entity grammar
(cap 256) then ops with that list in context (cap 1024); combined completion
tokens and wall seconds are reported. Every output is scanned for think tags.
Appends JSON lines (ISO timestamps) to logs/student8-<arm>-<utc>.jsonl and
writes students/<DESIGN>_<arm>.json (same shape as spike-003 student files,
plus design/prompt metadata; D3 carries step1 text and combined usage).
"""

from __future__ import annotations

import datetime
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ARMS = {
    "minicpm2b": "MiniCPM5-2B-Q8_0.gguf",
    "qwen4b": "Qwen3-4B-Q8_0.gguf",
}

MAX_TOKENS = 1024
STEP1_TOKENS = 256
TEMPERATURE = 0.0
SEED = 1234
N_CTX = 4096


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main() -> None:
    import prompts
    from prompts import HERE, SPIKE003, split_docs
    sys.path.insert(0, str(SPIKE003))
    from common import load_units
    from v02_grammar import grammar_v02
    from llama_cpp import Llama, LlamaGrammar

    arm = sys.argv[1]
    assert arm in ARMS, f"unknown arm {arm}; choose from {sorted(ARMS)}"
    only: list[int] | None = None
    suffix = ""
    for a in sys.argv[2:]:
        if a.startswith("--units="):
            only = [int(x) for x in a.split("=", 1)[1].split(",") if x != ""]
        elif a.startswith("--suffix="):
            suffix = a.split("=", 1)[1]

    models_dir = __import__("os").environ.get(
        "MELODYSCRIBE_MODELS", str(HERE.parent / ".models"))
    units, corpus_hash = load_units()
    contents = dict(units)
    examples, scored = split_docs()
    if only is not None:
        scored = [scored[i] for i in only]

    ops_grammar = LlamaGrammar.from_string(grammar_v02(), verbose=False)
    ent_grammar = LlamaGrammar.from_string(prompts.entity_grammar(), verbose=False)

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = HERE / "logs" / f"student8-{arm}-{stamp}.jsonl"
    log_path.parent.mkdir(exist_ok=True)
    (HERE / "students").mkdir(exist_ok=True)

    t_load0 = time.perf_counter()
    llm = Llama(model_path=str(Path(models_dir) / ARMS[arm]),
                n_gpu_layers=-1, n_ctx=N_CTX, verbose=False)
    load_s = time.perf_counter() - t_load0

    def decode(prompt: str, grammar, max_tokens: int) -> tuple[str, dict, float]:
        t0 = time.perf_counter()
        res = llm.create_completion(prompt, grammar=grammar,
                                    max_tokens=max_tokens,
                                    temperature=TEMPERATURE, seed=SEED)
        dt = time.perf_counter() - t0
        text = res["choices"][0]["text"]
        return text, res.get("usage", {}), dt

    think_hits = 0
    files: dict[str, dict] = {}
    for d in prompts.DESIGNS:
        files[d] = {"arm": f"{d}_{arm}", "design": d, "model_file": ARMS[arm],
                    "corpus_hash": corpus_hash, "temperature": TEMPERATURE,
                    "seed": SEED, "max_tokens": MAX_TOKENS, "chat_template": False,
                    "grammar": "score-io-v0.2-spike003 file=graph,sql",
                    "schema": "ops.v0.2", "load_seconds": round(load_s, 2),
                    "example_docs": examples, "outputs": {}}
    with open(log_path, "w") as log:
        def emit(ev: dict):
            ev = {"ts": now(), "arm": arm, **ev}
            log.write(json.dumps(ev) + "\n")
            log.flush()

        emit({"event": "load", "model_file": ARMS[arm],
              "seconds": round(load_s, 2), "examples": examples,
              "scored": scored})

        # Determinism self-check: D0's first scored doc decoded twice.
        p0 = prompts.build_prompt("D0", contents[scored[0]], contents, examples)
        t_a, _, _ = decode(p0, ops_grammar, MAX_TOKENS)
        t_b, _, _ = decode(p0, ops_grammar, MAX_TOKENS)
        emit({"event": "determinism-check", "design": "D0", "doc": scored[0],
              "identical": t_a == t_b, "chars": len(t_a)})

        for doc_id in scored:
            content = contents[doc_id]
            for d in prompts.DESIGNS:
                if d == "D3":
                    p1 = prompts.d3_step1_prompt(content)
                    e_text, e_use, e_dt = decode(p1, ent_grammar, STEP1_TOKENS)
                    try:
                        entities = json.loads(e_text).get("entities")
                        entities = entities if isinstance(entities, list) else None
                    except Exception:
                        entities = None
                    p2 = prompts.d3_step2_prompt(content, entities)
                    text, use, dt = decode(p2, ops_grammar, MAX_TOKENS)
                    ctoks = (e_use.get("completion_tokens") or 0) + \
                        (use.get("completion_tokens") or 0)
                    secs = round(e_dt + dt, 2)
                    ptoks = (e_use.get("prompt_tokens") or 0) + \
                        (use.get("prompt_tokens") or 0)
                    extra = {"step1_text": e_text[:4000], "step1_entities": entities,
                             "step1_prompt_tokens": e_use.get("prompt_tokens"),
                             "step1_completion_tokens": e_use.get("completion_tokens")}
                else:
                    prompt = prompts.build_prompt(d, content, contents, examples)
                    text, use, dt = decode(prompt, ops_grammar, MAX_TOKENS)
                    ctoks = use.get("completion_tokens")
                    ptoks = use.get("prompt_tokens")
                    secs = round(dt, 2)
                    extra = {}
                think = "<think" in text.lower() or "<thinking" in text.lower()
                think_hits += bool(think)
                files[d]["outputs"][doc_id] = {
                    "text": text, "prompt_tokens": ptoks,
                    "completion_tokens": ctoks, "seconds": secs,
                    "think_tag": think, **extra,
                }
                emit({"event": "decode", "design": d, "doc": doc_id,
                      "seconds": secs, "prompt_tokens": ptoks,
                      "completion_tokens": ctoks, "chars": len(text),
                      "think_tag": think, "raw": text[:4000]})
    for d in prompts.DESIGNS:
        (HERE / "students" / f"{d}_{arm}{suffix}.json").write_text(
            json.dumps(files[d], indent=1) + "\n")
    print(f"arm={arm}{suffix} designs={len(prompts.DESIGNS)} docs={len(scored)} "
          f"think_hits={think_hits} log={log_path}")


if __name__ == "__main__":
    sys.exit(main())
