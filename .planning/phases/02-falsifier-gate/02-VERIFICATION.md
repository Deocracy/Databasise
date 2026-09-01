---
phase: 02-falsifier-gate
verified: 2026-09-01T00:17:49Z
status: passed
score: 8/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 2: Falsifier Gate Verification Report

**Phase Goal:** Depth and execution mode are computed rather than declared, and the rung-1→rung-2 gate decision is recorded — the condition the ratified verdict rides on now, with the calibrated A/A noise floor deferred to its point of first need per the GATE-01 waiver record
**Verified:** 2026-09-01T00:17:49Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Owner runs the validator over the three named wirings and reads `effective_depth`/`execution_mode` computed (not self-declared), with §19.10 boundary enumeration recorded | ✓ VERIFIED | Ran `evaluate_wiring()` live for all three wirings — output matches SUMMARY's claimed table exactly (W1 all `stage`/`in-process` except `refine`→`long-lived-service`; W2/W3 taint-override to `opaque`). `FALSIFIER-2-EVIDENCE.md` contains `19.10`, `effects-change`, `value-crossing`, `knob` sections per wiring. |
| 2 | Every depth/execution_mode value comes from the canonical runner functions, never a reimplementation or self-declaration | ✓ VERIFIED | `evidence/falsifier2.py` imports `derive_execution_mode` only from `databasise.validator.execution_mode` (grep confirms zero occurrences of the superseded `validator.depth` import, zero `run_wiring`/`dispatch(` calls). Read source directly. |
| 3 | A self-declared derived field on a wiring node is refused (`self-declared-derivation`), distinguishable by code from an ordinary unknown-key typo (`invalid-node-schema`) | ✓ VERIFIED | Live execution: a node declaring `effective_depth: stage` is refused with code `self-declared-derivation` naming the node/field/computing-function; the same node with an unrelated unknown key `notes` is refused with `invalid-node-schema`. Confirmed by direct `parse_wiring()` call, not just test trust. |
| 4 | Answer-level and index-side measurement stays off by default; no measurement-gated promotion path exists; fallback runs are labelled `degraded`/`degradation_reason` | ✓ VERIFIED | `02-MACH-09-POSTURE.md` records the posture and cites Phase-1-landed `runner/trace.py`/`runner/scheduler.py` labelling (already tested). `tests/runner/test_measurement_posture.py` (3 tests, all passing) structurally pins no non-test ledger import, no promotion verb, `LedgerRecord.promotion_provenance` has no default — read source directly, confirmed AST-scan logic present. |
| 5 | The rung-1→rung-2 gate decision is written down; a Falsifier 2 failure still halts the ladder as a SELECTION.md-level reversal | ✓ VERIFIED | `02-GATE-01-WAIVER.md` quotes SELECTION.md's Falsifiers items 2 and 5 and Conditions item 6, states Falsifier 2 satisfied now / Falsifier 5 deferred / ladder proceeds, and explicitly states Falsifier 2 failure remains a halting SELECTION.md-level reversal. `ROADMAP.md`'s Ordering Constraints section cites the waiver by path. |
| 6 | The re-scope (MACH-02/MACH-03 → Phase 3, HARD-01/HARD-02 → Phase 7) is legitimate, complete, and every one of the 34 requirements still maps to exactly one phase | ✓ VERIFIED | `02-GATE-01-WAIVER.md`'s "What this authorises" section names the exact move. `ROADMAP.md` Phase 3/Phase 7 detail blocks and Requirement Coverage table (4+3+3+7+8+4+5=34, verified by arithmetic) agree with `REQUIREMENTS.md`'s traceability table (spot-checked all 34 rows) and with each requirement's own amendment-note text citing the waiver. No requirement dropped. |
| 7 | The evidence document is regenerable and byte-stable (generated output, never hand-edited) | ✓ VERIFIED | Ran `uv run python -m databasise.evidence.falsifier2` fresh; `git diff --exit-code -- evidence/FALSIFIER-2-EVIDENCE.md` exits 0 (drift gate clean). |
| 8 | The full test suite is green under the stricter, phase-produced validator behavior | ✓ VERIFIED | Ran `cd databasise && uv run pytest -q` fresh: 259 passed, 0 failed. Ran the 26 phase-specific tests individually (`test_measurement_posture.py`, `test_falsifier2_probes.py`, `test_falsifier2_evidence.py`): 26 passed. |

