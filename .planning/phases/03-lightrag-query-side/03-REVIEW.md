---
phase: 03-lightrag-query-side
reviewed: 2026-09-01T22:33:30Z
depth: standard
files_reviewed: 33
files_reviewed_list:
  - databasise/clients/base.py
  - databasise/clients/__init__.py
  - databasise/clients/openai_compat.py
  - databasise/evidence/falsifier2.py
  - databasise/evidence/parity_report.py
  - databasise/parity/build_corpus_fixture.py
  - databasise/parity/corpus.py
  - databasise/parity/import_index.py
  - databasise/parity/__init__.py
  - databasise/parity/run_arm.py
  - databasise/parity/run_comparison.py
  - databasise/parity/storage_audit.py
  - databasise/parity/v1_arm.py
  - databasise/parity/v1_driver_script.py
  - databasise/parts_core/declared_only.py
  - databasise/parts_core/lightrag/assemble.py
  - databasise/parts_core/lightrag/chunk_sel_kg.py
  - databasise/parts_core/lightrag/chunk_vector.py
  - databasise/parts_core/lightrag/embedder_index.py
  - databasise/parts_core/lightrag/embedder_query.py
  - databasise/parts_core/lightrag/entity_hydrate_expand.py
  - databasise/parts_core/lightrag/entity_lookup.py
  - databasise/parts_core/lightrag/generate.py
  - databasise/parts_core/lightrag/heading_backfill.py
  - databasise/parts_core/lightrag/__init__.py
  - databasise/parts_core/lightrag/join_roundrobin.py
  - databasise/parts_core/lightrag/keywords.py
  - databasise/parts_core/lightrag/relation_hydrate_expand.py
  - databasise/parts_core/lightrag/relation_lookup.py
  - databasise/parts_core/lightrag/rerank.py
  - databasise/parts_core/lightrag/truncator_token_budget.py
  - databasise/parts/registry.py
  - databasise/parts/schema.py
  - databasise/runner/scheduler.py
  - databasise/stores/graph.py
  - databasise/tools/check_import_boundary.py
  - databasise/wirings/resolve.py
  - v1/scripts/run_parity_ingest.py
findings:
  critical: 1
  warning: 3
  info: 1
  total: 5
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-09-01T22:33:30Z
**Depth:** standard
**Files Reviewed:** 33 source files (out of 98 listed paths; remainder were `.md`/`.json`/`.lock`/config/evidence excluded per scope)
**Status:** issues_found

## Summary

Reviewed the LightRAG query-side port: the fifteen registered `databasise/parts_core/lightrag/*`
component bodies, the structured-concurrency scheduler (`runner/scheduler.py`), the capability-scoped
client/store wrappers (`clients/`), the Cozo graph store port (`stores/graph.py`), the parity harness
(`parity/run_arm.py`, `parity/run_comparison.py`, `parity/import_index.py`, `parity/storage_audit.py`,
`parity/v1_arm.py`), the wiring resolver and the five arm patch documents, plus the registry/schema
and import-boundary tooling.

The part bodies themselves are careful, well-documented ports with explicit edge-case handling
(missing seeds reported rather than dropped, dedup provenance unioned rather than discarded, WEIGHT/
VECTOR fallback correctly gated). The scheduler's structured-concurrency and CR-01
(registry-effects-not-wiring-effects) discipline is consistently applied.

One real, reproducible **BLOCKER** was found in the parity comparison harness
(`databasise/parity/run_comparison.py`): the relation-id extraction used for the retrieval-level
diff assumes every merged relation item carries a `src_tgt` key, but the `join-relations` node's own
upstream producers emit two different shapes depending on which arm is resolved — this crashes with
`KeyError: 'src_tgt'` for the `global` arm deterministically, and with high likelihood for `hybrid`.
This path is untested (`test_retrieval_parity.py`'s environment-dependent group only exercises
`naive`), and the committed evidence JSONs for `global`/`hybrid` never got past the `inconclusive`
precondition gate, so the crash has never actually been observed in CI or evidence generation —
it will surface the first time someone runs a real `global`/`hybrid` comparison against a real
imported index.

Three WARNING-level robustness/quality issues and one INFO item are also recorded below.

## Critical Issues

### CR-01: `run_comparison.py`'s relation-id extraction crashes for `global` (always) and `hybrid` (in practice) arms

**File:** `databasise/parity/run_comparison.py:412-416`

**Issue:** `_extract_decomposed_ids` reads a decomposed run's final relation list off
`budget-relations` and builds each relation's comparison id with:

```python
relation_output = results.get(_RELATION_SOURCE_NODE_ID)
relation_ids = [
    f"{item['src_tgt'][0]}->{item['src_tgt'][1]}"
    for item in (relation_output or {}).get("items", [])
]
```

