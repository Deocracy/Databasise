---
phase: 01-machine-core
plan: 02
subsystem: infra
tags: [rfc8785, pydantic, graphlib, asyncio, sqlite3, wiring, identity]

# Dependency graph
requires:
  - phase: 01-machine-core
    provides: "01-01's databasise/ package scaffold, pytest harness, D-12/D-09 door confirmations"
provides:
  - "databasise.run_wiring(wiring_doc, *, store_root, registry=None, determinism_setting, concurrency_setting) — the public entry point every later plan and consumer calls"
  - "identity/{canon,env,instance}.py — config_hash (RFC 8785), environment_hash (D-12 option-a), instance_hash/cache_partition_key (neither accepts a node id)"
  - "parts/{schema,registry}.py — NodeKind discriminated union (5 structural kinds), the frozen 17-member Effect literal, WiringNode/Part/NodeContext shapes, explicit in-code PartRegistry (D-13) with a passthrough part and a writes_kv part"
  - "validator/{parse,depth}.py — one-pass wiring parse accumulating violations, effective_depth (taint min-reduce, acyclic case via graphlib), derive_execution_mode (D-08: in-process only)"
  - "runner/{scheduler,trace}.py — graphlib.TopologicalSorter + asyncio.TaskGroup driver, per-node asyncio.Semaphore sized from config.max_concurrency (D-09 option-a), RunRecord/NodeTrace dataclasses matching rig-trace.schema.json exactly"
  - "stores/{base,kv}.py — StorageNameSpace lifecycle ABC (ported by copy from v1, D-14) and SqliteKVStore with a deferred-write buffer"
affects: ["01-03", "01-04", "01-05", "01-06", "01-07"]

actuals:
  tokens: 12747
  tasks: 1
  commits: 2

tech-stack:
  added: []
  patterns:
    - "graphlib.TopologicalSorter for readiness bookkeeping + one asyncio.TaskGroup per ready batch — no orchestrator, no external scheduler"
    - "Per-node asyncio.Semaphore created fresh per node per run, sized from that node's own config.max_concurrency — never a module-level/process-wide concurrency primitive (D-09/D-11)"
    - "Bottom-up instance-identity resolution over the same topological order the depth pass uses: resolved_dependency_ids is the sorted list of each dep's own instance_hash, never the raw dependency node id"
    - "ParsedWiring is a frozen dataclass wrapping MappingProxyType views — the load-frozen snapshot CONTRACT §11 requires"
    - "Explicit, schema-valid placeholder sentinels (bundle_ref, corpus_snapshot_hash, tier/feed_tier) documented at the point of use rather than silently omitted, so the schema stays satisfied before Phase 2 builds the real producing mechanism"

key-files:
  created:
    - databasise/identity/canon.py
    - databasise/identity/env.py
    - databasise/identity/instance.py
    - databasise/parts/schema.py
    - databasise/parts/registry.py
    - databasise/validator/parse.py
    - databasise/validator/depth.py
    - databasise/runner/scheduler.py
    - databasise/runner/trace.py
    - databasise/stores/base.py
    - databasise/stores/kv.py
    - databasise/tests/fixtures/wiring-tracer.json
    - databasise/tests/test_tracer_end_to_end.py
  modified:
    - databasise/__init__.py

key-decisions:
  - "D-12 (recorded, plan 01-01 Task 3) transcribed verbatim into identity/env.py's module docstring: option-a — environment_hash is the resolved importlib.metadata distribution closure, never a lockfile, never a Nix store path."
  - "D-09 (recorded, plan 01-01 Task 4) transcribed verbatim into runner/scheduler.py's module docstring: option-a — config.max_concurrency lives inside the node's own config object and is therefore a config_hash input."
  - "NodeKind's five structural members (fanout/join/fixpoint/subgraph/opaque) are defined as a pydantic discriminated union, but WiringNode.kind is typed as a plain str — the tracer's two reference parts (passthrough, kv-writer) are primitive kinds, which CONTRACT §2 names as part of NodeKind's membership without ever freezing an authoritative list; a later plan builds the structural-kind dispatch that actually consumes NodeKind."
  - "derive_execution_mode's in-process/subprocess split treats machine-owned store effects (reads_*/writes_kv/writes_vector/writes_graph/writes_lexical/self_storage) as safe to host in-process (internal to the trusted runtime) and reserves subprocess for effects crossing a real external boundary (calls_llm/calls_rerank/calls_embedding/net/fs/mutates_store) or fixpoint (iterative) nodes — CONTRACT §3 requires the derivation but does not freeze the exact effect-to-mode table, so this is Phase 1's own documented choice."
  - "Trace-field placeholder policy: bundle_ref/corpus_snapshot_hash carry documented sentinel strings (no eval bundle exists until Phase 2); tier/feed_tier carry a documented T3 placeholder for nodes that never handle a scored evidence item. Every other D-10 gate-read field (arm_execution_order, cache_hit, guards_fired, realised_budget_share, determinism_setting, concurrency_setting) carries a real, computed value from this commit forward."

