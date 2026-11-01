# Phase 15: Offline Tooling & Packaging - Pattern Map

**Mapped:** 2026-10-21
**Files analyzed:** about 75 new/modified files across plans 15-01..15-18 (source: 15-RESEARCH.md §9 plan split, §6 test inventory, §8 docstring inventory, Code Examples; 15-VALIDATION.md uses the same test paths).
**Analogs found:** all in-repo except the new `databasise/cli.py` shared helper (partial analog: `launcher.refuse`). Paths are relative to `databasise/` unless they start with `docs/` or `.planning/`. All 26 excerpted analogs were confirmed git-tracked with `git ls-files` at HEAD 50d54c5. No protected `test_ref` file was read, grepped or diffed; the protected list is the research's `p15r/protected.txt` (101 files). Constraints that come from protected tests are cited from 15-RESEARCH.md §6.3 only. **Line numbers are HEAD values; re-check before editing.**

## File Classification

| New/Modified File | Plan | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|---|
| `pyproject.toml` (`databasise.tools` package, package-data, `dynamic = ["version"]`, `mcp>=2.2.0,<3`), `uv.lock` | 15-01 | config | - | same file :5-7, :100-102, :118-163 | exact (self) |
| `seam/rest.py:363` (`version=__version__`) | 15-01 | config-in-code | - | `seam/rest.py:116` already uses `__version__` | exact (self) |
| `tools/check_import_boundary.py` (skip dirs, `unparseable`, aliased `import_module`, resolved-path exclusions, argparse, provenance skip) | 15-01 | utility (CLI) | file-I/O / transform | same file :91-205; argparse from `eval/corpus_ingest.py:198-202` | exact (self) |
| new `tests/test_packaging.py`; `tests/test_import_boundary.py` (+4) | 15-01 | test | file-I/O (subprocess build) | RESEARCH Code Example "Building the wheel in a temp copy" | no in-repo analog for wheel build |
| new `cli.py` (refusal helper, exit table, selector-vs-wiring check) | 15-02 | utility | request-response | `launcher/__init__.py:125-129` (`refuse`) | partial (role-match; must not reuse) |
| inert `--spend` on `parity/run_arm.py`, `storage_audit.py`, `run_comparison.py`, `run_cross_modality.py`, `build_hipporag_index.py`, `eval/remint.py` | 15-02 | CLI | request-response | `eval/corpus_ingest.py:190-240`, `eval/aa_run.py:538-564` | exact |
| `tests/parity/test_cli_builder_refusals.py`, `test_parity_cli_store_lock.py`, `tests/launcher/test_launch_refusals.py` (pass `--spend`), new `tests/test_cli_support.py` | 15-02 | test | request-response | same files (:19-53, :22-52) | exact (self) |
| new `parts/admission.admit_registry`; `parts/registry.default_registry` calls it; `seam/engine.py` `__init__` calls it for injected registry | 15-03 | service (validation) | transform | `parts/admission.py:123-203`, `parts/registry.py:150-225`, `seam/engine.py:1146-1164` | exact |
| `tests/parts/test_admission.py` (+5); protected `tests/seam/test_seam_events.py` (owner grant only) | 15-03 | test | - | research §6.4 exact edit | n/a |
| `foreign/codebase_memory_mcp_adapter.py` (allowlist, launch timeout, error mapping), `foreign/_mcp_sdk_guard.py` (lock), `parts_core/codebase_memory_mcp.py` (lazy hashing), `parts_core/declared_only.py` | 15-04 | adapter | request-response (stdio MCP) | same adapter :124-293 | exact (self) |
| new `tests/foreign/test_cbm_adapter.py` | 15-04 | test | request-response (fake server) | `tests/parts_core/test_codebase_memory_mcp_admission.py` (unprotected; imports cbm constants by name) | role-match |
| `eval/bundle.py` (hash with text + gold ids, recompute in dedup, opened flag, `split_counts`), `evidence/EVAL-BUNDLE-V1.md` note | 15-05 | model + store | file-I/O | `eval/bundle.py:227-233` (`_find_version_by_content_hash`), `:337-417`, `:487` | exact (self) |
| `tests/eval/test_bundle_versioning.py` (+4) | 15-05 | test | file-I/O | same file (keep :229-240 negative control, :314-329 table parse) | exact (self) |
| `__init__.py` `run_wiring` (canonicalise first) | 15-06 | service | transform | same function :48-107 | exact (self) |
| `tests/test_tracer_end_to_end.py` (+2) | 15-06 | test | - | same file | exact (self) |
| `mcp/server.py` (`description=` on ten `@server.tool`), `mcp/tools.py`, `mcp/__init__.py` docstrings | 15-07 | transport | request-response | `mcp/server.py:180-267` | exact (self) |
| new `tests/mcp/test_tool_descriptions.py`; `tests/mcp/test_dual_transport_parity.py` (:3, :402 text) | 15-07 | test | request-response | `tests/mcp/test_tool_growth_invariant.py:21-31, :88-89` | exact |
| `evidence/parity_report.py`, `DECLARED-DEVIATIONS.md`, `PARITY-EVIDENCE.md`, `FALSIFIER-5-EVIDENCE.md` | 15-08 | renderer | transform | `evidence/parity_report.py:108-126` (`_run_state`), `:1405-1440` (`main`) | exact (self) |
| new `tests/evidence/test_parity_report_render.py`; `tests/parity/test_parity_evidence.py` | 15-08 | test | transform | `RESULTS_DIR` monkeypatch idiom named at `parity_report.py:111-114` | exact |
| `parity/import_index.py` (argparse before lock, workspace line, missing-v2-graph violation, `precondition` literal) | 15-09 | CLI + service | request-response | `parity/run_arm.py:246-266` (argparse then lock), `import_index.py:103-117, :660-737` | exact |
| new `tests/parity/test_import_index_cli.py`; `tests/parity/test_import_verification.py` | 15-09 | test | - | `tests/parity/test_parity_cli_store_lock.py:32-52`; RESEARCH Code Example TOOL-02 | exact |
| `eval/corpus_ingest.py`, `eval/aa_run.py` (one event loop, named ValueError subclasses, injected empty-index check), `eval/remint.py` | 15-10 | CLI | request-response | `eval/aa_run.py:527-618`, `corpus_ingest.py:190-240` | exact (self) |
| new `tests/eval/test_eval_store_boundary.py`; `tests/eval/test_aa_run.py`, `test_corpus_ingest.py`, `test_remint.py` | 15-10 | test | - | `tests/eval/test_aa_run.py:125-160` (`_StubEngine`), `:413-433` | exact |
| `parity/run_comparison.py` (inconclusive exit 3, preflight, variance >= 2) | 15-11 | CLI | batch | same `main` :711-743; record status Literal :445 | exact (self) |
| new `tests/parity/test_run_comparison.py` | 15-11 | test | - | `test_parity_cli_store_lock.py` `_boom` idiom | role-match |
| `parity/v1_driver_script.py`, `parity/v1_arm.py` | 15-12 | subprocess driver | request-response | same files; RESEARCH Code Example "Loading the v1 driver without lightrag" | exact (self) |
| new `tests/parity/test_v1_driver_script.py` | 15-12 | test | - | RESEARCH Code Example (stub `sys.modules`) | no in-repo analog |
| `parity/run_arm.py`, `parity/storage_audit.py` (`--arm hipporag`, partial/cycle exit 3, `unreached`) | 15-13 | CLI | batch | `storage_audit.py:213-214` (cycle dict), `:238-266`; keep `run_arm._inject_query` | exact (self) |
| `tests/parity/test_storage_audit.py` (:388-435 + new nodes) | 15-13 | test | - | same file | exact (self) |
| `parity/run_cross_modality.py` (read-only preflight, selector check, partial records, `corpus_hash`) | 15-14 | CLI | batch | `eval/corpus_ingest.py:76-79` (`_ARM_SELECTORS`), `run_comparison.py:723-743` | role-match |
| `tests/parity/test_cross_modality_isolation.py` (+5) | 15-14 | test | - | same file | exact (self) |
| `parity/build_hipporag_index.py` (dry run, empty-root build, chunk-count check) | 15-15 | CLI | batch | `eval/corpus_ingest.py:190-240` | exact |
| `tests/parity/test_build_hipporag_index.py` (+3; keep `test_3` :165-176) | 15-15 | test | - | same file | exact (self) |
| new `seam/floors_store.py` (`<store_root>/floors.db`) | 15-16 | store | CRUD (sqlite) | `seam/jobs_store.py:1-56` | exact |
| `seam/engine.py` `promote` (two-stage gate), `seam/promotion.py` | 15-16 | service | request-response | `seam/engine.py:2376-2416`; `seam/selectors.py:299-303` (read-only ledger) | exact (self) |
| `eval/calibration.py` (refuse empty traces, two-sided floor), `eval/aa_run.py` (persist floor) | 15-16 | service | transform | `eval/calibration.py:83-166` | exact (self) |
| new `tests/seam/test_promotion_floor.py`, `tests/seam/test_floors_store.py`; `tests/eval/test_calibration.py`, `test_aa_run.py` | 15-16 | test | CRUD / request-response | `tests/eval/test_aa_run.py:125-160`; RESEARCH Code Example TOOL-12 | exact |
| `docs/gui/API-INVENTORY.md` §3.5.1, §7 | 15-16 | doc | - | n/a | text edit |
| `evidence/falsifier2.py` (computed verdict, int `main`), `evidence/f07_report.py` (new `main`), `evidence/__init__.py`, `evidence/wirings/w2-codebase-memory-mcp.json`, regenerated `FALSIFIER-2-EVIDENCE.md`, `F-07-MUTABLE-STORE-DISPOSITION.md`, `CROSS-MODALITY-EVIDENCE.md` | 15-17 | renderer | transform | `evidence/parity_report.py:1405-1440` (argparse + int main), `falsifier2.py:554-578`, `f07_report.py:173-187` | exact |
| new `tests/evidence/test_falsifier2_verdict.py`, `test_docstring_facts.py`; `test_f07_record.py`, `test_cross_modality_record.py` | 15-17 | test | transform | same evidence test files | exact (self) |
| new `tests/test_cli_refusals.py`, `tests/test_dry_run_default.py`; `docs/gui/CODEBASE-MAP.md` | 15-18 | test / doc | request-response | `tests/parity/test_cli_builder_refusals.py:19-53`, `tests/eval/test_aa_run.py:413-433` | exact |
| TOOL-17 `tests/test_removed_stores_absent.py` (protected, existing) | orchestrator | test | - | no code; `record-fail --at 226b2cf^` | n/a |

