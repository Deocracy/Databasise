---
phase: 12-hipporag-fixes
reviewed: 2026-10-19T00:00:00Z
depth: deep
diff_base: 26ca959^
iteration: 3
parts: "A (HippoRAG parts and wirings) + B (seam, stores, runner, foreign, mcp), merged; ids prefixed A-/B-. Iteration 3 re-reviews the three iteration-2 fix commits e85c3fc, f69256e, f886e2c (git diff edd4883..HEAD); the rest of the 59-file scope is unchanged since iteration 2."
files_reviewed: 59
files_reviewed_list:
  - databasise/evidence/HIPPORAG-PORT-RECORD.md
  - databasise/foreign/v1_corpus_adapter.py
  - databasise/mcp/server.py
  - databasise/mcp/tools.py
  - databasise/parts/registry.py
  - databasise/parts_core/hipporag/__init__.py
  - databasise/parts_core/hipporag/assemble_result.py
  - databasise/parts_core/hipporag/chunk_embed.py
  - databasise/parts_core/hipporag/document_remover.py
  - databasise/parts_core/hipporag/dpr_fallback.py
  - databasise/parts_core/hipporag/entity_fact_embed.py
  - databasise/parts_core/hipporag/fact_edges.py
  - databasise/parts_core/hipporag/fact_score.py
  - databasise/parts_core/hipporag/graph_augment_persist.py
  - databasise/parts_core/hipporag/openie.py
  - databasise/parts_core/hipporag/passage_edges.py
  - databasise/parts_core/hipporag/ppr.py
  - databasise/parts_core/hipporag/qa.py
  - databasise/parts_core/hipporag/reset_vector_join.py
  - databasise/parts_core/hipporag/synonymy_edges.py
  - databasise/runner/scheduler.py
  - databasise/runner/trace.py
  - databasise/seam/engine.py
  - databasise/seam/refusals.py
  - databasise/seam/rest.py
  - databasise/seam/selectors.py
  - databasise/seam/tokens.py
  - databasise/stores/probes.py
  - databasise/stores/vector.py
  - databasise/tests/evidence/test_hipporag_port_record.py
  - databasise/tests/foreign/test_secret_redaction.py
  - databasise/tests/parts/test_registry.py
  - databasise/tests/parts_core/hipporag/conftest.py
  - databasise/tests/parts_core/hipporag/test_assemble_result.py
  - databasise/tests/parts_core/hipporag/test_document_remover.py
  - databasise/tests/parts_core/hipporag/test_dpr_fallback_guard.py
  - databasise/tests/parts_core/hipporag/test_graph_construction.py
  - databasise/tests/parts_core/hipporag/test_index_side_extraction.py
  - databasise/tests/parts_core/hipporag/test_ppr.py
  - databasise/tests/parts_core/hipporag/test_qa_node.py
  - databasise/tests/parts_core/hipporag/test_registration.py
  - databasise/tests/parts_core/hipporag/test_thirteen_positions.py
  - databasise/tests/runner/test_degraded_on_guard.py
  - databasise/tests/runner/test_token_sum.py
  - databasise/tests/seam/test_compare.py
  - databasise/tests/seam/test_cross_modality_run.py
  - databasise/tests/seam/test_extraction_failed_refusal.py
  - databasise/tests/seam/test_foreign_engine_refusal.py
  - databasise/tests/seam/test_hipporag_corpus_surface.py
  - databasise/tests/seam/test_hipporag_query_path.py
  - databasise/tests/seam/test_hipporag_write_gate.py
  - databasise/tests/seam/test_hipporag_write_path.py
  - databasise/tests/stores/test_kv_readonly_listing.py
  - databasise/tests/stores/test_vector_self_knn_pending.py
  - databasise/tests/wirings/test_query_run_pruning.py
  - databasise/wirings/hipporag/base.json
  - databasise/wirings/hipporag/corpus-delete.json
  - databasise/wirings/hipporag/corpus-ingest.json
  - databasise/wirings/resolve.py
findings:
  critical: 0
  warning: 0
  info: 15
  total: 15
status: issues_found
---
# Phase 12: Code Review Report (iteration 3)

**Reviewed:** 2026-10-19
**Depth:** deep
**Files Reviewed:** 59 (the files touched by e85c3fc, f69256e and f886e2c re-read against `git diff edd4883..HEAD`; the rest unchanged since iteration 2)
**Status:** issues_found (Info only)

