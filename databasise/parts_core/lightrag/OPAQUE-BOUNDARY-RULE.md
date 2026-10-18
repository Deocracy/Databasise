# The inside-vs-across-boundary change rule for LightRAG's opaque corpus-side parts

This document is addressed to a future contributor who has not read any GSD plan. If you are
about to touch `databasise/parts_core/lightrag/full_ingest.py`, `full_delete.py`,
`v1_index_sync.py`, or anything under `databasise/foreign/` that those parts launch, read this
first.

## 1. What this rule is for

`lightrag/full-ingest@0.2.0` and `lightrag/full-delete@0.2.0` admit LightRAG's ~1,786-line ingest
core as an **opaque node** (CONTRACT §8) precisely because it is too entangled to decompose
cleanly today. Under schedule pressure, an opaque node like this one is exactly the place where new
capability gets added the fast way: by editing inside the already-opaque core instead of authoring
a proper fitted node. `.planning/research/PITFALLS.md` names this failure directly — "the
opaque-node 'quarantine' quietly become[s] a dumping ground" — and this document exists to stop it
before it starts, not to audit it after the fact.

This rule is **build-added discipline, not a CONTRACT clause**. CONTRACT §8 states what an opaque
node must satisfy to be admitted in the first place; it says nothing about what may change inside
that node afterward without re-running admission. This document is that missing "afterward" rule,
scoped to these two parts and to `lightrag/v1-index-sync@0.1.0`, the opaque mirror that follows
either of them (it reads v1's committed index and writes the v2 stores through `ctx.stores`).

**Version history.** Phase 11 batched every change to these ports' effects, verdicts and driver
protocol into **one** bump to `@0.2.0` (11-03-PLAN.md, D-06), with a fresh eleven-verdict record
per port; the sync part is new at `@0.1.0` and is pinned the same way. No later Phase 11 plan
edits the driver script or this document.

## 2. Across the boundary — a change here requires a version bump and re-admission

Every identifier below is a **published boundary value**. Changing any one of them — for either
part — means minting a new `name@version` per CONTRACT §0 and re-running admission (a fresh
eleven-`ConditionVerdict` `AdmissionRecord`, re-validated by `PartRegistry.register`). It is never a
same-version edit, no matter how small the diff looks.

**The `Part` declaration itself** (`databasise/parts_core/declared_only.py`), for each of
`LIGHTRAG_FULL_INGEST_PART`, `LIGHTRAG_FULL_DELETE_PART` and `LIGHTRAG_V1_INDEX_SYNC_PART`:

- `name_at_version` — today `lightrag/full-ingest@0.2.0`, `lightrag/full-delete@0.2.0` and
  `lightrag/v1-index-sync@0.1.0`.
- `kind` — today `"opaque"` for all three; this is the literal value `PartRegistry.register`'s
  admission gate and `databasise.validator.execution_mode.derive_execution_mode`'s subprocess
  placement decision both key on.
- `structural_depth` — today `"opaque"` for all three.
- `effects` (the `effects[]` list) — today `["calls_llm", "mutates_store", "reads_kv",
  "reads_graph"]` for both ingest and delete, and `["mutates_store", "writes_kv", "writes_vector",
  "writes_graph"]` for the sync. Ingest and delete are separate ports on purpose (§19.6, see §4
  below) — widening or narrowing any list is a boundary change regardless of which direction it
  moves. `@0.2.0` dropped ingest's `writes_artifact` (v1 writes no artifact, it mutates its own
  working dir, LRAG-03) and added delete's `calls_llm` (a partial-rebuild delete reaches the LLM
  and is metered, LRAG-11).
- `upstream_ref` — today `v1/lightrag/pipeline.py` (ingest), `v1/lightrag/lightrag.py` (delete)
  and `v1/lightrag/kg/faiss_impl.py` (sync).
