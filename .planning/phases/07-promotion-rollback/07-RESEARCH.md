# Phase 7: Promotion & Rollback - Research

**Researched:** 2026-09-11
**Domain:** Append-only promotion ledger, operator-asserted promote/rollback/retire verbs, three-transport seam surface (in-process/REST/MCP)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Scope re-cut (owner decisions, 2026-09-11)**

- **D-01: HARD-04 is deferred, not built.** Owner: *"Unless this testing is required I wanted to
  defer it until the product is built and I do in-depth testing for an entirely different phase."*
  It is not required here: an operator-asserted promotion reads no bundle and carries no verdict
  (CONTRACT §6, RIG §PR.3), so the owner-corpus layer is consumed by nothing in Phase 7 — the
  identical argument `06-GATE-AMENDMENT.md` made for MACH-03. When it does happen: the corpus is a
  smaller subset the owner picks later, and only hashes and an evidence record cross into git
  (documents, questions, gold answers stay in a local-only directory named at mint time; the
  repo is public). Phase 7 builds no coverage check on promote() and no question-authoring tool.
  Reversibility: reversible — `databasise.parity.corpus.load_snapshot` plus
  `databasise.eval.bundle.mint_bundle` already accept any directory, so the later phase mints
  without new machinery.
- **D-02: HARD-01 and HARD-02 are deferred to the same later hardening phase.** Neither is
  consumed by the promote path. Phase 7's requirement set is therefore MACH-07 + API-09. The open
  question of where those edits land (upstream repo and re-mirror, in-place edit with a recorded
  divergence, or project-layer copies — `docs/system-model/` is a verbatim upstream mirror that is
  never edited) travels with the deferral, unresolved.
- **D-03: The deferral is recorded, never silent** — GATE-01's discipline, followed exactly as
  `02-GATE-01-WAIVER.md`, `03-GATE-AMENDMENT.md` and `06-GATE-AMENDMENT.md` did. Planning ships a
  written amendment record in the phase directory that: quotes ROADMAP Phase 7 criteria 4 and 5
  and its requirements line; states the operator-path-consumes-nothing argument; names the point
  of first need for each of HARD-01/02/04 as *the owner's in-depth testing / hardening phase, or
  the first gate-adjudicated promotion, whichever comes first*; and lists the residual risk (every
  promotion in this milestone is provisional and unmeasured on the owner's own data). It authorises
  the tracking edits: ROADMAP Phase 7 requirements → `MACH-07, API-09`; criteria 4–5 struck with a
  pointer to the record; REQUIREMENTS.md rows HARD-01/02/04 gain a dated deferral note and stay
  Pending, checkboxes unchecked, so the milestone audit lists them beside MACH-03 and MODAL-01.
  The later phase does not exist in the roadmap yet — the record names it as the owner's to add
  (`/gsd-phase add`). Reversibility: reversible — a roadmap edit and a dated note.

**Promotion target and the generation record**

- **D-04: The promotion target is derived from `promotion_trace_ids`, never named by the caller.**
  The operator hands promote() the alias, the trace ids they read, and `change_origin`. Each trace
  id resolves through the existing `TraceStore` to a run record naming its wiring; every id must
  resolve, and all must name one wiring, otherwise the call refuses by name (unknown trace,
  disagreeing traces, empty list). That wiring's arm name becomes the record's `mutation_id` —
  exactly the read contract `selectors._resolve_alias` already inherits. This keeps Phase 4 D-11
  (no wiring name, node id or instance hash as seam input) intact on the operator surface and makes
  `promotion_trace_ids` verifiable rather than decorative. Reversibility: costly — the call
  signature crosses all three transports and the conformance tests pin it.
- **D-05: Rollback names an explicit semver target; there is no default "previous".** rollback()
  takes the alias, the semver minted at the generation being returned to, trace ids and
  `change_origin`. It appends a new `operator_asserted` generation record whose `parent` names the
  mutation id being returned to (RIG §PR.2), carrying no new arm run and no verdict, and the alias
  repoints to that generation. An unknown semver, a semver minted under a different alias, or a
  tombstoned target refuses by name.
- **D-06: The semver is minted by the machine at promotion; the operator states nothing about
  versions.** First promotion of an alias mints `1.0.0`. Thereafter, per CONTRACT §0's fixed
  rule: MAJOR when the promoted wiring's declared socket / capability / effects surface differs
  from the prior active generation's; otherwise MINOR. PATCH is never minted on the operator
  path — no measured "bug fix" distinction exists without a gate. Running an arm never mints
  anything (§6). The minted semver is stored on the generation record and is the public handle a
  rollback names. Reversibility: one-way per record — a minted version is a published name under
  §0.4 and is never reused; the rule is a source edit.
- **D-07: Tombstoning is an operator `retire` verb on the same append-only path.** retire()
  appends a tombstone record for a generation (alias + semver, trace ids, `change_origin`, no
  verdict). promote() and rollback() refuse any target whose latest ledger state is tombstoned;
  pins to tombstoned artifacts already refuse per CONTRACT §16.2. No act lifts a tombstone:
  promoting the same wiring again later is a new generation with a new semver, never a
  resurrection (RIG §PR.2, §0.4). This makes SC1's "tombstoned losers are never lifted" real in
  production, not only against a test-seeded row.
- **D-08: `change_origin` is required input on promote, rollback and retire, both values
  accepted.** Absent → refuse by name. `machine_mutation` is accepted as a value even though no
  proposer exists in this milestone, because CONTRACT §7 makes the field orthogonal to
  `promotion_provenance` and the contract is frozen input the seam does not re-litigate. Never
  defaulted, never inferred.

**Verb surface and the posture refusal**

- **D-09: One promote entry point carrying the verb as a closed enum.** promote() takes a `verb`
  covering CONTRACT §5's ladder (`check`, `preview`, `run`, `promote-next`, `promote-now`) plus the
  operator-asserted path. In this milestone only the operator path appends. The others refuse by
  name with the specific reason: promote-next / promote-now at answer-level or index-side class
  → the refusal names the measurement posture and cites RIG §F3.2 (SC3, the load-bearing refusal
  `06-GATE-AMENDMENT.md` depends on); at retrieval-side class → the refusal names the missing
  calibrated A/A floor (RIG §AA.2, MACH-03 Pending), since that class is on by default but no
  floor exists; check / preview / run → refuse as not built in this milestone, by name — no gate
  implementation exists and Phase 7 does not build one. Rollback and retire are their own entry
  points (Phase 4 D-03: one entry per §18 operation). Reversibility: reversible — flipping a
  refusal into a real verb later is additive.
- **D-10: The mutation class is machine-derived; the caller may not state it.** Derived from the
  delta between the promoted wiring and the prior active generation of the alias: any index-recipe
  node differs → `index-side`; any generation / keyword / prompt-bearing node differs →
  `answer-level`; otherwise `retrieval-side`. A first promotion (no prior generation) is classed by
  the wiring's own node set under the same rule. Recorded in the existing `mutation_class` column.
  A caller cannot talk a promotion into a cheaper class. Which node kinds count as index-recipe
  and answer-level is Claude's discretion, anchored on PARTS §L.1 (`embedder-index` is the index
  recipe node) and RIG §CM's three spending moments.
