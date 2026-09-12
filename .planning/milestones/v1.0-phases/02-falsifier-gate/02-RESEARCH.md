# Phase 2: Falsifier Gate - Research

**Researched:** 2026-08-31
**Domain:** internal mechanism verification (no new external stack) — committed evidence artifacts over an already-built validator, plus a governance waiver record
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Gate re-scope (owner decisions, 2026-08-31)**

- **D-01:** Product-first: Falsifier 5 (eval bundle + A/A floor) is deferred from Phase 2 to the
  point where a comparison first needs it (Phase 3 parity at the earliest). Rationale: the floor
  would otherwise be calibrated on a stand-in arm — Phase 1 has only canned deterministic parts —
  and calibrating against the real pre-decomposition LightRAG when it first exists is better
  methodology as well as cheaper. — **Reversibility:** reversible — the bundle/calibration design
  is fully specified in RIG §EV/§AA and can be stood up whenever wanted.
- **D-02:** The waiver is recorded, never silent: the ratified §VD verdict named Falsifiers 2 and
  5 as its conditions, so GATE-01's deliverable becomes a written owner decision amending the
  condition (Falsifier 2 now; Falsifier 5 at point of need; ladder proceeds). A Falsifier 2
  failure still halts.
- **D-03:** Falsifier 2 stays in Phase 2: near-free, mechanism already built and live in the
  machine's write path. The evidence run was demonstrated 2026-08-31 (scratchpad script): all
  three named wirings compute correctly (taint rule overrides declared depth in W2/W3), and both
  self-declaration probes are refused (`blast-radius-refusal`, `effects-exceed-part`). Phase 2
  turns this into committed evidence: the three wirings as JSON files plus an evidence document
  recording computed-vs-declared per node and the §19.10 enumeration.
- **D-04:** Human-in-the-loop verdicts are the operating mode: under MACH-09's default-off
  posture the only enabled promotion path is operator-asserted, and Phase 6's comparison output is
  verdict-free by design. Automated statistical verdict machinery needs explicit owner opt-in.
- **D-05:** Phase 3's parity gate, in the absence of the A/A floor, is checked at the retrieval
  level with deterministic, zero-token comparisons (retrieved chunk sets / rankings, original vs
  decomposed) plus human spot-checks of answers. Accepted risk, stated: subtle answer-quality
  drift is unmeasured until a floor is calibrated; judged low because Phase 3 keeps the same
  prompts and models, so decomposition bugs surface at the retrieval level.

**Eval-run decisions banked for when Falsifier 5 runs** (D-06..D-12) — NOT executed in Phase 2,
recorded here only so the planner does not accidentally re-derive them differently: HotpotQA
distractor corpus; qwen/qwen3.7-flash generator via OpenRouter provider-pinned; judge never free
(gemini-3.1-flash-lite or gpt-5-mini, provider-pinned, prompt hashed, judge identity derived from
the response's installed provider/model, not the requested id); local embedder (bge/nomic via
Ollama); declared concurrency 8 for any calibration; cache-bypass/temperature/no-invisible-caching
preconditions verified before a calibration run counts; $10 lifetime OpenRouter credits for
1,000 req/day free-tier draft quota.

**Parallelization (settled by inspection)**

- **D-13:** The v1 "3 runs at a time" cap is confirmed gone in the v2 machine: concurrency is a
  per-node semaphore sized by that node's own `config.max_concurrency` (default 1), never shared,
  no global cap (Phase 1 D-09/D-11).

### Claude's Discretion

- Shape and location of the committed Falsifier 2 evidence artifact (JSON wirings + evidence doc)
  and of the GATE-01 waiver record.
- MACH-09 implementation detail (where the posture switches live, how `degraded` labelling is
  wired), within the refusals-over-silent-fallbacks house style.
- Test structure for the evidence run, following existing databasise/tests conventions.

### Deferred Ideas (OUT OF SCOPE)

- **MACH-02 / MACH-03 (eval bundle + A/A calibration, Falsifier 5)** → Phase 3 at the earliest,
  at the parity comparison's point of need, against the real pre-decomposition original. Banked
  decisions D-06..D-12 apply. REQUIREMENTS.md and ROADMAP.md still assign these to Phase 2 —
  amend during planning (roadmap edit) so coverage tracking follows the re-scope.
- **HARD-01 (parts-check.sh / anatomy-check.sh vacuous-pass fixes)** → later doc pass.
- **HARD-02 (eight ANATOMY §F rows + stale cross-document rows)** → same later doc pass.
- **Review GUI for human-in-the-loop checking** → scope addition if wanted; current scope is
  API-only (Sourcerer is the client).
