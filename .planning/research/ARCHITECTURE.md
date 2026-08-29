# Architecture Research

**Domain:** Implementation architecture for an agnostic RAG execution machine (wiring-graph runner, content-addressed storage, versioned component registry) — the §H1 must-decide layer beneath a frozen system model (D4 One Machine).
**Researched:** 2026-08-29
**Confidence:** MEDIUM (stdlib/library facts HIGH; specific-package recommendations MEDIUM; all findings cross-checked against the frozen `CONTRACT.md`/`RIG.md` text, which is the binding source of truth for *what* must be built — this document is only about *how*)

**Scope note.** `SYSTEM-MODEL.md §H1` and `RIG.md §RUN.3`/`§9` are explicit that the runner, scheduler, and storage-keying scheme are named-but-not-designed by the model, on purpose (D-12): "the process model, the scheduler and the storage-keying scheme are **not** designed in this section." This document is the build's own answer to that fence — it does not reopen anything `CONTRACT.md`/`RIG.md` already settled (NodeKind tagged sum, `effects[]`, the three artifact scopes, the ledger-wins rule, multiplicative fan-out budgeting), it only picks concrete Python mechanisms that satisfy those already-frozen shapes.

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  WIRING SPEC (inert JSON — no eval semantics)                        │
│  nodes / deps / recipe / harnesses / provides   (CONTRACT §1)         │
└───────────────────────────────┬────────────────────────────────────-─┘
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  PART REGISTRY (loaded once, at process start)                       │
│  importlib.metadata.entry_points(group="databasise.parts")           │
│  name@version → {schema, effects[], socket types, execution hints}   │
└───────────────────────────────┬──────────────────────────────────────┘
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  VALIDATOR  (CONTRACT §1/§2/§3/§13 — Falsifier 2's own deliverable)   │
│  1. parse nodes against NodeKind tagged sum (pydantic discriminated  │
│     union) — one pass, every violation returned with a JSON-Pointer  │
│  2. cycle detection over `deps` (Tarjan SCC) — cycle reported as     │
│     data {cycle:[...]}, never a raised interpreter fault             │
│  3. depth = min-reduce over the SCC-condensation DAG (taint rule)    │
│  4. execution_mode derived from each node's declared effects[]       │
│  5. socket-type check across every `deps` edge (§13.2)               │
└───────────────────────────────┬──────────────────────────────────────┘
                                 ▼  (frozen at load — CONTRACT §11)
┌──────────────────────────────────────────────────────────────────────┐
│  RUNNER / SCHEDULER  (this document's own design, see Patterns)      │
│  graphlib.TopologicalSorter drives readiness ordering;               │
│  asyncio.TaskGroup executes one "ready batch" as sibling tasks;      │
│  execution_mode picks the task's backing primitive (coroutine /      │
│  subprocess / confined-unit / long-lived-service handle);            │
│  budget token metered at each node's declared boundary only —        │
│  intra-node concurrency is the node's own business (CONTRACT §9)     │
└───────┬───────────────────────────────────────────────┬──────────────┘
        ▼                                                ▼
┌──────────────────────┐                     ┌────────────────────────┐
│ MACHINE-OWNED STORES  │                     │ IDENTITY / KEYING       │
│ KV · graph · vector · │◀────namespace──────│ config_hash = SHA-256(  │
│ lexical · blob (embed-│     derivation      │   RFC8785(input))       │
│ ded: SQLite / Cozo)   │                     │ instance = (name@ver,  │
└───────────┬───────────┘                     │   config_hash, deps)   │
            ▼                                 └────────────────────────┘
┌──────────────────────────────────────────────────────────────────────┐
│  ARTIFACT REGISTRY (gigabyte-sized, deletion-capable, CONTRACT §7)   │
│  content-hash-addressed blob store on disk (git-object-store style)  │
│  + SQLite index row per entry (namespace/scope, SA-2 stamps, corpus) │
└───────────────────────────────┬──────────────────────────────────────┘
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LEDGER (byte-sized, append-only, never deleted, CONTRACT §6/§7)     │
│  SQLite INSERT-only table; "active pointer" = a derived query over   │
│  the log, never an independently-written field — the log always wins│
└──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Part registry | Discover installed parts, expose `name@version → schema/effects` | `importlib.metadata.entry_points(group=...)`, resolved once at process start, cached in a dict |
| Validator | Turn wiring JSON into a typed, depth-stamped, execution-mode-stamped graph; refuse or report every defect in one pass | `pydantic` discriminated union for `NodeKind`; hand-rolled Tarjan SCC for cycle detection; SCC-condensation min-reduce for depth |
| Runner/scheduler | Execute a validated graph, respecting `deps`, fan-out concurrency, budget, and `execution_mode` placement | `graphlib.TopologicalSorter` (readiness) + `asyncio.TaskGroup` (structured concurrency, 3.11+) |
| Identity/keying | Produce the frozen `(name@version, config_hash, resolved_dependency_ids)` tuple and the runtime-minted-instance hash formula | `rfc8785` (RFC 8785 JCS) + `hashlib.sha256` |
| Machine-owned stores | Own KV/graph/vector/lexical/blob primitives behind `effects[]` | Embedded engines only (Cozo already in v1; SQLite for KV/relational; no server processes) |
| Artifact registry | Content-addressed, deletion-capable storage for `shared`/`quarantined`/`self_storage` artifacts | Disk blob store keyed by hash (git-loose-object layout) + SQLite metadata index |
| Ledger | Append-only promotion record; the single source of truth the active pointer projects from | SQLite table, `INSERT`-only, monotonic `id`, "current" resolved by `ORDER BY id DESC LIMIT 1` |

## Recommended Project Structure

```
databasise/
├── identity/                # config_hash, instance-hash, JCS canonicalization
│   ├── canon.py              # wraps rfc8785 + hashlib.sha256
│   └── instance.py           # (name@version, config_hash, deps) tuple + runtime-minted formula
├── parts/
│   ├── registry.py           # importlib.metadata.entry_points loader, name@version -> Part
│   └── schema.py              # NodeKind tagged sum as pydantic discriminated union (CONTRACT §2/§13)
├── validator/
│   ├── parse.py               # one-pass JSON -> typed graph, JSON-Pointer error accumulation
│   ├── cycles.py               # Tarjan SCC, {cycle:[...]} as data
│   ├── depth.py                # SCC-condensation min-reduce over {opaque,evidence,stage}
│   └── execution_mode.py       # effects[] -> {in-process,subprocess,confined-unit,long-lived-service}
├── runner/
│   ├── scheduler.py            # graphlib.TopologicalSorter + asyncio.TaskGroup driver
│   ├── placement.py            # execution_mode -> task backing primitive
│   └── budget.py                # per-node spend/wall-clock metering, multiplicative fan-out accounting
├── stores/
│   ├── kv.py / graph.py / vector.py / lexical.py / blob.py   # effects[]-gated store adapters
├── registry_artifact/
│   ├── blob_store.py            # content-hash-addressed disk layout (fan-out dirs, git-style)
│   └── index.py                  # SQLite metadata rows (namespace, SA-2 stamps, corpus, space_id)
├── ledger/
│   └── ledger.py                  # append-only SQLite table + active-pointer projection query
└── seam/                          # §18 REST + MCP surface (out of this document's scope)
```

### Structure Rationale

- **`identity/` sits at the bottom of the dependency graph on purpose.** Every other module — the validator's instance identity, the runner's cache-partition key, the artifact registry's namespace, the ledger's arm-instance hashes — reads from it. Building it first and freezing its output shape early avoids re-hashing churn later (`CONTRACT §1`'s own warning: "re-hashing byte-identical input after a defaulted-option change has already destroyed in-flight A/B baselines").
- **`parts/registry.py` is a thin discovery layer, not a plugin framework.** It does one thing: turn installed packages into a `name@version → Part` dict at process start. No hook dispatch, no lifecycle machinery — the wiring graph itself is the only thing that decides what runs when.
- **`validator/` is four small, independently testable passes**, not one monolith function — this mirrors the contract's own "return every violation from a single validation pass at once" requirement (§1): each pass can be unit-tested against a fixed wiring fixture without executing anything.
- **`runner/` is deliberately thin.** It does not reimplement Airflow/Dagster/Prefect-shaped scheduling (DAG persistence, retries-as-a-service, a control-plane database) — see Anti-Patterns. It is a library call, not a process.
- **`registry_artifact/` and `ledger/` are separate modules even though both could live in "the database"** — they have different growth/retention shapes (`CONTRACT §7`: registry is byte-sized and never deleted, artifact registry is gigabyte-sized and deletion-capable), and conflating them would make the never-delete guarantee on one accidentally depend on the deletion logic of the other.

## Architectural Patterns

### Pattern 1: TopologicalSorter-driven TaskGroup execution

**What:** Use `graphlib.TopologicalSorter` purely for readiness bookkeeping (which nodes' predecessors are all `done()`), and `asyncio.TaskGroup` purely for running one "ready batch" concurrently with structured-concurrency failure semantics (one task's exception cancels its siblings via `except*`, no orphaned tasks). The two stdlib pieces are complementary, not competing: the sorter never touches the event loop, `TaskGroup` never touches dependency state.

**When to use:** Every wiring run. This is the default execution path for the `fanout`/`join`/plain-DAG shape. `fixpoint` nodes wrap a sub-DAG in their own bounded loop (the executor, not the component, owns the halt condition per `CONTRACT §2`) — same sorter/TaskGroup pattern re-entered per iteration, with the loop's own budget check (`CONTRACT §9`) as the exit condition alongside convergence.

**Trade-offs:** Pro — zero new dependencies, `except*` gives exact per-branch failure attribution for free (feeds `cross_process_failure_cause`, `RIG §TR.1`), and `TopologicalSorter.static_order()`/`get_ready()` already exposes exactly the "declared executor property" the contract requires (whether branches ran concurrently is observable, not assumed). Con — `TaskGroup` requires Python 3.11+; no retry/backoff built in (must be layered per-node explicitly, matching the contract's own view that retry is wiring content — a CRAG-style loop — not scheduler magic).

**Example:**
```python
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

### Pattern 2: SCC-condensation depth computation (the taint rule as a lattice fixpoint)

**What:** Depth (`{opaque, evidence, stage}`) is defined as the minimum over a node's *transitive* `deps` (`CONTRACT §3`), and cycles are legal wiring content, not a validator error. A single topological pass cannot compute this directly once cycles exist, because a plain topo-order does not exist for a cyclic graph. The proven fix is the standard compiler technique: run Tarjan's strongly-connected-components algorithm first, treat each SCC as one condensed node (a cycle's members are mutually reachable, so by the taint rule's own "minimum over transitive deps" definition they must all resolve to the same effective depth — the minimum over the whole SCC plus its external deps), topologically order the condensation DAG (`graphlib.TopologicalSorter` again — the condensation is always acyclic by construction), and min-reduce depth across it in one linear pass.

**When to use:** Once, at validation time, over the load-frozen wiring snapshot. This is Falsifier 2's own deliverable — depth "computed statically from wiring + registry alone."

**Trade-offs:** Pro — O(V+E), no iterative worklist needed (unlike a general dataflow fixpoint, the SCC-condensation trick collapses this to one linear pass because the depth lattice's meet operation is simply `min`). Con — Tarjan's SCC has no stdlib implementation; it is ~30 lines of well-known code and is the one piece of this whole document that is not "reach for the standard library first" — `networkx.strongly_connected_components` is the honest alternative if the codebase already needs a graph-algorithms dependency for other reasons, but adding it solely for this one function is not justified for a single 30-line, extensively-documented algorithm.

**Example (shape only):**
```python
# 1. sccs = tarjan(deps)                      # list of node-id sets, cycle members grouped
# 2. condensation = {scc_id: {scc_of(d) for n in scc for d in deps[n]} - {scc_id}}
# 3. order = list(graphlib.TopologicalSorter(condensation).static_order())
# 4. for scc_id in order:  # leaves (no deps) first
#        depth[scc_id] = min([own_depth(n) for n in scc] +
#                             [depth[condensation_dep] for condensation_dep in condensation[scc_id]])
```

### Pattern 3: Content-addressed artifact store + append-only ledger (git-object-store shape)

**What:** Two structurally different persistence needs, both already named in the contract, map onto one well-worn pattern each:
- **Artifact registry** (`CONTRACT §7`): content-hash-addressed, gigabyte-sized, deletion-capable → a disk blob store keyed by hash with a fan-out directory layout (`ab/cd/abcd1234...`, exactly Git's own `.git/objects` layout, chosen to avoid one huge flat directory), plus a SQLite row per entry carrying the metadata the registry MUST record (namespace/scope, SA-2 sub-recipe stamps, corpus, `space_id`, producing instance). Deletion (GC, tombstoning) is deleting rows and unlinking blobs — never mutating a row in place.
- **Ledger** (`CONTRACT §6`/`§7`): byte-sized, append-only, never deleted → a plain SQLite table with `INSERT`-only writes and a monotonically increasing `id`. "The active pointer" is never its own writable column — it is always `SELECT ... WHERE mutation_id = ? ORDER BY id DESC LIMIT 1`, which is the literal Python expression of the contract's own "the ledger append **is** the promotion decision; the active pointer is a projection derived from the ledger, not an independent record."

**When to use:** Both from the first phase that produces a promotable artifact or a ledger record — the ledger table exists before Phase 1's A/A calibration run needs to record anything, even though the first real promotion doesn't happen until Phase 2.

**Trade-offs:** Pro — no external DB server (SQLite is embedded, matches the "no external DB servers, no Docker" constraint directly), the git-object-store shape is a battle-tested pattern with a well-understood failure mode (partial writes are detectable by re-hashing on read), and separating blob bytes from metadata rows keeps the byte-sized ledger table small even as the gigabyte-sized artifact store grows. Con — SQLite's single-writer lock means the ledger append path needs WAL mode and short transactions if the runner is highly concurrent; this is a known, well-documented tuning knob, not an open design question.

**Example:**
```python
# Artifact write (content-addressed, never overwritten):
h = hashlib.sha256(artifact_bytes).hexdigest()
path = blob_root / h[:2] / h[2:4] / h
if not path.exists():                      # identical content already stored -> no-op, not a collision
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(artifact_bytes)
registry_db.execute(
    "INSERT INTO artifacts(hash, namespace, scope, sa2_stamps, corpus_id, space_id, producer) "
    "VALUES (?,?,?,?,?,?,?)", (h, namespace, scope, json.dumps(sa2), corpus_id, space_id, producer))

# Ledger append (append-only; active pointer is a query, not a write):
ledger_db.execute(
    "INSERT INTO ledger(mutation_id, class, parent, verdict, promotion_provenance, ...) VALUES (?,...)", (...))
# active = SELECT * FROM ledger WHERE mutation_id=? ORDER BY id DESC LIMIT 1
```

## Data Flow

### Wiring-to-run flow

```
wiring.json (inert)
    ↓ parse
NodeKind-tagged, typed graph  ──(pydantic discriminated union)
    ↓ validate (single pass, JSON-Pointer errors)
cycle-checked graph ──(Tarjan SCC; {cycle:[...]} reported as data)
    ↓
depth-stamped, execution_mode-stamped graph ──(SCC-condensation min-reduce; effects[]→mode)
    ↓ freeze (load-time snapshot, CONTRACT §11 — no mid-run reads of mutable state)
runner (TopologicalSorter + TaskGroup)
    ↓ per-node execution, effects[]-gated store access
machine-owned stores (KV/graph/vector/lexical/blob)
    ↓ writes_artifact only
artifact registry (content-hash keyed, scope-tagged shared/quarantined/self_storage)
    ↓ only at promotion (never at run time)
ledger (append-only; active pointer = derived query)
```

### Identity/keying flow

```
author-supplied config JSON
    ↓ RFC 8785 canonicalize (rfc8785 package)
canonical UTF-8 bytes
    ↓ SHA-256
config_hash
    ↓ combine with (name@version, resolved_dependency_ids)
instance identity tuple  ──used as──▶  cache partition key (§1 D7)
                          ──used as──▶  artifact namespace component (§RUN.1)
                          ──used as──▶  ledger arm-instance hash (§7)
```

### Key Data Flows

1. **Validate-then-freeze-then-run.** The validator's output is a load-time snapshot; nothing downstream (runner, ledger, artifact registry) re-reads mutable decision state mid-run (`CONTRACT §11`'s plane rule) — this is a hard boundary, not a convenience: any design that has the runner querying the ledger or scoreboard while a run is in flight violates the frozen contract, not just this document's recommendation.
2. **Depth flows forward, never backward.** Once computed at validation time, depth and `execution_mode` are stamped data carried alongside each node through execution and into the trace/ledger — the runner never recomputes them, and no downstream component (gate, scoreboard) is allowed to treat a runtime observation as evidence for a different depth than the validator assigned.
3. **Two disjoint write paths converge at the ledger only through promotion.** A run writes to machine-owned stores and (conditionally, at `stage` depth) the artifact registry; only an explicit `promote` verb (`CONTRACT §5`'s five-verb gate ladder) appends to the ledger. Running an arm never touches the ledger — this is worth over-stating because it is the single easiest invariant to accidentally violate by convenience-wiring a "record every run" call into the executor.

## Scaling Considerations

Not a users-at-scale system — the load axes that actually matter here are graph width (fan-out arity), corpus size, and comparison batch width (N arms against one baseline, `RIG §RUN.3`).

| Concern | Small (single wiring, ≤10 nodes, dev loop) | Medium (Phase 2–3 parity runs, batch of N arms) | Large (Phase 4 side-by-side, two full modalities) |
|---------|---------------------------------------------|--------------------------------------------------|------------------------------------------------------|
| Runner concurrency | Sequential is fine; TaskGroup batch of 1 | TaskGroup batches per ready-set; budget metering matters | Multiplicative fan-out budgeting (`§9`) becomes load-bearing — N-way spend must be N independent allocations, verified, not assumed |
| Artifact store | Flat SQLite file + a handful of blob files | Fan-out directory layout starts paying off (avoid one huge flat dir) | GC/tombstoning (retention tiers, `§7`) becomes necessary, not optional |
| Ledger | Single SQLite file, no contention | WAL mode, short transactions | Batch-promotion (`RIG §PR.4`) and epoch-level FDR correction read the ledger in bulk — index on `mutation_id`, `class`, `id` |
| Validator | Runs in milliseconds, re-run on every edit | Cache the part-registry lookup (loaded once at process start, not per-validation) | Same — validation cost does not grow with corpus size, only with node count, which stays small even at Phase 4's 13-node HippoRAG wiring |

### Scaling Priorities

1. **First real pressure point: SQLite write contention on the ledger** once batch promotion (`RIG §PR.4`) and concurrent arm runs land in Phase 2+. Mitigate with WAL mode and keeping ledger transactions to a single `INSERT` — do not reach for a second database engine before measuring actual contention.
2. **Second: artifact registry disk layout** once Phase 3 admits `codebase-memory-mcp` and LightRAG's ingest core as opaque nodes producing real `quarantined` artifacts at corpus scale — the git-style fan-out directory layout should be in place *before* this phase, not retrofitted after a flat directory becomes unusable.

## Anti-Patterns

### Anti-Pattern 1: Reaching for a "real" orchestrator (Airflow/Dagster/Prefect/Temporal)

**What people do:** Seeing "runner, scheduler, DAG execution" and reaching for a workflow-orchestration platform because it is the familiar answer to "I need to run a graph of tasks."

**Why it's wrong:** Every one of these requires either an external server/scheduler process, a metadata database server, or both — directly violating the project's own stated constraints (`PROJECT.md`: "embeddable-first, local NixOS runtime," "no external DB servers," "no Docker"). They also each bring their own opinionated notion of task identity, retry, and persistence that would have to be forced to match `CONTRACT.md`'s own frozen identity/effects/depth model rather than reused — the orchestrator's DAG is not this contract's wiring, and bridging the two adds a translation layer with no payoff.

**Do this instead:** `graphlib.TopologicalSorter` + `asyncio.TaskGroup`, as detailed in Pattern 1 — a library, not a service, exactly matching the "micro-orchestrator" shape the wider Python ecosystem has independently converged on for this exact embeddable-DAG-in-one-process problem (Apache Hamilton is the clearest named precedent, already integrated with Haystack in production).

### Anti-Pattern 2: Treating node ids as instance identity

**What people do:** Using a wiring's node id (a JSON object key like `"chunk"` or `"embed"`) as a cache key, a registry key, or an equality check for "is this the same component."

**Why it's wrong:** `CONTRACT §1` states this explicitly as a measured failure mode: "node ids are positions in the wiring and MUST NOT be treated as instance identities — two nodes MAY share the same `component@version` with identical config as legitimate fan-out, and a validator that keys nodes by instance identity silently drops one branch." Any code path that uses `nodes[node_id]` as a dict key for caching, dedup, or artifact lookup reproduces this exact bug.

**Do this instead:** Always key by the frozen `(name@version, config_hash, resolved_dependency_ids)` tuple (or its hash) — never the wiring-local node id. The node id is only ever a lookup key *into the wiring itself* (for `deps` resolution), nothing downstream of validation.

### Anti-Pattern 3: A second schema-validation engine alongside pydantic

**What people do:** Adding the `jsonschema` package to validate wiring JSON against a hand-written JSON Schema document, then *also* parsing the validated JSON into pydantic models for use in code — running the same structural check twice, in two different type systems, that can drift out of sync.

**Why it's wrong:** `CONTRACT §2` already specifies the tagged-sum representation in terms directly matching a pydantic discriminated union ("stated in a portable vocabulary such as serde external tagging or a pydantic discriminated union"). Pydantic v2's own `model_validate_json` performs the structural check *and* produces the typed object the validator's later passes (cycle detection, depth, execution_mode) need to operate on — a separate JSON Schema pass adds a second source of truth for the same shape with no additional guarantee. `pydantic`'s `.model_json_schema()` can still emit a JSON Schema document for external tooling/publication if one is needed, without a second validation pass at runtime.

**Do this instead:** One schema, expressed once, as pydantic models; JSON Schema (if needed for documentation or external tooling) is generated *from* those models, never maintained as a parallel hand-written artifact.

## Integration Points

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Validator ↔ Part registry | Direct in-process call (`registry.lookup(name, version) -> Part`) | Registry is loaded once, read many times; no live network or file re-scan per validation |
| Runner ↔ Machine-owned stores | Only through a node's declared `effects[]` — the runner never grants a capability a node did not declare (`CONTRACT §2`'s undeclared-is-denied rule) | Store adapters should refuse a call from a node whose declared `effects[]` don't cover it, as a second enforcement layer beneath the validator's own check |
| Runner ↔ Artifact registry | `writes_artifact` only, gated by effective depth == `stage` for the `shared` scope (`CONTRACT §3`'s blast-radius rule) | The blast-radius check belongs in the artifact-write path itself, not only in the validator — depth is stamped data by the time a node runs, so the write path can assert it cheaply |
| Runner ↔ Ledger | No direct connection — only the gate's `promote` verb (`CONTRACT §5`) writes to the ledger | Keeping the runner with zero ledger-write capability is the simplest way to guarantee "running an arm MUST NOT append to the ledger" holds structurally, not just by convention |
| Identity/keying ↔ everything else | Pure functions, no I/O, no shared mutable state | Should be the easiest module in the codebase to unit-test exhaustively (canonicalization edge cases: int/float collapse, int64 boundary) since `CONTRACT §1` calls these out by name as load-bearing |

## Suggested Build Order (within `§BP` Phase 1)

`SYSTEM-MODEL.md §BP` fixes the four coarse phases and states Phase 1 needs "a runner at all" for the first time — this section is the build's own finer-grained order *inside* that first rung, since the model deliberately stops at coarse phases (D-09/D-12).

1. **Identity/keying module first.** Everything downstream reads from it (cache keys, namespaces, ledger fields); getting the canonicalization edge cases right early avoids invalidating hashes computed by later modules.
2. **Part registry loader second.** The validator cannot resolve a `NodeKind` instance to a schema without it; trivial in isolation (no wiring-graph logic yet), so it unblocks the validator with minimal risk.
3. **Validator third — this is Falsifier 2's actual deliverable.** Build cycle detection and depth computation as two separately testable functions before wiring them into one pass; test both against the three named wirings (`decomposed lightrag-local`, `opaque codebase-memory-mcp`, `half-decomposed full LightRAG`) the falsifier experiment itself names.
4. **Minimal runner fourth — only as wide as Falsifier 5 needs.** The first A/A calibration run (`RIG §AA.1`) needs *something* executing the three named wirings, but does not need the full budget/execution_mode-driven process-placement machinery yet — a TopologicalSorter+TaskGroup runner that always executes in-process is sufficient to produce real trace data for calibration; subprocess/confined-unit/long-lived-service placement is earned in Phase 2+ as real opaque-node admission (`§8`) makes it necessary.
5. **Artifact registry + ledger fifth**, sized to record Phase 1's own eval-bundle/A/A-calibration output — the full three-scope (`shared`/`quarantined`/`self_storage`) namespace logic is not exercised for real until Phase 2's first decomposition and Phase 3's opaque-node admission, but the schema should be stood up now so trace/ledger records have somewhere to land from the start.

This order is chosen so each step's own tests can run against the previous step's real output rather than a stub — the identity module has no dependencies to stub, the registry loader only needs the identity module, and so on up the chain.

## Sources

- [Coroutines and Tasks — Python 3.14 documentation (asyncio.TaskGroup)](https://docs.python.org/3/library/asyncio-task.html) — HIGH (stdlib docs)
- [graphlib — Python 3 documentation](https://docs.python.org/3/library/graphlib.html) — HIGH (stdlib docs)
- [Planning parallel downloads with TopologicalSorter — Simon Willison](https://til.simonwillison.net/python/graphlib-topologicalsorter) — MEDIUM (worked example, confirms the get_ready()/done() parallel-batch pattern)
- [asyncio TaskGroup Patterns: The Complete 2026 Guide](https://www.pyblog.in/programming/asyncio-taskgroup-patterns-the-complete-2026-guide/) — MEDIUM (web, current)
- [Modern AsyncIO Patterns in Python — TaskGroup, anyio, and What Changed](https://blog.rajpoot.dev/posts/python/asyncio-patterns-taskgroup-anyio-2026/) — MEDIUM (web, current)
- [rfc8785 — pure-Python RFC 8785 implementation, trailofbits](https://github.com/trailofbits/rfc8785.py) — HIGH (matches `CONTRACT §1`'s config_hash requirement exactly)
- [RFC 8785 — JSON Canonicalization Scheme (JCS), IETF Datatracker](https://datatracker.ietf.org/doc/rfc8785/) — HIGH (spec itself)
- [Content-addressable storage — Wikipedia](https://en.wikipedia.org/wiki/Content-addressable_storage) — MEDIUM (background)
- [Git's database internals I: packed object store — The GitHub Blog](https://github.blog/open-source/git/gits-database-internals-i-packed-object-store/) — MEDIUM (the git-object-store pattern this document adapts for the artifact registry)
- [Using importlib.metadata — Python documentation](https://docs.python.org/3/library/importlib.metadata.html) — HIGH (stdlib docs)
- [Python entry points — DEV Community](https://dev.to/borisuu/python-entry-points-1idk) — MEDIUM (confirms pluggy itself is built on entry_points, supporting the "entry_points alone is sufficient" recommendation)
- [Apache Hamilton — GitHub](https://github.com/apache/hamilton) — MEDIUM (named precedent for embeddable, no-server, library-only DAG execution, already integrated with Haystack in production)
- `docs/system-model/CONTRACT.md` §1, §2, §3, §5, §6, §7, §8, §9, §11 — HIGH (docs-verified, frozen project source of truth)
- `docs/system-model/RIG.md` §RUN, §TR, §PR — HIGH (docs-verified, frozen project source of truth)
- `docs/system-model/SYSTEM-MODEL.md` §BP, §H1 — HIGH (docs-verified, frozen project source of truth)

---
*Architecture research for: Databasise 2.0 implementation architecture (runner/scheduler, storage keying, registries, wiring validation)*
*Researched: 2026-08-29*
