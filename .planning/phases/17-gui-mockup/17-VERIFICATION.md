---
phase: 17-gui-mockup
verified: 2026-11-01T00:41:22Z
status: passed
score: 5/5 must-haves verified
covered_files:
  - .planning/phases/17-gui-mockup/17-01-PLAN.md
  - .planning/phases/17-gui-mockup/17-01-SUMMARY.md
  - .planning/phases/17-gui-mockup/17-02-PLAN.md
  - .planning/phases/17-gui-mockup/17-02-SUMMARY.md
  - .planning/phases/17-gui-mockup/17-03-PLAN.md
  - .planning/phases/17-gui-mockup/17-03-SUMMARY.md
  - .planning/phases/17-gui-mockup/17-04-PLAN.md
  - .planning/phases/17-gui-mockup/17-04-SUMMARY.md
  - .planning/phases/17-gui-mockup/17-05-PLAN.md
  - .planning/phases/17-gui-mockup/17-05-SUMMARY.md
  - .planning/phases/17-gui-mockup/17-06-PLAN.md
  - .planning/phases/17-gui-mockup/17-06-SUMMARY.md
  - .planning/phases/17-gui-mockup/17-07-PLAN.md
  - .planning/phases/17-gui-mockup/17-07-SUMMARY.md
  - .planning/phases/17-gui-mockup/17-08-PLAN.md
  - .planning/phases/17-gui-mockup/17-08-SUMMARY.md
  - .planning/phases/17-gui-mockup/17-09-PLAN.md
  - .planning/phases/17-gui-mockup/17-09-SUMMARY.md
  - .planning/phases/17-gui-mockup/17-10-PLAN.md
  - .planning/phases/17-gui-mockup/17-10-SUMMARY.md
  - .planning/phases/17-gui-mockup/17-11-PLAN.md
  - .planning/phases/17-gui-mockup/17-11-SUMMARY.md
  - .planning/phases/17-gui-mockup/17-12-PLAN.md
  - .planning/phases/17-gui-mockup/17-12-SUMMARY.md
  - .planning/phases/17-gui-mockup/17-13-PLAN.md
  - .planning/phases/17-gui-mockup/17-13-SUMMARY.md
  - databasise/pyproject.toml
  - docs/gui/API-INVENTORY.md
  - docs/gui/GAP-ROUTES.json
  - docs/gui/INVENTORY-MAP.json
  - docs/gui/MOCK-IDS.json
  - docs/gui/MOCKUP-APPROVAL.md
  - docs/gui/refusals.json
  - mockups/build.py
  - mockups/operator-console.html
covered_digest: "v3:sha256:6c79aa78e61bca3ef9e53f7eb95dca14913c89a643fd3ba1b076a374cbd5c486"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 5/5
  previous_verified: 2026-10-31T00:00:00Z
  trigger: "fingerprint staleness after Phase 18 edited databasise/pyproject.toml, docs/gui/API-INVENTORY.md and mockups/build.py"
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 17: GUI Mockup Verification Report

