# Phase 6: HippoRAG 2 & Side-by-Side - Research

**Researched:** 2026-09-09
**Domain:** Graph-algorithm decomposition (HippoRAG 2 → 13 fitted nodes over `igraph`/`prpack`), cross-arm comparison seam (§18 envelope fan-out), eval-bundle + A/A statistical calibration, mutable-store snapshot/reset protocol decision
**Confidence:** MEDIUM — the *contract* is HIGH confidence (frozen, already-written design text, code-verified against this session's own reads); the *build mechanics* (bootstrap replicate count, "materially narrower" threshold, new-package pins) are LOW/ASSUMED and need owner confirmation before they become locked decisions.

## Summary

Phase 6 is a **build** phase against an already-**finished design**. `docs/system-model/CONTRACT.md`, `RIG.md`, and `PARTS.md ## §H` are a verbatim, frozen mirror of an upstream design project — they already specify HippoRAG 2's thirteen node positions, the whole-graph-PPR capability shape, the cross-arm namespace-isolation rule, the comparison-surface envelope, the eval-bundle/A-A-calibration procedure, and the two open falsifiers (F-07, F-14) this phase must close. Nothing in this phase is a fresh architecture decision; everything is "read the frozen clause, build the thing it names." The one genuine judgment call left to the owner is F-07 (build a snapshot/reset protocol for `mutable-store` components, or declare the exclusion permanent) and the numeric threshold behind "T1's null width materially narrower than T0's," which RIG.md never quantifies.

Three things this research verified this session that the frozen docs did not (or could not) verify themselves: (1) `docs/system-model/PARTS.md ## §H`'s thirteen-node HippoRAG table maps cleanly onto the **real, official** `hipporag` PyPI package's own `run_ppr` method — fetched live from `github.com/OSU-NLP-Group/HippoRAG/src/hipporag/HippoRAG.py` this session — confirming the exact `igraph.Graph.personalized_pagerank(vertices=..., damping=0.5, directed=False, weights='weight', reset=reset_prob, implementation='prpack')` call shape; (2) the codebase's own namespace-derivation machinery (`databasise/namespaces.py`) already implements RIG §RUN.1's isolation rule exactly, so "two arms on one corpus" is not new design — it is a namespace hash that already differs because the two recipes share no resolved input, exactly as RIG §RUN.2's own worked `VT-1`/`GR-1` pair predicts; and (3) the `join`/`fanout` **structural-kind dispatch that `reset-vector-join` needs is not implemented anywhere in the runner today** — `databasise/parts/schema.py`'s own docstring says so explicitly ("a later plan is where the fanout/join/... dispatch actually gets built") — making this a real Wave-0 infrastructure gap, not merely "wire up one more part."

**Primary recommendation:** Build in this order — (1) graph-store bulk-export + vector-store self-KNN/score_all capability methods (new methods on the existing `CozoGraphStore`/`FaissVectorStore` adapters, not new store types), (2) the `join` structural-kind dispatch in the runner, (3) the thirteen HippoRAG parts and their wiring JSON, (4) a parity run against the real upstream `hipporag` PyPI package to earn `stage` depth (Falsifier 7's second application), (5) the comparison seam endpoint (API-08) as a thin fan-out over the existing single-arm `_execute()` path, (6) the eval bundle + A/A calibration tooling (greenfield — no code exists yet), (7) the F-07 decision and F-14's live-seam-call record last, since both need a working comparison to observe.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HippoRAG 2 node decomposition (13 Parts) | API / Backend (Part bodies) | — | Pure Python compute nodes registered exactly like the existing LightRAG parts (`databasise/parts_core/lightrag/*.py`) |
| Whole-graph PPR (`ppr` node) | Database / Storage (Graph store bulk-export) | API / Backend (the `igraph`/`prpack` compute itself, which runs in-process, not inside Cozo) | The *read* is a Graph-store capability (§14.2 bulk-export); the *compute* is a machine-owned in-process library call over the exported representation, not a database operation |
| Cross-arm store isolation | Database / Storage | — | Already built (`databasise/namespaces.py`, `databasise/stores/*.py`) — no new tier, just a new recipe hash that naturally isolates |
| Comparison seam endpoint (API-08) | API / Backend | — | A fan-out wrapper over the existing `Databasise._execute()` single-arm path (`databasise/seam/engine.py`) |
| Eval bundle + A/A calibration (MACH-02/03) | API / Backend (offline tooling, not request-serving) | Database / Storage (bundle persistence) | Runs out-of-band against the same seam a caller uses; not a live request path |
| Snapshot/reset protocol for `mutable-store` (F-07/MACH-10) | Database / Storage | — | `codebase-memory-mcp`'s own SQLite files are the only real `mutable-store` instance in this project today; a snapshot/reset is a file-copy-and-restore operation at that tier |

## Frozen System-Model Inputs — What They Already Settle

This phase's domain is unusual: the "architecture research" is already written, ratified, and verbatim-frozen. `docs/system-model/CONTRACT.md`/`RIG.md`/`PARTS.md ## §H`/`## §R` (both files) are the authoritative source for every design question this phase would otherwise have to answer from scratch. Below is what each already settles, cited with section numbers so the planner can jump straight to the clause.

## User Constraints

<user_constraints>
No `CONTEXT.md` exists for this phase — the operator chose to plan without `/gsd-discuss-phase`. Per the orchestrator's own instruction, `ROADMAP.md`'s Phase 6 success criteria are the decision record and are treated as locked, not as discretion:

### Locked Decisions (from ROADMAP.md Phase 6, verbatim success criteria)

1. HippoRAG 2 runs as thirteen fitted node positions with no opaque core left behind, whole-graph PPR reached through §14.2's Graph bulk-export declared capability into the native igraph/prpack call, with OpenIE and reset-vector-join scaling carried as node internals and index-side effective depth staying `opaque` under the taint rule until its parity is shown
2. LightRAG and HippoRAG 2 run on one corpus under RIG §RUN — KV shared only where scope admits it, graph and vector stores isolated per arm — and their outputs are structurally comparable
3. Caller sends one query against two or more modalities and receives per-arm results keyed by the selectors they supplied, never by arm id, wiring name, node id, or modality name; comparison returns per-arm outputs, traces, and scores with no verdict, and a single arm comes back as a run rather than a comparison
4. The first genuine seam call records F-14's outcome either way: no consumer-visible envelope field changed across the modality swap, or the field that did is named
5. Mutable-store components either have a defined snapshot/reset protocol or are recorded as permanently excluded from A/B — F-07 discharged rather than left open
6. Owner mints an eval bundle with dev/holdout/sealed splits carrying questions, gold answers, judge instance, judge prompt hash, corpus snapshot hash, determinism/concurrency setting, and both §EV.2 target families (MACH-02), then runs one A/A calibration and reads a bootstrap-resampled p95 floor keyed to `(bundle@v, tier, metric)` with T1's null width materially narrower than T0's — Falsifier 5, MACH-03, carried forward from Phase 3 per `.planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md`

### Additional locked project constraints (from `.claude/CLAUDE.md` and `ROADMAP.md ## Ordering Constraints`)

- D4 One Machine — settled, not re-litigated; contract vocabulary (NodeKind tagged sum, 17-member `effects[]`, three artifact scopes, budget tokens, promote/rollback ledger) is frozen input
- Language: Python; Runtime: local NixOS, embeddable in-process; no external DB servers, no Docker
- The §18 seam must stay modality-agnostic — swapping the fitted modality changes no field a consumer sees
- Real defaults are Cozo (graph) + Faiss (vector) — **not** LanceDB. `.planning/research/STACK.md:26,69,85,97` still recommends LanceDB on stale pre-correction data; it is superseded by `ROADMAP.md`'s own inline amendment and `.claude/CLAUDE.md`'s explicit correction. Treat `.planning/research/STACK.md` as historical/superseded for any vector-store recommendation.
- "Rig before comparison surface": API-08's comparison endpoint lands in Phase 6 with the side-by-side rig, not earlier (`ROADMAP.md` line 296)
- Phase 6 does not start until Phase 5's admission work completes (already true — Phase 5 is closed per `.planning/STATE.md`)

### Claude's Discretion

Everything not pinned above: the exact bootstrap replicate count `B`, the concrete numeric threshold for "materially narrower," whether `igraph` is added as a runtime dependency of `databasise` itself or only of a separate parity-harness environment, and the internal shape of the eval-bundle persistence format (file layout, not its required *content*, which §10/§EV.1 already freeze).

### Deferred Ideas (OUT OF SCOPE)

- Any UI, Docker/k8s, re-litigating D4, Sourcerer-side applet work, Falsifier 6's foreign-hosted-LightRAG experiment, full corpus/index dumps via API, N1/N3 (store kinds as NodeKind members / `writes_artifact` differentiation) — all per `REQUIREMENTS.md ## Out of Scope`
- Self-improving/auto-promotion loop, third-modality port, measured cost-model validation replacing §CM.3's inference bands, DR-05 bi-temporal validity — all v2 per `REQUIREMENTS.md ## v2 Requirements`
- Switching the default measurement-gated-promotion posture ON for answer-level/index-side classes — named `## §F3.2`'s own reversibility note, explicitly a later build-time act, not this phase's
</user_constraints>

## Phase Requirements

<phase_requirements>

| ID | Description | Research Support |
|----|-------------|------------------|
| MODAL-04 | HippoRAG 2 fully decomposed — 13 node positions, no opaque core; whole-graph PPR via §14.2 bulk-export into native igraph/prpack; OpenIE/reset-vector-join carried as node internals; index-side effective depth stays `opaque` under the taint rule until parity is shown | `PARTS.md ## §H`'s full node table (quoted below); this session's live verification of the upstream `hipporag` package's `run_ppr`/`add_synonymy_edges`/`save_igraph`; "Don't Hand-Roll" §Graph bulk-export and §Vector self-KNN; "Taint rule" section below |
| MODAL-05 | LightRAG and HippoRAG 2 run side-by-side on one corpus under RIG §RUN; KV shared per MACH-08 scope rules, graph/vector isolated per arm; F-14 recorded either way on first genuine seam call | `RIG.md ## §RUN.1`/`§RUN.2` (quoted below); `databasise/namespaces.py` (already-built isolation, read this session); "Two arms on one corpus" section |
| API-08 | One query against ≥2 modalities in one call, per-arm results keyed by caller-supplied selectors (never arm_id/wiring/node id/modality name); inspection-only, no verdict; one arm returns a run, not a comparison | `CONTRACT.md §18.2`/`§18.3`/`§18.4` (quoted); `RIG.md ## §RUN.3`/`§RUN.4`/`## §AA.4` (comparison modes, quoted); "The §18 comparison surface" section |
| MACH-10 | F-07 discharged: snapshot/reset protocol for `mutable-store` components defined, or A/B exclusion recorded permanent | `CONTRACT.md §14.4` point 3 (quoted); `MODEL-RED-TEAM.md F-07` (quoted); "F-07 snapshot/reset protocol" section |
| MACH-02 | Eval bundle: dev/holdout/sealed splits, questions/gold/judge instance/judge prompt hash/corpus snapshot hash/determinism-concurrency setting, both §EV.2 target families | `RIG.md ## §EV.1`/`## §EV.2` (quoted); "Eval bundle + A/A calibration" section |
| MACH-03 | First A/A calibration: bootstrap-resampled p95 floor keyed to `(bundle@v, tier, metric)`; T1 null width materially narrower than T0's — Falsifier 5 gate | `RIG.md ## §AA.1`/`## §AA.2`/`## §AA.3` (quoted); "Eval bundle + A/A calibration" section, cost derivation |

</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `igraph` | `>=0.11,<2.0` [ASSUMED — package identity VERIFIED, version range not yet checkpointed] | Native whole-graph Personalized PageRank via `prpack`; also hosts `graph-augment-persist`'s in-memory graph object | `personalized_pagerank(..., implementation='prpack')` is exactly the call `CONTRACT.md §14.2`'s Graph bulk-export row and `PARTS.md ## §H`'s `ppr` node describe; confirmed against the real upstream HippoRAG source this session (see Code Examples) |
| `numpy` | matches `v1/pyproject.toml`'s existing `>=1.24.0,<3.0.0` pin [ASSUMED — not yet in `databasise/pyproject.toml`] | Dense reset-vector arrays (`reset-vector-join`), bootstrap resampling arrays (MACH-03) | Already a transitive/direct dependency everywhere else in this monorepo (`v1/pyproject.toml:31,67`); `igraph`'s own PPR call takes/returns numpy-shaped arrays |
| `scipy` | `>=1.11` [ASSUMED] | `scipy.stats.bootstrap(..., paired=True, method='percentile')` for the A/A calibration's bootstrap-resample step; `scipy.stats.binomtest` for exact McNemar (binary metrics) | Don't-hand-roll: RIG §AA.1 names "the ordinary nonparametric bootstrap" and reuses "the paired-bootstrap machinery §5 already specifies" — `scipy.stats.bootstrap` is exactly that machinery, built-in, tested, with `paired=True` and a `ConfidenceInterval` result shape [CITED: docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `hipporag` (real upstream PyPI package) | `2.0.0a4` on PyPI / `2.0.0a5` on `main` [VERIFIED: pypi.org/pypi/hipporag/json and github.com/OSU-NLP-Group/HippoRAG/pyproject.toml, both fetched this session] | Parity-baseline oracle for Falsifier 7's second application (compare the decomposed 13-node wiring's retrieval output against the unmodified original, exactly as Phase 3 did for LightRAG) | Install in a **separate, isolated interpreter/venv** — never import into `databasise/`'s own environment. Its own pin list is heavy: `torch==2.5.1`, `transformers==4.45.2`, `python_igraph==0.11.8` (the *legacy* package name — see Pitfall below), `litellm==1.73.1`, `networkx==3.4.2`. Mirror the existing "subprocess-backed opaque Part body" pattern (`05-LEARNINGS.md`'s pattern of the same name) — a leaf driver script under its own pinned interpreter, JSON over stdin/stdout. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `igraph`'s native `prpack` PPR | Hand-rolled power-iteration PPR over Cozo query results | Forbidden by contract: `CONTRACT.md §14.2`'s bulk-export row explicitly requires "the store exposes a bulk-export path rather than forcing an N-call pointwise emulation," and a store lacking a needed sub-capability "has not yet earned this capability... MUST refuse the wiring rather than silently truncating/emulating" |
| `scipy.stats.bootstrap` | Hand-rolled `for _ in range(B): resample...` loop + `np.percentile` | Legal (numpy alone is sufficient and the RIG text never mandates `scipy` by name) — recommend `scipy` only for its already-vetted `paired=True` handling and one-sided confidence-interval support, saving a hand-rolled resampling loop's edge cases (ties, small-n degenerate resamples) |

**Installation:**
```bash
cd databasise
uv add "igraph>=0.11,<2.0" "numpy>=1.24,<3.0" "scipy>=1.11"
```

**Version verification performed this session:**
- `igraph` on PyPI: latest `1.0.0`, published 2025-10-23, `requires_python>=3.9`, homepage `igraph.org/python`, source `github.com/igraph/python-igraph` [VERIFIED: pypi.org/pypi/igraph/json]. Release history back through `0.9.8`–`0.11.9` confirms this is the same project's continuous line, not a rename collision.
- `python-igraph` on PyPI: latest `1.0.0`, summary literally reads **"(legacy package)"** [VERIFIED: pypi.org/pypi/python-igraph/json] — same underlying project, kept installable for backward compatibility, but the *current* name to depend on is `igraph`.
- `hipporag` on PyPI: `2.0.0a4`; `main` branch `pyproject.toml`/`setup.py` both read `version="2.0.0a5"` [VERIFIED: fetched both this session].
- `numpy`/`scipy` version ranges are carried from the monorepo's own existing `v1/pyproject.toml` pins, not independently re-verified against the PyPI registry this session (training-derived range, [ASSUMED]).

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `igraph` | pypi | Project itself is 20+ years old (igraph.org); PyPI `1.0.0` release is 2025-10-23 | Sandbox reports `unknown-downloads` | `github.com/igraph/python-igraph` | `[SUS]` — reason `unknown-downloads` | Flagged — planner must add `checkpoint:human-verify` before install. **Known checker blind spot**: this is the same "download-count blind spot in the checking sandbox, not a slopsquat signature" pattern `05-LEARNINGS.md` already documents for `mcp`/`python-multipart` in Phase 5 — `igraph` is a two-decade-old, widely-used scientific-computing project with an active GitHub org, not a plausible hallucination. |
| `numpy` | pypi | Extremely well-established (originated 2006, NumFOCUS-governed) | Sandbox reports `unknown-downloads`, `no-repository`, `too-new` (misreading the latest micro-release's upload date as founding date — the same failure mode `05-LEARNINGS.md` names) | `github.com/numpy/numpy` (not surfaced by the sandbox check) | `[SUS]` | Flagged for the same reason — checkpoint required by protocol, but this is the numpy already pinned in `v1/pyproject.toml:31,67` in this exact monorepo. |
| `scipy` | pypi | Extremely well-established (originated 2001) | Same `too-new`/`unknown-downloads`/`no-repository` blind spot | `github.com/scipy/scipy` (not surfaced) | `[SUS]` | Flagged, checkpoint required. |
| `hipporag` | pypi | Alpha releases only (`2.0.0a4`/`a5`) — genuinely a young package on the *version* axis, though the org (OSU-NLP-Group, published NeurIPS'24) is not | Not checked via the seam (dev-only parity tool, not a `databasise/pyproject.toml` dependency) | `github.com/OSU-NLP-Group/HippoRAG` [VERIFIED: fetched `pyproject.toml`/`setup.py`/`HippoRAG.py` directly this session] | Not run through `package-legitimacy check` (out of scope — never added to `databasise/pyproject.toml`) | Approved for use **only** as an isolated parity-harness dependency, in its own venv, per the pattern above. Flag its alpha-version status to the owner explicitly: this project is depending on a pre-1.0 API for a **measurement**, not for production behavior, and an upstream API break between `2.0.0a4` and a future `2.0.0` would break the parity harness, not `databasise` itself. |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** `igraph`, `numpy`, `scipy` — the planner must add a `checkpoint:human-verify` task before each install, per protocol. All three are almost certainly false positives (the same sandbox blind spot phase 5 already documented and resolved by human confirmation), but the gate is mechanical and does not know that on its own.

## Architecture Patterns

### System Architecture Diagram

```
                         Caller (REST / MCP / in-process)
                                     │
                                     ▼
                    §18.4 selector resolution (existing, per-arm)
                    ┌────────────────┴────────────────┐
                    │  API-08 comparison request:      │
                    │  N selectors, one query object    │
                    └────────────────┬────────────────┘
                                     │  fan-out (NEW — this phase)
              ┌──────────────────────┼──────────────────────┐
              ▼                      ▼                      ▼
    resolve_selector(sel_1)   resolve_selector(sel_2)   resolve_selector(sel_N)
    → lightrag/hybrid wiring  → hipporag/base wiring    → ...
              │                      │                      │
              ▼                      ▼                      ▼
    Databasise._execute()   Databasise._execute()   Databasise._execute()
    (existing, unmodified)  (existing, unmodified)   (existing, unmodified)
              │                      │                      │
      ┌───────┴────────┐    ┌────────┴─────────┐
      │ namespace =     │    │ namespace =       │   ← derive_namespace() (existing,
      │ hash(lightrag    │    │ hash(hipporag      │      databasise/namespaces.py) —
      │ recipe, corpus,  │    │ recipe, corpus,     │      the two hashes differ because
      │ scope=shared)    │    │ scope=quarantined)   │      the two recipes share no
      └───────┬────────┘    └────────┬─────────┘      resolved input (RIG §RUN.2) —
              │                      │                     isolation is a SIDE EFFECT,
              ▼                      ▼                     not new code
    Cozo graph / Faiss vector   Cozo graph / Faiss vector
    (LightRAG's own namespace)  (HippoRAG's own namespace,
                                 PLUS in-process igraph.Graph
                                 object for bulk PPR — NEW)
              │                      │
              └──────────┬───────────┘
                          ▼
         per-arm §18.2 envelope assembly (existing shape, reused per-arm)
                          │
                          ▼
     keyed-by-caller-supplied-selector response dict (NEW — this phase)
     { selector_1: envelope_1, selector_2: envelope_2, ... }
     — no arm_id, wiring name, node id, or modality name anywhere in this shape
     — no verdict; inspection-only; N=1 selector returns one bare envelope (a run),
       never this dict shape, per RIG §RUN.3's degenerate-width rule
```

### Recommended Project Structure

```
databasise/
├── parts_core/
│   └── hipporag/                  # NEW — mirrors parts_core/lightrag/'s one-file-per-node convention
│       ├── chunk_embed.py         # hipporag/chunker-embedder@0.1.0
│       ├── openie.py              # hipporag/openie-extractor@0.1.0
│       ├── entity_fact_embed.py   # hipporag/entity-fact-embedder@0.1.0
│       ├── fact_edges.py          # hipporag/fact-edge-builder@0.1.0
│       ├── passage_edges.py       # hipporag/passage-edge-builder@0.1.0
│       ├── synonymy_edges.py      # hipporag/synonymy-edge-builder@0.1.0 (self-KNN)
│       ├── graph_augment_persist.py  # hipporag/graph-materializer@0.1.0 (bulk-export write)
│       ├── fact_score.py          # hipporag/fact-scorer@0.1.0 (score_all)
│       ├── fact_filter.py         # hipporag/fact-filter@0.1.0
│       ├── dpr_fallback.py        # hipporag/dpr-fallback@0.1.0
│       ├── reset_vector_join.py   # hipporag/reset-vector-join@0.1.0 (join structural kind)
│       ├── ppr.py                 # hipporag/ppr-retriever@0.1.0 (bulk-export read + igraph call)
│       └── assemble_result.py     # hipporag/result-assembler@0.1.0
├── wirings/
│   └── hipporag/
│       └── base.json              # NEW — single base wiring, no arms (PARTS.md §H's own verdict)
├── stores/
│   ├── graph.py                   # MODIFIED — add bulk_export() to CozoGraphStore
│   └── vector.py                  # MODIFIED — add self_knn()/score_all() to FaissVectorStore
├── runner/
│   └── (join/fanout structural-kind dispatch — MODIFIED, wherever the scheduler
│         currently dispatches Part.body; schema.py's NodeKind union already exists,
│         only the dispatch is missing)
├── seam/
│   └── compare.py                 # NEW — API-08's fan-out wrapper over engine._execute()
└── eval/                          # NEW — greenfield, no prior code
    ├── bundle.py                  # EvalBundle schema, dev/holdout/sealed, versioning (MACH-02)
    └── calibration.py             # A/A bootstrap calibration procedure (MACH-03)
```

### Pattern 1: Bulk-export capability as a new adapter method, not a new store type

**What:** `CONTRACT.md §14.2`'s Graph bulk-export sub-capability is satisfied by adding one new method to the *existing* `CozoGraphStore` adapter (`databasise/stores/graph.py`), which converts Cozo's relational node/edge rows into an `igraph.Graph` object. This keeps "one machine, one Graph-store backend" intact — Cozo remains the sole graph backend; `igraph` is a compute library the `ppr` node calls, not a second database.

**When to use:** Any node declaring `§14.2`'s `bulk-export` sub-capability (here: `graph-augment-persist` writes the accumulated node/edge/weight data; `ppr` reads the whole graph back for the native PPR call).

**Example:**
```python
# Source: this session's read of databasise/stores/graph.py (CozoGraphStore, no bulk-export
# method exists yet — this is new code following the file's own existing query/type-conversion
# conventions, e.g. explicit type assertions per Cozo bug #275).
async def export_to_igraph(self, *, weight_attr: str = "weight") -> "igraph.Graph":
    """§14.2 Graph bulk-export: return the whole graph as a native igraph.Graph object.

    Reads every node and edge row via a single Cozo query each (never N pointwise calls,
    per §14.2's own "forcing an N-call pointwise emulation" refusal) and constructs one
    igraph.Graph with all node ids as vertex names and the resolved `weight_attr` as the
    single collapsed edge weight — exactly the "single weight edge attribute collapsing all
    three edge types" shape PARTS.md ## §H's `ppr` row already documents for HippoRAG's own
    graph-augment-persist output.
    """
    import igraph as ig

    node_rows = await self._run("?[id] := *nodes{id}")          # bulk read, one query
    edge_rows = await self._run(f"?[src, tgt, {weight_attr}] := *edges{{src, tgt, {weight_attr}}}")
    vertex_names = [row[0] for row in node_rows]
    idx = {name: i for i, name in enumerate(vertex_names)}
    edges = [(idx[r[0]], idx[r[1]]) for r in edge_rows]
    weights = [r[2] for r in edge_rows]
    g = ig.Graph(n=len(vertex_names), edges=edges, directed=False)
    g.vs["name"] = vertex_names
    g.es["weight"] = weights
    return g
```

### Pattern 2: `join` structural-kind dispatch (currently missing — build before wiring HippoRAG's query side)

**What:** `databasise/parts/schema.py` already declares `NodeKind`'s `_JoinKind` member (a pydantic discriminated-union tag), but its own docstring states plainly: *"a later plan is where the fanout/join/fixpoint/subgraph/opaque structural-kind dispatch actually gets built and where `NodeKind` starts being consumed as more than a declared skeleton."* `reset-vector-join` is HippoRAG's one `join`-kind node (the `ref`-keyed vector-sum shape `CONTRACT.md §13.3`'s H2 repair already specifies), and nothing in the runner today knows how to execute a `join` node.

**When to use:** Wave 0 of this phase, before any HippoRAG query-side part is wired — `ppr` depends on `reset-vector-join`'s output.

**Example (the socket shape, quoted rather than invented):**
```python
# Source: docs/system-model/CONTRACT.md §13.3's join schema, and PARTS.md ## §H's
# reset-vector-join row (both [docs-verified]/[code-verified] in the frozen contract).
# The ref-keyed vector-sum shape: multiple branches each emit a sparse {vertex_ref: weight}
# mapping over the SAME dense vertex-index space the graph bulk-export uses (PARTS.md ## §H's
# own "two shape details" note); the join sums them, order-insensitive, disjoint-support.
def dispatch_join_node(node: WiringNode, branch_outputs: list[dict[str, float]], vertex_count: int) -> "np.ndarray":
    import numpy as np
    summed = np.zeros(vertex_count)
    for branch in branch_outputs:
        for vertex_idx, weight in branch.items():
            summed[vertex_idx] += weight  # disjoint-support sum, per PARTS.md §H arm-precedence
    return summed
```

### Pattern 3: HippoRAG's own upstream PPR call (verified against the real, current package)

**What:** The exact call the `ppr` node's body should reproduce, fetched live from the real upstream repository this session — not paraphrased from a paper or from training memory.

**Example:**
```python
# Source: github.com/OSU-NLP-Group/HippoRAG/src/hipporag/HippoRAG.py, `run_ppr` method,
# fetched via raw.githubusercontent.com this session [VERIFIED — live fetch, current `main`].
# NOTE: PARTS.md ## §H cites this method at HippoRAG.py:1709-1748 against an older pinned
# commit; the current `main` branch has it at a different line range (~2166-2205) with an
# identical call shape — see the Assumptions Log entry on this line-number drift.
pagerank_scores = graph.personalized_pagerank(
    vertices=range(len(node_name_to_vertex_idx)),
    damping=damping,          # HippoRAG's own default: 0.5, not igraph's own default of 0.85
    directed=False,            # "HippoRAG propagates relevance over the undirected projection"
    weights="weight",
    reset=reset_prob,          # dense per-vertex array, NaN/negative entries zeroed first
    implementation="prpack",
)
doc_scores = [pagerank_scores[idx] for idx in passage_node_idxs]  # partitioned readback
```

### Pattern 4: Comparison as a thin fan-out over the existing single-arm path

**What:** `databasise/seam/engine.py`'s `Databasise._execute()` already does selector resolution → run → envelope assembly for one arm (`query()`/`query_stream()` both call it). API-08 does not need a new execution engine — it needs a loop over `_execute()` keyed by the caller's own selectors, with the per-arm internal identity (wiring name, arm id) stripped before assembly, exactly as `§18.2`'s closed-envelope rule already requires for the single-arm case.

**When to use:** API-08's comparison endpoint.

**Anti-pattern to avoid:** Do not build a second scheduler, a second store-namespace-resolution path, or a second envelope-assembly function for the comparison case — `RIG.md ## §RUN.4` states explicitly that "comparison as inspection is always available even where adjudication is not" and costs "nothing beyond the runs themselves," because it reuses the same per-arm mechanics.

### Anti-Patterns to Avoid

- **Hand-rolling PPR or self-KNN as N pointwise queries:** `§14.2` explicitly forbids this — a store lacking the sub-capability "MUST refuse the wiring rather than silently truncating to top-k" or emulating an `O(N²)` pointwise pass.
- **A second, HippoRAG-specific comparison mechanism:** RIG `## §AA.4` is explicit that LightRAG-vs-HippoRAG is `architecture-comparison mode` under the *same* gate mechanism (`check`/`preview`/`run`/`promote-next`/`promote-now`, the same eight verdicts, the same refusal list) as everything else — never a bespoke HippoRAG-only code path.
- **Reading "parity, not gain" onto the LightRAG-vs-HippoRAG comparison:** that framing is `decomposition-parity mode` only (a recut arm vs. its own pre-decomposition original). LightRAG vs. HippoRAG is `architecture-comparison mode`, where "an improvement is the comparison's own payoff, not a suspicious result to be explained away" (`RIG.md ## §AA.4`).
- **Letting a comparison caller name a wiring, node id, or modality by string:** `§18.4` forbids this on the way in exactly as `§18.2` forbids it on the way out — selectors only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Whole-graph Personalized PageRank | A power-iteration loop over Cozo query results | `igraph.Graph.personalized_pagerank(..., implementation="prpack")` | `§14.2` forbids the pointwise emulation outright; `prpack` "calculates PageRank scores by solving a set of linear equations and is the suggested [implementation], as it is the most stable and fastest for all but small graphs" [CITED: python.igraph.org's own PPR tutorial + API reference, fetched this session] |
| Bulk self-referential KNN (`synonymy-edges`) | An `O(N²)` all-pairs cosine loop | A batched top-k similarity search the vector store exposes as one call | `§14.2`'s `self-knn` row: "that the store exposes a batched self-KNN path rather than forcing an `O(N²)` pointwise emulation" |
| Bootstrap-resampled confidence floor | A hand-written `for _ in range(B): np.random.choice(...)` loop | `scipy.stats.bootstrap(data, statistic, paired=True, method="percentile")` | Reuses vetted, tested resampling machinery with correct handling of `paired=True` and one-sided intervals; RIG §AA.1 explicitly reuses "the paired-bootstrap machinery §5 already specifies," never inventing new statistical apparatus |
| RFC 8785 canonicalisation / RFC 6902 patch application | Anything — already built | `databasise/identity/canon.py`'s `canonicalise()`; the existing `jsonpatch` dependency | Already shipped in Phase 1/3; no reason to touch it in Phase 6 |
| Cross-arm storage isolation | A new namespace-keying scheme for the comparison rig specifically | `databasise/namespaces.py`'s `derive_namespace()`, unmodified | RIG §RUN.1's isolation rule is already implemented; HippoRAG's differing recipe hash isolates automatically |

**Key insight:** every "don't hand-roll" item in this phase is a case where the frozen contract has *already* named the forbidden shortcut by name and forbidden it — this is not a generic best-practice list, it is a literal transcription of `§14.2`'s own machine-checked refusal rules.

## Taint Rule / `opaque` Effective Depth — What Keeps It `opaque` and What "Parity" Requires

**The apparent puzzle.** `PARTS.md ## §H` decomposes HippoRAG 2 into thirteen named, individually-typed node positions — no node is declared the `opaque` *structural kind*. Yet the same document states: *"Artifact scopes: `quarantined` — the whole index side (`chunk-embed` through `graph-augment-persist`) is undecomposed relative to any prior port on this record, so its effective depth is `opaque` under the taint rule."* [docs-verified, quoted from `PARTS.md ## §H`]

**The resolution.** Two distinct facts explain this, both already in the frozen record:

1. Several nodes are typed by **"nearest signature"** rather than an exact `§13.4` primitive-part-type match: `fact-score`/`ppr`/`dpr-fallback` are typed `retriever` "nearest signature," and `graph-augment-persist` has **no `§13.4` row at all** ("no `§13.4` row names a whole-graph materialization step"). `§19.1`'s port-completeness diagnostic — which the validator uses to certify a socket's type-compatibility — cannot fully certify a node whose type is an analogy rather than an exact match.
2. `§6`'s **"parity, not gain"** rule and `§5`'s **"determinism is verified, never declared"** rule together mean a fresh port earns `stage`-eligibility only by being *measured* against a trusted baseline, never by self-declaration. LightRAG's own decomposed query side earned exactly this measurement in Phase 3 (`03-GATE-AMENDMENT.md`'s own retrieval-level parity gate). HippoRAG 2 has had no equivalent run yet.

**What "showing parity" concretely requires (this session's own synthesis, not stated verbatim anywhere in the frozen docs — [inference]):** Run the real upstream `hipporag` PyPI package (installed in its own isolated interpreter, per the Standard Stack section above) end-to-end on the same corpus and the same queries the decomposed 13-node wiring runs, and compare retrieval-level output (which passages come back, in what order, at what PPR score) — the same methodology `03-GATE-AMENDMENT.md` already ran for LightRAG, itself a second application of **Falsifier 7** ("the first real decomposition increment the build performs: if decomposing [the port] against the opaque original cannot be brought inside the A/A band this section's parity gate requires, promotion under this section's mechanism is a rewrite wearing a refactor's name" — `CONTRACT.md §6`'s own Falsifier text, generalized here from LightRAG to HippoRAG since both are decomposition increments the same falsifier governs). Until that run lands inside the A/A band (or every excursion is named as a declared deviation under `§5`'s parity-not-gain rule), the index side's disposition stays exactly as `PARTS.md ## §H` already states it: `quarantined` scope, `opaque` effective depth, no artifact sharing.

**Practical consequence for the plan:** this parity run is not optional polish — it is the literal mechanism named by success criterion 1's own last clause ("index-side effective depth staying `opaque` under the taint rule until its parity is shown"). Budget a Phase-3-shaped parity task for it.

## Two Arms on One Corpus (RIG §RUN)

**The isolation rule, quoted exactly:** *"The KV is shared across arms where, and only where, `§3`'s `shared` scope admits it — under `§3`'s blast-radius rule that means effective depth `stage`... An arm containing an `opaque` node writes `quarantined` and never `shared`... its index is therefore instance-scoped and readable only by explicit pin from another wiring, never SA-1-shareable."* [docs-verified, `RIG.md ## §RUN.1`]

**Why graph and vector stores are isolated per arm, not merely KV.** Per `§RUN.1`, the per-part graph and vector *namespace* derivation rule already folds recipe identity into the namespace hash — a namespace is derived from "namespace, sub-recipe stamps (SA-2), corpus, `space_id`, producing instance... plus the arm's own SA-1 recipe identity." Two arms whose recipes are hash-identical share an artifact (`§RUN.2`'s iff rule); two arms whose recipes differ in any resolved input build separately isolated namespaces. LightRAG's recipe (`chunk-vector`/`entity-hydrate-expand`/etc. over Cozo+Faiss with LightRAG's own entity/relation ontology) and HippoRAG's recipe (`chunk-embed`/`openie`/`entity-fact-embed`/etc. over its own OpenIE-derived fact/entity ontology, plus an in-process `igraph.Graph`) share **no resolved input at all** — the exact structural relationship `RIG.md ## §RUN.2`'s own worked pair (`VT-1` vs. `GR-1`) already states as the norm for two unrelated recipes: **zero artifact overlap, two full index costs.**

**How this lands on the existing storage/factory layer — verified this session, not designed here.** `databasise/namespaces.py`'s `derive_namespace()` [VERIFIED: read this session] already computes exactly the eight inputs `RIG §RUN.1` names (SA-1 instance hash, SA-2 chunker/extraction/embedding stamps, corpus id, `space_id`, scope) as a SHA-256 over their RFC-8785 canonicalisation. `namespace_dir()` then maps that hash to `<store_root>/<scope>-<hex>`. **No new isolation code is needed** — HippoRAG's own recipe hash simply resolves to a different directory than LightRAG's, because the SA-2 stamps genuinely differ. The one new requirement is that HippoRAG's parts pass their own recipe identity through this existing function, exactly as LightRAG's parts already do.

**"Structurally comparable outputs," made checkable.** `RIG.md ## §RUN.4` states the comparison rig aligns "a per-arm output set... on the eval bundle's own question order," and `§4`'s pooling key (`(eval_bundle@v, corpus@v, judge_instance, tier, counted_by, feed_tier)`) is what makes two arms' outputs poolable at all. Concretely: LightRAG and HippoRAG's per-arm `ScoredItem`s both carry the `§4`-frozen `{ref, kind, score, provenance, payload, metadata}` shape regardless of which recipe produced them — comparability is a *type* guarantee (both emit `ItemKind` union members over the same socket contract), not a *content* guarantee (the two arms' actual passages/scores may differ arbitrarily, which is the whole point of `architecture-comparison mode`).

## The §18 Comparison Surface (API-08 / MACH-10)

**Selectors, never internal identity, quoted exactly:** *"A consumer MUST express which modality or harness answers a query through exactly one of the following selectors, and MUST NOT name a wiring, a node id, or an instance hash to do it"* — alias, capability, harness name, or the default selector (`CONTRACT.md §18.4`). The comparison endpoint accepts N such selectors and returns a dict keyed by **the caller's own selector value**, never by any machine-internal id.

**Why a single arm returns a run, not a comparison.** `RIG.md ## §RUN.3`'s own degenerate-width rule: *"A one-arm fan-out is a valid run and never a valid comparison: `§5`'s policy computes a paired statistic across the arms under comparison, and one arm has no pair to compute one against... the rig instead returns exactly what the `run` verb of `§5`'s own five-verb ladder already returns for any single arm: a trace and a score, with no gate verdict attached."* Concretely: if API-08's endpoint is called with exactly one selector, it must return the same bare `ResponseEnvelope` shape `query()` already returns today — not a one-key comparison dict.

**What "no verdict" excludes.** The eight-verdict vocabulary (`promote`/`reject`/`inconclusive`/`insufficient-depth`/`below-floor`/`unconfirmed`/`regression-veto`/`straddle`, `§5`) belongs to the *gate*'s `check`/`preview`/`run`/`promote-next`/`promote-now` verb ladder — a promotion decision. API-08's comparison is explicitly "inspection-only (per-arm outputs, traces, scores — no verdict)" per its own requirement text, and `RIG.md ## §RUN.4` confirms: *"Comparison as inspection is always available even where adjudication is not... comparison as inspection is free — only adjudication costs"* (D-05's own survivor list). Concretely: the comparison endpoint's response never contains anything resembling `promote`/`reject`/etc.; it returns raw per-arm envelopes side by side. A later, separate call into the gate's own `check`/`preview` verbs (not built in this phase — that machinery already exists per Phase 5/prior phases' `§5` work) is where a verdict would come from, if ever requested.

**F-14's either-way record, in practice.** `MODEL-RED-TEAM.md`'s own F-14 finding: *"no wiring has run against a live seam implementation anywhere in the record... the falsifier both clauses name as the actual test has not fired, in either direction, because nothing has run."* The concrete discharge mechanic for this phase: run **one** real comparison call (LightRAG hybrid arm + HippoRAG base wiring, one query, through the actual seam code) and diff the two arms' envelope field sets. Two possible honest outcomes, both acceptable, both must be *recorded* in the phase's evidence (mirroring `PARTY-EVIDENCE.md`'s own house format from Phase 3): (a) field sets are identical → F-14 holds, record it; (b) a field genuinely differs → name the field explicitly in the record, which itself would be a `§18.2` defect requiring a repair, not merely a note. Either outcome satisfies success criterion 4 — the criterion is about **recording** the outcome, not about which outcome occurs.

**Which comparison mode governs LightRAG vs. HippoRAG.** Per `RIG.md ## §AA.4`'s own mode-determination rule ("read from the arms themselves... never from an operator flag"): LightRAG's arms are merge-patch siblings of one base wiring (`decomposition-parity mode` applies *among* LightRAG's own arms), but LightRAG-vs-HippoRAG is two **independently-registered wirings** — `architecture-comparison mode`, exactly like `RIG.md`'s own worked `VT-1`-vs-`GR-1` example. Consequences to build into the comparison path: "parity, not gain" does **not** apply (an improvement is the payoff, not a red flag); `§5`'s sixth refusal condition (`held_constant` diff exceeding the declared mutation's scope) is **trivially satisfied** since the two recipes share no resolved input to hold constant in the first place — `RIG.md ## §AA.4`'s own A6 check performs exactly this reasoning for `VT-1`/`GR-1` and it transfers directly to LightRAG/HippoRAG by the identical structural argument (two independently-registered wirings, zero shared resolved recipe input).

## F-07 Snapshot/Reset Protocol (MACH-10)

**The gap, quoted exactly:** `CONTRACT.md §14.4` point 3 states a `mutates_store`-declaring node "MUST be excluded from `§5`'s parity and determinism comparisons by an explicit refusal... unless and until a snapshot/reset protocol is defined and the node is re-verified against it." No such protocol is defined anywhere in the frozen docs. `MODEL-RED-TEAM.md`'s own F-07 finding names three roster entries carrying `mutable-store`: `CA-2` (`codebase-memory-mcp`'s `manage_adr`/`delete_project`), `MC-1` (`postgres-mcp`'s `execute_sql` in Unrestricted Mode), `CA-7` (a hypothetical memory-agent's own memory-edit node). **Only `CA-2` is actually admitted and running in this project today** (Phase 5) — `MC-1`/`CA-7` are catalogued but not built.

**What a defined protocol would concretely require on this runtime, for the one real instance.** `codebase-memory-mcp`'s own storage is confirmed self-contained SQLite at `~/.cache/codebase-memory-mcp/` [docs-verified, cited in `PARTS.md ## §X` from `05-06-SUMMARY.md`'s own admission work]. A snapshot/reset protocol for a SQLite-backed `mutable-store` component is mechanically simple: **snapshot = copy the SQLite file (plus its WAL/SHM siblings) to a side path before the comparison run; reset = restore those files after.** This is the same file-level operation `delete_project`'s own admitted mutation surface already touches (per `PARTS.md ## §X`'s mutation-surface scan: "it unlinks the project's SQLite database, WAL and SHM files outright"). No new machine primitive is required — this is a filesystem operation the adapter layer (`databasise/foreign/codebase_memory_mcp_adapter.py`) could own, mirroring the "process lifecycle... as a fixed cost" framing `§17` already gives that adapter.

**The two legitimate outcomes, presented to the owner as a checkpoint, not decided here:**
1. **Build it.** Add a snapshot/reset method to the `codebase-memory-mcp` adapter; re-verify the node under it; lift the exclusion for this one instance. Cost: one adapter method plus one re-verification test. Benefit: `codebase-memory-mcp` becomes A/B-comparable, closing goal 8's own gap for the one real roster entry that matters today.
2. **Declare permanent exclusion.** State in the record (mirroring `PARTS.md ## §X`'s own house style for a not-clean-yes finding) that `mutable-store` components stay excluded from `§5`'s comparisons indefinitely, and rely exclusively on `## §PR`'s operator-asserted promotion path for any future change to such a component. Cost: zero code. Cedes: no gate-adjudicated A/B for this capability class, ever, under the current contract.

**Recommendation:** given this project's own "product-first testing posture" (owner defers eval/QC to point of need, per this session's memory context) and that the only real instance (`codebase-memory-mcp`) is admitted *whole-engine opaque* and excluded from the default selector anyway, **option 2 (declare permanent, cheaply) is the lower-risk default** unless the owner specifically wants `codebase-memory-mcp`'s `manage_adr`/`delete_project` behavior A/B-testable. This is exactly the kind of decision `## §PR`'s scope was built to leave open — flag it as a `checkpoint:human-verify` in the plan rather than deciding it here.

## Eval Bundle + A/A Calibration (MACH-02 / MACH-03, Falsifier 5)

**Bundle structure, quoted exactly from the frozen contract** — an eval bundle MUST carry: questions, gold answers, a judge instance, a judge prompt hash, a corpus snapshot hash, and the determinism/concurrency setting it was calibrated under; split into `dev`/`holdout`/`sealed`; carrying **both** target families (`CONTRACT.md §10`, `RIG.md ## §EV.1`/`## §EV.2`). Both target families, concretely:

| Target family | What it measures | `§4` evidence tier | Cost (per `§CM.2`) |
|---|---|---|---|
| Gold-passage (retrieval-side) | recall@k / nDCG against gold passages | `T1` and above | ~1-5% of the full per-decision bill — no generator, no judge |
| Answer-level | end-to-end judged correctness | `T0` | ~5.1-5.2M tokens per adjudicated decision (see derivation below) |

**Versioning rule.** A new `bundle@v` is minted, never edited in place, on: a question added/removed, a gold answer corrected, the judge instance/prompt hash changing, the corpus snapshot hash changing, or the determinism/concurrency setting changing (`RIG.md ## §EV.1`). `sealed` stays untouched until a real promotion decision needs it — opening it mints a new version.

**The A/A calibration procedure, exact mechanics — quoted, not paraphrased:** *"one A/A run at n questions produces n paired per-question differences between the two runs of the same arm under one fixed `(bundle@v, tier, metric)` triple and one fixed concurrency/determinism setting — the arm is run against itself, twice... Bootstrap-resample those n paired differences — with replacement, the ordinary nonparametric bootstrap — to build the null distribution, and take that resampled distribution's p95 as the calibrated floor."* [docs-verified, `RIG.md ## §AA.1`]

**The floor-boundary rule (easy to get backwards):** a measured delta landing *exactly* on the p95 floor does **not** promote — the observed statistic must strictly exceed the floor (`RIG.md ## §AA.1`).

**Cache-bypass is a hard precondition, not an optimization:** *"A genuine A/A calibration run MUST bypass the response cache... a cache-hit-heavy calibration run measures a near-zero variance... a promotion floor derived from that near-zero null is too permissive."* [docs-verified, `RIG.md ## §AA.2`] Concretely: the A/A harness must construct its two same-arm runs with the response-cache disabled (or a fresh cache namespace per run), and the run's `cache_hit` trace field must be recorded and checked before the resulting null is trusted — *"a null whose bypass status is unknown is not usable as a floor."*

**T0 vs. T1, and what "materially narrower" means here.** `T0`/`T1` in success criterion 6 are `§4`'s evidence tiers, not test-suite tiers: `T0` = answer-level (judged), `T1` = gold-passage/retrieval-level. `RIG.md ## §EV.3` point 5 explains *why* `T1`'s null should be narrower: *"judge-noise compounding: `SD_effective = sqrt(SD_true² + SD_judge_noise²)`, with judge self-disagreement at ~5-15%... A fixed true effect size therefore produces a smaller effective d for a judge-scored answer-level target than for a judge-free retrieval-side target at the same n."* **No document anywhere quantifies "materially" as a specific ratio or percentage** — this is a genuine open number the owner or planner must pick (e.g., "T1's calibrated p95 floor is at least 30% narrower, in absolute score units, than T0's"). Flagged as `[ASSUMED]`/Open Question below; do not let the plan silently invent a number without a checkpoint.

**Bootstrap replicate count `B`.** RIG.md never names a specific replicate count for the resampling step. Standard statistical practice for a stable empirical-percentile bootstrap estimate is `B ≥ 2,000` [ASSUMED — general statistical convention, not sourced from this project's own docs]; recommend defaulting to `B = 2,000` (or `scipy.stats.bootstrap`'s own default `n_resamples=9999` if performance is not a constraint — resampling itself is CPU-only and cheap relative to the LLM-call cost that dominates this procedure) and flag the choice for owner confirmation.

**How much compute a single calibration costs — shown as arithmetic on `§CM.2`'s own cited anchors, not a new measurement.** `§CM.2`'s own worked figure — "~5.1-5.2M tokens" — is priced for "n=40, **2 arms, 2 repeats**" (160 total query executions: 40 questions × 2 arms × 2 repeats). An A/A calibration run is structurally "the same arm, twice" at n questions — exactly **half** the query-execution count of that figure (80 executions at n=40, vs. 160). Scaling proportionally:

| Tier | Full 2-arm/2-repeat figure (`§CM.2`) | One A/A run (half the query count) | Disposition |
|---|---|---|---|
| Retrieval-side (`T1`) | ~1-5% of ~5.1-5.2M ≈ 51k-260k tokens | ~26k-130k tokens | Affordable, confirmed — negligible |
| Answer-level (`T0`) | ~5.1-5.2M tokens | ~2.55-2.6M tokens | Affordable only under `§F3.2`'s opt-in, rate-limited, escalated-survivors-only posture |

This arithmetic is `[inference]` — a linear scaling of `§CM.2`'s own cited, tagged anchors, not a new benchmark run — and should be re-verified once a real corpus and real queries exist (the same residual-inputs caveat `§CM.3` already names for the underlying anchors: A2, the LLM output-size band, is the dominant remaining uncertainty, at ±14-38% on the 2x-sensitivity check `§CM.3` already ran).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2+ (`databasise/pyproject.toml`'s `[dependency-groups] dev`) |
| Config file | `databasise/pyproject.toml ## [tool.pytest.ini_options]` — `asyncio_mode="auto"`, `testpaths=["tests"]` |
| Quick run command | `cd databasise && uv run pytest -q tests/parts_core/hipporag/` (once that directory exists) |
| Full suite command | `cd databasise && uv run pytest -q` (matches `.planning/config.json`'s `workflow.test_command`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODAL-04 | Each of the 13 HippoRAG parts registers with correct `effects[]`/`kind`/`structural_depth` | unit | `pytest tests/parts_core/hipporag/test_registration.py -x` | ❌ Wave 0 |
| MODAL-04 | `ppr` node's PPR call reproduces upstream `hipporag`'s scores within tolerance on a small fixture graph | integration | `pytest tests/parts_core/hipporag/test_ppr_parity.py -x` | ❌ Wave 0 |
| MODAL-04 | Bulk-export produces a valid `igraph.Graph` from real Cozo data (round-trip: write via `graph-augment-persist`, read via `ppr`) | integration | `pytest tests/stores/test_graph_bulk_export.py -x` | ❌ Wave 0 |
| MODAL-05 | LightRAG's and HippoRAG's namespaces resolve to different directories on the same corpus | unit | `pytest tests/test_namespace_isolation.py -x` | ❌ Wave 0 |
| MODAL-05 | Same query against both arms produces structurally valid (schema-conformant) `ScoredItem` output on both sides | integration | `pytest tests/seam/test_cross_modality_run.py -x` | ❌ Wave 0 |
| API-08 | Comparison request with 2 selectors returns dict keyed by those exact selector values, no internal id anywhere in the response | unit | `pytest tests/seam/test_compare.py::test_keyed_by_selector -x` | ❌ Wave 0 |
| API-08 | Comparison request with 1 selector returns a bare envelope (a run), not a comparison dict | unit | `pytest tests/seam/test_compare.py::test_single_selector_is_a_run -x` | ❌ Wave 0 |
| API-08 | Comparison response contains no verdict field/value from `§5`'s eight-verdict vocabulary | unit | `pytest tests/seam/test_compare.py::test_no_verdict_leaks -x` | ❌ Wave 0 |
| MACH-10 | F-07 decision recorded (protocol defined + tested, OR exclusion documented) | manual-only | N/A — evidence-document review, per `PARTS.md`'s own house format | — |
| MACH-02 | Eval bundle round-trips dev/holdout/sealed content and mints a new version on any of the five invalidating changes | unit | `pytest tests/eval/test_bundle_versioning.py -x` | ❌ Wave 0 |
| MACH-03 | A/A calibration on a fixture arm produces a bootstrap null; re-running with `cache_hit=True` injected is refused as an unusable floor | unit | `pytest tests/eval/test_calibration.py -x` | ❌ Wave 0 |
| MACH-03 | T1's calibrated floor is narrower than T0's on the same fixture (owner-confirmed threshold) | manual-only, owner-confirmed threshold required first | N/A — depends on the "materially narrower" number the owner picks | — |

### Sampling Rate

- **Per task commit:** `cd databasise && uv run pytest -q tests/<new-directory>/`
- **Per wave merge:** `cd databasise && uv run pytest -q` (full suite — 745 tests passed at Phase 5's close per `05-LEARNINGS.md`; expect this count to grow substantially this phase)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `databasise/stores/graph.py`'s `CozoGraphStore.export_to_igraph()` (or equivalently-named bulk-export method) — no test infrastructure exists for it yet
- [ ] `databasise/stores/vector.py`'s `FaissVectorStore.self_knn()`/`score_all()` methods
- [ ] The `join` structural-kind dispatch in the runner (currently an unconsumed declared skeleton per `schema.py`'s own docstring)
- [ ] `tests/parts_core/hipporag/` directory and its `conftest.py`/fixtures
- [ ] `tests/eval/` directory — genuinely greenfield, no prior eval-bundle or calibration test infrastructure exists anywhere in this codebase
- [ ] An isolated-venv harness for the real upstream `hipporag` package (parity oracle) — needs its own `conftest.py`-level skip-if-absent guard, mirroring `05-06-SUMMARY.md`'s "optional SDK imported lazily" pattern for the `mcp` extra

## Common Pitfalls

### Pitfall 1: `python-igraph` vs. `igraph` package-name trap
**What goes wrong:** `pip install python-igraph` still works (PyPI keeps it installable for compatibility) but its own PyPI page literally says "(legacy package)" — a `pyproject.toml` pin naming `python-igraph` looks correct to anyone who has used this library before 2024 and would pass any registry-existence check, but is the wrong name to depend on going forward.
**Why it happens:** The upstream project renamed its PyPI distribution from `python-igraph` to `igraph` at some point before the current `1.0.0` release; both names still resolve, so nothing fails loudly.
**How to avoid:** Pin `igraph`, not `python-igraph`, in `databasise/pyproject.toml`. Note the real upstream `hipporag` package itself still pins the *old* name (`python_igraph==0.11.8`) in its own `install_requires` — that is fine and expected for the isolated parity-harness venv (matching upstream's own pin exactly), but must not leak into `databasise`'s own dependency list.
**Warning signs:** A `uv.lock` entry reading `python-igraph` instead of `igraph`.

### Pitfall 2: Trusting the pointwise `FaissVectorStore.query()`/`CozoGraphStore` methods to already support what HippoRAG needs
**What goes wrong:** Assuming `synonymy-edges`' self-KNN or `fact-score`'s exhaustive `score_all` can be built by calling the *existing* `query(vector, top_k=...)` method in a loop.
**Why it happens:** The existing methods look superficially sufficient (they do return scored results), and nothing fails at import time — it just silently becomes the forbidden `O(N²)` pointwise emulation `§14.2` explicitly refuses.
**How to avoid:** Add genuinely new methods (`self_knn`, `score_all`) rather than composing the existing `query` in a loop.
**Warning signs:** A profiling run showing `query()` called once per entity during index-time synonymy-edge construction.

### Pitfall 3: Treating `reset-vector-join` as "just another Part" without building the `join` dispatch first
**What goes wrong:** Writing `reset_vector_join.py`'s `body` function and registering it as a `Part`, discovering only at run time that the scheduler has no dispatch branch for `kind="join"`.
**Why it happens:** `schema.py`'s `NodeKind` union already exists and looks "done"; its own docstring explicitly warns this is a declared skeleton, not a consumed dispatch — easy to miss on a skim.
**How to avoid:** Confirm the runner's dispatch logic branches on `join`/`fanout`/etc. before writing any HippoRAG query-side part; if it does not, build that dispatch as its own Wave-0 task.
**Warning signs:** `NotImplementedError` or a silent fallthrough to treating `join` as a plain `Part` at run time.

### Pitfall 4: Calibrating an A/A null against a warm cache
**What goes wrong:** Running the "same arm, twice" A/A procedure without disabling the response cache, producing a near-zero-width null and an artificially permissive promotion floor.
**Why it happens:** LightRAG's own response cache (`handle_cache`) is keyed by content hash and will happily serve the second identical run from cache — the run *completes successfully* and *looks* like a clean calibration.
**How to avoid:** Force cache-bypass (or a fresh cache namespace) for both A/A runs, and check the `cache_hit` trace field before trusting the resulting null — `RIG.md ## §AA.2` states this as a hard precondition, not a nice-to-have.
**Warning signs:** A calibrated null with suspiciously tiny variance, or a promotion that clears the floor on the very first real comparison.

### Pitfall 5: Double-correcting (or forgetting) the batch-width floor correction
**What goes wrong:** Applying `§5`'s existing epoch-level FDR correction and RIG `## §AA.3`'s new batch-width correction as if they were the same thing (either skipping one, or stacking them uncoordinated).
**Why it happens:** Both are "multiple-comparisons corrections" and sound like duplicates on a skim.
**How to avoid:** They are nested, not competing: the batch-width correction (BH-FDR at the bulk-screening tier, Dunnett/Holm at the escalated-survivor tier) narrows N-candidates-in-a-batch down to at most one decision per batch; the epoch-level correction then runs across the resulting per-batch decisions. Apply both, in that order, on distinct populations.
**Warning signs:** A promotion rate that looks too permissive (missing the batch-width layer) or a bundle that never promotes anything even on a genuine effect (double-corrected).

### Pitfall 6: Letting the comparison endpoint leak `provenance` or any node-position identity
**What goes wrong:** Assembling the comparison response by reusing `ScoredItem.provenance` (a set of contributing *node positions*) directly in the returned payload.
**Why it happens:** `provenance` is a real, useful field on the internal `ScoredItem` type, and it is easy to forget it is explicitly redacted at the seam (`CONTRACT.md §4`'s own "reconciling with §18.2's closed envelope" clause: *"`provenance` is redacted at the seam and reachable only through the envelope's existing trace reference — never returned as a field of its own"*).
**How to avoid:** Reuse the existing `§18.2` envelope-assembly code path per arm (Pattern 4 above) rather than hand-assembling a new response shape for the comparison case — the existing path already does this redaction correctly for the single-arm case.
**Warning signs:** A comparison response JSON containing a `provenance` key with node-id-shaped strings inside it.

## Code Examples

### A HippoRAG Part, in this codebase's own established shape

```python
# Source: verified this session against databasise/parts/schema.py (Part/NodeContext dataclasses)
# and databasise/parts_core/lightrag/chunk_vector.py (the existing convention this mirrors).
from __future__ import annotations
from typing import Any
from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "hipporag/fact-scorer@0.1.0"


async def _fact_score_body(ctx: NodeContext) -> dict[str, Any]:
    query_vec = ctx.inputs["fact-embed-query"]["vector"]
    fact_store = ctx.stores["vector"].select("facts")
    # §14.2 score_all: exhaustive dense dot product against every fact — never top-k.
    scored = await fact_store.score_all(query_vec)
    return {"items": scored}


HIPPORAG_FACT_SCORER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="retriever",
    structural_depth="opaque",  # per this session's "Taint rule" finding — stays opaque until parity is shown
    effects=["reads_vector"],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_fact_score_body,
)
```

### The real upstream `run_ppr` call this session verified live

```python
# Source: raw.githubusercontent.com/OSU-NLP-Group/HippoRAG/main/src/hipporag/HippoRAG.py,
# `run_ppr` method — fetched and read directly this session [VERIFIED].
def run_ppr(self, reset_prob, damping=0.5):
    if damping is None:
        damping = 0.5
    reset_prob = np.where(np.isnan(reset_prob) | (reset_prob < 0), 0, reset_prob)
    pagerank_scores = self.graph.personalized_pagerank(
        vertices=range(len(self.node_name_to_vertex_idx)),
        damping=damping,
        directed=False,
        weights="weight",
        reset=reset_prob,
        implementation="prpack",
    )
    doc_scores = np.array([pagerank_scores[idx] for idx in self.passage_node_idxs])
    sorted_doc_ids = np.argsort(doc_scores)[::-1]
    sorted_doc_scores = doc_scores[sorted_doc_ids.tolist()]
    return sorted_doc_ids, sorted_doc_scores
```

### A/A calibration's bootstrap step, using `scipy.stats.bootstrap`

```python
# Source: this session's synthesis of RIG.md ## §AA.1's procedure text against
# scipy.stats.bootstrap's documented paired=True/method="percentile" support
# [CITED: docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html].
import numpy as np
from scipy.stats import bootstrap


def calibrate_aa_floor(paired_diffs: np.ndarray, n_resamples: int = 2000) -> float:
    """RIG §AA.1: bootstrap-resample n paired per-question differences (same arm, run twice,
    cache-bypassed per §AA.2), take the resampled distribution's p95 as the calibrated floor.
    """
    res = bootstrap(
        (paired_diffs,),
        statistic=np.mean,
        n_resamples=n_resamples,
        method="percentile",
        confidence_level=0.90,  # two-sided 90% CI's upper bound == one-sided p95
    )
    return res.confidence_interval.high  # the calibrated p95 floor
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `python-igraph` as the PyPI distribution name | `igraph` (same project, same maintainers) | Sometime before the current `1.0.0` release (2025-10-23) | Any pin written before this rename needs updating; both names still resolve, so nothing breaks loudly if missed — see Pitfall 1 |

**Deprecated/outdated:**
- `.planning/research/STACK.md`'s LanceDB recommendation (lines 26, 69, 85, 97, 119) — superseded by the corrected real defaults (Cozo + Faiss), per `ROADMAP.md`'s own inline amendment and `.claude/CLAUDE.md`. Do not consult this file for vector-store guidance in this phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `igraph` version range `>=0.11,<2.0` is safe for databasise's own use (independent of upstream `hipporag`'s exact `0.11.8` pin) | Standard Stack | Low — the PPR call signature (`personalized_pagerank`, `implementation="prpack"`) is confirmed stable across the `0.9.x`→`1.0.0` line via PyPI release history; a major-version API break is the only real risk, mitigated by pinning `<2.0` |
| A2 | `numpy`/`scipy` version ranges carried from `v1/pyproject.toml` are still current and compatible with Python 3.11+ (`databasise`'s own floor) | Standard Stack | Low — both are long-lived, backward-compatible scientific packages; worth a live `pip index versions` check before locking |
| A3 | Bootstrap replicate count `B=2000` (or `scipy`'s own default `n_resamples=9999`) is an adequate default | Eval bundle + A/A calibration | Medium — an under-replicated bootstrap produces a noisy p95 estimate, which could make the promotion floor itself unstable run-to-run; RIG.md never specifies a number, so this needs explicit owner sign-off |
| A4 | "Materially narrower" (success criterion 6 / Falsifier 5) has no quantified threshold anywhere in the frozen docs | Eval bundle + A/A calibration | High if left undecided — the gate cannot mechanically check an unquantified criterion; must become a locked number before MACH-03 can be marked complete |
| A5 | The snapshot/reset protocol for `codebase-memory-mcp`'s `mutable-store` capability can be a simple file-copy-and-restore of its SQLite database/WAL/SHM files | F-07 snapshot/reset protocol | Medium — assumes no other process holds an open write handle across the snapshot window; a real implementation needs a brief write-quiesce, not verified against the adapter's actual concurrency model this session |
| A6 | The "showing parity" mechanism for HippoRAG's index side is a Phase-3-shaped comparison against the real upstream `hipporag` package, not some other measurement | Taint rule section | Medium — this is this session's own synthesis ([inference]), not stated verbatim in any frozen doc; the planner should confirm this reading matches the owner's intent before committing a whole task to building the isolated-venv parity harness |
| A7 | PARTS.md §H's HippoRAG.py line-number citations (e.g. `:1709-1748` for `run_ppr`) were correct against whatever commit that research session pinned, and the drift to `~2166-2205` on current `main` is upstream's own commit history moving, not an error in PARTS.md | Code Examples / Pattern 3 | Low — the *call shape* is confirmed identical either way; only exact line numbers drifted |

**If this table is empty:** N/A — table is populated above.

## Open Questions

1. **What number does "T1's null width materially narrower than T0's" resolve to?**
   - What we know: `RIG.md ## §EV.3` explains *why* T1 should be narrower (judge-noise compounding widens T0's effective SD) but never states a ratio or threshold.
   - What's unclear: whether "materially" means 2x, 30%, one full evidence-tier's worth of MDE, or something else.
   - Recommendation: raise as a `checkpoint:human-verify` in the plan before MACH-03's completion criterion can be mechanically checked; default proposal if the owner has no preference: T1's calibrated p95 floor (in the same score units) is at most half of T0's.

2. **Does F-07 get built or permanently excluded?**
   - What we know: only one real `mutable-store` instance exists in this project today (`codebase-memory-mcp`), and it is already excluded from the default selector as a whole-engine opaque node.
   - What's unclear: whether the owner wants `manage_adr`/`delete_project` A/B-testable at all, ever.
   - Recommendation: present both options (build vs. declare-permanent) as a checkpoint; this research recommends declare-permanent as the lower-cost default (see F-07 section above) but does not decide it.

3. **Is the real upstream `hipporag` package's alpha status (`2.0.0a4`/`a5`) acceptable as a parity oracle?**
   - What we know: the package is pre-1.0, from the paper's own authors, actively maintained (NeurIPS'24 paper, GitHub org still committing).
   - What's unclear: whether a future upstream release could change `run_ppr`'s exact call shape before this phase's parity run is complete, invalidating the comparison mid-flight.
   - Recommendation: pin the exact commit SHA (not just the PyPI alpha version) for the parity harness's isolated venv, mirroring the existing pattern of pinning `v1`'s LightRAG fork by exact commit for the same reason.

4. **Should `igraph`/`numpy`/`scipy` be added to `databasise`'s core `dependencies` list, or gated behind a new `[project.optional-dependencies]` extra (e.g. `hipporag`)?**
   - What we know: `EMBED-01`/`EMBED-02` and the existing `rest`/`mcp` extras establish precedent for gating transport-layer additions behind opt-in extras; but `igraph`/`numpy` are needed for a *core modality* to run at all (unlike `mcp`, which gates a transport).
   - What's unclear: whether HippoRAG's status as "the second modality, not yet the default" argues for an extra, or whether MODAL-04's "no opaque core left behind" framing argues it should ship in core.
   - Recommendation: match the existing pattern used for LightRAG's own core dependencies (`pycozo`, `faiss-cpu` are core, unconditional) — HippoRAG is a first-class modality per this milestone's own core value statement ("LightRAG and HippoRAG 2 both live behind one unchanging §18 envelope"), so `igraph`/`numpy`/`scipy` belong in core `dependencies`, not an extra. Flagged as a recommendation, not a locked decision.

## Sources

### Primary (HIGH confidence)
- `docs/system-model/CONTRACT.md` — §0, §1, §2, §3 (Ruling R-1), §4, §5, §6, §14 (§14.2, §14.3, §14.4), §17, §18, §19 — read in full this session
- `docs/system-model/RIG.md` — §RUN, §TR, §CM, §EV, §F3, §PR, §AA, §LC, §R — read in full this session
- `docs/system-model/PARTS.md ## §H` (HippoRAG 2 node table) and `## §X` (codebase-memory-mcp, cited for F-07's real instance) — read in full this session
- `docs/system-model/MODEL-RED-TEAM.md` F-07 through F-15 — read in full this session
- `docs/system-model/wirings/hipporag-base.json` — read in full this session
- `databasise/namespaces.py`, `databasise/stores/graph.py`, `databasise/stores/vector.py`, `databasise/parts/schema.py`, `databasise/parts_core/lightrag/chunk_vector.py`, `databasise/parts/admission.py`, `databasise/seam/engine.py`, `databasise/seam/query.py`, `databasise/wirings/lightrag/base.json` — read this session
- `github.com/OSU-NLP-Group/HippoRAG/src/hipporag/HippoRAG.py` — fetched live this session via `raw.githubusercontent.com` (`run_ppr`, `add_synonymy_edges`, `save_igraph`, `initialize_graph`, `graph_search_with_fact_entities`)
- `github.com/OSU-NLP-Group/HippoRAG/pyproject.toml`, `setup.py` — fetched live this session
- `pypi.org/pypi/igraph/json`, `pypi.org/pypi/python-igraph/json`, `pypi.org/pypi/hipporag/json` — fetched live this session

### Secondary (MEDIUM confidence)
- `python.igraph.org`'s personalized-PageRank tutorial and API reference (WebSearch-surfaced, cross-checked against the live `HippoRAG.py` fetch's actual call — the two agree)
- `docs.scipy.org`'s `scipy.stats.bootstrap` reference (WebSearch-surfaced; `paired=True`/`method="percentile"` support confirmed, exact default `n_resamples` not independently re-verified against the current release)

### Tertiary (LOW confidence)
- Bootstrap replicate count convention (`B≥2000`) — general statistical practice, not sourced from any project document; flagged in Assumptions Log

## Metadata

**Confidence breakdown:**
- Frozen contract text (HippoRAG node decomposition, comparison surface, eval-bundle/A-A procedure): HIGH — directly quoted from ratified, verbatim-mirrored design docs, cross-checked against this session's own live reads of the actual codebase and the real upstream `hipporag` package
- Build mechanics (new store methods, join dispatch, comparison endpoint shape): HIGH for "what must exist," MEDIUM for "exact function signatures" (these are this session's own reasonable extrapolations from existing code conventions, not yet-written code)
- Statistical parameters (bootstrap `B`, "materially narrower" threshold): LOW/ASSUMED — genuinely unspecified anywhere in the project record; flagged for owner checkpoint, not guessed silently

**Research date:** 2026-09-09
**Valid until:** 30 days for the frozen-contract portions (stable, verbatim, will not change without a project-level amendment); 7 days for the live-fetched upstream `hipporag`/`igraph` package facts (an alpha-status package and a library mid-rename can both move faster than 30 days)
