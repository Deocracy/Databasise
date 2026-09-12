# Phase 1: Machine Core - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-29
**Phase:** 1-Machine Core
**Areas discussed:** Depth machinery boundary, Stores & namespace isolation, Runner & concurrency fence, Identity inputs & package shape

---

## Depth machinery boundary

### Phase 1 / Phase 2 seam

| Option | Description | Selected |
|--------|-------------|----------|
| Computation here, evidence there | Phase 1 builds the full depth computation as a library; Phase 2 adds §19.10's boundary enumeration, the three named wirings, and the Falsifier 2 evidence run | ✓ |
| Minimal enforcement only | Phase 1 enforces blast-radius at the write path with per-node depth, no transitive taint; Phase 2 builds the whole validator | |
| Everything in Phase 1 | Move MACH-01 out of Phase 2 entirely | |

**User's choice:** Computation here, evidence there.
**Notes:** Raised because the roadmap assigns MACH-01 to Phase 2, but Phase 1's own success criterion 4 (an opaque arm cannot reach `shared`) already requires effective-depth taint. The minimal option was flagged as reproducing the laundering hole spike 005 measured.

### What Phase 1 executes wirings with

| Option | Description | Selected |
|--------|-------------|----------|
| Reference parts + named-wiring stubs | Executable `core/` parts for the runner, plus declaration-only registry entries for the three Falsifier-2 wirings | ✓ |
| Executable reference parts only | Named-wiring entries deferred to Phase 2 | |
| Declaration-only, nothing executes | Synthetic in-test parts only, nothing shipped | |

**User's choice:** Reference parts + named-wiring stubs.

### Blast-radius enforcement point

| Option | Description | Selected |
|--------|-------------|----------|
| Both validator and write path | Load-time refusal plus a stamped-depth assertion before any artifact write | ✓ |
| Validator only | Single enforcement point; write path trusts the validated graph | |
| Write path only | Enforce at the point of consequence; validator reports without refusing | |

**User's choice:** Both.

### Spike 005's `taint.py`

| Option | Description | Selected |
|--------|-------------|----------|
| Port the 12 cases, repair the 3 divergences | Carry the case table forward restated in frozen contract vocabulary | ✓ |
| Port the cases and keep taint.py as a differential oracle | Two implementations that must agree | |
| Cite it, write fresh tests from CONTRACT §3 | No inherited vocabulary drift | |

**User's choice:** Port and repair.
**Notes:** The user asked to see spike 005 before answering. Review surfaced three divergences between the prototype and the frozen contract: `writes_quarantined` is not an `effects[]` member; `writes_artifact` is conflated with "writes shared", predating the PARTS-04 D1 transient-write repair; and the harness exempts any case titled `"3."` from its failure count. Also noted as prototype tells: `lru_cache` imported and unused, and no `execution_mode` derivation at all. Reproduced live before the discussion — 12 cases, exit 0.

---

## Stores & namespace isolation

### Engine ownership

**User's choice (free text, not from options):** "Cozo+Faiss is what Databasise is currently built on and I would like it to stay that way."

**Notes:** This area was interrupted twice by fact-checking. The user first challenged the presence of SQLite ("why is there sqlite we are using duckdb i thought"), then flagged that FAISS was missing from my account of the stores. Both challenges were correct in substance:

- DuckDB appears exactly three times in the whole repository, all illustrative — CONTRACT §15 naming it as an engine *a part* might embed for itself, and a spike-004 version-skew example. It was never a decision. Confirmed against all 984 files, all extensions, and `git log --all -S`.
- FAISS is the fork's **default** vector store, which my first account listed flat among seven backends without saying so. Verified at `v1/lightrag/lightrag.py:278` and `v1/lightrag/api/config.py:66`.
- Six places in the tree still carry upstream LightRAG's defaults and contradict the code, including `.claude/CLAUDE.md`.
- The LanceDB recommendation in `.planning/research/STACK.md:26` was made against a misdescribed incumbent ("faiss-cpu + nano-vectordb pairing"), and that recommendation became EMBED-01.

An earlier three-option question offering LanceDB was withdrawn once the user stated the decision directly.

### KV, lexical, and blob

| Option | Description | Selected |
|--------|-------------|----------|
| SQLite for KV + lexical + bookkeeping | stdlib SQLite for KV, FTS5 lexical, artifact index and ledger; filesystem for blob | ✓ |
| Cozo takes KV too | One fewer engine; SQLite reserved for ledger and index | |
| Keep v1's file-based KV | `JsonKVStorage` carried forward; lexical deferred | |

**User's choice:** SQLite for KV + lexical + bookkeeping.

### Namespace isolation boundary

| Option | Description | Selected |
|--------|-------------|----------|
| One store directory per namespace | Own Cozo DB file and own Faiss index dir per arm, path derived from SA-1 identity | ✓ |
| One store, namespaced inside it | Prefixed relations and tagged metadata in single stores | |
| Split by engine's own grain | Cozo namespaced internally, Faiss per-directory | |

**User's choice:** One store directory per namespace.

---

## Runner & concurrency fence

### `execution_mode` placements