**Phase Goal:** The operator can click through a complete static mockup of the six console screens on fixture data shaped like the real API, with every control id-stamped and every missing backend visibly marked
**Verified:** 2026-10-31 (initial), re-verified 2026-11-01T00:41:22Z
**Status:** passed
**Re-verification:** Yes, after a Phase 18 fingerprint staleness trip (initial verification 2026-10-31 passed 5/5; see "Re-verification 2026-10-31 (Phase 18 staleness)" below)

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | One static file opens from file:// with no network, six screens switchable, health indicator in header, every control/region has a unique data-mock-id matching the checked-in list | VERIFIED | `mockups/operator-console.html` (7009 lines) exists; own Playwright probe over file:// recorded 0 non-file requests and 0 page errors; six `shell.nav.*` entries found; `docs/gui/MOCK-IDS.json` holds 623 ids; test_gui_01_shell, test_gui_02_ids (set equality, html.parser walk equals scripts/mockup-id-check.py, id-less-sample predicate proof) pass; no external http(s) src/href in the file |
| 2 | Every API-INVENTORY section 3 / 5.1 control is present and usable on fixtures; routes that do not exist carry data-needs-backend naming the route and a visible badge | VERIFIED | All 20 routes in `docs/gui/GAP-ROUTES.json` appear as `data-needs-backend` values in the built file (54 wrappers); every GUI-03 route named in REQUIREMENTS.md is present (aliases, history, traces, promote/preview, info, wirings, selectors/resolve, refusals, graph/nodes, graph/node, chunks, stores/counts, jobs, corpus filter/sort, pipeline, cancel, reprocess, resolve-batch); operator-kind set is computed against `create_app(operator=True)` minus `create_app()` at test time (test_gui_03); test_inventory_map covers the 17-13 INVENTORY-MAP |
| 3 | Query & Compare: query run and N-column compare on fixtures show answer, badges, evidence, tokens, seam events, trace link in every state; client-side blocks for empty text, empty capability, hash alias, multi-member selector, duplicate compare keys | VERIFIED | test_gui_04 (6 tests) and test_gui_05 (6 tests) pass with behavioral assertions (eight state views mutually exclusive, whitespace block, empty capability block, lower-case and `sha256:` upper-case hash alias block, multi-member and invalid raw JSON, `trace_token` null disables link, partial disables Promote, HippoRAG result promotable, six arms in Resolves-to table). My probe confirmed advanced panel starts collapsed and the capability select offers 20 options (17 Effect literals + 3 reads_vector tokens per 17-06). Caveat: see Advisory findings WR-JSA-02/06 |
| 4 | Every screen that issues a call renders the three server error shapes distinctly (typed refusal banner, field errors, server-failure with cause behind a toggle, generic 5xx) | VERIFIED | test_gui_06 parametrised over all six screens injects 422+refusal_type, 502+ForeignEngineRefusalError, 422+detail, 500 and 0, asserts exactly one shape visible, details toggle `aria-expanded`, `aria-invalid` on the offending field, and branching on `refusal_type` over status; catalogue compared by name against a recursive `SeamRefusalError.__subclasses__()` walk with no hard-coded count (embedded and `docs/gui/refusals.json`) |
| 5 | Walkthrough of evidence/trace inspection, paste/upload ingest with jobs and delete, corpus and health, ledger promote form and alias timeline (Retire disabled on active row, active rollback target, tombstoned rows), graph/vector browser by selector, each with client-side pre-checks | VERIFIED | test_gui_07 to test_gui_11 pass (6+7+6+6+7 nodes). Read test_gui_10 directly: Retire disabled on slots 1/2/5 with exact tooltips, enabled on slot 3, typed-version gate, `roll back first` link focusing the active row, no preselected origin, partial trace blocks, HippoRAG trace does not (D-07), hash alias blocked. My own probe additionally confirmed what the tests do not (IN-TST-05): selecting trace-1 (Default) and trace-6 (alias prod) shows the "different selectors" warning; a confirmed promote renders the success card with alias, version, record_kind, provenance, generation_ordinal |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `mockups/operator-console.html` | Single built static file | VERIFIED | `python3 mockups/build.py --check` exit 0 (checked-in bytes equal a fresh build from `mockups/src/`); sha256 `bf98e79e...4d20` equals the digest in `docs/gui/MOCKUP-APPROVAL.md` |
| `mockups/build.py` + `mockups/src/` | Reproducible source | VERIFIED | build check above; test_mockup_build passes |
| `docs/gui/MOCK-IDS.json` | Sorted id list | VERIFIED | 623 ids, set-equal to the in-file walk (test) |
| `docs/gui/GAP-ROUTES.json` | Route kind table | VERIFIED | 20 routes, all badged in the file |
| `docs/gui/refusals.json` | Refusal catalogue | VERIFIED | equals runtime subclass set (test) |
| `docs/gui/INVENTORY-MAP.json`, `API-INVENTORY.md` | 17-13 coverage map | VERIFIED | test_inventory_map passes |
| `docs/gui/MOCKUP-APPROVAL.md` | Owner approval record | VERIFIED | verbatim "approved" 2026-10-30, digest matches current file |
| `databasise/tests/gui/*` (conftest + 12 test files) | Browser test suite | VERIFIED | 68 passed under `DATABASISE_REQUIRE_BROWSER=1` (my run, 47.7 s; orchestrator 29.5 s) |
| `databasise/pyproject.toml` | Playwright in dev group | VERIFIED | suite imports and runs against installed Chromium |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `mockups/src/**` | `operator-console.html` | `build.py` | WIRED | `--check` exit 0 |
| `docs/gui/MOCK-IDS.json` | built file | id walk | WIRED | set equality test |
| `docs/gui/GAP-ROUTES.json` | `create_app(operator=True)` | run-time route diff | WIRED | test_gui_03 |
| `docs/gui/refusals.json` | `SeamRefusalError` subclasses | recursive walk | WIRED | test_gui_06 |
| Evidence Open (query/compare/graph chunks) | Evidence Inspector | `window.__mock` events | WIRED (with caveat) | exercised by test_gui_07/11; Open trace link fallback defect is WR-JSB-01 |

