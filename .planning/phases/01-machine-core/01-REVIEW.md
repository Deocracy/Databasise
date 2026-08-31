---
phase: 01-machine-core
reviewed: 2026-08-30T00:00:00Z
depth: standard
files_reviewed: 71
files_reviewed_list:
  - databasise/README.md
  - databasise/__init__.py
  - databasise/identity/__init__.py
  - databasise/identity/canon.py
  - databasise/identity/env.py
  - databasise/identity/instance.py
  - databasise/ledger/__init__.py
  - databasise/ledger/ledger.py
  - databasise/namespaces.py
  - databasise/parts/__init__.py
  - databasise/parts/registry.py
  - databasise/parts/schema.py
  - databasise/parts_core/__init__.py
  - databasise/parts_core/declared_only.py
  - databasise/parts_core/fake_llm_caller.py
  - databasise/parts_core/fake_retriever.py
  - databasise/parts_core/fixpoint_body.py
  - databasise/parts_core/passthrough.py
  - databasise/pyproject.toml
  - databasise/registry_artifact/__init__.py
  - databasise/registry_artifact/index.py
  - databasise/registry_artifact/write_path.py
  - databasise/runner/__init__.py
  - databasise/runner/budget.py
  - databasise/runner/guards.py
  - databasise/runner/scheduler.py
  - databasise/runner/trace.py
  - databasise/stores/__init__.py
  - databasise/stores/base.py
  - databasise/stores/blob.py
  - databasise/stores/graph.py
  - databasise/stores/kv.py
  - databasise/stores/lexical.py
  - databasise/stores/vector.py
  - databasise/tests/conftest.py
  - databasise/tests/fixtures/wiring-tracer.json
  - databasise/tests/identity/test_config_hash.py
  - databasise/tests/identity/test_instance_identity.py
  - databasise/tests/ledger/test_ledger.py
  - databasise/tests/parts/test_reference_parts.py
  - databasise/tests/parts/test_registry.py
  - databasise/tests/registry_artifact/test_index.py
  - databasise/tests/registry_artifact/test_write_path_blast_radius.py
  - databasise/tests/runner/test_budget.py
  - databasise/tests/runner/test_run_record.py
  - databasise/tests/runner/test_scheduler.py
  - databasise/tests/stores/test_blob.py
  - databasise/tests/stores/test_graph.py
  - databasise/tests/stores/test_graph_frozen_bugs.py
  - databasise/tests/stores/test_kv.py
  - databasise/tests/stores/test_lexical.py
  - databasise/tests/stores/test_namespace_derivation.py
  - databasise/tests/stores/test_vector.py
  - databasise/tests/test_conftest_fixtures.py
  - databasise/tests/test_embed_startup.py
  - databasise/tests/test_import_boundary.py
  - databasise/tests/test_phase_success_criteria.py
  - databasise/tests/test_tracer_end_to_end.py
  - databasise/tests/validator/test_blast_radius.py
  - databasise/tests/validator/test_cycles_and_depth.py
  - databasise/tests/validator/test_execution_mode.py
  - databasise/tests/validator/test_taint_conformance.py
  - databasise/tools/__init__.py
  - databasise/tools/check_import_boundary.py
  - databasise/validator/__init__.py
  - databasise/validator/blast_radius.py
  - databasise/validator/cycles.py
  - databasise/validator/depth.py
  - databasise/validator/errors.py
  - databasise/validator/execution_mode.py
  - databasise/validator/parse.py
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 01-machine-core: Code Review Report

**Reviewed:** 2026-08-30T00:00:00Z
**Depth:** standard
**Files Reviewed:** 71
**Status:** issues_found

## Summary

This phase implements the machine core: identity/canonicalisation, the part registry, the
validator (parse, cycle-safe depth, blast-radius, execution-mode), the structured-concurrency
runner, the five store adapters, the artifact registry/write-path, and the append-only ledger.
The code is unusually well-documented — nearly every module docstring names the contract clause,
decision id, or known gap it implements, and the test suite (spike-005 taint conformance, frozen
Cozo-bug regressions, budget/guard unit tests, EMBED-01 process-isolation smoke tests) is broad
and mostly exercises real behavior rather than mocks.

