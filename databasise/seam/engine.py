"""``databasise.seam.engine`` — the async ``Databasise`` seam object (D-01), the phase's primary
noun. A caller reaches the engine with a §18.1 query object and receives a §18.2 closed
``ResponseEnvelope`` — no wiring name, arm name, node id or instance hash crossing the boundary in
either direction.

**Pattern 1 (04-RESEARCH.md): generalizing ``run_arm.py``'s call shape.** ``query()``'s body
follows ``databasise/parity/run_arm.py:run_arm``'s established sequence exactly — resolve, inject
query, inject a token allowance, parse, build stores, ``scheduler.run_wiring``, construct a
``RunRecord`` — the one difference being the wiring comes from selector resolution (§18.4) rather
than a hardcoded arm name, and the ``RunRecord`` is redacted into a closed envelope rather than
returned as the un-redacted dict ``run_arm`` returns. ``provides`` is read off the raw resolved
dict, never through ``ParsedWiring`` (Pitfall 1) — ``run_arm.py``'s own precedent.

**04-02: evidence references and the token breakdown.** Before the ``RunRecord`` (and the
scheduler's raw ``results`` dict) go out of scope, ``query()`` mints the envelope's ``evidence``
list from the resolved wiring's own declared retrieval position's output (06-01-PLAN.md:
``evidence_position``, preserving that node's own output order verbatim — Task 2's own no-re-sort
rule) and assembles the
``token_accounting`` breakdown from every node's own ``TokenAccounting`` (``databasise.seam.tokens
.assemble_token_breakdown``). The breakdown assembly raises before any envelope is constructed if a
node reports the ``unbudgetable`` sentinel (D-08) — that exception is left to propagate out of
``query()`` unmodified.

**04-04, Task 1: the opaque trace reference (API-10, D-06).** ``query()`` persists the ``RunRecord``
into ``databasise.seam.trace_store.TraceStore`` and mints an opaque token before the record goes
out of scope, binding it to the envelope's ``trace_token`` field — 04-01's declared-but-empty
placeholder. ``resolve_trace`` is the third §18 operation the seam exposes (per part kind, never
per modality): it returns the run's node-by-node trace only when the caller sets ``debug``; without
it, the response is filtered to an explicit allow-list of non-identity fields (CR-02) so a caller
that did not ask for internal identities does not receive them (T-04-19).

**04-04, Task 2: MACH-11 — the out-of-``deps`` store-mutation event (D-09, FA-08).** ``query()``
passes a recorder callable to ``scheduler.run_wiring`` that records every ``(node_id, "store",
store_key)`` touch the scheduler's own ``_ScopedStoresView`` reports. After the run, ``_mach11_events``
correlates: for every node whose registered ``Part`` declares ``mutates_store``, the store keys it
touched are compared against ``_accounted_store_keys`` — the union, over that node's own declared
``deps`` (``ParsedWiring.deps``), of any ``reads_*``/``writes_*`` effect its dependency's own
resolved ``Part`` declares. A touched key no declared dependency accounts for is an out-of-``deps``
mutation and produces one ``SeamEvent``, carrying the part's registered ``name@version`` (never a
node id), its own token spend, and an outcome drawn from ``ResponseEnvelope``'s closed vocabulary.

**This correlation rule is defined by this plan, not by CONTRACT (FA-08) — read this before
extending it.** ``mutates_store`` itself names no specific store key (§2's vocabulary keeps it
opaque on purpose), so it never contributes to ``_accounted_store_keys`` on its own; only a
dependency's own concrete ``reads_*``/``writes_*`` effect counts as "this data flow accounts for
that store".

**05-03-PLAN.md Task 2: the rule re-checked against a real deleting part — two touch kinds, not
one.** As Phase 4 built this correlation, it keyed on store touches the scheduler's own
``_ScopedStoresView`` observes — a machine-held store handle the node reads/writes through. Phase
5's two corpus-side ports (``lightrag/full-ingest@0.1.0``, ``lightrag/full-delete@0.1.0``) are
hosted at the ``subprocess`` placement: their real store mutation happens inside v1's own
subprocess, against v1's own storage handles, which the machine never touches directly — the
machine can observe *nothing* for a ``mutates_store`` node at that placement. Such a node instead
reports its own touches through ``databasise.parts.schema.NodeContext.record_store_touch``,
threaded by the scheduler to the run's recorder with the ``TOUCH_KIND_NODE_REPORTED`` kind
(``databasise.runner.scheduler``) — distinct from the machine-observed ``TOUCH_KIND_OBSERVED`` kind
``_ScopedStoresView`` emits. ``_mach11_events`` treats both kinds as touches for a ``mutates_store``
part, but the two are never merged into one undifferentiated tuple: a reader can always tell
observed evidence (the machine crossed a handle it holds) from a self-report (the node says it
mutated something the machine could not see). ``lightrag/full-delete@0.1.0`` is the first real,
non-fixture part to exercise this correlation — the in-``deps`` no-event case Phase 4 already
proved against fixture parts remains unchanged and untouched by this addition.

**04-05, Task 2: ``query_stream`` (API-04, D-16) shares ``query``'s execution, never forks it.**
``query()``'s entire body — selector resolution, run execution, evidence minting, token-breakdown
assembly, MACH-11 correlation, trace persistence, envelope construction — now lives in
``_execute()``. ``query()`` is exactly ``return await self._execute(...)``; ``query_stream()`` is
an async generator over the identical ``_execute()`` call, shaping the already-assembled
envelope's own fields incrementally (one event per evidence reference, in the envelope's own
order, then one final event carrying every remaining field) rather than fabricating a second,
divergent execution path or a token-level stream the underlying scheduler does not itself produce.

**05-01-PLAN.md: ``ingest`` — the fourth §18 operation, an operation rather than a selector.**
``query``/``query_stream``/``resolve_evidence``/``resolve_trace`` are all reads over an already-
admitted corpus; ``ingest`` is the first write. It dispatches the single named
``lightrag/full-ingest`` opaque Part directly (loading ``databasise/wirings/lightrag/corpus-
ingest.json``, stamping a fresh caller document id and v1 track id onto the node's config, then the
same ``parse_wiring`` -> ``_build_stores`` -> ``scheduler.run_wiring`` sequence ``_execute`` uses)
rather than resolving a selector, because no selector shape can express "put this document into the
corpus" — there is no candidate wiring to choose among, only one fixed operation to perform.

**05-03-PLAN.md: ``delete_document`` — the fifth §18 operation, and MACH-11's first real
correlation.** Mirrors ``ingest``'s own direct-dispatch shape exactly (loading
``databasise/wirings/lightrag/corpus-delete.json``, stamping the target document id onto the
node's config, the identical ``parse_wiring`` -> ``_build_stores`` -> ``scheduler.run_wiring``
sequence) — with one addition ``ingest`` does not need: it passes the same recorder callable
``_execute()`` passes, because ``lightrag/full-delete@0.1.0`` is the first production Part to
declare ``mutates_store``. See ``_mach11_events``'s own docstring for the two-touch-kind
correlation rule this exercises for real.

**05-04-PLAN.md Task 1: bounded status/health/counts — a liveness/status read is owned by the
§17 adapter, never a registered port.** ``get_job_status``/``health``/``corpus_status``/
``document_counts`` are this seam's sixth through ninth operations (API-01's polling half,
API-06). Unlike ``ingest``/``delete_document``, none of the four dispatches a wiring through the
real scheduler — a bounded liveness/status read produces no evidence, mutates nothing, and
declares no effect, so it reaches ``databasise.foreign.run_corpus_op`` directly, exactly as
``ingest``/``delete_document``'s own opaque Part bodies do, but with no ``Part``/wiring/scheduler
step in between. ``get_job_status``/``corpus_status`` call the single ``"status"`` op with
different ``track_id``/``Page`` arguments; ``document_counts`` calls the same op with a
zero-length page and reads only its ``counts`` field; ``health`` calls the ``"health"`` op *and*
additionally probes the machine's own kv/vector/graph stores directly (never through the
scheduler), catching each store's own construction exception into a reachability map rather than
letting it propagate — an unreachable participant is reported as unreachable, never a raised
refusal. ``get_job_status`` raises ``UnknownJobError`` when the driver reports zero total matching
documents for the given job id — the same raise-not-None precedent ``TraceStore.resolve``
established, restated here for an unknown ingest job rather than an unknown trace reference.

**CR-01 gap closure: the REST transport reuses this event-shaping, never reimplements it.** The
CR-01 review fix moved envelope resolution into a FastAPI ``Depends()`` dependency so a
``SeamRefusalError`` is known and mapped to a 422 *before* the SSE response begins — but an async
generator's own body (including ``query_stream()``'s) does not run any code until it is first
iterated, so ``query_stream()`` itself cannot supply that eager-refusal guarantee to a REST caller.
The module-level :func:`stream_envelope_events` below is the fix: it is the one event-shaping
implementation both ``query_stream()`` and ``databasise.seam.rest``'s ``/query/stream`` endpoint
iterate over. REST resolves the envelope eagerly via the identical ``_execute()`` call (through
``query()``, in its own ``Depends()`` dependency) and then shapes it with the exact same function
``query_stream()`` shapes it with — one shared shaping implementation, never two independently
maintained copies that could silently diverge.

**06-10-PLAN.md: ``ingest`` becomes a two-arm write, closing Gap 1(a).** Before this plan
``ingest()``/``delete_document()`` dispatched exactly one hardcoded LightRAG wiring each, via the
module constants ``_INGEST_WIRING_PATH``/``_INGEST_NODE_ID``/``_DELETE_WIRING_PATH``/
``_DELETE_NODE_ID``. This plan promotes the corpus wiring path to a function of the resolved
*target modality* (:func:`_corpus_wiring`, keyed by :func:`databasise.wirings.resolve.wiring_family`)
— the same §18.4 selector ``query``/``compare`` already accept now also names which fitted
modality's index a write lands in. The on-disk layout ``databasise/wirings/<family>/corpus-
<operation>.json`` **is** the lookup table (no dict, no registry): a file that exists is a
supported write path, a file that does not exist is
:class:`~databasise.seam.refusals.NoWritePathForModalityError`. ``ingest()`` reads the node whose
config is stamped from the resolved corpus wiring's own ``consumes_documents[0]``, and the node
whose result is read from its own ``provides[0]`` — never a module constant, so a modality added
later needs only two files on disk. ``delete_document()`` gains the identical ``selector``
parameter (Task 2): a HippoRAG-selected delete raised ``NoWritePathForModalityError`` by name
until Phase 12 D-12 (HIPP-16) shipped ``wirings/hipporag/corpus-delete.json``: the
``hipporag/document-remover`` part retracts a document's chunk/entity/fact vectors and its
fact/passage/synonymy edges by the ``doc:<id>`` manifest, and never touches the v1 working dir; an
unselected or LightRAG-selected delete resolves to the identical wiring the former
``_DELETE_WIRING_PATH`` constant named, byte-for-byte.

**10-05-PLAN.md (STOR-06, D-07): a successful run commits through prepare-all, then commit-all.**
:func:`_commit_all` holds one ``asyncio.Lock`` per (event loop, store root) from the first
``prepare`` to the last ``commit_prepared``. Every store prepares first: kv runs its DML inside an
uncommitted ``BEGIN IMMEDIATE`` transaction, the vector store writes its ``.tmp`` file pair, and the
graph store stages a ``multi_transact``. Any prepare failure aborts every store, commits nothing and
raises ``ForeignEngineRefusalError(failure_class="StoreFault")``. The lock is taken before any DML,
so a second run waits on an ``await`` instead of blocking the loop on sqlite's busy timeout or
RocksDB's one-second key-lock timeout. Residual window: commits run kv, then vector, then graph,
and are not one transaction. A crash between two stores' commits, or between the vector store's two
``os.replace`` calls, leaves a partial commit; the vector sidecar checksum detects a torn index pair
at the next open (``VectorStoreCorruptedError``).

**11-01-PLAN.md (D-01, M-04 option b, LRAG-01): the LightRAG write path is v1 then a mirror.** Every
LightRAG corpus op uses one v1 working dir per engine, ``<store_root>/<workspace>/lightrag-v1``
(:meth:`Databasise._v1_working_dir`), stamped onto every ``lightrag/*`` corpus node's config and
passed to every status/health ``run_corpus_op`` call; there is no repo-global default. The corpus
wirings run v1's own ingest or delete subprocess, then ``lightrag/v1-index-sync``, which mirrors
v1's committed index into the staged v2 stores the query arms read. Residual window: v1 has
already committed by the time the v2 commit runs. If the v2 commit fails, v1 and v2 diverge until
the next sync, which re-mirrors the whole index and so heals them. Deletes heal too: the sync's
prune manifest keeps the ids it pruned until every store committed (11 REVIEW A-WR-01).

**11-06-PLAN.md (D-07, LRAG-04): one LightRAG write per working dir at a time.** Phase 8 guarantees
one engine process per store root, so an in-process ``threading.Lock`` per resolved v1 working dir
(:func:`_write_gate`) serializes every LightRAG ingest and delete. It is taken right after
``_build_stores`` (the STOR-02 first-error pin) and held through the v1 subprocess, the index sync's
manifest read and staging, the commit or drop, and the inbox cleanup, so two writes can never read
the same prune manifest. A second write is refused with ``StoreBusyError(store_kind="corpus")``
(409), not queued. Reads take no gate. A cancelled or timed-out write keeps the gate until the v1
worker thread returns (11 REVIEW A-CR-01, A2-WR-01).

**12-06-PLAN.md (D-14, HIPP-16): HippoRAG writes queue per workspace.** HippoRAG has no v1 dir, so
its ingests and deletes take a separate per-workspace gate keyed on ``<store_root>/<workspace>/
hipporag-write`` (:meth:`Databasise._hipporag_gate_path`, never created on disk), entered by
:func:`_serialising_write_gate` before ``_build_stores`` because the Faiss store reads its committed
snapshot at construction. Their read-merge-write steps (edge accumulation, fact provenance, document
removal) would lose updates if two writers interleaved, so a second HippoRAG writer waits, polling,
and is refused with ``StoreBusyError(store_kind="corpus")`` only after ``_HIPPORAG_GATE_WAIT_SECONDS``.
LightRAG writes keep refusing at once (D-07 above); a held v1 gate never delays a HippoRAG write.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
import hashlib
import json
import logging
import sqlite3
import sys
import threading
import time
import traceback
import uuid
import weakref
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator, Sequence
from pathlib import Path
from typing import Any

from databasise.clients import CLIENT_EFFECT_TO_KEY
from databasise.foreign import CorpusOpBusyError, run_corpus_op
from databasise.foreign.v1_corpus_adapter import (
    DEFAULT_V1_INTERPRETER,
    STATUS_WALL_CLOCK_CEILING_SECONDS,
    redact_secrets,
)
from databasise.identity.canon import canonicalise
from databasise.ledger.ledger import Ledger, LedgerRecord
from databasise.parts.registry import PartRegistry, default_registry
from databasise.parts.schema import Depth
from databasise.parts_core import EFFECT_TO_STORE
from databasise.parts_core.lightrag import chunk_vector as _chunk_vector
from databasise.parts_core.lightrag import entity_lookup as _entity_lookup
from databasise.parts_core.lightrag import relation_lookup as _relation_lookup
from databasise.parts_core.lightrag.full_ingest import ABANDONED_WORKERS
from databasise.parts_core.lightrag.v1_index_sync import V1_INDEX_SYNC_MANIFEST_KEY
from databasise.runner import scheduler as _scheduler
from databasise.runner.trace import NodeTrace, RunRecord
from databasise.seam.corpus import (
    _URL_RE,
    CorpusStatus,
    DeletionOutcome,
    DocumentCounts,
    DocumentStatusEntry,
    HealthReport,
    IngestDocument,
    IngestJob,
    JobStatus,
    Page,
    generated_on_disk_name,
    upload_suffix,
)
from databasise.seam.envelope import PromotionResult, ResponseEnvelope, SeamEvent
from databasise.seam.jobs_store import JobFamilyStore
from databasise.seam.evidence import (
    CHUNKS_NAMESPACE,
    EvidenceRef,
    MalformedEvidenceItemError,
    mint_evidence_refs,
    resolve_evidence_ref,
    validate_evidence_namespace,
)
from databasise.seam.compare import comparison_keys
from databasise.seam.promotion import (
    CHANGE_ORIGINS,
    PROMOTION_VERBS,
    PROVENANCE_OPERATOR_ASSERTED,
    PromotionVerb,
    RECORD_KIND_PROMOTION,
    RECORD_KIND_ROLLBACK,
    RECORD_KIND_TOMBSTONE,
    _GATE_VERBS,
    _NOT_BUILT_VERBS,
    declared_surface,
    derive_mutation_class,
    enforce_gate_verb_posture,
    mint_version,
    resolve_single_arm,
    resolved_wiring_for_arm,
)
from databasise.seam.query import QueryObject, check_consumable
from databasise.seam.refusals import (
    ActiveGenerationRetirementError,
    DocumentNotInterruptedError,
    DuplicateDocumentIdError,
    EmptyComparisonRequestError,
    EmptyNamespaceError,
    ForeignEngineRefusalError,
    GateVerbNotBuiltError,
    InvalidChangeOriginError,
    InvalidPromotionAliasError,
    MutableStoreComparisonExcludedError,
    NoRawUploadPathForModalityError,
    NoWritePathForModalityError,
    SeamRefusalError,
    StoreBusyError,
    TombstonedGenerationError,
    UnknownDocumentError,
    UnknownGenerationVersionError,
    UnknownJobError,
    UnparseableWiringError,
    UnrecognisedPromotionVerbError,
    UnresolvableEvidenceReferenceError,
)
from databasise.seam.selectors import (
    _INSTANCE_HASH_PATTERN,
    Selector,
    _wiring_effects,
    resolve_selector,
)
from databasise.seam.tokens import TokenBreakdownEntry, assemble_token_breakdown
from databasise.seam.trace_store import TraceStore
from databasise.stores.graph import CozoGraphStore, GraphStoreBusyError
from databasise.stores.kv import SqliteKVStore
from databasise.stores.probes import list_kv_prefix, probe_graph, probe_kv, probe_vector
from databasise.stores.vector import MultiNamespaceVectorStore, VectorStoreCorruptedError, load_committed
from databasise.validator.parse import ParsedWiring, parse_wiring
from databasise.wirings.resolve import wiring_family, without_recipe_only_nodes

# 06-10-PLAN.md: the per-modality corpus-wiring root — databasise/wirings/<family>/corpus-
# <operation>.json is itself the write-path lookup table (see _corpus_wiring below); no dict or
# registry duplicates it. Resolved relative to this file, mirroring
# databasise/wirings/resolve.py's own Path(__file__)-relative load shape. Replaces the former
# _INGEST_WIRING_PATH/_INGEST_NODE_ID/_DELETE_WIRING_PATH/_DELETE_NODE_ID module constants, which
# named only LightRAG's own two corpus wirings — the node id each operation targets is now read
# off the resolved corpus wiring's own consumes_documents[0]/provides[0], never a module constant.
_WIRINGS_ROOT = Path(__file__).resolve().parent.parent / "wirings"

logger = logging.getLogger(__name__)


def _foreign_fault(
    operation: str, cause: BaseException, *, failure_class: str | None = None, node_id: str | None = None
) -> ForeignEngineRefusalError:
    """09-05-PLAN.md (SEAM-05, D-04): the one place an engine fault is built and logged, whether
    the v1 engine, a store (D-13) or the run itself (an early stop) failed. The full cause (stderr,
    traceback) goes to the server log exactly once; the returned refusal carries it privately and
    exposes only the operation and the allow-listed ``failure_class``.

    Phase 12 D-11 (A-WR-05): the full cause stays readable in-process on ``refusal.cause``; the log
    carries a redacted copy (exception type name plus a ``redact_secrets``-then-URL-scrubbed
    traceback) and no attached exception, so an in-process provider error cannot leak a key or URL."""
    refusal = ForeignEngineRefusalError(
        operation=operation, cause=cause, failure_class=failure_class, node_id=node_id
    )
    detail = _URL_RE.sub("<url>", redact_secrets("".join(traceback.format_exception(cause))))
    logger.error(
        "engine fault: operation=%s failure_class=%s node=%s cause=%s detail=%s",
        operation,
        refusal.failure_class,
        node_id or "-",
        type(cause).__name__,
        detail,
    )
    return refusal


def _is_store_fault(exc: BaseException) -> bool:
    """D-13: a sqlite error, or any exception type defined by ``databasise.stores`` or pycozo, is a
    store fault (judged by the type's module, so ``stores/`` need not export a common base)."""
    module = type(exc).__module__ or ""
    return isinstance(exc, sqlite3.Error) or module.startswith(("databasise.stores", "pycozo"))

def _log_staged_left(staged: Path) -> None:
    """09 REVIEW WR-04: a fault after the v1 run started leaves the staged upload in place (v1 may
    hold its path). Logged once, server-side, so an operator can reap it."""
    logger.warning("staged upload left in place after an ingest fault: %s", staged)


# 11-05 (D-09): the ingest faults after which v1 may still list the document, so its staged
# source is kept (and logged) for a delete or an 11-08 retry.
_KEEP_STAGED = frozenset({"CorpusOpTimeoutError", "CorpusOpSubprocessError", "MalformedDriverOutput"})


def _remove_staged(staged: Path) -> None:
    """11-05 (D-09, LRAG-09): remove a staged upload and the copy v1 moved to ``__parsed__/`` after
    parsing it. A removal error is logged and never fails the operation that already ran."""
    try:
        for path in (staged, staged.parent / "__parsed__" / staged.name):
            path.unlink(missing_ok=True)
    except OSError:
        logger.exception("could not remove the staged upload %s", staged)


# v1's own docs_format vocabulary (lightrag.constants.FULL_DOCS_FORMAT_RAW/_PENDING_PARSE),
# duplicated as bare string literals here rather than imported — databasise/tools/
# check_import_boundary.py forbids importing lightrag anywhere under databasise/ except the named
# subprocess-entry-point leaf scripts, and this module is not one of them.
_DOCS_FORMAT_RAW = "raw"
_DOCS_FORMAT_PENDING_PARSE = "pending_parse"

# The v1-native per-kind names the LightRAG wirings' kv/graph stores are keyed by — matching
# databasise/parity/run_arm.py's own _TEXT_CHUNKS_KIND/_GRAPH_KIND constants exactly.
_TEXT_CHUNKS_KIND = "text_chunks"
_GRAPH_KIND = "chunk_entity_relation"

# Every namespace of every shipped wiring, probed by health() (Phase 10 D-14). kv/graph come from the
# wirings' store_namespaces, vector from the part modules' *_NAMESPACE constants; test_health_probe.py
# fails if either drifts (research Pitfall 19).
_HEALTH_PROBES: tuple[tuple[str, str], ...] = (
    ("kv", _TEXT_CHUNKS_KIND),
    ("graph", _GRAPH_KIND),
    ("vector", "chunks"),
    ("vector", "entities"),
    ("vector", "relationships"),
    ("kv", "hipporag-text-chunks"),
    ("graph", "hipporag-graph"),
    ("vector", "hipporag-chunks"),
    ("vector", "hipporag-entities"),
    ("vector", "hipporag-facts"),
)
_PROBES = {"kv": probe_kv, "graph": probe_graph, "vector": probe_vector}

# 11-10 (D-15, LRAG-16): the vector namespace each retrieval component reads, keyed by component
# name without version. The values are the part modules' own constants; test_empty_namespace.py
# fails if this table drifts from them.
_RETRIEVAL_NAMESPACES: dict[str, str] = {
    "lightrag/retriever-chunk-topk": _chunk_vector._CHUNKS_NAMESPACE,
    "lightrag/entity-lookup": _entity_lookup._ENTITIES_NAMESPACE,
    "lightrag/relation-lookup": _relation_lookup._RELATIONSHIPS_NAMESPACE,
}


# D-04 / research Q4 (LRAG-19): the run copy without recipe-only nodes. One shared helper, so
# promotion's trace-to-arm match sees the same node set a query run dispatches (B-CR-01).
_without_recipe_only_nodes = without_recipe_only_nodes


def _refuse_empty_namespaces(store_root: Path, workspace: str, resolved: dict[str, Any]) -> None:
    """D-15: ``EmptyNamespaceError`` when a retrieval node of ``resolved`` reads a vector namespace
    with neither index file, i.e. one never populated. A namespace emptied by a delete keeps its
    (zero-row) index and is answered as no match. A half-written pair (STOR-08) or an unreadable
    one is the ``StoreCorrupted`` fault the run's own open raises (11 REVIEW B3-WR-01). Reads only;
    creates nothing."""
    for node in (resolved.get("nodes") or {}).values():
        namespace = _RETRIEVAL_NAMESPACES.get(str(node.get("component", "")).split("@")[0])
        if not namespace:
            continue
        try:
            committed = load_committed(store_root / workspace / namespace)
        except VectorStoreCorruptedError as exc:
            raise _foreign_fault("query", exc, failure_class="StoreCorrupted") from exc
        if committed is None:
            raise EmptyNamespaceError(store_kind="vector")

# 06-01-PLAN.md: the retrieval position and its namespace are now read off each resolved wiring's
# own declared evidence_position ({"node": ..., "namespace": ...}) rather than hardcoded here —
# see _execute()'s own evidence-minting block. This module no longer names any single arm's
# retrieval node id directly.

_EXECUTOR_VERSION = "databasise@0.1.0"
_DETERMINISM_SETTING = "cache-bypassed"
_CONCURRENCY_SETTING = "sequential"

# Mirrors run_arm.py's _DEFAULT_TOKEN_ALLOWANCE/DEC-B note: an absent config.token_allowance
# defaults to 0 at the scheduler, budget-halting every node on its first spend. The seam is the
# one caller that needs a real run to complete, so it sets a real, generous per-node allowance —
# never the published wiring itself.
_DEFAULT_TOKEN_ALLOWANCE = 1_000_000
_DEFAULT_MAX_TOTAL_TOKENS = 30000  # v1 constants.py DEFAULT_MAX_TOTAL_TOKENS (LRAG-17)

# CR-02: the RunRecord fields `resolve_trace(debug=False)` returns — an explicit allow-list, not a
# deny-list of one key (`nodes`). §18.2 forbids a consumer receiving `run_id`, `wiring_id`,
# `wiring_instance_hash`, or `arm_id` without `debug=True`; a deny-list silently leaks any field
# not named, which is exactly how those four survived the old `!= "nodes"` filter unnoticed. An
# allow-list instead excludes a new internal-identity field added to RunRecord later by default,
# rather than leaking it by omission.
_NON_DEBUG_TRACE_FIELDS = frozenset(
    {
        "partial",
        "degraded",
        "stop_reason",
        "degradation_reason",
        "bundle_ref",
        "corpus_snapshot_hash",
        "executor_version",
        "concurrency_setting",
        "determinism_setting",
        "arm_execution_order",
    }
)


def _next_offset(page: Page, documents: list[Any], total: int) -> int | None:
    """SEAM-08: ``offset + len(documents)`` when that is below ``total`` and the page returned rows,
    else ``None``. A driver page with zero rows below ``total`` is ``None``, never the same offset
    again, so a polling caller cannot loop forever."""
    reached = page.offset + len(documents)
    return reached if documents and reached < total else None


def _node_dicts(resolved: dict[str, Any]) -> list[dict[str, Any]]:
    """The resolved wiring's node dicts; a malformed `nodes` yields none so the injectors below
    pass it through to ``parse_wiring``, whose report names the defect (WIRE-06)."""
    nodes = resolved.get("nodes", {})
    if not isinstance(nodes, dict):
        return []
    return [node for node in nodes.values() if isinstance(node, dict)]


def _inject_query(resolved: dict[str, Any], query: str) -> dict[str, Any]:
    """06-01-PLAN.md: stamps ``query`` onto every node the resolved wiring's own declared
    ``consumes_query`` array names — a no-op for a node the resolved wiring does not contain
    (an arm patch that removes a node, e.g. ``naive`` removing ``keywords``). Reads the array off
    the resolved dict rather than a hardcoded id list: LightRAG's own base now declares
    ``["keywords", "embedder-query", "generate"]`` — the exact three ids this function
    previously hardcoded — so LightRAG's own behaviour is byte-identical; HippoRAG's base
    declares ``["fact-score", "fact-filter", "reset-vector-join", "dpr-fallback", "qa"]``.
    Defaults to an empty list for a resolved wiring declaring no ``consumes_query`` at all (the
    fixture wirings this module's own tests build directly), preserving the prior
    no-op-for-an-absent-declaration behaviour.
    """
    nodes = resolved.get("nodes", {})
    if not isinstance(nodes, dict):  # a malformed document is refused by parse_wiring, not here
        return resolved
    consumes_query = resolved.get("consumes_query") or []
    for node_id in consumes_query:
        if node_id not in nodes:
            continue
        config = dict(nodes[node_id].get("config") or {})
        config["query"] = query
        nodes[node_id]["config"] = config
    return resolved


def _inject_token_allowance(resolved: dict[str, Any], allowance: int) -> dict[str, Any]:
    """Mirrors ``run_arm.py``'s own ``_inject_token_allowance`` exactly: sets
    ``config.token_allowance`` on every resolved node that does not already declare one."""
    for node in _node_dicts(resolved):
        config = dict(node.get("config") or {})
        config.setdefault("token_allowance", allowance)
        node["config"] = config
    return resolved


# 11 REVIEW A-WR-02: an opaque corpus op is metered after its subprocess has spent and v1 has
# committed, so a budget halt there could only skip the index sync and the v2 commit. Its
# allowance cannot be hit; the spend stays in its node trace and an overrun is logged.
_UNHALTABLE_TOKEN_ALLOWANCE = sys.maxsize


def _inject_corpus_token_allowance(resolved: dict[str, Any]) -> dict[str, Any]:
    """The corpus write wirings' allowances: every opaque node gets one no spend reaches, every
    other node the default (a HippoRAG node still halts before its own v2 commit)."""
    for node in resolved.get("nodes", {}).values():
        if node.get("kind") == "opaque":
            node["config"] = {**(node.get("config") or {}), "token_allowance": _UNHALTABLE_TOKEN_ALLOWANCE}
    return _inject_token_allowance(resolved, _DEFAULT_TOKEN_ALLOWANCE)


def _log_corpus_overrun(scheduled: dict[str, Any], operation: str) -> None:
    """A-WR-02: log each node that spent more than the default allowance. The write still syncs
    and commits, because the spend already happened."""
    for trace in scheduled.get("nodes") or []:
        spent = trace.tokens.prompt_tokens + trace.tokens.completion_tokens
        if spent > _DEFAULT_TOKEN_ALLOWANCE:
            logger.warning(
                "corpus %s: node %s spent %d tokens, %d over the default allowance of %d",
                operation,
                trace.node_id,
                spent,
                spent - _DEFAULT_TOKEN_ALLOWANCE,
                _DEFAULT_TOKEN_ALLOWANCE,
            )


def _inject_max_total_tokens(resolved: dict[str, Any], max_total_tokens: int) -> dict[str, Any]:
    """11-11 (LRAG-17, T-11-24): every LightRAG context assembler gets ``config.max_total_tokens``
    (v1's ``DEFAULT_MAX_TOTAL_TOKENS``) unless the wiring sets its own, so no assembled context is
    unbounded."""
    for node in _node_dicts(resolved):
        if str(node.get("component", "")).startswith("lightrag/assembler-kg-context"):
            config = dict(node.get("config") or {})
            config.setdefault("max_total_tokens", max_total_tokens)
            node["config"] = config
    return resolved


def _build_stores(
    store_root: Path,
    workspace: str,
    resolved: dict[str, Any] | None = None,
    *,
    into: dict[str, Any] | None = None,
    operation: str = "open_stores",
) -> dict[str, Any]:
    """kv/vector/graph, all three, at the engine's own namespace/workspace — mirrors
    ``run_arm.py``'s own ``_build_stores`` (see that module's docstring for why every wiring gets
    every store wired regardless of which subset it actually touches).

    06-01-PLAN.md: ``kv``/``graph`` are each a single namespaced store per run, resolved from the
    wiring's own declared ``store_namespaces`` (``{"kv": ..., "graph": ...}``) when ``resolved``
    is supplied — falling back to the existing ``_TEXT_CHUNKS_KIND``/``_GRAPH_KIND`` constants
    when it is absent or declares none (``ingest``, ``retry_document`` through ``_run_corpus_ingest``,
    ``delete_document`` and ``_execute_resolved`` pass ``resolved``; a wiring with no
    ``store_namespaces`` keeps the defaults). LightRAG's own base now
    declares ``{"kv": "text_chunks", "graph": "chunk_entity_relation"}`` — the exact values those
    two constants already hold — so a LightRAG run through ``_execute`` resolves to an identical
    on-disk directory either way. ``vector`` stays a :class:`MultiNamespaceVectorStore`, selected
    per-node by name: vector isolation between modalities is already a side effect of each part
    selecting its own namespace by name (``hipporag-facts``/``hipporag-chunks`` vs.
    ``entities``/``relationships``/``chunks``), so the multi-namespace handle needs no wiring-level
    declaration of its own.

    Phase 10 D-04 (STOR-02): the stores are added to ``into`` (or a new dict) one at a time, kv,
    then vector, then graph, and that dict is returned. A caller passes its own dict, declared
    before its ``try``, so when a later open raises, its ``finally`` still finalizes every store
    already opened.

    Phase 10 review WR-08: a store that cannot be opened because its file is corrupt (a sqlite
    error, or pycozo's bare ``Exception``) is ``ForeignEngineRefusalError(StoreCorrupted)``, an OS
    error is ``StoreFault``, both labelled with ``operation``; no raw store error reaches a caller.
    """
    store_namespaces = (resolved or {}).get("store_namespaces") or {}
    kv_namespace = store_namespaces.get("kv", _TEXT_CHUNKS_KIND)
    graph_namespace = store_namespaces.get("graph", _GRAPH_KIND)
    stores = into if into is not None else {}
    try:
        stores["kv"] = SqliteKVStore(namespace=kv_namespace, workspace=workspace, store_root=store_root)
        stores["vector"] = MultiNamespaceVectorStore(workspace=workspace, store_root=store_root)
        stores["graph"] = CozoGraphStore(
            namespace=graph_namespace, workspace=workspace, store_root=store_root
        )
    except GraphStoreBusyError as exc:
        # Phase 10 D-01/D-02: the cause text embeds the store path, so it is logged here once and
        # the caller sees only store_kind (research Pitfall 17).
        logger.warning("graph store busy", exc_info=exc)
        raise StoreBusyError(store_kind="graph") from None
    except Exception as exc:
        # pycozo's native layer raises a bare ``Exception`` at open, so it is recognised by origin
        # (it can only come from the constructors above), not by type.
        if isinstance(exc, (sqlite3.Error, VectorStoreCorruptedError)) or type(exc) is Exception:
            raise _foreign_fault(operation, exc, failure_class="StoreCorrupted") from exc
        if isinstance(exc, OSError):
            raise _foreign_fault(operation, exc, failure_class="StoreFault") from exc
        raise
    return stores


def _refuse_unparseable(parsed: ParsedWiring) -> None:
    """Phase 10 D-15 / Q5: a non-ok parse report is a named 422 refusal raised before any store is
    built, never the scheduler's ``WiringRefusedError`` surfacing as a 500. Codes only."""
    if not parsed.report.ok:
        raise UnparseableWiringError(violations=sorted({v.code for v in parsed.report.violations}))


def _corpus_wiring(query_wiring: dict[str, Any], operation: str) -> dict[str, Any]:
    """06-10-PLAN.md: the per-modality write-path lookup. Computes ``query_wiring``'s own
    ``wiring_family`` (the resolved wiring a selector already produced for ``query``/``compare``)
    and loads ``databasise/wirings/<family>/corpus-<operation>.json`` — the on-disk layout IS the
    lookup table, deliberately, so a modality added later needs only a file, never a registry
    entry. Raises :class:`NoWritePathForModalityError` when that file does not exist, rather than
    falling back to another modality's corpus wiring: a write silently landing in a different
    modality's index than the caller selected is undetectable from the return value.
    """
    family = wiring_family(query_wiring)
    path = _WIRINGS_ROOT / family / f"corpus-{operation}.json"
    if not path.is_file():
        raise NoWritePathForModalityError(operation=operation)
    return json.loads(path.read_text(encoding="utf-8"))


# What a well-formed JSON driver result of the wrong shape raises when parsed (SEAM-06). Deliberately
# not caught around UnknownJobError, which is a ValueError and is raised outside every parse wrapper.
_MALFORMED_RESULT = (TypeError, ValueError, AttributeError, KeyError)

# D-08 (LRAG-07): v1's mid-pipeline statuses. With no write holding the D-07 gate, no run is
# advancing such a document, so the corpus views report it as "interrupted". PENDING is not one:
# v1 enqueues it and no run has started on it (Q9).
_MID_PIPELINE = frozenset({"parsing", "analyzing", "processing"})
_INTERRUPTED = "interrupted"


def _interrupted_counts(counts: dict[str, int]) -> dict[str, int]:
    """``counts`` with every mid-pipeline bucket folded into ``interrupted``; the total is kept."""
    out: dict[str, int] = {}
    for status, count in counts.items():
        key = _INTERRUPTED if status in _MID_PIPELINE else status
        out[key] = out.get(key, 0) + int(count)
    return out


_V1_DOC_STATUS_FILE = "kv_store_doc_status.json"


def _v1_row_track_id(status_path: Path, document_id: str) -> str | None:
    """A-CR-02: the track id of v1's row for ``document_id`` by the driver's id stem rule (a text
    row keeps our id; a ``doc-*`` file row maps back through its basename's stem). Read only under
    the write gate, when no v1 process writes the file; ``None`` when it cannot be read."""
    try:
        rows = json.loads(status_path.read_text(encoding="utf-8"))
        for v1_id, row in sorted(rows.items()):
            stem = Path(str(row.get("file_path") or "")).stem
            if (v1_id == document_id or (v1_id.startswith("doc-") and stem == document_id)) and row.get("track_id"):
                return str(row["track_id"])
    except (OSError, ValueError, AttributeError):
        logger.warning("v1 doc-status file unreadable while looking up a track id")
    return None


def _stamp_v1_working_dir(resolved: dict[str, Any], working_dir: Path) -> None:
    """11-01 (D-01, LRAG-01): every LightRAG corpus node (the v1 port and the index sync) reads the
    per-workspace v1 dir from its config; no node falls back to a repo-global dir."""
    for node in resolved.get("nodes", {}).values():
        if str(node.get("component", "")).startswith("lightrag/"):
            node["config"] = {**(node.get("config") or {}), "working_dir": str(working_dir)}


async def _corpus_op_or_refuse(op: str, payload: dict[str, Any], operation: str, working_dir: Path) -> Any:
    """09-05-PLAN.md (SEAM-06, D-04): the read routes' call into the v1 corpus driver. Any
    non-refusal exception from the adapter (its four named failure modes, but also undecodable
    driver bytes and ``OSError`` from a missing or unrunnable interpreter or cwd) becomes the same
    ``ForeignEngineRefusalError`` fault the write routes raise, so a read route never answers with a
    bare 500 (09 REVIEW WR-01). A ``SeamRefusalError`` passes through. ``run_corpus_op`` is looked up
    as a module global at call time so tests can monkeypatch ``databasise.seam.engine.run_corpus_op``."""
    try:
        return await asyncio.to_thread(
            run_corpus_op, op, payload, timeout=STATUS_WALL_CLOCK_CEILING_SECONDS, working_dir=working_dir
        )
    except SeamRefusalError:
        raise
    except CorpusOpBusyError as exc:
        # 11-07 (Q2): a torn doc-status read is a write in progress, so a 409, never a partial list.
        logger.warning("v1 doc-status file unreadable during %s", operation, exc_info=exc)
        raise StoreBusyError(store_kind="corpus") from None
    except Exception as exc:
        # An OSError (PermissionError, FileNotFoundError) means the v1 interpreter or cwd is unusable.
        raise _foreign_fault(
            operation, exc, failure_class="DriverUnavailable" if isinstance(exc, OSError) else None
        ) from exc


async def _drop_pending(stores: dict[str, Any], store_root: Path) -> None:
    """D-06 (STOR-06): abort every store's staged writes. One store's failure is logged and the
    rest are still dropped, so no store is left holding a refused run's writes. Phase 10 review
    WR-04: runs under the store root's flush lock, so it cannot interleave with another run's
    prepare-to-commit window on the same namespace."""
    async with _flush_lock(store_root):
        for name, store in stores.items():
            try:
                await store.drop_pending_index_ops()
            except Exception:  # noqa: BLE001 - keep dropping the other stores
                logger.exception("drop_pending_index_ops failed for store %s", name)


# Keyed by the running loop (research A7): one engine can see several loops under the REST TestClient,
# and an asyncio.Lock must not be shared across loops.
_FLUSH_LOCKS: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, dict[str, asyncio.Lock]] = (
    weakref.WeakKeyDictionary()
)


