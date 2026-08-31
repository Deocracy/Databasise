# Phase 2: Falsifier Gate - Context

**Gathered:** 2026-08-31
**Status:** Ready for planning

<domain>
## Phase Boundary

**Re-scoped by owner decision (2026-08-31).** The owner directed a product-first posture: build
Databasise to completion; formal eval/QC infrastructure runs at point of need, with a human in the
loop for verdicts, not front-loaded. Phase 2 shrinks to the near-free items and records the waiver
of the front-loaded gate.

In scope:
- **Falsifier 2 evidence run** (MACH-01): validator over the three named wirings with computed
  `effective_depth` / `execution_mode` and the §19.10 boundary enumeration recorded — as committed
  JSON wirings + a committed evidence artifact. Already demonstrated free on 2026-08-31 (all
  probes pass, falsifier does not fire); Phase 2 execution formalizes it.
- **MACH-09 posture**: answer-level and index-side measurement off by default; fallback runs
  labelled `degraded`/`degradation_reason`.
- **GATE-01 waiver record**: the recorded owner decision that Falsifier 5 moves to point of first
  need and the ladder proceeds; a Falsifier 2 failure still halts.

Moved out of this phase (owner decision — see Deferred):
- **MACH-02 (eval bundle) and MACH-03 (A/A calibration / Falsifier 5)** → deferred to point of
  first need, Phase 3's parity comparison at the earliest, calibrated against the real
  pre-decomposition original rather than a stand-in arm.
- **HARD-01 (gate-script vacuous-pass fixes) and HARD-02 (ANATOMY §F reconciliation)** → deferred
  doc pass; guards model documents, not the product.

</domain>

<decisions>
## Implementation Decisions

### Gate re-scope (owner decisions, 2026-08-31)

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

### Eval-run decisions banked for when Falsifier 5 runs (researched 2026-08-31, live OpenRouter data)

- **D-06:** Corpus: **HotpotQA distractor setting** — ships gold answers AND gold passages (both
  §EV.2 families, zero authoring cost), corpus size scales with question count, and it is
  HippoRAG 2's own benchmark family so Phase 6 inherits a comparable bundle.
- **D-07:** Generator: **qwen/qwen3.7-flash via OpenRouter, provider-pinned** ($0.03/M in,
  $0.13/M out; recorded calibration ≈ $0.10). Free models (z-ai/glm-5.2:free et al.) for drafts
  only — free variants re-route across providers, and an identity change mid-run voids the floor.
- **D-08:** Judge: **never free** — gemini-3.1-flash-lite or gpt-5-mini, provider-pinned, prompt
  hashed. The judge instance is part of `bundle@v` identity (§EV.1); derive its identity from the
  provider/model returned in the response, not the requested id (same rule as Phase 1's D-12:
  hash what is installed, not what is declared). — **Reversibility:** one-way once a bundle is
  minted — changing the judge mints a new `bundle@v` and voids every null calibrated under it.
- **D-09:** Embedder: local (bge / nomic via Ollama) — keeps T1 genuinely free; OpenRouter is
  chat-completions oriented.
- **D-10:** Declared concurrency for any calibration: **8**, picked once and kept through Phase 3
  (§AA.1 keys the null to the setting; a floor cannot be borrowed across settings).
  — **Reversibility:** costly — changing it later requires recalibrating the floor.
