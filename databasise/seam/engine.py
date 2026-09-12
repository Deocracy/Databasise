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
parameter (Task 2): a HippoRAG-selected delete raises ``NoWritePathForModalityError`` by name,
since no HippoRAG delete node exists anywhere in this repository (removing a document from
HippoRAG's index would mean retracting its chunk/entity/fact vectors and its fact/passage/synonymy
edges — new node code, out of this plan's scope); an unselected or LightRAG-selected delete
resolves to the identical wiring the former ``_DELETE_WIRING_PATH`` constant named, byte-for-byte.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from collections.abc import AsyncIterator, Iterator, Sequence
from pathlib import Path
from typing import Any

from databasise.foreign import run_corpus_op
from databasise.foreign.v1_corpus_adapter import (
    DEFAULT_V1_INTERPRETER,
    STATUS_WALL_CLOCK_CEILING_SECONDS,
)
from databasise.identity.canon import canonicalise
from databasise.ledger.ledger import Ledger, LedgerRecord
from databasise.parts.registry import PartRegistry, default_registry
from databasise.runner import scheduler as _scheduler
from databasise.runner.trace import NodeTrace, RunRecord
from databasise.seam.corpus import (
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
)
from databasise.seam.envelope import PromotionResult, ResponseEnvelope, SeamEvent
from databasise.seam.evidence import (
    CHUNKS_NAMESPACE,
    EvidenceRef,
    mint_evidence_refs,
    resolve_evidence_ref,
)
from databasise.seam.compare import compare_arms
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
    EmptyComparisonRequestError,
    ForeignEngineRefusalError,
    GateVerbNotBuiltError,
    InvalidChangeOriginError,
    MutableStoreComparisonExcludedError,
    NoRawUploadPathForModalityError,
    NoWritePathForModalityError,
    TombstonedGenerationError,
    UnknownDocumentError,
    UnknownGenerationVersionError,
    UnknownJobError,
    UnrecognisedPromotionVerbError,
)
from databasise.seam.selectors import Selector, _wiring_effects, resolve_selector
from databasise.seam.tokens import TokenBreakdownEntry, assemble_token_breakdown
from databasise.seam.trace_store import TraceStore
from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import MultiNamespaceVectorStore
from databasise.validator.parse import ParsedWiring, parse_wiring
from databasise.wirings.resolve import wiring_family

# 06-10-PLAN.md: the per-modality corpus-wiring root — databasise/wirings/<family>/corpus-
# <operation>.json is itself the write-path lookup table (see _corpus_wiring below); no dict or
# registry duplicates it. Resolved relative to this file, mirroring
# databasise/wirings/resolve.py's own Path(__file__)-relative load shape. Replaces the former
# _INGEST_WIRING_PATH/_INGEST_NODE_ID/_DELETE_WIRING_PATH/_DELETE_NODE_ID module constants, which
# named only LightRAG's own two corpus wirings — the node id each operation targets is now read
# off the resolved corpus wiring's own consumes_documents[0]/provides[0], never a module constant.
_WIRINGS_ROOT = Path(__file__).resolve().parent.parent / "wirings"

# v1's own docs_format vocabulary (lightrag.constants.FULL_DOCS_FORMAT_RAW/_PENDING_PARSE),
# duplicated as bare string literals here rather than imported — databasise/tools/
# check_import_boundary.py forbids importing lightrag anywhere under databasise/ except the named
# subprocess-entry-point leaf scripts, and this module is not one of them.
_DOCS_FORMAT_RAW = "raw"
_DOCS_FORMAT_PENDING_PARSE = "pending_parse"

# 04-04 Task 2 (MACH-11): a reads_*/writes_* effect suffix names the store key it accounts for —
# mirrors databasise/parts_core/__init__.py's own CapabilityScopedStores.require suffix rule
# (`effect.split("_", 1)[-1]`). "mutates_store" itself is excluded: its own suffix, "store", names
# no real store key (§2 keeps it deliberately opaque), so it never contributes to the accounted set.
_ACCOUNTABLE_STORE_EFFECT_PREFIXES = ("reads_", "writes_")

