---
phase: 7
phase_name: "promotion-rollback"
project: "Databasise 2.0 — Fully Agnostic System"
generated: "2026-09-12"
counts:
  decisions: 26
  lessons: 18
  patterns: 19
  surprises: 12
missing_artifacts: []
---

# Phase 7 Learnings: Promotion & Rollback

## Decisions

### HARD-01, HARD-02 and HARD-04 deferred out of Phase 7; the phase's requirement set is MACH-07 + API-09
ROADMAP success criteria 4 and 5 were struck and the three hardening requirements moved to the owner's in-depth testing / hardening phase, or the first gate-adjudicated promotion, whichever comes first. This is the third re-timing of HARD-01/HARD-02 and the first of HARD-04.

**Rationale:** An operator-asserted promotion reads no eval bundle, no floor and no verdict (CONTRACT §6, RIG §PR.3), so nothing Phase 7 builds consumes the owner-corpus layer, the gate-script repair or the ANATOMY/PARTS reconciliation. The owner directed the deferral ("Unless this testing is required I wanted to defer it until the product is built"); the consumes-nothing argument is Claude's and is labelled as such in the record.
**Source:** 07-GATE-AMENDMENT.md, 07-CONTEXT.md, 07-DISCUSSION-LOG.md

---

### The deferral is recorded in a written amendment and the requirements stay Pending
A dated amendment record quotes the struck criteria and requirements line in full, names the point of first need per requirement, lists residual risk, and authorises the ROADMAP/REQUIREMENTS edits. HARD-01/02/04 keep unchecked checkboxes so the milestone audit lists them beside MACH-03 and MODAL-01 (five open rows).

**Rationale:** GATE-01's discipline as followed by `02-GATE-01-WAIVER.md`, `03-GATE-AMENDMENT.md` and `06-GATE-AMENDMENT.md`: an absence is stated, never filled, and nothing is substituted for the deferred work.
**Source:** 07-GATE-AMENDMENT.md, 07-CONTEXT.md

---

### The later HARD-04 shape is agreed now: a small owner-picked subset, hashes and evidence only in git, no coverage check on promote()
When HARD-04 runs, the corpus is a subset the owner picks later; documents, questions and gold answers stay in a local-only directory; only bundle hash, snapshot hash and an evidence record are committed. Phase 7 builds no bundle-coverage refusal on `promote()` and no question-authoring tool.

**Rationale:** The repository is public. Whether `promote()` should later refuse without bundle coverage, and who authors the questions, are open questions that travel with the deferral rather than being decided here.
**Source:** 07-GATE-AMENDMENT.md, 07-DISCUSSION-LOG.md

---

### The promotion target is derived from `promotion_trace_ids`, never named by the caller
The operator hands `promote()` the alias, the trace ids they read, and `change_origin`. Every trace id must resolve through `TraceStore` and all must name one wiring; empty, unknown or disagreeing ids refuse by name before any write.

**Rationale:** Keeps Phase 4 D-11 (no wiring name, node id or instance hash as seam input) intact on the operator surface and makes `promotion_trace_ids` verifiable rather than decorative. Rated costly to reverse because the signature crosses all three transports.
**Source:** 07-CONTEXT.md, 07-DISCUSSION-LOG.md, 07-01-SUMMARY.md

---

### Rollback names an explicit semver target; there is no default "previous"
`rollback(alias, version, trace_ids, change_origin)` has no default on `version`. It appends a new `operator_asserted` record whose `mutation_id`/`parent` name the target's own `mutation_id`, mints a genuinely new semver, and never reuses the target's. Unknown, foreign-alias, or tombstoned targets refuse by name with nothing written.

**Rationale:** An implicit "previous" is ambiguous after repeated moves (RIG §PR.2). Unknown and foreign-alias versions share one refusal (`UnknownGenerationVersionError`) because both mean "this alias has no such generation".
**Source:** 07-CONTEXT.md, 07-DISCUSSION-LOG.md, 07-02-SUMMARY.md

---

### The machine mints the semver: 1.0.0 on first promotion, MAJOR when the declared surface differs, MINOR otherwise, PATCH never
The operator states nothing about versions. `declared_surface`/`mint_version` in `promotion.py` implement CONTRACT §0's rule; running an arm never mints anything.

**Rationale:** No measured "bug fix" distinction exists on the operator path without a gate, so PATCH cannot be justified. A minted version is a published name under §0.4 and is never reused.
**Source:** 07-CONTEXT.md, 07-DISCUSSION-LOG.md, 07-01-SUMMARY.md

---

### Tombstoning is an operator `retire` verb on the same append-only path, and no act lifts a tombstone
`retire()` appends a tombstone record (`minted_version=None`, `targets_version=<retired>`); `promote()`/`rollback()` refuse tombstoned targets; retiring the alias's own active generation refuses (`ActiveGenerationRetirementError`, the operator must roll back first). Re-promoting a retired wiring mints a new generation while the tombstone stays forever.

