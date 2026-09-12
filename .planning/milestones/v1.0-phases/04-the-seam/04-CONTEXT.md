# Phase 4: The Seam - Context

**Gathered:** 2026-09-06
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — four grey areas proposed in batch, all four recommendations accepted by the owner

<domain>
## Phase Boundary

Callers reach the engine through one closed envelope that tells them nothing about which modality
answered. This phase builds the **consumer-facing** §18 seam — the query object in, the closed
response envelope out, the four selectors, the refusal vocabulary, the trace reference, and the
optional REST transport over the same call path.

**What this phase is not.** It does not add a modality, does not change any fitted part, and does
not touch the parity harness. Phase 3's `run_wiring` is a *machine-internal* entry point: it
returns a raw run record carrying `wiring_id`, node ids and instance hashes — exactly the fields
§18.2 forbids a consumer from receiving. This phase builds the redacting surface over it, and the
Phase 3 seam becomes internal rather than public.

The contract is unusually prescriptive here: §18.1 freezes the query object's five members,
§18.2 freezes the envelope's field set as a closed set, §18.4 freezes the four selectors, and
§18.5 freezes how the tool surface may grow. Those are frozen input, not open questions. The
decisions below are the implementation choices the contract deliberately leaves open.

</domain>

<decisions>
## Implementation Decisions

### Seam surface

- **D-01: An async `Databasise` class in a new `databasise/seam/` package.** It holds `store_root`
  and the parts registry, and exposes `async def query(...)`. Async-only — the whole codebase is
  async (`scheduler.run_wiring`, every store, every client), and paired sync wrappers are
  speculative surface until a real caller needs one.
- **D-02: `run_wiring` is demoted to machine-internal.** It stays importable (Phase 3's parity
  harness calls it directly and must keep working) but its docstring stops describing it as "the
  seam every consumer calls" — that sentence is now false, and leaving it would invite a consumer
  to take the un-redacted path.
- **D-03: One entry point per §18 operation, never per modality.** §18.5's growth rule is
  structural here: the surface grows per part kind, never per modality. A second modality answering
  an operation an existing entry point already exposes adds no entry point.

### The response envelope

- **D-04: A Pydantic model with a frozen field set.** Pydantic v2 is already a declared dependency
  (`databasise/pyproject.toml`), so this adds nothing to the dependency set and buys validation and
  serialization for free. The field set is exactly §18.2's: evidence references, trace reference,
  depth label and evidence tier labels, partial and degraded flags, and `counted_by` on every token
  number.
- **D-05: The closed-set rule is enforced twice, structurally and behaviorally.** The frozen model
  fixes the top-level shape; a conformance test additionally serializes a real envelope from a real
  run and fails if any wiring name, node id, or instance hash appears anywhere in the output at any
  nesting depth. The structural guard alone would miss an internal id smuggled inside a nested
  value, which is the failure mode that matters.
- **D-06: The trace reference is an opaque token, not a run id.** §18.2 requires internal identity
  to stay *behind* the reference; a raw `run_id` in the envelope is itself an internal identity.
  The token resolves to the run's trace record through §7's ledger apparatus (API-10).
- **D-07: Evidence references are machine-resolvable refs, never inline copies.** They follow §4's
  deref-raising discipline. A consumer receives a reference it can resolve, never a copy of
  evidence content that could silently diverge from the machine's own record (API-05).
- **D-08: Every token number carries `counted_by`, and an `unbudgetable` participant produces an
  explicit refusal.** Never a substituted or estimated number. Spend is never reported as capacity
  (API-11, §9).
- **D-09: MACH-11 — a `mutates_store` call outside a wiring's `deps` graph surfaces as a seam-level
  event** carrying `name@version`, spend, and outcome, per §18.2's envelope shape. It must not
  vanish just because it happened outside the dataflow.

### Selectors and refusal

- **D-10: An unsatisfiable selector raises a typed refusal exception at the library seam; the REST
  layer maps it to a refusal response.** Raising is idiomatic in-process and cannot be ignored by
  accident, which a returned refusal value can. The refusal names what was missing — never a silent
  fallback to the default (§18.4).
- **D-11: The four §18.4 selectors and nothing else:** a stable alias, a declared capability or
  capability set, a harness by name, or the default selector. A wiring name, node id, or instance
  hash is forbidden as *input* exactly as it is forbidden as output.
