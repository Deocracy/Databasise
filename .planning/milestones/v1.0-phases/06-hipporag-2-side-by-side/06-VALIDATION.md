---
phase: "6"
slug: "hipporag-2-side-by-side"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-09"
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from `06-RESEARCH.md ## Validation Architecture`. The Per-Task
> Verification Map is filled once PLAN.md task IDs exist.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2+ (`databasise/pyproject.toml` → `[dependency-groups] dev`) |
| **Config file** | `databasise/pyproject.toml` → `[tool.pytest.ini_options]` (`asyncio_mode="auto"`, `testpaths=["tests"]`) |
| **Quick run command** | `cd databasise && uv run pytest -q tests/<new-directory>/` |
| **Full suite command** | `cd databasise && uv run pytest -q` |
| **Estimated runtime** | full suite ~grew past 745 tests at Phase 5 close; expect growth this phase |

---

## Sampling Rate

- **After every task commit:** Run `cd databasise && uv run pytest -q tests/<new-directory>/`
- **After every plan wave:** Run `cd databasise && uv run pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** quick run under 60s; full suite is the wave-merge gate, not the per-task gate

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| {6-NN-NN} | {NN} | {N} | {REQ-ID} | — | N/A | unit | `{command}` | ❌ W0 | ⬜ pending |

*Filled from PLAN.md task IDs by `/gsd-validate-phase`. Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Requirement → behavior map (from research, pre-task-ID)

| Req ID | Behavior | Test Type | Automated Command |
|--------|----------|-----------|-------------------|
| MODAL-04 | Each of the 13 HippoRAG parts registers with correct `effects[]` / `kind` / `structural_depth` | unit | `pytest tests/parts_core/hipporag/test_registration.py -x` |
| MODAL-04 | The `ppr` node's PPR call reproduces upstream `hipporag` scores within tolerance on a small fixture graph | integration | `pytest tests/parts_core/hipporag/test_ppr_parity.py -x` |
| MODAL-04 | Bulk-export produces a valid `igraph.Graph` from real Cozo data (round-trip: write via `graph-augment-persist`, read via `ppr`) | integration | `pytest tests/stores/test_graph_bulk_export.py -x` |
| MODAL-05 | LightRAG's and HippoRAG's namespaces resolve to different directories on the same corpus | unit | `pytest tests/test_namespace_isolation.py -x` |
| MODAL-05 | The same query against both arms produces schema-conformant `ScoredItem` output on both sides | integration | `pytest tests/seam/test_cross_modality_run.py -x` |
| API-08 | A 2-selector comparison returns a dict keyed by those exact selector values, with no internal id anywhere in the response | unit | `pytest tests/seam/test_compare.py::test_keyed_by_selector -x` |
| API-08 | A 1-selector comparison returns a bare envelope (a run), not a comparison dict | unit | `pytest tests/seam/test_compare.py::test_single_selector_is_a_run -x` |
| API-08 | A comparison response contains no verdict field or value from §5's eight-verdict vocabulary | unit | `pytest tests/seam/test_compare.py::test_no_verdict_leaks -x` |
| MACH-10 | F-07 decision recorded — protocol defined and tested, OR exclusion documented | manual-only | N/A — evidence-document review |
| MACH-02 | Eval bundle round-trips dev/holdout/sealed content and mints a new version on any of the five invalidating changes | unit | `pytest tests/eval/test_bundle_versioning.py -x` |
| MACH-03 | A/A calibration on a fixture arm produces a bootstrap null; re-running with `cache_hit=True` injected is refused as an unusable floor | unit | `pytest tests/eval/test_calibration.py -x` |
| MACH-03 | T1's calibrated floor is narrower than T0's on the same fixture | manual-only | Owner-confirmed numeric threshold required first |

---

## Wave 0 Requirements

- [ ] `CozoGraphStore` bulk-export method in `databasise/stores/graph.py` — no test infrastructure exists for it yet
- [ ] `FaissVectorStore` self-KNN / score-all methods in `databasise/stores/vector.py`
- [ ] The `join` / `fanout` structural-kind dispatch in the runner — declared in `databasise/parts/schema.py` but never implemented (its own docstring says so)
- [ ] `tests/parts_core/hipporag/` directory plus its `conftest.py` and fixtures
- [ ] `tests/eval/` directory — greenfield; no eval-bundle or calibration test infrastructure exists anywhere in this codebase
- [ ] Isolated-venv harness for the real upstream `hipporag` package (parity oracle), with a `conftest.py`-level skip-if-absent guard mirroring Phase 5's lazy optional-SDK import pattern for the `mcp` extra

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| F-07 discharge — snapshot/reset protocol defined, or permanent A/B exclusion recorded | MACH-10 | The outcome is a recorded owner decision, not a computable property | Review the evidence document against `PARTS.md`'s house format; confirm every mutable-store component appears in exactly one of the two dispositions |
| T1 null width materially narrower than T0's | MACH-03 | "Materially narrower" is not quantified in any project document; the threshold is an owner decision | Owner sets the numeric threshold, then reads the bootstrap-resampled p95 floor keyed to `(bundle@v, tier, metric)` for both tiers and confirms the T1/T0 relation holds |
| F-14 seam-envelope record | MACH-10 | The recorded outcome is either-way; the finding itself is the deliverable | On the first genuine seam call across the modality swap, diff the consumer-visible envelope fields and record either "no field changed" or the name of the field that did |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s on the quick run
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
