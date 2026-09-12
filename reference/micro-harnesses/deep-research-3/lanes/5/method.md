# Lane 5 method

Lane: LoRA and PEFT science for forgetting and capacity (lane 5 of 10).

## Queries run

Web search (session provider), each 3-8 results, all 2026-09-12:
- "LoRA learns less and forgets less arXiv fine-tuning forgetting"
- "rsLoRA rank stabilization LoRA scaling factor alpha arXiv"
- "DoRA Weight-Decomposed Low-Rank Adaptation arXiv"
- "LoRA+ Efficient Low Rank Adaptation of Large Models differential learning rates arXiv"
- "PiSSA Principal Singular values and Singular vectors Adaptation arXiv"
- "AdaLoRA adaptive budget allocation parameter-efficient fine-tuning arXiv"
- "VeRA Vector-based Random Matrix Adaptation LoRA frozen random matrices arXiv 2310"
- "LoftQ LoRA-fine-tuning-aware quantization initialization arXiv"
- "QA-LoRA quantization-aware low-rank adaptation small language models arXiv"
- "O-LoRA orthogonal subspace continual learning large language models catastrophic forgetting arXiv"
- "ReLoRA high-rank training low-rank updates restarts arXiv"
- "GaLore memory-efficient LLM training gradient low-rank projection arXiv"
- "LoRA-Null null space initialization catastrophic forgetting arXiv 2025"
- "(IA)3 few-shot parameter-efficient fine-tuning learned vectors scaling activations arXiv Liu"
- "LoRA-FA memory-efficient low-rank adaptation freezing first matrix arXiv"
- "LQ-LoRA low-rank plus quantized matrix decomposition efficient language model finetuning arXiv"

Primary-source verification: every admitted id opened at
`https://arxiv.org/abs/<id>` via fetch (abs pages for 2106.09685, 2410.21228,
2602.06204, 2406.09044, 2504.01241) or via fetched full-page excerpts of the
abs/proceedings/HTML pages returned by search (all others). Venues taken only
from fetched pages (PMLR v235 for LoRA+/DoRA/GaLore; neurips.cc 2024 for
PiSSA, 2022 for (IA)3; ICLR virtual/poster pages for LoftQ/QA-LoRA/ReLoRA/LQ-LoRA;
ACL Anthology for O-LoRA/AFLoRA; AAAI 2026 proceedings pages for OPLoRA/LoRA-Null;
TMLR acceptance note for 2405.09673). Repos via GitHub REST API
(`repos/{owner}/{repo}` exact lookups; `/search/repositories` for discovery);
stars/pushed/license are 2026-09-12 point reads.

## Counts

Screened 32 rows (20 admit, 12 abstain). PDFs downloaded: 20, each verified to
start with `%PDF` and title-slugged to <=70 chars. No repositories cloned.

## What failed

- arXiv export API (`export.arxiv.org/api/query`): first "Rate exceeded", then
  a 120 s timeout even with backoff — abandoned; abs-page fetch + web search
  used instead. Consequence: no systematic listing sweeps; discovery ran
  through search-engine ranking, which biases toward highly cited work.
- Semantic Scholar API: HTTP 429 throughout — no citation-graph forward/backward
  chaining was possible. Forward chaining was partially replaced by following
  reference lists inside fetched HTML/PDF excerpts (e.g. OPLoRA's related-work
  section surfaced LoRA-Null and MiLoRA; VeRA's references confirmed LoRA-FA's id).
- Three recalled arXiv ids were wrong (2305.16605, 2402.10960, plus 2304.15033 /
  2309.14739 / 2306.08156 guesses corrected before opening). Each was checked
  at the abs page rather than trusted; the two opened wrong ones are logged as
  abstain probes in the inventory.
- GitHub code-search endpoint degraded mid-session (empty totals); repos for
  VeRA, LoRA-FA, LR-QAT, OPLoRA, muA, and the forgetting-law papers remain
  unverified. LoRA+ paper's repo URL failed to resolve.
- Papers with Code and Hugging Face Hub APIs were not queried (budget); HF peft
  docs were fetched once to confirm VeRA/(IA)3 implementation availability.
- 2025-onward coverage leans on search ranking, not listings; recent small
  workshops and non-arXiv venues (e.g. AFLoRA, LoRAF) stayed below the admit bar.