## Summary

Iteration 3 verifies the three iteration-2 fixes (A-WR-05, IN-06, B-IN-07) and looks for regressions. All three are resolved, and I found no Critical or Warning issue. Two new Info items concern the port record. The 13 other open Info findings are carried forward unchanged.

What I checked on the A-WR-05 change, which is the only logic change:

- **The new guard declaration.** `base.json` declares `empty_ppr_dpr_stand_in` in `assemble-result`'s `config.guards` (`evaluating_node: assemble-result`, `value_when_not_fired: false`, `granularity: per-query`). `_validated_guards` passes it through `declare_guard`, so the declaration is valid. `corpus-ingest.json` and `corpus-delete.json` have no `assemble-result`, so they are unaffected.
- **`_GuardAwareResult._flag`.** The class attribute defaults to `"guard_fired"`, so `fact-filter`'s `__eq__`, which compares a bool sentinel to `guard_fired`, behaves exactly as before. `_StandInResult._flag = "dpr_stand_in"` makes `evaluate_guards`'s `results["assemble-result"] != False` read `dpr_stand_in`. `__ne__` is `not __eq__`, so the `!=` in `runner/guards.py:evaluate_guards` is honoured.
- **Scheduler evaluation.** `evaluate_guards(guards_by_node[node_id], results)` runs per node, right after `results[node_id] = output`. So `fact-filter`'s guard is still evaluated against its own output, and the new guard against `assemble-result`'s. The two paths are mutually exclusive in the body: the stand-in is set only on the `not guard_fired` branch. So `degraded = partial or any(guards_fired)` yields `declared_fallback` / `fallback_path_taken` with `partial` false, and no run can report both guards.
- **Other consumers.** The output is still a `dict` (a subclass), so `qa`, the evidence mint and trace serialisation read `items` as before. `dpr_stand_in` is set only when the stand-in supplied at least one item.
- **Test run.** I re-ran the 25 tests in the two review-fix test files, and a keyword-selected subset of 359 tests (`hipporag or guard or degraded or wiring or cross_modality`), which includes the protected guard and degradation tests: 359 passed. The fix report records the full offline suite at 2203 in both styles. I did not repeat the full run.
- **Cross-modality parity.** `parity/run_cross_modality.py` refuses an arm where `degraded` is true (lines 339-347). So a HippoRAG arm that takes the stand-in path is now refused, which matches the port record's new sentence. `build_hipporag_index.py` builds only the index side, so it never reaches `assemble-result`.

B-IN-07: `list_kv_prefix` now reads the WAL size in a `try`/`except FileNotFoundError`; a vanished WAL counts as no frames. `live` re-reads existence afterwards, so the later open picks the immutable or `mode=ro` URI from the current state. A WAL that vanished means the writer checkpointed into the main file, so the immutable open sees every row. `PermissionError` and other `OSError`s still propagate to `StoreFault`. The new test patches `Path.stat` to remove the WAL and raise, and passes.

IN-06: the `synonymy_edges.py` docstring and the port record's D-05 entry now state the restore exception.

## Narrative Findings (AI reviewer)

## Info

### IN-01: The `qa` one-shot text sends `$$94` / `$$940.3`, while upstream renders `$94` / `$940.3`

**File:** `databasise/parts_core/hipporag/qa.py:30`
**Issue:** Upstream builds its chat template with `string.Template` and calls `.substitute()` (`prompt_template_manager.py:120-133` in the reference clone), so the `$$` in `rag_qa_musique.py` reaches the model as `$`. The port copies `$$` into a plain string. The docstring claims the one-shot pair is "kept verbatim", but the model sees different text from what upstream sends.
**Fix:** Use `$94 million` and `$940.3 million` in `_ONE_SHOT_DOCS`, or note the difference in the port record.

### IN-02: The DPR tests still put `chunk:`-prefixed ids into the `hipporag-chunks` vector namespace

**File:** `databasise/tests/parts_core/hipporag/test_dpr_fallback_guard.py:82,114,148`
**Issue:** D-01 limits the `chunk:` prefix to graph vertex names, and conftest was migrated to bare ids. These three tests still seed `chunk:c1` and similar ids into the chunk vector namespace. They pass, but they show an id form the real write path never produces.
**Fix:** Seed bare ids (`c1`, `c2`, `c3`) and update the expected id lists.