**Score:** 8/8 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `databasise/evidence/falsifier2.py` | Re-runnable Falsifier 2 evidence run, canonical imports | ✓ VERIFIED | Exists, substantive, wired to `validator.execution_mode`/`validator.depth`/`parts.registry`; produces correct live output |
| `databasise/evidence/FALSIFIER-2-EVIDENCE.md` | Computed-vs-declared table + §19.10 enumeration + probe section + verdict | ✓ VERIFIED | 118 lines, all required sections present, byte-stable against fresh render |
| `databasise/evidence/wirings/{w1,w2,w3}*.json` | Three named MACH-01 wirings resolving against `default_registry()` | ✓ VERIFIED | All three parse, all `component` values resolve without raising (confirmed by direct import/eval) |
| `databasise/validator/errors.py` | `CODE_SELF_DECLARED_DERIVATION` | ✓ VERIFIED | Present with full docstring, distinct from `CODE_INVALID_NODE_SCHEMA` |
| `databasise/parts/schema.py` | `WiringNode` wire-time strictness | ✓ VERIFIED | `ConfigDict(extra="forbid")`; zero `extra="ignore"` occurrences |
| `databasise/validator/parse.py` | Derived-field classifier | ✓ VERIFIED | `_DERIVED_FIELD_NAMES` (6 fields), `_classify_node_schema_error` routes correctly, confirmed live |
| `databasise/tests/runner/test_measurement_posture.py` | Structural guard for unbuilt promotion path | ✓ VERIFIED | 3 tests present and passing; AST-scan + dataclass-fields checks read directly |
| `.planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md` | GATE-01's deliverable — the written owner amendment | ✓ VERIFIED | All required sections present, cites SELECTION.md and FALSIFIER-2-EVIDENCE.md, `docs/system-model/` untouched (`git status --porcelain docs/system-model/` empty) |
| `.planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md` | MACH-09 posture record | ✓ VERIFIED | Contains `promote-next`, `degradation_reason`, `F3.2`, `TR.3`, `CM.3`, `A1-A4` |
| `.planning/ROADMAP.md` (re-scoped) | Coverage/ordering matching re-scope | ✓ VERIFIED | Phase 2/3/7 blocks, coverage table, ordering constraints all match waiver authority |
| `.planning/REQUIREMENTS.md` (re-scoped) | Traceability matching re-scope | ✓ VERIFIED | MACH-02/MACH-03→Phase 3, HARD-01/HARD-02→Phase 7, all with amendment notes citing the waiver |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `evidence/falsifier2.py` | `validator/execution_mode.py` | canonical `derive_execution_mode` import | ✓ WIRED | Confirmed by grep and live execution |
| `evidence/falsifier2.py` | `parts/registry.py` | `default_registry()` | ✓ WIRED | Confirmed live — all three wirings resolve |
| `validator/parse.py` | `validator/errors.py` | `CODE_SELF_DECLARED_DERIVATION` | ✓ WIRED | Confirmed live self-declaration refusal |
| `02-GATE-01-WAIVER.md` | `evidence/FALSIFIER-2-EVIDENCE.md` | names the evidence it rests on | ✓ WIRED | Confirmed by grep — waiver contains `FALSIFIER-2-EVIDENCE.md` |
| `ROADMAP.md` Ordering Constraints | `02-GATE-01-WAIVER.md` | cites waiver as rung-ordering authority | ✓ WIRED | Confirmed — both ordering-constraint bullets cite the waiver path |
| `REQUIREMENTS.md` traceability | `02-GATE-01-WAIVER.md` | amendment notes on moved requirements | ✓ WIRED | Confirmed — all four moved requirement texts carry the citation |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Computed depth/execution_mode matches claimed table | `evaluate_wiring()` for all 3 wirings, live | Exact match to SUMMARY's table | ✓ PASS |
| Self-declaration refusal fires with correct code | `parse_wiring()` with `effective_depth` key on a node | `self-declared-derivation`, correct message | ✓ PASS |
| Typo/unknown-key distinguishable from self-declaration | `parse_wiring()` with `notes` key on a node | `invalid-node-schema` | ✓ PASS |
| Evidence document byte-stable | `python -m databasise.evidence.falsifier2` + `git diff --exit-code` | exit 0, no diff | ✓ PASS |
| Full suite green | `uv run pytest -q` | 259 passed | ✓ PASS |
| `docs/system-model/` untouched by the re-scope | `git status --porcelain docs/system-model/` | empty | ✓ PASS |
| Requirement coverage arithmetic | 4+3+3+7+8+4+5 | 34 | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| GATE-01 | 02-04 | Rung ordering enforced; Falsifier 2/5 failure halts the ladder | ✓ SATISFIED | `02-GATE-01-WAIVER.md` records the decision; `ROADMAP.md` Ordering Constraints enforce it |
| MACH-01 | 02-01, 02-03 | Static validator computes depth/execution_mode; no self-declaration | ✓ SATISFIED | `FALSIFIER-2-EVIDENCE.md`, live-confirmed computation and refusal |
| MACH-09 | 02-02 | Measurement posture off by default, structurally pinned | ✓ SATISFIED | `02-MACH-09-POSTURE.md`, `test_measurement_posture.py` (3/3 passing) |

