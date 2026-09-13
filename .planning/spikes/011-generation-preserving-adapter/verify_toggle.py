"""Toggle check: adapter-disabled forward equals pure base (GPU, train venv).

Usage: verify_toggle.py <run_name> <adapter_dir>
Loads the pure MiniCPM5-2B base AND base + adapter in one process, then on
one fixed 003 student prompt compares:
  (a) max abs logit diff between pure base and adapter-disabled forward
      (expect exactly 0.0: Hydra-style byte recovery), and
  (b) greedy 64-token continuations for pure base, adapter-disabled, and
      adapter-enabled (expect base == disabled, enabled differs).
Writes results/toggle_<run>.json. Arm T (toggle) reuses base generation
numbers iff (a) is 0.0 and (b) holds on every probe.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_eval import RESULTS, emit  # noqa: E402
from train_r import MODEL_DIR  # noqa: E402 (shared constants)
from data import load_docs  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent
                       / "003-op-emission-size-sweep"))
from common import student_prompt  # noqa: E402 (spike 003, read-only)


def main() -> None:
    run_name, adapter = sys.argv[1:3]
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR), trust_remote_code=True)
    docs, _ = load_docs()
    prompt = student_prompt(dict(docs)["janet_waldo"])[:1500]
    ids = tok(prompt, return_tensors="pt",
              truncation=True, max_length=512).to("cuda")

    pure = AutoModelForCausalLM.from_pretrained(
        str(MODEL_DIR), torch_dtype=torch.bfloat16,
        trust_remote_code=True).cuda().eval()
    adapted = PeftModel.from_pretrained(
        AutoModelForCausalLM.from_pretrained(
            str(MODEL_DIR), torch_dtype=torch.bfloat16,
            trust_remote_code=True).cuda().eval(),
        str(Path(__file__).resolve().parent / adapter)).cuda().eval()

    def greedy_cont(model, n=64):
        with torch.no_grad():
            gen = model.generate(**ids, do_sample=False, max_new_tokens=n,
                                 pad_token_id=tok.eos_token_id)
        return tok.decode(gen[0][ids.input_ids.shape[1]:],
                          skip_special_tokens=True)

    with torch.no_grad():
        lp = pure(input_ids=ids.input_ids,
                  attention_mask=ids.attention_mask).logits.float()
        with adapted.disable_adapter():
            ld = adapted(input_ids=ids.input_ids,
                         attention_mask=ids.attention_mask).logits.float()
        la = adapted(input_ids=ids.input_ids,
                     attention_mask=ids.attention_mask).logits.float()
    maxdiff_disabled = (lp - ld).abs().max().item()
    maxdiff_enabled = (lp - la).abs().max().item()
    t_pure = greedy_cont(pure)
    with adapted.disable_adapter():
        t_dis = greedy_cont(adapted)
    t_en = greedy_cont(adapted)
    out = {"adapter": adapter,
           "logit_maxabsdiff_disabled_vs_pure": maxdiff_disabled,
           "logit_maxabsdiff_enabled_vs_pure": maxdiff_enabled,
           "greedy_eq_disabled_vs_pure": t_dis == t_pure,
           "greedy_enabled_differs": t_en != t_pure,
           "samples": {"pure": t_pure[:300], "disabled": t_dis[:300],
                       "enabled": t_en[:300]}}
    (RESULTS / f"toggle_{run_name}.json").write_text(
        json.dumps(out, indent=1) + "\n")
    emit(run_name, "toggle_checked", adapter=adapter,
         maxdiff_disabled=maxdiff_disabled, eq=out["greedy_eq_disabled_vs_pure"],
         differs=out["greedy_enabled_differs"])
    print(f"toggle: maxdiff_disabled={maxdiff_disabled} "
          f"eq={out['greedy_eq_disabled_vs_pure']} "
          f"differs={out['greedy_enabled_differs']}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
