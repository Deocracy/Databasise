# Phase 1: Machine Core - Context

**Gathered:** 2026-08-29
**Status:** Ready for planning

<domain>
## Phase Boundary

The machine executes a wiring graph over embedded stores with stable component identity, inside one
local process tree. This is the §H1 "must decide itself" fence — the runner, scheduler, and
storage-keying design the frozen model deliberately did not specify, faced here for the first time.

Requirements: **EMBED-01, MACH-05, MACH-06, MACH-08**.

In scope: embedded store primitives, component and artifact identity, the depth/execution_mode
computation as a library, the runner and its concurrency model, storage keying and namespace
isolation, and the run-record fields the gate later reads.

Out of scope: the Falsifier 2 evidence run and the eval bundle (Phase 2), any modality port
(Phase 3+), the §18 seam (Phase 4), the promotion ledger's operator path (Phase 7).

</domain>

<decisions>
## Implementation Decisions

### Depth machinery

- **D-01:** Phase 1 builds the **full depth computation as a library** — Tarjan SCC condensation,
  taint min-reduce over `{opaque, evidence, stage}`, and `effects[] → execution_mode` derivation.
  Phase 2 adds §19.10's boundary enumeration, the three named wirings, and the Falsifier 2 evidence
  run. Phase 1 owns the mechanism; Phase 2 owns the proof.
- **D-02:** The blast-radius rule is enforced at **both** the validator (load time) and the
  artifact-write path (before writing). Depth is stamped data by run time so the second check is
  nearly free, and no path reaching the artifact registry — test helper, repair script, Phase 5's
  opaque admission — can bypass the rule.
  — **Reversibility:** reversible — two call sites, no stored state.
- **D-03:** Spike 005's `taint.py` case table is **ported as a named conformance set**, restated in
  frozen contract vocabulary. Three prototype divergences must be repaired in the port, not carried:
  (1) `writes_quarantined` is not an `effects[]` member — scope is a property of the artifact write;
  (2) `writes_artifact` must be distinguished from the transient `writes_kv`/`writes_vector`/
  `writes_graph`/`writes_lexical` members, which sit outside the blast-radius rule by design
  (PARTS-04 D1); (3) case 3 becomes an ordinary expected-refusal — the prototype's harness exempts
  any case whose title starts with `"3."` from its failure count.
- **D-04:** Phase 1 ships **executable reference parts** under `core/` (a passthrough, a
  deterministic fake retriever, a fake LLM caller declaring `calls_llm`, a `fixpoint` body) to
  exercise the runner, budget metering, and store access for real — **plus declaration-only registry
  entries** (schema + `effects[]`, no body) for the three named Falsifier-2 wirings, so Phase 2 has a
  registry to compute over without waiting on Phase 3.

### Stores

- **D-05:** **Cozo owns graph, Faiss owns vector.** Owner decision, locked. These are the fork's
  actual defaults (`v1/lightrag/lightrag.py:275-284`, `v1/lightrag/api/config.py:64-68`).
  **EMBED-01 and ROADMAP Phase 1 criterion 1 currently say LanceDB and must be amended** to read
  Cozo + Faiss + SQLite. See Deferred for the provenance of that error.
  — **Reversibility:** one-way — the vector store is the Phase 3 parity baseline; swapping it while
  decomposing the query side confounds the parity measurement (PITFALLS 8), so a later change means
  re-running parity, not editing a config value.
- **D-06:** **SQLite (stdlib) owns KV, lexical via FTS5, the artifact-registry index, and the
  append-only ledger.** Filesystem owns blob, content-addressed in a git-style fan-out layout. Zero
  new dependency. Note: `lexical` and `blob` are **new primitives** — v1 has neither, so there is no
  incumbent to preserve or port.
- **D-07:** **One store directory per namespace.** Each arm/namespace gets its own Cozo database
  file and its own Faiss index directory, under a path derived from SA-1 recipe identity. Success
  criterion 4's "visibly separate after a run" becomes verifiable with `ls`, and GC is deleting a
  directory — which matches the `quarantined` scope's "GC'd with the instance" rule directly.
  — **Reversibility:** costly — the layout is baked into every namespace-derivation call site and
  into artifact-registry rows written under it; changing it later means a migration of on-disk state.

### Runner and concurrency (the §H1 fence)

- **D-08:** The runner implements **`in-process` only**. `subprocess`, `confined-unit`, and
  `long-lived-service` return an **explicit refusal naming the unimplemented placement**. The
  derivation from `effects[]` is still computed and stamped — only the hosting is unbuilt. Placement
  is earned in Phase 5 when real opaque-node admission forces it.
