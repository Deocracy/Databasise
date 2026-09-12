# Phase 6 Plan 1 — Checkpoint answers (recorded 2026-09-09)

The owner answered Task 1's package-legitimacy checkpoint in full before Task 2 began. This file
records every answer verbatim, mirroring `04-CHECKPOINT-ANSWERS.md`'s format.

## 06-01 Task 1 — Package legitimacy for `igraph`, `numpy`, `scipy` (`blocking-human`)

**Answer: `approved` — all three of `igraph`, `numpy` and `scipy` are confirmed legitimate.**

Recorded evidence, per the owner's verbatim response:

1. `igraph`, `numpy` and `scipy` are all confirmed LEGITIMATE. Their `[SUS]` verdicts in
   `06-RESEARCH.md`'s Package Legitimacy Audit were the sandbox's missing-metadata blind spot
   (`unknown-downloads` / `no-repository` / `too-new`), not a slopsquat signature — the same
   blind spot `05-LEARNINGS.md` recorded and resolved by human confirmation for `mcp` and
   `python-multipart` in Phase 5. Add all three.
2. **Open Question 4 is answered: core.** All three go in `databasise/pyproject.toml`'s
   `[project.dependencies]`, NOT behind a new optional extra. Rationale: HippoRAG 2 is a
   first-class modality of this milestone, not an optional transport like `rest`/`mcp`.
3. The dependency name is `igraph`, never the legacy `python-igraph` distribution.

**Package-by-package verdict:**

- `igraph` — VERIFIED legitimate. Project page (`https://pypi.org/project/igraph/`) links source
  repository `github.com/igraph/python-igraph`; `https://pypi.org/project/python-igraph/`
  describes itself as the legacy distribution of the same project. Depend on `igraph`, never
  `python-igraph`.
- `numpy` — VERIFIED legitimate. Source repository `github.com/numpy/numpy`; already pinned in
  `v1/pyproject.toml` in this same monorepo.
- `scipy` — VERIFIED legitimate. Source repository `github.com/scipy/scipy`; needed by plans
  06-04 and 06-06 for `scipy.stats.bootstrap`, cleared here so those plans carry no second
  checkpoint. Not added to `databasise/pyproject.toml` by this plan — 06-04/06-06 own that edit.

**Dependency placement (Open Question 4): core dependencies.** `igraph>=0.11,<2.0` and
`numpy>=1.24,<3.0` land in `databasise/pyproject.toml`'s `[project] dependencies`, per the owner's
answer above — not behind a new optional extra.

No edit to `databasise/pyproject.toml` was committed before this checkpoint was answered.
