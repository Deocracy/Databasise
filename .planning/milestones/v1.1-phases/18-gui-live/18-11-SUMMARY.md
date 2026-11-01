---
phase: 18-gui-live
plan: 11
subsystem: ui
tags: [console, live-build, fixtures, inflight, sse, owner-click-through, ledger, fail-first]

requires:
  - phase: 18-gui-live
    provides: "the live screens of 18-02 to 18-10, the InFlight registry and api() transport (18-03), the SSE stream reader (18-04), the health poll that skips on InFlight.any() (18-07)"
provides:
  - "databasise/console/operator-console.html: the final live build, every present route wired, no screen fixtures embedded (Task 1)"
  - "17-REVIEW-DISPOSITION.md: IN-JSC-05/06/07 read 'n/a in live (fixture-only)' (Task 1)"
  - "R18-07 fixed: a streamed query holds InFlight('query') until the SSE body settles, so the health poll cannot run during the event replay"
  - "LIVE-01 to LIVE-09 linked (test_ref, code_ref), proven fail-first at their RED commits and set to done by scripts/ledger-amend.py; the kit files are left unstaged for the orchestrator"
affects: [18-gui-live]

actuals:
  tokens: 9000
  tasks: 3
  commits: 4
plan_head_before: 8cb88d468af25ac8155716d16849740d3d49b5c3
plan_head_after: 416b5e5e
# commits counts this plan's own commits: Task 1 (252c455, 4e4dc0f) and R18-07 (13dd233, 416b5e5). The range
# plan_head_before..plan_head_after also holds 77 audit and re-verification commits made between Task 1 and the resume.

tech-stack:
  added: []
  patterns:
    - "A raw api() call ends its InFlight entry when the headers arrive; a caller that keeps reading the body takes its own InFlight.begin(kind) and releases it with .then(done, done) at the end of the chain"
    - "A Playwright test that needs an open response body wraps window.fetch in the page (route.fulfill cannot hold a body open) and polls with page.evaluate, because the console's CSP refuses the string eval that wait_for_function uses"

key-files:
  created: []
  modified:
    - databasise/console/src/js/20-query.js
    - databasise/console/operator-console.html
    - databasise/tests/gui_live/test_live_02_query_compare.py
    - .planning/phases/17-gui-mockup/17-REVIEW-DISPOSITION.md
  deleted:
    - databasise/console/src/fixtures/ (ten files, Task 1)

key-decisions:
  - "Owner click-through 2026-11-01: Approved"
  - "Roadmap open question 8: keep the different-stores notice; documents.notice.store-split stays visible, no console change"
  - "The two 18-07 planner assumptions (unknown stores keys appended as rows; unknown counts chips wrap with no cap) accepted as assumed"
  - "The LIVE-03 typed-refusal deviation (multi-member selector is a named refusal, MultiMemberSelectorError banner) acknowledged"
  - "R18-05 alias-arm wording stays store-neutral (a0483f4e)"
  - "R18-07 fixed in this plan (owner: Fix it)"
  - "Debug-trace redaction keeps the literal cause: Phase 12 D-11 and CONTRACT §3/§17 take precedence over Phase 09 D-04; no change"

requirements-completed: [LIVE-01, LIVE-02, LIVE-03, LIVE-04, LIVE-05, LIVE-06, LIVE-07, LIVE-08, LIVE-09]

duration: Task 1 on 2026-10-31; R18-07 and Task 3 about 45 min on 2026-11-01
completed: 2026-11-01
status: complete
---

# Phase 18 Plan 11: Final live build, owner click-through and LIVE row closure Summary

**The live console ships with no screen fixtures and every present route wired; the owner approved the click-through with real clients; R18-07 is fixed test-first so a streamed query blocks the health poll until its SSE body settles; and LIVE-01 to LIVE-09 are linked, proven fail-first at their RED commits and done through the kit script.**

## Accomplishments

- Task 1 (done before this resume, `252c455`, `4e4dc0f`): `databasise/console/src/fixtures/` removed from the live build, LIVE-09 green in the three launch modes, IN-JSC-05/06/07 recorded as `n/a in live (fixture-only)`.
- Task 2: the owner approved the click-through on 2026-11-01 (answers below).
- R18-07 (owner: "Fix it"): `runStream` in `databasise/console/src/js/20-query.js` takes its own `InFlight.begin("query")` and releases it with `.then(done, done)` after `readStream` settles, on success, on a stream error and on abort. The raw `api()` call no longer passes `kind`, so the count is not dropped at the headers. `test_stream_holds_inflight_until_the_body_settles[close|error]` holds the body open after the first evidence event and asserts `InFlight.counts.query == 1`, then closes (success view) or errors (disconnected view) the body and waits for the count to reach 0.
- Task 3: 27 kit commands run one per Bash call, as written in the plan.