| Option | Description | Selected |
|--------|-------------|----------|
| in-process only, others refuse by name | Derivation still computed and stamped; hosting unbuilt until Phase 5 earns it | ✓ |
| in-process + subprocess now | Exercise cross-process failure recording and SQLite multi-process access early | |
| All four placements | Complete runner; three placements speculative until an opaque node exists | |

**User's choice:** in-process only, others refuse by name.

### Intra-node concurrency (the §H1 handover)

| Option | Description | Selected |
|--------|-------------|----------|
| Per-node semaphore, size enters `config_hash` | Runner-owned bound, declared in node config, so the concurrency setting is part of instance identity | ✓ |
| No cap — boundary metering only | Exactly CONTRACT §9's V-7 minimum and nothing more | |
| One process-wide cap | v1's `_global_concurrency_limits` approach | |

**User's choice:** Per-node semaphore with the size in `config_hash`.
**Notes:** The deciding argument was RIG §AA.1 — the concurrency setting is part of the A/A null's identity and two runs under different settings must not be pooled, so folding the cap into `config_hash` makes that structural rather than remembered. The process-wide option was flagged as both the singleton PITFALLS 7 forbids and a Phase 6 contamination risk, since one arm's fan-out would throttle another arm beside it.

### Run-record fields for the gate's refusals

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 1 stamps the full set | determinism/concurrency setting, per-node `cache_hit`, `arm_execution_order`, `realised_budget_share`, guards fired | ✓ |
| Minimal now, extend in Phase 2 | Only what Phase 1's own reference parts exercise | |
| Trace is entirely Phase 2's | Whole §TR schema lands with the eval bundle | |

**User's choice:** Phase 1 stamps the full set.
**Notes:** Raised because §5's refusal conditions 8, 10 and 11 are evaluated against exactly these fields; without them a confounded comparison returns a normal verdict, which the contract calls worse than a refusal. Noted that MACH-05's definition of done does not currently include them.

---

## Identity inputs & package shape

### Environment hash

| Option | Description | Selected |
|--------|-------------|----------|
| Machine-computed resolved-closure digest | `importlib.metadata` dist names, versions, wheel hashes, plus Python version and platform | ✓ |
| Nix store closure hash as an input | Genuinely the whole resolved closure on this host | |
| Lockfile digest | Hash `uv.lock` | |

**User's choice:** Machine-computed resolved-closure digest.
**Notes:** The Nix option was presented with its own disqualifier — spike 004 holds that Nix is substrate-only and store paths are never identity. The lockfile option was flagged as the declared-vs-resolved error §1 names D1 for making.

### Part discovery

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit in-code registry | A dict mapping `name@version` to a Part | ✓ |
| `importlib.metadata` entry_points | The research recommendation and conventional Python answer | |
| Both | In-code for core, entry_points for external | |

**User's choice:** Explicit in-code registry.

### Package shape

| Option | Description | Selected |
|--------|-------------|----------|
| New top-level `databasise/`, port by copy, never import | Nothing imports from `v1/`; attribution via `upstream_ref` | ✓ |
| New `v2/` mirroring `v1/` | Same isolation, milestone-shaped naming | |
| Build incrementally inside `v1/` | Grow the machine in place, deleting as you go | |

**User's choice:** New top-level `databasise/`, port by copy, never import.
**Notes:** Chosen partly because it makes PITFALLS 1 and 7 structurally impossible — with no import path to `shared_storage.py`, its singletons cannot leak into the machine. The in-place option was measured against: `v1/` carries 26,080 lines of server-only storage backends against 4,929 embedded, plus 7.2M of compiled React bundled inside the Python package, all of which would sit on the import path throughout.

---

## Claude's Discretion

- Structured-concurrency mechanism inside the runner (`graphlib.TopologicalSorter` + `asyncio.TaskGroup` is the researched default)
- RFC 8785 canonicalisation library choice
- Blob-store fan-out depth and artifact-registry table schema
- Reference-part internals beyond the four named roles
- Test structure and fixture layout

## Deferred Ideas

- **Requirement corrections:** EMBED-01 and ROADMAP Phase 1 criterion 1 name LanceDB and need amending to Cozo + Faiss + SQLite; MACH-05's definition of done omits the run-record fields
- **The recovered fact layer** — `/wiki/resolve` with `as_of`, contradictions, vocab, claims with provenance. Lost in the destructive incident, reconstructed in `.planning/RECOVERED-FACT-LAYER.md`; touches Phase 4's §18 envelope
- **DR-05** deferral rests on reasoning now known to be incomplete
- **`v1/lightrag/evaluation/`** — prior art for Phase 2's eval bundle, in no requirement
- **`v1/lightrag/sidecar/`** — unexamined subsystem, in no requirement
- **Multimodal/VLM** — built in v1, off by default, in no requirement
- **Four LLM roles** — exist in v1, no v2 equivalent concept
- **DuckDB** for Phase 2+ scoreboard/trace analytics only
- **`entry_points`** part discovery if an external party ever authors a part
- **`lmdb`** as a KV escalation path only on measured contention

## Session note

This discussion was interrupted by the discovery that a destructive incident on another machine had deleted a Databasise subsystem (`version_routes.py` and the fact layer beneath it) with no recoverable server code anywhere. Roughly half the session went to establishing what was lost, what survived, and what could be reconstructed. That work is recorded in `.planning/RECOVERED-FACT-LAYER.md` and is not repeated here.