This assumes every item in `budget-relations`'s output carries a `src_tgt` key. But
`join-relations` (the node feeding `budget-relations`, see `databasise/wirings/lightrag/base.json`)
merges items from up to two producers with two *different* shapes:

- `entity-hydrate-expand` (`databasise/parts_core/lightrag/entity_hydrate_expand.py:67-74`) emits
  relations shaped `{"src_tgt": [a, b], ...}`.
- `relation-hydrate-expand` (`databasise/parts_core/lightrag/relation_hydrate_expand.py:57`) emits
  relations shaped `{"src_id": a, "tgt_id": b, ...}` — **no `src_tgt` key at all**.

`databasise/parts_core/lightrag/join_roundrobin.py`'s own `_relation_key` helper (lines 97-107)
explicitly handles both shapes for dedup purposes — the module docstring even calls this out as
"v1's own dual-shape dedup key" — so the merged, deduplicated list surviving into
`budget-relations["items"]` legitimately contains items of *either* shape, mixed together for the
`hybrid` arm and exclusively `src_id`/`tgt_id`-shaped for the `global` arm:

- `global` arm (`databasise/wirings/lightrag/arm-global.json-patch.json`): `join-relations.deps` is
  patched to `["relation-hydrate-expand"]` only — every surviving relation item lacks `src_tgt`.
  `_extract_decomposed_ids` raises `KeyError: 'src_tgt'` on **every** query for this arm.
- `hybrid` arm (unpatched `join-relations.deps` = `["entity-hydrate-expand",
  "relation-hydrate-expand"]`): any relation surviving dedup that originated purely from
  `relation-hydrate-expand` (i.e. an edge `entity-hydrate-expand`'s neighbour-expansion did not also
  find) triggers the same crash.
- `local` arm is safe: `join-relations.deps` is patched to `["entity-hydrate-expand"]` only, so every
  item has `src_tgt`.

This is unverified in the test suite: `databasise/tests/parity/test_retrieval_parity.py`'s
environment-dependent group only runs the `naive` arm end-to-end
(`test_real_naive_arm_comparison_runs_end_to_end_against_the_real_index`), and
`databasise/tests/parity/test_arm_conformance.py` only checks structural parsing/depth/blast-radius
for all five arms, never real execution with populated stores. The committed evidence
(`databasise/evidence/parity_results/global-comparison.json`,
`databasise/evidence/parity_results/hybrid-comparison.json`) never got past the index-identity
precondition (`status: "inconclusive"`, `"no imported v2 store found"`), so this code path has never
actually executed against real data — the crash is latent, not yet observed, but deterministic once
someone runs a real `global`/`hybrid` comparison (exactly the scenario `03-VALIDATION.md`/gate work
for this phase depends on).

Note `v1_driver_script.py:135` (the *original*-arm side of the same comparison) already uses the
correct dual-key-safe form implicitly (`f"{r['src_id']}->{r['tgt_id']}"`, since v1's own
`aquery_data` normalises to `src_id`/`tgt_id` before this script reads it) — confirming `src->tgt`
is the intended id format on both sides; only the decomposed-side extraction is shape-unsafe.

**Fix:**

```python
def _relation_comparison_id(item: dict[str, Any]) -> str:
    pair = item.get("src_tgt")
    if pair is None:
        pair = (item.get("src_id"), item.get("tgt_id"))
    return f"{pair[0]}->{pair[1]}"

relation_output = results.get(_RELATION_SOURCE_NODE_ID)
relation_ids = [
    _relation_comparison_id(item)
    for item in (relation_output or {}).get("items", [])
]
```

Add a regression test in `test_retrieval_parity.py`'s deterministic group feeding
`_extract_decomposed_ids` (or a renamed, testable helper) a `budget-relations` output mixing both
item shapes — the `hybrid`/`global` arms are exactly the case the current deterministic group never
constructs.

## Warnings

### WR-01: `CozoGraphStore._ensure_relations` swallows any exception whose message merely contains the word "relation"

**File:** `databasise/stores/graph.py:123-128`

**Issue:**

```python
try:
    self._client.run(script, {})
except Exception as exc:  # idempotent :create; only "already exists" is expected
    message = str(exc).lower()
    if "already exists" not in message and "relation" not in message:
        raise
```

