# Recovered: the Databasise fact layer (wiki / vocab / `as_of`)

**Status:** reconstruction from surviving evidence. Not a specification — a record of what
existed, what can be proved about it, and what cannot.

**Why this file exists.** A destructive incident on the Windows development machine deleted
files and git repositories. The Databasise engine code survived (see §1), but a subsystem that
ran on top of it did not. That subsystem implemented the three capabilities the owner names as
critical — point-in-time query, canonical identity, and contradiction handling — and **no trace
of its server code exists on this machine.** This document captures everything recoverable so
the knowledge is not lost a second time.

**Evidence discipline.** Every claim carries exactly the tag its evidence supports, per the
project convention. `[code-verified]` = read in implementing code. `[docs-verified]` = a
document or design artifact states it; no implementing code was found. `[inference]` = reasoning
from partial evidence. **No claim below is `[code-verified]` against the lost server** — that
code was never found. Where a claim is `[code-verified]`, it is verified against surviving
*client* code or against `v1/`.

---

## §1 — Status of the record

### What survived

- **The Databasise v1 engine, complete.** `v1/` holds 414 Python files. The pre-sanitization
  archive at `/home/chris/Vibe Coding/Databasise/_archives/sourcerer-lightrag_nonstripped_2026-06-26.tgz`
  holds exactly the same 414 `.py` files — the file lists diff to zero. Sanitization removed
  secrets only; nothing of code or design value was lost there. [code-verified]
- **The Sourcerer spikes.** Contrary to the assumption that they were lost, spikes 001–005 survive
  packaged as a skill at
  `/home/chris/Vibe Coding/Sourcerer-Archived/.claude/skills/spike-findings-sourcerer/`,
  with runnable `server.mjs` sources and three distilled reference documents. [code-verified]
  **Operational lesson: check `.claude/skills/spike-findings-*/` in every damaged repo before
  concluding a spike is gone.** The same packaging saved this project's own spikes into
  `.claude/skills/spike-findings-rag-graph-vector-raw/`.
- **The consumer side.** Sourcerer's Wiki and Library applets, the sidecar tool bridge, and the
  design handoff that seeded them. [code-verified]

### What is lost

- **`version_routes.py`** — the FastAPI router carrying the `/wiki/*` and vocab surface.
- **The fact layer** beneath it — resolver, claim store, conflict resolution, version history.
- **`sourcerer.py`** — the fork's entrypoint.

### Where it was ruled out

Searched and confirmed absent: all four repository trees on this machine; the entire git history
of `Deocracy/Databasise` (`git log --all --name-only` — the filename never appears); the
non-stripped tarball; every repository under the `Deocracy` and `ServerDestroyer` GitHub accounts;
every remote branch the local clones do not already hold; all dangling git objects (those are
Sourcerer Wiki-applet stashes in TSX — Sourcerer-Archived has **zero** `.py` files in its entire
history); and all 3,165 Claude Code transcript files. [code-verified]

Last known location: `D:\Vibe Coding\Databasise\runtime` on the Windows machine, with the fork at
a sibling path `../sourcerer-lightrag/` and a virtualenv at `../sourcerer-venv/`. [docs-verified]

---

## §2 — What the subsystem was

A **fact layer** over the RAG engine, exposed as a wiki. Not a document store and not a second
index — a layer that composes, per canonical entity, a set of **claims** (attribute/value pairs),
each carrying document-level provenance, a trust tier, and a record of *which rule resolved it*
when sources disagreed. Where it could not resolve a conflict, it refused to pick and surfaced the
competing candidates with confidence weights. [docs-verified]

The doctrine is stated inside the surviving design data itself, on a genuine birthplace conflict:

> "Sources genuinely disagree. **Surfaced, never silently resolved.**"
> — `src/applets/Wiki/wikiContent.ts:164`

