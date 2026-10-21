---
phase: 14-promotion-ledger
lane: B
reviewed: 2026-10-20T00:00:00Z
depth: deep
diff_base: bb52fbb
files_reviewed: 13
files_reviewed_list:
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
  warning: 3
  info: 8
  total: 11
status: issues_found
---

# Phase 14: Code Review Report (Lane B)

**Reviewed:** 2026-10-20
**Depth:** deep (cross-file: callers in `seam/engine.py`, `seam/promotion.py`; probes run against HEAD)
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Lane B covers the store layer (`Ledger.open_existing`, `close`/context manager, `lineage`,
`history_for_alias`, `LedgerEntry`), the alias selector, `wiring_for_name`, the codebase-memory-mcp
unregistration (D-13) and the LEDG-14 docstring rewrites.

Verified correct:
- The `lineage` walk, and the rollback and retire guards that call it (`engine.py:2546-2555`,
  `2697-2706`). Traced by hand over promote, rollback, retire and re-promote sequences: no
  tombstoned generation becomes reachable through a rollback chain, and a version in the active
  lineage cannot be retired.
- Guard reads and the append share one `BEGIN IMMEDIATE` span. Minted versions rise
  monotonically, because every minting row becomes the next `by_alias` row, so the unique index
  stays unreachable.
- Gate verbs refuse before any `Ledger` construction.
- `_resolve_alias` refuses identically in all three miss cases and names only the alias.
- The selectors capability table in the module docstring matches the code. Probed: all 13
  requests resolve as documented, and node counts are 7/1/17/15/15/14.
- Every wiring and corpus variant parses clean against `default_registry()`, which holds no body-less part.
- `FALSIFIER-2-EVIDENCE.md` and `F-07-MUTABLE-STORE-DISPOSITION.md` re-render byte-identically.
- 161 tests in the ledger, posture, concurrency, rollback, retire and evidence suites pass.

Defects found:
- The Falsifier-2 gate evidence now misstates which registry it was computed against.
- `open_existing`, the "read must not write" path, still writes in three demonstrated cases.
- Through `wiring_for_name`, all three operator verbs refuse on an alias whose active row names a
  wiring that no longer resolves. With an append-only ledger, nothing can ever repair that alias.

No §18 leak was found on any live consumer path. Two latent leak surfaces are recorded as Info.

Process note, not a code defect: the session-start report shows WIRE-17
(`tests/seam/test_refusal_reachability.py`) "check changed after its first failing run". This is
the D-13 owner `grant-check-edit` item, and it is still waiting for the owner's `lock-checks` approval.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: Falsifier-2 gate evidence claims `default_registry()` but is now computed against `probe_registry()`

**File:** `databasise/evidence/falsifier2.py:298-301` (with stale text at 10-13, 15-18, 134-139, 305, 503, 514, 537, 547-550)
**Issue:**
- D-13 changed `_parse` from `default_registry()` to `probe_registry()`. `probe_registry()` is
  `default_registry()` plus `probe/shared-artifact-writer`, `probe/evidence-writer` and
  `codebase-memory-mcp@0.1.0`.
- The rendered, committed `FALSIFIER-2-EVIDENCE.md` still says each named wiring is "Resolved
  against `default_registry()`'s Phase-1 entries" (line 514).
- The verdict says every value "was derived from that wiring's `nodes`/`deps` plus
  `default_registry()` alone" (lines 547-550).
- The probe section says `probe_registry()` is "`default_registry()` plus two probe-only parts"
  (line 537). It now adds three.
- The `probe_registry` docstring still says production `default_registry()` "stays exactly D-04's
  seven entries" (line 137). It holds 37.

This document is the Phase 1→2 gate artifact (Falsifier 2), so its provenance statement is false
as committed. There is also a second effect. W1 and W3 are now parsed against a registry that
contains the two probe-only parts. A named wiring that referenced `probe/shared-artifact-writer@0.1.0`
would previously have failed with `unknown-component`. It now parses and contributes rows to the
"did not fire" verdict.

**Fix:** Parse the named wirings against `default_registry()` plus only the catalogued CBM part,
keep the probe parts for `PROBES`, and render text that names the registry actually used:
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
Then replace "`default_registry()`" with "`evidence_registry()` (`default_registry()` plus the
catalogued `codebase-memory-mcp@0.1.0`)" at lines 503, 514 and 547-550, and "two probe-only parts"
with the actual set at 17 and 537. Drop "D-04's seven entries" at 137. Re-render the evidence file.

### WR-02: `Ledger.open_existing` is not a read-only open; the alias selector's query path writes in three demonstrated cases

