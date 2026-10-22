---
phase: 15-offline-tooling-packaging
lane: C
reviewed: 2026-10-21T23:51:57Z
depth: deep
diff_base: 00eeae8
files_reviewed: 15
files_reviewed_list:
  - databasise/parts_core/codebase_memory_mcp.py
  - databasise/parts_core/declared_only.py
  - databasise/foreign/codebase_memory_mcp_adapter.py
  - databasise/foreign/_mcp_sdk_guard.py
  - databasise/mcp/server.py
  - databasise/mcp/tools.py
  - databasise/mcp/__init__.py
  - databasise/evidence/parity_report.py
  - databasise/evidence/f07_report.py
  - databasise/evidence/falsifier2.py
  - databasise/evidence/__init__.py
  - databasise/tools/check_import_boundary.py
  - databasise/pyproject.toml
  - databasise/README.md
  - docs/gui/CODEBASE-MAP.md
findings:
  critical: 1
  warning: 6
  info: 8
  total: 15
status: issues_found
---

# Phase 15: Code Review Report (Lane C)

**Reviewed:** 2026-10-21T23:51:57Z
**Depth:** deep
**Files Reviewed:** 15
**Status:** issues_found

## Narrative Findings (AI reviewer)

## Summary

Scope: the codebase-memory-mcp part and adapter (allowlist, launch timeout, lazy admission), the MCP server tool descriptions, the three evidence renderers (parity_report, falsifier2, f07_report), the import-boundary checker, packaging metadata, and the README and CODEBASE-MAP edits. Offline tests for evidence, mcp, foreign and parts_core pass (538 passed). The defects below were confirmed with scratch probes that wrote only to temp directories. No provider spend, no `--spend`, no env-file reads.

The adapter allowlist and the lazy admission work as described. No §18 leak was found in the MCP tool descriptions, and no path in scope prints env-file contents. The main problems are in the evidence renderers, which D-16 says must "compute verdicts and exit codes from results":
- the Falsifier 2 verdict ignores the named wirings' own validator results;
- `parity_report` still lets four failure classes escape as tracebacks, and can leave its two documents out of sync;
- `parity_report`'s inconclusive and mixed prose describes a precondition cause that D-07 no longer guarantees.

The CODEBASE-MAP launch command was changed to one that does not run.

## Critical Issues

### CR-01: The Falsifier 2 verdict and exit code ignore validator violations in the three named wirings

**File:** `databasise/evidence/falsifier2.py:319-361`, `:570-594`, `:597-604`
**Issue:** `evaluate_wiring()` computes `violations` and `cycles` for each named wiring (lines 359-360). Neither field is rendered anywhere in `render_markdown()`, and neither feeds the verdict. The verdict and `main()`'s exit code depend only on `failing_probes()`, so the "did not fire" text (which says "All three named wirings above compute without any self-declaration") is printed without checking it.
**Confirmed scenario:** Add `writes_artifact` to the w2 node's effects (a temp copy of `wirings/`, with `WIRINGS_DIR` and `EVIDENCE_PATH` retargeted). `evaluate_wiring("w2-codebase-memory-mcp").violations == ['effects-exceed-part']`, yet `main([])` returns 0. The document says "Falsifier 2 did not fire", and the violation code appears nowhere in the wiring sections.
**Second scenario:** Put a self-declared `effective_depth` on a named-wiring node. `parse_wiring` drops the node, and line 333 (`parsed.parts[node_id]`) raises a bare `KeyError: 'cbm'`. The run crashes with a traceback and does not report "Falsifier 2 fired". That is the exact self-declaration case this falsifier exists to catch.
**Fix:** Include the named wirings in the verdict and the exit code, and render their violations:
```python
def failing_wirings() -> tuple[str, ...]:
    failing = []
    for stem in NAMED_WIRINGS:
        parsed = parse_wiring(load_wiring(stem), probe_registry())
        if parsed.report.violations or set(parsed.node_order) != set(parsed.parts):
            failing.append(stem)
    return tuple(failing)

# render_markdown: render each wiring's violations; verdict "fired" when
# failing_probes() or failing_wirings(); evaluate_wiring skips nodes absent from parsed.parts
# main: return 1 if failing_probes() or failing_wirings() else 0
```

