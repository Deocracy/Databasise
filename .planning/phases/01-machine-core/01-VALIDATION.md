---
phase: 1
slug: machine-core
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-30
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2+ / pytest-asyncio 1.2+ with `asyncio_mode = "auto"`, matching v1's existing convention (`v1/pyproject.toml:189-193`). `jsonschema` is a dev dependency so run records can be validated against `docs/system-model/rig-trace.schema.json`. |
| **Config file** | `databasise/pyproject.toml` `[tool.pytest.ini_options]` — **does not exist yet; plan 01-01 Task 2 creates it (Wave 0)** |
| **Quick run command** | `cd databasise && uv run pytest tests/ -x -k <touched-module>` |
| **Full suite command** | `cd databasise && uv run pytest tests/` |
| **Estimated runtime** | ~45 seconds for the full suite (embedded stores only; no network, no model calls — the reference LLM part is a deterministic fake) |

---

## Sampling Rate

- **After every task commit:** Run `cd databasise && uv run pytest tests/ -x -k <touched-module>`
- **After every plan wave:** Run `cd databasise && uv run pytest tests/`
- **Before `/gsd-verify-work`:** Full suite must be green, **and** `cd databasise && uv run python -m databasise.tools.check_import_boundary` must exit 0, **and** the ported Cozo frozen-bug regression suite must be green against `databasise/stores/graph.py` specifically (01-RESEARCH.md Pitfall 2) rather than only against the original v1 class.
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | EMBED-01 | — | package-legitimacy gate for rfc8785 before first install | checkpoint | *(blocking-human gate — no automated command)* | n/a | ⬜ pending |
| 1-01-02 | 01 | 1 | EMBED-01 | — | dependency set is the proof: 4 runtime deps, no server client | smoke | `cd databasise && uv run pytest --collect-only` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | MACH-06 | — | one-way gate: environment-hash input set (D-12) | checkpoint | *(blocking decision — no automated command)* | n/a | ⬜ pending |
| 1-01-04 | 01 | 1 | MACH-05 | — | one-way gate: per-node semaphore in `config_hash` (D-09) | checkpoint | *(blocking decision — no automated command)* | n/a | ⬜ pending |
| 1-01-05 | 01 | 1 | EMBED-01, MACH-05, MACH-06, MACH-08 | — | tracer: schema-valid run record, no listening socket | integration | `cd databasise && uv run pytest tests/test_tracer_end_to_end.py -x` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 2 | MACH-05, MACH-08 | — | cycle-safe depth; all violations at once with JSON-Pointer paths | unit | `cd databasise && uv run pytest tests/validator/test_cycles_and_depth.py -x` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 2 | MACH-08 | — | blast-radius refusal at load time; placement refusal by name (D-08) | unit | `cd databasise && uv run pytest tests/validator/test_blast_radius.py tests/validator/test_execution_mode.py -x` | ❌ W0 | ⬜ pending |
| 1-02-03 | 02 | 2 | MACH-08 | — | spike-005 conformance, 12 cases, no exemptions (D-03) | unit | `cd databasise && uv run pytest tests/validator/test_taint_conformance.py -x` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 2 | MACH-06 | — | int64 exclusion, int/float collapse, UTF-16 key order, no node-id identity | unit | `cd databasise && uv run pytest tests/identity/ -x` | ❌ W0 | ⬜ pending |
| 1-03-02 | 03 | 2 | MACH-06 | — | deny-by-default reaches the part boundary, not only the validator | unit | `cd databasise && uv run pytest tests/parts/test_reference_parts.py -x` | ❌ W0 | ⬜ pending |
| 1-03-03 | 03 | 2 | MACH-06 | — | explicit registry, no dynamic-import fallback (D-13) | unit | `cd databasise && uv run pytest tests/parts/test_registry.py -x` | ❌ W0 | ⬜ pending |
| 1-04-01 | 04 | 2 | MACH-08 | — | namespace cannot escape store root; scope readable in directory name | unit | `cd databasise && uv run pytest tests/stores/test_namespace_derivation.py -x` | ❌ W0 | ⬜ pending |
| 1-04-02 | 04 | 2 | EMBED-01, MACH-08 | — | bound parameters throughout; no silent `LIKE` fallback when FTS5 absent | unit | `cd databasise && uv run pytest tests/stores/test_kv.py tests/stores/test_lexical.py -x` | ❌ W0 | ⬜ pending |
| 1-04-03 | 04 | 2 | MACH-08 | — | atomic content-addressed write; partial blob never observable | unit | `cd databasise && uv run pytest tests/stores/test_blob.py -x` | ❌ W0 | ⬜ pending |
| 1-05-01 | 05 | 2 | EMBED-01, MACH-08 | — | Datalog metacharacters cannot alter query structure (bound params) | integration | `cd databasise && uv run pytest tests/stores/test_graph.py -x` | ❌ W0 | ⬜ pending |
| 1-05-02 | 05 | 2 | EMBED-01 | — | four Cozo 0.7.6 silent-wrong-result bugs bound against the NEW adapter | regression | `cd databasise && uv run pytest tests/stores/test_graph_frozen_bugs.py -x` | ❌ W0 | ⬜ pending |
| 1-05-03 | 05 | 2 | EMBED-01, MACH-08 | — | embedding-count mismatch raises before mutation; no partial write | integration | `cd databasise && uv run pytest tests/stores/test_vector.py -x` | ❌ W0 | ⬜ pending |
| 1-06-01 | 06 | 3 | MACH-06, MACH-08 | — | registry applies its own scope filter; caller cannot disable it | integration | `cd databasise && uv run pytest tests/registry_artifact/test_index.py -x` | ❌ W0 | ⬜ pending |
| 1-06-02 | 06 | 3 | MACH-08 | — | no route to the registry bypasses the blast-radius rule (D-02) | integration | `cd databasise && uv run pytest tests/registry_artifact/test_write_path_blast_radius.py -x` | ❌ W0 | ⬜ pending |
| 1-06-03 | 06 | 3 | MACH-06 | — | append-only enforced by DB triggers, not by method omission | unit | `cd databasise && uv run pytest tests/ledger/test_ledger.py -x` | ❌ W0 | ⬜ pending |
| 1-07-01 | 07 | 3 | MACH-05 | — | per-node semaphore only; no process-wide cap (D-09/D-11); stable dispatch order | integration | `cd databasise && uv run pytest tests/runner/test_scheduler.py -x` | ❌ W0 | ⬜ pending |
| 1-07-02 | 07 | 3 | MACH-05 | — | exact integer budget split; halt is first-class and never reported clean | unit | `cd databasise && uv run pytest tests/runner/test_budget.py -x` | ❌ W0 | ⬜ pending |
| 1-07-03 | 07 | 3 | MACH-05 | — | full §TR.1 field set; constructor refuses a confounded-as-clean record (D-10) | integration | `cd databasise && uv run pytest tests/runner/test_run_record.py -x` | ❌ W0 | ⬜ pending |
| 1-08-01 | 08 | 4 | EMBED-01 | — | no child process, no listening socket, no silent fallback to an external store | smoke | `cd databasise && uv run pytest tests/test_embed_startup.py -x` | ❌ W0 | ⬜ pending |
| 1-08-02 | 08 | 4 | EMBED-01 | — | v1 import boundary machine-checked in 4 syntactic forms + filesystem reach (D-14) | lint/unit | `cd databasise && uv run pytest tests/test_import_boundary.py -x` | ❌ W0 | ⬜ pending |
| 1-08-03 | 08 | 4 | EMBED-01, MACH-05, MACH-06, MACH-08 | — | opaque arm writes quarantined, cannot reach shared KV; namespaces visibly separate | acceptance | `cd databasise && uv run pytest tests/test_phase_success_criteria.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Sampling continuity:** no three consecutive tasks lack an automated verify. The three checkpoint
tasks (1-01-01, 1-01-03, 1-01-04) are consecutive but are gates rather than code-producing tasks;
the code-producing task on either side (1-01-02 and 1-01-05) each carries an automated command.

---

## Wave 0 Requirements

Wave 0 is **plan 01-01 Task 2**, which must complete before any test in this phase can run. Nothing
exists on disk yet — there is no root-level build config in this repository at all.

- [ ] `databasise/pyproject.toml` — build config for the new package, `requires-python = ">=3.11"`, four runtime dependencies, `[tool.pytest.ini_options]` with `asyncio_mode = "auto"`. **Blocks every test below.**
- [ ] `databasise/.python-version` — pins the uv-managed cpython-3.12.13 rather than the system 3.13
- [ ] Framework install — `pytest`, `pytest-asyncio`, `jsonschema`, `ruff` as dev dependencies inside `databasise/`
- [ ] `databasise/tests/conftest.py` — shared fixtures `store_root` (per-namespace temp store directories per D-07), `rig_trace_schema` (loads `docs/system-model/rig-trace.schema.json`), `assert_valid_trace` (validates an emitted run record against it)
- [ ] `databasise/tests/fixtures/wiring-tracer.json` — the two-node wiring the tracer test drives

Ported rather than newly authored (plan 01-05 Task 2, not Wave 0 but called out because it is an
adaptation rather than a fresh suite): `v1/tests/kg/test_cozo_graph_storage.py`'s frozen-bug
regression shapes, retargeted at `databasise/stores/graph.py`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Success criterion 4 reads as *evidence* to a human — one directory per namespace, scope legible in the name, opaque arm visibly separate from the transparent arm | MACH-08 | The automated test asserts directory names and separation programmatically, but the criterion's value is that separation is inspectable from *outside* the process. A human confirming it by eye is what makes the property a product claim rather than a test artifact. | Run `cd databasise && uv run pytest tests/test_phase_success_criteria.py -x -v`, then list the store root the test prints and confirm by eye. Carried to the end-of-phase review (`human_verify_mode: end-of-phase`), not a mid-run blocking checkpoint. |
| `rfc8785` package legitimacy before first install | EMBED-01 | Package-legitimacy gates are never auto-approvable; `workflow.auto_advance` is ignored for them. The check is a human reading a registry page. | Plan 01-01 Task 1. Confirm version 0.1.4 / 2024-09-27 / Trail of Bits / repo name matches package name exactly. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies — **satisfied**: every non-checkpoint task carries an automated command; all commands depend on Wave 0 (plan 01-01 Task 2)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify — **satisfied**, see note under the map
- [ ] Wave 0 covers all MISSING references — **satisfied**: every ❌ W0 row resolves once plan 01-01 Task 2 lands
- [ ] No watch-mode flags — **satisfied**: no command uses `--watch`, `-f`, or a persistent runner
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
