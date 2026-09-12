# Phase 5: Opaque-Side Admission - Research

**Researched:** 2026-09-08
**Domain:** Opaque-node admission (CONTRACT §8/§17), ingest/delete/status product surface (API-01/02/06/07), MCP transport
**Confidence:** MEDIUM — the admission conditions and most of the code seams are HIGH confidence (read verbatim from CONTRACT.md and the live `databasise/` tree); the two genuinely open design questions (DR-04, the five sandbox-candidate engines) are LOW confidence and are surfaced below as explicit OPEN DECISIONs rather than silently resolved, per this phase having no CONTEXT.md.

<user_constraints>
## User Constraints (from CONTEXT.md)

**No `05-CONTEXT.md` exists for this phase — `/gsd-discuss-phase` was not run.** There are no
locked decisions, discretion areas, or deferred ideas to copy forward. This RESEARCH.md is
therefore the primary design input for `/gsd-plan-phase`; every place a discuss-phase would
normally have locked a choice is instead flagged below as an **OPEN DECISION** with a recommended
default and the evidence for it. The planner and/or a checkpoint should confirm these before
they harden into plan tasks.

**Project Constraints (from `.claude/CLAUDE.md`), treated as locked:**
- D4 One Machine architecture — one executor, no sandbox regime; an opaque node is a node kind,
  not a hosting tier. Not re-litigated.
- Python only; no Docker; no external DB servers; local NixOS, embeddable in-process.
- The §18 seam must stay modality-agnostic — nothing this phase adds may put a modality-specific
  field in the envelope or a modality-specific tool on the MCP/REST surface (§18.3/§18.5).
