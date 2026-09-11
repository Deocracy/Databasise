---
phase: 06-hipporag-2-side-by-side
verified: 2026-09-10T20:00:00Z
status: gaps_found
score: 4/6 must-haves verified
covered_files:
  - ".planning/REQUIREMENTS.md"
  - ".planning/ROADMAP.md"
  - ".planning/WINDOWS.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-01-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-01-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-02-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-02-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-03-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-03-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-04-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-04-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-05-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-05-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-06-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-06-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-07-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-07-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-08-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-08-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-09-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-09-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-10-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-10-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-11-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-11-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-12-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-12-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-13-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-13-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-REVIEW-FIX.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-REVIEW.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-UAT.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-VALIDATION.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-VERIFICATION.md"
  - ".planning/phases/06-hipporag-2-side-by-side/COVERAGE.md"
  - "databasise/eval/corpus_ingest.py"
  - "databasise/eval/remint.py"
  - "databasise/evidence/CROSS-MODALITY-EVIDENCE.md"
  - "databasise/evidence/FALSIFIER-5-EVIDENCE.md"
  - "databasise/mcp/server.py"
  - "databasise/mcp/tools.py"
  - "databasise/parts_core/hipporag/chunk_embed.py"
  - "databasise/seam/engine.py"
  - "databasise/seam/refusals.py"
  - "databasise/seam/rest.py"
  - "databasise/wirings/hipporag/corpus-ingest.json"
  - "databasise/wirings/lightrag/corpus-ingest.json"
  - "databasise/wirings/resolve.py"
covered_digest: "v1:sha256:502da9da38e78ba113e9d0a312c0234f5795e0ef2553b9c4c543b5adea6a726e"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 3/6
  gaps_closed:
    - "Human-verification item 1 (MACH-10's permanent-exclusion disposition) — owner confirmed in 06-UAT.md Test 1 (result: pass); REQUIREMENTS.md flipped MACH-10 to Complete (06-11)"
    - "The structural half of SC2/MODAL-05 (06-REVIEW.md CR-01, original round) — Databasise.ingest()/delete_document() were hardcoded to LightRAG-only wiring files with no HippoRAG write path at all. 06-10 gives HippoRAG a real, tested ingest wiring dispatched per resolved modality, with a named refusal (NoWritePathForModalityError) for delete. A text-bearing document ingested through the public seam with a HippoRAG selector now lands in HippoRAG's own namespaces and is retrievable as real evidence — verified by a passing tracer test, not asserted."
  gaps_remaining:
    - "SC2/MODAL-05 — no real cross-modality run against the Phase 3 parity corpus has ever produced a comparable output. The owner authorized one real attempt at 06-13's checkpoint; the harness's own post-run verification refused (fact-score node, provider 400 on an empty-string batch item) before a comparison could run. Real spend was incurred; no result exists."
    - "SC6/MACH-03 (Falsifier 5) — both of Falsifier 5's named preconditions are now closed in code (06-12: a resolved judge-identity resolver, a cost-bounded eval-corpus ingest path), but no real A/A calibration has ever executed. The owner declined the spend a second time at 06-13's checkpoint, citing the same-session fact-score failure as the reason to fix it first."
  regressions:
    - "06-10's new per-modality write dispatch introduced a new, independently-confirmed Critical defect (06-REVIEW.md, this round, unfixed as of commit cc3abf3): a raw-bytes IngestDocument (the /documents/upload path — PDF, DOCX, etc.) against a HippoRAG-resolving selector always stamps text=\"\" for hipporag/chunker-embedder, which silently short-circuits to zero chunks/embeddings/writes and still returns a normal-looking successful IngestJob(enqueued=1). This did not exist before 06-10 because no HippoRAG write path existed at all; it is new-to-this-round, not carried forward, and remains open."
