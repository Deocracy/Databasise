# Lane 2 method

Lane: KV-cache reuse beyond the prefix (position-independent / modular caching,
out-of-order composition quality, partial-recompute repair, serving-engine APIs).

## Queries run

- arXiv API (`export.arxiv.org/api/query`, Atom XML), sorted by submittedDate:
  `all:"prompt cache"` (20 results), `all:"KV cache reuse"` (50),
  `all:"CacheBlend"`, `all:"RAGCache"`, `all:"CacheGen"`, `all:"ChunkAttention"`,
  `all:"Block-Attention for Efficient"` (found 2409.15355),
  `all:"TurboRAG"`, `all:"EPIC position-independent caching"`, `all:"KVLink"` —
  10 each. Six further API queries (prefix caching, RadixAttention, PagedAttention,
  recompute/cross-attention, attention sinks) were issued but returned HTTP 429.
- arXiv abs pages via curl (`arxiv.org/abs/<id>`, title/authors/date/abstract
  extracted with regex): 32 ids opened and verified (all 20 admits + 12 abstains).
  Four arXiv abs pages rendered via webfetch (2311.04934, 2405.16444, 2410.15332,
  2404.12457, 2410.07590, 2310.07240, 2402.15220) before switching to curl to save
  context.
- arXiv HTML pages (`arxiv.org/html/<id>`) for 19 papers to extract official
  repository URLs from the paper source itself (reliable where GitHub search failed).
- Semantic Scholar API (search + intended citation chaining): unusable — HTTP 429
  on all six search calls (unauthenticated rate limit). No S2 data is cited anywhere
  in this lane's outputs. Forward-chaining was done instead via arXiv related-title
  search and the 2026 papers' own related-work mentions (e.g. CacheClip names APE
  and CacheBlend; Grounded Cache Routing surveys six systems).
- GitHub REST API: 2 search batches + 19 direct `repos/<owner>/<repo>` lookups for
  stars, pushed_at, license. Official repo paths were taken from paper HTML, never
  guessed (one guess, `microsoft/prompt-cache`, returned 404 and was discarded;
  the correct `yale-sys/prompt-cache` came from the paper HTML).
- Papers with Code API: 4 queries, all failed (non-JSON responses); no PWC data cited.
- Hugging Face Hub: not queried — no checkpoint artefacts in this lane needed it
  (reuse systems release code, not weights, except TurboRAG's unreleased fine-tune).

## Counts

- Screened: 43 candidates (every row of `inventory.tsv`).
- Admitted: 24 (20 papers, each opened at its arXiv abs page and downloaded as PDF
  with `%PDF` magic verified; 4 code-only engines verified via GitHub API, not cloned).
- Abstained: 19, each with a reason in `inventory.tsv` and summarized in
  `findings.md` section (c). Nothing screened was dropped silently.

## What failed

- arXiv API rate-limiting (HTTP 429) after ~8 queries; mitigated with 60 s wait +
  switch to per-id abs/HTML fetches via curl, which never rate-limited.
- Semantic Scholar: fully rate-limited without an API key; citation-graph chaining
  as specified in the brief was not possible. Partial substitute: arXiv
  title-search + 2026 survey-style papers (Grounded Cache Routing, CacheClip).
- Papers with Code API: no usable responses.
- GitHub code search for academic repos is poor (e.g. "RAGCache" returns only
  forks; "KVLink LLM" returns zero); resolved by extracting repo URLs from paper HTML.
- No public repo found for RAGCache, HYPIC, CacheClip, Grounded Cache Routing,
  CachePrune, CoinRAG (recorded as `--`, not invented).
- Venue recorded only where the arXiv comments field states it (MLSys 2024,
  SIGCOMM'24, ACL 2024); all else is `preprint` or `n/a (code)`.
- Star counts / push dates are GitHub API values fetched 2026-09-12; licenses are
  the API `spdx_id` verbatim (including `NOASSERTION` and `None stated`).
- 2026 preprints (13 of 20 admitted papers) are abs-verified but single-source and
  unreplicated; findings mark replication risk per item.