The one finding that matters most (CR-01) is structural: the runner's deny-by-default
enforcement — `execution_mode` derivation, the capability-scoped store view, and the
blast-radius rule — is driven by the **wiring document's self-declared** `effects[]`/`kind`
(`WiringNode.effects`, `WiringNode.kind`) rather than by the **registry's own declared**
`Part.effects`/`Part.kind`. Since a wiring document is explicitly treated elsewhere in this
codebase as untrusted, author-supplied data (see `validator/cycles.py`'s own "a hostile or
merely large wiring could declare..." framing), this lets a wiring under-declare a node's
effects and silently bypass both containment placement and the blast-radius refusal — the exact
property Falsifier 2 (this phase's gate) is meant to prove. Everything else found is a
narrower robustness/consistency gap (a non-atomic two-file commit, blocking I/O inside the
async event loop, a silent `None` instead of a named refusal, an uncaught `ValueError` on
malformed config) rather than a wrong-answer bug in the algorithms themselves (Tarjan SCC,
JCS canonicalisation, budget split arithmetic, and the honesty-invariant run record all read as
correct and are well covered by their own test suites).

## Critical Issues

### CR-01: Deny-by-default containment and blast-radius checks trust the wiring's self-declared effects/kind, not the registry's

**File:** `databasise/runner/scheduler.py:227` (also `:240`), `databasise/validator/blast_radius.py:48`
**Issue:**

`_run_node` derives the node's containment placement from the **wiring node's own** declared
fields, not from the resolved `Part`:

```python
node = parsed.nodes[node_id]
part = parsed.parts[node_id]

execution_mode = derive_execution_mode(node.effects, node.kind)   # WiringNode.effects / .kind
...
scoped_stores = _ScopedStoresView(CapabilityScopedStores(stores, node.effects), node.effects)
```

and `blast_radius_violations` gates its whole rule on the same wiring-declared field:

```python
for node_id, node in parsed.nodes.items():
    if "writes_artifact" not in node.effects:   # WiringNode.effects, not part.effects
        continue
```

`parse_wiring` (`databasise/validator/parse.py`) never cross-checks `WiringNode.effects`/`.kind`
against the resolved `Part.effects`/`.kind` — the only effects-related check it performs is that
each declared effect is one of the 17 `Literal` members (a pydantic-enforced vocabulary check,
not a Part-consistency check). `WiringNode.effects` defaults to `[]` when omitted
(`databasise/parts/schema.py:131`).

Consequence: a wiring author (or a hostile/buggy wiring generator — this project's own
`validator/cycles.py` docstring already treats a wiring document as adversarial input) can
register a component whose registered `Part` performs `calls_llm`/`net`/`fs`/`writes_artifact`,
then wire a node for that component while omitting (or under-declaring) `effects` on the
`WiringNode` itself. The result:

- `derive_execution_mode([], kind)` returns `"in-process"` instead of the placement the Part's
  real capabilities would require — CONTRACT §3's containment rule ("only pure, non-iterative
  nodes MAY be hosted in-process") is bypassed entirely, silently, at the one enforcement point
  D-08 built.
- `blast_radius_violations` never even inspects the node, because
  `"writes_artifact" not in node.effects` short-circuits — a shared-scope write from an
  opaque-depth Part evades CONTRACT §3's blast-radius refusal completely, with no violation, no
  exception, no trace of the bypass.

The direct unit tests for these mechanisms (`tests/parts/test_reference_parts.py`,
`tests/parts_core`) pass `Part.effects` directly into `CapabilityScopedStores`, so they exercise
correct behavior; only the live scheduler path (`runner/scheduler.py`) has this substitution, so
the gap is easy to miss by reading the unit tests alone. `tests/test_phase_success_criteria.py`'s
criterion-4 fixture even hand-tunes `WiringNode.kind="stage"` against `Part.structural_depth=
"opaque"` "deliberately" to route around the placement refusal (line ~335-339) — that comment
documents *routing around* the D-08 refusal for test-fixture convenience, but nowhere documents
that the containment/blast-radius decision itself is sourced from the untrusted field rather than
the trusted one.

**Fix:** Derive `execution_mode`, the capability-scoped store view, and the blast-radius
predicate from `parsed.parts[node_id].effects` / `.kind` (the registry's own declaration), not
from `parsed.nodes[node_id].effects` / `.kind`. If a wiring is intentionally allowed to declare a
*narrower* set (e.g., to prove it only exercises a subset of what the Part is capable of), add an
explicit `parse_wiring` check that `set(node.effects) <= set(part.effects)` (or that the two are
equal) and accumulate a violation otherwise — never silently let the wiring's claim override the
registry's. Example sketch for `scheduler.py`:

```python
execution_mode = derive_execution_mode(part.effects, part.kind)
...
scoped_stores = _ScopedStoresView(CapabilityScopedStores(stores, part.effects), part.effects)
```

and for `blast_radius.py`:

```python
part = parsed.parts[node_id]
if "writes_artifact" not in part.effects:
    continue
```

## Warnings

### WR-01: `CapabilityScopedStores.require()` returns `None` instead of refusing when a declared effect's backing store isn't wired

**File:** `databasise/parts_core/__init__.py:42-46`
**Issue:** `require()` correctly raises `UndeclaredEffectError` when the effect itself isn't
declared, but when the effect *is* declared and the corresponding store key is simply absent
from the run's `stores` dict, it falls through to `self._raw_stores.get(store_key)`, which
returns `None` rather than raising:

```python
def require(self, effect: Effect) -> Any:
    if effect not in self._declared_effects:
        raise UndeclaredEffectError(effect, self._declared_effects)
    store_key = effect.split("_", 1)[-1]
    return self._raw_stores.get(store_key)
```

`databasise/__init__.py`'s composer currently wires only `"kv"` into `stores` (documented
elsewhere as a "Known Gap"), so any node declaring `reads_vector`/`reads_graph`/`writes_lexical`/
etc. gets a silent `None` back from `ctx.stores[...]` instead of a named error, and the part body
fails downstream with a confusing `AttributeError: 'NoneType' object has no attribute '...'`
instead of an actionable message. This directly contradicts the "refusals over silent fallbacks"
house style stated repeatedly elsewhere in this codebase (e.g. `stores/lexical.py`'s FTS5
availability check, `stores/vector.py`'s faiss-import guard).
**Fix:** Use `self._raw_stores[store_key]` (raise `KeyError`) or raise a purpose-built
`StoreNotWiredError(effect, store_key)` naming both the effect and the missing store key.

### WR-02: `FaissVectorStore._persist`'s two-file commit is not atomic as a pair

**File:** `databasise/stores/vector.py:208-231`
**Issue:** The module docstring and method docstring both claim "the index and sidecar commit
together or neither does," but the two commits are two separate `os.replace` calls with no shared
transaction:

```python
os.replace(tmp_index, self._index_path)
os.replace(tmp_meta, self._meta_path)
```

The `try/except` above only guards the *write-to-temp-file* phase (and does clean up temp files
on a Python exception there); it does not cover the window between the two `os.replace` calls. A
process crash (SIGKILL, power loss) landing exactly between them leaves the *new* index file
paired with the *old* metadata sidecar — a real inconsistency (new int_ids present in the index
with no corresponding `entries` row), not merely a hypothetical one, and outside what the existing
test (`test_index_and_sidecar_commit_together_or_neither`, which only forces a failure during the
temp-file write) exercises.
**Fix:** Either (a) reorder so the file whose staleness is safer to read from an old committed
pair is renamed last and document which one that is, or (b) fold both files' commit into a single
rename of a per-flush staging directory (git's own two-level object-store pattern already used by
`stores/blob.py` composes cleanly with a "swap one symlink/dir" scheme), or (c) add a checksum/
generation field to the sidecar that's cross-validated against the index at open time so a
half-committed pair is detected and refused at the next `__init__` rather than silently used.

### WR-03: Blocking, synchronous I/O runs directly inside `async def` store methods, inconsistent with the Cozo adapter's own stated rationale

**File:** `databasise/stores/kv.py:87-100`, `databasise/stores/lexical.py:94-108`,
`databasise/stores/vector.py:178-231`, `databasise/ledger/ledger.py:127-158`,
`databasise/registry_artifact/index.py:216-269`
**Issue:** `stores/graph.py`'s own docstring explains its `run_in_executor` dispatch exists
specifically "so it never blocks the runner's event loop — plan 01-08's structured-concurrency
plan depends on this." The KV, lexical, and artifact-registry stores instead call `sqlite3`
methods synchronously inline inside `async def` bodies, and `FaissVectorStore.index_done_callback`
/`_persist` run `np.vstack`, `faiss.add_with_ids`, and `faiss.write_index` synchronously inline
too. Under `runner/scheduler.py`'s `asyncio.TaskGroup`-based batch dispatch, several nodes are
genuinely scheduled concurrently in the same event loop; a slow synchronous write in one node's
body (a large KV flush, a large Faiss index write) stalls every sibling task in that batch —
directly working against D-11's own stated design goal, quoted in `scheduler.py`'s own docstring:
"one arm's fan-out must never throttle an unrelated arm beside it."
**Fix:** Either dispatch the synchronous calls via `loop.run_in_executor(None, ...)` the same way
`stores/graph.py` does, or explicitly document (as `stores/graph.py` does) why the other four
stores are exempt from the same concern — SQLite writes under WAL are typically fast, but this
should be a stated, deliberate exception rather than an unstated inconsistency, especially for
`FaissVectorStore`'s flush, which is not obviously cheap at scale.

### WR-04: `max_concurrency` validation raises an uncaught `ValueError` for non-numeric config instead of the documented refusal

**File:** `databasise/runner/scheduler.py:205-214`
**Issue:**

```python
def _validated_max_concurrency(node_id: str, config: dict[str, Any] | None) -> int:
    max_concurrency = 1
    if config:
        max_concurrency = int(config.get("max_concurrency", 1))
    if max_concurrency < 1:
        raise InvalidMaxConcurrencyError(node_id, max_concurrency)
    return max_concurrency
```

`int(config.get("max_concurrency", 1))` is not guarded: a wiring declaring
`"max_concurrency": "not-a-number"` (or a list/dict) raises a bare `ValueError` from `int(...)`
rather than the module's own `InvalidMaxConcurrencyError`, breaking this module's own documented
"refused at validation, before any node is dispatched, naming the offending node id" contract for
that class of malformed input.
**Fix:** Wrap the coercion and re-raise as `InvalidMaxConcurrencyError(node_id, value)`:

```python
raw = config.get("max_concurrency", 1)
try:
    max_concurrency = int(raw)
except (TypeError, ValueError):
    raise InvalidMaxConcurrencyError(node_id, raw) from None
```

## Info

### IN-01: `runner/budget.py`/`runner/guards.py` are fully built and tested but not wired into the live scheduler path

**File:** `databasise/runner/scheduler.py:380-390`
**Issue:** Every successfully-completed node's trace hardcodes `budget_state="within_budget"`,
`realised_budget_share=1.0`, and `guards_fired=[]` regardless of the part's real token spend or
any declared guard — `runner/budget.py`'s `meter()` and `runner/guards.py`'s `evaluate_guards()`
are never called from `scheduler.py`. This is called out in the code's own inline comments as a
"Known Gap," so it isn't hidden, but `tests/test_phase_success_criteria.py`'s criterion-2 test
only asserts the field is present and in `[0, 1]` — it cannot and does not prove metered spend is
real, which is easy to miss when reading that test in isolation as "budget metering is covered."
**Fix:** No action required for this phase if intentionally deferred; consider a one-line note in
that test's docstring making the "field present, not yet metered" distinction explicit so a
future reader doesn't mistake presence-checking for metering coverage.

### IN-02: `LedgerRecord` never surfaces the `id`/`created_at` columns it stores

**File:** `databasise/ledger/ledger.py:34-53`, `:118-125`
**Issue:** The `ledger` table stores `id` (the monotonic append order) and `created_at`, but
`LedgerRecord`'s dataclass fields don't include either, and `_row_to_record` only ever populates
fields present in `LedgerRecord.__dataclass_fields__`. `append()` returns the raw `id` as an
`int` at call time, but `active_pointer()`/`history()` — the two read paths — never expose it or
`created_at` at all, so a caller reading the ledger back later has no way to recover append order
or timestamp without a second, ad hoc SQL query.
**Fix:** Add `id: int` and `created_at: str` to `LedgerRecord` (or a wrapping read-model type) so
`history()`/`active_pointer()` round-trip everything the table actually stores.

### IN-03: `fixpoint_body`'s zero-round edge case reports `"max_rounds_reached"` for a config that never ran a round

**File:** `databasise/parts_core/fixpoint_body.py:23-39`
**Issue:** `max_rounds = int(config.get("max_rounds", _DEFAULT_MAX_ROUNDS))` has no floor check;
for `max_rounds<=0` the `while rounds_run < max_rounds` loop body never executes, so the part
returns `{"rounds_run": 0, "halted_on": "max_rounds_reached"}` — a misleading label for "no round
ever ran" rather than "the round bound was hit." Untested (no test exercises `max_rounds<=0`).
**Fix:** Either reject `max_rounds < 1` explicitly (mirroring `scheduler.py`'s own
`InvalidMaxConcurrencyError` pattern for `max_concurrency`), or special-case
`halted_on = "zero_max_rounds"` when `rounds_run == 0`.

---

_Reviewed: 2026-08-30T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
