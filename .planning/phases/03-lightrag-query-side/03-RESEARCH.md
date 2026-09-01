# Phase 3: LightRAG Query Side - Research

**Researched:** 2026-08-31
**Domain:** Decomposing a monolithic RAG query pipeline (LightRAG's `operate.py`) into machine-hosted primitive-part nodes over a frozen fitting contract, plus a parity-measurement harness against the pre-decomposition original
**Confidence:** MEDIUM-HIGH — the node set, wiring shape, and contract rules are already published and code-verified in `docs/system-model/`; the two genuinely new subsystems this phase must build (the LLM/embedding client primitive, the parity harness) have no existing `databasise/` code, so their internal shape is this research's own synthesis, not a re-statement of settled fact.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Provenance of this section:** the owner reviewed the four gray areas and directed
"no area needs covered, go with recommendations" (2026-08-31). Every decision below is Claude's,
made under the rationale stated with it. Any of them is open to owner reversal on sight — the
reversibility ratings say what each reversal costs.

**Index provenance — one index, two arms**

- **D-01:** v1's ingest builds the index once; both arms read that same content. The corpus is
  indexed end-to-end by stock v1 LightRAG (its own pinned environment, per D-04), producing its
  native Cozo graph, Faiss index + sidecar, and KV state. A one-time import step loads that
  on-disk state into the v2 namespace layout (Phase 1 D-07: one store directory per namespace),
  copying vectors verbatim — never recomputing them. Reversibility: costly — every parity number
  recorded under it is keyed to that one index.
- **D-02:** The import is verified, not assumed. Before any parity run is recorded: (a) chunk text
  is byte-identical between v1's KV and the v2 KV primitive, (b) the vector set hashes equal on
  both sides, (c) the graph node/edge count and ids match. A failing precondition makes the harness
  report `inconclusive`, never a plain pass/fail.
- **D-03:** `embedder-index` is authored but does not re-index the corpus in this phase. It is
  authored with a real body and registered, and validated by reproduction on a sample — run it over
  a sample of chunks and check its vectors against v1's stored vectors for that same text — rather
  than by re-embedding the corpus.

**The original arm — external, pinned, not imported**

- **D-04:** v1 runs in its own pinned environment (its own `uv` venv under `v1/`), invoked by the
  parity harness as a subprocess. It is never imported into `databasise/`. v1 has no venv today —
  standing one up is real Phase 3 work. Reversibility: reversible — the harness owns the invocation.
- **D-05:** The original arm does NOT run as an opaque node inside the machine in this phase.
  Admitting v1 as an opaque node is Phase 5's MODAL-02 work, and Phase 1 D-08 already refuses the
  `subprocess` placement by name. The parity harness — not the runner — pairs the two arms. Record
  explicitly that the two arms' traces are not symmetric: the decomposed arm produces a full RIG
  §TR.1 run record, the original arm is instrumented by the harness only.

**Model clients — machine primitives, one OpenAI-compatible shape**

- **D-06:** LLM, embedding, and rerank clients are machine-owned primitives injected into the node
  context — a `clients` mapping alongside the existing `stores` mapping on `NodeContext`, holding
  `llm`, `embedding`, `rerank` handles. Not part-internal. Forced by MACH-05's metering-at-declared-
  boundary rule. Reversibility: costly — every ported part's body signature assumes where the
  client comes from.
- **D-07:** One client shape: OpenAI-compatible chat-completions + embeddings. OpenRouter and
  Ollama both speak it, and v1 is configured through env vars that speak it too, so one pinned
  record hands the identical `base_url`/`model`/sampling parameters to both arms.
- **D-08:** Models, carried from Phase 2's banked decisions: generator and keyword LLM =
  `qwen/qwen3.7-flash` via OpenRouter, provider-pinned (Phase 2 D-07); embedder = local via Ollama
  (Phase 2 D-09). Identity is derived from the provider/model returned in the response, never the
  requested id.
- **D-09:** Rerank is off in the parity arm. The `rerank` node is authored and wired but configured
  as a declared pass-through. It still declares `calls_rerank`, per §19.9's fallback-reachability
  rule. Reversibility: reversible — turning it on is node config, but a parity number recorded with
  rerank off does not transfer to a run with it on.

**Parity gate — deterministic at the retrieval level, with `keywords` isolated**

- **D-10:** Criterion 6's deterministic retrieval-level gate is the phase gate. Criteria 4 and 5
  (MACH-02 eval bundle, MACH-03 A/A calibration, Falsifier 5) are deferred once more — to Phase 6's
  side-by-side run. With one shared index (D-01) and both arms pinned to one model identity
  (D-07/D-08), everything downstream of keyword extraction is a deterministic function of the query
  embedding and the store contents, making the retrieval-level comparison a sharper instrument than
  a weak substitute for an A/A floor. Reversibility: reversible.
- **D-11:** The deferral is recorded, never silent. Phase 3 ships a written record amending the
  ROADMAP's criteria 4 and 5, citing D-10's reason, naming the residual risk plainly: answer-level
  drift originating in `keywords` and `generate` stays unmeasured until a floor exists. REQUIREMENTS.md
  and ROADMAP.md still assign MACH-02/MACH-03 to Phase 3 — amend both during planning.
- **D-12:** Keyword extraction is pinned per query, then measured separately. Run `keywords` once
  per query, record its output, feed the same recorded keywords to both arms. The `keywords` node
  itself is compared on its own — N runs, variance band over its output.
- **D-13:** All five arms, staged over one base. Base wiring is `mix`, then the five arm patches as
  RFC 6902 (Phase 1 / spike 004: 7386 for additive, 6902 for subtraction).
- **D-14:** Corpus: a small fixed snapshot drawn from HotpotQA distractor, with a recorded hash.
  Reuses Phase 2 D-06's corpus family.

**Storage-ownership audit — machine-checked, not a prose table**

- **D-15:** Criterion 3's per-node audit ships as a machine-checked artifact emitted from the run
  record. For each of the seventeen nodes, record which store handle(s) it actually touched during
  the parity run and cross-check against that node's declared `effects[]`. A node touching a store
  it did not declare is a refusal, not a report line. Extend the existing import-boundary check to
  assert no part can reach any `v1.` module.

### Claude's Discretion

- Shape and file layout of the parity harness, and where the arm patches live on disk (§L.2's
  `Illustrative JSON:` field names `.planning/architectures/wirings/` — that directory does not
  exist; the wirings may reasonably live under `databasise/` instead, where Phase 2's already do).
- The import step's mechanism (direct file copy of the Faiss index vs. read-and-reinsert), provided
  D-02's byte-identity assertions hold.
- Internal structure of the seventeen part bodies, beyond the accepted→emitted kinds §L.2 fixes.
- Test structure and fixture layout, following `databasise/tests/` conventions.
- Form of the declared-deviation record under CONTRACT §5's parity-not-gain rule.

### Deferred Ideas (OUT OF SCOPE)

- MACH-02 / MACH-03 (eval bundle + A/A calibration, Falsifier 5) → Phase 6's side-by-side run, per
  D-10. Second deferral; Phase 2 D-01 was the first. REQUIREMENTS.md and ROADMAP.md still assign
  these to Phase 3 — amend during planning.
- Rerank as a live path → whenever a rerank provider is worth standing up; D-09 keeps the node and
  its declaration, so turning it on is node config plus a re-run.
- The original arm as an admitted opaque node → Phase 5 (MODAL-02), which is where opaque admission
  and the `subprocess` placement Phase 1 D-08 refuses both get earned.
- The `.planning/architectures/wirings/` illustrative JSON named by PARTS §L.2 → either write it
  where §L.2 says, or record that Phase 3's real wirings under `databasise/` supersede it.
- PARTS defects D1, D2, D7, D12 (write-effect asymmetry, store-instance-grained read declaration,
  mode-partitioned keyword cache, the priority axis with no home in §14.3) → contract-level defects,
  not port bugs; note any the port trips over, do not repair them here.
- HARD-01 / HARD-02 (gate-script vacuous passes, ANATOMY §F reconciliation) → later doc pass, Phase 7.
- The fact layer / DR-05 `validity` sub-capability → still open; Phase 4's frozen §18 envelope is
  its deadline, not a Phase 3 concern.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MODAL-01 | LightRAG query side re-cut into primitive-part nodes — seventeen of the eighteen §L.1 positions (the eighteenth, `embedder-index`, is the one index-recipe node the port authors) — with N-run, variance-banded parity against the pre-decomposition original inside the A/A band, or named declared deviations (CONTRACT §5's parity-not-gain rule) | PARTS.md §L.1/§L.2 publish the exact 18-node table, effects, `accepted→emitted` kinds, and the illustrative wiring JSON at `docs/system-model/wirings/`; `databasise/parts/schema.py`, `registry.py`, `runner/scheduler.py` are the concrete integration points confirmed by reading this session (see Architecture Patterns, Code Examples). `keywords` isolation (D-12) plus the deterministic retrieval-level comparison (D-10) is this phase's actual parity mechanism — Validation Architecture section below maps it to a concrete test plan. |
| MACH-02 | Eval bundle per RIG §EV.1 — **amended 2026-08-31 to Phase 6** per D-10/D-11; this phase's obligation is to ship the amendment record naming the deferral and the residual risk, not the bundle itself | RIG §EV.1–§EV.3 read and summarized below (bundle versioning, both target families, target-MDE derivation) so the amendment record can cite the exact clauses it defers, and so Phase 6 planning inherits a correct pointer. |
| MACH-03 | First A/A calibration per RIG §AA.1, Falsifier 5 — **amended 2026-08-31 to Phase 6** per D-10/D-11; this phase substitutes D-10's deterministic retrieval-level gate (criterion 6) as the interim rung-2 parity instrument | RIG §AA read (calibration procedure, cache-bypass precondition, batch-width correction) so the amendment record is grounded in the actual mechanism being deferred, not just a schedule note. |

**Both MACH-02 and MACH-03 require an explicit written amendment during planning** — a `03-GATE-AMENDMENT.md` or equivalent, following the `02-GATE-01-WAIVER.md` precedent (same directory, same structure: what was required, what is substituted, why, and the residual risk named in D-11's own words). This is not optional bookkeeping — REQUIREMENTS.md and ROADMAP.md currently assign both to Phase 3 by number, and a plan that silently defers them without a written record repeats exactly the failure mode GATE-01's own precedent exists to prevent.
</phase_requirements>

## Summary

Phase 3 is a **port against an already-published table**, not a fresh decomposition exercise. `docs/system-model/PARTS.md` §L.1 and §L.2 — verified by reading this session — already name all eighteen query-side positions, their component names, `§13.4` primitive-part types, `effects[]`, `accepted→emitted` socket kinds, and the five-arm family (`hybrid`, `local`, `global`, `naive`, `bypass`) staged over one `mix` base. `docs/system-model/wirings/lightrag-base.json` and its five RFC 6902 arm-patch siblings — also read and verified this session — already serialize that exact node set as illustrative-only JSON, giving the planner a checked, mechanically-validated starting skeleton rather than a blank page. The planner's job is therefore to turn eighteen already-named node positions into seventeen real registered `Part` bodies (`embedder-index` is the eighteenth, authored but not corpus-re-indexing) plus the machinery around them: a new LLM/embedding/rerank client primitive that does not exist anywhere in `databasise/` today, a one-time verified import of v1's on-disk index into the v2 namespace layout, a parity harness that runs both arms and reports a variance band rather than a single diff, and a machine-checked per-node storage-ownership audit.

Three concrete gaps were confirmed by reading the live code this session, none of them mentioned by name in CONTEXT.md, all three load-bearing for planning: (1) `NodeContext` (`databasise/parts/schema.py:84-95`) has exactly four fields — `node_id`, `config`, `inputs`, `stores` — confirming D-06's schema change is real, and the one call site that constructs it (`databasise/runner/scheduler.py:353`) is the exact integration point a `clients` parameter must be threaded through; (2) `CozoGraphStore` (`databasise/stores/graph.py`) exposes only single-item methods (`get_node`, `has_edge`, `node_degree`, ...) with no batch equivalents of v1's `get_nodes_batch`/`node_degrees_batch`, which `entity-hydrate-expand`/`relation-hydrate-expand` need, and Cozo's frozen bug #244 forbids `count()` aggregation, narrowing how a batch method could even be added; (3) PARTS.md's own cited line numbers into `v1/lightrag/operate.py` and `utils.py` do **not** match the current `v1/` checkout (verified by grep — see Common Pitfalls) — the semantic claims hold, the line numbers do not, and any node body written by jumping to a cited line rather than searching for the described logic will silently port the wrong code.

**Primary recommendation:** Build the seventeen part bodies directly against `docs/system-model/wirings/lightrag-base.json`'s already-serialized node/dep/config shape (do not re-derive it), wire a `clients` mapping onto `NodeContext` mirroring the existing `CapabilityScopedStores` deny-by-default pattern for symmetry with `stores`, use the official `openai` Python SDK (already a v1 dependency, same `base_url`-swap shape OpenRouter/Ollama both speak) for the new client primitive, and gate every part-body implementation task on re-locating its source logic in `v1/lightrag/operate.py` by grep/search rather than by the PARTS.md-cited line number.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Query-side retrieval logic (17 nodes: keyword extraction, entity/relation lookup+expand, chunk retrieval, joins, budgets, rerank, assemble, generate) | API / Backend (in-process machine node) | — | Every node's derived `execution_mode` (per `databasise/validator/execution_mode.py`, read this session) resolves to `in-process` for this node set — none declares `net`/`fs`/`self_storage`/`mutates_store`, none is `kind="fixpoint"` or `kind="opaque"` — so all seventeen run hosted directly inside the runner's own process, not as a separate service tier. |
| LLM/embedding/rerank client primitive | API / Backend (machine-owned primitive, injected via `NodeContext.clients`) | — | D-06: forced by MACH-05's metering-at-declared-boundary rule — a part-internal HTTP call has no boundary the meter can see. Lives beside `stores/` as a new `databasise/clients/` (or similar) package, not inside any one part. |
| Corpus index (Cozo graph + Faiss vector + KV) | Database / Storage | — | Already-built primitives (`databasise/stores/graph.py`, `vector.py`, `kv.py`) — Phase 3 only imports data into them (D-01/D-02), it does not change their shape. |
| v1 original arm (comparison baseline) | External Process (subprocess, harness-invoked only) | — | D-04/D-05: never imported, never admitted as an opaque machine node this phase — invoked as a pinned-venv subprocess purely by the parity harness, outside the machine's own `execution_mode` vocabulary. |
| Parity harness (variance band, storage-ownership audit, declared-deviation record) | API / Backend (new, harness-side tooling, not a wiring node) | — | Precedented by `v1/tests/parity/run_substrate_parity.py` (571 lines, read this session) and `databasise/evidence/falsifier2.py`'s "evidence ships as committed, re-runnable files" house style — a script/module under `databasise/evidence/` or a new `databasise/parity/`, not a node in any wiring. |
| Embedder-index (index-recipe node) | Database / Storage (writes `quarantined` artifact scope) | — | §L.2: its effective depth is `opaque` (tainted by the undecomposed ingest core), so its output MUST go to `quarantined`, never `shared` — confirmed against `databasise/parts/schema.py`'s `ArtifactScope` enum. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `openai` | `>=2.0.0,<3.0.0` [ASSUMED — package name/version drawn from v1's own pinned range at `v1/pyproject.toml:68`, read this session; not independently re-verified against PyPI's current latest] | LLM chat-completions + embeddings client, `base_url`-overridable for OpenRouter/Ollama (D-07) | v1 already depends on and configures this exact package this way (`v1/env.example:534-701`, read this session: `LLM_BINDING=openai` with `LLM_BINDING_HOST=https://openrouter.ai/api/v1` for OpenRouter, `LLM_BINDING_HOST=http://localhost:11434` for Ollama) — reusing it keeps D-07's "one pinned record, both arms" claim true at the library level, not just the config level |
| `jsonpatch` | latest [ASSUMED — not currently a dependency of either `databasise/pyproject.toml` or `v1/pyproject.toml`, confirmed by grep this session] | Apply the five RFC 6902 arm patches to the `mix` base wiring at harness/load time (D-13) | RFC 6902 has non-trivial edge cases (JSON-Pointer `~0`/`~1` escaping, array-index semantics, `test` op, `remove` erroring on a missing target) that CONTRACT.md:184 relies on for its fail-closed subtraction guarantee — hand-rolling this is exactly a "Don't Hand-Roll" case (see below); `jsonpatch` (`python-json-patch`, `github.com/stefankoegl/python-json-patch`) is the de-facto standard Python implementation |
| `pydantic` | `>=2.0,<3.0` (already pinned) | `NodeContext`/`Part`/`WiringNode` schema, extend for `clients` field | Already the project's schema library (Phase 1); no new choice needed |
| `pycozo[embedded]` | `==0.7.6` (already pinned, exact) | Graph store the entity/relation nodes read | Frozen per Phase 1 D-05 — do not touch the pin |
| `faiss-cpu` | `>=1.7.0,<2.0.0` (already pinned) | Vector store the chunk/entity/relation lookup nodes query | Already the Phase 3 parity baseline per `databasise/stores/vector.py`'s own docstring |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `statistics` (stdlib) | — | N-run variance band over `keywords`' output (D-12) and the retrieval-level comparison's structural diff counts | Use for `mean`/`pstdev` over a small (single-digit-to-low-double-digit) N of harness runs — this phase does NOT need a bootstrap-resampled p95 floor (that is Phase 6's MACH-03 scope, per D-10); reaching for `numpy`/`scipy` here would be over-tooling for a plain mean/spread over ≤~20 samples |
| `hashlib` (stdlib) | — | D-02's byte-identity assertions (chunk text hash, vector-set hash) and D-14's corpus-snapshot hash | Already the pattern `databasise/namespaces.py`/`stores/vector.py` use (SHA-256 checksums) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `openai` SDK | Raw `httpx`/`aiohttp` JSON calls to the OpenAI-compatible endpoint | Hand-rolling loses request/response typing, retry/backoff, and streaming helpers the SDK already provides for zero cost given `openai` is already vendored in this monorepo (`v1/pyproject.toml`); only worth it if the SDK's dependency footprint becomes a real problem, which nothing in this phase indicates |
| `jsonpatch` | Hand-written patch applier (6 ops: add/remove/replace/move/copy/test) | Only 6 ops sounds small, but JSON-Pointer path resolution (escaping, array-vs-object dispatch, out-of-range indices, the `-` end-of-array token) is exactly the kind of "looks like 20 lines, is actually 200 lines of edge cases" the ponytail ladder warns about; CONTRACT.md:184 depends on `remove` actually erroring on a missing target — get that wrong and D-13's whole "fail-closed subtraction" claim silently stops holding |
| CozoGraphStore batch methods (new) | Loop N single-item `get_node`/`node_degree` calls from inside the node body | Looping avoids writing and frozen-bug-testing a new aggregation-shaped Cozo query (real risk per Pitfall 6 / bug #244's "aggregation returning zero rows silently"); costs N round-trips per node instead of 1, but this phase's corpus is deliberately small (D-14) so the latency cost is likely acceptable — see Open Questions |

**Installation:**
```bash
cd databasise
uv add "openai>=2.0.0,<3.0.0" jsonpatch
```

**Version verification:** `openai`'s exact current PyPI version was not independently re-verified against the registry this session beyond the package-legitimacy seam's existence check (see Package Legitimacy Audit) — the version range above is copied from v1's own pin, not freshly queried. Before locking the version in a plan, run `uv add --dry-run "openai"` (or equivalent) against the live registry to confirm current best-practice range.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `openai` | PyPI | Latest release 2026-08-28 (frequent-release cadence — this is a routine version bump, not a new package; already vendored at `v1/pyproject.toml:68,126`) | Unknown to the legitimacy tool (`weeklyDownloads: null`) | `github.com/openai/openai-python` (official) | SUS (`too-new`, `unknown-downloads`) | **Flagged — planner must add `checkpoint:human-verify` before the install task**, but the SUS signal is a heuristic false-positive here: the repo is the official `openai` GitHub org, the package is already a dependency of this same monorepo's `v1/`, and "too-new" reflects release cadence, not package novelty. Still gated per protocol since the verdict came back non-`OK`. |
| `jsonpatch` | PyPI | Published 2023-06-16 per registry metadata (the underlying `python-json-patch` project has existed since ~2011; this date is likely the last-release timestamp, not project age) | Unknown to the legitimacy tool | `github.com/stefankoegl/python-json-patch` | SUS (`unknown-downloads`) | **Flagged — planner must add `checkpoint:human-verify` before the install task.** No red flags beyond the tool's inability to read download counts; this is the standard, long-established Python RFC 6902 implementation. |

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** `openai`, `jsonpatch` — both flagged solely on the legitimacy tool's `unknown-downloads`/`too-new` heuristics, not on any structural red flag (no missing repo, no postinstall script, no name-squatting pattern); both package names are `[ASSUMED]` per the provenance rule (discovered via training knowledge / existing monorepo usage, not independently confirmed against an authoritative source this session) — the planner must gate each install behind a `checkpoint:human-verify` task per protocol regardless of this research's own assessment that the flags are false positives.

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────────────────────┐
                         │  Parity Harness (new, Phase 3)            │
                         │  databasise/parity/ or evidence/          │
                         └───────────────┬───────────────┬───────────┘
                                         │               │
                     ┌───────────────────┘               └───────────────────┐
                     ▼                                                       ▼
        ┌────────────────────────────┐                      ┌─────────────────────────────┐
        │  Decomposed arm             │                      │  Original arm (v1, D-04/D-05) │
        │  databasise.run_wiring()    │                      │  subprocess, pinned venv       │
        │                             │                      │  v1/lightrag (never imported)  │
        │  1. Load mix base JSON      │                      │                                 │
        │  2. jsonpatch.apply(arm)    │                      │  Harness-instrumented only —    │
        │  3. parse_wiring()          │                      │  no RIG §TR.1 run record         │
        │  4. run_wiring(..., clients)│                      └───────────────┬─────────────────┘
        └──────────────┬──────────────┘                                      │
                        │  17 nodes, in-process (execution_mode derived)      │
                        ▼                                                    │
        ┌───────────────────────────────────────────────┐                    │
        │ keywords → embedder-query → {entity,relation}- │                    │
        │ lookup → hydrate-expand → join → budget →       │                    │
        │ chunk-sel-kg / chunk-vector → join-chunks →      │                    │
        │ heading-backfill → rerank(off) → assemble →      │                    │
        │ generate                                         │                    │
        │                                                   │                    │
        │ each node: NodeContext(stores=..., clients=...)  │                    │
        │   stores → Cozo/Faiss/KV (imported once, D-01)   │                    │
        │   clients → LLM/embedding (OpenAI-compat, D-07)  │                    │
        └───────────────────────┬───────────────────────┘                    │
                                 │  RIG §TR.1 run record (17 NodeTrace rows)  │
                                 ▼                                            ▼
                    ┌────────────────────────────────────────────────────────┐
                    │  Comparison: retrieved chunk sets + rankings (D-10)      │
                    │  keywords' own N-run variance band (D-12)                │
                    │  per-node storage-ownership audit (D-15)                 │
                    │  → declared-deviation record or PASS                     │
                    └────────────────────────────────────────────────────────┘
```

A reader tracing "one query in, one comparison verdict out": the harness fans the same query into both arms; the decomposed arm resolves a wiring (base JSON + RFC 6902 patch), runs it in-process through the existing scheduler with a new `clients` mapping alongside `stores`, and the original arm runs as an external subprocess the harness itself instruments (never a machine node). Both sides' retrieved-chunk output converges at the harness's comparison step, which is deterministic and zero-token per D-10 — no LLM judge call happens on this critical path.

### Recommended Project Structure

```
databasise/
├── clients/                       # NEW — D-06's machine-owned LLM/embedding/rerank primitives
│   ├── __init__.py                #   CapabilityScopedClients (mirrors CapabilityScopedStores)
│   ├── base.py                    #   LLMClient/EmbeddingClient/RerankClient protocols
│   └── openai_compat.py           #   the one OpenAI-compatible implementation (D-07)
├── parts_core/
│   └── lightrag/                  # NEW — the 17 ported part bodies + embedder-index (18th)
│       ├── keywords.py
│       ├── embedder_query.py
│       ├── entity_lookup.py
│       ├── entity_hydrate_expand.py
│       ├── relation_lookup.py
│       ├── relation_hydrate_expand.py
│       ├── chunk_vector.py
│       ├── join_entities.py       # may share one join_roundrobin.py module (recurs 3x per §L.1)
│       ├── join_relations.py
│       ├── join_chunks.py
│       ├── budget_entities.py     # may share one truncator_token_budget.py module (recurs 2x)
│       ├── budget_relations.py
│       ├── chunk_sel_kg.py
│       ├── heading_backfill.py
│       ├── rerank.py              # pass-through per D-09
│       ├── assemble.py
│       ├── generate.py
│       └── embedder_index.py      # the 18th, index-recipe node (D-03)
├── evidence/wirings/ or a new
│   databasise/wirings/lightrag/   # base + 5 RFC 6902 arm patches — mirrors docs/system-model/
│                                   #   wirings/*.json shape exactly (Claude's Discretion: file
│                                   #   location; content should NOT re-derive the node set)
├── parity/                        # NEW — the parity harness (Claude's Discretion: name/location)
│   ├── import_index.py            #   D-01/D-02's verified one-time import
│   ├── run_comparison.py          #   drives both arms, D-10's retrieval-level diff
│   └── storage_audit.py           #   D-15's machine-checked per-node audit
└── tests/
    ├── clients/                   # NEW
    ├── parts_core/lightrag/       # NEW
    └── parity/                    # NEW
```

### Structure Rationale

- `clients/` sits beside `stores/` deliberately — same tier, same "machine-owned primitive injected via `NodeContext`" shape, so a reader scanning top-level packages sees the two primitive families side by side.
- `parts_core/lightrag/` (not `parts_core/` flat) follows the `lightrag/`-namespace demotion PARTS §L.1 already records for every component name — the directory layout should read the same story the component names already tell.
- The wiring JSON location is explicitly left to Claude's Discretion per CONTEXT.md; whichever is chosen, its **content** must be a byte-for-byte match (modulo the `illustrative-only` status fields, which a registered wiring drops) to `docs/system-model/wirings/lightrag-*.json` — those files were already checked mechanically (D-06's kill condition: "applying each of the five arm patches to the base... reproduces exactly the node id sets... confirmed by script, not asserted") and re-deriving the node set independently risks silently diverging from a verdict already run.

### Pattern 1: Deny-by-default capability scoping, extended from stores to clients

**What:** `databasise/parts_core/__init__.py`'s `CapabilityScopedStores` (read this session) wraps a run's raw `stores` dict and raises `UndeclaredEffectError` unless the calling part's own declared `effects[]` names the matching effect. `databasise/runner/scheduler.py:213-236`'s `_ScopedStoresView` then adapts that into the plain-dict-subscript shape (`ctx.stores["kv"]`) every existing part body already uses.

**When to use:** D-06 adds a `clients` mapping to `NodeContext` "alongside the existing `stores` mapping" — the existing code's own CR-01 rationale ("an under-declaring wiring must not be able to meter a real LLM/rerank/embedding spend as zero") applies identically to a client call as to a store call. Recommend a `CapabilityScopedClients` class with the same shape, keyed on `calls_llm`/`calls_embedding`/`calls_rerank` rather than `reads_*`/`writes_*`.

**Example:**
```python
# Source: databasise/parts_core/__init__.py:51-71 (read this session) — the existing pattern to mirror
class CapabilityScopedStores:
    def __init__(self, raw_stores: dict[str, Any], declared_effects: list[Effect]):
        self._raw_stores = raw_stores
        self._declared_effects = list(declared_effects)

    def require(self, effect: Effect) -> Any:
        if effect not in self._declared_effects:
            raise UndeclaredEffectError(effect, self._declared_effects)
        store_key = effect.split("_", 1)[-1]  # "reads_kv" -> "kv"
        try:
            return self._raw_stores[store_key]
        except KeyError:
            raise StoreNotWiredError(effect, store_key) from None

# Recommended mirror for clients (not yet built):
# CLIENT_EFFECT_TO_KEY = {"calls_llm": "llm", "calls_embedding": "embedding", "calls_rerank": "rerank"}
# class CapabilityScopedClients:
#     def require(self, effect: Effect) -> Any:
#         if effect not in self._declared_effects: raise UndeclaredEffectError(...)
#         return self._raw_clients[CLIENT_EFFECT_TO_KEY[effect]]
```

### Pattern 2: Part-body return shape for metered nodes

**What:** `databasise/parts_core/fake_llm_caller.py` (read this session) is the one existing precedent for a part body that (a) declares `calls_llm`, (b) reads/writes a cache-partition key against `ctx.stores["kv"]`, and (c) returns `{"tokens": TokenAccounting(...), "cache_hit": bool, ...}` — the exact shape `runner/scheduler.py`'s `_body_report()` (line 309-326) reads to drive `meter()`.

**When to use:** Every one of `keywords`, `embedder-query`, `rerank`, `generate`, `embedder-index` (the five nodes declaring `calls_llm`/`calls_embedding`/`calls_rerank`) MUST return this shape or their real token spend silently meters as zero — `runner/budget.py`'s `meter()` (read this session) only accrues spend when the node's own declared `effects` intersects `{calls_llm, calls_rerank, calls_embedding}` AND the returned `TokenAccounting` is populated.

**Example:**
```python
# Source: databasise/parts_core/fake_llm_caller.py (read this session)
async def _fake_llm_caller_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    prompt = str(config.get("prompt", ""))
    cache_store = ctx.stores["kv"]
    partition_key = _prompt_cache_key(prompt)
    cached = await cache_store.get_by_id(partition_key)
    cache_hit = cached is not None
    # ... populate TokenAccounting from the real client response, not canned ...
    return {"node_id": ctx.node_id, "cache_hit": cache_hit, "tokens": TokenAccounting(...)}
```

### Pattern 3: RFC 6902 arm resolution before `parse_wiring`

**What:** `databasise/validator/parse.py:141`'s `parse_wiring(doc: dict, registry: PartRegistry) -> ParsedWiring` (read this session) takes a plain, already-resolved wiring `dict` — it has no concept of "base + patch." The five arms must be materialized (`jsonpatch.apply_patch(base_dict, patch["operations"])`) into a flat dict **before** it reaches `parse_wiring`.

**When to use:** Every arm run in the parity harness and every arm run by the parity harness's storage-ownership audit.

**Example:**
```python
# Illustrative shape, not yet built — combining docs/system-model/wirings/*.json (read this
# session) with the jsonpatch library and the existing parse_wiring/run_wiring call sequence
import json
import jsonpatch

base = json.loads(Path("lightrag-base.json").read_text())
patch = json.loads(Path("lightrag-arm-hybrid.json-patch.json").read_text())
resolved = jsonpatch.apply_patch(base, patch["operations"])
# Base MUST also be independently re-validated with no arm applied (CONTRACT.md:184) —
# run parse_wiring(base, registry) too, not only the patched result.
parsed = parse_wiring(resolved, registry)
result = await run_wiring(parsed, registry, stores={"kv": ..., "vector": ..., "graph": ...},
                           determinism_setting="pinned", concurrency_setting="sequential")
```

### Anti-Patterns to Avoid

- **Re-deriving the node boundary during planning:** PARTS §L.1/§L.2's eighteen positions and their `effects[]`/kinds are settled and code-verified (§L.3's "conformance-re-checked" verdict, the D-06 kill-condition script run). A plan that re-argues where a node boundary sits (e.g., "should `entity-lookup` and `entity-hydrate-expand` really be one node?") is re-litigating a decision CONTEXT.md's canonical refs explicitly close: "Re-deriving the cut is not in scope."
- **Trusting PARTS.md's cited `v1/lightrag/operate.py`/`utils.py` line numbers verbatim:** confirmed stale this session (see Common Pitfalls) — locate the actual logic by `grep`/search for the named function or field, never by jumping straight to the cited line range.
- **Building a new Cozo `count()`-aggregation query for batch entity/relation degree lookups:** bug #244 (`databasise/tests/stores/test_graph_frozen_bugs.py`, read this session) is exactly this failure mode — "aggregation returning zero rows silently." If a batch method is added to `CozoGraphStore`, it must be checked against this suite before any node body depends on it.
- **Giving the parity harness's original (v1) arm a real RIG §TR.1 run record:** D-05 explicitly states the two arms' traces are asymmetric — the original arm is harness-instrumented only. Fabricating a symmetric-looking trace for it would misrepresent what was actually measured.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RFC 6902 patch application (D-13's arm mechanism) | A custom JSON-Pointer walker/patcher | `jsonpatch` (PyPI) | Path-escaping (`~0`/`~1`), array-index semantics, and `remove`-errors-on-missing-target are exactly the edge cases CONTRACT.md:184 relies on for fail-closed subtraction; a hand-rolled version that gets even one of these wrong silently breaks the "arm mechanism guarantees a base type error can't be masked" claim |
| OpenAI-compatible chat/embeddings HTTP calls (D-06/D-07) | Raw `httpx`/`aiohttp` request building, response parsing, retry/backoff | `openai` Python SDK, `base_url` override | Already vendored in this same monorepo (`v1/pyproject.toml`) for the exact same OpenAI-compatible shape OpenRouter/Ollama both speak; zero marginal dependency risk given it is already an install this project trusts |
| N-run variance-band statistics for `keywords`' output (D-12) and the retrieval-level diff | A custom mean/stdev/confidence-interval implementation | stdlib `statistics` module | The phase's own statistical need is a plain mean and spread over a small N — reaching for `numpy`/`scipy` (not currently a `databasise/` dependency at all) for this is over-tooling; save the heavier statistics for Phase 6's actual bootstrap-resampled A/A floor, which is explicitly out of this phase's scope (D-10) |
| Byte-identity / hash verification for the index import (D-02) | A custom hashing scheme | stdlib `hashlib.sha256`, matching `databasise/stores/vector.py`'s and `namespaces.py`'s existing SHA-256 checksum pattern | Consistency with the codebase's own established provenance-hashing convention, not a new one |

**Key insight:** every "don't hand-roll" item above already has either an established library the rest of this very monorepo depends on (`openai`) or a well-known small-but-jagged spec (RFC 6902) where the failure mode is a silent correctness bug, not a crash — exactly the domain where reuse beats a from-scratch implementation regardless of how small the from-scratch version looks on paper.

## Common Pitfalls

### Pitfall 1: Storage decomposition looks done while every node still reaches a shared singleton

**What goes wrong:** A phase report states "17 of 18 positions decomposed" while every node still reaches into `v1`'s `shared_storage.py` singleton (`_manager`, `_storage_instance`, `_global_concurrency_limits`) at runtime, because node boundaries describe data flow, not who owns the storage handle.

**Why it happens:** Storage state is invisible in a call graph; clean primitive-part boundaries on paper coexist easily with shared mutable state underneath, especially when porting logic quickly from an existing monolith.

**How to avoid:** D-15 already makes this a machine-checked artifact, not a prose table — for each of the seventeen nodes, cross-check which store handle(s) it actually touched during a run against its declared `effects[]`, and extend `databasise/tools/check_import_boundary.py`'s existing scan (already walks the whole `databasise/` tree by AST, confirmed by reading it this session — no code change needed there, just a new test exercising the ported files) to assert no part reaches any `v1.` module.

**Warning signs:** A node's tests pass in isolation but fail when run alongside a sibling node in the same process; any new code under `parts_core/lightrag/` importing from `v1` at all (would be caught immediately by the existing AST-walking checker).

### Pitfall 2: A single parity run is reported as "PASS," hiding real LLM-output variance

**What goes wrong:** Temperature=0 does not mean determinism — provider-side batching and floating-point non-associativity mean identical prompts can still produce different completions/embeddings run to run. A one-shot parity check that happens to agree gets treated as proof of equivalence.

**Why it happens:** The mechanism to run N times and report a variance band costs more to build than a single-run diff, so it is easy to skip under deadline pressure.

**How to avoid:** D-10/D-12 already design around this specifically for this phase's narrower scope: pin `keywords`' output per query (making everything downstream deterministic) and measure `keywords` itself over N runs as its own variance band, rather than trying to build a full bootstrap floor this phase explicitly defers (MACH-03). The retrieval-level comparison itself (chunk sets, rankings) is then a deterministic, zero-token diff — no variance band needed for that half at all, because nothing downstream of the pinned keywords is stochastic under D-01/D-07/D-08's shared-index, shared-model-identity design.

**Warning signs:** A parity report with no run-count field; `keywords`' own N-run band showing high variance while the harness still reports a flat "PASS/FAIL" for the retrieval-level comparison without flagging that `keywords`' instability could shift which downstream retrieval path executes (the `local`/`global` fall-through guards, per PARTS §L.3).

### Pitfall 3: Embedding-generation mismatch between the two paths silently invalidates parity

**What goes wrong:** Any difference in chunking, preprocessing, or embedding between the original and decomposed paths makes a parity diff report "the decomposition changed behavior" when it actually only measured embedding drift.

**Why it happens:** Chunking/preprocessing code is exactly the kind of logic that moves during decomposition, and subtle differences (text normalization order, truncation boundaries) are easy to introduce without noticing.

**How to avoid:** D-01/D-02 already close this by construction for this phase — index once, import verbatim, assert byte-identity before any parity run is recorded, and treat a failed precondition as `inconclusive` rather than pass/fail. This is the single most load-bearing decision in CONTEXT.md for this pitfall; the planner's job is to make D-02's three assertions (chunk-text byte-identity, vector-set hash equality, graph node/edge count+id match) real, automated, pre-flight checks the harness runs before recording any comparison, not a manual one-time sanity check.

**Warning signs:** Diffs correlating with chunk-boundary or truncation code paths rather than with the actual node logic under test; the import step's byte-identity assertions not being wired as an automated pre-flight gate.

### Pitfall 4: Cozo's frozen 0.7.6 correctness bugs get silently re-triggered

**What goes wrong:** A new query shape written for the ported graph-reading nodes (`entity-hydrate-expand`, `relation-hydrate-expand`, `chunk-sel-kg`) reintroduces one of Cozo's four documented, permanently-unfixed correctness bugs — most relevantly here, bug #244 ("aggregation returning zero rows silently"), since any batch degree/neighbor query is aggregation-shaped.

**Why it happens:** `CozoGraphStore` (confirmed by reading `databasise/stores/graph.py` this session) exposes only single-item methods (`get_node`, `has_edge`, `node_degree`, `get_all_labels`) — no batch equivalent of v1's `get_nodes_batch`/`node_degrees_batch` exists yet. Whoever writes the port is likely to need one and may write a new aggregation query to get it efficiently, which is exactly the risk pattern.

**How to avoid:** `databasise/tests/stores/test_graph_frozen_bugs.py` (171 lines, read this session; explicitly "no test in this module may carry a pytest skip or xfail marker") is the existing, non-negotiable regression gate. Any new `CozoGraphStore` method must run against it before a node body depends on it. The simpler, lower-risk alternative — loop N single-item calls from inside the node body instead of adding a batch method — avoids writing a new query shape entirely at the cost of N round-trips; given D-14's deliberately small corpus, this may be the better default (see Open Questions).

**Warning signs:** A new graph-store method under review with no corresponding addition to `test_graph_frozen_bugs.py`; any use of `count()` in a newly-written CozoScript query.

### Pitfall 5: PARTS.md's cited `v1/` line numbers do not match the current checkout

**What goes wrong:** A plan or an executor jumps to a line number PARTS.md/CONTEXT.md cites (e.g., `operate.py:4975-5018` for the query-embedder precompute boundary, `utils.py:5940-5955` for `min_rerank_score`) and either finds unrelated code or, worse, finds code that happens to compile and looks plausible, silently porting the wrong logic.

**Why it happens:** Confirmed directly this session: `v1/lightrag/utils.py` currently has 5,033 total lines — `utils.py:5940-5955` is entirely past end-of-file. `grep -n "min_rerank_score"` instead finds it at `utils.py:4375-4393`. Similarly, `query_embedding`'s actual precompute/fallback logic is spread across `operate.py:4262-5424` in several places, not cleanly bounded at `4975-5018` as cited. `v1/lightrag/operate.py`'s total line count (5,995) DOES match PARTS.md's own citation ("5,995 lines"), so the file as a whole is the right one — only the fine-grained internal line numbers have drifted, most likely because the docs were pinned against a specific commit (RIG §CM's own text names `b93f7c31f10880bcaccc9518c6a7582fbbe94f1b`) that differs from whatever is checked out in `v1/` today.

**How to avoid:** Treat every PARTS.md/CONTEXT.md line-number citation into `v1/` as a **pointer to search from**, not a location to trust. Before writing any part body, `grep` for the named function, field, or constant (e.g., `chunk_tracking`, `min_rerank_score`, `query_embedding`) and confirm the surrounding logic matches the cited description, rather than reading the cited line range cold.

**Warning signs:** A part body's docstring citing a `v1/` line range that was never independently re-confirmed by search this session; any `sed -n 'START,ENDp'` against `v1/` returning empty or clearly-unrelated content during implementation.

## Code Examples

### The published node table as a concrete wiring skeleton

```json
// Source: docs/system-model/wirings/lightrag-base.json (read this session, verified against
// PARTS.md §L.1/§L.2's own node table) — the mix base wiring, all 18 positions
{
  "wiring_version": "1",
  "nodes": {
    "keywords": { "component": "lightrag/keyword-extractor", "kind": "rewriter",
                  "effects": ["calls_llm"], "deps": [] },
    "embedder-query": { "component": "lightrag/embedder-query", "kind": "embedder",
                         "effects": ["calls_embedding"], "deps": ["keywords"] },
    "entity-lookup": { "component": "lightrag/entity-lookup", "kind": "retriever",
                        "effects": ["reads_vector"], "deps": ["embedder-query"] }
    /* ... 15 more nodes, full base at docs/system-model/wirings/lightrag-base.json ... */
  },
  "recipe": { "embedding": "embedder-index" },
  "harnesses": [],
  "provides": ["generate"]
}
```

### Part registration pattern to replace the declaration-only stub

```python
# Source: databasise/parts/registry.py (read this session) — DeclarationOnlyPartError fires today
# for lightrag/query-side@0.1.0; Phase 3 replaces the stub with 17 real Part registrations.
# Illustrative shape combining databasise/parts/schema.py's Part dataclass with §L.1's table:
from databasise.parts.schema import Part

KEYWORDS_PART = Part(
    name_at_version="lightrag/keyword-extractor@0.1.0",  # no @version suffix minted until
                                                            # promotion (§0) — confirm exact
                                                            # naming convention against §0 during
                                                            # planning, not assumed here
    kind="rewriter",
    structural_depth="stage",   # computed by the validator per node in practice; stated here as
                                  # the expected value for a pure query-time transform
    effects=["calls_llm"],
    upstream_ref="v1/lightrag/operate.py",  # exact function located by search, not by stale line no.
    body=_keywords_body,        # new, to be written — reads ctx.clients["llm"] (D-06)
)
```

### The declaration-only stub this phase retires

```python
# Source: databasise/parts_core/declared_only.py:17-25 (read this session)
LIGHTRAG_QUERY_SIDE_PART = Part(
    name_at_version="lightrag/query-side@0.1.0",
    kind="subgraph",  # stands in for a decomposed multi-node wiring, not yet ported (Phase 3)
    structural_depth="stage",
    effects=["reads_kv", "reads_vector", "reads_graph", "calls_llm", "calls_embedding"],
    upstream_ref="v1/lightrag/operate.py",
    body=None,
    artifact_scope=None,
)
# Phase 3 retires this single stub, replacing it with 17 real registered parts plus embedder-index
# (18 total) — databasise/evidence/wirings/w1-lightrag-query-side.json's own fake-part wiring
# must keep computing the same Falsifier 2 verdicts afterward, or the change is a regression to
# explain, per CONTEXT.md's own "Integration Points" note.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Monolithic `operate.py` 4-stage pipeline (keyword extraction → KG search → token control → context merging), one process, direct store singleton access | Eighteen fitted primitive-part nodes over machine-owned store/client primitives, each independently metered and traced | This phase (§BP rung 2) | Every node's storage access becomes machine-checkable (D-15) instead of trust-based; parity must be measured, not asserted (§5) |
| `min_rerank_score` and `chunk_top_k`/token-truncation as separate standalone nodes (an earlier decomposition's own working draft) | Both reversed and absorbed into `rerank`'s guarded scope and `assemble` respectively, per §19.4(a)'s "a numeric threshold/cap is config, not a knob" rule | Settled at PARTS §L.1's "three re-derived cuts," confirmed 3/3 by blind review before this phase started | Fewer nodes than an earlier draft implied — the planner should NOT resurrect these as separate nodes |

**Deprecated/outdated:** `nano-vectordb` is explicitly not part of this stack (`databasise/stores/vector.py`'s own docstring, Phase 1 D-05) — Faiss is the sole vector primitive with no fallback pairing; do not reach for `nano-vectordb` compatibility code when porting any vector-reading node.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `openai` Python SDK version range `>=2.0.0,<3.0.0` is appropriate for `databasise/pyproject.toml` | Standard Stack | Low — copied from v1's own working pin in the same monorepo; worst case is a version-range tweak during the install task |
| A2 | `jsonpatch` (PyPI, `python-json-patch`) is the correct/standard library for RFC 6902 application in Python | Standard Stack, Don't Hand-Roll | Low-medium — this is standard training knowledge, not independently confirmed via Context7/official docs this session; if wrong, the fallback (hand-rolled patch application) is strictly worse per the Don't Hand-Roll rationale, not a blocker |
| A3 | Looping single-item `CozoGraphStore` calls (rather than adding a new batch method) is an acceptable performance tradeoff for this phase's deliberately small corpus (D-14) | Architecture Patterns, Open Questions | Medium — if the corpus or query volume is larger than expected, N round-trips per hydrate-expand node could dominate wall-clock; not measured this session, flagged as an Open Question for the planner to size against the actual D-14 corpus |
| A4 | A `CapabilityScopedClients` class mirroring `CapabilityScopedStores` is the right shape for `NodeContext.clients`' deny-by-default enforcement | Architecture Patterns Pattern 1 | Low-medium — this is a design recommendation extrapolated from the existing store-scoping pattern for consistency, not a decision CONTEXT.md itself states; a planner could reasonably choose a lighter-weight enforcement mechanism instead, provided it still closes the CR-01-class gap (an under-declaring wiring metering a real spend as zero) |
| A5 | Part naming convention (`lightrag/keyword-extractor@0.1.0` style, matching the existing three declaration-only stubs' `@0.1.0` pattern) applies to the 17 new parts | Code Examples | Low — §0 states a semver is minted only at promotion, and none of these components has been promoted; the exact pre-promotion naming convention (whether `@0.1.0` is even correct, vs. some other unversioned marker) should be confirmed against CONTRACT §0 directly during planning, not assumed from this research's example alone |

**If this table is empty:** N/A — five assumptions recorded above, all flagged for confirmation before being treated as locked.

## Open Questions

1. **Does the corpus/query volume in D-14's HotpotQA-distractor snapshot make looping single-item Cozo calls (vs. a new batch method) an acceptable performance tradeoff for `entity-hydrate-expand`/`relation-hydrate-expand`?**
   - What we know: `CozoGraphStore` has no batch methods today; a new batch method risks bug #244's aggregation failure mode; D-14's corpus is "sized to what makes one v1 index affordable," implying it is deliberately small.
   - What's unclear: the actual node/edge counts of the chosen snapshot, and therefore whether N-round-trip looping is fast enough not to matter for this phase's purposes.
   - Recommendation: default to looping (lower risk, per Don't Hand-Roll), measure wall-clock during Wave 0/1 implementation, and only invest in a frozen-bug-tested batch method if looping proves to be the dominant cost.

2. **What exact enforcement shape does `NodeContext.clients` need — a full `CapabilityScopedClients` mirror of `CapabilityScopedStores`, or something lighter?**
   - What we know: D-06 states the schema addition (`clients` mapping alongside `stores`); the existing `stores` pattern uses deny-by-default scoping keyed on declared effects, motivated by the same CR-01 "under-declaring wiring must not meter zero" concern that applies identically to clients.
   - What's unclear: CONTEXT.md does not explicitly require client scoping to mirror store scoping — this is this research's own extrapolation for consistency, not a locked decision.
   - Recommendation: build the mirror (Pattern 1 above) unless the planner identifies a specific reason the store precedent doesn't transfer; the marginal cost of doing so is small and the consistency payoff (one deny-by-default story instead of two) is real.

3. **Exact pre-promotion part-naming convention for the 17+1 new components** — see Assumption A5. Confirm against CONTRACT §0 directly during planning rather than copying the existing three stubs' `@0.1.0` pattern by inference.

4. **Where does the parity harness's declared-deviation record (CONTRACT §5's parity-not-gain rule) live, and what does it look like?** CONTEXT.md leaves this to Claude's Discretion explicitly. `databasise/evidence/FALSIFIER-2-EVIDENCE.md` is the nearest existing precedent (a committed, human-readable evidence document alongside runnable code) — recommend following that shape rather than inventing a new one.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `v1/` Python virtualenv | D-04's pinned original-arm subprocess | ✗ | — | None — this is named Phase 3 work in CONTEXT.md itself ("v1 has no venv today — standing one up is real Phase 3 work"), not a gap to route around |
| OpenRouter API reachability (`qwen/qwen3.7-flash`, D-08) | Both arms' generator/keyword LLM | Not verified this session (network-dependent, credential-dependent) | — | None stated in CONTEXT.md; this is carried forward as a banked Phase 2 decision, assumed reachable |
| Local Ollama instance (embedder, D-08) | Both arms' query embedding | Not verified this session (requires a running local service) | — | None stated; carried forward as a banked Phase 2 decision |
| `openai` PyPI package | New client primitive (D-06/D-07) | Not yet installed in `databasise/` (confirmed absent from `databasise/pyproject.toml` this session) | `>=2.0.0,<3.0.0` per v1's pin [ASSUMED] | Install task, gated by `checkpoint:human-verify` per Package Legitimacy Audit |
| `jsonpatch` PyPI package | Arm-patch resolution (D-13) | Not yet installed in `databasise/` (confirmed absent this session) | latest [ASSUMED] | Install task, gated by `checkpoint:human-verify` per Package Legitimacy Audit |
| Faiss/Cozo/SQLite embedded stores | Corpus index (D-01) | ✓ (already built, Phase 1) | pinned per `databasise/pyproject.toml` | — |

**Missing dependencies with no fallback:**
- v1's virtualenv — must be built as an explicit Phase 3 task; there is no way to run the original arm without it, and D-04 already names this as real, unbudgeted-looking work.

**Missing dependencies with fallback:**
- `openai`, `jsonpatch` — straightforward install tasks, each gated by a `checkpoint:human-verify` per the package-legitimacy protocol's SUS disposition.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2+ with `pytest-asyncio` (`asyncio_mode = "auto"`), per `databasise/pyproject.toml` (already configured, Phase 1) |
| Config file | `databasise/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd databasise && uv run pytest -q tests/parts_core/lightrag/ tests/clients/` (per-module, during node-by-node implementation) |
| Full suite command | `cd databasise && uv run pytest -q` (matches `.planning/config.json`'s configured `workflow.test_command`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODAL-01 (criterion 1) | All 17 nodes register with a real body; `embedder-index` authored as the 18th | unit | `pytest tests/parts/test_registry.py -k lightrag -x` | ❌ Wave 0 — extend existing `test_registry.py` or add a sibling |
| MODAL-01 (criterion 1) | Each of the 5 arm patches resolves against the base to exactly the node-id set §L.3's table states | unit | `pytest tests/parity/test_arm_resolution.py -x` | ❌ Wave 0 |
| MODAL-01 (criterion 2) | N-run variance band over `keywords`' output; retrieval-level structural diff within tolerance or named deviation | integration | `pytest tests/parity/test_retrieval_parity.py -x` (requires v1 venv + reachable LLM/embedding endpoints — likely `checkpoint:human-verify` gated per Environment Availability) | ❌ Wave 0 |
| MODAL-01 (criterion 3) | Per-node storage-ownership audit: no node touches an undeclared store | unit/integration | `pytest tests/parity/test_storage_audit.py -x` | ❌ Wave 0 |
| MODAL-01 (index import, D-01/D-02) | Byte-identical chunk text, matching vector-set hash, matching graph node/edge count between v1's on-disk index and the v2-imported copy | integration | `pytest tests/parity/test_import_verification.py -x` | ❌ Wave 0 |
| MACH-02 / MACH-03 (amendment) | A written amendment record exists naming the deferral and residual risk, mirroring `02-GATE-01-WAIVER.md`'s shape | manual-only (a document, not a behavior) | N/A — reviewed as a plan deliverable, not asserted by a test | ❌ Wave 0 — the amendment document itself |
| D-15 | Import-boundary check extended: no part under `parts_core/lightrag/` imports `v1.*` | unit | `pytest tests/test_import_boundary.py -x` (existing file — confirm it already covers new files by tree-walk, per this research's own finding that `scan_tree` walks the whole `databasise/` package; likely needs no code change, only a new assertion/fixture exercising the new directory) | ⚠️ Existing file, needs a new test case, not new checker logic |

### Sampling Rate

- **Per task commit:** `cd databasise && uv run pytest -q tests/parts_core/lightrag/ tests/clients/ tests/parts/test_registry.py` (fast, no network)
- **Per wave merge:** `cd databasise && uv run pytest -q` (full suite, per `.planning/config.json`'s `workflow.test_command`)
- **Phase gate:** Full suite green, plus the parity harness's own retrieval-level comparison run and recorded (D-10), before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `databasise/tests/parts_core/lightrag/` — new directory, one test module per ported node (or grouped by shared component, e.g. one `test_join_roundrobin.py` covering all three `join-*` positions)
- [ ] `databasise/tests/clients/` — new directory, tests for the new LLM/embedding/rerank client primitive and its capability-scoped wrapper
- [ ] `databasise/tests/parity/` — new directory: arm resolution, storage audit, import verification, retrieval parity
- [ ] `databasise/tests/parity/conftest.py` — shared fixtures: a fixed small corpus fixture (D-14), a v1-venv-availability skip-guard (since the venv is real, unbudgeted Phase 3 work per D-04, tests depending on it should skip cleanly, not fail, when the venv isn't yet built)
- [ ] Framework install: none — pytest/pytest-asyncio already configured; only the two new library installs (`openai`, `jsonpatch`) are needed, both `checkpoint:human-verify` gated

## Security Domain

Skipped — `.planning/config.json`'s `workflow.security_enforcement` is explicitly `false` (confirmed by reading the file this session).

## Sources

### Primary (HIGH confidence — read directly this session)

- `docs/system-model/PARTS.md` §L.1, §L.2, §L.3 (lines 45-213) — the eighteen-position node table, wiring family, PARTS-01 verdict
- `docs/system-model/CONTRACT.md` §1, §2, §3, §4, §5, §9, §13.4 (lines 168-546) — wiring format/identity, node kinds/effects, depth/containment, evidence/measurement, the gate, budget, primitive part types
- `docs/system-model/RIG.md` §TR.1-3, §EV.1-3, §CM.1 (lines 102-200, 340-415) — trace schema field table, eval-bundle versioning, target-MDE derivation
- `docs/system-model/wirings/lightrag-base.json` and all five `lightrag-arm-*.json-patch.json` files — the full 18-node base wiring plus every arm's RFC 6902 operations
- `databasise/parts/schema.py`, `databasise/parts/registry.py`, `databasise/parts_core/__init__.py`, `databasise/parts_core/declared_only.py`, `databasise/parts_core/fake_llm_caller.py` — the exact `NodeContext`/`Part`/`CapabilityScopedStores` shapes this phase extends
- `databasise/runner/scheduler.py`, `databasise/runner/trace.py`, `databasise/runner/budget.py` — the `NodeContext` construction call site, the `RunRecord`/`NodeTrace` shape, the `meter()` function
- `databasise/validator/execution_mode.py` — confirmed `calls_llm`/`calls_embedding`/`calls_rerank` do not force out-of-process hosting
- `databasise/validator/parse.py` — `parse_wiring`'s plain-dict input contract (confirms arm resolution must happen before this call)
- `databasise/stores/vector.py`, `databasise/stores/graph.py`, `databasise/stores/kv.py`, `databasise/stores/base.py`, `databasise/namespaces.py` — store adapter surfaces the import step and the port's node bodies read
- `databasise/tools/check_import_boundary.py`, `databasise/tests/stores/test_graph_frozen_bugs.py` — the existing import-boundary and Cozo frozen-bug regression gates
- `databasise/evidence/wirings/w1-lightrag-query-side.json`, `databasise/evidence/falsifier2.py` — the stub this phase retires, the "evidence ships as committed re-runnable files" precedent
- `v1/tests/parity/run_substrate_parity.py` (571 lines) — the exact parity-harness precedent CONTEXT.md names
- `v1/pyproject.toml`, `v1/env.example` — confirms v1's existing `openai` SDK dependency and OpenAI-compatible env-var configuration for OpenRouter/Ollama
- `v1/lightrag/operate.py`, `v1/lightrag/utils.py` (grep-verified) — confirmed PARTS.md's cited line numbers do not match the current checkout (see Common Pitfalls, Pitfall 5)
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/config.json` — requirement text, project state, phase success criteria, workflow toggles (`nyquist_validation: true`, `security_enforcement: false`)
- `.planning/phases/03-lightrag-query-side/03-CONTEXT.md`, `03-DISCUSSION-LOG.md` — this phase's locked decisions
- `.planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md` (referenced, structure noted) — the amendment-record precedent for MACH-02/MACH-03's deferral
- `.planning/research/PITFALLS.md` (Pitfalls 1, 2, 6, 8), `.planning/research/ARCHITECTURE.md` — the failure modes this phase is designed against

### Secondary (MEDIUM confidence)

- `openai` PyPI package's existence and repo — confirmed via `gsd-tools query package-legitimacy check`, cross-referenced against v1's own already-vendored dependency (same package, same purpose)
- `jsonpatch` PyPI package's existence and repo — confirmed via the same tool; the RFC 6902 standard-library-choice claim itself is training knowledge, not independently checked against an authoritative docs source this session

### Tertiary (LOW confidence, marked for validation)

- `openai` SDK version range (`>=2.0.0,<3.0.0`) — copied from v1's pin, not freshly queried against the live PyPI registry this session
- `jsonpatch`'s claim to be "the" standard Python RFC 6902 library — plausible and consistent with training knowledge, but not cross-checked against Context7/official PyPI trend data this session

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM — the node/wiring shape is HIGH confidence (code-verified, mechanically checked per D-06's kill condition); the two new libraries (`openai`, `jsonpatch`) are MEDIUM (existence confirmed, exact version not freshly queried, "standard choice" claim is training knowledge)
- Architecture: HIGH — every integration point named (`NodeContext` construction site, `CapabilityScopedStores` pattern, `parse_wiring`'s plain-dict contract, `execution_mode` derivation) was confirmed by reading the live code this session, not inferred from documentation alone
- Pitfalls: MEDIUM-HIGH — Pitfalls 1/2/3/4 are project-specific research already vetted at Phase 1 kickoff (`.planning/research/PITFALLS.md`, MEDIUM confidence by its own header); Pitfall 5 (stale line numbers) is a new HIGH-confidence finding from this session's own direct grep verification

**Research date:** 2026-08-31
**Valid until:** 30 days for the contract/architecture findings (stable, code-verified); 7 days for anything touching the live `v1/` checkout state or external package registry data (fast-moving relative to this research's shelf life)
</content>
