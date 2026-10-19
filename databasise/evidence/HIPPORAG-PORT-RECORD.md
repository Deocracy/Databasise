# HippoRAG 2 Port Record — thirteen positions, no opaque core

Dated 2026-09-10 (06-07-PLAN.md). The code-inspected record closing MODAL-04's decomposition
claim, restating what the built port (`databasise/parts_core/hipporag/`,
`databasise/wirings/hipporag/base.json`) actually declares against `docs/system-model/PARTS.md
## §H` — this modality's governing entry — and enumerating every point where the two diverge,
with a reason for each, per the 05-06-PLAN.md `ADMISSION-CODEBASE-MEMORY-MCP.md` precedent for
recording a discrepancy rather than resolving it silently in either direction.

## The claim under test (MODAL-04, verbatim)

> HippoRAG 2 fully decomposed — thirteen node positions, no opaque core left behind — with
> whole-graph PPR reached via §14.2's Graph bulk-export declared capability and the native
> igraph/prpack call plus OpenIE/reset-vector-join scaling formulas carried over as node
> internals; index-side effective depth remains `opaque` under the taint rule until its parity is
> shown

## Verdict

**The decomposition half of MODAL-04 is satisfied and checkable** —
`tests/parts_core/hipporag/test_thirteen_positions.py` pins it against `## §H` at test time: all
thirteen node ids resolve to registered, executable (`body is not None`) parts; none is
opaque-kinded and none carries an admission record (`## §H`'s `Admission: n/a — decomposed`
verdict, made checkable); effective depth is `opaque` at every position under the taint rule; the
wiring's `recipe` matches `## §H`'s own `Recipe:` field; no arm exists and no patch file was
written for this modality (`Arms: none (single base wiring)`); and every node resolves
`in-process` execution.

**The parity half is explicitly not attempted in this phase** — see Limits, below. The claim's
own text conditions the index side's `opaque` status on parity being shown; this record's own
verdict is that keeping it `opaque` is what this phase correctly delivers, not a gap in it.

## The findings table

| # | Finding | Evidence |
|---|---|---|
| 1 | The built wiring's resolved node ids equal `## §H`'s own node-table ids plus the recorded `qa` node (see "The `qa` node divergence") — `chunk-embed`, `openie`, `entity-fact-embed`, `fact-edges`, `passage-edges`, `synonymy-edges`, `graph-augment-persist`, `fact-score`, `fact-filter`, `dpr-fallback`, `reset-vector-join`, `ppr`, `assemble-result` | `[code-verified]` `test_the_built_wirings_resolved_node_id_set_equals_the_governing_thirteen_plus_the_recorded_qa` |
| 2 | Every one of the thirteen resolves in `default_registry()` to a `Part` with a non-`None` body — no declaration-only placeholder remains | `[code-verified]` `test_every_node_resolves_to_a_registered_part_with_a_non_none_body` |
| 3 | No `hipporag/` part carries `kind == "opaque"`, and none carries an `AdmissionRecord` | `[code-verified]` `test_no_hipporag_part_is_opaque_kinded_and_none_carries_an_admission_record` |
| 4 | `effective_depth` over the parsed wiring is `opaque` at all thirteen positions (the taint rule holding transitively) | `[code-verified]` `test_effective_depth_is_opaque_at_every_position_including_the_recorded_qa` |
| 5 | The wiring declares no arms and no `*.json-patch.json` file exists under `databasise/wirings/hipporag/` | `[code-verified]` `test_the_wiring_declares_no_arms_and_no_patch_file_exists_for_this_modality`, matching `## §H`'s own `Arms: none (single base wiring)` |
| 6 | `derive_execution_mode` returns `in-process` for all thirteen — no node needs subprocess containment | `[code-verified]` `test_derive_execution_mode_returns_in_process_for_every_position` |
| 7 | The built effects union equals `## §H`'s own declared `effects[]:` union plus exactly four additive effects, no more | `[code-verified]` `test_declared_effects_union_equals_the_governing_union_plus_exactly_the_additive_set` — see the reconciliation table below |
| 8 | Whole-graph PPR is served by one native `igraph`/`prpack` call over a two-Cozo-query bulk export (06-01), never an N-call pointwise emulation | `[code-verified]` `databasise/parts_core/hipporag/ppr.py`, `databasise/stores/graph.py`'s `export_to_igraph` |

## The declared-effects reconciliation

