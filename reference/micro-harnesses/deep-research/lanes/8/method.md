# Lane 8 method

## Queries run

arXiv API (`export.arxiv.org/api/query`), each followed by a 3-4s wait:
- `all:"sleep-time compute"` → confirmed 2504.13171.
- `all:"memory consolidation" AND all:"language model"` → 30 hits; surfaced 2608.11775,
  2607.17545, 2606.25161, 2606.03979, 2605.18930, 2603.14517, 2603.11768, 2601.02845,
  2607.29167 and others.
- `all:"self-refine" AND all:"language model"` → surfaced 2607.28576, 2607.22653 and others.
- `all:Expel AND all:agent` → returned empty (API hiccup); ExpeL resolved instead via direct
  abs-page check of recalled id 2308.10144, confirmed by title.
- Per-id abs-page fetches (`arxiv.org/abs/<id>`) for all 40 candidates: title, authors,
  date, GitHub links extracted from page HTML.

Semantic Scholar API: attempted once, got HTTP 429 (rate limited); not used further.
Papers with Code / Hugging Face: not needed; no trained-checkpoint claim in this lane
required them beyond paper statements.

GitHub REST API (unauthenticated): succeeded for mem0ai/mem0, noahshinn/reflexion,
agiresearch/A-MEM and MemOS search (stars, push dates, licenses recorded) before hitting
the 60-req/hr limit (reset ~45 min out). Remaining repos verified by HTTP existence check
(`curl` status 200/301 on `github.com/<owner>/<repo>`); stars/licenses recorded as n/a
rather than invented. Official repo URLs taken from paper-PDF `strings | grep github.com`
output (primary source) or the arXiv abs page.

PDF download: `https://arxiv.org/pdf/<id>` for each of the 34 admitted papers; every file
checked to start with `%PDF`. Refuted/abstained items were not downloaded, per the brief.

## Counts

- Screened: 40 (34 admit, 2 refute, 4 abstain). Per-lane minimums met (≥20 screened, ≥8 admitted).
- PDFs downloaded: 34 into `papers/`.
- Date range of admitted set: 2016 (EWC) to 2026-08; 15 of 34 are 2025-08 or newer, all from fetched pages.

## What failed

- Semantic Scholar: 429 rate limit; citation chaining not performed — forward-chaining gap.
  Mitigation: used arXiv date-sorted search plus PDF reference-mining for repo discovery.
- GitHub API: rate limit exhausted mid-lane; fell back to HTTP existence checks (no stars,
  push dates, or licenses for 15 repos — marked n/a in inventory).
- Two recalled arXiv ids were wrong (2310.01417 is not ExpeL; 2311.13856 is not H2O);
  both caught by opening the abs page and recorded as abstains.
- Recalled names without sources (RMM, H2O id) could not be verified and were abstained,
  not admitted.
- 2026 papers dominate the novel-consolidation results; most are single-author or
  single-cluster preprints with no released code — treated as design patterns (relevance 1-2)
  unless they had code or a directly reusable mechanism.
