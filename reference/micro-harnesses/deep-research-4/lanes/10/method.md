# Lane 10 method

## Queries run

No general web-search engine was available except a session websearch tool; arXiv API and Semantic Scholar API were tried first and were rate-limited (HTTP 429 on both), so the lane pivoted to:

1. Session websearch for each brief-named benchmark plus reward-line papers (queries: "LOCOMO benchmark ... Maharana 2024", "LongMemEval ... Wu 2410", "BRIGHT ... Su 2024", "tau-bench ... Wen 2024", "BFCL ... Yan Gorilla 2024", "CodeRAG-Bench ... 2024", "Search-R1 ... 2503", "ReAct ... 2210.03629 Yao", "DeepSeekMath ... RLVR ... 2402.03300", "Reflexion ... 2303.11366", "MemBench ...", "vLLM PagedAttention ... Kwon 2309", "Gorilla ... 2305.15334", "R1-Searcher ...", "DeepSeek-R1 ... 2501", "Memory-R1 ... 2025", "SGLang ... Zheng 2024", "ToolSandbox ... Lu", "Sarathi-Serve ... Agrawal", "Berkeley Function Calling Leaderboard arxiv paper ...").
2. arXiv abs pages opened via webfetch for ID confirmation (a recalled LoCoMo id, 2406.16789, proved to be a quantum-optics paper — discarded, correct id 2402.17753 found via search).
3. GitHub API: `api.github.com/repos/...` (core quota exhausted after 1 success: tau-bench) then `api.github.com/search/repositories` (10-call quota, all used) for stars/pushed/license of sglang, vllm, ToolSandbox, gorilla, reflexion, LongMemEval, Search-R1, R1-Searcher, Memory-R1.
4. PMLR page for BFCL opened directly (no arXiv version exists); PDF URL taken from the page's `citation_pdf_url` meta tag after a first guessed URL returned HTML.
5. Hugging Face model/paper pages opened for DeepSeek-R1, R1-Searcher, Memory-R1; ACL Anthology / ICLR / NeurIPS / USENIX / OpenReview / ACM DL pages opened to confirm venues.

## Sources used

arXiv abs pages (primary for all 18 arXiv admits), paper PDFs (all 19 downloaded and `%PDF`-verified), PMLR proceedings page (BFCL), venue proceedings pages (ICLR, NeurIPS, OSDI, ACL Anthology), GitHub API records (10 repos), live leaderboard/blog pages (BFCL, Gorilla — secondary, used only for code location and cost/latency notes).

## Screening counts

- Screened: 38 candidates (19 admitted, 19 abstained; see inventory.tsv).
- Admitted: 19 (18 arXiv + 1 PMLR). Every admitted item was opened at its primary source.
- PDFs filed: 19 in `papers/`, all starting with `%PDF`, named `<id>_<slug<=70>.pdf`.
- Failed: arXiv export API (429), Semantic Scholar API (429), GitHub core API (quota exhausted after tau-bench); worked around per above. Nothing 2025+ was admitted from memory — MemBench, Memory-R1, Search-R1, R1-Searcher, DeepSeek-R1, BFCL all came from fetched pages.

## Naming deviation

`papers/PMLR-v267-patil25a_The_Berkeley_Function_Calling_Leaderboard_BFCL_From_Tool_Use_to_Agenti.pdf` uses the PMLR paper id instead of an arXiv id because BFCL was never posted to arXiv; the PDF bytes are the PMLR open-access file. Documented in findings U5.
