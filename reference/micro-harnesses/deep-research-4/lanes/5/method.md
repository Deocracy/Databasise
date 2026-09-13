# Lane 5 method

## Queries run

Vendor/API docs (webfetch markdown unless noted):
- `https://docs.anthropic.com/en/docs/build-with-claude/streaming` (redirected to platform.claude.com) — OK
- `https://platform.openai.com/docs/guides/streaming-responses` (redirected to developers.openai.com) — OK
- `https://platform.claude.com/docs/en/build-with-claude/prompt-caching` — OK (very long; key sections extracted)
- `https://platform.claude.com/docs/en/agents-and-tools/tool-use/fine-grained-tool-streaming` — OK
- `https://developers.openai.com/api/docs/guides/function-calling` — OK (very long; key sections extracted)
- `https://platform.claude.com/docs/en/build-with-claude/context-editing` — OK
- `https://developers.openai.com/api/docs/guides/realtime-conversations` — OK (very long; key sections extracted)
- `https://ai.google.dev/gemini-api/docs/*` (text-generation, function-calling, caching) — webfetch transport errors; recovered via `curl` + HTML-strip extraction
- `https://spec.modelcontextprotocol.io/specification/server/sampling/` — transport error; recovered by locating sampling under `docs/specification/2025-06-18/client/sampling.mdx` in github.com/modelcontextprotocol/modelcontextprotocol via Contents API + raw fetch
- `https://docs.nvidia.com/nemo/guardrails/.../streaming.md` — 404 (two URL shapes); NeMo README via raw fetch mentions streaming only as telemetry flag

arXiv (curl abs-page extractor `/tmp/abs.py`, title extractor `/tmp/title.py`, venue extractor
`/tmp/venue.py`, repo-href extractor `/tmp/links.py`, search-HTML parser inline):
- Direct abs verification: 2305.06983, 2309.10072, 2305→(Self-RAG search), 2503.09516, 2501.05366, 2401.08711, 2407.08223, 2210.15097, 2307.09228, 2312.06674, 2310.08560, 2403.03870, 2310.12962, 2504.13171, 2211.17192, 2302.01318, 2504.11536, 2512.12818, 2503.23383, 2608.11879, 2608.29605, 2312.12286
- arXiv search UI queries (quote queries that worked): `DRAGIN dynamic retrieval augmented generation` → 2403.10081; `Self-RAG learning to retrieve generate critique` → 2310.11511; `"Co-LLM"` → 2403.03870 + false positive; `"small model" "large model" collaborative inference`; `"proxy tuning"` (missed); `"tuning by proxy"` (missed); `"emulated fine-tuning"` → 2310.12962; `"sleep-time compute"` → 2504.13171; `"Memori" memory` (too broad, unused); `"hindsight" memory agent` and `"hindsight" memory llm` (oldest-first) → 2512.12818; `"ToRL" tool reasoning` → 2503.23383
- arXiv export API (`export.arxiv.org/api/query`): hit HTTP 429 rate limits repeatedly; abandoned in favor of abs pages + search UI
- Re-retry at write time: export API now times out entirely (HTTP 000, 40s), Semantic Scholar still HTTP 429. Both endpoints unreachable from this environment; minimums already exceeded via abs-page + fetched-doc provenance, so no further retries.
- Semantic Scholar API: HTTP 429 repeatedly (no key); unused for admission
- Papers with Code API: empty/302-redirect responses; unused

GitHub (API while unauthenticated, then HTML/raw after rate limit):
- `api.github.com/search/repositories` and `/repos/...` worked initially (Memori: 16694 stars, pushed 2026-09-03), then HTTP 403 rate-limit; search endpoints 429
- HTML extractor `/tmp/gh.py` (stargazerCount/forksCount/og:description/license badge): DRAGIN 191, Search-R1 5413 Apache-2.0, Search-o1 1244 MIT, co-llm 130, FLARE 668 MIT, Memori 16694/3446
- Raw file fetches (no rate limit): Memori LICENSE (Apache-2.0), Memori README, NeMo README, guardrails-ai README, MCP sampling.mdx
- Repo URLs for Search-R1/Search-o1/co-llm/FLARE extracted from arXiv abs-page GitHub hrefs (primary source)

Hugging Face API: confirmed `selfrag` org + `selfrag_llama2_7b` weights (used only for the abstain reason, not admission).

## Counts

- Screened: 36 rows in inventory.tsv (26 admitted incl. 7 doc/repo sources; 10 abstained)
- Admitted papers with PDFs: 19 (all verified `%PDF` magic, renamed to `<id>_<slug>.pdf`)
- Admitted doc/repo sources: 7 (4 vendor doc groups + MCP spec + 2 repos; filed as inventory rows, no PDFs per brief categories)

## What failed

1. arXiv export API and Semantic Scholar API rate-limited this egress IP throughout; discovery pivoted to arXiv search-UI HTML + direct abs verification (stronger provenance anyway).
2. Four recalled arXiv IDs were wrong (2309.10072, 2401.08711, 2307.09228, 2312.12286) — all caught by opening the abs page, none cited. Recall is not a source.
3. GitHub API rate limit blocked push-date collection for most repos; stars recorded only where a fetched page showed them, otherwise `unverified`.
4. No primary source found for streaming-deployed guardrail sidecars or a paper literally named "Proxy Tuning"; both abstained with the nearest verified substitute named.
5. ai.google.dev blocks the markdown fetcher; Gemini claims rest on curl-extracted page text (same pages, weaker fidelity — noted per claim).
