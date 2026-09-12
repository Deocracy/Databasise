---
phase: 06-hipporag-2-side-by-side
verified: 2026-09-12T18:45:00Z
status: gaps_found
score: 5/6 must-haves verified
covered_files:
  - ".planning/REQUIREMENTS.md"
  - ".planning/ROADMAP.md"
  - ".planning/WINDOWS.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-01-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-01-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-02-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-02-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-03-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-03-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-04-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-04-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-05-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-05-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-06-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-06-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-07-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-07-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-08-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-08-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-09-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-09-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-10-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-10-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-11-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-11-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-12-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-12-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-13-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-13-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-14-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-14-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-15-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-15-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-16-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-16-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-17-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-17-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-18-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-18-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-GATE-AMENDMENT.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-PATTERNS.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-RESEARCH.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-REVIEW-FIX.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-REVIEW.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-UAT.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-VALIDATION.md"
  - ".planning/phases/06-hipporag-2-side-by-side/COVERAGE.md"
  - "databasise/clients/openai_compat.py"
  - "databasise/tests/eval/test_aa_run.py"
covered_digest: "v1:sha256:d31a2c70bb12262e630036ba0eff9ba502a64af1aec2a3584f03c1225e11a2ef"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 5/6
  gaps_closed: []
  gaps_remaining:
    - "Owner mints an eval bundle (MACH-02) then runs one A/A calibration reading a p95 floor at both target families with T1 materially narrower than T0 (MACH-03, Falsifier 5) — roadmap Success Criterion 6"
  regressions: []
gaps:
  - truth: "Owner mints an eval bundle (MACH-02) then runs one A/A calibration reading a p95 floor at both target families with T1 materially narrower than T0 (MACH-03, Falsifier 5) — roadmap Success Criterion 6"
    status: failed
    reason: >
      Unchanged from the prior verification round, and correctly so: 06-18 is a paperwork-only
      gap-closure plan whose own must_haves.prohibitions explicitly forbade re-asking the owner
      about the MACH-03 spend, flipping MACH-03/MODAL-01 to Complete, or touching either checkbox.
      No file this round touched aa_run.py, calibration.py, or FALSIFIER-5-EVIDENCE.md. What did
      change: `06-GATE-AMENDMENT.md` (already on file before this run, not authored by 06-18) defers
      MACH-03 a fourth time, to the first gate-adjudicated promotion, which the amendment states lies
      outside this milestone under MACH-09's default posture; 06-18 closed the one remaining tracking
      gap that amendment's own "What this authorises" section named but a prior round never applied —
      ROADMAP Phase 6's Success Criterion 6 now carries a dated annotation citing that amendment,
      independently confirmed present verbatim in `.planning/ROADMAP.md` line 241. This makes the
      FAILED status legible and explained rather than a silent gap, but it does not close it: the
      amendment itself says in as many words "Phase 6 stays `gaps_found`... this record authorises
      Phase 7 to start; it does not mark either phase complete." The observable truth — a real p95
      floor at both target families, T1 materially narrower than T0 — still does not exist anywhere
      in this codebase. `.planning/REQUIREMENTS.md`'s MACH-03 row is independently confirmed still
      `- [ ]` / Pending; no real A/A run has ever executed at either tier.
    artifacts:
      - path: ".planning/phases/06-hipporag-2-side-by-side/06-GATE-AMENDMENT.md"
        issue: "A written, owner-originated deferral of MACH-03 to a point of first need outside this milestone. It authorizes Phase 7 to proceed and explains why the gap is not a defect, but it does not itself discharge the requirement or the roadmap truth — it says so explicitly in its own 'What is not amended' section."
      - path: "databasise/eval/aa_run.py"
        issue: "Genuine, tested, runnable A/A calibration driver (13 tests, independently confirmed passing in the full-suite run) that has still never been invoked with --spend in this environment. No floor exists at either tier."
    missing:
      - "One real A/A run producing two CalibrationResult floors (gold_passage_recall, answer_level_correctness), read against the pre-registered threshold in FALSIFIER-5-EVIDENCE.md, discharging MACH-03/Falsifier 5 either way — deferred by 06-GATE-AMENDMENT.md to the first gate-adjudicated promotion, outside this milestone"
---