**Rationale:** Makes SC1's "tombstoned losers are never lifted" true against the real write path rather than only against a test-seeded row. The alternative (no operator tombstone in v1) was rejected.
**Source:** 07-CONTEXT.md, 07-DISCUSSION-LOG.md, 07-02-SUMMARY.md

---

### `change_origin` is required on promote, rollback and retire, with both values accepted
Absent or unrecognised `change_origin` refuses by name. `machine_mutation` is accepted even though no proposer exists in this milestone.

**Rationale:** CONTRACT §7 makes the field orthogonal to `promotion_provenance` and the contract is frozen input the seam does not re-litigate; adding a proposer-existence check would add a check nothing can satisfy yet.
**Source:** 07-CONTEXT.md, 07-DISCUSSION-LOG.md

---

### One `promote()` entry point carries the verb as a closed enum; gate verbs refuse by name
`promote()` takes a `verb` covering CONTRACT §5's ladder plus `operator-asserted` (the default). `promote-next`/`promote-now` refuse naming the measurement posture (answer-level, index-side; RIG §F3.2) or the missing calibrated A/A floor (retrieval-side; RIG §AA.2); `check`/`preview`/`run` refuse as not built. Only `operator-asserted` reaches `Ledger.append()`. Rollback and retire are their own entry points.

**Rationale:** SC3 requires the gate verbs to exist so they can refuse by name; separate always-refusing entries across three transports were rejected. Phase 4 D-03 fixes one entry per §18 operation for rollback/retire.
**Source:** 07-CONTEXT.md, 07-DISCUSSION-LOG.md, 07-01-SUMMARY.md

---

### The mutation class is machine-derived from the wiring delta; the caller may not state it
`derive_mutation_class` compares the promoted wiring with the alias's prior active generation: index-recipe node differs → `index-side`; generate/keyword/prompt node differs → `answer-level`; otherwise `retrieval-side`. It takes the two full resolved wiring dicts, not bare node-id sets, so it can compare each shared node's own `component` field.

**Rationale:** A caller cannot talk a promotion into a cheaper class. The plan's literal "differing node ids" signature could not express the "component identity differs" half of D-10's stated rule.
**Source:** 07-CONTEXT.md, 07-01-SUMMARY.md

---

### The measurement posture is a frozen module constant read at exactly one site, and the refusal quotes it
`_MEASUREMENT_POSTURE` in `promotion.py` maps class → on/off (retrieval-side on, answer-level and index-side off). `enforce_gate_verb_posture` is the only read site; a flip is a source edit, never a runtime flag or constructor argument, and makes MACH-03 due.

**Rationale:** A runtime-constructible posture could reach the floor-less gate path. `test_posture_is_not_flippable_at_runtime` pins it.
**Source:** 07-CONTEXT.md, 07-01-SUMMARY.md

---

### Trace-id → arm-name resolution matches on the dispatched node-id set
`resolve_single_arm` compares `RunRecord.nodes[*].node_id` against each registered wiring's resolved node set, not `wiring_id`/`arm_id` (both constant literals across every LightRAG arm) or `wiring_instance_hash` (varies per query because it hashes the query-injected wiring).

**Rationale:** The node-id set is the one signal a persisted `RunRecord` carries that is both query-invariant and unique per arm. The plan's literal `wiring_id`/`arm_id` description did not survive contact with the real record shape.
**Source:** 07-01-SUMMARY.md

---

### Four additive ledger columns, no `ALTER TABLE`; `by_alias()` excludes tombstoned rows
`change_origin`, `record_kind`, `minted_version`, `targets_version` were added following Phase 4's `alias`-column no-migration precedent, plus a `generation_state(alias, version)` projection (latest record for a generation, `ORDER BY id DESC LIMIT 1`). The `BEFORE UPDATE`/`BEFORE DELETE` triggers and derived projections were kept.

**Rationale:** The ledger held no rows yet, so no migration was needed. `by_alias()` must skip tombstones or the active pointer could derive from a retirement record.
**Source:** 07-01-SUMMARY.md, 07-CONTEXT.md

---

### The whole ledger read-modify-append sequence runs in one `run_in_executor` call
`Ledger()` construction, the prior-generation read, derivation, and `append()` all execute inside one function handed to the executor, never split between the event-loop thread and the executor thread.

**Rationale:** sqlite3 refuses cross-thread use of a connection; opening `Ledger()` on the loop thread and calling `append()` from the executor raised `sqlite3.ProgrammingError`.
**Source:** 07-01-SUMMARY.md

---

### The MACH-09 posture guard's exemptions were narrowed by name, never relaxed
`test_measurement_posture.py`'s exemption lists name `seam/engine.py` explicitly with the exact detail strings `"def promote(...)"` and `"def rollback(...)"`; a future `promote_next`/`promote_now` implementation, or `promote` defined elsewhere, still fails the guard. `02-MACH-09-POSTURE.md` gained a dated section per plan explaining why the operator-asserted write does not mean the gate-adjudicated path exists.

