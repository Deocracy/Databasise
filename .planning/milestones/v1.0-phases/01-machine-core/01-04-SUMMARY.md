---
phase: 01-machine-core
plan: 04
subsystem: identity+parts
tags: [rfc8785, jcs, config_hash, instance-identity, part-registry, d-04, d-13]

# Dependency graph
requires:
  - phase: 01-machine-core
    provides: "01-02's tracer slice — identity/{canon,env,instance}.py and parts/{schema,registry}.py in minimal, working form"
provides:
  - "identity/canon.py — config_hash hardened to CONTRACT §1's full rule set: int64-range exclusion (not just the installed rfc8785's narrower JS-safe-integer domain), int/float collapse, UTF-16 key ordering, no Unicode normalisation, absent-vs-empty config distinguished"
  - "identity/env.py — Nix-store-path assertion on the collection path; _collect_environment_payload() exposed uncached for testability"
  - "identity/instance.py — runtime_instance_hash() for planner-emitted plan nodes; hardened docstrings naming the node-id-is-never-an-identity guarantee"
  - "parts/schema.py — ArtifactScope (shared/quarantined/self_storage) and Part.artifact_scope"
  - "parts/registry.py — PartRegistry.register()/keys() (D-13); dispatch() with an explicit DeclarationOnlyPartError refusal; default_registry() returning exactly D-04's 7 Phase-1 entries"
  - "parts_core/ — 4 executable reference parts (passthrough, fake retriever, fake LLM caller, fixpoint body) plus 3 declaration-only Falsifier-2 wiring entries (declared_only.py), CapabilityScopedStores enforcing deny-by-default at the part boundary"
affects: ["01-05", "01-06", "01-07", "01-08", "01-09"]

actuals:
  tokens: 12931
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "int64-range walk-then-widen: this task's own walk enforces CONTRACT §1's signed-64-bit exclusion (raising CanonicalisationError with a JSON-Pointer path), then temporarily widens rfc8785==0.1.4's private domain constants (_rfc8785_impl._INT_MIN/_INT_MAX) for the duration of one canonicalise() call, since the installed library's own integer-serialisation path (str(int), exact for any magnitude) is more permissive than the guard it enforces by default — the guard is what's narrow (JS's Number.isSafeInteger, ±(2**53-1)), not the underlying algorithm"
    - "absent-vs-empty config: config_hash(None) omits the \"config\" payload key entirely; config_hash({}) includes it as an empty object — the two are pinned to hash differently, matching CONTRACT §1's never-normalise-the-input rule"
    - "CapabilityScopedStores: a thin wrapper (parts_core/__init__.py) gating store access by a part's own declared effects[], raising UndeclaredEffectError for anything not declared — deny-by-default enforced at the part boundary itself, demonstrated by test but not yet wired into the live runner path (see Deviations)"
    - "declaration-only Part: body=None marks an un-executable placeholder; registry.dispatch() refuses it by name (DeclarationOnlyPartError) rather than the pre-existing scheduler pattern of silently falling back to raw inputs"

key-files:
  created:
    - databasise/tests/identity/__init__.py
    - databasise/tests/identity/test_config_hash.py
    - databasise/tests/identity/test_instance_identity.py
    - databasise/parts_core/__init__.py
    - databasise/parts_core/passthrough.py
    - databasise/parts_core/fake_retriever.py
    - databasise/parts_core/fake_llm_caller.py
    - databasise/parts_core/fixpoint_body.py
    - databasise/parts_core/declared_only.py
    - databasise/tests/parts/__init__.py
    - databasise/tests/parts/test_reference_parts.py
    - databasise/tests/parts/test_registry.py
  modified:
    - databasise/identity/canon.py
    - databasise/identity/env.py
    - databasise/identity/instance.py
    - databasise/parts/schema.py
    - databasise/parts/registry.py
    - databasise/pyproject.toml

