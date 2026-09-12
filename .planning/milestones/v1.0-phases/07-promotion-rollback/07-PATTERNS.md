# Phase 7: Promotion & Rollback - Pattern Map

**Mapped:** 2026-09-11
**Files analyzed:** 11 (new/modified, from CONTEXT.md discretion notes + RESEARCH.md Recommended Project Structure/Wave 0 Gaps)
**Analogs found:** 11 / 11 (all analogs are existing files in this same codebase; no external pattern needed)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `databasise/ledger/ledger.py` (MODIFY: add `change_origin`, `minted_version`, `record_kind` columns) | model (dataclass + SQLite schema) | CRUD (append-only insert + derived-query read) | itself — existing `alias` column addition (Phase 4) | exact |
| `databasise/seam/promotion.py` (NEW) | service (pure computation: class derivation, posture constant, semver mint) | transform | `databasise/seam/selectors.py` (`_wiring_effects`, `_match_capability` — pure functions over resolved wirings) | exact |
| `databasise/seam/engine.py` (MODIFY: add `Databasise.promote()`/`rollback()`/`retire()`) | service/controller (seam write operation) | request-response / event-driven (single ledger append as the decision) | `databasise/seam/engine.py::delete_document` (lines 747-830) — a write op that resolves a selector/target, refuses by name, dispatches, returns a typed result | exact |
| `databasise/seam/refusals.py` (MODIFY: add trace/class/posture/tombstone refusal subclasses) | model (typed exception hierarchy) | — | itself — `UnsatisfiableSelectorError` (lines 42-57) | exact |
| `databasise/seam/rest.py` (MODIFY: add `POST /promote`, `/rollback`, `/retire`) | route (REST endpoint) | request-response | itself — `post_documents` (lines 260-262), `post_query` (lines 213-215) | exact |
| `databasise/mcp/server.py` (MODIFY: add `promote`/`rollback`/`retire` tools) | route (MCP transport) | request-response | itself — `delete_tool` (lines 215-219) | exact |
| `databasise/mcp/tools.py` (MODIFY: add `PromoteToolArgs`/`RollbackToolArgs`/`RetireToolArgs`) | model (Pydantic tool-argument DTO) | — | itself — `DeleteToolArgs`/`IngestToolArgs` (module pattern, lines 1-60) | exact |
| `databasise/seam/envelope.py` (MODIFY or NEW model: promotion response shape) | model (frozen response DTO) | — | itself — `_StrictModel`/`ResponseEnvelope` closed-set pattern | exact |
| `databasise/tests/seam/test_promote.py` (NEW) | test | — | `databasise/tests/seam/test_alias_registry.py` (hand-appends a `LedgerRecord` through `Ledger.append()` to prove the read side) | exact |
| `databasise/tests/seam/test_rollback.py`, `test_retire.py`, `test_promotion_posture.py` (NEW) | test | — | same as above | exact |
| `.planning/phases/07-promotion-rollback/07-GATE-AMENDMENT.md` (NEW, non-code) | config/docs (deferral record) | — | `.planning/phases/06-hipporag-2-side-by-side/06-GATE-AMENDMENT.md` | exact |

## Pattern Assignments

### `databasise/ledger/ledger.py` (model, CRUD)

**Analog:** itself — the existing `alias` column addition is the exact precedent (same file, same discipline: additive column on an empty table, no migration).

**Current schema/dataclass to extend** (lines 57-77, verbatim):
```python
@dataclass(frozen=True)
class LedgerRecord:
    mutation_id: str
    mutation_class: str
    parent: str | None
    arm_instance_hashes: list[str]
    effect_size: float | None
    verdict: str | None
    evidence_pointer: str | None
    proposer_id: str
    depth_label: str | None
    tier_of_decision: str | None
    decomposition_ratio: float | None
    opaque_ttl_renewals: list[dict[str, Any]]
    parity_records: list[dict[str, Any]]
    promotion_provenance: str
    promotion_trace_ids: list[str]
    alias: str | None = None
    # Phase 7 additions:
    # change_origin: str            (NOT NULL — "human_edit" | "machine_mutation")
    # minted_version: str | None    (semver string; None only for a retire/tombstone record)
    # record_kind: str              (NOT NULL — "promotion" | "rollback" | "tombstone")
```

