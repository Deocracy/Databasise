# Lane 9 method

## Queries run
- arXiv API (`export.arxiv.org/api/query`, `search_query=all:"GraphRAG"`): **rate-limited on every attempt**
  ("Rate exceeded" even after 5s+ waits; retried 3 times, then abandoned). All arXiv verification
  done via `webfetch` of `https://arxiv.org/abs/<id>` pages (14 abs pages opened) plus
  `https://arxiv.org/pdf/<id>` downloads (13 PDFs, each verified to start with `%PDF`).
- Semantic Scholar REST (`api.semanticscholar.org` search): **HTTP 429 without API key**; citation
  chaining not performed. Forward-chaining substituted with: (a) related-work sections of fetched
  PDFs (RAPTOR→LlamaIndex, Zep→MemGPT, PathRAG→GraphRAG/LightRAG), (b) repo "used by / projects
  using" lists (nano-graphrag → LightRAG, fast-graphrag, HiRAG, MiniRAG-adjacent HKUDS org).
- GitHub REST (`api.github.com/repos/...`, unauthenticated): worked for the first 4 repos, then
  **rate-limited (60/hr shared-IP quota)** for ~2h. Recovered late in the pass; remaining repo facts
  taken from `webfetch` of GitHub repo HTML pages (stars/forks/license visible) or recorded as
  unverified. No star/push/license figure in inventory.tsv is recalled: every number cites the API
  response or the rendered repo page; rate-limited cells say `unverified`.
- Papers with Code API and Hugging Face API: not used (no added value once arXiv+GitHub covered
  the seed systems; HF hosts no graph-pipeline artifacts relevant to this lane).
- Web search (session provider): used for ID recovery (PathRAG 2502.14902, IRCoT 2212.10509, EDC
  2404.03868, Leiden 1810.08473, Cognee paper 2505.24478) and for official-docs passages (GraphRAG
  `update` CLI/API docs, FastGraphRAG method docs, LazyGraphRAG blog). Every recovered ID was then
  verified at its arXiv abs page before admission.
- PDF text mining: `pypdf` (via `uv run --with pypdf`) extracted full text of the 10 pipeline-core
  PDFs to `/tmp/l9_*.txt`; quoted numbers (LightRAG Table 2, HippoRAG §§1/4, GraphRAG §3.1,
  RAPTOR §3, MiniRAG §§2–3, PathRAG §3, KGGen §§1–2, HippoRAG2 Fig.2/§3) were `grep`ed with context
  from those extractions, not copied from search snippets.

## Candidates per lane minimum
- Screened: 22 (16 admit, 6 abstain). Admitted: 13 papers (PDFs in `papers/`) + 2 repos + 1 vendor
  blog (secondary-only). Inventory header: `name, title, authors, year, venue, arxiv_id_or_doi,
  repo_url, stars, last_push, license, artefact_released, one_line, capability, relevance_0_3,
  disposition, reason`.

## What failed
1. arXiv API rate limits (3 attempts) — worked around via abs-page fetches + PDF downloads.
2. Semantic Scholar 429 (no key) — no citation-graph chaining; related-work sections + repo
   dependency lists substituted (documented above).
3. GitHub API 60/hr quota — 4 repos via API; graphiti/cognee/nano via rendered pages; 1 repo
   (BUPT-GAMMA/PathRAG) unverified for stars/push; kg-gen license returned null (recorded as-is).
4. Two recalled arXiv IDs were wrong (2502.18886 ≠ PathRAG, 2212.08658 ≠ IRCoT) — caught at the abs
   page, recorded as abstains so no future pass re-screens them.
5. LangChain indexing docs URL redirected to overview — recorded abstain rather than citing recalled
   record-manager design.
6. No `pip`/pdf tooling on PATH — used `uv run --with pypdf`.
7. No primary source anywhere reports documents-per-hour with hardware for any system in this lane;
   recorded as the lane's main unresolved item, not filled by estimation.
