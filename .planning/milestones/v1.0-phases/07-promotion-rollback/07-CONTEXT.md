# Phase 7: Promotion & Rollback - Context

**Gathered:** 2026-09-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 7 delivers **MACH-07 and API-09**: the operator-invoked promote / rollback / retire path over
the append-only ledger Phase 1 stood up and Phase 4 gave an `alias` column, reachable in-process,
over REST, and over MCP through the §18 seam. Every generation record carries `change_origin` and
`promotion_provenance`, never defaulted; a semver is minted at promotion and only at promotion; the
active pointer stays a derived query; tombstoned generations are never lifted; the gate-adjudicated
verbs (`promote-next`, `promote-now`) exist on the surface and refuse by name under the default
measurement posture (ROADMAP success criteria 1–3).

**Re-scoped by the owner in this discussion (2026-09-11):** HARD-04 (owner's corpus into the eval
bundle), HARD-01 (gate-script vacuous passes) and HARD-02 (ANATOMY §F / PARTS Appendix A
reconciliation) are **deferred out of Phase 7** to a later in-depth testing / hardening phase the
owner will run after the product is built. ROADMAP success criteria 4 and 5 are amended during
planning per D-03 below. The deferral is permitted for the same reason `06-GATE-AMENDMENT.md`
deferred MACH-03: the operator-asserted path carries no verdict and reads no bundle, so nothing in
this phase consumes any of the three.

</domain>

<decisions>
## Implementation Decisions

### Scope re-cut (owner decisions, 2026-09-11)

- **D-01: HARD-04 is deferred, not built.** Owner: *"Unless this testing is required I wanted to
  defer it until the product is built and I do in-depth testing for an entirely different phase."*
  It is not required here: an operator-asserted promotion reads no bundle and carries no verdict
  (CONTRACT §6, RIG §PR.3), so the owner-corpus layer is consumed by nothing in Phase 7 — the
  identical argument `06-GATE-AMENDMENT.md` made for MACH-03. When it does happen: the corpus is a
  **smaller subset the owner picks later**, and **only hashes and an evidence record cross into
  git** (documents, questions, gold answers stay in a local-only directory named at mint time; the
  repo is public). Phase 7 builds **no coverage check on promote()** and **no question-authoring
  tool**. — **Reversibility:** reversible — `databasise.parity.corpus.load_snapshot` plus
  `databasise.eval.bundle.mint_bundle` already accept any directory, so the later phase mints
  without new machinery.
- **D-02: HARD-01 and HARD-02 are deferred to the same later hardening phase.** Neither is
  consumed by the promote path. Phase 7's requirement set is therefore **MACH-07 + API-09**. The
  open question of *where* those edits land (upstream repo and re-mirror, in-place edit with a
  recorded divergence, or project-layer copies — `docs/system-model/` is a verbatim upstream
  mirror that is never edited) travels with the deferral, unresolved.
