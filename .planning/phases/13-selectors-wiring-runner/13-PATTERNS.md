# Phase 13: Selectors, Wiring & Runner - Pattern Map

**Mapped:** 2026-10-19
**Files analyzed:** 40 new/modified (production 30, tests 10 groups)
**Analogs found:** all in-repo (every phase change tightens or extends an existing mechanism). Paths are relative to `databasise/`. All analog paths were confirmed git-tracked (`git ls-files`) for the files excerpted; none is a gitignored mirror.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `seam/refusals.py` (new refusals: ambiguous answer, invalid node setting, invalid guard declaration; `trace_token` attr; docstring) | model (refusal) | request-response | `UnbudgetableParticipantError` (:728-745), `ForeignEngineRefusalError` (:767-827), `UnparseableWiringError` (:874-885) | exact |
| `seam/engine.py` (`_refuse_unparseable` cycles, preflight translation, persist-before-raise, `_select_answer`, health, compare) | service | request-response | `_refuse_unparseable` (:608-612), `health()` (:1880-1950) | exact (self) |
| `runner/trace.py` (reason-code constants, `NodeTrace` fields) | model | transform | same file lines 38-42 constants, 83-116 `NodeTrace` | exact (self) |
| `runner/guards.py` (`signal`, `evaluate_guards`) | utility | transform | same file; `declare_guard` (:57-70) | exact (self) |
| `runner/scheduler.py` (strict ints, `_validated_guards`, sequential dispatch, per-node traces) | service | event-driven | `_validated_max_concurrency` (:362-371), `_validated_token_allowance` (:381-390), `_validated_guards` (:393-402) | exact (self) |
| `identity/env.py` (payload) | utility | transform | same file `_collect_environment_payload` (:60-77) | exact (self) |
| `validator/parse.py` + `validator/errors.py` (robustness, ghost refs, kind, RFC 6901) | utility | transform | `parse_wiring` (:145-272); constants `validator/errors.py:23-36` | exact (self) |
| `parts/schema.py` (`Part.reads_namespaces`) | model | CRUD | `Part` dataclass (:115-141) trailing defaulted fields | exact |
| `seam/selectors.py` (namespace-token matcher) | service | request-response | `_wiring_effects` / `_match_capability` (selectors.py:147-165) | exact (self) |
| `parts/registry.py` (effect validation in `register`) | service | request-response | existing opaque-admission check in `register` | role-match |
| `seam/redact.py` (response-time reason gate) | utility | transform | same file docstring/gate (:15-30, :66) | exact (self) |
| `tests/seam/test_*.py` new WIRE tests | test | request-response | `tests/seam/test_hipporag_review_fixes.py` | exact |
| `tests/seam/test_rest_transport.py::_REFUSAL_FACTORIES` | test | request-response | same dict (:415-470) | exact (self) |
| `evidence/rig-trace.databasise.schema.json`, `evidence/RIG-TRACE-DEVIATIONS.md` | config / doc | transform | `docs/system-model/rig-trace.schema.json`; RIG.md §R table (:654-668) | role-match |

## Pattern Assignments

### `seam/refusals.py` new refusals (model, request-response)

**Analog:** `UnbudgetableParticipantError` (private node id) and `UnparseableWiringError` (codes only).

**Private-attribute precedent** (refusals.py:743-745):
```python
    def __init__(self, node_id: str):
        self._internal_node_id = node_id  # never exposed via the message or vars()
        super().__init__("a participant is admitted unbudgetable; no token comparison may include it")
```
Use for `InvalidNodeSettingError(setting=...)` and `InvalidGuardDeclarationError`: public attr = closed setting name only (`self.setting = setting`), node id on `self._node_id`, message names neither node id nor value.

**Export mechanism** (refusals.py:54-60) - this is how `trace_token` reaches REST and MCP with no extra code; set `exc.trace_token = token` as a public attribute after construction:
```python
    body: dict[str, Any] = {"refusal_type": type(exc).__name__, "message": str(exc)}
    for key, value in vars(exc).items():
        if key.startswith("_"):
            continue
        ...
        body[key] = _finite(value)
```