- **D-11: The measurement posture is a module constant the refusal quotes.** One frozen mapping
  class → measurement on/off in the promotion module: retrieval-side on, answer-level and
  index-side off, exactly RIG §F3.2. Refusals quote the entry and cite §F3.2. Flipping a class is
  a source edit, never a runtime flag or a constructor argument, and `06-GATE-AMENDMENT.md` makes
  MACH-03 due at that moment. Reversibility: reversible in code, but the amendment record binds
  the flip to running the A/A calibration first.

### Claude's Discretion

- **Ledger schema additions.** The Phase 1 schema lacks `change_origin` (required by CONTRACT §7
  and SC1), the minted semver, and a record kind (promotion / rollback / tombstone). Add them as
  additive columns exactly as Phase 4 added `alias`; the ledger holds no rows yet, so no migration.
  Keep §7's field enumeration, the `BEFORE UPDATE` / `BEFORE DELETE` triggers, and every derived
  projection (`active_pointer`, `by_alias`, `history`).
- **Atomicity.** The active pointer is a derived query, so one `INSERT` in one transaction *is* the
  atomic alias repoint; SQLite serialises racing promotions into two ordered rows and the later
  one wins, exactly RIG §PR.1's concurrent-promotion reading. No second write is needed and none
  may be introduced.
- **Async call site.** `Ledger` is synchronous by deliberate exception (`ledger.py` WR-03 note);
  offload `append()` with `run_in_executor` at the seam's async call site, as that note directs.
- **Names and shapes.** Entry-point names, refusal exception types, REST paths, MCP tool names,
  and the promote / rollback / retire response shape — which must obey §18.2's closed set: alias,
  minted semver, provenance, generation ordinal, never a wiring name, node id or instance hash.
  Three-transport parity proven by conformance test (Phase 4 D-17, Phase 5 MCP parity).
- **Trace → wiring resolution.** How a trace token's run record yields the arm name, using
  `TraceStore` and `wirings.resolve` as they stand.
- **Alias lifecycle.** First promotion creates the alias. Whether an alias itself can be retired is
  not required and not asked for.
- **Amendment record shape and file name**, following the three existing gate records.
- **Test scope.** Per the owner's standing posture: tests that prove the refusals and the
  never-lifted rule are in scope; nothing beyond what the decisions above need.

### Deferred Ideas (OUT OF SCOPE)

- **HARD-04 — owner's corpus into the eval bundle** → the owner's later in-depth testing /
  hardening phase (not yet on the roadmap). Shape already agreed: a small owner-picked subset,
  local-only directory named at mint time, hashes and evidence only in git. Open when it runs: who
  authors questions / gold answers / gold document ids, and whether promote() should then refuse
  without bundle coverage.
- **HARD-01 — gate-script vacuous-pass sites** (parts-check.sh: 5 extraction sites; anatomy-check.sh:
  1 site guarding 3 checks) → same later phase. Open: where the fix lands given the never-edited
  mirror.
- **HARD-02 — ANATOMY §F rows lacking landed-repair pointers + stale cross-document rows (DR-06)**
  → same later phase, same open where-it-lands question.
- **A new roadmap phase** for that hardening / in-depth testing pass, holding HARD-01/02/04, the
  MACH-03 A/A spend, MODAL-01's two owner items, and the Phase 6 UAT refresh — the owner's to add.
- **The gate-adjudicated promotion path itself** (§5 gate, eight verdicts, floor consumption) →
  outside this milestone under MACH-09; the first such promotion is MACH-03's point of need.
- **Batch promotion (RIG §PR.4)** and the mutation proposer (MUTPROP) → not v1.
- **Alias retirement** (retiring an alias, not a generation) → not asked for.
- **Coverage recorded on the generation record** (which bundle, if any, covered the corpus) →
  revisit with HARD-04.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MACH-07 | Append-only promote/rollback ledger per CONTRACT §7 + RIG §PR: `change_origin`/`promotion_provenance` required on every generation record, never defaulted/inferable; non-empty `promotion_trace_ids` on operator promotions; ledger append is the decision; alias repoint atomic; semver minted only at promotion; tombstoned losers never lifted; active pointer always a derived query | `## Architecture Patterns`, `## Code Examples`, `## Common Pitfalls` — the existing `Ledger`/`LedgerRecord` (`databasise/ledger/ledger.py`) is fully read and quoted; additive-column plan given; §6/§7 quoted verbatim below |
| API-09 | Caller promotes/rolls back a wiring via RIG §PR.3's operator path: `promotion_provenance: operator_asserted` with non-empty `promotion_trace_ids`, no `verdict`/`tier-of-decision`; promote-next/promote-now unavailable for answer-level/index-side under default posture (MACH-09) | `## Architecture Patterns` (three-transport thin-adapter pattern from `rest.py`/`mcp/server.py`), `## Validation Architecture`, refusal vocabulary in `## Code Examples` |
| HARD-04 | Owner's own corpus into the eval bundle before any promotion decision | `## Amendment Record Requirements` below — Phase 7 does not build this; research supports only the amendment record's point-of-first-need and residual-risk statements |
| HARD-01 | Gate-script vacuous-pass sites | `## Amendment Record Requirements` below — same treatment |
| HARD-02 | ANATOMY §F / PARTS Appendix A reconciliation | `## Amendment Record Requirements` below — same treatment |
</phase_requirements>

## Summary

