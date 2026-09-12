"""Spike 009 serving path 2: vLLM offline benchmark (only if install worked).

Uses safetensors weights under .models/hf with automatic prefix caching on.
Same ingest prompts (INSTRUCTION + section) so tok/s is comparable to the
llama.cpp scheduler arms. Emits one JSON object per line.
"""
from __future__ import annotations
import datetime
import json
import os
import sys
import time

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(D, "..", "003-op-emission-size-sweep"))
from common import load_units, student_prompt  # noqa: E402


def main() -> int:
    from vllm import LLM, SamplingParams  # noqa: E402
    log = open(os.path.join(D, "logs", "vllm.jsonl"), "w")

    def emit(**ev):
        ev = {"ts": datetime.datetime.now(
            datetime.timezone.utc).isoformat(), **ev}
        log.write(json.dumps(ev) + "\n")
        log.flush()

    units, chash = load_units()
    paras = []
    for doc_id, text in units:
        body = text.split("\n", 1)[1] if "\n" in text else text
        for p in [x.strip().replace("\n", " ") for x in body.split("\n\n")]:
            if len(p) >= 200:
                paras.append(p[:600])
                break
    prompts = [student_prompt(p) for p in paras[:8]]
    t0 = time.perf_counter()
    local = os.path.join(D, "..", ".models", "hf", "Qwen__Qwen3-1.7B")
    # enforce_eager: torch.compile/inductor needs /sbin/ldconfig, absent on
    # NixOS (see logs/vllm-run.err); eager is a legitimate serving mode.
    llm = LLM(model=local, enable_prefix_caching=True,
              gpu_memory_utilization=0.85, max_num_seqs=32,
              dtype="bfloat16", enforce_eager=True)
    emit(event="load", seconds=round(time.perf_counter() - t0, 3))
    sp = SamplingParams(temperature=0.0, max_tokens=48, seed=11)
    for N in (1, 8):
        reqs = [prompts[i % len(prompts)] for i in range(N)]
        t0 = time.perf_counter()
        outs = llm.generate(reqs, sp)
        wall = time.perf_counter() - t0
        pt = sum(len(o.prompt_token_ids) for o in outs)
        ct = sum(len(o.outputs[0].token_ids) for o in outs)
        emit(event="cell", N=N, wall_s=round(wall, 3),
             tok_per_s=round((pt + ct) / wall, 1),
             req_per_s=round(N / wall, 3))
    log.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