- **D-12: Aliases are read from the existing ledger** (`databasise/ledger/`), which already carries
  the record shape. Phase 7 builds promote/rollback on top; this phase only reads.
- **D-13: The default selector excludes parts at `opaque` effective depth** per §8 condition 7.
  Exclusion from the default selector is not exclusion from the seam — an opaque part remains
  explicitly selectable by alias, capability, or harness name.
- **D-14: An unconsumable query-object member is refused by name**, never silently dropped and
  answered from the remainder (§18.1). A silently narrowed query is indistinguishable from a
  deliberately narrow one.

### The REST transport

- **D-15: REST ships in this phase, with FastAPI behind an optional dependency group.** ROADMAP
  criterion 5 requires the same seam reachable two ways, so deferring it would leave the phase's
  own criterion unmet. Putting FastAPI in an optional group keeps the embedded library's dependency
  set exactly as it is today — the machine stays embeddable without pulling a web stack.
- **D-16: Streaming via server-sent events** (API-04).
- **D-17: One call path, proven by test.** REST is a thin layer over the same seam object
  (EMBED-02). A conformance test asserts both transports produce the same envelope for the same
  query — not merely that both work.

### Claude's Discretion

Module layout within `databasise/seam/`, the concrete names of the refusal exception types, the
SSE event framing, and the internal shape of the opaque trace token are all at Claude's discretion,
provided the decisions above hold.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `databasise/runner/scheduler.py` — `async def run_wiring(...)` is the execution path the seam
  wraps. It already returns `partial`, `degraded`, `stop_reason` and `degradation_reason`, which
  are four of §18.2's required envelope inputs.
- `databasise/runner/trace.py` — `RunRecord` already carries `counted_by` and enforces an honesty
  invariant (a node reporting a halted budget state while the run is not marked partial raises).
  The envelope's partial/degraded flags derive from here rather than being recomputed.
- `databasise/wirings/resolve.py` — `resolve_arm(arm_name)`, `resolved_node_ids`,
  `declared_node_ids` and `UnknownArmError`. Arm resolution exists; selector resolution is the new
  layer above it.
- `databasise/ledger/ledger.py` — `LedgerRecord` and `Ledger`, the alias source for D-12.
- `databasise/parts/registry.py` and `schema.py` — declared capabilities, the input to the
  capability selector.
- `databasise/identity/` — `canonicalise` (RFC 8785) is available if the opaque trace token needs a
  stable derivation.

### Established Patterns

- **Async throughout.** Every store, client, and the scheduler are `async`. D-01 follows this.
- **Refusals over silent fallbacks.** `MissingParityEnvKeyError`, `UnparseableProviderRoutingError`,
  `UnknownArmError`, and the multi-namespace vector store's no-silent-default refusal are the house
  style Phase 3 established. D-10 and D-14 continue it.
- **Pydantic v2 is present but barely used.** The codebase leans on dataclasses; D-04 is the first
  substantial Pydantic model. Follow `parts/schema.py`'s existing typing conventions where they
  apply.
- **Tests assert against real data, never shape alone.** Phase 3's code review rejected a
  shape-only assertion twice. The conformance tests in D-05 and D-17 must assert real values.

### Integration Points

- The seam sits above `run_wiring` and below any consumer. Nothing currently imports a consumer
  surface, so there is no existing caller to migrate.
- `databasise/__init__.py`'s module docstring currently names `run_wiring` as "the seam every later
  plan and every consumer calls" — D-02 requires that sentence to change.
- Phase 3's parity harness (`databasise/parity/run_arm.py`) calls `run_wiring` directly and must
  keep working unchanged.

</code_context>

<specifics>
## Specific Ideas

The §18 falsifier is the phase's own success test, stated in the contract: the seam is refuted if
any of the Phase 3 stress modalities cannot be reached through it without a modality-specific field
or a modality-specific tool, or if a consumer needs a wiring name — rather than an alias, a
capability, or a harness name — to select what it wants. The five arms Phase 3 built (`naive`,
`bypass`, `hybrid`, `local`, `global`) are available as real subjects for exactly that test.

</specifics>

<deferred>
## Deferred Ideas

- Sync wrappers over the async seam (D-01) — add when a real non-async caller exists.
- MCP transport (API-07) — the ROADMAP scopes this phase to REST plus in-process; the MCP surface
  is a later concern and, per §18.5, must add no tool a selector could express.
- Promote/rollback over the alias the seam reads (D-12) — Phase 7.

</deferred>