This is what makes point-in-time query load-bearing rather than decorative. Claims are added,
superseded, merged, and re-resolved as documents arrive; `as_of` answers *what the canonical view
of this entity looked like at time T*. The three capabilities are one mechanism. [inference]

---

## §3 — The REST surface

Served by **the same FastAPI application as the RAG engine**, on LightRAG's own default port
`9621`, and self-describing at `/openapi.json`. [code-verified: the client fetched
`http://127.0.0.1:9621/openapi.json`, `sidecar/src/tools/databasise.ts:17,165`]

That means the lost fork was **`v1` plus one mounted router plus a fact layer underneath** — an
additive delta on code that survived, not a separate program. [inference]

| Method | Path | Parameters | Purpose |
|---|---|---|---|
| POST | `/wiki/resolve` | query: `canonical_id`, **`as_of`** — no JSON body | Compose the canonical view of one entity |
| GET | `/wiki/unresolved` | — | List open contradictions |
| GET | `/wiki/unplaced` | — | List off-vocabulary captures |
| POST | `/wiki/preview` | `attribute`, `new_value` | Dry-run an edit; **excluded from the read whitelist** |
| — | vocab routes | unknown | Named, never enumerated |
| POST | `/query` | body: `query`, `mode` | The RAG surface — **this one exists in v1** |

[docs-verified] — `.claude/skills/spike-findings-sourcerer/references/databasise-tools.md`;
`sidecar/src/tools/databasise.ts:48-51`

Total surface was **~40 endpoints**. v1 has 42, none of them `/wiki/*`. [docs-verified / code-verified]

**Behavioural notes that survived:**

- `/wiki/resolve` returns `{}` when the fact layer holds nothing for that entity. This is **not an
  error** — clients must render the empty state gracefully.
- Resolve payloads can be large; the client truncated tool results at 4,000 characters.
- `combined_auth` passed **unauthenticated** in the local guest-mode configuration. The skill flags
  this explicitly as a decision the real build must make deliberately, not inherit.

---

## §4 — The data model

**Evidence status, stated plainly:** the types below come from
`src/applets/Wiki/wikiContent.ts`, whose own header says it is hand-authored demo data ported from
a design handoff. **It is the conceptual model, not a captured API response.** It was authored
against a system that existed and its vocabulary is precise, but the wire format is not proven.
[docs-verified]

```ts
WikiClaim      { id, attr, val, trust, prov, copies }
WikiTrust      "curated" | "library"
WikiProvenance { won, docs[], why }
   won   : "trust" | "recency" | "provenance"   // which rule resolved the conflict
   docs  : [title, page/location, year]         // document-level citation
   why   : human-readable rationale
WikiUnresolved { attr, note, candidates[] }
   candidate : { val, trust, docs[], conf }     // confidence per competing value
WikiArticle    { title, kind, trust, lede, sections[], unresolved }
WikiSection    { g, claims[] }                  // g = group label, e.g. "Identity", "Work"
```

Load-bearing elements:

- **Two trust tiers.** `curated` = human-reviewed. `library` = machine-derived. Rendered as a
  visual distinction, not metadata. [code-verified: `src/applets/Wiki/index.tsx:60,212-217`]
- **`won` records the resolution rule**, not just the outcome. A claim that beat a competitor
  because of source recency is distinguishable from one that won on trust tier or on provenance.
- **`copies`** counts derived copies of a claim elsewhere in the corpus. Editing a claim
  propagates to them. [code-verified: `index.tsx:176,384,411`]
- **`conf`** is a per-candidate confidence on unresolved conflicts, displayed to two decimals.
  [code-verified: `index.tsx:279`]

**Corpus-level model** — `src/applets/Library/libraryContent.ts`: [docs-verified]

```ts
LibraryCorpus      { id, name, tier, docs, conflicts }   // tier: "Full" | "Standard" | "Simple"
LibraryCorpusStats { docs, entities, claims, contradictions, curated }
LibraryDoc         { title, author, kind, trust, status } // status: "ok" | "proc" | "fail"
```

