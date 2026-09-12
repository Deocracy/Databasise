# Phase 3: LightRAG Query Side - Context

**Gathered:** 2026-08-31
**Status:** Ready for planning

<domain>
## Phase Boundary

LightRAG's query path runs as fitted primitive-part nodes over machine-owned primitives, and its
parity against the pre-decomposition original is measured, not asserted (§BP rung 2).

This is a **port against a published table**, not a fresh decomposition. `docs/system-model/PARTS.md`
§L.1 already publishes all eighteen positions with component names, §13.4 types, `effects[]`, and
three re-derived cuts; §L.2 publishes the wiring family, accepted→emitted kinds, declared
capabilities, artifact scopes, recipe, and the five arms. Phase 3 builds what those two sections
specify. Re-deriving the cut is not in scope — the granularity criterion was already run, blind-
confirmed at six of seven boundaries, and the verdict published.

In scope:
- The seventeen query-time positions as real registered parts with bodies, replacing the Phase 2
  declaration-only `lightrag/query-side@0.1.0` subgraph stub
- The eighteenth position, `embedder-index`, authored as the port's one index-recipe node (§1's
  recipe requirement — a port decision, not a §19-forced cut)
- The base wiring plus five RFC 6902 arm patches (`mix` base; `hybrid`, `local`, `global`, `naive`,
  `bypass`)
- Machine-owned LLM / embedding / rerank client primitives — they do not exist in `databasise/` yet
- Corpus index provenance and the import path that makes both arms read one index
- The pre-decomposition original as a runnable comparison arm
- The parity harness, its N-run variance band, and its declared-deviation record
- The per-node storage-ownership audit (criterion 3), machine-checked

Out of scope:
- **Opaque admission of the ingest core** — Phase 5 (MODAL-02). Phase 3 consumes an index; it does
  not admit the thing that built it.
- **The §18 seam** — Phase 4. Phase 3's arms are reached through the machine and the harness, not
  through a public envelope.
- **HippoRAG 2 and side-by-side** — Phase 6 (MODAL-04/05).
- **Re-deriving node boundaries** — settled at PARTS §L.1.

</domain>

<decisions>
## Implementation Decisions

**Provenance of this section:** the owner reviewed the four gray areas and directed
"no area needs covered, go with recommendations" (2026-08-31). Every decision below is Claude's,
made under the rationale stated with it. Any of them is open to owner reversal on sight — the
reversibility ratings say what each reversal costs.

### Index provenance — one index, two arms

- **D-01:** **v1's ingest builds the index once; both arms read that same content.** The corpus is
  indexed end-to-end by stock v1 LightRAG (its own pinned environment, per D-04), producing its
  native Cozo graph, Faiss index + sidecar, and KV state. A one-time **import step** loads that
  on-disk state into the v2 namespace layout (Phase 1 D-07: one store directory per namespace),
  **copying vectors verbatim — never recomputing them.** Rationale: PITFALLS 8 says any difference
  in chunking, preprocessing, or embedding between the two paths invalidates the comparison by
  construction. Indexing twice makes embedding drift indistinguishable from a decomposition bug.
  Indexing once makes the query side the only variable under test, which is the whole point of
  rung 2. — **Reversibility:** costly — the import is a build step, but every parity number
  recorded under it is keyed to that one index; re-indexing means re-running the whole comparison,
  not editing a config value.
- **D-02:** **The import is verified, not assumed.** The import step asserts, before any parity run
  is recorded: (a) chunk text is byte-identical between v1's KV and the v2 KV primitive, (b) the
  vector set hashes equal on both sides, (c) the graph node/edge count and ids match. A failing
  precondition makes the harness report `inconclusive`, never a plain pass/fail — PITFALLS 8's own
  prescription, and consistent with the house style of refusals over silent fallbacks.
- **D-03:** **`embedder-index` is authored but does not re-index the corpus in this phase.**
  Criterion 1 requires the port to author it and identify it as its one index-recipe node; §L.1
  records that it is a §1 requirement, not a §19-forced cut. It is authored with a real body and
  registered, and it is **validated by reproduction on a sample** — run it over a sample of chunks
  and check its vectors against v1's stored vectors for that same text — rather than by re-embedding
  the corpus. That is the cheap, decisive check, and it discharges PITFALLS 8's precondition on the
  index side as well. §L.1 notes that feeding the store a vector rather than text supersedes the
  store-internal fallback path (`nano_vector_db_impl.py:807`); the sample reproduction is where that
  substantive difference gets priced.

