# F-14 — Seam Invariance, Recorded From a Real Cross-Modality Call

**Date:** 2026-09-09

F-14, quoted verbatim from `docs/system-model/MODEL-RED-TEAM.md` (`## §A`, "F-14: The
seam-invariance rule's own falsifier has never been run"):

> `§18.3`'s invariance rule states plainly what would refute it: "the first Phase 3
> stress-modality wiring exercise run against this seam finding a case a consumer can only
> interpret correctly by knowing which modality answered — at that point the envelope's closed
> field set is incomplete." `§18.5`'s own falsifier names the identical unrun test from the
> tool-surface side. This is a design-documents project — "code appears only as viability spikes"
> — and no wiring has actually been run against a live seam implementation anywhere in the
> record; `PARTS.md ## §L`/`## §H`/`## §X` each state node sets and declared capabilities on
> paper, never a runtime seam call. The structural argument for invariance is sound and checked
> by construction across seventy-two catalogued systems (`CATALOG.md ## §T`, no roster entry
> needing a modality-named field or tool), but the falsifier both clauses name as the actual test
> has not fired, in either direction, because nothing has run.

`PARTS.md`'s own record never states this falsifier ran — F-14's own finding is that the
Phase-3-named stress-modality wiring exercise "has not fired, in either direction, because
nothing has run." This document is the actual run, against `databasise.seam.Databasise.compare`
(06-03-PLAN.md, landed the same plan this document is part of), the first genuine two-arm
comparison call this project's record has ever executed.

## Method

One real `Databasise.compare()` call, two arms, one query — `databasise/tests/seam/test_compare.py`
exercises the identical call this document's findings are drawn from (`dual_arm_store` fixture,
`test_keyed_by_selector`/`test_no_verdict_leaks`/`test_no_internal_identity_leaks`):

- **Query:** `QueryObject(text="What sat on the mat?")`
- **Arm 1 — LightRAG's `naive` arm**, resolved via `Selector(capability=["reads_vector"])`
  (`databasise/seam/selectors.py`'s own smallest-resolved-wiring-wins tie-break picks the 7-node
  naive wiring over hybrid/local/global's 15-17 nodes and HippoRAG's own 8 for this capability).
- **Arm 2 — HippoRAG 2's base wiring**, resolved via
  `Selector(capability=["reads_graph", "reads_kv"])` (only HippoRAG's 8-node wiring satisfies this
  at the smallest resolved size — mirrors `databasise/tests/seam/test_cross_modality_run.py`'s own
  selector choice).
- Both arms run against seeded, disjoint store fixtures under one shared `store_root`/workspace
  (RIG §RUN.1/§RUN.2's own per-modality isolation, proven separately by
  `databasise/tests/seam/test_store_isolation.py`), with stub embedding/LLM clients — no network
  call, no real corpus.

## Findings — every `ResponseEnvelope` field, per arm, this session's real run

`ResponseEnvelope.model_fields` (`databasise/seam/envelope.py`) declares exactly ten fields. Every
row below is a real observed value from the run described above, `[code-verified]`.