**Rationale:** The guard's own docstring instructs "update 02-MACH-09-POSTURE.md in the same change rather than relaxing this test". `retire` needed no exemption because it was never in the scanned vocabulary.
**Source:** 07-01-SUMMARY.md, 07-02-SUMMARY.md

---

### Shared operator-path preconditions live in one `Databasise` method
`_resolve_operator_preconditions` (invalid `change_origin`, trace resolution, `resolve_single_arm` agreement) was extracted from `promote()`'s prologue and is called by all three verbs; it returns `(resolved_records, arm_name, arm_instance_hashes)`.

**Rationale:** The helper needs `self._trace_store`, so it lands as a method rather than a `promotion.py` function; three near-identical validation copies were avoided.
**Source:** 07-02-SUMMARY.md

---

### `rollback()`/`retire()` derive `mutation_class` with the same two-wiring diff `promote()` uses
"New" is the generation in play (rolled-back-to, or being retired) and "prior" is the alias's still-active generation; `retire()` records the resolved trace arm but does not match it against the retirement target (RESEARCH.md Open Question 2), stated in the docstring.

**Rationale:** The plan said only "derived the same way" without naming operands; reusing `derive_mutation_class`'s existing signature avoids a second derivation rule.
**Source:** 07-02-SUMMARY.md

---

### Three-transport parity uses isolated store roots with a directly-inserted fixed trace token
Each transport gets its own store root, and a trace token is inserted directly into `trace.db` rather than minted by `TraceStore.persist()`'s random `secrets.token_urlsafe()`, so all three stores resolve the identical `promotion_trace_ids` and every `LedgerRecord` column can be compared.

**Rationale:** Reusing one alias across transports against a shared store would mint 1.0.0/1.1.0/1.2.0 — an artifact of call order, not a transport divergence — and independent stores can never share a randomly minted token.
**Source:** 07-03-SUMMARY.md

---

### The evidence document's strictly-checked criteria table cites only extras-free test node ids
`PROMOTION-LEDGER-EVIDENCE.md`'s table cites `test_promote.py`/`test_rollback.py`/`test_retire.py`/`test_promotion_posture.py`/`test_ledger.py` nodes; REST/MCP tests are cited in prose. 07-04 later cited one extras-gated node id and updated "Method and limits" to name that exception explicitly.

**Rationale:** `test_promotion_ledger_record.py` runs `pytest --collect-only` per cited node id under a bare `uv run pytest`; a node inside a `pytest.importorskip`-guarded module reports "found no collectors" (exit 4) when the extra is absent.
**Source:** 07-03-SUMMARY.md, 07-04-SUMMARY.md

---

### REST routes and MCP tools are thin adapters; `TOOL_NAMES` grows from six to nine as three genuine §18 operations
Each route is a single `return await engine.<verb>(...)` with no route-local exception handling; the MCP tools go through the existing `@_refusal_mapped` wrapper. Never one tool per modality, never folded into a scope-dispatched lifecycle tool.

**Rationale:** Follows `ingest`/`delete_document`'s existing thin-adapter shape; the pre-existing single `SeamRefusalError` handler already maps every refusal.
**Source:** 07-03-SUMMARY.md, 07-03-PLAN.md

---

### An out-of-enum verb refuses at the engine as `UnrecognisedPromotionVerbError`; transport DTOs keep `verb: str`
The guard is the first statement in `promote()`'s body, above the not-built check and trace resolution. `PromoteRequest.verb`/`PromoteToolArgs.verb` carry no `Literal` or `field_validator`.

**Rationale:** Constraining at the Pydantic layer produces a 422 from FastAPI's own handler with no `refusal_type` key, making the verb the one refusal whose name differs per transport. One refusal, one mechanism, three transports.
**Source:** 07-04-PLAN.md, 07-04-SUMMARY.md

---

### `PROMOTION_VERBS` is derived from `typing.get_args(PromotionVerb)`, never a second list
`frozenset(get_args(PromotionVerb))` is the runtime accepted set; `test_the_verb_guard_reads_the_enum_rather_than_a_second_list` pins it.

**Rationale:** A hand-restated list drifts when a seventh literal lands.
**Source:** 07-04-SUMMARY.md

---

### SQLite `BEGIN IMMEDIATE` (`Ledger.transaction()`) over the `asyncio.Lock` WR-01 proposed
Each operator verb's guard read through its `append()` runs inside one `BEGIN IMMEDIATE` span; the `Ledger()` construction stays outside it.

