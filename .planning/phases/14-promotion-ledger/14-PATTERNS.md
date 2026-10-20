# Phase 14: Promotion & Ledger - Pattern Map

**Mapped:** 2026-10-20
**Files analyzed:** 46 new/modified (production 17, docs/evidence 7, tests 22). Source is 14-RESEARCH.md §9 (plan split 14-01..14-09) and §6 (test inventory), plus 14-VALIDATION.md (same 19 test paths).
**Analogs found:** all in-repo. Every change extends an existing mechanism. Paths are relative to `databasise/` unless they start with `docs/` or `.planning/`. Every excerpted analog is git-tracked source (confirmed with `git ls-files` for the fixtures dir, `wirings/codebase-memory-mcp.json` and `evidence/F-07-MUTABLE-STORE-DISPOSITION.md`; the rest are tracked modules read at HEAD 2a16376). No protected `test_ref` file was read, grepped or diffed. Lines cited for `tests/seam/test_refusal_reachability.py` (protected, WIRE-17) come from 14-RESEARCH.md only.

## File Classification

| New/Modified File | Plan | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|---|
| `ledger/ledger.py` (`LedgerEntry`, `close`/`__enter__`/`__exit__`, `open_existing`, `lineage`, `history_for_alias`, `_row_to_record(cls=)`, docstrings) | 14-01 | model + store | CRUD (sqlite) | same file: `LedgerRecord` (:99-122), `transaction()` (:175-202), `_row_to_record` (:281-288), `generation_state`/`history` (:362-384) | exact (self) |
| `seam/refusals.py` (`PartialRunEvidenceError`, `GateNotCalibratedError`, `__all__`, docstrings :167-171, :494-496, :671-687) | 14-02 / 14-07 / 14-09 | model (refusal) | request-response | `DisagreeingPromotionTraceIdsError` (:526-540), `GateVerbNotBuiltError` (:580-592) | exact |
| `tests/seam/test_rest_transport.py` (`_REFUSAL_FACTORIES` + import list) | 14-02 | test | request-response | same dict (:418-493), imports (:43-90) | exact (self) |
| `wirings/resolve.py` (`wiring_for_name`, `__all__`, docstrings) | 14-02 | utility | transform | `all_wirings` (:201-219), `load_wiring` (:134-150) | exact (self) |
| `seam/selectors.py` (`_resolve_alias`, import :99, docstrings) | 14-05 | service | request-response | same function (:277-301) | exact (self) |
| `seam/promotion.py` (`refuse_partial_evidence`, arm_id-first `resolve_single_arm`, docstring :7-18) | 14-07 | service (pure) | transform | `resolve_single_arm` (:160-184), `resolved_wiring_for_arm` (:144-157) | exact (self) |
| `seam/engine.py` (promote top, `_resolve_operator_preconditions`, three verb closures, `_corpus_wiring`, class docstring) | 14-04 / 14-06 / 14-07 / 14-08 | service | request-response | same file (:2265-2434, :2630-2690, :685-698, :306-315) | exact (self) |
| `seam/rest.py` `TraceRequest`, `mcp/tools.py` `ResolveToolArgs` (`StrictBool`) | 14-04 | DTO | request-response | `rest.py:182-215`, `tools.py:96-101,192-200` | exact (self) |
| `parts_core/declared_only.py` (drop cbm from `DECLARED_ONLY_PARTS`) | 14-06 | config (registry data) | - | same tuple (:132-135) | exact (self) |
| `evidence/falsifier2.py` (`probe_registry` + cbm, `_parse` uses it) | 14-06 | utility (evidence registry) | transform | `probe_registry` (:132-142), `evaluate_probe` (:287-292) | exact (self) |
| `evidence/f07_report.py` + regenerated `evidence/F-07-MUTABLE-STORE-DISPOSITION.md` | 14-06 | renderer | transform | `_CATALOGUED_NOT_BUILT` (:91-122), `_live_mutates_store_rows` (:125-153) | exact (self) |
| `tests/fixtures/codebase-memory-mcp.json` (moved from `wirings/`) | 14-06 | fixture | file-I/O | `tests/fixtures/codebase_memory_mcp_raw_items.json` (sibling home) | role-match |
| `parts/registry.py`, `parts/schema.py` docstrings | 14-06 | docs-in-code | - | `default_registry` (:209-227) | exact (self) |
| `docs/gui/API-INVENTORY.md`, `evidence/PROMOTION-LEDGER-EVIDENCE.md`, `evidence/ADMISSION-CODEBASE-MEMORY-MCP.md`, `docs/gui/CODEBASE-MAP.md`, `pyproject.toml` comment | 14-04/06/07/09 | doc | - | research §8 table and Pitfalls 5, 18 | n/a (text edits) |
| `tests/ledger/test_ledger_history.py`, `tests/ledger/test_ledger_store_api.py`, `tests/ledger/test_ledger_lifecycle.py` | 14-01 / 14-08 | test | CRUD | `tests/ledger/test_ledger.py` (:1-60) | exact |
| `tests/wirings/test_wiring_for_name.py` | 14-02 | test | transform | `all_wirings` contract; `tests/seam/test_operator_verb_concurrency.py` `_seed_trace` (:44-54) for the `all_wirings()` iteration idiom | role-match |
| `tests/seam/test_capability_effects.py`, `tests/validator/test_node_kind.py` | 14-03 | test | transform | research §5.1/§5.2 (import-at-old-commit rules) | role-match |
| `tests/seam/test_debug_strict_boolean.py`, `tests/mcp/test_debug_strict_boolean.py` | 14-04 | test | request-response | `test_rest_transport.py` (:132-142, :344-356); `tests/mcp/test_tool_growth_invariant.py` (:21-33, :87-88) | exact |
| `tests/seam/test_alias_resolution.py` | 14-05 | test | request-response | `test_rest_transport.py` stub clients (:96-129) + `create_app` (:132-142) | exact |
| `tests/parts/test_registry_reachability.py`, `tests/seam/test_corpus_wiring.py` | 14-06 | test | transform | `tests/parts/test_registry.py` (:1-20); research Code Examples | role-match |
| `tests/seam/test_partial_run_evidence.py`, `test_promote_refuses_partial.py`, `test_operator_alias_validation.py`, new LEDG-08 node in `test_promotion_posture.py` | 14-07 | test | request-response | `tests/seam/test_promotion_posture.py` (:1-56) | exact |
| `tests/seam/test_retire_lineage.py` | 14-08 | test | CRUD | `tests/seam/test_operator_verb_concurrency.py` (:1-75) | exact |
| Edits to unprotected `test_query_object.py`, `test_operator_verb_concurrency.py`, `test_mutable_store_exclusion.py`, `test_codebase_memory_mcp_admission.py`, `test_registry.py`, `test_falsifier2_evidence.py`, `test_alias_registry.py` | 14-05/06/08 | test | - | research §6.1 lines | exact (self) |
| `tests/test_docstring_currency.py` | 14-09 | test | transform | research §8 banned-substring list | no direct analog |
| Protected `tests/seam/test_refusal_reachability.py` (owner grant only) | 14-06 task 1 | test | - | exact edit in research §6.4 | n/a |