**Foreign-engine wrap for D-22** (refusals.py:751-760, 792-818): add `"EnvironmentDigestError": "EnvironmentDigestUnavailable"` to `_FOREIGN_FAILURE_CLASSES` (or pass `failure_class=` explicitly) and add the class to `_ENGINE_UNAVAILABLE` in `seam/rest.py:131-143` (503). No new class, so protected SEAM-04 is untouched. Update docstring sentence at :788-789 ("Every other class keeps exactly ``operation`` and ``failure_class``") to mention public `trace_token`.

**Violation-code-only precedent** (refusals.py:880-885): `self.violations = sorted(set(violations))`; message lists codes only. D-25 keeps this shape; add `CODE_CYCLIC_WIRING` to the code set.

**Catalogue obligations:** each new class is added to `__all__` (refusals.py:888-935 list) and to `_REFUSAL_FACTORIES`.

---

### `tests/seam/test_rest_transport.py::_REFUSAL_FACTORIES` (test)

**Analog:** same dict, lines 415-470. Copy the one-line lambda form, keyed by class:
```python
    UnparseableWiringError: lambda: UnparseableWiringError(violations=["unwired-store-effect"]),
    UnbudgetableParticipantError: lambda: UnbudgetableParticipantError("some-node"),
```
Add one lambda per new refusal. Keep every new class at 422 (protected `test_refusal_status_codes.py` demands 422 for anything not listed elsewhere).

---

### `seam/engine.py` (service, request-response)

**Cycle check** - extend `_refuse_unparseable` (engine.py:608-612):
```python
def _refuse_unparseable(parsed: ParsedWiring) -> None:
    if not parsed.report.ok:
        raise UnparseableWiringError(violations=sorted({v.code for v in parsed.report.violations}))
```
Add: `codes = {v.code for v in parsed.report.violations}`; `if parsed.report.cycles: codes.add(CODE_CYCLIC_WIRING)`; raise when `codes`. Call sites: engine.py:1301, 1499, 1564, 1648, 1984.

**Health fixed-text pattern** (engine.py:1916-1949) for the D-16 digest leg:
```python
reasons: list[str] = []  # fixed text and key names only, never values (D-12, Q5)
...
except Exception as exc:  # noqa: BLE001 - health reports an unreachable engine, never raises
    logger.warning("health: the v1 driver health op failed: %s", type(exc).__name__)
    reasons.append("v1 unreachable")
...
overall_ok = (all(v == "ok" for v in stores.values()) and all(engine_report.values()) and clients_wired)
```
Add: `try: await asyncio.to_thread(environment_hash) except EnvironmentDigestError: reasons.append("environment digest unavailable"); digest_ok = False`, AND `digest_ok` into `overall_ok`. No new `HealthReport` field.

**Persist-before-raise (D-04):** wrap post-dispatch steps in `try/except SeamRefusalError as exc: exc.trace_token = trace_token; raise` after `trace_store.persist` (research 4.3).

---

### `runner/trace.py` (model, transform)

**Constants block to extend** (trace.py:38-42):
```python
STOP_REASON_DECLARED_FALLBACK = "declared_fallback"  # D-21: a completed run on a declared fallback path
DEGRADATION_REASON_FALLBACK_PATH = "fallback_path_taken"  # D-21: node-free, guard-free consumer code
TIER_PLACEHOLDER = "T3"  # delete (D-14)
```
Add same-style constants: `REASON_NODE_FAILED = "node_failed"`, `REASON_PLACEMENT_REFUSED = "placement_refused"`, `REASON_BUDGET_HALT = "budget_halt"`, `REASON_CANCELLED = "cancelled"`, plus `REASON_CODES = frozenset({...six...})` reusing the two existing constants. Trailing comment per constant.

