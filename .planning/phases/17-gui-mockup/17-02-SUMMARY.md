---
phase: 17-gui-mockup
plan: 02
subsystem: ui
tags: [mockup, html, playwright, assembler, gui]
requires:
  - phase: 17-01
    provides: "Playwright harness, ui fixture, fail-first GUI-01 / GUI-02 / build-stability tests"
provides:
  - "mockups/build.py: deterministic assembler (include, repeat, glob, fixtures, --check)"
  - "mockups/operator-console.html: single static console shell, six screen roots, offline"
  - "docs/gui/MOCK-IDS.json: sorted checked-in id list (D-02)"
  - "Console registry, $id, window.__mock, Console.health() in mockups/src/js/00-app.js"
  - "Base stylesheet with the region-marker classes panel, banner, state-view, badges"
affects: [17-03, 17-04, 17-05, 17-06, 17-07, 17-08, 17-09, 17-10, 17-11, 17-12, 17-13]
tech-stack:
  added: []
  patterns:
    - "mockups/src is the only hand-edited source; operator-console.html is build output guarded by test_mockup_build.py"
    - "js/*.js are concatenated into one script, so FIX, SCREENS, $id and Console are shared globals for later screen scripts"
key-files:
  created:
    - mockups/build.py
    - mockups/src/page.html
    - mockups/src/screens/query.html
    - mockups/src/screens/evidence.html
    - mockups/src/screens/documents.html
    - mockups/src/screens/corpus.html
    - mockups/src/screens/ledger.html
    - mockups/src/screens/graph.html
    - mockups/src/js/00-app.js
    - mockups/src/css/00-base.css
    - mockups/src/fixtures/health.json
    - mockups/operator-console.html
    - docs/gui/MOCK-IDS.json
  modified: []
key-decisions:
  - "00-app.js has no IIFE: later plans' scripts are concatenated into the same script and need FIX, $id and Console in scope"
  - "Health indicator state is data-state ok|degraded|loading|error with state words ok|degraded|checking|unreachable; CSS maps both these and the ok|warn|fail|neutral|progress vocabularies onto the same tints"
  - "Mobile .app-body uses align-content:start; without it the 3 x 2 nav grid rows stretched to 136 px"
requirements-completed: []
duration: one executor session
completed: 2026-10-30
status: complete
commits: 2
plan_head_before: e658a40d3d56390c16eab9eda17cc07db47c85cd
plan_head_after: 40c12598fd665bcab9667bfeecbf2782bcf5ccdc
actuals:
  tokens: 11500
  tasks: 2
  commits: 2
---

# Phase 17 Plan 02: Console shell and assembler Summary

`mockups/build.py` assembles `mockups/src/` into the single offline file `mockups/operator-console.html`: header health badge with four states, six-entry nav, six screen roots, inline fixture block and `window.__mock`; the 17-01 GUI-01, GUI-02 and build-stability tests now pass.

Requirements GUI-01 and GUI-02 are NOT marked complete here. The orchestrator records the ledger rows (`record-fail --at 6e39279`, code_ref `mockups/operator-console.html`), so `requirements-completed` is empty on purpose.

## What was built

- Task 1 (tracer): the assembler, `page.html`, six one-element screen stubs, `health.json` (ten store keys, degraded fixture without `vector:chunks`, loading and error shapes), and `00-app.js` (Console registry, hash routing, nav, `window.__mock` with `show` and three dispatchers that throw `<screen> has no <method>`). Smoke, GUI-01 (4 nodes) and build-stability pass; `build.py --check` exits 0.
- Task 2: `00-base.css` (tokens, `[hidden]`, header 56 px, rail 224 px, below 768 px a two-row header and a 3 x 2 grid of 44 px nav buttons, shared classes), the mock banner, a `shell.mock.health-fixture` select, a seven-symbol sprite, the four health states with spinner for `checking`, `Health details` (shows corpus, emits `focus-health`), `Console.health()`, and `docs/gui/MOCK-IDS.json` (17 ids, all new).

## Test results

`DATABASISE_REQUIRE_BROWSER=1 databasise/.venv/bin/python -m pytest -q databasise/tests/gui/test_gui_01_shell.py databasise/tests/gui/test_gui_02_ids.py databasise/tests/gui/test_mockup_build.py databasise/tests/gui/test_playwright_smoke.py -p no:cacheprovider` gives `9 passed`. `build.py --check` exits 0. The 17-01 tests were not edited.

Extra check outside the suite (scratch Playwright script, not committed): the select moves the header badge through `ok`, `degraded`, `checking` (spinner visible) and `unreachable`; at 375 px all six nav buttons are 47 px high with no clipped text and the page does not scroll horizontally.

## Commits

- `17ca54c` feat(17-02): console shell and assembler pass GUI-01
- `40c1259` feat(17-02): id list, build stability and base styles

## Deviations from Plan

None - plan executed as written. Notes on judgment calls inside the plan's freedom:

- The `.panel`, `.banner`, `.state-view` and `.badges` classes exist but are not used by any element yet, so the region-marker checks are exercised only by the test's synthetic sample until a later plan adds a screen. The real-file walk finds the banner (id present) and nothing else.
- The header glyph, state word and spinner are plain spans with `data-role` attributes (exempt from ids per UI-SPEC), not id-bearing elements.
- A small fix during Task 2 (mobile nav rows stretching to 136 px) was found by the scratch check and fixed in the same commit.

## Known Stubs

The six `mockups/src/screens/*.html` files are intentional one-element stubs (a hidden root plus its title); later plans own them: query 17-06/17-07, evidence 17-08, documents 17-09, corpus 17-10, ledger 17-11, graph 17-12. The `dialogs/*.html` glob is empty on purpose until those plans add the four dialogs. `shell.instance.chip` is not built (not in this plan's scope).

## Threat Flags

None. T-17-02 holds: nothing sets `innerHTML`, and the `@fixtures` directive writes `</` as `<\/`. T-17-22 holds: `test_mockup_build.py` and `build.py --check` fail on a hand-edited output. The file contains no link, script src, img src, @import or `url(http`.

## Self-Check: PASSED

- All 13 files in `files_modified` exist.
- Commits 17ca54c and 40c1259 are ancestors of HEAD; `git rev-list --count` from the recorded base is 2.
- Final run `9 passed`; `build.py --check` exit 0.
