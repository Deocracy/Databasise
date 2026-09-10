# Cross-Modality Evidence — MODAL-05: BLOCKED, Not Discharged

**Date:** 2026-09-09

`.planning/REQUIREMENTS.md` MODAL-05's claim, quoted verbatim:

> LightRAG and HippoRAG 2 run side-by-side on one corpus under RIG §RUN (KV sharing per MACH-08's
> scope rules, isolated graph/vector stores), outputs structurally comparable — the milestone proof
> point. The first genuine seam call records F-14's outcome (the §18.3 seam-invariance falsifier)
> either way

## Status

**BLOCKED. MODAL-05 is NOT discharged.** No real cross-modality run against the Phase 3 parity
corpus occurred in this plan. No index-build counts exist, no token spend exists, no run duration
exists, and no per-query comparison result exists — every one of those figures is the output of a
real invocation that did not happen, and none is reported here, anywhere, as if it had.

**This document does not imply a run happened.** It also does not imply MODAL-05 failed — no
comparison ran, so there is no adverse verdict to record either. MODAL-05 is **open**, not settled
in either direction. F-14's own seam-invariance outcome was already recorded from a real (synthetic
fixture) cross-modality call in `databasise/evidence/F-14-SEAM-INVARIANCE.md` (06-03-PLAN.md) —
that document stays the record for F-14 specifically; this document does not restate or supersede
it. What this document blocks is the *real-corpus* side-by-side run MODAL-05's own text names as
"the milestone proof point" — a different, larger claim than F-14's own synthetic-fixture proof.

## Findings — the blocker, verbatim and verifiable

| # | What | Blocker | Cited authority |
|---|---|---|---|
| 1 | One real invocation of `databasise.parity.build_hipporag_index` against the 20-document Phase 3 parity corpus (`databasise/tests/fixtures/corpus/`, 2,119 words, 15,711 bytes), using live credentials from `v1/.env.parity` (`qwen/qwen3.7-flash` for extraction, `qwen/qwen3-embedding-8b` for embedding) | Not authorized during this plan's execution — presented as a `gate="blocking-human"` checkpoint at Task 1 and resolved by the owner as `defer-and-record-blocked`, not as a spend authorization. No HippoRAG namespace exists under the parity store root today: `v1/.parity_v2_store/` holds only the LightRAG namespace (`shared-4fab18fef508b7bc3dda1cc2d8f12e36`), confirmed by a read-only directory listing — there is no already-built HippoRAG index to reuse in place of the real invocation. | `[code-verified]` `databasise/parity/build_hipporag_index.py` (harness built by this plan, never invoked — its own module docstring states this explicitly); `[code-verified]` `v1/.parity_v2_store/` directory listing at this document's date contains no `hipporag-*`-prefixed namespace |