## Pattern Assignments

### CLI `main()` shape: argparse, estimate-only default, exit codes (15-02, 15-09..15-15)

**Analog:** `eval/corpus_ingest.py:190-240`. This is the target shape for every offline CLI: argparse first, read-only estimate, `--spend` gate before any client, lock or store.
```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--arm", choices=list(_ARM_CHOICES), default="lightrag")
    parser.add_argument("--spend", action="store_true", default=False)
    args = parser.parse_args(argv)

    snapshot = load_snapshot(CORPUS_DIR)
    try:
        result = estimate(snapshot, limit=args.limit, arm=args.arm)
    except LimitExceedsCorpusError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result.to_dict(), indent=2))

    if not args.spend:
        print("mode: estimate-only")
        return 0

    try:
        env = _load_env_file(DEFAULT_V1_ENV_PARITY)
        clients = _build_clients(env)
    except BUILDER_REFUSALS as exc:
        print(str(exc), file=sys.stderr)
        return 1
```
The CLIs that spend by default today put the lock first, with no estimate step. They must gain the block above *before* the lock. Current `parity/run_arm.py:253-266`:
```python
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", required=True, choices=["naive", "bypass", "hybrid", "local", "global"])
    parser.add_argument("--query", required=True)
    args = parser.parse_args(argv)

    try:
        with store_lock(import_index.DEFAULT_STORE_ROOT):  # D-03
            result = asyncio.run(run_arm(args.arm, args.query))
    except (StoreLockedError, *BUILDER_REFUSALS) as exc:
        print(str(exc), file=sys.stderr)
        return 1
```
Keep reading `import_index.DEFAULT_STORE_ROOT` at call time. The lock test monkeypatches that attribute (`test_parity_cli_store_lock.py:38`).