# Phase 6: HippoRAG 2 & Side-by-Side Verification Report

**Phase Goal:** Two modalities answer the same corpus behind the same seam and the caller sees both at once — the milestone's proof of swappability (§BP rung 4)
**Verified:** 2026-09-12
**Status:** gaps_found
**Re-verification:** Yes — after gap-closure round 3 (plan 06-18, paperwork-only)

## What changed since the prior verification round

The prior round (5/6, `gaps_found`, dated 2026-09-11) found one FAILED roadmap truth remaining
(SC6/MACH-03) after every code precondition for a real A/A calibration was closed and the owner
declined the spend a third time. One gap-closure plan executed since then:

- **06-18** made three paperwork/hygiene corrections, none of which touch MACH-03's substance:
  1. Appended a dated annotation to Phase 6 Success Criterion 6 in `.planning/ROADMAP.md`, citing
     `06-GATE-AMENDMENT.md`'s fourth deferral of MACH-03. Independently confirmed: the original
     criterion sentence survives byte-for-byte (`grep` for both its opening and closing clauses each
     returns exactly 1), and the annotation contains no strike-through markup — matching the
     amendment's own statement that condition 6 is "re-timed, not withdrawn."
  2. Replaced the stale `**Plans**:` line (previously `17/17`, `4/6`, SC2 FAILED, one open WINDOWS.md
     defect) with `18/18`, `5/6`, SC2 VERIFIED, WINDOWS.md entry id 3 closed, SC6 named as the sole
     remaining FAILED criterion. Independently confirmed present verbatim.
  3. Deleted a redundant module-level `pytestmark = pytest.mark.asyncio` in
     `databasise/tests/eval/test_aa_run.py` that was misapplying itself to 8 sync test functions
     under `asyncio_mode = "auto"`. Independently re-ran `tests/eval/test_aa_run.py` directly: `15
     passed in 1.59s`, no warnings clause — matching the plan's claimed baseline exactly (7 async + 8
     sync tests present, `import pytest` retained for its 5 remaining call sites).

Net effect: **no roadmap truth changed status this round.** SC6/MACH-03 remains FAILED — this was
expected and, per the run context governing this verification, is not to be treated as an
unexplained gap: `06-GATE-AMENDMENT.md` (a pre-existing document this plan did not author) already
records the owner's fourth deferral of MACH-03, and 06-18's own prohibitions explicitly forbade
touching MACH-03/MODAL-01's checkboxes or re-raising the spend question. What 06-18 added is
legibility: a reader of the ROADMAP no longer has to go looking for the amendment to learn that SC6
was re-timed rather than simply missed.

**One frontmatter/body inconsistency in `06-18-SUMMARY.md`, resolved here in favor of the checkbox.**
The SUMMARY's frontmatter carries `requirements-completed: [MACH-03]`, but its own body states the
opposite plainly: the `update_requirements` step was deliberately skipped, `.planning/REQUIREMENTS.md`
was never opened by any task, and the plan's own prohibitions forbade flipping MACH-03. Independently
confirmed: `.planning/REQUIREMENTS.md` line 17 still reads `- [ ] **MACH-03**` (unchecked), and the
requirements table still lists `| MACH-03 | Phase 6 | Pending |`. Ground truth is the checkbox state,
not the frontmatter label — `requirements: [MACH-03]` in the PLAN linked this plan to paperwork
*about* the requirement (the SC6 annotation), not its discharge. MACH-03 is scored Pending/gap below,
consistent with the checkbox and with the phase's own gate discipline.

## Goal Achievement

