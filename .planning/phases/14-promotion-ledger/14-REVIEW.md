---
phase: 14-promotion-ledger
reviewed: 2026-10-20T00:00:00Z
depth: deep
diff_base: bb52fbb
parts: "A (seam verbs, promotion, refusals, REST/MCP debug, GUI API inventory) + B (ledger store, alias selector, wiring lookup, registry, declared-only parts, evidence, packaging, codebase map), merged; ids prefixed A-/B-. The two lanes' file lists are disjoint. Two lane findings pairs described the same defect and were merged (A-WR-01 absorbs B-WR-02; A-WR-02 absorbs B-WR-03)."
files_reviewed: 19
files_reviewed_list:
  - databasise/seam/engine.py
  - databasise/seam/promotion.py
  - databasise/seam/refusals.py
  - databasise/seam/rest.py
  - databasise/mcp/tools.py
  - docs/gui/API-INVENTORY.md
  - databasise/ledger/ledger.py
  - databasise/seam/selectors.py
  - databasise/wirings/resolve.py
  - databasise/parts/registry.py
  - databasise/parts/schema.py
  - databasise/parts_core/declared_only.py
  - databasise/evidence/falsifier2.py
  - databasise/evidence/f07_report.py
  - databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md
  - databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md
  - databasise/evidence/ADMISSION-CODEBASE-MEMORY-MCP.md
  - databasise/pyproject.toml
  - docs/gui/CODEBASE-MAP.md
findings:
  critical: 0
  warning: 4
  info: 14
  total: 18
status: issues_found
---
# Phase 14: Code Review Report

**Reviewed:** 2026-10-20
**Depth:** deep (lane A traced into `ledger/ledger.py`, `wirings/resolve.py`, `seam/selectors.py`, `runner/scheduler.py` as callees; lane B traced callers in `seam/engine.py` and `seam/promotion.py`; both lanes ran probes against HEAD)
**Files Reviewed:** 19 (lane A 6, lane B 13)
**Status:** issues_found (no Critical; 4 Warning, 14 Info)

## Summary

The diff is `git diff bb52fbb HEAD`. Lane A covers the engine verb paths (promote, rollback, retire), the shared prologue, `refuse_partial_evidence` and `_arm_name_for_record`, the two new refusal classes, StrictBool `debug` on REST and MCP, the `_corpus_wiring` move to `load_wiring`, and the API inventory. Lane B covers the store layer (`Ledger.open_existing`, `close` and the context manager, `lineage`, `history_for_alias`, `LedgerEntry`), the alias selector, `wiring_for_name`, the codebase-memory-mcp unregistration (D-13) and the LEDG-14 docstring rewrites.

Both lanes verified the following against the source and with probes:

- **Ledger concurrency.** Every guard read (`generation_state`, `by_alias`, `lineage`) and the single `append` run inside one `BEGIN IMMEDIATE` span on the executor thread. Minted versions rise monotonically, because every minting row becomes the next `by_alias` row, so the unique index cannot be hit.
- **Connection lifetime.** The `with Ledger(...) as ledger, ledger.transaction():` nesting closes the connection after the transaction exits.
- **Lineage walk.** Traced by hand over retire-after-rollback, rollback-to-a-rollback, and promote/rollback/retire/re-promote sequences (`engine.py:2546-2555`, `2697-2706`). No sequence makes a tombstoned generation reachable or lets the alias serve one, and a version in the active lineage cannot be retired.
- **Gate verbs** refuse before any `Ledger` is constructed.
- **§18.** The new refusals name only caller input (`trace_ids`, `verb`, `alias`). `_resolve_alias` refuses identically in all three miss cases and names only the alias. No §18 leak was found on any live consumer path. Two latent leak surfaces are recorded as Info (A-IN-05, B-IN-05), and one forward risk (B-IN-01).
- **Selectors.** The capability table in the module docstring matches the code. All 13 probed requests resolve as documented, with node counts 7/1/17/15/15/14.
- **Wirings.** Every wiring and corpus variant parses clean against `default_registry()`, which holds no body-less part.
- **Rendered evidence.** `FALSIFIER-2-EVIDENCE.md` and `F-07-MUTABLE-STORE-DISPOSITION.md` re-render byte-identically.
- **Tests.** Lane A: 93 tests across the Phase 14 seam files pass (`-m "not live"`). Lane B: 161 tests in the ledger, posture, concurrency, rollback, retire and evidence suites pass.