**Exit 3 (D-03):** `run_comparison.py:739-743` currently returns `2` for inconclusive. Remap it to `3`, because `2` is reserved for argparse errors. Update the docstring at :712-716.
```python
    if had_error:
        return 1
    if any(r.status == "inconclusive" for r in records):
        return 2
    return 0
```
`storage_audit` follows the same rule. `run_audit` returns `{"cycle": ..., "partial": False}` at `storage_audit.py:213-214`. Map `cycle` or `partial` to exit 3 and print the reason.

**`import_index` (15-09):** replace the literal argv sniff at `import_index.py:710-711` (`verify_only = "--verify" in argv`) with argparse (`--verify` as `store_true`) placed before the `with store_lock(...)` at :720. Print the derived workspace from `_import_workspace()` (:120) along with its source. Add `"precondition"` to the `Violation.assertion` Literal at :109. Add an `else` branch to the graph check at :663 (`if v1_graph is not None and v2_graph is not None:`) for the case where v1 is present and v2 is absent (`graph-topology`).

**One event loop (15-10, TOOL-04):** `aa_run.py:584-597` calls `asyncio.run(...)` once per family inside a `for`. Move the loop into one `async def` and call `asyncio.run` once. Keep the `calibrate_family(...)` keyword call shape, because protected LRAG-15 patches it and asserts `seen == [expected]` (research finding 3). Make the empty-index check an injected callable parameter of `calibrate_family` that defaults to `None`. Do not put it in `main`. The bare `ValueError` in `aa_run.py:556` must become named subclasses (D-03).