def _flush_lock(store_root: Path) -> asyncio.Lock:
    """The one lock serializing prepare-to-commit for ``store_root`` on the running loop (D-07)."""
    locks = _FLUSH_LOCKS.setdefault(asyncio.get_running_loop(), {})
    key = str(Path(store_root).resolve())
    if key not in locks:
        locks[key] = asyncio.Lock()
    return locks[key]


# D-07 (LRAG-04): one write gate per resolved v1 working dir. A threading.Lock, not an asyncio.Lock:
# one engine can be driven from several event loops (the REST TestClient), as with _FLUSH_LOCKS.
_WRITE_GATES: dict[str, threading.Lock] = {}
_WRITE_GATES_GUARD = threading.Lock()


def _gate_for(working_dir: Path) -> threading.Lock:
    with _WRITE_GATES_GUARD:
        return _WRITE_GATES.setdefault(str(working_dir.resolve()), threading.Lock())


@contextlib.contextmanager
def _write_gate(working_dir: Path) -> Iterator[None]:
    """Hold ``working_dir``'s write gate, or refuse at once with ``StoreBusyError(store_kind=
    "corpus")`` (409) when another write holds it. Never waits. Released in ``finally``, so a failed
    or cancelled write never leaves it held. A cancelled or timed-out write may have given up on a
    v1 worker thread that is still running (``to_thread_until_done`` parks it in
    ``ABANDONED_WORKERS``); the release is then deferred to a waiter thread that frees the gate once
    every parked worker has returned (A-CR-01, A2-WR-01). The path is never named in the refusal."""
    gate = _gate_for(working_dir)
    if not gate.acquire(blocking=False):
        raise StoreBusyError(store_kind="corpus")
    parked: list[concurrent.futures.Future] = []
    token = ABANDONED_WORKERS.set(parked)
    try:
        yield
    finally:
        try:
            ABANDONED_WORKERS.reset(token)
        finally:
            # A3-WR-02: nested, so a failing reset cannot skip the release and hold the gate for good.
            if parked:
                threading.Thread(
                    target=lambda: (concurrent.futures.wait(parked), gate.release()), daemon=True
                ).start()
            else:
                gate.release()