`## §H`'s own `effects[]:` sentence declares the union `{calls_embedding, calls_llm, reads_vector,
reads_graph, reads_kv}`. The built port's own union additionally carries `{writes_vector,
writes_kv, writes_graph, writes_artifact}`. Every row below traces to the same mechanical cause:
`CapabilityScopedStores.require` (`databasise/parts_core/__init__.py`) hands a node's body no
store handle for an effect it did not declare — a node `## §H`'s own prose describes as writing a
store must declare that write to reach the store at all, or its own documented behaviour is
unreachable code. The inverse also holds: a node that no longer calls a client stops declaring
it, so the last two rows below are narrower than `## §H`.

| Node | `## §H` declared | Built declares | Reason |
|---|---|---|---|
| `fact-score` | `reads_vector` | `reads_vector`, `calls_embedding` | `06-01`. This node's `deps` is `[]` — no upstream `embedder-query`-shaped position feeds it a precomputed query vector (unlike LightRAG's `chunk-vector`, which always receives one). It must embed the query itself. |
| `chunk-embed` | `calls_embedding` | `calls_embedding`, `writes_vector`, `writes_kv` | `06-02`. `## §H`'s own row states this node fuses chunk storage and embedding (`EmbeddingStore.insert_strings`, no external cut point) — the store writes it performs are real and must be declared. |
| `entity-fact-embed` | `calls_embedding` | `calls_embedding`, `writes_vector`, `writes_kv` | `06-02` declared `writes_vector` (this node writes two Vector namespaces — entities, facts). `06-07` additionally declares `writes_kv`: closing the fact-chunk-association gap `06-05-SUMMARY.md`'s own "Next Phase Readiness" section named and disposed to this plan — `reset-vector-join.py` (`06-01`, already committed) reads each surviving fact's own chunk association from a KV `fact:<id>` record; before `06-07`, no code wrote that record for a real end-to-end run, only the test fixture hand-seeded it. |
| `graph-augment-persist` | *(none declared)* | `writes_graph`, `writes_artifact` | `06-05`. This node persists the whole `igraph.Graph` object as one write; `## §H`'s own node-table row for it declares no effect at all, which would make its documented write unreachable. |
| `reset-vector-join` | `reads_vector`, `calls_embedding`, `reads_kv` | `reads_vector`, `reads_kv` | `12-07` (D-17). The query is embedded once at `fact-score` and the vector reaches this node over a direct dep (`ctx.inputs["fact-score"]["query_vector"]`), so the node never calls the embedding client and no longer declares `calls_embedding`. |
| `dpr-fallback` | `calls_embedding`, `reads_vector` | `reads_vector` | `12-07` (D-17). Same reason: the query is embedded once at `fact-score` and the vector reaches this node over a direct dep, so neither this node nor `reset-vector-join` calls the embedding client. |

The first four rows are genuine over-declarations relative to `## §H`'s node-table text, and the
last two are narrowings; none is a resolution of `## §H` in either direction:
`docs/system-model/PARTS.md` is a verbatim frozen mirror and is not edited by this record, and no
built part's effects is narrowed below what its own body actually reaches.

## The query-vector deps divergence

`12-07` (D-17). The illustrative `docs/system-model/wirings/hipporag-base.json` declares
`reset-vector-join` and `dpr-fallback` with `deps: ["fact-filter"]`. The built wiring declares
`["fact-filter", "fact-score"]` for both. A node reads another node's output only through its own
declared `deps` → `ctx.inputs`, so the shared query vector `fact-score` emits as `query_vector`
reaches the two nodes only if `fact-score` is a direct dep of each. The addition leaves the
scheduling order unchanged (`fact-filter` already depends on `fact-score`) and `fact-score`'s own
deps stay `[]`. Before this change a HippoRAG query embedded its text three times (once in each of
the three nodes); it now embeds once. The row follows the `assemble-result` deps divergence
below.

## The guard-placement divergence

