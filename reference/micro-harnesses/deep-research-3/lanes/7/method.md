# Lane 7 method

## Queries run

Web-search queries (each returned up to 8 results; all findings verified at primary
sources afterwards, never cited from snippets):

- MiniCPM arXiv technical report small language model 2024 2025
- Qwen3 technical report arXiv 2025 post-training SFT RL
- SmolLM3 arXiv technical report post-training SFT DPO 2025
- Phi-4-mini technical report arXiv Microsoft small model post-training
- Gemma 3 technical report arXiv 2025 post-training distillation RL
- LFM2 Liquid AI technical report arXiv hybrid small model post-training
- IBM Granite 3.0 small language models technical report arXiv post-training
- MiniCPM3 4B arXiv technical report 2024 scaling law SFT
- SmolLM2 technical report arXiv 2025 post-training SFT DPO data mixture
- SmolTulu Tulu small model post-training replication arXiv
- Anchored Preference Optimization APO arXiv small language model
- Phi-4 technical report arXiv 2412.08905 synthetic data post-training
- Qwen2.5 technical report arXiv post-training 18T tokens small model
- Gemma 2 technical report arXiv 2408.00118 distillation post-training
- Granite 4.0 small language models IBM 2025 technical report hybrid

Primary-source fetches:

- arXiv abs pages for 15 ids (title/authors/date/subject via citation meta tags).
- arXiv PDFs for all 15 admitted papers, each verified to start with `%PDF`.
- GitHub API for 10 repos (stars, pushed_at, license): OpenBMB/MiniCPM,
  huggingface/alignment-handbook, huggingface/smollm, QwenLM/Qwen3,
  allenai/open-instruct, ibm-granite/granite-3.0-language-models,
  ibm-granite/granite-4.0-language-models,
  ibm-granite/granite-4.0-nano-language-models, google-deepmind/gemma,
  huggingface/smol-course.
- Raw recipe configs: alignment-handbook `recipes/smollm3/sft/sft.yaml`,
  `recipes/smollm3/dpo/apo.yaml`, `recipes/smollm2/sft/config.yaml` (LR, scheduler,
  epochs, batch fields extracted by grep).
- Hugging Face API for 11 weight cards (license, gated, downloads), which fixed
  the Gemma (custom), Phi (MIT), Granite/Qwen/SmolLM (Apache-2.0), LFM2 (custom),
  Tulu-3 stages (Llama-3.1) licenses.
- Repo/blog pages: OpenBMB/MiniCPM README (MiniCPM5-1B release notes),
  SmolLM3 HF blog, Granite 3.0/4.0 READMEs and IBM docs, SmolTulu HF model pages.

Forward/backward chaining: citations were followed from Qwen3 (GRPO, QwQ-32B),
SmolLM3 (APO paper, Tulu-3 preferences), Tulu 3 (DPO, RLVR lineage), and APO
(DPO/KTO comparisons), which surfaced the APO-hinge-zero follow-up and the
SmolTulu replication. Papers-with-Code entries were used only to confirm arXiv
ids, not as evidence.

## Counts

Screened 24 candidates (inventory.tsv rows). Admitted 18 (15 arXiv papers with
PDFs in papers/, plus the SmolLM3 recipe configs, Granite 3.0, and Granite 4.0 via
repos/docs). Abstained 5, refuted 1 (the brief's MiniCPM5-2B size label). Lane
minimums (20 screened / 8 admitted) are met.

## What failed

- arXiv export API (`export.arxiv.org/api/query`) returned `Rate exceeded` on the
  first call, so systematic listing searches were abandoned in favor of abs-page
  fetches plus web search; 2025-onwards items were still all verified on fetched
  pages, satisfying the recency rule.
- `QwenLM/Qwen2.5` resolves to HTTP 301 on the GitHub API (renamed/redirected), so
  no repo facts are asserted for Qwen2.5; the paper PDF is the evidence.
- `microsoft/phi-cookbook`, `LiquidAI/LFM2`, `allenai/tulu-v3`, `SultanR/SmolTulu`
  repos do not exist (API 404); no repo facts asserted for Phi, LFM2, or SmolTulu.
- `HuggingFaceTB/smollm3-3B` 404s on the HF API (canonical id is
  `HuggingFaceTB/SmolLM3-3B`, verified instead with 586912 downloads).
- No standalone recipe document exists for MiniCPM5-1B, MiniCPM3-4B, or the
  LFM2-Nanos; all three were abstained rather than padded from secondary sources.
- Star counts and push dates are point-in-time (2026-09-12) and will drift;
  license strings are per-artefact (repo vs weights) and recorded separately where
  they differ.
