# Declared Deviations

CONTRACT §5's parity-not-gain record: every excursion outside the stated retrieval-level tolerance (zero, per 03-09-PLAN.md's own flagged planner assumption — see `PARITY-EVIDENCE.md`), named individually with its own cause. A blanket or catch-all cause makes this document's own renderer refuse to render rather than silently absorbing the excursion into an unnamed category.

## Zero declared deviations

No excursion is recorded in this document. This is a stated zero, not an absent file — and, as of this render, it reflects that **no completed comparison run has occurred**: every arm's committed result under `parity_results/` carries `status="inconclusive"` (the index-identity precondition and/or the `v1/.env.parity` precondition failed on this machine — see `PARITY-EVIDENCE.md`'s "What was compared" section). A stated zero here should therefore be read as "nothing has been measured yet," not as "the comparison ran and found no excursions." Re-running `parity_report.py` after a real comparison lands will populate this section with either named entries or an updated zero statement that reflects an actual completed comparison.

## Known design deviation (pending measurement)

Not a measured excursion (`_collect_deviations()` only picks up a `symmetric_difference` on a `status="completed"` comparison record, and none exist yet — see the zero-deviations statement above); recorded here ahead of the automatic mechanism because it is already known from reading the code, per CR-01's `03-REVIEW.md` finding.

| arm | query | measured difference | cause |
|---|---|---|---|
| hybrid, local, global | n/a — design-level, not yet measured | v2's `entity-lookup`/`relation-lookup` embed one raw-query vector (`embedder-query`'s output for `ctx.inputs["keywords"]["query"]`) | v1 embeds two separate keyword-derived vectors instead: `", ".join(ll_keywords)` for entity lookup (`_get_node_data`) and `", ".join(hl_keywords)` for relation lookup (`_get_edge_data`), per `v1/lightrag/operate.py`. The v2 wiring (`databasise/wirings/lightrag/base.json`, frozen input) feeds one shared `embedder-query` node into `entity-lookup`, `relation-lookup`, and `chunk-vector`, so this is a structural difference, not a bug — CR-01's fix makes `embedder-query` embed the real query text (closing the "empty string" bug) but does not restructure the wiring into v1's two-keyword-vector shape. Expected to surface as a retrieval-level `entity_diff`/`relation_diff` excursion once a completed comparison run exists (see `PARITY-EVIDENCE.md`), at which point the measured row above supersedes this entry. |
