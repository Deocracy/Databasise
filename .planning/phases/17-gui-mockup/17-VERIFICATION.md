---
phase: 17-gui-mockup
verified: 2026-11-01T17:07:57Z
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
covered_digest: "v3:sha256:3bb20dec3311596d5d12bf9a2e88c2a97117e696ca9fb1361469ec407c9bccc5"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 5/5
  previous_verified: 2026-11-01T07:20:43Z
  trigger: "owner re-freeze in commit cda59dc3: mockups/operator-console.html rebuilt with the 52-type refusal catalogue (adds NonEncodableTextError) and re-frozen as console-a; new sha256 3ac0e278c929ba41179249a47606edb910ae4b6032b1d0acb9fc19a739c0c837 recorded in docs/gui/MOCKUP-APPROVAL.md"
  gaps_closed:
    - "Owner item resolved: the frozen mockup's embedded refusal catalogue now matches the code (52 types); the three locked tests pass again"
  gaps_remaining: []
  regressions: []
---

# Phase 17: GUI Mockup Verification Report

**Phase Goal:** The operator can click through a complete static mockup of the six console screens on fixture data shaped like the real API, with every control id-stamped and every missing backend visibly marked
**Verified:** 2026-10-31 (initial), re-verified 2026-11-01T00:41:22Z (Phase 18 staleness), re-verified 2026-11-01T07:20:43Z (audit fixes), re-verified 2026-11-01T17:07:57Z (owner re-freeze)
**Status:** passed (goal holds, 5/5; the owner action raised at the 2026-11-01 audit-fixes re-verification is resolved by the owner re-freeze in commit `cda59dc3`, see "Re-verification 2026-11-01 (owner re-freeze)")
**Re-verification:** Yes, three times: after a Phase 18 fingerprint staleness trip (initial verification 2026-10-31 passed 5/5; see "Re-verification 2026-10-31 (Phase 18 staleness)" below), after the 2026-11-01 audit bug-fix commits changed `docs/gui/refusals.json` (see "Re-verification 2026-11-01 (audit fixes)" below), and after the owner re-froze the mockup on 2026-11-01 (see "Re-verification 2026-11-01 (owner re-freeze)" below)

_Earlier status line (2026-11-01T07:20:43Z, kept verbatim):_ **Status:** human_needed (goal holds, 5/5; one owner action pending: rebuild and re-freeze the mockup against the 52-type refusal catalogue, see "Re-verification 2026-11-01 (audit fixes)")

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
| `mockups/operator-console.html` | Single built static file | VERIFIED | `python3 mockups/build.py --check` exit 0 (checked-in bytes equal a fresh build from `mockups/src/`); sha256 `bf98e79e...4d20` equals the digest in `docs/gui/MOCKUP-APPROVAL.md`. Re-frozen 2026-11-01 by the owner (commit `cda59dc3`): sha256 is now `3ac0e278...c837`, equal to the digest in `docs/gui/MOCKUP-APPROVAL.md`; build equality re-proven by `test_checked_in_mockup_equals_a_fresh_build` (in the 68/68 run) |
| `mockups/build.py` + `mockups/src/` | Reproducible source | VERIFIED | build check above; test_mockup_build passes |
| `docs/gui/MOCK-IDS.json` | Sorted id list | VERIFIED | 623 ids, set-equal to the in-file walk (test) |
| `docs/gui/GAP-ROUTES.json` | Route kind table | VERIFIED | 20 routes, all badged in the file |
| `docs/gui/refusals.json` | Refusal catalogue | VERIFIED | equals runtime subclass set (test) |
| `docs/gui/INVENTORY-MAP.json`, `API-INVENTORY.md` | 17-13 coverage map | VERIFIED | test_inventory_map passes |
| `docs/gui/MOCKUP-APPROVAL.md` | Owner approval record | VERIFIED | verbatim "approved" 2026-10-30, digest matches current file. Re-freeze 2026-11-01: digest updated from `bf98e79e...4d20` to `3ac0e278...c837` with a `refrozen:` line and a "Re-freeze 2026-11-01" note; still matches the file on disk |
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

None outstanding. Visual and flow acceptance is already recorded as the owner's verbatim "approved" after a file:// click-through on 2026-10-30, bound to the current sha256. (Re-frozen 2026-11-01 by the owner: the approval record now binds sha256 `3ac0e278...c837`.)

