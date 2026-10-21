# F-07 Mutable-Store Disposition — MACH-10

Dated 2026-09-10 (06-09-PLAN.md). Discharges MACH-10 / F-07: every component declaring
`mutates_store` in this project's own registry, plus every roster entry
`docs/system-model/MODEL-RED-TEAM.md`'s F-07 finding names but this project has not built, is
named below in exactly one of §14.4 point 3's two admissible dispositions. Rendered from
`databasise.parts.registry.default_registry()` through `render_f07_record()`
(`databasise/evidence/f07_report.py`) — re-rendering on unchanged inputs reproduces this document
byte-identically; a second run of this discharge is not a second finding.

## The clause under discharge (`CONTRACT.md §14.4` point 3, quoted verbatim)

> The determinism and parity decision. `§5`'s "determinism is verified, never declared" clause
> requires re-running a node on identical input to confirm it, and the parity gate compares a
> decomposition's output to the pre-decomposition original under an A/A band. A node that
> mutates its own backing store on each call is not safely re-runnable for this purpose without
> an explicit snapshot/reset protocol this contract does not define. **Decision:** a
> `mutates_store`-declaring node MUST be excluded from `§5`'s parity and determinism comparisons
> by an explicit refusal, mirroring `§4`'s `unbudgetable`-node exclusion from token comparisons
> — never by substituting an estimated or pre-mutation number in its place — unless and until a
> snapshot/reset protocol is defined and the node is re-verified against it.

## The finding under discharge (`MODEL-RED-TEAM.md` F-07, quoted verbatim)