- **DuckDB for scoreboard/trace analytics** → only relevant when the statistical machinery is
  stood up; stays deferred with it.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GATE-01 | Rung ordering enforced; a Falsifier 2/5 failure halts the ladder (SELECTION.md-level reversal) | The waiver-record artifact type does not exist anywhere in the repo yet — no `SELECTION.md`-level reversal precedent to imitate. §"Waiver Record" pattern below is a new-synthesis recommendation, not a discovered convention. |
| MACH-01 | `effective_depth`/`execution_mode` computed not declared, over the three named wirings, §19.10 boundary enumeration recorded with the node set | Validator mechanism fully read and confirmed working end-to-end (`parse_wiring` → `effective_depth` → `blast_radius_violations`); three declaration-only `Part` entries for the named wirings already exist in `databasise/parts_core/declared_only.py`. §"Standard Stack"/"Architecture Patterns"/"Code Examples" below. |
| MACH-09 | Answer-level/index-side measurement off by default; fallback runs labelled `degraded`/`degradation_reason` | The labelling mechanism (`RunRecord`/`NodeTrace` honesty fields) is already fully built and schema-validated from Phase 1 (MACH-05). No measurement-gated promotion code exists anywhere yet (grep-confirmed) — the "off by default" posture holds trivially today. §"Runtime State Inventory" and "Common Pitfalls" below. |
| HARD-01 | Deferred this phase (owner re-scope) | Not researched — out of scope per CONTEXT.md. |
| HARD-02 | Deferred this phase (owner re-scope) | Not researched — out of scope per CONTEXT.md. |
</phase_requirements>

## Summary

Phase 2, after the 2026-08-31 re-scope, is almost entirely a **read-and-commit** phase, not a
build phase: the validator mechanism MACH-01 needs (`parse_wiring`, `effective_depth`,
`derive_execution_mode`, `blast_radius_violations`) is complete, tested (233 green tests as of
2026-08-31), and already exercised by a scratchpad script that is not committed. The three named
wirings' `Part` declarations already exist in `databasise/parts_core/declared_only.py`
(`lightrag/query-side@0.1.0`, `codebase-memory-mcp@0.1.0`, `lightrag/full-ingest@0.1.0`). What
Phase 2 actually adds is: (1) three committed wiring JSON documents that reference those parts and
exercise the taint rule in a way that demonstrates the disagreement between declared and computed
depth, (2) a committed evidence document recording the computed-vs-declared table plus the §19.10
boundary enumeration, (3) two committed "self-declaration probe" tests reproducing the two refusal
codes the scratchpad demonstrated (`blast-radius-refusal`, `effects-exceed-part`), (4) a written
GATE-01 waiver record amending the ratified §VD verdict's stated condition, and (5) a small MACH-09
posture record/guard — which, because no promotion or measurement-gated code exists anywhere in
the repo yet, reduces to documenting and pinning an already-true state rather than writing new
runtime logic.