#### Resolved 2026-11-01: rebuild and re-freeze the mockup against the 52-type refusal catalogue

Raised at the 2026-11-01 (audit fixes) re-verification as owner item 1 and resolved by the owner in commit `cda59dc3`; see "Re-verification 2026-11-01 (owner re-freeze)" below for the evidence. The original item is kept verbatim as the record:

> ### 1. Rebuild and re-freeze the mockup against the 52-type refusal catalogue
>
> **Test:** Run `python3 mockups/build.py` (owner only; the verifier must not), then from `databasise/` run `tests/gui/test_gui_06_errors.py` and `tests/gui/test_mockup_build.py` under `DATABASISE_REQUIRE_BROWSER=1`, click through the rebuilt file over file://, and record the new sha256 in `docs/gui/MOCKUP-APPROVAL.md`.
> **Expected:** `test_refusal_catalogue_matches_the_code_and_the_mockup`, `test_gui_06_four_error_shapes_and_catalogue` and `test_checked_in_mockup_equals_a_fresh_build` pass; the embedded `#mock-fixtures` catalogue lists 52 refusal types including `NonEncodableTextError`; the approval digest matches the new file.
> **Why human:** The frozen page (`bf98e79e...4d20`) is bound to the owner's verbatim approval; rebuilding changes the approved bytes, so only the owner can rebuild, re-approve and re-freeze. This is an owner item, not a code regression: the code and `docs/gui/refusals.json` agree (sync test passes), only the frozen page's embedded copy lags by one entry.

Former frontmatter entry (removed from `human_verification:` at this re-verification, kept verbatim):

> test: "Owner action: rebuild and re-freeze mockups/operator-console.html from mockups/src (python3 mockups/build.py), re-run the three locked tests, then re-record the new sha256 in docs/gui/MOCKUP-APPROVAL.md after a file:// click-through"
> expected: "tests/gui/test_gui_06_errors.py::test_refusal_catalogue_matches_the_code_and_the_mockup, ::test_gui_06_four_error_shapes_and_catalogue and tests/gui/test_mockup_build.py::test_checked_in_mockup_equals_a_fresh_build pass; the embedded #mock-fixtures catalogue lists 52 refusal types including NonEncodableTextError; the approval digest matches the new file"
> why_human: "The frozen page bf98e79e...4d20 is bound to the owner's verbatim approval; a rebuild changes the approved bytes, so only the owner can rebuild, re-approve and re-freeze. The verifier must not run mockups/build.py"

Resolution: all three expected outcomes hold. The three named tests pass inside the 68/68 run; the embedded catalogue lists 52 types including `NonEncodableTextError` (one occurrence in the built file); the approval digest `3ac0e278...c837` equals `sha256sum mockups/operator-console.html`.

### Gaps Summary

No gaps. The five roadmap success criteria and all eleven GUI requirements are met in the built mockup; the suite is green (68 GUI tests, 3128 full-suite), the build is reproducible, and the approved digest matches the file on disk. Open review warnings are carried to Phase 18.

### Re-verification 2026-10-31 (Phase 18 staleness)

Trigger: the covered-file fingerprint tripped because Phase 18 (GUI Live) changed three covered files after the initial verdict. Commits `6a36f2d` (18-01) and `65dd699` (18-02); diff read in full with `git diff 6a36f2d~1 HEAD` on the three paths.

What changed:

- `databasise/pyproject.toml`: additive only. `databasise.console` appended to `packages`, plus a package-data line `"databasise.console" = ["operator-console.html"]`. The Playwright dev-group entry this report cites is untouched.
- `docs/gui/API-INVENTORY.md`: one additive paragraph after line 763 describing `databasise-rest --operator --console` and `GET /console`. No section 3 / 5.1 route row changed, so truth 2 and test_inventory_map's input are unaffected.
- `mockups/build.py`: gained `argparse` with `--src DIR` and `--out FILE`, threading `src` through `fixtures_json`, `expand` and `build`. Defaults are the module constants `SRC` and `OUT`, so the zero-argument invocation resolves to `build(SRC)` written to `mockups/operator-console.html`, and `--check` with no other flags compares that same build against that same file. `SHARED_FIXTURES` paths are unchanged. The `--check` branch is read-only (only the non-check branch calls `out.write_bytes`). I did not run the builder, by instruction; the default path's output equivalence is proven by the suite instead (next item).

