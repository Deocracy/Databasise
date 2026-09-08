---
last_mapped_commit: 8044f9a
---

# Codebase Concerns

**Analysis Date:** 2026-09-08

## Tech Debt

### Deprecated v1 Adapter Methods Still Exposed

**Area:** v1 LightRAG
- Issue: Three deprecated adapter methods remain in the public API and carry no deprecation warning
  - `insert_custom_chunks()` (async: `ainsert_custom_chunks()`) — marked `# TODO: deprecated, use insert instead`
  - `setup_logger()` — marked `# TODO: Deprecated, use setup_logger in utils.py instead`
  - `auto_manage_storages_states` config parameter — marked `# TODO: Deprecated (will never initialize storage automatically)`
- Files: `v1/lightrag/lightrag.py` (lines ~445, ~450, ~140)
- Impact: Callers may discover these are deprecated only through failed usage; no migration path is documented
- Fix approach: Add `@deprecated()` decorator with clear message pointing to the replacement, or remove if no known callers exist outside the repo

### Large Monolithic Files Limit Maintainability

**Area:** v1 LightRAG core modules
- Issue: Several files exceed 4000 lines, creating cognitive overhead and increasing change blast radius
  - `v1/lightrag/kg/postgres_impl.py` — 8396 lines (one backend implementation)
  - `v1/lightrag/operate.py` — 6001 lines (query orchestration)
  - `v1/lightrag/utils.py` — 5033 lines (general utilities)
  - `v1/lightrag/pipeline.py` — 4479 lines (async ingestion)
- Files: `v1/lightrag/{kg/postgres_impl.py, operate.py, utils.py, pipeline.py}`
- Impact: Making changes requires reading/understanding large context; refactoring risk is high; testing individual functions requires setup of entire module state
- Fix approach: Extract utility submodules (e.g., tokenization, entity-formatting helpers out of utils.py; query-stage isolation in operate.py); decompose postgres_impl into schema-specific modules

### Global State in API Configuration (v1)

**Area:** v1 FastAPI initialization
- Issue: Module-level `_global_args`, `_initialized` globals in `v1/lightrag/api/config.py` create thread-safety concerns in multi-worker deployments
  - Initialization not atomic across Gunicorn/Uvicorn workers
  - No guard against partial/duplicate initialization in concurrent startup
- Files: `v1/lightrag/api/config.py` (lines ~798, ~840, ~858, ~864)
- Impact: On worker fork/spawn, initialization race is possible (one worker sees uninitialized config while another initializes); state is not worker-local
- Fix approach: Thread the config through dependency injection (FastAPI `Depends()`) instead of module-level globals; initialize once at app startup hook before workers receive requests

### Incomplete XML Parsing Safeguards

**Area:** v1 Document parsing
- Issue: `v1/lightrag/parser/docx/omml/ommlparser.py` imports deprecated `cElementTree` and does not participate in the defusedxml safety layer used elsewhere
  - Line 1: `from xml.etree.cElementTree import Element` (deprecated since Python 3.9)
  - Other DOCX parsing modules (`parse_document.py`, `drawing_image_extractor.py`, `numbering_resolver.py`) correctly use `defusedxml.ElementTree`
  - OMMLParser receives already-parsed Element objects (not raw XML), so XXE risk is indirect (inherited from calling code), but the inconsistency is fragile
- Files: `v1/lightrag/parser/docx/omml/ommlparser.py` (line 1); safe parsers at `v1/lightrag/parser/docx/{parse_document.py:305, drawing_image_extractor.py:20, numbering_resolver.py:8}`
- Impact: If calling code ever changes to pass raw DOCX XML directly to OMMLParser, XXE vulnerability becomes direct; cElementTree import will fail on Python 3.13+
- Fix approach: Import from `xml.etree.ElementTree` (modern) or `defusedxml.ElementTree` depending on upstream parsing context; add type hint `defusedxml.Element | xml.etree.ElementTree.Element` if both paths remain

---

## Known Bugs & Incomplete Fixes

### Databasise 2.0 — Parity Measurement Latent Completeness Gap

**Area:** Phase 03 — Parity Evidence
- Issue: The `_render_not_measured()` function uses a priority-chain branch (`if degraded_arms: ... elif excursion_arms: ... else:`) rather than a per-arm loop
  - Currently correct on the real data (all arms clean/excursion, no mixed degradation)
  - But would silently drop mention of excursion arms if a future re-run produced mixed degraded + non-degraded arms simultaneously
- Files: `databasise/evidence/parity_report.py` (lines 1228–1253)
- Trigger: A future run where one graph arm degrades while others show excursion
- Workaround: None (latent — would only surface if measurement conditions change)
- Fix approach: Mirror `_render_verdict()`'s per-arm loop: build one clause per arm keyed on that arm's own degradation state and join them; add synthetic regression test exercising mixed degraded+excursion case to prevent silent re-occurrence