The one real landmine: **two functions named `derive_execution_mode` exist** in the codebase —
`databasise.validator.depth.derive_execution_mode` (tracer-era, 2-value: `in-process`/`subprocess`)
and `databasise.validator.execution_mode.derive_execution_mode` (the hardened 4-value version with
`host()` and `UnimplementedPlacementError`, actually wired into `runner/scheduler.py`). The
scheduler's own module docstring states explicitly that the `depth` module's copy is "left
untouched (out of this plan's lane)" and is dead code outside one test file. The Falsifier 2
evidence artifact MUST use `validator.execution_mode.derive_execution_mode` — using the other one
would compute a plausible-looking but wrong `execution_mode` value that the real runner does not
use.

**Primary recommendation:** Build the Falsifier 2 evidence as a small, re-runnable, committed
Python module under `databasise/` (not under `docs/system-model/wirings/`, which is explicitly
"illustrative only, never governing" per its own README and does not use the real registry's
component names) that (a) loads the three named wirings through `default_registry()` +
`parse_wiring`, (b) prints/writes a computed-vs-declared table plus the §19.10 node-set
enumeration to a committed evidence doc, and (c) is backed by a pytest module the owner can run
directly (`uv run pytest -q` or a plain `python -m` invocation) so the artifact is inspectable, not
a buried assertion — matching the owner's explicit "visible in a working environment" request.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Wiring parse + depth/execution_mode computation | Machine core (`databasise/validator/`) | — | Already built; Phase 2 only exercises it over new fixture data, no new tier |
| Falsifier 2 evidence wirings (JSON) | Machine core (`databasise/`, not `docs/`) | Test suite (`databasise/tests/`) | Must resolve against the real `PartRegistry`/`default_registry()`, so it belongs beside the code that parses it, not in the doc-only illustrative directory |
| §19.10 boundary enumeration record | Documentation artifact (committed evidence doc) | — | A recorded human/authoring judgment call, not computed by the validator itself |
| GATE-01 waiver record | Documentation artifact (`.planning/` or `docs/system-model/`) | — | Governance-level record amending a ratified `SELECTION.md` verdict condition; no runtime component owns this |
| MACH-09 posture ("off by default") | Machine core (guard/assertion, if anything) | Documentation artifact | No measurement-gated promotion code exists yet anywhere in the repo (Phase 7 territory); Phase 2's job is to record/pin the posture, not implement a switch |
| `degraded`/`degradation_reason` labelling | Machine core (`databasise/runner/trace.py`) — already built | — | `RunRecord`/`NodeTrace` honesty-field mechanism is complete and schema-validated (Phase 1 MACH-05); Phase 2 does not need to build this, only confirm/cite it |

## Standard Stack

No new external stack is introduced by this phase. The evidence run is pure Python over the
existing `databasise` package and `pytest`; the waiver/posture records are Markdown documents.

### Core (already in place, reused)
| Component | Location | Purpose | Status |
|-----------|---------|---------|--------|
| `parse_wiring` | `databasise/validator/parse.py` | One-pass wiring validation, accumulates every violation, always computes depth/blast-radius when structurally sound | Complete, 233-test suite green |
| `effective_depth` | `databasise/validator/depth.py` | Taint-rule minimum-over-transitive-deps depth computation (SCC-condensation based) | Complete |
| `derive_execution_mode` (canonical) | `databasise/validator/execution_mode.py` | 4-value `execution_mode` derivation from `effects[]`/`kind`, with `host()` refusal for unimplemented placements | Complete — **this is the one to use, not `validator.depth`'s duplicate** |
| `blast_radius_violations` | `databasise/validator/blast_radius.py` | Refuses a shared-scope artifact write at non-`stage` effective depth | Complete |
| `default_registry()` | `databasise/parts/registry.py` | Preloaded registry with exactly D-04's seven Phase-1 entries, including the three named-wiring declaration-only parts | Complete |
| `DECLARED_ONLY_PARTS` | `databasise/parts_core/declared_only.py` | The three named-wiring `Part` declarations MACH-01 targets | Complete |
| `RunRecord`/`NodeTrace` honesty fields | `databasise/runner/trace.py` | `degraded`/`degradation_reason`/`stop_reason`/`partial` required-together labelling, schema-validated | Complete |
| `assert_valid_trace` fixture | `databasise/tests/conftest.py` | Validates a run-record dict against `docs/system-model/rig-trace.schema.json` via `jsonschema` | Complete |

### Version verification
No new packages. `jsonschema>=4.0` is already an existing dependency (`databasise/pyproject.toml:36`), already used by `tests/conftest.py`'s `assert_valid_trace` fixture — no new install required if the evidence artifact wants schema-checked output.

## Package Legitimacy Audit

Not applicable — this phase installs no new external packages. All work is over the existing `databasise` package plus stdlib `pytest`/`json`/`pathlib`.

## Architecture Patterns

### Falsifier 2 evidence data flow

```
databasise/parts_core/declared_only.py   (already exists — 3 Part declarations)
              │
              ▼
   default_registry()  ──►  registers all 7 D-04 parts, including the 3 named ones
              │
              ▼
  [NEW] three wiring JSON documents, one per named wiring
    - decomposed lightrag-local query-side wiring
    - opaque codebase-memory-mcp wiring
    - half-decomposed full-LightRAG wiring
    each referencing the matching registered `component` name(s)
              │
              ▼
     parse_wiring(doc, registry)  ──►  ParsedWiring{ nodes, parts, deps, report }
              │
              ├──► effective_depth(parsed)         → per-node computed depth
              ├──► derive_execution_mode(effects, kind)  → per-node execution_mode
              │      (from validator.execution_mode — NOT validator.depth)
              └──► blast_radius_violations(parsed, depth_map)  → refusals, if any
              │
              ▼
  [NEW] evidence doc: computed-vs-declared table per node,
        §19.10 boundary enumeration recorded with the node set
              │
              ▼
  [NEW] two probe tests reproducing the scratchpad's refused self-declarations:
        (a) a node over-declaring effects beyond its resolved Part → CODE_EFFECTS_EXCEED_PART
        (b) a node self-declaring a shared write outside stage depth → CODE_BLAST_RADIUS_REFUSAL
```

### Recommended location for the evidence artifact

```
databasise/
├── parts_core/declared_only.py     # already exists — the 3 named Part declarations
├── evidence/                        # NEW — or wherever the plan places it; not docs/system-model/wirings/
│   ├── falsifier2_wirings.py        # or 3x .json — must resolve against default_registry()
│   └── falsifier2_evidence.md       # or generated at test time — computed-vs-declared + §19.10
└── tests/
    └── validator/
        └── test_falsifier2_evidence.py   # re-runnable, asserts + can print the table
```

Do **not** put the real evidence wirings in `docs/system-model/wirings/`: that directory's own
README states every file there is "illustrative only ... never governing" and is not wired to
`default_registry()`'s actual component names (it predates the three named-wiring `Part`
declarations and uses a different, illustrative component vocabulary). Reusing it would produce a
file that looks like real evidence but is not actually loadable/parseable against the live
registry — the opposite of what D-03 asks for ("committed evidence, re-runnable and readable").

