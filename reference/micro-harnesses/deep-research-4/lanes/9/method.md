# Lane 9 method

## Queries run

arXiv HTML search (`https://arxiv.org/search/?query=...&searchtype=all`, size 25, UA `melodyscribe-lane9/1.0`),
22 queries in two batches (14 + 8), 4 s between calls:
MIRIX memory agent; Graphiti temporal knowledge graph; Zep memory layer temporal graph;
BIRD text-to-SQL benchmark; Spider text-to-SQL dataset; small language model text-to-SQL SQLite;
TableRAG table retrieval; entity resolution alias merging knowledge graph (0 hits);
temporal validity contradiction LLM memory; Mem0 memory layer; HippoRAG memory retrieval;
bitemporal knowledge graph LLM; contradiction detection persistent memory agent;
schema generation structured extraction small LLM;
CodeS text-to-SQL open source; DIN-SQL text-to-SQL decomposition (0 hits);
schema linking text-to-SQL; entity linking coreference knowledge graph construction;
SQLCoder defog text-to-SQL small (0 hits); OmniSQL text-to-SQL;
contradiction temporal reasoning conversational memory; structured knowledge vault personal agent memory.
Merged unique arXiv ids across both batches: 133.

Abs verification: 30 abs pages fetched at `https://arxiv.org/abs/<id>` (title/authors/abstract parsed from
page HTML), 4 s between calls; results cached in scratch `abs.json` (kept outside the lane folder).

GitHub: `api.github.com/search/repositories` + `api.github.com/repos/<owner>/<repo>` for MIRIX, Graphiti,
Zep, Mem0, SQLCoder, prem-1B-SQL, SQLMesh. Hugging Face: `huggingface.co/api/models` for
defog/sqlcoder-7b-2 and prem-research/prem-1B-SQL. Papers with Code API: not reached (evidence sufficient).
Forward citation chaining: reference lists inside opened abstracts only (see below for why).

## Sources used

arXiv abs pages + PDFs (primary for all admitted papers); GitHub API page + repo HTML page (primary for repo
facts); Hugging Face model API (primary for weights artefacts). No blog or vendor page admitted as more than
"what the vendor reports". Every 2025–2026 item comes from a page fetched 2026-09-13, not from recall.

## Counts

Screened: 143 candidates (133 unique arXiv ids + 7 repo lookups + 3 HF model records, minus overlap).
Admitted: 26 (20 papers with PDFs in `papers/`, 4 repos, 2 weight artefacts).
Refute: 2 admitted-as-refuting (HippoRAG 2, ReFind). Abstain: remainder, each with a reason in
`inventory.tsv` (10 abs-opened tangentials/mismatches + ~100 title-screen-only + 3 rate-limited lookups).

## What failed

- `export.arxiv.org` API: "Rate exceeded" for the whole session (shared IP under concurrent lane load);
replaced with `arxiv.org/search` HTML scraping, which worked.
- Semantic Scholar API: HTTP 429 for the whole session; planned citation forward/backward chaining was
replaced by arXiv related-search plus in-abstract reference inspection. 2026 papers' citation contexts are
therefore thinner than the brief asks; flagged in the unresolved ledger.
- GitHub REST API: rate-limited mid-session (authenticated quota suggestion received); getzep/graphiti stars
taken from page-embedded `stargazerCount` JSON (~30850, marked approximate), license (Apache-2.0) from the
same page; sqlcoder/premAI GitHub lookups superseded by Hugging Face API records.
- Hugging Face single-model endpoint returned one transient auth error; model-search endpoint worked.
- "entity resolution alias merging" and "DIN-SQL"/"SQLCoder" arXiv queries returned zero hits; CodeS/DIN-SQL
papers not located (one recalled id verified as a physics paper — recorded as abstain, not admitted).
- Date parsing on abs pages failed (regex missed the dateline); years for papers taken from arXiv id prefixes
and cross-checked against search ordering. Venues recorded as "arXiv preprint" except Spider (EMNLP 2018,
well-established and stated on the abs page).
