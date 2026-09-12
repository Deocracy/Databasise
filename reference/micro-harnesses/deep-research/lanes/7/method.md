# Lane 7 method

## Queries run

- arXiv API (`export.arxiv.org/api/query`), `ti:`-scoped: MiniLLM, DistiLLM,
  FrugalGPT, RouteLLM, LoRA+low-rank, QLoRA, XGrammar, Outlines, SGLang,
  Toolformer (blocked), RA-DIT (blocked), plus `all:`-scoped: distilling
  step-by-step, on-policy distillation, generalized knowledge distillation,
  constrained decoding, structured generation+LLM, sequence-level distillation,
  self-MoA, CAPA, function-calling+small, DoRA, Orca. Quoted multi-word
  `all:"..."` queries returned zero rows (phrase semantics too strict) and were
  replaced by `ti:`/`AND` queries. After ~21 calls the arXiv API returned
  HTTP 429 for the session IP; remaining verification moved to `arxiv.org/abs`
  pages via curl (worked) and OpenAlex (worked).
- OpenAlex API (`api.openalex.org/works?search=...`), 1s pacing, ~50 title
  queries across distillation, routing, adapters, constrained decoding,
  function calling, and small-model reports. Used for id resolution and
  citation counts. Two script batches crashed partway on `primary_location:
  null` records (fixed with a guard); no data was fabricated for the skipped
  entries — affected queries were re-covered by abs-page fetches.
- Semantic Scholar API: fully rate-limited (HTTP 429 on every call from this
  IP, even at 4s pacing). No S2 data used.
- GitHub REST API (`api.github.com/repos/...`): verified dottxt-ai/outlines
  (15785 stars, pushed 2026-09-09, Apache-2.0), mlc-ai/xgrammar (1881 stars,
  pushed 2026-09-11, Apache-2.0), sgl-project/sglang (35835 stars, pushed
  2026-09-12, Apache-2.0); then hour-rate-limited. Fallback: repo existence
  via `raw.githubusercontent.com/<owner>/<repo>/main|master/README.md`
  (HTTP 200 + byte size) for gorilla, RouteLLM, MoA, outlines, xgrammar,
  sglang, llama.cpp; repo homepages via `github.com` HTML for description
  confirmation. Stars/push/license for the four non-API repos are recorded as
  unknown, not estimated.
- Hugging Face API (`huggingface.co/api/models?search=...`): verified
  microsoft/Phi-3-mini-4k-instruct (439,652 downloads), ibm-granite org
  models, MiniLLM org models (MiniPLM-Qwen), xlam-function-calling-60k dataset
  tag reference, third-party ToolACE/Granite derivatives.
- Papers with Code: not queried (no lane-7-specific need beyond what arXiv +
  repos covered).
- Forward/backward chaining: citation chaining via S2 was impossible
  (rate-limited); chaining was approximated with OpenAlex `cited_by_count` and
  related-work overlap across the verified set, plus arXiv listing pages that
  surfaced the 2025–2026 constrained-decoding cluster (JSONSchemaBench,
  Repair-Not-Improvement, Where-vs-What, Guided-Decoding-in-RAG, XGrammar-2
  sighted but not admitted).

## Counts

Screened: 45 rows in `inventory.tsv` (36 verified admits/refutes, 9 abstains).
Admitted papers with PDFs in `papers/`: 35 (34 arXiv + 1 ACL Anthology).
Code-only admit: 1 (llama.cpp, no PDF). Minimums met: ≥20 screened, ≥8
admitted. Recall-to-primary correction rate: 8 brief/recall ids were wrong on
fetch and were corrected or abstained (see ledger); no recalled id was trusted
without fetching.

## What failed

1. Semantic Scholar: 100% HTTP 429, abandoned.
2. arXiv API: HTTP 429 after ~21 queries; worked around via abs pages + OpenAlex.
3. GitHub API: hour quota exhausted after 3 successful repo calls; worked around
   via README/descriptions; 4 repos lack star counts.
4. `raw_oa*.jsonl` / `raw_ax.json` / `raw_s2.json` / `verified.json` scratch
   files in the lane folder document the raw search trail.
5. XGrammar-2 (arXiv:2601.04426) and Trie-Automata constrained decoding
   (arXiv:2608.12574) were sighted in listings but not verified/admitted for
   time reasons — recommended first additions on a refresh pass.
6. LoRA-vs-full at exactly 2B scale: no study found at that precise scale;
   the lane reports the nearest verified evidence (Biderman et al. 2024;
   Zheng et al. 2026) and marks the 2B-specific gap explicitly.