> `CONTRACT.md §14.4`'s `mutable-store` capability definition states, in its own third numbered
> point: "a `mutates_store`-declaring node MUST be excluded from `§5`'s parity and determinism
> comparisons by an explicit refusal, mirroring `§4`'s `unbudgetable`-node exclusion from token
> comparisons — never by substituting an estimated or pre-mutation number in its place — unless
> and until a snapshot/reset protocol is defined and the node is re-verified against it." No
> snapshot/reset protocol is defined anywhere in `CONTRACT.md`, `ANATOMY.md`, `PARTS.md`,
> `CATALOG.md`, or `RIG.md` — the clause names the escape condition and leaves it unmet. This is
> not a hypothetical class: `CATALOG.md ## §T` catalogues `CA-2` (codebase-memory-mcp,
> `manage_adr`/`delete_project`), `MC-1` (postgres-mcp's `execute_sql` in Unrestricted Mode), and
> `CA-7` (memory-agent systems' own memory-edit node) as three roster entries declaring exactly
> this capability. For each, goal 8's own requirement — vary, budget, A/B-run against the
> original — is structurally unreachable through `§5`'s gate, the machine's only specified
> comparison mechanism, with no repair path scoped anywhere in the record.

**Fix, as recorded by `MODEL-RED-TEAM.md`:** "Define the snapshot/reset protocol `§14.4`'s own
point 3 names as the condition for lifting the exclusion, or state explicitly that
`mutable-store` components are permanently excluded from goal 8's A/B mechanism and must instead
rely on `## §PR`'s operator-asserted promotion path alone — the contract currently names neither
outcome as settled." This record takes the second branch, per component, below.

## Population and disposition

Enumerated from `default_registry()` itself at render time — never a hand list — plus the
roster entries named above that this project has not registered as a `Part` in
`default_registry()`:

| Component | Disposition | Reason | Tag |
|---|---|---|---|
| `lightrag/full-delete@0.2.0` | `permanent-exclusion` | Not named in MODEL-RED-TEAM.md's own three-entry F-07 roster -- a fourth, real, registered mutable-store component this record's own registry-derived enumeration finds that a hand list would have missed, which is exactly why this record computes its population from default_registry() rather than transcribing the frozen roster. Dispatched directly by Databasise.delete_document() through a single-node wiring built inline, never routed through resolve_selector()'s candidate pool (all_wirings()) that query()/compare() draw from -- structurally unreachable through any comparison today, by construction rather than by this record's own choice. No requirement in this milestone asks for corpus-delete behaviour to be A/B-testable. Recorded for completeness, not because a comparison call can reach it. | [code-verified] |
| `lightrag/full-ingest@0.2.0` | `permanent-exclusion` | Added by 11-03-PLAN.md (LRAG-03, D-06): at @0.2.0 the ingest port declares mutates_store, because v1 mutates its own per-workspace working dir. Same structural exclusion as lightrag/full-delete: dispatched only by Databasise.ingest() through the corpus-ingest wiring, never through resolve_selector()'s candidate pool (all_wirings()), so no comparison call can reach it. No requirement in this milestone asks for corpus-write behaviour to be A/B-testable. | [code-verified] |
| `lightrag/v1-index-sync@0.1.0` | `permanent-exclusion` | Added by 11-01-PLAN.md (D-01): the v1-to-v2 index mirror, the second node of LightRAG's corpus-ingest and corpus-delete wirings. Same structural exclusion as lightrag/full-delete@0.2.0: dispatched only by Databasise.ingest()/delete_document() through those corpus wirings, never through resolve_selector()'s candidate pool (all_wirings()), so no comparison call can reach it. It declares mutates_store only to derive the hosted opaque placement; its writes go through the engine's staged ctx.stores handles. No requirement in this milestone asks for corpus-write behaviour to be A/B-testable. | [code-verified] |
| `codebase-memory-mcp@0.1.0 (CA-2, admitted, not registered)` | `permanent-exclusion` | CA-2 in MODEL-RED-TEAM.md's own F-07 roster; admitted whole-engine opaque under ADMISSION-CODEBASE-MEMORY-MCP.md (PARTS.md ## §X) but not registered in default_registry() since Phase 14 (LEDG-12, D-13): no selector reaches it. databasise/wirings/resolve.py's WIRING_NAMES names only ("lightrag", "hipporag"), so the capability/default/harness selectors' shared candidate pool (all_wirings()) never included its single-node wiring, and an admitted mutates_store part that nothing can select is surface with no consumer. It is registered only by the Falsifier-2 probe registry (databasise/evidence/falsifier2.py probe_registry()) and by tests that pass registry=; its single-node wiring is the fixture databasise/tests/fixtures/codebase-memory-mcp.json. Its provides node resolves opaque effective depth, so it would be excluded from the *default* selector under §8 condition 7 if it were wired. Reversal condition: a requirement that wires it as a selectable arm (TOOL-15/TOOL-18) and asks for manage_adr/delete_project's own behaviour to be A/B-testable, at which point it re-enters default_registry() and needs its own row in _KNOWN_REASONS, and the snapshot/reset protocol is a file-copy-and-restore of the engine's own SQLite database plus its WAL and SHM siblings, in databasise/foreign/codebase_memory_mcp_adapter.py. No adapter owns a file-unlink shape for delete_project today: it is admitted but not driven (COVERAGE.md's OPT-OUT row). | [code-verified] |
| `MC-1 (postgres-mcp's execute_sql, Unrestricted Mode)` | `permanent-exclusion` | Catalogued in CATALOG.md ## §T as a roster entry declaring mutable-store; no postgres-mcp Part is registered in default_registry() today. Catalogued, not registered -- inherits this record's default disposition (permanent-exclusion) if and when it is built, unless a future requirement asks for its own A/B testability, per this record's own reversal condition. | [docs-verified] |
| `CA-7 (a hypothetical memory-agent system's own memory-edit node)` | `permanent-exclusion` | Catalogued in CATALOG.md ## §T as a roster entry declaring mutable-store; hypothetical -- no such system is built in this project. Catalogued, not registered -- inherits this record's default disposition (permanent-exclusion) if and when it is built, unless a future requirement asks for its own A/B testability, per this record's own reversal condition. | [docs-verified] |

Every component above is given the **`permanent-exclusion`**
disposition, on `06-RESEARCH.md`'s own recommended grounds: the one admitted-but-unregistered
instance (`codebase-memory-mcp@0.1.0`) is admitted whole-engine opaque, no selector reaches it, and
no requirement in this milestone asks for any listed component's mutation behaviour to be
A/B-testable. The alternative not taken, for any component, is
**`snapshot-reset-defined`** — building an explicit snapshot/reset protocol and
re-verifying the node against it, per §14.4 point 3's own escape clause.

## Verdict

F-07 is discharged for every registered mutable-store component this project has built
(`lightrag/full-delete@0.2.0`, `lightrag/full-ingest@0.2.0`, `lightrag/v1-index-sync@0.1.0`) and for the admitted-but-unregistered `codebase-memory-mcp@0.1.0` (`CA-2`): each
carries exactly one recorded disposition (`permanent-exclusion`). The two
catalogued-not-built roster entries (`MC-1`, `CA-7`) carry the same disposition, scoped explicitly
to what they are — inherited, not a fresh decision, since neither is built.

**A qualification stated plainly, not left implicit.** The explicit refusal
`databasise.seam.refusals.MutableStoreComparisonExcludedError` (06-09-PLAN.md Task 2) is defined
and fires for a registry that registers a `mutates_store` part and resolves a comparison to it. No
served wiring reaches that comparison path for any component above. Each registered component's
exclusion is a *structural* fact of how it is dispatched (directly, by `Databasise.ingest()` or
`Databasise.delete_document()`, never through `resolve_selector()`'s candidate pool), and
`codebase-memory-mcp@0.1.0` has been outside `default_registry()` since Phase 14, so the refusal
is exercised only by tests that register such a part themselves. This record still names every
registered component, because its population is computed from the registry rather than from what
happens to be reachable.

**How this stands against MODAL-05.** The capability/default/harness selectors' shared
`all_wirings()` set names only LightRAG's five arms and HippoRAG's base wiring; no `mutates_store`
component above is a member, so this exclusion does not narrow `Databasise.compare()`'s own
reachable A/B surface for the LightRAG-vs-HippoRAG comparison `MODAL-05` names. MODAL-05 is discharged by the 2026-09-10 run; Phase 12 changed the HippoRAG path since (HIPP-01, 02, 11, 13, 14), so a pre-Phase-12 HippoRAG store must be rebuilt, and the run has not been repeated on today's code.
The run is recorded in `databasise/evidence/CROSS-MODALITY-EVIDENCE.md`; this record's own F-07
disposition neither advances nor blocks it.

## Method and limits

**Method.** `_live_mutates_store_rows()` (`databasise/evidence/f07_report.py`) walks
`default_registry().keys()`, filters to every `Part` whose `effects` contain `mutates_store`, and
raises rather than silently omitting a row if it finds a component this module has not been told
a disposition reason for. The three catalogued-not-registered rows are a fixed, hand-maintained
addition, since none is discoverable from `default_registry()` by construction.

**The write-quiesce caveat (06-RESEARCH.md's own assumption A5), recorded as unestablished.** Had
either component taken the `snapshot-reset-defined` disposition instead, a
file-level snapshot/reset of `codebase-memory-mcp`'s own SQLite database (plus its WAL and SHM
siblings) would assume no other process holds an open write handle across the snapshot window — a
brief write-quiesce this project has **not established** against
`databasise/foreign/codebase_memory_mcp_adapter.py`'s actual concurrency model. This record states
that limit as not established, rather than assuming it away, since it is exactly the concurrency
question a reader would otherwise have to ask unanswered.

**What is guaranteed under an interrupted or concurrent snapshot/reset.** Neither real component
took the `snapshot-reset-defined` disposition, so no snapshot or reset ever runs
against either one — the explicit refusal fires before any arm executes (06-09-PLAN.md Task 2's
own tested acceptance criterion), which makes an interrupted-mid-snapshot state and a
two-comparisons-touching-the-same-store race both structurally impossible under the disposition
this record actually adopts. Neither guarantee is established by an actual snapshot/reset
mechanism, because none is built; both are guaranteed instead by the mutation never being
attempted concurrently with a comparison in the first place. Had either component instead taken
`snapshot-reset-defined`, both questions would need a real answer this record does
not attempt to pre-supply for a protocol that was never built.

**Reversal.** Either component's disposition flips to `snapshot-reset-defined` only
when a future requirement specifically asks for that component's own mutation behaviour to be
A/B-testable — not by this record being re-rendered on an unchanged registry, which reproduces it
byte-identically by design.
