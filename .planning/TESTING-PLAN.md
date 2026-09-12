# Testing Plan — post-v1.0, outside any phase

Owner-driven testing carried out of v1.0. This is not a roadmap phase. Each item names its trigger, the exact entry point, and where the result lands. Run items when their trigger fires or when there is time; nothing here blocks the next milestone from starting.

Source of record for the deferrals: `.planning/milestones/v1.0-MILESTONE-AUDIT.md`, `.planning/milestones/v1.0-phases/06-hipporag-2-side-by-side/06-GATE-AMENDMENT.md`, `.planning/milestones/v1.0-phases/07-promotion-rollback/07-GATE-AMENDMENT.md`.

## 1. Owner judgment items (no code, no spend)

| Item | Requirement | What to do | Where it lands |
|---|---|---|---|
| Declared-deviation causes | MODAL-01 | Review the 20 hybrid/local/global excursions listed in `databasise/evidence/DECLARED-DEVIATIONS.md` "Outstanding" and record your own cause for each. Exact commands and JSON shape: 03-UAT.md test 3 (archived under `.planning/milestones/v1.0-phases/03-lightrag-query-side/`). | `databasise/evidence/human_findings.json` → `declared_causes` (replace the two AI-authored entries, add 18) |
| Answer-substance spot-check q1/q2 | MODAL-01 | Run `databasise.parity.run_comparison --arm naive` for q1 and q2, compare against v1's recorded answer, record match / partial / no-match with notes. Commands: 03-UAT.md test 2. | `databasise/evidence/human_findings.json` → `answer_spotchecks` |

Trigger: the parity claim itself (06-GATE-AMENDMENT.md). Both landing mechanisms exist and are tested; only the judgment is missing.

## 2. Real-spend runs

| Item | Requirement | What to do | Where it lands |
|---|---|---|---|
| A/A calibration, Falsifier 5 | MACH-03 | `python -m databasise.eval.aa_run` (dry-run by default; pass the real-spend flag it documents). Produces n paired per-question differences, bootstrap p95 floor keyed `(bundle@v, tier, metric)`. Pass condition, pre-registered: T1 null width materially narrower than T0. | `databasise/evidence/` A/A record; flip MACH-03 in the next milestone's requirements |
| Owner corpus in the eval bundle | HARD-04 | Pick a subset of your own documents; mint with `databasise.eval.bundle.mint_bundle` from a local-only directory. Only hashes and the evidence record are committed (public repo). Open questions when you run it: who authors questions and gold answers; whether `promote()` should refuse without bundle coverage. | new `bundle@v2`, evidence record |

Trigger: the first gate-adjudicated promotion, or whenever you decide to price it. Both require judge spend.

## 3. Nyquist validation (automated, no spend)

Run `/gsd-validate-phase N` for phases 1, 2, 4, 5, 6. Phases 3 and 7 are already compliant. Phase 4 has no VALIDATION.md at all. These reconcile test coverage against each phase's requirements and write VALIDATION.md; they close no product gap but make the coverage record authoritative.

## 4. Doc hardening (no spend)

| Item | Requirement | What to do |
|---|---|---|
| Gate-script vacuous-pass sites | HARD-01 | Fix 5 extraction sites in `parts-check.sh` and 1 in `anatomy-check.sh`. Decide first where the repair lands: upstream `ServerDestroyer/rag-modality-swap-system-model` and re-mirror, in-place with recorded divergence, or project-layer copies. |
| ANATOMY §F / PARTS Appendix A reconciliation | HARD-02 | Link the eight §F rows to their Appendix A dispositions; fix DR-06's contradiction ("Answered" vs "not reached"). Same landing decision as HARD-01. |

## 5. Tech debt worth a test before it becomes reachable

From the v1.0 audit's tech-debt ledger, the items with a real failure mode:

- Phase 7 WR-03: ledger-wide write lock contended by read-only alias lookups; no sqlite timeout tuning, lock-timeout error not wrapped as a refusal. Test: concurrent promote + burst of queries by alias; expect no raw OperationalError.
- Phase 1 CR-01: Faiss flush race drops a write arriving mid-flush. Dormant until Faiss is wired into a live node. Test when that happens.
- Phase 5 WR-02: unchecked tool name forwarded by the codebase-memory-mcp part. Reachable once a wiring declares a config block for it.
- Phase 5 IN-02: IngestDocument validation error loses its refusal shape on both transports.
- Phase 7 WR-04: six-way-promote race test detects at ~88% per run; raise trials if it ever flakes green.

## 6. Full suite baseline

```
cd databasise && uv run pytest -q
```

Baseline at v1.0 close: 1068 passed, 1 skipped.