**Defaulted fields** (trace.py:83-116): add new `NodeTrace` fields after `tokens` with defaults (`status: str = "completed"`, `execution_mode: str | None = None`, `spent: int | None = None`, `allowance: int | None = None`; `tier`/`feed_tier` default `None`; `cache_hit: bool | None`) and extend `to_dict()`. Defaults keep keyword constructions in existing tests valid. Honesty invariant at :137-165 (`budget_state == "halted"` requires `partial`) stays; failed nodes keep `halted` (Open Question 3).

---

### `parts/schema.py` `Part.reads_namespaces` (model)

**Analog:** `Part` trailing defaulted fields (schema.py:134-141):
```python
    name_at_version: str
    kind: str
    structural_depth: Depth
    effects: list[Effect]
    upstream_ref: str | None
    body: Callable[[NodeContext], Any] | None = None
    artifact_scope: ArtifactScope | None = None
    admission: "AdmissionRecord | None" = None
```
Append `reads_namespaces: tuple[str, ...] = ()` as the LAST field (after `admission`). Add a docstring paragraph in the same voice as the `artifact_scope`/`admission` paragraphs (:124-131). Dependency-free for hashing (identity is name@version + config_hash, scheduler.py:345-350).

---

### `seam/selectors.py` (service, request-response)

**Analog:** the existing `_wiring_effects` (selectors.py:147-154) and the superset test in `_match_capability` (:165). Add a sibling `_wiring_read_namespaces(resolved, registry)` and OR into the superset test; do NOT alter `_wiring_effects` (promotion and compare use it). Docstring rewrite (lines 4-14) must keep `all_wirings()` and avoid `'registry is empty'`, `'five arms'`, `'five Phase 3 arms'`, `'_ARM_NAMES'` anywhere in the file (protected SEAM-16, `test_seam_doc_consistency.py:163-171`).

---

### `runner/guards.py` (utility, transform)

**Declaration path to extend** (guards.py:45-70, 73-84):
```python
@dataclass(frozen=True)
class GuardDeclaration:
    name: str
    evaluating_node: str
    value_when_not_fired: Any
    granularity: GuardGranularity

def declare_guard(name, evaluating_node, value_when_not_fired, granularity) -> GuardDeclaration:
    if granularity not in _ADMISSIBLE_GRANULARITIES:
        raise GuardDeclarationError(name, granularity)
    return GuardDeclaration(...)

def evaluate_guards(guards, runtime_values) -> list[str]:
    return [guard.name for guard in guards
            if runtime_values.get(guard.evaluating_node) != guard.value_when_not_fired]
```
D-19 edits: `signal: str | None = None` as FIFTH parameter (protected `test_dpr_fallback_guard.py:311-322` calls with four keywords and expects `GuardDeclarationError`, so granularity is validated first and `signal` must default); `signal` field on the dataclass; `GuardDeclarationError` gains optional `node_id` attribute (keep the existing `guard_name`/`granularity` positional constructor); `evaluate_guards` reads `runtime_values[g.evaluating_node][g.signal]` and raises `GuardDeclarationError` on a missing node/key, never fires.

**Scheduler call site to harden** (scheduler.py:393-402): currently `[declare_guard(**entry) for entry in raw_guards]` (bare `TypeError` on bad keys). Wrap: non-mapping entry or `TypeError` -> `GuardDeclarationError`; add the ancestor check against `parsed.deps` on the pruned wiring.

**Wiring entries to update** (`wirings/hipporag/base.json:65-72, 107-114`): add `"signal": "guard_fired"` and `"signal": "dpr_stand_in"`. Hash shift is batched (D-21).

---

### `runner/scheduler.py` strict ints (service)

**Current** (scheduler.py:362-371, 381-390): `int(raw)` inside `try/except (TypeError, ValueError)` raising `InvalidMaxConcurrencyError(node_id, raw) from None` / `InvalidTokenAllowanceError`. Replace the coercion with:
```python
if not (isinstance(raw, int) and not isinstance(raw, bool)):
    raise InvalidMaxConcurrencyError(node_id, raw)
```
Keep the `< 1` / `< 0` range checks. Runner error classes stay `ValueError` subclasses in the runner (scheduler.py:196-210, 226-235); the engine translates them. `NodeExecutionError.__init__(node_id, cause)` gains optional `wall_clock_ms` for D-13.

