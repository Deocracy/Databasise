# Phase 4: The Seam - Research

**Researched:** 2026-09-06
**Domain:** Public API surface (async Python facade + optional FastAPI/SSE transport) over an internal async scheduler; Pydantic v2 closed-envelope modeling; redaction/leak-testing methodology
**Confidence:** MEDIUM — the contract text (§18, §4, §8, §9, §14.2, §19.8) is prescriptive and fully read; the codebase seams this phase must wrap (`run_wiring`, `RunRecord`, `resolve.py`, `ledger.py`) are fully read and quoted below; the parts that are genuinely unresolved (capability-selector semantics, the ledger's total absence of an "alias" concept, `ParsedWiring`'s silent drop of `provides`/`harnesses`) are flagged as open questions rather than guessed at.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Seam surface**
- **D-01: An async `Databasise` class in a new `databasise/seam/` package.** It holds `store_root` and the parts registry, and exposes `async def query(...)`. Async-only — the whole codebase is async (`scheduler.run_wiring`, every store, every client), and paired sync wrappers are speculative surface until a real caller needs one.
- **D-02: `run_wiring` is demoted to machine-internal.** It stays importable (Phase 3's parity harness calls it directly and must keep working) but its docstring stops describing it as "the seam every consumer calls" — that sentence is now false, and leaving it would invite a consumer to take the un-redacted path.
- **D-03: One entry point per §18 operation, never per modality.** §18.5's growth rule is structural here: the surface grows per part kind, never per modality. A second modality answering an operation an existing entry point already exposes adds no entry point.

**The response envelope**
- **D-04: A Pydantic model with a frozen field set.** Pydantic v2 is already a declared dependency (`databasise/pyproject.toml`), so this adds nothing to the dependency set and buys validation and serialization for free. The field set is exactly §18.2's: evidence references, trace reference, depth label and evidence tier labels, partial and degraded flags, and `counted_by` on every token number.
- **D-05: The closed-set rule is enforced twice, structurally and behaviorally.** The frozen model fixes the top-level shape; a conformance test additionally serializes a real envelope from a real run and fails if any wiring name, node id, or instance hash appears anywhere in the output at any nesting depth. The structural guard alone would miss an internal id smuggled inside a nested value, which is the failure mode that matters.
- **D-06: The trace reference is an opaque token, not a run id.** §18.2 requires internal identity to stay *behind* the reference; a raw `run_id` in the envelope is itself an internal identity. The token resolves to the run's trace record through §7's ledger apparatus (API-10).
- **D-07: Evidence references are machine-resolvable refs, never inline copies.** They follow §4's deref-raising discipline. A consumer receives a reference it can resolve, never a copy of evidence content that could silently diverge from the machine's own record (API-05).
- **D-08: Every token number carries `counted_by`, and an `unbudgetable` participant produces an explicit refusal.** Never a substituted or estimated number. Spend is never reported as capacity (API-11, §9).
- **D-09: MACH-11 — a `mutates_store` call outside a wiring's `deps` graph surfaces as a seam-level event** carrying `name@version`, spend, and outcome, per §18.2's envelope shape. It must not vanish just because it happened outside the dataflow.

**Selectors and refusal**
- **D-10: An unsatisfiable selector raises a typed refusal exception at the library seam; the REST layer maps it to a refusal response.** Raising is idiomatic in-process and cannot be ignored by accident, which a returned refusal value can. The refusal names what was missing — never a silent fallback to the default (§18.4).
- **D-11: The four §18.4 selectors and nothing else:** a stable alias, a declared capability or capability set, a harness by name, or the default selector. A wiring name, node id, or instance hash is forbidden as *input* exactly as it is forbidden as output.
- **D-12: Aliases are read from the existing ledger** (`databasise/ledger/`), which already carries the record shape. Phase 7 builds promote/rollback on top; this phase only reads.
- **D-13: The default selector excludes parts at `opaque` effective depth** per §8 condition 7. Exclusion from the default selector is not exclusion from the seam — an opaque part remains explicitly selectable by alias, capability, or harness name.
- **D-14: An unconsumable query-object member is refused by name**, never silently dropped and answered from the remainder (§18.1). A silently narrowed query is indistinguishable from a deliberately narrow one.

**The REST transport**
- **D-15: REST ships in this phase, with FastAPI behind an optional dependency group.** ROADMAP criterion 5 requires the same seam reachable two ways, so deferring it would leave the phase's own criterion unmet. Putting FastAPI in an optional group keeps the embedded library's dependency set exactly as it is today — the machine stays embeddable without pulling a web stack.
- **D-16: Streaming via server-sent events** (API-04).
- **D-17: One call path, proven by test.** REST is a thin layer over the same seam object (EMBED-02). A conformance test asserts both transports produce the same envelope for the same query — not merely that both work.

### Claude's Discretion

Module layout within `databasise/seam/`, the concrete names of the refusal exception types, the SSE event framing, and the internal shape of the opaque trace token are all at Claude's discretion, provided the decisions above hold.

### Deferred Ideas (OUT OF SCOPE)

- Sync wrappers over the async seam (D-01) — add when a real non-async caller exists.
- MCP transport (API-07) — the ROADMAP scopes this phase to REST plus in-process; the MCP surface is a later concern and, per §18.5, must add no tool a selector could express.
- Promote/rollback over the alias the seam reads (D-12) — Phase 7.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| API-03 | Caller queries with §18.1's query object; selection via §18.4's four selectors; unsatisfiable selector / unconsumable member is refused by name; opaque nodes excluded from default; §18.2 closed envelope | See "The query object" and "The four selectors" under Architecture Patterns; field-by-field envelope mapping under Common Pitfalls |
| API-04 | Caller can stream query responses | See "SSE streaming" — FastAPI 0.135+ ships native `EventSourceResponse`, no extra dependency; async-generator-to-SSE pattern documented |
| API-05 | Every answer carries citations/provenance (evidence references per §18.2) | See "No `ScoredItem`/`ChunkRef` exists yet" pitfall — this phase must construct minimal machine-resolvable refs from raw store output, there is nothing to reuse |
| API-10 | Trace reference reached through §18.2; debug-flagged; internal identities never enter the envelope | See "The trace-token design" — no run-record persistence exists yet either; this phase adds it |
| API-11 | `counted_by` on every token number; explicit refusal for `unbudgetable`; spend never conflated with capacity | See "Token accounting has no single aggregate" pitfall — per-node `counted_by` already exists and can disagree across nodes |
| MACH-11 | Envelope extended with seam-level event shape (`name@version`, spend, outcome) for `mutates_store`-outside-`deps` | See "MACH-11's event has no source yet" — nothing in the current scheduler distinguishes an in-`deps` mutation from an out-of-`deps` one |
| EMBED-02 | REST + MCP server is a thin optional layer over the same seam; one seam, two transports | See "FastAPI as an optional dependency" and "One call path, proven by test" |
</phase_requirements>

## Summary

This phase builds a redacting facade over `databasise.runner.scheduler.run_wiring` (wrapped today by `databasise/__init__.py:run_wiring` and, for the five real LightRAG arms, by `databasise/parity/run_arm.py`). Both of those existing entry points already assemble almost everything the envelope needs — a `RunRecord` carrying `partial`/`degraded`/`stop_reason`/`degradation_reason` (already honesty-checked at construction), per-node `TokenAccounting.counted_by`, and a `provides`-keyed results dict — but every one of those existing entry points returns **exactly** the internal-identity-bearing shape §18.2 forbids exposing: `wiring_id`, `wiring_instance_hash`, `arm_id`, and a `node_id` on every trace entry. The seam's job is subtractive and additive at once: strip every internal identity `run_arm.py`'s own return shape already carries, and add several fields nothing in the codebase produces yet — a machine-resolvable evidence ref (no `ScoredItem`/`ChunkRef` type exists in this codebase today), an opaque trace token backed by a persisted run record (nothing persists a `RunRecord` today; it is constructed and returned in-memory only), and a `name@version`/spend/outcome event for the `mutates_store`-outside-`deps` case (nothing in the scheduler distinguishes that case from an ordinary declared mutation today).

Two of D-11's four selectors have no concrete implementation to select over yet, and this is the single most important thing for the planner to know before estimating this phase: `ParsedWiring` (`databasise/validator/parse.py`) never reads or exposes a wiring document's `provides`, `harnesses`, or `recipe` top-level members — it silently drops them, reading only `nodes`. Those three keys **do** exist in the raw wiring JSON (`databasise/wirings/lightrag/base.json` carries `"recipe"`, `"harnesses": []`, `"provides": ["generate"]`), and `run_arm.py` already reads `resolved.get("provides")` directly off the raw dict rather than through `ParsedWiring` — that is the precedent to generalize, not a gap to fix in the validator. The harness selector has no test subject at all: the LightRAG base wiring's own `harnesses` array is empty, so there is no way to prove that selector end-to-end against the five real arms this phase is supposed to exercise (the phase's own falsifier names the five arms as "real subjects" but says nothing about a harness). The alias selector (D-12) has a similar gap: `databasise/ledger/ledger.py`'s `LedgerRecord` has a `mutation_id` field and no `alias` field anywhere — "aliases are read from the existing ledger" is a CONTEXT.md claim about intent, not a description of an existing column, and the planner needs to decide (or add a task to decide) what in the ledger schema actually plays the alias role before D-12 can be implemented as written.