### Observable Truths (roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | HippoRAG 2 runs as thirteen fitted node positions, no opaque core left, whole-graph PPR via §14.2 bulk-export into native igraph/prpack, index-side depth stays `opaque` until parity shown | ✓ VERIFIED | Unchanged this round — no file in 06-18's `files_modified` touches `base.json`'s node inventory, HippoRAG's positions, or the graph-export path. Regression: full suite (below) includes this area and passed clean. |
| 2 | LightRAG and HippoRAG 2 run on one corpus, isolated stores, outputs structurally comparable | ✓ VERIFIED | Unchanged this round. `.planning/REQUIREMENTS.md` MODAL-05 row independently confirmed `Complete`; `06-18` touched neither `databasise/seam/engine.py` nor the cross-modality harness. |
| 3 | Caller sends one query against two or more modalities, receives per-arm results keyed by caller-supplied selectors, no verdict, single arm degenerates to a run | ✓ VERIFIED | Unchanged this round — `Databasise.compare`, `POST /compare`, MCP `compare` tool untouched by 06-18's `files_modified` list (`.planning/ROADMAP.md`, `databasise/tests/eval/test_aa_run.py` only). `.planning/REQUIREMENTS.md` API-08 row independently confirmed `Complete`. |
| 4 | The first genuine seam call records F-14's outcome either way | ✓ VERIFIED | Unchanged this round — `F-14-SEAM-INVARIANCE.md`'s only commit predates this round entirely (06-03), and 06-18 did not touch it. |
| 5 | Mutable-store components have a defined snapshot/reset protocol or are recorded as permanently excluded — F-07 discharged | ✓ VERIFIED | Unchanged this round — `.planning/REQUIREMENTS.md` MACH-10 row independently confirmed `Complete`; 06-18 did not touch `F-07-MUTABLE-STORE-DISPOSITION.md` or the exclusion enforcement path. |
| 6 | Owner mints an eval bundle (MACH-02) then runs one A/A calibration reading a p95 floor at both target families with T1 materially narrower than T0 (MACH-03, Falsifier 5) | ✗ FAILED | MACH-02 unchanged, satisfied (`Complete`). MACH-03 independently confirmed still `- [ ]` Pending in `.planning/REQUIREMENTS.md`. No real A/A run has executed at either tier; no floor exists. `06-GATE-AMENDMENT.md` (pre-existing, owner-originated) defers this a fourth time to the first gate-adjudicated promotion, outside this milestone, and 06-18 made that deferral legible on SC6's own text. Falsifier 5 stays open, not failed. See Gap 1. |

**Score:** 5/6 truths verified (0 present-but-behavior-unverified) — unchanged from the prior round.

### Requirements Coverage