## Pattern Assignments

### `seam/refusals.py` new refusals (model, request-response)

**Analog for `PartialRunEvidenceError(*, trace_ids)`:** `DisagreeingPromotionTraceIdsError` (refusals.py:526-540). Same public attribute, same "names only the caller's own trace_ids" rule:
```python
class DisagreeingPromotionTraceIdsError(SeamRefusalError):
    """Raised by ``databasise.seam.promotion.resolve_single_arm`` (07-01-PLAN.md, D-04) when the
    supplied trace ids resolve to more than one distinct wiring ... Names only the caller's own
    ``trace_ids`` — never the resolved arm names, per this module's own no-enumeration house style.
    """

    def __init__(self, *, trace_ids: list[str]):
        self.trace_ids = list(trace_ids)
        super().__init__(
            "DisagreeingPromotionTraceIdsError: trace ids "
            f"{self.trace_ids!r} resolve to more than one distinct wiring; a promotion target "
            "must be named by trace ids that all agree on exactly one"
        )
```
Message must name no arm, node id or mutation class (D-02, §18.3). Message form `"PartialRunEvidenceError: trace ids [...] ..."`.

**Analog for `GateNotCalibratedError(*, verb)`:** `GateVerbNotBuiltError` (refusals.py:580-592):
```python
    def __init__(self, *, verb: str):
        self.verb = verb
        super().__init__(f"GateVerbNotBuiltError: verb {verb!r} is not built in this milestone")
```
Only public attribute `verb`. No `mutation_class` (contrast `MeasurementPostureRefusalError` :595-611, which carries it; D-04 says the refusal is identical for every arm). Do not quote the floor value.