patterns-established:
  - "Store lifecycle ABC (initialize/finalize/index_done_callback/drop_pending_index_ops/drop) shared by every stores/*.py adapter — gives the runner one commit/abort contract regardless of backend (v1/lightrag/base.py:160-219, ported by copy per D-14)."
  - "Deferred-write buffer with read-your-writes-before-flush discipline, reproduced from v1's Cozo adapter pattern, for SqliteKVStore — the same discipline plan 01-06's Cozo port will need."

requirements-completed: [EMBED-01, MACH-05, MACH-06, MACH-08]

coverage:
  - id: D1
    description: "A trivial two-node wiring JSON submitted to databasise.run_wiring executes to completion and returns a run record that validates against rig-trace.schema.json with zero errors (partial=false, degraded=false, stop_reason=null, 2 nodes)"
    requirement: "MACH-05"
    verification:
      - kind: unit
        ref: "databasise/tests/test_tracer_end_to_end.py#test_tracer_runs_end_to_end_and_produces_a_schema_valid_run_record"
        status: pass
    human_judgment: false
  - id: D2
    description: "The KV node's write is readable back from the embedded SQLite store after the run, proving the run touched a real store"
    requirement: "EMBED-01"
    verification:
      - kind: unit
        ref: "databasise/tests/test_tracer_end_to_end.py#test_kv_node_write_is_readable_back_from_the_sqlite_store"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every NodeTrace carries a 64-char lowercase-hex instance_hash that never equals its own node_id (node ids are positions, never identities)"
    requirement: "MACH-06"
    verification:
      - kind: unit
        ref: "databasise/tests/test_tracer_end_to_end.py#test_instance_hash_is_a_64_char_lowercase_hex_digest_and_never_equals_node_id"
        status: pass
    human_judgment: false
  - id: D4
    description: "Instance identity is stable across two runs of the same wiring (per-node instance_hash pairwise equal) while run_id differs each time"
    requirement: "MACH-06"
    verification:
      - kind: unit
        ref: "databasise/tests/test_tracer_end_to_end.py#test_identity_is_stable_across_runs_while_run_id_differs"
        status: pass
    human_judgment: false
  - id: D5
    description: "Mutating a single byte inside one node's config changes only that node's instance_hash, leaving an unrelated node's identity untouched"
    requirement: "MACH-06"
    verification:
      - kind: unit
        ref: "databasise/tests/test_tracer_end_to_end.py#test_mutating_one_nodes_config_changes_only_that_nodes_instance_hash"
        status: pass
    human_judgment: false
  - id: D6
    description: "config.max_concurrency is one of the bytes covered by config_hash (D-09) — two configs differing only in that field hash differently"
    requirement: "MACH-08"
    verification:
      - kind: unit
        ref: "databasise/tests/test_tracer_end_to_end.py#test_config_max_concurrency_is_covered_by_config_hash"
        status: pass
    human_judgment: false
  - id: D7
    description: "Importing databasise spawns no child process and opens no listening socket (EMBED-01's no-external-server claim, verified at the import boundary)"
    requirement: "EMBED-01"
    verification:
      - kind: unit
        ref: "databasise/tests/test_tracer_end_to_end.py#test_importing_databasise_spawns_no_child_process_or_listening_socket"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-08-30
status: complete
---

# Phase 01 Plan 02: Machine-Core End-to-End Tracer Summary

**One production-quality two-node wiring (passthrough -> kv-writer) runs end-to-end through identity, parts, validator, runner, and stores, emitting a run record that validates against `rig-trace.schema.json` with zero errors — the proven slice every wave-3 expansion plan builds on.**

## Performance

- **Duration:** 45 min
- **Tasks:** 1
- **Files modified:** 14 (13 new, 1 modified)

## Accomplishments