---

### `cli.py` shared refusal helper (new, 15-02)

**Partial analog:** `launcher/__init__.py:125-129`
```python
def refuse(exc: BaseException) -> int:
    # A decode error's text quotes bytes of the env file; name the file problem without them (RUN-05).
    detail = "the --env-file is not valid UTF-8" if isinstance(exc, UnicodeDecodeError) else exc
    print(f"databasise: {detail}", file=sys.stderr)
    return 1
```
Copy the shape: one stderr line, return the int, and never quote env bytes. Change the prefix to `ClassName: message` (D-03), and collapse and truncate multi-line text (`V1ArmSubprocessError` carries v1 stderr; research Security Domain). Some messages already begin with their class name (`LimitExceedsCorpusError: ...` at `corpus_ingest.py:95`). Do not print the class name twice.

**Do not put it in `launcher` and do not import it from `launcher`.** `launcher/__init__.py:23` does `from databasise.parity.import_index import DEFAULT_STORE_ROOT`, and RUN-06/07 tests pin the `databasise: ` prefix.

**Import-cycle constraint (research finding 7):** importing `databasise.seam.refusals` loads `seam.engine` and `parity.import_index`. `cli.py` is imported by `parity.import_index`, so it **must import seam types lazily inside functions**. This follows the house pattern in `parts/admission.py:173-174`:
```python
    from databasise.seam.query import QueryObject
    from databasise.seam.selectors import _is_default_eligible
```
and `parts/registry.py:214-220` ("Local import: ... keeps the registry/parts_core dependency direction one-way"). Keep top-level imports to stdlib only.

**Selector-vs-named-wiring check (D-10):** the input is `corpus_ingest._ARM_SELECTORS` (`corpus_ingest.py:76-79`). Keep its name and values (LRAG-15):
```python
_ARM_SELECTORS: dict[str, Selector] = {
    "lightrag": Selector(capability=["reads_vector"]),
    "hipporag": Selector(capability=["reads_graph", "reads_kv"]),
}
```

---

### `seam/floors_store.py` (new store, CRUD sqlite, 15-16)

**Analog:** `seam/jobs_store.py:12-56`. Copy it whole. It uses a per-call connection, WAL, `CREATE TABLE IF NOT EXISTS` only on write, and a read-only URI read that never creates the file.
```python
class JobFamilyStore:
    def __init__(self, store_root: str | Path) -> None:
        self._path = Path(store_root) / "jobs.db"

    def record(self, job_id: str, family: str, document_id: str | None) -> None:
        """Record ``job_id``'s family, creating ``jobs.db`` on the first call."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with contextlib.closing(sqlite3.connect(self._path)) as conn, conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS job_families (job_id TEXT PRIMARY KEY, family TEXT NOT NULL, "
                "document_id TEXT, created_at TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT OR REPLACE INTO job_families VALUES (?, ?, ?, ?)",
                (job_id, family, document_id, datetime.now(UTC).isoformat()),
            )

    def lookup(self, job_id: str) -> JobFamily | None:
        """``job_id``'s row, or ``None``. Opens read-only and creates nothing."""
        if not self._path.is_file():
            return None
        with contextlib.closing(sqlite3.connect(f"{self._path.resolve().as_uri()}?mode=ro", uri=True)) as conn:
            row = conn.execute(...).fetchone()
        return JobFamily(*row) if row else None
```
Floor row key: `wiring_instance_hash` plus the five `NullIdentity` fields (`eval/calibration.py:108-118`: `bundle_at_v, tier, metric, determinism_setting, concurrency_setting`), and the `floor` value. Stage 1 needs an `any_floor()` method that follows the `lookup` pattern (file absent means False, nothing created). **The module must not import `databasise.ledger`** (the measurement-posture test, research finding / Pitfall 5). Instantiate it in `Databasise.__init__` beside `self._jobs = JobFamilyStore(self.store_root)` (`engine.py:1164`). Note that 15-03 also owns `__init__` in W1. 15-16 is W3, so these edits do not collide.

**Staleness:** reuse `CalibrationResult.floor_for` / `NullIdentity.stale_reason` (`calibration.py:120-166`). The engine maps `StaleNullError` to `GateNotCalibratedError(verb=verb)`. No new refusal class (D-13).

---

### Promote gate, two stages (`seam/engine.py` `promote`, 15-16)