# D-14 (Phase 12): HippoRAG writes queue. Their read-merge-write steps (edge accumulation D-04, fact
# provenance D-06, document removal D-12) would lose updates if two writers interleaved, and
# refusing at once would break two concurrent HippoRAG ingests that are both valid. The ceiling is
# LightRAG's ingest wall-clock ceiling; a waiter holds no store, so waiting costs nothing.
_HIPPORAG_GATE_WAIT_SECONDS = 900.0
_GATE_POLL_SECONDS = 0.02


@contextlib.asynccontextmanager
async def _serialising_write_gate(path: Path) -> AsyncIterator[None]:
    """Hold ``path``'s gate, waiting (polling, never blocking the loop) up to
    ``_HIPPORAG_GATE_WAIT_SECONDS``, then refuse with ``StoreBusyError(store_kind="corpus")`` (409).
    A threading lock polled with ``acquire(blocking=False)``, not acquired in a thread, so a
    cancelled waiter can never leave the lock held. Released in ``finally``. ``_write_gate`` (the
    LightRAG refuse-at-once gate, LRAG-04) is unchanged."""
    gate = _gate_for(path)
    deadline = time.monotonic() + _HIPPORAG_GATE_WAIT_SECONDS
    while not gate.acquire(blocking=False):
        if time.monotonic() >= deadline:
            raise StoreBusyError(store_kind="corpus")
        await asyncio.sleep(_GATE_POLL_SECONDS)
    try:
        yield
    finally:
        gate.release()


async def _abort_prepared(stores: dict[str, Any]) -> None:
    for name, store in stores.items():
        try:
            await store.abort_prepared()
        except Exception:  # noqa: BLE001 - keep aborting the other stores
            logger.exception("abort_prepared failed for store %s", name)


async def _commit_all(stores: dict[str, Any], operation: str, store_root: Path) -> None:
    """D-07 (STOR-06): prepare every store, then commit every store, under the store root's flush
    lock. A prepare failure aborts all of them; a commit failure aborts the ones not yet committed
    (the documented residual window). Either raises ``StoreFault``."""
    async with _flush_lock(store_root):
        try:
            for store in stores.values():
                await store.prepare()
        except BaseException as exc:
            await _abort_prepared(stores)
            if not isinstance(exc, Exception):
                raise
            raise _foreign_fault(operation, exc, failure_class="StoreFault") from exc
        remaining = dict(stores)
        try:
            for name, store in stores.items():
                await store.commit_prepared()
                del remaining[name]
        except BaseException as exc:
            await _abort_prepared(remaining)
            if not isinstance(exc, Exception):
                raise
            raise _foreign_fault(operation, exc, failure_class="StoreFault") from exc


async def _narrow_sync_manifest(stores: dict[str, Any], scheduled: dict[str, Any], store_root: Path) -> None:
    """11 REVIEW A-WR-01: after every store committed, narrow the v1 index-sync manifest to the
    snapshot's ids (the sync committed it with the pruned ids still listed). A failure keeps the
    wider manifest, which is safe: the next sync prunes those ids again."""
    manifest = next(
        (r["manifest"] for r in scheduled["results"].values() if isinstance(r, dict) and "manifest" in r), None
    )
    kv = stores.get("kv")
    if manifest is None or kv is None:
        return
    try:
        await kv.upsert({V1_INDEX_SYNC_MANIFEST_KEY: manifest})
        async with _flush_lock(store_root):
            await kv.prepare()
            await kv.commit_prepared()
    except Exception:
        await kv.abort_prepared()
        logger.warning("could not narrow the v1 index-sync manifest; the next sync prunes again", exc_info=True)


def _node_result_or_refuse(scheduled: dict[str, Any], node_id: str, operation: str) -> dict[str, Any]:
    """G-05-1 / 05-REVIEW.md CR-02: the one shared refusal decision both ``ingest()`` and
    ``delete_document()`` route through, so a failed run refuses identically at both write call
    sites. It reads the run's own maps (``databasise/runner/scheduler.py``), never a type test
    against whichever exception class the failure happened to raise.

    D-06 (STOR-06): the whole run counts, not only ``node_id``. In order:
    1. a cyclic wiring (``"cycle"``) refuses as ``RunIncomplete``;
    2. ``node_id``'s recorded exception, else the first recorded exception of any other node; a
       store error is ``StoreFault`` (D-13), anything else keeps its existing class;
    3. ``partial`` (an early stop with no exception) refuses as ``RunIncomplete``; a ``stop_reason``
       on a run that is not partial is a declared fallback and never refuses (Phase 12 D-21);
    4. no result for ``node_id`` refuses with a synthesized cause (a cancelled sibling, a dropped
       dispatch). The synthesized ``RuntimeError`` is used only where no real exception exists.
    The caller drops every store's pending writes before the refusal propagates (``_drop_pending``).
    """
    if "cycle" in scheduled:
        raise _foreign_fault(
            operation,
            RuntimeError(f"the {operation!r} wiring has a cycle: {scheduled['cycle']}"),
            failure_class="RunIncomplete",
        )
    node_exceptions = scheduled.get("node_exceptions") or {}
    failed_node_id = node_id
    node_exception = node_exceptions.get(node_id)
    if node_exception is None and node_exceptions:
        failed_node_id, node_exception = next(iter(node_exceptions.items()))
    if node_exception is not None:
        if _is_store_fault(node_exception):
            raise _foreign_fault(
                operation, node_exception, failure_class="StoreFault", node_id=failed_node_id
            ) from node_exception
        raise _foreign_fault(operation, node_exception, node_id=failed_node_id) from node_exception
    stop_reason = scheduled.get("stop_reason")
    if scheduled.get("partial"):
        raise _foreign_fault(
            operation,
            RuntimeError(f"the {operation!r} run stopped early: {stop_reason}"),
            failure_class="RunIncomplete",
        )
    result = scheduled["results"].get(node_id)
    if result is None:
        raise _foreign_fault(
            operation, RuntimeError(f"the {operation!r} node produced no result and no exception")
        )
    return result


def _accounted_store_keys(parsed: ParsedWiring, node_id: str) -> set[str]:
    """The store keys ``node_id``'s own declared ``deps`` account for (FA-08's correlation rule) —
    the union, over each direct dependency's own resolved ``Part.effects``, of the store kind
    ``EFFECT_TO_STORE`` (D-09) maps each effect to. Effects no store backs, ``mutates_store``
    included (§2 keeps it deliberately opaque), map to ``None`` and never contribute. See this
    module's docstring for the rule's full statement and provenance.
    """
    accounted: set[str] = set()
    for dep_id in parsed.deps.get(node_id, ()):
        dep_part = parsed.parts.get(dep_id)
        if dep_part is None:
            continue
        for effect in dep_part.effects:
            entry = EFFECT_TO_STORE.get(effect)
            if entry is not None:
                accounted.add(entry[0])
    return accounted


