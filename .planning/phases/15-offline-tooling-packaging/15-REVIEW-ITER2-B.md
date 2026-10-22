---
phase: 15-offline-tooling-packaging
lane: B
iteration: 2
reviewed: 2026-10-21T00:00:00Z
depth: deep
scope: fix commits 0869ea4 11eeba8 9c4f337 2e0fe3e 1e1b196 1a2e13b c0cb857 d00e8ec (after 27b81c2)
files_reviewed: 8
files_reviewed_list:
  - databasise/eval/aa_run.py
  - databasise/seam/floors_store.py
  - databasise/eval/bundle.py
  - databasise/eval/remint.py
  - databasise/cli.py
  - databasise/seam/engine.py
  - databasise/eval/calibration.py
  - docs/gui/API-INVENTORY.md
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 15: Code Review Iteration 2, Lane B

**Reviewed:** 2026-10-21
**Depth:** deep. The fix diffs were traced into `seam/engine.py` (promote, `_refuse_gate_verb`), `seam/rest.py` and `mcp/server.py` (error mapping), `eval/calibration.py` (`_verify_cache_bypassed`), and `stores/probes.py` (`list_kv_prefix`, the pattern B-WR-02 copies).
**Status:** issues_found

## Summary

All eight lane-B findings were reworked. Five are fully fixed. Three of the fixes have a new or remaining defect: the B-CR-01 parser refuses a valid PARTIAL reply, the B-WR-02 read path now lets raw sqlite errors out of `promote`, and the B-WR-07 sealed-partition rule is only enforced within one content hash. No fix breaks D-03 or D-04: every new refusal class is in `cli.offline_refusals` or aa_run's `_refusals()` and exits 1, and every new check sits on the `--spend` path. No fix contradicts D-13 or D-14 either. B-WR-05 was outside this lane's fix list. It is closed by lane A's A-WR-01: `VectorStoreCorruptedError` is at `cli.py:72`.

| Finding | Verdict | Evidence |
|---|---|---|
| B-CR-01 | Fixed, with a new defect (WR-01) | `aa_run.py:136-137, 373-376`. "not correct", "Partially correct" and an echoed option list are now refused. Confirmed by running the regex. |
| B-WR-01 | Fixed | `aa_run.py:750`. `dict.fromkeys` removes duplicates, so the run matches `estimate_calls`. |
| B-WR-02 | Fixed, with a new defect (WR-02) | `floors_store.py:69-83`. Reads open `immutable` unless both side files exist, so they create no `-shm` or `-wal`. Only "no such table" reads as no floor (`:92-95`, `:108-111`). |
| B-WR-03 | Fixed | `aa_run.py:794-804`. The result prints before persisting. `floors_store.py:54-67`: one `with conn:` transaction around `executemany`. `aa_run.py:719-724`: `FloorPersistError` is in `_refusals()` (`:677`). |
| B-WR-04 | Fixed | `aa_run.py:479-486`. The check runs per question, before scoring and before the judge call. `:552, :562` reuse the same refusal text with the correct `run_a`/`run_b` label. The per-node check (`calibration.py:236-249`) is equivalent per question. |
| B-WR-06 | Fixed | `bundle.py:534-546` and `cli.py:77`. |
| B-WR-07 | Partly fixed (WR-03) | `bundle.py:586-587` and `remint.py:171-172` close the same-content-hash paths. A changed non-question input re-seals the opened questions. |
| B-WR-08 | Fixed | Spot-checked against `corpus_ingest.py:68-76`, `mcp/server.py:120-128` and `cli.py:65-84`. The rewritten rows match the code. |

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: The B-CR-01 parser refuses the committed prompt's own PARTIAL line and any explanation that uses "correct"

**File:** `databasise/eval/aa_run.py:137`, `databasise/eval/aa_run.py:375`
**Issue:** The fix refuses any reply in which more than one distinct verdict word appears anywhere (`len(set(_VERDICT_WORD.findall(text_upper))) != 1`). The committed judge prompt (`evidence/eval-bundles/judge-prompt-v1.txt`) defines PARTIAL as "the candidate answer is factually **correct** but incomplete". A judge that repeats its chosen option line, a common LLM habit, then gets these results (confirmed by running the regex):
- `"PARTIAL — the candidate answer is factually correct but incomplete relative to the gold answer."` is REFUSED, because it contains {PARTIAL, CORRECT}.
- `"INCORRECT — the candidate answer contradicts or omits ..."` parses.
- `"CORRECT — the candidate answer states the same fact(s) ..."` parses.
- `"INCORRECT. The candidate is not correct."` is REFUSED.

So the same reply format parses for two verdicts and is refused for the third. The docstring (`:362-366`) and API-INVENTORY :867 say that "a verdict followed by a dash or a sentence" parses, and this case contradicts them.

`UnparseableJudgeVerdictError` aborts the whole `answer_level` calibration (it is in `_refusals()`). One such reply therefore throws away every engine query and judge call already made in the run, and exits 1.

The result is a refusal, not a wrong score, which is why this is a Warning and not a Blocker. Note, however, that "CORRECT, not INCORRECT" is now refused by design. The fixer flagged that as needing a human check.
**Fix:** Count distinct verdicts only where they open a line. An echoed option list still has three line-leading verdicts and is refused. An explanation after the verdict no longer counts. Checked against all the cases above:
```python
_VERDICT_LINE = re.compile(r"(?m)^\W*(?:VERDICT\W*:\W*)?(CORRECT|PARTIAL|INCORRECT)\b")
match = _VERDICT_PATTERN.match(text_upper)
if match is None or len(set(_VERDICT_LINE.findall(text_upper))) != 1:
    raise UnparseableJudgeVerdictError(result.text)
```

