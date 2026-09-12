---
phase: 6
phase_name: "hipporag-2-side-by-side"
project: "Databasise 2.0 — Fully Agnostic System"
generated: "2026-09-12"
counts:
  decisions: 29
  lessons: 22
  patterns: 26
  surprises: 16
missing_artifacts: []
---

# Phase 6 Learnings: HippoRAG 2 & Side-by-Side

## Decisions

### `igraph`, `numpy`, `scipy` confirmed legitimate and placed in core dependencies
The owner cleared all three packages at the 06-01 package-legitimacy checkpoint. `igraph>=0.11,<2.0` and `numpy>=1.24,<3.0` landed in `databasise/pyproject.toml`'s `[project.dependencies]`, not behind an optional extra; `scipy>=1.11` followed in 06-06. The dependency name is `igraph`, never the legacy `python-igraph`.

**Rationale:** The `[SUS]` verdicts in 06-RESEARCH were the sandbox's missing-metadata blind spot already documented in 05-LEARNINGS.md, not a slopsquat signature. HippoRAG 2 is a first-class modality of the milestone, not an optional transport like `rest`/`mcp`.
**Source:** 06-CHECKPOINT-ANSWERS.md, 06-01-SUMMARY.md, 06-06-SUMMARY.md

---

### Seam couplings are declared per wiring, not hardcoded per modality
`consumes_query`, `evidence_position` and `store_namespaces` became top-level keys on each wiring's own JSON, read by `seam/engine.py` and `parity/run_arm.py`. `wirings/resolve.py`'s `all_wirings()`/`WIRING_NAMES` replaced the LightRAG-only five-arm candidate list in `seam/selectors.py`. LightRAG's base wiring now declares the exact values those modules previously hardcoded.

**Rationale:** A second modality could not register, resolve or return through constants that named LightRAG's node ids. Declaring the prior hardcoded values on LightRAG's own wiring preserves its behavior by construction. RIG §RUN.1's `derive_namespace()` was deliberately not adopted because it would relocate every existing LightRAG store directory (an on-disk migration per `namespaces.py`'s D-07 note).
**Source:** 06-01-PLAN.md, 06-01-SUMMARY.md

---

### `ctx.stores["graph"]` is a single already-namespaced store, never a `.select()` handle
`ppr.py` calls `ctx.stores["graph"].export_to_igraph()` directly. The plan's literal action prose named a `.select("hipporag-graph")` call that does not exist on `CozoGraphStore`.

**Rationale:** The same plan's `store_namespaces` paragraph states that only the vector store selects per-node by name; kv/graph are each one store already scoped by `_build_stores`. The architecture description, not the action prose, was the consistent reading.
**Source:** 06-01-SUMMARY.md

---

### Every HippoRAG part stays `structural_depth="opaque"`; the upstream-package parity measurement is deferred with a trigger
No HippoRAG part is declared `stage` or `evidence`. The upstream `hipporag` PyPI package is not installed and is not the oracle; `test_ppr.py` pins the transcription risk against a direct `igraph` call with pinned arguments (damping 0.5, undirected, prpack, NaN/negative zeroing, partitioned readback). `HIPPORAG-PORT-RECORD.md`'s Limits section names the deferred measurement, what it would buy, and its trigger.

**Rationale:** An earned depth stated without a parity measurement against a trusted baseline launders an unmeasured claim as a measured one. 06-RESEARCH's "parity means running the upstream package" reading was an inference, not a frozen-document clause, and the upstream package's alpha status and `torch==2.5.1` dependency make it a poor oracle now.
**Source:** 06-01-PLAN.md, 06-07-SUMMARY.md, 06-09-PLAN.md, 06-09-SUMMARY.md

---

### `chunk-embed`'s chunker is a deterministic sliding-window stand-in, not upstream HippoRAG's chunker
A dependency-free character splitter (1200/100 defaults) with SHA-256(`document_id:ordinal`) chunk ids fills the position. Only the id determinism and the batched-embed/store-write contract are load-bearing.

**Rationale:** The real algorithm lives inside the still-opaque, quarantined index-side chain; the node needs the same input/output shape, not the upstream implementation.
**Source:** 06-02-SUMMARY.md

---

### `openie` fails open per chunk on a malformed triple response
A malformed response drops only that chunk's findings; the dispatch never aborts.

**Rationale:** Mirrors the graceful-degradation precedent `keywords.py` and `fact_filter.py` already established rather than inventing a new failure mode.
**Source:** 06-02-SUMMARY.md

---

### Capability-selector keys render in caller order, `+`-joined, never normalised; a key collision refuses by name
`render_selector_key` joins a multi-capability selector's values in the caller's supplied order with the module constant `CAPABILITY_KEY_SEPARATOR = "+"`, without case-folding, sorting or dedup. Two selectors rendering to the same key raise `DuplicateComparisonKeyError` rather than collapsing into one entry.

**Rationale:** §18.4 names no rendering rule for a multi-capability selector, so the plan declared its own as a module constant so a later change is one edit. A silent collapse is the same "partial mapping a consumer cannot distinguish from legitimate emptiness" failure the unsatisfiable-selector rule exists to prevent.
**Source:** 06-03-PLAN.md, 06-03-SUMMARY.md

---

### `compare()` is a thin fan-out over the single-arm `_execute()` path, with arms run sequentially
`compare_arms` builds no second scheduler, store-resolution path or envelope-assembly function. A single selector degenerates to `self._execute(...)` unchanged (RIG §RUN.3); zero selectors raise `EmptyComparisonRequestError`. Parallel arm execution was not introduced.

**Rationale:** A divergent second path is where a redaction rule silently stops applying; the leak gate and §4 provenance redaction apply to every arm by construction. The engine already declares `_CONCURRENCY_SETTING` as sequential and 06-06's calibration is keyed to that setting.
**Source:** 06-03-PLAN.md, 06-03-SUMMARY.md

---

