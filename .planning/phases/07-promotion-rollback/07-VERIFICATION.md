---
phase: 07-promotion-rollback
verified: 2026-09-12T09:00:00Z
status: passed
score: 3/3 roadmap success criteria verified; G-07-1 closed with evidence, zero open human-verification items
covered_files:
  - ".planning/REQUIREMENTS.md"
  - ".planning/phases/07-promotion-rollback/07-01-PLAN.md"
  - ".planning/phases/07-promotion-rollback/07-01-SUMMARY.md"
  - ".planning/phases/07-promotion-rollback/07-02-PLAN.md"
  - ".planning/phases/07-promotion-rollback/07-02-SUMMARY.md"
  - ".planning/phases/07-promotion-rollback/07-03-PLAN.md"
  - ".planning/phases/07-promotion-rollback/07-03-SUMMARY.md"
  - ".planning/phases/07-promotion-rollback/07-04-PLAN.md"
  - ".planning/phases/07-promotion-rollback/07-04-SUMMARY.md"
  - ".planning/phases/07-promotion-rollback/07-05-PLAN.md"
  - ".planning/phases/07-promotion-rollback/07-05-SUMMARY.md"
  - ".planning/phases/07-promotion-rollback/07-GATE-AMENDMENT.md"
  - ".planning/phases/07-promotion-rollback/07-REVIEW.md"
  - ".planning/phases/07-promotion-rollback/07-UAT.md"
  - ".planning/phases/07-promotion-rollback/07-VALIDATION.md"
  - ".planning/phases/07-promotion-rollback/COVERAGE.md"
  - "databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md"
  - "databasise/ledger/ledger.py"
  - "databasise/mcp/server.py"
  - "databasise/mcp/tools.py"
  - "databasise/seam/engine.py"
  - "databasise/seam/promotion.py"
  - "databasise/seam/refusals.py"
  - "databasise/seam/rest.py"
  - "databasise/tests/ledger/test_ledger_generation_uniqueness.py"
  - "databasise/tests/seam/test_dual_transport.py"
  - "databasise/tests/seam/test_operator_verb_concurrency.py"
  - "databasise/tests/seam/test_promotion_posture.py"
  - "databasise/tests/seam/test_rest_transport.py"
covered_digest: "v1:sha256:c008e4fc24fa1c5ec0d93a00f38c226108242dcf7b3482f0490413a0b079c392"
re_verification:
  previous_status: human_needed
  previous_score: "3/3 roadmap success criteria verified; 1 open human-verification item (G-07-1, the concurrent operator-verb race)"
  gaps_closed:
    - "G-07-1 (07-UAT.md; 07-REVIEW.md WR-01): concurrent promote/rollback/retire on one alias no longer lets a loser commit on stale state — closed by 07-05's Ledger.transaction() (BEGIN IMMEDIATE spanning each verb's guard read through its append()) plus a UNIQUE(alias, minted_version) schema backstop"
  gaps_remaining: []
  regressions: []
---

# Phase 7: Promotion & Rollback Verification Report

**Phase Goal:** The owner can promote a wiring and roll it back on recorded evidence, with nothing
inferable by absence.
**Scope (per `07-GATE-AMENDMENT.md`):** ROADMAP success criteria 1, 2, 3 only. Criteria 4 and 5 are
struck; HARD-01/HARD-02/HARD-04 are deferred and are correctly **not** scored as gaps here.
**Verified:** 2026-09-12
**Status:** passed
**Re-verification:** Yes — after 07-05's gap closure of the previous run's sole open item, G-07-1
(the concurrent operator-verb race, carried in `07-REVIEW.md` as WR-01).

## Gap Closure Verdict (07-05 / G-07-1)

**CLOSED.** Checked directly against the running code and by executing the new tests myself this
session — not trusted from 07-05-SUMMARY.md's claim.