**CREATE TABLE to extend, same file** (lines 92-113): add the three columns to the single
`CREATE TABLE IF NOT EXISTS ledger (...)` statement's column list directly — no `ALTER TABLE`,
following the module's own precedent for `alias`. Extend `_JSON_FIELDS` only if a new list-valued
field is added (none needed here — all three new fields are scalar `TEXT`).

**Derived-query pattern to copy for a semver/tombstone lookup** (`by_alias`, lines 195-211):
```python
def by_alias(self, alias: str) -> LedgerRecord | None:
    cur = self._conn.execute(
        "SELECT * FROM ledger WHERE alias = ? ORDER BY id DESC LIMIT 1",
        (alias,),
    )
    row = cur.fetchone()
    return self._row_to_record(row) if row is not None else None
```
Use this exact shape (`ORDER BY id DESC LIMIT 1`, never a written "current" column) for any new
lookup Phase 7 needs — e.g. "latest record for this alias+minted_version" to check tombstone state
(Pitfall 4 in RESEARCH.md: check the *latest* record for the specific target, never "does a
tombstone exist anywhere in history").

**Append pattern to extend** (`append`, lines 149-179): add the three new fields to the parameter
tuple and `INSERT` column list in the same positional order as the dataclass fields — the existing
method already loops `LedgerRecord.__dataclass_fields__` in `_row_to_record`, so no other method
needs to change once the dataclass and schema both carry the new fields.

---

### `databasise/seam/promotion.py` (NEW — service, transform)

**Analog:** `databasise/seam/selectors.py` — `_wiring_effects` (lines 139-146) for the pure
diff-over-resolved-wirings pattern, and its own module-constant-and-pure-function shape (no state,
no I/O beyond what is handed in).

**Effects-union pattern to copy for D-10's class derivation and D-06's MAJOR/MINOR diff**
(verbatim, lines 139-146):
```python
def _wiring_effects(resolved: dict[str, Any], registry: PartRegistry) -> set[str]:
    """The union of every node's *registered Part's* own declared effects (never the wiring
    node's own, possibly-narrower ``effects`` — CR-01)."""
    effects: set[str] = set()
    for node in resolved.get("nodes", {}).values():
        part = registry.get(node["component"])
        effects.update(part.effects)
    return effects
```
D-06's MAJOR/MINOR mint rule and D-10's `index-side`/`answer-level`/`retrieval-side` class
derivation are both node-set/effects-set diffs against a prior resolved wiring — resolve both
wirings via `databasise.wirings.resolve.resolve_arm`, then diff node-id sets / `_wiring_effects()`
unions directly (RESEARCH.md's own "Don't Hand-Roll" section: no `jsonpatch`-based diff needed for
this — a set comparison suffices and is simpler).

**Module-constant posture mapping (D-11)** — follow this codebase's own module-constant
convention (e.g. `_ACCOUNTABLE_STORE_EFFECT_PREFIXES`/`_ARM_NAMES` elsewhere in the codebase): a
literal dict at module scope, e.g. `_POSTURE: dict[str, bool] = {"retrieval-side": True,
"answer-level": False, "index-side": False}` — never a settings object, `.env` value, or
constructor argument (RESEARCH.md Pitfall 5).

---

### `databasise/seam/engine.py` — `promote()`/`rollback()`/`retire()` (service/controller, request-response)

**Analog:** `Databasise.delete_document` (lines 747-830) — closest existing write operation:
resolves a target, validates/refuses by name before touching storage, dispatches, returns a typed
result.

**Refuse-before-any-write shape to copy** (verbatim structure, lines 774-778):
```python
try:
    generated_on_disk_name(document_id)
except ValueError as exc:
    raise UnknownDocumentError(document_id=document_id) from exc

query_wiring = resolve_selector(selector, registry=self.registry, store_root=self.store_root)
```
Apply the identical shape to `promote()`: resolve every trace id via `self._trace_store` /
`TraceStore.resolve()` (raises `UnknownTraceReferenceError` per-id automatically), collect the
distinct `arm_id`/`wiring_id` values, and refuse (a new typed refusal) before constructing any
`LedgerRecord` if the ids disagree or resolve to none/more-than-one wiring — this discharges both
D-04's requirement and RESEARCH.md Pitfall 1/3 in one check.

**Trace resolution to reuse verbatim** (`databasise/seam/trace_store.py`, `TraceStore.resolve`,
lines 108-115):
```python
def resolve(self, token: str) -> dict[str, Any]:
    """The record persisted under ``token``. Raises :class:`UnknownTraceReferenceError` —
    never returns ``None``, never a partial record — for a token this store does not hold.
    """
    cur = self._conn.execute("SELECT run_record FROM traces WHERE token = ?", (token,))
    row = cur.fetchone()
    if row is None:
        raise UnknownTraceReferenceError(token)
    return json.loads(row["run_record"])
```
`RunRecord.to_dict()` (persisted via `TraceStore.persist`) carries `wiring_id`/`arm_id` fields —
read these off each resolved trace record, never a caller-supplied wiring/arm name (Phase 4 D-11,
preserved by D-04).

**Async offload to copy** (`ledger.py`'s own WR-03 instruction; `stores/graph.py` gives the
concrete call-site shape, line 349):
```python
await loop.run_in_executor(None, _do_flush)
```
Wrap `Ledger.append(record)` the same way at the `promote()`/`rollback()`/`retire()` call site:
`await asyncio.get_running_loop().run_in_executor(None, lambda: ledger.append(record))` — `Ledger`
itself stays synchronous, per the module's own deliberate-exception note.

**Return-shape discipline:** follow `DeletionOutcome`'s pattern (a small frozen result model, not
a raw dict) — new `PromotionResult`/`RollbackResult`/`RetireResult` models must obey §18.2's closed
set per CONTEXT.md D-discretion: alias, minted semver, provenance, generation ordinal — never a
wiring name, node id, or instance hash. Build these next to `envelope.py`'s existing
`_StrictModel` base.