`## §H`'s `Arms:` field (point 1) and the illustrative `docs/system-model/wirings/
hipporag-base.json` both carry the `zero_surviving_facts_dpr_fallback` guard declaration at the
**top level** of the wiring document, in a rich descriptive shape (`guard_name`, `declared_per`,
`evaluating_node`, `condition`, `emitted_when_not_fired`, `when_fired`, `observability`,
`gate_consequence`).

The **built** wiring (`databasise/wirings/hipporag/base.json`) instead carries the guard on the
guarded node's own `config.guards` (the `fact-filter` node), in the narrower shape
`databasise/runner/guards.py`'s `declare_guard` actually consumes: `name`, `evaluating_node`,
`value_when_not_fired`, `granularity`. This is a **placement and shape difference between an
illustrative document and the built form, not a semantic one** — `runner/guards.py`'s own module
docstring states the rule this built placement follows: "a guard declaration is carried as an
ordinary field on the guarded node's own wiring `config` (`config.guards`), so
`identity.canon.config_hash` already covers it — two wirings differing only in a guard are two
identities, never one identity carrying two behaviours." The illustrative document's top-level
`guards` array is evidence `## §H` cites; it is never parsed by `validator/parse.py` (which reads
only `doc.get("nodes", {})` at the top level) and therefore never reaches
`runner/scheduler.py`'s own `_validated_guards`, which reads `node.config` per node.

## The guard-observability resolution

`12-12` (D-21, HIPP-14). `## §H`'s `Arms:` field states the guard's firing is observable per query
through `§18.2`'s existing envelope machinery, with no new field minted. The 06-07 resolution held
that `degraded` was unusable for this purpose because `RunRecord.__post_init__` refused a record
where `degraded` and `partial` disagreed. Phase 12 reverses that: the relaxed invariant lets a
completed run on a declared degradation path be `degraded` without being `partial`. A fired guard
now sets `degraded` true (`partial` stays false) with the closed, node-free reason codes
`declared_fallback` (stop reason) and `fallback_path_taken` (degradation reason); a run whose guard
did not fire stays clean. The per-node `guards_fired` field stays in the run record, reached by a
caller through the envelope's existing `trace_token` → `Databasise.resolve_trace(..., debug=True)`
path, and the guard name still never appears in the serialised `ResponseEnvelope`
(`tests/parts_core/hipporag/test_dpr_fallback_guard.py`). No new envelope field is minted.

## Phase 12 divergences and limits

Each entry cites the decision that made it. Evidence class is `[code-verified]` for all of them; the
pinning tests are named in the Phase 12 plan summaries.

- **D-05, asymmetric recall.** `synonymy-edges` matches only entities new in this ingest against
  every committed and staged entity. A new entity that appears only in an old entity's top-k (not
  the reverse) is missed; upstream recomputes the full self-KNN each time. A pair is emitted once,
  on the ingest that introduces it, with one exception (A-CR-01): on a re-ingest, the synonymy edges
  of an entity `document-remover` deleted as an orphan, which the same run re-adds, are restored
  (the remover returns them as `removed_synonymy_edges`; `synonymy-edges` re-emits those whose two
  endpoints still exist at the end of the run).
- **D-04, summed weight against upstream's max.** The persisted edge `weight` is the sum of the
  per-chunk co-occurrence counts, the synonymy weight and the passage weight. Upstream keeps the
  max of the source count and the synonym score. The sum is the Databasise form; the divergence
  changes PPR transition probabilities on graphs where one pair carries more than one edge type.
- **D-08, strict extraction.** An OpenIE response that fails to parse or validate raises instead of
  yielding an empty finding. A real-provider ingest is therefore refused on one malformed response,
  where upstream logs and continues. The trade-off is a loud refusal over a silently thinner graph.
- **D-20, `top_k` default 5.** `assemble-result` keeps the first `top_k` items of the selected branch
  (default 5, upstream `qa_top_k`), after dropping zero-score PPR items. Dense passage retrieval is
  never cut. This bounds both the `qa` prompt and the minted evidence. Divergence from upstream
  (A-WR-02, A-WR-05): upstream returns its PPR ranking even when every score is 0. Here, if no PPR
  item scores above 0 (an all-zero reset vector), `dpr-fallback`'s items answer instead. That is a
  declared degradation path under D-21: `base.json` declares the per-query guard
  `empty_ppr_dpr_stand_in` on `assemble-result`, so the node's `guards_fired` names it and the run
  reads `degraded` (not `partial`) with `declared_fallback` / `fallback_path_taken`. Like the
  `fact-filter` guard, a cross-modality arm that took it is one `parity/run_cross_modality.py`
  refuses (CONTRACT §5, tenth refusal).
- **D-19, `qa` costs a call.** The `qa` node adds one LLM call per HippoRAG query. The owner-run check
  of its answer quality and per-query cost is listed in section 2 of `.planning/TESTING-PLAN.md`.
- **D-03, chunk id form.** A chunk id is `sha256(document_id:ordinal:text)` (sha256 over the
  document id, the ordinal and the chunk text), not the ordinal alone.
