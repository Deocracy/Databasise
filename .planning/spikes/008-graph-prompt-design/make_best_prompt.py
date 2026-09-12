"""Write results/best-prompt.md with the exact D1 prompt bytes (stdlib only)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "003-op-emission-size-sweep"))
from prompts import example_block, split_docs  # noqa: E402
from common import load_units  # noqa: E402

units, _ = load_units()
contents = dict(units)
ex, _ = split_docs()
doc = example_block(ex[0], contents)
lines = [
    "# Recommended prompt: D1 one-shot (spike 008)",
    "",
    "Winner on the pre-registered bar and the only winner that keeps the",
    "one-pass property (single decode under the v0.2 grammar). Numbers on",
    "the 16-doc scored set, Qwen3-4B Q8, raw completion, temp 0, seed 1234,",
    "cap 1024 (results.json): routing_exact 0.500 vs D0 0.375 (+0.125),",
    "Proof-pass 0.780 vs 0.360 (+0.420), evidence failures 22 vs 54,",
    "tokens/para 523.9 vs 353.6. On MiniCPM5-2B: routing 0.562 vs 0.500",
    "(+0.062, below the 0.10 bar but +3 on the 13 run-stable docs),",
    "Proof-pass 0.830 vs 0.754.",
    "",
    "Construction (prompts.py build_prompt('D1', ...)): 003 INSTRUCTION, then",
    "the block below (teacher ops for held-out example doc " + ex[0] + "),",
    "then the target section. D3 two-step scores higher on qwen4b (route",
    "0.562, proof 0.936) but needs two decodes and breaks the one-pass",
    "design; adopt only if accuracy outweighs the extra pass.",
    "",
    "## Prompt template",
    "",
    "<INSTRUCTION = spike-003 INSTRUCTION, byte-identical>",
    "",
    "Example:",
    "<example block below>",
    "",
    "Section:",
    "<section content>",
    "",
    "JSON:",
    "",
    "## Example block (held-out doc: " + ex[0] + ")",
    "",
    doc,
    "",
]
(HERE / "results").mkdir(exist_ok=True)
(HERE / "results" / "best-prompt.md").write_text("\n".join(lines))
print("wrote best-prompt.md", len("\n".join(lines)))
