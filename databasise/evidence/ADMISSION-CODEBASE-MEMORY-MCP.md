# Admission Manifest — codebase-memory-mcp@0.1.0

The code-inspected §8 admission manifest for `codebase-memory-mcp` (05-06-PLAN.md Task 2),
turning `PARTS.md ## §X`'s already-run, source-level eleven-verdict analysis into an executable
`AdmissionRecord` (`databasise/parts_core/codebase_memory_mcp.py`). This document restates the
verdict table for a human reader, adds the two measurements §X itself could not supply (a wall-
clock ceiling, a live tool-surface comparison), and records the version drift between the pinned
clone the verdicts were code-verified against and the binary this admission actually runs.

## Entry path and node-kind choice

`external-tool` primitive part type, hosted at the `opaque` structural kind (`CONTRACT.md ## §17`'s
Node-kind-choice paragraph: the two are one admission, not alternative choices). Entry path:
`whole-engine opaque node` — the exercise is the eleven `§8` admission verdicts against a real,
unmodified foreign binary, never a decomposition of its fifteen tools.

## The eleven verdicts

Projected from `PARTS.md ## §X`'s own table — this section does not re-derive the analysis, it
restates it as the record's own field values.

| # | Verdict | Evidence (this record's own words, citing `PARTS.md ## §X`) |
|---|---|---|
| 1 | `confirms-the-rule` | The engine's own tool self-report is demonstrably imprecise — ten of fifteen tools self-declare `destructive_hint=True` despite calling no mutation function, only `list_projects` self-declares `read_only_hint=True` (re-confirmed live against 0.10.8 this session, matching §X's `mcp.c:698-724` finding against the pinned clone). |
| 2 | `satisfied` | `environment_hash` covers the whole resolved closure for this single-binary, no-interpreter engine (§X: "no interpreter, no venv, no external SDK to hash separately") — the resolved binary path, its own SHA-256, and its self-reported version. |
| 3 | `open-question` | Zero LLM/network calls in any of the fifteen tool handlers, but a loopback-bound HTTP UI server exists in the same OS process outside the MCP tool surface; per-call-vs-per-process denial scoping is not settled by §8's text (`## §R` row `N12`). Recorded open, not rounded to a yes. |
| 4 | `satisfied` | `CBM_WALL_CLOCK_CEILING_SECONDS=120.0`, declared by this admission — the engine self-reports none (§X's own negative-result grep). See "The measured ceiling" below. |
| 5 | `satisfied` | `storage='self-contained'`; `CODEBASE_MEMORY_MCP_PART.artifact_scope='self_storage'`, never `'shared'`. |
| 6 | `satisfied` | `index_repository`'s only input is a filesystem `repo_path` — re-confirmed by calling it directly this session; this engine never consumes a machine-produced feed at all. |
| 7 | `machine-side-obligation` | Policy-level; enforced by `cross_check_conditions` at registration (the wiring's provides node excluded from the default selector). |
| 8 | `machine-side-obligation` | Policy-level ~90-day TTL/ledger mechanic; `ttl_days=90` declared on this record. |
| 9 | `machine-side-obligation` | The invocation-shape half is satisfied (all fifteen tools are explicit, named calls, re-confirmed live); the counting-and-non-promotion half is a machine-side ledger mechanic with no source evidence either way — not rounded up to a full yes. |
| 10 | `satisfied` | Enforced by `cross_check_conditions`: `artifact_scope='self_storage'` can never be enumerated as an SA-1-shareable artifact. |
| 11 | `satisfied` | Re-confirmed live against the installed 0.10.8 binary's own input schemas: none of the fifteen tools carries an `as_of`/`valid_at`/interval parameter; `QueryObject` declares no `as_of` member. |

## The three not-clean-yeses, called out so a reader cannot miss them

- **Condition 1** is not a satisfied/failed verdict at all — it is evidence *for* the admission
  rule itself (an opaque node's self-report is not trusted at face value). Recorded as
  `confirms-the-rule`.
- **Condition 3** is an **open question**, not a clean yes — the network-namespace denial's
  scoping (per-call vs. per-process) is unsettled by `§8`'s own text, and this admission carries
  that question forward as its own caveat (see "Network-namespace scope decision" below), never as
  a closed condition.
- **Conditions 7, 8, and the counting half of 9** are **machine-side obligations** with no source
  evidence either way — they are the admitting machine's own responsibility to discharge (and this
  machine's registration-time enforcement does discharge the checkable halves), not a fact about
  the foreign engine's source that could be verified or falsified.

## The measured ceiling

`§8` condition 4 requires the *admitting machine* declare a wall-clock ceiling; `PARTS.md ## §X`
condition 4 already found the engine self-reports none anywhere in its source or README — a
measurement is the only honest basis.

| Field | Value |
|---|---|
| Measured duration | 2.88 seconds (cold-start `index_repository` against this repository's own `databasise/` directory: ~177 Python files, 3204 nodes, 14401 edges) |
| Declared ceiling | 120.0 seconds |
| Margin | ~40x the measured duration |
| Margin rationale | A real target repository this engine indexes may be an order of magnitude or more larger than this project's own `databasise/` directory; ~40x the measured cold-start duration gives headroom for that without being an arbitrary round number picked from convention. |

## The version drift

`PARTS.md ## §X`'s eleven verdicts were code-verified against the pinned clone
**`codebase-memory-mcp@61b3b1b2`**. This admission runs the binary actually installed on this
machine:

| Field | Value |
|---|---|
| Pinned clone (verdicts verified against) | `codebase-memory-mcp@61b3b1b2` |
| Installed binary (this admission runs) | `codebase-memory-mcp 0.10.8` |
| Installed binary path | `/home/chris/.local/bin/codebase-memory-mcp` |
| Installed binary SHA-256 | `sha256:1175645cb30560e7e47d78611cd1bcb509478eaf6d4e51f72fe18327ee9c1351` |
| `environment_hash` (this record) | `sha256:ed704242ed963ea2f5fb5b07124da3d28f53b2e43893568f8473c6302bccd8c1` |

### Drift stated plainly

The two builds are **not the same build** — a version string (`61b3b1b2` is a commit-pinned clone
SHA; `0.10.8` is a released version tag) and no evidence in this session establishes they are
byte-identical. This admission runs `0.10.8`, and every verdict above that cites a §X finding is
therefore **inherited from a different build than the one installed**, not re-verified against
`0.10.8`'s own source. What *is* re-verified live against `0.10.8` this session, independent of the
source-level analysis: the tool surface (below), `index_repository`'s input schema (condition 6),
the tool self-report's own annotations (condition 1), and the absence of any `as_of`-shaped
parameter across all fifteen schemas (condition 11) — these four are re-confirmed live, not merely
inherited. The remaining verdicts (2, 3, 4, 5, 9's invocation-shape half, 10) rest on structural
facts (the engine's own storage model, its process shape, its call shape) that a patch-version bump
between a commit-pinned clone and a tagged release is unlikely to change, but this admission states
the inheritance rather than assuming it away.

## The live tool-surface comparison

`list_tools()` called against the installed `0.10.8` binary this session returns exactly the same
fifteen tool names `PARTS.md ## §X`'s table already enumerates — no new tool, none gone:

`index_repository`, `search_graph`, `query_graph`, `trace_path`, `get_code_snippet`,
`get_graph_schema`, `get_architecture`, `search_code`, `list_projects`, `delete_project`,
`index_status`, `check_index_coverage`, `detect_changes`, `manage_adr`, `ingest_traces`.

Because the tool surface has not moved, the exhaustive claims conditions 6, 9, and 11 rest on
("none of the fifteen tools' schemas carries an `as_of`," "index_repository's only input is
`repo_path`," "every tool is an explicit named call") are re-checked against the *live* schema set
this session, not merely inherited from the pinned clone's own scan — each holds against `0.10.8`
exactly as it held against `61b3b1b2`.

## The declared-effects discrepancy

`PARTS.md ## §X` declares this part's effects as `mutates_store` only (landed by the X1 repair).
The built `Part` (`databasise/parts_core/declared_only.py`) declares three:
`["self_storage", "fs", "mutates_store"]`. This is a real discrepancy, recorded rather than
silently resolved either direction: `self_storage` and `fs` are over-declarations of the same
self-contained-storage fact `§X`'s own analysis already establishes (the engine's SQLite cache,
bundled embeddings, and tree-sitter parse state never leave its own process/filesystem boundary),
and `§2`'s deny-by-default rule permits an over-declaration — it is never a wire-time refusal risk
the way an under-declaration is. They are retained specifically because
`databasise/evidence/wirings/w2-codebase-memory-mcp.json` and `FALSIFIER-2-EVIDENCE.md` already pin
them as committed Falsifier-2 evidence from an earlier phase; removing them now would silently
invalidate that committed evidence rather than correct a stated discrepancy.

## Network-namespace scope decision

Carried forward from `PARTS.md ## §R` row `N12`, as this admission's own caveat rather than a
closed condition: `§8` condition 3's network-namespace denial is not scoped by its own text to
per-MCP-tool-call versus per-OS-process granularity. Zero LLM/network calls exist across this
engine's fifteen tool handlers, but a loopback-bound HTTP UI server (127.0.0.1-only, same-origin
CORS) exists inside the same OS process, outside the MCP tool surface. **No OS-level
network-namespace isolation mechanism is built this phase** — consistent with the project's
no-Docker, embeddable-in-process, local-NixOS constraint (`05-RESEARCH.md` Open Question 3) — and
this open question stands exactly as `## §R` row `N12` records it, not silently resolved by this
admission.

## What this admission does and does not license

**Licenses:** dispatching `codebase-memory-mcp` as a real, executable opaque `Part` through the
same `parse_wiring -> run_wiring` machinery the LightRAG corpus-side ports use
(`databasise/wirings/codebase-memory-mcp.json`); calling any of the eleven evidence-returning tools
through the adapter and receiving a §4-typed, tier-capped result; recording the engine's declared
mutation surface (`manage_adr`/`delete_project`) as a machine-known fact.

**Does not license:** running `manage_adr`/`delete_project`/`ingest_traces` from any machine-side
operation this phase adds (none does — see `COVERAGE.md`'s OPT-OUT rows); treating condition 3's
open network-namespace question as resolved; treating any of the eleven verdicts as re-verified
against `0.10.8`'s own source beyond the four this document names as live-re-checked; or building
OS-level network-namespace isolation this phase deliberately defers.