---

### `identity/env.py` (utility, transform)

**Payload to change** (env.py:73-77):
```python
    return {
        "python_version": list(sys.version_info[:3]),
        "platform": platform.platform(),
        "distributions": dist_rows,
    }
```
Replace `"platform"` with `"system": platform.system()`, `"machine": platform.machine()`, `"libc": list(platform.libc_ver())`. Rewrite the module docstring to list every hashed input (it currently lists none of the platform inputs). Cache note: `@functools.cache` at :80; tests call `environment_hash.cache_clear()`. Failure path: `EnvironmentDigestError(RuntimeError)` from `_assert_no_nix_store_path` (:41-47); test by monkeypatching `databasise.identity.env.distributions` with a fake whose `read_text("RECORD")` contains `/nix/store/`.

---

### `validator/parse.py` + `validator/errors.py` (utility, transform)

**Violation construction pattern** (parse.py:149-156, 192-198, 235-243):
```python
violations.append(
    Violation(
        code=CODE_DANGLING_DEP,
        pointer=f"/nodes/{node_id}/deps/{dep_index}",
        message=f"dependency {dep!r} is not a node in this wiring",
    )
)
```
New codes live beside `validator/errors.py:23-36` (`CODE_UNKNOWN_COMPONENT = "unknown-component"` style, kebab-case): `CODE_CYCLIC_WIRING = "cyclic-wiring"`, `CODE_UNKNOWN_PROVIDES`, `CODE_UNKNOWN_EVIDENCE_NODE`, `CODE_KIND_MISMATCH`, `CODE_INVALID_WIRING_DOCUMENT`. Import them in the block at parse.py:54-62.

**Never-raise guard** at parse.py:147: `raw_nodes: dict = doc.get("nodes", {})` is the AttributeError source. Guard `isinstance(doc, dict)` / `isinstance(raw_nodes, dict)`, append one violation, continue with `{}`.

**RFC 6901 escape:** apply `token.replace("~", "~0").replace("/", "~1")` to `node_id` and every `err["loc"]` part at parse.py:164-165, 195, 213, 228, 240; also `validator/blast_radius.py` (`/nodes/{node_id}/effects`).

**Message cleanup:** parse.py:196 `message=str(exc)` becomes `f"component {node.component!r} is not a registered part"`.

**Cycle dedupe** (parse.py:251-254): add the self-loop `[node_id]` only if `node_id` is not already in a multi-member component.

---

### New test files (test, request-response)

**Analog:** `tests/seam/test_hipporag_review_fixes.py`.

**Header and imports** (lines 1-24): module docstring naming the requirement and why a new file exists (neighbouring tests are ledger-protected), `from __future__ import annotations`, absolute `databasise.*` imports, module-level `_HIPPORAG = Selector(capability=["reads_graph", "reads_kv"])`.

**Stub clients** (lines 26-69): small classes with `async def embed(self, texts, **kwargs)` returning `EmbeddingResult(vectors=..., tokens=TokenAccounting(prompt_tokens=..., call_count=1, counted_by="stub-embed"), resolved_model_identity=...)` and `async def chat(self, messages, **kwargs)` returning `ChatResult(text=..., tokens=TokenAccounting(..., counted_by="stub-llm"), ...)`. No usage-bearing client = unbudgetable on LightRAG arms (D-11 note), so keep `counted_by` set.

**Test shape** (lines 72-101): plain `async def test_*(store_root)` (asyncio_mode auto), one behaviour per test, docstring starting with the finding id (use `WIRE-NN:`), engine built as
```python
engine = Databasise(store_root=store_root, workspace=workspace,
                    clients={"embedding": _ClusterEmbeddingClient(), "llm": _TwoDocumentLLMClient()})
```
then a single behavioural assertion; a store handle is closed in `try/finally: await graph_store.finalize()`.