**Current site:** `seam/engine.py:2379-2416`
```python
        if verb in _NOT_BUILT_VERBS:
            raise GateVerbNotBuiltError(verb=verb)

        # LEDG-08 (D-04): no arm has a calibrated floor, so a gate verb is refused identically for
        # every arm, before alias validation, trace resolution and any Ledger construction.
        if verb in _GATE_VERBS:
            raise GateNotCalibratedError(verb=verb)

        _resolved_records, arm_name, arm_instance_hashes = self._resolve_operator_preconditions(
            alias, trace_ids, change_origin, refuse_partial=True
        )
        new_resolved = _wiring_for_row(arm_name, alias=alias)

        def _promote_sync() -> tuple[str, int]:
            ...
            with Ledger(self.store_root) as ledger, ledger.transaction():
                prior_record = ledger.by_alias(alias)
                ...
                mutation_class = derive_mutation_class(new_resolved, prior_resolved)
                if verb in _GATE_VERBS:
                    enforce_gate_verb_posture(verb, mutation_class)  # always raises
```
- **Stage 1** replaces :2384-2385 with `if verb in _GATE_VERBS and not self._floors.any_floor(): raise GateNotCalibratedError(verb=verb)`. It must still run before alias and trace resolution, because protected LEDG-08 expects `GateNotCalibratedError` for an empty alias and for `["no-such-trace"]` (research finding 4).
- **Stage 2** runs after `_resolve_operator_preconditions` and before `_promote_sync`, and must not use `with Ledger(...)`. That form creates `ledger.db`, and LEDG-06 forbids it. Use the read-only analog from `seam/selectors.py:299-304`:
```python
    ledger = Ledger.open_existing(store_root, read_only=True)
    if ledger is None:
        raise refusal
    with ledger:
        record = ledger.by_alias(alias)
    resolved = wiring_for_name(record.mutation_id) if record is not None else None
```
(`Ledger.open_existing` is at `ledger/ledger.py:163-206`; it returns `None` when the file is absent and opens with `PRAGMA query_only`.) Then look up floors by `arm_instance_hashes`, never a recomputed hash (D-13), and call `enforce_gate_verb_posture(verb, mutation_class)` (`seam/promotion.py:264`). Full sketch: RESEARCH Code Example "The gate, stage 1 and stage 2".
- Replace the stale comment at :2412-2413 ("Unreachable until TOOL-12 ...").

---

### `admit_registry` (15-03)

**Analogs:** `parts/admission.py:160-203` (`cross_check_conditions`, already lazy-importing seam) and `parts/registry.py:208-225`.
```python
def default_registry() -> PartRegistry:
    from databasise.parts_core import PARTS
    ...
    registry = PartRegistry(seed_tracer_parts=False)
    for part in (*PARTS, *DECLARED_ONLY_PARTS, *LIGHTRAG_PARTS, *HIPPORAG_PARTS, *HIPPORAG_CORPUS_PARTS):
        registry.register(part)
    return registry        # <- admit_registry(registry) goes immediately before this return
```
Engine site: `seam/engine.py:1156` `self.registry = registry if registry is not None else default_registry()`. Call `admit_registry(registry)` only on the injected branch, because `default_registry()` already admits.

**Shared-scope rule to change:** `admission.py:156` gates on `structural_depth`:
```python
    if part.structural_depth == "opaque" and part.artifact_scope == "shared":
        raise ForbiddenSharedScopeError(part.name_at_version, part.artifact_scope)
```
D-17 changes this to `part.kind == "opaque"`. Gate on `kind`, not `structural_depth`, as the `register()` docstring at `registry.py:165-173` already explains. The name-match check (`record.part_name_at_version == part.name_at_version`) and the field checks belong in `validate_admission` (:123-157). New refusals subclass `RuntimeError` with positional `part_name_at_version` and follow `ForbiddenSharedScopeError` (:110-120). **Do not reword any admission evidence string** (LRAG-12; research §8 last row). Sketch: RESEARCH Code Example `admit_registry`. The first task is the owner-gated edit to `tests/seam/test_seam_events.py:156` (research §6.4); the plan is `autonomous: false`.

---

### cbm adapter (anyio / MCP client, 15-04)

