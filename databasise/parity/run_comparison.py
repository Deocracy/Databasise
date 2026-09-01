"""The parity harness: pinned keywords, a deterministic retrieval-level diff, and an N-run
variance band over the one stochastic query-side node (03-07-PLAN.md Task 2).

Follows ``databasise/evidence/falsifier2.py``'s house style — committed, re-runnable, and
rendering something a second author can read without opening a test file — and
``v1/tests/parity/run_substrate_parity.py``'s output shape: a machine-readable JSON result plus a
human summary, with an exit code that means something.

**Pre-flight (D-02).** Every comparison first runs plan 03-02's index-identity verifier
(``databasise.parity.import_index.verify_import``). Anything other than ``"verified"`` yields a
whole-run ``"inconclusive"`` outcome with no comparison number recorded — a confounded comparison
that returns a normal-looking verdict is worse than a refusal, because it reads as settled rather
than unsettled.

**Keyword pinning (D-12).** Per query, ``keywords`` (``lightrag/keyword-extractor@0.1.0``) is run
live exactly once and its output recorded, then that one recorded pair is fed to both arms — the
decomposed arm through the ``keywords`` node's own ``config["pinned"]``/``config["pinned_output"]``
mechanism (plan 03-05), the original arm through v1's existing ``QueryParam.hl_keywords``/
``ll_keywords`` seam (confirmed live at ``v1/lightrag/operate.py:4023-4024`` — no change to v1 was
needed). An arm whose resolved node set carries no ``keywords`` position (``naive``/``bypass``)
skips pinning entirely: there is nothing to pin.

**The keywords variance band (criterion 2's N-run half).** *Separately* from the one pinning call
above, ``keywords`` is run N more times live (pinning disabled) and :func:`compute_keyword_variance_band`
reports per-keyword frequency and the mean/spread of list sizes over those N independent runs — the
standard library's ``statistics`` module, not a bootstrap floor (Phase 6's own scope, not this
one). A request for a band over fewer than two runs is refused (:class:`SingleRunBandError`), never
silently reported as a zero-width band (PITFALLS 2).

**The retrieval-level diff (criterion 6, D-10).** With keywords pinned, everything downstream is a
deterministic function of the query embedding and the store contents. :func:`diff_ranked_ids` is
pure list/set arithmetic — reachable with no store and no client wired at all — computing the
symmetric difference, a Kendall-style ranking-agreement fraction over the intersection, and the
position of the first disagreement between two ranked id lists.

**Trace asymmetry (D-05).** The decomposed arm's run comes back as a full RIG §TR.1 run record
(``databasise.runner.trace.RunRecord``); the original arm's comes back as
``databasise.parity.v1_arm.V1ArmResult``, whose own ``instrumentation`` field is always
``"harness-external"``. Both are carried under distinguishable keys in :class:`ComparisonRecord` —
never normalised into one shape.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Literal

from databasise.identity.canon import canonicalise
from databasise.parity import import_index
from databasise.parity.corpus import CorpusSnapshot, load_snapshot
from databasise.parity.run_arm import (
    DEFAULT_V1_ENV_PARITY,
    MissingParityEnvError,
    _build_clients,
    _build_stores,
    _DETERMINISM_SETTING as _DECOMPOSED_DETERMINISM_SETTING,
    _CONCURRENCY_SETTING as _DECOMPOSED_CONCURRENCY_SETTING,
    _EXECUTOR_VERSION,
    _inject_query,
    _inject_token_allowance,
    _load_env_file,
    _DEFAULT_TOKEN_ALLOWANCE,
)
from databasise.parity.v1_arm import (
    DEFAULT_V1_WORKING_DIR,
    MissingV1InterpreterError,
    V1ArmResult,
    V1ArmSubprocessError,
    run_v1_arm,
)
from databasise.parts.registry import PartRegistry, default_registry
from databasise.parts.schema import NodeContext
from databasise.runner import scheduler as _scheduler
from databasise.runner.trace import RunRecord
from databasise.validator.parse import parse_wiring
from databasise.wirings.resolve import resolve_arm

_KEYWORDS_NODE_ID = "keywords"
_KEYWORDS_PART_NAME = "lightrag/keyword-extractor@0.1.0"
_CHUNK_SOURCE_NODE_ID = "rerank"
_ENTITY_SOURCE_NODE_ID = "budget-entities"
_RELATION_SOURCE_NODE_ID = "budget-relations"

# Every arm name this phase's wiring set uses maps directly onto one of v1's own
# QueryParam.mode literals (v1/lightrag/base.py) — no translation table beyond the identity map,
# recorded here so a reader sees the mapping is deliberate, not an accident of matching strings.
_ARM_TO_V1_MODE: dict[str, str] = {
    "naive": "naive",
    "bypass": "bypass",
    "hybrid": "hybrid",
    "local": "local",
    "global": "global",
}

_DEFAULT_KEYWORD_VARIANCE_RUNS = 5

VerifyImportFn = Callable[..., Awaitable["import_index.VerificationResult"]]


class SingleRunBandError(ValueError):
    """A variance band over fewer than two runs is not a band (criterion 2 / PITFALLS 2) — the
    harness refuses to compute one rather than reporting a zero-width band.
    """


# --------------------------------------------------------------------------------------------- #
# Keywords: one live pinning call, an independent N-run variance band
# --------------------------------------------------------------------------------------------- #


@dataclass(frozen=True)
class KeywordsResult:
    """One live ``keywords`` call's recorded output."""

    high_level_keywords: tuple[str, ...]
    low_level_keywords: tuple[str, ...]
    cache_served: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "high_level_keywords": list(self.high_level_keywords),
            "low_level_keywords": list(self.low_level_keywords),
            "cache_served": self.cache_served,
        }


