# Lane 4 method

Lane: small models (1B-8B) trained to manage memory or decide retrieval.

## Queries run

- arXiv export API (`export.arxiv.org/api/query`), one phrase at a time with
3-5 s gaps: `MemAgent`, `R1-Searcher`, `ReSearch AND retrieval`, `ti:ReSearch`,
`DeepRetrieval`, `RAG-Gym`. arXiv API rate-limiting caused several empty
responses; every gap was filled via the web-search fallback below.
- Targeted web searches (8 total): ReSearch RL recipe; DeepRetrieval 3B;
RECOMP compressor sizes; FilCo filter sizes; RankRAG repo/training cost;
Adaptive-RAG classifier; CRAG evaluator; RAG-Gym process supervision;
Search-o1 backbone; ReST correct id (2308.08998, after 2308.08920 proved to be
a different paper); RankRAG code release.
- arXiv abs pages (curl, 22 ids): title/author/date match for every screened
candidate; journal-ref field captured where present (none had one).
- ar5iv HTML full text (curl): Mem-alpha (Qwen3-4B backbone, 8B failure note,
repo link), Memory-R1 (LLaMA-3.1-8B + Qwen-2.5-7B backbones), Search-R1,
R1-Searcher(++), RA-DIT, Toolformer, STaR, Self-RAG, FilCo (3B filter + 7B
LoRA exact sizes), ReSearch; MemAgent HTML unavailable (no ar5iv render), so
MemAgent facts came from its repo README instead.
- GitHub REST API: `search/repositories` (2 calls) + `repos/{owner}/{repo}`
(17 calls) for stars, pushed_at, license; renames followed
(Agent-RL/ReSearch -> Agent-RL/ReCall; Self-RAG canonical path is
AkariAsai/self-rag after selfrag/self-rag 404'd; Toolformer has no
facebookresearch repo, 404).
- Hugging Face Hub API (`huggingface.co/api/models?search=`): selfrag,
RAG-Gym, Search-R1 (PeterJinGo), DeepRetrieval, R1-Searcher, ReSearch,
RankRAG, Memory-R1, Mem-alpha artefact checks.
- Semantic Scholar API: attempted twice, 429 rate-limited both times;
abandoned in favor of arXiv + web search. No citation-graph chaining was
possible; forward-chaining was approximated by screening the related-work
families the seed papers cite (RAG-Gym explicitly benchmarks Search-R1 and
R1-Searcher; Mem-alpha cites MemAgent and MEM1).
- Downloaded PDFs: primary-source mining with `strings` + grep for
github.com links and model-size tokens; lossy, so all size claims were
re-confirmed in ar5iv HTML or repo READMEs.

## Counts

Screened 22 (all 10 brief-named seeds for this lane: Mem-alpha, Memory-R1,
MemAgent, Search-R1, ReSearch, R1-Searcher, Self-RAG, RA-DIT, Toolformer, ReST;
plus R1-Searcher++, DeepRetrieval, STaR, RECOMP, FilCo, RankRAG, Adaptive-RAG,
CRAG, RAG-Gym, Search-o1, DSPy, ActiveRAG). Admitted 18; abstained 4 with
reasons in findings.md (c). No `refute` dispositions: nothing screened
contradicts a brief claim outright; three qualifying tensions are listed under
findings.md (b).

## What failed

- Semantic Scholar API 429s; Papers with Code and OpenReview not queried
(time, and coverage already sufficient from arXiv/repo/HF primaries).
- arXiv export API returned empty/error bodies on ~4 queries (rate limiting);
retried with backoff, supplemented by web search.
- ar5iv has no render for MemAgent (2507.02259); facts taken from repo README
(primary project source) instead.
- RankRAG, Memory-R1, STaR, Toolformer: no code/weights found after checking
paper text, PDF link extraction, GitHub API, and HF Hub; recorded as `--`
with recipe-only reuse notes rather than guessed URLs.
- Mem-alpha weights: only an unverified community upload found; recorded as
unverified, not as a released artefact.
- No repository cloning was performed per lane instructions; only
commit-independent facts (stars, push date, license) were recorded.
