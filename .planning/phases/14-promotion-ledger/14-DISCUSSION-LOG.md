# Phase 14: Promotion & Ledger - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 14-CONTEXT.md. This log preserves the alternatives considered.

**Date:** 2026-10-20
**Phase:** 14-promotion-ledger
**Mode:** --auto (the owner delegated grey-area decisions). Each choice is grounded in a five-agent code study: four lanes and a critic.

| Area | Question | Options | Selected |
|------|----------|---------|----------|
| Trace evidence | M-06: partial traces | (a) refuse for all three verbs; (b) refuse for promote, accept for rollback and retire | [auto] (b), using `arm_id` from Phase 13 (D-01) |
| Trace evidence | Refusal class | reuse UnknownTraceReferenceError; new class | [auto] new `PartialRunEvidenceError` (D-02) |
| Trace evidence | G-18: same rule for rollback and retire? | shared rule; promote only | [auto] promote only, keyed on `partial`, not `degraded` (D-03) |
| Gate verbs | G-19: refusal class | GateVerbNotBuiltError; UncalibratedFloorRefusalError up front; new class | [auto] new `GateNotCalibratedError` before any ledger access (D-04) |
| Aliases | M-07: HippoRAG aliases | (a) resolve every all_wirings() name; (b) refuse non-LightRAG promotion | [auto] (a) (D-05) |
| Aliases | G-17: retire guard | by version; by wiring identity | [auto] by version, through the rollback lineage (D-06) |
| Aliases | Bad aliases | new class; reuse InvalidPromotionAliasError | [auto] reuse (D-07) |
| Ledger | Connection lifecycle | skip schema when the file exists; always build the schema | [auto] `open_existing` returns None only when the file is absent; the schema migration is kept (D-08). The critic rejected skipping the schema. |
| Ledger | LEDG-07 shape | add id and created_at to LedgerRecord; a projection type | [auto] `LedgerEntry` projection, engine read only (D-09) |
| Tenancy | G-35 | per-workspace namespaces; one store_root = one tenant | [auto] one tenant per store_root, documented (D-10) |
| Tenancy | Operator-only debug | gate; no gate | [auto] no gate (no auth layer); StrictBool (D-10) |
| Selection | LEDG-10 effect set | wiring-node effects; Part effects over the pruned run | [auto] Part effects over the pruned run; already met at 3fd6e4c (D-11) |
| Registry | LEDG-12 | wire codebase-memory-mcp; unregister it | [auto] unregister, and move it to probe_registry (D-13) |

## Claude's Discretion
- Where the shared partial-evidence function lives and what it is called (D-03).
- The rollback-side tombstone lineage check (D-06): Success Criterion 3 covers it, though the LEDG-04 text does not.

## Deferred Ideas
- Per-workspace namespaces; an operator-only debug gate; a calibrated floor; codebase-memory-mcp as an arm.