### Data-Flow Trace (Level 4)

Not a live-data phase. All data comes from inline fixtures (`#mock-fixtures` script) by design (GUI-01); fixtures are shaped from API-INVENTORY section 3 and checked by test_inventory_map. No DISCONNECTED or HOLLOW_PROP finding; no network fetch exists (0 external requests observed).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| GUI suite | `.venv/bin/python -m pytest tests/gui -q -p no:randomly` with `DATABASISE_REQUIRE_BROWSER=1` | 68 passed | PASS |
| Build reproducible | `python3 mockups/build.py --check` | exit 0 | PASS |
| Id checker | `python3 scripts/mockup-id-check.py` | "skipped (no frozen variant)", by design: D-13 moves `mockup_freeze` to Phase 18's first plan | PASS (n/a) |
| Zero network on file:// | own Playwright probe | 0 external requests, 0 page errors | PASS |
| Mixed-selector warning, promote success card | own Playwright probe | both rendered | PASS |
| Debt markers | grep TBD/FIXME/XXX in `mockups/` | none | PASS |

Regression gate (orchestrator evidence, cited not repeated): full suite 3128 passed, 0 failed.

### Probe Execution

No phase-declared probe scripts. Step 7c: SKIPPED.

### Requirements Coverage

All 11 phase IDs are declared in PLAN frontmatter and map to Phase 17 in REQUIREMENTS.md; no orphans.

| Requirement | Source Plan(s) | Status | Evidence |
|-------------|----------------|--------|----------|
| GUI-01 | 17-01, 17-02, 17-13 | SATISFIED | six screens, header health, file://, 0 network |
| GUI-02 | 17-01, 17-02, 17-03 (contrib), 17-13 | SATISFIED | 623 ids, set equality, `data-mock-variant`, checker equality; `mockup_freeze` write deferred to Phase 18 per amended text (D-13) |
| GUI-03 | 17-03, 17-12, 17-13 | SATISFIED | 20 routes badged, kinds verified against the app |
| GUI-04 | 17-04, 17-06, 17-13 | SATISFIED | see truth 3 |
| GUI-05 | 17-04, 17-07, 17-13 | SATISFIED with advisory (WR-JSA-02, WR-JSA-06) | builder, key preview, duplicate/zero/one-row messages, tabs below 768 px, HippoRAG promotable |
| GUI-06 | 17-04, 17-06, 17-11, 17-13 | SATISFIED | see truth 4 |
| GUI-07 | 17-05, 17-08, 17-13 | SATISFIED with advisory (WR-JSB-01) | test_gui_07 |
| GUI-08 | 17-05, 17-09, 17-13 | SATISFIED with advisory (WR-JSB-02) | test_gui_08 |
| GUI-09 | 17-05, 17-10, 17-13 | SATISFIED | test_gui_09 (loading/poll/paging untested, IN-TST-07) |
| GUI-10 | 17-05, 17-11, 17-13 | SATISFIED | see truth 5 |
| GUI-11 | 17-05, 17-12, 17-13 | SATISFIED | test_gui_11, every graph control wrapped |

Note: REQUIREMENTS.md traceability rows still read `Pending` and the BAK completion gate lists GUI-01..11 as open; flipping both is an orchestrator/owner action after this verdict, not a code gap.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `mockups/src/**` | n/a | no TBD/FIXME/XXX | none | clean |
| `mockups/src/js/20-query.js` | 246 | unvalidated raw-selector member types (WR-JSA-01) | Warning | uncaught TypeError for `{"capability":"x"}`; multi-member block still works |
| `mockups/src/js/21-compare.js` | 336 | Compare.run has no blocker guard; the mock state switcher re-enables Run (WR-JSA-02) | Warning | duplicate-key block holds on every real user path (key edit, add row); bypass needs the mock-only state switcher |
| `mockups/src/js/21-compare.js` | 366 | every Run column uses the q-success body (WR-JSA-06) | Warning | columns on Run show identical data; per-arm bodies exist and load via the `cmp-3col` fixture, which the HippoRAG promote test uses |
| `mockups/src/js/30-evidence.js` | 443 | Open trace falls back to the Query link (WR-JSB-01) | Warning | wrong or stale trace for graph chunk openers |
| `mockups/src/js/40-documents.js` | 603 | Keep/Escape does not abort the pending delete (WR-JSB-02) | Warning | mock confirm timer is 300 ms |

### Advisory (disposition)

