# Lane 4 method

Lane: hybrid models — one small model that embeds and generates (brief Q2).

## Queries and sources

- arXiv abs pages (primary verification for every admit: title, authors, submission
dates, abstract read from the fetched page). 27/27 admitted papers opened this way.
- arXiv export API (`export.arxiv.org/api/query`, Atom): used for `merging+embedding`
and `LM-Cocktail` / `Super Mario` / `RepLLaMA` / `LLaRA` searches. Became
rate-limited mid-session ("Rate exceeded", then empty/400 responses), so later
screening switched to `arxiv.org/abs/<id>` fetches and `arxiv.org/search` HTML for
two id corrections only.
- Semantic Scholar API (no key, 1–7 s spacing): forward-chained citations of
2402.09906 (GritLM, ~100 citing papers with arXiv ids mined for GEM, LLM2Vec-Gen,
GRC, Embedder's Dilemma, Giga-MoE, MidTokens, LayerDynamics, AttentionValues, EPIC)
and 2409.05152 (OneGen, 16 citing papers: RetroLLM, MAGNET, Hydra, UnifiedOnDevice).
One LLM2Vec-citation call hit HTTP 429 and was abandoned; GritLM/OneGen chains
already covered the lane. S2 search endpoint also 429'd once; abs-page verification
replaced it.
- GitHub API: repo verification for ContextualAI/gritlm, zjunlp/OneGen,
McGill-NLP/llm2vec, McGill-NLP/llm2vec-gen, Muennighoff/sgpt, arcee-ai/mergekit,
sunnynexus/RetroLLM (stars, pushed_at, license), plus search API for OneGen/LLM2Vec
correct orgs and for Hydra/MAGNET/GRC (no hits — recorded blank, not invented).
- Hugging Face API: `models?search=OneGen` confirmed vendor-reported zjunlp
checkpoints exist (download counts sighted, not recorded as claims).

## Counts

- Screened: 33 rows in inventory.tsv (27 papers + mergekit tool + 5 abstain misses).
- Admitted: 28 (27 papers, all with PDFs in papers/ verified to start with `%PDF`;
plus mergekit as a tool artefact, no PDF by rule).
- PDFs: 27 files, `<arxiv-id>_<Title_Slug>.pdf`, slug truncated to 70 chars.

## What failed

- export.arxiv.org throttling after ~6 rapid calls: switched to slower abs-page
fetches (6–8 s spacing), which held for the rest of the session.
- Four arXiv ids recalled from memory resolved to unrelated papers at the abs page
(QCD, phylogeny, Collatz, ColBERT analysis); corrected two via fresh search
(DARE=2311.03099, LM-Cocktail=2311.13534), left RepLLaMA/LLaRA unresolved.
- S2 citation call for LLM2Vec (2404.05961) returned 429; not retried, coverage came
from the GritLM/OneGen chains instead.
- No venue claims beyond what abs pages (no journal-ref shown) and repo tags
(EMNLP 2024, ACL 2025) support; no star counts, dates, or figures invented — every
number in inventory.tsv and findings.md traces to a fetched page noted in the row.
