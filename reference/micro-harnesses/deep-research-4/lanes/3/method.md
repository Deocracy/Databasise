# Lane 3 method

## Queries run

arXiv abs pages fetched directly via curl (title/author/date verification,
2026-09-13): 2212.10509, 2310.11511, 2305.06983, 2403.10081, 2210.03629,
2503.09516, 2501.05366, 2502.01142, 2409.05152, 2405.14831, 2502.14802,
2410.05779, 2507.07957, 2403.14403, 2305.15294, 2310.08560, 2402.09906,
2210.03350, 2402.17753, 2410.10813, 2402.03367, 2501.13956 (22 papers).
arXiv title-search endpoint used once successfully (DRAGIN → 2403.10081),
then returned backend-error pages and was abandoned. Web search used to
discover candidate IDs (DeepRAG, OneGen, HippoRAG 2, LightRAG, MIRIX, LoCoMo,
LongMemEval, MemGPT, Adaptive-RAG, HippoRAG, RAG-Fusion, GritLM, ITER-RETGEN,
Self-Ask, RRF), each then verified at its arXiv abs page before admission.
GitHub REST API (no auth): getzep/graphiti, mem0ai/mem0, run-llama/llama_index,
HKUDS/LightRAG, OSU-NLP-Group/HippoRAG, Mirix-AI/MIRIX (stars, pushed_at,
license, 2026-09-13). Web fetch: Graphiti README, LlamaIndex router docs,
ACM page + author PDF for RRF.

## Sources used

arXiv abs pages (primary, all admits); arXiv PDFs (primary, all 22 paper
admits, %PDF-checked); ACL Anthology pages (OneGen, LightRAG, Adaptive-RAG
venues); NeurIPS proceedings PDF (HippoRAG venue/content); GitHub API + README
(Graphiti, LlamaIndex routers); vendor docs (LlamaIndex routers, primary for
framework behavior). Semantic Scholar API was rate-limited (429) and arXiv
export API returned 503, so neither contributed.

## Screening counts

28 candidates screened: 24 admitted (22 papers with PDFs + Graphiti repo +
LlamaIndex routers), 4 abstained (RRF original, Mem0, RankRAG,
SQLAutoVectorQueryEngine). Two guessed IDs were falsified at the abs page
(2305.13386 is not FLARE, 2309.10072 is not DRAGIN, 2503.00639 is not DeepRAG,
2409.08946 is not OneGen, 2402.09997 is not GritLM) and corrected before
admission; the wrong guesses are not listed as candidates.

## Failures

- export.arxiv.org API: HTTP 503 for search queries.
- api.semanticscholar.org: HTTP 429 without API key; no citation chaining done.
- arxiv.org/search title search: worked once, then error pages.
- No PDF-text tools on machine (no poppler, no pip); key numbers inside PDFs
were confirmed with a stdlib zlib-stream extractor (/tmp/pdftext, scratch
only), all other figures come from fetched abs/HTML pages.
- Initial arXiv-ID guesses from memory were wrong 5 times; every one was
caught by opening the abs page, none entered the inventory.