There are no blockers. The four warnings:

1. **The "read-only" ledger open writes** (A-WR-01). On a legacy file it permanently drops an index and turns every later alias query into a 500. It also writes a schema into a zero-byte file and converts rollback-journal files to WAL. Both lanes confirmed this with probes.
2. **An alias whose active row names an unresolvable wiring cannot be repaired** (A-WR-02). Promote, rollback and retire all refuse, and the append-only ledger offers no other way out. Both lanes confirmed this with probes.
3. **The API inventory contradicts the code** in four places that Phase 16 plans from (A-WR-03).
4. **The Falsifier-2 gate evidence names the wrong registry** (B-WR-01). It says `default_registry()`, but since D-13 it is computed against `probe_registry()`.

**Process note, not a code defect:** the session-start report shows WIRE-17 (`tests/seam/test_refusal_reachability.py`) as "check changed after its first failing run". This is the D-13 owner `grant-check-edit` item, and it is still waiting for the owner's `lock-checks` approval.

**Merge notes.**

- A-WR-01 and B-WR-02 describe the same defect: `Ledger.open_existing` runs the full migrating constructor on the read path. They are merged under A-WR-01. Lane A contributed the legacy-index probe and the permanent-500 consequence. Lane B contributed the zero-byte and rollback-journal cases, the false `transaction()` docstring and the busy-timeout wait. The fix uses lane B's `read_only` variant, which keeps the migrating open for rollback and retire.
- A-WR-02 and B-WR-03 describe the same defect: `_wiring_for_row` refuses on an unresolvable prior, current or active row. They are merged under A-WR-02. Lane A said `mint_version` and `derive_mutation_class` would need to change to accept an unknown prior surface. Lane B said `mint_version` already MAJOR-bumps in that case. Reading `promotion.py:214-261` at merge time confirms lane B: `mint_version` compares `new_surface != None` (true, so it MAJOR-bumps), and `derive_mutation_class` already accepts `prior_resolved=None`. Neither function has to change.
- B-IN-02 (synchronous SQLite I/O on the event loop) depends on A-WR-01. It is cross-referenced, not merged, because the read-only fix shrinks it but does not remove it.
- A-WR-03 (API-INVENTORY.md) and B-IN-08 (CODEBASE-MAP.md) are both stale Phase 16 GUI inputs in different files. They are cross-referenced. A-IN-06 covers the out-of-date line citations in the same inventory as A-WR-03.
- A-IN-05 (a node-id leak in `promotion.py`) and B-IN-05 (an arm/part enumeration leak in `resolve.py` and `registry.py`) are different latent leaks. Both are kept.

## Narrative Findings (AI reviewer)

## Warnings

### A-WR-01: The "read-only" ledger open writes the file and can permanently break alias reads (merged with B-WR-02)

**File:** `databasise/ledger/ledger.py:158-167` (`open_existing` returns `cls(store_root)`, which runs `__init__` 146-156, `_set_wal` 200-207 and `_create_schema` 238-313). Callers: `databasise/seam/selectors.py:295-299`, `databasise/seam/engine.py:2542` (rollback), `databasise/seam/engine.py:2693` (retire). Stale docstrings: `selectors.py:280-282`, `engine.py:2537-2540`, `ledger.py:220-221`.