@dataclass(frozen=True)
class KeywordVarianceBand:
    """The variance band over N independent live ``keywords`` runs — every figure below is
    reported alongside ``run_count``, per this module's own prohibition against a band figure
    whose run count is unstated.
    """

    run_count: int
    high_level_frequency: dict[str, int]
    low_level_frequency: dict[str, int]
    high_level_size_mean: float
    high_level_size_stdev: float
    low_level_size_mean: float
    low_level_size_stdev: float
    any_cache_served: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_count": self.run_count,
            "high_level_frequency": dict(self.high_level_frequency),
            "low_level_frequency": dict(self.low_level_frequency),
            "high_level_size_mean": self.high_level_size_mean,
            "high_level_size_stdev": self.high_level_size_stdev,
            "low_level_size_mean": self.low_level_size_mean,
            "low_level_size_stdev": self.low_level_size_stdev,
            "any_cache_served": self.any_cache_served,
        }


def compute_keyword_variance_band(runs: list[KeywordsResult]) -> KeywordVarianceBand:
    """Compute a variance band over N independent :class:`KeywordsResult` runs. Raises
    :class:`SingleRunBandError` for ``len(runs) < 2`` — asking for a band from one run is not a
    band, and this is the refusal PITFALLS 2 names.
    """
    if len(runs) < 2:
        raise SingleRunBandError(
            f"a variance band requires at least 2 runs, got {len(runs)} — a single run is not a "
            "band (criterion 2 / PITFALLS 2); pass keyword_variance_runs >= 2"
        )

    hl_frequency: dict[str, int] = {}
    ll_frequency: dict[str, int] = {}
    for run in runs:
        for kw in run.high_level_keywords:
            hl_frequency[kw] = hl_frequency.get(kw, 0) + 1
        for kw in run.low_level_keywords:
            ll_frequency[kw] = ll_frequency.get(kw, 0) + 1

    hl_sizes = [len(r.high_level_keywords) for r in runs]
    ll_sizes = [len(r.low_level_keywords) for r in runs]

    return KeywordVarianceBand(
        run_count=len(runs),
        high_level_frequency=hl_frequency,
        low_level_frequency=ll_frequency,
        high_level_size_mean=statistics.fmean(hl_sizes),
        high_level_size_stdev=statistics.stdev(hl_sizes),
        low_level_size_mean=statistics.fmean(ll_sizes),
        low_level_size_stdev=statistics.stdev(ll_sizes),
        any_cache_served=any(r.cache_served for r in runs),
    )


async def _run_keywords_live(query: str, clients: dict[str, Any], registry: PartRegistry) -> KeywordsResult:
    """One live call through the real ``lightrag/keyword-extractor@0.1.0`` part body — never the
    pinned-replay path (``config["pinned"]`` is never set here)."""
    part = registry.get(_KEYWORDS_PART_NAME)
    ctx = NodeContext(node_id=_KEYWORDS_NODE_ID, config={"query": query}, inputs={}, stores={}, clients=clients)
    output = await part.body(ctx)
    tokens = output.get("tokens")
    cache_served = bool(getattr(tokens, "cached_read_tokens", 0))
    return KeywordsResult(
        high_level_keywords=tuple(output.get("high_level_keywords") or []),
        low_level_keywords=tuple(output.get("low_level_keywords") or []),
        cache_served=cache_served,
    )