## Warnings

### WR-01: parity_report.main lets four failure classes escape as tracebacks and can write one of its two documents only

**File:** `databasise/evidence/parity_report.py:1688-1700`, `:1722-1730`; raise sites `:115-125`, `:824-834`, `:868-874`, `:1212`, `:1290`, `:992`
**Issue:** `main()` maps only `ParityRecordFormatError` to `refuse()`. The class docstring promises "a caller never sees `JSONDecodeError` or `KeyError`". A probe against temp copies of `parity_results/` shows these escaping instead:
- a comparison record missing `status` raises `KeyError: 'status'` (line 1212, `record['status']`). `check_results` reports this as a violation, but the render path does not run that check;
- a missing `<arm>-comparison.json` raises a raw `FileNotFoundError`. This is the normal case from an installed wheel, because `parity_results/` and `human_findings.json` are not package data;
- an orphan `declared_causes` entry raises `OrphanDeviationCauseError` (a `ValueError`, not mapped);
- a `judgment` outside the allowed set raises `InvalidJudgmentError`.

`notes: null` in a spot-check raises `AttributeError` at line 992 (`_escape_cell(None)`).

The `InvalidJudgmentError` case also shows a partial write. `DECLARED-DEVIATIONS.md` is written at line 1724, then `render_markdown()` raises, so `PARITY-EVIDENCE.md` is left stale beside a freshly written deviations file.
**Fix:** Render both texts before writing either. Map the module's named refusals through `refuse`. Run `check_results()` first and refuse on violations:
```python
def _run(args):
    ...
    violations = check_results()
    if violations:
        raise ParityRecordFormatError("; ".join(map(str, violations)))
    deviations_text = render_deviations_document(_collect_deviations())
    evidence_text = render_markdown()
    DEVIATIONS_PATH.write_text(deviations_text, encoding="utf-8")
    EVIDENCE_PATH.write_text(evidence_text, encoding="utf-8")
...
except (ParityRecordFormatError, UnreasonedDeviationError, InvalidJudgmentError, FileNotFoundError) as exc:
    return refuse(exc)
```
Also coerce `raw.get("notes") or ""`.

### WR-02: parity_report's inconclusive and mixed prose states a cause it never reads, which D-07 has made false

**File:** `databasise/evidence/parity_report.py:543-554`, `:1097-1103`, `:1115-1128`, `:1376-1395`, `:1598-1611`, `:225-231`
**Issue:** D-07 (15-06) changed `run_comparison`. A partial, degraded or cyclic decomposed run is now written as `status="inconclusive"` with `decomposed_run_record` populated (`parity/run_comparison.py:611-618`). The renderer was not updated for this, and still asserts precondition causes it never reads:
- the all-inconclusive branch says `v1/.venv`, `v1/.parity_working_dir`, `v1/.parity_v2_store` and `v1/.env.parity` "are all absent" (1116-1127);
- the storage-audit branch says the audits hit `MissingParityEnvError` (1390-1394);
- the verdict says every arm "reports an environment-precondition refusal" (1601-1604);
- the mixed branch says each inconclusive record "stopped at a precondition" (1099-1101).

Meanwhile `_arm_degraded()` (225-231) inspects only `completed` records. Its "Degraded run — read the zero diffs" disclosure therefore cannot fire for a fresh run.

**Scenario:** The owner re-runs the arms with `--spend`, and hybrid, local and global degrade (as the committed 2026-09 runs did). The rendered PARITY-EVIDENCE.md then blames missing env files and preconditions that were present. This breaks D-16 ("render only states they read").
**Fix:** Derive the cause per record from `inconclusive_reason` and `decomposed_run_record`, and render it. Delete the fixed precondition text. In `_arm_degraded`, treat an `inconclusive` record whose `decomposed_run_record.degraded` is true as degraded.

### WR-03: Evidence CLIs write into the package directory by default, and a wheel install writes into site-packages

