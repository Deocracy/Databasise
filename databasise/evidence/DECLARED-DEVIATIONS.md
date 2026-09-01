# Declared Deviations

CONTRACT §5's parity-not-gain record: every excursion outside the stated retrieval-level tolerance (zero, per 03-09-PLAN.md's own flagged planner assumption — see `PARITY-EVIDENCE.md`), named individually with its own cause. A blanket or catch-all cause makes this document's own renderer refuse to render rather than silently absorbing the excursion into an unnamed category.

## Zero declared deviations

No excursion is recorded in this document. This is a stated zero, not an absent file — and, as of this render, it reflects that **no completed comparison run has occurred**: every arm's committed result under `parity_results/` carries `status="inconclusive"` (the index-identity precondition and/or the `v1/.env.parity` precondition failed on this machine — see `PARITY-EVIDENCE.md`'s "What was compared" section). A stated zero here should therefore be read as "nothing has been measured yet," not as "the comparison ran and found no excursions." Re-running `parity_report.py` after a real comparison lands will populate this section with either named entries or an updated zero statement that reflects an actual completed comparison.
