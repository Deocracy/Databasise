# Phase 1: Machine Core - Research

**Researched:** 2026-08-30
**Domain:** Embeddable wiring-graph execution machine (validator + runner/scheduler + identity/keying + embedded storage) implementing the §H1 "must-decide-itself" fence of a frozen fitting contract
**Confidence:** HIGH (frozen contract text and v1 source are read-and-quoted this session; runner-mechanism choices are MEDIUM — library recommendations, not contract-frozen)

## Summary

Phase 1 has almost no open design questions left to research — `01-CONTEXT.md` already carries fourteen locked decisions (D-01 through D-14) reached through `/gsd-discuss-phase`, each citing the frozen `CONTRACT.md`/`RIG.md` clause it implements. This document's job is narrower than usual: verify the technical claims those decisions rest on against primary sources (the contract text itself, the v1 source files being ported, and package registries), surface the two places where a v1 requirement document is now known to be wrong, and give the planner a build-ready architecture skeleton with verified library versions.

The stack is settled and requires no library research: Python 3.10+ (uv already has 3.12.13 installed locally, matching v1's pin), `pycozo[embedded]==0.7.6` for the graph store, `faiss-cpu` for the vector store, `sqlite3` (stdlib) for KV/lexical/registry/ledger, `rfc8785` for RFC 8785 JSON canonicalisation, and `graphlib.TopologicalSorter` + `asyncio.TaskGroup` (both stdlib, Python 3.11+) for the runner. Every one of these except `rfc8785` is either already a v1 dependency or stdlib. The two genuinely new pieces of engineering are the SCC-condensation depth computation (Tarjan cycle-safe taint-rule min-reduce — no stdlib implementation, ~30 lines) and the per-namespace store-directory layout (D-07).

**Primary recommendation:** Build in the order `identity/keying → part registry → validator (Falsifier 2's deliverable) → minimal in-process-only runner → artifact registry + ledger`, per the existing `.planning/research/ARCHITECTURE.md` build order — it is already aligned with D-01 through D-14 and needs no revision. The two corrections this research surfaces (EMBED-01 names the wrong vector store; MACH-05's definition of done is missing the run-record fields D-10 requires) must be applied to `REQUIREMENTS.md` before or during planning, per CONTEXT.md's own Deferred section.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Wiring parse + type validation | API/Backend (embedded library) | — | `NodeKind` tagged-sum parse is pure in-process compute, no I/O; CONTRACT §2 |
| Cycle detection + depth computation | API/Backend (embedded library) | — | Load-time-only, computed once per run over the load-frozen snapshot; CONTRACT §3, §11 |
| Runner/scheduler (structured concurrency) | API/Backend (embedded library) | — | In-process orchestration; D-08 restricts Phase 1 to `in-process` execution_mode only |
| Budget metering | API/Backend (embedded library) | — | Metered only at each node's declared boundary per D-09/CONTRACT §9; never a process-wide gate |
| Graph store (Cozo) | Database/Storage | — | Embedded RocksDB-backed process, no server; D-05 |
| Vector store (Faiss) | Database/Storage | — | Embedded, in-process index; D-05 |
| KV/lexical/registry/ledger (SQLite) | Database/Storage | — | Embedded, stdlib, zero new dependency; D-06 |
| Blob store (content-addressed filesystem) | Database/Storage | — | Git-object-store-style fan-out directory layout; D-06 |
| Identity/keying (`config_hash`, instance tuple) | API/Backend (embedded library) | Database/Storage | Pure function producing the key every store layer reads by; CONTRACT §1 |
| REST + MCP seam (§18) | *(out of Phase 1 scope — Phase 4)* | — | EMBED-02/API-* are Phase 4/5; noted only to keep this map from implying Phase 1 builds it |

There is no browser/client or CDN/static tier in this phase — Phase 1 delivers an embeddable Python library with no UI surface (`EMBED-01`'s own success criterion 1), so every capability above resolves to the API/Backend or Database/Storage tier by construction. This absence is itself worth stating explicitly for the plan-checker: a task that tries to place any Phase 1 capability in a client or CDN tier is a misassignment.

## User Constraints

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Depth machinery**

- **D-01:** Phase 1 builds the **full depth computation as a library** — Tarjan SCC condensation, taint min-reduce over `{opaque, evidence, stage}`, and `effects[] → execution_mode` derivation. Phase 2 adds §19.10's boundary enumeration, the three named wirings, and the Falsifier 2 evidence run. Phase 1 owns the mechanism; Phase 2 owns the proof.
- **D-02:** The blast-radius rule is enforced at **both** the validator (load time) and the artifact-write path (before writing). Depth is stamped data by run time so the second check is nearly free, and no path reaching the artifact registry — test helper, repair script, Phase 5's opaque admission — can bypass the rule. — *Reversibility: reversible — two call sites, no stored state.*
- **D-03:** Spike 005's `taint.py` case table is **ported as a named conformance set**, restated in frozen contract vocabulary. Three prototype divergences must be repaired in the port, not carried: (1) `writes_quarantined` is not an `effects[]` member — scope is a property of the artifact write; (2) `writes_artifact` must be distinguished from the transient `writes_kv`/`writes_vector`/`writes_graph`/`writes_lexical` members, which sit outside the blast-radius rule by design (PARTS-04 D1); (3) case 3 becomes an ordinary expected-refusal — the prototype's harness exempts any case whose title starts with `"3."` from its failure count.
- **D-04:** Phase 1 ships **executable reference parts** under `core/` (a passthrough, a deterministic fake retriever, a fake LLM caller declaring `calls_llm`, a `fixpoint` body) to exercise the runner, budget metering, and store access for real — **plus declaration-only registry entries** (schema + `effects[]`, no body) for the three named Falsifier-2 wirings, so Phase 2 has a registry to compute over without waiting on Phase 3.

**Stores**

- **D-05:** **Cozo owns graph, Faiss owns vector.** Owner decision, locked. These are the fork's actual defaults (`v1/lightrag/lightrag.py:275-284`, `v1/lightrag/api/config.py:64-68`). **EMBED-01 and ROADMAP Phase 1 criterion 1 currently say LanceDB and must be amended** to read Cozo + Faiss + SQLite. See Deferred for the provenance of that error. — *Reversibility: one-way — the vector store is the Phase 3 parity baseline; swapping it while decomposing the query side confounds the parity measurement (PITFALLS 8), so a later change means re-running parity, not editing a config value.*
- **D-06:** **SQLite (stdlib) owns KV, lexical via FTS5, the artifact-registry index, and the append-only ledger.** Filesystem owns blob, content-addressed in a git-style fan-out layout. Zero new dependency. Note: `lexical` and `blob` are **new primitives** — v1 has neither, so there is no incumbent to preserve or port.
- **D-07:** **One store directory per namespace.** Each arm/namespace gets its own Cozo database file and its own Faiss index directory, under a path derived from SA-1 recipe identity. Success criterion 4's "visibly separate after a run" becomes verifiable with `ls`, and GC is deleting a directory — which matches the `quarantined` scope's "GC'd with the instance" rule directly. — *Reversibility: costly — the layout is baked into every namespace-derivation call site and into artifact-registry rows written under it; changing it later means a migration of on-disk state.*

**Runner and concurrency (the §H1 fence)**

- **D-08:** The runner implements **`in-process` only**. `subprocess`, `confined-unit`, and `long-lived-service` return an **explicit refusal naming the unimplemented placement**. The derivation from `effects[]` is still computed and stamped — only the hosting is unbuilt. Placement is earned in Phase 5 when real opaque-node admission forces it.
- **D-09:** **Intra-node concurrency is bounded by a per-node semaphore owned by the runner, whose size is declared in that node's config and therefore enters its `config_hash`** under §1. This is the §H1 handover answered. It goes beyond CONTRACT §9's V-7 minimum deliberately: RIG §AA.1 makes the concurrency setting part of the A/A null's identity and forbids pooling two runs under different settings, so folding the cap into `config_hash` makes that automatic rather than something a later step must remember to record. — *Reversibility: one-way — the cap is an input to `config_hash`, so changing what feeds it changes every instance identity computed under the old rule and invalidates in-flight A/B baselines. §1 names this exact failure ("re-hashing byte-identical input after a defaulted-option change has already destroyed in-flight A/B baselines").*
- **D-10:** The Phase 1 runner **stamps the full run-record field set the gate later reads**: the declared determinism/concurrency setting, per-node `cache_hit`, `arm_execution_order`, `realised_budget_share`, and which data guards fired. Without these, §5 can never evaluate refusal conditions 8, 10 or 11 — and a confounded comparison then returns a normal verdict, which the contract calls worse than a refusal because it looks settled rather than unsettled. **This is not currently written into MACH-05's definition of done and should be.**
- **D-11:** The runner must **not** import `v1/lightrag/kg/shared_storage.py`'s `UnifiedLock` or any module-level singleton (`_manager`, `_storage_instance`, `_global_concurrency_limits`). A process-wide concurrency cap is rejected explicitly: one arm's fan-out would throttle an unrelated arm beside it, contaminating Phase 6's side-by-side comparison.

**Identity and package**

- **D-12:** The environment hash folded into `config_hash` is a **machine-computed resolved-closure digest** — distribution names, versions and wheel hashes read from `importlib.metadata` at runtime, plus Python version and platform. Hash what is *installed*, never what a lockfile *declares*. §1 names the declared-closure alternative as "the exact Feast skew the environment hash exists to kill". Nix is not consulted: spike 004 holds that Nix is substrate-only and store paths are never identity. — *Reversibility: one-way — same reason as D-09; the digest is an input to every `config_hash`.*
- **D-13:** Parts are resolved through an **explicit in-code registry** — a dict mapping `name@version` to a Part. Every part in this milestone is authored by this project, so `entry_points` buys extensibility nothing needs yet while costing an editable install before any test can see a part. `entry_points` can be added later without changing the part interface.
- **D-14:** The v2 engine lives in a **new top-level `databasise/` package**, beside `v1/`. **Nothing in `databasise/` imports from `v1/`** — code moves by deliberate copy, with attribution recorded in the component registry's `upstream_ref` field per CONTRACT §7. This is structural, not stylistic: it makes PITFALLS 1 and 7 impossible by construction, because there is no import path to v1's singletons. It also makes success criterion 1 trivially true — the new package simply has no server backends, no bundled React, and no Docker. — *Reversibility: costly — every ported module's import graph assumes it.*

### Claude's Discretion

- Structured-concurrency mechanism inside the runner (`graphlib.TopologicalSorter` for readiness plus `asyncio.TaskGroup` for each ready batch is the researched default; no orchestrator).
- RFC 8785 canonicalisation library choice (`rfc8785` is the researched default).
- Blob-store fan-out directory depth and the artifact-registry table schema.
- Reference-part internals, beyond the four roles named in D-04.
- Test structure, fixture layout, and naming, following v1's existing conventions.

### Deferred Ideas (OUT OF SCOPE)

**Requirement corrections needed before or during planning**

- **EMBED-01 and ROADMAP Phase 1 criterion 1 name LanceDB.** Provenance of the error: `.planning/research/STACK.md:26` describes the incumbent as a "faiss-cpu + nano-vectordb pairing" — which is not the default — and recommends LanceDB on that basis; the requirement adopted it. Neither Cozo, Faiss, LanceDB nor SQLite is named by the frozen model, which only ever says "the machine's Graph/Vector/KV client". Engine choice is a build decision, not frozen input. Amend to Cozo + Faiss + SQLite.
- **MACH-05's definition of done does not include the run-record fields** D-10 requires.

**Discovered capability gaps — belong to other phases**

- The fact layer (`/wiki/resolve` with `as_of`, `/wiki/unresolved`, `/wiki/unplaced`, vocab routes, claims with provenance and trust tiers). Lost; reconstructed in `.planning/RECOVERED-FACT-LAYER.md`. Touches Phase 4's §18 envelope.
- DR-05 (graph-store `validity` sub-capability) deferred in REQUIREMENTS.md, reasoning now known incomplete — re-decide later.
- `v1/lightrag/evaluation/` — prior art for Phase 2's eval bundle, referenced in no requirement.
- `v1/lightrag/sidecar/` — unexamined; appears in no requirement.
- Multimodal/VLM — no v2 requirement mentions vision.
- Four LLM roles (`extract`, `keyword`, `query`, `vlm`) — the v2 node model has no per-role LLM binding.

**Later-milestone ideas**

- DuckDB for Phase 2+ scoreboard/trace analytics only — not for KV or the ledger.
- `entry_points` part discovery, if an external party ever authors a part (D-13).
- `lmdb` as a KV escalation path only if SQLite write throughput is measured as the bottleneck.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EMBED-01 | Databasise installs and runs as a single self-contained process tree — importable as a Python library, embedded stores (**Cozo + Faiss + SQLite**, correcting the requirement text's stale "LanceDB" — see Deferred above), no external DB servers, no Docker; `execution_mode` remains derived per CONTRACT §3 | D-05/D-14 lock the stores and the greenfield package boundary; Environment Availability section below confirms Python 3.12 + all three store engines install cleanly on NixOS via `uv` with `programs.nix-ld.enable` already on |
| MACH-05 | Runner/scheduler executes wiring graphs with structured concurrency, metering spend at each node's declared boundary; intra-node concurrency scheduling mechanism decided as part of this design | D-08/D-09/D-11 answer the §H1 handover; Architecture Patterns Pattern 1 gives the `graphlib.TopologicalSorter` + `asyncio.TaskGroup` mechanism; D-10 adds the run-record field set MACH-05's own definition of done is currently missing |
| MACH-06 | Component and artifact identity per CONTRACT §0/§1: `name@version`, RFC 8785 + SHA-256 `config_hash`, content-addressed artifact registry with `upstream_ref` lineage; instance identity `(name@version, config_hash, resolved_dependency_ids)`, never a wiring node id | D-12/D-13 lock the environment-hash and registry mechanism; Architecture Patterns Pattern 3 gives the content-addressed store + append-only ledger shape; CONTRACT §1/§7 quoted in full below |
| MACH-08 | Storage keying per RIG §RUN: KV shared only where CONTRACT §3's `shared` scope admits it (effective depth `stage`); an arm containing an `opaque` node writes `quarantined`, never `shared`; per-part graph/vector namespaces; artifact sharing iff index-recipe hashes are identical | D-07 locks the per-namespace directory layout; RIG §RUN.1/§RUN.2 quoted in full below; D-03 ports spike 005's `taint.py` case table as the conformance set that proves the rule |

</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.10+ (target 3.12) | Runtime | `uv python list` confirms `cpython-3.12.13` already installed locally under `~/.local/share/uv/python/`, matching v1's own pin (`v1/pyproject.toml:14`: `requires-python = ">=3.10"`) [VERIFIED: uv python list, this session] |
| `pycozo[embedded]` | 0.7.6 | Graph store primitive | Architecture-frozen incumbent (D-05, D4 One Machine). Confirmed on PyPI: `pycozo` 0.7.6 uploaded 2023-12-11, pure-Python wrapper (`py3-none-any` wheel); its `[embedded]` extra pulls `cozo-embedded==0.7.6`, which ships `manylinux_2_17_x86_64` wheels (`cp37-abi3`, so compatible with 3.12/3.13 via the stable ABI) [VERIFIED: PyPI JSON API `pypi.org/pypi/pycozo/0.7.6/json` and `pypi.org/pypi/cozo_embedded/json`, this session] |
| `faiss-cpu` | already pinned `>=1.7.0,<2.0.0` in `v1/pyproject.toml:48,113` [VERIFIED: v1/pyproject.toml:48, this session] | Vector store primitive | Owner-locked incumbent (D-05). Latest PyPI release 1.15.0 (2026-08-03) satisfies v1's existing `<2.0.0` upper bound [VERIFIED: PyPI JSON API `pypi.org/pypi/faiss-cpu/json`, this session] |
| `sqlite3` | stdlib (Python 3.13.15's bundled sqlite is 3.51.2 on this host) | KV, lexical (FTS5), artifact-registry index, append-only ledger | D-06. Zero new dependency; ships with every CPython build [VERIFIED: `python3 -c "import sqlite3; print(sqlite3.sqlite_version)"`, this session, printed `3.51.2`] |
| `rfc8785` | 0.1.4 (PyPI, uploaded 2024-09-27, `requires_python >=3.8`) | RFC 8785 (JCS) canonicalisation for `config_hash` | Claude's Discretion in CONTEXT.md, confirmed against the actual registry: pure-Python, trailofbits-authored [VERIFIED: PyPI JSON API `pypi.org/pypi/rfc8785/json`, this session]. **Package-legitimacy check returned `SUS` on "unknown-downloads"** — see Package Legitimacy Audit below for why this is a data-availability artifact, not a real risk signal |
| `graphlib` (stdlib) | Python 3.9+ | Readiness-ordering (`TopologicalSorter`) for the runner and for the SCC-condensation depth pass | Confirmed importable on this host's Python 3.13.15 [VERIFIED: `python3 -c "import graphlib"`, this session] |
| `asyncio.TaskGroup` (stdlib) | Python 3.11+ | Structured-concurrency execution of one "ready batch" | Confirmed present (`hasattr(asyncio, 'TaskGroup')` → `True`) on this host's Python 3.13.15 [VERIFIED: this session]. **Constraint: requires Python 3.11+**, so the project's `requires-python = ">=3.10"` floor must either raise to 3.11, or the runner falls back to a manual `asyncio.gather`-based batch driver on 3.10 — flag for planner decision |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `importlib.metadata` (stdlib) | Python 3.8+ | Resolved-closure environment hash (D-12) — distribution names, versions, wheel hashes read at runtime | Environment hash computation; never Nix, never a lockfile |
| `hashlib` (stdlib) | — | SHA-256 over the RFC-8785-canonicalised bytes | `config_hash` computation (CONTRACT §1) |
| `pydantic` v2 | already a v1 dependency | `NodeKind` tagged sum as a discriminated union | Matches CONTRACT §2's own wording ("serde external tagging or a pydantic discriminated union"); `.planning/research/ARCHITECTURE.md` Anti-Pattern 3 explains why a second JSON-Schema validation pass is redundant with it |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pycozo[embedded]` + `faiss-cpu` | `lancedb` (per stale `.planning/research/STACK.md:26`) | **Rejected by explicit owner decision (D-05).** LanceDB was recommended on a factually wrong description of the incumbent ("faiss-cpu + nano-vectordb pairing" — not the actual default) and would confound the Phase 3 parity baseline if swapped mid-project |
| Tarjan SCC hand-rolled (~30 lines) | `networkx.strongly_connected_components` | `.planning/research/ARCHITECTURE.md` Pattern 2 argues against adding NetworkX solely for one function; NetworkX is already a v1 dependency (kept for the quick-start default graph backend) but pulling it into `databasise/` for one algorithm reopens D-14's "nothing imports from v1" boundary question if done carelessly — hand-roll unless another Phase 1 need for graph algorithms emerges |
| `entry_points`-based part discovery | Explicit in-code registry dict | **Rejected for Phase 1 (D-13).** Every part this milestone is authored by this project; `entry_points` costs an editable install before any test can see a part, for extensibility nothing needs yet |
| `asyncio.TaskGroup` (3.11+) | `anyio.create_task_group` (works on 3.10) | Only relevant if the planner keeps `requires-python = ">=3.10"` as a hard floor; `anyio` is a real new dependency versus a stdlib-only runner — recommend raising the floor to 3.11 instead, since `uv` already has 3.12 available locally and nothing else in the stack needs 3.10 |

**Installation:**
```bash
# New root-level databasise/ package — no root pyproject.toml exists yet (verified this session: `ls *.toml` at repo root returns nothing)
uv add "pycozo[embedded]"==0.7.6 "faiss-cpu>=1.7.0,<2.0.0" rfc8785 pydantic

# Dev
uv add --dev pytest pytest-asyncio ruff
```

**Version verification:** All four externally-installed packages above (`pycozo`, `cozo-embedded`, `faiss-cpu`, `rfc8785`) were checked this session against the live PyPI JSON API (`pypi.org/pypi/<pkg>/json`), not training-data recall. `pycozo`'s upstream is dormant (no release since 2023-12-11) but this is the architecture-frozen incumbent per D-05, not a live selection decision — pin the exact version and vendor the wheel per CONTEXT.md's own STATE.md blocker note ("Cozo 0.7.6 is architecture-frozen with four known correctness bugs and no upstream fixes expected").

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `rfc8785` | pypi | ~2 years (2024-09-27) | unknown (PyPI download-stats unavailable to the checker) | `github.com/trailofbits/rfc8785.py` | SUS | **Approved with note** — flagged only on `unknown-downloads`, a data-availability gap in the legitimacy-check tool for PyPI, not a signal of the package itself. Author organisation (Trail of Bits) is a well-known security research firm; repo is real and matches the package name exactly |
| `pycozo` | pypi | ~3 years (2023-12-11) | unknown | none listed by checker (actual repo is `github.com/cozodb/cozo`, monorepo — the checker only searches for a repo named exactly `pycozo`) | SUS | **Approved** — already a direct v1 dependency (`v1/pyproject.toml:45`), architecture-frozen per D-05, not a new adoption decision. `no-repository` is a checker false negative: the real repo is the `cozodb/cozo` monorepo, confirmed via `.planning/research/STACK.md`'s own GitHub-API cross-check (4.1k stars, not archived) |
| `faiss-cpu` | pypi | latest release 2026-08-03 (package itself is years old; only the specific pinned build is new) | unknown | `github.com/facebookresearch/faiss` | SUS | **Approved** — flagged only on `too-new` (most recent release date) and `unknown-downloads`; Facebook Research-maintained, already a direct v1 dependency (`v1/pyproject.toml:48`), one of the most widely-used vector-search libraries in the ecosystem. The "too-new" signal reflects a routine version bump, not a new/unvetted package |

**Packages removed due to `SLOP` verdict:** none.
**Packages flagged as suspicious `SUS`:** `rfc8785`, `pycozo`, `faiss-cpu` — all three are flagged only on the checker's `unknown-downloads` heuristic (PyPI download counts are not exposed the way npm's are to this tool) and, for `pycozo`/`faiss-cpu`, on the fact that both are pre-existing v1 dependencies rather than new adoptions. **No `checkpoint:human-verify` task is warranted for `pycozo` or `faiss-cpu`** — they are already running in production inside v1 (`v1/lightrag/lightrag.py:275-284`, confirmed this session). For `rfc8785`, since it is a genuinely new dependency for this milestone, the planner should still add one lightweight `checkpoint:human-verify` before first install, per the package-legitimacy protocol's own rule for any newly-adopted package a checker cannot fully clear — even though the `SUS` reason here (download-count opacity) is unlikely to reflect real risk.

*`rfc8785`, `pycozo`, and `faiss-cpu` were all discovered via prior in-repo research/CONTEXT.md rather than fresh WebSearch this session, but their existence and current version were independently confirmed against the PyPI registry this session — tagged `[VERIFIED: PyPI JSON API]` above, not `[ASSUMED]`.*

## Architecture Patterns

### System Architecture Diagram

```
WIRING JSON (inert, no eval semantics — CONTRACT §1)
    │  nodes / deps / recipe / harnesses / provides
    ▼
PART REGISTRY  (explicit in-code dict, D-13; loaded once at process start)
    │  name@version → {schema, effects[], socket types}
    ▼
VALIDATOR  (Falsifier 2's own deliverable — CONTRACT §1/§2/§3)
    │  1. parse against NodeKind tagged sum (pydantic discriminated union), one pass,
    │     every violation returned with a JSON-Pointer path
    │  2. cycle detection over `deps` (Tarjan SCC) — cycle reported as {cycle:[...]} data
    │  3. depth = min-reduce over the SCC-condensation DAG (the taint rule, D-01/D-03)
    │  4. execution_mode derived from each node's declared effects[] (D-08: only
    │     in-process is implemented; subprocess/confined-unit/long-lived-service refuse
    │     by name)
    │  5. blast-radius check #1 — a node may write `shared` only at effective depth
    │     `stage` (D-02, load-time enforcement)
    ▼  (frozen at load — CONTRACT §11: no mid-run reads of mutable decision state)
RUNNER / SCHEDULER  (graphlib.TopologicalSorter + asyncio.TaskGroup, D-08/D-09/D-11)
    │  per-node semaphore sized from node config → feeds config_hash (D-09)
    │  budget metered only at each node's declared boundary (CONTRACT §9)
    │  blast-radius check #2 — re-asserted at the artifact-write path itself (D-02)
    ├──────────────────────────────┬─────────────────────────────────────────┐
    ▼                              ▼                                         ▼
MACHINE-OWNED STORES         IDENTITY/KEYING                        RUN-RECORD STAMPING
Cozo (graph, per-namespace    config_hash = SHA-256(                (D-10 — the fields
dir, D-07) · Faiss (vector,     RFC8785(input JSON))                 RIG §TR.1 requires:
per-namespace dir, D-07) ·     instance = (name@version,             cache_hit, guards_fired,
SQLite (KV/lexical/registry/    config_hash, deps)                   arm_execution_order,
ledger, D-06) · filesystem      environment hash =                   realised_budget_share,
blob store (content-addressed,  importlib.metadata closure           determinism/concurrency
git-style fan-out, D-06)        digest, never Nix (D-12)              setting)
    │
    ▼  (writes_artifact only, gated by effective depth == stage for `shared`)
ARTIFACT REGISTRY (SQLite index + content-hash blob store, CONTRACT §7)
    namespace field distinguishes shared / quarantined / self_storage (CONTRACT §3)
    │
    ▼  (only at promotion — Phase 1 does not exercise a real promote yet, but the
    │   ledger table is stood up now so trace/A-A-calibration records have somewhere
    │   to land, per .planning/research/ARCHITECTURE.md's build-order rationale)
LEDGER  (SQLite, append-only, INSERT-only; "active pointer" = a derived query,
         never an independently-written field — CONTRACT §7/§6)
```

A reader tracing the primary use case (submit a wiring, get an executed run with a stamped record) follows: wiring JSON → part registry lookup → validator's five-pass check → the load-frozen snapshot → runner execution respecting `deps` and the per-node semaphore → machine-owned store reads/writes gated by `effects[]` → artifact registry write (only if `writes_artifact` and effective depth `stage`) → run-record fields stamped for the (Phase 2) gate to later read.

### Recommended Project Structure

```
databasise/
├── identity/                 # config_hash, instance-hash, JCS canonicalization — build FIRST (D-12)
│   ├── canon.py               # wraps rfc8785 + hashlib.sha256
│   └── instance.py            # (name@version, config_hash, deps) tuple; runtime-minted formula
├── parts/
│   ├── registry.py            # explicit in-code dict, name@version -> Part (D-13)
│   └── schema.py               # NodeKind tagged sum as pydantic discriminated union (CONTRACT §2)
├── validator/
│   ├── parse.py                # one-pass JSON -> typed graph, JSON-Pointer error accumulation
│   ├── cycles.py                 # Tarjan SCC, {cycle:[...]} as data
│   ├── depth.py                  # SCC-condensation min-reduce over {opaque,evidence,stage} (D-01/D-03)
│   └── execution_mode.py         # effects[] -> execution_mode; D-08 refuses non-in-process by name
├── runner/
│   ├── scheduler.py               # graphlib.TopologicalSorter + asyncio.TaskGroup driver (D-08/D-09)
│   ├── budget.py                   # per-node spend/wall-clock metering, multiplicative fan-out
│   └── trace.py                     # D-10's run-record field stamping (cache_hit, guards_fired, ...)
├── stores/
│   ├── kv.py / lexical.py / blob.py     # SQLite-backed, effects[]-gated (D-06)
│   ├── graph.py                          # Cozo adapter, per-namespace directory (D-05/D-07)
│   └── vector.py                          # Faiss adapter, per-namespace directory (D-05/D-07)
├── registry_artifact/
│   ├── blob_store.py            # content-hash-addressed disk layout (git-style fan-out)
│   └── index.py                  # SQLite metadata rows (namespace/scope, SA-2 stamps, corpus, space_id)
├── ledger/
│   └── ledger.py                  # append-only SQLite table + active-pointer projection query
├── parts_core/                    # D-04's four executable reference parts (passthrough, fake retriever,
│   └── ...                        #   fake LLM caller, fixpoint body) — never imports v1
└── (no seam/ yet — §18 REST+MCP is Phase 4, out of this phase's scope)
```

Nothing under `databasise/` imports from `v1/` (D-14) — every module above is either stdlib, one of the four externally-installed packages, or new code, ported by deliberate copy where v1 has a proven pattern to draw from (see Code Examples below).

### Pattern 1: TopologicalSorter-driven TaskGroup execution

**What:** `graphlib.TopologicalSorter` handles readiness bookkeeping only (which nodes' predecessors are all `done()`); `asyncio.TaskGroup` runs one "ready batch" concurrently with structured-concurrency failure semantics (`except*` cancels siblings on one task's exception, no orphaned tasks). The two stdlib pieces are complementary: the sorter never touches the event loop, `TaskGroup` never touches dependency state.

**When to use:** Every wiring run — the default execution path for the `fanout`/`join`/plain-DAG shape. `fixpoint` nodes (D-04's fourth reference part) wrap a sub-DAG in their own bounded loop, the executor owning the halt condition per CONTRACT §2, re-entering the same sorter/TaskGroup pattern per iteration.

**Example:**
```python
# Source: .planning/research/ARCHITECTURE.md Pattern 1 (already project-researched, not re-derived here)
import asyncio, graphlib

async def run_wiring(nodes: dict, deps: dict[str, set[str]], exec_node):
    ts = graphlib.TopologicalSorter(deps)
    try:
        ts.prepare()
    except graphlib.CycleError as e:
        return {"cycle": e.args[1]}          # cycle reported as data, never raised past this point

    results = {}
    while ts.is_active():
        ready = ts.get_ready()
        async with asyncio.TaskGroup() as tg:
            tasks = {n: tg.create_task(exec_node(n, nodes[n], results)) for n in ready}
        for n, t in tasks.items():
            results[n] = t.result()
            ts.done(n)
    return results
```

**Constraint verified this session:** `asyncio.TaskGroup` requires Python 3.11+ (`hasattr(asyncio, 'TaskGroup')` confirmed `True` on this host's 3.13.15; the feature does not exist on 3.10). Since `v1/pyproject.toml` declares `requires-python = ">=3.10"` and `databasise/` is a new, separate package (D-14), the planner should decide whether `databasise/pyproject.toml` raises its own floor to `>=3.11` — recommended, since `uv` already has 3.12 available locally and nothing else in the Phase 1 stack needs 3.10.

### Pattern 2: SCC-condensation depth computation (the taint rule as a lattice fixpoint)

**What:** Depth (`{opaque, evidence, stage}`) is the minimum over a node's *transitive* `deps` (CONTRACT §3's taint rule), and cycles are legal wiring content (CONTRACT §1), so a plain topological pass cannot compute depth directly once cycles exist. Run Tarjan's SCC algorithm first, treat each SCC as one condensed node (members are mutually reachable, so by the taint rule's own definition they resolve to the same effective depth), topologically order the condensation DAG (always acyclic by construction), and min-reduce depth across it in one linear pass.

**When to use:** Once, at validation time, over the load-frozen wiring snapshot — this is D-01's own scope and Falsifier 2's deliverable.

**Verified against CONTRACT §3 directly, not paraphrased:** *"Effective depth is the minimum over a node's transitive `deps` — the taint rule — and wiring depth is the minimum over the compared path."* [VERIFIED: docs/system-model/CONTRACT.md:236]

**Example (shape only, per `.planning/research/ARCHITECTURE.md` Pattern 2):**
```python
# 1. sccs = tarjan(deps)                      # list of node-id sets, cycle members grouped
# 2. condensation = {scc_id: {scc_of(d) for n in scc for d in deps[n]} - {scc_id}}
# 3. order = list(graphlib.TopologicalSorter(condensation).static_order())
# 4. for scc_id in order:  # leaves (no deps) first
#        depth[scc_id] = min([own_depth(n) for n in scc] +
#                             [depth[condensation_dep] for condensation_dep in condensation[scc_id]])
```

**No stdlib implementation exists for Tarjan's SCC** — this is the one piece of the whole stack that is not "reach for the standard library first." `networkx.strongly_connected_components` is the honest alternative, but `.planning/research/ARCHITECTURE.md` argues against adding NetworkX to `databasise/` solely for this one ~30-line, extensively-documented algorithm — and doing so would also brush against D-14's "nothing imports from v1" boundary if NetworkX is pulled in carelessly from the v1 dependency set rather than declared fresh.

### Pattern 3: Content-addressed artifact store + append-only ledger (git-object-store shape)

**What:** Two structurally different persistence needs from CONTRACT §7, both mapping onto one well-worn pattern each:
- **Artifact registry** (content-hash-addressed, gigabyte-sized, deletion-capable): disk blob store keyed by hash with a fan-out directory layout (`ab/cd/abcd1234...`, Git's own `.git/objects` layout), plus a SQLite row per entry carrying namespace/scope (D-07's per-namespace directories), SA-2 sub-recipe stamps, corpus, `space_id`, producing instance.
- **Ledger** (byte-sized, append-only, never deleted): a plain SQLite table, `INSERT`-only, monotonically increasing `id`. "The active pointer" is never its own writable column — always `SELECT ... WHERE mutation_id = ? ORDER BY id DESC LIMIT 1`.

**Verified against CONTRACT §7 directly:** *"The artifact registry MUST be gigabyte-sized and deletion-capable, unlike the byte-sized, never-deleted component registry above."* [VERIFIED: docs/system-model/CONTRACT.md:354] *"A ledger record MUST enumerate: mutation id, class, parent, arm instance hashes, effect size, verdict, evidence pointer, proposer id, depth label, tier-of-decision, decomposition ratio, opaque-node TTL renewals with their recorded reasons, parity records for decompositions, `promotion_provenance` ... and `promotion_trace_ids`."* [VERIFIED: docs/system-model/CONTRACT.md:362]

**When to use:** Both from Phase 1 — the ledger table should exist before Phase 1's own A/A calibration run needs to record anything (per `.planning/research/ARCHITECTURE.md`'s build-order rationale), even though the first real `promote` doesn't happen until Phase 2.

**Example:**
```python
# Source: .planning/research/ARCHITECTURE.md Pattern 3
h = hashlib.sha256(artifact_bytes).hexdigest()
path = blob_root / h[:2] / h[2:4] / h
if not path.exists():                      # identical content already stored -> no-op, not a collision
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(artifact_bytes)
registry_db.execute(
    "INSERT INTO artifacts(hash, namespace, scope, sa2_stamps, corpus_id, space_id, producer) "
    "VALUES (?,?,?,?,?,?,?)", (h, namespace, scope, json.dumps(sa2), corpus_id, space_id, producer))

ledger_db.execute(
    "INSERT INTO ledger(mutation_id, class, parent, verdict, promotion_provenance, ...) VALUES (?,...)", (...))
# active = SELECT * FROM ledger WHERE mutation_id=? ORDER BY id DESC LIMIT 1
```

### Pattern 4: Per-namespace store directory derivation (D-07, MACH-08)

**What:** RIG §RUN.1 states the namespace-derivation rule the machine applies (not a storage-keying design it invents): *"a namespace is derived from the artifact-registry vocabulary §7 already froze — namespace, sub-recipe stamps (SA-2), corpus, space_id, producing instance — plus the arm's own SA-1 recipe identity from §1's `(name@version, config_hash, resolved_dependency_ids)` tuple."* [VERIFIED: docs/system-model/RIG.md:52] D-07 makes this concrete: each arm/namespace gets its own Cozo database file and its own Faiss index directory, under a path derived from that same recipe-identity tuple.

**Verified — the shared/quarantined boundary, quoted directly:** *"The KV is shared across arms where, and only where, §3's `shared` scope admits it ... An arm containing an `opaque` node writes `quarantined` and never `shared`, per §3's own scope table and the same rule §8 restates for opaque-node admission; its index is therefore instance-scoped and readable only by explicit pin from another wiring, never SA-1-shareable."* [VERIFIED: docs/system-model/RIG.md:54,56]

**When to use:** Every store-access call the runner makes, gated by the node's stamped effective depth (from Pattern 2) at the moment of the write.

**Directory-per-namespace verification approach:** Success criterion 4 ("per-part graph and vector namespaces are visibly separate after a run") becomes checkable with a plain `ls` over the store root — a `shared`-scope namespace directory and a `quarantined`-scope one produced by the same run must be distinguishable filesystem paths, and GC of a `quarantined` instance is deleting its directory, matching CONTRACT §3's "GC'd with the instance" rule for that scope directly. [inference — directory-per-namespace is D-07's own chosen mechanism, not separately re-derived here]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RFC 8785 JSON canonicalisation | A custom JCS serializer | `rfc8785` (pure-Python, trailofbits) | CONTRACT §1 pins the exact algorithm (int64 boundary, int/float collapse) — hand-rolling risks a subtle divergence from the spec that silently breaks `config_hash` reproducibility across two implementations |
| Wiring-graph orchestration | A workflow-orchestration platform (Airflow/Dagster/Prefect/Temporal) | `graphlib.TopologicalSorter` + `asyncio.TaskGroup` | Every orchestrator option requires an external server/scheduler process or a metadata DB server, directly violating "no external DB servers, no Docker, embeddable-first"; each also brings its own task-identity/retry/persistence model that would have to be forced to match CONTRACT.md's frozen identity/effects/depth model rather than reused. `.planning/research/ARCHITECTURE.md` Anti-Pattern 1 |
| Cycle-safe topological depth ordering | A hand-rolled iterative worklist / general dataflow-fixpoint solver | SCC-condensation (Tarjan) + `graphlib.TopologicalSorter` min-reduce (Pattern 2) | The depth lattice's meet operation is simply `min`, which collapses a general iterative fixpoint to one linear pass once cycles are condensed — building a general worklist algorithm for this one lattice is unneeded complexity |
| JSON Schema validation of wiring documents | A second, hand-written JSON Schema validation pass alongside pydantic | pydantic v2 discriminated union alone | CONTRACT §2 already specifies the tagged-sum shape in terms matching a pydantic discriminated union directly; running the same structural check twice in two type systems that can drift out of sync is pure risk with no additional guarantee. `.planning/research/ARCHITECTURE.md` Anti-Pattern 3 |
| Cozo query construction for the four frozen 0.7.6 bugs | New ad hoc mitigation code per new graph-storage call site | Port `v1/lightrag/kg/cozo_impl.py`'s existing mitigations (deferred-write buffers, bound parameters, `run_in_executor` dispatch, `test_cozo_graph_storage.py`'s regression shapes) by copy | Cozo 0.7.6 is architecture-frozen with no upstream fixes expected (STATE.md's own blocker note); the four correctness bugs (#244, #275, #253, #296/#269) are silent-wrong-result bugs, not exceptions — re-deriving the mitigations from scratch risks silently reintroducing one |
| Multi-process/multi-worker locking for the runner | v1's `UnifiedLock` (hybrid `asyncio.Lock` + `multiprocessing.Manager.Lock`) or any module-level singleton from `shared_storage.py` | A new, node-scoped concurrency primitive — the per-node semaphore D-09 already specifies | D-11 explicitly forbids importing `UnifiedLock`/`_manager`/`_global_concurrency_limits`; confirmed present at `v1/lightrag/kg/shared_storage.py:66,111,175` [VERIFIED: v1/lightrag/kg/shared_storage.py:66,111,175 — `_manager = None` / `_global_concurrency_limits: Optional[Dict[str, int]] = None` / `class UnifiedLock(Generic[T]):`, this session] — a process-wide cap would throttle one arm's fan-out against an unrelated arm beside it, contaminating Phase 6's side-by-side comparison |

**Key insight:** Every "don't hand-roll" item above already has a working reference in this exact repository (v1's Cozo/Faiss adapters) or a stdlib primitive that exactly matches the contract's own stated shape — this phase's engineering effort should go into the SCC-condensation depth computation and the identity/keying module (the two genuinely novel pieces), not into re-solving problems v1 or the stdlib already solved.

## Common Pitfalls

### Pitfall 1: Storage/lock ownership hidden inside "decomposed" node code

**What goes wrong:** A node's call-graph boundary can look clean while its storage access still reaches into v1's `shared_storage.py` singleton state.
**Why it happens:** Storage state is invisible in a call graph — node boundaries (`effects[]`, artifact scopes) describe data flow, not who owns the lock.
**How to avoid:** D-14 already makes this structurally impossible for Phase 1 by construction (no import path from `databasise/` to `v1/` exists at all) — the discipline that matters for Phase 1 is not accidentally reaching back into v1 for "just this one utility function." Enforce with a lint/CI check that fails on any `from lightrag` or `from v1` import inside `databasise/`.
**Warning signs:** Any `import` statement inside `databasise/` referencing `lightrag.*` or a relative path into `v1/`.
**Source:** `.planning/research/PITFALLS.md` Pitfall 1, `.planning/research/PITFALLS.md` Pitfall 7.

### Pitfall 2: Cozo's frozen 0.7.6 correctness bugs silently re-triggered by new query construction

**What goes wrong:** Four known silent-wrong-result bugs in Cozo 0.7.6 (#244 aggregation 0-rows, #275 wrong DataValue types, #253 JSON key-order loss, #296/#269 UUID sort/coercion) are currently mitigated by specific query shapes documented in `v1/lightrag/kg/cozo_impl.py`'s own docstring: *"avoid `count()` aggregation, store all keys as String never UUID, consume JSON as dict not relying on key order, assert types on round-trip"* [VERIFIED: v1/lightrag/kg/cozo_impl.py:54-59]. Writing a new Cozo adapter for `databasise/stores/graph.py` from scratch risks reintroducing one of these query shapes.
**Why it happens:** The mitigations live as docstring/test-comment tribal knowledge, not as an enforced constraint a new implementation is forced to encounter.
**How to avoid:** Port `test_cozo_graph_storage.py`'s frozen-bug regression shapes forward as a mandatory, non-skippable suite that runs against the new `databasise/stores/graph.py` adapter, not just the original v1 class.
**Warning signs:** New query construction using `count()`, UUID-typed keys, or relying on JSON key order.
**Source:** `.planning/research/PITFALLS.md` Pitfall 6; `v1/lightrag/kg/cozo_impl.py:54-59` (verbatim, this session).

### Pitfall 3: Asyncio + multiprocessing hybrid locking gets carried into the new runner by convenience

**What goes wrong:** v1's `UnifiedLock` "already works," so the path of least resistance when building the new runner is to keep calling into it rather than designing the new concurrency model D-09 specifies.
**Why it happens:** The hybrid lock has no documented fix (by design, per project history) and reaching for a known-working primitive under time pressure is the natural move.
**How to avoid:** D-11 already forbids this by name. Treat the §H1 fence as the place to define a genuinely new concurrency model — the per-node semaphore whose size enters `config_hash` (D-09) — not a decision about which v1 lock primitive to keep.
**Warning signs:** Any `from lightrag.kg.shared_storage import ...` inside `databasise/` (should be structurally impossible per D-14, so its presence is itself the bug).
**Source:** `.planning/research/PITFALLS.md` Pitfall 7; CONTEXT.md D-11.

### Pitfall 4: `asyncio.TaskGroup` version-floor mismatch

**What goes wrong:** `.planning/research/ARCHITECTURE.md` recommends `asyncio.TaskGroup`, which requires Python 3.11+, while the existing v1 project floor is `>=3.10` (`v1/pyproject.toml:14`). If `databasise/pyproject.toml` is created inheriting the same `>=3.10` floor without noticing the TaskGroup dependency, a contributor on 3.10 gets an `AttributeError: module 'asyncio' has no attribute 'TaskGroup'` at import time, not at install time.
**Why it happens:** `databasise/` is a new, separate top-level package (D-14) with no root `pyproject.toml` yet (confirmed this session — `ls *.toml` at repo root returns nothing) — there is no existing floor to accidentally inherit, but there is also no existing floor to notice is wrong.
**How to avoid:** Set `requires-python = ">=3.11"` explicitly in the new `databasise/pyproject.toml` (or wherever the new package's build metadata lives), and note in the same file why it differs from v1's `>=3.10`.
**Warning signs:** CI running against a 3.10 interpreter for `databasise/` tests.
**Source:** Verified this session (`hasattr(asyncio, 'TaskGroup')` → `True` only from 3.11 per Python's own changelog; `v1/pyproject.toml:14` confirmed `>=3.10`; repo-root `ls *.toml` confirmed empty).

### Pitfall 5: NixOS manylinux-wheel loading for `cozo-embedded`/`faiss-cpu` native extensions

**What goes wrong:** `cozo-embedded` and `faiss-cpu` ship compiled `manylinux2014_x86_64` wheels that dynamically link against glibc/libstdc++ paths a NixOS system does not expose by default (no FHS `/lib64/ld-linux...`), which can cause `ImportError: libc.so.6: cannot open shared object file` or similar at first `import`.
**Why it happens:** manylinux wheels assume a standard FHS layout; NixOS deliberately does not provide one.
**How to avoid:** This host already has `programs.nix-ld.enable = true` set in `/etc/nixos/configuration.nix:307` [VERIFIED: /etc/nixos/configuration.nix:307 — `programs.nix-ld.enable = true;`, this session], which provides the dynamic loader shim manylinux wheels need. Confirm the same is true for whichever machine actually builds/runs Phase 1, and confirm `uv`'s installed interpreter (not the system Python 3.13) is the one used, since `uv python list` shows a working `cpython-3.12.13` already present.
**Warning signs:** `ImportError` on `import pycozo` or `import faiss` that does not reproduce on non-NixOS dev machines.
**Source:** Verified this session (`/etc/nixos/configuration.nix:307`; `cozo_embedded` wheel filenames from PyPI JSON API list `manylinux_2_17_x86_64.manylinux2014_x86_64`).

## Code Examples

### RFC 8785 config_hash computation

```python
# Shape only — rfc8785 API confirmed via PyPI package description this session;
# exact function signature should be verified against the installed package's
# docstring during implementation, not assumed from this research pass.
import hashlib
import rfc8785

def config_hash(author_supplied_json: dict) -> str:
    canonical_bytes = rfc8785.dumps(author_supplied_json)   # JCS-canonicalised UTF-8 bytes
    return hashlib.sha256(canonical_bytes).hexdigest()
```

### Tarjan SCC + depth min-reduce

See Pattern 2 above — `.planning/research/ARCHITECTURE.md`'s shape-only sketch is the starting point; no full implementation exists yet in this repository (confirmed: `databasise/` package does not exist on disk this session — `find . -maxdepth 3 -iname databasise -type d` returned nothing).

### Cozo deferred-write buffer pattern (port by copy, per D-14)

```python
# Source: v1/lightrag/kg/cozo_impl.py:25-45 (docstring, quoted verbatim this session)
# "Cozo commits each :put/:rm immediately in its own transaction, but LightRAG
#  buffers writes in-memory and flushes them at index_done_callback. This adapter
#  resolves the mismatch by maintaining four in-process buffers:
#      _pending_node_puts  : dict[id, attrs]      — nodes to upsert
#      _pending_edge_puts  : dict[(src,tgt), attrs] — edges to upsert (canonical order)
#      _pending_node_rms   : set[id]               — node ids to delete
#      _pending_edge_rms   : set[(src,tgt)]        — edge pairs to delete (canonical order)
#  Reads consult these buffers FIRST (read-your-writes before flush)."
```
This buffering discipline, the `run_in_executor` dispatch for `pycozo.Client.run()`'s synchronous API, and the bound-parameter rule for entity names containing Datalog metacharacters (`v1/lightrag/kg/cozo_impl.py:40-52`, verified this session) must all travel with the `databasise/stores/graph.py` port, per CONTEXT.md's own canonical-refs list.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `.planning/research/STACK.md`'s LanceDB recommendation for the vector store | Faiss (D-05, owner decision, 2026-08-29) | This project's own Phase 1 context-gathering session | `STACK.md`'s recommendation was built on a factual error about the incumbent ("faiss-cpu + nano-vectordb pairing" is not v1's actual default) — the planner must read `STACK.md`'s vector-store row as superseded, not as live guidance |
| A "shallowest-denominator" comparison framing | "Greatest common depth" (CONTRACT §4) | Frozen at contract-writing time, explicitly named and rejected | CONTRACT §4 states: *"The alternative framing recorded in 01-RESEARCH.md's State of the Art table (row 2) — 'shallowest-denominator' comparison — was an explicit condition from spike 002 that SELECTION.md REJECTED... that phrase MUST NOT be used as this contract's comparison rule."* [VERIFIED: docs/system-model/CONTRACT.md:288] Not directly load-bearing for Phase 1's own deliverables (this is a Phase 2 gate concept), but the planner should not introduce this rejected phrase into any Phase 1 doc/comment referencing depth comparison |

**Deprecated/outdated:**
- v1's `UnifiedLock`/`shared_storage.py` singleton concurrency model — explicitly not carried forward (D-11); the new runner defines its own scoped per-node semaphore.
- `nano-vectordb` as a fallback vector store — not part of the Phase 1 stack at all; D-05 locks Faiss as the sole vector-store primitive, no fallback pairing.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `rfc8785`'s exact function-call signature (`rfc8785.dumps(...)` shown in Code Examples) is a plausible shape based on the package's stated purpose, not confirmed against its actual source/docstring this session | Code Examples | Low — the planner/executor should read the installed package's own API during implementation rather than trust this shape; a signature mismatch fails fast at import/call time, not silently |
| A2 | `databasise/pyproject.toml` should raise `requires-python` to `>=3.11` to use `asyncio.TaskGroup` | Standard Stack, Pitfall 4 | Low-medium — if the planner instead keeps `>=3.10` and picks `anyio` for TaskGroup-equivalent behavior, that is a legitimate alternative Claude's Discretion already permits ("structured-concurrency mechanism ... is the researched default; no orchestrator") — this assumption only concerns which stdlib-vs-dependency tradeoff to default to |
| A3 | The `SUS` package-legitimacy verdicts on `rfc8785`/`pycozo`/`faiss-cpu` reflect the checker's PyPI download-count data gap rather than real risk | Package Legitimacy Audit | Low — all three packages are independently corroborated by repo identity (Trail of Bits, cozodb org, Facebook Research) and, for two of three, by already running in production inside v1; a planner who wants stronger confirmation can re-run the check once a downloads-aware PyPI signal source is available |

**If this table is empty:** N/A — see entries above; every other claim in this document is tagged `[VERIFIED: ...]` against a primary source read this session (CONTRACT.md, RIG.md, v1 source files, the PyPI JSON API, or the local shell environment).

## Open Questions

1. **Does `databasise/pyproject.toml` raise `requires-python` to `>=3.11`, or does the runner fall back to `anyio` for TaskGroup-equivalent structured concurrency on 3.10?**
   - What we know: `asyncio.TaskGroup` (the researched default per CONTEXT.md's own Claude's Discretion) requires 3.11+; v1's floor is `>=3.10`; `uv` already has 3.12 installed locally so raising the floor costs nothing operationally.
   - What's unclear: whether any downstream consumer of `databasise/` (Sourcerer, per CLAUDE.md's framing as "one consumer among any") has its own floor below 3.11 that this would break.
   - Recommendation: raise to `>=3.11` for `databasise/` specifically (it is a new, separate package per D-14, so it need not match v1's floor) unless the planner has evidence of a 3.10-only consumer.

2. **Where does the new root-level `databasise/pyproject.toml` (or equivalent build config) live, and does it participate in the existing `uv.lock`/root workspace, or get its own?**
   - What we know: no root-level `pyproject.toml` exists yet (confirmed this session); `v1/pyproject.toml` is self-contained; D-14 requires `databasise/` to import nothing from `v1/`.
   - What's unclear: whether the project wants one root `uv` workspace spanning both `v1/` and `databasise/` (shared lockfile, easier cross-package dependency alignment) or two fully independent package trees.
   - Recommendation: this is a build-tooling decision for the planner/first task, not something this research should preempt — flag it as the first concrete task in Phase 1's plan.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python interpreter matching v1's pin | Running `databasise/` at all | ✓ | `cpython-3.12.13` already installed under `uv`'s Python management [VERIFIED: `uv python list`, this session] | System `python3` is 3.13.15 — also usable, but not what v1 validated against; prefer the uv-managed 3.12.13 |
| `uv` (package manager) | Dependency install/lock | ✓ | 0.11.21 [VERIFIED: `uv --version`, this session] | — |
| `sqlite3` (stdlib) | KV/lexical/registry/ledger | ✓ | bundled with system Python, 3.51.2 [VERIFIED: this session] | — |
| `graphlib`/`asyncio.TaskGroup` (stdlib) | Runner readiness ordering + structured concurrency | ✓ (on 3.11+; confirmed present on this host's 3.13.15) | stdlib | On 3.10, `TaskGroup` is absent — see Open Question 1 |
| `pycozo[embedded]` (`cozo-embedded` native wheel) | Graph store primitive | Not yet installed in any project venv (no root venv exists this session) — but a compatible `manylinux2014_x86_64` wheel exists on PyPI for the pinned version | 0.7.6 [VERIFIED: PyPI JSON API, this session] | None viable — this is the architecture-frozen incumbent (D-05); no fallback graph store is in scope for Phase 1 |
| `faiss-cpu` | Vector store primitive | Not yet installed in any project venv this session; wheel availability confirmed via v1's own working install | already pinned `>=1.7.0,<2.0.0` in v1 | None viable — architecture-frozen incumbent (D-05) |
| `nix-ld` (NixOS dynamic-loader shim for manylinux wheels) | Loading `cozo-embedded`'s and `faiss-cpu`'s compiled native extensions on this NixOS host | ✓ | `programs.nix-ld.enable = true` [VERIFIED: /etc/nixos/configuration.nix:307, this session] | — |
| Rust toolchain | Only if a wheel must be built from source (not expected — manylinux wheels exist for the pinned versions) | Not checked this session (not needed given prebuilt wheels exist) | — | Building from source is the fallback if a prebuilt wheel ever fails to load |

**Missing dependencies with no fallback:** none — every Phase 1 dependency either has a prebuilt wheel confirmed available, or is stdlib.

**Missing dependencies with fallback:** none required this phase; Open Question 1 (Python floor) is a design decision, not a missing-dependency blocker.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2+ / pytest-asyncio 1.2+ (v1's existing choice; confirmed via `v1/pyproject.toml:189-193` `[tool.pytest.ini_options]`, `asyncio_mode = "auto"`) [VERIFIED: v1/pyproject.toml:189-193, this session] |
| Config file | none yet for `databasise/` — no root-level `pyproject.toml` or `pytest.ini` exists (confirmed this session) — **this is Wave 0's first gap** |
| Quick run command | `pytest databasise/tests/ -x` (path presumed from the Recommended Project Structure above; does not yet exist on disk) |
| Full suite command | `pytest databasise/tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EMBED-01 | Databasise imports and starts with zero external DB servers/containers | integration/smoke | `pytest databasise/tests/test_embed_startup.py -x` | ❌ Wave 0 |
| MACH-05 | Runner executes a wiring graph to completion under structured concurrency, meters spend at each node's boundary, per-node semaphore is decided and enforced | integration | `pytest databasise/tests/runner/test_scheduler.py -x` | ❌ Wave 0 |
| MACH-06 | Same component wired twice with byte-identical config resolves to one instance identity/cache partition; any config byte change yields a different `config_hash` | unit | `pytest databasise/tests/identity/test_config_hash.py -x` | ❌ Wave 0 |
| MACH-06 (D-03 conformance) | Spike 005's `taint.py` 12-case table ported and passing under the repaired vocabulary (D-03's three named repairs) | unit | `pytest databasise/tests/validator/test_taint_conformance.py -x` | ❌ Wave 0 — the case table itself is fully specified at `.claude/skills/spike-findings-rag-graph-vector-raw/sources/005-laundering-test/taint.py:86-195` [VERIFIED: this session] and can be ported directly |
| MACH-08 | Opaque-arm writes land in `quarantined`, never `shared`; per-part graph/vector namespaces visibly separate via `ls` | integration | `pytest databasise/tests/stores/test_namespace_isolation.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest databasise/tests/ -x -k <touched-module>`
- **Per wave merge:** `pytest databasise/tests/` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`; additionally, `test_cozo_graph_storage.py`'s ported frozen-bug regression suite must be green against the new `databasise/stores/graph.py` adapter specifically (Pitfall 2), not merely against the original v1 class.

### Wave 0 Gaps

- [ ] `databasise/pyproject.toml` (or root-level equivalent) — no build config exists for the new package yet; blocks every other test file below.
- [ ] `databasise/tests/conftest.py` — shared fixtures (temp store directories per D-07, a minimal wiring fixture, the four D-04 reference parts).
- [ ] Framework install: `uv add --dev pytest pytest-asyncio` inside whatever `databasise/` build config Open Question 2 resolves to.
- [ ] Port `test_cozo_graph_storage.py`'s frozen-bug regression shapes forward against the new adapter (Pitfall 2) — not a new test file from scratch, an adapted port.

## Sources

### Primary (HIGH confidence)

- `docs/system-model/CONTRACT.md` §0, Ruling R-1, §1, §2, §3, §4, §5, §7, §8, §9, §10, §11 — read and quoted directly this session
- `docs/system-model/RIG.md` §RUN (§RUN.1-§RUN.4), §TR (§TR.1-§TR.3), §AA (§AA.1-§AA.4) — read and quoted directly this session
- `docs/system-model/SYSTEM-MODEL.md` §H1 — read directly this session
- `.claude/skills/spike-findings-rag-graph-vector-raw/references/selected-architecture.md`, `wiring-spec-and-validation.md`, `nix-substrate-boundary.md` — read directly this session
- `.claude/skills/spike-findings-rag-graph-vector-raw/sources/005-laundering-test/taint.py`, `README.md` — read directly this session, case table (lines 86-195) confirmed
- `v1/lightrag/lightrag.py:275-284`, `v1/lightrag/api/config.py:64-68` — read directly this session, confirms Cozo+Faiss+JsonKV as the actual v1 defaults
- `v1/lightrag/kg/cozo_impl.py:1-100` — read directly this session, confirms the four mitigation patterns and the Validity forward-compatibility note
- `v1/lightrag/kg/shared_storage.py:50-180` — read directly this session, confirms `UnifiedLock`, `_manager`, `_global_concurrency_limits` exist as stated
- `v1/lightrag/namespace.py`, `v1/lightrag/tools/rebuild_vdb.py:1-20`, `v1/pyproject.toml` — read directly this session
- PyPI JSON API (`pypi.org/pypi/<pkg>/json`) for `rfc8785`, `pycozo`, `cozo_embedded`, `faiss-cpu` — queried live this session
- `/etc/nixos/configuration.nix:307` — read directly this session (`programs.nix-ld.enable = true`)
- Local shell environment (`uv python list`, `uv --version`, `python3 --version`, `git --version`, `sqlite3` version probe, `graphlib`/`asyncio.TaskGroup` import probes) — run directly this session

### Secondary (MEDIUM confidence)

- `.planning/research/ARCHITECTURE.md` — prior-session research, cross-checked against CONTRACT.md/RIG.md quotes this session, not re-derived from scratch
- `.planning/research/PITFALLS.md` — prior-session research, web-sourced per its own confidence note (MEDIUM); Phase-1-relevant pitfalls (1, 6, 7) cross-checked against v1 source this session
- gsd-tools `package-legitimacy check` output for `rfc8785`/`pycozo`/`faiss-cpu` — automated heuristic check, interpreted and cross-checked against repo identity this session

### Tertiary (LOW confidence)

- `.planning/research/STACK.md` — **superseded by owner decision D-05 for the graph/vector store rows specifically**; its LanceDB recommendation is explicitly flagged as built on a factual error about the incumbent (see State of the Art table above). Its MCP/REST-surface rows (Phase 4/5 scope) are not evaluated in this research pass and should be re-verified when those phases are researched.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every package version checked live against PyPI this session; store engines are owner-locked (not a research judgment call)
- Architecture: HIGH for the contract-frozen shapes (identity, depth, blast-radius — all quoted verbatim from CONTRACT.md/RIG.md); MEDIUM for the runner-mechanism recommendation (TopologicalSorter+TaskGroup) since that is a build-time library choice, not contract-frozen
- Pitfalls: MEDIUM — Phase-1-relevant pitfalls corroborated against actual v1 source this session (not merely inherited from prior web-sourced research); the underlying web sources PITFALLS.md cites remain unverified this session

**Research date:** 2026-08-30
**Valid until:** 30 days for the stack/version claims (PyPI-sourced, can drift); no expiry for the contract-frozen architecture claims (CONTRACT.md/RIG.md text is locked input per CLAUDE.md's own constraints) — re-verify only if CONTRACT.md/RIG.md themselves are amended.

---
*Phase: 1-Machine Core*
*Researched: 2026-08-30*
