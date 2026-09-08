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
list from the naive arm's own retrieval position's output (``_EVIDENCE_RETRIEVAL_NODE_ID``,
preserving that node's own output order verbatim — Task 2's own no-re-sort rule) and assembles the
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
that store". No part registered anywhere in ``parts_core``/``LIGHTRAG_PARTS`` declares
``mutates_store`` today, so ``seam_events`` is always empty for every production arm this phase
ships — the correlation is proven only against the fixture parts
``databasise/tests/seam/test_mach11_event.py`` registers. A later phase introducing a real
out-of-``deps`` mutating part should re-check this rule against it rather than assume it already
covers every shape such a part could take.

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
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

from databasise.foreign import CorpusOpSubprocessError, CorpusOpTimeoutError
from databasise.identity.canon import canonicalise
from databasise.parts.registry import PartRegistry, default_registry
from databasise.runner import scheduler as _scheduler
from databasise.runner.trace import NodeTrace, RunRecord
from databasise.seam.corpus import IngestDocument, IngestJob, generated_on_disk_name
from databasise.seam.envelope import ResponseEnvelope, SeamEvent
from databasise.seam.evidence import (
    CHUNKS_NAMESPACE,
    EvidenceRef,
    mint_evidence_refs,
    resolve_evidence_ref,
)
from databasise.seam.query import QueryObject, check_consumable
from databasise.seam.refusals import ForeignEngineRefusalError
from databasise.seam.selectors import Selector, resolve_selector
from databasise.seam.tokens import TokenBreakdownEntry, assemble_token_breakdown
from databasise.seam.trace_store import TraceStore
from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import MultiNamespaceVectorStore
from databasise.validator.parse import ParsedWiring, parse_wiring

# 05-01-PLAN.md: the one-node ingest wiring Databasise.ingest() parses and runs — resolved
# relative to this file, mirroring databasise/wirings/resolve.py's own Path(__file__)-relative
# load shape.
_INGEST_WIRING_PATH = (
    Path(__file__).resolve().parent.parent / "wirings" / "lightrag" / "corpus-ingest.json"
)
_INGEST_NODE_ID = "full-ingest"

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

# The naive arm's own retrieval position (databasise/wirings/lightrag/arm-naive.json-patch.json's
# "chunk-vector" node, kind "retriever") — the only arm the default selector resolves in this
# phase (04-03's alias/capability/harness selectors are the only other resolvable arms, and none
# lands in this plan). A future selector resolving a wiring with a differently-named or absent
# retrieval position is out of this plan's scope — mirrors the same hardcoded-node-id precedent
# already established by ``_inject_query``'s "keywords"/"embedder-query"/"generate" below.
_EVIDENCE_RETRIEVAL_NODE_ID = "chunk-vector"

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
    """Mirrors ``run_arm.py``'s own ``_inject_query`` exactly: stamps ``query`` onto every
    resolved node whose config reads one (``keywords``, ``embedder-query``, ``generate``) — a
    no-op for a node the resolved wiring does not contain."""
    nodes = resolved.get("nodes", {})
    for node_id in ("keywords", "embedder-query", "generate"):
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


def _build_stores(store_root: Path, workspace: str) -> dict[str, Any]:
    """kv/vector/graph, all three, at the engine's own namespace/workspace — mirrors
    ``run_arm.py``'s own ``_build_stores`` exactly (see that module's docstring for why every arm
    gets every store wired regardless of which subset it actually touches)."""
    return {
        "kv": SqliteKVStore(namespace=_TEXT_CHUNKS_KIND, workspace=workspace, store_root=store_root),
        "vector": MultiNamespaceVectorStore(workspace=workspace, store_root=store_root),
        "graph": CozoGraphStore(namespace=_GRAPH_KIND, workspace=workspace, store_root=store_root),
    }


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