- **D-03: The deferral is recorded, never silent** — GATE-01's discipline, followed exactly as
  `02-GATE-01-WAIVER.md`, `03-GATE-AMENDMENT.md` and `06-GATE-AMENDMENT.md` did. Planning ships a
  written amendment record in the phase directory that: quotes ROADMAP Phase 7 criteria 4 and 5
  and its requirements line; states the operator-path-consumes-nothing argument; names the point
  of first need for each of HARD-01/02/04 as *the owner's in-depth testing / hardening phase, or
  the first gate-adjudicated promotion, whichever comes first*; and lists the residual risk (every
  promotion in this milestone is provisional and unmeasured on the owner's own data). It authorises
  the tracking edits: ROADMAP Phase 7 requirements → `MACH-07, API-09`; criteria 4–5 struck with a
  pointer to the record; REQUIREMENTS.md rows HARD-01/02/04 gain a dated deferral note and **stay
  Pending, checkboxes unchecked**, so the milestone audit lists them beside MACH-03 and MODAL-01.
  The later phase does not exist in the roadmap yet — the record names it as the owner's to add
  (`/gsd-phase add`). — **Reversibility:** reversible — a roadmap edit and a dated note.

### Promotion target and the generation record

- **D-04: The promotion target is derived from `promotion_trace_ids`, never named by the caller.**
  The operator hands promote() the alias, the trace ids they read, and `change_origin`. Each trace
  id resolves through the existing `TraceStore` to a run record naming its wiring; every id must
  resolve, and all must name **one** wiring, otherwise the call refuses by name (unknown trace,
  disagreeing traces, empty list). That wiring's arm name becomes the record's `mutation_id` —
  exactly the read contract `selectors._resolve_alias` already inherits. This keeps Phase 4 D-11
  (no wiring name, node id or instance hash as seam input) intact on the operator surface and makes
  `promotion_trace_ids` verifiable rather than decorative. — **Reversibility:** costly — the call
  signature crosses all three transports and the conformance tests pin it.
- **D-05: Rollback names an explicit semver target; there is no default "previous".** rollback()
  takes the alias, the semver minted at the generation being returned to, trace ids and
  `change_origin`. It appends a new `operator_asserted` generation record whose `parent` names the
  mutation id being returned to (RIG §PR.2), carrying no new arm run and no verdict, and the alias
  repoints to that generation. An unknown semver, a semver minted under a different alias, or a
  tombstoned target refuses by name.
- **D-06: The semver is minted by the machine at promotion; the operator states nothing about versions.** First promotion of an alias mints `1.0.0`. Thereafter, per CONTRACT §0's fixed
  rule: **MAJOR** when the promoted wiring's declared socket / capability / effects surface differs
  from the prior active generation's; otherwise **MINOR**. **PATCH is never minted on the operator
  path** — no measured "bug fix" distinction exists without a gate. Running an arm never mints
  anything (§6). The minted semver is stored on the generation record and is the public handle a
  rollback names. — **Reversibility:** one-way per record — a minted version is a published name
  under §0.4 and is never reused; the *rule* is a source edit.
- **D-07: Tombstoning is an operator `retire` verb on the same append-only path.** retire()
  appends a tombstone record for a generation (alias + semver, trace ids, `change_origin`, no
  verdict). promote() and rollback() refuse any target whose latest ledger state is tombstoned;
  pins to tombstoned artifacts already refuse per CONTRACT §16.2. **No act lifts a tombstone**:
  promoting the same wiring again later is a new generation with a new semver, never a
  resurrection (RIG §PR.2, §0.4). This makes SC1's "tombstoned losers are never lifted" real in
  production, not only against a test-seeded row.
- **D-08: `change_origin` is required input on promote, rollback and retire, both values accepted.** Absent → refuse by name. `machine_mutation` is accepted as a value even though no
  proposer exists in this milestone, because CONTRACT §7 makes the field orthogonal to
  `promotion_provenance` and the contract is frozen input the seam does not re-litigate. Never
  defaulted, never inferred.

### Verb surface and the posture refusal

- **D-09: One promote entry point carrying the verb as a closed enum.** promote() takes a `verb`
  covering CONTRACT §5's ladder (`check`, `preview`, `run`, `promote-next`, `promote-now`) plus the
  operator-asserted path. In this milestone only the operator path appends. The others refuse by
  name with the *specific* reason: **`promote-next` / `promote-now` at answer-level or index-side
  class → the refusal names the measurement posture and cites RIG §F3.2** (SC3, the load-bearing
  refusal `06-GATE-AMENDMENT.md` depends on); **at retrieval-side class → the refusal names the
  missing calibrated A/A floor** (RIG §AA.2, MACH-03 Pending), since that class is on by default
  but no floor exists; **`check` / `preview` / `run` → refuse as not built in this milestone**, by
  name — no gate implementation exists and Phase 7 does not build one. Rollback and retire are
  their own entry points (Phase 4 D-03: one entry per §18 operation). — **Reversibility:**
  reversible — flipping a refusal into a real verb later is additive.
- **D-10: The mutation class is machine-derived; the caller may not state it.** Derived from the
  delta between the promoted wiring and the prior active generation of the alias: any index-recipe
  node differs → `index-side`; any generation / keyword / prompt-bearing node differs →
  `answer-level`; otherwise `retrieval-side`. A first promotion (no prior generation) is classed by
  the wiring's own node set under the same rule. Recorded in the existing `mutation_class` column.
  A caller cannot talk a promotion into a cheaper class. Which node kinds count as index-recipe
  and answer-level is Claude's discretion, anchored on PARTS §L.1 (`embedder-index` is the index
  recipe node) and RIG §CM's three spending moments.
- **D-11: The measurement posture is a module constant the refusal quotes.** One frozen mapping
  class → measurement on/off in the promotion module: `retrieval-side` on, `answer-level` and
  `index-side` off, exactly RIG §F3.2. Refusals quote the entry and cite §F3.2. Flipping a class is
  a **source edit**, never a runtime flag or a constructor argument, and `06-GATE-AMENDMENT.md`
  makes MACH-03 due at that moment. — **Reversibility:** reversible in code, but the amendment
  record binds the flip to running the A/A calibration first.

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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