---

### `databasise/seam/refusals.py` (model, typed exception hierarchy)

**Analog:** `UnsatisfiableSelectorError` (lines 42-57) — the exact house style: name only the
consumer's own input, never the machine's registered candidates.

**Pattern to copy verbatim for every new Phase 7 refusal** (structure, lines 42-57):
```python
class UnsatisfiableSelectorError(SeamRefusalError):
    """... never a candidate wiring id, arm name, or node id."""

    def __init__(self, *, selector_kind: str, requested: Any):
        self.selector_kind = selector_kind
        self.requested = requested
        super().__init__(
            f"no fitted modality satisfies the {selector_kind!r} selector: {requested!r}"
        )
```
New subclasses needed (per RESEARCH.md's refusal vocabulary and CONTEXT.md D-04/D-07/D-09):
- disagreeing/unresolvable/empty `promotion_trace_ids` (names the offending trace ids, never the
  resolved wiring)
- tombstoned target (promote/rollback/retire) — names alias + semver, never mutation_id
- gate-verb refused by posture (`promote-next`/`promote-now` at answer-level/index-side) — names
  the mutation class and cites RIG §F3.2 in the message, per D-09
- gate-verb refused by missing floor (retrieval-side) — cites RIG §AA.2
- gate-verb not built (`check`/`preview`/`run`) — one shared type parameterized by `verb`,
  mirroring `UnsatisfiableSelectorError`'s own `selector_kind` parameterization (RESEARCH.md Open
  Question 1's own recommendation)

Every new subclass is picked up automatically by both transports' generic
`SeamRefusalError.__subclasses__()` walks — no transport-layer code changes needed (see below).

---

### `databasise/seam/rest.py` (route, request-response)

**Analog:** `post_documents` (lines 260-262) — the plainest write-operation route shape.

**Pattern to copy verbatim (add three routes, same shape):**
```python
@app.post("/documents")
async def post_documents(body: IngestRequest) -> IngestJob:
    return await engine.ingest(body.document, body.selector)
```
`app.add_exception_handler(SeamRefusalError, _refusal_response)` (line 211) is already registered
once for the whole app — no per-route exception handling needed for any new refusal subclass.

---

### `databasise/mcp/server.py` / `databasise/mcp/tools.py` (route, request-response)

**Analog:** `delete_tool` (server.py lines 215-219) + `DeleteToolArgs`/`IngestToolArgs` (tools.py
module pattern).

**Pattern to copy verbatim (add three tools, same shape):**
```python
@server.tool(name="delete")
@_refusal_mapped
async def delete_tool(args: DeleteToolArgs) -> dict[str, Any]:
    outcome = await engine.delete_document(args.document_id, args.selector)
    return outcome.model_dump()
```
`_refusal_mapped` (server.py lines 91-99) already catches the single `SeamRefusalError` base class
generically — no per-tool exception handling needed. New `PromoteToolArgs`/`RollbackToolArgs`/
`RetireToolArgs` in `tools.py` follow the existing `DeleteToolArgs` field-reuse convention: reuse
the seam's own request fields (alias, trace ids, `change_origin`, semver for rollback/retire)
rather than re-declaring parallel types.

**Roster-growth test to extend:** `databasise/tests/mcp/test_tool_growth_invariant.py` already
proves §18.5's per-operation (not per-modality) growth rule — extend its expected tuple by exactly
three names (`promote`, `rollback`, `retire`), per Phase 4 D-03 (one entry per §18 operation; do
not scope-dispatch rollback/retire into one tool, per RESEARCH.md Open Question 3).

---

### Test files (`test_promote.py`, `test_rollback.py`, `test_retire.py`, `test_promotion_posture.py`)

**Analog:** `databasise/tests/seam/test_alias_registry.py` — hand-appends a `LedgerRecord` through
`Ledger.append()` to prove the read side; Phase 7's tests prove the write side produces the
identical shape. Also extend `databasise/tests/seam/test_rest_transport.py`'s `_REFUSAL_FACTORIES`
dict with a factory entry per new refusal subclass (required, not automatic — the walk itself is
automatic, but each subclass needs one factory-callable entry).

---

### `.planning/phases/07-promotion-rollback/07-GATE-AMENDMENT.md` (docs, config)

**Analog:** `.planning/phases/06-hipporag-2-side-by-side/06-GATE-AMENDMENT.md` — copy its exact
section structure (quote the ROADMAP criteria and requirements line; state the
operator-path-consumes-nothing argument; name the point of first need; list residual risk) per
CONTEXT.md D-03's explicit instruction to follow it "exactly."

## Shared Patterns

### Refusal typing and dual-transport mapping (no new transport code needed)
**Source:** `databasise/seam/rest.py:211` (`app.add_exception_handler(SeamRefusalError, ...)`) and
`databasise/mcp/server.py:91-99` (`_refusal_mapped`)
**Apply to:** every new refusal subclass in `refusals.py` — both transports already catch the
single base class generically; only `test_rest_transport.py`'s `_REFUSAL_FACTORIES` dict needs a
manual entry per new subclass.

### Synchronous store, async call-site offload
**Source:** `databasise/ledger/ledger.py` module docstring (WR-03) + `databasise/stores/graph.py:349`
(`await loop.run_in_executor(None, _do_flush)`)
**Apply to:** every `Ledger.append()` call inside `promote()`/`rollback()`/`retire()` — `Ledger`
itself stays synchronous by deliberate exception; only the async call site offloads.

### Additive-column, no-migration schema change
**Source:** `databasise/ledger/ledger.py`'s own `alias` column precedent (module docstring)
**Apply to:** `change_origin`, `minted_version`, `record_kind` — edit the single `CREATE TABLE IF
NOT EXISTS` column list directly; the table holds zero rows in every environment this milestone
runs in, so no `ALTER TABLE`/backfill is needed.

### Derived-query "active pointer," never a written column
**Source:** `databasise/ledger/ledger.py::active_pointer`/`by_alias` (`ORDER BY id DESC LIMIT 1`)
**Apply to:** any new lookup Phase 7 needs (tombstone-state check by alias+semver, prior-active
generation for the semver-mint diff) — never a second, independently-writable "current" field.

## No Analog Found

None — every file Phase 7 touches has a direct, exact-match analog already in this codebase (the
phase's own RESEARCH.md observes this: "Nearly everything Phase 7 needs mechanically... was
already built by Phases 1/4/5 specifically *for* Phase 7 to consume").

## Metadata

**Analog search scope:** `databasise/ledger/`, `databasise/seam/`, `databasise/mcp/`,
`databasise/tests/seam/`, `databasise/tests/mcp/`, `.planning/phases/06-hipporag-2-side-by-side/`
**Files read this session:** `databasise/ledger/ledger.py` (full), `databasise/seam/refusals.py`
(head + one subclass in full), `databasise/seam/engine.py` (targeted: `ingest`, `delete_document`),
`databasise/seam/trace_store.py` (full), `databasise/seam/selectors.py` (targeted: `Selector`,
`_wiring_effects`, `_resolve_alias`), `databasise/seam/rest.py` (targeted: route registrations),
`databasise/mcp/server.py` (targeted: tool registrations, `_refusal_mapped`), `databasise/mcp/tools.py`
(head), `.planning/phases/06-hipporag-2-side-by-side/06-PATTERNS.md` (head, for format)
**Pattern extraction date:** 2026-09-11