The comment states only an "already exists" error is expected on a re-open (idempotent `:create`),
and that condition alone would already catch Cozo's real re-create message (which itself typically
reads "stored relation ... already exists"). The `"relation" not in message` clause widens the
suppression far beyond that: it also swallows any *other* exception whose text happens to mention
"relation" at all — a word that is extremely likely to appear in a wide range of genuine Cozo
errors for a graph store (a malformed schema on a version bump, a corrupted RocksDB file surfaced as
a relation-scoped error, a permissions or disk error during table creation, etc.). Since the
constructor calls `_ensure_relations()` unconditionally on every store open (`__init__` line 108), a
future genuine schema-creation failure could be silently absorbed here rather than surfacing as a
constructor exception, leaving the store instance appearing to construct successfully with missing
or partially-created relations.

**Fix:** Narrow the guard to the one condition the comment actually documents:

```python
except Exception as exc:  # idempotent :create; only "already exists" is expected
    if "already exists" not in str(exc).lower():
        raise
```

If a specific "already exists but phrased without that substring" Cozo message is the actual reason
the `"relation"` clause was added, name that exact observed message in the comment instead of a bare
substring that matches unrelated failures too.

### WR-02: `import_index.py` reaches into `FaissVectorStore`'s private attributes

**File:** `databasise/parity/import_index.py:305-314`

**Issue:** `_v2_vector_pairs` reads `store._entries` and `store._index` directly:

```python
store = FaissVectorStore(namespace=kind, workspace=workspace, store_root=store_root)
pairs = []
for doc_id, entry in store._entries.items():
    vec = store._index.reconstruct(entry["int_id"])
    pairs.append((doc_id, _quantized_vector_bytes(vec)))
```

This couples the verifier to `FaissVectorStore`'s internal representation across a module boundary
(`databasise/parity/` reaching into `databasise/stores/`'s private state). It works today, but any
future refactor of `FaissVectorStore`'s internal field names or storage shape (e.g. changing
`_entries`'s structure, renaming `_index`) silently breaks this verifier with no compile-time
signal and no test coverage pointing at the cause — the failure would surface as an unrelated
`AttributeError` deep in a parity comparison run, not at the store's own change site.

**Fix:** Add a small public accessor on `FaissVectorStore` (e.g. `iter_vectors() -> Iterator[tuple[str,
np.ndarray]]`) that the verifier calls instead of touching `_entries`/`_index` directly, keeping the
store's internal representation free to change without hunting down every private-attribute reader.

### WR-03: `run_wiring`'s failed/cancelled nodes in a batch never call `ts.done()`

**File:** `databasise/runner/scheduler.py:549-626`

**Issue:** In the per-batch dispatch loop, a node that fails (`node_id in node_failures`) or is
cancelled by the `TaskGroup` (`task.cancelled()`) is traced (or skipped) via `continue`, without
ever calling `ts.done(node_id)` on the `graphlib.TopologicalSorter`. Only the success path calls
`ts.done(node_id)` (line 618). This is currently harmless only because the very next statement after
the batch loop (`if node_failures or budget_halted: break`) unconditionally exits the `while
ts.is_active()` loop whenever any failure/cancellation occurred in that batch, so the sorter's
now-inconsistent internal state is never read again. This is correct by construction today, but it
is a latent trap: any future change that continues the loop past a partial batch failure (e.g. to
support "skip the failed subtree, keep scheduling independent branches") would immediately hit
`ts.is_active()`/`ts.get_ready()` operating on a sorter that thinks a completed-or-abandoned node is
still pending, likely deadlocking or raising from `graphlib`.

**Fix:** Either call `ts.done(node_id)` unconditionally for every node in `ready` regardless of
outcome (cancelled/failed/succeeded) right after the batch resolves, or add a comment at the
`break` site making the invariant ("the sorter is only ever read again if no failure occurred in
this batch") explicit so a future change to that control flow does not silently violate it.

## Info

### IN-01: `_load_env_file` is duplicated verbatim between `run_arm.py` and `v1_arm.py`

**File:** `databasise/parity/run_arm.py:74-93`, `databasise/parity/v1_arm.py:98-116`

**Issue:** The `.env.parity` KEY=VALUE parser is byte-for-byte identical in both modules (the
comment in `v1_arm.py` explains this is deliberate — "each caller's own dependency surface stays
obvious rather than reaching into a sibling module's private helper"). That's a reasonable
house-style call for a ~15-line stdlib parser, but the two copies have already drifted slightly in
behavior: `run_arm._load_env_file` raises `MissingParityEnvError` when the file is absent, while
`v1_arm._load_env_file` silently returns `{}` for the same condition. If this divergence is
intentional (the `v1_arm` caller falls back to plain `os.environ`), it's worth a one-line comment
noting the asymmetry is deliberate, since a future edit to either copy could easily "fix" it into a
regression in the other file, believing it is restoring consistency between two copies that were
supposed to be identical.

**Fix:** Add a short comment at each definition cross-referencing the sibling copy and stating the
absent-file behavior differs on purpose.

---

_Reviewed: 2026-09-01T22:33:30Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