**Analog:** `foreign/codebase_memory_mcp_adapter.py:211-293` (the code being changed).
```python
    resolved = _resolve_binary(binary)

    import anyio

    mcp_module = import_real_mcp("mcp")
    stdio_module = import_real_mcp("mcp.client.stdio")
    ...
    params = StdioServerParameters(command=resolved, args=[])
    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                with anyio.fail_after(timeout):
                    return await call(session)
    except ForeignEngineUnavailableError:
        raise
    except BaseException as exc:  # noqa: BLE001
        unwrapped = _unwrap(exc)
        if isinstance(unwrapped, TimeoutError):
            raise CbmToolTimeoutError(tool_name, timeout) from exc
        raise CbmTransportError(tool_name=tool_name, cause=..., machine_endpoint=..., foreign_endpoint=...) from exc
```
Defects visible here, matching the TOOL-18 fail-first list:
- `session.initialize()` sits outside `fail_after`, so a hanging server is not bounded at launch. Wrap the handshake in its own launch timeout.
- `CbmToolCallError`, raised inside `_call` (:284-286), is caught by the `except BaseException` and re-raised as `CbmTransportError`. Add `except (CbmToolCallError, UntypedForeignItemError): raise` (after `_unwrap`) ahead of the generic branch.
- Allowlist: refuse `delete_project`, `manage_adr`, `index_repository` and `ingest_traces` by name in `call_tool` (:272) **before** `_resolve_binary` and before any launch. Follow the refusal-class style of `CbmToolCallError` (:141-149).
- `_mcp_sdk_guard.import_real_mcp` gains a lock. Protected RUN-04 `test_mcp_sdk_guard` constrains its behaviour, so run it after the change.
- Lazy hashing in `parts_core/codebase_memory_mcp.py`: importing that module must not read the 293 MB binary (research finding 8). Keep the module constants importable by the same names (`tests/parts_core/test_codebase_memory_mcp_admission.py` imports them; WIRE-17 registers `CODEBASE_MEMORY_MCP_PART`). The part stays out of `default_registry()` and keeps `mutates_store` (D-19).

---

### MCP tool registration and descriptions (15-07)

**Analog:** `mcp/server.py:197-265`. Ten decorators, each `@server.tool(name="...")`, each taking the single `args` model and returning `model_dump()`:
```python
    @server.tool(name="ingest")
    async def ingest_tool(args: IngestToolArgs) -> dict[str, Any]:
        job = await engine.ingest(args.to_ingest_document(), args.selector)
        return job.model_dump()
```
Add `description="..."` to each decorator. The SDK reads `description=` from the decorator (research §5.4, probe). Several tools currently publish their docstrings, which contain plan references (`compare_tool` :209-220 "06-03-PLAN.md", `retry_tool` :233 "11-08 (D-08)", `promote_tool` :251-253 "07-03-PLAN.md"). A description must match none of `PLAN\.md`, `Phase \d`, `_refusal_mapped`, `\d\d-\d\d`, and must name no arm, wiring, part or node (§18 agnostic constraint). Fix the stale "registers the five tools" text at :189. Names and the `args` schema stay unchanged (SEAM-03, RUN-01, `test_tool_growth_invariant`).

**Test analog:** `tests/mcp/test_tool_growth_invariant.py:26-30, :88-89`. Copy the skip guard and the listing:
```python
try:
    import databasise.mcp as mcp_package_module
except ImportError:
    pytest.skip("the `mcp` extra is not installed", allow_module_level=True)
from databasise.mcp import create_server
...
    server = create_server(store_root=tmp_path, workspace="growth-pin")
    names = [tool.name for tool in await server.list_tools()]
```
Do not use `pytest.importorskip("mcp")` (CWD-shadow, comment :21-25).

---

### Evidence renderers: falsifier2, f07_report, parity_report (15-08, 15-17)

**Target `main` analog:** `evidence/parity_report.py:1405-1440`. It parses with argparse, returns an int, writes with `Path.write_text(..., encoding="utf-8")`, and ends with `sys.exit(main())` at :1443-1444.

**`falsifier2.main` today** (`falsifier2.py:571-578`) returns `None`, and the verdict is a fixed string at :556-567 ("**Result: Falsifier 2 did not fire.** ..."):
```python
def main() -> None:
    text = render_markdown()
    EVIDENCE_PATH.write_text(text, encoding="utf-8")
    print(text)
```
Compute the verdict from `evaluate_probe` (:301) and `evaluate_wiring` (:315) results, and return a non-zero exit when the falsifier fires. `FALSIFIER-2-EVIDENCE.md` is byte-pinned by `tests/validator/test_falsifier2_evidence.py`, so regenerate it in the same task.

**`f07_report`** has no `main`. `render_f07_record(registry)` (:173-187) is pure and raises `ValueError` on an empty enumeration:
```python
    live_rows = _live_mutates_store_rows(registry)
    all_rows = [*live_rows, *_CATALOGUED_NOT_BUILT]
    if not all_rows:
        raise ValueError("F-07 record would enumerate zero mutable-store components -- ...")
```
Add `main()` that writes `render_f07_record(default_registry())` (D-16) in parity_report's main shape. Add it to `__all__` (:315-319). The verdict prose at :249-278 ("enforced as an explicit refusal in the comparison path", "MODAL-05 itself stays unproven") must change (D-16; research §8). The document is byte-pinned at `tests/evidence/test_f07_record.py:86-91`, so regenerate it.

