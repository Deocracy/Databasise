---
phase: 03-lightrag-query-side
reviewed: 2026-09-05T00:00:00Z
depth: standard
files_reviewed: 74
files_reviewed_list:
  - databasise/clients/base.py
  - databasise/clients/__init__.py
  - databasise/clients/openai_compat.py
  - databasise/evidence/DECLARED-DEVIATIONS.md
  - databasise/evidence/FALSIFIER-2-EVIDENCE.md
  - databasise/evidence/falsifier2.py
  - databasise/evidence/human_findings.json
  - databasise/evidence/PARITY-EVIDENCE.md
  - databasise/evidence/parity_report.py
  - databasise/evidence/parity_results/bypass-comparison.json
  - databasise/evidence/parity_results/bypass-storage-audit.json
  - databasise/evidence/parity_results/global-comparison.json
  - databasise/evidence/parity_results/global-storage-audit.json
  - databasise/evidence/parity_results/hybrid-comparison.json
  - databasise/evidence/parity_results/hybrid-storage-audit.json
  - databasise/evidence/parity_results/local-comparison.json
  - databasise/evidence/parity_results/local-storage-audit.json
  - databasise/evidence/parity_results/naive-comparison.json
  - databasise/evidence/parity_results/naive-storage-audit.json
  - databasise/evidence/wirings/w1-lightrag-query-side.json
  - databasise/evidence/wirings/w3-lightrag-half-decomposed.json
  - databasise/.gitignore
  - databasise/__init__.py
  - databasise/parity/build_corpus_fixture.py
  - databasise/parity/corpus.py
  - databasise/parity/import_index.py
  - databasise/parity/__init__.py
  - databasise/parity/run_arm.py
  - databasise/parity/run_comparison.py
  - databasise/parity/storage_audit.py
  - databasise/parity/v1_arm.py
  - databasise/parity/v1_driver_script.py
  - databasise/parts_core/declared_only.py
  - databasise/parts_core/lightrag/assemble.py
  - databasise/parts_core/lightrag/chunk_sel_kg.py
  - databasise/parts_core/lightrag/chunk_vector.py
  - databasise/parts_core/lightrag/embedder_index.py
  - databasise/parts_core/lightrag/embedder_query.py
  - databasise/parts_core/lightrag/entity_hydrate_expand.py
  - databasise/parts_core/lightrag/entity_lookup.py
  - databasise/parts_core/lightrag/generate.py
  - databasise/parts_core/lightrag/heading_backfill.py
  - databasise/parts_core/lightrag/__init__.py
  - databasise/parts_core/lightrag/join_roundrobin.py
  - databasise/parts_core/lightrag/keywords.py
  - databasise/parts_core/lightrag/relation_hydrate_expand.py
  - databasise/parts_core/lightrag/relation_lookup.py
  - databasise/parts_core/lightrag/rerank.py
  - databasise/parts_core/lightrag/truncator_token_budget.py
  - databasise/parts/registry.py
  - databasise/parts/schema.py
  - databasise/pyproject.toml
  - databasise/runner/scheduler.py
  - databasise/stores/graph.py
  - databasise/stores/vector.py
  - databasise/tests/clients/__init__.py
  - databasise/tests/clients/test_capability_scoped_clients.py
  - databasise/tests/clients/test_openai_compat.py
  - databasise/tests/fixtures/corpus/MANIFEST.json
  - databasise/tests/fixtures/corpus/README.md
  - databasise/tests/parity/conftest.py
  - databasise/tests/parity/__init__.py
  - databasise/tests/parity/test_arm_conformance.py
  - databasise/tests/parity/test_embedder_index_reproduction.py
  - databasise/tests/parity/test_import_verification.py
  - databasise/tests/parity/test_keyword_variance.py
  - databasise/tests/parity/test_naive_arm_end_to_end.py
  - databasise/tests/parity/test_parity_evidence.py
  - databasise/tests/parity/test_retrieval_parity.py
  - databasise/tests/parity/test_storage_audit.py
  - databasise/tests/parts_core/lightrag/test_graph_half_parts.py
  - databasise/tests/parts_core/lightrag/test_naive_arm_parts.py
  - databasise/tests/parts_core/lightrag/test_transform_parts.py
  - databasise/tests/parts/test_registry.py
  - databasise/tests/runner/test_clients_threading.py
  - databasise/tests/runner/test_scheduler.py
  - databasise/tests/stores/test_graph_frozen_bugs.py
  - databasise/tests/stores/test_graph.py
  - databasise/tests/test_embed_startup.py
  - databasise/tests/test_import_boundary.py
  - databasise/tests/validator/test_falsifier2_evidence.py
  - databasise/tests/validator/test_falsifier2_probes.py
  - databasise/tools/check_import_boundary.py
  - databasise/wirings/__init__.py
  - databasise/wirings/lightrag/arm-bypass.json-patch.json
  - databasise/wirings/lightrag/arm-global.json-patch.json
  - databasise/wirings/lightrag/arm-hybrid.json-patch.json
  - databasise/wirings/lightrag/arm-local.json-patch.json
  - databasise/wirings/lightrag/arm-naive.json-patch.json
  - databasise/wirings/lightrag/base.json
  - databasise/wirings/lightrag/README.md
  - databasise/wirings/resolve.py
  - v1/README-PARITY.md
  - v1/scripts/run_parity_ingest.py
