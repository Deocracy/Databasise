# Lane 1 method: Embedding model architectures

## Queries run (arXiv export API, Atom)

- `ti:"Repeat After Me"` — 3 results, all unrelated (established the remembered
  title was wrong; led to the correct query below).
- `ti:"Repetition Improves Language Model Embeddings"` — 1 result: 2402.15449
  (echo embeddings). Admitted.
- `ti:"Massive Multilingual Text Embedding Benchmark"` — 1 result: 2502.13595
  (MMTEB). Admitted.
- `ti:"C-Pack" OR ti:"BGE M3"` — 9 results; identified 2309.07597 (C-Pack).
  Screened, abstained (Chinese-centric).
- `ti:"Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval
  Models"` and `au:Thakur_N AND ti:BEIR` — returned empty/unparseable (arXiv
  rate limiting by then); BEIR id left unresolved.
- `ti:"Towards General Text Embeddings with Multi-stage Contrastive Learning"`
  — unparseable under rate limiting; GTE id left unresolved.
- Direct abs-page fetches (`https://arxiv.org/abs/<id>`, curl): 24 pages,
  all HTTP 200, titles/authors/abstracts parsed from HTML. Three remembered
  ids resolved to unrelated papers (2104.08671, 2310.01730, 2402.13840);
  the intended candidates (BEIR, GTE, echo) were re-resolved by title search
  (echo, MMTEB) or deferred (BEIR, GTE).

## Other sources

- Semantic Scholar paper-search API: one call, HTTP 429 (no key). Abandoned.
- GitHub REST API (`/repos/{owner}/{repo}`, curl): 14 repo lookups; 2 needed
  `-L`/search-API recovery after org renames (sentence-transformers is now
  huggingface/sentence-transformers; FlagEmbedding is now
  FlagOpen/FlagEmbedding). QwenLM/Qwen3-Embedding license field null;
  NVIDIA/NV-Embed has no official training repo in search results.
- Hugging Face / Papers with Code / leaderboards: not queried (see gaps).

## Counts

- Screened: 24 rows in inventory.tsv (21 verified abs pages + 3 wrong-id
  fetches recorded as abstains).
- Admitted: 16 (PDFs in papers/, all starting with %PDF, two spot-checked
  for title strings).
- Per-lane minimums (20 screened, 8 admitted): met (24 / 16).

## Year/venue convention

Year is the submission year from the arXiv id prefix (YYMM). Venue is
"arXiv preprint" for all rows except DPR, whose abs page states EMNLP 2020.
No venue was recalled from memory.

## What failed

- arXiv API rate limiting after ~8 calls (empty responses); mitigated with
  3-20s sleeps, but BEIR/GTE title searches never completed.
- Semantic Scholar without API key: 429 immediately.
- GitHub search for small-model repos (nomic-embed-text, jina-embeddings-v2,
  SFR-Embedding): no authoritative training repo identified; left blank
  rather than invented.
- Only abstracts were read. All "reported numbers" in findings.md are
  abstract-level vendor claims, not PDF-extracted tables. Full-reading the
  16 PDFs (inference costs, ablations, MTEB tables) is open work.
- No forward/backward citation chaining was completed (S2 blocked, arXiv
  API throttled); the lane relies on seed papers plus title search, so
  2025 successors beyond Qwen3-Embedding/MMTEB are likely missed.