**`parity_report` "render only states it read":** use the existing `_run_state()` pattern (:108-126). It derives state from the records and retargets through `monkeypatch.setattr(parity_report, "RESULTS_DIR", tmp_path)` (docstring :111-114):
```python
    statuses = {record.get("status", "inconclusive") for arm in ARMS for record in load_comparison(arm)}
    statuses |= {load_storage_audit(arm).get("status", "inconclusive") for arm in ARMS}
    if statuses == {"completed"}:
        return "completed"
```
The stale `.planning/phases/02-`/`03-` refs at `parity_report.py:60-62, :493, :506, :1342` become `.planning/milestones/v1.0-phases/...` (research finding 12).

---

### Packaging: pyproject (15-01)

**Analog:** the same file. Current version line `pyproject.toml:7` `version = "0.1.0"`. Source of truth is `__init__.py:38` `__version__ = "0.1.0"`, already used at `seam/rest.py:116`. The edits:
```toml
[project]
name = "databasise"
dynamic = ["version"]          # replaces line 7

[tool.setuptools.dynamic]
version = {attr = "databasise.__version__"}
```
Existing package-data syntax to extend (`pyproject.toml:158-163`, i.e. the section starting at file line 158):
```toml
[tool.setuptools.package-data]
"databasise.evidence" = ["wirings/*.json"]
"databasise.wirings" = ["*.json", "lightrag/*.json", "hipporag/*.json"]
```
Add `databasise = ["evidence/eval-bundles/**/*", "tests/fixtures/corpus/**/*", "tests/fixtures/eval-corpus/**/*"]`. Add `"databasise.tools"` to `packages` (:124-154), keeping the per-entry comment style ("named in the same commit that ..."). The `mcp` extra at :100-102 becomes `"mcp>=2.2.0,<3"`. `package-dir = {"databasise" = "."}` (:123) stays. Protected `test_removed_stores_absent.py` reads the package list, so run it. Run `uv lock --offline` afterwards.

**`seam/rest.py:363`** `FastAPI(title="databasise", version="0.1.0")` becomes `version=__version__`.

**Import-boundary scan (`tools/check_import_boundary.py`):**
- `scan_file` :119-120 calls `path.read_text` then `ast.parse` unguarded. Wrap both and emit `Violation(str(path), 0, repr(exc), "unparseable")` on `SyntaxError`, `UnicodeDecodeError` or `ValueError`.
- `_dynamic_import_target` :97-104 recognises only `importlib.import_module` and `__import__`. Also track names bound by `from importlib import import_module [as x]` (collect them in a first pass over `ast.ImportFrom`).
- `scan_tree` :151-155: skip parts starting with `.` or equal to `site-packages`, `build` or `dist`. Replace `path.name in _SUBPROCESS_ENTRY_POINT_EXCLUSIONS` with a resolved-path comparison, as the self-exclusion at :149-153 already does.
- `main` :189-205: `del argv` becomes argparse. When `repo_root / "v1"` is absent, print one stderr line and skip `check_upstream_refs`.

**Packaging test:** no in-repo analog. Use RESEARCH Code Example "Building the wheel in a temp copy". Skip with a named reason when `uv` or the warm cache is missing (that skip is not a pass).

---

### Test fixtures for CLIs: capsys, tmp store roots, stub clients

**Store-root redirect and lock (copy for every lock/dry-run test):** `tests/parity/test_parity_cli_store_lock.py:36-52`
```python
    module = importlib.import_module(f"databasise.parity.{module_name}")
    root = tmp_path / "store"
    monkeypatch.setattr(import_index, "DEFAULT_STORE_ROOT", root)

    def _boom(*_args, **_kwargs):
        raise AssertionError(_NOT_STARTED)

    for name in work_functions:
        monkeypatch.setattr(module, name, _boom)

    with store_lock(root):
        returncode = module.main(argv)

    assert returncode == 1
    err = capsys.readouterr().err
```
For `test_dry_run_default.py`, use the same `_boom` on work functions, client builders and `store_lock`, then assert `main([]) == 0` and `not root.exists()`.

**Stub env file (never the real one, D-24):** `tests/parity/test_cli_builder_refusals.py:12-17, :39-46`
```python
    env_file = tmp_path / "env"
    env_file.write_text(_ENV, encoding="utf-8")
    monkeypatch.setattr(import_index, "DEFAULT_STORE_ROOT", tmp_path / "store")
    monkeypatch.setattr(run_arm, "DEFAULT_V1_ENV_PARITY", env_file)
    monkeypatch.setattr(run_arm, "_build_stores", lambda *a, **k: {})
    if hasattr(module, "DEFAULT_V1_ENV_PARITY"):
        monkeypatch.setattr(module, "DEFAULT_V1_ENV_PARITY", env_file)
    ...
    assert module.main(argv) != 0
    err = capsys.readouterr().err
    assert "RERANK_BINDING" in err and "bogus-marker" not in err and "Traceback" not in err
```
The `_CASES` table (:19-31) is the parametrize shape for `tests/test_cli_refusals.py`. In 15-02, add `"--spend"` to the run_arm, storage_audit, run_cross_modality, build_hipporag_index and remint entries.