### IN-03: The "thirteen" wording is stale after the 14th node

**File:** `databasise/evidence/HIPPORAG-PORT-RECORD.md:1,38,40,42`; `databasise/tests/parts_core/hipporag/test_thirteen_positions.py:4-5`
**Issue:** The record's title and findings rows 2, 4 and 6 still say "all thirteen" or "every one of the thirteen", while the cited tests now cover 14 nodes. The test module docstring still says "a single 13-node base wiring".
**Fix:** Change these to "the thirteen governing positions plus the recorded `qa`".

### IN-04: The chunk-id preimage is ambiguous when a document id contains `:`

**File:** `databasise/parts_core/hipporag/chunk_embed.py:89`
**Issue:** `f"{document_id}:{ordinal}:{piece}"` gives the same preimage for (`"a:1"`, 0, `"x"`) and (`"a"`, 1, `"0:x"`). The seam's `_DOCUMENT_ID_TOKEN_RE` refuses `:`, so ingest through the engine is safe. The part itself accepts any id, though, for example from a parity build or a hand-built context.
**Fix:** Hash a length-prefixed or JSON-encoded tuple, for example `json.dumps([document_id, ordinal, piece])`. This changes the D-03 id values, so do it only together with a rebuild.

### IN-05: OpenIE's fallback semaphore and model-identity handling

**File:** `databasise/parts_core/hipporag/openie.py:202-204,213-215`
**Issue:** On a hand-built context, the fallback `asyncio.Semaphore(int(config.get("max_concurrency", 1)))` hangs forever on `0` and raises `ValueError` on a negative value. The scheduler validates the value, but this fallback does not. The node also reports the last non-None `resolved_model_identity` across all chunk calls without a check, while `entity_fact_embed.py:131-137` refuses on a per-call identity mismatch (the WR-02 precedent).
**Fix:** Use `max(1, int(...))` in the fallback, and apply the same identity-divergence refusal across the chunk results.

### IN-07: A single non-string entity or blank triple member now refuses the whole document

**File:** `databasise/parts_core/hipporag/openie.py:110-111,126-131`
**Issue:** After A-WR-03, one numeric item in `entities` (for example a bare year, which JSON-mode models do emit) or one blank member in one triple makes the chunk `unparseable_response`, and a chunk failure refuses the whole ingest. The port record's D-08 entry accepts this trade-off, and the behaviour now matches it. The consequence for real providers is a higher refusal rate than the tests show, because the tests use stub clients that never emit such items. I did not check whether `.planning/TESTING-PLAN.md` lists it.
**Fix:** No code change needed under D-08. Add the owner-run real-provider ingest check (rate of `unparseable_response` per corpus) to the testing plan if it is not there.

### IN-08: The port record states upstream behaviour for an all-zero PPR that was not checked against the reference

**File:** `databasise/evidence/HIPPORAG-PORT-RECORD.md` (D-20 entry, "upstream returns its PPR ranking even when every score is 0")
**Issue:** This sentence entered the record through the iteration-2 review's own A-WR-05 text, and neither the reviewer nor the fixer verified it. No upstream clone exists in this checkout (`find` for `HippoRAG.py` returns nothing), and the record's evidence-class convention marks every row `[code-verified]`. Upstream may instead raise or return a uniform ranking on an all-zero personalization vector, in which case the divergence is described wrongly.
**Fix:** Check `HippoRAG.run_ppr` in the reference clone, then either keep the sentence with its citation (file and line) or reword it to "this port substitutes dense retrieval; upstream behaviour on an all-zero reset vector was not checked".

### IN-09: The port record's guard sections still describe a single guard

**File:** `databasise/evidence/HIPPORAG-PORT-RECORD.md` ("The guard-placement divergence", about lines 83-102; "The guard-observability resolution", about lines 104-116)
**Issue:** After A-WR-05 the built `base.json` carries two per-query guards, `zero_surviving_facts_dpr_fallback` on `fact-filter` and `empty_ppr_dpr_stand_in` on `assemble-result`. The placement section says the built wiring carries "the guard" on `fact-filter`, and the observability section says "a fired guard" with no mention of the second one. The D-20 entry does describe the new guard correctly, so only the two dedicated sections are stale. Also, the fix report noted that the real-world frequency of the stand-in path is unmeasured (a one-chunk stub query still scored above 0), so the iteration-1 claim that a single-chunk corpus is always empty-PPR was wrong.
**Fix:** Add one sentence to each of the two sections naming the second guard and pointing to the D-20 entry.