# The v1-native per-kind names the LightRAG wirings' kv/graph stores are keyed by — matching
# databasise/parity/run_arm.py's own _TEXT_CHUNKS_KIND/_GRAPH_KIND constants exactly.
_TEXT_CHUNKS_KIND = "text_chunks"
_GRAPH_KIND = "chunk_entity_relation"

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


def _inject_query(resolved: dict[str, Any], query: str) -> dict[str, Any]:
    """06-01-PLAN.md: stamps ``query`` onto every node the resolved wiring's own declared
    ``consumes_query`` array names — a no-op for a node the resolved wiring does not contain
    (an arm patch that removes a node, e.g. ``naive`` removing ``keywords``). Reads the array off
    the resolved dict rather than a hardcoded id list: LightRAG's own base now declares
    ``["keywords", "embedder-query", "generate"]`` — the exact three ids this function
    previously hardcoded — so LightRAG's own behaviour is byte-identical; HippoRAG's base
    declares ``["fact-score", "reset-vector-join"]``. Defaults to an empty list for a resolved
    wiring declaring no ``consumes_query`` at all (the fixture wirings this module's own tests
    build directly), preserving the prior no-op-for-an-absent-declaration behaviour.
    """
    nodes = resolved.get("nodes", {})
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
    for node in resolved.get("nodes", {}).values():
        config = dict(node.get("config") or {})
        config.setdefault("token_allowance", allowance)
        node["config"] = config
    return resolved


def _build_stores(
    store_root: Path, workspace: str, resolved: dict[str, Any] | None = None
) -> dict[str, Any]:
    """kv/vector/graph, all three, at the engine's own namespace/workspace — mirrors
    ``run_arm.py``'s own ``_build_stores`` (see that module's docstring for why every wiring gets
    every store wired regardless of which subset it actually touches).

    06-01-PLAN.md: ``kv``/``graph`` are each a single namespaced store per run, resolved from the
    wiring's own declared ``store_namespaces`` (``{"kv": ..., "graph": ...}``) when ``resolved``
    is supplied — falling back to the existing ``_TEXT_CHUNKS_KIND``/``_GRAPH_KIND`` constants
    when it is absent (``ingest``/``delete_document``/``health``/``resolve_evidence`` call this
    with no ``resolved`` at all, so their directories are unchanged). LightRAG's own base now
    declares ``{"kv": "text_chunks", "graph": "chunk_entity_relation"}`` — the exact values those
    two constants already hold — so a LightRAG run through ``_execute`` resolves to an identical
    on-disk directory either way. ``vector`` stays a :class:`MultiNamespaceVectorStore`, selected
    per-node by name: vector isolation between modalities is already a side effect of each part
    selecting its own namespace by name (``hipporag-facts``/``hipporag-chunks`` vs.
    ``entities``/``relationships``/``chunks``), so the multi-namespace handle needs no wiring-level
    declaration of its own.
    """
    store_namespaces = (resolved or {}).get("store_namespaces") or {}
    kv_namespace = store_namespaces.get("kv", _TEXT_CHUNKS_KIND)
    graph_namespace = store_namespaces.get("graph", _GRAPH_KIND)
    return {
        "kv": SqliteKVStore(namespace=kv_namespace, workspace=workspace, store_root=store_root),
        "vector": MultiNamespaceVectorStore(workspace=workspace, store_root=store_root),
        "graph": CozoGraphStore(namespace=graph_namespace, workspace=workspace, store_root=store_root),
    }


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