# --------------------------------------------------------------------------------------------- #
# The retrieval-level diff — deterministic, zero-token, reachable with no client wired at all
# --------------------------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RetrievalDiff:
    decomposed_ids: tuple[str, ...]
    original_ids: tuple[str, ...]
    symmetric_difference: tuple[str, ...]
    ranking_agreement: float
    first_disagreement_position: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "decomposed_ids": list(self.decomposed_ids),
            "original_ids": list(self.original_ids),
            "symmetric_difference": list(self.symmetric_difference),
            "ranking_agreement": self.ranking_agreement,
            "first_disagreement_position": self.first_disagreement_position,
        }


def _first_disagreement_position(a: list[str], b: list[str]) -> int | None:
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    if len(a) != len(b):
        return min(len(a), len(b))
    return None


def _ranking_agreement(a: list[str], b: list[str]) -> float:
    """Kendall-style pairwise concordance fraction, restricted to ids common to both lists: for
    every pair of commonly-retrieved ids, do the two lists agree on which comes first? 1.0 for
    zero or one common id (nothing to disagree on) or for two identical lists; 0.0 for two fully
    disjoint (non-empty vs empty is handled by the caller).
    """
    common = set(a) & set(b)
    if len(common) < 2:
        return 1.0
    order_a = [x for x in a if x in common]
    pos_b = {v: i for i, v in enumerate(b) if v in common}
    concordant = 0
    total = 0
    for i in range(len(order_a)):
        for j in range(i + 1, len(order_a)):
            total += 1
            if pos_b[order_a[i]] < pos_b[order_a[j]]:
                concordant += 1
    return concordant / total if total else 1.0


def _no_retrieval_to_compare_note(arm_name: str, has_chunk_node: bool) -> str | None:
    """``None`` when ``arm_name``'s resolved node set includes a chunk-source node (there is a
    real chunk-set comparison to make); otherwise a stated reason distinguishing "no retrieval
    happened for this arm" from "the comparison happened and found zero difference" — the
    ``bypass`` arm's own case (a single ``generate`` node, no retrieval at all). A pure function
    of the one fact that decides it, directly testable with no scheduler, no store, no client.
    """
    if has_chunk_node:
        return None
    return (
        f"the {arm_name!r} arm resolves to a single 'generate' node with no retrieval at "
        "all — there is no chunk-set comparison to make for this arm, distinct from a "
        "computed zero symmetric difference"
    )


def diff_ranked_ids(decomposed_ids: list[str], original_ids: list[str]) -> RetrievalDiff:
    """The deterministic, zero-token retrieval-level diff (criterion 6, D-10) — pure list/set
    arithmetic over two ranked id lists. Makes no LLM call, no store call, no client call of any
    kind: reachable with no client wired at all (Task 2's own acceptance criterion).
    """
    a = list(decomposed_ids)
    b = list(original_ids)
    set_a, set_b = set(a), set(b)
    sym_diff = tuple(sorted(set_a ^ set_b))

    if not set_a and not set_b:
        agreement = 1.0
    elif not (set_a & set_b):
        agreement = 0.0
    else:
        agreement = _ranking_agreement(a, b)

    return RetrievalDiff(
        decomposed_ids=tuple(a),
        original_ids=tuple(b),
        symmetric_difference=sym_diff,
        ranking_agreement=agreement,
        first_disagreement_position=_first_disagreement_position(a, b),
    )


# --------------------------------------------------------------------------------------------- #
# The decomposed arm — pinned keywords injected, full per-node results kept (not just `provides`)
# --------------------------------------------------------------------------------------------- #