- **D-09:** **Intra-node concurrency is bounded by a per-node semaphore owned by the runner, whose
  size is declared in that node's config and therefore enters its `config_hash`** under §1. This is
  the §H1 handover answered. It goes beyond CONTRACT §9's V-7 minimum deliberately: RIG §AA.1 makes
  the concurrency setting part of the A/A null's identity and forbids pooling two runs under
  different settings, so folding the cap into `config_hash` makes that automatic rather than
  something a later step must remember to record.
  — **Reversibility:** one-way — the cap is an input to `config_hash`, so changing what feeds it
  changes every instance identity computed under the old rule and invalidates in-flight A/B
  baselines. §1 names this exact failure ("re-hashing byte-identical input after a defaulted-option
  change has already destroyed in-flight A/B baselines").
- **D-10:** The Phase 1 runner **stamps the full run-record field set the gate later reads**: the
  declared determinism/concurrency setting, per-node `cache_hit`, `arm_execution_order`,
  `realised_budget_share`, and which data guards fired. Without these, §5 can never evaluate refusal
  conditions 8, 10 or 11 — and a confounded comparison then returns a normal verdict, which the
  contract calls worse than a refusal because it looks settled rather than unsettled.
  **This is not currently written into MACH-05's definition of done and should be.**
- **D-11:** The runner must **not** import `v1/lightrag/kg/shared_storage.py`'s `UnifiedLock` or any
  module-level singleton (`_manager`, `_storage_instance`, `_global_concurrency_limits`). A
  process-wide concurrency cap is rejected explicitly: one arm's fan-out would throttle an unrelated
  arm beside it, contaminating Phase 6's side-by-side comparison.

### Identity and package

- **D-12:** The environment hash folded into `config_hash` is a **machine-computed resolved-closure
  digest** — distribution names, versions and wheel hashes read from `importlib.metadata` at runtime,
  plus Python version and platform. Hash what is *installed*, never what a lockfile *declares*. §1
  names the declared-closure alternative as "the exact Feast skew the environment hash exists to
  kill". Nix is not consulted: spike 004 holds that Nix is substrate-only and store paths are never
  identity.
  — **Reversibility:** one-way — same reason as D-09; the digest is an input to every `config_hash`.
- **D-13:** Parts are resolved through an **explicit in-code registry** — a dict mapping
  `name@version` to a Part. Every part in this milestone is authored by this project, so
  `entry_points` buys extensibility nothing needs yet while costing an editable install before any
  test can see a part. `entry_points` can be added later without changing the part interface.
- **D-14:** The v2 engine lives in a **new top-level `databasise/` package**, beside `v1/`.
  **Nothing in `databasise/` imports from `v1/`** — code moves by deliberate copy, with attribution
  recorded in the component registry's `upstream_ref` field per CONTRACT §7. This is structural, not
  stylistic: it makes PITFALLS 1 and 7 impossible by construction, because there is no import path
  to v1's singletons. It also makes success criterion 1 trivially true — the new package simply has
  no server backends, no bundled React, and no Docker.
  — **Reversibility:** costly — every ported module's import graph assumes it.

### Claude's Discretion

- Structured-concurrency mechanism inside the runner (`graphlib.TopologicalSorter` for readiness
  plus `asyncio.TaskGroup` for each ready batch is the researched default; no orchestrator).
- RFC 8785 canonicalisation library choice (`rfc8785` is the researched default).
- Blob-store fan-out directory depth and the artifact-registry table schema.
- Reference-part internals, beyond the four roles named in D-04.
- Test structure, fixture layout, and naming, following v1's existing conventions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Frozen contract — the normative source

- `docs/system-model/CONTRACT.md` §0 — component naming, `namespace/name`, semver axes, version
  minted only at promotion
- `docs/system-model/CONTRACT.md` §1 — wiring format, identity tuple, `config_hash` over RFC 8785,
  environment hash, cache-partition key, arms, validator behaviour
- `docs/system-model/CONTRACT.md` §2 — `NodeKind` tagged sum, the 17-member `effects[]` union,
  undeclared-is-denied, `fixpoint` hosting, embedder-coupling refusal
- `docs/system-model/CONTRACT.md` §3 — depth computed not declared, the taint rule, the
  blast-radius rule, the three artifact scopes, `execution_mode` derivation, the strict cross-run
  pin rule
- `docs/system-model/CONTRACT.md` §9 — budget as splittable capability token, fan-out
  multiplicative, the V-7 intra-node concurrency repair, merge-side apportionment
- `docs/system-model/CONTRACT.md` §11 — plane rules; artifact-plane values resolved at load, no
  mid-run reads of mutable decision state
- `docs/system-model/CONTRACT.md` §7 — registries and retention; `upstream_ref` per entry and per
  realized node
- `docs/system-model/RIG.md` §RUN.1 — namespace derivation and the shared KV; the rule MACH-08
  implements
- `docs/system-model/RIG.md` §RUN.2 — artifact overlap is an iff on index-recipe hashes
- `docs/system-model/RIG.md` §AA.1 — why the concurrency/determinism setting is part of the A/A
  null's identity (governs D-09)
- `docs/system-model/SYSTEM-MODEL.md` §H1 — the must-decide fence this phase answers
- `docs/system-model/D-VARIANTS/SELECTION.md` — governs on any disagreement, including its
  spike-005 AMENDMENT

### Spike findings — validated prior work

- `.claude/skills/spike-findings-rag-graph-vector-raw/references/selected-architecture.md` — the
  frozen contract skeleton; entry point for design work
- `.claude/skills/spike-findings-rag-graph-vector-raw/sources/005-laundering-test/taint.py` — the
  12-case oracle D-03 ports; runnable, exit 0
- `.claude/skills/spike-findings-rag-graph-vector-raw/sources/005-laundering-test/README.md` — the
  Falsifier 1 record and the three-scope repair
- `.claude/skills/spike-findings-rag-graph-vector-raw/references/wiring-spec-and-validation.md` —
  wiring JSON, RFC 8785 identity, validator returns all violations at once
- `.claude/skills/spike-findings-rag-graph-vector-raw/references/nix-substrate-boundary.md` — Nix is
  substrate-only; store paths are never identity (governs D-12)

### Build research

- `.planning/research/ARCHITECTURE.md` — TopologicalSorter + TaskGroup pattern, SCC-condensation
  depth, content-addressed store plus append-only ledger, the suggested build order inside Phase 1
- `.planning/research/PITFALLS.md` — pitfalls 1 (storage ownership), 2 (single-run parity), 7
  (hybrid locking), 8 (embedding mismatch)
- `.planning/research/STACK.md` — library recommendations; **note its incumbent description is
  wrong**, see Deferred

### v1 — the porting source, read but never imported

- `v1/lightrag/lightrag.py:275-284` and `v1/lightrag/api/config.py:64-68` — the real store defaults
- `v1/lightrag/kg/cozo_impl.py` — deferred-write buffering, `run_in_executor` dispatch, bound
  parameters, the four frozen-bug mitigations, the `Validity` forward-compatibility note at :16-23
- `v1/lightrag/kg/faiss_impl.py` — the incumbent vector store, its sidecar metadata and deferred
  embedding
- `v1/lightrag/kg/shared_storage.py` — **what not to inherit** (D-11)
- `v1/lightrag/namespace.py` — the 12 existing namespace strings
- `v1/lightrag/tools/rebuild_vdb.py:4-13` — the authoritative-source invariant, stated in code
- `v1/tests/kg/test_cozo_graph_storage.py` — the frozen-bug regression shapes

### Recovery record

- `.planning/RECOVERED-FACT-LAYER.md` — the lost wiki/`as_of`/contradiction subsystem; §7 records
  where it would land in the contract, §8 the honest gap list

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets (port by copy, never import)

- **Cozo adapter patterns** (`cozo_impl.py`) — four in-process write buffers reconciling Cozo's
  immediate-commit model with deferred flush; `run_in_executor` dispatch because `pycozo`'s
  `Client.run()` is synchronous; bound parameters so LLM-extracted entity names containing Datalog
  metacharacters cannot alter query structure. All four constraints must travel with any port.
- **Faiss adapter** (`faiss_impl.py`) — the incumbent vector store with its own metadata sidecar and
  deferred-embedding behaviour.
- **Parity harness** (`v1/tests/parity/run_substrate_parity.py`) — named in the contract as the
  working precedent for SA-3 migration acceptance tests.
- **Frozen-bug regression suite** (`v1/tests/kg/test_cozo_graph_storage.py`) — Cozo 0.7.6 is pinned
  forever, so these four shapes bind any new Cozo query construction permanently.

### Established patterns

- **Storage abstraction**: four ABCs in `v1/lightrag/base.py` plus a name→module registry and a
  late-binding factory. The shape is sound and worth keeping; the singleton state underneath is not.
- **Namespace-not-table**: every store instance is `(workspace, namespace)` over 12 fixed namespace
  strings. D-07 extends this to per-namespace directories.
- **Authoritative-source invariant**: the graph and `text_chunks` KV are authoritative; all three
  vector stores are derived and rebuildable, including across an embedding-model change. This is
  what CONTRACT §6's reindex planner formalises as `reuse`/`re-embed`/`re-extract`/`rebuild`, and it
  should be an explicit tested property of the v2 machine rather than an inherited accident.

### Integration points

- The new `databasise/` package is greenfield — there is no v1 integration point by design (D-14).
- Phase 2 consumes: the depth computation library, the part registry, the reference parts, the
  named-wiring declaration entries, and the run-record fields (D-10).
- Phase 3 consumes: the store primitives and namespace derivation, and the per-node
  storage-ownership audit those make possible.

</code_context>

<specifics>
## Specific Ideas

- **Cozo + Faiss is the owner's explicit instruction**, stated directly: "Cozo+Faiss is what
  Databasise is currently built on and I would like it to stay that way." This overrides EMBED-01 as
  written.
- **Time travel, the DB construction, and single source of truth are named by the owner as
  critical.** Investigation established they are one mechanism, not three, and that the layer
  implementing them was lost in a destructive incident. See `.planning/RECOVERED-FACT-LAYER.md`.
  Phase 1 does not build it, but D-05 and D-07 should not foreclose it — the Cozo schema is already
  shaped for an additive `Validity` key column.
- **Refusals over silent fallbacks** is the house style and shows up in D-08 (unimplemented
  placements refuse by name) and D-10 (a meter with nowhere to write is not a meter).

</specifics>

<deferred>
## Deferred Ideas

### Requirement corrections needed before or during planning

- **EMBED-01 and ROADMAP Phase 1 criterion 1 name LanceDB.** Provenance of the error:
  `.planning/research/STACK.md:26` describes the incumbent as a "faiss-cpu + nano-vectordb pairing"
  — which is not the default — and recommends LanceDB on that basis; the requirement adopted it.
  Neither Cozo, Faiss, LanceDB nor SQLite is named by the frozen model, which only ever says "the
  machine's Graph/Vector/KV client". Engine choice is a build decision, not frozen input. Amend to
  Cozo + Faiss + SQLite.
- **MACH-05's definition of done does not include the run-record fields** D-10 requires.

### Discovered capability gaps — belong to other phases

- **The fact layer** (`/wiki/resolve` with `as_of`, `/wiki/unresolved`, `/wiki/unplaced`, vocab
  routes, claims with provenance and trust tiers). Lost; reconstructed in
  `.planning/RECOVERED-FACT-LAYER.md`. Touches Phase 4's §18 envelope, which is frozen there — must
  be decided knowingly before the seam locks.
- **DR-05** (graph-store `validity` sub-capability) is deferred in `REQUIREMENTS.md:66` because "no
  v1 modality declares `temporal`". That reasoning is now known to be incomplete. Re-decide.
- **`v1/lightrag/evaluation/`** — `eval_rag_quality.py`, `offline_retrieval_check.py`, a RAGAS
  integration, `sample_dataset.json`, `sample_retrieval_oracle.json`. Prior art for Phase 2's
  MACH-02/MACH-03 eval bundle, referenced in no requirement.
- **`v1/lightrag/sidecar/`** — `backfill.py`, `ir.py`, `placeholders.py`, `writer.py`. Unexamined;
  appears in no requirement.
- **Multimodal/VLM** is built in v1 and off by default (`VLM_PROCESS_ENABLE=False`), with a full
  `multimodal_context.py`. No v2 requirement mentions vision.
- **Four LLM roles** (`extract`, `keyword`, `query`, `vlm`) exist in `v1/lightrag/llm_roles.py:52-56`
  with 24 config vars driven off one registry. The v2 node model has no per-role LLM binding.

### Later-milestone ideas

- **DuckDB for Phase 2+ scoreboard and trace analytics only** — bootstrap resampling, per-tier null
  widths, epoch FDR are genuinely columnar work. Not for KV or the ledger: DuckDB's single-process
  write model fights EMBED-01's `subprocess` and `confined-unit` placements.
- **`entry_points` part discovery**, if an external party ever authors a part (D-13).
- **`lmdb`** as a KV escalation path only if SQLite write throughput is measured as the bottleneck.

</deferred>

---

*Phase: 1-Machine Core*
*Context gathered: 2026-08-29*