def _mach11_events(
    parsed: ParsedWiring,
    touches: list[tuple[str, str, str]],
    node_by_id: dict[str, NodeTrace],
) -> list[SeamEvent]:
    """Correlate a run's recorded store touches against its own wiring graph (FA-08): for every
    node whose registered ``Part`` declares ``mutates_store``, a touched store key
    ``_accounted_store_keys`` does not cover is an out-of-``deps`` mutation, surfaced as exactly
    one ``SeamEvent`` per such node — never per touch, since the event names the participant, not
    each individual store access.
    """
    events: list[SeamEvent] = []
    reported_nodes: set[str] = set()
    for node_id, kind, store_key in touches:
        if kind != "store" or node_id in reported_nodes:
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

    async def ingest(self, document: IngestDocument) -> IngestJob:
        """The fourth §18 operation this seam exposes (05-01-PLAN.md) — and the first that is not
        a query: no selector can express "put this document into the corpus", so this method
        dispatches the single named ``lightrag/full-ingest`` opaque Part directly through the real
        scheduler, rather than through ``_execute()``'s selector-resolution/envelope-assembly
        path. Returns an ``IngestJob`` job handle, never a ``ResponseEnvelope`` — ingest is a
        distinct operation, not a query, and never touches ``databasise/seam/envelope.py``'s
        closed field set.

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

        resolved = json.loads(_INGEST_WIRING_PATH.read_text(encoding="utf-8"))
        node_config = dict(resolved["nodes"][_INGEST_NODE_ID].get("config") or {})
        if document.raw is not None:
            inbox_dir = self.store_root / "corpus-inbox"
            inbox_dir.mkdir(parents=True, exist_ok=True)
            on_disk_path = inbox_dir / generated_on_disk_name(document_id)
            on_disk_path.write_bytes(document.raw)
            node_config["documents"] = [{"id": document_id, "text": ""}]
            node_config["file_paths"] = [str(on_disk_path)]
            node_config["docs_format"] = _DOCS_FORMAT_PENDING_PARSE
        else:
            node_config["documents"] = [{"id": document_id, "text": document.text}]
            node_config["docs_format"] = _DOCS_FORMAT_RAW
        node_config["track_id"] = track_id
        resolved["nodes"][_INGEST_NODE_ID]["config"] = node_config

        resolved = _inject_token_allowance(resolved, _DEFAULT_TOKEN_ALLOWANCE)
        parsed = parse_wiring(resolved, self.registry)

        stores = _build_stores(self.store_root, self.workspace)
        try:
            scheduled = await _scheduler.run_wiring(
                parsed,
                self.registry,
                stores,
                determinism_setting=_DETERMINISM_SETTING,
                concurrency_setting=_CONCURRENCY_SETTING,
                clients=self.clients,
            )
        finally:
            for store in stores.values():
                await store.finalize()

        # A subprocess-level refusal (timeout or non-zero exit) never propagates raw out of
        # run_wiring (CONTRACT §9's "partial outcomes are never discarded" rule) — it is recorded
        # in the run's own node_exceptions map instead. Re-raise it here as the seam-facing
        # ForeignEngineRefusalError, never as the machine-internal exception type.
        node_exception = scheduled.get("node_exceptions", {}).get(_INGEST_NODE_ID)
        if isinstance(node_exception, (CorpusOpSubprocessError, CorpusOpTimeoutError)):
            raise ForeignEngineRefusalError(operation="ingest", cause=node_exception) from node_exception

        result = scheduled["results"].get(_INGEST_NODE_ID) or {}
        return IngestJob(
            job_id=str(result.get("track_id") or track_id),
            enqueued=int(result.get("enqueued", 0)),
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

        # Task 1/2 (04-02): mint evidence refs from the naive arm's own retrieval position, in its
        # own output order — no re-sort here (see _EVIDENCE_RETRIEVAL_NODE_ID's own docstring note
        # and this module's docstring). A wiring that never dispatches this node (none does today —
        # the default selector always resolves the naive arm) yields no retrieval output at all,
        # which mints to an empty list, never a refusal (the empty-evidence behavior Task 1 proves).
        retrieval_output = scheduled["results"].get(_EVIDENCE_RETRIEVAL_NODE_ID)
        retrieval_items = retrieval_output["items"] if isinstance(retrieval_output, dict) else []
        evidence = mint_evidence_refs(retrieval_items, namespace=CHUNKS_NAMESPACE)

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


__all__ = ["Databasise", "stream_envelope_events"]