**Issue:** D-08 and the docstrings say the read path "never creates" anything and that a read must not write (CONTRACT §6). `open_existing` only avoids *creating* `ledger.db`. It then runs the full constructor:

- `PRAGMA journal_mode=WAL` rewrites the header of a file that is not in WAL mode.
- `CREATE ... IF NOT EXISTS` writes the schema into a file that has none.
- On a legacy file, `DROP INDEX IF EXISTS ix_ledger_generation` and `CREATE UNIQUE INDEX ux_ledger_generation` run, plus a `commit()`. Each statement autocommits, so when the unique index fails the drop has already been committed.

`_resolve_alias` runs on every alias-selected `query`/`compare`/`query_stream`/`ingest`/`delete` (`engine.py:1271, 1343, 1636, 1726, 1861, 2065`).

Probed at HEAD (lane A scratchpad `probe_a.py`, lane B scratchpad `lw.py`):

1. **Pre-07-05 file with duplicate rows.** The setup is a legacy `ledger.db` with the old plain `ix_ledger_generation` index and two `(prod, 1.0.0)` rows. This is the G-07-1 race that 07-05 fixed, so such files can exist. `_resolve_alias("prod", ...)` raises a raw `sqlite3.IntegrityError: UNIQUE constraint failed`, which is a 500 on `/query`, `/compare` and `/documents` with an alias selector. The indexes go from `[ix_ledger_mutation_id, ix_ledger_alias, ix_ledger_generation]` to `[ix_ledger_mutation_id, ix_ledger_alias]`. The read dropped the legacy index permanently, and every later read fails the same way.
2. **Zero-byte `ledger.db`.** An alias query writes the full schema (0 to 24576 bytes). An interrupted first `Ledger()` leaves such a file, because `sqlite3.connect` creates the file before any schema exists.
3. **Rollback-journal file** (`journal_mode=DELETE`). One alias read, even a refused one, converts it to WAL.

D-08 accepted only the legacy-index migration case. Cases 2 and 3 are unacknowledged writes on a consumer read path. The `transaction()` docstring (`ledger.py:220-221`) says opening over an existing schema "never waits on a writer". That is false for case 1: the DDL needs the write lock, so during a concurrent operator verb it can wait up to the 5 s busy timeout and then fail as a raw `sqlite3.OperationalError`, which the consumer sees as a 500.

The constructor behaviour predates this phase, but this phase documents the read path as non-writing, so the claim is now false.

**Fix:** Give the selector a real read-only open. Keep the migrating constructor for rollback and retire, which append anyway:

```python
@classmethod
def open_existing(cls, store_root, *, read_only: bool = False):
    path = Path(store_root) / "ledger.db"
    if not path.is_file():
        return None
    if not read_only:
        return cls(store_root)
    self = cls.__new__(cls)
    self._conn = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    self._conn.row_factory = sqlite3.Row
    return self
```

`_resolve_alias` calls `open_existing(store_root, read_only=True)` and maps `sqlite3.OperationalError` ("no such table", which covers the zero-byte case) to the same `UnsatisfiableSelectorError`. On the rollback and retire paths, map `sqlite3.IntegrityError` raised at open to a named fault. Correct the `selectors.py`, `engine.py` and `transaction()` docstrings.

**Related:** B-IN-02 (the same open runs synchronously on the event loop).

### A-WR-02: An alias whose active row names an unresolvable wiring is permanently unrepairable: all three verbs refuse (merged with B-WR-03)

**File:** `databasise/seam/engine.py:1121-1131` (`_wiring_for_row`), with uses at `engine.py:2399-2404` (promote prior), `2558-2563` (rollback current) and `2704-2711` (retire active). Root lookup: `databasise/wirings/resolve.py:224-235`.

**Issue:**

