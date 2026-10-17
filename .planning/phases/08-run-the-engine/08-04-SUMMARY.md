---
phase: 08-run-the-engine
plan: 04
subsystem: testing
tags: [pytest, rest, corpus, mutation-check, upload, delete]

requires:
  - phase: 05-seam
    provides: REST corpus endpoints and the stub corpus driver the tests run against
provides:
  - upload path-safety test that reads the file written to disk (RUN-09)
  - upload-poll-delete round trips that prove counts drop to zero after a delete (RUN-10)
affects: [08-run-the-engine, 09-seam]

actuals:
  tokens: 2700
  tasks: 2
  commits: 3
plan_head_before: 42a7f3bf1d6a8350eaf13873487a4f3edfd00f38
plan_head_after: 6143311b0d14470979998b95e36681a6fc3ec427

tech-stack:
  added: []
  patterns:
    - "Stub delete body takes an on_success hook; the status fake shares a state dict with it so a delete is observable in later reads"
    - "Mutation control: a temporary wrapper test monkeypatches the engine in-process, so no shared source file is edited"

key-files:
  created: []
  modified:
    - databasise/tests/seam/test_rest_corpus_endpoints.py

key-decisions:
  - "RUN-09 mutation done by patching databasise.seam.engine.generated_on_disk_name inside one temporary test; engine.py never edited"
  - "Stem derived with Path.stem, with name equality against generated_on_disk_name(stem) covering the suffix"

requirements-completed: [RUN-09, RUN-10]

coverage:
  - id: D1
    description: "Upload with filename '../escape.pdf' leaves exactly one 32-hex-stem file in corpus-inbox named by generated_on_disk_name, and no escape.pdf in store_root, the inbox or the parent"
    requirement: RUN-09
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_rest_corpus_endpoints.py#test_generated_on_disk_name_is_reachable_for_a_multipart_uploaded_document"
        status: pass
    human_judgment: false
  - id: D2
    description: "Both upload-poll-delete round trips read counts 1/1 before and 0/0 after a delete, and 0/0 after a not_found delete"
    requirement: RUN-10
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_rest_corpus_endpoints.py#test_upload_poll_delete_round_trip"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_rest_corpus_endpoints.py#test_upload_poll_delete_round_trip_in_process_matches_the_rest_status_sequence"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-10-17
status: complete
---

# Phase 8 Plan 04: Upload and Delete Seam Tests Summary

**Upload path-safety test now inspects the inbox file on disk, and the delete round trips assert counts fall from 1 to 0 through a stub-delete hook shared with the status fake; both fail under the mutations they claim to catch.**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-10-17T00:26Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- RUN-09: the upload test posts `../escape.pdf`, lists `store_root/corpus-inbox`, requires exactly one file whose stem matches `[0-9a-f]{32}` and whose name equals `generated_on_disk_name(stem)`, and requires no `escape.pdf` in `store_root`, the inbox, or `store_root.parent`.
- RUN-10: `_make_stub_delete_body(on_success=...)`, `_make_registry(on_delete=...)` and `state["deleted"]` in `_patch_status_sequence` connect a successful delete to the status fake. Both round trips assert `by_status["processed"] == 1` and `total == 1` before, `.get("processed", 0) == 0` and `total == 0` after, and the same zero counts after the second (`not_found`) delete. The always-true `total >= 0` assertion is gone.

## Mutation-check evidence

RUN-09 (command: `.venv/bin/pytest -q tests/seam/test_rest_corpus_endpoints.py -k "generated_on_disk_name or tmp_run09_mutant"`; the wrapper patched `databasise.seam.engine.generated_on_disk_name` to return `"../escape.pdf"`, which lands the bytes at `store_root/escape.pdf`):

1. Old test under the mutation: `2 passed, 15 deselected` (the old test is blind to it).
2. Rewritten test under the mutation: `FAILED ...test_tmp_run09_mutant` with `assert 0 == 1 where 0 = len([])`; `1 failed, 1 passed, 15 deselected`.
3. Rewritten test unpatched: `1 passed, 15 deselected`.

RUN-10 (mutation: the `on_success()` call replaced by `pass` in `_make_stub_delete_body`, run with `-k round_trip`):

- Mutated: `2 failed, 1 passed, 13 deselected`. Both failures are `assert 1 == 0` on `by_status.get('processed', 0)` (`{'processed': 1}`). The one pass is the status-sequence comparison test, which never deletes.
- Restored: `3 passed, 13 deselected`; whole file `16 passed`.
- The pre-rewrite round trips pass under this mutation: they asserted only the delete status code and `total >= 0`, and never read counts that depended on the delete.

`databasise/seam/engine.py` was never edited (`git diff --quiet` held at each check); the temporary `test_tmp_run09_mutant` was removed before the commit (`grep -c` prints 0).

## Task Commits

1. **Task 1: RUN-09 upload path-safety test reads the disk** - `e95b696` (test)
2. **Task 2: RUN-10 round trips prove counts drop after a delete** - `c358fa0` (test)
3. **Import-order fix for the new `Callable` import** - `6143311` (style)

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified

- `databasise/tests/seam/test_rest_corpus_endpoints.py` - rewritten upload test, `on_success`/`on_delete`/`state["deleted"]` plumbing, count-checking round trips

## Decisions Made

- The mutation for RUN-09 is an in-test monkeypatch rather than an edit of `engine.py`, as the plan specified, because wave-1 plans share one working tree.
- Stem is `Path.stem`; the full name equality against `generated_on_disk_name(stem)` still pins the suffix.

## Deviations from Plan

None - plan executed exactly as written. One added commit (`6143311`) fixed a ruff import-order error that my new import introduced; three other ruff findings in the file (two I001, one SIM118) are present at HEAD before this plan and were left alone.

## Issues Encountered

- First draft derived the stem with `removesuffix(generated_on_disk_name(""))`, which raises `ValueError` on an empty id. It was replaced with `Path.stem` before the first commit.

## Known Stubs

None. The stub corpus driver is a pre-existing test fixture, not a stub introduced here.

## Threat Flags

None.

## Next Phase Readiness

- RUN-09 and RUN-10 are covered; the empty-upload edge (RUN-09/empty) is deferred to Phase 9 (ROADMAP Phase 9 criterion 2) as the plan flagged.

---
*Phase: 08-run-the-engine*
*Completed: 2026-10-17*

## Self-Check: PASSED

- `databasise/tests/seam/test_rest_corpus_endpoints.py` exists; commits `e95b696`, `c358fa0`, `6143311` are ancestors of HEAD.
- `.venv/bin/pytest -q tests/seam/test_rest_corpus_endpoints.py`: 16 passed. `-k round_trip`: 3 passed. `-k generated_on_disk_name`: 1 passed.
- Acceptance greps: `corpus-inbox` present, `fullmatch(r"[0-9a-f]{32}"` once, `on_success` 4 lines, `state["deleted"]` present, `total >= 0` count 0, `tmp_run09_mutant` count 0, `engine.py` clean.