## Owner answers (Task 2, 2026-11-01, verbatim)

- Click-through: "Approved".
- A (roadmap open question 8, different-stores notice): "Keep notice". `documents.notice.store-split` stays visible; no console change was needed.
- B (the two 18-07 planner assumptions): "Accept as assumed".
- C (the LIVE-03 typed-refusal deviation): "Acknowledged".
- D (R18-05 wording): "Store-neutral". The wording of `a0483f4e` is kept.
- R18-07: "Fix it". Fixed in `13dd233` (RED) and `416b5e5` (GREEN).
- Debug-trace redaction: "Keep literal cause". Phase 12 D-11 and CONTRACT §3/§17 take precedence over Phase 09 D-04; no change.

## Task Commits

1. Task 1 `252c455` feat(18-11): drop screen fixtures from the live build
2. Task 1 `4e4dc0f` docs(18-11): record fixture-only Phase 17 findings as n/a in live
3. R18-07 RED `13dd233` test(18): streamed query must hold InFlight until the SSE body settles (R18-07 RED)
4. R18-07 GREEN `416b5e5` fix(18): streamed query holds InFlight until the SSE body settles (R18-07)

## Fail-first proof

- R18-07: at `13dd233` both parametrized cases failed with `assert 0 == 1` on `InFlight.counts.query` once the headers had arrived (2 failed). After `416b5e5` they pass.
- LIVE-01 to LIVE-09: proven by `record-fail` below. Every row exited 1 at its RED commit (recorded `"exit": 1`), and every kit call exited 0, so the control run at HEAD in a clean worktree passed.

## Task 3: the 27 kit commands

Every command exited 0 and printed nothing on stdout or stderr. Each wrote one entry to the kit history (versions 916 to 942). The RED sha of each row was checked against the RED line of its SUMMARY before use.

The `--cmd` value of every `record-fail` was:
`'env PYTHONPATH=$PWD PLAYWRIGHT_BROWSERS_PATH=/home/chris/.cache/databasise/playwright-browsers DATABASISE_REQUIRE_BROWSER=1 /home/chris/coding/Databasise-2.0-fully-agnostic-system/databasise/.venv/bin/python -m pytest <TEST> -q -p no:cacheprovider'`

### set (9)

| Row | Command | Output |
|-----|---------|--------|
| LIVE-01 | `python3 scripts/ledger-amend.py --root . set --id LIVE-01 --test-ref databasise/tests/gui_live/test_live_01_serving.py --code-ref databasise/launcher/serve_rest.py` | no output, exit 0 |
| LIVE-02 | `python3 scripts/ledger-amend.py --root . set --id LIVE-02 --test-ref databasise/tests/gui_live/test_live_02_query_compare.py --code-ref databasise/console/operator-console.html` | no output, exit 0 |
| LIVE-03 | `python3 scripts/ledger-amend.py --root . set --id LIVE-03 --test-ref databasise/tests/gui_live/test_live_03_errors.py --code-ref databasise/console/operator-console.html` | no output, exit 0 |
| LIVE-04 | `python3 scripts/ledger-amend.py --root . set --id LIVE-04 --test-ref databasise/tests/gui_live/test_live_04_evidence_trace.py --code-ref databasise/console/operator-console.html` | no output, exit 0 |
| LIVE-05 | `python3 scripts/ledger-amend.py --root . set --id LIVE-05 --test-ref databasise/tests/gui_live/test_live_05_documents.py --code-ref databasise/console/operator-console.html` | no output, exit 0 |
| LIVE-06 | `python3 scripts/ledger-amend.py --root . set --id LIVE-06 --test-ref databasise/tests/gui_live/test_live_06_corpus_health.py --code-ref databasise/console/operator-console.html` | no output, exit 0 |
| LIVE-07 | `python3 scripts/ledger-amend.py --root . set --id LIVE-07 --test-ref databasise/tests/gui_live/test_live_07_ledger.py --code-ref databasise/console/operator-console.html` | no output, exit 0 |
| LIVE-08 | `python3 scripts/ledger-amend.py --root . set --id LIVE-08 --test-ref databasise/tests/gui_live/test_live_08_graph.py --code-ref databasise/console/operator-console.html` | no output, exit 0 |
| LIVE-09 | `python3 scripts/ledger-amend.py --root . set --id LIVE-09 --test-ref databasise/tests/gui_live/test_live_09_badges_ids.py --code-ref databasise/console/operator-console.html` | no output, exit 0 |

The nine `test_ref` values were checked in the kit diff afterwards: one per `test_live_0N` file.

### record-fail (9)