**File:** `databasise/ledger/ledger.py:158-167` (via `__init__` 146-156, `_set_wal` 200-207, `_create_schema` 239-313); caller `databasise/seam/selectors.py:295-299`
**Issue:**
- `open_existing` only avoids *creating* `ledger.db`.
- It then runs the full constructor: `PRAGMA journal_mode=WAL`, `CREATE ... IF NOT EXISTS`,
  `DROP INDEX IF EXISTS ix_ledger_generation`, `CREATE UNIQUE INDEX ...` and `commit()`.
- `_resolve_alias` runs on every alias-selected `query`/`compare`/`query_stream`/`ingest`/`delete`
  (`engine.py:1271, 1343, 1636, 1726, 1861, 2065`).

Probed at HEAD (scratchpad `lw.py`):
1. A **zero-byte `ledger.db`** gets the full schema written by an alias query (0 → 24576 bytes).
   Such a file is left behind, for example, by an interrupted first `Ledger()`, because
   `sqlite3.connect` creates the file before any schema exists.
2. A **rollback-journal file** (`journal_mode=DELETE`) is converted to WAL by the read.
3. A **pre-07-05 file** has its index dropped and recreated by the read.

D-08 explicitly accepted case 3 only. Cases 1 and 2 are unacknowledged writes on a consumer read
path, against CONTRACT §6.

The transaction docstring (`ledger.py:220-221`) says opening over an existing schema "never waits
on a writer". That is also false for case 3. The DDL needs the write lock, so during a concurrent
operator verb it can wait up to the 5 s busy timeout, and then fail as a raw
`sqlite3.OperationalError`, which the consumer sees as a 500.

**Fix:** Give the selector a real read-only open. Keep the migrating constructor for rollback and
retire, which write anyway:
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
`_resolve_alias` calls `open_existing(store_root, read_only=True)`. It maps
`sqlite3.OperationalError` ("no such table", which covers the zero-byte case) to the same
`UnsatisfiableSelectorError`. Then correct the `transaction()` docstring.

### WR-03: An alias whose active row names an unresolvable wiring is permanently unrepairable: all three verbs refuse

**File:** `databasise/seam/engine.py:2399-2404` (promote), `2558-2563` (rollback), `2704-2711` (retire); root lookup `databasise/wirings/resolve.py:224-235`, mapped at `engine.py:1121-1131`
**Issue:**
- `_wiring_for_row` turns a `wiring_for_name(...) is None` miss into `UnsatisfiableSelectorError`.
- Promote calls it on `prior_record.mutation_id` before minting.
- Rollback calls it on `current_record.mutation_id`.
- Retire calls it on `active.mutation_id`.
- So once an alias's active row names a name outside `_ARM_NAMES` or `WIRING_NAMES`, every verb
  refuses. The ledger is append-only, so no row can ever be added to repoint that alias, and the
  alias name stays unusable permanently.