### `judge_instance` is recorded as the literal sentinel `"unresolved"`, never a plausible model string
`bundle@v1` carries `judge_instance: "unresolved"`; the judge prompt text and its SHA-256 are real.

**Rationale:** No live judge call was made, and the project's resolved-identity convention (Phase 1 D-12) forbids substituting a declared id for one read from a real provider response. This matches the `unbudgetable`-over-fabricated-zero convention for token accounting.
**Source:** 06-04-SUMMARY.md

---

### Eval-bundle splits are a deterministic SHA-256 hash of each question id at 60/20/20; the corpus is 30 questions
Both figures are the plan's own unvalidated decisions, stated as such in `EVAL-BUNDLE-V1.md`.

**Rationale:** RIG §EV.1/§10 name no minimum partition size or correct proportions. Sizing to §EV.3's MDE derivation needs cost anchors (§CM.3's A1–A4) the project has not measured; 30 is affordable at both tiers and is presented as that, not as MDE-derived.
**Source:** 06-04-PLAN.md, 06-04-SUMMARY.md, 06-UAT.md

---

### The eval corpus is a second fixture built by parameterising the Phase 3 generator, with offset-anchored query ids
`build_corpus_fixture.py`'s `build()` gained question-count, output-dir and row-offset parameters; the bare invocation still regenerates the Phase 3 corpus byte-identically. Query ids are `q{offset+i+1}` so the eval corpus produces `q3`–`q32`, disjoint from the parity corpus's `q1`/`q2`.

**Rationale:** Resizing the original corpus would change its hash and orphan the v1 index already imported against it. Enumerate-anchored ids would have failed the plan's own "no question id appears in both fixtures" criterion.
**Source:** 06-04-SUMMARY.md

---

### `synonymy-edges`' `num_new_chunks > 0` guard reads `entity-fact-embed`'s entity count as its proxy
The node's sole dependency carries no chunk-count field in its output.

**Rationale:** `entity-fact-embed` short-circuits to zero entities exactly when `openie` found zero findings, which happens only when `chunk-embed` produced zero new chunks; the available data's zero state is a faithful, testable proxy. If a later plan threads a real chunk count through the dep chain, the guard should read it directly.
**Source:** 06-05-SUMMARY.md

---

### `fact-edges`/`passage-edges` declare `effects=[]` genuinely; the graph is written once at `graph-augment-persist` under `quarantined` scope
Both edge builders reach no store and no client. `graph-augment-persist` sets `artifact_scope="quarantined"` on the Part (never the wiring node) and flushes via `index_done_callback`.

**Rationale:** Matches PARTS.md `## §H`'s declared-empty-effects rows. An arm whose nodes resolve to opaque effective depth writes `quarantined`, never `shared`; a shared write would make an unearned index eligible for reuse by another arm.
**Source:** 06-05-PLAN.md, 06-05-SUMMARY.md

---

### The §19.8 guard is declared on `fact-filter`'s own `config.guards`; `assemble-result` reads the outcome through `ctx.inputs`
The guard uses the shape `declare_guard()` consumes (`name`/`evaluating_node`/`value_when_not_fired`/`granularity`), not the illustrative docs copy's top-level richer `guards` array. `assemble-result`'s deps became `[ppr, dpr-fallback, fact-filter]` and `evidence_position` moved from `ppr` to `assemble-result`.

**Rationale:** `runner/guards.py` requires `config.guards` so `config_hash` covers the declaration; the illustrative array is never parsed by `validator/parse.py`. §11 forbids a mid-run read of the run record, so the control signal must arrive as an explicit dep. Moving `evidence_position` makes the envelope reflect whichever branch was actually selected.
**Source:** 06-07-SUMMARY.md

---

### A guard firing as designed is not a degraded or partial run, and is observable only through the trace
A guard-fired run reports `degraded=False`/`partial=False`; the firing is reachable only via `resolve_trace(..., debug=True)`'s `guards_fired`, never in the serialised `ResponseEnvelope`.

**Rationale:** `degraded`/`partial` name an unhealthy run; using them for a declared variant would make a real degradation indistinguishable from an ordinary fallback. No new envelope field was minted.
**Source:** 06-07-PLAN.md, 06-07-SUMMARY.md

---