- `_wiring_for_row` turns a `wiring_for_name(...) is None` miss into `UnsatisfiableSelectorError`.
- Each verb resolves the alias's current active row only to derive `mutation_class` and the semver surface. Promote calls it on `prior_record.mutation_id`, rollback on `current_record.mutation_id`, and retire on `active.mutation_id`.
- So once an alias's active row names something outside `_ARM_NAMES` or `WIRING_NAMES` (an arm renamed or removed in a later build, or a hand-seeded row), every verb refuses. The selector path refuses as well. The ledger is append-only, so no row can ever repoint that alias. The alias cannot be queried, re-promoted, rolled back to a good version or retired, and the only option left is to abandon the name.

Probe (lane A scratchpad `probe_b.py`): promote `prod` with naive to get 1.0.0, then append an active row with `mutation_id="ghost"`. After that:

- promote hybrid gives `UnsatisfiableSelectorError`;
- rollback to 1.0.0 gives `UnsatisfiableSelectorError`;
- retire 1.0.0 gives `UnsatisfiableSelectorError`, even though 1.0.0 is not in the active lineage.

The `_wiring_for_row` docstring and API-INVENTORY:130 document this as a property ("cannot be repaired through promote, rollback or retire"). It is a functional defect, not a refusal choice. The codebase itself anticipates the trigger: the `resolve_arm` docstring (`resolve.py:111-112`) foresees renaming naive's wiring. It also undercuts D-05's goal: the 500 became a 422, but the operator still has no way out.

**Fix:** Resolve the *target* strictly, as now. Treat an unresolvable *prior/current/active* wiring as "no comparable prior" when classing and minting, and keep the version lineage from the record:

```python
prior_resolved = wiring_for_name(prior_record.mutation_id) if prior_record is not None else None
# prior row names a wiring that no longer exists: class against nothing, MAJOR-bump via surface None;
# prior_version still comes from prior_record.minted_version so versions stay monotonic.
```

No change to `promotion.py` is needed. `mint_version(prior_version, None, new_surface)` already MAJOR-bumps, because `new_surface != None` is true (`promotion.py:231-232`). `derive_mutation_class` already accepts `prior_resolved=None` (`promotion.py:248`). With this fix, a rollback to a resolvable target or a fresh promote repairs the alias. Add a test that seeds a row with `mutation_id="retired-arm"` and asserts that promote succeeds and that the selector then resolves.

### A-WR-03: The API inventory contradicts the code in four places that Phase 16 and the GUI will rely on

**File:** `docs/gui/API-INVENTORY.md:678`, `:570`, `:246`, `:352`. All four lines were changed in this phase.

**Issue:**

1. `:678` (MCP live check) says "failed bypass trace → 1.0.0, again → 1.1.0". A failed node sets `partial = True` (`runner/scheduler.py:819-820`), and `refuse_partial_evidence` refuses it. Lines `:564` and `:588` of the same document say a failed bypass run gives `PartialRunEvidenceError`.
2. `:570` says "`LedgerRecord` omits the table's `id` and `created_at` columns ..., so no read method returns a row's ordinal or timestamp." That has been false since D-09: `Ledger.history_for_alias` returns `LedgerEntry` with both fields (`ledger.py:442-451`). Phase 16 CONN-06/07 are designed on this read.
3. `:246` says "Each selector is resolved twice (engine.py:645 and again in `_execute` at 975), so an alias repointed between the two resolutions runs a wiring the pre-check did not inspect." That is false: `compare` resolves each selector once and passes the wiring to `_execute_resolved` (`engine.py:1270-1286`, SEAM-11).
4. `:352` says "Promotion matches arms by exactly this set". Since D-01 the record's `arm_id` is used first and the node set is only the legacy fallback (`promotion.py:150-154`). The cited lines `promotion.py:109-112, 160-168` no longer point at the matcher.

**Fix:**

- On `:678`, change the bypass case to `PartialRunEvidenceError`.
- On `:570`, say `history_for_alias` returns `id` and `created_at` and has no route yet.
- On `:246`, delete the "resolved twice" sentence.
- On `:352`, describe the `arm_id`-first rule and fix the cited lines.

