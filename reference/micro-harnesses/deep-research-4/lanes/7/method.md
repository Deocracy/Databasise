# Lane 7 method

## Queries run

Web-search (session provider, each returning up to 8 results with fetched-page excerpts), all 2026-09-13:

1. `RepoGraph enhancing AI software engineering repository-level code graph arXiv`
2. `CodexGraph LLM-powered code graph reasoning arXiv`
3. `GraphCoder graph-based code completion retrieval arXiv`
4. `CodeRAG-Bench benchmark retrieval augmented code generation arXiv`
5. `RepoBench repository-level code completion arXiv RepoEval`
6. `SWE-bench verified Lite issue resolution benchmark arXiv 2310.06770`
7. `Aider repo map repository context tree-sitter ctags`
8. `Sourcegraph SCIP code intelligence protocol index graph`
9. `CocoIndex codebase indexing tree-sitter code graph GitHub`
10. `Potpie code graph RAG codebase agent arXiv GitHub`
11. `GitNexus code graph semantic search GitHub`
12. `codebase-memory-mcp knowledge graph code indexing GitHub`
13. `CrossCodeEval repository code completion benchmark arXiv`
14. `RepoCoder repository-level code completion iterative retrieval generation arXiv EMNLP`
15. `Graphify knowledge graph construction code documentation GitHub`
16. `CodeQL code graph database semantic analysis GitHub documentation`
17. `tree-sitter parser incremental code analysis GitHub stars license`
18. `Repoformer selective retrieval repository code completion GitHub Di Wu`
19. `GraphCodeAgent dual graph repo-level code generation GitHub Jia Li`

Primary-source verification via direct page fetch (webfetch, markdown): all 11 arXiv abs pages opened
(2410.14684, 2408.03910, 2406.07003, 2406.14497, 2306.03091, 2303.12570, 2310.11248, 2310.06770,
2504.10046, 2403.10059, 2408.13863). Repo facts via GitHub REST API (`/repos/{owner}/{repo}`) with a
research User-Agent on 2026-09-13 for 14 repositories; GitNexus facts via the search API
(`/search/repositories?q=GitNexus+in:name`) after the direct repo endpoint hit the rate limit.

## Sources used (authority order per brief)

arXiv abs pages (11, all opened); PMLR proceedings page for Repoformer (ICML 2024, confirms venue);
ACL Anthology pages for CodexGraph and RepoCoder (confirm NAACL 2025 / EMNLP 2023 venues); ACM DL
entries for GraphCoder (ASE 2024) and CrossCodeEval/SWE-bench/RepoBench (confirm venues, secondary
excerpts only); GitHub API (stars, pushed_at, license — primary for commit-independent facts);
project documentation as primary for what the tool does (aider.chat repo-map docs, SCIP README +
announcement post + scip.proto, CocoIndex docs, Potpie README, CodeQL overview docs). Vendor
benchmark and performance tables treated as primary only for "what the vendor reports."

## Screening counts

Screened 23 candidates (inventory.tsv): 11 papers (10 admitted + 1 refuted naming collision) and 12
systems/artefacts (8 admitted + 4 abstained). Admitted 18. Forward-chaining was done through related
paper references inside fetched excerpts (RepoGraph cites CodexGraph/RepoUnderstander; CodeRAG-Bench
indexes RepoEval/SWE-bench-Lite; GraphCodeAgent builds on CodeAgent 2401.07339 and contrasts
GraphCoder) rather than the Semantic Scholar API, which was unavailable (see failures).

## What failed

- arXiv export API (`export.arxiv.org/api/query`): first call returned `Rate exceeded`, retry
  returned HTTP 503. Abandoned in favour of web-search plus direct abs-page fetches; no candidate
  was admitted without its abs page opened.
- Semantic Scholar API: HTTP 429 (rate limited, no key) on the first call. Citation chaining was
  therefore done manually from references visible in fetched pages, not via the citations/references
  endpoints. 2025+ coverage rests on fetched abs pages (GraphCodeAgent v2 Nov 2025 opened).
- GitHub REST API: succeeded for 14 repos, then rate-limited (`API rate limit exceeded`) on the
  abhigyanpatwari/GitNexus direct lookup and all subsequent direct calls; GitNexus facts come from
  the search endpoint instead, and Graphify/sjhorn/code-graph-rag stars were never API-confirmed,
  which is recorded in the inventory reasons and the unresolved ledger (U1, U6) rather than papered over.
- No repositories were cloned, per the brief. Paper PDFs (10) were downloaded from
  https://arxiv.org/pdf/<id>, each verified to start with `%PDF`, and renamed to
  `<arxiv-id>_<Title_Slug>.pdf` (slug: non-alphanumerics to underscores, 70 chars max).
- Papers with Code and Hugging Face Hub were not needed: every paper artefact was resolved through
  the paper itself plus the linked GitHub repository.