gaps:
  - truth: "LightRAG and HippoRAG 2 run on one corpus under RIG §RUN, isolated stores, outputs structurally comparable (roadmap Success Criterion 2 / MODAL-05)"
    status: failed
    reason: >
      Real progress happened this round, and it should be credited plainly: the structural write-surface
      gap the prior verification round found (Gap 1, CR-01) is closed — Databasise.ingest() now
      dispatches a per-modality corpus wiring via wiring_family()/_corpus_wiring(), HippoRAG ships a
      real corpus-ingest.json wiring re-composed from its own seven index-side node positions, and a
      text-bearing document ingested through the public seam with a HippoRAG selector is independently
      confirmed (by reading engine.py and running tests/seam/test_hipporag_write_path.py) to land in
      HippoRAG's own graph/vector/KV namespaces and come back as real evidence from a subsequent
      HippoRAG query. That is genuine, tested, working machinery, not an assertion. The owner also
      authorized the real, spend-incurring cross-modality run this round — a real attempt was made
      against live credentials, not merely offered. But the roadmap's own SC2 text requires the two
      modalities to actually run on one corpus with comparable outputs, and that has still not
      happened: the harness's own post-run verification (build_hipporag_index's partial/degraded
      check) refused before completion, at the fact-score node, on a provider 400 over an empty-length
      string in its input batch — a genuine, previously-unexercised defect, not a spend-authorization
      problem. run_cross_modality was never reached. No HippoRAG index built from the real parity
      corpus exists anywhere in this repository today, so no comparable output exists either.
      Independently, and more severely for the phase's own core value, this round's own code review
      (06-REVIEW.md, commit cc3abf3) found — and I independently confirmed by reading
      databasise/seam/engine.py:665-685 and databasise/parts_core/hipporag/chunk_embed.py:66-91 — a
      still-unfixed Critical defect in the very write path 06-10 just built: a raw-bytes
      IngestDocument (the actual shape a real-world PDF/DOCX upload takes, via /documents/upload)
      against a HippoRAG-resolving selector always stamps node_config["documents"][0]["text"] = ""
      (the real bytes only reach file_paths/docs_format, which hipporag/chunker-embedder never reads),
      so chunk-embed's own `if not text: return []` guard silently produces zero chunks, zero
      embeddings, zero writes for that document — and ingest() still returns a normal-looking
      IngestJob(enqueued=1), because HippoRAG's provides node reports no `enqueued` field and the
      no-fabricated-zero fallback substitutes a literal 1. A caller who uploads a real document to
      HippoRAG through the seam cannot tell, from the response, that nothing was written. This is
      untested in every direction — no test in this phase's own new suite combines raw= with a
      HippoRAG-resolving selector. Both failures are honestly recorded where they belong
      (CROSS-MODALITY-EVIDENCE.md's new "Real run attempted — refused" section; 06-REVIEW.md), and
      REQUIREMENTS.md correctly keeps MODAL-05 Pending rather than rounding either up. But the
      roadmap truth itself — two modalities actually running on one corpus with comparable output —
      remains unmet, for two independent reasons, one of which (the raw-upload data loss) is a new
      defect this round's own fix introduced into the write surface it built.
    artifacts:
      - path: "databasise/parts_core/hipporag/fact_score.py"
        issue: "The fact-score node's provider call raises a 400 on an empty-string batch item rather than skipping/guarding it — the concrete blocker that stopped the one real, authorized cross-modality attempt this round. Filed as .planning/WINDOWS.md entry id 3, status open."
      - path: "databasise/seam/engine.py"
        issue: "Lines ~665-685 (the document.raw branch of ingest()): always stamps text=\"\" regardless of which modality the resolved corpus wiring targets, silently discarding raw-bytes content for any target whose node body does not itself parse file_paths/docs_format (HippoRAG's chunk-embed does not). No refusal, no partial/degraded signal — ingest() returns IngestJob, which has no such field to carry one."
      - path: "databasise/parts_core/hipporag/chunk_embed.py"
        issue: "Reads only document['text']/document['document_id']; has no awareness of file_paths/docs_format at all, so a raw upload against a HippoRAG selector always short-circuits through the empty-chunks early return with no error."
    missing:
      - "A fix for fact-score.py's handling of an empty-length string in its input batch (skip/guard rather than forwarding to the provider), so a real index build against a real corpus can complete and be verified rather than refused"
      - "Either real file-parsing awareness in hipporag/chunker-embedder for raw uploads, or a named refusal (e.g. NoRawUploadPathForModalityError, raised in ingest() before any node config is stamped) when a raw-bytes document is targeted at a modality whose corpus-ingest wiring's node cannot consume file_paths/docs_format — per 06-REVIEW.md's own stated fix options"
      - "Owner re-authorization of the real cross-modality run once fact-score is fixed, followed by a real invocation of run_cross_modality producing an actual per-query comparison result"
  - truth: "Owner mints an eval bundle (MACH-02) then runs one A/A calibration reading a p95 floor at both target families with T1 materially narrower than T0 (MACH-03, Falsifier 5) — roadmap Success Criterion 6"
    status: failed
    reason: >
      MACH-02 remains fully satisfied and unchanged (bundle@v1, committed, both §EV.2 families
      present). MACH-03's own two named preconditions — a resolved, non-sentinel judge_instance, and
      a cost-bounded ingest path for the 291-document eval-corpus — are both now closed in code by
      06-12 (databasise/eval/remint.py, databasise/eval/corpus_ingest.py), independently confirmed by
      reading both modules and running their test suites (10 passing tests between them). This is
      real, spend-free progress: the checkpoint question changed from "unbudgetable" to a bounded
      "N documents, ~X input tokens, proceed?" But no real A/A run has ever executed at any point in
      this phase. The owner declined the spend a second time at 06-13's checkpoint, and the stated
      reason is itself evidence the deferral is sound engineering judgment, not neglect: Task 1's real
      HippoRAG run had just died on the fact-score empty-string defect in the same session, and the
      same defect class could waste the far larger T0-leg spend, so fixing fact-score first is the
      cheaper path. FALSIFIER-5-EVIDENCE.md's new "Deferred again" section records this honestly, with
      no floor value, no fabricated number, for either tier — matching this project's own discipline.
      Regardless of how well-reasoned the deferral is, the roadmap's own SC6 text requires a real A/A
      run producing two real p95 floors with T1 materially narrower than T0, and that has not
      happened. This is not an oversight to correct — REQUIREMENTS.md correctly keeps MACH-03 Pending
      — but the truth itself remains unmet.
    artifacts:
      - path: "databasise/evidence/FALSIFIER-5-EVIDENCE.md"
        issue: "States plainly, in its new 2026-09-10 section, that the spend was declined a second time and no floor exists for either tier. Honest, not a gap in the record — the gap is that the run has not happened."
      - path: "databasise/parts_core/hipporag/fact_score.py"
        issue: "Same defect blocking SC2 above; the owner explicitly sequenced fixing it ahead of authorizing the MACH-03 spend."
    missing:
      - "The same fact-score.py fix named under SC2's gap"
      - "Owner authorization of the real A/A calibration run, now against a cost-bounded ingest path and a resolvable judge identity"
      - "One real A/A run producing paired per-question differences and a bootstrap p95 floor at each of the two §EV.2 target families, with T1's null width materially narrower than T0's"
---

# Phase 6: HippoRAG 2 & Side-by-Side Verification Report

**Phase Goal:** Two modalities answer the same corpus behind the same seam and the caller sees both at once — the milestone's proof of swappability (§BP rung 4)
**Verified:** 2026-09-10
**Status:** gaps_found
**Re-verification:** Yes — after gap closure (plans 06-10 through 06-13)

## What changed since the prior verification round

The prior round (3/6, `gaps_found`) found two FAILED roadmap truths (SC2/MODAL-05, SC6/MACH-03) and
one human-verification item (SC5/MACH-10). Four gap-closure plans executed:

- **06-10** gave HippoRAG a real, tested write path through the public §18 seam for text-bearing
  documents, closing the structural half of Gap 1 (06-REVIEW.md's original CR-01).
- **06-11** flipped MACH-10 to Complete on the owner's recorded confirmation (06-UAT.md Test 1).
- **06-12** closed both of Falsifier 5's named preconditions spend-free (a judge-identity resolver, a
  cost-bounded eval-corpus ingest path).
- **06-13** put both remaining spend decisions to the owner for real: MODAL-05's cross-modality run
  was **approved** and genuinely attempted against live credentials — and refused by the harness's
  own post-run verification on a fact-score empty-string defect, before producing a comparison.
  MACH-03's A/A calibration was **declined** a second time, with the owner's stated reason directly
  tied to that same-session failure.

Net effect: one truth (SC5/MACH-10) moved from human-verification-needed to VERIFIED. The other two
FAILED truths (SC2, SC6) are **not** resolved — they remain FAILED, for reasons that changed shape
(from "unauthorized" to "attempted and refused on a concrete defect" / "preconditions closed, spend
declined") but did not go away. A new, independently-confirmed Critical defect was also found this
round in the write path 06-10 built (raw-bytes uploads silently lose content for HippoRAG), which I
verified is still unfixed as of the latest commit.

## Goal Achievement

### Observable Truths (roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | HippoRAG 2 runs as thirteen fitted node positions, no opaque core left, whole-graph PPR via §14.2 bulk-export into native igraph/prpack, index-side depth stays `opaque` until parity shown | ✓ VERIFIED | Unchanged this round (no files in scope touched `base.json`'s node inventory beyond WR-01's effects correction, already verified). `databasise/wirings/hipporag/base.json` still declares 13 nodes; `ppr.py` still calls `export_to_igraph()` → native `personalized_pagerank(implementation="prpack")`. Regression-checked: full suite includes `test_thirteen_positions.py`/`test_graph_bulk_export.py`, part of the reported 936 passed / 3 skipped. |
| 2 | LightRAG and HippoRAG 2 run on one corpus, isolated stores, outputs structurally comparable | ✗ FAILED | Structural write path now real and tested (06-10). One real, authorized attempt was made and refused before completion by the harness's own verification (`fact-score` node, provider 400 on empty-string input) — `CROSS-MODALITY-EVIDENCE.md`'s new section. No comparable output exists. Independently, a new unfixed Critical defect (06-REVIEW.md) means raw-byte uploads to HippoRAG silently lose all content. See Gap 1. |
| 3 | Caller sends one query against two or more modalities, receives per-arm results keyed by caller-supplied selectors, no verdict, single arm degenerates to a run | ✓ VERIFIED | Unchanged this round — `Databasise.compare`, `POST /compare`, MCP `compare` tool untouched by 06-10..06-13's `files_modified`. Regression-checked via full suite (936 passed / 3 skipped includes `test_compare.py`, `test_rest_transport.py`, `test_dual_transport_parity.py`). |
| 4 | The first genuine seam call records F-14's outcome either way | ✓ VERIFIED | Unchanged this round — `F-14-SEAM-INVARIANCE.md` untouched by any of the four gap-closure plans' `files_modified` lists. |
| 5 | Mutable-store components have a defined snapshot/reset protocol or are recorded as permanently excluded — F-07 discharged | ✓ VERIFIED | **Moved from human-verification-needed to VERIFIED this round.** 06-11 flipped MACH-10 to Complete in `.planning/REQUIREMENTS.md` citing 06-UAT.md Test 1 (`result: pass`, owner confirmed 2026-09-10) and `F-07-MUTABLE-STORE-DISPOSITION.md`. Independently confirmed: `.planning/REQUIREMENTS.md` line 24 reads `- [x] **MACH-10**` with the `Confirmed 2026-09-10` annotation appended after (not replacing) the original 06-09 annotation; coverage table row reads `| MACH-10 | Phase 6 | Complete |`. Enforcement tests (`test_mutable_store_exclusion.py`, `test_f07_record.py`) re-run clean (16/16 pass). |
| 6 | Owner mints an eval bundle (MACH-02) then runs one A/A calibration reading a p95 floor at both target families with T1 materially narrower than T0 (MACH-03, Falsifier 5) | ✗ FAILED | MACH-02 unchanged, still satisfied. MACH-03: both named preconditions closed in code by 06-12 (`remint.py`, `corpus_ingest.py`, independently confirmed by reading both modules and running their tests — 10/10 pass). No real A/A run has ever executed; owner declined the spend a second time at 06-13's checkpoint, citing the same-session `fact-score` failure. `FALSIFIER-5-EVIDENCE.md`'s new "Deferred again" section records this honestly, no floor value for either tier. See Gap 2. |

**Score:** 4/6 truths verified (0 present-but-behavior-unverified) — up from 3/6 last round.

### CR-01 (this round) Assessment — raw-bytes ingest silently loses content for HippoRAG

I independently confirmed 06-REVIEW.md's new Critical finding by reading the cited code directly:

- `databasise/seam/engine.py` lines 665-685 (`document.raw is not None` branch of `ingest()`): for a
  raw-bytes payload it unconditionally stamps `node_config["documents"] = [{"id": document_id,
  "document_id": document_id, "text": ""}]`, with the real content only reachable via `file_paths`/
  `docs_format`. This is correct for LightRAG's opaque `full-ingest` node (a v1 subprocess that
  parses `pending_parse`-tagged files) and silently wrong for HippoRAG's `chunk-embed`.
- `databasise/parts_core/hipporag/chunk_embed.py` lines 66-91 (`_chunk_embed_body`): reads only
  `document["text"]`/`document["document_id"]`; has no knowledge of `file_paths`/`docs_format` at
  all. For a raw-upload document, `text` is always `""`, `_split_into_chunks("", ...)` returns `[]`
  by its own explicit guard, and the node returns `{"chunks": []}` — no embedding call, no write.
- Every downstream HippoRAG node degrades gracefully on an empty list (`openie.py`'s own
  `if not chunks: return {"findings": []}`), so the entire seven-node chain "succeeds" having
  written nothing for that document, and `ingest()`'s own no-fabricated-zero fallback (`enqueued =
  result.get("enqueued"); if enqueued is None: enqueued = 1`) returns a normal `IngestJob(enqueued=1)`
  — indistinguishable from a real success.
- `git log --oneline -15` confirms `cc3abf3` (the review itself) is the current HEAD for this scope;
  there is no subsequent fix commit. `06-REVIEW-FIX.md` on disk is dated `03:48:32Z`, hours before
  `06-REVIEW.md`'s `18:30:00Z` review that found this defect — it fixes the *prior* round's CR-01/
  WR-01/WR-02, not this one. **This defect is confirmed still open.**

**Conclusion:** This does not contradict 06-10's own must-have truths, which were tested and
verified using `text=`-only `IngestDocument`s — those pass genuinely. But it means the write path
06-10 built is unsafe for the realistic caller shape (a PDF/DOCX upload via `/documents/upload`)
against a HippoRAG selector, with silent data loss and no error signal anywhere in the response.
This is scored as part of Gap 1 (SC2) below, since it bears directly on whether "the caller sees
both at once" can be trusted for real documents, not merely fixture text.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `databasise/wirings/hipporag/corpus-ingest.json` | HippoRAG's real write-path wiring | ✓ VERIFIED | Parses as JSON; `nodes` has exactly the 7 expected keys; `provides`/`consumes_documents`/`store_namespaces` match `base.json`'s — confirmed by direct read |
| `databasise/seam/engine.py` (`_corpus_wiring`) | Per-modality write dispatch, filesystem as lookup table | ✓ VERIFIED | Confirmed by direct read: `_corpus_wiring()` builds `_WIRINGS_ROOT / family / f"corpus-{operation}.json"`, raises `NoWritePathForModalityError` when absent |
| `databasise/seam/refusals.py` (`NoWritePathForModalityError`) | Named refusal, no modality/wiring/node leak | ✓ VERIFIED | Class present; `test_hipporag_write_path.py`'s Test 4 (message-content assertion) passes |
| `databasise/eval/corpus_ingest.py` | Dry-run-default, cost-bounded eval-corpus ingest | ✓ VERIFIED | `estimate()`, `ingest_documents()`, `LimitExceedsCorpusError`, `main()` all present; `test_corpus_ingest.py` passes (5/5) |
| `databasise/eval/remint.py` | Real-response-only judge-identity resolver, next-version mint | ✓ VERIFIED | `resolve_judge_identity()`, `remint()`, `UnresolvedJudgeIdentityError` all present; `test_remint.py` passes (5/5) |
| `.planning/REQUIREMENTS.md` (MACH-10 row) | Flipped Complete with dated, cited annotation | ✓ VERIFIED | `- [x] **MACH-10**` with `Confirmed 2026-09-10` annotation appended after the original; coverage table row `Complete` |
| `databasise/evidence/CROSS-MODALITY-EVIDENCE.md` | Append-only; 2026-09-09 content intact, new dated section for the real attempt | ✓ VERIFIED | 2026-09-09 header/content byte-identical to prior round's cited text; new `## Real run attempted — refused — 2026-09-10` section below it, no fabricated counts |
| `databasise/evidence/FALSIFIER-5-EVIDENCE.md` | Append-only; 2026-09-09 content intact, new dated deferral section | ✓ VERIFIED | 2026-09-09 content intact; new `## Deferred again — 2026-09-10` section, no fabricated floor value |
| `.planning/WINDOWS.md` | `fact-score` defect filed as discoverable future work | ✓ VERIFIED | Entry id 3, `kind: deviation`, `status: open`, dated 2026-09-10T17:44:08.972Z |
| `.planning/phases/06-hipporag-2-side-by-side/COVERAGE.md` | Corrected write-surface record | ✓ VERIFIED | Names `hipporag/corpus-ingest.json`, `NoWritePathForModalityError`, LightRAG-only `corpus`/`corpus/counts`/`jobs`; the stale "reachable identically" phrase is gone |
| `databasise/parts_core/hipporag/fact_score.py` (implied working state) | Handle empty-string batch items without a provider 400 | ✗ NOT FIXED | Confirmed open — this is the concrete blocker for both remaining gaps |
| `databasise/seam/engine.py` (raw-bytes → HippoRAG safety) | Either real parsing or a named refusal for raw uploads against HippoRAG | ✗ MISSING | Confirmed open — 06-REVIEW.md's new Critical finding, unfixed as of `cc3abf3` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `Databasise.ingest(document, selector=<HippoRAG>)` (text payload) | HippoRAG's own graph/vector/KV namespaces | `_corpus_wiring` → `hipporag/corpus-ingest.json` → 7 nodes → `_build_stores(..., resolved)` | ✓ WIRED | Confirmed by reading `engine.py` and running `test_hipporag_write_path.py`'s tracer test (passes) |
| `Databasise.ingest(document, selector=<HippoRAG>)` (raw-bytes payload) | HippoRAG's own graph/vector/KV namespaces | same path, but `text` stamped `""` | ✗ NOT_WIRED (silent) | Confirmed by reading `chunk_embed.py`'s `if not text: return []` guard — no vertex/vector/KV write occurs, no error surfaces; 06-REVIEW.md's new Critical finding |
| `Databasise.delete_document(id, selector=<HippoRAG>)` | (no HippoRAG delete node exists) | `NoWritePathForModalityError` | ✓ WIRED (refuses by name) | Confirmed by reading `engine.py`/`refusals.py`; `test_hipporag_write_path.py` Test 4 passes |
| `databasise.parity.build_hipporag_index` (real invocation) | `databasise.parity.run_cross_modality` | index-build success gate | ✗ NOT REACHED | `build_hipporag_index` refused (`fact-score` 400) before certifying; `run_cross_modality` was never invoked, per `CROSS-MODALITY-EVIDENCE.md`'s own record |
| `databasise/eval/corpus_ingest.py --spend` | `Databasise.ingest()` | per-document seam call, bounded by `--limit` | ✓ WIRED (spend-free path proven; live path never invoked for real) | `ingest_documents()` confirmed to call `engine.ingest(...)` once per document; `test_corpus_ingest.py`'s call-counting tests pass |
| `databasise/eval/remint.py` | `databasise.eval.bundle.mint_bundle` | `resolve_judge_identity()` → `remint()` | ✓ WIRED (spend-free path proven; live path never invoked for real) | `remint()` confirmed as a thin call-through; `test_remint.py`'s byte-pinning test passes |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `chunk_embed.py` (`text=`-payload ingest) | `text` | caller-supplied `IngestDocument.text`, stamped verbatim into `node_config["documents"][0]["text"]` | Yes | ✓ FLOWING |
| `chunk_embed.py` (`raw=`-payload ingest, HippoRAG-resolving selector) | `text` | `engine.py` always stamps `""` for the raw path regardless of target modality | No | ✗ HOLLOW_PROP — caller-supplied bytes never reach the field the node reads; a real, non-empty payload is hardcoded to empty at the seam boundary |
| `build_hipporag_index.IndexBuildResult` (real corpus) | node/edge/vector counts, token spend | never constructed — harness raised `HippoRAGIndexBuildRefusedError` before assembly | N/A | ✗ DISCONNECTED — no comparable output exists for the real corpus at all |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| HippoRAG write-path tracer, no-selector default parity, isolation, delete refusal, write-path invariant, transport parity | `pytest tests/seam/test_hipporag_write_path.py` | 33 passed total across this and the checks below (see combined run) | ✓ PASS |
| Cost-bounded eval-corpus ingest (tracer, spend-nothing default, bound enforcement, over-large-limit refusal, per-arm labelling) | `pytest tests/eval/test_corpus_ingest.py` | included in combined run | ✓ PASS |
| Judge-identity resolution and bundle re-mint (present/absent identity, byte-pinning, idempotent re-mint, no-credentials refusal) | `pytest tests/eval/test_remint.py` | included in combined run | ✓ PASS |
| Mutable-store exclusion and F-07 disposition record (now claimed Complete in REQUIREMENTS.md) | `pytest tests/seam/test_mutable_store_exclusion.py tests/evidence/test_f07_record.py` | included in combined run | ✓ PASS |
| Combined: `pytest tests/seam/test_hipporag_write_path.py tests/eval/test_corpus_ingest.py tests/eval/test_remint.py tests/seam/test_mutable_store_exclusion.py tests/evidence/test_f07_record.py` | (run directly by this verifier) | 33 passed in 3.76s | ✓ PASS |
| Full workspace suite (reported by orchestrator, not re-run in full here per the no-redundant-full-run rule) | `uv run --extra rest --extra mcp pytest -q` | 936 passed, 3 skipped (per test_state); regression gate over 87 prior-phase files: 750 passed, 1 skipped, no cross-phase regressions | ✓ PASS (as reported) |
| HippoRAG wiring JSON structural check | `python -c "json.loads(...)"` over `wirings/hipporag/corpus-ingest.json` | 7 nodes, `provides`/`consumes_documents` correct | ✓ PASS |

### Probe Execution

Not applicable — this phase has no `scripts/*/tests/probe-*.sh` harness; verification relied on the
project's own pytest suite and direct code reading, per the phase's own conventions.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| MODAL-04 | 06-01, 06-02, 06-05, 06-07 | HippoRAG 2 fully decomposed, 13 positions, no opaque core | ✓ SATISFIED | Complete in REQUIREMENTS.md; unchanged this round, regression-checked |
| MODAL-05 | 06-01, 06-03, 06-08, 06-10, 06-13 | Both modalities run side-by-side on one corpus, comparable | ✗ BLOCKED | Pending in REQUIREMENTS.md, correctly. Structural write path closed (06-10); one real attempt was authorized and refused (fact-score defect, 06-13); a new unfixed Critical raw-upload defect also found this round |
| API-08 | 06-03 | One query against 2+ modalities, per-arm keyed results, inspection-only | ✓ SATISFIED | Complete in REQUIREMENTS.md; unchanged this round, regression-checked |
| MACH-10 | 06-09, 06-11 | F-07 discharged: mutable-store snapshot/reset or permanent exclusion | ✓ SATISFIED | **Newly Complete this round.** Owner confirmation recorded in 06-UAT.md Test 1; REQUIREMENTS.md flipped by 06-11; independently confirmed |
| MACH-02 | 06-04 | Eval bundle minted with dev/holdout/sealed, both §EV.2 families | ✓ SATISFIED | Complete in REQUIREMENTS.md; unchanged this round |
| MACH-03 | 06-06, 06-12, 06-13 | First A/A calibration, p95 floor at both tiers, Falsifier 5 | ✗ BLOCKED | Pending in REQUIREMENTS.md, correctly. Both preconditions closed in code (06-12); spend declined a second time (06-13), citing the fact-score failure |

No orphaned requirements: all six IDs declared across Phase 6 plans (`06-01` through `06-13`) match
exactly the six requirement rows REQUIREMENTS.md maps to "Phase 6."

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `databasise/seam/engine.py` / `databasise/parts_core/hipporag/chunk_embed.py` | engine.py:665-685; chunk_embed.py:66-91 | Raw-bytes `IngestDocument` against a HippoRAG-resolving selector silently loses all content — `text` stamped `""`, no refusal, `IngestJob(enqueued=1)` returned as if successful | 🛑 Blocker | This round's own code review (06-REVIEW.md) Critical finding, independently confirmed here, still unfixed as of `cc3abf3`. Untested in every direction. Directly undermines "the caller sees both at once" for realistic document uploads to HippoRAG. |
| `databasise/parts_core/hipporag/fact_score.py` | (empty-string batch item) | Provider call raises a 400 on an empty-length string rather than skipping/guarding it | 🛑 Blocker | The concrete blocker that stopped the one real, authorized cross-modality attempt and the reason the owner declined the A/A calibration spend. Filed at `.planning/WINDOWS.md` entry id 3, `status: open` — a real, discoverable ledger entry, not buried in prose. |
| `databasise/seam/rest.py:287` | `DeleteRequest = DeleteRequest()` | Mutable module-level singleton as a route default (fragile if a future edit mutates it) | ⚠️ Warning | Not observed to cause incorrect behavior today (06-REVIEW.md WR-01, this round) |
| `databasise/parts_core/hipporag/graph_augment_persist.py` | 78-82 | Iterates `weight_by_pair` unsorted, inconsistent with sibling edge-builders | ℹ️ Info | Carried forward, unchanged (06-REVIEW.md IN-01) |
| `databasise/stores/vector.py` | 272-315 | `self_knn`'s self-exclusion assumes the self-match is within the `top_k+1` window | ℹ️ Info | Carried forward, unchanged (06-REVIEW.md IN-02) |
| `databasise/seam/engine.py` | 662-663, 772 | `resolved["consumes_documents"][0]`/`resolved["provides"][0]` indexed with no bounds check | ℹ️ Info | Low priority given today's wirings are all well-formed; would surface as a raw exception rather than a named refusal for a future malformed file (06-REVIEW.md IN-03) |

No `TBD`/`FIXME`/`XXX` markers found in any phase-modified file. Debt-marker gate clear.

### Human Verification Required

None. The one item outstanding from the prior round (MACH-10's owner confirmation) is now closed and
independently verified above. No new human-verification items were identified this round — the two
remaining gaps (SC2, SC6) are both resolved to concrete, code-traceable blockers (`fact-score.py`'s
empty-string handling; the raw-upload data-loss defect) rather than open policy questions.

### Gaps Summary

Two of six roadmap Success Criteria remain unmet, and both are honestly recorded as Pending in
REQUIREMENTS.md and in their own evidence documents — this is not an oversight this round, it is the
project's own discipline against rounding a partial or refused result up to Complete, working as
intended. Real progress happened:

1. **SC2 (side-by-side one corpus)** — the structural write-surface gap from the prior round is
   genuinely closed for text-bearing documents (06-10), and the owner genuinely authorized and
   attempted the real spend-incurring run (06-13). But the attempt was refused by the harness's own
   verification on a concrete, previously-unexercised code defect (`fact-score`'s empty-string
   handling), so no comparable output exists. Separately and more concerning for the phase's own
   core value, this round's own code review found — and I independently confirmed as still open — a
   Critical defect where the write path 06-10 just built silently discards all content for a
   raw-bytes document upload against a HippoRAG selector, with no error signal. Both must be fixed
   before SC2 can be honestly claimed met.
2. **SC6 (A/A calibration)** — both of Falsifier 5's named preconditions are closed in code (06-12),
   real spend-free progress. But no real A/A run has ever executed, and the owner's second decline
   (06-13) is directly caused by the same `fact-score` defect blocking SC2 — a rational sequencing
   decision, not neglect.

**The one item that was open for human verification last round (SC5/MACH-10) is now closed and
verified.** The phase's overall trajectory is genuinely forward: 3/6 → 4/6, one structural gap fully
closed, both remaining blockers converged onto a single named, filed, fixable code defect
(`databasise/parts_core/hipporag/fact_score.py`) rather than three separate unresolved items. The
phase is not yet done — the roadmap's own goal ("the caller sees both at once ... the milestone's
proof of swappability") still requires a real comparable output that does not exist, and a write
path that is safe for realistic document uploads, neither of which exists today.

---

## Correction — findings closed after this report was written (2026-09-11)

This report was written against commit `cc3abf3`. Commits landing after it closed several of the
findings recorded above as open; this note records which, and is **not** a re-verification —
`/gsd-verify-work` owns the verdict, and the `status` and `score` above deliberately still read as
the verifier left them.

| Section | Row | Closed by | What now holds |
|---------|-----|-----------|-----------------|
| Required Artifacts | `databasise/seam/engine.py (raw-bytes → HippoRAG safety)`, recorded `✗ MISSING` | `5827165`, `2cb437a` | `Databasise.ingest()` now raises `NoRawUploadPathForModalityError` before any node config is stamped when a raw-bytes document targets a corpus wiring whose consuming node is not `kind: "opaque"`. |
| Key Links | `Databasise.ingest(document, selector=<HippoRAG>)` (raw-bytes payload), recorded `✗ NOT_WIRED (silent)` | `5827165`, `2cb437a` | The path now refuses by name rather than returning a normal-looking `IngestJob` over zero writes. |
| Data-Flow | `chunk_embed.py` (`raw=` payload), recorded `✗ HOLLOW_PROP` | `5827165`, `2cb437a` | Closed by unreachability: the refusal fires before `chunk-embed` is ever dispatched with an empty-text document from a raw upload. |
| Anti-Pattern row 1 | Silent content loss on raw-bytes ingest against a HippoRAG selector, `🛑 Blocker` | `5827165`, `2cb437a` | Closed, with the regression test `06-REVIEW-FIX.md` names: `test_raw_upload_against_a_hipporag_selector_refuses_by_name_rather_than_losing_content`. |
| Anti-Pattern row 3 | `rest.py:287` mutable-singleton `DeleteRequest` default, `⚠️ Warning` | `3de871b` | Closed: set `frozen=True` on `_RequestModel`, the shared base for every request DTO in `rest.py`. |
| Gap 1's first `missing` item | The `fact-score` empty-string fix | `06-14` (`7b5a3df`, `9c4694c`) | Closed at the root: `build_hipporag_index` now dispatches the already-committed seven-position `corpus-ingest` wiring instead of the thirteen-position base wiring (the actual cause — `fact-score` was reached with no query ever injected), and `OpenAICompatibleClient.embed` gained `EmptyEmbeddingInputError` as a second, independent guard. `.planning/WINDOWS.md` entry id 3 is `fixed`. |

**What is not closed by the six rows above, stated against each SUMMARY's real recorded branch:**
gap 1's third `missing` item — owner re-authorization of the real cross-modality run, followed by a
real `run_cross_modality` invocation producing an actual per-query comparison — **is** closed: 06-15
records the owner's real answer as `approve`, and both `build_hipporag_index` and
`run_cross_modality` exited 0 against live `v1/.env.parity` credentials (`graph_node_count=229`,
`graph_edge_count=460`, both queries `partial=False`/`degraded=False`), discharging MODAL-05 to
Complete in `.planning/REQUIREMENTS.md`. With the write-path defect (rows 1-4), the `fact-score`
defect (row 6), and the real run itself (06-15) all closed, gap 1 (SC2) has no outstanding item left
as of this note. Gap 2 (SC6/MACH-03/Falsifier 5) is **not** closed: this plan's own Task 1 records
the owner's real answer as `decline` — a third decline, after 06-06 and 06-13 — so MACH-03 stays
Pending in `.planning/REQUIREMENTS.md` and Falsifier 5 stays open, not failed; no comparison ran.

`06-REVIEW.md`'s IN-01, IN-02 and IN-03 remain open Info-severity items, deliberately untouched by
this round: none of them is implicated in the `fact-score` blast radius. In particular, IN-02
concerns `FaissVectorStore.self_knn`'s top-k window (`databasise/stores/vector.py:272-315`) — the
synonymy-edges path — while the `fact-score` defect ran through `score_all` and the wiring-resolution
choice in `build_hipporag_index.py` — a different method and a different call site. IN-01
(`graph_augment_persist.py`'s unsorted iteration) and IN-03 (`engine.py`'s unbounded-index reads) are
likewise unrelated to either closed defect and remain open exactly as `06-REVIEW.md` recorded them.

---
*Recorded: 2026-09-11*

---

_Verified: 2026-09-10_
_Verifier: Claude (gsd-verifier)_