| Envelope field | LightRAG `naive` arm (observed) | HippoRAG base-wiring arm (observed) | Field present in both? | Content identical? |
|---|---|---|---|---|
| `answer` | `'{"keep_ids": ["f1", "f2"]}'` (the stub LLM's raw completion text, via the `generate` node) | `'Cats sit on mats.\n\nThe cat sat on the mat again.'` (assembled context, no completion) | Yes `[code-verified]` | **No — a content difference, not a field-set difference.** HippoRAG 2's base wiring has no generator position among its thirteen (06-01-SUMMARY.md's own named limitation); its `answer` field carries assembled retrieval context where LightRAG's carries a generated completion. The field exists in both envelopes with the same name and the same declared type (`str`) — the machinery that populates it differs by design, not the envelope's own shape. |
| `evidence` | `[{'ref': 'chunk-1', 'namespace': 'chunks', 'kind': 'text_chunk', 'score': 1.0, 'tier': None}]` | `[{'ref': 'chunk:c1', ...}, {'ref': 'chunk:c2', ...}]`, `namespace='hipporag-chunks'` | Yes `[code-verified]` | Field shape identical (`list[EvidenceRef]`, same four/five sub-fields on every item); content (ref values, namespace, scores, list length) legitimately differs — different corpora, different arms. |
| `trace_token` | a fresh opaque string, e.g. `'OL4uiWGKF2No1gRQBQgmZEmXUqkf6XRN3xEw97xrF3I'` | a fresh opaque string, e.g. `'3yApX6ncwTCJEGVvfClvLN4BHM2wg7lMuRH0k22b3Io'` | Yes `[code-verified]` | Field shape identical (`str`); content is expected to differ every call, by design (D-06 — each run mints its own random opaque token). Not a modality-conditioned difference at all. |
| `depth_label` | `'stage'` | `'opaque'` | Yes `[code-verified]` | **No — a content difference, not a field-set difference.** HippoRAG's positions all resolve to `opaque` effective depth under the taint rule (06-RESEARCH.md's own "Taint Rule" finding: the whole index side is `quarantined`/`opaque` until parity against the real upstream package is shown); LightRAG's `naive` arm's own `provides` node (`generate`) is `stage`. The field exists in both envelopes with the same name and the same declared type (`str`) — the two arms legitimately report different values in the same field, exactly as HippoRAG's still-`opaque` decomposition status predicts. |
| `partial` | `False` | `False` | Yes `[code-verified]` | Identical value this run (neither arm degraded or halted). |
| `degraded` | `False` | `False` | Yes `[code-verified]` | Identical value this run. |
| `stop_reason` | `None` | `None` | Yes `[code-verified]` | Identical value this run (neither arm's run stopped early). |
| `degradation_reason` | `None` | `None` | Yes `[code-verified]` | Identical value this run. |
| `token_accounting` | three `TokenBreakdownEntry` items (`counted_by` in `{'none', 'stub-embed', 'stub-llm'}`) | three `TokenBreakdownEntry` items (`counted_by` in `{'none', 'stub-embed', 'stub-llm'}`) | Yes `[code-verified]` | Field shape identical (`list[TokenBreakdownEntry]`, same five sub-fields on every item, same `counted_by` vocabulary in this run); per-entry counts legitimately differ (HippoRAG's arm made two embedding calls this run, LightRAG's one — a real difference in how many nodes call the embedding client, not an envelope-shape difference). |
| `seam_events` | `[]` | `[]` | Yes `[code-verified]` | Identical value this run (neither arm's run produced an out-of-`deps` mutation this session — no registered part in either wiring exercises MACH-11's correlation today, matching `databasise/seam/engine.py`'s own `_mach11_events` docstring). |

No field present in one arm's envelope was absent from the other's. This is true by construction,
not merely by observation: both arms are instances of the identical `ResponseEnvelope` pydantic
model (`databasise/seam/envelope.py`), assembled by the identical `_execute()` code path
(`databasise/seam/compare.py`'s own module docstring — no second envelope-assembly function for
the comparison case) — a field-set divergence between arms is not a shape this machine's own
construction can produce today, since both arms are the same Python type.

## Verdict

**No consumer-visible envelope field changed across the modality swap — F-14 holds for this pair:
LightRAG's `naive` arm and HippoRAG 2's base wiring.** All ten `ResponseEnvelope` fields are
present, with the same declared type, in both arms' responses. Two fields (`answer`,
`depth_label`) legitimately carry different *content* per arm — documented above, and expected
given HippoRAG's still-`opaque` decomposition status and its missing generator position — but a
content difference in a shared field is not the field-set incompleteness §18.3's own refutation
condition names. `§18.3`'s invariance rule is not refuted by this run.

This does not settle F-14 permanently — it settles it for the one real call this session ran. A
future arm (a third modality, or a further-decomposed HippoRAG once its own parity run lands)
could still surface a genuinely modality-conditioned field the envelope does not yet declare; this
document records what the first real call actually showed, not a proof that no such call ever
will.

## Method and limits

- **One query against two seeded fixtures, not the real-corpus run plan 06-08 performs.** This run
  used synthetic stub embedding/LLM clients and hand-seeded stores (`databasise/tests/seam/
  test_compare.py`'s own `dual_arm_store` fixture) — the same class of synthetic-store precedent
  `databasise/tests/seam/test_leak.py`/`test_cross_modality_run.py` already establish for this
  codebase's other real-seam-call proofs. It is not the real-corpus, real-query side-by-side run
  06-08 is scoped to perform.
- **This comparison is `architecture-comparison mode` per RIG §AA.4** — LightRAG and HippoRAG are
  two independently-registered wirings sharing no resolved recipe input, not merge-patch siblings
  of one base (`decomposition-parity mode`, which governs LightRAG's own arms against each other).
  "Parity, not gain" does **not** apply here, and no field difference recorded above is evidence
  about retrieval quality, ranking correctness, or which arm answers "better" — this document
  makes no such claim and none should be inferred from it.
  - HippoRAG's own two content differences (`answer`, `depth_label`) are consequences of its
    still-`opaque` decomposition status and its base wiring's own missing generator position
    (06-01-SUMMARY.md), not measurements of retrieval quality.
- **HippoRAG's index side is still `opaque`/`quarantined`** (06-RESEARCH.md's Taint Rule finding)
  — this run exercises HippoRAG's *query* side only, against pre-seeded stores, never HippoRAG's
  own index-side ingestion path. A future parity run against the real upstream `hipporag` package
  (06-RESEARCH.md's own recommendation) is what would earn HippoRAG's index side `stage` depth;
  nothing in this document changes that disposition.