- **D-12 with D-03, rebuild required.** HippoRAG stores built before Phase 12 carry no `doc:`
  manifest, ordinal-only chunk ids and no per-chunk co-occurrence map. The document remover is a
  no-op without a manifest, so such a store cannot be corrected in place and must be rebuilt.
- **D-16, `[writes_artifact]` selector.** A query run is pruned to the ancestors of `provides`, and
  no query run writes artifacts, so a `[writes_artifact]` selector now raises
  `UnsatisfiableSelectorError`. `writes_graph`, `writes_kv` and `writes_vector` selectors no longer
  resolve to HippoRAG either. `base.json` keeps its nodes; promotion's declared surface stays on the
  full wiring.
- **D-22, removed config keys.** Config no part body, scheduler or guard path reads is gone from
  `base.json` and `corpus-ingest.json`: entity-fact-embed `namespaces`, synonymy-edges `guard`,
  reset-vector-join `socket_shape`, `arm_precedence` and `apportionment_policy`, ppr `readback`,
  assemble-result `order_policy`. `declared_capability` (three nodes of `base.json`, two of
  `corpus-ingest.json`) was read by no body either and is removed too, so the wiring no longer
  transcribes that key from `docs/system-model/wirings/hipporag-base.json`. The wiring `config_hash`
  changes.
- **D-22, edge types.** `edge_types` and the per-chunk co-occurrence map are persisted on the graph
  edge and not exported; `export_to_igraph` reads only `weight`. No route exposes the types.

## The `qa` node divergence

`12-10` (D-19, HIPP-13). `## §H` has no generator position among its thirteen, so the base wiring's
`answer` was the retrieved passages joined by blank lines, a different meaning from LightRAG's
generated answer. The built wiring carries a 14th node, `qa` (`hipporag/qa-reader@0.1.0`, kind
`generator`, effects `["calls_llm"]`, deps `["assemble-result"]`), which ports upstream HippoRAG 2's
`rag_qa` step (`src/hipporag/HippoRAG.py:1117-1172`, prompt `rag_qa_musique`, commit d5c8329, MIT):
the upstream system text, one-shot user/assistant pair, one `Wikipedia Title: <passage>` line per
hydrated passage (the upstream prefix is kept verbatim), then `Question: <query>` and `Thought:` plus a trailing space;
the answer is the text after `Answer:` (the whole response when the marker is absent). `qa` is the
wiring's `provides`; `assemble-result` no longer emits `completion` and stays the
`evidence_position`, so evidence still mints from the retrieved items. With no hydrated passage
content `qa` makes no LLM call and answers `PROMPTS["fail_response"]`, the same no-context answer
LightRAG's generator gives. Costs: one more LLM call per query, and a new `config_hash` for the
wiring (traces of the 13-node wiring no longer map to an arm in promotion). The effect `calls_llm`
is already in `## §H`'s union, so the declared-effects reconciliation above gains no row.
`tests/parts_core/hipporag/test_thirteen_positions.py` compares the node set with the governing
thirteen plus `qa`, and `test_registration.py` pins the part's shape.

## The `assemble-result` deps divergence

The illustrative `docs/system-model/wirings/hipporag-base.json` declares `assemble-result`'s
`deps` as `["ppr", "dpr-fallback"]`. The built wiring declares
`["ppr", "dpr-fallback", "fact-filter"]`. This third dep is required by `§11`'s
control-channel-is-a-read rule: `assemble-result` must learn the guard's own outcome
(`guard_fired`) to choose between `ppr`'s items and `dpr-fallback`'s, and the only sanctioned
channel for a node to read another node's output is its own declared `deps` → `ctx.inputs` — never
a mid-run read of the run record. `ppr` and `dpr-fallback` both run unconditionally and neither
reads the guard itself (per `## §H`'s own text, the wiring dispatches both, and `assemble-result`
chooses); `fact-filter` is therefore the only node carrying the outcome, and must be an explicit
dep for `assemble-result` to reach it. `evidence_position` was moved from `ppr` to `assemble-result`
in the same commit, for the same reason: before this change the envelope's own evidence was minted
from `ppr`'s raw output regardless of which branch `assemble-result` actually selected.

## The nearest-signature typing row