**Fail-if-constructed fakes plus a capsys estimate check:** `tests/eval/test_aa_run.py:413-433`
```python
    def _fail_if_constructed(**kwargs):
        raise AssertionError("Databasise must not be constructed without --spend")
    def _fail_if_called(*args, **kwargs):
        raise AssertionError("_build_clients/_load_env_file must not be called without --spend")
    monkeypatch.setattr(aa_run, "Databasise", _fail_if_constructed)
    monkeypatch.setattr(aa_run, "_build_clients", _fail_if_called)
    monkeypatch.setattr(aa_run, "_load_env_file", _fail_if_called)
    exit_code = aa_run.main(["--split", "dev"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "mode: estimate-only" in out
```
**Stub engine with real traces:** `tests/eval/test_aa_run.py:125-160` (`_StubEngine` persists `{"nodes": [{"node_id": "stub-node", "cache_hit": ...}]}` into a real `TraceStore`). Use it for TOOL-12 floor persistence and the empty-trace refusal. **Do not rename or move `_make_bundle`, `_StubEngine` or `_StubVectorStore`**, because protected LRAG-15 imports them (research §6.1).

**Fail-first capture (D-22):** RESEARCH Code Example TOOL-02 `_outcome(callable_, *args)`. Catch `BaseException` so `SystemExit` becomes data and the pre-fix failure is a plain `AssertionError`.

## Shared Patterns

### Exit-code table (D-03)
**Apply to:** `import_index`, `run_arm`, `storage_audit`, `run_comparison`, `run_cross_modality`, `build_hipporag_index`, `corpus_ingest`, `aa_run`, `remint`, `check_import_boundary`, `parity_report`, `falsifier2`, `f07_report`.
`0` done or estimate-only; `1` named refusal via `cli.refuse`; `2` argparse only; `3` ran but inconclusive. `main()` returns the int, and `if __name__ == "__main__": sys.exit(main())`.

### Lazy imports across the parts/seam/parity boundary
**Source:** `parts/admission.py:173-174`, `parts/registry.py:214-220`, `foreign/codebase_memory_mcp_adapter.py:228-236`.
**Apply to:** `cli.py` (seam refusals), `admit_registry` (wirings, seam), the cbm part module (binary hash), and the gate's `eval.bundle` lookup (research Open Question 2).

### Store files created only on write
**Source:** `seam/jobs_store.py:31-53`, `ledger/ledger.py:163-206`.
**Apply to:** `floors_store.py`, the promote gate's read path, and every dry run (no lock file, no `.comparison_results`).

### Refusal class style
**Source:** `eval/corpus_ingest.py:84-97` (ValueError subclass, keyword attrs, message prefixed with the class name) and `parts/admission.py:110-120`.
**Apply to:** the new named ValueError subclasses in `aa_run`/`remint`/`bundle`, the cbm allowlist refusal, and the admission field checks. No new class in `seam/refusals.__all__` (SEAM-04/14 catalogue untouched; D-13).

### Regenerate committed documents in the same task as their renderer
**Source:** `evidence/f07_report.py:174-178` (byte-identical re-render convention).
**Apply to:** `FALSIFIER-2-EVIDENCE.md`, `F-07-MUTABLE-STORE-DISPOSITION.md`, `PARITY-EVIDENCE.md`, `DECLARED-DEVIATIONS.md`, `CROSS-MODALITY-EVIDENCE.md`.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tests/test_packaging.py` | test | file-I/O (subprocess `uv build`) | no existing test builds a wheel; use the RESEARCH Code Example |
| `tests/parity/test_v1_driver_script.py` | test | stub `sys.modules` load | no test loads the v1 driver today; use the RESEARCH Code Example |
| `cli.py` | utility | request-response | only `launcher.refuse` is close, and it cannot be reused (cycle, pinned prefix) |

## Metadata

**Analog search scope:** `databasise/{eval,parity,seam,parts,parts_core,foreign,mcp,evidence,ledger,launcher,tools}`, `databasise/pyproject.toml`, `databasise/__init__.py`, unprotected tests in `tests/parity`, `tests/eval`, `tests/mcp`.
**Files scanned:** 26 analogs read (all `git ls-files`-tracked).
**Pattern extraction date:** 2026-10-21
