# Phase 16: GUI Connectors - Discussion Log

> **Audit trail only.** Do not use as input to planning, research or execution agents.
> Decisions are captured in 16-CONTEXT.md. This log keeps the alternatives that were considered.

**Date:** 2026-10-22
**Phase:** 16-gui-connectors
**Mode:** --auto, under owner delegation. A five-agent code study (four lanes and a critic) grounds each choice.

| Area | Question | Options | Selected |
|------|----------|---------|----------|
| Surface | OQ1a: where operator routes live | §18 app behind a flag; separate operator port | [auto] §18 app behind `--operator` (D-01). A separate port is a privileged client (§18.3) |
| Surface | OQ1b: MCP or REST-only | MCP tool plus COVERAGE row; REST-only | [auto] REST-only, deliberately-absent rows (D-03) |
| Surface | §18.2 for wiring-naming fields | refuse; operator exception | [auto] operator exception, debug=true precedent (D-02, owner may override) |
| Ledger | OQ2 (CONN-06): alias enumeration | relax no-enumeration; client-side log | [auto] relax it behind `--operator` (D-09) |
| Traces | OQ3 (CONN-07/08): trace tokens | return/list; keep client-side | [auto] return and list behind `--operator` (D-10) |
| Traces | OQ14: workspace filter | filter; one store_root = one workspace | [auto] one store_root = one workspace (D-11) |
| Ledger | OQ12 (CONN-09): HippoRAG preview | promotable; refused | resolved by LEDG-03: promotable (D-12) |
| Graph | OQ6 (CONN-12): attrs | raw attrs; references plus allowlist | [auto] references plus `edge_types`/`weight`, always present (D-16) |
| Graph | Unknown node status | 404; 422 | [auto] 422 (D-16). A 404 fails the protected status-code test |
| Graph | Busy graph status | 422 (text); 409 (D-02) | [auto] 409 (D-15) |
| Info | CONN-13: busy fields | /health; /info | [auto] /info (D-17) |
| Log | CONN-14 / OQ5: log access | flag-gated route; out of band | [auto] GET /log behind `--operator --log-file` (D-18); Phase 9 D-04 narrowed (D-19, owner may override) |

## Critic corrections to lane proposals
- **CONN-12:** keep 422. Moving it to 404 fails `test_refusal_status_codes.py` and the rest.py:116-123 rule.
- **Protected-file claims:** test_rest_transport.py, test_tool_growth_invariant.py, test_leak.py and test_store_refusal_status.py are not ledger test_refs.
- **CONN-01 citation:** the call ban is at test_rest_transport.py:202, not 182-201.
- **COVERAGE rows:** new operations go only in the deliberately-absent table. An operations-table row fails the growth test.
- **CONN-12 fields:** `edge_types` and `weight` must always be present, null when absent. A field that appears only for HippoRAG would break §18.3 invariance.

## Deferred Ideas
- **Graph:** a dereference route for graph entity text; out-of-process graph-busy detection.
- **MCP:** MCP operator tools.
- **trace.db:** a `created_at` index; a workspace column.