`## §H`'s own node table types three of the thirteen positions by "nearest signature" rather than
an exact `§13.4` primitive-part-type match — `fact-score`, `ppr` and `dpr-fallback` are typed
`retriever` "nearest signature," and `graph-augment-persist` carries **no `§13.4` row at all**
("no `§13.4` row names a whole-graph materialization step; nearest analog is row 3 `extractor`'s
graph-store-write shape, without that row's query/LLM signature"). `03-RESEARCH.md §H.2` names this
as one of two reasons the index side's effective depth stays `opaque` under the taint rule (the
other being that `§19.1`'s port-completeness diagnostic cannot fully certify a node whose type is
an analogy rather than an exact match) — carried here as a stated fact about the record, not
re-derived.

## Method

Every finding above is code-verified against this repository's own installed state: the built
`Part` objects in `databasise/parts_core/hipporag/*.py`, the built wiring in
`databasise/wirings/hipporag/base.json`, the illustrative `docs/system-model/wirings/
hipporag-base.json`, and `docs/system-model/PARTS.md ## §H`'s own prose. The reconciliation table's
"Reason" column cites the plan (`06-01`/`06-02`/`06-05`/`06-07`) that recorded each row, per this
codebase's own `ADMISSION-CODEBASE-MEMORY-MCP.md` precedent for compounding discrepancy records
across plans rather than losing the provenance of each row.

## Limits

**The upstream-package parity measurement is deliberately not run in this phase.**
`CONTRACT.md §6`'s parity-not-gain rule and `§5`'s determinism-is-verified rule together mean a
fresh port earns `stage`-eligibility only by measurement against a trusted baseline, and no such
measurement has been run for HippoRAG 2 anywhere in this milestone. What that measurement would
consist of: the real upstream `hipporag` PyPI package, pinned by exact commit SHA, installed in its
own isolated interpreter (never imported into `databasise/`'s own environment — the same D-14
import-boundary rule Phase 5 enforced for v1's `lightrag` package), run end to end on the same
corpus and queries this port's own tests use, and compared at the retrieval level exactly as Phase
3's `PARITY-EVIDENCE.md` did for LightRAG. This is not run here because MODAL-04's own text
requires the index-side effective depth to stay `opaque` until parity is shown — keeping it
`opaque` is what this phase delivers, and running an unfinished or informal parity check would
risk narrowing that depth on evidence this record cannot stand behind. Plan `06-09` carries the
deferral forward with its own trigger for when that measurement should be run.

**The named deferral entry (06-09-PLAN.md), tracked rather than left as an absence.**

| Field | Value |
|---|---|
| What it consists of | The real upstream `hipporag` package (PyPI `2.0.0a4` / `main` `2.0.0a5`), pinned by exact commit SHA, installed in its own isolated interpreter never imported into `databasise/`'s own environment — the same D-14 import-boundary rule Phase 5 enforced for v1's `lightrag` package (`databasise/parity/v1_arm.py`'s own subprocess-boundary pattern) — run end to end on the same corpus and queries this port's own tests use, and compared at the retrieval level exactly as Phase 3's `PARITY-EVIDENCE.md` did for LightRAG |
| What it would buy | `stage`-eligibility for the index side, and with it true shared-artifact eligibility under `§3`'s blast-radius rule and a genuine `reuse` classification from `§6`'s reindex planner, replacing the `opaque`/`quarantined` status this phase carries forward under the taint rule |
| Why it is not run here | MODAL-04's own text conditions the index side's `opaque` status on parity being shown; keeping it `opaque` absent that measurement is exactly what this phase correctly delivers, not a gap in it. `06-RESEARCH.md`'s own assumption A6 records the stronger reading — that "showing parity means running the upstream package" — as that session's own inference, not a clause any frozen document states as a requirement |
| Trigger | The first requirement asking for HippoRAG index-side artifact sharing or `stage`-depth eligibility |
| Standing risk to this future measurement | The upstream package's own alpha status (`2.0.0a4` on PyPI / `2.0.0a5` on `main`) — a pre-1.0 API is being depended on for a measurement, not for production behaviour, so an upstream break between the pinned SHA and a future `2.0.0` would invalidate the harness rather than the engine, and any future run must re-pin and re-verify the call shape (`run_ppr`/`add_synonymy_edges`/`save_igraph`) rather than assume it is unchanged |

**The synonymy-edges no-new-entity short circuit (06-05, reworded by D-05 and D-22).** `synonymy-edges`
declares no `guard` config key any more. A run that produced no new entity takes no store handle and
emits no edge, an ordinary conditional inside that node's own body. A reader should not conflate it
with `06-07`'s `zero_surviving_facts_dpr_fallback` guard, which is wired through `runner/guards.py`'s
declared-guard machinery.