**Related:** A-IN-06 (out-of-date line citations in the same document), B-IN-08 (stale rows in CODEBASE-MAP.md, the other Phase 16 GUI input).

### B-WR-01: Falsifier-2 gate evidence claims `default_registry()` but is now computed against `probe_registry()`

**File:** `databasise/evidence/falsifier2.py:298-301` (with stale text at 10-13, 15-18, 134-139, 305, 503, 514, 537, 547-550)

**Issue:**

- D-13 changed `_parse` from `default_registry()` to `probe_registry()`. `probe_registry()` is `default_registry()` plus `probe/shared-artifact-writer`, `probe/evidence-writer` and `codebase-memory-mcp@0.1.0`.
- The rendered, committed `FALSIFIER-2-EVIDENCE.md` still says each named wiring is "Resolved against `default_registry()`'s Phase-1 entries" (line 514).
- The verdict says every value "was derived from that wiring's `nodes`/`deps` plus `default_registry()` alone" (lines 547-550).
- The probe section says `probe_registry()` is "`default_registry()` plus two probe-only parts" (line 537). It now adds three.
- The `probe_registry` docstring still says production `default_registry()` "stays exactly D-04's seven entries" (line 137). It holds 37.

This document is the Phase 1→2 gate artifact (Falsifier 2), so its committed provenance statement is false. There is a second effect. W1 and W3 are now parsed against a registry that contains the two probe-only parts. A named wiring that referenced `probe/shared-artifact-writer@0.1.0` used to fail with `unknown-component`. It now parses and contributes rows to the "did not fire" verdict.

**Fix:** Parse the named wirings against `default_registry()` plus only the catalogued CBM part. Keep the probe parts for `PROBES`, and render text that names the registry actually used:

```python
def evidence_registry() -> PartRegistry:
    """default_registry() plus codebase-memory-mcp@0.1.0 (catalogued, unregistered since 14-07)."""
    registry = default_registry()
    registry.register(CODEBASE_MEMORY_MCP_PART)
    return registry

def _parse(stem):
    doc = load_wiring(stem)
    return doc, parse_wiring(doc, evidence_registry())
```

Then:

- At lines 503, 514 and 547-550, replace "`default_registry()`" with "`evidence_registry()` (`default_registry()` plus the catalogued `codebase-memory-mcp@0.1.0`)".
- At lines 17 and 537, replace "two probe-only parts" with the actual set.
- At line 137, drop "D-04's seven entries".
- Re-render the evidence file.

## Info

### A-IN-01: `refuse_partial_evidence` fails open when the two lists differ in length

**File:** `databasise/seam/promotion.py:169-173`

**Issue:** `zip(trace_ids, resolved_trace_records)` truncates without an error (ruff B905). The one current caller passes lists of the same length. However, D-03 makes this the shared rule that Phase 16's CONN-09 preview will call, and a caller that passes a shorter `trace_ids` would let a partial record through.

**Fix:** `zip(trace_ids, resolved_trace_records, strict=True)`.

### A-IN-02: The `PartialRunEvidenceError` text is wrong on rollback and retire, and names only the first trace

**File:** `databasise/seam/refusals.py:555-559`, `databasise/seam/promotion.py:155-157`

**Issue:** On rollback and retire, the refusal is raised because the arm cannot be identified, but the message says the traces "cannot be promotion evidence". D-01 says those verbs accept partial traces. The probe confirmed this message on a rollback. `_arm_name_for_record` also raises inside a set comprehension, so only the first unidentifiable partial trace is named. The class docstring says "naming exactly the trace ids".

**Fix:** Use a message that does not depend on the verb, for example "come from partial runs whose arm cannot be identified" on that path. Collect every unidentifiable id before raising.

### A-IN-03: The engine-level `debug` check uses truthiness

