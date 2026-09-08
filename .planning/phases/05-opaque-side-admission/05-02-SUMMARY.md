---
phase: 05-opaque-side-admission
plan: 02
subsystem: docs
tags: [evidence, mach-04, hard-03, falsifier-8, dr-04, admission]

# Dependency graph
requires:
  - phase: 04-the-seam
    provides: "FA-03 (EvidenceRef's real field set) — the prior finding this plan's DR-04 decision restates rather than re-derives"
provides:
  - "databasise/evidence/INJECTED-LLM-ENDPOINT-SURVEY.md — MACH-04's Falsifier 8 documentation pass, adjudicated against five sandbox-candidate engines"
  - "databasise/evidence/DR-04-DECISION.md — HARD-03 closed with a named, dated selection and an honest per-covering account"
  - "databasise/tests/evidence/ — structural assertions over both evidence documents"
affects: [05-06, 05-07]

# Actuals (#2632)
actuals:
  tokens: 6300
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "House evidence-document format (dated header, claim-under-test quoted verbatim, findings table with evidence-class tags, verdict, method/limits) reused from FALSIFIER-2-EVIDENCE.md for a second, unrelated evidence document"
    - "Structural markdown-table parsing in tests (header/separator/rows) rather than whole-file grep, so a later edit that empties a row fails the specific assertion it should"

key-files:
  created:
    - databasise/evidence/INJECTED-LLM-ENDPOINT-SURVEY.md
    - databasise/evidence/DR-04-DECISION.md
    - databasise/tests/evidence/__init__.py
    - databasise/tests/evidence/test_admission_docs.py

key-decisions:
  - "MACH-04's five-engine list adopted as recommended (05-RESEARCH.md Assumption A2): codebase-memory-mcp (CA-2), postgres-mcp (MC-1), supabase-mcp (MC-2), code-graph-rag (CA-1), a foreign-hosted LightRAG server — stated as an adopted default, not a sourced list, per the plan's own OPEN DECISION 1 disposition."
  - "DR-04/HARD-03 selected two-covering-rationale (05-RESEARCH.md Assumption A3's starting position), but recorded selection_is_clean: false — covering 1's §7 partial-coverage refusal (D8) has no implementation anywhere in this codebase (grep confirms zero matches), and covering 2 (EvidenceRef) is missing all four ChunkRef members (corpus_id, recipe@version, ordinal, content_hash) per Phase 4's FA-03 finding. A clean-yes selection would have been the exact rounding-up this phase's own admission discipline forbids."
  - "code-graph-rag's (CA-1) endpoint-injection acceptance is recorded [inference], not a verified yes — CATALOG.md's own code-verified analysis confirms it calls an LLM, but no clone of code-graph-rag's own client construction was read this session to confirm base_url injectability."

patterns-established:
  - "An evidence document's findings-table evidence-class column must carry one of [code-verified]/[docs-verified]/[inference] per row, asserted per-row by the test rather than by a whole-file grep — prevents an unread engine from being silently rounded up to a verified yes."

requirements-completed: [MACH-04, HARD-03]

coverage:
  - id: D1
    description: "MACH-04's injected-LLM-endpoint survey names exactly five engines with per-row evidence classes and adjudicates Falsifier 8 without overstating"
    requirement: "MACH-04"
    verification:
      - kind: unit
        ref: "tests/evidence/test_admission_docs.py::test_survey_names_five_engines"
        status: pass
      - kind: unit
        ref: "tests/evidence/test_admission_docs.py::test_survey_findings_table_each_row_carries_an_evidence_class_tag"
        status: pass
      - kind: unit
        ref: "tests/evidence/test_admission_docs.py::test_survey_states_list_provenance"
        status: pass
      - kind: unit
        ref: "tests/evidence/test_admission_docs.py::test_survey_states_the_claim_under_test_verbatim"
        status: pass
    human_judgment: true
    rationale: "The plan's own <verification> block asks the owner to read the five-engine list — an adopted default, not a sourced list — and correct any engine that does not belong before it is treated as final."
  - id: D2
    description: "HARD-03's DR-04 row carries one named, dated selection between its two options, with both coverings checked against live code and the record stating which falls short and by what"
    requirement: "HARD-03"
    verification:
      - kind: unit
        ref: "tests/evidence/test_admission_docs.py::test_dr04_selects_one_named_option"
        status: pass
      - kind: unit
        ref: "tests/evidence/test_admission_docs.py::test_dr04_checks_both_coverings"
        status: pass
    human_judgment: true
    rationale: "The plan's own <verification> block asks the phase's named owner to confirm the selected option — its own words: 'the phase's one real policy decision.'"

duration: 16min
completed: 2026-09-08
status: complete
---

# Phase 5 Plan 2: Opaque-side admission — Falsifier 8 survey and DR-04 decision Summary

**MACH-04's Falsifier 8 survey adjudicates five sandbox-candidate engines (three vacuous, one confirmed injectable by code, one left genuinely unresolved) and HARD-03's DR-04 row is closed on `two-covering-rationale` with an honest, non-clean disclosure that both named coverings fall short of the model text as built.**

## Performance

- **Duration:** ~16 min
- **Started:** 2026-09-08T21:56Z
- **Completed:** 2026-09-08T22:12Z
- **Tasks:** 2 completed
- **Files:** 4 created, 0 modified