# 05-03-PLAN.md Task 2: both store-touch kinds MACH-11 correlates — a machine-observed touch
# (a node whose store access crossed a handle the machine itself holds) or a node-reported one
# (an opaque/subprocess-hosted node self-reporting a mutation the machine could not observe).
# Imported from the scheduler rather than repeating the string values here.
_STORE_TOUCH_KINDS = (_scheduler.TOUCH_KIND_OBSERVED, _scheduler.TOUCH_KIND_NODE_REPORTED)


def _mach11_events(
    parsed: ParsedWiring,
    touches: list[tuple[str, str, str]],
    node_by_id: dict[str, NodeTrace],
) -> list[SeamEvent]:
    """Correlate a run's recorded store touches against its own wiring graph (FA-08): for every
    node whose registered ``Part`` declares ``mutates_store``, a touched store key
    ``_accounted_store_keys`` does not cover is an out-of-``deps`` mutation, surfaced as exactly
    one ``SeamEvent`` per such node — never per touch, since the event names the participant, not
    each individual store access. A touch counts whether it is machine-observed
    (``TOUCH_KIND_OBSERVED``, the scheduler's own ``_ScopedStoresView``) or node-reported
    (``TOUCH_KIND_NODE_REPORTED``, an opaque/subprocess-hosted node's own
    ``NodeContext.record_store_touch`` self-report, per this module's own docstring's 05-03
    section) — both are real evidence of a mutation this correlation must not miss, even though
    only one of them is something the machine itself crossed a handle to observe.
    """
    events: list[SeamEvent] = []
    reported_nodes: set[str] = set()
    for node_id, kind, store_key in touches:
        if kind not in _STORE_TOUCH_KINDS or node_id in reported_nodes:
            continue
        part = parsed.parts.get(node_id)
        if part is None or "mutates_store" not in part.effects:
            continue
        if store_key in _accounted_store_keys(parsed, node_id):
            continue

        reported_nodes.add(node_id)
        node_trace = node_by_id.get(node_id)
        # WR-02: a genuinely untraced node (this run's own node_by_id carries no NodeTrace for it,
        # despite a recorded touch) reports the sentinel "unknown" — never the real "none" value a
        # node that honestly spent zero tokens reports. Conflating the two would report a confident
        # fabricated zero for a node this code never actually observed, in tension with
        # UnbudgetableParticipantError's own stated principle (D-08: a plausible-looking fabricated
        # count is worse than a refusal because it reads as measured). In production this branch
        # should be unreachable — every node the scheduler's own recorder reports a touch for also
        # receives a NodeTrace, even when halted (see test_mach11_event.py's own D-08 note) — but a
        # visibly distinct sentinel, rather than deletion, is the safer choice if that guarantee
        # ever changes.
        spend = (
            TokenBreakdownEntry(**node_trace.tokens.to_dict())
            if node_trace is not None
            else TokenBreakdownEntry(counted_by="unknown")
        )
        outcome = "halted" if node_trace is not None and node_trace.budget_state == "halted" else "completed"
        events.append(SeamEvent(component=part.name_at_version, spend=spend, outcome=outcome))
    return events


def stream_envelope_events(envelope: ResponseEnvelope) -> Iterator[dict[str, Any]]:
    """The one event-shaping implementation :meth:`Databasise.query_stream` and
    ``databasise.seam.rest``'s ``/query/stream`` endpoint both iterate — never two independently
    maintained copies (see this module's docstring, "CR-01 gap closure"). Pure and synchronous on
    purpose: it only reads an already-computed ``ResponseEnvelope``'s own fields, so calling it can
    never itself raise a ``SeamRefusalError`` — every refusal is already resolved (or raised) by
    the time a caller has an ``envelope`` to pass in. One event per evidence reference, in the
    envelope's own order (no re-sort), then one final event carrying every remaining field.
    """
    for ref in envelope.evidence:
        yield {"kind": "evidence", "evidence": ref.model_dump()}
    yield {"kind": "final", **envelope.model_dump(exclude={"evidence"})}


def _select_answer(
    provides: list[str],
    provided: dict[str, Any],
    node_by_id: dict[str, NodeTrace],
) -> tuple[str, Depth | None]:
    """WR-01: the envelope's ``answer``/``depth_label``, selected by iterating ``provides`` — the
    wiring's own declared order — never scheduler dispatch order. Iterating dispatch order let
    whichever provides-node happened to run last silently win for both fields, with no signal in
    the envelope that a choice was made among several — exactly the implicit, order-dependent
    behavior this package's own house style (explicit refusals over silent narrowing) prohibits
    elsewhere. Raises ``RuntimeError`` if more than one ``provides`` node produces a completion —
    no selector this phase resolves can produce that today (every arm this phase ships declares
    exactly one ``provides`` position), so it is refused rather than silently resolved by
    incidental order, mirroring ``_execute()``'s own precedent for a cyclic resolved wiring.

    WIRE-04, D-06: ``depth_label`` is ``None`` unless a ``provides`` node returned a completion (an
    empty completion string counts as answered); it is then that node's effective depth.
    """
    answer = ""
    depth_label: Depth | None = None
    answered_node_id: str | None = None
    for node_id in provides:
        output = provided.get(node_id)
        if not (isinstance(output, dict) and "completion" in output):
            continue
        if answered_node_id is not None:
            raise RuntimeError(
                f"wiring declares more than one provides position with a completion "
                f"({answered_node_id!r} and {node_id!r} both did); the seam has no defined "
                "tie-break for more than one answering provides node"
            )
        answered_node_id = node_id
        answer = str(output["completion"])
        node_trace = node_by_id.get(node_id)
        if node_trace is not None:
            depth_label = node_trace.effective_depth
    return answer, depth_label


def _mutates_store_component(resolved: dict[str, Any], registry: PartRegistry) -> str:
    """06-09-PLAN.md Task 2: the ``name@version`` of the first node in ``resolved`` whose
    registered ``Part`` declares ``mutates_store`` — used only to name the excluded component in
    :class:`~databasise.seam.refusals.MutableStoreComparisonExcludedError`'s message. This is a
    separate, small lookup from ``selectors.py``'s own :func:`_wiring_effects`, which stays the
    sole place the effect *union* is computed (this plan's own acceptance criterion) — this
    function never recomputes that union, it only re-walks the same ``nodes`` mapping once more to
    identify which single node the caller already knows (via ``_wiring_effects``) is responsible.
    """
    for node in resolved.get("nodes", {}).values():
        part = registry.get(node["component"])
        if "mutates_store" in part.effects:
            return part.name_at_version
    raise AssertionError(
        "_mutates_store_component called on a wiring whose _wiring_effects union does not "
        "actually contain mutates_store"
    )


