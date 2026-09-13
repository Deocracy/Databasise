"""Bias probe for the template-bias control (GPU, train venv, tiny).

Usage: bias_probe.py <run_name>
Loads the MiniCPM5-2B base (no adapter) and encodes a few content-free
probes (empty string, blank, bare heading) each with the literal MARKER,
exactly like embed_untrained.py. The averaged vector is the marker-only
template bias subtracted by controls.py. Writes results/bias_<run>.json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_eval import RESULTS, emit  # noqa: E402
from train_r import MARKER, MODEL_DIR  # noqa: E402 (shared constants)

PROBES = ["", " ", "Paragraph:"]


def main() -> None:
    run_name = sys.argv[1]
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t0 = time.perf_counter()
    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR), trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        str(MODEL_DIR), torch_dtype=torch.bfloat16,
        trust_remote_code=True).cuda().eval()
    load_s = time.perf_counter() - t0
    emit(run_name, "model_loaded", model="MiniCPM5-2B-bias-probe",
         load_s=round(load_s, 2))

    vecs = []
    with torch.no_grad():
        for t in PROBES:
            ids = tok(t + MARKER, return_tensors="pt",
                      truncation=True, max_length=512).to("cuda")
            h = model(**ids, output_hidden_states=True).hidden_states[-1]
            v = h[0, -1, :].float()
            vecs.append((v / v.norm()).tolist())
    out = {"probes": PROBES, "vecs": vecs}
    (RESULTS / f"bias_{run_name}.json").write_text(json.dumps(out) + "\n")
    emit(run_name, "bias_probed", n=len(PROBES))
    print(f"bias probe done: {len(PROBES)} probes load={load_s:.1f}s", flush=True)


if __name__ == "__main__":
    sys.exit(main())