**Rules from research:** fail-first tests must not import symbols this phase adds (resolve with `getattr(module, "Name", None)` and assert not-None, or catch the base class and assert the type name). For KG-arm evidence, reuse `tests/parts_core/lightrag/test_kg_fidelity.py::_ingested_engine` (:93-123). Injected wirings monkeypatch `databasise.seam.engine.resolve_selector` or `engine._corpus_wiring`.

---

### Derived trace schema (config) and deviation record (doc)

**Analog:** `docs/system-model/rig-trace.schema.json` (frozen; `NodeTrace` has `additionalProperties: false`, boolean `cache_hit`, `T0..T3` tier enum; read-only) copied into `evidence/rig-trace.databasise.schema.json` with additive amendments only (research Section 3 and "Code Examples"). Guard drift with `jsonpatch.make_patch(frozen, derived)` and compare op paths to a listed set. `evidence/RIG-TRACE-DEVIATIONS.md` follows the RIG.md §R columns (`docs/system-model/RIG.md:654-668`): `| # | Clause | Defect | Repair direction | Forcing requirement | ANATOMY re-projection | Status |`, no empty cell, Status `recorded, no amendment`. Existing `tests/evidence/test_*_record.py` files are the presence-test pattern. `tests/conftest.py` `assert_valid_trace` flips to the derived schema in the same plan that adds the fields (research Pitfall 7).

## Shared Patterns

### Node-free consumer vocabulary
**Source:** `runner/trace.py:40-41` constants + `seam/redact.py:15-30` (equality key-walk, 'test-time gate' phrase) + `seam/refusals.py:781-783` (node id private).
**Apply to:** every new refusal, reason code, and violation detail. Public attributes are closed codes or counts; node ids, pointers, messages, class names go to `_private` attributes and the server log.

### Pre-dispatch refusal translation
**Source:** `seam/engine.py:608-612` (`_refuse_unparseable`) as the single choke point called before any store opens (call sites 1301, 1499, 1564, 1648, 1984).
**Apply to:** cycles, `InvalidMaxConcurrencyError`, `InvalidTokenAllowanceError`, `GuardDeclarationError`, `EnvironmentDigestError` (runner classes stay runner classes; translate in the engine; four `run_wiring` sites at engine.py:1408, 1505, 1670, 1998).

### Closed-set refusal catalogue
**Source:** `seam/refusals.py:888-935` `__all__` and `tests/seam/test_rest_transport.py:415-470` factories.
**Apply to:** each new `SeamRefusalError` subclass: defined in refusals.py, listed in `__all__`, factory added, status 422.

### Frozen documents
**Source:** `docs/system-model/**` verbatim copy.
**Apply to:** never edit; amendments live in `databasise/evidence/` derived files.

### Protected tests
Edits to `tests/seam/test_query_trace_nodes.py` (lines 33-38, D-03) and `tests/seam/test_lightrag_ingest_mach11.py` (lines 17, 28, 34, D-15) need the owner's `grant-check-edit`. Other protected files named in CONTEXT stay unedited; new behaviour goes in new unprotected files.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `evidence/rig-trace.databasise.schema.json` | config | transform | No derived-schema precedent; use patched copy of the frozen schema plus drift test |
| Sequential per-node dispatch loop in `scheduler.run_wiring` | service | event-driven | Current `TaskGroup` loop (scheduler.py:581-700) is being replaced; use the skeleton in 13-RESEARCH.md Pattern 2 |
| `AmbiguousAnswerPositionError` (two answering provides) | model | request-response | Only a bare `RuntimeError` at engine.py:1008-1013 exists; model on `EmptyNamespaceError` (no public attrs beyond a closed code) |

## Metadata

**Analog search scope:** `databasise/seam`, `runner`, `validator`, `parts`, `identity`, `tests/seam`, with line numbers taken from 13-RESEARCH.md for files not re-read (scheduler body, selectors, redact, registry).
**Files read directly this pass:** refusals.py (40-70, 725-935), guards.py, env.py, trace.py, test_hipporag_review_fixes.py (1-130), parts/schema.py (105-150), parse.py (145-272), engine.py (1905-1952), test_rest_transport.py (410-470), scheduler.py (360-405).
**Pattern extraction date:** 2026-10-19