**Rationale:** Rejected on correctness, not size: an `asyncio.Lock` serializes only callers on one `Databasise` instance on one event loop and does nothing for a second instance, process, or REST worker sharing `ledger.db`. `BEGIN IMMEDIATE` serializes at the file and is also the smaller diff.
**Source:** 07-05-PLAN.md, 07-05-SUMMARY.md

---

### `DROP INDEX` then `CREATE UNIQUE INDEX` under a new name (`ux_ledger_generation`)
The non-unique `ix_ledger_generation` is dropped and a UNIQUE index on `(alias, minted_version)` created under a different name; NULL `minted_version` tombstone rows stay distinct under a plain unique index.

**Rationale:** Verified against SQLite 3.53.1 that `CREATE UNIQUE INDEX IF NOT EXISTS` reusing the old name is a silent no-op over an existing plain index, which would ship a fix that does nothing on any machine already holding a `ledger.db`.
**Source:** 07-05-PLAN.md, 07-05-SUMMARY.md

---

### The UNIQUE index's `sqlite3.IntegrityError` stays unwrapped; no new `SeamRefusalError`
The refusal ladder stays at ten `refusals.py` classes plus `UnknownTraceReferenceError`; `refusals.py`, `rest.py`, `mcp/tools.py`, `mcp/server.py` are byte-identical across 07-05's range.

**Rationale:** With `transaction()` in place the constraint is unreachable through the seam under normal operation; wrapping it would add §18 surface for a path no consumer can reach, mirroring the `UnrecognisedPromotionVerbError` backstop pattern.
**Source:** 07-05-SUMMARY.md, 07-VERIFICATION.md

---