key-decisions:
  - "int64 vs rfc8785's default domain: the installed rfc8785==0.1.4 package enforces JavaScript's Number.isSafeInteger range (±(2**53-1)) as its default integer domain, not CONTRACT.md §1's signed-64-bit range. Read against the library's own source this session (rfc8785._impl.dump's int branch writes str(obj) exactly, losslessly, for any magnitude — the safe-integer check is a library-imposed guard, not a real precision limit of the algorithm). Resolved by (1) this module's own walk enforcing the CONTRACT-correct int64 boundary first, raising CanonicalisationError with a JSON-Pointer path, then (2) temporarily widening rfc8785's private _INT_MIN/_INT_MAX constants for the duration of the call so its own exact serialisation executes for the CONTRACT-legal range it would otherwise reject. Documented as a deviation from a bare rfc8785.dumps() call, not a change to JCS's canonical output for any value both accept."
  - "PartRegistry() (bare constructor) keeps plan 01-02's two tracer parts (core/passthrough@1.0.0, core/kv-writer@1.0.0) unchanged, since databasise/__init__.py's run_wiring() (out of this plan's scope) calls it bare and the tracer fixture depends on those two keys. default_registry() is a separate, fresh PartRegistry(seed_tracer_parts=False) holding exactly D-04's 7 Phase-1 entries — this is why the four parts_core parts use a distinct 'parts-core/' namespace rather than colliding with the tracer's 'core/' names."
  - "The three declaration-only Parts (declared_only.py) each represent one entire named MACH-01 wiring as a single coarse-grained registry stand-in (structural_depth + aggregate effects[] modeling that wiring's real capability surface), not yet decomposed into the real multi-node wirings Phase 3 will build — sufficient for Phase 2's static validator to compute depth/execution_mode over without waiting on the real port."

patterns-established:
  - "Fake LLM caller cache: routed through identity.instance.cache_partition_key against the run's real SqliteKVStore (not a simulated cache dict), so a second identical call is a genuine store-backed cache hit the runner can stamp — the same pattern a later plan's real LLM-calling parts will need."
  - "Fixpoint body: the executor (not the component) owns the halt condition, reporting which of exactly two termination reasons applied (halt_condition_met / max_rounds_reached) — the pattern any future real fixpoint part follows."

requirements-completed: []

coverage:
  - id: D1
    description: "Every CONTRACT §1 identity rule this task hardens (int64 exclusion, int/float collapse, UTF-16 key ordering, no Unicode normalisation, absent-vs-empty config, environment participation, environment content, max_concurrency participation) has one test each, all passing"
    requirement: "MACH-06"
    verification:
      - kind: unit
        ref: "databasise/tests/identity/test_config_hash.py (10 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Instance identity's structural invariants — fan-out never collapsed, dependency-order invariance, empty-dependency validity, cache-partition-key's exact four admitted members, the node-id/arm/run/mode signature prohibition, and the runtime-minted formula's four members — all hold"
    requirement: "MACH-06"
    verification:
      - kind: unit
        ref: "databasise/tests/identity/test_instance_identity.py (6 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "All four parts_core reference parts (passthrough, fake retriever, fake LLM caller, fixpoint body) behave per D-04's spec, including a genuine store-backed cache hit and deny-by-default reaching the part boundary itself"
    requirement: "MACH-06"
    verification:
      - kind: unit
        ref: "databasise/tests/parts/test_reference_parts.py (6 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The registry holds exactly 7 entries (4 executable + 3 declaration-only), unknown-key/duplicate-key refusals work, and dispatching a declaration-only part raises naming the part rather than silently no-opping"
    requirement: "MACH-06"
    verification:
      - kind: unit
        ref: "databasise/tests/parts/test_registry.py (5 tests)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Plan 01-02's tracer test still passes unchanged after this plan's identity hardening"
    requirement: "MACH-05, MACH-06, MACH-08, EMBED-01"
    verification:
      - kind: unit
        ref: "databasise/tests/test_tracer_end_to_end.py (7 tests, part of the 37-test full suite)"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-08-30
status: complete
---