### The original arm — external, pinned, not imported

- **D-04:** **v1 runs in its own pinned environment (its own `uv` venv under `v1/`), invoked by the
  parity harness as a subprocess.** It is never imported into `databasise/`. Rationale: Phase 1
  D-14's import boundary is structural and enforced by a test (`databasise/tests/test_import_boundary.py`,
  `databasise/tools/check_import_boundary.py`); vendoring v1's query path inside `databasise/` would
  either break that test or need an exemption, and a re-typed copy is no longer "the original".
  v1 has no venv today — standing one up is real Phase 3 work and should be planned as such.
  — **Reversibility:** reversible — the harness owns the invocation; nothing in `databasise/`
  depends on how the original arm is launched.
- **D-05:** **The original arm does NOT run as an opaque node inside the machine in this phase.**
  Admitting v1 as an opaque node is Phase 5's MODAL-02 work, and Phase 1 D-08 already refuses the
  `subprocess` placement by name. The parity harness — not the runner — pairs the two arms. Record
  explicitly in the parity evidence that **the two arms' traces are not symmetric**: the decomposed
  arm produces a full RIG §TR.1 run record, the original arm is instrumented by the harness only.
  Stating the asymmetry is what keeps it from being read later as a measurement claim it is not.

### Model clients — machine primitives, one OpenAI-compatible shape

- **D-06:** **LLM, embedding, and rerank clients are machine-owned primitives injected into the node
  context** — a `clients` mapping alongside the existing `stores` mapping on `NodeContext`, holding
  `llm`, `embedding`, `rerank` handles. They are **not** part-internal. Rationale: this is forced by
  the metering design, not chosen for tidiness — MACH-05 meters spend "at each node's declared
  boundary", and a part-internal HTTP call has no boundary the meter can see. §8 condition 3's
  injected-LLM-provider rule (Phase 5) also needs one machine-side endpoint to inject, and building
  the client anywhere else means moving it later. — **Reversibility:** costly — every ported part's
  body signature assumes where the client comes from; moving it later touches all seventeen.
- **D-07:** **One client shape: OpenAI-compatible chat-completions + embeddings.** OpenRouter and
  Ollama both speak it, and — decisively for this phase — **v1 is configured through env vars that
  speak it too**, so the identical `base_url` / `model` / sampling parameters can be handed to the
  original arm and to the decomposed arm from one pinned record. Two client shapes would mean two
  configuration paths and a parity comparison with an unpinned axis.
- **D-08:** **Models, carried from Phase 2's banked decisions:** generator and keyword LLM =
  `qwen/qwen3.7-flash` via OpenRouter, **provider-pinned** (Phase 2 D-07); embedder = local via
  Ollama (Phase 2 D-09). Identity is derived from the provider/model returned in the response, never
  the requested id (Phase 1 D-12, Phase 2 D-08: hash what is installed, not what is declared).
  Since D-01 builds the index once, the embedder identity has to match across arms only for the
  **query** embedding — a much smaller surface than a two-index design would have needed.
- **D-09:** **Rerank is off in the parity arm.** The `rerank` node is authored and wired — criterion 1
  wants all seventeen positions — but configured as a declared pass-through. It **still declares
  `calls_rerank`**, per §19.9's fallback-reachability rule, exactly as §L.2 has `chunk-sel-kg`
  declare `reads_vector` on a `WEIGHT`-only configuration. Rationale: v1's rerank is off by default
  and needs a separate provider; standing one up adds a cost source and a variance source to the one
  comparison meant to isolate decomposition. — **Reversibility:** reversible — turning it on is node
  config, but a parity number recorded with rerank off does not transfer to a run with it on.

### Parity gate — deterministic at the retrieval level, with `keywords` isolated

- **D-10:** **Criterion 6's deterministic retrieval-level gate is the phase gate. Criteria 4 and 5
  (MACH-02 eval bundle, MACH-03 A/A calibration, Falsifier 5) are deferred once more — to Phase 6's
  side-by-side run.** Rationale, and it is a technical argument rather than a scheduling one: with
  one shared index (D-01) and both arms pinned to one model identity (D-07/D-08), everything
  downstream of keyword extraction is a **deterministic function** of the query embedding and the
  store contents. At that point the retrieval-level comparison is not a weak substitute for an A/A
  floor — it is a *sharper* instrument for the thing rung 2 actually tests (did the re-cut change
  what gets retrieved?). An A/A floor measures answer-level noise, which is exactly what MACH-09's
  default-off posture says not to measure yet. The first comparison that genuinely needs a floor is
  Phase 6's cross-modality run, where no retrieval-level identity exists to lean on.
  — **Reversibility:** reversible — RIG §EV/§AA fully specify the bundle and calibration, and Phase 2
  D-06..D-12 bank every parameter; standing it up later costs nothing that standing it up now would
  have saved.