**File:** `databasise/evidence/f07_report.py:324-331`, `databasise/evidence/falsifier2.py:597-604`, `databasise/evidence/parity_report.py:1722-1727`
**Issue:** The phase boundary says the offline CLIs never "write outside their own store, by default". All three renderers overwrite a committed document beside `__file__` on every bare run, with no flag and no dry run. From a wheel (`databasise.evidence` ships), `python -m databasise.evidence.f07_report` rewrites `site-packages/databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md`. A root-owned install instead fails with a `PermissionError` traceback.

`f07_report.main()` is new in this phase, and it writes on a bare run while `parity_report` at least offers `--check-results`.
**Fix:** Make the bare run print to stdout only, and write only with an explicit `--write` (or refuse to write when `Path(__file__)` resolves under `site-packages`). Map `OSError` and the renderers' `ValueError`s through `databasise.cli.refuse`.

### WR-04: The evidence renderers' named refusals escape as tracebacks (D-03)

**File:** `databasise/evidence/f07_report.py:160-166`, `:324-331`; `databasise/evidence/falsifier2.py:333`, `:411-415`, `:597-604`
**Issue:** These modules gained argparse and an int `main()` this phase, so they are treated as D-03 CLIs. None of them calls `refuse`:
- `f07_report`: a registry part declaring `mutates_store` without a `_KNOWN_REASONS` entry raises a bare `ValueError` traceback. D-16 names this case: rendering from `probe_registry()` raises.
- `falsifier2`: a malformed `boundary_knobs` entry (`ValueError`) and the `KeyError` from CR-01 escape the same way.
**Fix:** Give each one a named refusal class (for example `UnreasonedMutableStoreError(ValueError)`) and wrap `main()` in `try: ... except (<named>, FileNotFoundError) as exc: return refuse(exc)`.

### WR-05: CODEBASE-MAP's new launch command uses an interpreter without the project's dependencies

**File:** `docs/gui/CODEBASE-MAP.md:431`
**Issue:** The line changed from `cd databasise && uv run python -m <module>` to "`uv run python -m <module>` from the repository root". The repository root has no `pyproject.toml` and no `.venv`, so uv runs outside any project.

Verified from the repo root: `uv run --offline python -c ...` resolves `~/.local/share/uv/python/cpython-3.13-.../python3.13` (uv warns "`--no-sync` has no effect when used outside of a project"), and `import pycozo` raises `ModuleNotFoundError`. A console author who follows the map gets an import failure from every CLI.
**Fix:** Use `uv run --project databasise python -m databasise.<module>` (or `databasise/.venv/bin/python -m databasise.<module>`) and state the `databasise.` prefix explicitly.

### WR-06: CODEBASE-MAP still lists f07_report as library-only after it became a file-writing CLI

**File:** `docs/gui/CODEBASE-MAP.md:451` (also `:202`)
**Issue:** This phase gave `evidence.f07_report` a `main()` and an `if __name__ == "__main__"` that overwrites `F-07-MUTABLE-STORE-DISPOSITION.md` (`f07_report.py:324-344`). The surfaces table still says "`evidence.f07_report` | Library only | Ignore", so an operator console wrapping CLIs would not know it writes a committed file. The same table line was edited this phase, but the f07 entry was not updated.
**Fix:** Change the row to "`evidence.f07_report` | CLI, overwrites a committed file, exit 0 | Ignore", and fix line 202 to match.

## Info

### IN-01: The codebase-memory-mcp admission evidence now describes a tool its adapter refuses

**File:** `databasise/parts_core/codebase_memory_mcp.py:145-152`, `:238-246`; `databasise/foreign/codebase_memory_mcp_adapter.py:97-100`, `:309-310`
**Issue:** `wall_clock_ceiling_basis` is measured on `index_repository` "through the adapter", and condition 6 cites calling `index_repository` "directly". `call_tool` now refuses `index_repository`, so the part cannot reproduce its own ceiling measurement or build an index. Every read tool depends on an index built outside the adapter. D-17 and LRAG-12 forbid rewording these strings, and D-19 keeps `mutates_store`, so this is a recorded limit rather than a defect.
**Fix:** Record the limit in ADMISSION-CODEBASE-MEMORY-MCP.md (the evidence strings stay unchanged).

### IN-02: The lazy `functools.cache` builders are not synchronised