### Pattern 1: Named-wiring construction over `default_registry()`

**What:** Build a minimal `WiringNode` graph per named wiring that references the already-registered
component and exercises the taint rule (a `stage`-depth node depending on an `opaque` one, so the
computed effective depth diverges from any naively-assumed declared value).

**When to use:** For each of the three MACH-01 wirings.

**Example (based on the confirmed registered parts):**
```python
# Source: databasise/parts_core/declared_only.py (already registered names) +
# databasise/validator/parse.py (parse_wiring signature)
from databasise.parts.registry import default_registry
from databasise.validator.parse import parse_wiring
from databasise.validator.depth import effective_depth
from databasise.validator.execution_mode import derive_execution_mode  # the canonical one

registry = default_registry()

# W2 — opaque codebase-memory-mcp, single-node wiring (whole-engine opaque per MODAL-03)
w2_doc = {
    "nodes": {
        "cbm": {
            "component": "codebase-memory-mcp@0.1.0",
            "kind": "opaque",
            "effects": ["self_storage", "fs"],  # must be a subset of the Part's own effects
            "deps": [],
        }
    }
}
parsed = parse_wiring(w2_doc, registry)
assert parsed.report.ok
depths = effective_depth(parsed)
for node_id, part in parsed.parts.items():
    mode = derive_execution_mode(part.effects, part.kind)
    print(node_id, depths[node_id], mode)
```

### Pattern 2: Self-declaration probes (reproducing the scratchpad's refusals)

**What:** Two small wirings, each designed to fail one specific validator check, proving the
check is load-bearing rather than vacuous.

**Example — probe (a), `effects-exceed-part`:**
```python
# Source: databasise/tests/validator/test_cycles_and_depth.py
# (test_wiring_node_declaring_an_effect_its_part_does_not_is_refused — existing pattern to mirror)
doc = {
    "nodes": {
        "over-declared": {
            "component": "codebase-memory-mcp@0.1.0",
            "kind": "opaque",
            "effects": ["self_storage", "fs", "writes_artifact"],  # writes_artifact is NOT
                                                                     # in the Part's own effects
            "deps": [],
        }
    }
}
parsed = parse_wiring(doc, registry)
assert not parsed.report.ok
assert any(v.code == "effects-exceed-part" for v in parsed.report.violations)
```

**Example — probe (b), `blast-radius-refusal`:**
```python
# Source: databasise/tests/validator/test_blast_radius.py (existing pattern to mirror)
# lightrag/full-ingest@0.1.0 is opaque, writes_artifact, artifact_scope="quarantined" already —
# to trigger the refusal, register a variant/stand-in part with artifact_scope defaulting to
# "shared" (the CONTRACT §3 default) at non-stage depth, or use the existing
# test_blast_radius.py-style opaque_shared_writer fixture pattern directly.
```

### Anti-Patterns to Avoid

- **Using `databasise.validator.depth.derive_execution_mode`:** This function still exists,
  is still imported by `tests/parts/test_reference_parts.py`, and returns a plausible 2-value
  result (`in-process`/`subprocess`). It is NOT the function the real runner uses. Using it in the
  evidence artifact would silently produce `execution_mode` values that disagree with what
  `runner/scheduler.py` actually computes at dispatch time — exactly the kind of self-consistent-
  but-wrong artifact Falsifier 2 exists to catch.
- **Committing evidence wirings under `docs/system-model/wirings/`:** That directory is explicitly
  "illustrative only ... never governing" (its own README, line 1). A file placed there both sends
  the wrong signal (a reader would assume it is prose-illustrative, not load-bearing evidence) and
  will not resolve against `default_registry()`'s real component vocabulary unless painstakingly
  kept in sync — a maintenance trap the directory's own design deliberately avoids taking on.
