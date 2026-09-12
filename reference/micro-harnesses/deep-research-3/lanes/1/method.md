# Lane 1 method

Lane: fine-tuning small models for structured and constrained generation.
Date: 2026-09-12. Worker: single sub-agent, no further delegation.

## Queries run

- arXiv abs-page verification loop (curl + `<title>` / `citation_author` /
  `citation_date` meta extraction, 2-4 s spacing) for 20 candidate ids. Two recalled
  ids proved wrong on opening and were discarded before admission: 2305.13534
  (a hallucinations paper, not Gorilla) and 2406.03622 / 2409.07726 (unrelated
  papers, not APIGen/ToolACE). Correct ids were recovered via web search and then
  abs-verified: Gorilla 2305.15334, APIGen 2406.18518, ToolACE 2409.00920.
- One early `export.arxiv.org/api/query` search attempt (ToolACE phrase) returned
  off-topic 2025-2026 results; a second API attempt returned HTTP 503. arXiv API
  search was then abandoned in favour of abs-page verification plus web search.
- Semantic Scholar API: one batched query, HTTP 429 (rate-limited, no key).
  Citation-chaining via S2 was therefore not performed; forward/backward chaining was
  done manually from paper reference lists named in fetched content
  (e.g. Hammer cites xLAM/Granite/API-Bank/Tool-Alpaca/Seal-Tools; TinyAgent cites
  LLMCompiler).
- Papers with Code API: two queries, empty/non-JSON responses; abandoned.
- Web search (session provider): 8 queries — APIGen arXiv, ToolACE arXiv, BFCL paper,
  TinyAgent paper, Hammer paper, SynCode paper, NexusRaven-V2, Granite function
  calling, Seal-Tools, Outlines guided generation, FoFo benchmark. Used only to
  locate primary sources; every factual claim was then checked at the primary.
- GitHub REST API (`/repos/{owner}/{repo}`): 17 repo lookups for stars/pushed_at/
  license — gorilla, TinyAgent, Hammer, NexusRaven-V2 (correct org `nexusflowai`
  found via search after `Nexusflow/` 404'd), functionary, outlines, syncode
  (`structuredllm` canonical after `uiuc-focal-lab` 301'd), BFCL-leaderboard guess
  (404, dropped), Hermes-Function-Calling, Seal-Tools, Salesforce/xlam (404, dropped),
  Qwen/Qwen2.5 (404, dropped), guidance-ai/guidance, FoFo, ToolBench guess (404).
- Hugging Face API (`/api/models?search=`): ToolACE (Team-ACE/ToolACE-8B top hit)
  and xlam-function-calling model listings.
- arXiv PDF downloads: 18/18 admitted papers fetched from `https://arxiv.org/pdf/<id`,
  each verified to start with `%PDF`, renamed to `<id>_<slug>.pdf` (slug ≤70 chars,
  non-alphanumerics → underscore).

## Counts

- Screened: 26 candidates (inventory.tsv).
- Admitted: 22 (18 papers with PDFs + BFCL proceedings artefact + 3 code/eval
  artefacts: Functionary, Hermes-Function-Calling, Guidance).
- Abstained: 4 (NexusRaven-V2, Glaive-v2, Gorilla-OpenFunctions-v2, Qwen2.5
  vendor claims) — each with reason in inventory and findings §(c).
- Refutations: 3 (Hammer §5.6 abstention loss; FoFo format/content independence;
  SynCode syntax-vs-grounding split), each tied to a fetched primary source.

## What failed

- arXiv API search (off-topic + HTTP 503), Semantic Scholar (429, no key),
  Papers with Code (empty responses) — see above for fallbacks.
- Four guessed GitHub paths 404/301'd; corrected via search or dropped.
- No sub-3B independent training result could be verified at a primary source
  (Qwen2.5, SmolLM3 tool-call numbers unopened); recorded as abstain, not admitted.
- Venue strings are given as "arXiv preprint" wherever the fetched abs page showed
  no journal reference; only ACL/ICLR/NeurIPS/EMNLP/NLPCC/ICML venues backed by a
  fetched page are named.