Re-checks performed:

- `sha256sum mockups/operator-console.html` = `bf98e79e0a0312940963efae9028e708a012021bfc62f51ebdbca57918034d20`, equal to the digest at `docs/gui/MOCKUP-APPROVAL.md` line 5. The frozen mockup is byte-identical to the owner-approved file. `git status --porcelain` on `mockups/`, `docs/gui/` and `databasise/pyproject.toml` is empty (no uncommitted drift). (Re-frozen 2026-11-01 by the owner: the file and the approval record now both read `3ac0e278c929ba41179249a47606edb910ae4b6032b1d0acb9fc19a739c0c837`.)
- `tests/gui` under `DATABASISE_REQUIRE_BROWSER=1`: 68 passed in 128.29 s (`-p no:cacheprovider`). This includes `test_checked_in_mockup_equals_a_fresh_build`, which imports `build.py` and asserts `module.build()` (no arguments, so the new defaults) equals the checked-in file; that is the read-only proof that the zero-arg path still reproduces the approved bytes. test_gui_01..11, test_inventory_map and the id-walk equality test are all in the 68.
- Rows citing `API-INVENTORY.md` (truth 2, "17-13 coverage map" artifact, test_inventory_map) and `pyproject.toml` ("Playwright in dev group") were re-read against the diff; neither diff touches the content those rows depend on.

Result: no regression. All five truths, nine artifacts and five key links hold as recorded above; the goal still holds. Status stays `passed` 5/5. The fingerprint was regenerated over the same covered_files list (`covered_digest` in the frontmatter now reflects the Phase 18 bytes of the three changed files).

### Re-verification 2026-11-01 (audit fixes)

Trigger: the covered-file fingerprint tripped after the 2026-10-31/11-01 debugging and security battery (test-first bug-fix commits `3aafcc62..0d9cabcf`). Of the nine implementation files this report covers, exactly one changed: `docs/gui/refusals.json`, in commit `7a07da50` "fix(09): refuse lone-surrogate text at the input boundary as NonEncodableTextError (422)" (fuzz F2/F3/F4). `git diff 3aafcc62 HEAD --stat` over all nine covered paths lists only that file (8 insertions, 0 deletions). The change digest named in the task (`scratchpad/audit/change-digest.md`) does not exist on disk; the git log and diffs were read directly instead.

What changed:

- `docs/gui/refusals.json`: one additive entry, `{"refusal_type": "NonEncodableTextError", "module": "databasise.seam.refusals", "attribute_keys": ["field"], "http_status": 422}`, inserted in sorted position between `NoRawUploadPathForModalityError` and `NonFiniteNumberError`. 51 -> 52 refusal types. No existing entry's name, attribute keys or status changed.
- The matching runtime class is `databasise/seam/refusals.py:136` `class NonEncodableTextError(SeamRefusalError)` with `self.field`, exported in `__all__` (line 1066); `_status_for` in `databasise/seam/rest.py:151` maps it to the 422 default (no `StoreBusyError`, `ForeignEngineRefusalError` or not-found branch applies). `refusals.py` itself was rewritten across the battery (192 lines since `3aafcc62`, mainly `13fda6a6` bounding every echoed caller value), so the JSON's agreement with the code was re-proven rather than assumed (next list).
- `mockups/operator-console.html` is unchanged: sha256 `bf98e79e0a0312940963efae9028e708a012021bfc62f51ebdbca57918034d20`, equal to the digest in `docs/gui/MOCKUP-APPROVAL.md`. `git status --porcelain` on `mockups/`, `docs/gui/` and `databasise/pyproject.toml` is empty. I did not run `mockups/build.py`, by instruction. `mockups/src/` contains no reference to `NonEncodableTextError`; the catalogue reaches the page only through `build.py` line 26 (`SHARED_FIXTURES["refusals"]`), so the frozen page's embedded `#mock-fixtures` catalogue still holds the 51 types it was built from (grep: `NonEncodableTextError` 0 occurrences in the built file; `NonFiniteNumberError` 1). (Re-frozen 2026-11-01 by the owner in commit `cda59dc3`: sha256 is now `3ac0e278c929ba41179249a47606edb910ae4b6032b1d0acb9fc19a739c0c837`, and the embedded catalogue holds 52 types with `NonEncodableTextError` once.)