The `_wiring_for_row` docstring admits this ("cannot be repaired through promote, rollback or
retire"), but it is a functional defect, not a refusal choice. It is reachable through renames that
the codebase itself anticipates: the `resolve_arm` docstring (`resolve.py:111-112`) foresees
renaming naive's wiring, and any arm removed or renamed from `_ARM_NAMES` triggers it. It also
undercuts D-05's goal: the 500 became a 422, but the operator still has no way out.

**Fix:** In promote, treat an unresolvable prior as unknown surface and keep the version lineage,
so a fresh promote repairs the alias. A changed or unknown surface already mints a MAJOR bump:
```python
prior_resolved = wiring_for_name(prior_record.mutation_id) if prior_record is not None else None
# prior row names a wiring that no longer exists: class against nothing, MAJOR-bump via surface None
```
`mint_version(prior_version, None, new_surface)` must then MAJOR-bump when `prior_version` is set
and `prior_surface` is None. Today it compares `new_surface != None`, which is True, so it already
MAJOR-bumps. Add a test that seeds a row with `mutation_id="retired-arm"` and asserts that promote
succeeds and that the selector then resolves.

## Info

### IN-01: `history_for_alias` returns internal identities with no consumer-safe projection (forward §18 risk)

**File:** `databasise/ledger/ledger.py:123-131, 442-451`
**Issue:** `LedgerEntry` carries `arm_instance_hashes` (internal hashes), `mutation_id` and
`parent` (arm names), and `promotion_trace_ids`. The docstring says "Phase 16's CONN-06/CONN-07
routes read it", but nothing warns that these fields must not cross §18. No product code calls it
today.
**Fix:** State the strip rule in the docstring, or add the consumer projection (alias, versions,
record_kind, id, created_at, change_origin, provenance) here so Phase 16 cannot serialize the raw
entry.

### IN-02: The alias branch does synchronous SQLite I/O on the event-loop thread

**File:** `databasise/seam/selectors.py:295-299`, called from async methods at `engine.py:1271, 1343, 1636, 1726, 1861, 2065`
**Issue:** The connect, WAL pragma, schema DDL and SELECT all run inline on the loop. The ledger
module docstring (lines 74-81) describes the offload discipline for the verbs only. In the WR-02
migration case, the loop can block for up to the 5 s busy timeout.
**Fix:** Offload with `run_in_executor` in the engine's selector call sites. This becomes
negligible once the open is read-only (WR-02).

### IN-03: `f07_report` labels a built component as not built, and its verdict contradicts its qualification

**File:** `databasise/evidence/f07_report.py:94-106, 180-181`; rendered verdict in `F-07-MUTABLE-STORE-DISPOSITION.md`
**Issue:**
- The comment and the tuple name `_CATALOGUED_NOT_BUILT` say these rows project onto "a component
  that does not yet exist", but the CA-2 row is built and admitted (`[code-verified]`).
- The verdict says the disposition is "enforced as an explicit refusal in the comparison path".
  The next paragraph says no live path exists for CBM since it left `default_registry()`.
- `render_f07_record(probe_registry())` raises `ValueError`, because CBM has no `_KNOWN_REASONS`
  entry, for any registry that registers CBM (probed).
- The reversal text says to add a `_KNOWN_REASONS` row, but not to remove the catalogued row.
  Following it would produce a duplicate.

**Fix:** Rename the tuple to `_CATALOGUED_NOT_REGISTERED`, fix the comment, and say "defined, not
live" in the verdict. Have `_live_mutates_store_rows` skip any component already present in the
catalogued rows.

### IN-04: The `declared_only.py` module docstring and `DECLARED_ONLY_PARTS` name are stale

**File:** `databasise/parts_core/declared_only.py:1-5, 22-28, 134`
**Issue:** The docstring still presents CBM as part of the set this module registers ("is admitted
whole-engine", "Every entry this module declares"). `DECLARED_ONLY_PARTS` now holds only the three
corpus parts, and none of them is declaration-only. The registry docstring (`registry.py:210`)
refers readers to "the parts of `parts_core/declared_only.py`", which now excludes a part that
module defines.
**Fix:** Add one docstring sentence: CBM is defined here but excluded from `DECLARED_ONLY_PARTS`
since 14-07. Optionally alias `DECLARED_ONLY_PARTS` to `LIGHTRAG_CORPUS_PARTS`.

### IN-05: Residual enumerating error messages (`known arms`, `registered parts`)

**File:** `databasise/wirings/resolve.py:46-50`; `databasise/parts/registry.py:28-33`
**Issue:** `UnknownArmError` still prints `known arms: [...]`, and `UnknownPartError` prints every
registered part. Neither is consumer-reachable today: every product caller goes through
`wiring_for_name`, which checks membership first, and committed wirings parse clean. D-05 states
that no body contains "known arms". A future caller that passes consumer input to `resolve_arm`
would leak the arm list in a 500 body.
**Fix:** Drop the enumeration from the messages and keep it on an attribute for logs.

### IN-06: PROMOTION-LEDGER-EVIDENCE criterion 3 is marked "Holds" while its literal text no longer holds

**File:** `databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md:31`
**Issue:** The criterion reads "the refusal names the posture". The status cell says the refusal
"names the verb, not a posture", yet still reads "Holds".
**Fix:** Use a status of "Superseded by LEDG-08 (restated below)" rather than "Holds".

### IN-07: The `databasise.wirings` package-data `"*.json"` pattern now matches nothing

**File:** `databasise/pyproject.toml:160-163`
**Issue:** The rewritten comment says the pattern covers "any wiring JSON at the package root",
but the only root JSON (the CBM wiring) moved to `tests/fixtures/`, and `databasise.tests` is not
a packaged package. The pattern is dead and the comment describes a file set that does not exist.
**Fix:** Drop `"*.json"`, or reword the comment as a placeholder for future root wirings.

### IN-08: CODEBASE-MAP rows beside the edited row are stale (Phase 16 GUI input)

**File:** `docs/gui/CODEBASE-MAP.md:108, 113-116, 121`
**Issue:** Measured at HEAD:
- `default_registry` holds 37 parts, not 35.
- All six arms are selectable, not "only naive, bypass and local".
- The LightRAG corpus wirings have 2 nodes each, not "single opaque node".
- `hipporag/base.json` has 14 nodes, not 13. CONTEXT Specifics already flags this for CONN-05.
- `hipporag/corpus-ingest.json` has 8 nodes, and `hipporag/corpus-delete.json` exists (1 node).
- The ledger row omits `open_existing`, `lineage`, `history_for_alias` and `close`, and its line
  references are stale.

The phase edited line 117 and left these.
**Fix:** Regenerate these rows from the code before Phase 16 plans read the map.

---

_Reviewed: 2026-10-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
