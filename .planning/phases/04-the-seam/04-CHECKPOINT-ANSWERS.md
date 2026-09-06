# Phase 4 — Checkpoint answers (recorded 2026-09-06)

The owner answered all three of this phase's checkpoints in one batch before execution began, so
each plan's checkpoint task is **already resolved**. Each executor records its own plan's answer in
that plan's SUMMARY under `decisions_recorded_here`, per the checkpoint's acceptance criteria.

## 04-01 — §18.2 envelope field set

**Answer: `declare-upfront`.** The complete field set is declared in wave 1; later plans bind
element types into fields that already exist and MUST NOT widen the envelope. Rationale recorded by
the owner: a closed set that is still open during the phase is not a closed set.

**`resolved_model_identity`: EXCLUDED from the envelope.** No requirement in this phase asks for it,
and including it would make which model answered visible to consumers without that having been
decided under §18.3's invariance rule. FA-02 is resolved by this answer.

## 04-03 — Alias registry read shape

**Answer: `dedicated-alias-column`.** Add one small additive alias column to the ledger now, rather
than overloading `mutation_id`.

Rationale recorded by the owner, which differs from the plan's own first-listed option: the ledger
is append-only and enforced by `BEFORE UPDATE` / `BEFORE DELETE` triggers, so a field carrying two
meanings can never be disentangled once Phase 7 writes the first real row; and Phase 7 is a
committed roadmap phase, not a speculative caller, so the column is not speculative surface.

The registry remains empty in this phase and every alias lookup refuses — that is the expected end
state. This plan must name concretely: the exact lookup call the seam makes, the exact record field
it reads to identify the active wiring, and what Phase 7 must append for the read to succeed.

## 04-05 — Package legitimacy (`blocking-human`)

**Answer: `approved` — all three of fastapi, uvicorn and httpx.**

Recorded evidence: all three resolve to their canonical repositories (`fastapi/fastapi`,
`Kludex/uvicorn`, `encode/httpx`) and are already approved, in-use dependencies in
`v1/pyproject.toml` in this same monorepo. The research audit's `[SUS]` verdict is a tool
data-source artifact — the checker reports only the newest release's publish timestamp and has no
PyPI download counts, so it returns `too-new` / `unknown-downloads` for essentially every package.

fastapi and uvicorn go in the new optional `rest` extra; httpx is test-only and goes in the existing
PEP 735 `dev` group.
