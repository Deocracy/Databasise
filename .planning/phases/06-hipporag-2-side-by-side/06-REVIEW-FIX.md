---
phase: 06-hipporag-2-side-by-side
fixed_at: 2026-09-10T03:48:32Z
review_path: .planning/phases/06-hipporag-2-side-by-side/06-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 06: Code Review Fix Report

**Fixed at:** 2026-09-10T03:48:32Z
**Source review:** `.planning/phases/06-hipporag-2-side-by-side/06-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope (Critical + Warning): 3
- Fixed: 3
- Skipped: 0

Info findings (IN-01, IN-02) were out of `fix_scope: critical_warning` and were not touched.

## Fixed Issues

### CR-01: `ingest()`/`delete_document()` never reach HippoRAG's index — contradicts this phase's own coverage claim

**Files modified:** `.planning/phases/06-hipporag-2-side-by-side/COVERAGE.md`
**Commit:** `1aacf5b`
**Applied fix:** Took the review's option (b): `Databasise.ingest()`/`delete_document()`
genuinely have no HippoRAG-targeted write path today — adding one (option (a)) would require a
new modality-targeting concept for write operations (`ingest`/`delete` take no selector, unlike
`query`), which is a design decision with REST/MCP/schema surface area far beyond a mechanical
review-fix diff. Corrected `COVERAGE.md`'s false claim that `ingest`/`delete` "remain reachable
identically for both LightRAG and HippoRAG arms" to state explicitly that those two operations are
LightRAG-arm only in this phase, that HippoRAG's index is populated only via the standalone
`parity/build_hipporag_index.py` harness (which bypasses the public seam entirely), and that the
resulting "empty HippoRAG result after ingest" behavior is a known, now-documented gap rather than
an undocumented contradiction — tracked as follow-up scope for whichever future phase gives
HippoRAG a public write path. This resolves the specific defect the finding's own title names
("contradicts this phase's own coverage claim"); the deeper architectural gap (no HippoRAG write
surface) remains, now honestly recorded instead of contradicted.

### WR-01: `entity-fact-embed`'s wiring-declared `effects` under-declares relative to its own Part and its own evidence record

**Files modified:** `databasise/wirings/hipporag/base.json`
**Commit:** `83e1a3c`
**Applied fix:** Updated the `entity-fact-embed` node's `effects` array from
`["calls_embedding", "writes_vector"]` to `["calls_embedding", "writes_vector", "writes_kv"]`,
matching both `HIPPORAG_ENTITY_FACT_EMBEDDER_PART.effects` (already `writes_kv`-inclusive in
`entity_fact_embed.py`) and `HIPPORAG-PORT-RECORD.md`'s own reconciliation table. No runtime
behavior change (effect-union computations are keyed off the registered `Part`, never the wiring
node, per CR-01's own precedent cited in the finding) — this closes an audit-trail gap only.
Verified: `tests/evidence/test_hipporag_port_record.py`, `tests/parts_core/hipporag/`,
`tests/parts/test_registry.py`, `tests/seam/` all pass (255 passed, 1 skipped).

### WR-02: `entity_fact_embed.py` reports only the entity-embedding call's `resolved_model_identity`, silently dropping the fact-embedding call's own

**Files modified:** `databasise/parts_core/hipporag/entity_fact_embed.py`
**Commit:** `31e1ced`
**Applied fix:** Took the review's option 1 (assert equality, raise on mismatch) rather than
option 2 (report both identities), to match this file's own sibling precedent
(`reset_vector_join.py`'s arity-mismatch check: `raise ValueError` naming the disagreement, never
a best-effort merge) instead of inventing a new field/abstraction no downstream consumer reads.
Added a check immediately after both `embedding_client.embed()` calls: if
`entity_embed_result.resolved_model_identity != fact_embed_result.resolved_model_identity`, raises
`ValueError` naming both identities. In production this is a no-op (one embedding client resolves
one stable identity per process, confirmed harmless in the review's own text) — the fix only
changes behavior for the currently-unreachable divergent-identity case, which was previously
silently mishandled.

## Skipped Issues

None — all in-scope findings were fixed.

## Verification

Ran inside an isolated git worktree
(`.claude/worktrees/rf-06-<pid>-<epoch>/`) on branch `gsd-reviewfix/06-<pid>`, using the main
checkout's existing venv (`databasise/.venv`) with `PYTHONPATH` pointed at the worktree so imports
resolved to the worktree's edited files rather than the main checkout's editable install:

```
cd databasise && PYTHONPATH=<worktree-root>:$PYTHONPATH python -m pytest \
  tests/evidence/test_hipporag_port_record.py \
  tests/parts_core/hipporag/ \
  tests/parts/test_registry.py \
  tests/seam/ -q
```
Result: **255 passed, 1 skipped** (after all three fixes were applied, before any were committed).

Also ran per-fix, narrower slices during development (all passing):
- `tests/parts_core/hipporag/test_registration.py tests/evidence/test_hipporag_port_record.py` — 15 passed
- `tests/parts/test_registry.py tests/parts_core/hipporag/ tests/seam/` — 245 passed, 1 skipped

Syntax/structure checks:
- `databasise/wirings/hipporag/base.json` — `node -e "JSON.parse(...)"` — OK
- `databasise/parts_core/hipporag/entity_fact_embed.py` — `python3 -c "ast.parse(...)"` — OK
- `.planning/phases/06-hipporag-2-side-by-side/COVERAGE.md` — Markdown, Tier 1 re-read only (no syntax checker applicable)

The worktree's branch (`gsd-reviewfix/06-<pid>`) was fast-forward-merged into `main` and the
worktree removed after all three commits landed; `main` now carries all three fix commits.

---

_Fixed: 2026-09-10T03:48:32Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