### `reset-vector-join`'s KV read is authoritative; `entity-fact-embed` additionally writes the `fact:<id> -> {chunk_ids}` KV record
The gap between the two nodes was disposed in 06-05 (reset-vector-join's already-committed, declared and tested `reads_kv` interface wins) and closed in 06-07 by adding `writes_kv` to `entity-fact-embed`, keeping its existing vector-metadata write.

**Rationale:** The governing wiring's `store_namespaces` already named the KV namespace; a real end-to-end run from `chunk-embed` through `reset-vector-join` had no writer for the record the reader consumed. 06-05's `<files>` list named neither module, so the fix belonged to the plan that landed the last query-side position.
**Source:** 06-02-SUMMARY.md, 06-05-SUMMARY.md, 06-07-SUMMARY.md

---

### Deferred spends are recorded as BLOCKED, never rounded to passed, failed or skipped
06-06: owner chose `defer-run` for the A/A calibration (T0 blocked by unresolved judge identity, T1 by unbudgetable eval-corpus ingest). 06-08: owner chose `defer-and-record-blocked` for the cross-modality run. Both evidence documents were rewritten from a passing-verdict shape to a BLOCKED shape on the owner's explicit instruction, with the requirement rows left Pending.

**Rationale:** The owner's standing posture is build the product first, expensive measurement is opt-in. A declined checkpoint is a complete outcome of a plan; no fabricated or estimated number may exist in the committed record.
**Source:** 06-06-SUMMARY.md, 06-08-SUMMARY.md, 06-13-PLAN.md

---

### MACH-03 is deferred a fourth time to the first gate-adjudicated promotion, outside this milestone
After three owner declines (06-06, 06-13, 06-17), `06-GATE-AMENDMENT.md` re-times the A/A floor to its point of first need. `03-GATE-AMENDMENT.md`'s standing condition is narrowed to "no *gate-adjudicated* promotion decision and no parity claim before the A/A floor exists." Phase 6 stays `gaps_found`; Phase 7 is authorised to start.

**Rationale:** Phase 7 builds only the operator-asserted path (RIG §PR.3, CONTRACT §7), which carries trace ids in place of an evidence pointer and consumes no floor. Under MACH-09's default posture the gate-adjudicated path stays unavailable for all of v1. The argument is recorded as Claude's, the decision as the owner's.
**Source:** 06-GATE-AMENDMENT.md, 06-17-SUMMARY.md, 06-VERIFICATION.md

---

### F-07 disposes every mutable-store component as `permanent-exclusion`, enforced by `MutableStoreComparisonExcludedError`
`codebase-memory-mcp@0.1.0` (CA-2) and `lightrag/full-delete@0.1.0` both carry permanent exclusion from §5 parity/determinism comparisons. `Databasise.compare()` resolves every selector up front and raises before `compare_arms` if any resolved wiring's effect union contains `mutates_store`. `full-delete`'s exclusion is recorded as a structural fact (never in the candidate pool), not an enforced refusal.

**Rationale:** 06-RESEARCH recommended exclusion as the lower-risk default and no requirement asks for that engine's mutation behavior to be A/B-testable. The owner confirmed the disposition in 06-UAT.md Test 1, after which MACH-10 flipped to Complete (06-11).
**Source:** 06-09-SUMMARY.md, 06-11-SUMMARY.md, 06-UAT.md

---

### `codebase-memory-mcp`'s wiring is not added to the production candidate pool
`WIRING_NAMES` stays `("lightrag", "hipporag")`. The mutable-store exclusion test drives the real committed wiring through `Databasise.compare()` via a test-scoped `monkeypatch` of `_capability_candidates()`.

**Rationale:** Adding a non-modality dev tool as a comparable query modality is an architectural decision outside the plan's scope, and `load_wiring()`'s `<name>/base.json` layout does not fit the committed file anyway.
**Source:** 06-09-SUMMARY.md

---

### A requirement is never marked Complete on the strength of a plan having run
Every Phase 6 row carries a dated annotation naming the committed evidence; MACH-03, MODAL-05 and MACH-10 stayed Pending against a named outstanding item until discharged. Annotations are appended, never rewritten, so a row's history stays visible.

**Rationale:** Phase 5's lesson: five never-defective rows were reverted en masse from a phase status. The status must reflect what the committed evidence establishes, and the plan's `requirements:` frontmatter naming an ID is not the same as the requirement completing.
**Source:** 06-09-PLAN.md, 06-09-SUMMARY.md, 06-11-SUMMARY.md, 06-12-SUMMARY.md, 06-18-SUMMARY.md

---

### HippoRAG ingest is a real wiring; HippoRAG delete is a named refusal
`databasise/wirings/hipporag/corpus-ingest.json` re-composes `base.json`'s seven index-side node objects. `delete_document()` raises `NoWritePathForModalityError` for HippoRAG.

**Rationale:** All seven index-side positions already existed and ran together in `build_hipporag_index.py`, so ingest needed no new node code. No HippoRAG node retracts vectors or edges anywhere in the repository; a delete wiring would need new node code, which the gap brief put out of scope.
**Source:** 06-10-PLAN.md, 06-10-SUMMARY.md

---

### `artifacts_overlap` compares the resolved wiring's own canonicalise hash, pre-query-injection
The cross-modality harness records overlap between the two arms' structural identity hashes, and never gates on it — an unexpected `True` is a human-judgment finding.

**Rationale:** No per-query call site computes a standalone "index recipe" hash via `derive_namespace()`'s eight-input scheme today; the pragmatic choice is stated in `run_cross_modality.py`'s docstring.
**Source:** 06-08-SUMMARY.md

---

### The eval-corpus ingest path uses its own dedicated store root
`corpus_ingest.py`'s `--spend` path lands in `v1/.eval_corpus_store` (workspace `eval-corpus-ingest`), separate from the Phase 3 parity store and the Phase 6 build-harness store.

**Rationale:** A real eval-corpus ingest must never land documents in either of the other two stores' directories.
**Source:** 06-12-SUMMARY.md

---

### The `fact-score` defect was fixed at the harness wiring level plus one client-level guard, not inside `fact_score.py`
`build_hipporag_index.py` now resolves `load_wiring("hipporag", variant="corpus-ingest")` (seven index-side positions). `OpenAICompatibleClient.embed` raises `EmptyEmbeddingInputError` for any empty or whitespace-only batch item before a request is constructed.

**Rationale:** The actual defect was an unauthorized dispatch (query-side nodes in an index build), not a missing input check on an authorized one. Three other query-side call sites carry the same unguarded `str(config.get("query", ""))` pattern and `entity_fact_embed.py` can hand `embed()` an empty list; one guard at the method all seven call sites route through covers every case.
**Source:** 06-14-PLAN.md, 06-14-SUMMARY.md

---

### The "materially narrower" threshold is pre-registered as `T1 floor <= 0.5 × T0 floor` before any floor exists
Adopted from 06-RESEARCH Open Question 1 and committed to `FALSIFIER-5-EVIDENCE.md`'s `## Pre-registered threshold — 2026-09-11` section before `aa_run --spend` could be invoked. Both floors are treated as unit-interval scores by construction.

**Rationale:** A threshold chosen after seeing two numbers is a description of the result, not a criterion. A future plan wanting a different threshold must pre-register it the same way.
**Source:** 06-17-PLAN.md, 06-17-SUMMARY.md, 06-GATE-AMENDMENT.md

---

### `aa_run.py` scoring assumptions: `PARTIAL` scores 0.5, gold-passage uses recall over the gold set, default split is `dev`
Each is a declared module constant or named metric (`gold_passage_recall`) so it travels with every `NullIdentity`.

**Rationale:** The committed judge prompt defines three verdicts with no weights; RIG §EV.2 names the family, not the formula; `holdout`/`sealed` follow the bundle module's one-shot opening protocol.
**Source:** 06-16-PLAN.md

---

### Roadmap SC6 takes the Phase 3 parenthetical annotation form, not Phase 7's struck-through form
The original criterion sentence survives byte-for-byte with an appended parenthetical citing `06-GATE-AMENDMENT.md`.

**Rationale:** The amendment states condition 6's substance is "re-timed a fourth time, not withdrawn"; a strike-through would misstate that.
**Source:** 06-18-PLAN.md, 06-18-SUMMARY.md, 06-VERIFICATION.md

---

### Stale research recommendations are corrected in place with a dated supersession note, never deleted
`STACK.md`'s LanceDB rows were corrected to name Cozo/Faiss as the shipped defaults; `grep -c lancedb` still returns 10.

**Rationale:** The document's history stays readable; a reader sees what was recommended and what superseded it.
**Source:** 06-09-SUMMARY.md, 06-UAT.md

---

## Lessons

### The registered wiring schema rejects fields the illustrative docs copy carries
`WiringNode` (`parts/schema.py`, `extra="forbid"`) refuses a `note` key. Copying the governing `docs/system-model/wirings/hipporag-base.json`'s `note` field into `databasise/wirings/hipporag/base.json` raised `WiringRefusedError` at parse time, cascading into the seam cross-modality tests.

**Context:** Caught during 06-02's first full-suite verify and fixed before landing. Any future position added to this wiring by copying from the docs copy hits the same refusal.
**Source:** 06-02-SUMMARY.md

---

### `uv sync --extra X` is an exact sync, not an additive install
Running `uv sync --extra mcp` after `uv sync --extra rest` uninstalls `fastapi`; a bare `uv sync` drops both. Tests guarded by `pytest.importorskip("fastapi")` then skip silently, and the literal verify command still passes because not every test skips.

**Context:** 06-03's verify sequence skipped `test_dual_transport_parity.py`'s whole module including the new `compare` scenario; 06-04 briefly saw a lower bare pass count for the same reason. Always install both extras together (`uv sync --extra rest --extra mcp`) when authoring verify commands.
**Source:** 06-03-SUMMARY.md, 06-04-SUMMARY.md

---

### `gsd_run check tdd-red-evidence` cannot classify pytest output
The tool parses TAP/Node-test-runner summaries and does not read pytest's default format. RED evidence in this Python project must be verified manually from pytest's exit code and per-test failure attribution.

**Context:** Recorded in 06-01, 06-02 and 06-12; the working substitute is committing tests with a deliberately broken draft implementation, capturing real `AssertionError`s, then restoring the correct body for GREEN.
**Source:** 06-01-SUMMARY.md, 06-02-SUMMARY.md, 06-12-SUMMARY.md

---

### A `dict` subclass's `__eq__` override does not apply to `!=`
`dict`'s C-level `__ne__` slot does not fall back to a subclass's `__eq__` the way plain Python classes do; `d != False` returned `True` even when `d == False` was `True`. `evaluate_guards`'s `!=` comparison bypassed `_GuardAwareResult.__eq__` entirely until `__ne__` was also defined.

**Context:** Found during 06-07's GREEN verify, alongside an inverted boolean in the first `__eq__` draft. Both directions of the guard are now tested.
**Source:** 06-07-SUMMARY.md

---

### `resolve_trace` returns no `nodes` unless `debug=True`
`Databasise.resolve_trace` filters to `_NON_DEBUG_TRACE_FIELDS` by default; a test reading the node-by-node trace hit `KeyError: 'nodes'`.

**Context:** 06-07's guard-branch tests needed `guards_fired`, which only the debug trace carries.
**Source:** 06-07-SUMMARY.md

---

### `finalize()` never commits pending store writes; `index_done_callback()` must run first
Store-writing nodes stage writes in each store's in-memory pending buffer. `ingest()`'s existing `finally: await store.finalize()` would have silently discarded every HippoRAG chunk/entity/fact vector and KV record on return.

**Context:** 06-10 was the first real write-path run through the seam to hold a store-writing node's handle. The fix (`index_done_callback()` on every store after a successful `run_wiring`, before `finalize()`) is a no-op for LightRAG's opaque path.
**Source:** 06-10-SUMMARY.md

---

### The first real-corpus run surfaced a defect no fixture test had exercised, and the root cause was two layers away from the traceback
The provider returned `400 too_small` from `fact-score` because `build_hipporag_index.py` loaded the 13-node base wiring for an index build; `fact-score` (`deps: []`) dispatched in the first batch with no query injected. 06-10 had already built the correct seven-node `corpus-ingest.json`; the harness never used it.

**Context:** Real spend was incurred on 2026-09-10 with no comparison produced. 06-13's checkpoint rule ("a non-zero exit is a refusal, not a result; never retry with a weakened guard") prevented a mid-checkpoint patch; 06-14 fixed the root cause and 06-15's re-run completed cleanly.
**Source:** 06-13-SUMMARY.md, 06-14-PLAN.md, 06-14-SUMMARY.md, 06-15-SUMMARY.md

---

### "Only the spend remains" was wrong: no A/A driver existed
`calibrate_aa_floor`'s only callers were its own tests; nothing ran an arm twice over the bundle's questions or scored envelopes against gold. An `approve` at 06-13 would have funded a run with no code to perform it.

**Context:** Discovered by reading the code during 06-16 planning, after two declines had been recorded against preconditions and defects. The driver (`databasise/eval/aa_run.py`) was built before the third ask in 06-17.
**Source:** 06-16-PLAN.md, 06-17-PLAN.md, 06-16-SUMMARY.md

---

### Enumerating from the live registry finds what a hand-transcribed roster misses
Computing the F-07 population from `default_registry()` surfaced `lightrag/full-delete@0.1.0` as a mutable-store component `MODEL-RED-TEAM.md`'s frozen three-entry roster never named.

**Context:** The record now derives its population from the registry and raises if it finds a `mutates_store` component without a named disposition.
**Source:** 06-09-SUMMARY.md

---

### A plan's `read_first` framing can be false; verify reachability in code before building on it
06-09's brief said `codebase-memory-mcp.json` was "now reachable through the candidate pool." It was not: `WIRING_NAMES` names only `lightrag`/`hipporag`, and `load_wiring()`'s directory layout does not fit the file.

**Context:** Recorded as a code-verified fact in the F-07 record; the test used a scoped monkeypatch rather than a production change.
**Source:** 06-09-SUMMARY.md

---

### A corpus-size figure carried between plans was overstated by 64%
06-13's checkpoint text cited the Phase 3 parity corpus as 15,711 bytes / 2,119 words; `load_snapshot()` and `wc` both measure 9,597 bytes / 1,590 words. `MANIFEST.json` states no byte or word count at all.

**Context:** The projection's conclusion was unaffected and the approved checkpoint text was left as the owner saw it. Any future projection must call `load_snapshot()` or `wc`, not reuse the stale figure. 06-15 carried the same figure forward deliberately to avoid a second differently-rounded number.
**Source:** 06-13-SUMMARY.md, 06-15-PLAN.md

---

### Graph vertex names and vector/KV record keys live in different identity spaces
`ppr`'s readback identifies passage vertices by the prefixed graph name (`chunk:` + chunk_id); `chunk-embed` writes the chunk's KV/vector records under the bare chunk_id. The mismatch only surfaced in the first real ingest-to-query round trip.

**Context:** 06-10's test forced the DPR-fallback branch (vector-only path) to avoid it; the mismatch is left unfixed and outside that plan's `<files>` scope for `ppr.py`/`passage_edges.py`.
**Source:** 06-10-SUMMARY.md

---

### `resolve_evidence_ref` reads vector-store metadata only, never the sibling KV record
A HippoRAG-ingested chunk could not resolve to its own text until `chunk_embed.py` added `"content"` to the vector metadata, mirroring LightRAG's content-carrying Faiss meta convention.

**Context:** Found while writing 06-10's evidence-resolution assertion.
**Source:** 06-10-SUMMARY.md

---

### Once the seam resolves a selector, every candidate wiring must parse against the test registry
`ingest()`/`delete_document()` now call `resolve_selector()` first; the no-selector default path requires every wiring `all_wirings()` enumerates to parse. Test helpers that built a registry holding only the part under test broke in four files.

**Context:** Rebuilt each helper atop a full `default_registry()` with the test-local part swapped in by name.
**Source:** 06-10-SUMMARY.md

---

### A bare `RuntimeError` in an except tuple swallows the refusals the code must not catch
`aa_run.main()`'s `--spend` handler caught `RuntimeError`, which also caught `calibration.StaleNullError` (a `RuntimeError` subclass `calibrate_family` must not handle) and any unrelated `RuntimeError` deeper in the chain.

**Context:** Review finding WR-02; fixed by a named `ConfoundedPassError` and a regression test (WR-01) that drives `main()` and asserts exit code 1.
**Source:** 06-REVIEW-FIX.md

---

### Pinned suite figures go stale across documents; assert what is measured and state the cause
06-VERIFICATION.md and 06-17-SUMMARY.md cite 962 passed / 6 warnings; 06-18 measured 1068 / 8 (Phase 7's five plans added tests; 06-REVIEW-FIX's two sync tests each added a warning).

**Context:** A gate keyed to a stale count fails on a correct change. The older documents were not rewritten; the reconciliation is stated in the SUMMARY.
**Source:** 06-18-PLAN.md, 06-18-SUMMARY.md

---

### A module-level `pytestmark = pytest.mark.asyncio` under `asyncio_mode = "auto"` is redundant for async tests and wrong for sync ones
The mark applied to every test in `test_aa_run.py` regardless of definition style, producing one `PytestWarning` per sync test.

**Context:** 06-18 deleted it after confirming `asyncio_mode = "auto"` in `pyproject.toml`; had the mode been `strict`, the deletion would have silently stopped the async tests from being awaited while still exiting 0.
**Source:** 06-18-PLAN.md, 06-18-SUMMARY.md, 06-REVIEW.md

---

### Ground truth for a requirement's status is the checkbox, not a SUMMARY's frontmatter
06-18-SUMMARY.md's frontmatter carried `requirements-completed: [MACH-03]` while its body stated the `update_requirements` step was deliberately skipped. The verifier scored MACH-03 Pending from `.planning/REQUIREMENTS.md`'s `- [ ]`.

**Context:** A plan's `requirements:` field can link paperwork *about* a requirement (the SC6 annotation), not its discharge.
**Source:** 06-VERIFICATION.md, 06-18-SUMMARY.md

---

### Recovering an interrupted executor's draft: verify the file, not the recovery note
06-16's draft `aa_run.py` and its tests were fully written but uncommitted; a `del StaleNullError` line referencing a never-imported name raised `NameError` at import time. The recovery note said "6 tests is thin"; `grep -c "def test_"` counted 13, matching the plan one-for-one.

**Context:** Before deleting the dead statement, `calibration.py` was read in full to confirm `calibrate_family` never calls `floor_for`, so the deletion adds no second, weaker path to a floor. The finished draft was committed as one task commit rather than an artificial two-commit split.
**Source:** 06-16-SUMMARY.md

---

### Documents mined by automated gates need the exact table shape the parser reads
COVERAGE.md failed the `api-coverage` gate as "matrix is empty" because the parser needs a `| capability |` table or a `No external API integration: <reason>` line, not the §18.5 operations table. Phases 04 and 05 failed identically.

**Context:** Fixed by adding the declaration line; no content changed.
**Source:** 06-UAT.md

---

### `pycozo` prints a `pandas` `ModuleNotFoundError` traceback at every store construction
It is an optional-feature probe inside a `try`, printed but caught internally; both harnesses continued and exited 0.

**Context:** 06-15 evaluated the plan's "record honestly if a run fails in a new way" rule against it and found it did not apply, since neither harness raised or reported a failure.
**Source:** 06-15-SUMMARY.md

---

### A real OpenIE extraction pass exceeds the 600 s foreground command timeout
The 20-document build made 40 LLM calls (109,341 completion tokens) and had to be run in the background and polled by PID.

**Context:** Any future real index build should be launched detached from the start rather than retried after a timeout.
**Source:** 06-15-SUMMARY.md

---

## Patterns

### Wiring-level declarative seam coupling
A new cross-modality behavior (query injection point, evidence position, store namespaces) is added as a top-level wiring key the seam reads, and every existing wiring is updated to declare its prior hardcoded value.

**When to use:** Any time the seam would otherwise branch on a modality name or import a per-modality constant. Existing behavior is preserved by construction, not by re-testing.
**Source:** 06-01-SUMMARY.md

---

### §14.2 bulk capabilities are second store methods, never loops over the pointwise path
`export_to_igraph()` beside `get_node_edges` (two Cozo queries regardless of graph size); `score_all()` beside `query()` (no top-k truncation); `self_knn()` (one Faiss search over the whole matrix). Each is proven by a call-count test at two sizes plus a negative control.

**When to use:** Whenever a modality needs whole-graph or whole-matrix access. A loop that produces the right numbers hides a capability the store has not earned.
**Source:** 06-01-PLAN.md, 06-01-SUMMARY.md, 06-05-PLAN.md, 06-05-SUMMARY.md

---

### Per-task TDD RED/GREEN with a deliberately wrong stub body
The `test(...)` commit carries the test file plus a stub body that ignores config/inputs and makes zero client calls, so target tests fail on real assertions rather than a collection error; the `feat(...)` commit replaces it with the real body.

**When to use:** Every `tdd="true"` task in this Python project, since the TAP-oriented RED-evidence tool cannot read pytest output.
**Source:** 06-02-SUMMARY.md, 06-05-SUMMARY.md, 06-12-SUMMARY.md

---

### Summed `TokenAccounting` for multi-call nodes
`_sum_token_accountings` sums prompt/completion/cached_read/call_count across calls, propagates the `unbudgetable` sentinel if any call carried it, otherwise inherits the first call's `counted_by`.

**When to use:** Any node making more than one client call per dispatch (`openie`'s two calls per chunk, `entity-fact-embed`'s two batched embeds).
**Source:** 06-02-SUMMARY.md, 06-UAT.md

---

### Content-addressed versioning with a separate integrity sidecar
A bundle version's identity is SHA-256 over the RFC 8785 canonicalisation of exactly the invalidating inputs (re-minting identical input is idempotent; any change mints a new sequential version). A separate `bundle.sha256` checksum of the raw bytes detects later on-disk mutation.

**When to use:** Any minted, append-only artifact whose identity keys other records (`eval_bundle@v` in §4's pooling key).
**Source:** 06-04-SUMMARY.md

---

### Partition discipline enforced in code
`dev` is a plain read; `holdout` is gated behind an append-only usage log (`record_holdout_use`/`read_holdout`); `sealed` is reachable only through `open_sealed`, which unconditionally mints a new version and logs the opening event.

**When to use:** Any split whose value depends on whether it has been consulted.
**Source:** 06-04-SUMMARY.md

---

### Parameterise the existing fixture generator rather than resizing the fixture
`build()` gained question count, output dir and row offset; the default invocation stays byte-identical.

**When to use:** Adding a second corpus while a committed hash or imported index depends on the first.
**Source:** 06-04-SUMMARY.md

---

### One canonical order-insensitive pair convention across every edge builder
A sorted endpoint tuple keys `fact-edges`, `passage-edges` dedup, `synonymy-edges`, and `graph-augment-persist`'s weight-collapse grouping; `ENTITY_VERTEX_PREFIX`/`CHUNK_VERTEX_PREFIX` are imported from one module, never re-spelled.

**When to use:** Any set of nodes sharing an identity space; one convention with four call sites cannot drift.
**Source:** 06-02-SUMMARY.md, 06-05-SUMMARY.md

---

### Store-method proxy for call-counting a C-extension method
Wrap the instance attribute holding the Faiss index in a proxy that delegates everything via `__getattr__` except the counted `search()`.

**When to use:** When the bound method itself cannot be monkeypatched (C extensions). `CozoGraphStore` needs no proxy because `_run` is an ordinary Python method.
**Source:** 06-05-SUMMARY.md

---

### House-format BLOCKED evidence record
Same sections as a passing/failing record (dated header, verbatim claim quote, findings table with one row per blocker, owner-decision section, method-and-limits, entry criterion), plus a structural test suite asserting the document names its blockers and never reports a numeric result.

**When to use:** Any falsifier or requirement whose run was deferred, so a reader recognises an honestly-unrun item without learning a second document shape.
**Source:** 06-06-SUMMARY.md, 06-08-SUMMARY.md, 06-17-SUMMARY.md

---

### Pre-flight-then-run harness shape
Assert every hard precondition by name (env file and keys, prior index present, store directories disjoint) before any spend; verify the post-run state (non-zero graph/vector counts, both vertex prefixes present) before reporting success; read token spend from `assemble_token_breakdown`, never an estimate.

**When to use:** Any harness that incurs real spend. `build_hipporag_index.py` and `run_cross_modality.py` mirror `import_index.py`/`run_comparison.py`; 06-15 re-verified all preconditions live before the re-attempt rather than trusting the prior record.
**Source:** 06-06-SUMMARY.md, 06-08-SUMMARY.md, 06-15-SUMMARY.md

---

### A deferred-spend plan still lands a complete, runnable harness
The harness is written to the standard of a live run, committed unexecuted, with real-index tests skip-guarded by a pure path-existence check and synthetic-store tests exercising the same logic.

**When to use:** When the run itself is the withheld decision. The skip guard must never construct a store, so collecting the module cannot mutate the real parity store.
**Source:** 06-08-SUMMARY.md

---

### One shared helper for a formula two nodes compute
`dpr_fallback.py`'s `dense_passage_retrieval()` is imported by `reset_vector_join.py` instead of re-implemented.

**When to use:** Whenever two positions cite the same upstream call; a future edit cannot silently diverge them.
**Source:** 06-07-SUMMARY.md

---

### Control-channel-is-a-read with a comparison-aware result wrapper
A node needing another node's control signal becomes an explicit dep so the signal arrives via `ctx.inputs`. `_GuardAwareResult` (a `dict` subclass overriding `__eq__` and `__ne__`) lets `evaluate_guards`'s whole-output comparison read one boolean field against a JSON-literal `value_when_not_fired` sentinel with no second guard mechanism.

**When to use:** Wiring a per-node live guard on a node whose other outputs vary per query. This was the first production use of `runner/guards.py` against a rich-payload node.
**Source:** 06-07-SUMMARY.md

---

### Render-from-committed-inputs evidence records
`render_f07_record()` is a pure function of `default_registry()` plus a fixed catalogued-not-built table; a test asserts the committed `.md` is byte-identical to its output, and the renderer raises on an empty enumeration or an undisposed component.

**When to use:** Any evidence document whose population should be computed, not transcribed (second application after `parity_report.py`).
**Source:** 06-09-SUMMARY.md

---

### Test-scoped candidate-pool monkeypatch
A fixture reads a real committed wiring JSON and appends it to `_capability_candidates()` for the duration of one test, driving real selector resolution with zero production change.

**When to use:** Exercising a real wiring the production pool deliberately excludes; keep one test without the fixture to prove production behavior is unaffected.
**Source:** 06-09-SUMMARY.md

---

### On-disk file existence as the dispatch table
`wirings/<family>/corpus-<operation>.json` existing is the write-path decision; `load_wiring(name, variant=...)` generalises the same layout for index-side vs query-side.

**When to use:** Per-modality operation lookup. No dict, no registry; a new modality needs only files.
**Source:** 06-10-SUMMARY.md, 06-14-SUMMARY.md

---

### Dual-key document stamping
`ingest()` stamps both `id` and `document_id` on each document dict so LightRAG's opaque node and HippoRAG's `chunk-embed` each read the key they need.

**When to use:** When two node families read different key names from one caller-supplied shape and a per-family branch in the seam is not wanted.
**Source:** 06-10-SUMMARY.md

---

### Estimate-first, spend-only-on-opt-in CLI
`--limit` prints a real computed projection and constructs no client; `--spend` is the sole flag that reaches a real client or store. An over-large limit refuses (`LimitExceedsCorpusError`) rather than clamping. `aa_run` follows the same shape with `estimate_calls`.

**When to use:** Any entry point that can incur live spend; the owner then decides against a number, never an unknown.
**Source:** 06-12-SUMMARY.md, 06-16-SUMMARY.md

---

### Thin call-through that adds no second mechanism
`remint()` relies entirely on `mint_bundle`'s existing content-hash idempotence over `judge_instance`; `aa_run` never catches `calibrate_aa_floor`'s own refusals.

**When to use:** When the underlying module already enforces the invariant; adding a second dedup or refusal path would weaken it.
**Source:** 06-12-SUMMARY.md, 06-16-SUMMARY.md

---

### One named refusal at the single method every caller routes through
`EmptyEmbeddingInputError` at `OpenAICompatibleClient.embed` replaces per-call-site guards across seven embedding call sites.

**When to use:** A failure class shared by many callers; the shared method turns a live provider `400` into a diagnosable local refusal.
**Source:** 06-14-SUMMARY.md

---

### Evidence and verification documents grow by dated appended sections
Spend checkpoints append a dated house-sectioned entry (`## Deferred a third time — 2026-09-11`, `## Real run — 2026-09-10`); `06-VERIFICATION.md`'s correction is an append citing commit hashes, never a rewrite of status/score/gap bodies. A harness's own refusal is recorded as "attempted and refused," distinct from success and from an undecided deferral.

**When to use:** Any re-run or re-decision; the history of every deferral and attempt stays readable in one place.
**Source:** 06-13-SUMMARY.md, 06-15-SUMMARY.md, 06-17-SUMMARY.md

---

### Pre-register the comparison threshold in writing before either side is computed
Committed to the evidence document as a formula over not-yet-existing floors; the structural test's smuggled-value regex was narrowed so a `<=` formula does not read as a reported number.

**When to use:** Any pass criterion that compares two measured values.
**Source:** 06-17-SUMMARY.md

---

### Pinned-count tests updated per addition with a provenance note
`test_registry.py` and `test_registration.py` pin exact registry counts and a per-part shape table; each new part updates the count, extends the shape table, and renames the count-named test.

**When to use:** Every plan that registers a part or adds a runtime dependency. The pins exist specifically to catch such changes.
**Source:** 06-01-SUMMARY.md, 06-02-SUMMARY.md, 06-05-SUMMARY.md, 06-07-SUMMARY.md

---

### Identity-leak checks derive their forbidden-token set live
`test_no_internal_identity_leaks` builds its forbidden set from the registry and both resolved wirings (node ids, wiring ids, `provenance`, instance-hash-shaped values), never a hand-written list.

**When to use:** Any seam-boundary test; a hand list goes stale the moment a node is added.
**Source:** 06-03-SUMMARY.md

---

### Conformance tests pin the decomposition claim against the governing record at test time
`test_thirteen_positions.py` asserts the built wiring's node-id set equals PARTS.md `## §H`'s thirteen and that the declared-effects union equals the governing union plus exactly the recorded additive set; `test_hipporag_port_record.py` asserts the reconciliation table covers exactly the computed divergent-node set.

**When to use:** Any port whose completeness is a requirement; a future part gaining an undeclared effect fails as an unrecorded divergence rather than passing by omission.
**Source:** 06-07-SUMMARY.md

---

## Surprises

### The first authorized real run was refused by the harness's own post-build verification
Real spend was incurred on 2026-09-10 and no comparison was produced: `fact-score` handed the provider a zero-length string.

**Impact:** MODAL-05 moved from "unauthorized" to "blocked on a concrete defect"; the owner declined the A/A spend a second time to sequence the fix first. The money did not come back; 06-14 ensured it would not be spent the same way twice.
**Source:** 06-13-SUMMARY.md, 06-15-PLAN.md

---

### The defect's root cause was in the harness, not in the node the traceback named
`build_hipporag_index.py` used the 13-node base wiring instead of the already-committed 7-node `corpus-ingest.json`.

**Impact:** The WINDOWS.md entry filed against `fact_score.py` was closed by a wiring-variant change plus a client-level guard; no part body changed.
**Source:** 06-14-SUMMARY.md

---

### MACH-03's stated blocker omitted a missing driver
Two owner declines were recorded against preconditions and defects before anyone noticed `calibrate_aa_floor` had no caller outside its tests.

**Impact:** An additional plan (06-16) was needed before the spend question was genuinely answerable; 06-17 was the first ask with real code behind it.
**Source:** 06-16-PLAN.md, 06-17-PLAN.md

---

### A fourth mutable-store component existed that the frozen red-team roster never named
`lightrag/full-delete@0.1.0` surfaced only because the F-07 record computes its population from the registry.

**Impact:** Recorded with the same permanent-exclusion disposition; its exclusion is structural (never in the candidate pool) rather than enforced.
**Source:** 06-09-SUMMARY.md

---

### `codebase-memory-mcp`'s wiring was not reachable through any production selector
The plan brief assumed otherwise.

**Impact:** The mutable-store exclusion test needed a scoped monkeypatch; widening `WIRING_NAMES` was declined as an out-of-scope architectural change.
**Source:** 06-09-SUMMARY.md

---

### The parity corpus size cited to the owner was 64% too large
15,711 bytes / 2,119 words was carried into the checkpoint text; the measured figure is 9,597 bytes / 1,590 words.

**Impact:** No effect on the "well under 1M tokens" conclusion; the approved text was left unchanged so the record shows what the owner actually saw.
**Source:** 06-13-SUMMARY.md

---

### `dict`'s `__ne__` slot ignores a subclass `__eq__`
Confirmed with a standalone repro during 06-07.

**Impact:** `_GuardAwareResult` needed an explicit `__ne__`; without it the guard comparison silently never fired.
**Source:** 06-07-SUMMARY.md

---

### `uv sync --extra` uninstalls extras it was not asked for
A plan's own verify sequence passed while silently skipping an entire test module.

**Impact:** The `<fails_when>` condition did not trip because only some tests skipped; verified separately with both extras installed together.
**Source:** 06-03-SUMMARY.md, 06-04-SUMMARY.md

---

### `ingest()` would have silently discarded every HippoRAG write
`finalize()` alone never flushes pending buffers; the first real write-path run through the seam exposed it.

**Impact:** Every HippoRAG chunk/entity/fact vector and KV record was being dropped on return until `index_done_callback()` was added.
**Source:** 06-10-SUMMARY.md

---

### The first ingest-to-query round trip exposed a graph/vector identity-space mismatch
`chunk:`-prefixed vertex names vs bare chunk ids in vector/KV records.

**Impact:** 06-10's test deliberately forced the DPR-fallback branch to avoid it; the mismatch stays open and undocumented as a distinct issue.
**Source:** 06-10-SUMMARY.md

---

### LightRAG's `local`/`global` guard has never been wired live
It remains illustrative-only in the docs; 06-07's `zero_surviving_facts_dpr_fallback` guard was the first real production use of `runner/guards.py`.

**Impact:** The guard machinery had never been exercised against a rich-payload node before, which is why the `__eq__`/`__ne__` mechanism had to be invented in this phase.
**Source:** 06-07-SUMMARY.md

---

### The full suite's pass count drifted from 962 to 1068 between two Phase 6 documents
Phase 7's plans landed tests while Phase 6's gap-closure rounds were still open; two review-fix sync tests raised the warning count from 6 to 8.

**Impact:** 06-18 asserted the measured baseline rather than the documented one and stated the cause instead of correcting the older documents.
**Source:** 06-18-SUMMARY.md

---

### An interrupted executor left a complete, uncommitted deliverable
06-16's `aa_run.py` and all 13 tests were fully drafted; the recovery note's "6 tests is thin" was based on a partial view.

**Impact:** The session's work was verification plus a one-line `NameError` fix, not net-new implementation.
**Source:** 06-16-SUMMARY.md

---

### The structural evidence test rejected the pre-registered threshold formula as a smuggled floor value
`floor <= 0.5 x ... floor` matched the `=` branch of the no-floor-value regex.

**Impact:** A one-line negative-lookbehind fix; the threshold text itself was not touched, per the plan's prohibition against adjusting it.
**Source:** 06-17-SUMMARY.md

---

### The owner declined the A/A spend three times, and the fourth deferral moved it outside the milestone
Each decline came with a different state of readiness (preconditions open; defect just surfaced; everything closed).

**Impact:** Phase 6 closes `gaps_found` at 5/6 with one written, dated, reversible deferral; every promotion Phase 7 makes is provisional and unmeasured under RIG §PR.3.
**Source:** 06-06-SUMMARY.md, 06-13-SUMMARY.md, 06-17-SUMMARY.md, 06-GATE-AMENDMENT.md, 06-VERIFICATION.md

---

### A real 20-document build ran past the 600 s foreground limit and printed a library traceback that was not an error
40 LLM calls and 109,341 completion tokens; `pycozo` printed a `pandas` `ModuleNotFoundError` at every store construction.

**Impact:** The build was polled in the background by PID; the traceback was classified as caught-internally noise after both harnesses exited 0 with verified values.
**Source:** 06-15-SUMMARY.md

---