- GSD workflow enforcement: file-changing work happens through `/gsd-execute-phase`, not ad hoc.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MODAL-02 | LightRAG's ~1,786-line ingest core admitted opaque under §8, output `quarantined`, inside-vs-across-boundary change rule + compat test, DR-04 decided | §8/§17 conditions quoted below; existing `quarantined`-scope machinery in `databasise/`; subprocess-boundary precedent (`v1_driver_script.py`) that MODAL-02's real Part body must follow; DR-04 OPEN DECISION with recommendation |
| MODAL-03 | codebase-memory-mcp admitted whole-engine, verdict per condition, Falsifier 4 both legs | §X already ran all eleven verdicts at the docs level (`PARTS.md ## §X`) — this phase's job is to encode that verdict table as an executable `Part` registration, not re-derive it |
| MACH-04 | Injected-LLM-endpoint survey across five sandbox-candidate engines (Falsifier 8, non-gating) | OPEN DECISION: the five engines are not enumerated anywhere in the docs tree found by this research; a recommended default list is given |
| API-01 | Ingest documents (raw + structured) with async job status polling | v1's own `DocStatusStorage`/`pipeline_status` shared-storage mechanism already provides exactly this; reuse, do not build a second job-tracking system |
| API-02 | Delete a document, graph-aware cleanup, no orphaning survivors | v1's `adelete_by_doc_id` (`v1/lightrag/lightrag.py:3111`) already implements source_id-set-subtraction reference counting for entities/edges — cite and preserve this algorithm |
| API-06 | Health, corpus status, document counts — bounded/paginated, never a full dump | New engine methods following the existing `Databasise.resolve_evidence`/`resolve_trace` thin-method pattern |
| API-07 | MCP surface, intention-level tools, capability parity with REST, no modality-specific tool growth | New `mcp` PyPI package (official SDK); mirror `databasise/seam/rest.py`'s thin-adapter pattern; selector-vs-tool test from §18.5 |
| HARD-03 | DR-04 decided either way | OPEN DECISION with recommendation: the two-covering rationale (existing SA-2 registry stamp + §7's partial-coverage refusal) is sufficient; do not add a new per-chunk field |
</phase_requirements>

## Summary

Phase 5 is mostly an **implementation** phase over an admission analysis that already exists on
paper. `PARTS.md ## §X` already ran codebase-memory-mcp's whole-engine admission against all
eleven §8 conditions verdict-by-verdict, at the source-code level, against a pinned clone
(`codebase-memory-mcp@61b3b1b2`) — three rows are already flagged "not clean yeses" in the docs
themselves. Similarly, `databasise/`'s `quarantined` artifact scope, the `mutates_store` effect,
and the MACH-11 seam-level-event mechanism for out-of-`deps` mutations were all built in prior
phases specifically to carry this admission (Phase 1's `namespaces.py`/`registry_artifact/`,
Phase 4's `_mach11_events`). What does **not** yet exist is: (1) a real, executable `Part` body
for LightRAG's ingest core — today it is a `body=None` declaration-only stub
(`databasise/parts_core/declared_only.py`'s `LIGHTRAG_FULL_INGEST_PART`); (2) any `Part`
registration for codebase-memory-mcp beyond the same kind of stub; (3) any job-status, delete, or
corpus-introspection surface on the `Databasise` seam object or its REST/MCP transports.

The single most load-bearing finding: **`databasise/` structurally forbids importing v1's
`lightrag` package in-process** (`databasise/tools/check_import_boundary.py`, enforced by an AST
scan with one named exception). Phase 3 already solved this exact problem for the *query* side by
launching v1 as a subprocess under v1's own pinned interpreter and speaking JSON over
stdin/stdout (`databasise/parity/v1_driver_script.py` + `v1_arm.py`). MODAL-02's real ingest
`Part` body has no other legal way to reach v1's `ainsert()`/`apipeline_process_enqueue_documents`
pipeline — it must follow the identical subprocess pattern, not a direct import. This is not an
optional convenience; it is enforced by a compat test that already exists and that this phase's
own "compat test enforces the inside-vs-across-boundary rule" success criterion can extend rather
than invent from nothing.

The second load-bearing finding: v1's `adelete_by_doc_id` already implements the exact
reference-counting algorithm API-02 asks for — subtracting the deleted document's chunk ids from
each affected entity's/relation's `source_id` set and only deleting the entity/edge outright when
the remaining set is empty, otherwise rebuilding it from the surviving sources. This phase does
not need to invent graph-aware deletion; it needs to admit it, expose it through the seam, and
decide how a query-time mutation against an opaque node's own backing store is classified — which
CONTRACT already answers via the `mutates_store` effect and the `mutable-store` capability,
verbatim-precedented by `codebase-memory-mcp`'s own `manage_adr`/`delete_project`.

**Primary recommendation:** Port the ingest core as a subprocess-backed opaque `Part` (mirroring
`v1_driver_script.py`), register codebase-memory-mcp as a second opaque `Part` from the existing
`PARTS.md ## §X` verdict table, add `mutates_store`-declared delete operations for both (routed
through the already-built MACH-11 seam-event path), reuse v1's own doc-status mechanism for
API-01's job polling rather than building a new one, and add a thin MCP transport mirroring
`rest.py`'s existing thin-adapter shape.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Document ingest (parse, chunk, extract, graph-upsert) | Opaque Part (in-process Python calling out to a v1 subprocess) | Machine (artifact registry, quarantined scope) | The ~1,786-line core stays inside LightRAG's own process/venv; the machine only registers its output artifact |
| Async job status | Opaque Part's own internal state (v1's `doc_status`/`pipeline_status`) | Seam (`Databasise.get_job_status`) | Reuse v1's existing async doc-status tracking; the seam is a thin read-through, not a new state machine |
| Document deletion + graph cleanup | Opaque Part (same subprocess, `mutates_store` effect) | Seam (MACH-11 seam-level event) | The reference-counting logic (source_id subtraction) is v1-internal; the seam only needs to observe and trace the mutation, per CONTRACT's `mutable-store` definition |
| Health / corpus status / doc counts | Seam (`Databasise`) | Store layer (artifact registry, doc-status read) | Bounded, paginated reads — no new opaque-node work; this is ordinary seam-method addition |
| MCP tool surface | Seam-adjacent transport (`databasise/mcp/`) | — | Thin adapter over the same `Databasise` engine object REST already wraps — never a second execution path |
| codebase-memory-mcp admission | Machine (opaque-node admission machinery: `Part.kind="opaque"`, effects, artifact_scope) | — | Whole-engine foreign process; the machine's job is admission bookkeeping, not decomposition |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `mcp` | 2.2.0 (PyPI, released 2026-09-07) | Official Model Context Protocol Python SDK — server + tool registration | This is the canonical SDK published by the protocol's own maintainers (`modelcontextprotocol/python-sdk`); building a hand-rolled MCP framer would duplicate a maintained, spec-conformant implementation [ASSUMED — package name discovered via direct PyPI query this session, not via Context7/official docs fetch; registry existence and metadata (`requires_python>=3.10`, homepage `modelcontextprotocol.io`) are `[VERIFIED: PyPI registry query]` but the recommendation to *use* it is a judgment call, not a docs citation] |
| `python-multipart` | 0.0.32 (PyPI) | Required by FastAPI/Starlette to parse `multipart/form-data` — needed for API-01's raw-document-upload REST endpoint | FastAPI's `UploadFile` silently fails at request time without this installed; it is the documented, standard companion package, not a competing choice [ASSUMED — training-knowledge fact about FastAPI's own dependency graph, package metadata `[VERIFIED: PyPI registry query]`] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `fastapi` / `uvicorn` | already pinned in `[project.optional-dependencies] rest` (Phase 4) | REST transport | Already installed for Phase 4's `/query` endpoints; API-01/02/06 add routes to the same `create_app()` factory, no new dependency |
| `pytest` / `pytest-asyncio` | already pinned (`[dependency-groups] dev`) | Test harness | Unchanged from prior phases |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `mcp` (official SDK) | `fastmcp` (third-party wrapper) | `fastmcp` trades SDK conformance for a friendlier decorator API; the official `mcp` package is the safer default for a contract that must satisfy §18.5's exact tool-growth rule under scrutiny — no attempt was made to evaluate `fastmcp`'s legitimacy this session, so it is not recommended |
| A new job-tracking table | v1's existing `DocStatusStorage`/`pipeline_status` | Building a second async job-status mechanism duplicates what v1's ingest core already does natively (PENDING/PROCESSING/PROCESSED/FAILED, with its own locking) — see Don't Hand-Roll below |

**Installation:**
```bash
# added to [project.optional-dependencies] rest, alongside fastapi/uvicorn:
uv add --optional rest 'mcp>=2.2.0' 'python-multipart>=0.0.32'
```

**Version verification:** confirmed live this session via `curl https://pypi.org/pypi/<pkg>/json`
(no `pip`/`npm` CLI present in this sandbox — the JSON API was used directly as the ecosystem
registry, equivalent evidence to `pip index versions`). `mcp` 2.2.0 published 2026-09-07T16:06:19Z,
`requires_python>=3.10` (compatible with the project's Python 3.10+ floor). `python-multipart`
0.0.32 published 2026-06-04, same `requires_python` floor.

## Package Legitimacy Audit

Ran `gsd_run query package-legitimacy check --ecosystem pypi mcp python-multipart` this session.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `mcp` | PyPI | latest release published same-day (2026-09-07); package itself is the long-established official MCP SDK | unknown (seam reports `null`) | `github.com/modelcontextprotocol/python-sdk` (official) | **SUS** (`too-new`, `unknown-downloads`) | Flagged — planner must add `checkpoint:human-verify` before this install. The `too-new` signal is an artifact of checking the *latest patch release's* publish date, not the package's founding date; the homepage/repo resolve to the protocol's own official domain and GitHub org, which is strong independent evidence of legitimacy, but this session did not independently confirm download counts or founding date, so the seam's verdict stands as recorded. |
| `python-multipart` | PyPI | published 2026-06-04 (not brand-new) | unknown (seam reports `null`) | `github.com/Kludex/python-multipart` | **SUS** (`unknown-downloads` only) | Flagged — planner must add `checkpoint:human-verify` before this install, though this is FastAPI's own long-documented multipart dependency and the flag is solely a download-count blind spot in this environment's checker, not a substantive red flag. |

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** `mcp`, `python-multipart` — both flagged only on the
seam's `unknown-downloads` signal (this sandbox cannot reach a downloads API); the planner must
gate each install behind `checkpoint:human-verify` per protocol, but neither shows a slopsquat
signature (both resolve to their real, official upstream repos).

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────────────────────────┐
                         │   Caller (REST client / MCP client / import) │
                         └───────────────────┬───────────────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │  REST (databasise/seam/rest.py)  MCP (NEW: databasise/mcp/) │
                    └─────────────────────────┬─────────────────────────┘
                                              │  thin adapters, same calls
                                              ▼
                         ┌───────────────────────────────────────┐
                         │  Databasise (databasise/seam/engine.py) │
                         │  existing: query, query_stream,         │
                         │            resolve_evidence, resolve_trace │
                         │  NEW: ingest, get_job_status,           │
                         │       delete_document, health,          │
                         │       corpus_status, document_counts    │
                         └───────┬───────────────────┬─────────────┘
                                 │                    │
                    ingest/delete│                    │query (unchanged,
                    (this phase) │                    │ Phase 3/4 path)
                                 ▼                    ▼
                 ┌───────────────────────────┐   ┌─────────────────────┐
                 │  Opaque Part: lightrag/     │   │ decomposed query    │
                 │  full-ingest (real body,    │   │ wiring (naive/      │
                 │  NEW this phase)            │   │ hybrid/local/global)│
                 │  ─ subprocess → v1's own    │   └─────────────────────┘
                 │    pinned venv, JSON I/O    │
                 │    (mirrors v1_driver_      │
                 │    script.py precedent)     │
                 │  ─ effects: calls_llm,      │
                 │    writes_artifact          │
                 │    (ingest) / mutates_store │
                 │    (delete) — two ports     │
                 │    per §19.6                │
                 └──────────┬──────────────────┘
                            │ writes_artifact → quarantined scope
                            ▼
                 ┌───────────────────────────┐        ┌─────────────────────────┐
                 │ registry_artifact/index.py │        │ Opaque Part:            │
                 │ (existing) — namespace,    │        │ codebase-memory-mcp      │
                 │ SA-2 stamps, scope=        │        │ (NEW registration this   │
                 │ "quarantined"              │        │ phase, from PARTS §X's   │
                 └───────────────────────────┘        │ already-run 11-condition │
                                                        │ verdict table)           │
                                                        │ effects: self_storage,   │
                                                        │ fs / mutates_store       │
                                                        │ (manage_adr/             │
                                                        │ delete_project)          │
                                                        └─────────────────────────┘
```

### Recommended Project Structure

```
databasise/
├── parts_core/lightrag/
│   └── full_ingest.py        # NEW: real Part body, subprocess-backed (replaces the
│                              #      body=None stub in parts_core/declared_only.py)
├── parity/                   # EXISTING — v1_driver_script.py is the pattern to mirror,
│                              #            not reuse directly (parity is read-only/query;
│                              #            ingest needs a write-capable sibling script)
├── mcp/                       # NEW package: MCP server, thin adapter over Databasise
│   ├── __init__.py
│   ├── server.py              # tool registration: ingest, query, delete, status, compare
│   └── tools.py                # per-tool request/response shaping (mirrors seam/rest.py)
├── seam/
│   ├── engine.py               # add: ingest(), get_job_status(), delete_document(),
│   │                            #      health(), corpus_status(), document_counts()
│   └── rest.py                  # add: POST /documents, GET /documents/{id}/status,
│                                #      DELETE /documents/{id}, GET /health, GET /corpus
└── tests/
    ├── parts_core/lightrag/test_full_ingest_compat.py   # inside-vs-across-boundary compat test
    └── mcp/                                              # tool-parity / no-growth tests
```

### Pattern 1: Subprocess-backed opaque Part body

**What:** The ingest core's `Part.body` shells out to a script executed by v1's own pinned
`.venv` interpreter, speaking one JSON object over stdin and one over stdout — never a direct
Python import of `lightrag`.
**When to use:** Any Part whose upstream implementation lives in `v1/` and must stay out of
`databasise/`'s own import graph (`check_import_boundary.py`'s AST scan enforces this structurally
today, for the query side; extending it to cover the new ingest driver script is this phase's own
compat-test work).
**Example:**
```python
# Source: databasise/parity/v1_driver_script.py (existing precedent, query-side)
# and databasise/parity/v1_arm.py's subprocess.run(..., timeout=timeout) launch —
# both read this session, quoted verbatim below.

# v1_driver_script.py's own module docstring states the protocol:
# "Protocol: read one JSON object from stdin — {...} — build v1's LightRAG facade ...
#  run the query, and write one JSON object to stdout: {...}"
# v1_arm.py's launch:
proc = subprocess.run(
    [...],           # v1's own venv python + driver script path
    input=...,        # job JSON on stdin
    capture_output=True,
    timeout=timeout,  # already parameterized — this is §8 condition 4's wall-clock ceiling
)
```
The ingest-side equivalent (net new, not yet written) needs the same shape but for
`ainsert()`/`apipeline_process_enqueue_documents()` plus `adelete_by_doc_id()`, not
`aquery_data()`.

### Pattern 2: `mutates_store` for query-time deletion (CONTRACT §2/§14.4, PARTS §X)

**What:** A query-time-callable operation that overwrites a part's own backing store outside the
`writes_artifact`/§3/§7 shape declares `mutates_store`, not `writes_artifact`.
**When to use:** Document deletion against the ingest core's own quarantined graph/vector data,
and any codebase-memory-mcp mutation (`manage_adr`, `delete_project`).
**Example:**
```python
# Source: docs/system-model/CONTRACT.md §14.4's mutable-store definition (quoted verbatim,
# read this session, lines 625-631):
# "mutates_store (## §2) is checked and denied-by-default exactly like every other effects[]
#  member ... A mutates_store call made outside any wiring's deps graph is traced at ## §18's
#  seam boundary as a seam-level event ... per ## §18.2's envelope shape"
```
The seam-level event mechanism is already built: `databasise/seam/engine.py`'s `_mach11_events`
correlates any node declaring `mutates_store` against its dependency-accounted store keys and
emits a `SeamEvent`. Its own docstring (read this session) states the load-bearing caveat: **no
part registered anywhere today declares `mutates_store`**, so this correlation has only been
proven against test fixtures — Phase 5 is the first phase to exercise it for real, and the plan
must re-verify the correlation rule against a real deleting part rather than assume prior test
coverage already covers this shape.

### Pattern 3: §19.6's separate-port rule for opaque nodes

**What:** For an opaque node, two invocations are separate ports (nodes) whenever they differ in
declared effects — never one port handling both.
**Example (quoted verbatim, `CONTRACT.md §19.6`, read this session):**
> "Where a node's internals are not machine-visible, granularity is decided over its declared
> ports, not its operations: two invocations MUST be separate ports where they differ in emitted
> `ItemKind` set, score semantics, or declared effects, and MUST be one port otherwise."

Ingest (`writes_artifact`) and delete (`mutates_store`) differ in declared effects, so §19.6
settles the design question of whether they should be one Part exposing two operations or two
distinct node registrations: **they must be two separate node/port declarations**, even though
both may be backed by the same underlying subprocess/engine identity. This mirrors
`codebase-memory-mcp`'s own precedent exactly: `index_repository` (writes_artifact-shaped) and
`manage_adr`/`delete_project` (`mutates_store`) are already recorded as distinct effect
declarations on the same whole-engine part in `PARTS.md ## §X`.

### Anti-Patterns to Avoid

- **Importing `lightrag` from inside `databasise/`:** `check_import_boundary.py` already forbids
  this by AST scan; a new ingest Part body that does `from lightrag import LightRAG` directly
  will fail an existing test, not merely violate a style preference.
- **Building a second job-status table:** v1's `doc_status`/`pipeline_status` shared-storage
  mechanism already tracks PENDING/PROCESSING/PROCESSED/FAILED with its own locking
  (`v1/lightrag/pipeline.py`). A new machine-side job table would duplicate state that already
  lives correctly inside the opaque boundary.
- **Returning a full corpus/index dump from the status/health endpoints:** explicitly out of
  scope per ROADMAP criterion 4 and REQUIREMENTS.md's "Out of Scope" list — every status/health
  method must be bounded and paginated by construction, not by convention.
- **A per-modality MCP tool:** §18.5's growth rule — "a second modality that answers an operation
  an existing tool already exposes MUST add no tool" — means the MCP tool set is fixed at five
  intention-level tools (ingest, query, delete, status, compare) regardless of how many modalities
  Phase 6 adds.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async ingest job tracking | A new job-status table/queue | v1's `DocStatusStorage`/`pipeline_status` (`v1/lightrag/pipeline.py`) | Already async, already locked, already tracks exactly the states API-01 needs; it is inside the opaque boundary the machine is admitting anyway |
| Graph-aware deletion / reference counting | A new entity/edge reference-count mechanism | v1's `adelete_by_doc_id` (`v1/lightrag/lightrag.py:3111`) + `subtract_source_ids` (`v1/lightrag/utils.py:4564`) | Already implements exactly API-02's "cleaned up without orphaning survivors" requirement via `source_id` set subtraction; re-verified via `entity_chunks`/`relation_chunks` chunk-tracking stores, not just the graph's own possibly-stale `source_id` field |
| MCP protocol framing | A hand-rolled JSON-RPC/tool-schema layer | `mcp` (official PyPI SDK) | Duplicating a spec-conformant SDK is exactly the kind of speculative complexity a maintained package already solves |
| Multipart upload parsing | Custom `multipart/form-data` parser | `python-multipart` (FastAPI's own documented dependency) | Standard, already-required companion package for `UploadFile` |
| Inside-vs-across-boundary compat checking | A new bespoke checker from scratch | Extend `databasise/tools/check_import_boundary.py`'s existing AST-scan pattern | The exact style of check this phase needs (declared-boundary values pinned, internals free to change) already has a working precedent in this repo |

**Key insight:** almost everything Phase 5 needs already exists somewhere in this codebase —
either as executable machinery from Phases 1/3/4 (`quarantined` scope, `mutates_store`,
`_mach11_events`, the subprocess pattern) or as already-completed analysis in the docs tree
(`PARTS.md ## §X`'s eleven-condition verdict table). The actual net-new work is comparatively
small: wiring these together into real `Part` registrations and seam methods, not inventing new
mechanisms.

## Runtime State Inventory

Not applicable — this is new-capability work (ingest/delete/MCP endpoints), not a
rename/refactor/migration phase. Skipped per the trigger condition in the research protocol.

## Common Pitfalls

### Pitfall 1: Assuming the ingest Part can import v1 directly because it is "just Python"

**What goes wrong:** A plan writes `from lightrag.pipeline import _PipelineMixin` inside
`databasise/parts_core/lightrag/full_ingest.py`.
**Why it happens:** The query side's ported nodes (`databasise/parts_core/lightrag/*.py`) *do*
call v1 utility functions in some cases, and it is easy to assume the same license extends to the
whole ingest pipeline.
**How to avoid:** `check_import_boundary.py` forbids importing `lightrag`/`v1` from anywhere
under `databasise/` except one named subprocess-entry-point exclusion list
(`_SUBPROCESS_ENTRY_POINT_EXCLUSIONS`). The new ingest driver script must be added to that list
by name, exactly as `v1_driver_script.py` already is, and the `Part` body must launch it as a
subprocess.
**Warning signs:** `uv run pytest databasise/tests/test_import_boundary.py` fails immediately if
this is violated — this is a fast, cheap, already-existing detector.

### Pitfall 2: Treating `mutates_store` deletion as if it needed a new envelope field

**What goes wrong:** A plan adds a new `ResponseEnvelope` field for "mutation events" from
scratch.
**Why it happens:** MACH-11's seam-level event mechanism is easy to miss because it currently
fires on zero production parts (its own docstring says so).
**How to avoid:** `_mach11_events` and `SeamEvent` already exist and are already wired into
`Databasise._execute()`. The new deleting Part only needs to declare `mutates_store` correctly;
no envelope schema change is needed.
**Warning signs:** If a plan proposes editing `databasise/seam/envelope.py`'s frozen field set
for this reason, that is very likely the closed-envelope rule (§18.2) being violated.

### Pitfall 3: Registering codebase-memory-mcp with the wrong `feed_tier`/`recipe` framing

**What goes wrong:** Treating `codebase-memory-mcp`'s `index_repository` as though it consumed a
machine-produced chunk feed, because that is the shape every other ingest path in this project
takes.
**Why it happens:** Every other admitted engine in this project (LightRAG) does consume or
produce machine-typed evidence at some boundary.
**How to avoid:** `PARTS.md ## §X` already establishes, code-verified, that `index_repository`'s
only input is a filesystem `repo_path` — it never consumes a machine `text_chunk` feed at all, and
its output never enters the artifact registry (`storage: self-contained`, `Recipe: n/a`). Falsifier
4's "consuming machine chunks" leg is recorded as **possibly not runnable as worded** for exactly
this structural reason — do not plan a task that assumes it can be made to work by minor
plumbing; the finding is that the two-leg design may not distinguish two genuinely different code
paths for a filesystem-only-input engine.
**Warning signs:** A plan task that tries to feed `text_chunk` evidence into `index_repository` is
re-deriving something `PARTS.md ## §X` already found questionable — read that section before
attempting it.

### Pitfall 4: Letting new ingest logic get bolted onto the opaque core instead of a fitted node

**What goes wrong:** Under schedule pressure, new capability (e.g. a new document-format
handler) gets added by editing inside the ~1,786-line ingest block because "it's already opaque
and faster than adding a proper node."
**Why it happens:** Named explicitly in `.planning/research/PITFALLS.md`: "the opaque-node
'quarantine' quietly become[s] a dumping ground."
**How to avoid:** This is exactly why ROADMAP criterion 1 requires "a written inside-vs-across-
boundary change rule that a compat test enforces." The rule this research recommends: the
compat test pins the Part's **declared boundary values** (`name@version`, `effects[]`,
`artifact_scope`, `upstream_ref`, the subprocess script's stdin/stdout JSON schema) — anything
inside the subprocess/v1 venv may change freely; any change to a pinned boundary value must bump
the Part's version and re-trigger admission, never land as a silent same-version edit.
**Warning signs:** A diff that touches `full_ingest.py`'s declared `effects`/`artifact_scope`
without a version bump on `_NAME_AT_VERSION`.

## Code Examples

### Existing admission-relevant declarations (verified this session)

```python
# Source: databasise/parts_core/declared_only.py (read this session, lines 32-43) —
# the CURRENT declaration-only stub this phase must give a real body:
LIGHTRAG_FULL_INGEST_PART = Part(
    name_at_version="lightrag/full-ingest@0.1.0",
    kind="opaque",
    structural_depth="opaque",
    effects=["calls_llm", "writes_artifact", "reads_kv", "reads_graph"],
    upstream_ref="v1/lightrag/pipeline.py",
    body=None,
    artifact_scope="quarantined",
)
```

```python
# Source: databasise/parts_core/declared_only.py (read this session, lines 22-30) —
# the existing codebase-memory-mcp stub (self_storage, not machine-storage):
CODEBASE_MEMORY_MCP_PART = Part(
    name_at_version="codebase-memory-mcp@0.1.0",
    kind="opaque",
    structural_depth="opaque",
    effects=["self_storage", "fs"],
    upstream_ref="external:codebase-memory-mcp",
    body=None,
    artifact_scope="self_storage",
)
```

### v1's graph-aware deletion algorithm (the mechanism API-02 must preserve)

```python
# Source: v1/lightrag/lightrag.py, adelete_by_doc_id (read this session, lines 3532-3552,
# entity path; the relation path at lines 3608-3627 is symmetric):
remaining_sources = subtract_source_ids(existing_sources, chunk_ids)
if not remaining_sources:
    entities_to_delete.add(node_label)
    entity_chunk_updates[node_label] = []
elif remaining_sources != existing_sources or graph_references_deleted_chunks:
    entities_to_rebuild[node_label] = remaining_sources
    entity_chunk_updates[node_label] = remaining_sources
else:
    logger.info(f"Untouch entity: {node_label}")
```
`existing_sources` is read preferentially from the dedicated `entity_chunks`/`relation_chunks`
chunk-tracking stores, falling back to the graph node/edge's own `source_id` field
(`GRAPH_FIELD_SEP`-joined) only when the tracking store has nothing — and a stale graph
`source_id` referencing a chunk being deleted forces a rebuild even when the tracking store looks
clean, so metadata cannot silently drift (`graph_references_deleted_chunks`, same lines).

### The subprocess protocol MODAL-02's real Part body must mirror

```python
# Source: databasise/parity/v1_driver_script.py module docstring (read this session,
# lines 1-31) — the existing query-side precedent:
# "Protocol: read one JSON object from stdin —
#  {"mode": str, "query": str, "hl_keywords": [...], "ll_keywords": [...], "working_dir": str}
#  ... run the query, and write one JSON object to stdout:
#  {"chunk_ids": [...], "entity_ids": [...], "relation_ids": [...], "answer": str, ...}"
```

```python
# Source: databasise/parity/v1_arm.py (read this session, lines 134, 160-167) —
# the existing launch mechanism, already timeout-parameterized:
proc = subprocess.run(
    [...],
    input=...,
    capture_output=True,
    timeout=timeout,
)
```

## State of the Art

| Old Approach (docs framing, pre-Phase-4) | Current Approach (as of this session) | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MCP transport deferred, treated as an open future concern | API-07 is now this phase's own requirement, due immediately after REST | Phase 4 close (04-CONTEXT.md's Deferred Ideas) | The MCP surface must reuse the exact same `Databasise` engine calls REST uses — no second execution path, per D-17's dual-transport precedent |
| `mutates_store`/`_mach11_events` existed only as a tested-but-unused mechanism | This phase is the first to register a real Part declaring `mutates_store` | Phase 4's own docstring already flags this ("no part registered anywhere ... declares mutates_store today") | The correlation rule must be re-verified against a real deleting part, not assumed already proven |

**Deprecated/outdated:** none — this is a young codebase (milestone in progress); no library or
pattern named above has been superseded within this project's own history.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `mcp` (PyPI) is the correct package to use for the MCP transport, and its recommendation as "standard" | Standard Stack | Low — package existence/metadata is registry-verified; the choice-of-package judgment is training knowledge, not docs-cited. If wrong, swapping SDKs is a contained change behind the thin `databasise/mcp/` adapter |
| A2 | The five "sandbox-candidate engines" for MACH-04's survey are not explicitly enumerated anywhere in the docs tree this research searched (`CONTRACT.md`, `SELECTION.md`, `RED-TEAM.md`, `CATALOG.md`, `PARTS.md`); the recommended default list (codebase-memory-mcp, postgres-mcp, supabase-mcp, code-graph-rag, a foreign-hosted LightRAG server) is inferred from CATALOG.md's `MC-`/`CA-`/`GR-` opaque-shaped entries and Falsifier 6's own worked pair, not a verbatim source list | Open Questions / OPEN DECISION 1 | Medium — MACH-04 is explicitly non-gating (Falsifier 8, "documentation pass," "accepted-as-stated-risk"), so a wrong or incomplete list does not block the phase, but the planner should confirm the list with the owner before writing tasks against it |
| A3 | HARD-03/DR-04 should resolve to "the two-covering rationale is sufficient" (no new per-chunk stamp) rather than "adopt the per-chunk stamp" | Open Questions / OPEN DECISION 2 | Medium — this is a genuine architectural fork with real engineering cost on one branch (modifying the opaque ingest core's internal chunk schema) vs. a documentation-only close on the other; if the owner disagrees, the plan's Wave structure changes materially |
| A4 | Document deletion should be classified `mutates_store` (not `writes_artifact`) and modeled as a second, separate node/port from ingest per §19.6 | Architecture Patterns, Pattern 2/3 | Low-Medium — this follows directly from CONTRACT text and the existing `codebase-memory-mcp` precedent, but no CONTRACT clause states the ingest-deletion case by name the way it states `manage_adr`/`delete_project`; it is the closest-fitting existing category, not a verbatim-named one |
| A5 | The new ingest driver script should live under `databasise/parity/`-adjacent naming and be added to `check_import_boundary.py`'s exclusion list, following `v1_driver_script.py`'s exact pattern | Recommended Project Structure | Low — this is a direct extension of an existing, working pattern; the main risk is naming/location bikeshedding, not a wrong mechanism |

## Open Questions

### OPEN DECISION 1: Which five engines does MACH-04's survey cover?

- **What we know:** `SYSTEM-MODEL.md` and the D-VARIANTS `SELECTION.md` both refer to "the five
  sandbox-candidate engines already named in the lineup" for Falsifier 8, but no single table in
  the docs tree searched this session enumerates exactly five engines under that label. Falsifier
  6 (a closely related falsifier) names exactly two: `codebase-memory-mcp` (no LLM, own storage)
  and "a LightRAG server" (LLM-heavy, injectable endpoint). `CATALOG.md`'s `## §T` master table
  has a dedicated `MC-` bucket with exactly two MCP-hosted candidates (`postgres-mcp`,
  `supabase-mcp`) plus `CA-1` (code-graph-rag, Memgraph-backed) and `CA-2`
  (codebase-memory-mcp) as foreign/opaque-shaped entries.
- **What's unclear:** Whether "the lineup" refers to a specific named subset the original spike
  author had in mind but did not table explicitly, or whether the planner is meant to compose the
  five from the catalog's own opaque-shaped entries.
- **Recommendation:** Default to: `codebase-memory-mcp` (CA-2, already fully surveyed in
  `PARTS.md ## §X`), `postgres-mcp` (MC-1), `supabase-mcp` (MC-2), `code-graph-rag`/cgr (CA-1),
  and a foreign-hosted LightRAG server (the Falsifier-6-named second case, distinct from the
  in-process opaque ingest core this phase also admits). Since Falsifier 8 is explicitly
  "non-gating" and "accepted-as-stated-risk," the plan should treat this as a documentation task
  that can proceed on this default list, with a checkpoint asking the owner to confirm or correct
  it before the survey is written up as final.

### OPEN DECISION 2: DR-04 — per-chunk provenance stamp, or the two-covering rationale?

- **What we know:** `ANATOMY.md`'s defect register (`## §F`, row DR-04, read this session in
  full) states the row is still **unselected between its two options** as of the 2026-08-27
  milestone audit: "Does the machine's own chunk artifact carry a checkable per-chunk provenance
  stamp (chunker/embedder identity), or only a per-run sub-recipe stamp at the artifact-registry
  level (§7's SA-2)?" `CONTRACT.md §4`'s D9 repair settled an adjacent question
  (`ScoredItem.provenance`, an evidence-record field during a run) but explicitly does **not**
  settle this row: "a chunk sitting in the store is not [an evidence record]."
- **What's unclear:** Whether the corpus this project will actually run against is ever
  heterogeneous enough (mixed chunker/embedder versions within one registered artifact set) for a
  per-chunk stamp to matter in practice, versus always being ingested under one uniform recipe per
  registration.
- **Recommendation:** Close HARD-03 with **the two-covering rationale**, not a new per-chunk
  field. The existing artifact-registry schema already records a per-registration SA-2 stamp
  (chunker/extraction/embedding) for every artifact set (`registry_artifact/index.py`, read this
  session), and CONTRACT §7's already-repaired "partial-coverage registration" rule (D8, read
  verbatim this session) already **refuses** registering a sub-recipe stamp over a corpus it was
  not applied to in full — forcing a corpus split before registration rather than letting mixed
  provenance hide inside one artifact-set id. Together these two existing mechanisms answer the
  provenance question a per-chunk stamp would answer, without requiring a schema change inside
  the opaque ingest core's own internals (which CONTRACT's own framing treats as a capability
  "not yet earned," i.e. a cost to defer, not a gap to patch around). This is a judgment call,
  not a re-derivation of settled contract text — flag it to the owner as the phase's one real
  policy decision.

### Open question 3: What network-namespace enforcement does condition 3 actually require for an in-process opaque Part?

- **What we know:** §8 condition 3 requires the node's network namespace be denied, with the
  machine acting as the injected LLM provider — or the node is admitted `unbudgetable`. For the
  LightRAG ingest core, this is achievable *by construction*: the ported Part body calls the
  machine's own `OpenAICompatibleClient` (already supports arbitrary `base_url` injection,
  confirmed this session) rather than the subprocess making its own independent outbound calls —
  the same technique Phase 3's parity harness already uses (`OPENAI_LLM_EXTRA_BODY`-style env
  injection into the v1 subprocess). For `codebase-memory-mcp`, `PARTS.md ## §X` already found
  condition 3 to be an **open question, not a clean yes** — zero LLM/network calls in the 15 tool
  handlers, but a loopback-bound HTTP UI server exists inside the same OS process, and whether
  denial is scoped per-tool-call or per-process is unsettled (`## §R` row `N12`).
- **What's unclear:** Whether this phase needs to actually implement OS-level network-namespace
  isolation (e.g. a Nix sandbox, a network namespace via `unshare`/systemd) for the
  `codebase-memory-mcp` subprocess, or whether recording the open question (as `PARTS.md` already
  does) and admitting the engine with the caveat noted is sufficient for this milestone.
- **Recommendation:** Given the project's "no Docker, embeddable in-process, local NixOS"
  constraint and the absence of any existing sandboxing machinery in `databasise/`, treat real OS
  namespace denial as **out of scope for this phase** and record the same open finding
  `PARTS.md ## §X` already recorded (row `N12`) as the admission's own caveat, rather than
  building new sandboxing infrastructure under this phase's budget. Flag this explicitly to the
  planner as a scope boundary, not a silent gap.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `codebase-memory-mcp` binary | MODAL-03 admission testing | Yes | 0.10.8 (at `/home/chris/.local/bin/codebase-memory-mcp`) | — |
| `v1/.venv` (pinned LightRAG environment) | MODAL-02's subprocess-backed ingest Part | Yes (Phase 3 already built and pins this) | per `v1/pyproject.toml` | — |
| `mcp` (PyPI) | API-07 | Not yet installed in `databasise/.venv` | to be added, 2.2.0 | none needed — straightforward `uv add` |
| `python-multipart` (PyPI) | API-01 raw upload | Not yet installed | to be added, 0.0.32 | none needed |
| `fastapi`/`uvicorn` | REST additions | Yes (Phase 4 already installed under `[project.optional-dependencies] rest`) | pinned per Phase 4 | — |

**Missing dependencies with no fallback:** none — both new packages are ordinary `uv add`s with
no environment obstacle found.

**Missing dependencies with fallback:** none.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2+ with `pytest-asyncio` (`asyncio_mode = "auto"`), per `databasise/pyproject.toml` (read this session) |
| Config file | `databasise/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd databasise && uv run pytest tests/<new dir> -x` |
| Full suite command | `cd databasise && uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODAL-02 | Ingest Part produces a `quarantined`-scope artifact via subprocess | integration | `uv run pytest tests/parts_core/lightrag/test_full_ingest.py -x` | ❌ Wave 0 |
| MODAL-02 | Inside-vs-across-boundary compat rule enforced | unit | `uv run pytest tests/parts_core/lightrag/test_full_ingest_compat.py -x` | ❌ Wave 0 |
| MODAL-03 | codebase-memory-mcp registered with the eleven-condition verdicts encoded as declared metadata | unit | `uv run pytest tests/parts_core/test_codebase_memory_mcp_admission.py -x` | ❌ Wave 0 |
| API-01 | Ingest + job-status polling round-trip | integration | `uv run pytest tests/seam/test_ingest_job_status.py -x` | ❌ Wave 0 |
| API-02 | Delete a document; shared entity survives, orphan-only entity is removed | integration | `uv run pytest tests/seam/test_delete_document.py -x` | ❌ Wave 0 |
| API-02 | MACH-11 seam event fires for the deleting part (first real, non-fixture exercise) | unit | `uv run pytest tests/seam/test_mach11_event.py -x` (extend existing file) | ✅ (extend) |
| API-06 | Health/corpus-status/doc-count responses are bounded and paginated | unit | `uv run pytest tests/seam/test_corpus_status.py -x` | ❌ Wave 0 |
| API-07 | MCP tool set has exactly five tools; adding a modality adds none (selector-vs-tool test) | unit | `uv run pytest tests/mcp/test_tool_growth_invariant.py -x` | ❌ Wave 0 |
| API-07 | MCP and REST reach identical results for the same operation (dual-transport parity, mirroring D-17) | integration | `uv run pytest tests/mcp/test_dual_transport_parity.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** the relevant new test file only (`uv run pytest tests/<area> -x`)
- **Per wave merge:** `uv run pytest` (full suite) plus `uv run python -m databasise.tools.check_import_boundary` (must stay exit 0 — the new ingest driver script must be added to its exclusion list, not silently pass or silently fail)
- **Phase gate:** full suite green, plus a manual check that `check_import_boundary.py`'s exclusion list update is itself reviewed (a new entry there is exactly the kind of change that deserves a human look, since it is opening a hole in an enforced boundary)

### Wave 0 Gaps

- [ ] `tests/parts_core/lightrag/test_full_ingest.py` — covers MODAL-02 (needs the new subprocess-backed Part body to exist first)
- [ ] `tests/parts_core/lightrag/test_full_ingest_compat.py` — covers MODAL-02's compat-test success criterion
- [ ] `tests/parts_core/test_codebase_memory_mcp_admission.py` — covers MODAL-03
- [ ] `tests/seam/test_ingest_job_status.py` — covers API-01
- [ ] `tests/seam/test_delete_document.py` — covers API-02
- [ ] `tests/seam/test_corpus_status.py` — covers API-06
- [ ] `tests/mcp/` (new directory) — covers API-07, both the growth-invariant and dual-transport-parity tests
- [ ] A new ingest driver script under `databasise/parity/` (or a sibling directory) — precondition for `test_full_ingest.py`, mirroring `v1_driver_script.py`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No — out of this phase's scope (no auth requirement named in REQUIREMENTS.md for Phase 5; the existing REST layer has no auth middleware today per Phase 4's scope) | — |
| V3 Session Management | No | — |
| V4 Access Control | No — single-tenant, local, embeddable engine; no multi-tenant boundary this phase introduces | — |
| V5 Input Validation | **Yes** — API-01's raw document upload and structured payload are the phase's one new external-input trust boundary | FastAPI/Pydantic request models (`_RequestModel` pattern already established in `databasise/seam/rest.py`); reject oversized uploads and unexpected content types at the REST boundary before the subprocess ever sees the bytes |
| V6 Cryptography | No — no new secrets/crypto surface this phase adds | — |
| V12 File and Resources | **Yes** — raw document upload writes bytes to disk before/while handing them to the subprocess-backed ingest Part | Never trust a client-supplied filename for a filesystem path (mirror `namespaces.py`'s own `_NAMESPACE_TOKEN_RE` bare-token discipline: generate the on-disk name server-side, never echo the client's own path string into a filesystem join) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via a malicious document filename or structured-payload field reaching a filesystem join | Tampering | Never join a client-supplied string directly into a path; generate server-side identifiers, exactly as `namespaces.py`'s `namespace_dir()` already refuses any token that could escape `store_root` (a directly reusable precedent) |
| Command/argument injection into the subprocess launch for the new ingest driver script | Tampering / Elevation of Privilege | Pass all caller-controlled data through the existing JSON-over-stdin protocol (`v1_driver_script.py`'s own pattern) — never interpolate caller input into the subprocess's argv or into a shell string |
| Unbounded upload size exhausting disk/memory | Denial of Service | Enforce a request body size limit at the REST layer (FastAPI/Starlette supports this) before any bytes reach the ingest Part |
| Deleting a document that does not exist, or double-deleting mid-flight | (correctness, not a STRIDE category per se) | Mirror v1's own `DeletionResult` status vocabulary (`"not_found"`, `"not_allowed"`, `"fail"`, `"success"`) rather than inventing a new one — v1 already has a pipeline-lock discipline preventing concurrent conflicting deletions |

## Sources

### Primary (HIGH confidence — read verbatim this session)

- `docs/system-model/CONTRACT.md` §4, §7, §8, §9, §17, §18, §19 — read in full this session
- `docs/system-model/PARTS.md` §X (codebase-memory-mcp admission, all eleven conditions), §R (repair register references), §P — read in full this session
- `docs/system-model/ANATOMY.md` §F (defect register, DR-04 row) — read in full this session
- `docs/system-model/RIG.md` §F3 (Falsifier 3 verdict, default posture, fallback ladders) — read in full this session
- `docs/system-model/SYSTEM-MODEL.md`, D-VARIANTS `SELECTION.md` — searched for "lineup"/"sandbox-candidate" this session
- `databasise/parts_core/declared_only.py`, `databasise/parts_core/lightrag/embedder_index.py`, `databasise/namespaces.py`, `databasise/registry_artifact/index.py`, `databasise/parts/schema.py`, `databasise/validator/blast_radius.py` — read/grepped this session
- `databasise/seam/engine.py`, `databasise/seam/rest.py` — read this session
- `databasise/parity/v1_driver_script.py`, `databasise/parity/v1_arm.py` — read this session
- `databasise/tools/check_import_boundary.py` — read in full this session
- `v1/lightrag/lightrag.py` (`adelete_by_doc_id`, lines 3111-3650) — read this session
- `.planning/phases/04-the-seam/04-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md` — read in full this session
- `.claude/skills/spike-findings-rag-graph-vector-raw/SKILL.md` — read this session
- PyPI JSON API queries for `mcp` and `python-multipart` (`pypi.org/pypi/<pkg>/json`) — this session

### Secondary (MEDIUM confidence)

- `gsd_run query package-legitimacy check` seam output for `mcp`/`python-multipart` — cross-checked against the PyPI JSON API's own repo/homepage fields

### Tertiary (LOW confidence — flagged as OPEN DECISIONs above, not stated as settled)

- The exact five "sandbox-candidate engines" for MACH-04 — inferred from `CATALOG.md`'s `MC-`/`CA-`/`GR-` buckets, not read from a verbatim named list
- DR-04's resolution — a recommendation, not a re-derivation of settled contract text

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM — package choices are training-knowledge-informed with registry-verified metadata, not Context7/official-docs-fetched this session (no MCP fetch tool was invoked; direct PyPI JSON queries were used instead as the ecosystem-registry check)
- Architecture: HIGH — every architectural claim about the *existing* `databasise/` codebase (quarantined scope, mutates_store, the subprocess pattern, the import-boundary checker, v1's deletion algorithm) is grounded in files read verbatim this session
- Pitfalls: HIGH for pitfalls 1-2 (directly evidenced by existing code/docstrings); MEDIUM for pitfalls 3-4 (grounded in PARTS.md/PITFALLS.md text but extrapolated to this phase's specific tasks)

**Research date:** 2026-09-08
**Valid until:** 30 days (stable, slow-moving contract text) for the CONTRACT/PARTS findings; 7 days for the PyPI package-version findings (`mcp` is a fast-moving young SDK)