### WR-03 (lock contention on `Ledger()` construction) is carried as an anti-pattern, not a phase gap
The verifier weighed WR-03 against every must-have and success criterion: 07-05's truths are scoped to operator verbs racing each other, and no Phase 7 criterion asserts `query()`'s behavior under concurrent promotion (that surface belongs to Phase 4/5's API-03..07). Adversarial re-verification (0/3 refute votes) upheld the scoring.

**Rationale:** A real robustness risk outside the phase's scored surface is recorded for a hardening pass (explicit `timeout=` on `sqlite3.connect()`, wrap lock-timeout `OperationalError`) rather than blocking the phase.
**Source:** 07-VERIFICATION.md, 07-REVIEW.md

---

## Lessons

### A plan's literal description of a record's fields must be checked against the record the code actually constructs
07-01's plan said to match trace records on `wiring_id`/`arm_id`; both are the same constant for every LightRAG arm (`lightrag-base` and `seam`), so the matcher had to be redesigned around the dispatched node-id set.

**Context:** The read path `_resolve_alias` had only ever consumed hand-appended rows; the write path was the first code to derive an arm name from a persisted `RunRecord`.
**Source:** 07-01-SUMMARY.md

---

### A sqlite3 connection must be opened and used on the same thread when offloading to an executor
Opening `Ledger()` on the event-loop thread and calling `append()` via `run_in_executor` raised `sqlite3.ProgrammingError`. Offloading only the final `append()` is insufficient; the whole open-read-append sequence must move together.

**Context:** Found during manual end-to-end verification before tests were written.
**Source:** 07-01-SUMMARY.md

---

### Every new refusal subclass, tool, or roster entry trips a pre-existing growth-invariant test, and not all pins are in the file the plan names
`test_rest_transport.py` walks `SeamRefusalError.__subclasses__()` and requires a factory entry per subclass; `test_dual_transport_parity.py` looks up `_SCENARIOS[tool_name]` for every `TOOL_NAMES` entry and also carried its own `assert len(TOOL_NAMES) == 6` that the plan's read-first list did not enumerate. All five plans hit one or more of these.

**Context:** The guards fired as designed; each fix was a Rule 3 blocking deviation recorded in the SUMMARY.
**Source:** 07-01-SUMMARY.md, 07-02-SUMMARY.md, 07-03-SUMMARY.md, 07-04-SUMMARY.md

---

### A Phase 2 guard vocabulary can encode a naming guess that a later phase's real design contradicts
`_PROMOTION_VERB_NAMES` listed `rollback` as a presumed CONTRACT §5 ladder member; Phase 7 settled that the real `rollback()` is RIG §PR.2's operator-asserted path. Landing it tripped the guard, which was resolved by a named exemption plus a dated posture-record section, not by relaxing the test.

**Context:** The guard's docstring anticipated its own failure and named the resolution procedure.
**Source:** 07-02-SUMMARY.md, 07-01-SUMMARY.md

---

### A grep-based acceptance criterion counts docstring prose, not only code
`grep -v '^\s*#' | grep -c '@server.tool'` returned 10 for nine real decorators because the module docstring contained the literal substring `@server.tool(name=...)`. The docstring was reworded.

**Context:** The comment filter drops `#` lines only; a triple-quoted docstring passes through.
**Source:** 07-03-SUMMARY.md

---

### `pytest --collect-only` on a node id inside an `importorskip`-guarded module is a collection error, not a skip, when the extra is absent
It reports "found no collectors" with exit 4. A collectibility check that must pass under a bare `uv run pytest` therefore cannot cite extras-gated node ids.

**Context:** Verified empirically while writing `test_promotion_ledger_record.py`.
**Source:** 07-03-SUMMARY.md

---

### A parametrized test's bare function name collects N tests, failing a "1 test collected" check
Citing `test_an_unrecognised_verb_refuses_by_name_before_any_trace_resolution` collected six; the specific `[promote_next_typo]` node id had to be cited.

**Context:** `test_promotion_ledger_record.py` asserts exactly `1 test collected` per cited node.
**Source:** 07-04-SUMMARY.md

---

### A projection that deliberately excludes rows returns the wrong record for a test that just wrote one of those rows
`Ledger.by_alias()` skips tombstones, so after retiring the first generation it returned the still-active seed generation, producing a spurious `promotion_trace_ids` mismatch. `generation_state(alias, version)` was the correct read.

**Context:** The exclusion was 07-01's own recorded change; 07-03's first-draft parity test read the wrong projection.
**Source:** 07-03-SUMMARY.md

---

### Check-then-act across separate autocommit statements is a race; a single atomic INSERT does not make the decision atomic
Each `_*_sync` body read prior state and appended on separate autocommit statements with no lock anywhere in the package and a non-UNIQUE `(alias, minted_version)` index. `retire(v)` vs `rollback(v)` accepted a post-tombstone rollback in 134/200 trials; six-way `promote()` minted duplicate semvers in 13/300.

**Context:** CONTEXT.md's atomicity discretion fixed one INSERT as the atomic repoint; it did not cover the guard read that decides the INSERT. The transaction must span the read.
**Source:** 07-UAT.md, 07-VERIFICATION.md, 07-05-PLAN.md

---

### Validating a closed enum at the Pydantic layer would make the refusal transport-dependent
FastAPI's own request-validation 422 carries a `detail` array with no `refusal_type` key, so the parity tests asserting identical `refusal_type` across transports would fail for exactly one refusal.

**Context:** The alternative was analysed and rejected in the plan before execution.
**Source:** 07-04-PLAN.md, 07-04-SUMMARY.md

---

### `CREATE UNIQUE INDEX IF NOT EXISTS <name>` over an existing plain index of that name is a silent no-op
`sqlite_master.sql` still reads `CREATE INDEX` and duplicates are still accepted. The upgrade must drop the old index and create the unique one under a new name; a test reopening a database carrying the old plain index pins it.

**Context:** The planner named it "the single most likely way to ship a fix that does nothing."
**Source:** 07-05-PLAN.md, 07-05-SUMMARY.md

---

### An unreleased write transaction stalls the next `Ledger()` construction because `__init__` runs DDL on every open
`_create_schema()` issues `CREATE ... IF NOT EXISTS` on every construction, including read-only callers. The planner's first prototype relied on refcounting to release and a refusal path held the transaction open; the next `Ledger()` waited the full 5000 ms busy timeout and raised `database is locked`. The `try/finally` in `transaction()` is load-bearing.

**Context:** Fact 4 of the four SQLite facts the planner verified before writing the plan.
**Source:** 07-05-PLAN.md, 07-05-SUMMARY.md

---

### The first concurrent construction of a resource exposes latent initialization defects from earlier phases
`PRAGMA journal_mode=WAL` in `Ledger.__init__` (Phase 1, `4aa1239`) raises `SQLITE_BUSY` outright when several connections open a fresh `ledger.db` at once, because SQLite does not run the busy handler for a journal-mode flip. 07-05's concurrency test was the first code to construct `Ledger()` concurrently.

**Context:** Reproduced at 5/360 constructions and 1 failure in 30 runs of the phase's own gate test; fixed in `18a5346` with a bounded retry that degrades to the rollback journal (WAL is not load-bearing for correctness).
**Source:** 07-VERIFICATION.md, 07-REVIEW.md

---

### A contention claim derived from reading code must be measured before it is scored
WR-03 stated that every read-only `Ledger()` blocks behind a held `BEGIN IMMEDIATE`. Measured: with the schema present, the `IF NOT EXISTS` DDL is a no-op taking no write lock, and five concurrent constructions plus `by_alias()` under a held transaction each completed in ~1 ms. The kernel was real but at a different call site (the WAL pragma).

**Context:** Three independent skeptics tested the finding against running code; the addendum corrected the mechanism and narrowed the residual to the missing `timeout=` and unwrapped `OperationalError`.
**Source:** 07-REVIEW.md, 07-VERIFICATION.md

---

### A regression test's trial count must be sized to the measured per-trial detection rate
The six-way promote test runs 20 trials at ~10% pre-fix detection per trial, giving ~88% single-run detection (`1 - 0.9^20`), against the retire/rollback sibling's ~100% at ~68% per trial. Nothing in the file flags the asymmetry.

**Context:** Recorded as WR-04; the fix is ~45 trials or a comment stating the actual probability.
**Source:** 07-REVIEW.md, 07-VERIFICATION.md

---

### A validation-map selector that matches zero tests reads green forever
The MACH-07 SC1 `change_origin` row pointed at `tests/ledger/test_ledger.py -k change_origin`, which selects nothing. The behavior was covered in `test_promote.py` and `test_measurement_posture.py` all along; the command was repointed.

**Context:** The one real finding of the post-07-04 validation audit.
**Source:** 07-VALIDATION.md

---

### A `git diff` range must start at the change under proof, not at a commit that postdates it
The §18-envelope-unchanged rows originally cited `git diff 634e99a..HEAD`, where `634e99a` is the code-review commit after 07-05. Recomputed against `89d55fb^..9882a4c`, the conclusion held; only the evidence line was wrong.

**Context:** Caught by adversarial re-verification of the verifier's gating claims.
**Source:** 07-VERIFICATION.md

---

### Passed/skipped counts vary with which optional extras are installed, and a concurrent process on the shared branch inflates measured commit counts
07-05's plan said 1062/2, its SUMMARY 1067/2, and the orchestrator measured 1068/1 — one extras-gated test flipping between skipped and passed. Separately, `docs(melodyscribe)` commits from another process landed on `main` mid-plan, so `actuals.commits` (raw `git rev-list --count`) includes them.

**Context:** Both were judged non-material; the session had `isolation=none`.
**Source:** 07-VERIFICATION.md, 07-03-SUMMARY.md, 07-04-SUMMARY.md

---

## Patterns

### Pure-computation seam module beside the engine
`promotion.py` mirrors `selectors.py`'s shape: module constants plus pure functions over already-resolved data, no I/O, no engine import. The engine method does the I/O and calls in.

**When to use:** Any derivation (version mint, class derivation, posture check) that must be unit-testable without a store and must stay inside the import boundary.
**Source:** 07-01-SUMMARY.md

---

### A `Literal` as the single source of truth that both a constant and a test introspect
`MutationClass` (a `Literal`) drives `_MEASUREMENT_POSTURE`'s key set and its own test; a fourth class landing in the `Literal` without a posture entry is a `KeyError`, not a silent fall-through. `PROMOTION_VERBS = frozenset(get_args(PromotionVerb))` applies the same idea to the verb guard.

**When to use:** Any closed enum that has a parallel runtime mapping or accepted-set which could drift.
**Source:** 07-01-SUMMARY.md, 07-04-SUMMARY.md

---

### Gate-verb refusal enforced at exactly one read site
`enforce_gate_verb_posture` is the sole reader of `_MEASUREMENT_POSTURE`; the calling engine method never reads the constant.

**When to use:** A policy constant whose flip must be a source edit with one auditable location.
**Source:** 07-01-SUMMARY.md

---

### Shared precondition helper extracted from the first verb's prologue
`_resolve_operator_preconditions` holds the validation all three operator verbs share, returning the resolved tuple each needs.

**When to use:** When a second and third entry point repeat the first's input validation.
**Source:** 07-02-SUMMARY.md

---

### Latest-record-for-a-generation read reused for every guard
`Ledger.generation_state(alias, version)` (`ORDER BY id DESC LIMIT 1`) serves the unknown-version, tombstone, and active-generation checks; never a full `history()` scan.

**When to use:** Append-only ledgers where "current state of X" is the last row naming X.
**Source:** 07-02-SUMMARY.md, 07-03-SUMMARY.md

---

### One load-bearing test against the real write path for an invariant previously proven only against seeded rows
`test_never_lifted_repromotion_is_a_new_generation` runs promote/promote/retire/re-promote through the engine and asserts the tombstone persists while a new generation is minted.

**When to use:** Any contract rule that a hand-seeded fixture could satisfy without the production path being exercised.
**Source:** 07-02-SUMMARY.md

---

### Fixed, directly-inserted trace token for cross-store parity tests
Insert one known token into each isolated store's `trace.db` instead of calling the random-minting `persist()`, so full field equality (including `promotion_trace_ids`) is assertable across transports.

**When to use:** Three-transport parity proof for any write operation that mints derived state and references a randomly-minted id.
**Source:** 07-03-SUMMARY.md

---

### Distinct alias per transport so each call is a first promotion
MCP parity scenarios use a different alias per transport (excluded from the comparison alongside `generation_ordinal`) so no call becomes an order-dependent 1.1.0/1.2.0.

**When to use:** Per-tool parity tests that share one store and cannot isolate store roots.
**Source:** 07-03-SUMMARY.md

---

### Evidence document enforced by a `pytest --collect-only` subprocess per cited node id
`test_promotion_ledger_record.py` asserts each cited node in the criteria table collects exactly one test, and that the document cites the gate amendment and states criteria 4-5 are deferred.

**When to use:** Any phase evidence record that names tests as proof; prevents citations rotting silently.
**Source:** 07-03-SUMMARY.md, 07-04-SUMMARY.md

---

### Engine-level named refusal as the sole mechanism; transport DTOs stay deserialization-only
Invalid public input (`change_origin`, `verb`) is allowed to reach `Databasise.<verb>()`, which raises the named `SeamRefusalError`; the existing REST handler and MCP `_refusal_mapped` carry it unchanged.

**When to use:** Any input whose refusal must carry an identical `refusal_type` across in-process, REST and MCP.
**Source:** 07-04-PLAN.md, 07-04-SUMMARY.md

---

### Unreachable-by-construction backstop kept, not deleted
`_promote_sync`'s terminal branch raises the named verb refusal even though the top-of-body guard makes it unreachable; the UNIQUE index refuses duplicates even though `transaction()` prevents them.

**When to use:** When a future enum member or a bypassed Python path could otherwise fall through into a ledger append.
**Source:** 07-04-SUMMARY.md, 07-05-SUMMARY.md

---

### `Ledger.transaction()`: `BEGIN IMMEDIATE` context manager with `try`/`except BaseException`/`else`
Enter issues `BEGIN IMMEDIATE`; clean exit commits; any exception rolls back and re-raises. The construction stays outside the span; the first guard read is the first statement inside; `append()` is the last.

**When to use:** Any read-derive-append on a shared SQLite file where the read decides the write.
**Source:** 07-05-SUMMARY.md, 07-VERIFICATION.md

---

### Schema-level backstop independent of the Python read path
A UNIQUE index on the published key (`alias`, `minted_version`) refuses a duplicate name regardless of which code path wrote it; NULLs stay distinct so tombstones are unaffected.

**When to use:** Any invariant a database constraint can express; it survives future callers the transaction discipline does not cover.
**Source:** 07-05-SUMMARY.md, 07-05-PLAN.md

---

### RED evidence captured by reverting only the touched files with `git checkout --`
Fix and tests were developed together; the two production files were restored to their committed pre-fix state from a scratchpad backup, the new tests run against real pre-fix code, and the fix restored. No stash, no history rewrite.

**When to use:** Tracer/TDD tasks where the fix has named traps that make separate RED-first development unsafe but genuine RED evidence is still required.
**Source:** 07-05-SUMMARY.md

---

### Multi-trial concurrency test with `asyncio.gather()` against a real engine and a fresh SQLite file per trial
Each trial seeds a real store in a `TemporaryDirectory`, fires the racing calls, and asserts on row ids read back from the database; outcomes must be a `PromotionResult` or an already-shipped `SeamRefusalError`.

**When to use:** Proving a race is closed; size the trial count to the measured per-trial detection rate.
**Source:** 07-05-SUMMARY.md, 07-VERIFICATION.md, 07-REVIEW.md

---

### Planner verifies the proposed mechanism against the reproduction harness before writing the plan
07-05's planner rebound the `Ledger` name in the engine module namespace to wrap exactly the three `_*_sync` spans, ran 40 trials per race before and after, and recorded four SQLite facts as "do not re-derive".

**When to use:** Gap-closure plans for a reproduced defect where the fix's shape has known traps.
**Source:** 07-05-PLAN.md

---

### Written gate amendment record per deferral
Quote the struck criteria and requirements line in full, restate the deferred requirement from its rule rather than its id, state the consumes-nothing argument, name the point of first need, list residual risk plainly, state what is not substituted, and mark provenance (owner decision vs Claude's argument).

**When to use:** Any re-timing of a roadmap requirement; follows GATE-01, 03- and 06-GATE-AMENDMENT.
**Source:** 07-GATE-AMENDMENT.md, 07-CONTEXT.md

---

### Guard tests that anticipate their own failure and name the resolution procedure
`test_measurement_posture.py` pins structurally that no non-test module imports the ledger or defines a promotion verb, and its docstring says the test is expected to fail when Phase 7 lands and must be resolved by updating the posture record, not by relaxing the test.

**When to use:** Any invariant that a planned future phase will deliberately cross; the guard forces the crossing to be recorded.
**Source:** 07-01-SUMMARY.md, 07-02-SUMMARY.md

---

### Adversarial re-verification of each gating claim by independent refuters
Before marking the phase complete, each of the verifier's four gating claims was put to three agents instructed to refute it; a claim fell only by majority. The pass produced one evidence correction, one mechanism correction, and one real fixed defect.

**When to use:** Phase close-out after a gap-closure round, where the verifier's own evidence lines are the weakest link.
**Source:** 07-VERIFICATION.md

---

## Surprises

### `wiring_id` and `arm_id` are identical constants across every LightRAG arm
`wiring_id` is the shared `lightrag-base` string and `arm_id` is the literal `seam` for all five arms, so the plan's matcher could not distinguish arms at all.

**Impact:** `resolve_single_arm` was redesigned around the dispatched node-id set during Task 1.
**Source:** 07-01-SUMMARY.md

---

### The unchanged Phase 4 read path cannot resolve a non-LightRAG arm name
`resolve_arm` only resolves LightRAG's five named arms, so promoting a HippoRAG wiring through `promote()` would leave a later alias read unable to resolve it.

**Impact:** MAJOR/MINOR tests use two real LightRAG arms instead of a HippoRAG wiring; the gap is pre-existing and recorded rather than exercised.
**Source:** 07-01-SUMMARY.md

---

### The UAT concurrency item was first recorded as a pass and converted to an issue by the pre-seal audit
`retire(v)` vs `rollback(v)` accepted a post-tombstone rollback in 134/200 trials with both calls returning ok. Static analysis had already established no lock existed anywhere in `engine.py`.

**Impact:** Phase status went to `human_needed`, gap G-07-1 opened, and 07-05 was planned as a gap-closure plan.
**Source:** 07-UAT.md, 07-VERIFICATION.md

---

### The duplicate-semver race does not surface at two-call concurrency
0/300 at two concurrent promotes; 13/300 at six-way concurrency.

**Impact:** The regression test needs six-way concurrency, and its per-trial detection rate (~10%) is much lower than the retire/rollback race's (~68%).
**Source:** 07-UAT.md, 07-REVIEW.md

---

### A second hardcoded roster-length pin lived in a file the plan did not name
`test_dual_transport_parity.py` carried its own `assert len(TOOL_NAMES) == 6` alongside the pin in `test_tool_growth_invariant.py`.

**Impact:** One extra Rule 3 fix and a test rename in the Task 2 commit.
**Source:** 07-03-SUMMARY.md

---

### A module docstring inflated a grep-based decorator count
The plan's `grep -c '@server.tool'` acceptance criterion returned 10 for nine decorators because the docstring quoted the decorator literally.

**Impact:** Docstring reworded (and its stale "five tool bodies" corrected to nine).
**Source:** 07-03-SUMMARY.md

---

### The WAL pragma in `Ledger.__init__` was a latent Phase 1 defect for six phases
Concurrent first-touch of a fresh `ledger.db` raises `SQLITE_BUSY` from `PRAGMA journal_mode=WAL` because SQLite runs no busy handler for it. Reproduced at 1.4% of constructions and 1 in 30 runs of the phase's own gate test.

**Impact:** Fixed in `18a5346` after the phase's verification; made the gate evidence deterministic (0/360, 40/40) without touching §18.
**Source:** 07-VERIFICATION.md, 07-REVIEW.md

---

### WR-03's stated mechanism was wrong in steady state
Read-only `Ledger()` construction against an existing WAL database returns in ~0.00 s even while a promote holds `BEGIN IMMEDIATE`; the 5 s block reproduces only when `_create_schema` has real DDL to do.

**Impact:** The scoring (anti-pattern, not gap) was correct for a firmer reason; the residual narrowed to the missing `timeout=` and unwrapped `OperationalError`, reachable only at ~88 simultaneous operator calls against a ~57 ms span.
**Source:** 07-REVIEW.md, 07-VERIFICATION.md

---

### The planner's first `transaction()` prototype stalled the next `Ledger()` for the full busy timeout
Relying on refcounting to release, with a refusal path holding the transaction open, produced a 5000 ms wait and `database is locked` on the next construction.

**Impact:** The `try/finally` release became a named must-have trap in the plan's `key_links`.
**Source:** 07-05-PLAN.md

---

### A pre-existing database with duplicate `(alias, minted_version)` rows fails on every open after the index upgrade
`DROP INDEX` autocommits, then `CREATE UNIQUE INDEX` raises `sqlite3.IntegrityError` out of `__init__`; every subsequent `Ledger()` fails identically until the duplicates are removed, after which the migration self-heals. Documented in a code comment, pinned by no test.

**Impact:** Recorded as IN-02; the on-open crash would take down every ledger read as well as every write for such a store.
**Source:** 07-REVIEW.md

---

### The validation map's `change_origin` row selected zero tests since planning time
`tests/ledger/test_ledger.py -k change_origin` matched nothing; coverage existed elsewhere.

**Impact:** Repointed during the audit; every Per-Task Map row also still read `pending` from planning time and 07-04 had no rows.
**Source:** 07-VALIDATION.md

---

### 07-01's plan text itself instructed matching on fields that could not work, yet the same plan's `must_haves.truths` were satisfiable
The redesign (node-id-set matching, full wiring dicts for class derivation) satisfied every plan truth without a replan.

**Impact:** Both redesigns were recorded as key decisions in the SUMMARY rather than as plan deviations.
**Source:** 07-01-SUMMARY.md