### Databasise 2.0 — Stated Safety Margin Is Arithmetically Wrong

**Area:** Phase 03 — Vector Parity Tolerance
- Issue: `_VECTOR_TOLERANCE` comment states `"1e-4 is two orders of magnitude above the measured ~1e-5 noise ceiling"`
  - Actual ratio: `1e-4 / 1e-5 = 10` (one order of magnitude, not two)
  - Two orders of magnitude above `1e-5` would be `1e-3`
  - The true 10x margin is still defensible but the code misstates its own math
- Files: `databasise/parity/import_index.py` (line 289–290); same error in commit `45925d6` message
- Impact: Next person to consider tightening/loosening `_VECTOR_TOLERANCE` reasons from wrong numbers; confidence in the margin is misplaced
- Fix approach: Correct comment to say "one order of magnitude" or "10x"; if wider margin is needed, update `_VECTOR_TOLERANCE` value with explicit rationale

### Databasise 2.0 — Perturbation Test Doesn't Prove Strictness Improvement

**Area:** Phase 03 — Vector Import Verification
- Issue: `test_real_v1_build_perturbed_vector_is_caught_and_named()` perturbs by `+1.0` to a component of a unit-normalized vector
  - This shift is `> 1000 * _VECTOR_TOLERANCE` and would fail the old 2-decimal-rounding check as well
  - Test only proves the new mechanism catches obvious, gross differences, not the actual claimed improvement (catching subtler differences in the `0.005`–`0.0156` range that old rounding would miss)
- Files: `databasise/tests/parity/test_import_verification.py` (new test, not explicitly named in review)
- Impact: The specific claim that the new tolerance check is "strictly stronger" than the old rounding check is unproven; could both be equally coarse-grained
- Fix approach: Change perturbation to `5e-3` (above tolerance but within 2-decimal grid resolution), then assert (a) new check flags it, (b) old quantized comparison would not

### Databasise 2.0 — Graph Topology Assertion Never Checks Attributes

**Area:** Phase 03 — Parity Verification
- Issue: `verify_import()`'s `_v1_graph()` and `_v2_graph()` return only node-id sets and edge-endpoint-pair sets
  - Does not compare each node/edge's `attrs` payload (`description`, `weight`, `entity_type`, etc.)
  - An import that preserves every id and edge pair but corrupts an attribute would pass `verify_import` cleanly
- Files: `databasise/parity/import_index.py` (lines 365–462)
- Impact: "Verified import" claims less fidelity than readers expect; the exact attribute-corruption class (weight confusion, type mismatch) that Phase 03 fixed is invisible to this assertion
- Fix approach: If attribute-level fidelity matters, extend assertion to also compare `attrs` dict between v1 and v2; if intentional scope limitation, document it explicitly in module docstring

---

## Evidence Rendering & Validation Gaps

### Databasise 2.0 — Markdown Table Corruption on Special Characters

**Area:** Phase 02 — Falsifier 2 Evidence Renderer
- Issue: Evidence markdown tables have no escaping for `|` or newlines in wiring-derived strings
  - Functions `_render_node_table`, `_render_boundaries`, `_render_probe_table`, `_wiring_shape_summary` directly interpolate strings from wiring documents
  - A `|` in `component`, `between`, `rationale`, or `wiring_shape` silently splits the table row
- Files: `databasise/evidence/falsifier2.py` (lines 398–467)
- Trigger: Author adds a wiring with `component="a | b"` or rationale containing `|`
- Workaround: None in the evidence renderer (the three committed wirings happen not to contain these chars)
- Fix approach: Escape `|` → `\|` and normalize newlines to spaces in every interpolated cell before building table rows

### Databasise 2.0 — Uncaught KeyError on Malformed Boundary Knobs

**Area:** Phase 02 — Falsifier 2 Evidence Renderer
- Issue: `enumerate_boundaries()` reads `boundary_knobs` raw from wiring document with no validation
  - Direct indexing of `knob["between"]` and `knob["rationale"]` without fallback
  - A missing key crashes `render_markdown()` with bare `KeyError` instead of an actionable error message
- Files: `databasise/evidence/falsifier2.py` (lines 384–393)
- Trigger: Hand-edited wiring fixture with typo'd knob key
- Workaround: Validate wiring JSON manually before running render
- Fix approach: Validate knob shape upfront (pydantic or explicit checks) rather than relying on bare `KeyError` propagation

### Databasise 2.0 — Ledger Import Guard Misses One Import Shape