## Accomplishments

- `databasise/evidence/INJECTED-LLM-ENDPOINT-SURVEY.md`: adjudicates Falsifier 8's "engines accept an injected LLM endpoint in the common case" claim against `codebase-memory-mcp` (CA-2), `postgres-mcp` (MC-1), `supabase-mcp` (MC-2), `code-graph-rag` (CA-1), and a foreign-hosted LightRAG server — three vacuous (no LLM to inject into), one confirmed by code (`v1/lightrag/llm/openai.py`'s `base_url`/`api_key` params, already exercised by Phase 3's parity harness), one recorded `[inference]` rather than rounded up (code-graph-rag's own client construction was not read this session).
- `databasise/evidence/DR-04-DECISION.md`: checks both of DR-04's named coverings against live code (`databasise/registry_artifact/index.py`'s `sa2_chunker`/`sa2_extraction`/`sa2_embedding` columns; `databasise/seam/evidence.py`'s real `EvidenceRef` field set) before selecting — closes HARD-03 on `two-covering-rationale` with `selection_is_clean: false`, naming exactly which covering falls short and by what.
- `databasise/tests/evidence/test_admission_docs.py`: eight structural assertions (parsed markdown table, parsed YAML front matter) so a later edit that empties a row or a front-matter field fails a test rather than passing unnoticed.

## Task Commits

Each task was committed atomically:

1. **Task 1: The injected-LLM-endpoint survey across five sandbox-candidate engines** - `95a939c` (docs)
2. **Task 2: DR-04 decided, with both coverings checked against live code** - `ed90929` (docs)

## Files Created/Modified

- `databasise/evidence/INJECTED-LLM-ENDPOINT-SURVEY.md` - MACH-04's Falsifier 8 documentation pass
- `databasise/evidence/DR-04-DECISION.md` - HARD-03's DR-04 decision, with YAML front matter (`defect_row`, `requirement`, `decided`, `selected_option`, `selection_is_clean`)
- `databasise/tests/evidence/__init__.py` - new test package
- `databasise/tests/evidence/test_admission_docs.py` - structural assertions over both documents

## Decisions Made

See `key-decisions` in frontmatter — two decisions: adopting the five-engine survey list as-is (05-RESEARCH.md A2) with its provenance stated in the document itself, and selecting `two-covering-rationale` for DR-04 while explicitly marking the selection not-clean because one covering's enforcement half is unimplemented and the other's field set is missing entirely.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Findings-table separator row needed spaces to satisfy the plan's own `grep -c '^| '` acceptance check**
- **Found during:** Task 1
- **Issue:** A standard compact markdown separator row (`|---|---|...|`) does not match `grep -c '^| '` (pipe immediately followed by dash, no space), so the plan's own literal acceptance-criteria command would have undercounted the findings table by one line.
- **Fix:** Wrote the separator row with spaces (`| --- | --- | ... |`), matching `^| ` and bringing the grep count to the expected 7 (header + separator + five rows).
- **Files modified:** `databasise/evidence/INJECTED-LLM-ENDPOINT-SURVEY.md`
- **Verification:** `grep -c '^| ' databasise/evidence/INJECTED-LLM-ENDPOINT-SURVEY.md` returns `7`.
- **Committed in:** `95a939c` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 3 — blocking, a formatting adjustment required for the plan's own literal acceptance check to pass).
**Impact on plan:** Cosmetic only — no content, evidence class, or verdict changed. No scope creep.

## Issues Encountered

None beyond the deviation documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both of the phase's two purely-documentation requirements (MACH-04, HARD-03) are closed. Neither gates the ladder; MACH-04 is `accepted-as-stated-risk` and HARD-03's own decision states no code change follows from the selected option.
- The plan's two `<human-check>` items (confirm the DR-04 selection; confirm or correct the five-engine survey list) are not executor-halted per `workflow.human_verify_mode: end-of-phase` (no `checkpoint:*` task exists in this plan) — they are harvested into UAT at end-of-phase per the standard flow.
- DR-04-DECISION.md's "What Falls Short" section names two concrete, currently-unowned gaps (covering 1's partial-coverage refusal has no implementation; covering 2/EvidenceRef is missing all four ChunkRef members) — no requirement in the current milestone assigns closing either, and this record is the reference point if one is raised later.
- No blockers for 05-03 through 05-07.

## Self-Check: PASSED

- FOUND: `databasise/evidence/INJECTED-LLM-ENDPOINT-SURVEY.md`
- FOUND: `databasise/evidence/DR-04-DECISION.md`
- FOUND: `databasise/tests/evidence/__init__.py`
- FOUND: `databasise/tests/evidence/test_admission_docs.py`
- FOUND commit: `95a939c`
- FOUND commit: `ed90929`
- Re-ran all `<acceptance_criteria>` from both tasks: all pass (findings-table row count, engine strings, CATALOG ids, per-row evidence-class tags, provenance-section naming A2, DR-04 front-matter parse, sa2_/EvidenceRef identifiers, `FA-03` string, `git show` clean of `docs/system-model/`).
- Re-ran plan-level `<verification>`: `cd databasise && uv run pytest -q` — 617 passed.

---
*Phase: 05-opaque-side-admission*
*Completed: 2026-09-08*