Because the index build never ran, `databasise.parity.run_cross_modality` (Task 2's own harness,
also built by this plan and also never invoked) has no built HippoRAG index to compare against
either — its own `preflight()` function refuses with `MissingArmIndexError` naming exactly this
absence when pointed at the real parity store, which `databasise/tests/parity/
test_cross_modality_isolation.py`'s skip-guarded real-index tests confirm by skipping cleanly
rather than failing (see that file's own module docstring). Both blockers trace to the single root
cause named in row 1: one real, spend-incurring invocation was not authorized in this plan.

## Owner decision: defer-and-record-blocked

Presented as a `gate="blocking-human"` checkpoint during Task 1 (the spend checkpoint gating one
real invocation of the index-build harness against live `v1/.env.parity` credentials), the owner
selected **defer-and-record-blocked**:

1. **No real invocation runs.** No LLM call, no embedding call, no ingestion, no spend. The index
   build does not happen in this plan.
2. **The harness code is written, not executed.** `databasise/parity/build_hipporag_index.py` and
   `databasise/parity/run_cross_modality.py` are genuine, reviewable, runnable code — the artifact
   a later plan will invoke once spend is authorized — never a stub or a placeholder.
3. **MODAL-05 stays Pending** in `.planning/REQUIREMENTS.md`. This plan's own core-value proof
   point is explicitly NOT delivered.
4. **This document is the honest BLOCKED record** — no simulated numbers, no numbers "for
   illustration," nowhere in this document.

This mirrors 06-06-PLAN.md's own `defer-run` decision for Falsifier 5/MACH-03
(`databasise/evidence/FALSIFIER-5-EVIDENCE.md`), which left MACH-03 Pending for the identical
reason: an unauthorized real invocation against live credentials/real spend. Two of this phase's
evidence requirements ship blocked for the same underlying cause — this document says so plainly
rather than softening it.

## What was built instead

Genuine, runnable harness code — reviewable now, invokable later once spend is authorized:

- `databasise/parity/build_hipporag_index.py` — `build_index()`, `IndexBuildResult`. Builds
  HippoRAG 2's index over the Phase 3 parity corpus for real, verifies non-zero graph node/edge
  counts and non-zero entity/fact vector namespace counts before reporting success (adopting
  03-11-PLAN.md's own guard against a silently-empty extraction pass), and reads token spend from
  the run's own node-trace accounting.
- `databasise/parity/run_cross_modality.py` — `run_cross_modality()`, `preflight()`,
  `CrossModalityRecord`. Runs the Phase 3 corpus's own queries through one `Databasise.compare()`
  call per query against both arms, pre-flight-verifying both arms' indexes are present, their
  resolved store directories are disjoint, and recording `artifacts_overlap` between the two arms'
  index-recipe hashes — refusing to report a run where either arm reports `partial` or `degraded`.
- `databasise/tests/parity/test_cross_modality_isolation.py` — tests the harnesses' own isolation
  logic (`preflight`'s directory-disjointness check, `artifacts_overlap`'s genuine iff, a
  cross-read negative control) against synthetic, hand-seeded stores — no real corpus, no network,
  no spend. Its two tests against the *real* built indexes are guarded to skip cleanly when the
  real index is absent, which is the case on every machine today, including this one.

## Method and limits

**Method.** No real method to report — this document records the deliberate decision not to
proceed past harness-writing into a real invocation, and states plainly why.

**Limits, stated plainly:**

- **No counts, spend, duration, or comparison result is reported anywhere in this document.** An
  absent run has no numbers to report; reporting any — even "for illustration" — would fabricate
  observed data, the same discipline `FALSIFIER-5-EVIDENCE.md` already applies to its own
  "no floor value" limit.
- **The comparison mode that would govern the real run, stated for context only, not as a result of
  this document's own (non-existent) run.** Once the run occurs, RIG.md `## §AA.4`'s
  mode-determination rule would read LightRAG and HippoRAG as `architecture-comparison mode` — two
  independently-registered wirings sharing no resolved recipe input, exactly the structural
  relationship `## §AA.4`'s own worked `VT-1`/`GR-1` pair states as the norm — meaning "parity, not
  gain" would not apply and a retrieval difference between the arms would not be a quality finding.
  This is stated here as the applicable framework for a future reader, not as an observation drawn
  from any run this document records.
- **MODAL-05 stays Pending in `.planning/REQUIREMENTS.md`.** This document is not the "MODAL-05
  complete" record; it is the record of why MODAL-05 is not yet complete, and of the entry
  criterion that would make it completable.
- **This project's core-value proof point is unproven.** `.planning/PROJECT.md`'s own Core Value
  statement — "the same corpus, the same seam, N modalities running side-by-side and comparable on
  the rig" — is what MODAL-05's real-corpus run exists to demonstrate observed rather than asserted.
  That demonstration has not happened yet.

## Entry criterion for the deferred run

The real cross-modality run is **deferred to a later plan**. Its entry criterion is the single
precondition named above: **owner authorization of one real invocation** of
`databasise.parity.build_hipporag_index` against the 20-document Phase 3 parity corpus, using live
`v1/.env.parity` credentials (`qwen/qwen3.7-flash` extraction, `qwen/qwen3-embedding-8b`
embedding), followed by one real invocation of `databasise.parity.run_cross_modality` against the
resulting built index. Both harnesses are already written and ready to run once that authorization
is given — no further code is needed to unblock this run, only the spend decision itself.

## Next Phase Readiness

- **The real cross-modality run is deferred**, not abandoned. Its entry criterion — owner
  authorization of the real invocation named above — is the only precondition unmet.
- **MODAL-05, this phase's core-value requirement, remains unproven** until that run happens.
  `.planning/ROADMAP.md`'s Phase 6 success criteria name this run as the milestone's own proof
  point; this document is the honest record that the proof has not yet been produced, not a
  substitute for it.
- **The harnesses are ready.** `build_hipporag_index.py` and `run_cross_modality.py` need no
  further code changes to accept a real, spend-authorized run's data — the next plan to run them
  need only supply the authorization this plan did not.
- **Falsifier 5/MACH-03 (06-06-PLAN.md) carries the same shape of deferral** for an unrelated
  reason (an unresolved judge identity and an unbudgetable eval-corpus ingest, not a HippoRAG index
  build) — both documents exist so a reader of this phase's evidence sees the blocked state
  plainly rather than inferring it from an absent number.

---
*MODAL-05 (Cross-Modality Side-by-Side) — BLOCKED, not discharged*
*Recorded: 2026-09-09*

## Real run attempted — refused — 2026-09-10

**Claim.** The owner authorized the real cross-modality run at Task 1's `gate="blocking-human"`
checkpoint (`approve`, 06-13-PLAN.md). One real invocation of
`databasise.parity.build_hipporag_index` ran against the 20-document Phase 3 parity corpus using
live `v1/.env.parity` credentials. It did not complete: the harness's own post-run verification
refused to report success.

**Method.** `cd databasise && uv run python -m databasise.parity.build_hipporag_index` was invoked
directly, exactly as this document's own "Entry criterion for the deferred run" section names. No
flag was weakened, no guard was bypassed, and the invocation was not retried after its refusal,
per this plan's own prohibition against re-running with a weakened guard.

**Findings.** The harness exited non-zero (exit code 1). Its own refusal message, verbatim:

> the index build reported partial=True degraded=True stop_reason='node \'fact-score\':
> NodeExecutionError: Error code: 400 - {\'error\': {\'message\': \'[\n  {\n    "origin": "string",\n
> "code": "too_small",\n    "minimum": 1,\n    "inclusive": true,\n    "path": [\n      "input",\n
> 0\n    ],\n    "message": "Too small: expected string to have >=1 characters"\n  }\n]\', \'code\':
> 400}, \'user_id\': \'user_3IHRlVFnqS7CEPs4DFLIvo1JB4i\'}' degradation_reason=(same) — refusing to
> report success on a run that did not complete cleanly