| Row | RED sha (source) | Command | Output | Recorded |
|-----|------------------|---------|--------|----------|
| LIVE-01 | `8e40601` (18-02 Task 1) | `python3 scripts/ledger-amend.py --root . record-fail --id LIVE-01 --at 8e40601 --timeout 900 --cmd '...pytest databasise/tests/gui_live/test_live_01_serving.py -q -p no:cacheprovider'` | no output, exit 0 | v925 check-fail, exit 1 at RED |
| LIVE-02 | `779026a` (18-04 Task 1) | `python3 scripts/ledger-amend.py --root . record-fail --id LIVE-02 --at 779026a --timeout 900 --cmd '...pytest databasise/tests/gui_live/test_live_02_query_compare.py -q -p no:cacheprovider'` | no output, exit 0 | v926 check-fail, exit 1 at RED |
| LIVE-03 | `f31e45a` (18-04 Task 3) | `python3 scripts/ledger-amend.py --root . record-fail --id LIVE-03 --at f31e45a --timeout 900 --cmd '...pytest databasise/tests/gui_live/test_live_03_errors.py -q -p no:cacheprovider'` | no output, exit 0 | v927 check-fail, exit 1 at RED |
| LIVE-04 | `fed824e` (18-06 Task 1) | `python3 scripts/ledger-amend.py --root . record-fail --id LIVE-04 --at fed824e --timeout 900 --cmd '...pytest databasise/tests/gui_live/test_live_04_evidence_trace.py -q -p no:cacheprovider'` | no output, exit 0 | v928 check-fail, exit 1 at RED |
| LIVE-05 | `a223294` (18-08 Task 1) | `python3 scripts/ledger-amend.py --root . record-fail --id LIVE-05 --at a223294 --timeout 900 --cmd '...pytest databasise/tests/gui_live/test_live_05_documents.py -q -p no:cacheprovider'` | no output, exit 0 | v929 check-fail, exit 1 at RED |
| LIVE-06 | `8dbbc9d` (18-07 Task 1) | `python3 scripts/ledger-amend.py --root . record-fail --id LIVE-06 --at 8dbbc9d --timeout 900 --cmd '...pytest databasise/tests/gui_live/test_live_06_corpus_health.py -q -p no:cacheprovider'` | no output, exit 0 | v930 check-fail, exit 1 at RED |
| LIVE-07 | `72f1e00` (18-09 Task 1) | `python3 scripts/ledger-amend.py --root . record-fail --id LIVE-07 --at 72f1e00 --timeout 900 --cmd '...pytest databasise/tests/gui_live/test_live_07_ledger.py -q -p no:cacheprovider'` | no output, exit 0 | v931 check-fail, exit 1 at RED |
| LIVE-08 | `2c1c784` (18-10 Task 1) | `python3 scripts/ledger-amend.py --root . record-fail --id LIVE-08 --at 2c1c784 --timeout 900 --cmd '...pytest databasise/tests/gui_live/test_live_08_graph.py -q -p no:cacheprovider'` | no output, exit 0 | v932 check-fail, exit 1 at RED |
| LIVE-09 | `28ec65d` (18-03 Task 2) | `python3 scripts/ledger-amend.py --root . record-fail --id LIVE-09 --at 28ec65d --timeout 900 --cmd '...pytest databasise/tests/gui_live/test_live_09_badges_ids.py -q -p no:cacheprovider'` | no output, exit 0 | v933 check-fail, exit 1 at RED |

`...` stands for the full `--cmd` prefix quoted above; each command was run with it in full. No row passed at its RED commit, and no row failed its HEAD control run.

### set-status (9)

| Row | Command | Output | Recorded |
|-----|---------|--------|----------|
| LIVE-01 | `python3 scripts/ledger-amend.py --root . set-status --id LIVE-01 --status done` | no output, exit 0 | v934 open to done |
| LIVE-02 | `python3 scripts/ledger-amend.py --root . set-status --id LIVE-02 --status done` | no output, exit 0 | v935 open to done |
| LIVE-03 | `python3 scripts/ledger-amend.py --root . set-status --id LIVE-03 --status done` | no output, exit 0 | v936 open to done |
| LIVE-04 | `python3 scripts/ledger-amend.py --root . set-status --id LIVE-04 --status done` | no output, exit 0 | v937 open to done |
| LIVE-05 | `python3 scripts/ledger-amend.py --root . set-status --id LIVE-05 --status done` | no output, exit 0 | v938 open to done |
| LIVE-06 | `python3 scripts/ledger-amend.py --root . set-status --id LIVE-06 --status done` | no output, exit 0 | v939 open to done |
| LIVE-07 | `python3 scripts/ledger-amend.py --root . set-status --id LIVE-07 --status done` | no output, exit 0 | v940 open to done |
| LIVE-08 | `python3 scripts/ledger-amend.py --root . set-status --id LIVE-08 --status done` | no output, exit 0 | v941 open to done |
| LIVE-09 | `python3 scripts/ledger-amend.py --root . set-status --id LIVE-09 --status done` | no output, exit 0 | v942 open to done |

