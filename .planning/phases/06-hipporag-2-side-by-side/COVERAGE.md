# API Coverage — Phase 6: HippoRAG 2 & Side-by-Side

This phase carries its own §18.5 operations-table record, rather than only amending Phase 5's
(`.planning/phases/05-opaque-side-admission/COVERAGE.md`), so the phase that actually lands a new
operation is the phase whose own coverage record states it landed there.

## The §18.5 surface record

CONTRACT §18.5: *"The tool surface MAY grow per part and MUST NOT grow per modality."* This phase
adds exactly one new operation — API-08's comparison surface — reachable identically in-process,
over REST and over MCP. Registering HippoRAG 2 as this milestone's second modality (06-01 through
06-09) added **zero** new operations to this table; every row below either already existed
(Phase 4/5's own table) or is this plan's own new `compare` row.

| operation | transports | plan | why an operation and not a selector |
|---|---|---|---|
| compare | in-process, REST (`POST /compare`), MCP (`compare` tool) | 06-03 | API-08's comparison operation: a §18.4 selector picks one arm; `compare` fans out over N of them in one call, returning per-arm results keyed by the caller's own selector values — never an arm id, wiring name, node id or modality name. Inspection-only (no verdict, no aggregate, no winner — RIG.md ## §RUN.4). Landed once the rig had two real arms to fan out over ("rig before comparison surface," ROADMAP.md line 296), discharging the `OPT-OUT` row Phase 5's own table carried for it. |

Every other operation (`query`, `ingest`, `delete`, `status`/`health`/`corpus`/`document counts`,
`evidence`/`trace` resolution) is unchanged by this phase — see
`.planning/phases/05-opaque-side-admission/COVERAGE.md`'s own §18.5 table for those rows, all of
which remain reachable identically for both LightRAG and HippoRAG arms with no operation-level
change (§18.5's own modality-agnosticism holding by construction, not by a second per-modality
copy of any route or tool).

### Operations still deliberately absent

Unchanged from Phase 5's own table — `promote`/`rollback` (Phase 7's own deliverable) and the
comparison-rig operations (still a peer client of this seam, not an operation on it, per §18.3).