**Primary recommendation:** Build the seam as a thin, mostly-mechanical transform over the exact shape `databasise/parity/run_arm.py` already produces (resolve → inject query → parse → build stores/clients → `scheduler.run_wiring` → `RunRecord`), generalized to read `provides`/`harnesses` off the raw wiring dict the way `run_arm.py` already does; use Pydantic v2's `frozen=True, extra="forbid"` on every nested envelope model individually (nested strictness is not inherited in Pydantic v2 — this is a real, cited gotcha, not folklore); ship REST behind a `[project.optional-dependencies]` extra (not the existing PEP 735 `dev` dependency-group, which is invisible to installers and cannot be the mechanism for an installable runtime feature); and use FastAPI's own native `EventSourceResponse` (built in since FastAPI 0.135, confirmed via the framework's own PR #15030 and current release notes) rather than adding `sse-starlette` as a dependency.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Query-object validation, selector resolution, refusal raising | Backend / library seam (`databasise/seam/`) | — | §18.1/§18.4 are machine-enforced rules over machine-owned state (registry, ledger, wiring documents); no other tier has visibility into any of it |
| Envelope assembly (redaction, evidence-ref construction, trace-token minting) | Backend / library seam | — | The only tier that sees the un-redacted `RunRecord`; redaction must happen exactly once, at the seam, never re-derived downstream |
| REST transport (routing, request/response (de)serialization, SSE framing) | Backend / thin adapter (`databasise/seam/rest.py` or similar) | — | D-17 requires this be provably a thin adapter over the library seam — it must add no logic the library seam does not already have |
| In-process consumer (`import databasise; await Databasise(...).query(...)`) | Backend / library seam | — | The other of the seam's two required transports (criterion 5); no adapter code at all, direct call |
| Persisted trace record backing the opaque token (API-10) | Backend / storage (new: a trace store, likely SQLite beside `ledger.db`) | — | Nothing in the codebase persists a `RunRecord` today (`databasise/__init__.py:run_wiring` returns it in-memory only); the trace token is meaningless without something durable to resolve it against |
| Alias resolution (D-12) | Backend / `databasise/ledger/` | Backend / library seam | The ledger is machine-owned state; the seam reads it, never writes it (that is Phase 7's job) — but see the Open Questions section: the ledger schema as it exists today has no field that is unambiguously "the alias" |
| Capability-selector matching | Backend / library seam, reading `parts/schema.py`'s `Effect` vocabulary and `parts_core`'s registered `Part.effects` | — | §14.1 explicitly calls `effects[]` "the base capability vocabulary" — the only capability vocabulary that exists in code today |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pydantic` | 2.13.5 (verified installed in `databasise/.venv`; project pin `>=2.0,<3.0`) | The frozen, closed `ResponseEnvelope` model (D-04) | Already a project dependency; D-04's own rationale — adds nothing new |
| `fastapi` | `>=0.135` recommended (current PyPI release 0.141.1 as of this research) | Optional REST transport | Native `EventSourceResponse` for SSE ships from 0.135 onward — pinning below that forces a hand-rolled SSE framer or an extra dependency (`sse-starlette`) for no reason |
| `uvicorn` | Match `v1/pyproject.toml`'s existing unconstrained pin, or the current PyPI release | ASGI server to run the optional REST app | Already used elsewhere in this monorepo (`v1/pyproject.toml:95`) |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `httpx` | Match `v1/pyproject.toml`'s `>=0.28.1` | Test-only: drive the REST transport in D-17's dual-transport conformance test | FastAPI's own `TestClient` is httpx-based; needed as a **dev**-group (test) dependency regardless of whether the `rest` extra is installed, since the conformance test must exercise both transports |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FastAPI's native `EventSourceResponse` (0.135+) | `sse-starlette`'s `EventSourceResponse` | `sse-starlette` is the older, still-widely-used approach and works on any FastAPI version, but adds a dependency the native feature now makes unnecessary — pin FastAPI high enough and skip it (Ponytail rung 4/5: native platform feature over an added dependency) |
| A hand-rolled `"data: ...\n\n"` framer over `StreamingResponse` | Either of the above | Manual framing is what teams did before 0.135; it works, but it is exactly the kind of hand-rolled protocol-framing code the "Don't Hand-Roll" section below recommends against once a maintained option exists at zero extra dependency cost |

**Installation:**
```toml
# databasise/pyproject.toml — add a [project.optional-dependencies] extra (NOT the existing
# PEP 735 [dependency-groups] "dev" group — see the "FastAPI as an optional dependency" pattern
# below for why the two are not interchangeable).
[project.optional-dependencies]
rest = ["fastapi>=0.135", "uvicorn"]
```
```bash
cd databasise && uv sync --extra rest   # or: pip install -e ".[rest]"
```

**Version verification:** `databasise/.venv/bin/python -c "import pydantic; print(pydantic.VERSION)"` → `2.13.5` [VERIFIED: databasise/.venv, checked this session]. `fastapi` is **not installed** in `databasise/.venv` today [VERIFIED: `ModuleNotFoundError` raised this session] — confirming D-15's premise that it is genuinely absent, not merely unused. Current FastAPI release is 0.141.1 per PyPI's own package JSON, fetched this session [VERIFIED: pypi.org/pypi/fastapi/json]. FastAPI's native SSE support landing at 0.135 is corroborated by two independent sources: the framework's own tutorial page (`fastapi.tiangolo.com/tutorial/server-sent-events/`, fetched this session) and GitHub PR #15030 ("✨ Add support for Server Sent Events" by tiangolo, found via web search) [CITED: fastapi.tiangolo.com/tutorial/server-sent-events/] [CITED: github.com/fastapi/fastapi/pull/15030].

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| fastapi | PyPI | N/A — legitimacy tool reports only the newest release's publish date (2026-07-29), not package founding date | Not reported by tool ("unknown-downloads") | `github.com/fastapi/fastapi` (correct, matches official project) | SUS (tool artifact — see note) | Approved, but see note below |
| uvicorn | PyPI | Same limitation ("too-new", "unknown-downloads") | Not reported | `github.com/Kludex/uvicorn` (correct — Kludex is the current real maintainer) | SUS (tool artifact) | Approved, but see note below |
| httpx | PyPI | Same limitation | Not reported | `github.com/encode/httpx` (correct) | SUS (tool artifact) | Approved (dev/test-only) |

**Packages removed due to `[SLOP]` verdict:** none.

**Packages flagged as suspicious `[SUS]`:** fastapi, uvicorn, httpx — all three, but the SUS verdicts here are a **tool data-source artifact**, not a substantive finding: the legitimacy checker's PyPI signal source appears to report only the newest release's publish timestamp (interpreted by the tool as "too-new") and has no download-count data for PyPI packages at all, which triggers `unknown-downloads` for essentially every PyPI package checked this way. The repository URLs the tool did resolve are the correct, canonical GitHub organizations for all three projects (`fastapi/fastapi`, `Kludex/uvicorn`, `encode/httpx`) [VERIFIED: `gsd-tools query package-legitimacy check --ecosystem pypi`, run this session]. All three are already approved, in-use dependencies of `v1/pyproject.toml` in this same monorepo (`fastapi>=0.108`, `httpx>=0.28.1`, `uvicorn`) [VERIFIED: v1/pyproject.toml:85,87,95, read this session]. Per protocol the planner should still add a lightweight `checkpoint:human-verify` before the actual `uv add` for the new `rest` extra, but this is a process formality here, not a live risk signal — do not spend investigation time on it beyond that checkpoint.

## Architecture Patterns

### System Architecture Diagram

```
                        ┌───────────────────────────┐
                        │  Consumer (in-process)     │
                        │  import databasise; await  │
                        │  Databasise(...).query(q)  │
                        └──────────────┬─────────────┘
                                       │
   ┌───────────────────────────┐      │      ┌──────────────────────────────┐
   │  Consumer (REST)          │      │      │  Consumer (REST, streaming)   │
   │  POST /query              │      │      │  GET /query/stream (SSE)      │
   └──────────────┬────────────┘      │      └───────────────┬───────────────┘
                  │ thin adapter       │                      │ thin adapter,
                  │ (deserialize req,  │                      │ wraps the SAME
                  │  serialize resp)   │                      │ async generator
                  ▼                    ▼                      ▼
         ┌────────────────────────────────────────────────────────────┐
         │        databasise.seam.Databasise.query(query_obj, selector)│
         │  1. validate query object (§18.1) — refuse unconsumable     │
         │     member by name (D-14)                                  │
         │  2. resolve selector -> concrete wiring doc (§18.4)         │
         │     - alias   -> ledger read (D-12)                        │
         │     - capability -> match against registered Part.effects  │
         │     - harness -> match wiring's `harnesses` array          │
         │     - default -> exclude opaque-depth parts (D-13)         │
         │     UNSATISFIABLE -> raise typed refusal (D-10)            │
         │  3. inject query text, call runner.scheduler.run_wiring    │
         │     (the exact pattern databasise/parity/run_arm.py        │
         │     already establishes)                                  │
         │  4. redact: strip wiring_id/wiring_instance_hash/arm_id/   │
         │     node_id/instance_hash from every returned structure    │
         │  5. mint opaque trace token, persist trace record          │
         │  6. assemble frozen ResponseEnvelope (Pydantic v2)         │
         └───────────────────────────────┬──────────────────────────┘
                                          │
                                          ▼
                        ┌─────────────────────────────────┐
                        │ databasise.runner.scheduler       │
                        │ .run_wiring (machine-internal,    │
                        │ D-02 — never called by a consumer │
                        │ directly again)                   │
                        └─────────────────────────────────┘
```

### Recommended Project Structure

```
databasise/seam/
├── __init__.py          # exports Databasise, query-object model, refusal exception types
├── query.py             # §18.1 query-object Pydantic model + per-member consumption validation
├── selectors.py         # §18.4 selector resolution: alias (ledger read), capability, harness, default
├── envelope.py          # §18.2 ResponseEnvelope frozen Pydantic model(s) + assembly function
├── redact.py            # the D-05 redaction step + the leak-test's ground-truth-forbidden-set helper
├── trace_store.py        # persists RunRecord-shaped data keyed by the opaque trace token (API-10)
├── refusals.py           # typed refusal exception hierarchy (D-10)
└── rest.py               # optional: only imported when `databasise[rest]` is installed; FastAPI app,
                           # import-guarded (see "FastAPI as an optional dependency" below)
```

### Pattern 1: Generalizing `run_arm.py`'s call shape rather than inventing a new one

**What:** `databasise/parity/run_arm.py:run_arm()` already does almost exactly what the seam's internal query execution needs to do: `resolve_arm(name)` (or, for the seam, a selector-resolved wiring doc) → `_inject_query(resolved, query)` → `parse_wiring(resolved, registry)` → build stores/clients → `scheduler.run_wiring(...)` → construct a `RunRecord` → read `resolved.get("provides")` for the answer-bearing node(s).
**When to use:** As the literal template for the seam's internal `_execute(wiring_doc, query_obj)` helper. The differences from `run_arm.py` are: (1) the wiring doc comes from selector resolution, not a hardcoded arm name; (2) the query comes from §18.1's query object, not a bare string; (3) the result must be redacted before returning, never returned as `run_arm.py` currently returns it (keyed by `node_id`, carrying `wiring_id`/`arm_id`/`instance_hash` throughout).
**Example — the exact precedent, read this session:**
```python
# Source: databasise/parity/run_arm.py:276-330 (read this session)
resolved = resolve_arm(arm_name)                       # -> becomes: selector-resolved wiring doc
resolved = _inject_query(resolved, query)               # generalize: query object, not bare string
resolved = _inject_token_allowance(resolved, token_allowance)
parsed = parse_wiring(resolved, registry)
stores = _build_stores(resolved_store_root, resolved_workspace)
resolved_clients = clients or _build_clients(env)
scheduled = await _scheduler.run_wiring(
    parsed, registry, stores,
    determinism_setting=_DETERMINISM_SETTING,
    concurrency_setting=_CONCURRENCY_SETTING,
    clients=resolved_clients,
)
# ... RunRecord construction ...
provides = resolved.get("provides") or []               # <- provides read off the RAW dict,
provided = {node_id: scheduled["results"].get(node_id)   #    never through ParsedWiring, which
            for node_id in provides}                      #    does not carry this field at all
return {"run_record": record.to_dict(), "provided": provided}
```
This confirms the correct place to read `provides`/`harnesses` is the raw wiring dict, not `ParsedWiring` — see the pitfall below for why `ParsedWiring` cannot be used for this.

### Pattern 2: Typed refusal hierarchy, following the house style already established

**What:** Every existing named refusal in this codebase (`MissingParityEnvKeyError`, `UnparseableProviderRoutingError`, `UnknownArmError`, `WiringRefusedError`, `InvalidMaxConcurrencyError`, `UnknownPartError`) is a `ValueError`/`RuntimeError`/`KeyError` subclass that names exactly what was wrong in its constructor and message — never a bare stdlib exception.
**When to use:** D-10's typed refusal exception(s) for an unsatisfiable selector, and D-14's for an unconsumable query-object member, should follow this exact shape.
**Example:**
```python
# Source: databasise/wirings/resolve.py:32-41 (read this session) — the pattern to mirror
class UnknownArmError(ValueError):
    def __init__(self, arm_name: str):
        self.arm_name = arm_name
        super().__init__(f"unknown arm {arm_name!r}; known arms: {sorted(_ARM_NAMES)}")

# The seam's own refusal, same shape:
class UnsatisfiableSelectorError(ValueError):
    def __init__(self, selector: dict, reason: str):
        self.selector = selector
        self.reason = reason
        super().__init__(f"selector {selector!r} is unsatisfiable: {reason}")

class UnconsumableQueryMemberError(ValueError):
    def __init__(self, member_name: str, reason: str):
        self.member_name = member_name
        self.reason = reason
        super().__init__(f"query member {member_name!r} cannot be consumed: {reason}")
```

### Pattern 3: FastAPI as an optional dependency, with a clear import guard

**What:** `databasise/pyproject.toml` today has exactly one `[dependency-groups]` entry (`dev`), explicitly chosen over `[project.optional-dependencies]` because — quoting the pyproject's own comment — "uv installs the `dev` group automatically for `uv run`, whereas an extra requires an explicit `--extra dev`" [VERIFIED: databasise/pyproject.toml:39-41, read this session]. That reasoning is specific to *developer tooling* (pytest, ruff) that must always be present for `uv run pytest` to work on a clean checkout. It does not apply to FastAPI: PEP 735 dependency groups are explicitly **not installable by an end consumer of the published package** — `pip install package[group]` is not a thing; only `[project.optional-dependencies]` extras appear in a wheel's metadata as `Requires-Dist: fastapi; extra == "rest"` and are installable via `pip install databasise[rest]` [CITED: peps.python.org/pep-0735/, confirmed via web search this session]. Using a dependency group for FastAPI would make it **impossible for any external consumer to opt in** to the REST transport at all — it would only ever be installed for this repo's own dev/CI environment. This is not a stylistic choice; it is the mechanism that determines whether `EMBED-02`'s "optional layer" is actually reachable by anyone outside this repo.
**When to use:** Add `[project.optional-dependencies] rest = ["fastapi>=0.135", "uvicorn"]` to `databasise/pyproject.toml`. Keep `dev` as-is.
**Import guard pattern:**
```python
# databasise/seam/rest.py — only imported by a consumer who has installed the `rest` extra.
try:
    from fastapi import FastAPI
except ImportError as exc:
    raise ImportError(
        "databasise.seam.rest requires the optional REST transport dependencies. "
        "Install with: pip install 'databasise[rest]'"
    ) from exc
```
The critical property: `databasise/__init__.py` and `databasise/seam/__init__.py` must **never** import `databasise.seam.rest` at module scope — only a consumer who explicitly does `from databasise.seam.rest import app` (or similar) pays the FastAPI-absent cost, and they pay it as a clear message, not an `ImportError` traceback pointing at an unrelated line.

### Pattern 4: SSE via FastAPI's native `EventSourceResponse` (0.135+), one call path for both transports

**What:** FastAPI shipped built-in SSE support at 0.135 via `fastapi.sse.EventSourceResponse` — no `sse-starlette` dependency needed [CITED: fastapi.tiangolo.com/tutorial/server-sent-events/, fetched this session]. The pattern: an `async def` endpoint returning an `AsyncIterable[Model]`, decorated with `response_class=EventSourceResponse`; FastAPI handles event framing, keep-alive pings, and `Cache-Control`/`X-Accel-Buffering` headers automatically.
**When to use:** For API-04's streaming query response.
**The D-17 "thin adapter" requirement, concretely:** the REST streaming endpoint must not contain any logic beyond (a) deserializing the HTTP request into the same query-object/selector shape the in-process `query()` takes, (b) calling **the same** `Databasise` method the in-process consumer calls (an async-generator variant of `query`, or `query` itself yielding partial envelopes), and (c) wrapping the yielded values in `EventSourceResponse`. Any business logic (selector resolution, redaction, envelope assembly) living in `rest.py` rather than in `databasise/seam/`'s core would violate D-17 and would not be provably "the same call path."
**Example skeleton:**
```python
# databasise/seam/rest.py (sketch — not verified against a running FastAPI instance this session)
from fastapi import FastAPI
from fastapi.sse import EventSourceResponse
from databasise.seam import Databasise

app = FastAPI()
_engine = Databasise(...)  # constructed once, same object the in-process consumer would construct

@app.post("/query")
async def query(body: QueryRequest) -> ResponseEnvelope:
    return await _engine.query(body.query, body.selector)   # identical call to the in-process path

@app.post("/query/stream", response_class=EventSourceResponse)
async def query_stream(body: QueryRequest):
    async for partial_envelope in _engine.query_stream(body.query, body.selector):
        yield partial_envelope   # same underlying async generator an in-process caller could iterate
```
**Testing SSE deterministically:** use FastAPI's `TestClient` (httpx-based) with `.stream()` rather than a bare GET, per the httpx/FastAPI discussion on testing streaming responses [CITED: github.com/encode/httpx/discussions/2629, found via web search this session] — a plain `client.get()` on a streaming endpoint waits for the full body, which defeats the purpose of testing incremental delivery but is *fine* for D-17's equality assertion (which only needs the final assembled content, not incremental timing).

### Pattern 5: What "the same envelope" can and cannot mean for D-17's conformance test

**What:** D-17 requires "a conformance test asserts both transports produce the same envelope for the same query — not merely that both work." A byte-for-byte comparison will fail spuriously: the trace token (D-06, if minted per-call rather than deterministically) and any wall-clock-derived timing will legitimately differ between two independent runs, even against a stub/deterministic client.
**When to use:** Structure the comparison as: (1) run the in-process path once, capture the envelope; (2) run the REST path once against the same query and selector; (3) assert **field-by-field equality on every field except** the trace token and any timing-derived field, and separately assert that the trace token from each **independently resolves** (through `databasise`'s own trace-token-to-record lookup) to a record whose non-timing fields also match. This proves "same call path, same outputs" without requiring the token itself to be identical (it should not be — each call is a distinct run with a distinct trace record).
**Reduce timing/token noise by making the underlying run itself deterministic in tests:** use the stub-client pattern already established in `databasise/tests/parity/test_naive_arm_end_to_end.py` (a synthetic store built through v2 stores' own public write paths, `ChatResult`/`EmbeddingResult` stub client doubles from `databasise/clients/base.py`) [VERIFIED: databasise/tests/parity/test_naive_arm_end_to_end.py:1-33, read this session] rather than a real network-backed LLM call, so the only sources of run-to-run variance are the trace token and wall-clock timing — exactly the two things the comparison should exclude.

### Anti-Patterns to Avoid

- **Re-deriving redaction logic in `rest.py`:** if the REST layer has its own copy of "strip these fields," a future change to the redaction rule (or a newly-discovered leak) has to be fixed in two places, and D-17's "thin adapter" property is falsified by construction. Redaction happens once, in the library seam.
- **Trusting `ParsedWiring` for `provides`/`harnesses`:** as established above, `ParsedWiring` does not carry these fields at all — reading `parsed.provides` will `AttributeError`, and adding it to `ParsedWiring` is unnecessary extra surface when the raw wiring dict (already in hand at the point `parse_wiring` is called) has it directly, exactly as `run_arm.py` already reads it.
- **Summing `TokenAccounting` across nodes with different `counted_by` values into one scalar:** §4 explicitly forbids treating differently-counted token numbers as comparable ("Cross-part comparison of token counts MUST use a central recount under one `counted_by`"); silently summing them into the envelope's per-query total commits exactly the error this clause forbids, one level down (aggregation instead of comparison, but the same category of conflation).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE event framing (`data: ...\n\n`, keep-alive pings, buffering headers) | A manual `AsyncGenerator[str]` yielding hand-formatted SSE text over `StreamingResponse` | FastAPI's native `EventSourceResponse` (0.135+) | Ships in the framework already in the dependency set (once the `rest` extra is added); keep-alive and header correctness are exactly the kind of detail a hand-rolled framer gets subtly wrong under proxy/load-balancer conditions |
| RFC 8785 canonical hashing for the opaque trace token, if the token needs to be derived rather than random | A bespoke hash-and-encode scheme | `databasise.identity.canon.canonicalise` (already used by `instance_hash`/`config_hash`) | Already exists, already tested, already the project's one canonicalisation path — CONTEXT.md's own "Reusable Assets" list names `identity/` `canonicalise` as available for exactly this purpose |
| A closed/frozen JSON schema for the envelope | Hand-written `__slots__` + manual `to_dict()`/validation (the style `RunRecord`/`NodeTrace` currently use) | Pydantic v2 `BaseModel` with `frozen=True, extra="forbid"` | D-04 already settles this; Pydantic gives JSON Schema generation for free too, useful for the REST layer's OpenAPI docs |
| An append-only "has this alias been superseded" query | Hand-rolled SQL against `ledger.db` from the seam module | `databasise.ledger.ledger.Ledger.active_pointer(mutation_id)` (already computes `ORDER BY id DESC LIMIT 1`) | Already exists and already encodes the "ledger append **is** the promotion decision" rule (§6) — re-deriving it risks getting the ordering/projection semantics subtly wrong a second time |

**Key insight:** almost nothing about *executing* a query and *tracing* it needs to be built new — `run_wiring`, `RunRecord`, `resolve_arm`, and the ledger already do that work. What is genuinely new in this phase is entirely on the **boundary**: redaction, evidence-ref minting, trace-token/persistence, and the two transports. Time spent re-implementing execution-side machinery the codebase already has is time not spent on the boundary work that is actually this phase's job.

## Common Pitfalls

### Pitfall 1: `ParsedWiring` silently drops `provides`, `harnesses`, and `recipe`

**What goes wrong:** A planner or executor who assumes the validator's `ParsedWiring` dataclass is "the parsed wiring" and reaches for `parsed.provides` or `parsed.harnesses` will hit an `AttributeError` — those fields do not exist on `ParsedWiring` at all.
**Why it happens:** `databasise/validator/parse.py:parse_wiring` reads only `doc.get("nodes", {})` from the input dict [VERIFIED: databasise/validator/parse.py:143, read this session: `raw_nodes: dict[str, Any] = doc.get("nodes", {})`] and `ParsedWiring`'s own dataclass fields are exactly `nodes`, `parts`, `deps`, `node_order`, `report` [VERIFIED: databasise/validator/parse.py:106-110, read this session]. Meanwhile the raw wiring JSON genuinely carries `recipe`, `harnesses`, and `provides` as sibling top-level keys to `nodes` [VERIFIED: `databasise/wirings/lightrag/base.json`, read via inline script this session — `json.load(...)` on that file returns `dict_keys(['wiring_id', 'title', 'wiring_version', 'nodes', 'recipe', 'harnesses', 'provides'])`, with `"recipe": {"embedding": "embedder-index"}`, `"harnesses": []`, `"provides": ["generate"]`].
**How to avoid:** Read `provides`/`harnesses`/`recipe` off the **raw wiring dict**, before or alongside the `parse_wiring` call — exactly the pattern `databasise/parity/run_arm.py:328` already uses: `provides = resolved.get("provides") or []`. Do not add these fields to `ParsedWiring` unless a later need actually requires the validator itself to reason about them structurally (nothing in this phase's scope does).
**Warning signs:** Any code writing `parsed.provides`, `parsed.harnesses`, or expecting `parse_wiring` to validate that `provides` names real nodes (it currently does not check this at all).

### Pitfall 2: The harness selector has no live test subject

**What goes wrong:** D-11 requires "a harness by name" as one of exactly four selectors, and the phase's own falsifier language calls out the five LightRAG arms as "real subjects" for testing the seam — but the LightRAG base wiring's own `harnesses` array is empty (`"harnesses": []`) [VERIFIED: `databasise/wirings/lightrag/base.json`, read this session]. Nothing in the registered parts declares or implements a harness. There is currently no way to write a real, non-vacuous test of the harness selector against real data, the same house-style bar (CONTEXT.md's "Established Patterns" — "Tests assert against real data, never shape alone") every other conformance test in this codebase already meets.
**Why it happens:** Harnesses (CRAG-style retry wrappers, per §1's own worked example `"core/harness-crag@1.0.0"`) are a real but unbuilt concept — nothing in Phase 3's LightRAG port needed one.
**How to avoid:** Flag this to the planner explicitly as a scope decision: either (a) the harness selector is implemented and unit-tested against a synthetic/fixture wiring document that declares a `harnesses` entry (never against a resolved LightRAG arm, since none has one), accepting that the falsifier's "real subjects" language is satisfied only for the other three selectors, or (b) a minimal no-op harness stub is added as test fixture data. Either way, this needs to be a named decision in the plan, not discovered mid-execution.
**Warning signs:** A plan task that says "test the harness selector against the naive/bypass/hybrid/local/global arms" without first checking whether any of them declares a harness (none do).

### Pitfall 3: The ledger has no `alias` field — D-12 names an intent, not an existing column

**What goes wrong:** D-12 states "Aliases are read from the existing ledger... which already carries the record shape." `databasise/ledger/ledger.py`'s `LedgerRecord` dataclass fields are: `mutation_id, mutation_class, parent, arm_instance_hashes, effect_size, verdict, evidence_pointer, proposer_id, depth_label, tier_of_decision, decomposition_ratio, opaque_ttl_renewals, parity_records, promotion_provenance, promotion_trace_ids` [VERIFIED: databasise/ledger/ledger.py:46-64, read this session — the full `@dataclass(frozen=True) class LedgerRecord` field list]. **No field named `alias` exists.** A grep for `alias` across the entire `databasise/` package (excluding tests and `.venv`) finds zero hits outside AST-import-checking test helpers that use "alias" in the Python-import sense (`ast.alias`), completely unrelated to CONTRACT's promotion alias [VERIFIED: `grep -rn "alias" --include=*.py .` run this session across the whole package, non-test hits are only `ledger/ledger.py`'s own docstring mentioning "the atomic alias repoint" as unimplemented future work, and AST-related test/tool code].
**Why it happens:** The ledger table Phase 1 built stands the append-only table and the `active_pointer(mutation_id)` projection up, but explicitly scope-fences "the operator path, `change_origin`, the tombstone-lifting prohibition, or the atomic alias repoint" as MACH-07/Phase 7 deliverables [VERIFIED: databasise/ledger/ledger.py:17-21, read this session]. The alias mechanism (§6's "atomic alias repoint") genuinely does not exist yet — D-12's "read" framing assumes a write path (Phase 7) has already populated something the read can consume, but that write path has not landed.
**How to avoid:** The planner must decide concretely what "a stable alias" resolves against for THIS phase, given the alias-repoint mechanism does not exist. The two honest options: (a) treat `mutation_id` itself as playing the alias role for now (a `Ledger.active_pointer(mutation_id)` lookup returning the current `LedgerRecord`, then extracting `arm_instance_hashes` or similar to identify which wiring/arm is "active" for that id) — this works today with zero ledger schema changes, but should be named explicitly as a stand-in, not silently assumed equivalent to the future real alias; or (b) treat this as a real gap and scope a minimal ledger schema addition into this phase (a small, additive column) before D-12 can be implemented as literally written. Either is legitimate; silence on the choice is not.
**Warning signs:** A plan task that says "resolve the alias selector by reading the ledger" without naming which existing `LedgerRecord` field plays that role.

### Pitfall 4: No `ScoredItem`/`ChunkRef`/`Ref` type exists anywhere in the codebase — API-05's evidence references must be built from scratch

**What goes wrong:** §4 and §18.2 both assume a `ScoredItem{ref, kind, score, provenance, payload, metadata}` shape with machine-minted, deref-raising `Ref`s (e.g., `ChunkRef(corpus_id, recipe@version, ordinal, content_hash)`) already exists to redact `provenance` from and to expose as the envelope's "evidence references" field. **Nothing in `databasise/` implements any of these types.** A grep for `ScoredItem`, `class Ref`, or `EmbeddingSpace` across every `.py` file in the package returns zero results [VERIFIED: `grep -rln "ScoredItem\|class Ref\b\|EmbeddingSpace" --include=*.py .` run this session, empty output]. What the actual retrieval nodes emit instead is a plain dict with a raw store-internal `id`: `databasise/parts_core/lightrag/chunk_vector.py:35` returns `{"items": items}` where each item is `{"id": doc_id, "score": ..., **entry["metadata"]}`, and `id` traces back to `databasise/stores/vector.py:235`'s `results.append({"id": doc_id, "score": float(score), **entry["metadata"]})` — `doc_id` is whatever key the vector store's own `upsert` was called with, **not** a content-hash-based `ChunkRef` [VERIFIED: databasise/parts_core/lightrag/chunk_vector.py:24-35 and databasise/stores/vector.py:217-237, both read this session].
**Why it happens:** §4's evidence-record machinery was never a Phase 1–3 deliverable — Phase 3 ported LightRAG's *retrieval* nodes, not its *evidence-typing* layer, and nothing forced the gap to surface until this phase actually needs to hand a consumer something resolvable.
**How to avoid:** Budget real implementation time for a minimal evidence-ref layer in this phase, not a research task — this is new code, not a wrapper over existing code. The minimum viable version: a small function that, given a raw item dict (`{id, score, ...}`) and the resolved wiring's namespace/corpus context, constructs a `Ref`-shaped object (even a simple dataclass, not necessarily the full `ChunkRef(corpus_id, recipe@version, ordinal, content_hash)` tuple if that information genuinely is not available at this point in the pipeline yet) that the envelope can carry and that a follow-up dereference call could resolve back to the same item. Document explicitly which of §4's four `ChunkRef` members are and are not populated for a v1 seam, since the raw `doc_id` alone does not obviously decompose into `(corpus_id, recipe@version, ordinal, content_hash)` without additional plumbing this phase may not have time for — flag any shortfall as a declared, named limitation rather than silently shipping a ref that only looks like the contract's `ChunkRef`.
**Warning signs:** A plan task that says "wrap existing evidence items into the envelope" as if the items already have the right shape — they do not.

### Pitfall 5: Token accounting has no single per-query aggregate — nodes disagree on `counted_by`

**What goes wrong:** API-11 requires "`counted_by` on every token number," and the envelope needs *some* per-query total. But per-node `TokenAccounting.counted_by` values legitimately differ within one run today: a real LLM call sets `counted_by=resolved_model_identity` or a provider-reported tokenizer id [VERIFIED: databasise/clients/openai_compat.py:115,126, read this session — `return TokenAccounting(counted_by=resolved_model_identity)` and `counted_by=tokenizer_id or resolved_model_identity`], a pinned-replay node sets `counted_by="pinned-replay"` [VERIFIED: databasise/parts_core/lightrag/keywords.py:119, read this session — `"tokens": TokenAccounting(counted_by="pinned-replay")`], and a node with no LLM call at all defaults to `counted_by="none"` [VERIFIED: databasise/runner/trace.py:53, read this session — `counted_by: str = "none"  # real value: no tokenizer counted anything`]. Naively summing `prompt_tokens + completion_tokens` across every node into one envelope-level number, tagged with a single `counted_by`, misattributes tokens counted by one tokenizer to a `counted_by` value that did not count them — exactly the conflation §4 names explicitly for cross-arm comparison ("Cross-part comparison of token counts MUST use a central recount under one `counted_by` — comparing two parts' self-reported token counts, each counted by its own tokenizer, is not a comparison").
**Why it happens:** Per-node `TokenAccounting` was built (Phase 1, D-10) for the run-record's own honesty/completeness purposes, not for a single-number consumer-facing rollup — nothing required them to agree.
**How to avoid:** Design the envelope's token-accounting field as a **breakdown** (a list of `{counted_by, prompt_tokens, completion_tokens, ...}` entries, one per distinct `counted_by` value actually observed in the run), not a single scalar with one `counted_by` string. This satisfies "`counted_by` on every token number" literally (every number in the breakdown carries its own `counted_by`) without inventing a false single aggregate.
**Warning signs:** An envelope field typed as a single integer total with one `counted_by` string attached.

### Pitfall 6: MACH-11's `mutates_store`-outside-`deps` event has no source signal in the current scheduler

**What goes wrong:** MACH-11/D-09 requires the envelope to surface a seam-level event (`name@version`, spend, outcome) whenever a `mutates_store` call happens **outside** a wiring's declared `deps` graph. `databasise/runner/scheduler.py` today only knows a node's declared `effects` (used for containment/blast-radius/metering — the `_STORE_MUTATING_EFFECTS` frozenset already exists and includes `mutates_store` [VERIFIED: databasise/runner/scheduler.py:156-165, read this session]) — it has no concept of "outside `deps`" at all, because every dispatched node **is** a member of the wiring's `deps` graph by construction (the scheduler only ever dispatches nodes `graphlib.TopologicalSorter` produces from `parsed.deps`). There is currently no code path that could even produce the event this requirement asks the envelope to surface, because the triggering condition (a `mutates_store` effect firing from *outside* the graph the scheduler is walking) is not a scheduler-observable event in the current architecture — it would have to originate from inside a node's own body (a node with `mutates_store` declared, calling something that mutates a store *other than* through a declared dependency edge), which the scheduler cannot currently distinguish from an ordinary declared-and-in-graph mutation.
**Why it happens:** Phase 1–3 never needed to model "a mutation that escapes the dataflow" because no part built so far does one — `mutates_store` exists as a declared effect (`_STORE_MUTATING_EFFECTS`) but nothing in the registered `parts_core`/`LIGHTRAG_PARTS` set actually exercises the "outside `deps`" case.
**How to avoid:** Treat this as new instrumentation, not a wrapper: the seam (or a small scheduler-level hook, if the planner decides the signal must originate closer to dispatch) needs a way to detect and tag a `mutates_store` node whose declared `deps` do not include whatever it mutated. Given no current part exercises this case, the planner should also decide whether this phase can only build the *plumbing* (the envelope field, the event shape, a hook point) with no real triggering example to test against yet, versus needing a synthetic test fixture part that deliberately does an out-of-`deps` mutation to prove the event actually surfaces. The latter is closer to CONTEXT.md's "tests assert against real data, never shape alone" house style and is the recommended approach.
**Warning signs:** A plan task that treats MACH-11 as "just add a field to the envelope" without also adding the detection logic and a fixture part that can trigger it.

### Pitfall 7: Pydantic v2's `extra="forbid"` is not inherited by nested models

**What goes wrong:** D-05's structural half of the closed-envelope guarantee is easy to get wrong: setting `model_config = ConfigDict(extra="forbid", frozen=True)` on the top-level `ResponseEnvelope` class does **not** automatically apply `extra="forbid"` to any nested `BaseModel` fields (evidence-ref entries, the token-accounting breakdown entries, etc.) — each nested model class must set its own `model_config` independently, or inherit from a shared strict base class.
**Why it happens:** Pydantic v2's per-model configuration is exactly that — per-model — and does not cascade through nested model fields by default [CITED: pydantic/pydantic GitHub Discussion #2652 "Recursively set Config setting extra to forbid or ignore", confirmed via web search this session].
**How to avoid:** Define one shared strict base (`class _StrictModel(BaseModel): model_config = ConfigDict(frozen=True, extra="forbid")`) and have every model in `databasise/seam/envelope.py` — top-level and nested alike — inherit from it. Verify with a test that constructs the full nested envelope and confirms an extra key at **every** nesting depth (not just the top level) is rejected, mirroring D-05's own emphasis that "the structural guard alone would miss an internal id smuggled inside a nested value."
**Warning signs:** Only the top-level `ResponseEnvelope` class sets `model_config`; nested classes (an evidence-ref model, a token-breakdown-entry model) use bare `BaseModel` with no explicit config.

### Pitfall 8: A naive substring-based leak test will produce false positives on common-word node ids and false negatives on data it should catch

**What goes wrong:** D-05's own recommended technique — "serializes a real envelope from a real run and fails if any wiring name, node id, or instance hash appears anywhere in the output" — is right in spirit but the naive implementation (collect the run's node ids/wiring id/instance hashes into a set, serialize the envelope to JSON text, assert none of those strings appear as a substring) has two real failure modes worth planning around:
1. **False positive on generic node ids.** The LightRAG base wiring's own node ids include ordinary English words used as node names — e.g. `keywords` [VERIFIED: databasise/wirings/lightrag/base.json, read this session — node id `"keywords"`]. If a real query's answer text or evidence content legitimately contains the word "keywords" (plausible for almost any corpus), a blind substring check flags a false leak, and a team that has seen this test cry wolf once will be tempted to weaken it — precisely the failure mode CONTEXT.md warns against ("Phase 3's code review rejected a shape-only assertion twice").
2. **False positive on the wiring name itself.** `wiring_id` for the LightRAG base is the literal string `"lightrag-base"` [VERIFIED: databasise/wirings/lightrag/base.json:2, read this session], and `wiring_id` is also user-supplied when present (`wiring_doc.get("wiring_id")`) rather than hash-derived [VERIFIED: databasise/__init__.py:93-95 and databasise/parity/run_arm.py:308-310, both read this session — `wiring_id = wiring_doc.get("wiring_id") or f"wiring:{hash[:16]}"`]. A query that legitimately asks about "LightRAG" (plausible, since the corpus this phase's own test fixtures could plausibly discuss the project's own tech stack) would make the answer text contain the literal substring "lightrag," again a false positive on a generic-sounding domain word, not a real identity leak.
**Why it happens:** Node ids and wiring ids in this codebase are short, human-readable, English-word-like strings (`keywords`, `entity-lookup`, `lightrag-base`) — nothing like the astronomically improbable-to-collide SHA-256 hex strings that make `instance_hash`/`wiring_instance_hash` safe to substring-match unconditionally [VERIFIED: databasise/identity/instance.py:25-30, read this session — `instance_hash` is `hashlib.sha256(...).hexdigest()`, a 64-hex-char string].
**How to avoid:** Split the leak test into two checks with different rigor: (a) for high-entropy identity values (`instance_hash`, `wiring_instance_hash`, `config_hash` — all SHA-256 hex per `identity/instance.py`/`identity/canon.py`), a blind substring search across the full serialized JSON is safe and sufficient — collision with real content is not a practical concern; (b) for low-entropy, human-readable identity values (`node_id`s, `wiring_id`, `arm_id`), do a **structural** check instead of a substring search — walk the parsed JSON/dict tree and assert that no dict *key* equals a forbidden node id (the real leak vector — a redaction bug is far more likely to leave a `{"keywords": {...}}` key somewhere than to leak the word "keywords" into free-text content) and, separately, use a test corpus/fixture chosen so its evidence/answer text is provably free of the literal node-id/wiring-id strings (e.g., a synthetic corpus about an unrelated topic), documenting that choice explicitly so a future reader understands why the corpus was picked the way it was.
**Warning signs:** A leak test that does one blind `assert forbidden_string not in json.dumps(envelope)` for every forbidden value regardless of entropy, run against a real corpus that could plausibly contain the literal word "keywords" or "lightrag" in its answer text.

## Code Examples

### The ground-truth forbidden-value set for one run (input to the leak test)

```python
# Building the ground-truth set the leak test checks against — everything a real RunRecord for
# one run actually carries that §18.2 forbids exposing. Every value here traces to a field
# verified present on RunRecord/NodeTrace this session (databasise/runner/trace.py:101-171).
def forbidden_identities(run_record_dict: dict) -> tuple[set[str], set[str]]:
    """Returns (high_entropy_values, low_entropy_values) — see Pitfall 8 for why they need
    different check strategies."""
    high_entropy = {run_record_dict["wiring_instance_hash"]}
    low_entropy = {run_record_dict["wiring_id"], run_record_dict["arm_id"]}
    for node in run_record_dict["nodes"]:
        high_entropy.add(node["instance_hash"])
        low_entropy.add(node["node_id"])
    return high_entropy, low_entropy
```

### Structural key-leak check (the low-entropy half of Pitfall 8's fix)

```python
def assert_no_forbidden_keys(obj, forbidden_keys: set[str], path: str = "$") -> None:
    """Walks a parsed (not yet re-serialized) envelope structure and fails if any dict key at
    any nesting depth equals a forbidden node id / wiring id / arm id — the redaction-bug leak
    vector a blind substring search over free text cannot distinguish from ordinary content."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            assert key not in forbidden_keys, f"forbidden key {key!r} found at {path}.{key}"
            assert_no_forbidden_keys(value, forbidden_keys, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            assert_no_forbidden_keys(item, forbidden_keys, f"{path}[{i}]")
```

### A shared strict Pydantic v2 base every envelope model must use (Pitfall 7's fix)

```python
# Source: pydantic v2.13.5 (installed version, verified this session) ConfigDict semantics,
# per pydantic/pydantic GitHub Discussion #2652 (nested extra="forbid" is not inherited).
from pydantic import BaseModel, ConfigDict

class _StrictModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

class TokenBreakdownEntry(_StrictModel):
    counted_by: str
    prompt_tokens: int
    completion_tokens: int

class EvidenceRef(_StrictModel):
    ref: str          # machine-resolvable, deref-raising — see Pitfall 4
    kind: str
    score: float | None = None

class ResponseEnvelope(_StrictModel):
    evidence: list[EvidenceRef]
    trace_token: str
    depth_label: str
    partial: bool
    degraded: bool
    token_accounting: list[TokenBreakdownEntry]
    # ... remaining §18.2 fields
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `sse-starlette`'s `EventSourceResponse` bolted onto a `StreamingResponse` | FastAPI's own native `fastapi.sse.EventSourceResponse` | FastAPI 0.135 (2026, per GitHub PR #15030) | One fewer dependency to add for D-16; automatic keep-alive/header handling that a hand-rolled or third-party version would need to be configured for explicitly |

**Deprecated/outdated:** none directly relevant — this phase is new-build against a stable contract, not a migration.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | "A declared capability or capability set" (§18.4) resolves against the `Effect` vocabulary (`parts/schema.py`'s 17-member `Literal`) and/or the §14.2 store sub-capability tables, since no other "capability" vocabulary exists in code today | Architectural Responsibility Map, Standard Stack | If the intended capability vocabulary is meant to be something coarser (e.g., a named recipe-level tag like "hybrid retrieval") that does not exist in code either, the capability selector's matching logic needs a different, still-to-be-invented source of truth — this should be confirmed with the user/CONTEXT before implementation, not assumed |
| A2 | `mutation_id` in the existing `LedgerRecord` is an acceptable stand-in for "a stable alias" per D-12, absent any better-fitting existing field | Pitfall 3 | If the planner instead expects a real alias-repoint mechanism (Phase 7's actual deliverable) to already exist for this phase to read, D-12 cannot be implemented at all without first landing a piece of Phase 7's own scope early — this is exactly the kind of scope leak the phase boundary in CONTEXT.md's `<domain>` section explicitly tries to avoid ("does not touch...") |
| A3 | The envelope's per-query "depth label" (§18.2) should be computed from the `effective_depth` of the wiring's `provides`-named terminal node(s), not from some other aggregation over all nodes | Common Pitfalls / envelope field mapping | If the intended semantics is instead "the shallowest (or deepest) depth across every node in the run," the computed label would be wrong in wirings where the terminal node's depth differs from an intermediate node's — worth a quick confirmation before locking the assembly function |
| A4 | `resolved_model_identity` (returned by every LLM/embedding client call, e.g. `databasise/parts_core/lightrag/generate.py:39`) is not itself forbidden by §18.2's closed-set rule, since it names a model, not a wiring/node/instance identity | Common Pitfalls, Code Examples | If a stricter reading treats "which model answered" as equivalent to "which modality answered" for invariance purposes (§18.3), exposing it in the envelope could be judged a contract violation — recommend treating this as an explicit open question for the planner/user rather than silently including or excluding it |

**If this table is empty:** N/A — see rows above.

## Open Questions

1. **What does "a declared capability or capability set" concretely match against?**
   - What we know: §14.1 calls the 17-member `effects[]` vocabulary "the base capability vocabulary"; §14.2 adds store-level sub-capabilities (`score_all`, `bulk-export`, namespaces, etc.); neither is obviously what a consumer would name when asking for, e.g., "graph retrieval."
   - What's unclear: whether the intended selector granularity is effect-level (a consumer names `reads_graph`) or something coarser that would need a new, currently-nonexistent vocabulary layer.
   - Recommendation: confirm with the user before locking `selectors.py`'s capability-matching logic; the five real LightRAG arms (naive/bypass/hybrid/local/global) differ from each other exactly in which effects their nodes declare, so an effects-set match is at minimum sufficient to distinguish them, which may be enough to satisfy the phase's own falsifier even if it is not the most ergonomic long-term design.

2. **What backs the opaque trace token, concretely — and does this phase need to build run-record persistence from scratch?**
   - What we know: `databasise/__init__.py:run_wiring` and `databasise/parity/run_arm.py:run_arm` both construct a `RunRecord` and return it as an in-memory dict; neither persists it anywhere. `databasise/ledger/ledger.py`'s `Ledger` is a different, promotion-specific SQLite table (`ledger.db`) that explicitly does not receive a row per ordinary run ("Running an arm MUST NOT append to the ledger").
   - What's unclear: whether API-10's trace reference should be backed by a new, dedicated trace-record store (a new SQLite table beside `ledger.db`, an in-memory LRU keyed by token for a first pass, or something else), and whether that store's lifetime/durability requirements are in scope for this phase or can be minimal (e.g., in-process-only, lost on restart) for a first cut.
   - Recommendation: treat this as new infrastructure to scope explicitly in the plan (see Architectural Responsibility Map's "Persisted trace record" row) rather than something to "wire up" from existing pieces — nothing existing plays this role today.

3. **Is a synthetic no-op harness needed as test fixture data, given the real LightRAG wiring declares none?**
   - What we know: `harnesses: []` on the only real wiring document in the repo.
   - What's unclear: whether the plan should invest in a minimal fixture harness purely to give the harness selector something real to select and a test something real to assert against.
   - Recommendation: yes — add a small fixture wiring document (not a real LightRAG arm) declaring one trivial `harnesses` entry, used only by the selector's own unit test, and note in the test's docstring that no real LightRAG arm exercises this path yet.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Everything in `databasise/` | ✓ | requires-python `>=3.11` per `databasise/pyproject.toml:10` | — |
| pydantic | Envelope model (D-04) | ✓ | 2.13.5 installed in `databasise/.venv` [VERIFIED this session] | — |
| fastapi | Optional REST transport (D-15) | ✗ | not installed [VERIFIED this session — `ModuleNotFoundError`] | Expected — this is exactly what D-15's "optional dependency group" premise requires; install via the new `rest` extra when building/testing the REST layer |
| uvicorn | Running the optional REST app | ✗ (not checked directly, but absent alongside fastapi) | — | Same as above — part of the same `rest` extra |
| A network-reachable LLM/embedding endpoint | End-to-end query execution against real content | Not verified this session (requires `v1/.env.parity`, a repo-external config file) | — | Use the stub-client double pattern (`databasise/tests/parity/test_naive_arm_end_to_end.py`'s approach) for this phase's own tests — no network dependency needed for conformance/leak tests, only for a genuinely real end-to-end smoke test |

**Missing dependencies with no fallback:** none — both missing dependencies (fastapi, uvicorn) are the exact things this phase's own scope (D-15) is responsible for adding.

**Missing dependencies with fallback:** the network-reachable LLM endpoint has a documented fallback (stub clients) already established in this codebase's own test suite.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2+, pytest-asyncio 1.2+ (both already project dev dependencies) [VERIFIED: databasise/pyproject.toml:45-46] |
| Config file | `databasise/pyproject.toml` — `[tool.pytest.ini_options]`: `asyncio_mode = "auto"`, `testpaths = ["tests"]` [VERIFIED: databasise/pyproject.toml:52-54, read this session] |
| Quick run command | `cd databasise && uv run pytest tests/seam -q` (once the new test directory exists) |
| Full suite command | `cd databasise && uv run pytest -q` (already the project's configured `test_command` per `.planning/config.json`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| API-03 | Unsatisfiable selector raises named refusal; unconsumable query member refused by name; opaque excluded from default | unit | `pytest tests/seam/test_selectors.py -x` | ❌ Wave 0 |
| API-03 | §18.2 envelope is a closed set (structural) | unit | `pytest tests/seam/test_envelope_schema.py -x` | ❌ Wave 0 |
| API-05 | Evidence references are machine-resolvable, not inline copies | unit | `pytest tests/seam/test_evidence_refs.py -x` | ❌ Wave 0 |
| D-05 | Leak test: no wiring/node/instance identity anywhere in a real envelope | integration (real run, stub clients) | `pytest tests/seam/test_leak.py -x` | ❌ Wave 0 |
| API-04 / D-16 | SSE stream produces the same content as the non-streaming path | integration | `pytest tests/seam/test_sse.py -x` | ❌ Wave 0 |
| D-17 | REST and in-process transports produce equal envelopes (excluding trace token/timing) for the same query | integration | `pytest tests/seam/test_dual_transport.py -x` | ❌ Wave 0 |
| MACH-11 | `mutates_store`-outside-`deps` surfaces as a seam-level event | integration (needs a fixture part — see Pitfall 6) | `pytest tests/seam/test_mach11_event.py -x` | ❌ Wave 0 |
| API-10 | Trace token resolves back to the run's trace record; internal ids never appear in the envelope even via the token's own literal value | unit | `pytest tests/seam/test_trace_token.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd databasise && uv run pytest tests/seam -q`
- **Per wave merge:** `cd databasise && uv run pytest -q` (full suite, matching `.planning/config.json`'s configured `test_command`)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/seam/` directory and `__init__.py` — does not exist yet
- [ ] A fixture wiring document declaring a non-empty `harnesses` array (Pitfall 2 / Open Question 3) — needed before the harness selector can be tested against real data
- [ ] A fixture part that performs a `mutates_store` write outside its own `deps` (Pitfall 6) — needed before MACH-11's event can be tested against real data rather than asserted by inspection alone
- [ ] Framework install: none needed for the library-seam tests (pytest/pytest-asyncio already present); `uv sync --extra rest` needed once REST-layer tests are added

*(Every item above genuinely does not exist yet — this phase is new-build, not an extension of existing test infrastructure.)*

## Sources

### Primary (HIGH confidence — read directly this session)
- `docs/system-model/CONTRACT.md` §4, §5, §6, §7, §8, §9, §10, §11, §14.1, §14.2, §14.3, §18 (all four subsections), §19.8 — the frozen contract text this phase implements
- `.planning/phases/04-the-seam/04-CONTEXT.md` — settled decisions D-01 through D-17
- `.planning/REQUIREMENTS.md` — API-03, API-04, API-05, API-10, API-11, EMBED-02, MACH-11 definitions
- `databasise/__init__.py`, `databasise/runner/scheduler.py`, `databasise/runner/trace.py`, `databasise/wirings/resolve.py`, `databasise/ledger/ledger.py`, `databasise/identity/instance.py`, `databasise/identity/canon.py`, `databasise/parts/registry.py`, `databasise/parts/schema.py`, `databasise/validator/parse.py`, `databasise/parity/run_arm.py`, `databasise/parts_core/lightrag/generate.py`, `databasise/parts_core/lightrag/chunk_vector.py`, `databasise/stores/vector.py`, `databasise/clients/base.py`, `databasise/clients/openai_compat.py`, `databasise/parts_core/lightrag/keywords.py`, `databasise/wirings/lightrag/base.json`, `databasise/wirings/lightrag/arm-naive.json-patch.json`, `databasise/pyproject.toml`, `databasise/tests/parity/test_arm_conformance.py`, `databasise/tests/parity/test_naive_arm_end_to_end.py` — all read this session
- `databasise/.venv` — pydantic version confirmed installed (2.13.5); fastapi confirmed absent
- `gsd-tools query package-legitimacy check` — fastapi/uvicorn/httpx PyPI verdicts, run this session

### Secondary (MEDIUM confidence — official docs, web-fetched or web-searched this session)
- fastapi.tiangolo.com/tutorial/server-sent-events/ — native `EventSourceResponse`, fetched this session
- github.com/fastapi/fastapi/pull/15030 — "Add support for Server Sent Events," found via web search this session
- pypi.org/pypi/fastapi/json — current release 0.141.1, fetched this session
- peps.python.org/pep-0735/ — dependency groups vs. optional-dependencies distinction, found via web search
- github.com/pydantic/pydantic Discussion #2652 — nested `extra="forbid"` not inherited, found via web search
- github.com/encode/httpx Discussion #2629 — testing `StreamingResponse` with `TestClient`, found via web search

### Tertiary (LOW confidence)
- none used as load-bearing claims in this document

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH for pydantic (installed, verified); MEDIUM for FastAPI/SSE specifics (docs + PR cross-checked, but the native `EventSourceResponse` feature is recent enough that a hands-on smoke test before committing to it in the plan is warranted)
- Architecture: HIGH for the redaction/execution-reuse pattern (directly grounded in `run_arm.py`, read in full); MEDIUM-LOW for the capability-selector and harness-selector semantics (genuinely underspecified in code — see Open Questions)
- Pitfalls: HIGH — every pitfall in this document is grounded in a specific file/line read this session, not inferred

**Research date:** 2026-09-06
**Valid until:** 30 days for the codebase-grounded findings (stable unless Phase 3/5 land conflicting changes to `run_wiring`/`ParsedWiring`/`ledger.py` first); 14 days for the FastAPI version-specific claims (a fast-moving dependency: re-verify the installed/target FastAPI version against `fastapi.tiangolo.com/release-notes/` before implementation if this research is more than two weeks old)