Re-checks performed (targeted; the full suite was not re-run here):

- `tests/seam/test_refusal_catalogue_file.py` (the sync test that generates `refusals.json` under `DATABASISE_REGENERATE=1` and otherwise asserts it equals the runtime set with attribute keys and `_status_for` statuses; API-INVENTORY line 783): 1 passed in 0.21 s with `DATABASISE_REGENERATE` unset. This is the evidence that `docs/gui/refusals.json` equals the code after the refusals.py rewrite: names, attribute keys and status codes all unchanged for the 51 prior entries, one correct new entry.
- `tests/gui/test_gui_06_errors.py` + `tests/gui/test_mockup_build.py` under `DATABASISE_REQUIRE_BROWSER=1`: 3 failed, 7 passed in 2.77 s. Passing: all six `test_every_screen_renders_the_four_shapes[screen]` nodes (query, evidence, documents, corpus, ledger, graph render refusal / server-failure / validation / generic shapes, exactly one visible) and `test_branching_is_on_refusal_type_not_status`. Failing, as the task predicted: `test_refusal_catalogue_matches_the_code_and_the_mockup`, `test_gui_06_four_error_shapes_and_catalogue` and `test_checked_in_mockup_equals_a_fresh_build`. In the first two, `_assert_catalogue_matches` passes its first assertion (`_file_refusal_names == runtime`, the JSON equals the code) and fails its second (`_embedded_refusal_names == runtime`) with exactly one extra runtime item, `NonEncodableTextError`; the combined test calls that helper before any screen interaction, so its browser assertions never ran and are covered by the six passing per-screen nodes plus the pre-fix 68/68 runs above. The third fails because a fresh `build()` now embeds 52 types while the checked-in page embeds 51.
- Fixture refusal names the GUI-06 tests inject (`UnknownTraceReferenceError`, `UnknownJobError`, `ForeignEngineRefusalError`) and `StoreBusyError` are each present once in `docs/gui/refusals.json` and in the built file; the status branches (409 busy, 502/503 fault, 404 not-found set, 422 default) are unchanged in `_status_for`.
- The other eight covered implementation files are byte-identical to the previous verdict, so truths 1, 2, 3, 5, the ids, routes, inventory map, approval record and pyproject rows need no re-check beyond the fingerprint.

Rows above superseded by this subsection as of 2026-11-01T07:20:43Z (kept verbatim as the record of the earlier passes): the artifact rows "`python3 mockups/build.py --check` exit 0" and "test_mockup_build passes", the key-link row "`--check` exit 0", the spot-check rows "GUI suite 68 passed" and "Build reproducible exit 0", and the key-link row "`docs/gui/refusals.json` -> `SeamRefusalError` subclasses, test_gui_06". Today's state: the JSON-to-code link is WIRED (sync test), the JSON-to-frozen-page link lags by one entry, and the build-equality check fails until the owner rebuilds. 65 of the 68 GUI tests are expected to pass; 3 are owner items.

Result: no code regression. The fixes do not remove, rename or re-status any named refusal, add no unvalidated input path (the new refusal tightens validation at the boundary), and do not touch the store lifecycle this phase's mockup depends on (the mockup has no backend). All five truths hold: truth 4's rendering behaviour is proven by the passing per-screen nodes and its catalogue clause by the sync test on the JSON; the frozen page's embedded copy is one entry behind. The goal still holds (the operator can click through the six screens; "Show in refusal catalogue" would find no entry only for a `NonEncodableTextError` banner, a 422 the mockup never fixtures). Score stays 5/5. Status moves from `passed` to `human_needed` solely because a non-empty human list exists: the owner must rebuild and re-freeze the mockup (and re-record the approval digest) so the three locked tests go green again. The fingerprint was regenerated over the same covered_files list; no new source file was added, because `databasise/seam/refusals.py` was already an implicit dependency via the sync test, and the JSON is the artifact this phase owns.

### Re-verification 2026-11-01 (owner re-freeze)