def _node_result_or_refuse(scheduled: dict[str, Any], node_id: str, operation: str) -> dict[str, Any]:
    """G-05-1 / 05-REVIEW.md CR-02: the one shared refusal decision both ``ingest()`` and
    ``delete_document()`` route through, so a node failure the scheduler could not resolve refuses
    identically at both write call sites instead of being enumerated per exception type at each
    one separately (which is how this defect reached two call sites in the first place).

    Reads the run's own ``node_exceptions``/``results`` maps (``databasise/runner/scheduler.py``)
    directly — never a type test against whichever exception class the failure happened to raise.
    Any recorded node exception refuses, whatever its type, because the scheduler has already
    unwrapped it down to the real cause before storing it; a node with neither a recorded
    exception nor a recorded result also refuses, since that condition (a cancelled sibling, a
    silently-dropped dispatch) is itself evidence that nothing ran. A synthesized ``RuntimeError``
    cause is used only in that second branch, where no real exception object exists to carry
    forward — never substituted for one that does exist.

    The narrowing this replaces enumerated a fixed list of known-refusal exception types and let
    anything else fall through to a fabricated success (``ingest()``) or an undifferentiated,
    causeless failure (``delete_document()``, WR-01) — exactly the "no result was produced"
    condition this helper closes over instead.
    """
    node_exception = scheduled.get("node_exceptions", {}).get(node_id)
    if node_exception is not None:
        raise ForeignEngineRefusalError(operation=operation, cause=node_exception) from node_exception
    result = scheduled["results"].get(node_id)
    if result is None:
        raise ForeignEngineRefusalError(
            operation=operation,
            cause=RuntimeError(f"the {operation!r} node produced no result and no exception"),
        )
    return result