- `artifact_scope` — today `None` for all three (`@0.2.0` dropped ingest's `"quarantined"`).

**Every field of the part's `AdmissionRecord`** (`databasise/parts/admission.py`), for each part's
own record (`LIGHTRAG_FULL_INGEST_ADMISSION` / `LIGHTRAG_FULL_DELETE_ADMISSION` /
`LIGHTRAG_V1_INDEX_SYNC_ADMISSION`):

- `part_name_at_version` and `entry_path` — the record's own identity fields.
- `storage`, `wall_clock_ceiling_seconds`, `wall_clock_ceiling_basis`, `feed_tier`, `ttl_days`,
  `network_namespace`, `manifest_source`.
- `verdicts` — every one of the eleven `ConditionVerdict` entries, matched by `(condition,
  verdict)` pair (the concrete `verdict` string for each of the eleven numbered §8 conditions this
  record carries) — never by the `evidence` prose accompanying it, which is free to reword.
- `environment_hash` carries the field, but the compat test (§5) deliberately does not pin its
  computed digest value: it is a content hash over `v1/uv.lock` and `v1/.python-version`, both
  named in §3 below as free to change (a routine `uv sync` bump inside v1's own venv). Pinning the
  digest's exact value would turn that free change into a false-positive boundary violation. What
  the test does check is that both ports' `environment_hash` values are present, share the
  `sha256:` prefix, and agree with each other.

**How the records number CONTRACT §8** (LRAG-12). Each record's verdicts follow CONTRACT's own
numbering: condition 3 carries network denial by construction (the machine injects the only model
endpoints) and the spend rule — the driver hands `TokenTracker` to both model functions and the
part reports `counted_by` `v1-subprocess` from real usage, `none` for no model call, and
`unbudgetable` when the provider reports no usage; condition 5 states `storage` `self-contained`
(v1 writes only `<store_root>/<workspace>/lightrag-v1`) and no artifact scope; condition 8 is
`ttl_days` 90 with each renewal recorded in the ledger (`machine-side-obligation`); condition 9 is
explicit `part_ref` invocations counted as data, not a promotion trigger
(`machine-side-obligation`).

**The driver script's protocol** (`databasise/foreign/v1_corpus_driver_script.py`):

- The stdin key set for each operation the driver dispatches on.
- The stdout key set for each of those same operations.
- The set of operation names the driver's `_run()` dispatch recognizes at all — adding, removing,
  or renaming an operation is a boundary change even if every existing operation's own key sets
  stay untouched.

| op | stdin keys | stdout keys |
| --- | --- | --- |
| `ingest` | `documents`, `track_id`, `working_dir`, `file_paths`, `docs_format`, `input_dir`, `retry_doc_ids` | `track_id`, `enqueued`, `usage` |
| `delete` | `doc_id`, `delete_llm_cache`, `working_dir` | `status`, `doc_id`, `message`, `status_code`, `file_path`, `usage` |
| `status` | `track_id`, `limit`, `offset`, `working_dir` | `counts`, `documents`, `total` |
| `health` | (none) | `configured`, `missing_keys`, `unsupported_keys` |

`@0.2.0` removed the two proof-only ops `entities` and `entity_info` (D-05): the driver refuses
them as unknown ops.

**Exit channels.** Exit 0 with the stdout keys above is success; exit 1 is any failure (a
traceback on stderr). **Exit 3** is the configuration refusal (D-12): before any op but `health`
runs, `main` checks the environment v1 sees and, when a required key is missing or blank or a
storage key names a backend the sync cannot read, writes
`{"error": "v1_not_configured", "missing_keys": [...], "unsupported_keys": [...]}` — key names
only, never values. `health` builds no facade and creates no working dir (D-14); it reports the
same check as `configured`, `missing_keys` and `unsupported_keys`.

`ingest` (`@0.2.0`): a `pending_parse` job sets `INPUT_DIR` to `input_dir` and enqueues the staged
file with no `ids=`, so v1 parses the file's own bytes; v1 mints `doc-<md5(basename)>` and the id
stem rule maps it back (the staged name is `<document_id><suffix>`, so `Path(file_path).stem` is
our id; a text-ingested row keeps our id). Processing is restricted to this run's targets by an
instance-level wrapper around `doc_status.get_docs_by_statuses`; `retry_doc_ids` names the targets
of a retry. `enqueued` excludes the duplicates v1 recorded under the caller's track id. `usage` is
`{"llm": ..., "embedding": ...}` from two `TokenTracker`s, never summed. `delete` resolves
`doc_id` by the same stem rule and returns `usage` the same way (D-13).

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
separates `lightrag/full-ingest` from `lightrag/full-delete`: two invocations that
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
