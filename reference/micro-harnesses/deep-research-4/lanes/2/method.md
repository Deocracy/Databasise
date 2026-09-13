# Lane 2 method — ingest-side routing to typed stores

## Queries run
- arXiv HTML search (`arxiv.org/search/?query=...&searchtype=all`, curl, `+`-joined
  terms; the `export.arxiv.org/api/query` endpoint returned `Rate exceeded` for this
  IP, and Semantic Scholar returned HTTP 429, so no Atom/S2 calls succeeded):
  `LoCoMo Maharana`, `LoCoMo long conversation memory benchmark`,
  `AgentMemBench memory management strategies`, `Total Recall serving cost agentic
  memory`, `RuleMem active rule memory conversational`, `Learn to Memorize adaptive
  memory agents`, `FluctlightDB memory model data agents`, `When Does Memory Help
  cost-aware tool-using agents`, `Mem-alpha memory agents alpha`,
  `Memori long-term memory agents benchmark`.
- arXiv abs pages (`arxiv.org/abs/<id>`, curl): title/authors/date/abstract recorded
  for every admitted id before download.
- arXiv full-text HTML (`arxiv.org/html/<id>v1`, urllib): term-frequency checks of
  load-bearing mechanism claims for all 25 admitted papers (e.g. MIRIX "six Memory
  Managers … Meta Memory Manager responsible for task routing"; Mem0 ADD/UPDATE/DELETE
  counts; Zep edge/fact/episode counts; MemOS MemCube/MemScheduler counts).
- GitHub REST: `search/repositories` (MIRIX, Mem0, Graphiti, HippoRAG, A-MEM, Cognee,
  Memory-R1, Hindsight, LongMemEval, MemBench, mem-alpha, Memori, LoCoMo, RAPTOR,
  MemoryBank) and `repos/<owner>/<repo>` for stars/pushed_at/license; raw
  READMEs grepped for `arxiv.org/abs|pdf` links (this is how MIRIX 2507.07957,
  A-MEM 2502.12110, Cognee 2505.24478, Zep 2501.13956, HippoRAG 2502.14802,
  LongMemEval 2410.10813, Memori 2603.19935, MemOS 2507.03724 were pinned).
- Papers with Code API returned non-JSON (blocked); Hugging Face not needed.

## Screening funnel
- Candidates screened: 43 (25 papers admitted + 2 repos admitted + 16 abstained).
- Admitted: 25 papers (PDFs in `papers/`, all verified to start with `%PDF`) + 2
  repository artefacts (Letta platform, Graphiti implementation; no PDF by design).
- Forward chaining: done via repo README paper links and the citing/cited context in
  abstracts, not via the S2 citation API (rate-limited). Two near-miss arXiv ids were
  caught and rejected by opening the abs page (2507.07922 = topos theory, not MIRIX;
  2505.03234 = clinical trials, not HippoRAG 2).

## Failures and limits
- arXiv export API + Semantic Scholar: rate-limited for the whole session.
- No PDF text-extraction toolchain on the machine (no poppler, no pip); body claims
  verified through arXiv HTML instead. Claims that rest only on an abstract are
  worded as such in findings.md.
- GitHub search `total: 0` on retry for MemoryBank owner lookup; MemoryBank repo URL
  left blank (paper-only row). MemGPT repo `cpacker/MemGPT` returns Moved Permanently;
  lineage covered by `letta-ai/letta`.
- 2026-dated papers (AgentMemBench, Total Recall, MERIT, RuleMem, Memori, Chronos)
  are single-version arXiv preprints with no peer-review venue; treated as primary
  for "what the authors report", not as settled results.
- `capability` column convention: store numbers from brief §1 (1 vector, 2 knowledge
  graph, 3 code graph, 4 learning/procedural, 5 facts/SQL/vault), comma-separated
  when a paper spans stores; benchmarks that compare management strategies list all
  stores they evaluate.