# Phase 01 Plan 04: Identity Hardening + Reference Parts + Registry Summary

**config_hash now enforces CONTRACT §1's full int64/UTF-16/no-normalisation rule set (working around the installed rfc8785 package's narrower default integer domain), instance identity gained the runtime-minted formula, and D-04's four executable reference parts plus 3 declaration-only Falsifier-2 wiring entries now resolve through one explicit 7-entry registry — 37/37 tests green including the unmodified tracer.**

## Performance

- **Duration:** 55 min
- **Tasks:** 3
- **Files modified:** 18 (12 new, 6 modified)

## Accomplishments

- **Task 1 — Identity hardening (`identity/canon.py`, `env.py`, `instance.py`):** Implemented every CONTRACT §1 identity rule with a dedicated test: int64-range exclusion (working around the installed `rfc8785==0.1.4`'s narrower JS-safe-integer default domain — see Deviations), int/float collapse (already correct, verified), UTF-16 code-unit key ordering (pinned with a literal expected digest), no Unicode normalisation (NFC vs NFD), absent-vs-empty config distinguished (`config_hash(None) != config_hash({})`), environment participation, environment content (Nix-store-path assertion, version-change sensitivity, stability), and `max_concurrency` participation. Added `runtime_instance_hash()` for planner-emitted plan nodes per §1's runtime-minted formula. 16 new tests, all passing.
- **Task 2 — Four executable reference parts (`parts_core/`):** Shipped D-04's passthrough (zero-effect control), deterministic fake retriever (`reads_vector`, fixture corpus, no network), fake LLM caller (`calls_llm`, real `TokenAccounting` with 5 separate members, genuine store-backed cache hit via `cache_partition_key`), and fixpoint body (`kind="fixpoint"`, executor-owned bounded loop with two termination reasons). Added `CapabilityScopedStores` enforcing deny-by-default at the part boundary. Added `databasise.parts_core` to `pyproject.toml`'s setuptools packages list. 6 new tests, all passing.
- **Task 3 — Complete registry + 3 declaration-only entries (`parts/registry.py`, `parts_core/declared_only.py`):** Completed `PartRegistry` per D-13 (`register()`, `keys()`, `DuplicatePartError`), added `dispatch()` with an explicit `DeclarationOnlyPartError` refusal for a `body is None` Part, and `default_registry()` returning a fresh registry with exactly D-04's 7 Phase-1 entries (4 executable + 3 declaration-only). Added `ArtifactScope`/`Part.artifact_scope` to `parts/schema.py`. The 3 declaration-only entries cover MACH-01's named Falsifier-2 wirings: the decomposed lightrag-local query side, the opaque codebase-memory-mcp, and the half-decomposed full LightRAG (ingest side, `artifact_scope="quarantined"`). 5 new tests, all passing.
- Full suite: 37/37 tests pass (10 pre-existing tracer + 16 identity + 6 reference-parts + 5 registry). `ruff check` clean on every file this plan touched.

## Task Commits

1. **Task 1:** `872eb37` — feat(01-04): harden config_hash and instance identity per CONTRACT §1
2. **Task 2:** `9348f26` — feat(01-04): ship D-04's four executable parts_core reference parts
3. **Task 3:** `adcc1da` — feat(01-04): complete explicit part registry, add 3 declaration-only entries (D-13/D-04)

**Plan metadata:** (this commit) `docs(01-04): complete identity hardening + reference parts + registry plan`

## Files Created/Modified

- `databasise/identity/canon.py` — `config_hash` hardened; `_walk_int64_range()` (new); `INT64_MIN`/`INT64_MAX` widened onto `rfc8785`'s private domain constants for the duration of one call
- `databasise/identity/env.py` — `_assert_no_nix_store_path()`, `EnvironmentDigestError`, `_collect_environment_payload()` (new, uncached)
- `databasise/identity/instance.py` — `runtime_instance_hash()` (new); docstrings hardened
- `databasise/parts/schema.py` — `ArtifactScope` (new), `Part.artifact_scope` (new field)
- `databasise/parts/registry.py` — `PartRegistry.register()`/`.keys()` (new), `DuplicatePartError`, `DeclarationOnlyPartError`, `dispatch()` (new), `default_registry()` (new)
- `databasise/parts_core/__init__.py` — `PARTS` tuple, `CapabilityScopedStores`, `UndeclaredEffectError`
- `databasise/parts_core/passthrough.py` — `PASSTHROUGH_PART`
- `databasise/parts_core/fake_retriever.py` — `FAKE_RETRIEVER_PART`
- `databasise/parts_core/fake_llm_caller.py` — `FAKE_LLM_CALLER_PART`
- `databasise/parts_core/fixpoint_body.py` — `FIXPOINT_BODY_PART`
- `databasise/parts_core/declared_only.py` — `LIGHTRAG_QUERY_SIDE_PART`, `CODEBASE_MEMORY_MCP_PART`, `LIGHTRAG_FULL_INGEST_PART`, `DECLARED_ONLY_PARTS`
- `databasise/pyproject.toml` — added `"databasise.parts_core"` to the setuptools `packages` list
- `databasise/tests/identity/test_config_hash.py` — 10 tests (Tests 1-10)
- `databasise/tests/identity/test_instance_identity.py` — 6 tests (Tests 11-16)
- `databasise/tests/parts/test_reference_parts.py` — 6 tests
- `databasise/tests/parts/test_registry.py` — 5 tests

## Decisions Made

- **int64 vs rfc8785's default domain** — see key-decisions above; full reasoning in `identity/canon.py`'s module docstring.
- **`PartRegistry()` bare-constructor backward compatibility** — see key-decisions above; kept `databasise/__init__.py` (out of scope) and the tracer fixture working unchanged.
- **`parts-core/` naming namespace** for the four executable parts, distinct from the tracer's `core/` namespace, so `default_registry()`'s exactly-7-entries invariant never risks a silent key collision with `PartRegistry()`'s tracer defaults.
- **Declaration-only Parts as coarse wiring stand-ins** — see key-decisions above.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Installed `rfc8785==0.1.4` enforces a narrower integer domain than CONTRACT.md §1 requires**
- **Found during:** Task 1, writing Test 2 (int64 boundary)
- **Issue:** The pinned `rfc8785==0.1.4` package raises `IntegerDomainError` for any integer outside JavaScript's `Number.isSafeInteger` range (±(2**53-1)) — its own hard-coded default domain, confirmed by reading `rfc8785._impl.py`'s `_INT_MIN`/`_INT_MAX` constants and `dump()`'s int branch this session. CONTRACT.md §1 explicitly requires excluding only integers outside the *signed 64-bit* range (±(2**63-1)), a much wider domain the library's own serialisation algorithm can already handle exactly (`str(obj)`, lossless for any magnitude) — the safe-integer check is a guard the library chose to apply, not a precision limit of JCS's actual number-formatting algorithm for integers.
- **Fix:** `canon.py`'s `canonicalise()` now (1) walks the input itself first, raising `CanonicalisationError` with a JSON-Pointer path for anything outside int64, then (2) temporarily widens `rfc8785._impl`'s private `_INT_MIN`/`_INT_MAX` module attributes to int64 for the duration of the `rfc8785.dumps()` call (under a lock, restored in a `finally`), so the library's own exact serialisation path runs for the CONTRACT-legal range it would otherwise reject.
- **Files modified:** `databasise/identity/canon.py`
- **Verification:** `tests/identity/test_config_hash.py::test_2_int64_boundary_is_asserted_on_both_ends` — asserts the boundary and one step either side on both ends; full suite green.
- **Committed in:** `872eb37`
- **Risk noted:** this relies on `rfc8785._impl`'s private module attributes (the module's own docstring states it is "NOT a public API, and is not considered stable"). Since the package version is pinned exactly (`rfc8785==0.1.4`) and any shape change would raise `AttributeError` immediately and loudly at the patch site (not silently misbehave), this is judged an acceptable, well-contained, documented workaround rather than an architectural change — no `checkpoint:decision` was raised.