def _inject_pinned_keywords(resolved: dict[str, Any], hl_keywords: list[str], ll_keywords: list[str]) -> dict[str, Any]:
    """A no-op when the resolved arm has no ``keywords`` node (``naive``/``bypass``) — mirrors
    ``databasise/parity/run_arm.py``'s own ``_inject_query``/``_inject_token_allowance`` no-op
    convention for a node the resolved arm does not contain.
    """
    nodes = resolved.get("nodes", {})
    if _KEYWORDS_NODE_ID not in nodes:
        return resolved
    config = dict(nodes[_KEYWORDS_NODE_ID].get("config") or {})
    config["pinned"] = True
    config["pinned_output"] = {
        "high_level_keywords": list(hl_keywords),
        "low_level_keywords": list(ll_keywords),
    }
    nodes[_KEYWORDS_NODE_ID]["config"] = config
    return resolved


async def _run_decomposed_arm(
    arm_name: str,
    query: str,
    *,
    pinned_hl_keywords: list[str],
    pinned_ll_keywords: list[str],
    registry: PartRegistry,
    store_root: Path,
    workspace: str,
    clients: dict[str, Any],
    token_allowance: int = _DEFAULT_TOKEN_ALLOWANCE,
) -> dict[str, Any]:
    """Drives one real decomposed-arm run through ``runner.scheduler.run_wiring`` directly
    (mirroring ``databasise/parity/run_arm.py``'s own driver, whose store/client-assembly
    helpers this function reuses without modification), keeping every node's raw output —
    ``run_arm.run_arm()`` itself only returns the resolved wiring's own ``provides`` list, which
    is too narrow for the retrieval-level diff below (it names only ``generate``, never
    ``rerank``/``budget-entities``/``budget-relations``).
    """
    resolved = resolve_arm(arm_name)
    resolved = _inject_query(resolved, query)
    resolved = _inject_token_allowance(resolved, token_allowance)
    resolved = _inject_pinned_keywords(resolved, pinned_hl_keywords, pinned_ll_keywords)
    parsed = parse_wiring(resolved, registry)

    stores = _build_stores(store_root, workspace)
    try:
        scheduled = await _scheduler.run_wiring(
            parsed,
            registry,
            stores,
            determinism_setting=_DECOMPOSED_DETERMINISM_SETTING,
            concurrency_setting=_DECOMPOSED_CONCURRENCY_SETTING,
            clients=clients,
        )
    finally:
        for store in stores.values():
            await store.finalize()

    if "cycle" in scheduled:
        return {"cycle": scheduled["cycle"], "resolved": resolved}

    wiring_bytes = canonicalise(resolved)
    wiring_instance_hash = f"sha256:{hashlib.sha256(wiring_bytes).hexdigest()}"
    wiring_id = resolved.get("wiring_id") or f"wiring:{hashlib.sha256(wiring_bytes).hexdigest()[:16]}"

    record = RunRecord(
        run_id=f"parity-{arm_name}-{hashlib.sha256(query.encode('utf-8')).hexdigest()[:12]}",
        wiring_id=wiring_id,
        wiring_instance_hash=wiring_instance_hash,
        arm_id=arm_name,
        arm_execution_order=0,
        executor_version=_EXECUTOR_VERSION,
        concurrency_setting=_DECOMPOSED_CONCURRENCY_SETTING,
        determinism_setting=_DECOMPOSED_DETERMINISM_SETTING,
        nodes=scheduled["nodes"],
        partial=scheduled["partial"],
        degraded=scheduled["degraded"],
        stop_reason=scheduled["stop_reason"],
        degradation_reason=scheduled["degradation_reason"],
    )

    return {"run_record": record.to_dict(), "results": scheduled["results"], "resolved": resolved}