`docs/system-model/` is a verbatim upstream mirror and is **never edited**; project records cite
into it (precedent: `02-GATE-01-WAIVER.md`, `06-GATE-AMENDMENT.md`).

### The contract being implemented
- `docs/system-model/CONTRACT.md` §0 — version string rule (MAJOR = interface axis, MINOR/PATCH =
  implementation axis) and version minting (only at promotion; an arm never mints)
- `docs/system-model/CONTRACT.md` §0.4 — a published name is never reused (tombstones never lifted)
- `docs/system-model/CONTRACT.md` §5 — the five-verb ladder `check`/`preview`/`run`/`promote-next`/`promote-now`
- `docs/system-model/CONTRACT.md` §6 — mutation promotion: atomic alias repoint + generation record,
  ledger append **is** the decision, ledger wins on disagreement, running an arm never appends;
  promotion provenance clause; the cross-field rule (`promotion_trace_ids` non-empty iff
  `operator_asserted`); supersession with no special case; semver consequence
- `docs/system-model/CONTRACT.md` §7 — ledger record schema, `change_origin` (orthogonal to
  provenance, never defaulted, never inferable by absence, never conflated with `class`), retention
  tiers `runnable`/`readable`/`tombstoned`
- `docs/system-model/CONTRACT.md` §16.2 — pin validation refuses a tombstoned artifact
- `docs/system-model/CONTRACT.md` §18 — the seam: closed envelope, four selectors, refusals, growth rule
- `docs/system-model/RIG.md` §PR.1–§PR.4 — promote sequence, verb-per-class-and-posture table,
  concurrent promotion, rollback and tombstoning, the operator path, batch rule (out of scope)
- `docs/system-model/RIG.md` §F3.2 — the default posture: what it disables, what survives, reversibility
- `docs/system-model/RIG.md` §AA.2 — a floor with unknown bypass status is unusable (retrieval-side refusal reason)
- `docs/system-model/RIG.md` §TR — trace ids and the run record `promotion_trace_ids` point at
- `docs/system-model/RIG.md` §CM — the three spending moments (anchors the class derivation, D-10)
- `docs/system-model/PARTS.md` §L.1 — `embedder-index` as LightRAG's one index-recipe node (D-10)

### Project-layer records that bind this phase
- `.planning/phases/06-hipporag-2-side-by-side/06-GATE-AMENDMENT.md` — authorises Phase 7; MACH-03
  deferred to the first gate-adjudicated promotion; SC3's refusal named load-bearing
- `.planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md` — the deferral-record discipline D-03 follows
- `.planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md` — second precedent for the same record shape
- `.planning/phases/04-the-seam/04-CONTEXT.md` — D-03 (one entry per operation), D-10 (typed
  refusals), D-11 (no wiring name as input), D-12 (aliases read from the ledger), D-17 (transport parity)
- `.planning/phases/02-falsifier-gate/02-CONTEXT.md` — D-04 (operator-asserted is the only enabled path)
- `.planning/REQUIREMENTS.md` — MACH-07, API-09, MACH-09 (posture), MACH-03 (floor Pending);
  HARD-01/02/04 rows to receive deferral notes
- `.planning/ROADMAP.md` — Phase 7 entry (criteria 4–5 to be amended per D-03)

### Deferred-item references (for the amendment record, not for building)
- `databasise/evidence/EVAL-BUNDLE-V1.md`, `databasise/eval/bundle.py`, `databasise/eval/remint.py`,
  `databasise/parity/corpus.py` — the mint path HARD-04's later phase reuses unchanged
- `docs/system-model/parts-check.sh`, `docs/system-model/anatomy-check.sh` — HARD-01's sites
- `docs/system-model/ANATOMY.md` §F, `docs/system-model/PARTS.md` Appendix A — HARD-02's rows

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `databasise/ledger/ledger.py` — `Ledger` (SQLite, WAL, `append`, `active_pointer`, `by_alias`,
  `history`), `LedgerRecord` dataclass over §7's enumeration plus `alias`, append-only enforced by
  `BEFORE UPDATE`/`BEFORE DELETE` triggers. Its module docstring names exactly what Phase 7 owes:
  operator path, `change_origin`, tombstone prohibition, atomic repoint.
- `databasise/seam/selectors.py::_resolve_alias` — the read contract: `by_alias(alias).mutation_id`
  resolved as an arm name via `resolve_arm`. The promote path must append rows this read succeeds on.
