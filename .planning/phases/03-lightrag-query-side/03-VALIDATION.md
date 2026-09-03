---
phase: 3
slug: lightrag-query-side
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-31
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2+ with pytest-asyncio 1.2+, `asyncio_mode = "auto"` |
| **Config file** | `databasise/pyproject.toml` (`[tool.pytest.ini_options]`, `testpaths = ["tests"]`) |
| **Quick run command** | `cd databasise && uv run pytest -q tests/parts_core/lightrag/ tests/clients/` |
| **Full suite command** | `cd databasise && uv run pytest -q` (matches the configured `workflow.test_command` in `.planning/config.json`) |
| **Estimated runtime** | Quick: ~2.1s wall (measured this session, `python3 -c "time.time()"` around the subprocess); full: ~34.8s wall (415 passed, 4 skipped, measured this session) |

No test-framework install was needed at Wave 0: `pytest`/`pytest-asyncio` were already present from Phase 1/2 (`databasise/pyproject.toml`'s existing dev-dependency group). Plan 03-01 Task 2 added exactly two new runtime dependencies (`openai`, `jsonpatch`) via the package-legitimacy checkpoint (Task 1), neither a test-framework change.

---

## Sampling Rate

- **After every task commit:** Run `cd databasise && uv run pytest -q tests/parts_core/lightrag/ tests/clients/`
- **After every plan wave:** Run `cd databasise && uv run pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 3 seconds (quick command; measured ~2.1s wall, under budget)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | MODAL-01 | N/A | N/A | manual (checkpoint:human-verify, gate=blocking-human) | none — package-legitimacy gate, approved by owner before Task 2 ran | N/A (checkpoint) | ✅ approved |
| 3-01-02 | 01 | 1 | MODAL-01 | N/A | N/A | static import check | `cd databasise && uv run python -c "import openai, jsonpatch, databasise.clients, databasise.parity, databasise.wirings, databasise.parts_core.lightrag; print('ok')"` | ✅ | ✅ green |
| 3-01-03 | 01 | 1 | MODAL-01 | N/A | N/A | unit | `cd databasise && uv run pytest -q tests/clients/ -x` | ✅ | ✅ green |
| 3-01-04 | 01 | 1 | MODAL-01 | N/A | N/A | unit | `cd databasise && uv run pytest -q tests/runner/ tests/clients/ tests/parts/ -x` | ✅ | ✅ green |
| 3-02-01 | 02 | 2 | MODAL-01 | N/A | N/A | static import check + boundary check | `cd v1 && uv run python -c "import lightrag, pycozo, faiss; print('v1 arm runnable')" && cd .. && cd databasise && uv run python -m databasise.tools.check_import_boundary` | ✅ (`v1/.venv` build tooling present) | ⚠️ flaky — passes on a machine holding `v1/.venv`; environment-gapped on this worktree (`v1/.venv` absent, see 03-04-SUMMARY.md through 03-09-SUMMARY.md's shared documentation of this gap). The `check_import_boundary` half passes standalone (verified this session, exit 0). |
| 3-02-02 | 02 | 2 | MODAL-01 | N/A | N/A | static import check | `cd databasise && uv run python -c "from databasise.parity.corpus import load_snapshot; snap = load_snapshot(); print('docs', len(snap.documents), 'queries', len(snap.queries), 'hash', snap.corpus_hash[:12]); assert snap.documents and snap.queries"` | ✅ | ✅ green (verified this session: 20 docs, 2 queries, hash `ac55d19ec162`) |
| 3-02-03 | 02 | 2 | MODAL-01 | N/A | N/A | unit | `cd databasise && uv run pytest -q tests/parity/test_import_verification.py -x` | ✅ | ✅ green |
| 3-03-01 | 03 | 1 | MACH-02, MACH-03 | N/A | N/A | file/grep assertion | `test -f .planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md && grep -q "Phase 6" ... && grep -q "SELECTION.md" ... && grep -qi "residual risk" ... && echo AMENDMENT_OK` | ✅ | ✅ green |
| 3-03-02 | 03 | 1 | MACH-02, MACH-03 | N/A | N/A | grep assertion | `grep -n "03-GATE-AMENDMENT" .planning/ROADMAP.md .planning/REQUIREMENTS.md && grep -E "^\| MACH-0[23] \| Phase 6 \|" .planning/REQUIREMENTS.md && grep -E "^\| MODAL-01 \| Phase 3 \|" .planning/REQUIREMENTS.md` | ✅ | ✅ green (re-verified this session) |
| 3-03-03 | 03 | 1 | MACH-02, MACH-03 | N/A | N/A | script assertion | `python3 -c "..."` — parses `COVERAGE.md`'s decision rows, asserts ≥15 rows and 0 unreasoned opt-outs | ✅ | ✅ green |
| 3-04-01 | 04 | 3 | MODAL-01 | N/A | N/A | manual (checkpoint, pre-resolved) | none — component-naming-convention decision, resolved by the owner (`versioned`) before this plan ran | N/A (checkpoint) | ✅ pre-resolved |
| 3-04-02 | 04 | 3 | MODAL-01 | N/A | N/A | unit + integration | `cd databasise && uv run pytest -q tests/parts_core/lightrag/ tests/parity/test_naive_arm_end_to_end.py -x` | ✅ | ✅ green |
| 3-04-03 | 04 | 3 | MODAL-01 | N/A | N/A | unit (skip-guarded live case) | `cd databasise && uv run pytest -q tests/parity/test_embedder_index_reproduction.py -x` | ✅ | ✅ green (offline cases); real sample-reproduction case skip-guarded, `human_judgment: true` per 03-04-SUMMARY.md D5 |
| 3-05-01 | 05 | 4 | MODAL-01 | N/A | N/A | unit | `cd databasise && uv run pytest -q tests/stores/test_graph.py tests/stores/test_graph_frozen_bugs.py -x` | ✅ | ✅ green |
| 3-05-02 | 05 | 4 | MODAL-01 | N/A | N/A | unit | `cd databasise && uv run pytest -q tests/parts_core/lightrag/ -x` | ✅ | ✅ green |
| 3-05-03 | 05 | 4 | MODAL-01 | N/A | N/A | unit | `cd databasise && uv run pytest -q tests/parts_core/lightrag/ tests/stores/ -x` | ✅ | ✅ green |
| 3-06-01 | 06 | 5 | MODAL-01 | N/A | N/A | unit | `cd databasise && uv run pytest -q tests/parts_core/lightrag/test_transform_parts.py -x` | ✅ | ✅ green |
| 3-06-02 | 06 | 5 | MODAL-01 | N/A | N/A | unit | `cd databasise && uv run pytest -q tests/parts_core/lightrag/ -x` | ✅ | ✅ green |
| 3-06-03 | 06 | 5 | MODAL-01 | N/A | N/A | unit (validator conformance) | `cd databasise && uv run pytest -q tests/parity/test_arm_conformance.py -x` | ✅ | ✅ green |
| 3-07-01 | 07 | 6 | MODAL-01 | N/A | N/A | boundary check + static assertion | `cd databasise && uv run python -m databasise.tools.check_import_boundary && uv run python -c "from databasise.parity.v1_arm import V1ArmResult; fields = set(getattr(V1ArmResult, '__dataclass_fields__', {})); assert 'chunk_ids' in fields and 'answer' in fields, sorted(fields); print('v1 arm surface ok')"` | ✅ | ✅ green (verified this session, boundary check exit 0) |
| 3-07-02 | 07 | 6 | MODAL-01 | N/A | N/A | unit (deterministic group) + skip-guarded live case | `cd databasise && uv run pytest -q tests/parity/test_retrieval_parity.py -x` | ✅ | ✅ green (11 passed, 1 skipped this session — real two-arm run skip-guarded, `human_judgment: true`) |
| 3-07-03 | 07 | 6 | MODAL-01 | N/A | N/A | unit | `cd databasise && uv run pytest -q tests/parity/ -x` | ✅ | ✅ green |
| 3-08-01 | 08 | 6 | MODAL-01 | N/A | N/A | unit | `cd databasise && uv run pytest -q tests/parity/test_storage_audit.py tests/runner/ -x` | ✅ | ✅ green |
| 3-08-02 | 08 | 6 | MODAL-01 | N/A | N/A | unit + boundary check | `cd databasise && uv run pytest -q tests/test_import_boundary.py -x && uv run python -m databasise.tools.check_import_boundary` | ✅ | ✅ green |
| 3-08-03 | 08 | 6 | MODAL-01 | N/A | N/A | unit + script assertion | `cd databasise && uv run pytest -q tests/validator/ tests/parts/ -x && uv run python -c "..."` — asserts the retired stub's identity string is gone and Falsifier 2's verdict text is unchanged | ✅ | ✅ green |
| 3-09-01 | 09 | 7 | MODAL-01, MACH-02, MACH-03 | N/A | N/A | script assertion (provenance check) | `cd databasise && uv run python -m databasise.evidence.parity_report --check-results` | ✅ | ✅ green (this session: "provenance check: clean (5 arms)") |
| 3-09-02 | 09 | 7 | MODAL-01 | N/A | N/A | unit | `cd databasise && uv run pytest -q tests/parity/test_parity_evidence.py -x` | ✅ | ✅ green (25 passed) |
| 3-09-03 | 09 | 7 | MODAL-01, MACH-02, MACH-03 | N/A | N/A | unit (full suite) + human-check | `cd databasise && uv run pytest -q` | ✅ | ✅ green (415 passed, 4 skipped, this session); human-check performed — see Manual-Only Verifications and 03-09-SUMMARY.md |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Row 3-02-01's `⚠️ flaky` reflects a real, previously-documented fact (03-04-SUMMARY.md through 03-08-SUMMARY.md all record the same gap independently): the `v1/.venv` build artifact is a gitignored, worktree-local product of plan 03-02's own execution session and is absent whenever a fresh worktree is spawned for a later plan — including this one. The command's second half (`check_import_boundary`) is environment-independent and was re-verified green this session; the first half (`import lightrag, pycozo, faiss` under `v1/`) requires `v1/.venv` to exist, which it currently does not on this machine. This is not a code defect — it is the exact environment gap this SUMMARY and 03-09-SUMMARY.md document throughout.

---

## Wave 0 Requirements

- [x] `databasise/tests/parts_core/lightrag/` — populated across plans 03-04 through 03-06 (17 + 13 + transform-part tests)
- [x] `databasise/tests/clients/` — populated by plan 03-01 Task 3
- [x] `databasise/tests/parity/` — populated across plans 03-02 through 03-09 (import verification, naive-arm end-to-end, embedder-index reproduction, arm conformance, retrieval parity, keyword variance, storage audit, parity evidence)
- [x] `databasise/tests/parity/conftest.py` — the skip-guarded `v1_venv_python`/`v2_parity_store_dir`/`v1_env_parity_path` fixtures plan 03-02 introduced and 03-04/03-07/03-08 reused
- [x] `openai`, `jsonpatch` — the two new runtime dependencies plan 03-01 Task 2 added; no test-framework install was needed (pytest/pytest-asyncio already present from Phase 1/2)

No framework install was needed beyond the two library additions in plan 03-01 (per 03-09-PLAN.md Task 3's own instruction).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|--------------------|
| Human spot-check of answer substance (criterion 6) | MODAL-01 | An LLM-generated answer's *substance* (does it say the same thing as the other arm's answer) is not mechanically checkable — `generate` is stochastic and no A/A floor is calibrated yet (MACH-02/MACH-03 deferred to Phase 6, `03-GATE-AMENDMENT.md`), so word-for-word equality is not the right bar and only a human judgment call substitutes for it. | With the v1 environment rebuilt and the imported index present (both true as of the 03-10 fix cycle's completed run): for each of the corpus snapshot's 2 queries (q1, q2 — see note below), run `cd databasise && uv run python -m databasise.parity.run_comparison --arm naive --query "<query text>"`, then separately run the same query through v1 directly (`v1/README-PARITY.md`'s ingest-adjacent query path) to read both answers side by side, and judge whether the substance matches. **`--arm naive`, not `hybrid`** (corrected 2026-09-03, 03-10 fix cycle finding 5): `hybrid`/`local`/`global`'s decomposed runs degrade before reaching `generate` (`entity-hydrate-expand`/`relation-hydrate-expand` raise `NodeExecutionError` — see `PARITY-EVIDENCE.md`'s per-arm degradation notes), so none of the three produces a decomposed-side answer to compare; v1's own answer for those query/arm pairs is also `"…[no-context]"`, so instructing a spot-check against any of them would mean judging two non-answers. `naive` is the arm whose pipeline actually completed end to end on both sides. The graph arms become usable for this spot-check once their crash is repaired (out of the 03-10 fix cycle's scope). **Note on the plan's own "three query pairs" instruction**: the committed corpus snapshot (`databasise/tests/fixtures/corpus/MANIFEST.json`) carries exactly 2 queries (q1, q2), not 3 — confirmed this session (`load_snapshot()` returns `len(queries) == 2`). A third pair requires either running a second arm over one of the two existing queries (still a genuine pair, different arm) or the owner extending the corpus snapshot; recorded here as a discrepancy between the plan text and the actual fixture rather than silently substituting 2 for 3. |
| Owner's read of `PARITY-EVIDENCE.md` | MODAL-01, MACH-02, MACH-03 | The document's own stated purpose (03-09-PLAN.md's objective: "criterion 2 is not satisfied by a harness that could produce a band; it is satisfied by the owner reading one") makes the owner's read itself the verification, not a proxy for it. | Read `databasise/evidence/PARITY-EVIDENCE.md` top to bottom. On this machine it currently states, section by section, that every one of the five arms' comparisons and storage audits is `inconclusive` — no comparison has actually run (see the document's own "What was compared" and "Verdict" sections). Once the owner rebuilds the v1 environment and re-runs the five comparisons (`03-09-SUMMARY.md`'s "Next Phase Readiness" names the exact commands), re-reading this same document after re-running `parity_report.py` is what closes criterion 6 and criterion 2 for real. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — the two `checkpoint:human-verify`/pre-resolved-checkpoint tasks (3-01-01, 3-04-01) are the only tasks without an `<automated>` command, and both are recorded checkpoints with an owner decision on file (approved / `versioned`), not gaps.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify — the two checkpoint tasks (3-01-01, 3-04-01) are each immediately followed by an automated-verify task, never adjacent to each other.
- [x] Wave 0 covers all MISSING references — see Wave 0 Requirements above; all five referenced test directories/fixtures exist on disk (confirmed this session).
- [x] No watch-mode flags — every `<automated>` command in the Per-Task Verification Map above is a one-shot `pytest -q` / `python -c` / `grep` / import-check invocation; none carries `--watch`, `pytest-watch`, or an equivalent.
- [x] Feedback latency < 3s — quick command (`tests/parts_core/lightrag/ tests/clients/`) measured ~2.1s wall this session.
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-09-01 (this validation pass, executed within 03-09-PLAN.md Task 3)

**Note on the phase's real-environment coverage gap.** This sign-off certifies that every task in the phase carries a real, passing, non-vacuous automated verification *for the code the phase actually shipped* — the wiring set, the part bodies, the resolver, the harness, the evidence renderer, and their refusal/precondition-gate behavior. It does **not** certify that a real, completed five-arm parity comparison has been run: the `v1/.venv`, `v1/.parity_working_dir`, `v1/.parity_v2_store`, and `v1/.env.parity` build artifacts are absent on this machine (documented independently by 03-04-SUMMARY.md through 03-09-SUMMARY.md), so every comparison and storage-audit run this phase produced reports a genuine, harness-designed `inconclusive`/refusal outcome rather than a fabricated pass. That gap is real-environment-dependent, not code-dependent, and is tracked as the open item in 03-09-SUMMARY.md's "Next Phase Readiness" — not swept under this sign-off.
