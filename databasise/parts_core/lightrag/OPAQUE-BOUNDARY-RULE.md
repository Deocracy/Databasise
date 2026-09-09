# The inside-vs-across-boundary change rule for LightRAG's opaque corpus-side parts

This document is addressed to a future contributor who has not read any GSD plan. If you are
about to touch `databasise/parts_core/lightrag/full_ingest.py`, `full_delete.py`, or anything
under `databasise/foreign/` that those two parts launch, read this first.

## 1. What this rule is for

`lightrag/full-ingest@0.1.0` and `lightrag/full-delete@0.1.0` admit LightRAG's ~1,786-line ingest
core as an **opaque node** (CONTRACT §8) precisely because it is too entangled to decompose
cleanly today. Under schedule pressure, an opaque node like this one is exactly the place where new
capability gets added the fast way: by editing inside the already-opaque core instead of authoring
a proper fitted node. `.planning/research/PITFALLS.md` names this failure directly — "the
opaque-node 'quarantine' quietly become[s] a dumping ground" — and this document exists to stop it
before it starts, not to audit it after the fact.

This rule is **build-added discipline, not a CONTRACT clause**. CONTRACT §8 states what an opaque
node must satisfy to be admitted in the first place; it says nothing about what may change inside
that node afterward without re-running admission. This document is that missing "afterward" rule,
scoped to these two parts.

## 2. Across the boundary — a change here requires a version bump and re-admission

Every identifier below is a **published boundary value**. Changing any one of them — for either
part — means minting a new `name@version` per CONTRACT §0 and re-running admission (a fresh
eleven-`ConditionVerdict` `AdmissionRecord`, re-validated by `PartRegistry.register`). It is never a
same-version edit, no matter how small the diff looks.

**The `Part` declaration itself** (`databasise/parts_core/declared_only.py`), for each of
`LIGHTRAG_FULL_INGEST_PART` and `LIGHTRAG_FULL_DELETE_PART`:

- `name_at_version` — today `lightrag/full-ingest@0.1.0` and `lightrag/full-delete@0.1.0`.
- `kind` — today `"opaque"` for both; this is the literal value `PartRegistry.register`'s
  admission gate and `databasise.validator.execution_mode.derive_execution_mode`'s subprocess
  placement decision both key on.
- `structural_depth` — today `"opaque"` for both.
- `effects[]` — today `["calls_llm", "writes_artifact", "reads_kv", "reads_graph"]` for ingest and
  `["mutates_store", "reads_kv", "reads_graph"]` for delete. These two lists differ on purpose
  (§19.6, see §4 below) — widening or narrowing either list is a boundary change regardless of
  which direction it moves.
- `upstream_ref` — today `v1/lightrag/pipeline.py` (ingest) and `v1/lightrag/lightrag.py` (delete).
- `artifact_scope` — today `"quarantined"` (ingest) and `None` (delete).

**Every field of the part's `AdmissionRecord`** (`databasise/parts/admission.py`), for each part's
own record (`LIGHTRAG_FULL_INGEST_ADMISSION` / `LIGHTRAG_FULL_DELETE_ADMISSION`):

- `storage`, `wall_clock_ceiling_seconds`, `feed_tier`, `ttl_days`, `network_namespace`,
  `environment_hash`, `manifest_source`, and every one of the eleven `ConditionVerdict` entries
  (matched by `(condition, verdict)` pair — the concrete `verdict` string for each of the eleven
  numbered §8 conditions this record carries).

**The driver script's protocol** (`databasise/foreign/v1_corpus_driver_script.py`):

- The stdin key set for each operation the driver dispatches on (`ingest`, `delete`, `status`,
  `health`, and the two proof-only ops `entities`/`entity_info`).
- The stdout key set for each of those same operations.
- The set of operation names the driver's `_run()` dispatch recognizes at all — adding, removing,
  or renaming an operation is a boundary change even if every existing operation's own key sets
  stay untouched.

State the obligation plainly: changing any identifier or key set named above means minting a new
`name@version` per CONTRACT §0 and re-running admission for that part. It is never landed as a
silent same-version edit — `databasise/tests/parts_core/lightrag/test_full_ingest_compat.py` is
what turns "never" from a convention into a red test (§5 below).

## 3. Inside the boundary — free to change

Everything inside the subprocess and inside v1's own venv is free to change with no version bump
and no re-admission. This is the entire point of admitting the core opaque in the first place —
concretely, and without needing anyone's sign-off:

- v1's own `LightRAG` facade construction (`_build_rag` in the driver script) — which storage
  backends it selects, its constructor arguments, its internal wiring.
- The chunking strategy, the extraction prompt, the summarization prompt — any of v1's own prompt
  or pipeline text.
- v1's own internal concurrency (how many concurrent LLM calls `apipeline_process_enqueue_documents`
  issues, in what order).
- v1's own dependency versions inside `v1/.venv` (a `uv sync` bump to `lightrag`'s own transitive
  dependencies, so long as the pinned interpreter and the driver script's own imports still work).
- The internals of `adelete_by_doc_id`'s reference-counting algorithm, or any other v1-internal
  algorithm the driver script calls into but does not itself reimplement.

A change confined to this list needs no version bump and no re-admission, precisely because none of
it is a value either `Part` declares or either admission record pins.

## 4. The one thing that is neither

Adding a **new capability** — a new document format, a new retrieval behaviour, a new mutation
surface — is not an internal change even when the diff physically lands inside the subprocess,
because it widens what the node *does* without widening what it *declared*. A new document-format
handler added inside the driver script's `_run_ingest` looks, from the diff, exactly like an
internal change (§3) — it touches only files under `databasise/foreign/` and calls only v1's own
API — but it is not one, because the node's declared `effects[]`/`feed_tier`/operation set never
moved to say so.

The required response: author a fitted node for the new capability, or make it a genuinely new
declared operation on a new port with its own effects and its own admission record — never a quiet
widening of an existing port's undeclared behaviour. This is the same §19.6 rule that already
separates `lightrag/full-ingest@0.1.0` from `lightrag/full-delete@0.1.0`: two invocations that
differ in declared effects MUST be two separate ports, never one node quietly doing more than its
own declaration says.

This rests on CONTRACT §8's own framing: every restriction placed on an opaque node "names
something an opaque part has not yet earned, not a permanent exclusion" — earned only by
decomposition (§6's node-to-subgraph mechanism), never by exception or by a convenient same-version
edit that routes around the restriction instead of earning its way past it.

## 5. How this is enforced

`databasise/tests/parts_core/lightrag/test_full_ingest_compat.py` is the enforcement half of this
document. It pins every identifier and key set named in §2 as a literal value and asserts it
against the live `Part`/`AdmissionRecord`/driver-script AST — a diff to any pinned value fails the
test, by design. It pins nothing named in §3: no assertion in that file reaches into v1's facade
construction, a chunking parameter, a prompt, or any v1-internal module.

A red run of this test is the intended signal, not an obstacle to route around. It means a boundary
value moved and the version-bump obligation stated in §2 is owed — the fix is never to update the
test's pinned literal to match the new value without also bumping `name_at_version` and re-running
admission. Silencing the test that way defeats the entire purpose of pinning it.

## 6. Warning signs

- A diff that touches either part's declared `effects`/`artifact_scope` (or either admission
  record's fields) with no corresponding change to `name_at_version` and no fresh admission record.
- A new document-format handler, or any other new capability, added inside the ~1,786-line v1
  ingest core (or its driver-script wrapper) rather than as a new fitted node or a new declared
  port.