findings:
  critical: 1
  warning: 3
  info: 1
  total: 5
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-09-05
**Depth:** standard
**Files Reviewed:** 74 (non-source `.gitignore`/`.python-version`/lock/corpus-fixture paths cross-checked for secrets and malformed content, not reviewed as findings targets in their own right; `v1/.env.parity.example` could not be read — sandboxed out by the review environment's own permission settings, not a code defect)
**Status:** issues_found

## Summary

This is a re-review of the post-03-10 state at HEAD. The prior review's three findings
(CR-01 — `embedder-query` embedding an empty string; WR-01 — `_validated_token_allowance` not
refusing a negative value; IN-01 — the `_load_env_file` duplication) were re-verified directly
against the current source and all three hold up correctly: `keywords.py`'s `_keywords_body` now
emits `"query"` in both branches and `run_arm.py`'s `_inject_query` now stamps `keywords` too;
`scheduler.py`'s `_validated_token_allowance` now mirrors `_validated_max_concurrency`'s `< 0`
refusal exactly; both `_load_env_file` copies now carry cross-referencing docstrings naming their
deliberate absent-file asymmetry. None are re-listed below.

Plan 03-10 (parity evidence gap closure) and its own follow-up adversarial-audit fix cycle landed
after the prior review and were given full attention here, since they were not previously reviewed.
The renderer (`parity_report.py`) and its 41-test suite are unusually well hardened — the review
did not find a new defect in the eight fixed findings from that audit cycle, and the two gaps that
cycle explicitly left open (see WR-02/WR-03 below) are real and worth carrying into this report
since they were never before recorded in a `03-REVIEW.md`.

This pass also gave first-time review attention to `databasise/parts/schema.py` and
`databasise/parts/registry.py` (not in the prior review's file list) — both clean, no findings.

The one new Critical finding (CR-01 below) is a defect this review confirmed by direct code
reading, not merely repeated from the evidence documents: `entity-hydrate-expand.py`/
`relation-hydrate-expand.py` assume every seed item they consume carries a required key, with no
defensive path for a malformed/incomplete seed — the same class of gap the evidence documents
attribute to "diagnosis pending." Given the crash on `hybrid`/`local`/`global` is a real,
already-measured production defect (all three arms are stopped by a `NodeExecutionError` before
completing retrieval — see `PARITY-EVIDENCE.md`'s own Verdict section), it is recorded here as a
BLOCKER for the first time in a formal code review, with a concrete fix.

## Critical Issues

### CR-01: `entity-hydrate-expand`/`relation-hydrate-expand` crash the whole node on any seed item missing its expected key, instead of routing it to `missing_seeds` the way an absent graph node already is

**File:** `databasise/parts_core/lightrag/entity_hydrate_expand.py:44-52`, `databasise/parts_core/lightrag/relation_hydrate_expand.py:41-57`

**Issue:** Both bodies read a required field straight off each upstream seed item with a bare
subscript, before any validation:

```python
# entity_hydrate_expand.py
for seed in seeds:
    entity_name = str(seed["entity_name"])   # KeyError if absent
    node = await graph.get_node(entity_name)
    if node is None:
        missing.append({"entity_name": entity_name, "missing": True, "derived_from": [seed["id"]]})
        continue
```

```python
# relation_hydrate_expand.py
for seed in seeds:
    src_id = str(seed["src_id"])             # KeyError if absent
    tgt_id = str(seed["tgt_id"])              # KeyError if absent
    edge = await graph.get_edge(src_id, tgt_id)
    ...
```

Both modules' own docstrings state the house rule explicitly: "A seed whose node is absent from
the graph is reported in `missing_seeds` rather than silently dropped... this decomposition makes
that gap observable instead of silent." That rule is honored for a seed that *has* the expected
key but whose graph lookup misses — but a seed item that is missing the key itself (`entity_name`/
`src_id`/`tgt_id`/`id`) is not defended against at all: it raises a bare `KeyError`, which
`runner/scheduler.py`'s `_run_node` wraps into `NodeExecutionError` and which then halts the whole
batch (`scheduler.py`'s own documented "the whole scheduling loop" stop, confirmed in this same
review pass). This is precisely the failure class the already-committed evidence records: the
committed `parity_results/{hybrid,local,global}-comparison.json` all show
`decomposed_run_record.degraded=true` with a `stop_reason` naming `entity-hydrate-expand`/
`relation-hydrate-expand`, and `PARITY-EVIDENCE.md`'s own Verdict section states plainly that these
three arms "degraded before completing a real retrieval" on every query. `REQUIREMENTS.md`'s
MODAL-01 annotation and `03-UAT.md`'s G-03-1 entry both name this as a live, unrepaired defect —
but no `03-REVIEW.md` has recorded it as a classified finding with a concrete fix until now.

Cross-checked against the upstream producers during this review: `entity-lookup`/`relation-lookup`
(`databasise/parts_core/lightrag/entity_lookup.py`, `relation_lookup.py`) return whatever
`ctx.stores["vector"].query(...)` hands back, merged with each stored document's own imported
metadata (`FaissVectorStore.query`, `databasise/stores/vector.py:235`); that metadata is imported
verbatim from v1's own Faiss sidecar by `databasise/parity/import_index.py:186-188`, which strips
only `__id__`/`__vector__`/`__created_at__`. Nothing in that path re-validates that every record
still carries `entity_name` (or `src_id`/`tgt_id`) before it reaches `entity-hydrate-expand`/
`relation-hydrate-expand` — a v1-side record shaped even slightly differently than
`v1/lightrag/lightrag.py`'s `data_for_entities_vdb`/`data_for_rels_vdb` (e.g. an older or
partially-migrated v1 index snapshot) reaches this node's bare subscript and crashes the batch,
with no diagnostic naming which seed or which field was missing.

**Fix:** Mirror the existing "absent graph node -> `missing_seeds`" pattern for "malformed seed"
too, so a defect in the upstream data degrades this one item observably instead of halting the
entire node (and, per `scheduler.py`'s fail-fast batch semantics, every node still queued behind
it):

```python
for seed in seeds:
    entity_name = seed.get("entity_name")
    if not entity_name:
        missing.append({"entity_name": None, "missing": True, "derived_from": [seed.get("id")],
                         "malformed_seed": True})
        continue
    entity_name = str(entity_name)
    node = await graph.get_node(entity_name)
    ...
```

and the symmetric change for `relation_hydrate_expand.py`'s `src_id`/`tgt_id` read. This does not
fix the underlying root cause (why a seed is missing the field in the first place, which the 03-10
review-fix cycle correctly scoped as a separate, materially larger investigation) — it converts an
unhandled crash that halts the whole run into the same graceful, observable degradation this
module already gives a legitimately-absent graph node, which is enough to let the other seeds in
the same batch (and the nodes downstream of a *successful* hydrate-expand) keep running instead of
losing the entire arm to one bad record.

## Warnings

### WR-01: `run_arm._build_clients` reads four required `.env.parity` keys with bare subscript access, raising an unnamed `KeyError` instead of this module's own named refusal

**File:** `databasise/parity/run_arm.py:102-116`

**Issue:** `_build_clients` is the one caller `run_arm.run_arm`/`storage_audit.run_audit` both use
to construct real clients from the parsed `.env.parity` dict:

```python
def _build_clients(env: dict[str, str]) -> dict[str, Any]:
    llm = OpenAICompatibleClient(
        base_url=env["LLM_BINDING_HOST"],
        model=env["LLM_MODEL"],
        api_key=env["LLM_BINDING_API_KEY"],
    )
    embedding = OpenAICompatibleClient(
        base_url=env["EMBEDDING_BINDING_HOST"],
        model=env["EMBEDDING_MODEL"],
        api_key=env["EMBEDDING_BINDING_API_KEY"],
    )
    return {"llm": llm, "embedding": embedding}
```

This same module explicitly names `MissingParityEnvError` for the absent-file case, and its own
module docstring states the house style is "refusals over silent fallbacks." A `.env.parity` file
that exists but is missing (or misspells) one of these five keys — an easy mistake when hand-editing
the file per `v1/README-PARITY.md`'s recreate instructions — produces a bare, unnamed `KeyError:
'LLM_BINDING_HOST'` deep inside client construction, with no path back to which file or which key
was wrong. `storage_audit.run_audit` reuses this exact helper (`_run_arm._build_clients`), so the
gap reaches both callers.

**Fix:** Name the refusal the same way the absent-file case already is:

```python
_REQUIRED_ENV_KEYS = (
    "LLM_BINDING_HOST", "LLM_MODEL", "LLM_BINDING_API_KEY",
    "EMBEDDING_BINDING_HOST", "EMBEDDING_MODEL", "EMBEDDING_BINDING_API_KEY",
)

def _build_clients(env: dict[str, str]) -> dict[str, Any]:
    missing = [k for k in _REQUIRED_ENV_KEYS if k not in env]
    if missing:
        raise MissingParityEnvKeyError(missing)  # new, named error, mirroring MissingParityEnvError
    ...
```

### WR-02: `human_findings.json`'s two `declared_causes` entries are AI-authored, not human-authored, despite CONTRACT §5 requiring a human-authored cause for every named excursion

**File:** `databasise/evidence/human_findings.json:12-14,26-27`, `databasise/evidence/DECLARED-DEVIATIONS.md:9-10`

**Issue:** `parity_report.py`'s own module docstring states `human_findings.json` is "the one
committed, human-authored input this module reads" for CONTRACT §5's parity-not-gain record — the
mechanism exists specifically because a cause must be *human*-reasoned, not mechanically derived,
so an unverified excursion is never silently absorbed. Both of the file's two `declared_causes`
entries carry:

```json
"recorded_by": "Claude (AI agent, gsd-code-fixer) — commit 2ce3c30; NOT recorded by the human owner, despite this file's own name",
```

This is honestly disclosed (the 03-10 review-fix cycle's own finding 8 added this exact
provenance field for this exact reason), which is why this is a Warning rather than a Critical: the
gap is visible, not hidden. But the underlying gap is unresolved — CONTRACT §5's actual requirement
(a human traces and confirms the cause) is not met for either of the two currently-rendered
deviations, and nothing in the current pipeline (`check_results()`, `render_deviations_markdown()`)
distinguishes an AI-authored cause from a human-authored one when deciding whether a render is
"clean." A downstream reader of `PARITY-EVIDENCE.md`/`DECLARED-DEVIATIONS.md` who does not also
read `recorded_by` closely could reasonably believe the human owner has already verified these two
excursions are benign tail-length artifacts, when in fact no human has yet done so.

**Fix:** Either (a) have the human owner actually review and re-record these two causes (the fix
this file's own honesty is pointing at), or (b) add a `check_results()`/`render_deviations_markdown`
rule that refuses (or at minimum visibly flags in the rendered Verdict section) a
`recorded_by` value that does not look human-attributed, so "the render is clean" cannot be
mistaken for "a human has verified every named cause" while an AI-authored cause is still on file.

### WR-03: `check_results()` has no rule catching a `status="completed"` record whose `decomposed_run_record.degraded=true` alongside a vacuous (both-sides-empty) zero diff — such a record still passes the provenance check as clean

**File:** `databasise/evidence/parity_report.py:173-267`

**Issue:** `_REQUIRED_COMPARISON_KEYS` (line 173) and `check_results()`'s validation loop
(lines 226-254) check that a `completed` record carries its required provenance fields and that an
`inconclusive` record carries no comparison number — but neither checks
`decomposed_run_record.degraded`/`degradation_reason` at all. A `hybrid`/`local`/`global`-style
record — `status="completed"`, `entity_diff.symmetric_difference=[]`, but
`decomposed_run_record.degraded=true` because the run crashed before completing real retrieval —
satisfies every rule `check_results()` currently checks and prints `parity_results/ provenance
check: clean (5 arms)`. The "clean" claim is therefore true only in the narrow sense the function
actually checks (required keys present, no number alongside `inconclusive`); it does not mean "the
zero diffs recorded here are validated retrieval-level agreements," which is the reading a CLI
output literally named "clean" invites. This exact gap was surfaced and explicitly left unfixed by
the 03-10 review-fix cycle ("`check_results()` has no completed-direction rule... Noted, not
fixed.") — recorded here for the first time in a `03-REVIEW.md` rather than only in a plan
SUMMARY's own "explicitly left open" list, so it does not get lost when that SUMMARY is archived.

**Fix:** Add a rule to `check_results()`: a `completed` record whose `decomposed_run_record`
carries `degraded=true` and whose own comparison numbers are all-empty diffs should either be
excluded from "clean," or the CLI's success line should be qualified (e.g. "clean (5 arms, 3
degraded — see PARITY-EVIDENCE.md for disclosure)") so `--check-results`'s exit-0 output cannot be
read as "every arm's numbers are trustworthy" on its own.

## Info

### IN-01: `embedder_query._query_text`'s `or`-chain silently treats a genuinely empty query string the same as an absent key

**File:** `databasise/parts_core/lightrag/embedder_query.py:23-31`

**Issue:**

```python
def _query_text(ctx: NodeContext) -> str:
    keywords_output = ctx.inputs.get("keywords")
    if keywords_output is not None:
        if isinstance(keywords_output, dict):
            return str(keywords_output.get("query") or keywords_output.get("text") or "")
        return str(keywords_output)
    config = ctx.config or {}
    return str(config.get("query", ""))
```

`keywords_output.get("query") or keywords_output.get("text") or ""` treats a present-but-empty
`"query"` value identically to an absent one, falling through to `.get("text")` and then to `""`.
In practice `keywords.py`'s `_keywords_body` always stamps whatever `config["query"]` was (which
`run_arm._inject_query` always sets to the real user query text), so this is very unlikely to be
reached with a legitimately empty string today — a purely defensive, low-probability edge case, not
an observed defect.

**Fix:** `keywords_output.get("query") if keywords_output.get("query") is not None else
keywords_output.get("text", "")` if the distinction between "explicitly empty query" and "no query
key present" ever needs to be preserved; optional, given the low current likelihood of it mattering.

---

_Reviewed: 2026-09-05_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