The failing node is `fact-score`: the scoring provider rejected an input carrying an empty
(zero-length) string somewhere in its batch — a `400` validation error, not an authentication or
quota failure. `build_index()` raised `HippoRAGIndexBuildRefusedError` before constructing an
`IndexBuildResult`, so no graph node/edge count, no chunk/entity/fact vector count, and no
token-spend breakdown was ever returned by the harness's own accounting — there is nothing
verified to report for any of those fields. A real, non-zero spend against live `v1/.env.parity`
credentials did occur before the refusal (multiple upstream nodes — including chunk, entity, and
fact embedding — ran to completion ahead of `fact-score`), but its exact size is not known to this
document: the harness's own token accounting was never assembled because the run was never
allowed to complete, and estimating a figure here would be exactly the kind of
fabricated-plausible-value substitution this document's own Limits section already forbids.

Because the index build did not certify as complete, `databasise.parity.run_cross_modality` was
not invoked — its own `preflight()` step requires a verified HippoRAG index, which this run did
not produce, and this plan's own instruction is to stop the branch on a harness refusal rather
than proceed past it.

**Verdict.** MODAL-05 is **still not discharged**. This was a genuine, spend-incurring attempt at
the real invocation — not a second deferral and not a decline — but the harness itself refused to
certify the result, so no comparison ran and no side-by-side output exists. The blocker has
changed shape: it is no longer "unauthorized," it is now a concrete code defect in the
`fact-score` node's handling of an empty-string input, surfaced for the first time by this real
run against the real 20-document corpus (fixture-driven tests never exercised this input shape).

**Limits.** No graph node/edge count, no vector count, no duration, no per-query comparison
result, and no token-spend figure is reported anywhere in this section — none of those exist as
harness-verified values for this attempt. The owner's `approve` decision is recorded honestly as
*attempted and refused*, not rounded up to success. `.planning/REQUIREMENTS.md`'s MODAL-05 row
stays Pending; its outstanding item is updated to name the `fact-score` empty-string defect as the
concrete next blocker, superseding (not replacing) the prior "authorization" blocker, which is now
resolved.

---
*Real run attempted, refused before verification — 2026-09-10*