Multiple named corpora coexisted (`ficino`, `medici`, `sandbox`), each with its own conflict count
and a service tier. v1 has workspaces, which are namespace isolation only — no tier, no
corpus-level conflict accounting. [inference]

---

## §5 — The interaction model

Three views, recoverable from the applet. [code-verified: `src/applets/Wiki/index.tsx`]

**Article view.** Entity header with kind and trust chip, lede, unresolved-conflict banner if any,
then claims grouped into sections. Clicking a claim opens a provenance panel showing every source
document with page and year, the `why` rationale, and the derived-copy count.

**Review queue.** A badged tab listing open contradictions across the corpus. Each item names the
entity, the attribute, and the two competing values with their sources. Resolution is one of three
outcomes: `winner` | `both` | `dismiss` — pick one, keep both as coexisting claims, or dismiss the
conflict. [code-verified: `index.tsx:464,472,514`]

**Version history.** Per-entity append-only event log, each row `[when, actor, description]` with a
**REVERT** action. Two actors: `You` (human) and `Ingest` (machine). Recorded event kinds include
entity creation from N sources, claim additions from a named document, entity merges, and curated
edits. [code-verified: `index.tsx:652-690`]

**Edit flow.** Three stages — `edit → preview → applied`. The preview is a **dry run** that states
how many derived copies the change will propagate to before anything is written. This is what
`/wiki/preview` served, and why it needs `attribute` + `new_value`. [code-verified:
`index.tsx:57,297,372-411`]

---

## §6 — Delta against v1

| Capability | Lost fork | v1 |
|---|---|---|
| Canonical entity resolution (`canonical_id`) | yes | no |
| Point-in-time query (`as_of`) | yes | no |
| Claim store with per-claim provenance | yes | no |
| Conflict-resolution rule recorded (`won`) | yes | no |
| Contradictions surfaced, not auto-resolved | yes | no |
| Trust tiers (curated / library) | yes | no |
| Off-vocabulary capture (`/wiki/unplaced`) | yes | no |
| Controlled vocabulary | yes | no |
| Per-entity version history with revert | yes | no |
| Dry-run edit preview with propagation count | yes | no |
| Corpus tiers and conflict accounting | yes | workspaces only |
| RAG query (`POST /query`) | yes | **yes** |
| Graph, chunk, vector stores | yes | **yes** |

v1 holds the engine. It holds none of the layer above it. [code-verified against `v1/`]

**One adjacent fact worth recording here, because it was nearly missed:** `v1/lightrag/kg/cozo_impl.py:16-23`
states the Cozo schema is deliberately shaped so a `Validity`-typed key column can be added later,
for bi-temporal append-and-invalidate versioning, as an **additive** migration — no column dropped
or renamed. Cozo 0.7.6 carries a native `Validity` type with assert/retract semantics and `@`
time-travel query syntax. The storage substrate for `as_of` was prepared and never built out.
[code-verified]

