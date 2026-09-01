---
phase: 03-lightrag-query-side
plan: 03
subsystem: planning-governance
tags: [gate-amendment, requirements-tracking, api-coverage]
dependency graph:
  requires: [02-GATE-01-WAIVER.md]
  provides: [03-GATE-AMENDMENT.md, COVERAGE.md]
  affects: [.planning/ROADMAP.md, .planning/REQUIREMENTS.md]
tech-stack:
  added: []
  patterns: [written-amendment-record, capability-subtraction-matrix]
key-files:
  created:
    - .planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md
    - .planning/phases/03-lightrag-query-side/COVERAGE.md
  modified:
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md
decisions:
  - "MACH-02/MACH-03 (eval bundle + A/A calibration, Falsifier 5) deferred a second time, Phase 3 to Phase 6, per D-10's technical argument (shared index + pinned model identity make retrieval-level parity a sharper rung-2 instrument than an unmeasured A/A floor)"
  - "Residual risk stated plainly per D-11: answer-level drift in `keywords` and `generate` stays unmeasured until Phase 6's floor exists"
  - "ROADMAP.md Phase 6 gains a new success criterion (6) carrying the eval-bundle/A/A-calibration obligation forward; Phase 3's own criterion 2 now points at criterion 6's retrieval-level substitute gate instead of a floor Phase 3 no longer calibrates"
  - "COVERAGE.md decides all 18 identified capabilities of the OpenAI-compatible surface (chat-completions, embeddings, usage, provider pinning, sampling params INTEGRATE; streaming, rerank, catalogue, tools, structured-output, logprobs, images, audio, files, fine-tuning, batch, moderations, responses-API OPT-OUT), each opt-out carrying a one-line reason"
actuals:
  tokens: 5500
  tasks: 3
  commits: 3
status: complete
---

# Phase 3 Plan 03: MACH-02/MACH-03 Gate Amendment & API Coverage Matrix Summary

Second deferral of MACH-02/MACH-03 to Phase 6 recorded as a written, owner-visible amendment mirroring GATE-01's own structure, propagated into ROADMAP.md and REQUIREMENTS.md, alongside a full INTEGRATE/OPT-OUT matrix for the OpenAI-compatible model API this phase integrates.

## What Was Built

**`03-GATE-AMENDMENT.md`** — follows `02-GATE-01-WAIVER.md`'s section order (what is amended, quoting ROADMAP Phase 3 criteria 4/5 and RIG §EV.1/§EV.2/§AA.1 verbatim; the amendment; what is substituted; residual risk; what is not amended; reversibility; what this authorises; decision and date). States D-10's technical argument for the second deferral, names Phase 6's cross-modality run as the point of first need, and states D-11's residual risk verbatim: answer-level drift in `keywords` and `generate` stays unmeasured until the floor exists. Cites `docs/system-model/D-VARIANTS/SELECTION.md` as governing; `docs/system-model/` was not touched.

**ROADMAP.md** — Phase 3 criteria 4 and 5 marked `*(amended 2026-08-31 per 03-GATE-AMENDMENT.md)*` with the original text preserved (matching the file's existing amendment style), the Overview's A/A-floor sentence retimed to Phase 6, Phase 3's own criterion 2 repointed at criterion 6's substitute gate (fixing a dangling reference to the now-deferred criterion 5), Phase 3's `Requirements:` line and the Requirement Coverage table's Phase 3/Phase 6 rows updated, a new Phase 6 success criterion 6 added carrying the eval-bundle/A/A-calibration obligation forward, and the Ordering Constraints "Eval infrastructure at point of need" line retimed to Phase 6.

**REQUIREMENTS.md** — MACH-02 and MACH-03's bracketed amendment notes extended with the second move (same format as GATE-01's existing note), and both phase-assignment table rows changed from Phase 3 to Phase 6 with `Pending` status retained. MODAL-01 untouched, still Phase 3.

**`COVERAGE.md`** — 18-row INTEGRATE/OPT-OUT table for the OpenAI-compatible surface (OpenRouter, Ollama). `chat.completions` (non-streaming), `embeddings`, `usage`, provider pinning, and deterministic sampling params are INTEGRATE. Streaming, rerank (cites D-09), model catalogue, tool calling, structured-output, logprobs, images, audio, files, fine-tuning, batch, moderations, and the responses API are OPT-OUT, each with a one-line reason.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed dangling cross-reference in ROADMAP.md Phase 3 criterion 2**
- **Found during:** Task 2
- **Issue:** Criterion 2 read "the band sits inside this phase's own calibrated A/A floor (criterion 5)" — after amending criterion 5 to defer the floor to Phase 6, this reference pointed at a floor Phase 3 no longer calibrates, contradicting the amendment's own purpose.
- **Fix:** Repointed the sentence at criterion 6's deterministic retrieval-level substitute gate, with a parenthetical noting the floor itself is deferred per criteria 4/5's amendment.
- **Files modified:** `.planning/ROADMAP.md`
- **Commit:** c5bc59e

**2. [Rule 1 - Bug] Updated Requirement Coverage table and Ordering Constraints line beyond the task's literal action list**
- **Found during:** Task 2
- **Issue:** The task's `<action>` enumerated Phase 3 criteria 4/5, the Overview sentence, and Phase 6's new criterion, but not the Requirement Coverage table (which still listed MACH-02/MACH-03 against Phase 3) or the "Eval infrastructure at point of need" ordering-constraint sentence (which still named Phase 3's parity comparison as the bundle/floor's point of first need). Both directly contradicted the amendment and the plan's own top-level `<verification>` block ("ROADMAP.md ... neither carries MACH-02 or MACH-03 against Phase 3 any more").
- **Fix:** Updated the Requirement Coverage table's Phase 3 and Phase 6 rows, and retimed the Ordering Constraints sentence to Phase 6 with a note that Phase 3 uses the retrieval-level substitute gate instead.
- **Files modified:** `.planning/ROADMAP.md`
- **Commit:** c5bc59e

Both fixes stayed within scoped `Edit` replacements confined to the Phase 3 section, the Phase 6 section, the Requirement Coverage table's Phase 3/6 rows, and the Ordering Constraints eval-infrastructure line — no other phase's entries were touched (`git diff --stat` confirms a bounded 10-insertion/9-deletion diff).

## Known Stubs

None. This plan produces planning-governance documents only; no code stubs.

## Self-Check: PASSED

- FOUND: `.planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md`
- FOUND: `.planning/phases/03-lightrag-query-side/COVERAGE.md`
- FOUND commit 7504880 (Task 1: amendment record)
- FOUND commit c5bc59e (Task 2: ROADMAP/REQUIREMENTS propagation)
- FOUND commit 14e150d (Task 3: coverage matrix)
- Verified: `git status --short docs/` is empty — upstream mirror untouched
- Verified: `.planning/REQUIREMENTS.md` phase-assignment table shows MACH-02/MACH-03 at Phase 6, MODAL-01 at Phase 3
- Verified: COVERAGE.md verify script reports 18 rows, 0 unreasoned opt-outs