**Re-scope requirements (moved out of Phase 2, verified as legitimately tracked elsewhere, not dropped):**

| Requirement | Old Phase | New Phase | Status |
|-------------|-----------|-----------|--------|
| MACH-02 | 2 | 3 | ✓ Tracked — `ROADMAP.md` Phase 3 requirements line, `REQUIREMENTS.md` traceability row, both with amendment note citing waiver |
| MACH-03 | 2 | 3 | ✓ Tracked — same, plus Phase 3 success criteria 4/5 carry the moved content verbatim |
| HARD-01 | 2 (rung 1) | 7 | ✓ Tracked — `ROADMAP.md` Phase 7 requirements line + success criterion 5, `REQUIREMENTS.md` traceability row with amendment note |
| HARD-02 | 2 (rung 1) | 7 | ✓ Tracked — same |

No orphaned requirements found (all requirement IDs across all four plans' frontmatter map to REQUIREMENTS.md entries; no REQUIREMENTS.md phase-2-tagged ID is absent from a plan).

### Anti-Patterns Found

None. Grep for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` across all 12 phase-modified files returned zero matches. No empty-implementation or hardcoded-empty-data patterns found in the evidence module (confirmed by reading `falsifier2.py`, `parse.py`, `schema.py`, `errors.py` directly and by live execution producing real computed values, not stubs).

The independent code review (`02-REVIEW.md`, standard depth, 13 files) found 0 critical findings, 3 warnings, 3 info — all in incidental robustness surfaces (unescaped `|` in evidence-table rendering, uncaught `KeyError` on malformed `boundary_knobs`, an AST-import-shape blind spot in the MACH-09 ledger guard for `from databasise import ledger`). None of these affect the phase's core deliverable (the computed-not-declared derivation and its refusal), and none is a debt marker without a tracked follow-up — they are recorded findings in a review artifact, not silent gaps. Treated as non-blocking per the review's own `critical: 0` classification.

### Human Verification Required

None. All must-haves were verifiable programmatically by direct code execution, file inspection, and cross-document consistency checks.

### Gaps Summary

No gaps. All eight derived observable truths verified against live code execution (not test-suite trust alone — computed depth/execution_mode values, the self-declaration refusal, the typo/self-declaration code distinction, and the drift gate were each independently re-executed by this verifier). The mid-phase re-scope (plan 02-04) was checked against its stated authority: the waiver record authorizes exactly the four requirement moves made, `ROADMAP.md` and `REQUIREMENTS.md` agree with each other and with the waiver on every one of the 34 requirement IDs, and none of MACH-02/MACH-03/HARD-01/HARD-02 was dropped — each carries a named new phase and a named point of first need in both tracking documents.

---

*Verified: 2026-09-01T00:17:49Z*
*Verifier: Claude (gsd-verifier)*