*(Note: "Phase 6" in that docstring is the **old** Databasise v1 phase numbering, not the current
v2 ROADMAP's Phase 6.)*

---

## §7 — Where this lands in the v2 contract

Recorded so the fit is not re-derived later. [inference throughout this section]

- **Version history maps directly onto the ledger.** CONTRACT §7 requires `change_origin` on every
  generation record with exactly two values, `human_edit | machine_mutation`. The Wiki version
  history has exactly two actors, `You | Ingest`. Same distinction, same shape, and the v2
  vocabulary already exists for it. MACH-07 (Phase 7) is where that lands.
- **`as_of` needs a declared capability.** CONTRACT §14.4 defines `temporal`; §8 admission
  condition 11 refuses `as_of` on any node that has not declared it. The contract anticipated this
  surface.
- **DR-05 currently defers exactly this.** `.planning/REQUIREMENTS.md:66` lists the graph-store
  `validity` sub-capability under v2 deferred, reasoned as "no v1 modality declares `temporal`".
  That reasoning is now known to be incomplete — a prior Databasise **did** expose a temporal query
  axis. The deferral should be re-decided rather than inherited.
- **The seam is the forcing constraint.** Phase 4 freezes the §18 envelope. A canonical-entity,
  claim-with-provenance, contradiction-bearing response does not fit the current §18.2 shape.
  Whether the fact layer is in or out of this milestone, **Phase 4 must decide knowingly**, because
  the envelope is closed once locked.
- **Nothing in v2 REQUIREMENTS.md covers any of this.** All 34 requirements checked.

---

## §8 — What is NOT recovered

Stated so nobody plans against a gap as if it were a spec.

- **No response wire format.** Not one captured payload from any `/wiki/*` endpoint.
- **`as_of` semantics are unknown.** Timestamp? Version id? Cozo `Validity` instant? The single
  most important unknown, because it decides whether the time travel was real bi-temporal
  versioning or a shallower snapshot pointer.
- **No conflict-detection algorithm.** We know contradictions were surfaced; we do not know how
  they were detected, or how `conf` was computed.
- **`/wiki/unplaced` semantics.** "Off-vocabulary captures" is the entire description.
- **The vocab routes.** Named, never enumerated. Count and shape unknown.
- **~36 of the ~40 endpoints.** Only four were ever whitelisted into a tool, so only four are
  documented.
- **All server-side design.** Resolver, claim storage, propagation mechanism, merge semantics.
- **Whether the fact layer wrote to Cozo, to a separate store, or to KV.** Unknown.

---

## §9 — Sources

Every path below was read directly. Paths outside this repository are given absolute, in plain
text, because they contain spaces.

**In this repository:**

- `v1/lightrag/kg/cozo_impl.py:16-23` — the `Validity` forward-compatibility note
- `v1/lightrag/api/routers/` — the four surviving routers; no `version_routes.py`
- `.planning/REQUIREMENTS.md:66` — the DR-05 deferral

**In Sourcerer-Archived** (`/home/chris/Vibe Coding/Sourcerer-Archived/`):

- `.claude/skills/spike-findings-sourcerer/references/databasise-tools.md` — the fullest single
  source: endpoint list, param placement, run instructions, pitfalls
- `.claude/skills/spike-findings-sourcerer/sources/002-databasise-tools-over-pi/README.md` — the
  spike record, verdict VALIDATED, with the investigation trail
- `sidecar/src/tools/databasise.ts` — the working client, base URL, whitelist, degrade contract
- `sidecar/test/tools.test.mjs` — its tests
- `src/applets/Wiki/wikiContent.ts` — the claim/provenance/unresolved model
- `src/applets/Wiki/index.tsx` — article, review queue, version history, edit flow
- `src/applets/Library/libraryContent.ts` — corpus and document model
- `design-sync-setup-guide/design_handoff_bespoke_rails_shell/wiki.js` — the original design source
- `.planning/milestones/v1.0-phases/07-assistant-harness-.../07-02-PLAN.md:70-75,117,127,131` — tool
  signatures and query-vs-body split
- `.planning/milestones/v1.0-phases/07-assistant-harness-.../07-PATTERNS.md:169` — the whitelist
- `.planning/milestones/v2.0-REQUIREMENTS.md:39-42` — ENG-01 through ENG-04

**Runtime, on the damaged machine (not reachable from here):**

- `D:\Vibe Coding\Databasise\runtime` — working directory
- `../sourcerer-lightrag/sourcerer.py` — entrypoint
- `./rag_storage/` — the populated store: Cozo + Faiss, 112 entities
- `./sourcerer_data/` — the empty default the entrypoint used unless `WORKING_DIR` was set

---

*Written 2026-08-29 during Phase 1 discussion, after the fork was found missing.*
