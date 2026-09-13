# Lane 8 method — learning graphs and procedural memory

## Queries run

- arXiv abs pages (`arxiv.org/abs/<id>`, curl, 3 s spacing): 27 ids opened
  and title-checked — 21 admitted (2305.16291, 2303.11366, 2308.10144,
  2409.07429, 2502.12110, 2509.25911, 2512.12818, 2304.03442, 2310.08560,
  2305.17126, 2203.14465, 1506.05908, 2504.07079, 2410.10762, 2503.03704,
  2407.12784, 2402.07867, 2608.23471, 2604.13318, 2201.06953, 2605.12493)
  plus 3 guard rejections (2310.10495, 2405.15283, 2007.12375) and 3
  id-triage checks (2608.23670, 2608.17684, 2603.21357 from the AWM search —
  none the target; target found instead via web search).
- arXiv full-text HTML (`arxiv.org/html/<id>`, curl) term-count checks of
  load-bearing mechanism claims: Voyager skill-library/self-verification/
  curriculum; Reflexion verbal-reinforcement/episodic-memory; ExpeL
  insight/retrieval; Generative-Agents memory-stream/reflection/importance;
  LATM tool-maker/unit-test/dispatcher; PoisonedRAG target-question/
  attacker-injection/black-box/white-box; STaR rationalization/bootstrapping;
  DKT recurrent/knowledge-tracing.
- arXiv HTML search pages (`arxiv.org/search/?query=...`, curl): `"Agent
  Workflow Memory"` (quoted; returned 5 results, none the paper — the true
  id 2409.07429 came from web search) and `ExpeL experiential learners`
  (unquoted export-API path failed; true id 2308.10144 confirmed on abs).
- Web search (session provider, discovery only; every admit re-verified on
  its abs page): Agent Workflow Memory id; MINJA (confirmed 2503.03704,
  NeurIPS 2025 proceedings page); AgentPoison (confirmed 2407.12784, NeurIPS
  2024 poster page); SkillWeaver (confirmed 2504.07079, abs + GitHub);
  AFlow (confirmed 2410.10762, abs + ICLR proceedings page); KT surveys
  (2201.06953 ACM DL page, 2105.15106 abs, 2009.05991 abs).
- GitHub: REST API succeeded once (OSU-NLP-Group/SkillWeaver: 156 stars,
  2025-04-14 push, MIT) before the shared-IP 60/hr quota exhausted;
  remaining star counts taken from repo HTML pages
  (`github.com/<owner>/<repo>`, `stargazerCount` scrape, 2026-09-13,
  approximate): MineDojo/Voyager ~7194, zorazrw/agent-workflow-memory ~471,
  letta-ai/letta 24722 (agrees with lane-2 API), BillChan226/AgentPoison
  ~243, agiresearch/A-mem 1178 (agrees with lane-2 API), BlueBlood6/InjecMEM
  ~2. Licenses/push dates not extractable from scrape are recorded as
  unknown, except A-mem (MIT) and Letta (Apache-2.0) per lane-2 API.
- Semantic Scholar API: unusable the whole session (HTTP 429). arXiv export
  API: `Rate exceeded`. Papers with Code / HF Hub: not needed.

## Screening funnel

- Candidates screened: 30 rows in inventory.tsv (21 papers admitted + 9
  abstained, incl. 3 wrong-id/near-miss guards).
- Admitted: 21 PDFs in `papers/`, all verified to start with `%PDF`
  (filenames `<arxiv-id>_<slug>.pdf`, slug ≤70 chars). No repositories
  cloned; repo facts recorded in-row.
- Forward chaining: via WebXSkill's comparison table (ASI, WALT — both
  abstained, ids unverified), MINJA's reference to PoisonedRAG (admitted),
  and the MINJA/NeurIPS page's reference to AgentPoison (admitted).

## Failures and limits

- No PDF text-extraction toolchain on the machine; body claims verified
  through arXiv HTML term counts instead. Abstract-only numbers (AWM,
  SkillWeaver, AFlow, MINJA, AgentPoison, LongMemEval-V2) are worded as
  author-reported in findings.md.
- GitHub API quota exhausted after 1 repo; page-scraped star counts are
  approximate and dated in the table.
- `capability` column convention follows lane 2 (store numbers from brief
  §1): every learning/procedural item is store 4; guard rows carry 0/blank.
- 2026-dated papers (InjecMEM, WebXSkill, LongMemEval-V2) are single-version
  arXiv preprints with no peer-review venue; treated as primary for "what
  the authors report", not as settled results.
- Two recalled ids failed verification and are kept as guard rows
  (2310.10495 ≠ ExpeL; 2405.15283 ≠ AWM); one assumed id failed (2007.12375
  ≠ AKT). This lane verifies every id digit-by-digit on the abs page.