**Catalogue:** append both names to `__all__` (refusals.py:940-990, keyword-quoted one per line). Both default to 422 because `rest._status_for` (rest.py:149-154) returns 404 only for `_NOT_FOUND_REFUSALS` (rest.py:123). Do not add them there.

**Docstring edits:** `InvalidPromotionAliasError` (:167-171) "Raised by ``Databasise.promote``" -> all three verbs (D-07). `ActiveGenerationRetirementError` (:671-687) "``Ledger.by_alias(alias).minted_version == version``" -> lineage (D-06). `MutableStoreComparisonExcludedError` (:475-506, sentence at :494-496) must keep the word `unreachable` (SEAM-16).

---

### `tests/seam/test_rest_transport.py::_REFUSAL_FACTORIES` (test)

**Analog:** same dict (:418-493). One-line keyword lambdas keyed by class:
```python
    DisagreeingPromotionTraceIdsError: lambda: DisagreeingPromotionTraceIdsError(
        trace_ids=["trace-1", "trace-2"]
    ),
    GateVerbNotBuiltError: lambda: GateVerbNotBuiltError(verb="check"),
```
Add `PartialRunEvidenceError: lambda: PartialRunEvidenceError(trace_ids=["trace-1"])` and `GateNotCalibratedError: lambda: GateNotCalibratedError(verb="promote-next")`, plus both names in the `from databasise.seam.refusals import (...)` block (:43-90). Same plan as the classes (Pitfall 13: protected `test_refusal_status_codes.py` imports this dict and indexes it by every `__all__` class).

---

### `ledger/ledger.py` (model + store, sqlite CRUD)

**Projection type (D-09)** extends `LedgerRecord` (:99-122), a `@dataclass(frozen=True)` whose `promotion_provenance` has no default (pinned by `test_measurement_posture.py`):
```python
@dataclass(frozen=True)
class LedgerRecord:
    mutation_id: str
    ...
    record_kind: str
    alias: str | None = None
    minted_version: str | None = None
    targets_version: str | None = None
```
`LedgerEntry(LedgerRecord)` uses `@dataclass(frozen=True, kw_only=True)` with `id: int`, `created_at: str`.

**Row mapper to parameterise** (:281-288). Keep the one-positional call working (`test_rollback.py:56`):
```python
    def _row_to_record(self, row: sqlite3.Row) -> LedgerRecord:
        kwargs: dict[str, Any] = {}
        for field_name in LedgerRecord.__dataclass_fields__:
            value = row[field_name]
            if field_name in _JSON_FIELDS:
                value = json.loads(value)
            kwargs[field_name] = value
        return LedgerRecord(**kwargs)
```
Change to `def _row_to_record(self, row, cls=LedgerRecord)`, iterate `cls.__dataclass_fields__`, return `cls(**kwargs)`. `id` and `created_at` are table columns (:208, :229), so the same loop fills them.

**Query-method shape** for `history_for_alias` and `lineage`, copied from `history` (:378-384) and `generation_state` (:370-376):
```python
    def history(self, mutation_id: str) -> list[LedgerRecord]:
        """Every record for ``mutation_id``, oldest first."""
        cur = self._conn.execute(
            "SELECT * FROM ledger WHERE mutation_id = ? ORDER BY id ASC",
            (mutation_id,),
        )
        return [self._row_to_record(r) for r in cur.fetchall()]
```
`history_for_alias`: `WHERE alias = ? ORDER BY id ASC`, `cls=LedgerEntry`. `lineage`: use research Pattern 3 (`SELECT record_kind, targets_version ... WHERE alias = ? AND minted_version = ?`, visited list, stop at non-rollback). Do not walk via `generation_state` (it loops). Mark `history` docstring "test-only" (D-09).

**Construction / transaction style** (:137-143, :195-202). `open_existing` must call `cls(store_root)` so `_create_schema` (and the index migration :248-251) still runs:
```python
    def __init__(self, store_root: str | Path) -> None:
        db_path = Path(store_root) / "ledger.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._set_wal()
        self._create_schema()
    ...
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()
```
Add `close()` (`self._conn.close()`), `__enter__` returning `self`, `__exit__` calling `close()` and returning `None` (never swallows). `open_existing`: `if not (Path(store_root) / "ledger.db").is_file(): return None` then `return cls(store_root)`. Rewrite the `transaction()` docstring sentence at :183-187 so the word "stall" is gone (Pitfall 9). Docstring fixes at :17-21, :30-33, :48, :74-83, :344-347, :366-367 per research §8. The `ponytail:` comment style (:160-164, :189-193) is the house form for known limits.

