# Lane 10 method

## Queries run

Seed-first discovery (each seed: title/author web search, then open primary page):

- `Differentiable Search Index DSI Tay arxiv id` -> 2202.06991 (two wrong guesses from
memory, 2302.00622 and 2202.06997, falsified by opening the abs pages; corrected to
2202.06991 via fetched search results)
- `Neural Corpus Indexer Wang arxiv NCI` -> 2206.02743
- `Self-RAG Asai arxiv 2310 reflection tokens` -> 2310.11511
- `RETRO Borgeaud arxiv` -> 2112.04426; `Atlas Izacard arxiv` -> 2208.03299
- `RA-DIT retrieval augmented dual instruction tuning Lin` -> 2310.01352
- `REALM Guu arxiv id` -> 2002.08909
- `Retrieval-Augmented Generation Lewis arxiv 2005 RAG` -> 2005.11401
- `In-Context RALM Ram arxiv 2302` -> 2302.00083
- `REPLUG Shi arxiv id` -> 2301.12652; `FLARE Jiang arxiv id` -> 2305.06983
- `FiD Izacard arxiv id` -> 2007.01282; `GENRE De Cao arxiv id` -> 2010.00904
- `SEAL generative retrieval FM-index Bevilacqua` -> 2204.10628 (via repo README citation)
- `RAG survey Gao arxiv 2312.10997` -> 2312.10997
- `RankRAG arxiv id` -> 2407.02485; `RAFT Zhang arxiv id` -> 2403.10131
- `MiniRAG small language models arxiv` -> 2501.06713
- `CorpusBrain Chen arxiv id` -> 2208.07652 (plus CorpusBrain++ 2402.16767 and CorpusLM
2402.01176 from the same result set)
- `Dense Passage Retrieval Karpukhin arxiv` -> 2004.04906
- `generative information retrieval survey 2023/2024` -> 2406.01197, 2404.14851,
2306.11397, 2311.09134
- `Bridging Gap Indexing Retrieval DSI Query Generation Zhuang` -> 2206.10128
- `Contriever Izacard arxiv id` -> 2112.09118
- `Generation-Augmented Retrieval Mao arxiv id` -> 2009.08553
- `InstructRetro Wang arxiv` -> 2310.07713
- `Ultron retriever arxiv` -> 2208.09257 (via repo README citation, then abs page opened)
- `How Does Generative Retrieval Scale Pradeep` -> 2305.11841 (ACL page + Google
Research summary + PDF excerpts)
- `DynamicRetriever pre-training model-based IR` -> 2203.00537 (PDF URL only; abs never
opened -> abstain)
- `IncDSI Kishore arxiv` -> 2307.10323 (abs excerpt + PMLR page -> admit)

Repo resolution: `https://api.github.com/repos/<owner>/<repo>` for 20 repos (stars,
pushed_at, license), plus two `search/repositories` calls for REPLUG and Self-RAG
fallbacks. Hugging Face: model page fetched for `nvidia/retro-8b-instruct-4k`.

## Sources used

1. arXiv abs pages (webfetch, full markdown): 2404.14851, 2208.09257 directly; all other
admitted ids verified through fetched abs-page search excerpts (title, authors, date,
abstract) plus the downloaded PDFs themselves.
2. arXiv PDFs (`https://arxiv.org/pdf/<id>`, curl -L): 33 downloaded, all starting with
`%PDF`, sizes 326 KB-10 MB.
3. ACL Anthology pages (FiD, RAG via NeurIPS, REPLUG/NAACL, FLARE/EMNLP, In-Context
RALM/TACL, GAR/ACL, GR-scaling/EMNLP): venue and best-paper facts.
4. OpenReview/PMLR/JMLR pages: Self-RAG (ICLR 2024), RA-DIT (ICLR 2024), InstructRetro
(PMLR v235), REALM (PMLR v119), IncDSI (PMLR v202), Contriever (TMLR), Atlas (JMLR v24),
RAFT (COLM 2024 reviews).
5. GitHub: repo pages (GENRE, SEAL, MiniRAG, DSI-QG, CorpusBrain, GenIR surveys,
WebUltron, RA-DIT artifact) and REST API for stars/pushed_at/license.
6. Hugging Face: `nvidia/retro-8b-instruct-4k` model page (checkpoint artefact).
7. Secondary (venue/project pages only, never for admitted claims): Google Research
blog/posts for RETRO and GR-scaling, Gorilla blog for RAFT, selfrag.github.io mention.

## Counts

Screened 35 (33 admitted, 2 abstained: DynamicRetriever, Distill-Reader-to-Retriever).
Per-lane minimums met: >= 20 screened, >= 8 admitted with PDFs.

## What failed

- arXiv export API: `Rate exceeded` on first query; rested the endpoint and never used
it again — all arXiv discovery via abs pages and PDF URLs.
- Semantic Scholar API: HTTP 429 (`Too Many Requests`) on every call; no S2
citation-graph chaining performed. Chaining done manually via fetched reference lists.
- Three repo resolutions failed with API 404 and were recorded as unverified, not
guessed: swj0419/REPLUG, NVlabs/RankRAG (+ nvidia/RankRAG), selfrag/self-rag (+
selfrag/selfrag, allenai/self-rag). GitHub code search returned only unrelated forks.
- Two recalled arXiv ids from memory were wrong and caught by opening the pages
(2302.00622 and 2202.06997 are unrelated papers, not DSI). No id in the inventory comes
from memory alone: every admitted id was confirmed on its abs page or PDF.
- No sub-3B weights-level joint embedding-plus-generation paper was found; the gap is
recorded in the findings ledger rather than filled.
