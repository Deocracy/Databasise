# GATE-01 — Waiver Record

This document is GATE-01's deliverable: the written owner decision amending the ratified §VD
verdict's stated condition. It is recorded in this project's own layer — `docs/system-model/` is a
verbatim upstream mirror of the ratified system model and is never edited; this record cites into
it instead.

## What is amended

The governing document is `docs/system-model/D-VARIANTS/SELECTION.md`. Two of its clauses are the
subject of this record.

**`## Conditions on the selection`, item 6** (quoted in full):

> **The eval instrument precedes every claim this architecture makes** (shared blind spot #8,
> stated here rather than buried): at 30–50 questions no variant's advantage exists — power for
> +5 pp is ≈0.10 and a naive adopt-if-higher rule promotes noise ~5:1 [docs-verified,
> RT-selfimprove §2]. The settled sequencing (eval bundle + gate → isolation → architecture)
> stands, with the bundle carrying both target families, continuous scoring where possible, T1
> retrieval metrics for retrieval-side mutations, and a size honestly derived from the target MDE.
> **Benchmarks never settle decisions; only local measurement on our own corpus does.**

**`## Falsifiers`, item 5** (quoted in full — the clause this record amends):

> **Per-tier A/A nulls are not materially narrower at T1 than T0.** Then the ladder buys no
> statistical power and is decoration; D1's refusal-instead-of-labeling becomes the cheapest
> correct design. *Experiment:* first A/A calibration run, measurable before any architecture
> exists.

**`## Falsifiers`, item 2** (quoted in full — the clause this record does **not** amend):

> **Depth cannot be computed statically.** Over three real parts (decomposed `lightrag-local`,
> opaque `codebase-memory-mcp`, half-decomposed LightRAG), the validator cannot derive `depth`
> from wiring + registry without a self-declaration. Then D4 has no brake and D's regime was doing
> structural work. *Experiment:* write the depth computation against the three wirings' specs;
> days, no execution.

## The amendment

Three clauses.

**First — Falsifier 2 is satisfied now.** `databasise/evidence/FALSIFIER-2-EVIDENCE.md` is the
committed, re-runnable evidence: `effective_depth` and `execution_mode` are derived from each
wiring's `nodes`/`deps` plus `default_registry()` alone, through
`databasise.validator.depth.effective_depth` and
`databasise.validator.execution_mode.derive_execution_mode`, with no self-declared value read from
any wiring document. It covers the three named wirings the falsifier itself names —
`w1-lightrag-query-side` (decomposed lightrag-local query side), `w2-codebase-memory-mcp` (opaque
codebase-memory-mcp arm), and `w3-lightrag-half-decomposed` (half-decomposed full LightRAG) — plus
the seven-probe self-declaration and blast-radius suite (`databasise/tests/validator/test_falsifier2_probes.py`,
`databasise/tests/validator/test_falsifier2_evidence.py`). Its recorded verdict: **Falsifier 2 did
not fire.** D4's brake holds.

**Second — Falsifier 5 moves to its point of first need**, which is Phase 3's parity comparison at
the earliest, calibrated against the real pre-decomposition LightRAG rather than a stand-in arm.
D-01's own rationale, reproduced: the floor would otherwise be calibrated on a stand-in — Phase 1
has only canned deterministic parts — and calibrating against the real pre-decomposition LightRAG
when it first exists is better methodology as well as cheaper.

**Third — the ladder proceeds to rung 2.** Phase 3 (LightRAG Query Side) is authorised to start
once Falsifier 2 has passed, without waiting on a Falsifier 5 result that would in any case be
calibrated against a stand-in arm today.

## What is not amended

A Falsifier 2 failure still halts the ladder as a SELECTION.md-level reversal, not a repairable
defect. Condition 6's substance — no promotion or parity claim rides on an unmeasured comparison
— is re-timed, not withdrawn: it now applies at Phase 3's parity comparison rather than at Phase 2,
via the standing condition below.

## The standing condition

This waiver holds only so long as no promotion decision and no parity claim is taken before the
A/A floor exists. Until Phase 3 calibrates that floor, Phase 3's substitute gate (D-05) applies:
deterministic, zero-token retrieval-level comparison of retrieved chunk sets and rankings between
the original and the decomposed query side, plus human spot-checks of answers. Its accepted risk,
in the owner's own terms: subtle answer-quality drift is unmeasured until a floor is calibrated,
judged low because Phase 3 keeps the same prompts and models, so decomposition bugs surface at the
retrieval level.

## Reversibility

D-01's own rating: **reversible** — the bundle and calibration design is fully specified in RIG
§EV.1-§EV.3 and §AA.1-§AA.3 and can be stood up whenever wanted.

## Banked decisions

Each already-settled eval-run decision, so whoever executes the calibration inherits the decision
and its rating rather than re-deriving either:

- **D-06** — corpus: HotpotQA distractor setting.
- **D-07** — generator: qwen/qwen3.7-flash via OpenRouter, provider-pinned; free models restricted
  to drafts only, because a re-routed provider changes identity mid-run.
- **D-08** — judge: never free, provider-pinned and prompt-hashed, with its identity derived from
  the provider and model the response actually returns. Rated **one-way**: changing the judge
  mints a new bundle version and voids every null calibrated under it.
- **D-09** — embedder: local via Ollama, so tier one stays genuinely free.
- **D-10** — declared concurrency: picked once and held. Rated **costly**: changing it requires
  recalibrating the floor.
- **D-11** — the three calibration preconditions that must hold before a recorded run counts:
  cache bypassed and checkable per node, temperature honoured by the pinned provider, and no
  invisible upstream prompt caching.
- **D-12** — account prep.
- **D-13** — the machine-side fact that constrains D-10: the v1 three-runs-at-a-time cap is gone
  in the v2 machine — concurrency is a per-node semaphore sized by that node's own config with no
  process-wide cap — so a declared concurrency setting is a per-node config value and the binding
  limit is the API provider, not the runner.

## What this authorises

This record authorises the tracking changes made alongside it: `MACH-02` and `MACH-03` move to
Phase 3 (point of first need: Phase 3's parity comparison), and `HARD-01` and `HARD-02` move to
Phase 7's hardening pass (point of first need: Phase 7's hardening pass). Neither deferral is
open-ended — each carries a named phase and a named point of first need.

## Decision and date

**Decision:** Falsifier 2 is satisfied now with committed evidence; Falsifier 5 is deferred to
Phase 3's point of first need; the ladder proceeds to rung 2. A Falsifier 2 failure still halts the
ladder as a SELECTION.md-level reversal.

**Owner:** Christopher (Deocracy)
**Date:** 2026-08-31