**Area:** Phase 02 — MACH-09 Measurement Posture Guard
- Issue: `_ledger_import_findings()` in `test_measurement_posture.py` only inspects `ast.ImportFrom.module` names
  - Misses the `from databasise import ledger` shape where `module="databasise"` (parent package)
  - Imported alias names are not checked for `ast.ImportFrom` nodes with parent-package `module`
- Files: `databasise/tests/runner/test_measurement_posture.py` (lines 69–91)
- Trigger: Future code using `from databasise import ledger; ledger.ledger.Ledger()` bypasses the structural pin with the test staying green
- Impact: The guard's claim ("this test keeps that statement true going forward") fails silently for this import shape
- Fix approach: When `module` is a prefix of `"databasise.ledger"` (e.g., `"databasise"`), also check imported alias names (e.g., `f"{module}.{alias.name}"` against `"databasise.ledger."` predicate)

### Databasise 2.0 — Promotion Verb Guard Incomplete

**Area:** Phase 02 — MACH-09 Structural Pin
- Issue: `_promotion_verb_findings()` only matches `ast.FunctionDef` and `ast.AsyncFunctionDef` nodes
  - Does not catch `promote = _internal_impl` (plain name binding, not a function definition)
- Files: `databasise/tests/runner/test_measurement_posture.py` (lines 94–107)
- Severity: Lower than ledger-import gap (requires deliberate evasion) but same class of structural pin brittleness
- Fix approach: Optionally scan top-level/class-level `ast.Assign` targets whose name matches `_PROMOTION_VERB_NAMES`

---

## Data Loss & Documentation Drift

### Lost Fact Layer — Incomplete Reconstruction

**Area:** Critical incident on developer machine (pre-Phase 1)
- Issue: A rogue LLM session deleted files and git repositories on the owner's Windows machine
  - **v1 engine survived** (414 Python files, intact)
  - **Fact layer lost with no recovery:** `version_routes.py`, `sourcerer.py`, resolver, wiki routes (`/wiki/resolve`, `/wiki/unresolved`, `/wiki/unplaced`, `/wiki/preview`)
  - The lost layer implemented time-travel (`as_of` queries), contradiction resolution, vocabulary management, document-level provenance tracking
- Files: None (deleted)
- Impact: Critical capabilities for time-travel queries, conflict resolution, and single source of truth are not in v1 or Phase 2–4 requirements; planning that assumes requirements are complete will silently drop these capabilities
- Workaround: Consult `.claude/skills/spike-findings-*/` in related repos (spikes survived the deletion)
- Fix approach: Before concluding a feature never existed, check spike artifacts; owner is rebuilding from damaged record and `.planning/` may be incomplete (see `RECOVERED-FACT-LAYER.md`)

### Stale Defaults in Documentation and Configuration

**Area:** Configuration drift across v1 and documentation
- Issue: Real defaults are **Cozo + Faiss**, set in `v1/lightrag/lightrag.py:275–284` and `v1/lightrag/api/config.py:64–68`
  - But at least six places in the tree contradict this:
    - `v1/env.example:817–820` — says Json/NetworkX/Nano (upstream defaults)
    - `v1/lightrag/tools/rebuild_vdb.py:584–586` — says Json/NetworkX
    - `v1/tests/setup/test_validate.py:31–34` — says Json/NetworkX
    - `v1/tests/kg/test_graph_storage.py:73` — says Json/NetworkX
    - `v1/docs/ProgramingWithCore.md:73` — says Json/NetworkX
    - `.claude/CLAUDE.md` (project instructions) — says "Cozo + Nano VectorDB, NetworkX is default replaced by Cozo"
  - Embedding path has same problem: code defaults to ollama/bge-m3, but `env.example:722–723` says openai/text-embedding-3-large
  - This propagated into `.planning/research/STACK.md:26` (recommends LanceDB on stale data), then into Phase 1 requirement EMBED-01
- Files: `v1/env.example`, `v1/lightrag/tools/rebuild_vdb.py`, `v1/tests/setup/test_validate.py`, `v1/tests/kg/test_graph_storage.py`, `v1/docs/ProgramingWithCore.md`, `.claude/CLAUDE.md`
- Impact: A run silently uses the wrong store or embedding space if docs are followed instead of code; Phase 3's parity measurement is invalid if the two sides differ
- Fix approach: Update all docs/configs to match code reality (Cozo + Faiss + ollama/bge-m3); or change code to match documented defaults. Verify a default in `lightrag.py`/`api/config.py` before trusting any doc statement

---

## Security Considerations

### LLM Cache May Persist Truncated Structured Output

**Area:** v1 OpenAI LLM integration
- Issue: When OpenAI raises `LengthFinishReasonError` (structured output truncated), partial JSON is returned from `message.content`
  - Current code does cache this truncated response
  - Later runs with higher token budget reuse the incomplete cached JSON instead of re-querying