class Databasise:
    """The consumer-facing async seam object (D-01). Holds ``store_root``/``workspace``, an
    optional ``PartRegistry`` (defaulting to ``default_registry()``) and an optional ``clients``
    dict for test injection — the same override point ``run_arm.py`` already establishes."""

    def __init__(
        self,
        *,
        store_root: str | Path,
        workspace: str,
        registry: PartRegistry | None = None,
        clients: dict[str, Any] | None = None,
    ) -> None:
        self.store_root = Path(store_root)
        self.workspace = workspace
        self.registry = registry if registry is not None else default_registry()
        self.clients = clients
        # 04-04 Task 1: one TraceStore per engine, opened once against store_root — a second
        # Databasise instance constructed against the same store_root opens its own connection to
        # the same on-disk database file, which is what proves a minted token's durability across
        # the process that minted it.
        self._trace_store = TraceStore(self.store_root)
        # 11-06 (D-02): job id -> minting family; jobs.db is created by the first record, not here.
        self._jobs = JobFamilyStore(self.store_root)

    def _v1_working_dir(self) -> Path:
        """11-01 (D-01, LRAG-01): the one v1 working dir this engine's LightRAG corpus ops use.
        Not created here; v1 creates it on its first write."""
        return self.store_root / self.workspace / "lightrag-v1"

    def _hipporag_gate_path(self) -> Path:
        """D-14: the key of this workspace's HippoRAG write gate. Distinct from the v1 dir, and never
        created on disk: it only keys an in-process lock."""
        return self.store_root / self.workspace / "hipporag-write"

    def _write_gate_held(self) -> bool:
        """D-07: whether a LightRAG write holds this workspace's v1 working dir. Never acquires."""
        return _gate_for(self._v1_working_dir()).locked()

    def _record_job(self, job_id: str, family: str, document_id: str) -> None:
        """D-02: record which family minted ``job_id``; a jobs.db error is a ``StoreFault``."""
        try:
            self._jobs.record(job_id, family, document_id)
        except (sqlite3.Error, OSError) as exc:
            raise _foreign_fault("ingest", exc, failure_class="StoreFault") from exc

    def _inbox(self) -> Path:
        """11-05 (D-09, LRAG-09): this workspace's raw-upload inbox, v1's ``INPUT_DIR``. v1 moves a
        parsed source into ``<inbox>/__parsed__/``. Not created here."""
        return self.store_root / self.workspace / "corpus-inbox"

    async def query(
        self,
        query_object: QueryObject,
        selector: Selector | None = None,
    ) -> ResponseEnvelope:
        """§18.1 query object in, §18.2 closed envelope out. The envelope's own trace reference is
        always opaque; a caller wanting the node-by-node trace exchanges it through
        ``resolve_trace``.
        """
        return await self._execute(query_object, selector)

    async def query_stream(
        self,
        query_object: QueryObject,
        selector: Selector | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """The streaming variant of :meth:`query` (API-04, D-16). Shares ``query``'s selector
        resolution, execution and redaction entirely — it calls the identical ``_execute()`` this
        class's own ``query()`` calls, computing the exact same ``ResponseEnvelope`` — and shapes
        it into events via the module-level :func:`stream_envelope_events`, the same function
        ``databasise.seam.rest``'s ``/query/stream`` endpoint iterates (see this module's
        docstring, "CR-01 gap closure") rather than a second, divergent execution path or shaping
        copy, and never a token-level stream the underlying scheduler does not itself produce.
        """
        envelope = await self._execute(query_object, selector)
        for event in stream_envelope_events(envelope):
            yield event

    async def compare(
        self,
        query_object: QueryObject,
        selectors: Sequence[Selector],
    ) -> ResponseEnvelope | dict[str, ResponseEnvelope]:
        """API-08's comparison operation (06-03-PLAN.md) — one query object against N selectors,
        returning per-arm envelopes keyed by the caller's own selector values (never an arm id,
        wiring name, node id or modality name). Inspection-only: no verdict, no aggregate, no
        winner (RIG.md ## §RUN.4's "comparison as inspection is always available... free — only
        adjudication costs").

        Runs ``check_consumable`` once, before any arm, so an unconsumable query object refuses
        before any wiring is touched. A zero-length ``selectors`` sequence refuses with
        :class:`~databasise.seam.refusals.EmptyComparisonRequestError`. Exactly one selector
        degenerates to a run, not a comparison (RIG.md ## §RUN.3's degenerate-width rule): it
        returns the identical bare ``ResponseEnvelope`` ``query()`` already returns, never a one-key
        mapping, but only after the ``mutates_store`` check below ran on its resolved wiring (13-07,
        WIRE-17, D-11: CONTRACT.md section 14.4 point 3 refuses before any node runs, so a single
        selector is no exception). Two or more selectors check every comparison key (:func:`~databasise.seam.compare.comparison_keys`),
        resolve each selector once, and run each resolved wiring through ``_execute_resolved`` —
        the same body ``_execute`` runs after resolution, so the §4 ``provenance`` redaction and the
        §18.2 closed-envelope rule apply to every arm by construction. A key collision refuses
        before any selector is resolved and before any arm runs (SEAM-11).

        One selector returns a single envelope; two or more return a map keyed by each selector's
        rendered value (alias or harness string, capabilities joined with '+', or 'default'). A
        consumer tells them apart by the number of selectors it sent, never by inspecting keys, so
        a key named 'answer' cannot make a map look like an envelope. Keys are not prefixed. A key
        collision is refused before any arm runs.

        Arms run sequentially, in the caller's own
        supplied order — matching this engine's own declared ``_CONCURRENCY_SETTING``; this method
        never introduces parallel arm execution (06-03-PLAN.md's own flagged assumption: a future
        change to concurrent arm dispatch would change the declared concurrency setting a later
        phase's own calibration is keyed to).

        **06-09-PLAN.md Task 2 (MACH-10/F-07):** `§14.4` point 3's explicit-refusal requirement.
        Every selector (one included) is resolved up front — before any arm executes — and each resolved
        wiring's declared effect union is computed via ``selectors.py``'s own
        :func:`~databasise.seam.selectors._wiring_effects` (never a second copy of that
        computation). A ``mutates_store`` effect anywhere in that union raises
        :class:`~databasise.seam.refusals.MutableStoreComparisonExcludedError` naming the
        offending component — before the first arm runs, so no envelope is produced
        and no store is written for any arm, including one that would otherwise have run first in
        the caller's own order.
        """
        check_consumable(query_object, self.registry)
        if len(selectors) == 0:
            raise EmptyComparisonRequestError()
        # Two or more selectors check every key before any selector is resolved (SEAM-11).
        keys = comparison_keys(selectors) if len(selectors) > 1 else []
        wirings = [
            resolve_selector(selector, registry=self.registry, store_root=self.store_root)
            for selector in selectors
        ]
        for resolved in wirings:
            if "mutates_store" in _wiring_effects(resolved, self.registry):
                raise MutableStoreComparisonExcludedError(
                    component=_mutates_store_component(resolved, self.registry)
                )
        if len(selectors) == 1:
            return await self._execute_resolved(query_object, wirings[0])
        # 11 REVIEW B-WR-02: refuse a never-populated namespace for any arm before the first arm
        # spends, rather than after earlier arms ran and their envelopes are discarded.
        for resolved in wirings:
            _refuse_empty_namespaces(self.store_root, self.workspace, resolved)
        return {key: await self._execute_resolved(query_object, wiring) for key, wiring in zip(keys, wirings)}

    async def ingest(self, document: IngestDocument, selector: Selector | None = None) -> IngestJob:
        """The fourth §18 operation this seam exposes (05-01-PLAN.md; selector parameter added
        06-10-PLAN.md to close Gap 1(a)) — the first §18 operation that is not a query, and (as of
        06-10) the first two-arm write. ``selector`` names *which fitted modality's index* the
        write lands in — the same §18.4 selector ``query``/``compare`` already accept, never a
        second, write-only selector vocabulary. No selector value can itself express "put this
        document into the corpus" (there is no candidate wiring to choose *among*, only one fixed
        operation to perform once the target modality is known) — so this method resolves
        ``selector`` to a query wiring exactly as ``_execute()`` does, then dispatches that
        modality's own corpus-side write wiring (:func:`_corpus_wiring`) directly through the real
        scheduler, rather than through ``_execute()``'s envelope-assembly path. Returns an
        ``IngestJob`` job handle, never a ``ResponseEnvelope`` — ingest is a distinct operation,
        not a query, and never touches ``databasise/seam/envelope.py``'s closed field set.

        A caller supplying no selector resolves to the default modality exactly as before this
        change — the default (no-selector) path is unchanged, including its on-disk store
        directories: LightRAG's own ``corpus-ingest.json`` declares no ``store_namespaces``, so
        ``_build_stores`` falls back to the same ``_TEXT_CHUNKS_KIND``/``_GRAPH_KIND`` constants it
        always has.

        Both of ``IngestDocument``'s two input shapes (structured text, raw bytes) take this
        identical path (Task 3) — one operation, two input shapes, never two execution paths.

        A HippoRAG re-ingest of a document id removes that document's previous version in the same
        run and commit (D-12): the documents are stamped on every ``consumes_documents`` node.

        **Staging (11-05, D-09, LRAG-08/09).** A raw upload's ``file_name`` must carry a suffix
        ``upload_suffix`` accepts, else ``UnsupportedUploadTypeError`` before anything is written.
        The bytes are staged immediately before the run, by exclusive create, in this workspace's
        inbox ``<store_root>/<workspace>/corpus-inbox/`` as
        ``generated_on_disk_name(document_id, suffix)``: never the caller's name, so no ``../`` and
        no v1 ``[hint]`` reaches disk. The inbox is v1's ``INPUT_DIR``, and v1 maps the row back to
        ``document_id`` through the file stem. A file already staged for that id (a run in flight,
        or one kept after a fault) is refused as ``DuplicateDocumentIdError``. After a committed run,
        and after a refusal other than a v1 timeout, subprocess failure or malformed output, the
        staged file and v1's ``__parsed__/`` copy are removed. On those three faults, or a
        cancellation, the file stays and is logged once: v1 may still list the document, and a
        retry needs the source. ``delete_document`` removes whatever is left for the id.

        **An id v1 already holds (11 REVIEW A-CR-02).** Inside the D-07 gate, before anything is
        staged or recorded, a LightRAG ingest probes v1 with the status op ``retry_document`` uses.
        If v1 holds any row for the id (any status, text or file, any suffix), v1 is not called:
        the job is ``enqueued: 0`` under that row's track id (D-10). v1 would otherwise keep a
        second row for ``x.md`` beside ``x.txt``, and a delete removes only one of them. The
        v1-index-sync node still runs alone and commits, so a document v1 committed before an
        earlier sync timed out is mirrored to v2 (A3-WR-01).
        """
        # D-12: only None is absent; a caller-supplied '' reaches the token check and is refused.
        document_id = document.document_id if document.document_id is not None else uuid.uuid4().hex
        # A caller-supplied document_id is validated through the same bare-token rule a
        # server-minted one already satisfies by construction — a caller-supplied id can never
        # widen the on-disk path.
        generated_on_disk_name(document_id)
        track_id = uuid.uuid4().hex

        query_wiring = resolve_selector(selector, registry=self.registry, store_root=self.store_root)
        resolved = _corpus_wiring(query_wiring, "ingest")
        target_node_id = resolved["consumes_documents"][0]
        result_node_id = resolved["provides"][0]

        if document.raw is not None and resolved["nodes"][target_node_id].get("kind") != "opaque":
            # 06-REVIEW.md CR-01: a raw-bytes upload's real bytes are stamped only into
            # file_paths/docs_format=pending_parse below — a convention only an "opaque" node (a
            # v1 subprocess that parses the file itself, e.g. lightrag/full-ingest) knows how to
            # read. A non-opaque target node (e.g. hipporag/chunker-embedder) reads only
            # document["text"], which a raw upload always leaves "" — silently indexing nothing
            # while still reporting a normal-looking success. Refuse by name before any node
            # config is stamped, rather than let that silent data loss through.
            raise NoRawUploadPathForModalityError(operation="ingest")
        # 11-05 (D-09): before parse and _build_stores, which writes, so a refusal writes nothing.
        suffix = upload_suffix(document.file_name) if document.raw is not None else None

        node_config = dict(resolved["nodes"][target_node_id].get("config") or {})
        # 06-10-PLAN.md (Rule 3 deviation): stamped under both "id" (lightrag/full-ingest's own
        # opaque-payload key) and "document_id" (hipporag/chunker-embedder's own key) — the corpus
        # wiring's own consumes_documents names which node the documents land on, but the per-item
        # key each node's body reads for its own document id differs, and one caller-supplied
        # document list must satisfy either reader without a per-family branch here.
        # 09 REVIEW WR-04: the raw bytes are staged only right before the run (below), after
        # parse_wiring and _build_stores can no longer fail, so a pre-run failure leaves no file.
        staged: Path | None = None
        if document.raw is not None:
            on_disk_path = self._inbox() / generated_on_disk_name(document_id, suffix)
            staged = on_disk_path
            node_config["documents"] = [{"id": document_id, "document_id": document_id, "text": ""}]
            node_config["file_paths"] = [str(on_disk_path)]
            node_config["input_dir"] = str(on_disk_path.parent)  # v1 resolves the basename here (D-09)
            node_config["docs_format"] = _DOCS_FORMAT_PENDING_PARSE
        else:
            node_config["documents"] = [
                {"id": document_id, "document_id": document_id, "text": document.text}
            ]
            node_config["docs_format"] = _DOCS_FORMAT_RAW
        node_config["track_id"] = track_id
        resolved["nodes"][target_node_id]["config"] = node_config
        # D-12: every other consumes_documents node (HippoRAG's document-remover) sees the same
        # documents, so a re-ingest removes the previous version in this run. Parity stamps only [0].
        for other_id in resolved["consumes_documents"][1:]:
            other = resolved["nodes"][other_id]
            other["config"] = {**(other.get("config") or {}), "documents": node_config["documents"]}
        _stamp_v1_working_dir(resolved, self._v1_working_dir())

        resolved = _inject_corpus_token_allowance(resolved)
        parsed = parse_wiring(resolved, self.registry)
        _refuse_unparseable(parsed)
        family = wiring_family(query_wiring)
        return await self._run_corpus_ingest(
            resolved,
            parsed,
            family,
            document_id=document_id,
            track_id=track_id,
            result_node_id=result_node_id,
            staged=staged,
            raw=document.raw,
            precheck=(lambda: self._held_by_v1(document_id, track_id)) if family == "lightrag" else None,
        )

    async def _held_by_v1(self, document_id: str, track_id: str) -> IngestJob | None:
        """A-CR-02: ``enqueued: 0`` under the existing row's track id when v1 already holds a row
        for ``document_id``, else ``None``. Without a doc-status file v1 holds no row (the status
        op answers an empty corpus), so no probe is started. The status op lists no track id, so
        it is read from the file, under the gate, with the driver's id stem rule."""
        status_path = self._v1_working_dir() / _V1_DOC_STATUS_FILE
        if not status_path.is_file():
            return None
        result = await _corpus_op_or_refuse(
            "status",
            {"track_id": None, "document_id": document_id, "limit": 1, "offset": 0},
            "ingest",
            self._v1_working_dir(),
        )
        try:
            held = int(result["total"]) > 0
        except _MALFORMED_RESULT as exc:
            raise _foreign_fault("ingest", exc, failure_class="MalformedDriverOutput") from exc
        if not held:
            return None
        return IngestJob(job_id=_v1_row_track_id(status_path, document_id) or track_id, enqueued=0)

    async def _run_corpus_ingest(
        self,
        resolved: dict[str, Any],
        parsed: ParsedWiring,
        family: str,
        *,
        document_id: str,
        track_id: str,
        result_node_id: str,
        staged: Path | None = None,
        raw: bytes | None = None,
        precheck: Callable[[], Awaitable[IngestJob | None]] | None = None,
        remove_inbox_files: bool = False,
    ) -> IngestJob:
        """The run, commit and cleanup ``ingest`` and ``retry_document`` share (11-08): stores
        opened, the D-07 gate entered (LightRAG; HippoRAG queues on its own D-14 gate before the
        stores open), ``precheck`` awaited inside the gate (a job
        it returns is the answer, and nothing is staged or run), the
        upload staged, the corpus-ingest wiring run, every store committed or every pending write
        dropped, and the inbox cleaned after a committed run (``staged``, or with
        ``remove_inbox_files`` every inbox file for ``document_id``)."""
        # 06-10-PLAN.md: the three-argument form _execute() already uses — LightRAG's own
        # corpus-ingest.json declares no store_namespaces, so this is a no-op for the default path
        # (identical _TEXT_CHUNKS_KIND/_GRAPH_KIND fallback); HippoRAG's declares
        # {"kv": "hipporag-text-chunks", "graph": "hipporag-graph"}, landing an ingest in the same
        # directories base.json's query side reads.
        # 11-01 (LRAG-03): the same recorder shape delete_document passes, so the sync node's
        # observed store touches become MACH-11 events on the returned job.
        touches: list[tuple[str, str, str]] = []

        def _recorder(node_id: str, kind: str, key: str) -> None:
            touches.append((node_id, kind, key))

        stores: dict[str, Any] = {}
        wrote_staged = False
        gated = family == "lightrag"  # D-07: HippoRAG writes no v1 dir
        async with contextlib.AsyncExitStack() as gate:
            try:
                # D-14: a HippoRAG write queues on its own per-workspace gate BEFORE the stores open,
                # because the Faiss store reads its committed snapshot at construction.
                if family == "hipporag":
                    await gate.enter_async_context(_serialising_write_gate(self._hipporag_gate_path()))
                # D-04: built inside the try so a failed open finalizes what opened; still before the
                # staging block, so a failed open leaves no staged file (WR-04).
                stores = _build_stores(self.store_root, self.workspace, resolved, into=stores, operation="ingest")
                # D-07 (LRAG-04): after the open (STOR-02), held through the run, commit and cleanup.
                if gated:
                    gate.enter_context(_write_gate(self._v1_working_dir()))
                if precheck is not None and (existing := await precheck()) is not None:
                    if gated:
                        events = await self._mirror_v1_index_only(resolved, stores)
                        existing = existing.model_copy(update={"seam_events": events})
                    return existing
                if gated:
                    # D-02: before the run, so a job v1 records but that times out here is known.
                    self._record_job(track_id, family, document_id)
                if staged is not None:
                    staged.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        # Exclusive create: a run with this id may be in flight, or a fault kept its file.
                        with open(staged, "xb") as handle:
                            wrote_staged = True
                            handle.write(raw)
                    except FileExistsError:
                        raise DuplicateDocumentIdError(document_id=document_id) from None
                    except Exception:
                        # Pre-run only: nothing has started v1 yet, so the file is ours to remove.
                        if wrote_staged:
                            staged.unlink(missing_ok=True)
                            wrote_staged = False
                        raise
                scheduled = await _scheduler.run_wiring(
                    parsed,
                    self.registry,
                    stores,
                    determinism_setting=_DETERMINISM_SETTING,
                    concurrency_setting=_CONCURRENCY_SETTING,
                    clients=self.clients,
                    recorder=_recorder,
                )
                _log_corpus_overrun(scheduled, "ingest")
                # D-06 (STOR-06): any node failure or early stop commits nothing. Every store's
                # staged writes are dropped before the refusal propagates.
                try:
                    result = _node_result_or_refuse(scheduled, result_node_id, "ingest")
                except ForeignEngineRefusalError:
                    await _drop_pending(stores, self.store_root)
                    raise
                # 06-10-PLAN.md (Rule 2 deviation): a real write-path run, for the first time, has a
                # store-writing node (hipporag/chunker-embedder, hipporag/entity-fact-embedder) hold a
                # store handle before this method returns. Those bodies only stage writes in each
                # store's own pending buffer (kv.py/vector.py's own index_done_callback docstrings);
                # finalize() alone never commits them (stores/base.py's own default no-op). Without
                # this flush, every HippoRAG chunk/entity/fact vector and KV record ingest() writes
                # would be silently discarded the instant this method's own stores go out of scope —
                # LightRAG's own opaque full-ingest never touches ctx.stores at all, so this flush is a
                # safe no-op for the default (no-selector) path (kv.py/vector.py/graph.py's own
                # index_done_callback all early-return when nothing is pending).
                # 10-05 (D-07): all stores prepare, then all commit, or none does.
                await _commit_all(stores, "ingest", self.store_root)
                await _narrow_sync_manifest(stores, scheduled, self.store_root)
            except BaseException as exc:
                if wrote_staged:
                    # 11-05 (D-09): a refusal v1 cannot still be working on removes the file; a v1
                    # fault or a cancellation keeps it for the delete or retry that follows.
                    if isinstance(exc, SeamRefusalError) and getattr(exc, "failure_class", None) not in _KEEP_STAGED:
                        _remove_staged(staged)
                    else:
                        _log_staged_left(staged)
                raise
            finally:
                for store in stores.values():
                    await store.finalize()

            # 06-10-PLAN.md: a terminal node reporting its own "enqueued" count wins (LightRAG's own
            # full-ingest); otherwise this call submitted exactly one document, so that is what is
            # reported — never a fabricated literal 0 for a node that simply does not report the field
            # (HippoRAG's graph-augment-persist), per this codebase's no-fabricated-zero discipline.
            # Only a committed run reaches here, so a refused run mints no events (as in delete).
            node_by_id = {node.node_id: node for node in scheduled["nodes"]}
            seam_events = _mach11_events(parsed, touches, node_by_id)
            try:
                enqueued = result.get("enqueued")
                if enqueued is None:
                    enqueued = 1
                job = IngestJob(
                    job_id=str(result.get("track_id") or track_id), enqueued=int(enqueued), seam_events=seam_events
                )
            except _MALFORMED_RESULT as exc:  # 09 REVIEW WR-02: malformed driver output is a 502, as on the read routes
                if wrote_staged:
                    _log_staged_left(staged)
                raise _foreign_fault("ingest", exc, failure_class="MalformedDriverOutput") from exc
            if wrote_staged:
                _remove_staged(staged)  # 11-05 (D-09): v1 has read it; the driver waits for the pipeline
            if remove_inbox_files:
                self._remove_inbox_files(document_id)  # 11-08: a retried upload's kept source
            if not gated:
                try:
                    self._jobs.record(job.job_id, family, document_id)  # D-02: committed runs only
                except (sqlite3.Error, OSError):
                    # A-WR-04: the ingest is committed, so it still succeeds; /jobs for this id
                    # then answers UnknownJobError (no record, and v1 holds no such track).
                    logger.exception("job family record failed after a committed %s ingest", family)
            return job

    async def _mirror_v1_index_only(self, resolved: dict[str, Any], stores: dict[str, Any]) -> list[SeamEvent]:
        """11 REVIEW A3-WR-01: run the corpus wiring's v1-index-sync node alone and commit through
        ``_commit_all``. Called under the write gate when v1 already holds the id: a sync that timed
        out after v1 committed left that document out of v2, and only a sync mirrors it. v1 itself is
        not called. A failure drops the staged writes and refuses as the full ingest does."""
        sync_id = next(
            node_id
            for node_id, node in resolved["nodes"].items()
            if str(node.get("component", "")).startswith("lightrag/v1-index-sync@")
        )
        sync_only = {
            **resolved,
            "nodes": {sync_id: {**resolved["nodes"][sync_id], "deps": []}},
            "provides": [sync_id],
            "consumes_documents": [],
        }
        parsed = parse_wiring(sync_only, self.registry)
        _refuse_unparseable(parsed)
        touches: list[tuple[str, str, str]] = []

        def _recorder(node_id: str, kind: str, key: str) -> None:
            touches.append((node_id, kind, key))

        scheduled = await _scheduler.run_wiring(
            parsed,
            self.registry,
            stores,
            determinism_setting=_DETERMINISM_SETTING,
            concurrency_setting=_CONCURRENCY_SETTING,
            clients=self.clients,
            recorder=_recorder,
        )
        try:
            _node_result_or_refuse(scheduled, sync_id, "ingest")
        except ForeignEngineRefusalError:
            await _drop_pending(stores, self.store_root)
            raise
        await _commit_all(stores, "ingest", self.store_root)
        await _narrow_sync_manifest(stores, scheduled, self.store_root)
        return _mach11_events(parsed, touches, {node.node_id: node for node in scheduled["nodes"]})

    def _remove_inbox_files(self, document_id: str) -> None:
        """11-05 (D-09): remove every file for ``document_id`` (already a validated bare token) from
        this workspace's inbox and its ``__parsed__/``, by exact ``<id>.`` prefix, never a glob. A
        removal error never turns a delete v1 already performed into a failure."""
        prefix = f"{document_id}."
        for directory in (self._inbox(), self._inbox() / "__parsed__"):
            try:
                for path in directory.iterdir() if directory.is_dir() else ():
                    if path.name.startswith(prefix) and path.is_file():
                        path.unlink(missing_ok=True)
            except OSError:
                logger.exception("could not remove the staged upload for document id %r", document_id)

    async def retry_document(self, document_id: str, selector: Selector | None = None) -> IngestJob:
        """11-08 (D-08, LRAG-07): reprocess one interrupted document, a document v1 left in
        ``parsing``, ``analyzing`` or ``processing`` with no write in flight (a timed-out ingest).
        A write, like ``ingest``: the selector names the modality's index, and only LightRAG has a
        v1 pipeline to resume, so any other family is ``NoWritePathForModalityError(operation=
        "retry")``. Inside the D-07 gate, v1's row for the id is read first. No row is
        ``UnknownDocumentError``, any other status is ``DocumentNotInterruptedError``. The
        corpus-ingest wiring then runs with ``documents=[]`` and ``retry_doc_ids=[document_id]``
        (the driver processes only that id) and commits as ``ingest`` does. A kept upload's inbox
        files are removed after the commit. The job id is the document's original track id."""
        generated_on_disk_name(document_id)
        query_wiring = resolve_selector(selector, registry=self.registry, store_root=self.store_root)
        family = wiring_family(query_wiring)
        if family != "lightrag":
            raise NoWritePathForModalityError(operation="retry")
        resolved = _corpus_wiring(query_wiring, "ingest")
        target_node_id = resolved["consumes_documents"][0]
        track_id = uuid.uuid4().hex
        resolved["nodes"][target_node_id]["config"] = {
            **(resolved["nodes"][target_node_id].get("config") or {}),
            "documents": [],
            "retry_doc_ids": [document_id],
            "track_id": track_id,
            "input_dir": str(self._inbox()),  # v1 resolves a kept upload's basename here (D-09)
        }
        _stamp_v1_working_dir(resolved, self._v1_working_dir())
        resolved = _inject_corpus_token_allowance(resolved)
        parsed = parse_wiring(resolved, self.registry)
        _refuse_unparseable(parsed)

        async def _only_interrupted() -> None:
            result = await _corpus_op_or_refuse(
                "status",
                {"track_id": None, "document_id": document_id, "limit": 1, "offset": 0},
                "retry",
                self._v1_working_dir(),
            )
            try:
                rows = list(result.get("documents") or [])
                status = str(rows[0]["status"]) if rows else None
            except _MALFORMED_RESULT as exc:
                raise _foreign_fault("retry", exc, failure_class="MalformedDriverOutput") from exc
            if status is None:
                raise UnknownDocumentError(document_id=document_id)
            if status not in _MID_PIPELINE:
                raise DocumentNotInterruptedError(document_id=document_id, status=status)

        return await self._run_corpus_ingest(
            resolved,
            parsed,
            family,
            document_id=document_id,
            track_id=track_id,
            result_node_id=resolved["provides"][0],
            precheck=_only_interrupted,
            remove_inbox_files=True,
        )

    async def delete_document(
        self, document_id: str, selector: Selector | None = None
    ) -> DeletionOutcome:
        """The fifth §18 operation this seam exposes (05-03-PLAN.md; selector parameter added
        06-10-PLAN.md Task 2) — a write, like ``ingest``, dispatching the target modality's own
        corpus-delete wiring directly through the real scheduler rather than through
        ``_execute()``'s envelope-assembly path, for the same reason ``ingest`` does: no selector
        value can itself express "delete this document from the corpus" — ``selector`` here names
        which fitted modality's index the delete reaches, the same thing it already names for
        ``ingest``/``query``/``compare``.

        After v1 answers ``success`` or ``not_found``, every file left for this id in this
        workspace's inbox and its ``__parsed__/`` (one kept after an ingest fault) is removed
        (11-05, D-09). On ``not_allowed`` or ``fail`` v1 may still read the file, so it stays. The
        inbox is per workspace, so another workspace's delete never reaches it.

        Phase 10 D-08 (STOR-07): the kv and graph stores come from the resolved delete wiring's
        ``store_namespaces``. The delete's staged store writes commit, all stores or none, only when
        the run is not refused and its status is ``success`` or ``not_found``; otherwise they are
        dropped.

        A document v1 itself reports ``not_found`` (already deleted, or never ingested) is a
        normal outcome carried in ``DeletionOutcome.status`` — never a refusal. Only a
        ``document_id`` that fails the machine's own token discipline (the same bare-token rule
        ``generated_on_disk_name`` enforces for a raw-upload's on-disk name) is refused, as
        :class:`~databasise.seam.refusals.InvalidDocumentIdError`, before any wiring is even loaded.

        Passes **the same recorder-callable shape ``_execute()`` passes to ``run_wiring``** — this
        is the load-bearing line documented in this module's own docstring's 05-03 section:
        without it, MACH-11 sees nothing, and the deleting node's own ``mutates_store`` effect
        would never correlate into a ``SeamEvent`` at all.

        A caller supplying no selector resolves to the default modality exactly as before this
        change: it resolves to LightRAG's ``corpus-delete.json``, the identical wiring the former
        ``_DELETE_WIRING_PATH`` constant named, byte-for-byte, and runs under the v1 write gate.
        A HippoRAG selection (Phase 12 D-12, HIPP-16) runs HippoRAG's own ``corpus-delete.json``
        (``hipporag/document-remover``); it never touches the v1 working dir, so it enters no v1 gate.
        A selector resolving to a modality with no ``corpus-delete.json`` raises
        :class:`~databasise.seam.refusals.NoWritePathForModalityError` rather than deleting from a
        different modality's index than the caller selected.
        """
        generated_on_disk_name(document_id)

        query_wiring = resolve_selector(selector, registry=self.registry, store_root=self.store_root)
        family = wiring_family(query_wiring)
        resolved = _corpus_wiring(query_wiring, "delete")
        delete_node_id = resolved["provides"][0]
        node_config = dict(resolved["nodes"][delete_node_id].get("config") or {})
        node_config["doc_id"] = document_id
        resolved["nodes"][delete_node_id]["config"] = node_config
        _stamp_v1_working_dir(resolved, self._v1_working_dir())

        resolved = _inject_corpus_token_allowance(resolved)
        parsed = parse_wiring(resolved, self.registry)
        _refuse_unparseable(parsed)

        # 05-03-PLAN.md Task 2 (MACH-11): the same recorder shape _execute() passes to run_wiring
        # — records every (node_id, kind, store_key) touch, observed or node-reported alike.
        touches: list[tuple[str, str, str]] = []

        def _recorder(node_id: str, kind: str, key: str) -> None:
            touches.append((node_id, kind, key))

        stores: dict[str, Any] = {}
        async with contextlib.AsyncExitStack() as gate:
            try:
                # D-14: a HippoRAG delete queues behind HippoRAG ingests, before the stores open.
                if family == "hipporag":
                    await gate.enter_async_context(_serialising_write_gate(self._hipporag_gate_path()))
                # D-08 (STOR-07): the wiring's store_namespaces pick the kv and graph namespaces, as in
                # ingest; LightRAG's corpus-delete.json declares none, so it keeps the defaults.
                stores = _build_stores(self.store_root, self.workspace, resolved, into=stores, operation="delete")
                # D-07 (LRAG-04): after the open (STOR-02), held through the run, commit and cleanup.
                # D-12: a HippoRAG delete never touches the v1 working dir, so only LightRAG enters it.
                if family == "lightrag":
                    gate.enter_context(_write_gate(self._v1_working_dir()))
                scheduled = await _scheduler.run_wiring(
                    parsed,
                    self.registry,
                    stores,
                    determinism_setting=_DETERMINISM_SETTING,
                    concurrency_setting=_CONCURRENCY_SETTING,
                    clients=self.clients,
                    recorder=_recorder,
                )
                _log_corpus_overrun(scheduled, "delete")
                # G-05-1 / WR-01: the same shared _node_result_or_refuse helper ingest() routes
                # through, called before the MACH-11 correlation below so a refused run mints no seam
                # events. D-06/D-08: a refusal, or a delete reporting "fail" (Q4), drops every store's
                # staged deletes; anything else commits all stores or none (D-07).
                try:
                    result = _node_result_or_refuse(scheduled, delete_node_id, "delete")
                except ForeignEngineRefusalError:
                    await _drop_pending(stores, self.store_root)
                    raise
                # Phase 10 review WR-03: only an explicit success or not_found commits; not_allowed, fail
                # and any other status is a refusal that must not persist the staged deletes.
                if result.get("status") in ("success", "not_found"):
                    await _commit_all(stores, "delete", self.store_root)
                    await _narrow_sync_manifest(stores, scheduled, self.store_root)
                else:
                    await _drop_pending(stores, self.store_root)
            finally:
                for store in stores.values():
                    await store.finalize()

            # B-CR-01: the inbox holds only LightRAG's staged uploads, and a HippoRAG delete holds
            # no v1 gate, so it must neither lose a kept retry source nor race a v1 ingest.
            if family == "lightrag" and result.get("status") in ("success", "not_found"):
                self._remove_inbox_files(document_id)
        node_by_id = {node.node_id: node for node in scheduled["nodes"]}
        seam_events = _mach11_events(parsed, touches, node_by_id)

        try:
            return DeletionOutcome(
                document_id=document_id,
                status=result.get("status") or "fail",
                message=str(result.get("message") or ""),
                seam_events=seam_events,
            )
        except _MALFORMED_RESULT as exc:  # 09 REVIEW WR-02: e.g. a status outside the Literal
            raise _foreign_fault("delete", exc, failure_class="MalformedDriverOutput") from exc

    async def get_job_status(self, job_id: str, page: Page | None = None) -> JobStatus:
        """The sixth §18 operation this seam exposes (05-04-PLAN.md Task 1) — API-01's polling
        half. Reaches ``databasise.foreign.run_corpus_op`` directly (no wiring, no scheduler — see
        this module's own docstring): a status read produces no evidence and mutates nothing.
        Raises :class:`~databasise.seam.refusals.UnknownJobError` when the driver reports zero
        total matching documents for ``job_id`` — never returns an empty ``JobStatus`` for an
        unknown job, mirroring ``TraceStore.resolve``'s own raise-not-None precedent.

        11-06 (D-02, M-12): the job's family is looked up first. A HippoRAG job is recorded only
        once its run committed, so it answers ``processed`` from that record without asking v1. A
        LightRAG job, or an id with no record, takes the v1 path below unchanged. If that record
        write fails after the commit, the ingest still returns its job id (the failure is logged
        once), and this method answers ``UnknownJobError`` for it (11 REVIEW A-WR-04).

        11-08 (D-08): v1's raw status is reported, never ``"interrupted"``. A job id names one run,
        and "interrupted" is a corpus-level view (``corpus_status``/``document_counts``) of a
        document no run holds.
        """
        try:
            row = self._jobs.lookup(job_id)
        except sqlite3.Error as exc:
            raise _foreign_fault("job_status", exc, failure_class="StoreFault") from exc
        if row is not None and row.family == "hipporag":
            entry = DocumentStatusEntry(document_id=row.document_id, status="processed", updated_at=row.created_at)
            return JobStatus(job_id=job_id, documents=[entry], counts={"processed": 1}, next_offset=None)
        page = page or Page()
        result = await _corpus_op_or_refuse(
            "status",
            {"track_id": job_id, "limit": page.limit, "offset": page.offset},
            "job_status",
            self._v1_working_dir(),
        )
        try:
            total = int(result.get("total", 0))
        except _MALFORMED_RESULT as exc:
            raise _foreign_fault("job_status", exc, failure_class="MalformedDriverOutput") from exc
        # Outside every parse wrapper: UnknownJobError is a ValueError and must not be swallowed.
        if total == 0:
            raise UnknownJobError(job_id=job_id)

        try:
            documents = [DocumentStatusEntry(**doc) for doc in result.get("documents", [])]
            return JobStatus(
                job_id=job_id,
                documents=documents,
                counts=dict(result.get("counts") or {}),
                next_offset=_next_offset(page, documents, total),
            )
        except _MALFORMED_RESULT as exc:
            raise _foreign_fault("job_status", exc, failure_class="MalformedDriverOutput") from exc

    def _is_hipporag_selector(self, selector: Selector | None) -> bool:
        """D-13: True when ``selector`` resolves to the HippoRAG family. ``None`` is never HippoRAG
        and resolves nothing, so the no-selector read path stays exactly as it was."""
        if selector is None:
            return False
        resolved = resolve_selector(selector, registry=self.registry, store_root=self.store_root)
        return wiring_family(resolved) == "hipporag"

    def _hipporag_manifests(self, page: Page, operation: str) -> tuple[list[DocumentStatusEntry], int]:
        """D-13 (HIPP-15): one page of HippoRAG's document registry. The ``doc:<id>`` manifest in
        ``hipporag-text-chunks`` is written in the same commit as the document's data, so a manifest
        is a processed document. Read through :func:`list_kv_prefix`, which creates nothing."""
        try:
            rows, total = list_kv_prefix(
                self.store_root / self.workspace / "hipporag-text-chunks",
                "doc:",
                limit=page.limit,
                offset=page.offset,
            )
            documents = [
                DocumentStatusEntry(
                    document_id=key.removeprefix("doc:"),
                    status="processed",
                    updated_at=str(manifest.get("ingested_at") or ""),
                )
                for key, manifest in rows
            ]
        except (sqlite3.Error, OSError) as exc:
            raise _foreign_fault(operation, exc, failure_class="StoreFault") from exc
        except _MALFORMED_RESULT as exc:  # B-WR-01: an undecodable or non-dict manifest, as on the v1 read routes
            raise _foreign_fault(operation, exc, failure_class="MalformedDriverOutput") from exc
        return documents, total

    async def corpus_status(self, page: Page | None = None, selector: Selector | None = None) -> CorpusStatus:
        """The seventh §18 operation (05-04-PLAN.md Task 1, API-06) — a bounded, paginated
        document list, never a full corpus dump. ``page`` above ``MAX_PAGE_SIZE`` is already
        refused by :class:`~databasise.seam.corpus.Page`'s own validator before this method is
        ever reached.

        11-08 (D-08, LRAG-07): when no write holds this workspace's D-07 gate (checked before and
        after the read), a document v1 left in ``parsing``, ``analyzing`` or ``processing`` is
        reported as ``"interrupted"``, in its row and in ``counts``. ``pending`` is never remapped
        (Q9). While a write holds the gate, v1's own status is reported unchanged.
        ``get_job_status`` is not remapped: a job id names one run, and "interrupted" is a
        corpus-level view of a document no run holds.

        12-09 (D-13, HIPP-15): an optional ``selector``. One that resolves to the HippoRAG family
        lists that modality's documents from its per-document manifests (every manifest is a
        processed document, so no ``interrupted`` remap applies); any other selector, and no
        selector, take the v1 path below unchanged."""
        page = page or Page()
        if self._is_hipporag_selector(selector):
            documents, total = self._hipporag_manifests(page, "corpus_status")
            return CorpusStatus(
                documents=documents,
                counts={"processed": total} if total else {},
                total=total,
                next_offset=_next_offset(page, documents, total),
            )
        held = self._write_gate_held()
        result = await _corpus_op_or_refuse(
            "status",
            {"track_id": None, "limit": page.limit, "offset": page.offset},
            "corpus_status",
            self._v1_working_dir(),
        )
        held = held or self._write_gate_held()
        try:
            total = int(result.get("total", 0))
            documents = [DocumentStatusEntry(**doc) for doc in result.get("documents", [])]
            counts = dict(result.get("counts") or {})
            if not held:
                documents = [
                    doc.model_copy(update={"status": _INTERRUPTED}) if doc.status in _MID_PIPELINE else doc
                    for doc in documents
                ]
                counts = _interrupted_counts(counts)
            return CorpusStatus(
                documents=documents,
                counts=counts,
                total=total,
                next_offset=_next_offset(page, documents, total),
            )
        except _MALFORMED_RESULT as exc:
            raise _foreign_fault("corpus_status", exc, failure_class="MalformedDriverOutput") from exc

    async def document_counts(self, selector: Selector | None = None) -> DocumentCounts:
        """The eighth §18 operation (05-04-PLAN.md Task 1, API-06) — a fixed-size record, never a
        per-document list. Calls the same ``"status"`` op ``corpus_status`` calls, with a
        one-row page (the driver refuses ``limit < 1``), and reads only its ``counts`` field.

        11-08 (D-08): mid-pipeline buckets move into ``interrupted`` exactly as in
        ``corpus_status``, and ``total`` stays the sum of ``by_status``.

        12-09 (D-13, HIPP-15): a HippoRAG ``selector`` counts that modality's manifests as
        ``processed`` (see ``corpus_status``); any other selector, and none, take the v1 path."""
        if self._is_hipporag_selector(selector):
            _, total = self._hipporag_manifests(Page(limit=1), "document_counts")
            return DocumentCounts(by_status={"processed": total} if total else {}, total=total)
        held = self._write_gate_held()
        result = await _corpus_op_or_refuse(
            "status", {"track_id": None, "limit": 1, "offset": 0}, "document_counts", self._v1_working_dir()
        )
        held = held or self._write_gate_held()
        try:
            by_status = dict(result.get("counts") or {})
            if not held:
                by_status = _interrupted_counts(by_status)
            return DocumentCounts(by_status=by_status, total=sum(by_status.values()))
        except _MALFORMED_RESULT as exc:
            raise _foreign_fault("document_counts", exc, failure_class="MalformedDriverOutput") from exc

    async def health(self) -> HealthReport:
        """The ninth §18 operation (05-04-PLAN.md Task 1, API-06) — a fixed-size liveness record.
        Probes every ``(kind, namespace)`` in ``_HEALTH_PROBES`` read-only (Phase 10 D-14, STOR-04):
        no store is constructed and nothing is created, and each store reports ``ok``, ``absent``,
        ``corrupted`` or ``busy``. Then checks the v1 working dir's existence itself and calls the
        driver's facade-free ``"health"`` op for ``v1_reachable``, catching any failure of that call
        into ``engine`` and ``engine_reason`` (11-09 D-14, Q5). A probe that raises reports its
        store ``corrupted``. ``status`` is ``ok`` only when every store is ``ok``, every engine
        field is true and both the ``llm`` and ``embedding`` clients are wired (D-14 amends Phase 8
        D-08). Never raises for an unreachable store or an unreachable
        foreign engine — an unreachable participant is reported as unreachable, which is what a
        health check is for.
        """
        root = Path(self.store_root) / self.workspace

        def _probe(kind: str, namespace: str) -> str:
            try:
                return _PROBES[kind](root / namespace)
            except Exception as exc:  # noqa: BLE001 - a failing store is reported, never a 500 (D-14)
                logger.warning("health: the %s:%s probe failed: %s", kind, namespace, type(exc).__name__)
                return "corrupted"

        stores = await asyncio.to_thread(
            lambda: {f"{kind}:{namespace}": _probe(kind, namespace) for kind, namespace in _HEALTH_PROBES}
        )

        # D-14: every engine fact is checked here; the driver's health op builds no facade (11-03).
        try:
            working_dir_present = self._v1_working_dir().exists()
        except OSError:
            working_dir_present = False
        engine_report: dict[str, bool] = {
            "interpreter_present": DEFAULT_V1_INTERPRETER.exists(),
            "working_dir_present": working_dir_present,
            "v1_reachable": False,
        }
        reasons: list[str] = []  # fixed text and key names only, never values (D-12, Q5)
        try:
            result = await asyncio.to_thread(
                run_corpus_op,
                "health",
                {},
                timeout=STATUS_WALL_CLOCK_CEILING_SECONDS,
                working_dir=self._v1_working_dir(),
            )
            engine_report["v1_reachable"] = bool(result["configured"])
            if result.get("missing_keys"):
                reasons.append(f"v1 not configured: missing {', '.join(result['missing_keys'])}")
            if result.get("unsupported_keys"):
                reasons.append(f"v1 backend unsupported: {', '.join(result['unsupported_keys'])}")
        except Exception as exc:  # noqa: BLE001 - health reports an unreachable engine, never raises
            # The type name only: a subprocess error's text can carry driver stderr.
            logger.warning("health: the v1 driver health op failed: %s", type(exc).__name__)
            reasons.append("v1 unreachable")
        if not engine_report["interpreter_present"]:
            reasons.append("v1 interpreter missing")
        clients = self.clients or {}
        clients_wired = "llm" in clients and "embedding" in clients  # rerank stays optional (D-09)
        if not clients_wired:
            reasons.append("model clients not configured")

        overall_ok = (
            all(v == "ok" for v in stores.values()) and all(engine_report.values()) and clients_wired
        )
        return HealthReport(
            status="ok" if overall_ok else "degraded",
            stores=stores,
            engine=engine_report,
            clients={key: key in clients for key in CLIENT_EFFECT_TO_KEY.values()},
            engine_reason="; ".join(reasons) or None,
        )

    async def _execute(
        self,
        query_object: QueryObject,
        selector: Selector | None,
    ) -> ResponseEnvelope:
        """The one execution path both ``query`` and ``query_stream`` call — see this module's
        docstring (04-05, Task 2) for why splitting it out this way is what makes "shares
        resolution, execution and redaction" true by construction rather than by convention."""
        check_consumable(query_object, self.registry)
        resolved = resolve_selector(selector, registry=self.registry, store_root=self.store_root)
        return await self._execute_resolved(query_object, resolved)

    async def _execute_resolved(
        self,
        query_object: QueryObject,
        resolved: dict[str, Any],
    ) -> ResponseEnvelope:
        """Everything in :meth:`_execute` after selector resolution (09-08-PLAN.md, SEAM-11):
        ``compare`` resolves each selector once and hands that wiring here, so the arm that runs
        is the wiring the pre-check inspected even if an alias is repointed in between. Never
        resolves a selector. ``resolved`` is mutated by the query/token-allowance injection, so
        pass each resolved wiring to exactly one call.

        D-04 / research Q4 (LRAG-19): the run parses, opens stores for and runs
        :func:`_without_recipe_only_nodes`'s copy, so the index-recipe node is never dispatched on
        a query; the wiring identities (instance hash, wiring id) and ``provides`` and
        ``evidence_position`` still come from the full ``resolved``."""
        resolved = _inject_query(resolved, query_object.text or "")
        resolved = _inject_token_allowance(resolved, _DEFAULT_TOKEN_ALLOWANCE)
        resolved = _inject_max_total_tokens(resolved, _DEFAULT_MAX_TOTAL_TOKENS)
        run_resolved = _without_recipe_only_nodes(resolved)
        parsed = parse_wiring(run_resolved, self.registry)
        _refuse_unparseable(parsed)

        # 04-04 Task 2 (MACH-11): records every (node_id, "store", store_key) touch the scheduler's
        # own _ScopedStoresView reports, correlated against the wiring graph after the run.
        touches: list[tuple[str, str, str]] = []

        def _recorder(node_id: str, kind: str, key: str) -> None:
            touches.append((node_id, kind, key))

        stores: dict[str, Any] = {}
        try:
            stores = _build_stores(self.store_root, self.workspace, run_resolved, into=stores, operation="query")
            # After _build_stores, so its open errors keep precedence (STOR-02).
            _refuse_empty_namespaces(self.store_root, self.workspace, run_resolved)
            scheduled = await _scheduler.run_wiring(
                parsed,
                self.registry,
                stores,
                determinism_setting=_DETERMINISM_SETTING,
                concurrency_setting=_CONCURRENCY_SETTING,
                clients=self.clients,
                recorder=_recorder,
            )
        finally:
            for store in stores.values():
                await store.finalize()

        if "cycle" in scheduled:
            # No selector this plan resolves can produce a cyclic wiring (the naive arm is
            # acyclic, proven by databasise/tests/parity's own conformance tests) — a genuine
            # occurrence is out of this plan's scope, not silently swallowed.
            raise RuntimeError("the seam does not yet support a cyclic resolved wiring")

        # Phase 10 review CR-01 (D-13 on the query path): a store error inside a node is a named
        # fault, never a 200 envelope. Every other node exception keeps the degraded envelope, whose
        # stop_reason carries the exception class name only (runner/scheduler.py).
        for node_exception in scheduled.get("node_exceptions", {}).values():
            if _is_store_fault(node_exception):
                corrupted = isinstance(node_exception, VectorStoreCorruptedError)
                raise _foreign_fault(
                    "query", node_exception, failure_class="StoreCorrupted" if corrupted else "StoreFault"
                ) from node_exception

        wiring_bytes = canonicalise(resolved)
        wiring_instance_hash = f"sha256:{hashlib.sha256(wiring_bytes).hexdigest()}"
        wiring_id = resolved.get("wiring_id") or (
            f"wiring:{hashlib.sha256(wiring_bytes).hexdigest()[:16]}"
        )

        # Constructed and consumed here only — never returned. RunRecord carries exactly the
        # internal identities (wiring_id, wiring_instance_hash, node_id, instance_hash) §18.2
        # forbids a consumer from receiving; the envelope below is what actually crosses the seam.
        record = RunRecord(
            run_id=str(uuid.uuid4()),
            wiring_id=wiring_id,
            wiring_instance_hash=wiring_instance_hash,
            arm_id="seam",
            arm_execution_order=0,
            executor_version=_EXECUTOR_VERSION,
            concurrency_setting=_CONCURRENCY_SETTING,
            determinism_setting=_DETERMINISM_SETTING,
            nodes=scheduled["nodes"],
            partial=scheduled["partial"],
            degraded=scheduled["degraded"],
            stop_reason=scheduled["stop_reason"],
            degradation_reason=scheduled["degradation_reason"],
        )

        node_by_id = {node.node_id: node for node in record.nodes}

        provides = resolved.get("provides") or []
        provided = {node_id: scheduled["results"].get(node_id) for node_id in provides}
        answer, depth_label = _select_answer(provides, provided, node_by_id)

        # Task 1/2 (04-02); 06-01-PLAN.md: mint evidence refs from the resolved wiring's own
        # declared evidence_position ({"node": ..., "namespace": ...}) — read off the resolved
        # dict rather than a module-level retrieval-node constant, so a modality-agnostic wiring
        # can declare its own retrieval position and namespace (HippoRAG's base declares its own
        # ppr node under the hipporag-chunks namespace). LightRAG's own base now declares the
        # equivalent position under the module-level CHUNKS_NAMESPACE default — the exact value
        # that constant already held — so LightRAG's behaviour is unchanged. No re-sort here (see
        # this module's docstring). A resolved wiring declaring no evidence_position at all, or
        # one whose declared node never dispatches, yields no retrieval output at all, which mints
        # to an empty list, never a refusal (the empty-evidence behavior Task 1 proves).
        evidence_position = resolved.get("evidence_position") or {}
        evidence_node_id = evidence_position.get("node")
        evidence_namespace = evidence_position.get("namespace", CHUNKS_NAMESPACE)
        retrieval_output = (
            scheduled["results"].get(evidence_node_id) if evidence_node_id else None
        )
        try:
            # WIRE-14, D-09: a retrieval output without `items` is a named fault, never a bare KeyError.
            if isinstance(retrieval_output, dict) and "items" not in retrieval_output:
                raise MalformedEvidenceItemError(
                    namespace=evidence_namespace, index=0, reason="carries no 'items' key"
                )
            retrieval_items = retrieval_output["items"] if isinstance(retrieval_output, dict) else []
            evidence = mint_evidence_refs(retrieval_items, namespace=evidence_namespace)
        except MalformedEvidenceItemError as exc:  # 09 REVIEW WR-01: a store fault, not a caller refusal
            raise _foreign_fault("query", exc, failure_class="MalformedDriverOutput") from exc

        # Task 3 (04-02): raises UnbudgetableParticipantError before any envelope is constructed if
        # a node reports the unbudgetable sentinel (D-08) — left to propagate unmodified.
        token_accounting = assemble_token_breakdown(record.nodes)

        # 04-04 Task 2 (MACH-11): correlate the run's own recorded touches against its own wiring
        # graph — see this module's docstring for the rule's full statement (FA-08).
        seam_events = _mach11_events(parsed, touches, node_by_id)

        # 04-04 Task 1 (API-10, D-06): persist the RunRecord and mint its opaque trace reference
        # before the record goes out of scope.
        trace_token = self._trace_store.persist(record.to_dict())

        return ResponseEnvelope(
            answer=answer,
            evidence=evidence,
            trace_token=trace_token,
            depth_label=depth_label,
            partial=record.partial,
            degraded=record.degraded,
            stop_reason=record.stop_reason,
            degradation_reason=record.degradation_reason,
            token_accounting=token_accounting,
            seam_events=seam_events,
        )

    async def resolve_evidence(self, ref: EvidenceRef) -> dict[str, Any]:
        """The second §18 operation the seam exposes (§18.5 — per part kind, evidence, never per
        modality): resolves an evidence reference back through the same store handle it was minted
        from. Order matters (09-06-PLAN.md, SEAM-01, D-05): the namespace is validated first
        (``InvalidEvidenceNamespaceError``), then the namespace directory must already exist
        (``UnresolvableEvidenceReferenceError``, so an unknown namespace creates nothing), and only
        then is the vector store built — the kv and graph stores are never opened by this read.
        A corrupted namespace (checksum mismatch or a half-written directory, STOR-08) is the
        ``StoreCorrupted`` fault (Q6), never the "record no longer present" refusal.
        """
        validate_evidence_namespace(ref.namespace)
        if not (self.store_root / self.workspace / ref.namespace).is_dir():
            raise UnresolvableEvidenceReferenceError(ref)
        vector = None
        try:
            vector = MultiNamespaceVectorStore(workspace=self.workspace, store_root=self.store_root)
            return resolve_evidence_ref(ref, vector)
        except VectorStoreCorruptedError as exc:
            raise _foreign_fault("resolve_evidence", exc, failure_class="StoreCorrupted") from exc
        finally:
            if vector is not None:
                await vector.finalize()

    async def resolve_trace(self, trace_reference: str, *, debug: bool = False) -> dict[str, Any]:
        """The third §18 operation the seam exposes (API-10, D-06), per part kind and not per
        modality: exchanges an opaque trace reference for the run record it was minted from.
        Raises :class:`~databasise.seam.trace_store.UnknownTraceReferenceError` — never returns
        ``None``, never a partial record — for a reference this engine's ``TraceStore`` does not
        hold. Returns the full record, including the node-by-node trace, only when ``debug`` is
        set; without it, the response is filtered to ``_NON_DEBUG_TRACE_FIELDS`` (CR-02) so a
        caller that did not ask for internal identities does not receive ``run_id``, ``wiring_id``,
        ``wiring_instance_hash``, ``arm_id``, or the node-by-node ``nodes`` trace (T-04-19).
        """
        record = self._trace_store.resolve(trace_reference)
        if debug:
            return record
        return {key: value for key, value in record.items() if key in _NON_DEBUG_TRACE_FIELDS}

    def _resolve_operator_preconditions(
        self, alias: str, trace_ids: list[str], change_origin: str | None
    ) -> tuple[list[dict[str, Any]], str, list[str]]:
        """07-02-PLAN.md Task 1: the one shared place the operator-path preconditions live —
        extracted verbatim from ``promote()``'s own former prologue so ``rollback()``/``retire()``
        share it rather than each carrying their own copy (three copies is where one of them
        quietly stops being checked). Refuses an invalid ``change_origin``; resolves every trace id
        through ``self._trace_store`` (raising :class:`~databasise.seam.trace_store.
        UnknownTraceReferenceError` per unresolvable id); refuses an empty or disagreeing
        ``trace_ids`` via :func:`~databasise.seam.promotion.resolve_single_arm`.

        Returns ``(resolved_records, arm_name, arm_instance_hashes)``. ``promote()`` uses
        ``arm_name`` directly as its promotion target; ``rollback()``/``retire()`` derive their own
        target from the ledger instead (D-05/D-07) and use only ``resolved_records`` (for
        ``arm_instance_hashes``) and the refusal vocabulary this method already enforces —
        ``retire()``'s own docstring states explicitly that its resolved arm is recorded, never
        matched against the retirement target.
        """
        if change_origin not in CHANGE_ORIGINS:
            raise InvalidChangeOriginError(change_origin=change_origin)

        resolved_records = [self._trace_store.resolve(trace_id) for trace_id in trace_ids]
        arm_name = resolve_single_arm(resolved_records, alias=alias, trace_ids=list(trace_ids))

        # Real data from the runs the operator read — never fabricated, never returned to the
        # caller (§18.2's closed set forbids an instance hash crossing the seam either way).
        arm_instance_hashes = sorted(
            {
                str(trace_record["wiring_instance_hash"])
                for trace_record in resolved_records
                if trace_record.get("wiring_instance_hash")
            }
        )
        return resolved_records, arm_name, arm_instance_hashes

    async def promote(
        self,
        alias: str,
        trace_ids: list[str],
        change_origin: str | None,
        *,
        verb: PromotionVerb = "operator-asserted",
    ) -> PromotionResult:
        """The tenth §18 operation this seam exposes (07-01-PLAN.md, MACH-07/API-09) — RIG §PR.3's
        operator-asserted promotion path. The caller states an alias, the trace ids they read to
        form the judgment, and a ``change_origin`` — nothing else: the promotion target
        (``mutation_id``), the mutation class, and the minted semver are all derived, never
        accepted as caller input (D-04/D-10/D-11).

        Refusal order (D-09, amended 07-04-PLAN.md closing 07-REVIEW.md CR-01): a ``verb`` outside
        :data:`~databasise.seam.promotion.PROMOTION_VERBS`'s six declared literals refuses first,
        by name, before anything else runs — before the not-built check and before any trace-id
        resolution. Then a gate-ladder verb not built in this milestone (``check``, ``preview``,
        ``run``) refuses immediately, before anything else runs — there is nothing to resolve.
        Then an ``alias`` that is empty or shaped like an instance hash refuses as
        :class:`~databasise.seam.refusals.InvalidPromotionAliasError` (09-07, SEAM-12: no
        ``Selector`` could name it), before ``change_origin`` and trace ids are looked at.
        Otherwise: an invalid ``change_origin`` refuses; an empty, unknown, or disagreeing
        ``trace_ids`` refuses (via :func:`~databasise.seam.promotion.resolve_single_arm`); the
        mutation class is derived against the alias's prior active generation (if any); a
        gate-adjudicated verb (``promote-next``, ``promote-now``) then refuses by posture — it
        never appends a row in this milestone. Only the default ``"operator-asserted"`` verb
        reaches ``Ledger.append()``.

        One ``INSERT`` in one transaction **is** the atomic alias repoint (CONTRACT §6) — no
        second write, no transaction wrapper around two statements. ``Ledger`` stays synchronous by
        its own deliberate exception; the append is offloaded at this async call site via
        ``run_in_executor``. **07-05-PLAN.md (G-07-1):** the read that mints the version (the
        prior-active-generation read) now shares the INSERT's own ``BEGIN IMMEDIATE`` transaction
        via :meth:`~databasise.ledger.ledger.Ledger.transaction` — still one INSERT, still no
        second write, but the decision and the write are now atomic together, not only the write.
        The gate-verb and not-built refusal branches raising inside that span are correct: they
        are refusals, they write nothing, and the context manager rolls back an empty transaction.
        """
        if verb not in PROMOTION_VERBS:
            raise UnrecognisedPromotionVerbError(verb=verb)

        if verb in _NOT_BUILT_VERBS:
            raise GateVerbNotBuiltError(verb=verb)

        # SEAM-12: an alias no Selector could carry would write a row nobody can select. Same
        # pattern Selector's validator refuses, checked before trace resolution and any ledger touch.
        if alias == "" or _INSTANCE_HASH_PATTERN.match(alias):
            raise InvalidPromotionAliasError(alias=alias)

        _resolved_records, arm_name, arm_instance_hashes = self._resolve_operator_preconditions(
            alias, trace_ids, change_origin
        )
        new_resolved = resolved_wiring_for_arm(arm_name)

        def _promote_sync() -> tuple[str, int]:
            """Runs entirely on the executor thread: opening ``Ledger`` here (rather than on the
            calling event-loop thread) and never handing its connection across threads avoids
            sqlite3's own cross-thread-use refusal, since ``Ledger`` itself stays synchronous by
            deliberate exception. Every ledger touch this promotion needs — reading the prior
            active generation, minting the version off it, and appending — happens in this one
            offloaded call, so the read and the write are never split across two threads.
            """
            ledger = Ledger(self.store_root)

            with ledger.transaction():
                prior_record = ledger.by_alias(alias)
                prior_resolved = (
                    resolved_wiring_for_arm(prior_record.mutation_id)
                    if prior_record is not None
                    else None
                )

                mutation_class = derive_mutation_class(new_resolved, prior_resolved)

                if verb in _GATE_VERBS:
                    enforce_gate_verb_posture(verb, mutation_class)  # always raises

                if verb != "operator-asserted":
                    # Unreachable by construction: promote()'s own top-of-body guard already
                    # raises UnrecognisedPromotionVerbError for anything outside
                    # PROMOTION_VERBS, and every member of that set is handled above
                    # (_NOT_BUILT_VERBS, _GATE_VERBS) or is this branch's own
                    # "operator-asserted". Kept as a backstop so a seventh PromotionVerb literal
                    # added without a matching branch here refuses by name instead of falling
                    # through into a ledger append (07-04-PLAN.md, closing 07-REVIEW.md CR-01).
                    raise UnrecognisedPromotionVerbError(verb=verb)

                prior_version = (
                    prior_record.minted_version if prior_record is not None else None
                )
                prior_surface = (
                    declared_surface(prior_resolved, self.registry)
                    if prior_resolved is not None
                    else None
                )
                new_surface = declared_surface(new_resolved, self.registry)
                minted_version = mint_version(prior_version, prior_surface, new_surface)

                ledger_record = LedgerRecord(
                    mutation_id=arm_name,
                    mutation_class=mutation_class,
                    parent=prior_record.mutation_id if prior_record is not None else None,
                    arm_instance_hashes=arm_instance_hashes,
                    effect_size=None,
                    verdict=None,
                    evidence_pointer=None,
                    proposer_id="operator",
                    depth_label=None,
                    tier_of_decision=None,
                    decomposition_ratio=None,
                    opaque_ttl_renewals=[],
                    parity_records=[],
                    promotion_provenance=PROVENANCE_OPERATOR_ASSERTED,
                    promotion_trace_ids=list(trace_ids),
                    change_origin=change_origin,
                    record_kind=RECORD_KIND_PROMOTION,
                    alias=alias,
                    minted_version=minted_version,
                    targets_version=None,
                )
                generation_ordinal = ledger.append(ledger_record)
            return minted_version, generation_ordinal

        minted_version, generation_ordinal = await asyncio.get_running_loop().run_in_executor(
            None, _promote_sync
        )

        return PromotionResult(
            alias=alias,
            version=minted_version,
            record_kind=RECORD_KIND_PROMOTION,
            provenance=PROVENANCE_OPERATOR_ASSERTED,
            generation_ordinal=generation_ordinal,
        )

    async def rollback(
        self,
        alias: str,
        version: str,
        trace_ids: list[str],
        change_origin: str | None,
    ) -> PromotionResult:
        """The eleventh §18 operation this seam exposes (07-02-PLAN.md, MACH-07/API-09, D-05) —
        RIG §PR.2's rollback path. ``version`` is a required positional parameter with no default:
        D-05 settles that rollback names an explicit semver target, and there is no "previous" a
        caller can silently ask for — a default would let an operator repoint an alias to a
        generation they never named, which is a promotion decision made by the machine on their
        behalf.

        Shares ``promote()``'s validation prologue via
        :meth:`_resolve_operator_preconditions` — an invalid ``change_origin`` and an
        empty/unknown/disagreeing ``trace_ids`` refuse identically to ``promote()``. The target
        generation is then resolved through ``Ledger.generation_state(alias, version)`` — never a
        caller-supplied wiring name: ``None`` refuses as
        :class:`~databasise.seam.refusals.UnknownGenerationVersionError` (covering both "this
        alias never minted that version" and "that version belongs to a different alias" as one
        fact — this alias has no such generation); a tombstoned target refuses as
        :class:`~databasise.seam.refusals.TombstonedGenerationError` (RIG §PR.2, CONTRACT §0.4 — a
        retired generation is not reachable again). ``generation_state`` reads the *latest* record
        for the specific ``(alias, version)`` generation, never a scan for whether a tombstone
        exists anywhere in that mutation's history — a wiring retired once and later legitimately
        re-promoted must stay reachable under its own new generation.

        The appended record's ``mutation_id``/``parent`` both name the target generation's own
        ``mutation_id`` — the wiring being returned to, read from the ledger, never named by the
        caller (RIG §PR.2's own instruction that the record name what it returns to).
        ``targets_version`` is the caller's ``version``; ``minted_version`` is a **newly minted**
        semver, never the target's own — CONTRACT §0.4 says a published name is never reused, and
        re-publishing the target's version for a second, later generation would break the
        ``(alias, version)`` keying ``generation_state`` depends on. The mint uses the same
        :func:`~databasise.seam.promotion.mint_version` rule ``promote()`` uses: prior version is
        the alias's current active generation's own ``minted_version``, and the surface comparison
        is between the rolled-back-to wiring and that current active generation's wiring; the
        mutation class is derived from the same two wirings. The record carries no new arm run and
        no verdict (RIG §PR.3) — ``verdict``/``tier_of_decision``/``evidence_pointer``/
        ``effect_size``/``depth_label``/``decomposition_ratio`` are all ``None``.

        One ``append()``, offloaded via ``run_in_executor`` exactly as ``promote()`` offloads its
        own — the atomic repoint is the single ``INSERT``, never a second write. **07-05-PLAN.md
        (G-07-1):** the single INSERT is also now enclosed with its own guard read — the tombstone
        check and the prior-active-generation read the version mint depends on — in one
        ``BEGIN IMMEDIATE`` span via :meth:`~databasise.ledger.ledger.Ledger.transaction`, which is
        what makes the *decision* atomic, not only the write.
        """
        _resolved_records, _arm_name, arm_instance_hashes = self._resolve_operator_preconditions(
            alias, trace_ids, change_origin
        )

        def _rollback_sync() -> tuple[str, int]:
            """Runs entirely on the executor thread — mirrors ``promote()``'s own
            ``_promote_sync``: every ledger touch this rollback needs (reading the target
            generation, reading the alias's current active generation, minting the version, and
            appending) happens in this one offloaded call, never split across the calling
            event-loop thread and the executor thread.
            """
            ledger = Ledger(self.store_root)

            with ledger.transaction():
                target = ledger.generation_state(alias, version)
                if target is None:
                    raise UnknownGenerationVersionError(alias=alias, version=version)
                if target.record_kind == RECORD_KIND_TOMBSTONE:
                    raise TombstonedGenerationError(alias=alias, version=version)
                target_resolved = resolved_wiring_for_arm(target.mutation_id)

                current_record = ledger.by_alias(alias)
                current_resolved = (
                    resolved_wiring_for_arm(current_record.mutation_id)
                    if current_record is not None
                    else None
                )

                mutation_class = derive_mutation_class(target_resolved, current_resolved)

                prior_version = (
                    current_record.minted_version if current_record is not None else None
                )
                prior_surface = (
                    declared_surface(current_resolved, self.registry)
                    if current_resolved is not None
                    else None
                )
                new_surface = declared_surface(target_resolved, self.registry)
                minted_version = mint_version(prior_version, prior_surface, new_surface)

                ledger_record = LedgerRecord(
                    mutation_id=target.mutation_id,
                    mutation_class=mutation_class,
                    parent=target.mutation_id,
                    arm_instance_hashes=arm_instance_hashes,
                    effect_size=None,
                    verdict=None,
                    evidence_pointer=None,
                    proposer_id="operator",
                    depth_label=None,
                    tier_of_decision=None,
                    decomposition_ratio=None,
                    opaque_ttl_renewals=[],
                    parity_records=[],
                    promotion_provenance=PROVENANCE_OPERATOR_ASSERTED,
                    promotion_trace_ids=list(trace_ids),
                    change_origin=change_origin,
                    record_kind=RECORD_KIND_ROLLBACK,
                    alias=alias,
                    minted_version=minted_version,
                    targets_version=version,
                )
                generation_ordinal = ledger.append(ledger_record)
            return minted_version, generation_ordinal

        minted_version, generation_ordinal = await asyncio.get_running_loop().run_in_executor(
            None, _rollback_sync
        )

        return PromotionResult(
            alias=alias,
            version=minted_version,
            record_kind=RECORD_KIND_ROLLBACK,
            provenance=PROVENANCE_OPERATOR_ASSERTED,
            generation_ordinal=generation_ordinal,
        )

    async def retire(
        self,
        alias: str,
        version: str,
        trace_ids: list[str],
        change_origin: str | None,
    ) -> PromotionResult:
        """The twelfth §18 operation this seam exposes (07-02-PLAN.md, MACH-07/API-09, D-07) — a
        tombstone on the same append-only path ``promote()``/``rollback()`` write to. Shares the
        same parameter shape as ``rollback()`` so the three verbs read as one family across all
        three transports, and reuses :meth:`_resolve_operator_preconditions` for the identical
        ``change_origin``/trace-id checks.

        **A deliberate, stated non-requirement (RESEARCH.md Open Question 2): the resolved arm
        does not have to match the generation being retired.** CONTEXT.md D-07 does not decide
        this; the reading this method adopts is that an operator's judgment that a generation
        should stop being eligible may legitimately be formed by reading traces of a different run
        that demonstrated the problem. The trace ids are still required and must still resolve and
        agree on one arm — so the refusal vocabulary stays uniform across ``promote``/``rollback``/
        ``retire`` — but the resolved arm is recorded (via ``arm_instance_hashes``), never matched
        against the retirement target. Do not "fix" this into a match check.

        The target generation is resolved through ``Ledger.generation_state(alias, version)``,
        exactly as ``rollback()`` does: ``None`` refuses as
        :class:`~databasise.seam.refusals.UnknownGenerationVersionError`; an already-tombstoned
        target refuses as :class:`~databasise.seam.refusals.TombstonedGenerationError` rather than
        silently appending a second tombstone — a no-op success is indistinguishable from a real
        retirement to the caller.

        Then the active-generation guard: if the alias's own active generation
        (``Ledger.by_alias(alias)``) is the target being retired, this refuses as
        :class:`~databasise.seam.refusals.ActiveGenerationRetirementError` — retiring the
        generation an alias currently derives from would leave the alias resolving to a wiring
        just declared ineligible (CONTRACT §16.2 already refuses pins to tombstoned artifacts).
        The alternative — ``by_alias`` walking backward to the most recent non-retired generation —
        would be a second alias-lifecycle mechanism CONTEXT.md states plainly is "not required and
        not asked for"; refusing is the smaller surface, and composes: roll back, then retire.

        The tombstone record's ``mutation_id``/``mutation_class`` name the target generation being
        retired (classed against the alias's own still-active generation, the same two-wiring-diff
        pattern ``rollback()`` uses); ``targets_version`` is the caller's ``version``;
        ``minted_version`` is ``None`` — a retirement mints nothing, which is exactly why 07-01
        gave the minted and targeted versions separate ledger columns instead of overloading one.
        ``parent`` is ``None`` — a tombstone does not return to anything. The record carries no
        verdict, exactly as ``promote()``/``rollback()``'s own records do not.

        **Nothing lifts a tombstone, and that is structural, not defensive, here.** There is no
        un-retire verb, no flag on ``promote()`` that revives a generation, and no code path that
        updates or deletes a tombstone row (the database's own ``BEFORE UPDATE``/``BEFORE DELETE``
        triggers refuse both regardless). Re-promoting the same wiring later is simply a new
        generation with a new minted version (D-07) — the ledger expresses this naturally because
        versions are never reused: the retired ``(alias, version)`` pair keeps reporting a
        tombstone through ``generation_state`` forever, while the new generation is a different
        pair. ``promote()`` gains no check refusing an arm whose earlier generation was retired.

        One ``append()``, offloaded via ``run_in_executor``, and no second write. **07-05-PLAN.md
        (G-07-1):** the single INSERT is also now enclosed with its own guard read — the tombstone
        check and the active-generation guard — in one ``BEGIN IMMEDIATE`` span via
        :meth:`~databasise.ledger.ledger.Ledger.transaction`, which is what makes the *decision*
        atomic, not only the write. Returns ``PromotionResult`` with ``record_kind`` reporting
        ``"tombstone"`` and ``version`` reporting the *retired* version — the field's meaning is
        disambiguated by ``record_kind``.
        """
        _resolved_records, _arm_name, arm_instance_hashes = self._resolve_operator_preconditions(
            alias, trace_ids, change_origin
        )

        def _retire_sync() -> int:
            """Runs entirely on the executor thread, mirroring ``_promote_sync``/
            ``_rollback_sync``: reading the target generation, reading the alias's active
            generation for the guard and the class derivation, and appending, all in one offloaded
            call.
            """
            ledger = Ledger(self.store_root)

            with ledger.transaction():
                target = ledger.generation_state(alias, version)
                if target is None:
                    raise UnknownGenerationVersionError(alias=alias, version=version)
                if target.record_kind == RECORD_KIND_TOMBSTONE:
                    raise TombstonedGenerationError(alias=alias, version=version)

                active = ledger.by_alias(alias)
                if active is not None and active.minted_version == version:
                    raise ActiveGenerationRetirementError(alias=alias, version=version)

                target_resolved = resolved_wiring_for_arm(target.mutation_id)
                active_resolved = (
                    resolved_wiring_for_arm(active.mutation_id) if active is not None else None
                )
                mutation_class = derive_mutation_class(target_resolved, active_resolved)

                ledger_record = LedgerRecord(
                    mutation_id=target.mutation_id,
                    mutation_class=mutation_class,
                    parent=None,
                    arm_instance_hashes=arm_instance_hashes,
                    effect_size=None,
                    verdict=None,
                    evidence_pointer=None,
                    proposer_id="operator",
                    depth_label=None,
                    tier_of_decision=None,
                    decomposition_ratio=None,
                    opaque_ttl_renewals=[],
                    parity_records=[],
                    promotion_provenance=PROVENANCE_OPERATOR_ASSERTED,
                    promotion_trace_ids=list(trace_ids),
                    change_origin=change_origin,
                    record_kind=RECORD_KIND_TOMBSTONE,
                    alias=alias,
                    minted_version=None,
                    targets_version=version,
                )
                generation_ordinal = ledger.append(ledger_record)
            return generation_ordinal

        generation_ordinal = await asyncio.get_running_loop().run_in_executor(
            None, _retire_sync
        )

        return PromotionResult(
            alias=alias,
            version=version,
            record_kind=RECORD_KIND_TOMBSTONE,
            provenance=PROVENANCE_OPERATOR_ASSERTED,
            generation_ordinal=generation_ordinal,
        )


__all__ = ["Databasise", "stream_envelope_events"]
