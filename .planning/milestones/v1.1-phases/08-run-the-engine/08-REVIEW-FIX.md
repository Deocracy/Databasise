---
phase: 08-run-the-engine
fixed_at: 2026-10-16T21:00:00Z
review_path: .planning/phases/08-run-the-engine/08-REVIEW.md
iteration: 2
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 08: Code Review Fix Report

**Fixed at:** 2026-10-16T21:00:00Z
**Source review:** .planning/phases/08-run-the-engine/08-REVIEW.md
**Iteration:** 2

**Summary:**
- Findings in scope: 2 (Critical 0, Warning 2), plus one orchestrator addition (IN-05 part b)
- Fixed: 2 warnings + the IN-05 wildcard addition
- Skipped: 0

**Verification location:** `workflow.use_worktrees` is `false`, so all edits, tests and commits ran in the main checkout (no worktree, no temp branch, no recovery sentinel). Final gate: `cd databasise && .venv/bin/pytest -q tests/launcher tests/clients tests/seam tests/parity tests/eval` gave 665 passed, 1 skipped, 4 deselected (live). No `-m live` run; no real env file read (the new test uses a stub env file in `tmp_path`).

## Already fixed in iteration 1 (context, unchanged)

- WR-01 (b5e143c): Origin guard against cross-site writes in `launcher/serve_rest.py`.
- WR-02 (482ecee): launcher refusals for bad rerank binding / unreadable / non-UTF-8 env file; case-insensitive binding match.
- WR-03 (8df0750): wildcard binds refused even with `--allow-remote-unauthenticated`.
- WR-04 (81a39fb): rerank response model and score type checks, non-finite scores refused.

## Fixed Issues

### WR-01: `math.isfinite` raises `OverflowError` for very large integer scores

**Files modified:** `databasise/clients/rerank.py`, `databasise/tests/clients/test_rerank_client.py`
**Commit:** c1a84fa
**Applied fix:** `_is_number` catches `OverflowError` from `math.isfinite` and returns False, so a 400-digit integer `relevance_score` raises `RerankResponseError` like any other non-number. A 400-digit score case was added to the existing refusal parametrize list.

### WR-02: builder refusals still escape as tracebacks from the other CLIs

**Files modified:** `databasise/clients/builder.py`, `databasise/launcher/__init__.py`, `databasise/parity/run_arm.py`, `databasise/parity/storage_audit.py`, `databasise/parity/run_cross_modality.py`, `databasise/parity/build_hipporag_index.py`, `databasise/parity/run_comparison.py`, `databasise/eval/aa_run.py`, `databasise/eval/corpus_ingest.py`, `databasise/eval/remint.py`, `databasise/tests/parity/test_cli_builder_refusals.py` (new)
**Commits:** 5dc8b9b (fix and test), bb825b0 (test follow-up)
**Applied fix:**
- `clients/builder.py` exports `BUILDER_REFUSALS` (`MissingParityEnvError`, `MissingParityEnvKeyError`, `UnparseableProviderRoutingError`, `UnsupportedRerankBindingError`; these are all the named errors the builder raises) and lists it in `__all__`.
- `run_arm._CLI_REFUSALS` is removed. `run_arm.main` and `storage_audit.main` catch `(StoreLockedError, *BUILDER_REFUSALS)`, so `storage_audit` no longer reaches into a private name of `run_arm`.
- `run_cross_modality.main` and `build_hipporag_index.main` splice `*BUILDER_REFUSALS` into their existing tuples. `aa_run`, `corpus_ingest` and `remint` replace `(MissingParityEnvError, MissingParityEnvKeyError)` with `BUILDER_REFUSALS`. Exit code 1 and the `print(str(exc), file=sys.stderr)` style are unchanged in each.
- `launcher.LAUNCH_REFUSALS` now reuses `BUILDER_REFUSALS` (same set, no behaviour change).
- Beyond the named list: `run_comparison._run_cli` also reaches `build_clients` (through `compare_arm_on_query`) and caught only `MissingParityEnvError`; it now catches `*BUILDER_REFUSALS` per query. This path has no new test (its flow needs the v1 interpreter and index verification).
- New parametrised test `tests/parity/test_cli_builder_refusals.py`: for each of run_arm, storage_audit, run_cross_modality, build_hipporag_index, aa_run (`--spend`), corpus_ingest (`--spend`), remint, a stub env file with a bad `RERANK_BINDING` makes `main()` return non-zero, with `RERANK_BINDING` named, the bad value absent and no "Traceback". Confirmed to fail on the five newly covered CLIs with the source changes stashed. The test stubs `run_arm._build_stores` because run_arm and storage_audit otherwise open the real store before building clients, and the leaked RocksDB lock broke `tests/parity/test_cross_modality_isolation.py` when the suites ran together (fixed in bb825b0).

### IN-05 (orchestrator addition, part b): wildcard host spellings

**Files modified:** `databasise/launcher/__init__.py`, `databasise/tests/launcher/test_bind_guard.py`
**Commit:** 7807300
**Applied fix:** `_is_wildcard` now also treats an empty host, the short IPv4 forms (`0`, `0.0`, via `socket.inet_aton`) and `::ffff:0.0.0.0` as wildcard binds, refused with the existing "wildcard" message even with `--allow-remote-unauthenticated`. The wildcard test parametrization gained `0`, `0.0`, empty and `::ffff:0.0.0.0` for both launchers. Part (a) of IN-05 (default-port and https origins) was not changed; the safe-failure workaround is `--cors-origin`, and documenting it is left to the owner.

## Skipped Issues

None. IN-01 to IN-04 are out of scope for `critical_warning` and were not touched.

## Notes for the verifier

- The WR-02 and IN-05 changes alter which errors are caught and which hosts are refused, so a human should confirm they match intent. Marked "fixed: requires human verification" for that reason.
- `ruff check` reports no new violations compared with the pre-fix tree (same set as before, compared by file and rule). `ruff format` would reflow two long lines in `_is_wildcard`; the project already fails `ruff format --check`, so I did not reformat.
- `run_comparison` change is untested (see above).

---

_Fixed: 2026-10-16T21:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