Phase 7 adds three new operator-invoked verbs — `promote`, `rollback`, `retire` — to the
`Databasise` seam object, reachable in-process and through the REST and MCP transports Phase 4/5
already stood up. All three append to the same SQLite-backed, append-only `Ledger`
(`databasise/ledger/ledger.py`) Phase 1 built and Phase 4 gave an `alias` column; none of them run
a wiring, call an LLM, or consume the eval bundle. The read side of this contract already exists
and is already tested: `databasise.seam.selectors._resolve_alias` reads `Ledger.by_alias(alias)`
and resolves the returned record's `mutation_id` as an arm name via `resolve_arm` —
`databasise/tests/seam/test_alias_registry.py` proves this read path today by hand-appending a
`LedgerRecord` through `Ledger.append()`, which is exactly the shape `promote()` must produce for
real. The ledger schema itself is missing three things CONTRACT §7/§0 require on every generation
record: `change_origin` (`human_edit`/`machine_mutation`), a minted semver string, and a record
kind (promotion/rollback/tombstone) — all three are additive columns on an empty table (no rows
exist yet in production, so no migration is needed), following exactly the precedent Phase 4 set
when it added `alias`.

The three verbs are refusal-heavy by design: `promote()` must refuse an unresolvable, disagreeing,
or empty `promotion_trace_ids` list; a tombstoned target; and — per the CONTEXT.md D-09 verb-ladder
requirement — every gate-adjudicated verb (`check`/`preview`/`run`/`promote-next`/`promote-now`)
with a class- and posture-specific reason quoting RIG §F3.2/§AA.2. This refusal vocabulary follows
the codebase's own established house style exactly: every refusal in `databasise/seam/refusals.py`
is a typed `SeamRefusalError` subclass naming only the consumer's own input, mapped generically by
`rest.py`'s single `add_exception_handler(SeamRefusalError, ...)` and `mcp/server.py`'s single
`_refusal_mapped` wrapper — no per-route or per-tool exception handling is needed for whatever new
refusal types Phase 7 adds; they are picked up automatically by both transports' existing
`SeamRefusalError.__subclasses__()` walks.

No new external package is needed. Semver minting is a two-branch rule (first promotion → `1.0.0`;
thereafter MAJOR iff the declared effects/socket surface changed, else MINOR) simple enough to
hand-roll as a small dataclass — there is no `semver`/`packaging` dependency anywhere in
`pyproject.toml` today, and importing one for a two-branch integer bump would be over-engineering
for what is a five-line comparison against `selectors._wiring_effects`'s existing union.

**Primary recommendation:** Extend `LedgerRecord`/`Ledger` with additive `change_origin`,
`minted_version`, and `record_kind` columns; add `promote()`/`rollback()`/`retire()` to
`Databasise` following `ingest()`/`delete_document()`'s established direct-dispatch shape (resolve
trace ids → validate → construct `LedgerRecord` → `Ledger.append()` in a `run_in_executor` call);
add three matching REST routes and three matching MCP tools as thin adapters exactly like every
existing operation; and write the deferral amendment record (HARD-01/02/04) following
`06-GATE-AMENDMENT.md`'s exact section structure before requesting sign-off.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Append-only promotion ledger (schema, triggers, projections) | Machine / Backend (embedded SQLite) | — | `databasise/ledger/ledger.py` — durable state, no store server; CONTRACT §7 governs the schema |
| Trace-id → wiring resolution | Machine / Backend | — | `databasise.seam.trace_store.TraceStore` + `databasise.wirings.resolve` — pure in-process lookup, no I/O beyond SQLite |
| promote/rollback/retire verbs | API / Backend (seam) | — | New `Databasise` methods; this is the seam's write surface, same tier as existing `ingest()`/`delete_document()` |
| Mutation-class + posture refusal | API / Backend (seam) | — | Pure computation over already-resolved wirings (`_wiring_effects`) plus a module constant; no store or network dependency |
| REST/MCP transport | API / Backend (thin adapter) | — | `databasise/seam/rest.py`, `databasise/mcp/server.py` — deserialize → await engine method → return, no logic |
| Amendment record (HARD-01/02/04 deferral) | Docs/Planning (project layer) | — | `.planning/phases/07-promotion-rollback/` — never `docs/system-model/`, which is a verbatim upstream mirror |

No browser, CDN, or external-DB tier is implicated: EMBED-01 already locks this project to an
embedded, in-process SQLite/Cozo/Faiss stack with no external servers, and Phase 7 introduces no
new tier.

## Standard Stack

### Core

No new library dependency is required for MACH-07/API-09. Every mechanism Phase 7 needs already
exists in `databasise/pyproject.toml`'s committed dependency set:

| Library | Version (installed) | Purpose | Why Standard (for this repo) |
|---------|---------|---------|--------------|
| `pydantic` | `>=2.0,<3.0` [VERIFIED: databasise/pyproject.toml:20] | Request/response DTOs (`_StrictModel`/`_RequestModel`/`_ToolArgs` pattern) | Already the strict-model base every seam DTO in this repo inherits; a new `PromotionResult`/`PromoteRequest` follows the identical pattern |
| stdlib `sqlite3` | 3.12 runtime | Ledger append/read | `Ledger` already uses it directly; additive columns need no new tooling |
| `jsonpatch` | unpinned range [VERIFIED: databasise/pyproject.toml:32] | Not directly needed by Phase 7, but already a dependency the wirings-resolution path (`resolve_arm`) uses when comparing prior/new wirings if a diff-by-patch approach is chosen | Already vetted (03-01-SUMMARY.md) |

### Supporting

None needed. `asyncio.get_running_loop().run_in_executor` (stdlib) is the only new call-site
pattern, mirroring `ledger.py`'s own WR-03 docstring instruction and `stores/kv.py`'s existing
`run_in_executor` precedent elsewhere in this codebase.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled 2-branch semver mint (`1.0.0`, MAJOR/MINOR bump) | `semver` (PyPI) or `packaging.version` | Both are general-purpose semver *parsers/comparators* for arbitrary version strings; Phase 7 only ever mints its own strings from a MAJOR/MINOR counter it owns — pulling in a dependency to parse strings this codebase itself produces is unneeded indirection for a five-line rule. Not recommended. |

**Installation:** No `uv sync` change needed; no new package.

**Version verification:** N/A — no new package is being added. Existing pins (`pydantic`, `jsonpatch`) were verified in prior phases per `01-01-SUMMARY.md`/`03-01-SUMMARY.md` and are unchanged.

## Package Legitimacy Audit

**No external packages are introduced by this phase.** The Package Legitimacy Gate protocol is
therefore not run — there is nothing to check. If the plan or execution later decides a semver
library is wanted after all, run `gsd_run query package-legitimacy check --ecosystem pypi semver`
(or `packaging`) before adding it to `pyproject.toml`, per this project's own package-legitimacy
history in `03-01-SUMMARY.md`/`06-CHECKPOINT-ANSWERS.md`.