- **Reading `WiringNode.effects` for containment/scope decisions:** CR-01 (already fixed in Phase
  1, `runner/scheduler.py` and `validator/blast_radius.py`) established that `execution_mode`,
  store-scoping, and blast-radius must all read the resolved `Part`'s own `effects`, never the
  wiring's self-declared `WiringNode.effects` — a wiring is untrusted author input. Any new code
  in the evidence artifact must follow the same rule if it touches effects at all beyond what
  `parse_wiring` already validates.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Depth/execution_mode computation | A parallel or "simplified" reimplementation for the evidence script | `databasise.validator.parse.parse_wiring` + `databasise.validator.depth.effective_depth` + `databasise.validator.execution_mode.derive_execution_mode` directly | These are the exact functions the real runner calls; a reimplementation, however faithful, is not evidence that the *real* mechanism computes correctly — it is evidence about a copy |
| Run-record `degraded`/`stop_reason` schema | A new ad-hoc dict shape for MACH-09's labelling | `databasise.runner.trace.RunRecord`/`NodeTrace` (already built, already schema-validated against `docs/system-model/rig-trace.schema.json`) | The required-together honesty invariant (`partial`/`degraded`/`stop_reason`/`degradation_reason`) is already implemented with a `__post_init__` guard that refuses an inconsistent record; duplicating this logic risks a second, less-tested copy diverging from the schema |
| JSON Schema validation for any new evidence JSON | Hand-rolled key presence checks | `jsonschema` (already a dependency, already used via `tests/conftest.py`'s `assert_valid_trace` pattern) | Already wired in, zero new cost |

**Key insight:** Nearly everything MACH-01 needs already exists and is tested. The risk in this
phase is not "the mechanism doesn't work" — it demonstrably does (233 green tests, a working
scratchpad demo) — the risk is **duplicating or bypassing the real mechanism** while building the
"visible, re-runnable" evidence artifact the owner asked for, landing evidence that looks
authoritative but exercises a stale or parallel code path (the `validator.depth.derive_execution_mode`
trap is the concrete instance of this).

## Common Pitfalls

### Pitfall 1: Two `derive_execution_mode` functions, only one is real
**What goes wrong:** Importing `from databasise.validator.depth import derive_execution_mode`
instead of `from databasise.validator.execution_mode import derive_execution_mode` compiles,
runs, and returns plausible-looking output (`in-process`/`subprocess`) — no error, no warning.
**Why it happens:** Both modules define a function with the identical name and signature
(`derive_execution_mode(effects: list[str], kind: str) -> str`); `validator.depth`'s copy is a
tracer-era artifact `runner/scheduler.py`'s own docstring says was deliberately left untouched
("out of this plan's lane") rather than deleted.
**How to avoid:** The evidence artifact and its tests must import from
`databasise.validator.execution_mode`, matching what `runner/scheduler.py:339` actually calls.
Grep for `derive_execution_mode` and confirm every evidence-artifact import resolves to the
`execution_mode` module before treating any printed `execution_mode` value as real.
**Warning signs:** An evidence table showing only two distinct `execution_mode` values across the
three named wirings (should be up to four: `in-process`, `subprocess`, `confined-unit`,
`long-lived-service`) is a strong signal the wrong function was imported.

### Pitfall 2: `writes_artifact` vs. transient store-write effects confusion in the third named wiring
**What goes wrong:** `lightrag/full-ingest@0.1.0` (the third named wiring) declares
`["calls_llm", "writes_artifact", "reads_kv", "reads_graph"]` with `artifact_scope="quarantined"`.
A wiring node built against it that also declares `writes_kv`/`writes_graph` etc. thinking these
feed into the same blast-radius check will get confused results, because
`blast_radius_violations` only ever inspects `writes_artifact` — the four transient store-write
effects (`writes_kv`/`writes_vector`/`writes_graph`/`writes_lexical`) sit **outside** the
blast-radius rule by design (`validator/blast_radius.py` module docstring, point 2; CONTRACT §3).
**Why it happens:** Both effect families look similar ("writes_X") but have entirely different
governing rules — one is depth-gated (artifact scope), the other is not.
**How to avoid:** When constructing the third named wiring or its probes, keep `writes_artifact` +
`artifact_scope` as the only levers that matter for blast-radius; treat the KV/graph read/write
effects as orthogonal capability declarations.
**Warning signs:** A probe wiring intended to trigger `blast-radius-refusal` that declares only
`writes_kv`/`writes_graph` and never `writes_artifact` will silently pass validation — that is not
a bug in the validator, it is the by-design exclusion.

### Pitfall 3: `body=None` declaration-only parts are un-dispatchable, not un-parseable
**What goes wrong:** Attempting to actually *run* (dispatch) a wiring built over any of the three
named-wiring parts raises `DeclarationOnlyPartError` — expected and correct (D-04), but easy to
mistake for a bug if the evidence script tries to call `run_wiring`/`dispatch` instead of stopping
at `parse_wiring`+`effective_depth`+`derive_execution_mode`.
**Why it happens:** The three named-wiring `Part` entries are schema-plus-effects-only stand-ins;
their real executable ports land in Phase 3/5.
**How to avoid:** The Falsifier 2 evidence run is a **validation-time** demonstration only — it
must call `parse_wiring`/`effective_depth`/`derive_execution_mode`/`blast_radius_violations`
directly, never `databasise.run_wiring` or `registry.dispatch()`, against these three parts.
**Warning signs:** `DeclarationOnlyPartError` raised anywhere in the evidence script.

### Pitfall 4: MACH-09's "off by default" has no code to point at yet — don't invent a switch that isn't load-bearing
**What goes wrong:** Building a `measurement_posture` config flag, an enum, or a settings object
implies there is a real on/off decision point somewhere in the current runtime. There is not: no
`promote-next`/`promote-now` verb, no ledger-write path, and no measurement-gated code exists
anywhere in the codebase yet (confirmed by grep — `databasise/ledger/ledger.py` exists but the
promote/rollback protocol itself, `§PR`, is Phase 7's `MACH-07`). Building a switch now creates an
unused abstraction with no caller.
**Why it happens:** MACH-09's requirement text ("measurement posture ... defaults off") reads like
it wants a runtime toggle, but the actual promotion machinery it would toggle does not exist in
this codebase yet.
**How to avoid:** Treat MACH-09 in Phase 2 as a **posture record** (documenting that the default-
off state holds because the on-path is simply unbuilt) plus, if the plan wants a concrete guard,
a minimal assertion/test that no promotion path exists that isn't `operator_asserted`-shaped —
not a new config surface with no consumer. The `degraded`/`degradation_reason` labelling mechanism
MACH-09 also names is *already* fully built in `databasise/runner/trace.py` (Phase 1, D-10) — cite
and test-confirm it, don't rebuild it.
**Warning signs:** A plan task that adds a new settings/config module for this phase when no other
phase-2 requirement needs one.

## Code Examples

### Loading the registry and confirming the three named parts exist
```python
# Source: databasise/parts/registry.py (default_registry), verified by Read this session
from databasise.parts.registry import default_registry

registry = default_registry()
assert "lightrag/query-side@0.1.0" in registry.keys()
assert "codebase-memory-mcp@0.1.0" in registry.keys()
assert "lightrag/full-ingest@0.1.0" in registry.keys()
```

### The exact effects[] each named part carries (verbatim from `databasise/parts_core/declared_only.py`)
```python
# LIGHTRAG_QUERY_SIDE_PART: structural_depth="stage",
#   effects=["reads_kv", "reads_vector", "reads_graph", "calls_llm", "calls_embedding"]
# CODEBASE_MEMORY_MCP_PART: structural_depth="opaque",
#   effects=["self_storage", "fs"], artifact_scope="self_storage"
# LIGHTRAG_FULL_INGEST_PART: structural_depth="opaque",
#   effects=["calls_llm", "writes_artifact", "reads_kv", "reads_graph"],
#   artifact_scope="quarantined"
```
[VERIFIED: databasise/parts_core/declared_only.py:17-51 — read this session]

## State of the Art

Not applicable in the usual "external ecosystem moved on" sense — this is a phase over
internally-owned, recently-built (2026-08-30/31) code. The one internal "state of the art"
correction worth recording: the tracer-era `validator.depth.derive_execution_mode` was superseded
by `validator.execution_mode.derive_execution_mode` during Phase 1 plan 01-03, and the superseded
copy was deliberately left in place rather than deleted (still imported by one test file). Any
Phase 2 work touching `execution_mode` must use the superseding version.

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `validator.depth.derive_execution_mode` (2-value, tracer-era) | `validator.execution_mode.derive_execution_mode` (4-value, `host()`-backed) | Phase 1, plan 01-03 | The old function is dead in production but still importable and still passes its own tests — a plausible trap for new code |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The evidence artifact's best location is a new `databasise/evidence/` (or equivalent) directory rather than `docs/system-model/wirings/` | Architecture Patterns | Low — this is explicitly "Claude's Discretion" per CONTEXT.md; the only firm finding is where NOT to put it (`docs/system-model/wirings/`, because its README states files there are illustrative/non-governing and use a different component vocabulary) |
| A2 | MACH-09's Phase 2 deliverable should be a posture record + optional guard rather than a new config module | Common Pitfalls / Architectural Responsibility Map | Medium — if a later phase (7) turns out to need a config surface sooner than expected, a Phase-2-built switch might have been premature but is not wrong, only early; verify with the owner during planning if the plan wants to add a config module now |
| A3 | The GATE-01 waiver record has no existing precedent format to imitate (grepped `SELECTION.md` and `docs/system-model/*.md` for "waiver" — no hits) | Phase Requirements table | Low — worst case the planner invents a reasonable format; there is no wrong-precedent risk since none exists |

**If this table is empty:** N/A — see above.

## Open Questions

1. **Exact shape of the "two self-declaration probes" the scratchpad demonstrated**
   - What we know: CONTEXT.md D-03 names both refusal codes (`blast-radius-refusal`,
     `effects-exceed-part`) and states they were demonstrated against the three named wirings in a
     scratchpad script that was never committed (`falsifier2_evidence.py`, session-local).
   - What's unclear: The exact wiring shapes the scratchpad used to trigger each refusal against
     the *named* wirings specifically (versus the existing, already-committed generic test
     fixtures in `tests/validator/test_cycles_and_depth.py` / `test_blast_radius.py`, which prove
     the same codes fire but not against these three specific parts).
   - Recommendation: The planner should treat the existing test fixtures (Pattern 2 above) as the
     structural template and construct fresh probe wirings against the three named parts directly
     — reproducing the scratchpad's intent rather than its exact (lost) code.

2. **Whether GATE-01's waiver record should live in `.planning/` or `docs/system-model/`**
   - What we know: CONTEXT.md's canonical_refs section cites
     `docs/system-model/D-VARIANTS/SELECTION.md` as the document the waiver "must cite" and that
     "governs on disagreement" — suggesting the waiver record is a governance artifact that should
     sit near SELECTION.md's own tier (`docs/system-model/`), not buried in `.planning/`.
   - What's unclear: Whether the project wants a new file under `docs/system-model/D-VARIANTS/` (a
     sibling to SELECTION.md) or a lighter-weight record under `.planning/phases/02-falsifier-gate/`.
   - Recommendation: Given `docs/system-model/` is explicitly a "verbatim copy of
     ServerDestroyer/rag-modality-swap-system-model" (per CLAUDE.md), a phase-owned amendment
     record likely belongs in `.planning/` (this project's own layer) with an explicit citation
     into `docs/system-model/D-VARIANTS/SELECTION.md`, rather than editing the upstream-mirrored
     directory directly — but this should be confirmed with the owner, since editing the frozen
     model directory at all may be undesirable regardless of location.

## Environment Availability

Skipped — this phase has no external tool/service dependencies. All work runs against the
already-installed `databasise` package and `pytest` inside the existing `.venv`
(`databasise/.venv`, confirmed present with `pytest`, `jsonschema`, etc. already installed).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2+ (already installed, `databasise/.venv`) |
| Config file | `databasise/pyproject.toml` |
| Quick run command | `cd databasise && uv run pytest -q tests/validator/` |
| Full suite command | `cd databasise && uv run pytest -q` (233+ tests as of 2026-08-31; matches `.planning/config.json`'s `workflow.test_command`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MACH-01 | Three named wirings compute correct `effective_depth`/`execution_mode`, §19.10 enumeration recorded | unit/evidence | `cd databasise && uv run pytest -q tests/validator/test_falsifier2_evidence.py -x` | ❌ Wave 0 — new file |
| MACH-01 | Self-declaration probe (a): over-declared effects refused | unit | same file, mirrors `tests/validator/test_cycles_and_depth.py`'s existing pattern | ❌ Wave 0 — new test, existing pattern to mirror at `databasise/tests/validator/test_cycles_and_depth.py:166-186` |
| MACH-01 | Self-declaration probe (b): shared write at non-stage depth refused | unit | same file, mirrors `tests/validator/test_blast_radius.py`'s existing pattern | ❌ Wave 0 — new test, existing pattern to mirror at `databasise/tests/validator/test_blast_radius.py:130-155` |
| MACH-09 | Posture record accurately reflects "no promotion-gated code exists" | doc/assertion | grep-based guard or a simple existence check, if the plan wants one | ❌ Wave 0, optional |
| GATE-01 | Waiver record exists and cites SELECTION.md | doc review (manual) | N/A — documentation artifact, not automated | ❌ Wave 0 — new doc |

### Sampling Rate
- **Per task commit:** `cd databasise && uv run pytest -q tests/validator/`
- **Per wave merge:** `cd databasise && uv run pytest -q` (full suite — matches `.planning/config.json`'s configured `test_command`)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `databasise/tests/validator/test_falsifier2_evidence.py` (or equivalent name/location per
      the plan's chosen artifact shape) — covers MACH-01's evidence run and both probes
- [ ] The evidence document itself (Markdown or generated) — covers MACH-01's "recorded" clause
- [ ] The GATE-01 waiver record document — covers GATE-01
- [ ] A short MACH-09 posture note (and optional guard) — covers MACH-09

*(No test-framework install gap: pytest and jsonschema are already installed and configured.)*

## Security Domain

`security_enforcement` is `false` in `.planning/config.json` (`workflow.security_enforcement:
false`) — this section is omitted per the skip condition.

## Sources

### Primary (HIGH confidence — read this session, code/docs verified)
- `databasise/validator/parse.py` — `parse_wiring`, one-pass violation accumulation, load-time depth/blast-radius call site
- `databasise/validator/depth.py` — `effective_depth` (taint rule, SCC-condensation), tracer-era `derive_execution_mode` (superseded, still present)
- `databasise/validator/execution_mode.py` — canonical `derive_execution_mode` (4-value), `host()`, `UnimplementedPlacementError`
- `databasise/validator/blast_radius.py` — `blast_radius_violations`, the three-property contract (writes_quarantined not an effect, writes_artifact distinguished from transient writes, message clarity)
- `databasise/validator/errors.py` — `Violation`/`ValidationReport`, all stable violation codes including `blast-radius-refusal`/`effects-exceed-part`
- `databasise/parts_core/declared_only.py` — the three named-wiring `Part` declarations, verbatim effects/depth/scope
- `databasise/parts/schema.py` — `Effect` (17-member Literal), `Depth`, `ArtifactScope`, `Part`, `WiringNode`
- `databasise/parts/registry.py` — `PartRegistry`, `default_registry()`, `dispatch()`, `DeclarationOnlyPartError`
- `databasise/runner/scheduler.py` (lines 1-75, 320-390) — confirms canonical `derive_execution_mode` import, CR-01 sourcing rule, cycles-as-data handling
- `databasise/runner/trace.py` — `RunRecord`/`NodeTrace`, the `partial`/`degraded`/`stop_reason`/`degradation_reason` required-together honesty invariant, already schema-validated
- `docs/system-model/CONTRACT.md` §3 (Depth and containment), §4 (Evidence and measurement), §5 (The gate), §6 (Promotion), §7 (Registries and retention), §19.9-§19.10 (boundary enumeration) — read this session
- `docs/system-model/RIG.md` §TR.3 (Partial/degraded/failure fields), §F3 (Falsifier 3 verdict), §F3.2 (default posture), §F3.3 (fallback ladders) — read this session
- `docs/system-model/rig-trace.schema.json` — `degraded`/`degradation_reason`/`stop_reason`/`partial` required-together `allOf` rule, grep-confirmed against `trace.py`'s implementation
- `docs/system-model/wirings/README.md` — confirms the existing wirings directory is illustrative-only, wrong location for real evidence
- `databasise/tests/validator/test_cycles_and_depth.py`, `test_blast_radius.py`, `test_execution_mode.py`, `test_taint_conformance.py` — existing probe patterns to mirror
- `.planning/phases/02-falsifier-gate/02-CONTEXT.md` — full owner re-scope, all locked decisions
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md` — phase requirement text, traceability table (still shows MACH-02/03/HARD-01/02 assigned to Phase 2 — needs a roadmap amendment per CONTEXT.md's own deferred-ideas note)
- `.planning/config.json` — confirms `security_enforcement: false`, `test_command`, `nyquist_validation: true`

### Secondary (MEDIUM confidence)
- None used — no web/library research was needed for this phase; everything load-bearing is in-repo.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new stack; every cited function/module was read directly this session
- Architecture: HIGH — data flow and file locations traced through actual imports/call sites (`runner/scheduler.py`, `validator/*.py`), not inferred
- Pitfalls: HIGH — the `derive_execution_mode` duplication and the `writes_artifact` vs. transient-writes distinction are both directly documented in the source's own docstrings, not speculative
- GATE-01 waiver format / MACH-09 posture shape: MEDIUM — no precedent exists in the repo, so the recommended shape is new-synthesis reasoning grounded in adjacent conventions, not a discovered pattern; flagged as Open Questions for owner confirmation during planning/discuss

**Research date:** 2026-08-31
**Valid until:** No external-dependency expiry; re-verify only if Phase 1 code the validator relies on changes before this phase executes (unlikely — Phase 1 is complete and merged)