- **D-11:** **The deferral is recorded, never silent** — the same discipline as GATE-01. Phase 3
  ships a written record amending the ROADMAP's criteria 4 and 5, citing D-10's reason, and naming
  the residual risk plainly: **answer-level drift originating in `keywords` and `generate` stays
  unmeasured until a floor exists.** REQUIREMENTS.md and ROADMAP.md still assign MACH-02/MACH-03 to
  Phase 3 — amend both during planning so coverage tracking follows.
- **D-12:** **Keyword extraction is pinned per query, then measured separately.** `keywords` is the
  one genuinely stochastic node upstream of retrieval, and leaving it live would make "deterministic
  downstream" false. So: run `keywords` once per query, record its output, and feed **the same
  recorded keywords to both arms**. Everything downstream is then exactly comparable. The `keywords`
  node itself is compared on its own — N runs, variance band over its output — which isolates the
  single stochastic query-side node instead of smearing its variance across the whole path. This is
  how criterion 2's "N-run variance band rather than a single diff" is satisfied without an eval
  bundle. — **Reversibility:** reversible — pinning is harness configuration.
- **D-13:** **All five arms, staged over one base.** Base wiring is `mix` (§L.2's own base), then the
  five arm patches as RFC 6902 (Phase 1 / spike 004: 7386 for additive, 6902 for subtraction).
  Rationale: the marginal cost of an arm is a patch file and a run, not new parts, and several
  positions are present in only some arms — `chunk-vector` in `mix`/`naive` only, `entity-lookup` in
  `local`/`hybrid`/`mix` only. Porting one arm would leave positions unexercised and criterion 1
  unmet in substance.
- **D-14:** **Corpus: a small fixed snapshot drawn from HotpotQA distractor, with a recorded hash.**
  Reuses Phase 2 D-06's corpus family so Phase 6 inherits a comparable bundle, and sized to what
  makes one v1 index affordable rather than to what a statistical floor would need — since D-10 is
  not calibrating a floor here.

### Storage-ownership audit — machine-checked, not a prose table

- **D-15:** **Criterion 3's per-node audit ships as a machine-checked artifact emitted from the run
  record**, not a written table. For each of the seventeen nodes, record which store handle(s) it
  actually touched during the parity run and cross-check against that node's declared `effects[]`.
  A node touching a store it did not declare is a **refusal**, not a report line. Alongside it,
  extend the existing import-boundary check to assert no part can reach any `v1.` module.
  Rationale: PITFALLS 1 is precisely that a phase reports "17 of 18 positions decomposed" while every
  node still reaches one singleton — a prose table would report exactly as convincingly in the
  failing case. It also matches the owner's stated want from Phase 2: components visible in a working
  environment, re-runnable and readable, not a buried pytest assertion.

### Claude's Discretion

Owner directed recommendations throughout, so the whole of the above is Claude's call. Beyond it,
these are left open to the planner and executor:

- Shape and file layout of the parity harness, and where the arm patches live on disk (§L.2's
  `Illustrative JSON:` field names `.planning/architectures/wirings/` — that directory does not
  exist; the wirings may reasonably live under `databasise/` instead, where Phase 2's already do).
- The import step's mechanism (direct file copy of the Faiss index vs. read-and-reinsert), provided
  D-02's byte-identity assertions hold.
- Internal structure of the seventeen part bodies, beyond the accepted→emitted kinds §L.2 fixes.
- Test structure and fixture layout, following `databasise/tests/` conventions.
- Form of the declared-deviation record under CONTRACT §5's parity-not-gain rule.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The published node set — this phase's specification

- `docs/system-model/PARTS.md` §L.1 — the eighteen-position node table: component names, §13.4
  types, `effects[]`, `present in` per arm; the three re-derived cuts (`filter-min-score` dropped,
  chunk-budget absorbed into `assemble`, seed+hydration split at a third boundary); the `core/` →
  `lightrag/` namespace demotions; the `embedder-index` port decision. **Read this before writing
  any part.**
- `docs/system-model/PARTS.md` §L.2 — the wiring family: per-node mandatory §13.3 declarations,
  accepted→emitted kinds, declared capabilities (none), `effects[]` union with §19.9's
  over-declaration cost stated, artifact scopes (`quarantined` only), recipe
  (`{"embedding": "embedder-index"}`), the five arms, the two-lever ruling (D-08: parallelism knobs
  are declared executor properties, accuracy knobs are node config), the three decomposition
  requirements R1/R2/R3 and which of them hold, the E/R/C source-labelling correction, and the
  fan-in ordering position (`rank_position` emitted semantics at all three joins).
- `docs/system-model/PARTS.md` §L.3 — the PARTS-01 verdict and the five-arm listing order.

### Frozen contract — what governs the port

- `docs/system-model/CONTRACT.md` §1 — wiring format, identity tuple, `config_hash` over RFC 8785,
  the recipe requirement that forces `embedder-index`, arms and edge semantics
- `docs/system-model/CONTRACT.md` §2 — `NodeKind` tagged sum, the 17-member `effects[]` union,
  undeclared-is-denied
- `docs/system-model/CONTRACT.md` §3 — computed depth, taint rule, blast-radius rule, the three
  artifact scopes, and the accepted-cost framing (D-07) that leaves the ingest side opaque
- `docs/system-model/CONTRACT.md` §4 — `ScoredItem`, `provenance`, `ItemKind`; the score-semantics
  rules the joins declare against
- `docs/system-model/CONTRACT.md` §5 — the parity-not-gain gate and its refusal list; the rule
  criterion 2's "named declared deviations" comes from
- `docs/system-model/CONTRACT.md` §9 — budget as splittable token, metering at declared boundaries
  (governs D-06), merge-side apportionment
- `docs/system-model/CONTRACT.md` §13.1–§13.4 — socket types, per-kind schemas, the fourteen
  primitive part types the nodes are typed against
- `docs/system-model/CONTRACT.md` §19 — the granularity criterion, §19.4's knob-vs-config rule,
  §19.9's fallback-reachability rule (governs D-09's `calls_rerank` declaration), §19.10's boundary
  enumeration
- `docs/system-model/RIG.md` §RUN.1–§RUN.2 — namespace derivation, shared KV, artifact overlap as an
  iff on index-recipe hashes
- `docs/system-model/RIG.md` §TR.1 — the run-record field set the audit (D-15) reads
- `docs/system-model/RIG.md` §EV.1–§EV.3, §AA.1–§AA.3 — the deferred bundle/calibration design; read
  when Falsifier 5 is stood up (Phase 6 per D-10), not for Phase 3 execution
- `docs/system-model/D-VARIANTS/SELECTION.md` — governs on disagreement; D-11's amendment record
  must cite it, as GATE-01's did

### Prior phase decisions this phase is bound by

- `.planning/phases/01-machine-core/01-CONTEXT.md` — D-05 (Cozo + Faiss locked; one-way, the vector
  store is this phase's parity baseline), D-06 (SQLite KV/lexical), D-07 (one store dir per
  namespace), D-09 (per-node concurrency semaphore in `config_hash`), D-11 (no `shared_storage`
  singleton), D-12 (resolved-closure environment hash), D-13 (explicit in-code registry),
  D-14 (no `databasise/` → `v1/` import — governs D-04)
- `.planning/phases/02-falsifier-gate/02-CONTEXT.md` — D-01 (product-first deferral), D-05 (the
  retrieval-level substitute gate this phase implements), D-06..D-12 (banked eval-run decisions;
  D-07/D-09 carried into D-08 here), D-13 (no global concurrency cap in v2)
- `.planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md` — the precedent D-11 follows: a
  condition amended by a written owner-visible record, never silently

### Build research — the failure modes this phase is designed against

- `.planning/research/PITFALLS.md` Pitfall 1 — storage decomposition stalls while logic
  decomposition looks done; the warning signs D-15's audit is built to catch
- `.planning/research/PITFALLS.md` Pitfall 2 — single-run parity hides LLM variance; governs D-12's
  N-run band
- `.planning/research/PITFALLS.md` Pitfall 8 — embedding-generation mismatch silently invalidates
  parity; the decisive argument for D-01 and D-02
- `.planning/research/PITFALLS.md` Pitfall 6 — Cozo 0.7.6's four frozen bugs re-triggered by
  refactoring; binds any new Cozo query construction in the ported nodes
- `.planning/research/ARCHITECTURE.md` — TopologicalSorter + TaskGroup readiness pattern the runner
  already implements

### Spike findings — validated prior work

- `.claude/skills/spike-findings-rag-graph-vector-raw/SKILL.md` — entry point; **spike 005's binding
  order is the reason this phase exists before the ingest phase**: the query path is already
  component-shaped and decomposes first; any reasoning assuming a clean ingest lane is falsified
- `.claude/skills/spike-findings-rag-graph-vector-raw/references/selected-architecture.md` — the
  frozen contract skeleton
- `.claude/skills/spike-findings-rag-graph-vector-raw/references/databasise-engine-reality.md` — the
  fitting seam one level below the modality; the parity harness as rig precedent

### v1 — the porting source, read and run, never imported

- `v1/lightrag/operate.py` (5,995 lines) — the query pipeline §L.1's enumeration was cut against;
  the line references in §L.1/§L.2 (`:4903-4909`, `:4975-5018`, `:5227-5234`, `:5300-5307`,
  `:5556-5559`, `:5628`, `:5825-5838`, `:5887-5889`, `:6100`, `:6102-6112`) all land here
- `v1/lightrag/lightrag.py` — the facade the original arm is driven through
- `v1/lightrag/utils.py:5940-5955` — `min_rerank_score`'s guarded scope, absorbed into `rerank`
- `v1/lightrag/kg/cozo_impl.py` — deferred-write buffering, `run_in_executor` dispatch, bound
  parameters, the four frozen-bug mitigations; all four constraints travel with any port
- `v1/lightrag/kg/faiss_impl.py` — the incumbent vector store and its sidecar; what D-01's import
  step reads
- `v1/lightrag/kg/nano_vector_db_impl.py` ~`:337-354`, ~`:798-820`, `:807` — the ingest-side
  embedding boundary and the store-internal fallback path `embedder-index` supersedes
- `v1/lightrag/kg/shared_storage.py` — **what not to inherit** (Phase 1 D-11, PITFALLS 1)
- `v1/tests/parity/run_substrate_parity.py` — the parity-harness precedent named in the contract
- `v1/lightrag/constants.py` — where §L.2's two-lever ruling was code-verified

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `databasise/parts/registry.py` — `PartRegistry` with `UnknownPartError`, `DuplicatePartError`, and
  `DeclarationOnlyPartError`. The seventeen ports register here. `DeclarationOnlyPartError` is the
  refusal that fires today for `lightrag/query-side@0.1.0` — Phase 3 replaces that stub.
- `databasise/parts/schema.py` — `Part`, `NodeContext` (`node_id`, `config`, `inputs`, `stores`),
  the frozen 17-member `Effect` vocabulary, `Depth`, `ArtifactScope`, `NodeKind`. **D-06 adds a
  `clients` mapping to `NodeContext`** — that is the one schema change the ports need.
- `databasise/stores/` — `graph.py` (Cozo), `vector.py` (Faiss), `kv.py` / `lexical.py` (SQLite),
  `blob.py`, and `base.py`'s `StorageNameSpace` lifecycle. D-01's import step targets these.
- `databasise/runner/` — `scheduler.py`, `budget.py`, `guards.py`, `trace.py`. Already stamps the
  RIG §TR.1 field set (Phase 1 D-10), which is what D-15's audit reads.
- `databasise/validator/` — `parse.py`, `depth.py`, `execution_mode.py`, `blast_radius.py`,
  `cycles.py`. The decomposed wiring must pass this unchanged; it should compute effective depth
  `stage` throughout even though the index came from an opaque producer (spike 005's measured
  result — decomposition credit survives the artifact boundary).
- `databasise/namespaces.py` — namespace derivation; D-01's import lands under it.
- `databasise/tools/check_import_boundary.py` + `databasise/tests/test_import_boundary.py` — the
  existing enforcement D-15 extends.
- `databasise/evidence/` — `FALSIFIER-2-EVIDENCE.md` plus `wirings/*.json` and a runnable
  `falsifier2.py`. **The precedent for how this phase's parity evidence should ship:** committed,
  re-runnable, readable by the owner.

### Established Patterns

- **Refusals over silent fallbacks** — the house style. Governs D-02 (`inconclusive` on a failed
  precondition), D-15 (undeclared store touch is a refusal), and the existing
  `DeclarationOnlyPartError`.
- **Evidence lands as committed files reviewable by the owner**, not transient output.
- **Hash what is installed, never what is declared** (Phase 1 D-12, Phase 2 D-08) — carried into
  D-08's model identity.
- **Wirings are JSON with no evaluation semantics; arms are RFC 6902 patches** (spike 004) —
  governs D-13.

### Integration Points

- `databasise/evidence/wirings/w1-lightrag-query-side.json` currently wires the stub
  `lightrag/query-side@0.1.0` between `parts-core` fakes. Phase 3's real base wiring supersedes it;
  the Falsifier 2 evidence wirings must keep computing the same verdicts afterward, or the change is
  a regression to explain rather than a refactor.
- `databasise/parts_core/declared_only.py` — holds `lightrag/query-side@0.1.0` and
  `lightrag/full-ingest@0.1.0`. The first is retired by this phase; the second stays declaration-only
  until Phase 5.
- Phase 4 consumes: the fitted node set and the arm mechanism, which is what the §18 selectors
  select over.
- Phase 5 consumes: the index-provenance path D-01 builds, which is the thing opaque admission
  formalises.
- Phase 6 consumes: the parity harness, D-14's corpus snapshot, and — per D-10 — the eval bundle and
  A/A floor deferred to it.

### Notable absences found while scouting

- **No LLM, embedding, or rerank client exists anywhere in `databasise/`.** `calls_llm`,
  `calls_embedding`, and `calls_rerank` are effect labels only; every executable part today is a
  fake. D-06 builds the real thing — this is a substantial, unbudgeted-looking chunk of Phase 3 that
  the roadmap's success criteria do not name.
- **`v1/` has no virtualenv.** The pre-decomposition original is not runnable as the repo stands.
  D-04's environment is real work, not a `pip install` afterthought.
- **`.planning/architectures/wirings/` does not exist**, though PARTS §L.2's `Illustrative JSON:`
  field names six files in it. The illustrative wirings were specified but never written.

</code_context>

<specifics>
## Specific Ideas

- Owner directed "no area needs covered, go with recommendations" (2026-08-31) — the four gray areas
  presented (index provenance, the original arm, model clients, parity gate depth) were handed back
  for Claude to settle. Recorded so a later reader does not mistake D-01..D-15 for owner positions.
- Standing owner posture, carried from Phase 2: product-first, human in the loop for verdicts, and
  components visible in a working environment rather than buried in a test suite. D-10 and D-15 are
  both shaped by it.
- The owner's own framing of what decomposition is for, recorded at PARTS §L.2's D-07: components A
  and B compose into hybrid C, and **adjusting only A while measuring C is the point.** That is the
  test of whether this phase's cut is real — not the position count.

</specifics>

<deferred>
## Deferred Ideas

- **MACH-02 / MACH-03 (eval bundle + A/A calibration, Falsifier 5)** → Phase 6's side-by-side run,
  per D-10. Second deferral; Phase 2 D-01 was the first. Phase 2's banked parameters D-06..D-12 still
  apply. REQUIREMENTS.md and ROADMAP.md still assign these to Phase 3 — amend during planning.
- **Rerank as a live path** → whenever a rerank provider is worth standing up; D-09 keeps the node
  and its declaration, so turning it on is node config plus a re-run.
- **The original arm as an admitted opaque node** → Phase 5 (MODAL-02), which is where opaque
  admission and the `subprocess` placement Phase 1 D-08 refuses both get earned.
- **The `.planning/architectures/wirings/` illustrative JSON** named by PARTS §L.2 → either write it
  where §L.2 says, or record that Phase 3's real wirings under `databasise/` supersede it. A
  specified-but-absent file is a documentation defect either way; it belongs with HARD-01/HARD-02's
  doc pass if not resolved here.
- **PARTS defects D1, D2, D7, D12** (write-effect asymmetry, store-instance-grained read
  declaration, mode-partitioned keyword cache, the priority axis with no home in §14.3) → §L.2 marks
  all four unrepaired. They are contract-level defects, not port bugs; note any that the port trips
  over, do not repair them here.
- **HARD-01 / HARD-02** (gate-script vacuous passes, ANATOMY §F reconciliation) → still the later doc
  pass, Phase 7.
- **The fact layer / DR-05 `validity` sub-capability** (Phase 1 deferred) → still open, and Phase 4's
  frozen §18 envelope is its deadline. Not a Phase 3 concern, but the clock is running.

</deferred>

---

*Phase: 3-LightRAG Query Side*
*Context gathered: 2026-08-31*