**Packages removed due to [SLOP] verdict:** none — none proposed.
**Packages flagged as suspicious [SUS]:** none — none proposed.

## Architecture Patterns

### System Architecture Diagram

```
Operator (CLI / test / owner)
        │
        │ promote(alias, trace_ids, change_origin)
        │ rollback(alias, semver, trace_ids, change_origin)
        │ retire(alias, semver, trace_ids, change_origin)
        ▼
┌───────────────────────────────────────────────────────────────────┐
│  Databasise (databasise/seam/engine.py) — one entry point per verb │
│                                                                     │
│  1. Resolve each trace id → run record  (TraceStore.resolve)       │
│     ── all ids must name ONE wiring's arm  → else refuse           │
│  2. Compute mutation_class from wiring diff vs. prior active gen.  │
│     (index-side / answer-level / retrieval-side)                   │
│  3. [promote-next/-now/check/preview/run only] refuse by posture   │
│     — RIG §F3.2 module-constant lookup, never reached by promote() │
│  4. Refuse if target generation is tombstoned (rollback/retire)    │
│  5. Mint semver (promote/rollback only; retire mints none)         │
│  6. Construct LedgerRecord (operator_asserted, change_origin,      │
│     promotion_trace_ids, mutation_class, minted_version, kind)     │
│  7. Ledger.append(record)  ── the ledger append IS the decision    │
└───────────────────────────────────────────────────────────────────┘
        │                                          ▲
        │ INSERT (SQLite, WAL)                     │ SELECT ... ORDER BY id DESC LIMIT 1
        ▼                                          │  (active_pointer / by_alias — never a
┌───────────────────────────┐                      │   written "current" column)
│ ledger.db (append-only,   │──────────────────────┘
│ BEFORE UPDATE/DELETE      │
│ triggers RAISE(ABORT))    │
└───────────────────────────┘
        ▲
        │ read, at query time, by every future selector(alias=...) call
        │ (databasise.seam.selectors._resolve_alias — already built, Phase 4)
        │
┌───────────────────────────────────────────────────────────────────┐
│  Three thin transports, all calling the identical engine methods:  │
│  in-process → REST (POST /promote, /rollback, /retire)             │
│              → MCP (tool "promote"/"rollback"/"retire",             │
│                or folded into existing verb-ladder tool naming)     │
│  One shared SeamRefusalError → 422 (REST) / ToolError (MCP)         │
└───────────────────────────────────────────────────────────────────┘
```

A reader traces the primary use case end to end: an operator supplies trace ids read from prior
`query()` calls (via `resolve_trace`), the engine resolves them to one wiring, computes the
mutation class and (for promote) checks the posture, constructs a fully-populated `LedgerRecord`,
and appends it — the append is the only write, and every future read of the alias (any consumer's
`query(selector=Selector(alias=...))`) is a pure derived SELECT over the same table.

### Recommended Project Structure

No new top-level module is needed; every addition lands inside existing modules and their test
directories:

```
databasise/
├── ledger/
│   └── ledger.py            # add change_origin, minted_version, record_kind columns (additive)
├── seam/
│   ├── engine.py            # add Databasise.promote()/rollback()/retire()
│   ├── refusals.py          # add new SeamRefusalError subclasses (trace/class/posture/tombstone)
│   ├── promotion.py         # NEW (recommended): mutation-class derivation, posture constant,
│   │                        #   semver mint rule — kept out of engine.py to mirror how
│   │                        #   selectors.py/compare.py are already split out as focused modules
│   ├── rest.py               # add POST /promote, /rollback, /retire routes
│   └── envelope.py / a new promotion-result model  # §18.2 closed response shape
├── mcp/
│   ├── server.py             # add promote/rollback/retire tools
│   └── tools.py              # add PromoteToolArgs/RollbackToolArgs/RetireToolArgs
└── tests/
    ├── ledger/test_ledger.py           # extend for new columns
    ├── seam/test_promote.py            # NEW
    ├── seam/test_rollback.py           # NEW
    ├── seam/test_retire.py             # NEW
    ├── seam/test_promotion_posture.py  # NEW — SC3's refusal-by-name
    ├── seam/test_dual_transport.py     # extend for the three new verbs
    └── mcp/test_tool_growth_invariant.py  # extend TOOL_NAMES expectation
```

### Pattern 1: Trace-id → single-wiring resolution (D-04)

**What:** Every trace id in `promotion_trace_ids` must resolve through the already-built
`TraceStore` to a run record; the resolved records' wirings must all agree on exactly one arm name,
which becomes `mutation_id`.
**When to use:** At the top of `promote()`/`rollback()`/`retire()`, before any other validation.
**Example (existing code this pattern must reuse verbatim):**
```python
# Source: databasise/seam/trace_store.py (read this session)
async def resolve_trace(self, trace_reference: str, *, debug: bool = False) -> dict[str, Any]:
    record = self._trace_store.resolve(trace_reference)   # raises UnknownTraceReferenceError
    ...

# Source: databasise/wirings/resolve.py (read this session)
def resolve_arm(arm_name: str) -> dict[str, Any]:
    base = load_base()
    patch_doc = json.loads(_patch_path(arm_name).read_text(encoding="utf-8"))
    return jsonpatch.apply_patch(base, patch_doc["operations"], in_place=False)
```
A `RunRecord.to_dict()` (persisted by `TraceStore.persist`) carries `wiring_id`/`arm_id` fields
(`databasise/runner/trace.py`'s `RunRecord`, constructed in `engine.py::_execute` — see the
`RunRecord(... wiring_id=wiring_id, arm_id="seam", ...)` call read this session at
`databasise/seam/engine.py:993-1007`) — `promote()` reads `arm_id`/`wiring_id` off each resolved
trace record (never a caller-supplied wiring name, per Phase 4 D-11) to determine the single
target arm.

### Pattern 2: Additive ledger columns, no migration (Phase 4 precedent)