Phase requirement IDs (from PLAN frontmatter across all 18 plans, cross-referenced against
`.planning/REQUIREMENTS.md`'s "Phase 6" rows — the two sets match exactly, no orphans):

| Requirement | Description (abbreviated) | Status | Evidence |
|---|---|---|---|
| MODAL-04 | HippoRAG 2 fully decomposed, 13 node positions, whole-graph PPR | ✓ SATISFIED | `.planning/REQUIREMENTS.md`: `Complete`. Unchanged this round. |
| MODAL-05 | LightRAG + HippoRAG 2 side-by-side on one corpus, F-14 outcome recorded | ✓ SATISFIED | `.planning/REQUIREMENTS.md`: `Complete` (06-15's real cross-modality run). Unchanged this round. |
| API-08 | Caller runs one query against 2+ modalities, per-arm results keyed by caller selectors | ✓ SATISFIED | `.planning/REQUIREMENTS.md`: `Complete`. Unchanged this round. |
| MACH-10 | F-07 discharged: mutable-store snapshot/reset protocol or permanent-exclusion | ✓ SATISFIED | `.planning/REQUIREMENTS.md`: `Complete` (owner-confirmed 06-11). Unchanged this round. |
| MACH-02 | Eval bundle stood up per RIG §EV.1, both §EV.2 target families | ✓ SATISFIED | `.planning/REQUIREMENTS.md`: `Complete`. Unchanged this round. |
| MACH-03 | First A/A calibration per RIG §AA.1, Falsifier 5 pass criterion | ✗ BLOCKED | `.planning/REQUIREMENTS.md`: `- [ ] Pending`, four dated deferral notes, most recent citing `06-GATE-AMENDMENT.md`. No real run has executed. This is the phase's one unresolved requirement. |

No orphaned requirements: `grep -n "| Phase 6 |" .planning/REQUIREMENTS.md` returns exactly these six
rows, matching the six requirement IDs supplied for this verification.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| (none) | — | `grep -nE "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER"` over both files 06-18 modified (`.planning/ROADMAP.md`, `databasise/tests/eval/test_aa_run.py`) returns no matches | — | No debt markers introduced this round. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| `test_aa_run.py`'s asyncio-mark removal did not change its pass/fail set (7 async + 8 sync tests) | `cd databasise && uv run pytest -q tests/eval/test_aa_run.py` | `15 passed in 1.59s`, no warnings clause | ✓ PASS |
| `pytestmark`/`@pytest.mark.asyncio` genuinely absent from the file; `import pytest` retained | `grep -c pytestmark` → 0; `grep -c '^import pytest'` → 1; `grep -c '^async def test_'` → 7; `grep -c '^def test_'` → 8 | matches plan's claimed counts exactly | ✓ PASS |
| SC6's original sentence survives the annotation append, verbatim | `grep -n "MACH-03 is re-timed a fourth time" .planning/ROADMAP.md` | single match; both the original opening clause (`both §EV.2 target families (MACH-02), then runs one A/A calibration`) and closing clause (`Falsifier 5, MACH-03, carried forward from Phase 3 per`) present in the same line, plus the annotation with no strike-through | ✓ PASS |
| Phase 6's `**Plans**:` line reports 18/18, 5/6, SC2 VERIFIED, no stale `17/17` line remains | `grep -c '^\*\*Plans\*\*: 18/18' .planning/ROADMAP.md` → 1; `grep -c '^\*\*Plans\*\*: 17/17' .planning/ROADMAP.md` → 0 | as expected | ✓ PASS |
| MACH-03/MODAL-01 checkboxes still unchecked (not flipped by this round) | `grep -n "^- \[.\] \*\*MACH-03\*\*\|^- \[.\] \*\*MODAL-01\*\*" .planning/REQUIREMENTS.md` | both `- [ ]` | ✓ PASS |
| The three claimed commits exist in history | `git log --oneline --all \| grep -E "9185a3c\|cfc3cc5\|fa2077d"` | all three found, each with the stated subject | ✓ PASS |

Full-suite regression evidence (already collected by the orchestrator this run, per its own note, and
spot-confirmed above at the single-file level rather than re-run in full per the "run the full suite
at most once" constraint): `cd databasise && uv run pytest -q` → `1068 passed, 1 skipped` with zero
warnings, run twice (post-merge and cross-phase regression gates), both clean.

### Probe Execution

Not applicable — no `scripts/*/tests/probe-*.sh` files exist in this project and none are referenced
by any Phase 6 plan or the roadmap's success criteria.

## Deferred Items

No items deferred to a **later phase within this milestone**. SC6/MACH-03's deferral target — "the
first gate-adjudicated promotion" — is explicitly named by `06-GATE-AMENDMENT.md` as lying **outside
this milestone** (Phase 7 builds only the operator-asserted path under MACH-09's default posture), so
Step 9b's later-phase-in-roadmap matching does not apply here: no phase in `.planning/ROADMAP.md`
claims to close this gap. It remains a real, open gap against the roadmap's own Success Criterion 6
text, documented and explained by a written owner-originated amendment rather than left silent — the
distinction the gaps section above and this note both preserve.

## Human Verification Required

None. All six roadmap truths are resolvable from the codebase and `.planning/REQUIREMENTS.md`'s own
checkbox/status ledger; no visual, real-time, or subjective-judgment item is outstanding for this
phase's own scope.

## Gaps Summary

One gap remains, unchanged in substance from the prior round and expected to remain unchanged per the
governing amendment: **SC6/MACH-03** — no real A/A calibration has ever run, so no p95 floor exists at
either tier, and Falsifier 5 stays open rather than passed or failed. Every code precondition for that
run is closed and tested (judge-identity resolution, cost-bounded corpus ingest, the `aa_run.py`
driver, a pre-registered "materially narrower" threshold); the only missing piece is the owner's
authorization of the real spend, now formally deferred a fourth time by `06-GATE-AMENDMENT.md` to a
point of first need — the first gate-adjudicated promotion — that lies outside this milestone
entirely. This round's own plan (06-18) closed a paperwork gap (SC6 carried no annotation pointing to
that amendment) without attempting to close the substantive one, exactly as its own prohibitions
required. Phase 6 therefore correctly stays `gaps_found`: the amendment authorizes Phase 7 to proceed
without waiting on this gap, but does not itself mark Phase 6 complete, and this report does not treat
it as complete.

---

_Verified: 2026-09-12_
_Verifier: Claude (gsd-verifier)_
