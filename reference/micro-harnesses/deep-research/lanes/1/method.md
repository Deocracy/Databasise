# Lane 1 method

## Queries run

- arXiv API (`export.arxiv.org`, curl): `all:"GritLM"`, `all:"LLM2Vec"`,
  `all:"NV-Embed"`, `all:"echo embeddings improve"` — then blocked (empty
  responses/429), so all further verification used direct abs-page fetches.
- Direct abs-page fetches via curl (primary source, title/date/abstract/authors
  parsed from HTML): 2402.09906, 2404.05961, 2506.05176, 2405.17428, 2401.00368,
  2402.15449, 2403.20327, 2503.07891, 2509.20354, 2409.05152, 2402.18458,
  2307.16645, 2501.01028, 2402.03216, 2202.08904, 2212.03533, 2112.09118,
  2409.10173, 2501.03913 (negative: magnetron paper, id rejected),
  2311.00196 (negative: chemistry paper, id rejected), 2412.04506, 2603.10913.
  Two guessed ids were wrong and corrected via search (AnglE 2311.00196 ->
  2309.12871; NV-Embed 2405.17437 -> 2405.17428; Gecko 2310.12389 ->
  2403.20327; bge-multilingual-gemma2 2501.03913 rejected).
- Web search (secondary, discovery only; every discovery re-verified at abs page):
  Gecko arxiv id; EmbeddingGemma arxiv id (2509.20354); Gemini Embedding id
  (2503.07891); SFR-Embedding-Mistral (blog + HF only, no paper); BGE-M3 id;
  SGPT id + repo; OneGen paper + repo (zjunlp/OneGen); MetaEOL id + repo;
  PromptEOL id (2307.16645) + repo; Seed1.5/KaLM/Arctic (blog + ids);
  NV-Embed weights location (HF, no GitHub); KaLM repo; AnglE id + repo.
- Semantic Scholar API: attempted twice for citation chaining, both calls
  returned 429 (rate limit, no key) — forward-chaining not completed; noted as
  limitation. Compensated with venue/reference knowledge from opened papers
  (OneGen cites GritLM; MetaEOL compares LLM2Vec/Echo/PromptEOL; Qwen3 builds on
  GTE-Qwen; EmbeddingGemma builds on Gecko/Gemini/T5Gemma).
- GitHub API (stars, pushed_at, license, 2026-09-12): ContextualAI/gritlm,
  McGill-NLP/llm2vec, microsoft/unilm, FlagOpen/FlagEmbedding, Muennighoff/sgpt,
  QwenLM/Qwen3-Embedding, zjunlp/OneGen, HITsz-TMG/KaLM-Embedding,
  Yibin-Lei/MetaEOL, kongds/scaling_sentemb, facebookresearch/contriever,
  SeanLee97/AnglE, nvidia/NV-Embed (negative: not found), Salesforce search
  (negative: no official repo), echo search (negative: no official repo).
- Hugging Face API (license tags, downloads): nvidia/NV-Embed-v2
  (license:cc-by-nc-4.0), Qwen/Qwen3-Embedding-0.6B (apache-2.0),
  google/embeddinggemma-300m (gemma, gated), Salesforce/SFR-Embedding-Mistral,
  HIT-TMG/KaLM-embedding-multilingual-mini-instruct-v2.

## Sources used

arXiv abs pages + PDFs (primary, all admits); GitHub API + repo pages (primary
for code facts); Hugging Face API/model pages (primary for weights/license facts);
vendor blogs (Salesforce, ByteDance — secondary, abstains only); web search
snippets (discovery only, never cited as evidence).

## Counts

Screened 27 candidates (17 admit, 10 abstain, 0 refute-as-disposition; 3 refuting
observations recorded in findings from admitted sources). Refuted/abstained items
are cited in findings, nothing screened was dropped silently.

## What failed

- `export.arxiv.org` API returned empty/429 from this environment (curl and
  webfetch); worked around with per-page curl of `arxiv.org/abs/<id>`.
- Semantic Scholar API 429 without key: no systematic forward citation chaining;
  lane relies on reference lists observed in opened papers instead.
- Two arXiv ids recalled from memory were wrong (2405.17437, 2310.12389,
  2311.00196, 2501.03913-as-bge); all caught by opening the abs page and
  corrected or rejected — no recalled id was trusted.
- NV-Embed has no GitHub repo; SFR-Embedding-Mistral has no paper; Echo has no
  official code; MetaEOL/scaling_sentemb repos list no license — all recorded as
  found, not filled in.