**What:** Add `change_origin TEXT NOT NULL`, `minted_version TEXT`, `record_kind TEXT NOT NULL`
(`"promotion" | "rollback" | "tombstone"`) columns to the existing `ledger` table.
**When to use:** This is the only schema change MACH-07 requires.
**Example (the exact precedent to follow, read this session):**
```python
# Source: databasise/ledger/ledger.py:23-33 (module docstring, read this session)
# "A small, additive `alias TEXT` column, distinct from `mutation_id` ... The registry is empty
#  until Phase 7's promote path appends the first row" — the identical situation MACH-07's three
#  new columns are in: the table holds zero rows in every environment today (Phase 1's own scope
#  fence: "Nothing in the runner calls append()"), so CREATE TABLE's own column list can be edited
#  directly with no ALTER TABLE / backfill needed.
CREATE TABLE IF NOT EXISTS ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mutation_id TEXT NOT NULL,
    mutation_class TEXT NOT NULL,
    ...
    alias TEXT,
    -- Phase 7 additions, same pattern:
    change_origin TEXT NOT NULL,
    minted_version TEXT,
    record_kind TEXT NOT NULL,
    created_at TEXT NOT NULL
)
```
Confirm no production data exists before treating this as migration-free: `Ledger.__init__` always
calls `CREATE TABLE IF NOT EXISTS`, and every store root Phase 7 will run against in tests and in
this milestone is freshly created per-test (`tmp_path`-derived `store_root` fixture,
`databasise/tests/conftest.py:32-36`, read this session) — there is no persistent production
store yet in this milestone.

### Pattern 3: Refusal typing and dual-transport mapping (already proven, reuse unchanged)

**What:** Every new refusal is a `SeamRefusalError` subclass in `databasise/seam/refusals.py`,
naming only the consumer's own input.
**When to use:** For every new failure mode: unresolved/disagreeing/empty trace ids; a tombstoned
promote/rollback/retire target; a gate-verb refused by posture; a gate-verb refused as "not built".
**Example (verified: both transports pick up new subclasses with zero additional code):**
```python
# Source: databasise/seam/rest.py:211 (read this session)
app.add_exception_handler(SeamRefusalError, _refusal_response)   # generic, vars(exc) dump

# Source: databasise/mcp/server.py:91-104 (read this session)
def _refusal_mapped(fn):
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except SeamRefusalError as exc:
            raise ToolError(json.dumps(_refusal_detail(exc))) from exc
    return wrapper
```
`databasise/tests/seam/test_rest_transport.py` (read this session, lines ~387-475) walks
`SeamRefusalError.__subclasses__()` transitively and asserts every subclass maps to a non-2xx
response — a new refusal class Phase 7 adds is *automatically* covered by that existing
parametrized test as long as a corresponding entry is added to that test's own
`_REFUSAL_FACTORIES` dict (a required addition, not automatic).

### Anti-Patterns to Avoid

- **Inventing a second selector vocabulary for "which wiring to promote":** D-04 already settled
  this — the target is derived from `promotion_trace_ids`, never a caller-supplied wiring/arm name.
  Accepting an explicit arm-name parameter on `promote()` would violate Phase 4 D-11 and would need
  to be refused, not built.
- **A runtime flag for the measurement posture:** D-11 requires the posture to be a source-level
  module constant. A `--force` flag or constructor argument that flips it would make
  `06-GATE-AMENDMENT.md`'s residual-risk framing false (that MACH-03 becomes due "at that moment").
- **A second, ORM-style migration mechanism for the ledger:** the table is empty; `CREATE TABLE IF
  NOT EXISTS`'s own column list can just be edited. Building `alembic`-style versioned migrations
  for a zero-row table is unrequested infrastructure.
- **Writing the current alias/generation to a separate mutable column "for fast lookup":** CONTRACT
  §6 and this codebase's own `active_pointer`/`by_alias` precedent are explicit that the active
  pointer MUST be a derived query, never an independently-writable field. A cache column would
  reintroduce exactly the two-sources-of-truth bug §6 exists to prevent.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RFC 6902 wiring diffing (if used to detect index-recipe/answer-level node changes for D-10's class derivation) | A hand-rolled JSON diff walker | `jsonpatch` (already a dependency) generating a patch between the prior resolved wiring and the newly promoted one, or simpler: compare `_wiring_effects()`/node-id-set deltas directly | `jsonpatch` already handles JSON-Pointer edge cases this codebase explicitly avoided hand-rolling in Phase 3 (`wirings/resolve.py`'s own docstring: "a hand-rolled version goes quietly wrong") |
| Append-only table enforcement | Application-level "don't call update/delete" convention | SQLite `BEFORE UPDATE`/`BEFORE DELETE` triggers (already built, `ledger.py:126-144`) | Already proven database-level enforcement; Phase 7 adds columns, not a new enforcement mechanism |
| Cross-transport refusal mapping | A per-route/per-tool `try/except` for each new refusal type | The existing generic `SeamRefusalError` → `_refusal_response`/`_refusal_mapped` handlers | Already generic over `vars(exc)`; adding a new refusal subclass needs zero transport-layer code changes |

**Key insight:** Nearly everything Phase 7 needs mechanically (append-only enforcement, refusal
typing, transport thin-adapters, alias read-path) was already built by Phases 1/4/5 specifically
*for* Phase 7 to consume — the phase's own job is almost entirely the write path (three new
`Databasise` methods, three additive columns, three refusal types, three routes, three tools) over
machinery that already exists and is already tested from the read side.

## Runtime State Inventory

Not applicable — Phase 7 is not a rename/refactor/migration phase. The ledger schema change is a
column *addition* to a table that holds zero rows in every environment this milestone runs in
(Phase 1's own scope fence states nothing in the runner path calls `append()` yet; the alias
registry itself is stated empty as of Phase 4/6). There is no stored data, live service config,
OS-registered state, secret/env-var rename, or build artifact affected by this phase.

## Common Pitfalls

### Pitfall 1: Treating `promotion_trace_ids` resolution as resolving to a value rather than refusing on disagreement

**What goes wrong:** A promote call whose trace ids happen to belong to two different wirings (a
copy-paste of an old trace id alongside a fresh one) silently uses whichever record's `arm_id`
happens to be read last, promoting the wrong wiring.
**Why it happens:** `TraceStore.resolve()` returns a plain dict per id; without an explicit
all-ids-must-agree check, the natural "take the first/last" implementation hides a caller mistake.
**How to avoid:** Resolve every id, collect the distinct `arm_id`/`wiring_id` values, and refuse
(naming the disagreeing ids, never their resolved wiring) unless exactly one distinct value exists.
**Warning signs:** A promote test with two trace ids from different queries passes silently instead
of raising.

### Pitfall 2: Minting a semver from `count(*)` rows instead of the prior *active* generation