def _accounted_store_keys(parsed: ParsedWiring, node_id: str) -> set[str]:
    """The store keys ``node_id``'s own declared ``deps`` account for (FA-08's correlation rule) —
    the union, over each direct dependency's own resolved ``Part.effects``, of the store key any
    ``reads_*``/``writes_*`` effect names. See this module's docstring for the rule's full
    statement and provenance.
    """
    accounted: set[str] = set()
    for dep_id in parsed.deps.get(node_id, ()):
        dep_part = parsed.parts.get(dep_id)
        if dep_part is None:
            continue
        for effect in dep_part.effects:
            if effect.startswith(_ACCOUNTABLE_STORE_EFFECT_PREFIXES):
                accounted.add(effect.split("_", 1)[-1])
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
) -> tuple[str, str]:
    """WR-01: the envelope's ``answer``/``depth_label``, selected by iterating ``provides`` — the
    wiring's own declared order — never scheduler dispatch order. Iterating dispatch order let
    whichever provides-node happened to run last silently win for both fields, with no signal in
    the envelope that a choice was made among several — exactly the implicit, order-dependent
    behavior this package's own house style (explicit refusals over silent narrowing) prohibits
    elsewhere. Raises ``RuntimeError`` if more than one ``provides`` node produces a completion —
    no selector this phase resolves can produce that today (every arm this phase ships declares
    exactly one ``provides`` position), so it is refused rather than silently resolved by
    incidental order, mirroring ``_execute()``'s own precedent for a cyclic resolved wiring.
    """
    answer = ""
    depth_label = "stage"
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

    async def query(
        self,
        query_object: QueryObject,
        selector: Selector | None = None,
        *,
        debug: bool = False,
    ) -> ResponseEnvelope:
        """§18.1 query object in, §18.2 closed envelope out. ``debug`` is accepted here only for
        signature stability with ``resolve_trace`` — the envelope's own trace reference is always
        opaque; a caller wanting the node-by-node trace exchanges it through ``resolve_trace``.
        """
        del debug
        return await self._execute(query_object, selector)

    async def query_stream(
        self,
        query_object: QueryObject,
        selector: Selector | None = None,
        *,
        debug: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        """The streaming variant of :meth:`query` (API-04, D-16). Shares ``query``'s selector
        resolution, execution and redaction entirely — it calls the identical ``_execute()`` this
        class's own ``query()`` calls, computing the exact same ``ResponseEnvelope`` — and shapes
        it into events via the module-level :func:`stream_envelope_events`, the same function
        ``databasise.seam.rest``'s ``/query/stream`` endpoint iterates (see this module's
        docstring, "CR-01 gap closure") rather than a second, divergent execution path or shaping
        copy, and never a token-level stream the underlying scheduler does not itself produce.
        """
        del debug
        envelope = await self._execute(query_object, selector)
        for event in stream_envelope_events(envelope):
            yield event

    async def compare(
        self,
        query_object: QueryObject,
        selectors: Sequence[Selector],
        *,
        debug: bool = False,
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
        returns ``await self._execute(query_object, selectors[0])`` unchanged — the identical bare
        ``ResponseEnvelope`` ``query()`` already returns, never a one-key mapping. Two or more
        selectors delegate to :func:`~databasise.seam.compare.compare_arms`, which awaits this
        engine's own bound ``_execute`` once per selector — the identical path every other §18
        query already runs, so the §4 ``provenance`` redaction and the §18.2 closed-envelope rule
        apply to every arm by construction (see ``compare.py``'s own module docstring).

        ``debug`` is accepted and discarded for signature stability with ``query``/``query_stream``,
        exactly as those two methods already do. Arms run sequentially, in the caller's own
        supplied order — matching this engine's own declared ``_CONCURRENCY_SETTING``; this method
        never introduces parallel arm execution (06-03-PLAN.md's own flagged assumption: a future
        change to concurrent arm dispatch would change the declared concurrency setting a later
        phase's own calibration is keyed to).

        **06-09-PLAN.md Task 2 (MACH-10/F-07):** `§14.4` point 3's explicit-refusal requirement.
        Once two or more selectors are in play (an actual comparison, not the one-selector run
        above), every selector is resolved up front — before any arm executes — and each resolved
        wiring's declared effect union is computed via ``selectors.py``'s own
        :func:`~databasise.seam.selectors._wiring_effects` (never a second copy of that
        computation). A ``mutates_store`` effect anywhere in that union raises
        :class:`~databasise.seam.refusals.MutableStoreComparisonExcludedError` naming the
        offending component — before ``compare_arms`` is called at all, so no envelope is produced
        and no store is written for any arm, including one that would otherwise have run first in
        the caller's own order.
        """
        del debug
        check_consumable(query_object, self.registry)
        if len(selectors) == 0:
            raise EmptyComparisonRequestError()
        if len(selectors) == 1:
            return await self._execute(query_object, selectors[0])
        for selector in selectors:
            resolved = resolve_selector(selector, registry=self.registry, store_root=self.store_root)
            if "mutates_store" in _wiring_effects(resolved, self.registry):
                raise MutableStoreComparisonExcludedError(
                    component=_mutates_store_component(resolved, self.registry)
                )
        return await compare_arms(self._execute, query_object, selectors)

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
        identical path (Task 3) — one operation, two input shapes, never two execution paths. A
        raw payload's bytes are written server-side under ``store_root/corpus-inbox/`` using
        ``generated_on_disk_name`` (never the caller's own ``document_id`` string joined directly,
        and never ``file_name`` at all) before the node config is stamped.
        """
        document_id = document.document_id or uuid.uuid4().hex
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

        node_config = dict(resolved["nodes"][target_node_id].get("config") or {})
        # 06-10-PLAN.md (Rule 3 deviation): stamped under both "id" (lightrag/full-ingest's own
        # opaque-payload key) and "document_id" (hipporag/chunker-embedder's own key) — the corpus
        # wiring's own consumes_documents names which node the documents land on, but the per-item
        # key each node's body reads for its own document id differs, and one caller-supplied
        # document list must satisfy either reader without a per-family branch here.
        if document.raw is not None:
            inbox_dir = self.store_root / "corpus-inbox"
            inbox_dir.mkdir(parents=True, exist_ok=True)
            on_disk_path = inbox_dir / generated_on_disk_name(document_id)
            on_disk_path.write_bytes(document.raw)
            node_config["documents"] = [{"id": document_id, "document_id": document_id, "text": ""}]
            node_config["file_paths"] = [str(on_disk_path)]
            node_config["docs_format"] = _DOCS_FORMAT_PENDING_PARSE
        else:
            node_config["documents"] = [
                {"id": document_id, "document_id": document_id, "text": document.text}
            ]
            node_config["docs_format"] = _DOCS_FORMAT_RAW
        node_config["track_id"] = track_id
        resolved["nodes"][target_node_id]["config"] = node_config

        resolved = _inject_token_allowance(resolved, _DEFAULT_TOKEN_ALLOWANCE)
        parsed = parse_wiring(resolved, self.registry)

        # 06-10-PLAN.md: the three-argument form _execute() already uses — LightRAG's own
        # corpus-ingest.json declares no store_namespaces, so this is a no-op for the default path
        # (identical _TEXT_CHUNKS_KIND/_GRAPH_KIND fallback); HippoRAG's declares
        # {"kv": "hipporag-text-chunks", "graph": "hipporag-graph"}, landing an ingest in the same
        # directories base.json's query side reads.
        stores = _build_stores(self.store_root, self.workspace, resolved)
        try:
            scheduled = await _scheduler.run_wiring(
                parsed,
                self.registry,
                stores,
                determinism_setting=_DETERMINISM_SETTING,
                concurrency_setting=_CONCURRENCY_SETTING,
                clients=self.clients,
            )
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
            for store in stores.values():
                await store.index_done_callback()
        finally:
            for store in stores.values():
                await store.finalize()

        # G-05-1 / CR-02: a node failure, or no result at all, never propagates raw out of
        # run_wiring (CONTRACT §9's "partial outcomes are never discarded" rule) — it is recorded
        # in the run's own node_exceptions/results maps instead, and this module's own shared
        # _node_result_or_refuse re-raises it here as the seam-facing ForeignEngineRefusalError,
        # whatever the underlying failure actually was.
        result = _node_result_or_refuse(scheduled, result_node_id, "ingest")
        # 06-10-PLAN.md: a terminal node reporting its own "enqueued" count wins (LightRAG's own
        # full-ingest); otherwise this call submitted exactly one document, so that is what is
        # reported — never a fabricated literal 0 for a node that simply does not report the field
        # (HippoRAG's graph-augment-persist), per this codebase's no-fabricated-zero discipline.
        enqueued = result.get("enqueued")
        if enqueued is None:
            enqueued = 1
        return IngestJob(job_id=str(result.get("track_id") or track_id), enqueued=int(enqueued))

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

        A document v1 itself reports ``not_found`` (already deleted, or never ingested) is a
        normal outcome carried in ``DeletionOutcome.status`` — never a refusal. Only a
        ``document_id`` that fails the machine's own token discipline (the same bare-token rule
        ``generated_on_disk_name`` enforces for a raw-upload's on-disk name) is refused, as
        :class:`~databasise.seam.refusals.UnknownDocumentError`, before any wiring is even loaded.

        Passes **the same recorder-callable shape ``_execute()`` passes to ``run_wiring``** — this
        is the load-bearing line documented in this module's own docstring's 05-03 section:
        without it, MACH-11 sees nothing, and the deleting node's own ``mutates_store`` effect
        would never correlate into a ``SeamEvent`` at all.

        A caller supplying no selector resolves to the default modality exactly as before this
        change: LightRAG is the only modality that ships a ``corpus-delete.json`` today, so this
        call resolves to the identical wiring the former ``_DELETE_WIRING_PATH`` constant named,
        byte-for-byte. A selector resolving to a modality with no ``corpus-delete.json`` raises
        :class:`~databasise.seam.refusals.NoWritePathForModalityError` rather than deleting from a
        different modality's index than the caller selected.
        """
        try:
            generated_on_disk_name(document_id)
        except ValueError as exc:
            raise UnknownDocumentError(document_id=document_id) from exc

        query_wiring = resolve_selector(selector, registry=self.registry, store_root=self.store_root)
        resolved = _corpus_wiring(query_wiring, "delete")
        delete_node_id = resolved["provides"][0]
        node_config = dict(resolved["nodes"][delete_node_id].get("config") or {})
        node_config["doc_id"] = document_id
        resolved["nodes"][delete_node_id]["config"] = node_config

        resolved = _inject_token_allowance(resolved, _DEFAULT_TOKEN_ALLOWANCE)
        parsed = parse_wiring(resolved, self.registry)

        # 05-03-PLAN.md Task 2 (MACH-11): the same recorder shape _execute() passes to run_wiring
        # — records every (node_id, kind, store_key) touch, observed or node-reported alike.
        touches: list[tuple[str, str, str]] = []

        def _recorder(node_id: str, kind: str, key: str) -> None:
            touches.append((node_id, kind, key))

        stores = _build_stores(self.store_root, self.workspace)
        try:
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

        # G-05-1 / WR-01: the same shared _node_result_or_refuse helper ingest() routes through —
        # any node failure, or no result at all, raises ForeignEngineRefusalError with the real
        # cause, rather than degrading to an undifferentiated, causeless DeletionOutcome(fail).
        # Called before the MACH-11 correlation below so a refused run mints no seam events for a
        # node that did not run.
        result = _node_result_or_refuse(scheduled, delete_node_id, "delete")
        node_by_id = {node.node_id: node for node in scheduled["nodes"]}
        seam_events = _mach11_events(parsed, touches, node_by_id)

        return DeletionOutcome(
            document_id=document_id,
            status=result.get("status") or "fail",
            message=str(result.get("message") or ""),
            seam_events=seam_events,
        )

    async def get_job_status(self, job_id: str, page: Page | None = None) -> JobStatus:
        """The sixth §18 operation this seam exposes (05-04-PLAN.md Task 1) — API-01's polling
        half. Reaches ``databasise.foreign.run_corpus_op`` directly (no wiring, no scheduler — see
        this module's own docstring): a status read produces no evidence and mutates nothing.
        Raises :class:`~databasise.seam.refusals.UnknownJobError` when the driver reports zero
        total matching documents for ``job_id`` — never returns an empty ``JobStatus`` for an
        unknown job, mirroring ``TraceStore.resolve``'s own raise-not-None precedent.
        """
        page = page or Page()
        result = await asyncio.to_thread(
            run_corpus_op,
            "status",
            {"track_id": job_id, "limit": page.limit, "offset": page.offset},
            timeout=STATUS_WALL_CLOCK_CEILING_SECONDS,
        )
        total = int(result.get("total", 0))
        if total == 0:
            raise UnknownJobError(job_id=job_id)

        documents = [DocumentStatusEntry(**doc) for doc in result.get("documents", [])]
        next_offset = page.offset + len(documents)
        return JobStatus(
            job_id=job_id,
            documents=documents,
            counts=dict(result.get("counts") or {}),
            next_offset=next_offset if next_offset < total else None,
        )

    async def corpus_status(self, page: Page | None = None) -> CorpusStatus:
        """The seventh §18 operation (05-04-PLAN.md Task 1, API-06) — a bounded, paginated
        document list, never a full corpus dump. ``page`` above ``MAX_PAGE_SIZE`` is already
        refused by :class:`~databasise.seam.corpus.Page`'s own validator before this method is
        ever reached."""
        page = page or Page()
        result = await asyncio.to_thread(
            run_corpus_op,
            "status",
            {"track_id": None, "limit": page.limit, "offset": page.offset},
            timeout=STATUS_WALL_CLOCK_CEILING_SECONDS,
        )
        total = int(result.get("total", 0))
        documents = [DocumentStatusEntry(**doc) for doc in result.get("documents", [])]
        next_offset = page.offset + len(documents)
        return CorpusStatus(
            documents=documents,
            counts=dict(result.get("counts") or {}),
            total=total,
            next_offset=next_offset if next_offset < total else None,
        )

    async def document_counts(self) -> DocumentCounts:
        """The eighth §18 operation (05-04-PLAN.md Task 1, API-06) — a fixed-size record, never a
        per-document list. Calls the same ``"status"`` op ``corpus_status`` calls, with a
        zero-length page, and reads only its ``counts`` field."""
        result = await asyncio.to_thread(
            run_corpus_op,
            "status",
            {"track_id": None, "limit": 0, "offset": 0},
            timeout=STATUS_WALL_CLOCK_CEILING_SECONDS,
        )
        by_status = dict(result.get("counts") or {})
        return DocumentCounts(by_status=by_status, total=sum(by_status.values()))

    async def health(self) -> HealthReport:
        """The ninth §18 operation (05-04-PLAN.md Task 1, API-06) — a fixed-size liveness record.
        Probes the machine's own kv/vector/graph stores directly (never through the scheduler),
        catching each store's own construction exception into ``stores`` rather than propagating
        it, then calls the foreign engine's own ``"health"`` op, catching any failure of that call
        into ``engine`` the same way. Never raises for an unreachable store or an unreachable
        foreign engine — an unreachable participant is reported as unreachable, which is what a
        health check is for.
        """
        store_factories: dict[str, Any] = {
            "kv": lambda: SqliteKVStore(
                namespace=_TEXT_CHUNKS_KIND, workspace=self.workspace, store_root=self.store_root
            ),
            "vector": lambda: MultiNamespaceVectorStore(
                workspace=self.workspace, store_root=self.store_root
            ),
            "graph": lambda: CozoGraphStore(
                namespace=_GRAPH_KIND, workspace=self.workspace, store_root=self.store_root
            ),
        }
        opened_stores: dict[str, Any] = {}
        store_reachability: dict[str, bool] = {}
        for name, factory in store_factories.items():
            try:
                opened_stores[name] = factory()
                store_reachability[name] = True
            except Exception:
                store_reachability[name] = False
        for store in opened_stores.values():
            await store.finalize()

        engine_report: dict[str, bool] = {"interpreter_present": DEFAULT_V1_INTERPRETER.exists()}
        try:
            result = await asyncio.to_thread(
                run_corpus_op, "health", {}, timeout=STATUS_WALL_CLOCK_CEILING_SECONDS
            )
            engine_report["working_dir_present"] = bool(result.get("working_dir_present", False))
            engine_report["storages_initialized"] = bool(result.get("storages_initialized", False))
        except Exception:
            engine_report["working_dir_present"] = False
            engine_report["storages_initialized"] = False

        overall_ok = all(store_reachability.values()) and all(engine_report.values())
        return HealthReport(
            status="ok" if overall_ok else "degraded",
            stores=store_reachability,
            engine=engine_report,
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
        resolved = _inject_query(resolved, query_object.text or "")
        resolved = _inject_token_allowance(resolved, _DEFAULT_TOKEN_ALLOWANCE)
        parsed = parse_wiring(resolved, self.registry)

        # 04-04 Task 2 (MACH-11): records every (node_id, "store", store_key) touch the scheduler's
        # own _ScopedStoresView reports, correlated against the wiring graph after the run.
        touches: list[tuple[str, str, str]] = []

        def _recorder(node_id: str, kind: str, key: str) -> None:
            touches.append((node_id, kind, key))

        stores = _build_stores(self.store_root, self.workspace, resolved)
        try:
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
        retrieval_items = retrieval_output["items"] if isinstance(retrieval_output, dict) else []
        evidence = mint_evidence_refs(retrieval_items, namespace=evidence_namespace)

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
        from. Opens the store set the same way ``query`` does and finalizes it in a ``finally``
        block, mirroring ``query``'s own store lifecycle exactly.
        """
        stores = _build_stores(self.store_root, self.workspace)
        try:
            return resolve_evidence_ref(ref, stores["vector"])
        finally:
            for store in stores.values():
                await store.finalize()

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
        Otherwise: an invalid ``change_origin`` refuses; an empty, unknown, or disagreeing
        ``trace_ids`` refuses (via :func:`~databasise.seam.promotion.resolve_single_arm`); the
        mutation class is derived against the alias's prior active generation (if any); a
        gate-adjudicated verb (``promote-next``, ``promote-now``) then refuses by posture — it
        never appends a row in this milestone. Only the default ``"operator-asserted"`` verb
        reaches ``Ledger.append()``.

        One ``INSERT`` in one transaction **is** the atomic alias repoint (CONTRACT §6) — no
        second write, no transaction wrapper around two statements. ``Ledger`` stays synchronous by
        its own deliberate exception; the append is offloaded at this async call site via
        ``run_in_executor``.
        """
        if verb not in PROMOTION_VERBS:
            raise UnrecognisedPromotionVerbError(verb=verb)

        if verb in _NOT_BUILT_VERBS:
            raise GateVerbNotBuiltError(verb=verb)

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
                # Unreachable by construction: promote()'s own top-of-body guard already raises
                # UnrecognisedPromotionVerbError for anything outside PROMOTION_VERBS, and every
                # member of that set is handled above (_NOT_BUILT_VERBS, _GATE_VERBS) or is this
                # branch's own "operator-asserted". Kept as a backstop so a seventh PromotionVerb
                # literal added without a matching branch here refuses by name instead of falling
                # through into a ledger append (07-04-PLAN.md, closing 07-REVIEW.md CR-01).
                raise UnrecognisedPromotionVerbError(verb=verb)

            prior_version = prior_record.minted_version if prior_record is not None else None
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
            return minted_version, ledger.append(ledger_record)

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