- **D-11:** Calibration preconditions to verify before a recorded run: cache bypassed (checkable
  via the run record's per-node `cache_hit`), temperature > 0 honored by the pinned provider, and
  no invisible upstream prompt caching (§AA.2: an unknown-bypass floor is unusable).
- **D-12:** Account prep: put $10 lifetime credits on the OpenRouter account — lifts free-tier
  quota from 50 to 1,000 requests/day for all draft work.

### Parallelization (settled by inspection, 2026-08-31)

- **D-13:** The v1 "3 runs at a time" cap (`DEFAULT_MAX_PARALLEL_INSERT = 3`, `MAX_ASYNC = 4`,
  process-wide lock in `v1/lightrag/kg/shared_storage.py`) is confirmed gone in the v2 machine:
  concurrency is a per-node semaphore sized by that node's own `config.max_concurrency`
  (default 1), never shared, no global cap (Phase 1 D-09/D-11). Mass parallelism is a per-node
  config value; the binding limit is the API provider.

### Claude's Discretion

- Shape and location of the committed Falsifier 2 evidence artifact (JSON wirings + evidence doc)
  and of the GATE-01 waiver record.
- MACH-09 implementation detail (where the posture switches live, how `degraded` labelling is
  wired), within the refusals-over-silent-fallbacks house style.
- Test structure for the evidence run, following existing databasise/tests conventions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Frozen contract — what this phase proves and records

- `docs/system-model/CONTRACT.md` §3 — depth computed not declared, taint rule, blast-radius
  rule, three artifact scopes, `execution_mode` derivation
- `docs/system-model/CONTRACT.md` §19.10 — boundary enumeration: recorded with the node set so a
  second author can check the candidate set, not only the verdicts
- `docs/system-model/RIG.md` §F3.2 — the default measurement posture MACH-09 implements
  (off by default; what survives: check/preview/run, traces, manual promotion)
- `docs/system-model/RIG.md` §TR.3 — `degraded` / `degradation_reason` labelling
- `docs/system-model/RIG.md` §EV.1–§EV.3, §AA.1–§AA.3 — the deferred bundle/calibration design
  (read when Falsifier 5 is stood up, not for Phase 2 execution)
- `docs/system-model/D-VARIANTS/SELECTION.md` — governs on disagreement; the waiver record
  amends the §VD condition and must cite it

### Phase 1 outputs this phase computes over

- `databasise/parts_core/declared_only.py` — the three declaration-only parts for the named
  wirings (D-04, Phase 1)
- `databasise/validator/` — parse, depth, execution_mode, blast_radius (the mechanism, complete)
- `.planning/phases/01-machine-core/01-CONTEXT.md` — Phase 1 decisions D-01..D-14

### Evidence precedent

- Scratchpad demonstration script (2026-08-31, session-local, not committed):
  `falsifier2_evidence.py` — three wirings, computed-vs-declared table, probes (a)/(b)/(c) all
  refused correctly. Recreate as committed artifacts during execution.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `databasise.validator.parse.parse_wiring(doc, registry)` → `ParsedWiring` with accumulated
  `report` (all violations at once, cycles as data)
- `databasise.validator.depth.effective_depth(parsed)` / `derive_execution_mode(effects, kind)`
- `databasise.validator.blast_radius.blast_radius_violations(parsed, depth_map)`
- `databasise.parts.registry.default_registry()` — already seeds the three declared-only parts
- 233-test suite green as of 2026-08-31

### Established Patterns

- Refusals over silent fallbacks (Phase 1 house style; MACH-09's `degraded` labelling follows it)
- Evidence lands as committed files reviewable by the owner, not transient output

### Integration Points

- The GATE-01 waiver record is the input Phase 3 planning cites for its retrieval-level parity
  gate (D-05 above)
- Phase 3 stands up MACH-02/MACH-03 when its parity comparison first needs a floor, using D-06..
  D-12's banked decisions

</code_context>

<specifics>
## Specific Ideas

- Owner: "I would rather build the product then edit and fix it later according to checks" — and
  wants a human in the loop, having observed LLMs running unnecessary tests that navigate around
  the goal. Test scope needs owner opt-in beyond what this context locks.
- Owner wants components like the falsifier visible "in a working environment" — the evidence
  artifact should be something the owner can re-run and read, not a buried pytest assertion.
- Cost reality check (2026-08-31 prices): the entire original Phase 2 including a graph-extract
  index was < $1 in API cost; the deferral is about focus and sequencing, not money.

</specifics>

<deferred>
## Deferred Ideas

- **MACH-02 / MACH-03 (eval bundle + A/A calibration, Falsifier 5)** → Phase 3 at the earliest,
  at the parity comparison's point of need, against the real pre-decomposition original. Banked
  decisions D-06..D-12 apply. REQUIREMENTS.md and ROADMAP.md still assign these to Phase 2 —
  amend during planning (roadmap edit) so coverage tracking follows the re-scope.
- **HARD-01 (parts-check.sh / anatomy-check.sh vacuous-pass fixes)** → later doc pass.
- **HARD-02 (eight ANATOMY §F rows + stale cross-document rows)** → same later doc pass.
- **Review GUI for human-in-the-loop checking** → scope addition if wanted; current scope is
  API-only (Sourcerer is the client). Phase 6's verdict-free comparison output is the designed
  hook for human review.
- **DuckDB for scoreboard/trace analytics** (Phase 1 deferred idea) → only relevant when the
  statistical machinery is stood up; stays deferred with it.

</deferred>

---

*Phase: 2-Falsifier Gate*
*Context gathered: 2026-08-31*