**What goes wrong:** Using `len(ledger.history(mutation_id))` (or a similar row count) to decide
MAJOR/MINOR conflates "how many times has this mutation_id ever been promoted" with "what did the
alias's currently active generation declare." A rollback followed by a new promotion would then
mint a version number disconnected from the semantic MAJOR/MINOR rule CONTRACT §0 states (which
compares *declared surface*, not append count).
**Why it happens:** Row count is the easiest available number in the ledger; the correct comparison
requires resolving the prior generation's own resolved wiring and diffing its effects/socket
surface against the new one.
**How to avoid:** Read `Ledger.by_alias(alias)` for the prior active record (if any), resolve its
`mutation_id` to a wiring via `resolve_arm`, and diff via `selectors._wiring_effects` (or an
equivalent socket/capability comparison) against the newly promoted wiring — first promotion (no
prior record) always mints `1.0.0` regardless of effects.
**Warning signs:** A rollback-then-repromote sequence mints an unexpected version number that
doesn't reflect an actual capability change.

### Pitfall 3: Forgetting the cross-field rule when constructing a `gate_adjudicated`-shaped record by accident

**What goes wrong:** CONTRACT §6 requires `promotion_trace_ids` non-empty **iff**
`promotion_provenance == "operator_asserted"`. Since Phase 7 only ever constructs
`operator_asserted` records, a bug that leaves `promotion_trace_ids` empty (e.g. an off-by-one in
trace collection) produces a record that is representable but invalid under the contract, and
nothing at the SQLite layer catches it — `Ledger.append()` has no cross-field CHECK constraint.
**Why it happens:** SQLite's schema enforces column-level `NOT NULL`, not cross-field invariants;
the contract's "non-empty iff operator_asserted" rule must be enforced in Python before `append()`
is called.
**How to avoid:** Refuse at the top of `promote()`/`rollback()` if `promotion_trace_ids` is empty,
before touching the ledger at all — this is also D-04's own literal requirement ("all must name one
wiring... otherwise the call refuses"), so the same check discharges both.
**Warning signs:** A test constructing `LedgerRecord` directly (bypassing `promote()`) with an
empty `promotion_trace_ids` and `operator_asserted` provenance succeeds when it should be
impossible to reach through the real seam.

### Pitfall 4: A tombstone check that only looks at the exact target row, not "the latest ledger state for that mutation/alias"

**What goes wrong:** CONTRACT §16.2/RIG §PR.2 say a pin (and, by this phase's own extension,
promote/rollback) must refuse a target "whose latest ledger state is tombstoned" — checking only
whether *a* tombstone record exists anywhere in history is wrong if a later, non-tombstone record
re-promotes the same `mutation_id` (D-07: "promoting the same wiring again later is a new
generation... never a resurrection of the tombstoned one" — that new generation is *not* itself
tombstoned).
**Why it happens:** `Ledger.history()` returns every record; naively checking "was this
mutation_id/alias ever tombstoned" instead of "what is the *latest* record's kind" produces false
refusals for a legitimately re-promoted wiring.
**How to avoid:** Check the latest record for the specific target (by semver for rollback/retire,
by resolved mutation_id for promote) via a query shaped like `active_pointer`/`by_alias` — order by
`id DESC LIMIT 1` — never a "does a tombstone exist anywhere in history" scan.
**Warning signs:** A wiring tombstoned once and later legitimately re-promoted becomes permanently
unpromotable.

### Pitfall 5: Building the posture refusal as a runtime branch that reads a settings object

**What goes wrong:** D-11 requires the posture to be a source-level module constant so that
flipping it is a code change, never a config/env value — a settings-driven implementation would
make it trivially flippable without triggering `06-GATE-AMENDMENT.md`'s "MACH-03 due at that
moment" consequence, defeating the whole point of the amendment's residual-risk framing.
**How to avoid:** Define the class→posture mapping as a literal dict constant in the promotion
module (mirroring how `_ACCOUNTABLE_STORE_EFFECT_PREFIXES`/`_ARM_NAMES` are declared as module
constants elsewhere in this codebase), never read from `.env`, `config.json`, or a constructor
parameter.
**Warning signs:** A test can flip the posture via an environment variable or a `Databasise(...)`
constructor argument.

## Code Examples

### Existing read-path this phase's write-path must satisfy (verbatim, read this session)

```python
# Source: databasise/seam/selectors.py:244-269 (databasise.seam.selectors._resolve_alias)
def _resolve_alias(alias: str, *, store_root: str | Path) -> dict[str, Any]:
    ledger = Ledger(store_root)
    record = ledger.by_alias(alias)
    if record is None:
        raise UnsatisfiableSelectorError(selector_kind="alias", requested=alias)
    return resolve_arm(record.mutation_id)
```

### Existing append-only enforcement (verbatim, read this session — no change needed)

```python
# Source: databasise/ledger/ledger.py:126-144
CREATE TRIGGER IF NOT EXISTS trg_ledger_no_update
BEFORE UPDATE ON ledger
BEGIN
    SELECT RAISE(ABORT, 'ledger is append-only: UPDATE is refused');
END
```

### Existing LedgerRecord field set that MACH-07's additive columns extend (verbatim, read this session)

```python
# Source: databasise/ledger/ledger.py:57-77
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
    # Phase 7 additions (this session's recommendation, not yet in the file):
    # change_origin: str            (NOT NULL — "human_edit" | "machine_mutation")
    # minted_version: str | None    (semver string; None only for a retire/tombstone record)
    # record_kind: str              (NOT NULL — "promotion" | "rollback" | "tombstone")
```

### Existing three-transport thin-adapter shape to copy for the three new verbs (verbatim, read this session)

```python
# Source: databasise/seam/rest.py:260-262 (the pattern every new route follows)
@app.post("/documents")
async def post_documents(body: IngestRequest) -> IngestJob:
    return await engine.ingest(body.document, body.selector)

# Source: databasise/mcp/server.py:215-219 (the pattern every new tool follows)
@server.tool(name="delete")
@_refusal_mapped
async def delete_tool(args: DeleteToolArgs) -> dict[str, Any]:
    outcome = await engine.delete_document(args.document_id, args.selector)
    return outcome.model_dump()
```

## State of the Art

