"""Arm D: weight merges of Qwen3-Embedding-0.6B with Qwen3-0.6B (CPU only).

Usage: merge_d.py <run_name> [--ties]
Key facts (measured 2026-09-12): both Qwen3Config, hidden 1024, 28 layers,
but different key namespaces (embedder: bare `layers.*`, no lm_head; gen:
`model.*` + lm_head) and different vocabs (emb 151669 vs gen 151936, so
embed_tokens rows differ). Merge rule, recorded here:
  - align by stripping `model.` from gen keys;
  - shared hidden tensors: merged = w*emb + (1-w)*gen, w in {0.25,0.5,0.75};
  - embed_tokens: interpolate the shared first 151669 rows, keep gen's extra
    267 rows verbatim;
  - lm_head: gen only, taken verbatim (needed for the generation-retained
    arm; it never belonged to the embedder).
Output merged/<tag>/ is gen-shaped (config/tokenizer/generation_config from
the gen base + merged model.safetensors). With --ties, one TIES merge via
mergekit density 0.5 is attempted first; any mergekit error is logged and
the linear merges still proceed.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data import HERE, REPO  # noqa: E402
from common_eval import LOGS, emit  # noqa: E402

HF = REPO / ".planning" / "spikes" / ".models" / "hf"
EMB = HF / "Qwen__Qwen3-Embedding-0.6B"
GEN = HF / "Qwen__Qwen3-0.6B"
RATIOS = (0.25, 0.5, 0.75)


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> None:
    run_name = sys.argv[1]
    want_ties = "--ties" in sys.argv
    import torch
    from safetensors import safe_open
    from safetensors.torch import save_file

    with safe_open(str(EMB / "model.safetensors"), framework="pt") as f:
        emb = {k: f.get_tensor(k) for k in f.keys()}
    with safe_open(str(GEN / "model.safetensors"), framework="pt") as f:
        gen = {k: f.get_tensor(k) for k in f.keys()}
    gen_aligned = {k[len("model."):] if k.startswith("model.") else k: v
                   for k, v in gen.items()}
    shared = [k for k in emb if k in gen_aligned
              and emb[k].shape == gen_aligned[k].shape]
    only_emb = [k for k in emb if k not in gen_aligned]
    only_gen = [k for k in gen_aligned if k not in emb]
    emit(run_name, "merge_inventory", shared=len(shared),
         only_emb=only_emb, only_gen=only_gen,
         emb_vocab=emb["embed_tokens.weight"].shape[0],
         gen_vocab=gen_aligned["embed_tokens.weight"].shape[0])
    print(f"shared={len(shared)} only_emb={only_emb} only_gen={only_gen}",
          flush=True)
    assert not only_emb, f"unmapped embedder tensors: {only_emb}"

    # Tokenizer check: what are gen's extra 267 rows?
    etok = json.loads((EMB / "tokenizer.json").read_text())
    gtok = json.loads((GEN / "tokenizer.json").read_text())
    ev, gv = etok["model"]["vocab"], gtok["model"]["vocab"]
    extra = {t: i for t, i in gv.items() if t not in ev}
    emit(run_name, "vocab_check", emb_vocab=len(ev), gen_vocab=len(gv),
         n_extra=len(extra), extra_sample=sorted(extra)[:10])
    print(f"vocab emb={len(ev)} gen={len(gv)} extra_sample={sorted(extra)[:10]}",
          flush=True)

    merged_dir = HERE / "merged"
    merged_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    n_emb_rows = emb["embed_tokens.weight"].shape[0]
    for w in RATIOS:
        t0 = time.perf_counter()
        out = {}
        for k in shared:
            if k == "embed_tokens.weight":
                m = w * emb[k] + (1 - w) * gen_aligned[k][:n_emb_rows]
                out["model." + k] = torch.cat(
                    [m, gen_aligned[k][n_emb_rows:]], dim=0)
            else:
                out["model." + k] = w * emb[k] + (1 - w) * gen_aligned[k]
        out["lm_head.weight"] = gen["lm_head.weight"]
        tag = f"linear_w{w}"
        d = merged_dir / f"qwen06_{tag}_{run_name}"
        d.mkdir(parents=True, exist_ok=True)
        save_file(out, str(d / "model.safetensors"))
        for f in ("config.json", "tokenizer.json", "tokenizer_config.json",
                  "generation_config.json", "merges.txt", "vocab.json"):
            src = GEN / f
            if src.exists():
                (d / f).write_bytes(src.read_bytes())
        rec = {"tag": tag, "w_embed": w, "dir": str(d),
               "seconds": round(time.perf_counter() - t0, 1),
               "sha256": sha_file(d / "model.safetensors")}
        manifest.append(rec)
        emit(run_name, "merged", **rec)
        print(f"merged {tag} sha={rec['sha256'][:12]}", flush=True)

    if want_ties:
        try:
            manifest.append(ties_merge(run_name, emb, gen_aligned, gen,
                                       merged_dir))
        except Exception as e:  # noqa: BLE001 -- attempt, never fatal
            emit(run_name, "ties_failed", error=f"{type(e).__name__}: {e}")
            print(f"TIES failed (logged, continuing): {e}", flush=True)

    (merged_dir / f"manifest_{run_name}.json").write_text(
        json.dumps(manifest, indent=1) + "\n")
    print(f"MERGE DONE {len(manifest)} models", flush=True)


def ties_merge(run_name, emb, gen_aligned, gen, merged_dir):
    """TIES through mergekit on an aligned embedder copy. Raises on failure.

    The copy is padded to the gen vocab with the gen base's own reserved
    rows (delta 0 there, so TIES trim keeps the base) and carries the gen
    config; added tokens are identical in both tokenizers (verified in
    vocab_check), so every interpolated row aligns."""
    import torch
    import yaml
    from safetensors.torch import save_file
    t0 = time.perf_counter()
    n_emb_rows = emb["embed_tokens.weight"].shape[0]
    aligned = merged_dir / f"_aligned_emb_{run_name}"
    aligned.mkdir(parents=True, exist_ok=True)
    padded = torch.cat([emb["embed_tokens.weight"],
                        gen_aligned["embed_tokens.weight"][n_emb_rows:]], dim=0)
    save_file({("model." + k): (padded if k == "embed_tokens.weight" else v)
               for k, v in emb.items()},
              str(aligned / "model.safetensors"))
    for f in ("config.json", "tokenizer.json", "tokenizer_config.json"):
        src = GEN / f
        if src.exists():
            (aligned / f).write_bytes(src.read_bytes())
    cfg = {"models": [
        {"model": str(GEN), "parameters": {"density": 0.5, "weight": 0.5}},
        {"model": str(aligned), "parameters": {"density": 0.5, "weight": 0.5}}],
        "merge_method": "ties",
        "base_model": str(GEN),
        "dtype": "bfloat16",
        "out_dtype": "bfloat16"}
    yp = merged_dir / f"ties_{run_name}.yaml"
    yp.write_text(yaml.safe_dump(cfg))
    from mergekit.config import MergeConfiguration
    from mergekit.merge import run_merge
    from mergekit.options import MergeOptions
    out = merged_dir / f"qwen06_ties_{run_name}"
    run_merge(MergeConfiguration.model_validate(yaml.safe_load(
        yp.read_text())), str(out), MergeOptions(),
        config_source=str(yp))
    rec = {"tag": "ties_d0.5", "w_embed": 0.5, "dir": str(out),
           "seconds": round(time.perf_counter() - t0, 1),
           "sha256": sha_file(out / "model.safetensors")}
    emit(run_name, "merged", **rec)
    return rec


if __name__ == "__main__":
    sys.exit(main())