**File:** `databasise/seam/engine.py:2266`

**Issue:** StrictBool protects only REST and MCP. An in-process embedder that calls `resolve_trace(tok, debug="false")` receives the full record, including `arm_id`, `wiring_instance_hash` and node ids. Databasise is an embeddable product, so the Python API is also a seam.

**Fix:** `if debug is True:`, or raise `TypeError` on a value that is not a bool.

### A-IN-04: Docstrings in the verbs are out of date after the reorder

**File:** `databasise/seam/engine.py:2370-2371`, `databasise/seam/engine.py:2485-2487`

**Issue:** The promote docstring still says "The gate-verb and not-built refusal branches raising inside that span are correct". Both branches now refuse before any `Ledger` exists. The rollback docstring says that `trace_ids` "refuse identically to `promote()`", but promote refuses partial traces and rollback does not.

**Fix:** Update both sentences.

### A-IN-05: A latent node-id leak in the fallback refusal message

**File:** `databasise/seam/promotion.py:141`

**Issue:** `UnknownTraceReferenceError(trace_reference or f"<run with nodes {sorted(node_ids)!r}>")` puts node ids into a consumer-facing 404 body when `trace_reference` is falsy. The new `_arm_name_for_record` re-raises it at `:158`. It cannot be reached today: the engine always passes the caller's ids, and `TraceStore.resolve("")` refuses first. This phase did not introduce it.

**Fix:** Use a fixed placeholder such as `"<unidentified run>"`.

### A-IN-06: Line citations in the API inventory are out of date

**File:** `docs/gui/API-INVENTORY.md:570` (`engine.py:1245, 1372, 1501`), the rollback and retire refusal paragraphs (`engine.py:1339, 1341, 1479, 1481`), and `:246` (`engine.py:644-645`, `975`)

**Issue:** These citations point at unrelated code. `proposer_id="operator"` is now at `engine.py:2442/2586/2722`, and the verb refusals are at `2549-2555` and `2700-2706`.

**Fix:** Regenerate the citations, or cite symbols instead of line numbers. Related: A-WR-03.

### B-IN-01: `history_for_alias` returns internal identities with no consumer-safe projection (forward §18 risk)

**File:** `databasise/ledger/ledger.py:123-131, 442-451`

**Issue:** `LedgerEntry` carries `arm_instance_hashes` (internal hashes), `mutation_id` and `parent` (arm names), and `promotion_trace_ids`. The docstring says "Phase 16's CONN-06/CONN-07 routes read it", but nothing warns that these fields must not cross §18. No product code calls it today.

**Fix:** State the strip rule in the docstring, or add the consumer projection here (alias, versions, record_kind, id, created_at, change_origin, provenance) so Phase 16 cannot serialize the raw entry.

### B-IN-02: The alias branch does synchronous SQLite I/O on the event-loop thread

**File:** `databasise/seam/selectors.py:295-299`, called from async methods at `engine.py:1271, 1343, 1636, 1726, 1861, 2065`

**Issue:** The connect, WAL pragma, schema DDL and SELECT all run inline on the loop. The ledger module docstring (lines 74-81) describes the offload discipline for the verbs only. In the A-WR-01 migration case, the loop can block for up to the 5 s busy timeout.

**Fix:** Offload with `run_in_executor` at the engine's selector call sites. The cost becomes negligible once the open is read-only (A-WR-01).

### B-IN-03: `f07_report` labels a built component as not built, and its verdict contradicts its qualification

**File:** `databasise/evidence/f07_report.py:94-106, 180-181`; rendered verdict in `F-07-MUTABLE-STORE-DISPOSITION.md`

**Issue:**