def _extract_decomposed_ids(results: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    """Read the final ranked chunk/entity/relation ids out of the decomposed arm's full node
    result set — ``rerank`` for chunks (present in every arm that retrieves chunks at all;
    passthrough when the wiring configures no live reranker, per ``rerank.py``'s own docstring, so
    the order recorded here is the same order ``chunk-vector`` produced), ``budget-entities``/
    ``budget-relations`` for the final, post-truncation entity/relation lists — matching v1's own
    ``aquery_data``, which likewise returns the *final* (post-truncation) entities/relationships/
    chunks it would send to the LLM. An arm whose resolved node set lacks one of these positions
    (``naive``/``bypass`` have no entities/relations at all) reports an empty list for it, exactly
    like v1's own documented behaviour for those same two modes.
    """
    chunk_output = results.get(_CHUNK_SOURCE_NODE_ID)
    chunk_ids = [str(item["id"]) for item in (chunk_output or {}).get("items", [])]

    entity_output = results.get(_ENTITY_SOURCE_NODE_ID)
    entity_ids = [str(item["entity_name"]) for item in (entity_output or {}).get("items", [])]

    relation_output = results.get(_RELATION_SOURCE_NODE_ID)
    relation_ids = [
        _relation_comparison_id(item)
        for item in (relation_output or {}).get("items", [])
    ]

    return chunk_ids, entity_ids, relation_ids


def _relation_comparison_id(item: dict[str, Any]) -> str:
    """Build the ``src->tgt`` comparison id regardless of which of the two relation item shapes
    survives dedup into ``budget-relations`` — ``entity-hydrate-expand`` emits ``src_tgt``,
    ``relation-hydrate-expand`` emits ``src_id``/``tgt_id`` (see ``join_roundrobin.py``'s own
    dual-shape ``_relation_key`` dedup helper, which already treats both as legitimate). The
    ``global`` arm's ``join-relations.deps`` is patched to ``relation-hydrate-expand`` only, so
    every item there lacks ``src_tgt`` — CR-01.
    """
    pair = item.get("src_tgt")
    if pair is None:
        pair = (item.get("src_id"), item.get("tgt_id"))
    return f"{pair[0]}->{pair[1]}"


# --------------------------------------------------------------------------------------------- #
# The comparison record and per-query orchestration
# --------------------------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ComparisonRecord:
    status: Literal["completed", "inconclusive"]
    arm: str
    query_id: str
    query: str
    corpus_hash: str
    determinism_setting: str
    concurrency_setting: str
    run_count: int
    pinned_keywords: dict[str, list[str]] | None
    keyword_variance_band: KeywordVarianceBand | None
    chunk_diff: RetrievalDiff | None
    entity_diff: RetrievalDiff | None
    relation_diff: RetrievalDiff | None
    decomposed_run_record: dict[str, Any] | None
    original_arm_result: dict[str, Any] | None
    resolved_model_identities: dict[str, str]
    inconclusive_reason: str | None = None
    retrieval_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "arm": self.arm,
            "query_id": self.query_id,
            "query": self.query,
            "corpus_hash": self.corpus_hash,
            "determinism_setting": self.determinism_setting,
            "concurrency_setting": self.concurrency_setting,
            "run_count": self.run_count,
            "pinned_keywords": self.pinned_keywords,
            "keyword_variance_band": self.keyword_variance_band.to_dict() if self.keyword_variance_band else None,
            "chunk_diff": self.chunk_diff.to_dict() if self.chunk_diff else None,
            "entity_diff": self.entity_diff.to_dict() if self.entity_diff else None,
            "relation_diff": self.relation_diff.to_dict() if self.relation_diff else None,
            "decomposed_run_record": self.decomposed_run_record,
            "original_arm_result": self.original_arm_result,
            "original_arm_instrumentation": "harness-external",
            "resolved_model_identities": dict(self.resolved_model_identities),
            "inconclusive_reason": self.inconclusive_reason,
            "retrieval_note": self.retrieval_note,
        }


def _inconclusive_record(
    arm_name: str, query_id: str, query_text: str, corpus_hash: str, reason: str
) -> ComparisonRecord:
    return ComparisonRecord(
        status="inconclusive",
        arm=arm_name,
        query_id=query_id,
        query=query_text,
        corpus_hash=corpus_hash,
        determinism_setting=_DECOMPOSED_DETERMINISM_SETTING,
        concurrency_setting=_DECOMPOSED_CONCURRENCY_SETTING,
        run_count=0,
        pinned_keywords=None,
        keyword_variance_band=None,
        chunk_diff=None,
        entity_diff=None,
        relation_diff=None,
        decomposed_run_record=None,
        original_arm_result=None,
        resolved_model_identities={},
        inconclusive_reason=reason,
    )