Trigger: the owner resolved the audit-fixes owner item in commit `cda59dc3` "chore(17): owner re-freeze of mockup console-a with the 52-type refusal catalogue". `git show cda59dc3 --stat` lists five files: `docs/gui/MOCKUP-APPROVAL.md` (+6/-1), `mockups/operator-console.html` (+1/-1), and three BAK bookkeeping files outside this report's coverage. Two covered files changed; the other seven covered implementation files are untouched by the commit.

What changed:

- `mockups/operator-console.html`: a one-line diff (`git diff --numstat` 1/1), the `<script type="application/json" id="mock-fixtures">` line. I parsed the fixture JSON from both revisions (`git show cda59dc3~1:` and `cda59dc3:`): the only differing fixture key is `refusals`; it goes from 51 to 52 entries, adding exactly `{"refusal_type": "NonEncodableTextError", "module": "databasise.seam.refusals", "attribute_keys": ["field"], "http_status": 422}` (identical to the `docs/gui/refusals.json` entry) and removing none; the 51 prior entries are unchanged in content and order. With the fixture block masked out, the two pages are byte-identical, so no screen, control, style or script changed. The sorted `data-mock-id` attribute lists are equal between revisions, and the `data-needs-backend` attribute lists are equal. `NonEncodableTextError` occurs once in the new page.
- `docs/gui/MOCKUP-APPROVAL.md`: `sha256:` changed from `bf98e79e0a0312940963efae9028e708a012021bfc62f51ebdbca57918034d20` to `3ac0e278c929ba41179249a47606edb910ae4b6032b1d0acb9fc19a739c0c837`; added `refrozen: 2026-11-01 by the owner (freeze-variant console-a)` and a "Re-freeze 2026-11-01" section naming the previous digest. `approved_commit`, the 2026-10-30 approval line, `ids: 623` and the verbatim approval text are unchanged.

Re-checks performed:

- `sha256sum mockups/operator-console.html` = `3ac0e278c929ba41179249a47606edb910ae4b6032b1d0acb9fc19a739c0c837`, equal to the digest in `docs/gui/MOCKUP-APPROVAL.md`. `git status --porcelain` on `mockups/`, `docs/gui/` and `databasise/pyproject.toml` is empty.
- From `databasise/`, with `PLAYWRIGHT_BROWSERS_PATH=$HOME/.cache/databasise/playwright-browsers` and `DATABASISE_REQUIRE_BROWSER=1`: `.venv/bin/python -m pytest tests/gui -q -p no:cacheprovider` -> 68 passed in 26.08 s. This includes the three tests that failed at the audit-fixes re-verification (`test_refusal_catalogue_matches_the_code_and_the_mockup`, `test_gui_06_four_error_shapes_and_catalogue`, `test_checked_in_mockup_equals_a_fresh_build`): the embedded catalogue equals the runtime `SeamRefusalError` subclass set again, and the checked-in page equals a fresh in-process `build()`.
- `python3 scripts/mockup-id-check.py --root .` exits 0. The Phase 18 freeze now exists, so the checker runs against the frozen variant instead of reporting "skipped (no frozen variant)" as the earlier spot-check row records.
- I did not run `mockups/build.py` (not even `--check`), by instruction; build equality is proven by `test_checked_in_mockup_equals_a_fresh_build` in the 68.

Rows restored by this subsection (they were marked superseded at 2026-11-01T07:20:43Z): the build-equality artifact and key-link rows, the "GUI suite 68 passed" spot-check row, and the `docs/gui/refusals.json` -> `SeamRefusalError` key link, which is WIRED end to end again (code = JSON = embedded page). Every row above that cites the `bf98e79e` digest now carries a note recording the re-freeze to `3ac0e278` on 2026-11-01.

Result: the owner item is resolved and no regression was found. All five truths, nine artifacts and five key links hold; score 5/5, 0 behavior-unverified. No human item remains (the owner re-froze the page after the rebuild, and the approval record binds the new digest), so status moves from `human_needed` to `passed`. The fingerprint was regenerated over the same covered_files list.

---

_Verified: 2026-10-31 (initial); re-verified 2026-11-01T00:41:22Z (Phase 18 staleness); re-verified 2026-11-01T07:20:43Z (audit fixes); re-verified 2026-11-01T17:07:57Z (owner re-freeze)_
_Verifier: Claude (gsd-verifier)_