---

### `wirings/resolve.py` `wiring_for_name` (utility, transform)

**Analog:** `all_wirings` (:201-219), which the new function must equal per name:
```python
    candidates: list[tuple[str, dict[str, Any]]] = [
        (name, resolve_arm(name)) for name in _ARM_NAMES
    ]
    for wiring_name in WIRING_NAMES:
        if wiring_name == "lightrag":
            continue
        candidates.append((wiring_name, load_wiring(wiring_name)))
```
New function (research Pattern 1): `_ARM_NAMES` -> `resolve_arm(name)`; `WIRING_NAMES` minus `"lightrag"` -> `load_wiring(name)`; else `None`. Never raises `UnknownArmError`. Add to `__all__` (:222-234). Module must not import `databasise.ledger` or seam refusals (Pitfall 6, circular import). Docstring fixes :1-17 and `load_base` :94-96 (remove "does not necessarily *parse* clean").

---

### `seam/selectors.py` `_resolve_alias` (alias resolution branch)

**Current** (:297-301):
```python
    ledger = Ledger(store_root)
    record = ledger.by_alias(alias)
    if record is None:
        raise UnsatisfiableSelectorError(selector_kind="alias", requested=alias)
    return resolve_arm(record.mutation_id)
```
**Target:** `ledger = Ledger.open_existing(store_root)`; None -> the same `UnsatisfiableSelectorError(selector_kind="alias", requested=alias)`; `with ledger: record = ledger.by_alias(alias)`; `resolved = wiring_for_name(record.mutation_id)`; None -> same refusal (names only the caller's alias, refusals.py:122-137). Import at :99 swaps `resolve_arm` for `wiring_for_name`; then update unprotected `test_query_object.py:50-57`, which patches `databasise.seam.selectors.resolve_arm` (Pitfall 3). Keep signature `_resolve_alias(alias, *, store_root)` (imported by four tests). Docstring :277-296 rewrite must keep `all_wirings()` in the module docstring and avoid `registry is empty`, `five arms`, `five Phase 3 arms`, `_ARM_NAMES` (SEAM-16).

---

### `seam/promotion.py` (pure service, transform)

**Arm resolution to change** (:174-184):
```python
    arm_names = {
        _arm_name_for_node_ids(
            _dispatched_node_ids(record), trace_reference=trace_ids[i] if i < len(trace_ids) else None
        )
        for i, record in enumerate(resolved_trace_records)
    }
    if len(arm_names) > 1:
        raise DisagreeingPromotionTraceIdsError(trace_ids=list(trace_ids))
    return next(iter(arm_names))
```
Replace the comprehension with a loop: `arm_id = record.get("arm_id")`; if `isinstance(arm_id, str) and wiring_for_name(arm_id) is not None` use it; else call `_arm_name_for_node_ids(...)` and, on `UnknownTraceReferenceError` with `record.get("partial")` truthy, raise `PartialRunEvidenceError(trace_ids=[that id])`. Keep `_arm_name_for_node_ids` (:126-141) unchanged (pinned by `test_hipporag_review_fixes.py:203-213`).

**New `refuse_partial_evidence`:** research Code Examples "Partial-evidence refusal". Uses `record.get("partial")` (seeded records carry no `partial` key, Pitfall 2). Add to `__all__` (:261-276). Import nothing from `databasise.ledger`.

**`resolved_wiring_for_arm` (:144-157)** ends in `raise AssertionError(...)`. Its row-derived callers move to `wiring_for_name` + `UnsatisfiableSelectorError(selector_kind="alias", requested=alias)` (D-05).

---

### `seam/engine.py` verb prologues (service, request-response)

**Promote top** (:2339-2348). Insert the gate refusal directly after the not-built check, and move the alias check out:
```python
        if verb not in PROMOTION_VERBS:
            raise UnrecognisedPromotionVerbError(verb=verb)

        if verb in _NOT_BUILT_VERBS:
            raise GateVerbNotBuiltError(verb=verb)

        # SEAM-12: an alias no Selector could carry would write a row nobody can select. ...
        if alias == "" or _INSTANCE_HASH_PATTERN.match(alias):
            raise InvalidPromotionAliasError(alias=alias)
```
New line: `if verb in _GATE_VERBS: raise GateNotCalibratedError(verb=verb)` (`_GATE_VERBS` is already imported, :255). Keep the in-closure `enforce_gate_verb_posture` (:2375-2376) and add a comment saying it is unreachable until TOOL-12.

**Shared prologue** (:2265-2298) gains `*, refuse_partial: bool = False`. Order: alias check (moved from :2347), change_origin (:2283), trace resolution (:2286), `refuse_partial_evidence(resolved_records, list(trace_ids))` when `refuse_partial`, then `resolve_single_arm` (:2287):
```python
        if change_origin not in CHANGE_ORIGINS:
            raise InvalidChangeOriginError(change_origin=change_origin)

        resolved_records = [self._trace_store.resolve(trace_id) for trace_id in trace_ids]
        arm_name = resolve_single_arm(resolved_records, alias=alias, trace_ids=list(trace_ids))
```
Callers: promote :2350 (passes `refuse_partial=True`), rollback :2485, retire :2626.

**Executor-thread closures** (`_promote_sync` :2355-2422, `_rollback_sync` ~:2490-2549, `_retire_sync` :2630-2678). Pattern to keep: the `Ledger` is opened, used and closed on the executor thread:
```python
            ledger = Ledger(self.store_root)

            with ledger.transaction():
                target = ledger.generation_state(alias, version)
                if target is None:
                    raise UnknownGenerationVersionError(alias=alias, version=version)
                if target.record_kind == RECORD_KIND_TOMBSTONE:
                    raise TombstonedGenerationError(alias=alias, version=version)

                active = ledger.by_alias(alias)
                if active is not None and active.minted_version == version:
                    raise ActiveGenerationRetirementError(alias=alias, version=version)
```
Changes: promote uses `with Ledger(self.store_root) as ledger, ledger.transaction():`. Rollback and retire use `ledger = Ledger.open_existing(self.store_root)`, raise `UnknownGenerationVersionError` on None, then `with ledger, ledger.transaction():` (research Pattern 2). Retire guard becomes `version in ledger.lineage(alias, active.minted_version)`. Rollback adds `any(generation_state(alias, v).record_kind == RECORD_KIND_TOMBSTONE for v in ledger.lineage(alias, version))` -> `TombstonedGenerationError` naming the requested version. Row-derived `resolved_wiring_for_arm` calls (:2368, :2504, :2508, :2649, :2651) become a helper that maps `wiring_for_name(...) is None` to `UnsatisfiableSelectorError(selector_kind="alias", requested=alias)`. The offload stays `await asyncio.get_running_loop().run_in_executor(None, _x_sync)` (:2424, :2551, :2680).

**`_corpus_wiring`** (:685-698). Current:
```python
    family = wiring_family(query_wiring)
    path = _WIRINGS_ROOT / family / f"corpus-{operation}.json"
    if not path.is_file():
        raise NoWritePathForModalityError(operation=operation)
    return json.loads(path.read_text(encoding="utf-8"))
```
Target: `try: return load_wiring(family, variant=f"corpus-{operation}") except FileNotFoundError: raise NoWritePathForModalityError(operation=operation) from None`. Add `load_wiring` to the import at :306; delete `_WIRINGS_ROOT` and its comment (:308-315).

**Class docstring** (~:1127): add the literal tenancy phrase chosen for the LEDG-09 doc check ("one store_root is one tenant").

---

### `seam/rest.py` and `mcp/tools.py` request models (StrictBool)

**REST DTO** (rest.py:182-215). Base is `ConfigDict(extra="forbid", frozen=True)`; DTOs carry no logic (AST proof in `test_rest_transport.py:200`):
```python
class TraceRequest(_RequestModel):
    trace_reference: str
    debug: bool = False
```
**MCP DTO** (tools.py:192-200), base `_ToolArgs` (:96-101) mirrors `_RequestModel`:
```python
class ResolveToolArgs(_ToolArgs):
    scope: ResolveScope
    evidence_ref: EvidenceRef | None = None
    trace_reference: str | None = None
    debug: bool = False
```
Change both to `debug: StrictBool = False` and extend the imports `from pydantic import BaseModel, ConfigDict, ValidationError` (rest.py:84) and `from pydantic import BaseModel, ConfigDict, Field` (tools.py:60) with `StrictBool`. No route or handler change. A non-refusal validation error keeps FastAPI's `{detail: [...]}` body and, on MCP, the SDK `Error executing tool ...` text, because `_find_refusal` (mcp/server.py:102-116) returns None for it.

---

### `evidence/falsifier2.py` probe registry (utility)

**Analog:** `probe_registry` (:132-142):
```python
def probe_registry() -> PartRegistry:
    """``default_registry()`` plus the two probe-only parts above, assembled fresh on every call.
    ...
    """
    registry = default_registry()
    registry.register(SHARED_ARTIFACT_WRITER_PROBE_PART)
    registry.register(EVIDENCE_WRITER_PROBE_PART)
    return registry
```
Add `registry.register(CODEBASE_MEMORY_MCP_PART)` (import from `databasise.parts_core.declared_only`). Switch `_parse` (:295-298) from `default_registry()` to `probe_registry()`, matching `evaluate_probe` (:287-292). The "exactly D-04's seven entries" docstring text belongs to TOOL-19 (Phase 15); only touch it if the new sentence needs it. `tests/validator/test_falsifier2_probes.py` requires that `default_registry()` never carries the probe-only parts.

**Registry side** (`parts_core/declared_only.py:132-135`): remove `CODEBASE_MEMORY_MCP_PART` from the `DECLARED_ONLY_PARTS` tuple and keep the constant (:68). `default_registry` (parts/registry.py:209-227) needs no code change. Only its docstring changes (no counts, no "two declaration-only placeholders").

---

### `evidence/f07_report.py` F-07 renderer (renderer, transform)

**Analog:** `_CATALOGUED_NOT_BUILT` rows (:97-122):
```python
    _DispositionRow(
        component="MC-1 (postgres-mcp's execute_sql, Unrestricted Mode)",
        disposition=DISPOSITION_PERMANENT_EXCLUSION,
        reason=(
            "Catalogued in CATALOG.md ## §T as a roster entry declaring mutable-store; no "
            "postgres-mcp Part is registered in default_registry() today. Catalogued, not "
            "registered -- ..."
        ),
        tag="[docs-verified]",
    ),
```
Add a third row, for example `component="codebase-memory-mcp@0.1.0 (CA-2, admitted, not registered)"`. Rewrite `_CODEBASE_MEMORY_MCP_REASON` (:36-51): it currently says "admitted and registered" and cites `databasise/wirings/codebase-memory-mcp.json`. Drop the `"codebase-memory-mcp@0.1.0"` key from `_KNOWN_REASONS` (:85-90). After that, a registry containing the part makes `_live_mutates_store_rows` (:125-153) raise its "no named disposition reason" `ValueError`, which is the intended guard. Regenerate the `.md` from `render_f07_record(default_registry())` (:164) and keep `` `CA-2` ``, `` `MC-1` ``, `` `CA-7` `` in the text. `tests/evidence/test_f07_record.py` is not edited.

---

### New test files

**Ledger tests** (`tests/ledger/test_ledger_history.py`, `test_ledger_store_api.py`, `test_ledger_lifecycle.py`). Analog `tests/ledger/test_ledger.py:1-43`: a one-line module docstring naming the row, `from __future__ import annotations`, a `_record(**overrides)` builder over a full `LedgerRecord` kwargs dict, and plain sync `def test_*(store_root)`. Fail-first: guard new API with `hasattr(Ledger, "history_for_alias")` / `getattr(..., None)` and assert, never import a new name at module level (Pitfall 10). Lifecycle (a) uses the `sqlite3.connect` factory-counting snippet in research Code Examples, filtered to paths ending `ledger.db`. Lifecycle (b) checks `ledger.db`, `-wal` and `-shm` are all absent (Pitfall 16).

**Engine fixture + seeded trace** (analog `tests/seam/test_promotion_posture.py:23-41` and `test_operator_verb_concurrency.py:44-73`):
```python
def _seed_trace(store_root, arm_name: str) -> str:
    resolved = next(resolved for name, resolved in all_wirings() if name == arm_name)
    node_ids = sorted(resolved.get("nodes", {}).keys())
    fake_record = {
        "run_id": f"fake-run-{arm_name}",
        "wiring_id": resolved.get("wiring_id"),
        "wiring_instance_hash": f"sha256:{'0' * 64}",
        "arm_id": "seam",
        "nodes": [{"node_id": node_id} for node_id in node_ids],
    }
    return TraceStore(store_root).persist(fake_record)


def _engine(store_root) -> Databasise:
    return Databasise(store_root=store_root, workspace="posture-test")


def _row_count(store_root) -> int:
    return Ledger(store_root)._conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
```
For synthetic partial records (LEDG-01 b/c, LEDG-02), persist through the engine's own store: `eng._trace_store.persist(record)` (attribute set at engine.py:1148, the same `persist` the engine calls at :2140). Add `"partial": True`, per-node `"status"` (`"failed"`, `"not-scheduled"`) and either `arm_id: "hipporag"` (arm_id-first path) or `arm_id: "seam"` (old-format fallback). `_row_count` builds `Ledger(store_root)` and so creates `ledger.db`. In "no ledger.db" tests, check `(store_root / "ledger.db").exists()` before any `_row_count` call. Real partial traces (LEDG-01 a, LEDG-02 failed bypass) come from `engine.query` with `clients=None` over the `synthetic_naive_store` fixture (`tests/seam/conftest.py:20-38`, workspace `seam-test`). Catch with `try/except Exception as caught` and assert `type(caught).__name__ == "PartialRunEvidenceError"` so a pre-fix run fails by `AssertionError`.

**TestClient fixture + stub clients** (analog `tests/seam/test_rest_transport.py:104-142`):
```python
class _StubEmbeddingClient:
    def __init__(self, vector: list[float]):
        self.vector = vector

    async def embed(self, texts, **kwargs):
        return EmbeddingResult(
            vectors=[self.vector for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )
...
@pytest.fixture
def rest_app(synthetic_naive_store):
    return create_app(
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients=_stub_clients(synthetic_naive_store),
    )
```
`_StubLLMClient.chat` returns `ChatResult(text=..., tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"), resolved_model_identity="stub-llm-model")` (:113-122). Keep `counted_by` set so LightRAG arms stay budgetable. For refusal legs, build `TestClient(app, raise_server_exceptions=False)` and assert `status_code != 500`, `"known arms" not in response.text`, and `response.json()["refusal_type"]`. The LEDG-03 HippoRAG ingest leg needs these stub clients (Pitfall 11: no clients gives 502). Copy the stubs into each new file. Do not import them from the protected `test_refusal_reachability.py`.

**Debug-strict REST leg:** copy `test_trace_resolution_endpoint_returns_what_the_in_process_operation_returns` (test_rest_transport.py:344-356): POST `/query`, read `trace_token`, then POST `/trace/resolve` with `debug` in `'yes'`, `'true'`, `'1'`, `1` (expect 422, no `run_id` in the body) and `True` (200).

**MCP legs** (analog `tests/mcp/test_tool_growth_invariant.py:21-33, 87-88`): use the CWD-shadow-safe skip `try: import databasise.mcp ... except ImportError: pytest.skip(..., allow_module_level=True)`, then `server = create_server(store_root=tmp_path, workspace=...)` and `await server.call_tool("resolve", {...})`. A refusal arrives as `RefusalToolError` whose `str()` is `json.dumps(refusal_body(...))` (mcp/server.py:23-44). Parse it and assert `refusal_type`. A non-refusal validation error keeps the SDK `Error executing tool` text.

**Promotion-posture rewrite + LEDG-08 node** (`test_promotion_posture.py`): keep the file's `_seed_trace`/`_engine`/`_row_count` helpers. Rewrite the five per-class tests (:44 onward) to expect `GateNotCalibratedError`. The new node parametrises over `[n for n, _ in all_wirings()]` x `["promote-next", "promote-now"]` on a fresh root and asserts no `ledger.db` / `-wal` / `-shm`. Update `evidence/PROMOTION-LEDGER-EVIDENCE.md` row 3 in the same plan (Pitfall 5).

**Lineage / concurrency** (`test_retire_lineage.py`): copy `_rows_targeting` (test_operator_verb_concurrency.py:62-73) for raw `(id, record_kind)` reads and assert the row count is unchanged on each refusal. In the race test (:99-103), accept both `TombstonedGenerationError` and `ActiveGenerationRetirementError` (Pitfall 4).

**Already-met rows** (`test_capability_effects.py`, `test_node_kind.py`): these are re-proved with `record-fail --at 3fd6e4c^` / `--at 5d61a79^`, so they may import only names that exist at those commits (research §5.1/§5.2, Pitfall 10). Compare against the string `"kind-mismatch"`, not `CODE_KIND_MISMATCH`.

**Registry reachability / corpus wiring:** research Code Examples "Reachability of admitted parts", and §5.4 (`monkeypatch.setattr(resolve, "_WIRINGS_ROOT", tmp)`; `_WIRINGS_ROOT` is read inside `load_wiring` at resolve.py:149). The header style comes from `tests/parts/test_registry.py:1-16`. Do not state counts in docstrings (LEDG-14).

## Shared Patterns

### Consumer-safe refusal vocabulary
**Source:** `seam/refusals.py:122-137` (`UnsatisfiableSelectorError` names only `selector_kind`/`requested`), `:526-540`.
**Apply to:** `PartialRunEvidenceError`, `GateNotCalibratedError`, every alias-row failure. Public attributes hold only the caller's own input (`trace_ids`, `verb`, `alias`). They never hold an arm name, node id, mutation id or the list of known arms.

### Closed-set refusal catalogue
**Source:** `refusals.py:940-990` `__all__` + `test_rest_transport.py:418-493` factories + `rest.py:123-154` status mapping.
**Apply to:** both new classes. Define them in refusals.py, list them in `__all__`, add a factory in the same plan, and leave them at 422 by default.

### One sqlite connection per executor closure
**Source:** `engine.py:2355-2363` docstring (open on the executor thread, never cross threads) + `ledger.py:195-202` `BEGIN IMMEDIATE` span.
**Apply to:** `_resolve_alias` and the three verb closures. Use `with ledger` (closes) wrapping `ledger.transaction()` (commits or rolls back). Read paths go through `open_existing` (CONTRACT §6: a read must not write).

### Ledger import fence
**Source:** `tests/runner/test_measurement_posture.py:60-92` (Pitfall 6).
**Apply to:** `promotion.py` and `wirings/resolve.py` must not import `databasise.ledger`. Only `seam/selectors.py` and `seam/engine.py` may import it.

### Fail-first discipline
**Source:** 14-CONTEXT D-17, research Pitfall 10.
**Apply to:** every new row test. Put it in a new unprotected file, have it fail at HEAD by `AssertionError`, and resolve new symbols with `getattr`/`hasattr`. A row's `test_ref` node goes in the last plan that touches the row (Pitfall 12).

### Protected tests
Run every protected `test_ref` file a plan touches after each task (D-16). The only edit to a protected file is the owner-granted change to `tests/seam/test_refusal_reachability.py` (research §6.4 has the exact diff: new `_CBM_WIRING_PATH` under `tests/fixtures/`, `registry=` passthrough in `_engine`, and a registry with the cbm part for `test_compare_with_one_mutating_selector_is_refused`). Make it the first checkpoint task of 14-06.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `Ledger.lineage` walk | store | CRUD | No recursive or chained ledger read exists yet. Use research Pattern 3 (visited list, `(alias, minted_version)` unique index) |
| `Ledger.open_existing` / context manager | store | CRUD | No store in the repo has a read-only "open if present" constructor. Use research Pattern 2 |
| `tests/test_docstring_currency.py` | test | transform | No banned-substring test exists outside protected SEAM-16. Build it from the research §8 list |
| sqlite connection-counting fixture (LEDG-06 a) | test | - | No precedent. Use research Code Examples snippet |

## Metadata

**Analog search scope:** `databasise/seam` (refusals, engine, promotion, selectors, rest), `databasise/ledger`, `databasise/wirings/resolve.py`, `databasise/mcp` (tools, server), `databasise/evidence` (falsifier2, f07_report), `databasise/parts`, `databasise/parts_core/declared_only.py`, and the unprotected tests `tests/seam/{conftest,test_rest_transport,test_promotion_posture,test_operator_verb_concurrency}.py`, `tests/ledger/test_ledger.py`, `tests/parts/test_registry.py`, `tests/mcp/test_tool_growth_invariant.py`.
**Files read directly this pass:** refusals.py (122-180, 509-545, 580-690, 940-990), ledger.py (95-385), selectors.py (254-302), promotion.py (105-186, 245-276), resolve.py (93-152, 198-234), engine.py (300-316, 685-699, 2265-2434, 2630-2693), rest.py (182-216), tools.py (96-103, 192-201), mcp/server.py (14-48, 102-130), falsifier2.py (104-143, 287-300), f07_report.py (29-60, 85-175), registry.py (205-228), the test files listed above. The `_rollback_sync` body (~2490-2549) and the `promote` docstring were taken from 14-RESEARCH.md §1.1/§2.1 and not re-read.
**Protected files:** none read. `ledger/REQUIREMENTS.json` was not opened this pass. Protected/unprotected status was taken from 14-RESEARCH.md §6, which was built from a Read of that file.
**Pattern extraction date:** 2026-10-20
