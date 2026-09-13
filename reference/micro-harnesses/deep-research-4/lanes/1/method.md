# Lane 1 method

## Sources used (authority order per brief)

1. arXiv abs pages via web fetch (primary for papers): 20 ids opened and confirmed title/authors/date/abstract.
2. PMLR proceedings page for BFCL (https://proceedings.mlr.press/v267/patil25a.html ) plus OpenReview record.
3. GitHub REST API (`api.github.com/repos/{owner}/{repo}`) for stars, pushed_at, license, description (primary for artefacts).
4. Raw GitHub file fetches: `tools/server/README.md` of llama.cpp (tool-use plus --grammar plus json_schema lines grepped),
   smolagents README head, SqueezeAILab/TinyAgent README page (citation block giving the true TinyAgent id 2409.00608).
5. Hugging Face Hub API (`huggingface.co/api/models`) for xLAM search, SmolLM3-3B record, LiquidAI context.
6. Vendor pages via web search/fetch, labelled secondary: HF SmolLM3 blog, Google Gemma 3n docs, FunctionGemma blog plus
   model card, Liquid tool-use docs, OpenBMB repo README. Used only for screening/abstain reasons, never for admits,
   except where a repo artefact itself is primary (GitHub API/README).
7. Web search (session provider) to discover true ids after three recalled ids failed verification, and to confirm
   2025-era items (MiniCPM4 2506.07900, Phi-4-mini 2503.01743, Apple 2407.21075, Hammer 2410.04587, Octopus v4 2404.19296,
   LFM2 2511.23404, APIGen 2406.18518, BFCL PMLR record).

## Queries run

- arXiv abs verification (20): 2210.03629, 2302.04761, 2305.15334, 2305.18323, 2306.05301, 2307.16789, 2312.04511,
  2312.07104, 2404.01744, 2404.06395, 2404.11459, 2404.19296, 2406.18518, 2407.21075, 2409.00608, 2409.03215, 2410.04587,
  2503.01743, 2506.07900, 2511.23404.
- Failed verifications (3 recalled ids, now abstain rows): 2409.13324 (black-hole paper), 2406.03600 (legal-LLM paper),
  2311.05390 (exomoon paper).
- GitHub API repo checks (12): SqueezeAILab/TinyAgent, SqueezeAILab/LLMCompiler, OpenBMB/MiniCPM, ggml-org/llama.cpp,
  huggingface/smolagents, sgl-project/sglang, MadeAgents/Hammer, NexaAI/octopus-v4 (404), ShishirPatil/gorilla,
  nexusflowai/NexusRaven, nexusflowai/NexusRaven-V2, huggingface/smollm; plus org search `org:OpenBMB MCP`
  (returned UltraRAG only) and code search (401, unused).
- HF API (3): models search `xLAM-function-calling`, model record `HuggingFaceTB/SmolLM3-3B`, org context LiquidAI.
- Web searches (8): APIGen Salesforce; NexusRaven; MiniCPM4; SmolLM3; Phi-4-mini; BFCL; Hammer MadeAgents;
  Octopus v4; Apple foundation models; LFM2; Gemma 3n FunctionGemma.

## Screening counts

- Screened: 41 candidates (21 papers incl. BFCL, 20 repo/artefact/doc candidates).
- Admitted: 30 (20 arXiv papers with PDFs, BFCL PMLR paper with PDF, 9 repo artefacts without PDF).
- Abstain: 11 (3 wrong recalled ids, 8 unverifiable/secondary-only/unclear-license).
- Refute: 0 formal refutations; 2 vendor-claim cautions recorded in findings.

## Failures and deviations

- `export.arxiv.org` API and Semantic Scholar API both rate-limited (429/503); no listing/citation-chaining via API.
  Substituted web search plus direct abs-page fetches; every admit still opened at its primary source.
- `papers/` naming: 20 files follow `<arxiv-id>_<Title_Slug>.pdf` (slug truncated, no spaces, %PDF verified via
  `head -c 4`). The BFCL paper has no arXiv id, so it is filed as
  `BFCL_The_Berkeley_Function_Calling_Leaderboard_ICML2025.pdf` (PMLR PDF, %PDF verified) — documented deviation.
- Repo artefacts have no PDF by nature; recorded by URL plus API facts in inventory.tsv.
- Capability column mapping (brief says 1-5; section-1 stores do not fit this lane): 1 = ingest routing/constrained
  emission, 2 = recall/fusion, 3 = thinking control, 4 = caching/parallel/scheduling, 5 = real-time co-processor and
  harness boundaries.
- No repositories cloned; only commit-independent facts (stars, push date, license, description) recorded.
- Everything fetched treated as data; no fetched page contained actionable instructions relevant to this lane.
