# Run-trace schema deviations (D-12)

`docs/system-model/rig-trace.schema.json` and `docs/system-model/RIG.md` are frozen and stay verbatim.
Databasise run records validate against the derived schema `databasise/evidence/rig-trace.databasise.schema.json`,
which is the frozen file with the amendments listed below applied and nothing else. `RIG.md` §TR asks
that a divergence between the field table and the schema be recorded as a §R defect row; this file is
that record for the Databasise-local derivation. `databasise/tests/evidence/test_derived_trace_schema.py`
applies the same amendment list to the frozen file and compares the result with the derived file, so an
unrecorded edit to either file fails the test.

Columns follow `RIG.md` §R. The Clause cell names the JSON pointers the amendment touches. Status is
`recorded, no amendment`: the frozen files are not amended, the divergence is recorded here.

| # | Clause | Defect | Repair direction | Forcing requirement | ANATOMY re-projection | Status |
|---|--------|--------|------------------|---------------------|-----------------------|--------|
| D1 | `/$id`, `/title`, `/description` | The frozen file names itself the RIG-02 schema, so a derived copy would be mistaken for it | The derived file names itself the Databasise derived schema and points at this record | WIRE-11, D-12 | none (Databasise-local derived schema) | recorded, no amendment |
| D2 | `/$defs/NodeTrace/properties/cache_hit` | The frozen type is boolean, so a part that reports no cache flag has to be recorded as false, a value nothing measured | Type becomes boolean or null; null means the part reported nothing | WIRE-11, D-14 | none (Databasise-local derived schema) | recorded, no amendment |
| D3 | `/$defs/NodeTrace/properties/tier` | The frozen enum T0 to T3 forces a tier onto a node that handles no scored evidence item, which the tracer filled with a T3 placeholder | Type becomes string or null and null joins the enum; null means no evidence-tier machinery measured it | WIRE-11, D-14 | none (Databasise-local derived schema) | recorded, no amendment |
| D4 | `/$defs/NodeTrace/properties/feed_tier` | Same defect as tier for the tier a node's output feeds forward as | Type becomes string or null and null joins the enum | WIRE-11, D-14 | none (Databasise-local derived schema) | recorded, no amendment |
| D5 | `/$defs/NodeTrace/properties/status` | The frozen NodeTrace has no field that tells a completed node from a failed, cancelled or never-scheduled one, so a failed node is only inferable from budget_state halted | New property status with enum completed, failed, cancelled, not-scheduled | WIRE-10, D-14 | none (Databasise-local derived schema) | recorded, no amendment |
| D6 | `/$defs/NodeTrace/properties/execution_mode` | CONTRACT §3 derives a placement per node but the frozen NodeTrace cannot carry it, and additionalProperties false rejects the key | New property execution_mode with the four placements, stamped on the success and the refusal path | WIRE-11, D-14 | none (Databasise-local derived schema) | recorded, no amendment |
| D7 | `/$defs/NodeTrace/properties/spent` | realised_budget_share is capped at 1, so an overspending node is indistinguishable from one that spent exactly its allowance | New property spent, integer or null with minimum 0; the metered spend, null where the node never completed | WIRE-11, D-14 | none (Databasise-local derived schema) | recorded, no amendment |
| D8 | `/$defs/NodeTrace/properties/allowance` | Same defect as spent: the allowance the share was computed against is not on the record | New property allowance, integer or null with minimum 0 | WIRE-11, D-14 | none (Databasise-local derived schema) | recorded, no amendment |
| D9 | `/$defs/NodeTrace/required` | The four new properties would be optional, so a record could omit what was measured | The required list gains status, execution_mode, spent and allowance | WIRE-10, WIRE-11, D-14 | none (Databasise-local derived schema) | recorded, no amendment |
| D10 | `/properties/stop_reason` | The frozen type is any string, so a consumer-visible reason can carry a node id, a part name or an exception message | Enum of the six closed reason codes, or null | WIRE-03, D-05 | none (Databasise-local derived schema) | recorded, no amendment |
| D11 | `/properties/degradation_reason` | Same defect as stop_reason for the degradation reason | Enum of the same six closed reason codes, or null | WIRE-03, D-05 | none (Databasise-local derived schema) | recorded, no amendment |

The run-level `partial`/`degraded` required-together rule (`allOf`) and `realised_budget_share` with
maximum 1 are carried over unchanged.