### B-IN-01: Query pruning can drop the `evidence_position` node without any signal

**File:** `databasise/wirings/resolve.py:162-174`
**Issue:** The ancestor walk starts only from `provides`. If a wiring's `evidence_position.node` is not an ancestor of `provides`, it is pruned, and `_execute_resolved` then mints an empty evidence list without any refusal. Every shipped wiring satisfies this today; the rule is not enforced.
**Fix:** Seed `frontier` with `evidence_position["node"]` as well (and possibly `consumes_query` nodes), or have the validator refuse a wiring whose evidence node is not an ancestor of `provides`.

### B-IN-02: The MCP `status` selector is silently ignored for `job` and `health`

**File:** `databasise/mcp/tools.py:181-189`, `databasise/mcp/server.py:130-146`
**Issue:** The docstring says the selector "is read only for scope in {corpus, counts}", but `job` and `health` accept and discard it. A caller who sends `{"scope": "health", "selector": ...}` expecting a per-modality answer gets the workspace-wide answer. (Selector-scoped health is deferred.)
**Fix:** Refuse a selector for `job` and `health` (for example `MissingScopeArgumentError`'s sibling), or document the behaviour in the tool description.

### B-IN-03: `sum_token_accountings` merges counts labelled `"none"` under another label

**File:** `databasise/runner/trace.py:66-80`
**Issue:** `"none"` entries are excluded from the label set but their counts are still summed. An accounting that is labelled `"none"` but carries non-zero `prompt_tokens` or `call_count` (a client bug or stub) is reported under the other counter's label. That is the mixing HIPP-19 is meant to prevent.
**Fix:** Ignore `"none"` only when its counts are all zero. Otherwise treat it as a distinct label, which yields the sentinel.

### B-IN-04: The gate-ceiling test can hang for 900 s instead of failing

**File:** `databasise/tests/seam/test_hipporag_write_gate.py:76`
**Issue:** `monkeypatch.setattr(engine_module, "_HIPPORAG_GATE_WAIT_SECONDS", 0.1, raising=False)`. If the constant is renamed, the patch silently adds an unused attribute and the test waits the real 900 s ceiling.
**Fix:** Drop `raising=False`. The attribute exists now, and the test should fail loudly if it is renamed.

### B-IN-05: The runner imports the v1 adapter module for `redact_secrets`

**File:** `databasise/runner/scheduler.py:126`
**Issue:** The modality-agnostic scheduler now depends on `databasise.foreign.v1_corpus_adapter`, which holds the v1 subprocess driver, just to get a pure regex helper. Redaction is a cross-cutting utility, and this couples the runner layer to the LightRAG foreign adapter.
**Fix:** Move `_SECRET_PATTERNS` and `redact_secrets` to a neutral module (for example `databasise/identity/redact.py` or `databasise/_redact.py`) and re-export it from the adapter.

### B-IN-06: Redaction and node-id coverage gaps

**File:** `databasise/foreign/v1_corpus_adapter.py:60-66`; `databasise/seam/engine.py:2023`
**Issue:**
- `redact_secrets` does not mask `?access_token=`, `?token=` or a bare Google `AIza...` key outside a `key=` parameter. All three appear in provider SDK error strings.
- The query-path store fault calls `_foreign_fault` without `node_id`, so its log line reads `node=-`, while the ingest and delete paths name the node (D-09). The difference is minor but makes query faults harder to trace.

**Fix:**
- Add `(?i)([?&](?:access_)?token=)[^\s'\",&]+` and `\bAIza[0-9A-Za-z_-]{20,}`.
- Pass the failing node id at the `_foreign_fault("query", ...)` call (iterate `node_exceptions.items()`).

### B-IN-08: The strict replacement tests depend on private helpers of protected test modules, and the lax originals remain

**File:** `databasise/tests/seam/test_hipporag_review_fixes.py` (the helper imports from `seam.test_hipporag_write_path` and `seam.test_hipporag_query_path`, now also in `_hipporag_envelope` and the A-WR-05 test); `databasise/tests/seam/test_hipporag_write_path.py:310-316,394-399`; `databasise/tests/seam/test_hipporag_query_path.py:230-240`
**Issue:** This is the residual of B-WR-04. The new tests are strict and pass. They get their fixtures by importing underscore-named helpers (`_DOCUMENT_TEXT`, `_StubEmbeddingClient`, `_KeepAllFactsLLMClient`, `_refs_over_twenty_documents`, ...) from two ledger-protected test modules, which couples them to those modules' internals; a rename there breaks them at import time. Iteration 2 added two more such imports. The three lax assertions in the protected modules (`except Exception` then `assert not evidence`, and the `<= 5` / `all(score > 0)` pair that holds with zero refs) are unchanged and still pass on a regression. Tightening them in place needs the owner's `grant-check-edit`.
**Fix:** Move the shared stubs to a helper module that is not a test file, or accept the coupling and note it. Ask the owner for the grant to tighten the three originals.

## Resolved in iteration 1 fixes

All ten Critical/Warning findings of iteration 1 were verified resolved in iteration 2 (commits 26ca959, f4ef3ba, 27dd16d, 25ea962, e869d26, 76441a9, 0d42188, edd4883). Their evidence is in the iteration-2 review and is not repeated at length.

- **A-CR-01** (Critical): a re-ingest no longer deletes another document's synonymy edges. A scratch probe showed an exact edge-map round trip, and a changed re-ingest dropped only the removed entity's edge.
- **B-CR-01** (Critical): a HippoRAG delete no longer unlinks LightRAG's staged uploads.
- **A-WR-01**: `assemble-result` tolerates `config=None` and refuses `top_k < 1`.
- **A-WR-02**: an empty PPR branch no longer returns an empty answer; the dense items answer. Its observability residual (A-WR-05) is resolved below.
- **A-WR-03**: an OpenIE list with any invalid item is `unparseable_response`. Consequence noted as IN-07.
- **A-WR-04**: the unread `declared_capability` keys are removed, and the allowlist test fails on any unread key.
- **B-WR-01**: a bad or non-dict manifest row maps to `MalformedDriverOutput`, and store and OS errors map to `StoreFault`.
- **B-WR-02**: a WAL with frames and no `-shm` is refused instead of listed short.
- **B-WR-03**: a pre-Phase-12 HippoRAG trace shape promotes, and an unknown shape is a 404 refusal.
- **B-WR-04**: strict replacement tests exist and pass. The lax protected originals are carried as B-IN-08.

## Resolved in iteration 2 fixes

### A-WR-05 (was Warning): The dense stand-in on an empty PPR branch is invisible in the trace and absent from the port record. Resolved by e85c3fc.
The stand-in is now a declared degradation: `assemble-result` returns `_StandInResult` with `dpr_stand_in`, and `base.json` declares the per-query guard `empty_ppr_dpr_stand_in` on it. I verified the guard declaration validates, that `_flag` leaves `fact-filter`'s guard unchanged, that the scheduler evaluates each node's guards against its own output, that the two guards cannot both fire in one run, and that `qa` and evidence minting still read a plain `items` list. The test `test_an_empty_ppr_query_reads_degraded_with_the_node_free_reason` covers both the stand-in run and a clean PPR run, and passes. The port record's D-20 entry describes the guard and the cross-modality refusal accurately (checked against `parity/run_cross_modality.py:339-347` and the scheduler's D-21 block). The wiring `config_hash` changes again, which is expected and the same class as the A-WR-04 change. Two documentation leftovers are IN-08 and IN-09. The fix report leaves open whether the owner wants the guard name in the S4 trace records.

### IN-06 (was Info): Docstring and port record still say a synonymy pair is "never re-emitted". Resolved by f69256e.
Both the `synonymy_edges.py` docstring and the port record's D-05 entry now state the A-CR-01 restore as the one exception. The docstring line is longer than the surrounding wrap width (cosmetic).

### B-IN-07 (was Info): `list_kv_prefix` turns a benign WAL-removal race into a `StoreFault`. Resolved by f886e2c.
The WAL stat is guarded with `except FileNotFoundError`, and the new test simulates the vanishing WAL. The wider writer-closes-between-check-and-open race remains documented in the docstring.

---

_Reviewed: 2026-10-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
_Iteration: 3_
