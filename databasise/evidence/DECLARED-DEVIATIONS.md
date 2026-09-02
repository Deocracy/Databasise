# Declared Deviations

CONTRACT §5's parity-not-gain record: every excursion outside the stated retrieval-level tolerance (zero, per 03-09-PLAN.md's own flagged planner assumption — see `PARITY-EVIDENCE.md`), named individually with its own cause. A blanket or catch-all cause makes this document's own renderer refuse to render rather than silently absorbing the excursion into an unnamed category.

## Named deviations

| arm | query | measured difference | cause |
|---|---|---|---|
| naive | q1 | chunk_diff: symmetric_difference=['charles_craft-chunk-000', 'shirley_temple-chunk-000'] | v1's naive path retrieves up to chunk_top_k=20 candidate chunks via _get_vector_context (v1/lightrag/operate.py) and keeps chunks until token-budget truncation (process_chunks_unified) exhausts available_chunk_tokens, so these two tail chunks beyond rank 10 (ranks 11-12) survived because they still fit the budget on this small corpus; the decomposed chunk-vector node (databasise/parts_core/lightrag/chunk_vector.py) cuts strictly at top_k=10 and never retrieves past rank 10 at all — a tail-length difference in retrieval breadth, not a ranking divergence (ranking_agreement=1.000, first_disagreement_position=10). |
| naive | q2 | chunk_diff: symmetric_difference=['adam_collis-chunk-000', 'conrad_brooks-chunk-000', 'secretary_of_state_for_constitutional_affairs-chunk-000', 'village_accountant-chunk-000'] | v1's naive path retrieves up to chunk_top_k=20 candidate chunks via _get_vector_context (v1/lightrag/operate.py) and keeps chunks until token-budget truncation (process_chunks_unified) exhausts available_chunk_tokens, so these four tail chunks beyond rank 10 (ranks 11-14) survived because they still fit the budget on this small corpus; the decomposed chunk-vector node (databasise/parts_core/lightrag/chunk_vector.py) cuts strictly at top_k=10 and never retrieves past rank 10 at all — a tail-length difference in retrieval breadth, not a ranking divergence (ranking_agreement=1.000, first_disagreement_position=10). |

## Known design deviation (pending measurement)

Not a measured excursion (`_collect_deviations()` only picks up a `symmetric_difference` on a `status="completed"` comparison record); recorded here ahead of the automatic mechanism because it is already known from reading the code, per CR-01's `03-REVIEW.md` finding.

**Status, from the completed run**: `hybrid`/`local`/`global` all measured `entity_diff`/`relation_diff` `symmetric_difference=[]` on both corpus queries — the predicted excursion did not surface as a non-empty diff. That measurement is not dispositive, though: the same three arms' decomposed runs degraded before completing a real retrieval on both sides (see the per-arm degradation note in "Per-arm retrieval-level comparison" and the Verdict section) — the zero reflects both the decomposed and original arm retrieving nothing on this run, not a validated agreement over non-trivial entity/relation sets. The structural difference below is unrefuted, not confirmed absent; a clean run is needed to actually test it.

| arm | query | measured difference | cause |
|---|---|---|---|
| hybrid, local, global | n/a — design-level, not a measured excursion | v2's `entity-lookup`/`relation-lookup` embed one raw-query vector (`embedder-query`'s output for `ctx.inputs["keywords"]["query"]`) | v1 embeds two separate keyword-derived vectors instead: `", ".join(ll_keywords)` for entity lookup (`_get_node_data`) and `", ".join(hl_keywords)` for relation lookup (`_get_edge_data`), per `v1/lightrag/operate.py`. The v2 wiring (`databasise/wirings/lightrag/base.json`, frozen input) feeds one shared `embedder-query` node into `entity-lookup`, `relation-lookup`, and `chunk-vector`, so this is a structural difference, not a bug — CR-01's fix makes `embedder-query` embed the real query text (closing the "empty string" bug) but does not restructure the wiring into v1's two-keyword-vector shape. |
