---
phase: "7"
slug: "promotion-rollback"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: true
wave_0_complete: false
created: "2026-09-11"
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from `07-RESEARCH.md ## Validation Architecture`. The Per-Task
> Verification Map is filled once PLAN.md task IDs exist.
>
> Effective scope per `07-CONTEXT.md` D-01/D-02/D-03: **MACH-07 + API-09**
> (ROADMAP success criteria 1–3). HARD-01, HARD-02 and HARD-04 are deferred
> to a later hardening phase via a written amendment record; no rows below
> validate them.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2+ with pytest-asyncio 1.2+ (`databasise/pyproject.toml` → `[dependency-groups] dev`) |
| **Config file** | `databasise/pyproject.toml` → `[tool.pytest.ini_options]` (no separate `pytest.ini`) |
| **Quick run command** | `cd databasise && uv run pytest -q tests/ledger tests/seam -x` |
| **Full suite command** | `cd databasise && uv run pytest -q` |
| **Estimated runtime** | full suite baseline 960+ passed / 3 skipped at Phase 6 close (`06-16-SUMMARY.md`); expect growth this phase |

---

## Sampling Rate

- **After every task commit:** Run `cd databasise && uv run pytest -q tests/ledger tests/seam -x`
- **After every plan wave:** Run `cd databasise && uv run pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green, plus the two transport suites reused verbatim from Phase 6:
  - `cd databasise && uv sync --extra rest && uv run --extra rest pytest -q tests/seam/test_rest_transport.py tests/seam/test_dual_transport.py -x`
  - `cd databasise && uv sync --extra mcp && uv run --extra mcp pytest -q tests/mcp/ -x -rs`
- **Max feedback latency:** ~120 seconds (quick run); full suite bounded by the Phase 6 baseline

---

## Phase Requirements → Test Map (from research)

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MACH-07 (SC1) | Every generation record carries `change_origin` and `promotion_provenance`, never defaulted | unit | `cd databasise && uv run pytest -q tests/ledger/test_ledger.py -k change_origin -x` | ❌ Wave 0 — extend `test_ledger.py` |
| MACH-07 (SC1) | Semver minted only at promotion, MAJOR/MINOR rule correct | unit | `cd databasise && uv run pytest -q tests/seam/test_promote.py -k semver -x` | ❌ Wave 0 |
| MACH-07 (SC1) | Tombstoned losers never lifted (re-promotion is a new generation, not a resurrection) | unit | `cd databasise && uv run pytest -q tests/seam/test_retire.py -k never_lifted -x` | ❌ Wave 0 |
| MACH-07 (SC1) | Active pointer is a derived query, not a written field | unit (regression) | `cd databasise && uv run pytest -q tests/ledger/test_ledger.py -k active_pointer -x` | ✅ existing — extend for new columns |
| API-09 / MACH-07 (SC2) | promote()/rollback() with `operator_asserted` provenance and non-empty `promotion_trace_ids`, no verdict/tier-of-decision; ledger append is atomic | unit + integration | `cd databasise && uv run pytest -q tests/seam/test_promote.py tests/seam/test_rollback.py -x` | ❌ Wave 0 |
| API-09 (SC2) | Disagreeing/unresolvable/empty trace ids refuse by name | unit | `cd databasise && uv run pytest -q tests/seam/test_promote.py -k trace_ids -x` | ❌ Wave 0 |
| MACH-09 / API-09 (SC3) | promote-next/promote-now refuse for answer-level/index-side under default posture, naming the posture | unit | `cd databasise && uv run pytest -q tests/seam/test_promotion_posture.py -x` | ❌ Wave 0 |
| API-09 (SC2/3) | Three-transport parity (in-process/REST/MCP) for promote/rollback/retire | integration | `cd databasise && uv run --extra rest pytest -q tests/seam/test_dual_transport.py -k promot -x` and `cd databasise && uv run --extra mcp pytest -q tests/mcp/test_tool_growth_invariant.py -x` | ✅ existing — extend |
| API-09 | Refusal vocabulary maps to 422 (REST) / ToolError (MCP) automatically | regression | `cd databasise && uv run --extra rest pytest -q tests/seam/test_rest_transport.py -k refusal -x` | ✅ existing — extend `_REFUSAL_FACTORIES` |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| T1 (tracer) — end-to-end promote → ledger → alias read | 07-01 | 1 | MACH-07, API-09 | — | N/A (`workflow.security_enforcement: false`) | integration (end-to-end, one path) | `cd databasise && uv run pytest -q tests/seam/test_promote.py -x` | created by this task | ⬜ pending |
| T2 — trace/change_origin refusals, semver rule, class derivation | 07-01 | 1 | MACH-07, API-09 | — | N/A | unit | `cd databasise && uv run pytest -q tests/seam/test_promote.py -x` | created by T1 | ⬜ pending |
| T3 — verb ladder and posture refusal (SC3) | 07-01 | 1 | MACH-07, API-09 | — | N/A | unit | `cd databasise && uv run pytest -q tests/seam/test_promotion_posture.py -x` | created by this task | ⬜ pending |
| T1 — rollback to an explicit semver | 07-02 | 2 | MACH-07 | — | N/A | unit + integration | `cd databasise && uv run pytest -q tests/seam/test_rollback.py -x` | created by this task | ⬜ pending |
| T2 — retire, tombstone, never-lifted | 07-02 | 2 | MACH-07 | — | N/A | unit + integration | `cd databasise && uv run pytest -q tests/seam/test_retire.py -x` | created by this task | ⬜ pending |
| T1 — three REST routes, refusal mapping | 07-03 | 3 | API-09 | — | N/A | integration | `cd databasise && uv run --extra rest pytest -q tests/seam/test_rest_transport.py -x` | ✅ existing, extended | ⬜ pending |
| T2 — three MCP tools, roster growth, §18.5 coverage record | 07-03 | 3 | API-09 | — | N/A | integration | `cd databasise && uv run --extra mcp pytest -q tests/mcp/ -x -rs` | ✅ existing, extended | ⬜ pending |
| T3 — three-transport conformance + evidence record | 07-03 | 3 | API-09 | — | N/A | integration | `cd databasise && uv run --extra rest pytest -q tests/seam/test_dual_transport.py -x` | ✅ existing, extended | ⬜ pending |

**Wave 0 note.** Every `<automated>` command above is runnable at the end of the task that names it,
because each task creates or extends its own test file inside its own `<files>` set. No task carries
a `MISSING — Wave 0 …` sentinel and no separate Wave 0 plan is needed. Sampling continuity holds: no
three consecutive tasks lack an automated verify, since every task has one.

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `databasise/tests/seam/test_promote.py` — stubs for MACH-07 SC1/SC2, API-09
- [ ] `databasise/tests/seam/test_rollback.py` — stubs for MACH-07 SC1/SC2, API-09
- [ ] `databasise/tests/seam/test_retire.py` — stubs for MACH-07 SC1 (never-lifted)
- [ ] `databasise/tests/seam/test_promotion_posture.py` — stubs for MACH-07/API-09 SC3
- [ ] Extend `databasise/tests/ledger/test_ledger.py` — new columns round-trip
- [ ] Extend `databasise/tests/seam/test_dual_transport.py` — REST parity for the three new verbs
- [ ] Extend `databasise/tests/mcp/test_tool_growth_invariant.py` — MCP roster grows by exactly the new tool names (§18.5 per-operation growth rule)
- [ ] Extend `databasise/tests/seam/test_rest_transport.py` `_REFUSAL_FACTORIES` — one entry per new `SeamRefusalError` subclass
- Framework install: none — pytest/pytest-asyncio already installed via the `dev` dependency group

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Amendment record deferring HARD-01/02/04 is written, ROADMAP criteria 4–5 struck with a pointer, REQUIREMENTS rows carry a dated deferral note and stay Pending | D-03 (CONTEXT.md) | Documentation edits; verified by reading the files | **Discharged at planning time, 2026-09-11** — `07-GATE-AMENDMENT.md` written; `ROADMAP.md` Phase 7 requirements line reads `MACH-07, API-09`, criteria 4 and 5 struck with pointers, and the ordering constraint and coverage table annotated; `REQUIREMENTS.md` rows HARD-01/02/04 carry dated deferral notes and stay Pending with unchecked boxes. Also surfaced as a verifiable truth in `07-01-PLAN.md`'s `must_haves`. Re-read those three files to confirm. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references — no MISSING sentinel exists; every task creates or extends its own test file
- [x] No watch-mode flags
- [x] Feedback latency < 120s (quick run `cd databasise && uv run pytest -q tests/ledger tests/seam -x`)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** plans 07-01..07-03 mapped 2026-09-11