Not applicable in the usual "library version drift" sense — this phase's domain is entirely
project-internal (CONTRACT.md/RIG.md are frozen, ratified inputs, not external libraries with
release cadences). The one place a "current approach" question could arise — whether to use a
semver-parsing library — is answered above under Don't Hand-Roll: neither is warranted for this
codebase's minimal two-branch minting rule.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A new `databasise/seam/promotion.py` module (mutation-class derivation, posture constant, semver mint rule) is the right factoring, separate from `engine.py` | Recommended Project Structure | Low — this is a pure code-organization recommendation; the planner may instead inline this logic in `engine.py` without violating any contract clause. Flagged as `[ASSUMED]` because it is a design preference, not a requirement. |
| A2 | `record_kind` (`"promotion"`/`"rollback"`/`"tombstone"`) is a distinct new column, separate from the existing `verdict`/`mutation_class` fields | Pattern 2 / Code Examples | Medium — CONTRACT §7 does not name a `record_kind` field explicitly; it is inferred as necessary to distinguish a promotion generation from a rollback generation from a tombstone record when reading history. If the planner instead encodes this via `verdict` values or a convention on `parent`/`minted_version` being null, that is an equally valid discretionary choice per CONTEXT.md's "Names and shapes" discretion note. |
| A3 | Which specific node ids count as "index-recipe" (→ `index-side` class) and "generation/keyword/prompt-bearing" (→ `answer-level` class) beyond the two anchors already confirmed in code (`embedder-index` for index-side per PARTS §L.1; `generate`/`keywords` as LightRAG's own answer-level nodes, visible in `engine.py`'s `_inject_query` docstring) is not fully enumerated for HippoRAG's node set in this research | D-10 / Pattern discussion | Medium — CONTEXT.md explicitly marks this "Claude's Discretion," so under-specification here is expected and intentional, not a gap to treat as blocking. The planner should enumerate the exact node-id sets for both wiring families (`lightrag`, `hipporag`) as a first planning task, reading `databasise/wirings/lightrag/base.json` and `databasise/wirings/hipporag/base.json` directly rather than inferring from this research. |

**If this table is empty:** N/A — see rows above. All contract-text quotations in this document
(`CONTRACT.md`/`RIG.md` sections) are `[VERIFIED: docs/system-model/CONTRACT.md]` /
`[VERIFIED: docs/system-model/RIG.md]` — read directly this session with the quoted line ranges
shown in `## Sources` below. All codebase claims are `[VERIFIED: <path>:<lines>]` — every file
this document cites was opened with `Read` this session, not grepped.

## Open Questions

1. **Does `promote()`'s single `verb` enum parameter (D-09) return a normal value or raise for the
   four gate-ladder verbs it refuses (`check`/`preview`/`run`/`promote-next`/`promote-now`)?**
   - What we know: D-09 says each refuses "by name," which this codebase's house style means "raises
     a typed `SeamRefusalError`," never a normal return value carrying an error field.
   - What's unclear: whether `check`/`preview`/`run` (refused as "not built") should be three
     separate refusal types or one shared "`VerbNotImplementedError`" naming the verb.
   - Recommendation: one shared refusal type parameterized by `verb`, mirroring how
     `UnsatisfiableSelectorError` is parameterized by `selector_kind` — avoids four near-identical
     exception classes for the same "not built" fact.