async def compare_arm_on_query(
    arm_name: str,
    query_id: str,
    query_text: str,
    *,
    corpus_hash: str = "",
    keyword_variance_runs: int = _DEFAULT_KEYWORD_VARIANCE_RUNS,
    registry: PartRegistry | None = None,
    store_root: Path | None = None,
    workspace: str | None = None,
    clients: dict[str, Any] | None = None,
    env_path: Path | None = None,
    v1_interpreter: Path | None = None,
    v1_working_dir: Path | None = None,
    verify_fn: VerifyImportFn | None = None,
) -> ComparisonRecord:
    """Run the full pinning-plus-diff comparison for one query against one arm. Returns a
    ``status="inconclusive"`` record with no comparison number if the index-identity precondition
    (plan 03-02's verifier) has not passed — this check runs first, before either arm is touched.
    """
    verify_fn = verify_fn or import_index.verify_import
    verify_kwargs: dict[str, Any] = {}
    if store_root is not None:
        verify_kwargs["store_root"] = store_root
    if workspace is not None:
        verify_kwargs["workspace"] = workspace
    verification = await verify_fn(**verify_kwargs)

    if verification.status != "verified":
        violation_summary = "; ".join(
            f"{v.assertion}: {v.detail}" for v in verification.violations
        ) or "no comparison could be made"
        return _inconclusive_record(
            arm_name,
            query_id,
            query_text,
            corpus_hash,
            f"index-identity precondition returned {verification.status!r} ({violation_summary})",
        )

    registry = registry or default_registry()

    env = _load_env_file(env_path or DEFAULT_V1_ENV_PARITY)
    resolved_clients = clients if clients is not None else _build_clients(env)

    resolved_workspace = workspace
    if resolved_workspace is None:
        resolved_workspace = import_index._import_workspace()
    resolved_store_root = store_root or import_index.DEFAULT_STORE_ROOT

    resolved_arm = resolve_arm(arm_name)
    has_keywords_node = _KEYWORDS_NODE_ID in resolved_arm.get("nodes", {})
    has_chunk_node = _CHUNK_SOURCE_NODE_ID in resolved_arm.get("nodes", {})

    pinned_keywords: dict[str, list[str]] | None = None
    band: KeywordVarianceBand | None = None
    pinned_hl: list[str] = []
    pinned_ll: list[str] = []

    if has_keywords_node:
        pin_result = await _run_keywords_live(query_text, resolved_clients, registry)
        pinned_hl = list(pin_result.high_level_keywords)
        pinned_ll = list(pin_result.low_level_keywords)
        pinned_keywords = {"high_level_keywords": pinned_hl, "low_level_keywords": pinned_ll}

        band_runs = [
            await _run_keywords_live(query_text, resolved_clients, registry)
            for _ in range(keyword_variance_runs)
        ]
        band = compute_keyword_variance_band(band_runs)

    decomposed = await _run_decomposed_arm(
        arm_name,
        query_text,
        pinned_hl_keywords=pinned_hl,
        pinned_ll_keywords=pinned_ll,
        registry=registry,
        store_root=resolved_store_root,
        workspace=resolved_workspace,
        clients=resolved_clients,
    )
    decomposed_chunk_ids, decomposed_entity_ids, decomposed_relation_ids = _extract_decomposed_ids(
        decomposed.get("results", {})
    )

    v1_mode = _ARM_TO_V1_MODE[arm_name]
    v1_result: V1ArmResult = await asyncio.to_thread(
        run_v1_arm,
        v1_mode,
        query_text,
        hl_keywords=pinned_hl,
        ll_keywords=pinned_ll,
        interpreter=v1_interpreter,
        env_path=env_path,
        working_dir=v1_working_dir or DEFAULT_V1_WORKING_DIR,
    )

    # A resolved arm with no chunk-source node (bypass: a single `generate` node, no retrieval at
    # all) has nothing to diff — computing diff_ranked_ids([], []) here would read as a genuine
    # zero symmetric difference (perfect agreement), which is not what "no retrieval happened"
    # means. Recorded distinctly via retrieval_note instead (03-09-PLAN.md Task 1's own stated
    # prohibition).
    chunk_diff = (
        diff_ranked_ids(decomposed_chunk_ids, list(v1_result.chunk_ids)) if has_chunk_node else None
    )
    retrieval_note = _no_retrieval_to_compare_note(arm_name, has_chunk_node)
    entity_diff = (
        diff_ranked_ids(decomposed_entity_ids, list(v1_result.entity_ids)) if has_keywords_node else None
    )
    relation_diff = (
        diff_ranked_ids(decomposed_relation_ids, list(v1_result.relation_ids)) if has_keywords_node else None
    )

    generate_output = decomposed.get("results", {}).get("generate") or {}
    resolved_model_identities = {
        "decomposed_generate": str(generate_output.get("resolved_model_identity", "")),
        "original_arm_llm_model": env.get("LLM_MODEL", ""),
        "original_arm_embedding_model": env.get("EMBEDDING_MODEL", ""),
    }

    return ComparisonRecord(
        status="completed",
        arm=arm_name,
        query_id=query_id,
        query=query_text,
        corpus_hash=corpus_hash,
        determinism_setting=_DECOMPOSED_DETERMINISM_SETTING,
        concurrency_setting=_DECOMPOSED_CONCURRENCY_SETTING,
        run_count=1 + keyword_variance_runs if has_keywords_node else 0,
        pinned_keywords=pinned_keywords,
        keyword_variance_band=band,
        chunk_diff=chunk_diff,
        entity_diff=entity_diff,
        relation_diff=relation_diff,
        decomposed_run_record=decomposed.get("run_record"),
        original_arm_result=v1_result.to_dict(),
        resolved_model_identities=resolved_model_identities,
        retrieval_note=retrieval_note,
    )