- `databasise/seam/trace_store.py::TraceStore` and `Databasise.resolve_trace` — resolve an opaque
  trace token to its run record (D-04's derivation source).
- `databasise/seam/refusals.py` — `SeamRefusalError` family; `rest.py` maps it to refusal
  responses; MCP server surfaces the same. New refusals subclass here.
- `databasise/seam/engine.py::Databasise` — the seam object; `rest.py` (FastAPI, optional
  dependency) and `mcp/server.py` (`@server.tool(name=...)`) are thin layers over it.
- `databasise/seam/_base.py::_StrictModel` and `envelope.py` — frozen-field Pydantic base; the
  closed-set redaction test pattern (`redact.py`) for any new response model.
- `databasise/registry_artifact/index.py` — `_RETENTION_TIERS`, `Pin`, `discover`; §16.2 tombstone
  refusal at pin time already lives here.
- `databasise/wirings/resolve.py` / `load_wiring(variant=...)` — arm-name → resolved wiring, the
  input to D-06's surface diff and D-10's class derivation.
- `databasise/validator/` — computes `effects[]`/depth per node; the declared surface D-06 compares.

### Established Patterns
- Refusals over silent fallbacks, named for what was missing; never a substituted default.
- Typed exception at the library seam, mapped once per transport; one call path proven by a
  conformance test that both/all transports produce the same envelope.
- `docs/system-model/` never edited; deferrals recorded as dated owner decisions in the phase dir.
- Evidence documents under `databasise/evidence/` with `[code-verified]` tags; Rule 1 deviations
  recorded in SUMMARY files.
- Test command: `cd databasise && uv run pytest -q` (960 passed / 3 skipped at 06-16).
- Sync store modules offload at async call sites (`run_in_executor`), not by going async themselves.

### Integration Points
- `Databasise` gains promote / rollback / retire methods; `rest.py` gains matching routes;
  `mcp/server.py` gains matching tools — all three in parity.
- `ledger.py` schema gains additive columns (D-06, D-08, D-07) and the derived projections a
  rollback-by-semver and tombstone check need.
- The posture constant (D-11) lives beside the promotion logic, not in `engine.py` construction.
- ROADMAP.md / REQUIREMENTS.md tracking edits go through `gsd_run query` handlers, never direct writes.

</code_context>

<specifics>
## Specific Ideas

- Owner, 2026-09-11, on HARD-04: *"Unless this testing is required I wanted to defer it until the
  product is built and I do in-depth testing for an entirely different phase."* On the corpus:
  *"smaller subset I pick later to test on."* Recorded verbatim so the deferral reads as
  owner-originated; the argument that the operator path consumes no bundle is Claude's.
- The owner asked "what is HARD-04" mid-discussion — the requirement's origin (the model's
  "only local measurement on our own corpus counts" rule) was not front of mind. The amendment
  record should restate it in one paragraph so the later phase starts from the rule, not the ID.
- Every recommended option was accepted for the code-facing areas; the owner's own reversals were
  scope (defer), not mechanism. Same pattern as Phase 3's "go with recommendations".

</specifics>

<deferred>
## Deferred Ideas

- **HARD-04 — owner's corpus into the eval bundle** → the owner's later in-depth testing /
  hardening phase (not yet on the roadmap). Shape already agreed: a small owner-picked subset,
  local-only directory named at mint time, hashes and evidence only in git. Open when it runs: who
  authors questions / gold answers / gold document ids (LLM-drafted with per-question owner
  approval was the recommendation), and whether promote() should then refuse without bundle
  coverage.
- **HARD-01 — gate-script vacuous-pass sites** (parts-check.sh: 5 extraction sites; anatomy-check.sh:
  1 site guarding 3 checks) → same later phase. Open: where the fix lands given the never-edited
  mirror (fix upstream `ServerDestroyer/rag-modality-swap-system-model` and re-mirror, edit in
  place with a recorded divergence, or project-layer copies).
- **HARD-02 — ANATOMY §F rows lacking landed-repair pointers + stale cross-document rows (DR-06)**
  → same later phase, same open where-it-lands question.
- **A new roadmap phase** for that hardening / in-depth testing pass, holding HARD-01/02/04, the
  MACH-03 A/A spend, MODAL-01's two owner items, and the Phase 6 UAT refresh — the owner's to add.
- **The gate-adjudicated promotion path itself** (§5 gate, eight verdicts, floor consumption) →
  outside this milestone under MACH-09; the first such promotion is MACH-03's point of need.
- **Batch promotion (RIG §PR.4)** and the **mutation proposer (MUTPROP)** → not v1.
- **Alias retirement** (retiring an alias, not a generation) → not asked for.
- **Coverage recorded on the generation record** (which bundle, if any, covered the corpus) →
  revisit with HARD-04.

</deferred>

---

*Phase: 07-promotion-rollback*
*Context gathered: 2026-09-11*