- The comment and the tuple name `_CATALOGUED_NOT_BUILT` say these rows project onto "a component that does not yet exist", but the CA-2 row is built and admitted (`[code-verified]`).
- The verdict says the disposition is "enforced as an explicit refusal in the comparison path". The next paragraph says no live path exists for CBM since it left `default_registry()`.
- `render_f07_record(probe_registry())` raises `ValueError` for any registry that registers CBM, because CBM has no `_KNOWN_REASONS` entry (probed).
- The reversal text says to add a `_KNOWN_REASONS` row, but not to remove the catalogued row. Following it would produce a duplicate.

**Fix:** Rename the tuple to `_CATALOGUED_NOT_REGISTERED`, fix the comment, and say "defined, not live" in the verdict. Have `_live_mutates_store_rows` skip any component already present in the catalogued rows.

### B-IN-04: The `declared_only.py` module docstring and `DECLARED_ONLY_PARTS` name are stale

**File:** `databasise/parts_core/declared_only.py:1-5, 22-28, 134`

**Issue:** The docstring still presents CBM as part of the set this module registers ("is admitted whole-engine", "Every entry this module declares"). `DECLARED_ONLY_PARTS` now holds only the three corpus parts, and none of them is declaration-only. The registry docstring (`registry.py:210`) refers readers to "the parts of `parts_core/declared_only.py`", a set that now excludes a part the module defines.

**Fix:** Add one docstring sentence saying that CBM is defined here but has been excluded from `DECLARED_ONLY_PARTS` since 14-07. Optionally alias `DECLARED_ONLY_PARTS` to `LIGHTRAG_CORPUS_PARTS`.

### B-IN-05: Residual enumerating error messages (`known arms`, `registered parts`)

**File:** `databasise/wirings/resolve.py:46-50`; `databasise/parts/registry.py:28-33`

**Issue:** `UnknownArmError` still prints `known arms: [...]`, and `UnknownPartError` prints every registered part. Neither is consumer-reachable today: every product caller goes through `wiring_for_name`, which checks membership first, and the committed wirings parse clean. D-05 states that no body contains "known arms". A future caller that passed consumer input to `resolve_arm` would leak the arm list in a 500 body.

**Fix:** Drop the enumeration from the messages and keep it on an attribute for logs.

### B-IN-06: PROMOTION-LEDGER-EVIDENCE criterion 3 is marked "Holds" while its literal text no longer holds

**File:** `databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md:31`

**Issue:** The criterion reads "the refusal names the posture". The status cell says the refusal "names the verb, not a posture", yet still reads "Holds".

**Fix:** Use the status "Superseded by LEDG-08 (restated below)" instead of "Holds".

### B-IN-07: The `databasise.wirings` package-data `"*.json"` pattern now matches nothing

**File:** `databasise/pyproject.toml:160-163`

**Issue:** The rewritten comment says the pattern covers "any wiring JSON at the package root". The only root JSON, the CBM wiring, has moved to `tests/fixtures/`, and `databasise.tests` is not a packaged package. The pattern matches nothing, and the comment describes files that do not exist.

**Fix:** Drop `"*.json"`, or reword the comment as a placeholder for future root wirings.

### B-IN-08: CODEBASE-MAP rows beside the edited row are stale (Phase 16 GUI input)

**File:** `docs/gui/CODEBASE-MAP.md:108, 113-116, 121`

**Issue:** Measured at HEAD:

- `default_registry` holds 37 parts, not 35.
- All six arms are selectable, not "only naive, bypass and local".
- The LightRAG corpus wirings have 2 nodes each, not a "single opaque node".
- `hipporag/base.json` has 14 nodes, not 13. CONTEXT Specifics already flags this for CONN-05.
- `hipporag/corpus-ingest.json` has 8 nodes, and `hipporag/corpus-delete.json` exists (1 node).
- The ledger row omits `open_existing`, `lineage`, `history_for_alias` and `close`, and its line references are stale.

The phase edited line 117 and left these rows unchanged.

**Fix:** Regenerate these rows from the code before Phase 16 plans read the map. Related: A-WR-03.

---

_Reviewed: 2026-10-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