17-REVIEW.md lists 39 findings (0 critical, 17 warning, 22 info), all `open` in 17-REVIEW-DISPOSITION.md. I read WR-JSA-01/02/03/04/05/06, WR-JSB-01/02 and IN-TST-04..06 in full. None removes a control, a badge, an id or a requirement clause; each is a behavioural defect in the frozen mockup's JavaScript or a test-strength gap. They do not fail a must-have, because every must-have behavior was observed on its normal user path. The owner reviewed and approved the file with these in place (MOCKUP-APPROVAL.md), and Phase 18 D-16/D-17 absorbs the JS findings into the live copy. 17-UI-REVIEW.md scores 16/24 and is advisory.

Test-strength caveat: IN-TST-04/05/06/07 and WR-TST-01..03 mean a few requirement clauses (stream toggle, degraded tooltips, 17-literal count, mixed-selector warning, success card, autocomplete, GUI-09 loading/poll) have no passing test. I covered the mixed-selector warning, success card, 17+3 capability options and collapsed advanced panel directly with a Playwright probe (all PASS). Stream toggle, degraded tooltips, autocomplete and GUI-09 loading/poll were not independently exercised by me; the ids exist in the built file (`query.run.stream`, `query.result.degraded`, a `<datalist>`).

### Human Verification Required

None outstanding. Visual and flow acceptance is already recorded as the owner's verbatim "approved" after a file:// click-through on 2026-10-30, bound to the current sha256.

### Gaps Summary

No gaps. The five roadmap success criteria and all eleven GUI requirements are met in the built mockup; the suite is green (68 GUI tests, 3128 full-suite), the build is reproducible, and the approved digest matches the file on disk. Open review warnings are carried to Phase 18.

### Re-verification 2026-10-31 (Phase 18 staleness)

Trigger: the covered-file fingerprint tripped because Phase 18 (GUI Live) changed three covered files after the initial verdict. Commits `6a36f2d` (18-01) and `65dd699` (18-02); diff read in full with `git diff 6a36f2d~1 HEAD` on the three paths.

What changed:

- `databasise/pyproject.toml`: additive only. `databasise.console` appended to `packages`, plus a package-data line `"databasise.console" = ["operator-console.html"]`. The Playwright dev-group entry this report cites is untouched.
- `docs/gui/API-INVENTORY.md`: one additive paragraph after line 763 describing `databasise-rest --operator --console` and `GET /console`. No section 3 / 5.1 route row changed, so truth 2 and test_inventory_map's input are unaffected.
- `mockups/build.py`: gained `argparse` with `--src DIR` and `--out FILE`, threading `src` through `fixtures_json`, `expand` and `build`. Defaults are the module constants `SRC` and `OUT`, so the zero-argument invocation resolves to `build(SRC)` written to `mockups/operator-console.html`, and `--check` with no other flags compares that same build against that same file. `SHARED_FIXTURES` paths are unchanged. The `--check` branch is read-only (only the non-check branch calls `out.write_bytes`). I did not run the builder, by instruction; the default path's output equivalence is proven by the suite instead (next item).

Re-checks performed:

- `sha256sum mockups/operator-console.html` = `bf98e79e0a0312940963efae9028e708a012021bfc62f51ebdbca57918034d20`, equal to the digest at `docs/gui/MOCKUP-APPROVAL.md` line 5. The frozen mockup is byte-identical to the owner-approved file. `git status --porcelain` on `mockups/`, `docs/gui/` and `databasise/pyproject.toml` is empty (no uncommitted drift).
- `tests/gui` under `DATABASISE_REQUIRE_BROWSER=1`: 68 passed in 128.29 s (`-p no:cacheprovider`). This includes `test_checked_in_mockup_equals_a_fresh_build`, which imports `build.py` and asserts `module.build()` (no arguments, so the new defaults) equals the checked-in file; that is the read-only proof that the zero-arg path still reproduces the approved bytes. test_gui_01..11, test_inventory_map and the id-walk equality test are all in the 68.
- Rows citing `API-INVENTORY.md` (truth 2, "17-13 coverage map" artifact, test_inventory_map) and `pyproject.toml` ("Playwright in dev group") were re-read against the diff; neither diff touches the content those rows depend on.

Result: no regression. All five truths, nine artifacts and five key links hold as recorded above; the goal still holds. Status stays `passed` 5/5. The fingerprint was regenerated over the same covered_files list (`covered_digest` in the frontmatter now reflects the Phase 18 bytes of the three changed files).

---

_Verified: 2026-10-31 (initial); re-verified 2026-11-01T00:41:22Z_
_Verifier: Claude (gsd-verifier)_
