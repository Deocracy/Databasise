# Lane 3 method

## Queries and sources

- arXiv export API (`export.arxiv.org/api/query`), one working query before
rate-limiting began: `all:"agent memory system"` (50 results, newest first),
which surfaced the 2026 batch (Memanto, MemTX, Harness, ReFind, MemDelta, HAGE,
eMEM, Episodic-Semantic, Database paper, Beyond-Semantic). Two further API queries
returned empty (service-side throttling, zero-length bodies), so the API path was
abandoned in favor of abs pages.
- arXiv abs pages via curl (14 pages, 4s spacing): 2310.08560, 2303.11366,
2502.12110, 2504.19413, 2507.03724, 2507.07957, 2501.13956, 2305.10250, 2502.14802,
2304.03442, 2604.22085, 2605.26252, 2606.06090, 2608.15008, 2605.12978, 2608.12888,
2604.27707, 2605.17625, 2607.23929, 2605.09942, 2606.29914, 2606.03374, 2405.14831
(title/authors/date/abstract parsed from HTML and recorded).
- arXiv HTML search pages via webfetch (4 pages, used only because the API was
throttled): `HippoRAG 2` (resolved 2502.14802 as HippoRAG 2, correcting my own
misread), `SimpleMem lifelong memory` (2601.02553, 2604.01007), `MemInsight memory
agents` (2503.21760), `LightMem agent memory` (2604.07798 plus DimMem, StructMem,
FluxMem, SF-AMS, Reproducing-LightMem). These pages are large; per instructions
they were a fallback, and items admitted from them are flagged "search listing" in
`inventory.tsv` where the abs page was never opened.
- GitHub REST API: repository search (`agent memory llm`, `memobase`, `nemori`,
`cognee`, `honcho` in:name) plus 15 direct `repos/{owner}/{repo}` metadata fetches
(stars, pushed_at, license) for every admitted code system.
- Semantic Scholar API: attempted three times (typed-memory search, two citation
chains from seed 2502.12110); all returned HTTP 429 throughout the session. No S2
data was used. Forward-chaining was therefore done via arXiv related-result
listings and the "cites HippoRAG/A-MEM/Mem0" evidence inside 2026 abstracts, not
via the citation graph — a coverage gap the final report should note.

## Counts

Screened 45 candidates (30 papers with downloaded PDFs, 8 code-only systems, 7
abstains). Admitted 34 (26 papers + 8 code systems). Refuted 4 (PDFs downloaded,
cited in findings, not filed as admitted). Venues default to "arXiv preprint"
unless the fetched page stated otherwise (NeurIPS/ICML/ICLR/ACL noted where
verified). Star counts and push dates are GitHub API values fetched 2026-09-12.

## Failures

- Semantic Scholar 429 on every call (no key available).
- arXiv export API returned empty bodies after the first query (throttling).
- arXiv HTML search returned HTTP 400 for one query variant (with `&size=10`); worked without it.
- Two brief-implied identifiers were wrong on inspection: 2306.03609 is not
Generative Agents (correct: 2304.03442); 2606.29914 is MemDelta, not "Mandol".
Both corrected from primary sources.
- Zep paper PDF (2501.13956) is only 149KB; starts with %PDF and parsed as valid,
but it reads as a short paper — flag for the report assembler.
