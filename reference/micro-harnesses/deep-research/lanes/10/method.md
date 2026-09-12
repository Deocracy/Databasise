# Lane 10 method

## Search strategy

No general search engine was available. All discovery used, in order: (1) brief seed list as starting points (HippoRAG 2, LightRAG, GraphRAG, Graphiti, Cognee, Dense X Retrieval); (2) live web search for candidate verification and repo stats; (3) direct fetch of primary sources (arXiv abs pages, paper PDFs/HTML, ACL Anthology, AAAI/NeurIPS/ICLR proceedings and DOI pages, GitHub repo pages and the GitHub REST API, vendor docs); (4) forward/backward chaining through related-work sections of fetched papers (HippoRAG 2 cites GraphRAG/GRAG/GNN-RAG/HippoRAG; KAG cites ToG-2.0/GRAG/GNN-RAG/HippoRAG; Align-GRAG cites G-Retriever; PathRAG compares GraphRAG/LightRAG).

## Queries run (web search, 2026-09-12)

HippoRAG 2 github; LightRAG arxiv id; Microsoft GraphRAG arxiv 2404.16130; G-Retriever arxiv; MiniRAG arxiv 2501; RAPTOR arxiv 2401.18059; Think-on-Graph arxiv; TableRAG million-token (gave 2410.04739); GRAG arxiv; MiniRAG/SubgraphRAG details; CRAG arxiv 2406.04744; GLiNER arxiv 2311.08526; TableRAG heterogeneous / PathRAG / HippoRAG-1 / KAG AntGroup; TableRAG Google arxiv id; PathRAG github repo; KAG technical report; StructRAG; REBEL Cabot Navigli; Cognee memory github; RGB benchmark arxiv; GLiNER github repo; RAGBench arxiv; LeanRAG arxiv; topoteretes cognee stars; getzep graphiti stars; facebookresearch CRAG stars; yxh-y TableRAG; icip-cas StructRAG stars; chen700564 RGB. ~30 queries total.

## Sources used

arXiv abs pages (8 fetched directly: 2502.14802, 2311.08526, 2501.13956, 2312.06648, 2409.13731, 2410.08815 + search-rendered abs content for the rest); arXiv PDFs (22 downloaded, all verified `%PDF` magic + page-count sanity via size); ACL Anthology (TableRAG-Huawei 2025.emnlp-main.710, GRAG NAACL Findings, LightRAG EMNLP Findings, REBEL PDF); proceedings/DOI pages (ICLR for ToG/RAPTOR/SubgraphRAG/StructRAG, NeurIPS for G-Retriever/TableRAG-Google, AAAI OJS+DOI for PathRAG/LeanRAG/RGB); GitHub REST API via curl (4 repos fully: G-Retriever, SubgraphRAG, ToG, graphrag, GRAG, PathRAG, KAG, REBEL, LeanRAG) and via webfetch (2); GitHub repo pages via webfetch (HippoRAG) and search-index snapshots (LightRAG, RAPTOR, MiniRAG, GLiNER, graphiti, CRAG, Cognee, StructRAG); vendor docs (microsoft.github.io/graphrag, cognee.ai).

## Counts

Screened 25 candidates (24 admit, 1 abstain). PDFs filed: 22 arXiv + 1 ACL (REBEL, no arXiv version exists; filed as `ACL_2021_findings_emnlp_204_REBEL.pdf` — documented deviation from the `<arxiv-id>_` naming rule). Slugs: non-alphanumerics to underscores, truncated to 70 chars, no spaces. No repositories cloned per lane instructions; URLs and API-fetched facts recorded only.

## What failed

- `export.arxiv.org` API: HTTP 429 / empty bodies for the entire session (curl and search). Workaround: fetched abs pages + PDFs from `arxiv.org` directly, which worked reliably (23/23 PDFs HTTP 200, all `%PDF`-verified).
- Semantic Scholar API: HTTP 429 throughout; no key available. Workaround: manual citation chaining via fetched related-work sections.
- GitHub REST API via shell curl: intermittent HTTP 403 windows (roughly: 1 success per ~2-minute bucket). Workaround: paced requests with `sleep 10–20`, webfetch fallback, and search-index snapshots (explicitly labeled as secondary in inventory). Cells that could not be filled say `not fetched` with reason; nothing invented.
- Web search provider: intermittent HTTP 429 when batching 3–4 queries; paced to 1–2 per round, which held.
- `pdftotext`/`pdfinfo` not installed; PDF text grep fell back to `strings` (used once, to extract the DenseX data-repo URL).
- One name collision found: two distinct "StructRAG" papers (ICLR 2025 hybrid-structurization vs 2025 scholarly-KG companion). The latter is the lane's single abstain.
- LeanRAG repo `RaZzzyz/LeanRAG` redirects to `KnowledgeXLab/LeanRAG` (recorded via API response).
- Several repos report no license via API (`license: null` for ToG, PathRAG, REBEL, LeanRAG) — recorded as `none detected (API)`, not as unlicensed.