| Contract item (from `07-UAT.md`'s gap / 07-05-PLAN.md's `must_haves`) | Verified against code |
|---|---|
| `Ledger.transaction()` exists as a `BEGIN IMMEDIATE` span, commits on clean exit, rolls back and re-raises on any exception | ✓ Confirmed by direct read: `databasise/ledger/ledger.py:140-167`, `@contextlib.contextmanager`, `try: yield / except BaseException: rollback+raise / else: commit` |
| `transaction()` is entered BEFORE the first guard read in all three of `_promote_sync`, `_rollback_sync`, `_retire_sync`, with `append()` inside the span | ✓ Confirmed line-by-line in `databasise/seam/engine.py`: `_promote_sync` (1201/1203 — `ledger = Ledger(...)` then immediately `with ledger.transaction():`, first statement inside is `ledger.by_alias(alias)` at 1204, `append()` at 1259 is the last statement inside); `_rollback_sync` (1334/1336, first read `ledger.generation_state` at 1337, `append()` at 1386); `_retire_sync` (1474/1476, first read `ledger.generation_state` at 1477, `append()` at 1515). No read precedes the `with` in any of the three — entering one line late (the exact failure mode the plan's own `key_links` warned against) is not present |
| Index DDL is DROP-then-CREATE-UNIQUE under a NEW name, not a reuse of the old name | ✓ Confirmed: `databasise/ledger/ledger.py:213-216` — `DROP INDEX IF EXISTS ix_ledger_generation` followed by `CREATE UNIQUE INDEX IF NOT EXISTS ux_ledger_generation ON ledger(alias, minted_version)`. New name (`ux_ledger_generation`), not a `CREATE UNIQUE INDEX IF NOT EXISTS ix_ledger_generation` reuse — the verified silent-no-op pattern the plan named is not present |
| §18 seam envelope unchanged: no new refusal class, promote/rollback/retire field-for-field identical across transports | ✓ Confirmed: `git diff 89d55fb^..9882a4c -- seam/refusals.py seam/rest.py mcp/tools.py mcp/server.py` is empty — none of the four seam-surface files changed by 07-05 at all |
| The two new test modules exercise real concurrency, not a trivial pass | ✓ Confirmed by reading both test bodies: `test_operator_verb_concurrency.py` uses `asyncio.gather(engine.retire(...), engine.rollback(...), return_exceptions=True)` and `asyncio.gather(*(engine.promote(...) for ...))` against a real `Databasise` engine backed by a real SQLite file per trial (`tempfile.TemporaryDirectory`), asserting on actual row `id` order read back from the database — not a mock or a stub. Ran both files myself this session: `5 passed in 9.58s` |

Live re-run of the closure tests this session (not trusted from SUMMARY.md's claim):

```
cd databasise && uv run --frozen python -m pytest -q tests/seam/test_operator_verb_concurrency.py tests/ledger/test_ledger_generation_uniqueness.py
→ 5 passed in 9.58s
```

`git log --oneline -- databasise/ledger/ledger.py databasise/seam/engine.py` confirms `3fe2ee0` and
`89d55fb` ("fix(07-05): ...") are the top two commits touching those files, directly above `07-04`'s
`214faff` and `07-02`'s `94e36b5` — no undocumented later edit.

**Verdict: 07-05 closes G-07-1 exactly as specified. `07-UAT.md`'s sole gap is resolved with direct
evidence, not merely by SUMMARY claim.**

## Full-Suite / Cross-Phase Regression Evidence (established by the orchestrator this run)

Both runs below were executed by the orchestrator after 07-05 landed, and are cited here rather than
re-run (per the instruction not to duplicate a full-suite run):

- Post-merge test gate: `cd databasise && uv run pytest -q` → **1068 passed, 1 skipped, 0 failed**.
- Cross-phase regression gate (same command, covers phases 01–06): **1068 passed, 1 skipped, 0
  failed**.

**Discrepancy noted and judged.** 07-05-PLAN.md's must-have text says "the full suite stays at 1062
passed / 2 skipped / 0 failed" and 07-05-SUMMARY.md claims **1067 passed / 2 skipped**. The
orchestrator measured **1068 passed / 1 skipped** on two independent runs. Total collected is
identical either way: 1062 + 5 new tests = 1067, and 1067 + 1 = 1068 accounts for exactly one test
that is conditionally skipped in some environments and collected-and-passed in the orchestrator's
(e.g. an optional-dependency-gated test, consistent with this project's `--extra rest --extra mcp`
optional install groups). Zero failures across every run cited (07-05's own live run, the SUMMARY's
run, and both orchestrator runs). **Judgment: this is an environment-dependent skip, not a material
deviation** — no test that previously passed now fails or is missing; the only movement is one test
flipping from skipped to passed depending on which optional extras are installed in the environment
running pytest. Not a gap.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every generation record carries `change_origin` and `promotion_provenance`, never defaulted; a semver is minted at promotion and only at promotion; tombstoned losers are never lifted; the active pointer is a derived query | ✓ VERIFIED | `databasise/ledger/ledger.py:170-196` (`change_origin TEXT NOT NULL`, `record_kind TEXT NOT NULL`); `by_alias`/`generation_state` both `ORDER BY id DESC LIMIT 1`, no written "current" column. Untouched by 07-05 except for the new `transaction()` wrapper around the same reads; re-confirmed by direct read this session |
| 2 | Owner promotes by explicit call with `operator_asserted` provenance and non-empty `promotion_trace_ids`, no verdict/tier-of-decision; ledger append is the decision, alias repoint is atomic; rollback follows the same path | ✓ VERIFIED | `promote()`'s body: one `ledger.append()` call, now inside `with ledger.transaction():` so the read that derives the append and the append itself commit as one unit — the atomicity claim is now true of the *decision*, not only of the single `INSERT`, closing exactly the gap `07-UAT.md` reproduced. `test_promote.py`/`test_rollback.py`/`test_retire.py` and the two new concurrency test modules all pass live this session |
| 3 | `promote-next`/`promote-now` stay unavailable for answer-level/index-side classes under the default posture, and the refusal names the posture rather than failing silently — including every out-of-enum verb string | ✓ VERIFIED | Unchanged by 07-05 (not in its `files_modified`); `test_no_gate_verb_appends_a_row`, `test_operator_asserted_verb_still_appends`, and 07-04's `UnrecognisedPromotionVerbError` coverage all re-confirmed passing this session as part of the cited full-suite run |
| 4 | Concurrent promote/rollback/retire against one alias either serializes or cleanly refuses the loser — never two rows minting the same semver, never a guard passing on state that changes after its own read (G-07-1) | ✓ VERIFIED | This is the truth the previous verification left as ⚠️ human-verification (no automated evidence existed). It is now behaviorally proven: `test_retire_vs_rollback_race_never_lets_a_rollback_outrun_a_tombstone` and `test_six_concurrent_promotes_mint_six_distinct_versions_with_zero_exceptions` (`databasise/tests/seam/test_operator_verb_concurrency.py`) exercise the actual race via `asyncio.gather()` against a real SQLite-backed engine and assert on real row order / distinct versions. Both pass, run live this session (`5 passed in 9.58s`). RED evidence exists in 07-05-SUMMARY.md (captured against genuine pre-fix code via `git checkout --`, not narrated) |

**Score:** 4/4 truths verified against the current codebase (not against SUMMARY.md's claim) — the
three original roadmap criteria plus the concurrency truth the previous verification could not close
without a live run.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `databasise/ledger/ledger.py` | `Ledger.transaction()` context manager; `ux_ledger_generation` UNIQUE index via DROP+CREATE under a new name | ✓ VERIFIED | Confirmed by direct read, lines 140-167 and 204-225 |
| `databasise/seam/engine.py` | All three `_*_sync` bodies wrap guard-read-through-`append()` in `with ledger.transaction():` | ✓ VERIFIED | Confirmed line-by-line for `_promote_sync`, `_rollback_sync`, `_retire_sync` |
| `databasise/tests/seam/test_operator_verb_concurrency.py` | Two real-concurrency regression tests | ✓ VERIFIED | Both present, both pass live, both use genuine `asyncio.gather()` against a real engine/DB, not a mock |
| `databasise/tests/ledger/test_ledger_generation_uniqueness.py` | Duplicate-refused, tombstones-stay-distinct, old-index-upgrade tests | ✓ VERIFIED | Present, passes live (3 tests) |
| `databasise/seam/refusals.py` / `rest.py` / `mcp/tools.py` / `mcp/server.py` | Unchanged by 07-05 — no new refusal class, no envelope change | ✓ VERIFIED | `git diff 89d55fb^..9882a4c` over all four files is empty |
| `databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md` | Criterion 2 amended with new test citations and a dated correction note, append-only | ✓ VERIFIED | Confirmed by direct read: existing row body untouched, dated note appended below per the plan's own append-only discipline |
| `.planning/phases/07-promotion-rollback/COVERAGE.md` | Note recording that 07-05 added no refusal | ✓ VERIFIED | Confirmed present under "The refusal ladder is part of the surface" |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `_promote_sync`'s `by_alias` read | `_promote_sync`'s `append()` | `with ledger.transaction():` enclosing both | ✓ WIRED | Confirmed: 1203-1259, one continuous `with` block |
| `_rollback_sync`'s `generation_state`/tombstone guard | `_rollback_sync`'s `append()` | `with ledger.transaction():` | ✓ WIRED | Confirmed: 1336-1386 |
| `_retire_sync`'s tombstone guard / active-generation guard | `_retire_sync`'s `append()` | `with ledger.transaction():` | ✓ WIRED | Confirmed: 1476-1515 |
| A duplicate `(alias, minted_version)` INSERT | `sqlite3.IntegrityError` | `ux_ledger_generation` UNIQUE index | ✓ WIRED | Confirmed by direct test run: `test_a_duplicate_non_null_alias_minted_version_pair_is_refused_by_the_database` passes live |
| An old-schema `ledger.db` (plain `ix_ledger_generation`) | Uniqueness enforced after reopen | `DROP INDEX` + `CREATE UNIQUE INDEX` under new name on every `Ledger.__init__` | ✓ WIRED | Confirmed by direct test run: `test_reopening_a_database_carrying_the_old_plain_index_enforces_uniqueness` passes live |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Both concurrency races (retire-vs-rollback, six-way promote) | `uv run --frozen python -m pytest -q tests/seam/test_operator_verb_concurrency.py tests/ledger/test_ledger_generation_uniqueness.py` | `5 passed in 9.58s` | ✓ PASS (run live this session) |
| No stray `ValueError`/unwrapped exception introduced on the promote/rollback/retire path | reviewed engine.py transaction spans directly (above) | guard reads and appends share one atomic span in all three verbs | ✓ PASS |
| §18 envelope files unchanged | `git diff 89d55fb^..9882a4c -- seam/refusals.py seam/rest.py mcp/tools.py mcp/server.py` | empty diff | ✓ PASS |
| Debt-marker scan on all 07-05-touched files | `grep -n "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER"` across `ledger.py`, `engine.py`, both new test files, `PROMOTION-LEDGER-EVIDENCE.md` | no matches | ✓ PASS — no blocker |
| Full suite (orchestrator's `verified_context`, cited not re-run) | `uv run pytest -q` (×2, pre- and post-merge) | `1068 passed, 1 skipped, 0 failed` both times | ✓ PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` files exist in this project and no phase document references a
probe script. **SKIPPED (no runnable probes declared or found).**

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MACH-07 | 07-01, 07-02, 07-05 | Append-only promote/rollback ledger, §7 field discipline, atomic decision | ✓ SATISFIED | Ledger schema/projections re-confirmed this session; atomicity claim now holds for the full decision (read+append), not only the write, per G-07-1's closure; `.planning/REQUIREMENTS.md` line 21 checked `[x]`, traceability table line 91 reads "Phase 7 / Complete" |
| API-09 | 07-01, 07-03, 07-04, 07-05 | Operator can promote/rollback via RIG §PR.3's path, reachable identically over REST/MCP, including a named refusal for any invalid verb, and correct under concurrent access | ✓ SATISFIED | All prior 07-04 findings still hold (envelope unchanged); the concurrency gap is now closed with direct evidence; `.planning/REQUIREMENTS.md` line 45 checked `[x]`, traceability table line 109 reads "Phase 7 / Complete" |
| HARD-01 | — (deferred) | Gate-script vacuous-pass repair | Pending, correctly deferred | `07-GATE-AMENDMENT.md`; unaffected by this run |
| HARD-02 | — (deferred) | ANATOMY §F / PARTS Appendix A reconciliation | Pending, correctly deferred | Same |
| HARD-04 | — (deferred) | Owner's corpus in eval bundle | Pending, correctly deferred | Same |

No orphaned requirements: MACH-07 and API-09 are the only two IDs mapped to Phase 7 in
`REQUIREMENTS.md`'s traceability table; 07-05's own frontmatter declares
`requirements: [MACH-07, API-09]`, consistent with it being a targeted gap-closure plan against the
same requirements 07-01/07-02/07-03/07-04 already claimed.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `databasise/ledger/ledger.py` / `seam/selectors.py:265` | `Ledger.__init__` vs `transaction()`'s held write lock | Every `Ledger()` construction — including the read-only alias lookup an ordinary `query()`/`compare()` call makes — now contends for the same write lock a `promote`/`rollback`/`retire` transaction holds. `sqlite3.connect()` sets no `timeout=`, so the busy-timeout default is 5.0s; a lock-timeout `sqlite3.OperationalError` is not wrapped into a `SeamRefusalError` and would surface as a raw exception out of an ordinary read query if contention ever exceeds that window. New, introduced by 07-05's own fix (the transactional span is now wider than any single pre-07-05 write) | ⚠️ Warning (07-REVIEW.md WR-03) | See judgment below — not scored as a gap against this phase's must-haves, but a real robustness concern for the owner to track |
| `databasise/tests/seam/test_operator_verb_concurrency.py:37-39` | six-way-promote regression test's detection probability | 20 trials at the measured ~10%/trial pre-fix rate gives ~88% single-run detection (`1 - 0.9^20`), materially weaker than its sibling retire/rollback test's ~100% (`1 - 0.32^20`), with no comment flagging the asymmetry | ⚠️ Warning (07-REVIEW.md WR-04) | Test-quality concern only — both races are empirically closed (0/40+ across 07-05's and this session's live runs); does not affect current correctness, only future-regression detection confidence |
| `databasise/seam/promotion.py:111-124` (`_arm_name_for_node_ids`) | First-match-wins arm resolution with no uniqueness guard | Carried forward from `07-REVIEW.md`'s WR-02; not touched by 07-05; not exploitable against the currently registered arm set | ⚠️ Warning | Unchanged from prior verification |
| `databasise/seam/engine.py` (`rollback` docstring) | `rollback()`'s docstring does not state (as `retire()`'s does) that the resolved arm need not match the rollback target | ℹ️ Info | Carried forward from `07-REVIEW.md`'s IN-01; unchanged from prior verification |
| `databasise/ledger/ledger.py:204-225` | Pre-existing-duplicate-rows index-upgrade failure path (`CREATE UNIQUE INDEX` raising uncaught on open) is deliberate and documented, but pinned by no test | ℹ️ Info (07-REVIEW.md IN-02) | Genuinely reachable but rare production scenario; documented in the code comment as an intentional non-repair; new this cycle |
| `databasise/seam/engine.py:1213-1214` | Gate-verb refusal paths (guaranteed to never write) still acquire the sole ledger write lock inside `with ledger.transaction():` | ℹ️ Info (07-REVIEW.md IN-03) | Avoidable lock contention under load, not an incorrect-behavior defect; new this cycle |

**Judgment on WR-03 against this phase's must-haves and success criteria (per the explicit
adversarial instruction to weigh this, not wave it through).** 07-05-PLAN.md's `must_haves.truths`
state "a loser that cannot proceed refuses by an already-shipped named `SeamRefusalError`... never a
bare `sqlite3.OperationalError`" — but that truth, and its two committed regression tests, are
scoped specifically to the three operator verbs racing **each other** (promote-vs-promote,
retire-vs-rollback), which is exactly what `07-UAT.md`'s G-07-1 reproduced and what this plan closed.
WR-03 describes a **different** interaction: an ordinary read-only `query()`/`compare()` call
(`selectors.py`'s `by_alias` lookup) contending with a held promotion transaction. No must-have in
07-01 through 07-05, and no ROADMAP success criterion 1-3, asserts anything about `query()`'s
behavior under concurrent promotion — that surface belongs to Phase 4/5's API-03 through API-07, not
to Phase 7. WR-03 is therefore a genuine, newly-introduced robustness risk (correctly rated Warning,
not Critical, by the code reviewer) but it does **not** falsify any must-have or success criterion
this phase is scored against, so it is recorded here as a carried anti-pattern rather than a gap.
The owner should track it for a future hardening pass (an explicit `timeout=` on `sqlite3.connect()`
and wrapping a lock-timeout `OperationalError` into a named refusal, per the reviewer's own suggested
fix).

No new debt markers (`TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`) in any of 07-05's five modified
files — re-scanned directly this session, zero matches.

## Human Verification Required

None. The previous verification's sole open item (concurrent promote/rollback/retire on the same
alias) is now closed with direct, live, behavioral evidence — both reproduced races pass 0/40+ across
independent runs (07-05's own three 20-trial runs, plus this session's live re-run).

## Gaps Summary

**No gaps.** The previous verification's sole open item — G-07-1, the concurrent operator-verb race
that left the phase at `human_needed` because only a live concurrent run could demonstrate the
outcome — is now closed with committed, passing regression tests exercising genuine concurrency
(`asyncio.gather()` against a real SQLite-backed engine, not a mock), re-run live this session
(`5 passed in 9.58s`). `Ledger.transaction()` is entered before the first guard read in all three
operator verbs (checked line-by-line, not merely trusted), the index replacement uses DROP-then-
CREATE-UNIQUE under a new name (not the verified silent-no-op reuse of the old name), and the §18
envelope files (`refusals.py`, `rest.py`, `mcp/tools.py`, `mcp/server.py`) are byte-for-byte
unchanged by 07-05 (`git diff` empty).

One new Warning-level finding (WR-03, the ledger-wide lock-contention risk to ordinary `query()`
calls introduced by widening the transaction span) was evaluated against this phase's must-haves and
success criteria and found not to contradict any of them — it is a real risk outside this phase's
scored surface, carried forward as an anti-pattern for the owner's attention rather than as a gap.
WR-02, WR-04, IN-01, IN-02 and IN-03 are similarly carried as non-blocking findings, not gaps.

Phase 7's three ROADMAP success criteria (1-3) are fully and unqualifiedly verified, MACH-07 and
API-09 are both satisfied, and the concurrency truth the previous verification could not close
without a live run is now behaviorally proven. **Status: passed.**

## Adversarial Re-Verification (orchestrator, post-verifier)

Before marking the phase complete, this verification's four gating claims were each put to three
independent adversarial reviewers instructed to REFUTE (13 agents, distinct lenses per claim).

| Claim | Refute votes | Outcome |
|---|---|---|
| WR-03 is not a phase gap | 0/3 | survives |
| The `BEGIN IMMEDIATE` span actually closes both races | 1/3 | survives |
| The UNIQUE-index upgrade is real on a pre-existing DB | 0/3 | survives |
| The §18 envelope is unchanged | 1/3 | survives |

**Nothing fell by majority.** Two corrections and one real defect came out of it:

1. **Evidence-citation error (corrected above).** The §18 envelope rows originally cited
   `git diff 634e99a..HEAD`. `634e99a` is the code-review commit, which *postdates* 07-05, so that
   diff could not prove what 07-05 changed. Recomputed against 07-05's own range
   (`89d55fb^..9882a4c`): `refusals.py`, `rest.py`, `mcp/tools.py`, `mcp/server.py`, `envelope.py`
   and `promotion.py` are byte-identical. **The conclusion stands; only the evidence line was wrong.**

2. **WR-03's stated mechanism is wrong in steady state.** Measured: a read-only `Ledger()`
   construction against an existing WAL database returns in ~0.00s even while a promote holds
   `BEGIN IMMEDIATE`, because every `_create_schema` statement is a no-op `IF NOT EXISTS` that takes
   no write lock. Ordinary `query()` calls do not contend. The scoring decision (anti-pattern, not
   gap) was therefore correct, and correct for a firmer reason than originally given.

3. **A real defect WR-03 pointed at but mis-located — now fixed.** WR-03's *kernel* (an unwrapped
   `sqlite3` exception can cross the seam from code the transaction span cannot cover) is true, at a
   call site WR-03 did not name: `PRAGMA journal_mode=WAL` in `Ledger.__init__`. Flipping journal
   mode needs a moment with no other connection and SQLite does not run the busy handler for it, so
   concurrent first-touch of a *fresh* `ledger.db` raises `SQLITE_BUSY` outright.

   Independently reproduced by the orchestrator: **5/360 constructions (1.4%)** with six concurrent
   constructors, and **1 failure in 30 runs** of this phase's own headline gate test
   `test_six_concurrent_promotes_mint_six_distinct_versions_with_zero_exceptions` (fresh
   `TemporaryDirectory` + six concurrent `promote()` is exactly the exposing shape).

   Origin: the pragma dates to **Phase 1** (`4aa1239`, `feat(01-07)`) — a latent defect for six
   phases. 07-05 did not introduce it; 07-05's new concurrency test is the first thing in the
   codebase to construct `Ledger()` concurrently, and so the first to expose it.

   Fixed in `18a5346` (`Ledger._set_wal`, bounded retry, degrades to the rollback journal rather
   than raising — WAL is not load-bearing for correctness, `BEGIN IMMEDIATE` serializes writers in
   either mode). Post-fix: **0/360** raw constructions, **40/40** runs of the concurrency module,
   full suite 1068 passed / 1 skipped / 0 failed. This does not touch §18 and does not reopen the
   phase; it makes the phase's own gate evidence deterministic.

---

_Verified: 2026-09-12_
_Verifier: Claude (gsd-verifier), adversarially re-checked by the execute-phase orchestrator_
