---
defect_row: DR-04
requirement: HARD-03
decided: 2026-09-08
selected_option: two-covering-rationale
selection_is_clean: false
---

# DR-04 Decision

**Defect register row:** `docs/system-model/ANATOMY.md ## §F` DR-04, restated at
`docs/system-model/PARTS.md`'s `## Appendix A` DR-04 disposition: *"Does the machine's own chunk
artifact carry a checkable per-chunk provenance stamp (chunker/embedder identity), or only a
per-run sub-recipe stamp at the artifact-registry level (§7's SA-2)?"* The row's own two named
options, quoted from `SYSTEM-MODEL.md ## §H1`: a checkable per-chunk stamp on the artifact itself
(`per-chunk-provenance-stamp`), or the two existing coverings alone
(`two-covering-rationale`) — `CONTRACT.md §7`'s per-run SA-2 sub-recipe stamp at the
artifact-registry level, together with `ANATOMY.md ## §C`'s per-ref `ChunkRef(corpus_id,
recipe@version, ordinal, content_hash)`. `CONTRACT.md §4`'s D9 repair narrows but does not close
this row: D9 defines `ScoredItem.provenance`, the evidence record a socket boundary carries during
a run — a chunk sitting in the store is not one.

## Step 1 — Both Coverings Checked Against Live Code

### Covering 1 — the per-run SA-2 sub-recipe stamp (`CONTRACT.md §7`)

`databasise/registry_artifact/index.py`'s `ArtifactRecord`/`ArtifactRegistry.register()` carry
three real columns: `sa2_chunker`, `sa2_extraction`, `sa2_embedding` (the `artifacts` table's own
`CREATE TABLE` DDL, lines 184-186). `register()` declares all three as required, non-defaulted
keyword parameters — every registration writes a value into all three columns; there is no code
path that registers an artifact with an empty or null SA-2 stamp. **This half of covering 1
holds, as built, today.**

`§7`'s partial-coverage registration refusal (the D8 repair — "a sub-recipe stamp MUST NOT be
registered over a corpus to which that sub-recipe was not applied in full") is a separate clause
from the stamp-recording clause above. A repository-wide search for a partial-coverage check
(`grep -rn "partial.coverage\|PartialCoverage\|partial_coverage" databasise/`) returns **no
matches** anywhere under `databasise/registry_artifact/`, `databasise/seam/`, or
`databasise/tests/`. `register()`'s own docstring states what it actually refuses today — an
unauthorized caller and a transient-store-write `effect` — and names nothing about partial corpus
coverage. **This half of covering 1 is declared in `CONTRACT.md` but not implemented anywhere in
this codebase.**

### Covering 2 — the per-ref `ChunkRef(corpus_id, recipe@version, ordinal, content_hash)` (`ANATOMY.md ## §C`)

`databasise/seam/evidence.py`'s `EvidenceRef` (the seam's real, shipped reference type) carries
exactly five fields: `ref`, `namespace`, `kind`, `score`, `tier`. None of `ANATOMY.md ## §C`'s four
named `ChunkRef` members — `corpus_id`, `recipe@version`, `ordinal`, `content_hash` — is present.
Phase 4 already recorded this gap as FA-03: *"`EvidenceRef` carries only ref/namespace/kind/score/tier,
not the full §4 `ChunkRef` shape — `corpus_id`, `recipe@version`, `ordinal`, and `content_hash` are
not available at the retrieval position today (FA-03)."* This decision states what the code
carries, per FA-03's own prior finding, rather than restating `ANATOMY.md`'s model text as if it
described the code's actual behaviour. **Covering 2 does not hold as built.**

## Step 2 — Selection

**`selected_option: two-covering-rationale`.** The starting position from `05-RESEARCH.md`'s own
recommendation (OPEN DECISION 2 / Assumption A3) is that the existing SA-2 registration stamp plus
§7's partial-coverage refusal together answer the provenance question a per-chunk field would
answer, without a schema change inside the opaque ingest core's own internals — a change
`CONTRACT.md`'s own framing treats as a capability not yet earned (`## §8`'s "Framing" clause),
i.e. a cost to defer, not a gap to patch around. Step 1 above does not overturn that starting
position — no evidence surfaced this session argues *for* `per-chunk-provenance-stamp` instead —
but it does not let the selection be recorded as a clean yes either, because one of the two named
legs of `two-covering-rationale` is only half-built and the other has yet to be threaded through to
the seam's own evidence shape.

**`selection_is_clean: false`**, per the plan's own instruction: a selection recorded as clean
when one of its two legs is missing is exactly the rounding-up this phase's own admission
discipline forbids.

## What Falls Short

Neither covering is a clean yes as built, and the two fall short in different shapes:

- **Covering 1 (SA-2 stamp) is short by its enforcement half, not its recording half.** The stamp
  itself (`sa2_chunker`/`sa2_extraction`/`sa2_embedding`) is written on every registration —
  `register()` cannot be called without supplying all three. What is missing is `§7`'s
  partial-coverage refusal (D8): no code anywhere in this repository detects that a sub-recipe was
  applied to only part of a corpus and refuses registering a stamp over the whole corpus id on that
  basis. Closing this would require adding a coverage check to `ArtifactRegistry.register()` (or a
  pre-registration gate that calls it) — comparing the set of documents a sub-recipe actually ran
  against the full corpus membership before the stamp is written, and raising a named refusal
  (mirroring `UnauthorizedRegisterCallError`'s and `TransientWriteNotRegistrableError`'s existing
  shape) when they diverge.
- **Covering 2 (`EvidenceRef`) is short by all four `ChunkRef` members.** `corpus_id`,
  `recipe@version`, `ordinal`, and `content_hash` are all absent from the real, shipped type.
  Closing this — per FA-03's own framing — would require threading those four values from the
  ingest/chunk-store position through to wherever `resolve_evidence_ref` constructs an
  `EvidenceRef`, which FA-03 already records as unavailable at the retrieval position today; this
  is a data-flow change to the retrieval path, not a schema-only addition.

**No requirement in the current milestone's `REQUIREMENTS.md` names closing either gap**, and this
record does not assign one. Per `SYSTEM-MODEL.md ## §H1`'s own handoff ledger, DR-04 is owned by
"the build," first faced at the rung whose deliverables name a machine-owned chunk artifact at
all — which this phase now is. This decision is the input a future requirement would consume if
either gap is raised for closure; it does not itself open one.

## Step 3 — Consequence for This Phase

Under `two-covering-rationale`, **the opaque ingest core's own chunk artifact gains no new field**.
Plan 05-01's `lightrag/full-ingest@0.1.0` Part already registers its output through
`databasise/registry_artifact/index.py`'s existing `sa2_chunker`/`sa2_extraction`/`sa2_embedding`
columns at `artifact_scope="quarantined"`, exactly as the two-covering rationale requires — no
change to that registration shape follows from this decision. **No code change follows from this
decision under the selected option; this record itself is the deliverable.**

## Step 4 — Scope Fence

`docs/system-model/ANATOMY.md`'s and `docs/system-model/PARTS.md`'s own DR-04 rows are **not**
edited by this plan — that tree is a verbatim copy of the shipped system model. Reconciling
`ANATOMY.md ## §F`'s DR-04 row (and its restatement at `PARTS.md ## Appendix A`) with this
codebase's own state is Phase 7's HARD-02, scheduled and out of this plan's scope; this record is
the input that pass will consume when it runs.
