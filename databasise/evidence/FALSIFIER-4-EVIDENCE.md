# Falsifier 4 Evidence

Falsifier 4, quoted verbatim from `CONTRACT.md ## §4`:

> Falsifier 4 of the selection's pool, in this section's terms — run twice on
> `codebase-memory-mcp` (once consuming machine chunks, once chunking natively): if even the
> native-chunking case can produce output mapping to `ChunkRef`, T1 coverage for opaque parts is
> real and the depth ladder pays off immediately for black boxes; if only the machine-chunk case
> works, T1 coverage costs the chunker surrender and this section's evidence machinery
> concentrates its value on house parts. Either outcome calibrates this section; the section is
> refuted as written only if neither case can emit a machine-resolvable ref at all — meaning
> `ChunkRef` cannot be constructed from an opaque part's output under any feed strategy.

`PARTS.md ## §X`'s "Falsifier 4's status" section recorded this falsifier **unrun** — no evidence
of either leg having been executed against the pinned clone. This document is the actual run,
against the installed `codebase-memory-mcp@0.10.8` binary, through
`databasise/foreign/codebase_memory_mcp_adapter.py` (05-06-PLAN.md Tasks 1–2).

## Leg 1 — chunking natively (run for real)

Invoked `index_repository` through the adapter against this repository's own `databasise/`
directory, then called the engine's evidence-returning tools — `search_graph` (graph search),
`get_code_snippet` (code snippet), and `search_code` (code search), the three tools Task 3's own
action text names by role — and confirmed every returned item normalizes to a §4 `ItemKind`
member (`databasise.foreign.codebase_memory_mcp_adapter.normalise_to_item_kind`).

**Index build (precondition for the evidence calls below):** `index_repository` against this
repository's own `databasise/` directory — real run, this session:

| Field | Value |
|---|---|
| Duration | 2.88s (cold-start; matches `CBM_MEASURED_INDEX_DURATION_SECONDS` in `databasise/parts_core/codebase_memory_mcp.py`, the same measurement §8 condition 4's ceiling is grounded against) |
| Nodes / edges | 3204 / 14401 |
| Status | `indexed` |

**Per-field `ChunkRef(corpus_id, recipe@version, ordinal, content_hash)` result, one row per
field, real values from the three evidence-returning tools called against this repository:**

| ChunkRef field | `get_code_snippet` | `search_graph` | `search_code` | Disposition |
|---|---|---|---|---|
| `corpus_id` | not supplied | not supplied | not supplied | **Not supplied.** None of the three evidence-returning tools echoes a `project`/corpus identifier on the individual item — the caller-supplied `project` argument is not reflected back per-item. The adapter *could* thread the caller's own request-time `project` value through as a derived `corpus_id`, but `normalise_to_item_kind`'s signature is `(raw_item, tool_name)` — no call-context parameter — so this adapter records it as unsupplied rather than silently threading a value the item itself does not carry. |
| `recipe@version` | cannot be supplied | cannot be supplied | cannot be supplied | **Cannot be supplied at all.** This engine declares no recipe/sub-recipe concept anywhere in its fifteen-tool surface (`PARTS.md ## §X`: `"Recipe: n/a"`) — there is no chunker/extraction/embedding stamp for any tool to report, at any version, for this or any other repository it might index. This is the structural finding, not a per-call gap. |
| `ordinal` | cannot be supplied | cannot be supplied | cannot be supplied | **Cannot be supplied at all.** No chunk-ordinal concept exists anywhere in this engine's model — its unit of retrieval is a named symbol (function/class/variable) or a file/line range, never a position in a machine-defined chunk sequence. |
| `content_hash` | **derived** (`sha256:125ea3d1f5...` over the returned `source` text, real value from a live call this session) | not supplied | not supplied | **Derived only where the raw source text is present.** `get_code_snippet` is the only one of the three tools that returns the symbol's actual source text (`source` field) — the adapter hashes that text itself; the engine never reports a content hash. `search_graph`/`search_code` return file/line-range/rank locations with no source text attached, so no hash can be derived without a second round-trip (reading the file) this adapter does not perform. |

**Resulting evidence tier: `below_T1` for every item from every one of the three tools,
unconditionally** (`normalise_to_item_kind`'s own `tier`/`tier_reason` fields, asserted by
`test_a_ref_the_adapter_cannot_resolve_is_tier_capped_below_t1`). Even `get_code_snippet`'s
best case — a derived `content_hash` plus a real, machine-resolvable `file_path`/`line_range`
ref — still lacks `corpus_id`, `recipe@version` and `ordinal`, and two of those three
(`recipe@version`, `ordinal`) are structurally unsuppliable for this engine, not merely absent
from this particular call. The native-chunking case genuinely produces a machine-resolvable
partial ref (a real `file_path` plus a derivable `content_hash`) — it is not the empty result the
falsifier's refutation condition names — but it never reaches full `T1` `ChunkRef` coverage,
because two of the four required fields have no source in this engine's data model at all.

## Leg 2 — consuming machine chunks (disposition: not runnable as worded)

`PARTS.md ## §X`'s Falsifier-4 finding, carried forward verbatim: for any opaque node whose only
ingestion API is a filesystem path rather than a typed evidence parameter, the two-leg design may
not distinguish two genuinely different code paths at all.

**Disposition: not runnable as worded at this engine's ingestion API.** Confirmed again this
session against the live 0.10.8 binary, not merely re-read from `PARTS.md`: `index_repository`'s
only content-bearing input is `repo_path`, a filesystem path (`mcp.list_tools()`'s own
`input_schema` for the tool carries no chunk/evidence parameter of any kind — re-checked live this
session, matching §X condition 6's own code-verified finding against the pinned clone).

Per `05-RESEARCH.md` Pitfall 3, this document does not attempt either route that would make the
leg superficially "run":

- **Modifying the vendored engine to accept pre-chunked text** — an intrusive change to a
  black-box part this project's own §6/§8 framing treats as something earned by decomposition, not
  patched around.
- **Writing the machine's chunks to a temporary on-disk directory and pointing `repo_path` at
  it** — this does not test "consuming machine chunks" as a typed hand-off at all; the engine
  would still re-parse raw bytes from disk exactly as it does for any other file, collapsing this
  leg back into Leg 1 by construction rather than exercising a genuinely different code path.

**The structural reason, stated in `PARTS.md ## §X.5`'s own words:** "for any opaque node whose
only ingestion API is a filesystem path rather than a typed evidence parameter, the two-leg design
may not distinguish two genuinely different code paths at all." Nothing about the version drift
between the pinned clone (`61b3b1b2`) and the installed binary (`0.10.8`) changes this — the
finding is about the shape of the tool's own input schema, re-confirmed unchanged live this
session, not about a version-specific implementation detail that could have moved.

**What would have to change for this leg to become runnable:** `index_repository` (or a sibling
tool) would need a second, typed input parameter accepting pre-chunked evidence directly — e.g. a
`chunks: [{text, source_ref}]` argument alongside `repo_path` — which does not exist in this
engine's declared surface today and would itself be a decomposition of the engine's own ingestion
boundary, the exact kind of change `PARTS.md ## §X`'s "admission cost, not recut cost" framing
treats as out of scope for a whole-engine opaque admission.

## Verdict — what Falsifier 4 calibrates

The falsifier's own refutation condition — "neither case can emit a machine-resolvable ref at
all" — **is not met**: Leg 1's `get_code_snippet` calls produced a real, machine-resolvable
`file_path`/`line_range` ref with a derived `content_hash`, against a real repository, this
session. The section (`CONTRACT.md ## §4`) is **not refuted**.

Neither is the falsifier's optimistic branch reached in full: the native-chunking case does *not*
produce a complete `ChunkRef` — it is capped `below_T1` unconditionally, because `recipe@version`
and `ordinal` have no source anywhere in this engine's data model, independent of which tool is
called or which repository is indexed. This is a **third, more specific outcome** than the two the
falsifier's own text anticipates ("even the native-chunking case…" vs. "only the machine-chunk
case…"): for a self-contained, no-recipe opaque engine, T1 coverage does not cost "the chunker
surrender" (Leg 2 is not runnable at all, so there is no machine-chunk case to surrender to) — it
costs a recipe/corpus concept this engine's data model does not have, at any leg, for any tool.

**What this calibrates:** `CONTRACT.md ## §4`'s evidence-tier machinery (the `T0`–`T3` ladder and
its `ChunkRef` shape) is confirmed workable against a real black-box engine — partial refs
resolve, tier-capping behaves as designed, no evidence silently rounds up to a tier it did not
earn. It also confirms `PARTS.md ## §X.5`'s own finding was correct and is now evidenced rather
than merely argued: the two-leg design, as worded, cannot be run in full against this specific
engine shape, because the shape itself (filesystem-path-only ingestion, no recipe concept) removes
one leg from existing at all rather than merely making it hard to run. Falsifier 4 calibrates the
contract's evidence machinery; it does not halt the ladder — this admission proceeds on Leg 1's
real, tier-capped result and Leg 2's recorded disposition, exactly as `PARTS.md ## §X.5` already
anticipated it would.