### WR-02: Floor-store sqlite faults now escape `promote` as raw exceptions: REST returns a bare 500 and MCP returns an UnexpectedToolError

**File:** `databasise/seam/floors_store.py:80-81`, `:92-95`, `:108-111`; `databasise/seam/engine.py:2387`, `:2465`
**Issue:** B-WR-02 correctly stopped reading every `OperationalError` as "no floor". The errors now go straight out of `Databasise.promote`, though, and nothing on the seam maps them:
- REST registers handlers only for `SeamRefusalError`, `RequestValidationError` and `ValidationError` (`rest.py:366-368`). A `sqlite3.OperationalError` becomes Starlette's plain-text 500, with no §18 refusal envelope.
- MCP's `call_tool` (`server.py:120-128`) re-raises it as the SDK's opaque `"Error executing tool promote"`.

The new self-raised `sqlite3.OperationalError("floors.db-wal holds frames but floors.db-shm is missing")` at `floors_store.py:81` is called a refusal in the docstring. It is not a named class.

Failure scenario: an operator copies the eval store root while `aa_run` holds a connection, or a crash leaves `floors.db-wal` with frames but no `-shm`. From then on, every `POST /promote` with `promote-next` or `promote-now` returns an untyped 500. Before this fix, the same request returned the named `GateNotCalibratedError`.

The engine already has a pattern for store faults on read paths: `_foreign_fault(op, exc, failure_class="StoreFault")` at `engine.py:1833` and `:1891`. It is a `SeamRefusalError`, so it adds no refusal class, and D-13's "no new refusal class" holds.
**Fix:** Wrap both floor reads in `promote` and `_refuse_gate_verb`:
```python
try:
    has_floor = self._floors.any_floor()
except sqlite3.Error as exc:
    raise _foreign_fault("promote", exc, failure_class="StoreFault") from exc
```
Do the same around `self._floors.lookup(instance_hash)` at `:2387`.

### WR-03: The sealed-partition rule holds only within one content hash; any non-question change re-seals the opened questions

**File:** `databasise/eval/bundle.py:313-322`, `:450-455`, `:586-587`; `databasise/eval/remint.py:171-172`
**Issue:** `_assign_split` depends only on the question id (`bundle.py:313-322`). The content hash also covers `judge_instance`, `judge_prompt_hash`, `corpus_snapshot_hash` and the determinism/concurrency pair. If any of these changes, `mint_bundle` misses the dedup (`:450`) and mints a fresh version. That version's sealed split holds the same question ids that were already opened, and it has no `sealed_open` log entry, so `sealed_opened` is False.

Failure scenario:
1. `open_sealed(v2)` hands out the sealed ids and creates the opened copy v3.
2. The provider updates the judge model, so `resolve_judge_identity` returns a new `judge_instance`.
3. `remint --spend` mints v4, and the check at `remint.py:171` passes.
4. `open_sealed(v4)` passes the check at `:586` and returns the same already-seen questions as a fresh sealed read.

The fixer rejected "mint fresh" because it "would re-label opened questions as sealed", but this path still does exactly that. The refusal text ("change the question set to mint a sealed bundle") implies that only a question-set change can mint, which is wrong. RIG §EV.1 ("a touched partition is no longer sealed") is therefore still not enforced across versions, which was the substance of B-WR-07.
**Fix:** In `mint_bundle`, on the fresh-mint path only, collect the sealed question ids of every version whose `sealed_opened` is True. Refuse with `SealedPartitionOpenedError` before `_write_version` if the new sealed split overlaps them. This leaves the dedup return that `test_bundle_versioning.py` pins untouched.
```python
opened_sealed = {
    qid
    for n in _list_version_numbers(bundle_root)
    if (b := load_bundle(bundle_root, f"bundle@v{n}")).sealed_opened
    for qid in b.splits["sealed"].question_ids
}
if opened_sealed & set(splits["sealed"]):
    raise SealedPartitionOpenedError(...)
```

## Info

### IN-01: The CorruptUsageLogError message tells the operator to remove the line that may be the sealed_open entry

**File:** `databasise/eval/bundle.py:99-102`
**Issue:** The class docstring says a corrupt line is refused because "a skipped line could be the `sealed_open` entry". The message then says "repair or remove that line". Removing a truncated `sealed_open` line makes the version look unopened, which re-opens the B-WR-07 hole.
**Fix:** Say "repair that line (if it was a `sealed_open` entry, keep a `sealed_open` record)", and drop "or remove".

### IN-02: aa_run imports a private calibration helper

**File:** `databasise/eval/aa_run.py:89`, `:552`, `:562`
**Issue:** `_verify_cache_bypassed` is underscore-private in `eval/calibration.py`, but aa_run now depends on it.
**Fix:** Export it as a public name in `calibration.__all__`, or add a public `verify_cache_bypassed` alias.

### IN-03: The floors_store module docstring still names `record` as the only creator

**File:** `databasise/seam/floors_store.py:9`
**Issue:** The writer is now `record_many`, and `record` is a wrapper around it.
**Fix:** Change the docstring to name `record`/`record_many`.

---

_Reviewed: 2026-10-21_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
