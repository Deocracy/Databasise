# Lane 5 method

## Queries run

arXiv API (`export.arxiv.org/api/query`, Atom XML, custom parser after the first
quoted-phrase attempt returned zero rows — exact-phrase `all:"..."` queries silently
match nothing; bare `all:Term` works; 3 s sleep between calls):
`all:Palimpzest`, `all:DocETL`, `all:LOTUS AND all:semantic`,
`all:Text-to-SQL AND all:memory`, `all:query AND all:routing AND all:retrieval`,
`all:RouterRetriever`, `all:Adaptive-RAG`, `all:TableRAG`, `all:BlendSQL`,
`all:ReAcTable`, `all:Chain-of-Table`, `ti:Chain-of-Table`, `ti:RouteLLM`,
`ti:StructGPT`, `ti:TAG AND ti:Table-Augmented`, `ti:DIN-SQL`,
`ti:CHESS AND ti:Text-to-SQL`, `ti:DATER`, `ti:CHESS AND au:Talaei`,
`ti:Evaporate AND au:Arora`, `ti:Adaptive AND ti:Retrieval-Augmented AND ti:Generation`,
`ti:Table-Augmented AND ti:Generation`, `ti:HybridRAG`,
`all:Table-Augmented AND all:Generation AND all:database`, `all:ZenDB`, `all:Evaporate`,
plus three `id_list` verification batches covering all 40 admitted ids (title, date,
authors cross-checked; two recalled ids caught as wrong: 2305.11755 is a visualization
survey, not StructGPT; 2306.00770 is a Gaia-stars paper, not Chain-of-Table; 2406.05287
is online multi-group learning, not RouteLLM — correct ids found via `ti:` search).

Semantic Scholar API: attempted (search + citation chaining per brief) but the endpoint
returned HTTP 429 (rate limit, no key) on every attempt; chaining was replaced by
arXiv related-title search and reference-following via arXiv HTML full text.

Papers with Code API (`paperswithcode.com/api/v1/papers/`): attempted for five queries;
all returned non-JSON (endpoint effectively dead); abandoned.

GitHub API: `search/repositories` (≈15 queries) and `repos/{owner}/{repo}` for every
recorded repo (stars, `pushed_at`, license `spdx_id` read 2026-09-12). Official repo
identity confirmed via `arxiv.org/html/<id>` full-text grep for `github.com` links
(LOTUS→lotus-data/lotus, Adaptive-RAG→starsuzi/Adaptive-RAG,
RouterRetriever→amy-hyunji/RouterRetriever, TableRAG-hetero→yxh-y/TableRAG,
CHESS→ShayanTalaei/CHESS). Two guessed repo paths 404'd and were corrected this way
(stanford-futuredata/lotus, lotus-data/LOTUS-case variants).

arXiv abs pages opened via webfetch for 2407.11418 and 2403.14403 (title/author/abstract/
venue-comment confirmed; NAACL 2024 for Adaptive-RAG).

## Sources used

arXiv API + abs pages + HTML full text (primary); GitHub API (primary for repo facts);
downloaded PDFs `%PDF`-verified (primary). No vendor benchmark table cited as an
independent result. Hugging Face Hub not needed (no checkpoint claims admitted).

## Counts

- Screened: 57 inventory rows (40 papers + 12 code artefacts + 5 abstains); underlying
result lists inspected were several hundred across ~30 arXiv/GitHub queries.
- Admitted: 40 papers (all with PDFs in `papers/`) + 12 code artefacts.
- Refute disposition: none as standalone rows; 4 sourced qualifications in findings §(b).
- Abstain: 5 (TAG, DATER, SemCEB, CSR-RAG recall mismatch, ZenDB code).

## What failed

- Semantic Scholar 429s (no API key) — no citation-graph chaining; forward-chain
coverage is therefore thinner than the brief asks. Mitigation: `ti:`-targeted arXiv
search plus HTML full-text reference mining (e.g. LOTUS paper cites DocETL/Factool).
- Papers with Code API dead — no SOTA-table cross-checks.
- Quoted-phrase arXiv queries silently empty — reran bare; possible missed exact-title
hits for TAG/DATER (listed as abstains, not silently dropped).
- Venue metadata: only Adaptive-RAG's venue (NAACL 2024) verified from abs comments;
all other venues recorded as "arXiv preprint" rather than recalled (several are
published at VLDB/SIGMOD/ACL venues, but unverified).
- License "unverified"/None for smaller repos recorded as-is; YuhangWuAI/tablerag
(GPL-3.0) flagged as license-incompatible rather than admitted.