- Files: `v1/lightrag/llm/openai.py` (lines 225–279; comment at line 225)
- Trigger: Any query with `response_format={"type": "json_object"}` that produces output longer than the token limit
- Impact: Broken/repaired JSON persists in the cache; subsequent queries against the same prompt get incomplete data marked as "cached"
- Fix approach: Do not cache responses with `finish_reason == "length"`; mark truncated completions specially or skip caching them entirely; add a regression test exercising structured output with a token-budget constraint

### Default JWT Secret Used When Auth Is Unconfigured

**Area:** v1 FastAPI authentication
- Issue: `DEFAULT_TOKEN_SECRET = "lightrag-jwt-default-secret-key!"` is used when `TOKEN_SECRET` is not explicitly set and `AUTH_ACCOUNTS` is empty
  - This is a well-known constant (visible in the repo)
  - Any attacker who knows this repo can forge JWT tokens for unauthenticated instances
- Files: `v1/lightrag/api/config.py` (line 58); auth handler at `v1/lightrag/api/auth.py` (lines 27–36)
- Severity: Medium (only affects unauthenticated deployments; if `AUTH_ACCOUNTS` is configured, rejection at line 164-165 forces a real secret)
- Workaround: Always set `TOKEN_SECRET` explicitly in production, even if `AUTH_ACCOUNTS` is empty
- Fix approach: Refuse to start the API if `TOKEN_SECRET` is the hardcoded default and the API is not in development mode; or generate a random secret on first startup and persist it

---

## Performance Concerns

### Redundant Wiring Parse/Registry Construction

**Area:** Databasise 2.0 — Evidence generation
- Issue: `render_markdown()` redundantly parses the same wiring JSON file multiple times
  - Each call to `render_markdown()` invokes `_parse(stem)` directly (line 487)
  - Also calls `evaluate_wiring(stem)` (line 488), which internally calls `_parse(stem)` again (line 302)
  - `enumerate_boundaries()` independently calls `load_wiring(evidence.stem)` a third time (line 384)
  - Each `_parse` reconstructs a `default_registry()` and re-parses JSON
- Files: `databasise/evidence/falsifier2.py` (lines 298–341, 384, 486–488)
- Impact: Purely a duplication/maintainability nit (performance negligible for current wiring sizes, result is deterministic); but makes the code harder to follow and changes become fragile
- Fix approach: Thread the single `(doc, parsed)` pair produced by `render_markdown`'s loop into `evaluate_wiring` and `enumerate_boundaries` instead of re-deriving

---

## Fragile Areas

### Incomplete Per-Node Annotation Support

**Area:** Databasise 2.0 — Wiring Author Experience
- Issue: With `WiringNode.extra="forbid"`, any node-level key outside the explicit schema (`component`/`kind`/`effects`/`config`/`deps`) is refused
  - Includes author documentation fields like `"notes"` or `"description"`
  - No supported channel for per-node comments other than repurposing `config` (semantically wrong)
- Files: `databasise/parts/schema.py` (line 132), `databasise/validator/parse.py` (lines 126–138)
- Impact: Wiring authors cannot self-document their nodes; `config` is co-opted for documentation instead of purpose
- Fix approach: Add an explicitly-allowed `"metadata"` or `"notes"` field to `WiringNode` schema if future phases want to support wiring documentation

### Databasise 2.0 — OMMLParser Misses Formatting Support

**Area:** v1 DOCX math parsing
- Issue: OMMLParser does not support `m:rPr` (run properties) and `m:scr` (script style)
  - Results in loss of character styling information in mathematical equations
- Files: `v1/lightrag/parser/docx/omml/ommlparser.py` (line 66, marked TODO)
- Impact: Subscripts, superscripts, and formatting are stripped from OMML math; rendered LaTeX loses structure
- Workaround: None (will require extending OMMLParser to handle these tags)
- Fix approach: Add handlers for `m:rPr` (extract font properties) and `m:scr` (map script types to LaTeX commands like `^\text{superscript}`, `_\text{subscript}`)

---

## Deferred / Not-in-Scope (correctly disclosed, not gaps)

- The Databasise alias registry is empty this phase by design (Phase 7 populates it).
- Unauthenticated REST surface in Databasise is disclosed and accepted (marked `transfer` disposition).
- MACH-11's event proof is limited to fixture parts (no `parts_core` part declares `mutates_store` yet) — correct correlation.
- EMBED-02's MCP half is deferred to a later phase; COVERAGE.md records this as an explicit `OPT-OUT`.

---

*Concerns audit: 2026-09-08*
*Commit: 8044f9a*