### git status --short after the 27 commands

```
 M .planning/state.json
 M ledger/REQUIREMENTS.json
 M ledger/checksums.sha256
 M ledger/history/log.jsonl
 M trace/rounds.jsonl
?? .planning/milestone.lock
?? .planning/ui-reviews/
?? debug/
?? reference/deep-research-embeddings-sidelined/
```

The three kit files are the only changes from this task and are left unstaged. `.planning/state.json`, `trace/rounds.jsonl` and the four untracked paths were already in this state before the resume started, and this plan did not touch them.

## Verification

- R18-07: `python3 mockups/build.py --src databasise/console/src --out databasise/console/operator-console.html` rebuilt the console, and the same command with `--check` exited 0.
- `sha256sum mockups/operator-console.html` prints `3ac0e278c929ba41179249a47606edb910ae4b6032b1d0acb9fc19a739c0c837` (frozen digest after the 2026-11-01 owner re-freeze, unchanged).
- `python3 scripts/mockup-id-check.py --root .` exits 0 with no output (after R18-07 and again after Task 3).
- Whole gui_live suite from `databasise/` with `PLAYWRIGHT_BROWSERS_PATH` and `DATABASISE_REQUIRE_BROWSER=1`: `148 passed in 103.00s` (146 existing tests plus the 2 parametrized R18-07 cases).
- `python3 scripts/plan-gate.py --root . --phase 18 --plans .planning/phases/18-gui-live`: `plan gate passed: 1/1 IDs cited (phase 18)`.
- Not checked in this resume: the Phase 17 GUI suite and the launcher and seam surface tests (Task 1 ran them; R18-07 changes only `20-query.js` and the live build). There is no abort case in the R18-07 test, because the page-level fetch wrapper does not wire the abort signal into its synthetic body. The fix covers abort through the same `.then(done, done)`.

## Deviations from Plan

**1. [Owner-directed] R18-07 fixed inside 18-11**
- The owner answered "Fix it" at the click-through. The fix was made test-first (`13dd233`, `416b5e5`) before any row was linked, because linking protects `test_live_02_query_compare.py`. The edit guard accepted the edit to that file, so no `test_live_02b` file was needed.

**2. [Rule 1 - Bug in the new test] CSP refuses wait_for_function**
- `page.wait_for_function` with a string predicate failed with an `unsafe-eval` CSP error. The test polls with `page.evaluate` in a bounded loop instead, as `test_stream_renders_evidence_then_final` already does. Fixed before the RED commit.

**3. [Process] Nine `set` commands issued in one batch**
- The nine `set` calls were sent as separate Bash calls in one batch rather than strictly one after another. The kit diff shows all nine `test_ref` values and nine history entries, so no write was lost. Every later command ran on its own.

**4. [Process] Build run with absolute paths**
- `mockups/build.py` was run with absolute `--src` and `--out` paths to the same files, through `python3`, as the orchestrator directed. The `--check` run with the same arguments exited 0.

**Total deviations:** 1 owner-directed fix, 1 bug in the new test, 2 process notes. **Impact:** none on behaviour beyond R18-07.

## Bookkeeping for the orchestrator

- Commit the three kit files as `chore(bak): record LIVE-01..09 test refs, fail-first proofs and done status`, and write the S3/S4/S5 traces for LIVE-01 to LIVE-09 as in Phase 17.
- The owner may run `lock-checks` over the nine `databasise/tests/gui_live/test_live_0*.py` files.
- RUN-11 (Phase 8) is open and due under the plan gate. It is the owner-run live embedder measurement, deferred by the owner to TESTING-PLAN.md section 2. No Phase 18 task touches or proves it; it is cited here so the gate sees it carried, not dropped.
- REQUIREMENTS.md was not edited; `phase.complete` marks the rows.

## Known Stubs

None added. The mock-only controls kept for the frozen id check stay hidden, as recorded in the earlier SUMMARYs.

## Threat Flags

None. T-18-31: every row got `record-fail --at` on its recorded RED commit with a HEAD control run before `set-status`. T-18-32: the rows were linked only after the owner's approval and after the R18-07 test edit.

## Self-Check: PASSED

- `databasise/console/src/js/20-query.js`, `databasise/console/operator-console.html` and `databasise/tests/gui_live/test_live_02_query_compare.py` exist; commits 252c455, 4e4dc0f, 13dd233 and 416b5e5 are ancestors of HEAD.
- Nine `check-fail` and nine `set-status` entries for LIVE-01 to LIVE-09 are in the uncommitted kit history.