- Implemented the identity layer (`identity/canon.py`, `identity/env.py`, `identity/instance.py`): RFC 8785 `config_hash` over author-supplied config verbatim, the D-12 resolved-closure `environment_hash`, and `instance_hash`/`cache_partition_key` — neither of which accepts a node id, per the wiring-spec's node-id-is-a-position rule
- Implemented the parts layer (`parts/schema.py`, `parts/registry.py`): the frozen 17-member `Effect` literal, the `NodeKind` discriminated union's five structural members, `WiringNode`/`Part`/`NodeContext` shapes, and an explicit in-code `PartRegistry` (D-13) registering a zero-effect passthrough part and a `writes_kv` part
- Implemented the validator layer (`validator/parse.py`, `validator/depth.py`): one-pass wiring parse that accumulates violations, `effective_depth` as the taint min-reduce over `graphlib.TopologicalSorter` (the acyclic case; Tarjan SCC condensation is plan 01-03's deliverable), and `derive_execution_mode` (Phase 1: in-process only, per D-08)
- Implemented the runner layer (`runner/scheduler.py`, `runner/trace.py`): `graphlib.TopologicalSorter` + one `asyncio.TaskGroup` per ready batch, a per-node `asyncio.Semaphore` sized from `config.max_concurrency` (D-09 option-a, never a process-wide cap per D-11), and `RunRecord`/`NodeTrace`/`TokenAccounting` dataclasses matching `rig-trace.schema.json` field-for-field
- Implemented the stores layer (`stores/base.py`, `stores/kv.py`): the `StorageNameSpace` lifecycle ABC ported by copy from v1 (D-14), and `SqliteKVStore` with a deferred-write buffer (read-your-writes before flush)
- Wired the public entry point `databasise.run_wiring(...)` composing parse → depth → identity → scheduler → trace into one call
- 7/7 tracer tests pass; the emitted run record validates against `docs/system-model/rig-trace.schema.json` with zero errors

## Task Commits

Each task was committed atomically (TDD RED/GREEN pair, per this plan's single `tracer, tdd="true"` task):

1. **Task 1 (RED): End-to-end tracer test** — `8389e59` (test)
2. **Task 1 (GREEN): End-to-end tracer implementation** — `fc90cdb` (feat)

**Plan metadata:** (this commit) `docs(01-02): complete machine-core end-to-end tracer plan`

## Files Created/Modified

- `databasise/identity/canon.py` - `canonicalise()` (RFC 8785 wrapper), `config_hash()`, `CanonicalisationError`
- `databasise/identity/env.py` - `environment_hash()` (D-12 option-a), memoised per process
- `databasise/identity/instance.py` - `instance_hash()`, `cache_partition_key()` — neither accepts a node id
- `databasise/parts/schema.py` - `Effect` (17-member Literal), `Depth`, `NodeKind` (discriminated union, 5 structural kinds), `Part`, `WiringNode`, `NodeContext`
- `databasise/parts/registry.py` - `PartRegistry` (D-13, explicit in-code dict), `UnknownPartError`, two reference part bodies
- `databasise/validator/parse.py` - `parse_wiring()`, `ParsedWiring` (frozen, load-frozen snapshot), `WiringValidationError`
- `databasise/validator/depth.py` - `effective_depth()` (taint min-reduce, acyclic), `derive_execution_mode()`
- `databasise/runner/scheduler.py` - `run_wiring()` (TopologicalSorter + TaskGroup driver), `_resolve_identities()`, `UnsupportedExecutionModeError`
- `databasise/runner/trace.py` - `RunRecord`, `NodeTrace`, `TokenAccounting` dataclasses with `to_dict()`
- `databasise/stores/base.py` - `StorageNameSpace` lifecycle ABC (ported by copy, v1/lightrag/base.py:160-219)
- `databasise/stores/kv.py` - `SqliteKVStore` (deferred-write buffer, one db file per namespace directory)
- `databasise/tests/fixtures/wiring-tracer.json` - the two-node tracer fixture (passthrough -> kv-writer)
- `databasise/tests/test_tracer_end_to_end.py` - 7 tests covering all `<behavior>` claims
- `databasise/__init__.py` - extended with the public `run_wiring()` entry point and `TRACER_WORKSPACE`/`TRACER_KV_NAMESPACE` constants

## Decisions Made

- **D-12 transcribed** into `identity/env.py`'s module docstring: option-a, the resolved `importlib.metadata` distribution closure.
- **D-09 transcribed** into `runner/scheduler.py`'s module docstring: option-a, `config.max_concurrency` inside the node's own config.
- **`WiringNode.kind` typed as `str`, not joined to the `NodeKind` union.** CONTRACT §2 names `NodeKind`'s membership as "the primitive part types plus five structural kinds" without ever freezing an authoritative list of the primitive types. The tracer's two reference parts are primitive kinds (`passthrough`, `kv-writer`), so `NodeKind`'s discriminated union (defined here with its five structural members) is a declared skeleton this plan does not yet consume operationally — a later plan builds the structural-kind (fanout/join/fixpoint/subgraph/opaque) dispatch that does.
- **`derive_execution_mode`'s effect-to-mode table is this plan's own documented choice**, since CONTRACT §3 requires the derivation ("only pure, non-iterative nodes MAY be hosted in-process") without freezing an exact table. Machine-owned store effects stay in-process (internal to the trusted runtime); effects crossing a real external boundary (LLM/rerank/embedding calls, network, filesystem, in-place store overwrite) or `fixpoint` kind require `subprocess`. Both tracer nodes derive `in-process`, satisfying the plan's own acceptance criterion.
- **Trace-field placeholder policy** (documented in `runner/trace.py`'s module docstring): `bundle_ref`/`corpus_snapshot_hash` carry sentinel strings (no eval bundle until Phase 2); `tier`/`feed_tier` carry a `T3` placeholder for nodes that never handle a scored evidence item. Every other D-10 gate-read field carries a real value from this commit forward.
- **Store lifecycle scoped down from v1's shape**: `StorageNameSpace` drops v1's `global_config` field (namespace/workspace only) — nothing in this tracer needs it, and it can be added back without breaking the ABC's shape.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test 7's listening-socket assertion was environment-dependent**
- **Found during:** Task 1, running the test suite for the first time
- **Issue:** The initial test asserted `after_sockets == before_sockets == 0`, but this container's shared network namespace already exposes pre-existing listening sockets in `/proc/self/net/tcp{,6}` (system-wide, unrelated to `databasise`) — the `== 0` baseline assumption was wrong for this environment and made the test fail regardless of `databasise`'s own behavior.
- **Fix:** Changed the assertion to `after_sockets <= before_sockets` (no growth across the import), which is what the plan's own behavior spec actually claims ("importing databasise ... opens no listening socket") rather than "the process has zero listening sockets ever."
- **Files modified:** `databasise/tests/test_tracer_end_to_end.py`
- **Verification:** `uv run pytest tests/test_tracer_end_to_end.py -x` — 7 passed.
- **Committed in:** `8389e59` (test commit — fixed before commit, not a follow-up)

**2. [Rule 3 - Blocking] ruff lint fixes on newly created files**
- **Found during:** Task 1, post-implementation lint pass
- **Issue:** `uv run ruff check` flagged import-sort ordering (`I001`), `typing.Callable`/`typing.Mapping` deprecated in favor of `collections.abc` (`UP035`), `Union[...]` vs `X | Y` (`UP007`), redundant `return None` (`RET501`), a blind `except Exception` in `drop()` (`BLE001`), and `subprocess.run` without an explicit `check=` argument (`PLW1510`).
- **Fix:** Ran `ruff check --fix` scoped to only this plan's own files (not touching `conftest.py`/`test_conftest_fixtures.py` from plan 01-01), then manually cleaned up the auto-fixed local-import formatting in `canon.py`, added a targeted `# noqa: BLE001` on `drop()`'s documented broad-catch contract (matches v1's `StorageNameSpace.drop()` interface, which explicitly returns `{"status": "error", ...}` on any failure), and added `check=False` to the test's `subprocess.run` call.
- **Files modified:** `databasise/identity/canon.py`, `databasise/parts/schema.py`, `databasise/validator/parse.py`, `databasise/stores/base.py`, `databasise/stores/kv.py`, `databasise/tests/test_tracer_end_to_end.py`
- **Verification:** `uv run ruff check <this plan's files>` — all checks passed; `uv run pytest -q` — 10 passed (no regression).
- **Committed in:** `fc90cdb` (feat commit) / `8389e59` (test commit, for the test file's own fix)

---

**Total deviations:** 2 auto-fixed (1 bug fix in the test's own assertion, 1 blocking lint cleanup)
**Impact on plan:** Both fixes are scoped entirely to files this plan already owned; no acceptance criterion, dependency, or architectural decision was changed. No scope creep.

## Issues Encountered

None beyond the two deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The proven slice is in place for wave 3's four expansion plans to build outward from: identity, parts, validator, runner, stores, and trace all exist in real, committed, tested form on one end-to-end path. `cd databasise && uv run pytest -q` is green (10 tests). No blockers.

Note for the orchestrator: this plan's frontmatter lists `requirements: [EMBED-01, MACH-05, MACH-06, MACH-08]`, all four of which are also listed by other plans in this phase — per this phase's shared context, none of these should be marked complete in `REQUIREMENTS.md` until their last contributing plan lands; the orchestrator closes them at phase end.

---
*Phase: 01-machine-core*
*Completed: 2026-08-30*

## Self-Check: PASSED

All 14 claimed files found on disk; commits `8389e59` and `fc90cdb` confirmed in `git log --oneline --all`.