**File:** `databasise/parts_core/declared_only.py:74-91`; `databasise/parts_core/codebase_memory_mcp.py:87-94`, `:309`
**Issue:** `functools.cache` does not lock. Two threads touching `CODEBASE_MEMORY_MCP_PART` for the first time at once can each build a `Part` (and hash the 293 MB binary twice). That breaks the "same object every time" property the comment says `test_admission.py` relies on.
**Fix:** Guard the builders with a module `threading.Lock`, or accept the race and note it.

### IN-03: The f07 verdict renders "()" when no part declares mutates_store, and its empty-table guard is unreachable

**File:** `databasise/evidence/f07_report.py:193-201`, `:266`
**Issue:** `all_rows` always includes `_CATALOGUED_NOT_BUILT`, so the `if not all_rows` refusal never fires. With zero live rows, the new `registered` string is empty, and the verdict reads "every registered mutable-store component this project has built () and ...".
**Fix:** Check `if not live_rows` (or render "none registered").

### IN-04: The import-boundary scan misses some dynamic forms, and relative imports can be false positives

**File:** `databasise/tools/check_import_boundary.py:104-113`, `:132-148`
**Issue:**
- `import importlib as il; il.import_module("lightrag")` is not detected, and neither is `importlib.import_module(name="lightrag")`;
- `ImportFrom.level` is ignored, so a legitimate `from .lightrag import x` inside `parts_core/` (a real subpackage) would be flagged as a v1 import.
**Fix:** Track `import importlib as X` aliases, read the `name=` keyword, and skip `ImportFrom` nodes with `level > 0`.

### IN-05: The adapter's exception handler converts interrupts into transport faults and has a dead branch

**File:** `databasise/foreign/codebase_memory_mcp_adapter.py:268-283`
**Issue:**
- `except BaseException` turns `KeyboardInterrupt`, `SystemExit` and an outer `CancelledError` into `CbmTransportError`;
- `except ForeignEngineUnavailableError: raise` is unreachable, because `_resolve_binary` runs before the `try`;
- `_unwrap` takes only the first leaf of an exception group, so a group of `[Cancelled, CbmToolCallError]` is reported as a transport fault.
**Fix:** Catch `Exception` and re-raise `BaseException` subclasses as they are. Search the group for a `CbmToolCallError` or `UntypedForeignItemError` leaf instead of taking `exceptions[0]`.

### IN-06: The `databasise.mcp` docstring contradicts how the SDK is actually imported

**File:** `databasise/mcp/__init__.py:7-13`
**Issue:** The docstring says every import is an absolute `from mcp.server.mcpserver import MCPServer`. `server.py:92-93` deliberately resolves the SDK through `import_sdk`, because the bare form self-shadows. The docstring's first lines were edited this phase, but this paragraph was not.
**Fix:** Say that the SDK resolves through `databasise.mcp._sdk.import_sdk`.

### IN-07: The normalised cbm records carry raw engine output and internal citations, and `derived_from` is stored twice

**File:** `databasise/foreign/codebase_memory_mcp_adapter.py:373-391`
**Issue:**
- each record keeps `raw` (engine file paths, project names), `tool_name`, and a `tier_reason` that cites "PARTS.md ## §X". None of these may reach a §18 consumer field. The part is unregistered today, so nothing leaks yet;
- `derived_from` now lives both inside the tagged `kind` payload and at the top level, two copies that can diverge.
**Fix:** Keep only the tagged payload copy. Before the part is ever wired, document that the seam must redact `raw`, `tool_name` and `tier_reason`.

### IN-08: The provenance check is skipped silently with exit 0 in a source checkout that lacks v1/

**File:** `databasise/tools/check_import_boundary.py:226-230`
**Issue:** The wheel heuristic `(repo_root / "v1").is_dir()` also fires in a source checkout where `v1/` is missing or renamed. The provenance check is then skipped with only a stderr note, and the exit code stays 0, even though every `upstream_ref` in that checkout fails to resolve.
**Fix:** Decide "installed" by `"site-packages" in package_root.parts`, and treat a missing `v1/` in a source tree as a provenance violation.

---

_Reviewed: 2026-10-21T23:51:57Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