# --------------------------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------------------------- #

_RESULTS_DIR = Path(__file__).resolve().parent / ".comparison_results"


def _render_human_summary(records: list[ComparisonRecord]) -> str:
    lines = ["=" * 70, "  PARITY COMPARISON RESULT", "=" * 70]
    for record in records:
        lines.append(f"\n  query: {record.query_id!r} arm: {record.arm!r} status: {record.status}")
        if record.status == "inconclusive":
            lines.append(f"    inconclusive: {record.inconclusive_reason}")
            continue
        lines.append(f"    determinism: {record.determinism_setting}, concurrency: {record.concurrency_setting}")
        if record.pinned_keywords is not None:
            lines.append(f"    pinned keywords: {record.pinned_keywords}")
        if record.keyword_variance_band is not None:
            band = record.keyword_variance_band
            lines.append(
                f"    keyword variance band (N={band.run_count}, cache_served={band.any_cache_served}): "
                f"hl_size_mean={band.high_level_size_mean:.2f} ll_size_mean={band.low_level_size_mean:.2f}"
            )
        if record.chunk_diff is not None:
            lines.append(
                f"    chunk diff: sym_diff={len(record.chunk_diff.symmetric_difference)} "
                f"agreement={record.chunk_diff.ranking_agreement:.3f} "
                f"first_disagreement={record.chunk_diff.first_disagreement_position}"
            )
        elif record.retrieval_note is not None:
            lines.append(f"    chunk diff: {record.retrieval_note}")
        lines.append("    original arm instrumentation: harness-external (no RIG §TR.1 record — D-05)")
    lines.append("\n" + "=" * 70)
    return "\n".join(lines)


async def _run_cli(arm_name: str, query_ids: list[str] | None) -> tuple[list[ComparisonRecord], bool]:
    snapshot: CorpusSnapshot = load_snapshot()
    queries = snapshot.queries
    if query_ids:
        wanted = set(query_ids)
        queries = tuple(q for q in queries if q.id in wanted)

    records: list[ComparisonRecord] = []
    had_error = False
    for query in queries:
        try:
            record = await compare_arm_on_query(
                arm_name, query.id, query.question, corpus_hash=snapshot.corpus_hash
            )
        except (MissingParityEnvError, MissingV1InterpreterError, V1ArmSubprocessError) as exc:
            had_error = True
            print(f"error comparing query {query.id!r}: {exc}", file=sys.stderr)
            continue
        records.append(record)
    return records, had_error


def main(argv: list[str] | None = None) -> int:
    """``uv run python -m databasise.parity.run_comparison --arm naive`` — prints the human
    summary and the JSON result path. Exit codes: ``0`` every requested query completed cleanly,
    ``1`` at least one query errored while running an arm, ``2`` at least one query was
    inconclusive (the index-identity precondition failed) — distinct from both the clean and the
    error status, per this module's own "never a plain pass/fail" rule.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", required=True, choices=sorted(_ARM_TO_V1_MODE))
    parser.add_argument("--query", action="append", dest="query_ids", default=None)
    args = parser.parse_args(argv)

    records, had_error = asyncio.run(_run_cli(args.arm, args.query_ids))

    print(_render_human_summary(records))

    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_path = _RESULTS_DIR / f"{args.arm}.json"
    result_path.write_text(
        json.dumps([r.to_dict() for r in records], indent=2, default=str), encoding="utf-8"
    )
    print(f"\n[result] JSON result written to: {result_path}")

    if had_error:
        return 1
    if any(r.status == "inconclusive" for r in records):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
