# Lane 4 method

Lane: Distillation and RL recipes on one consumer GPU (on-policy distillation, GKD,
MiniLLM, DistiLLM, sequence-level KD, rejection sampling, GRPO-family RLVR, validator-as-
reward, compute/model sizes/artefacts).

## Queries run

arXiv full-text search (via webfetch, `https://arxiv.org/search/?query=...&searchtype=all`),
one topic per call:
- `MiniLLM knowledge distillation large language models` → MiniLLM 2306.08543 (also
  surfaced X-KD 2602.12674 as a citer — screened, abstained)
- `"generalized knowledge distillation" language models on-policy` → GKD 2306.13649,
  LiteGUI 2605.07505, DP-OPD 2604.04461, AV-motion-planning GKD application 2604.07944
- `DistiLLM distillation language models` → DistiLLM 2402.03898, DistiLLM-2 2503.07067,
  Rank-DistiLLM 2405.07920
- `"group relative policy optimization" OR "GRPO" DeepSeekMath` → DeepSeekMath 2402.03300
  plus theory (2603.01162), alignment-objective note (2502.18548), application noise
- `DeepSeek-R1 incentivizing reasoning` → 23 results incl. R1 paper itself 2501.12948,
  PEFT-for-RLVR 2512.23165, 1-shot RLVR 2504.20571, RL-in-Name-Only 2505.13697,
  RLVR-Implicit 2506.14245, Verifier-Flaws 2502.00271, Tricks-or-Traps 2508.08221,
  LongWriter-Zero, HAPO, S-GRPO, ConciseR (last four abstained: wrong scale/scope)
- `DAPO reinforcement learning open source LLM` → DAPO 2503.14476 (+3 incidental)
- `Scaling Relationship Learning Mathematical Reasoning rejection sampling` → RFT
  2308.01825; `DeepScaleR democratizing reinforcement learning` → no results (DeepScaleR
  not admitted — id unverifiable from this path)
- `V-STaR verifier bootstrapping reasoning`, `VSTaR STaR verifier` → no results
- `ORPO monolithic preference optimization reference model` → timed out (abstained)
- `DeepSeekMath-V2`, `DeepSeek-Prover`, `SuperCorrect`, `SimPO/KTO/DPO/RLOO/ReMax/RLAIF`
  reached via follow-up title checks rather than fresh searches (see verification)

arXiv abs verification: every admitted id opened at `https://arxiv.org/abs/<id>` via curl;
title parsed from `<title>`, authors/date from `citation_author`/`citation_date` meta tags,
abstracts from `citation_abstract` where the search snippet did not already carry them.
Four guessed ids were *disproven* by abs fetch and recorded as abstains: 2312.06829
(≠ MiniLLM), 2404.10019 (≠ ORPO), 2310.05689 (≠ V-STaR), 2411.15134 (≠ Tulu 3),
2309.07487 (≠ RAFT), 2308.13267/2308.01825 confusion resolved to 2308.01825 (= RFT),
2405.21034 (≠ RLOO) resolved to 2402.14740, 2503.10874 (≠ DeepScaleR, dropped).

GitHub API (`api.github.com/repos/<owner>/<repo>`): stars, pushed_at, license,
description for jongwooko/distillm, Jiayi-Pan/TinyZero, volcengine/verl,
YangLing0818/SuperCorrect-llm, ypwang61/One-Shot-RLVR, huggingface/trl,
deepseek-ai/DeepSeek-R1, microsoft/LMOps, deepseek-ai/DeepSeek-Math,
huggingface/open-r1 (open-r1/open-r1 404 noted, correct org huggingface verified).
Hugging Face API for deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B (downloads/likes/license).

PDF download: `https://arxiv.org/pdf/<id>` via curl, 5 s spacing, `%PDF` magic + byte
size verified for all 26 files into `papers/`.

## Counts

Screened 47 (25 admitted papers + 1 refutation paper + 4 admitted code artefacts + 17
abstains). Per-lane minimums (≥20 screened, ≥8 admitted) exceeded.

## What failed

1. Semantic Scholar API: HTTP 429 on all query shapes from this egress (no key); not
   used. Forward-chaining via citations therefore replaced by arXiv "cites/baseline"
   discovery (X-KD citing GKD/MiniLLM; LiteGUI building on GKD+GRPO) — thinner than a
   true citation graph; flag to integrator.
2. `export.arxiv.org/api/query`: 429 via both curl and webfetch; id_list variant also
   429. Worked around with HTML abs fetches + meta-tag parsing.
3. arXiv serves curl a stripped abs variant (no Comments/journal-ref block regardless of
   User-Agent), so venue claims are restricted to what fetched snippets verified
   (MiniLLM/GKD/DistiLLM/DistiLLM-2/SuperCorrect/RFT venues; 1-shot RLVR via repo
   description); all other venues recorded as "arXiv preprint (venue not verified)"
   rather than recalled.
4. Four recalled arXiv ids were wrong (see above) — caught by abs-fetch discipline, none
   entered the inventory as admits.
5. No per-paper training-compute (GPU-hours) figures were recoverable from abstracts for
   most items; compute reporting is itself a gap (only relative claims: 4.3x speedup,
   46 percent memory, 10x faster student).
