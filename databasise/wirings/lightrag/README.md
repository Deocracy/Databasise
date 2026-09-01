# LightRAG wirings — `databasise/wirings/lightrag/`

This directory holds the **registered** LightRAG query-side wiring set: the eighteen-position
base wiring plus the five arm patches published (as illustrative-only content) by
`docs/system-model/wirings/lightrag-*.json*`. These files are what `databasise/wirings/resolve.py`
actually loads and resolves; the `docs/system-model/` originals remain the frozen, never-governing
reference copy (PARTS.md preamble clause (b), CONTEXT D-04).

These files also supersede the never-written `.planning/architectures/wirings/` set that
PARTS.md §L.2's `Illustrative JSON:` field named as the eventual home for this content — that
specified-but-absent path is resolved here rather than left dangling.

## Provenance and edits

`base.json` and the five `arm-*.json-patch.json` files are copied **verbatim** from
`docs/system-model/wirings/` for every node, dep, config, recipe, harnesses, provides, operation,
and `resulting_node_id_set` field — the published set was already mechanically checked (03-RESEARCH.md),
and re-deriving it risks silently diverging from a verdict already run. Exactly three edits turn
the illustrative JSON into this registered set:

1. **Drop `status`/`status_note`, add `wiring_id`/`title` (base.json only).** The published files
   carry `"status": "illustrative-only-not-a-registered-wiring"` and an explanatory `status_note`
   — both dropped from every file here since they are no longer illustrative-only. `base.json`
   additionally gains `wiring_id: "lightrag-base"` and a `title`, in the shape
   `databasise/evidence/wirings/w1-lightrag-query-side.json` uses. The five arm patches are not
   wirings in their own right (they are RFC 6902 operation lists resolved against the base), so
   they gain no `wiring_id`/`title` of their own.
2. **Drop `artifact_scope` from the `embedder-index` node (base.json only).** `artifact_scope` is
   a member of `databasise/validator/parse.py`'s `_DERIVED_FIELD_NAMES` — a wiring that states it
   is refused with `CODE_SELF_DECLARED_DERIVATION`, since the value is sourced from the node's
   resolved `Part` in the registry, never from the wiring. The scope still governs
   (`quarantined`, per §L.2); it moves onto `LIGHTRAG_EMBEDDER_INDEX_PART` in
   `databasise/parts_core/lightrag/embedder_index.py`.
3. **Naming convention — every `component` string carries an `@0.1.0` suffix.** See
   "Naming convention" below. Applied to all eighteen `component` strings in `base.json`. No arm
   patch's `operations` list contains a `component` key, so this edit is a structural no-op for
   the five patch files (recorded here for completeness, not because any patch content changed).

## Naming convention (Task 1 checkpoint)

`docs/system-model/wirings/lightrag-base.json` publishes every component name with **no**
version suffix (e.g. `lightrag/keyword-extractor`), on the grounds that CONTRACT §0 mints a
semver only at promotion and none of the fifteen new LightRAG components has been promoted. This
plan's Task 1 posed that reading against the opposite convention already live in this registry —
`lightrag/query-side` (version `0.1.0`), `lightrag/full-ingest@0.1.0`, `codebase-memory-mcp@0.1.0`
— and the committed Falsifier 2 evidence (`databasise/evidence/wirings/w1-lightrag-query-side.json`,
`w3-lightrag-half-decomposed.json`) referenced `lightrag/query-side` (version `0.1.0`) by that
exact string.

**Update (03-08-PLAN.md Task 3): the `lightrag/query-side` stub is retired.** Phase 3 ported its
real eighteen positions, so this declaration-only placeholder no longer exists anywhere under
`databasise/` — `w1-lightrag-query-side.json` and `w3-lightrag-half-decomposed.json` were rewritten
to resolve against the real, registered ports instead (see those files and
`databasise/evidence/FALSIFIER-2-EVIDENCE.md`). The naming-convention decision recorded below
still holds for every other component name; only the one stub's own identity string is gone.

**Decision (owner, Task 1 checkpoint): `versioned`.** All fifteen new LightRAG components —
`lightrag/embedder-query@0.1.0`, `lightrag/retriever-chunk-topk@0.1.0`,
`lightrag/chunk-heading-backfiller@0.1.0`, `lightrag/reranker-cross-encoder@0.1.0`,
`lightrag/assembler-kg-context@0.1.0`, `lightrag/generator-llm@0.1.0`,
`lightrag/embedder-index@0.1.0`, and the eight graph-half components plan 03-05/03-06 fits parts
for (`lightrag/keyword-extractor@0.1.0`, `lightrag/entity-lookup@0.1.0`,
`lightrag/entity-hydrate-expand@0.1.0`, `lightrag/relation-lookup@0.1.0`,
`lightrag/relation-hydrate-expand@0.1.0`, `lightrag/join-roundrobin@0.1.0`,
`lightrag/truncator-token-budget@0.1.0`, `lightrag/chunk-selector-kg@0.1.0`) — are registered
with an `@0.1.0` suffix, matching the three existing stubs.

This **deviates from the published wiring's own unversioned names and from CONTRACT §0's own
version-minting rule** ("an experiment arm MUST NOT mint a version ... a semver is minted only at
promotion"), which the plan's own recommendation (`unversioned`) would have honored. The owner's
selection prioritizes one consistent convention across the whole registry — every `name_at_version`
field genuinely carries a version — over strict §0 compliance for these fifteen still-unpromoted
components. Phase 7's promotion ledger is the mechanism that was meant to mint these versions;
this decision mints them here instead, ahead of promotion, as a recorded and deliberate deviation,
not an oversight. Every `instance_hash` this phase's run records stamp is keyed to these `@0.1.0`
strings — changing this convention after evidence is recorded voids that evidence rather than
editing it (the same one-way-door property Task 1's checkpoint context stated for either choice).

## Files

| File | Role |
|---|---|
| `base.json` | The registered eighteen-position base wiring (`wiring_id: lightrag-base`) |
| `arm-naive.json-patch.json` | naive arm — 7 nodes, the tracer path this plan proves end to end |
| `arm-bypass.json-patch.json` | bypass arm — 1 node (`generate` only) |
| `arm-hybrid.json-patch.json` | hybrid arm — 17 nodes |
| `arm-local.json-patch.json` | local arm — 15 nodes, carries a declared guard |
| `arm-global.json-patch.json` | global arm — 15 nodes, carries a declared guard |

`databasise/wirings/resolve.py` is the loader/resolver for this set — see its own module
docstring for the base-plus-patch resolution mechanism.
