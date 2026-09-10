# API Coverage — Phase 6: HippoRAG 2 & Side-by-Side

This phase carries its own §18.5 operations-table record, rather than only amending Phase 5's
(`.planning/phases/05-opaque-side-admission/COVERAGE.md`), so the phase that actually lands a new
operation is the phase whose own coverage record states it landed there.

**No external API integration** — HippoRAG 2 is ported in-repo over the machine's own primitives; the one external API consumed (the OpenAI-compatible model endpoint) is Phase 3's, whose COVERAGE.md stays authoritative.

## The §18.5 surface record

CONTRACT §18.5: *"The tool surface MAY grow per part and MUST NOT grow per modality."* This phase
adds exactly one new operation — API-08's comparison surface — reachable the same way in-process,
over REST and over MCP. Registering HippoRAG 2 as this milestone's second modality (06-01 through
06-09) added **zero** new operations to this table; every row below either already existed
(Phase 4/5's own table) or is this plan's own new `compare` row.

| operation | transports | plan | why an operation and not a selector |
|---|---|---|---|
| compare | in-process, REST (`POST /compare`), MCP (`compare` tool) | 06-03 | API-08's comparison operation: a §18.4 selector picks one arm; `compare` fans out over N of them in one call, returning per-arm results keyed by the caller's own selector values — never an arm id, wiring name, node id or modality name. Inspection-only (no verdict, no aggregate, no winner — RIG.md ## §RUN.4). Landed once the rig had two real arms to fan out over ("rig before comparison surface," ROADMAP.md line 296), discharging the `OPT-OUT` row Phase 5's own table carried for it. |

Every other operation (`query`, `evidence`/`trace` resolution) is unchanged by this phase — both
LightRAG and HippoRAG arms reach it with no operation-level change (§18.5's own
modality-agnosticism holding by construction, not by a second per-modality copy of any route or
tool). `status`/`health`/`corpus`/`document counts` are the one exception in this phase — see the
`corpus`/`corpus/counts`/`jobs` note below, newly true only because 06-10 gave HippoRAG a real
write path to be absent from.

**Write-surface record (06-REVIEW.md CR-01, closed by 06-10): `ingest` is two-arm, `delete` is
LightRAG-only, both by name, never by silent fallback.**

1. **`ingest` is two-arm.** `Databasise.ingest()` accepts the same §18.4 selector `query`/`compare`
   accept and dispatches `databasise/wirings/<modality>/corpus-ingest.json` — both LightRAG
   (`databasise/wirings/lightrag/corpus-ingest.json`) and HippoRAG
   (`databasise/wirings/hipporag/corpus-ingest.json`) ship one. A caller supplying no selector
   reaches the LightRAG path unchanged, including its on-disk store directories.
2. **`delete` is LightRAG-only, and says so by name.** Only LightRAG ships a `corpus-delete.json`;
   a selector resolving to any other fitted modality raises `NoWritePathForModalityError` rather
   than writing into LightRAG's index. No HippoRAG node retracts vectors or edges — a delete
   wiring would need node code that does not exist yet — so this is tracked as follow-up scope for
   whichever phase builds that node, not silently absent.
3. **`corpus`, `corpus/counts` and `jobs/{job_id}` report the LightRAG corpus only.** These three
   reach v1's own foreign driver (`databasise.foreign.run_corpus_op`) directly, never through the
   scheduler, so a document ingested into HippoRAG through the seam does not appear in them. This
   sentence is newly required *because* of 06-10: before it, no document could exist in HippoRAG's
   index through the public seam at all, so there was nothing for these three to omit.

06-10 closed the CR-01 gap this section used to describe as open: `databasise/wirings/hipporag/
corpus-ingest.json` now exists (a re-composition of `base.json`'s own seven index-side node
objects, no new node code), `Databasise.ingest()`/`delete_document()` dispatch per the resolved
modality via `databasise.wirings.resolve.wiring_family`, and `NoWritePathForModalityError` refuses
by name rather than ever silently falling back to another modality's wiring. HippoRAG's index can
now be populated through the public seam — in-process, over REST, and over MCP — closing Gap 1(a)
from 06-VERIFICATION.md. Gap 1(b), the real, spend-incurring cross-modality run against the Phase 3
parity corpus, remains open — 06-13's own blocking checkpoint, not discharged by this plan.

### Operations still deliberately absent

Unchanged from Phase 5's own table — `promote`/`rollback` (Phase 7's own deliverable) and the
comparison-rig operations (still a peer client of this seam, not an operation on it, per §18.3).