2. **Does `retire()` require a resolved trace-id set naming the target generation's own wiring, or
   may it accept trace ids naming any run at all (since retiring doesn't run anything)?**
   - What we know: D-07 says retire() takes "the alias + semver, trace ids, `change_origin`" but
     does not state whether the trace ids must resolve to the specific generation being retired.
   - What's unclear: CONTRACT §6/RIG §PR.3's operator-path language ("trace ids the operator read
     to form the promotion judgment") is written for promote/rollback, where the judgment is about
     *which wiring to activate*; a retire's judgment is "this generation should stop being
     eligible," which may reasonably be formed by reading traces of *any* run demonstrating the
     problem, not necessarily a run of the exact tombstoned generation.
   - Recommendation: apply the same non-empty-and-must-resolve check for consistency and the
     simplest, most uniform refusal vocabulary across all three verbs, but do not require the
     resolved wiring to match the retirement target — flag this as a planning-time confirmation
     checkpoint rather than a locked design decision, since CONTEXT.md does not settle it.

3. **Should the REST/MCP surface add exactly three new operations (`promote`/`rollback`/`retire`),
   or fold rollback and retire into one "generation-lifecycle" endpoint/tool with a scope field
   (mirroring the existing `status`/`resolve` scope-dispatch pattern in `mcp/server.py`)?**
   - What we know: Phase 4 D-03 ("one entry per §18 operation") is quoted in CONTEXT.md as binding;
     CONTEXT.md's own discretion note says "Rollback and retire are their own entry points (Phase 4
     D-03: one entry per §18 operation)" — this reads as already answered: three separate entries.
   - What's unclear: nothing significant; included here only to flag that the `status`/`resolve`
     scope-dispatch precedent in `mcp/server.py` is available but explicitly NOT the intended
     pattern for these three verbs, per the CONTEXT.md quote above.
   - Recommendation: three separate REST routes and three separate MCP tools, following D-03
     literally; do not scope-dispatch.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2+ with pytest-asyncio 1.2+ [VERIFIED: databasise/pyproject.toml dev group] |
| Config file | `databasise/pyproject.toml` `[tool.pytest]`/dependency-groups section (no separate `pytest.ini`) |
| Quick run command | `cd databasise && uv run pytest -q tests/ledger tests/seam -x` |
| Full suite command | `cd databasise && uv run pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MACH-07 (SC1) | Every generation record carries `change_origin` and `promotion_provenance`, never defaulted | unit | `pytest tests/ledger/test_ledger.py -k change_origin -x` | ❌ Wave 0 — extend `test_ledger.py` |
| MACH-07 (SC1) | Semver minted only at promotion, MAJOR/MINOR rule correct | unit | `pytest tests/seam/test_promote.py -k semver -x` | ❌ Wave 0 |
| MACH-07 (SC1) | Tombstoned losers never lifted (re-promotion is a new generation, not a resurrection) | unit | `pytest tests/seam/test_retire.py -k never_lifted -x` | ❌ Wave 0 |
| MACH-07 (SC1) | Active pointer is a derived query, not a written field | unit (regression) | `pytest tests/ledger/test_ledger.py -k active_pointer -x` | ✅ existing `test_ledger.py` covers `active_pointer`/`by_alias` already; extend for new columns |
| API-09 / MACH-07 (SC2) | promote()/rollback() with `operator_asserted` provenance and non-empty `promotion_trace_ids`, no verdict/tier-of-decision; ledger append is atomic | unit + integration | `pytest tests/seam/test_promote.py tests/seam/test_rollback.py -x` | ❌ Wave 0 |
| API-09 (SC2) | Disagreeing/unresolvable/empty trace ids refuse by name | unit | `pytest tests/seam/test_promote.py -k trace_ids -x` | ❌ Wave 0 |
| MACH-09 / API-09 (SC3) | promote-next/promote-now refuse for answer-level/index-side under default posture, naming the posture | unit | `pytest tests/seam/test_promotion_posture.py -x` | ❌ Wave 0 |
| API-09 (SC2/3) | Three-transport parity (in-process/REST/MCP) for promote/rollback/retire | integration | `pytest tests/seam/test_dual_transport.py -k promot -x` (REST) and `pytest tests/mcp/test_tool_growth_invariant.py -x` (MCP roster) | ✅ existing files, extend — `test_dual_transport.py` and `test_tool_growth_invariant.py` already exist and already prove this pattern for other verbs |
| API-09 | Refusal vocabulary maps to 422 (REST) / ToolError (MCP) automatically | regression | `pytest tests/seam/test_rest_transport.py -k refusal -x` | ✅ existing — extend `_REFUSAL_FACTORIES` dict with new refusal types |

### Sampling Rate

- **Per task commit:** `cd databasise && uv run pytest -q tests/ledger tests/seam -x`
- **Per wave merge:** `cd databasise && uv run pytest -q` (full suite — 960+ passed / 3 skipped baseline per `06-16-SUMMARY.md`)
- **Phase gate:** Full suite green, plus `uv sync --extra rest && uv run --extra rest pytest -q tests/seam/test_rest_transport.py tests/seam/test_dual_transport.py -x` and `uv sync --extra mcp && uv run --extra mcp pytest -q tests/mcp/ -x -rs` (both verify commands reused verbatim from Phase 6, per the invocation prompt)

### Wave 0 Gaps

- [ ] `tests/seam/test_promote.py` — covers MACH-07 SC1/SC2, API-09
- [ ] `tests/seam/test_rollback.py` — covers MACH-07 SC1/SC2, API-09
- [ ] `tests/seam/test_retire.py` — covers MACH-07 SC1 (never-lifted)
- [ ] `tests/seam/test_promotion_posture.py` — covers MACH-07/API-09 SC3
- [ ] Extend `tests/ledger/test_ledger.py` — new columns round-trip
- [ ] Extend `tests/seam/test_dual_transport.py` — REST parity for the three new verbs
- [ ] Extend `tests/mcp/test_tool_growth_invariant.py` — MCP roster grows by exactly the new tool names, still proving §18.5's per-operation (not per-modality) growth rule
- [ ] Extend `tests/seam/test_rest_transport.py`'s `_REFUSAL_FACTORIES` — every new `SeamRefusalError` subclass gets a factory entry
- Framework install: none — pytest/pytest-asyncio already installed via the `dev` dependency group

## Security Domain

Skipped — `.planning/config.json` sets `workflow.security_enforcement: false` explicitly.

## Sources

### Primary (HIGH confidence — read directly this session)

- `docs/system-model/CONTRACT.md` §0 (lines 60-98), §5 (292-317), §6 (318-347), §7 (348-367), §16 (695-722), §18 (747-810) — the frozen contract text quoted verbatim above
- `docs/system-model/RIG.md` §TR (102-193), §CM opening (193-196), §F3 (415-469), §PR (470-526), §AA.1-2 (527-561) — quoted verbatim above
- `docs/system-model/PARTS.md` — grepped for `embedder-index` to confirm the index-recipe-node claim (lines 93-158 region)
- `databasise/ledger/ledger.py` (full file, 223 lines) — `LedgerRecord`, `Ledger`, schema, triggers, `active_pointer`/`by_alias`/`history`
- `databasise/seam/selectors.py` (full file, 307 lines) — `_resolve_alias`, `_wiring_effects`, `Selector`
- `databasise/seam/trace_store.py` (full file, 118 lines) — `TraceStore`, `UnknownTraceReferenceError`
- `databasise/seam/refusals.py` (full file, 345 lines) — every existing `SeamRefusalError` subclass and house style
- `databasise/seam/engine.py` (full file, 1088 lines) — `Databasise`, `_execute`, `RunRecord` construction, direct-dispatch pattern for `ingest`/`delete_document`
- `databasise/seam/rest.py` (full file, 341 lines), `databasise/mcp/server.py` (full file, 238 lines) — thin-adapter pattern, refusal mapping
- `databasise/wirings/resolve.py` (full file, 178 lines) — `resolve_arm`, `load_wiring`, `all_wirings`, `wiring_family`
- `databasise/parts/schema.py` (full file, 162 lines) — the 17-member `Effect` vocabulary, verbatim
- `databasise/validator/depth.py` (full file, 80 lines) — `effective_depth` taint rule
- `databasise/seam/envelope.py` (full file) — `_StrictModel`, `ResponseEnvelope`, `SeamEvent` closed-set pattern
- `databasise/tests/seam/test_alias_registry.py` (full file, 149 lines) — the exact `LedgerRecord.append()` shape `promote()` must produce, already tested from the read side
- `databasise/tests/seam/conftest.py`, `databasise/tests/conftest.py` — `store_root` fixture pattern
- `databasise/mcp/tools.py` (partial, lines 1-100) — `_ToolArgs` base, tool-argument DTO pattern
- `databasise/tests/mcp/test_tool_growth_invariant.py` (partial) — MCP roster growth-invariant test pattern
- `.planning/phases/06-hipporag-2-side-by-side/06-GATE-AMENDMENT.md` (full file) — exact section structure the HARD-01/02/04 amendment record must follow
- `.planning/phases/07-promotion-rollback/07-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/config.json` — required reading, read in full

### Secondary (MEDIUM confidence)

- None — no web search or external documentation lookup was needed; this phase's domain is entirely internal to the already-ratified contract and the already-built codebase.

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependency; existing pins independently verified in prior phases
- Architecture: HIGH — every pattern cited is read directly from committed source this session, not inferred
- Pitfalls: HIGH — derived directly from CONTRACT/RIG text and the existing codebase's own house-style docstrings, not speculative
- Mutation-class node-set enumeration (D-10): MEDIUM — explicitly flagged Claude's Discretion in CONTEXT.md; this research anchors the two confirmed cases (`embedder-index`, `generate`/`keywords`) but does not enumerate HippoRAG's full node set for the class-derivation function

**Research date:** 2026-09-11
**Valid until:** No external expiry — this research is keyed to frozen contract text and code already committed at HEAD; re-verify only if `docs/system-model/` is re-mirrored from upstream or `databasise/ledger/ledger.py`/`selectors.py`/`engine.py` change materially before planning executes.
