# Phase 15: Offline Tooling & Packaging - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 15-CONTEXT.md. This log keeps the alternatives that were considered.

**Date:** 2026-10-21
**Phase:** 15-offline-tooling-packaging
**Mode:** --auto, under owner delegation. A five-agent code study (four lanes and a critic) grounds each choice.

| Area | Question | Options | Selected |
|------|----------|---------|----------|
| Packaging | TOOL-01 | ship package data; source-checkout-only | [auto] ship package data. The parity CLIs cannot be excluded because the launcher imports them (D-01) |
| CLI | SC2 spend default | TOOL-05's two CLIs only; every offline CLI | [auto] every offline CLI (D-04) |
| CLI | M-04 | re-import `.corpus_working_dir`; the sync node | [auto] the sync node, already decided in Phase 11 (D-05) |
| CLI | M-01 | literal default plus print; launcher derives it; marker file | [auto] literal default plus print, plus an equality test (D-05) |
| Parity | G-27 | answer from aquery_data context; call aquery unchanged | [auto] one `aquery_llm` call; `no_results` is a legitimate empty retrieval (D-08) |
| Parity | IN-01 | keep; reverse | [auto] reverse, in `v1_arm` only (D-08) |
| Parity | M-08 | name arms by wiring id; keep the selectors and check them | [auto] keep the selectors and check each against the named wiring before spend (D-10) |
| Eval | G-34 | eval ingest may touch the live corpus; never | [auto] never (D-12) |
| Eval | G-19 | floors location and key; lifting the gate | [auto] `floors.db` keyed on the traces' `wiring_instance_hash`; lift in two stages; no new refusal class (D-13) |
| Eval | EV-02 | accept AI causes with recorded_by; refuse them | [auto] accept them, shown with recorded_by (D-15) |
| Eval | MODAL-05 | discharged; unproven | [auto] discharged 2026-09-10, with a note on the Phase 12 change (D-16) |
| Registry | D5 / TOOL-17 | wire the artifact registry; delete it | already deleted in Phase 10 (D-20) |
| Registry | TOOL-18 | keep registered; keep unregistered; drop mutates_store | [auto] keep unregistered and keep `mutates_store` (D-19) |
| MCP | TOOL-19 | keep `args` plus a generic schema; per-tool schemas | [auto] keep `args` plus a generic schema, and add descriptions (D-18) |

## Critic corrections to lane proposals
- TOOL-15: render F-07 from `default_registry()`; rendering from `probe_registry()` raises ValueError.
- TOOL-16: refuse shared scope on `kind` only; refusing on `structural_depth` breaks `test_blast_radius`.
- TOOL-07: a v1 `no_results` is not exit 1.
- TOOL-12: as written, the requirement's test passes trivially, so it is restated so that it can fail first.

## Deferred Ideas
- A project license; per-tool MCP schemas; cross-store floor reads; a production part that reports `cache_hit`.