**2. [Rule 3 - Blocking] ruff import-sort and a false-positive SIM118 in the two new registry-adjacent test files**
- **Found during:** Task 3, post-implementation lint pass
- **Issue:** `ruff check` flagged unsorted imports (`I001`) in `test_reference_parts.py`/`test_registry.py`, and `SIM118` ("use `key in dict`") against `for key in registry.keys()` — a false positive, since `PartRegistry` is not a dict and defines no `__contains__`.
- **Fix:** `ruff check --fix` for the import sort; added a scoped `# noqa: SIM118` with an inline reason for the two genuine false positives.
- **Files modified:** `databasise/tests/parts/test_reference_parts.py`, `databasise/tests/parts/test_registry.py`
- **Verification:** `uv run ruff check` — all checks passed; full suite still green.
- **Committed in:** `adcc1da`

---

**Total deviations:** 2 auto-fixed (1 library-domain-mismatch bug fix, 1 blocking lint cleanup). No architectural decision was changed; no scope creep.

## Known Gaps (deferred, out of this plan's scope)

- **`runner/scheduler.py`'s node-dispatch call site still silently falls back to raw `inputs` for a `body is None` Part** (`output = await part.body(ctx) if part.body is not None else inputs`, pre-existing from plan 01-02). D-04's own requirement — "A body of `None` must make the part un-executable rather than silently no-op" — is satisfied by this plan's `registry.dispatch()` (exercised directly by `tests/parts/test_registry.py`), but wiring `dispatch()` into the actual runner call site requires editing `databasise/runner/scheduler.py`, which is out of this plan's scope (`runner/**` is owned by a sibling plan this wave, per the wave's parallel-execution boundary). **A later plan or the orchestrator should wire `registry.dispatch()` into `scheduler._run_node()`'s body-invocation line** so the real run path gets the same refusal this plan's tests already prove works.
- **`CapabilityScopedStores` (deny-by-default at the part boundary) is a standalone, tested mechanism (`parts_core/__init__.py`) but is not yet wired into the live runner's `NodeContext.stores` construction** (also `runner/scheduler.py`, out of scope). Currently `ctx.stores` stays a raw dict in the real run path; a later plan should wrap it per-node using each dispatched part's own declared `effects`.

## Known Stubs

- **The 3 declaration-only Parts in `parts_core/declared_only.py` (`body=None`) are intentional per D-04** — Phase 1 ships them as registry-only placeholders "so Phase 2 has a registry to compute over without waiting on Phase 3." This is the plan's explicit deliverable, not an unintended stub; Phase 3 is where each gets its real, executable port.

## Issues Encountered

None beyond the two deviations documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Identity is hardened to CONTRACT §1 in full, and the 7-entry explicit part registry (D-13) is in place with D-04's four executable reference parts proven against real store access. Plans 01-05 through 01-08 (validator hardening, Cozo/Faiss stores, budget metering, run-record completion) build on this without any open identity questions. The two known gaps above (wiring `dispatch()`/`CapabilityScopedStores` into `runner/scheduler.py`) are scoped to a later plan or the orchestrator, since `runner/**` was out of this plan's edit boundary this wave.

Note for the orchestrator: this plan's frontmatter lists `requirements: [MACH-06]`, which (per `.planning/phases/01-machine-core/01-CONTEXT.md`) is also listed by other plans in this phase; per this phase's shared context, do not mark it complete in `REQUIREMENTS.md` until its last contributing plan lands — the orchestrator closes it at phase end. `requirements-completed` above is left empty for the same reason.

---
*Phase: 01-machine-core*
*Completed: 2026-08-30*

## Self-Check: PASSED

All 18 claimed files found on disk; commits `872eb37`, `9348f26`, `adcc1da` confirmed in `git log --oneline --all`.
