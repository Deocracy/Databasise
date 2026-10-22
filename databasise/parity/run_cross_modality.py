"""One real cross-modality comparison run — LightRAG's ``naive`` arm and HippoRAG 2's base wiring,
answering the same Phase 3 parity corpus through one ``Databasise.compare()`` call per query
(06-08-PLAN.md Task 2) — a comparison harness in ``run_comparison.py``'s own shape: pre-flight
verification first, then the run, then a machine-readable :class:`CrossModalityRecord` plus a
human-readable summary, with a non-zero exit meaning something.

**Exact invocation:**

    uv run python -m databasise.parity.run_cross_modality

**Pre-flight, before any query** (:func:`preflight`): both arms' indexes are present and
non-empty at their own declared namespaces; the two arms' resolved store directory sets are
disjoint; and ``artifacts_overlap`` between the two arms' index-recipe hashes is recorded.
RIG.md ``## §RUN.2``'s rule is an iff on recipe hashes and nothing else — never a similarity
judgment — and the expected result here is ``False``, the same zero-overlap case ``## §RUN.2``'s
own worked ``VT-1``/``GR-1`` pair states as the norm for two unrelated recipes sharing no resolved
input: no artifact sharing, two full index costs.

A run where either arm reports ``partial`` or ``degraded`` on any query is refused — a confounded
run serialised as a clean comparison reads as settled rather than unsettled, which this project's
own trace-honesty invariant already refuses at the record layer (``RunRecord.__post_init__``) and
this harness refuses at the report layer.

**Structural comparability, made checkable rather than asserted.** Every item both arms return
conforms to the same ``§4`` item shape (``databasise.seam.envelope.ResponseEnvelope``'s own
``EvidenceRef`` element type) and the two envelopes carry identical field sets — a type guarantee,
not a content guarantee. The two arms' actual passages and scores may differ arbitrarily, which is
the point of architecture-comparison mode (RIG.md ``## §AA.4``); this harness's own summary states
that explicitly so a reader of the numbers cannot mistake a retrieval difference for a defect.

**Real runs.** This module ran for real on 2026-09-10 against the Phase 3 parity corpus; the
refused first attempt and the completed run are recorded in
``databasise/evidence/CROSS-MODALITY-EVIDENCE.md`` ("Real run attempted - refused" and "Real
run"). Phase 12 has changed the HippoRAG path since, so a HippoRAG store built before Phase 12 must
be rebuilt (``databasise.parity.build_hipporag_index``) before a new run.

**Offline CLI.** Needs a source checkout with the imported parity store and ``v1/.env.parity``;
neither ships in the wheel. Without ``--spend`` it prints an estimate, ends on an estimate-only
line and touches nothing. Exit codes: 0 done or estimate-only; 1 a named refusal (one stderr line ``ClassName: message``);
2 bad arguments. A refusal for a partial or degraded arm keeps the per-query records collected so
far in ``cross_modality.json``, marked ``"status": "refused"``.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from databasise import cli
from databasise.identity.canon import canonicalise
from databasise.namespaces import artifacts_overlap
from databasise.parity import import_index
from databasise.parity.build_hipporag_index import unverified_build_marker
from databasise.parity.corpus import CorpusQuery, load_snapshot
from databasise.parity.run_arm import (
    DEFAULT_V1_ENV_PARITY,
    _build_clients,
    _load_env_file,
    estimate_arm,
)
from databasise.parts.registry import default_registry
from databasise.seam import Databasise, QueryObject
from databasise.seam.engine import _GRAPH_KIND, _TEXT_CHUNKS_KIND
from databasise.seam.envelope import ResponseEnvelope
from databasise.seam.selectors import Selector
from databasise.store_lock import store_lock
from databasise.stores.vector import VectorStoreCorruptedError, load_committed
from databasise.wirings.resolve import load_wiring, resolve_arm

_LIGHTRAG_ARM = "naive"
_HIPPORAG_ARM = "hipporag"
_LIGHTRAG_CAPABILITY = ["reads_vector"]
_HIPPORAG_CAPABILITY = ["reads_graph", "reads_kv"]

# Mirrors import_index.py's own _VECTOR_KINDS / entity_fact_embed.py's own namespace constants —
# every per-store-kind directory each arm's own recipe declares, used to prove the two arms'
# resolved on-disk directory sets are disjoint (RIG.md ## §RUN.1/§RUN.2).
_LIGHTRAG_VECTOR_NAMESPACES = ("chunks", "entities", "relationships")
_HIPPORAG_VECTOR_NAMESPACES = ("hipporag-chunks", "hipporag-entities", "hipporag-facts")

_STRUCTURAL_COMPARABILITY_NOTE = (
    "Every item both arms return conforms to the same §4 item shape and both envelopes carry the "
    "same field set — a type guarantee, not a content guarantee. A retrieval difference between "
    "the arms is expected (architecture-comparison mode, RIG.md ## §AA.4: two independently-"
    "registered wirings sharing no resolved recipe input) and is not a quality finding."
)


class MissingArmIndexError(RuntimeError):
    """Raised when one arm's index is absent or empty at its own declared namespaces — pre-flight
    refuses before any query runs, naming which arm and which harness builds it.
    """


class OverlappingStoreDirectoriesError(RuntimeError):
    """Raised when the two arms' resolved store directories are not disjoint — RIG.md
    ``## §RUN.1``/``## §RUN.2``'s isolation guarantee does not hold for this ``store_root``/
    ``workspace`` pair, naming the offending directories.
    """


class DegradedCrossModalityRunError(RuntimeError):
    """Raised when either arm reports ``partial`` or ``degraded`` on any query — a confounded run
    is refused rather than serialised as a clean comparison (this module's own docstring). Carries
    the query id, the arm key and the record of every query run so far, the offending one included,
    so :func:`main` can keep them on disk (TOOL-09).
    """

    def __init__(
        self,
        message: str,
        *,
        query_id: str | None = None,
        arm_key: str | None = None,
        record: CrossModalityRecord | None = None,
    ):
        super().__init__(message)
        self.query_id = query_id
        self.arm_key = arm_key
        self.record = record


@dataclass(frozen=True)
class PreflightResult:
    directories_disjoint: bool
    lightrag_recipe_hash: str
    hipporag_recipe_hash: str
    artifacts_overlap: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "directories_disjoint": self.directories_disjoint,
            "lightrag_recipe_hash": self.lightrag_recipe_hash,
            "hipporag_recipe_hash": self.hipporag_recipe_hash,
            "artifacts_overlap": self.artifacts_overlap,
        }


@dataclass(frozen=True)
class ArmQueryResult:
    """One arm's ``§18.2`` envelope for one query, reduced to what this record needs — the full
    envelope's own field set (for the structural-comparability check), the returned item count,
    and the honesty-invariant fields (``partial``/``degraded``/``stop_reason``/
    ``degradation_reason``)."""

    selector_key: str
    envelope_fields: tuple[str, ...]
    item_count: int
    items: list[dict[str, Any]]
    partial: bool
    degraded: bool
    stop_reason: str | None
    degradation_reason: str | None
    token_accounting: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "selector_key": self.selector_key,
            "envelope_fields": list(self.envelope_fields),
            "item_count": self.item_count,
            "items": self.items,
            "partial": self.partial,
            "degraded": self.degraded,
            "stop_reason": self.stop_reason,
            "degradation_reason": self.degradation_reason,
            "token_accounting": self.token_accounting,
        }


@dataclass(frozen=True)
class CrossModalityQueryRecord:
    query_id: str
    query: str
    arms: dict[str, ArmQueryResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "query": self.query,
            "arms": {key: arm.to_dict() for key, arm in self.arms.items()},
        }


@dataclass(frozen=True)
class CrossModalityRecord:
    corpus_hash: str
    preflight: PreflightResult
    queries: list[CrossModalityQueryRecord]
    structural_comparability_note: str = _STRUCTURAL_COMPARABILITY_NOTE
    # Set only when the caller supplied its own queries; the default run's record is unchanged.
    queries_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "corpus_hash": self.corpus_hash,
            "preflight": self.preflight.to_dict(),
            "queries": [q.to_dict() for q in self.queries],
            "structural_comparability_note": self.structural_comparability_note,
        }
        if self.queries_hash is not None:
            payload["queries_hash"] = self.queries_hash
        return payload


# --------------------------------------------------------------------------------------------- #
# Pre-flight
# --------------------------------------------------------------------------------------------- #


def _resolved_store_dirs(
    store_root: Path,
    workspace: str,
    resolved: dict[str, Any],
    vector_namespaces: tuple[str, ...],
) -> set[Path]:
    """Every directory this resolved wiring's own declared stores write under — graph, kv, and
    each of its own vector namespaces — computed the same way ``test_store_isolation.py`` already
    proves disjoint for the synthetic case, extended here to the real declared namespace lists.
    """
    # Phase 10 review WR-09: computed from the declared namespaces, never by opening stores, so no
    # graph client or kv connection is left held by a path-only question. The defaults are the same
    # ones ``seam.engine._build_stores`` falls back to.
    namespaces = resolved.get("store_namespaces") or {}
    root = Path(store_root) / workspace
    dirs = {root / namespaces.get("graph", _GRAPH_KIND), root / namespaces.get("kv", _TEXT_CHUNKS_KIND)}
    dirs.update(root / namespace for namespace in vector_namespaces)
    return dirs


def _index_recipe_hash(resolved: dict[str, Any]) -> str:
    """The resolved wiring's own structural identity, pre-query-injection — the "index recipe"
    RIG.md ``## §RUN.2``'s ``artifacts_overlap`` iff-rule compares. Computed identically to the
    ``wiring_instance_hash`` ``run_arm.py``/``engine.py`` already stamp on every ``RunRecord``, but
    over the wiring as resolved (no query text, no token allowance stamped yet) — query text is a
    per-call input, not part of the index recipe two arms either do or do not share.
    """
    return f"sha256:{hashlib.sha256(canonicalise(resolved)).hexdigest()}"


def _require_namespace(store_root: Path, workspace: str, namespace: str, builder: str) -> None:
    """Read-only: ``load_committed`` never creates a directory (D-10). Absent, empty or torn all refuse."""
    path = Path(store_root) / workspace / namespace
    try:
        committed = load_committed(path)
    except VectorStoreCorruptedError as exc:
        raise MissingArmIndexError(f"the vector namespace {namespace!r} at {path} is unreadable: {exc}") from exc
    if committed is None or not committed.entries:
        raise MissingArmIndexError(
            f"no built index in the vector namespace {namespace!r} at {path} - run {builder} first"
        )


def preflight(*, store_root: Path, workspace: str) -> PreflightResult:
    """Run before any query, in the order this module's own docstring states: both arms' indexes
    present and non-empty; the two arms' resolved store directories disjoint;
    ``artifacts_overlap`` between the two arms' index-recipe hashes recorded (never used to gate —
    an unexpected ``True`` is recorded, not silently turned into a refusal, since interpreting it
    is a human judgment this harness does not make for itself).
    """
    lightrag_resolved = resolve_arm(_LIGHTRAG_ARM)
    hipporag_resolved = load_wiring("hipporag")

    _require_namespace(store_root, workspace, "chunks", "databasise.parity.import_index (03-02-PLAN.md Task 3)")
    _require_namespace(
        store_root, workspace, "hipporag-chunks", "databasise.parity.build_hipporag_index (06-08-PLAN.md Task 1)"
    )
    marker = unverified_build_marker(store_root, workspace)
    if marker.exists():
        # A-WR-06: the builder refused (or never finished verifying) this index; its stores stay on disk.
        raise MissingArmIndexError(
            f"the HippoRAG index at {Path(store_root) / workspace} did not pass its builder's verification "
            f"({marker.name} is present) - rerun databasise.parity.build_hipporag_index --spend"
        )

    lightrag_dirs = _resolved_store_dirs(
        store_root, workspace, lightrag_resolved, _LIGHTRAG_VECTOR_NAMESPACES
    )
    hipporag_dirs = _resolved_store_dirs(
        store_root, workspace, hipporag_resolved, _HIPPORAG_VECTOR_NAMESPACES
    )
    overlap_dirs = lightrag_dirs & hipporag_dirs
    directories_disjoint = not overlap_dirs
    if not directories_disjoint:
        raise OverlappingStoreDirectoriesError(
            "the two arms' resolved store directories are not disjoint: "
            f"{sorted(str(d) for d in overlap_dirs)}"
        )

    lightrag_hash = _index_recipe_hash(lightrag_resolved)
    hipporag_hash = _index_recipe_hash(hipporag_resolved)
    overlap = artifacts_overlap(lightrag_hash, hipporag_hash)

    return PreflightResult(
        directories_disjoint=directories_disjoint,
        lightrag_recipe_hash=lightrag_hash,
        hipporag_recipe_hash=hipporag_hash,
        artifacts_overlap=overlap,
    )


# --------------------------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------------------------- #


def _arm_result_from_envelope(selector_key: str, envelope: ResponseEnvelope) -> ArmQueryResult:
    dumped = envelope.model_dump()
    return ArmQueryResult(
        selector_key=selector_key,
        envelope_fields=tuple(sorted(dumped.keys())),
        item_count=len(dumped.get("evidence") or []),
        items=[dict(item) for item in (dumped.get("evidence") or [])],
        partial=envelope.partial,
        degraded=envelope.degraded,
        stop_reason=envelope.stop_reason,
        degradation_reason=envelope.degradation_reason,
        token_accounting=[dict(entry) for entry in (dumped.get("token_accounting") or [])],
    )


async def run_cross_modality(
    *,
    store_root: Path | None = None,
    workspace: str | None = None,
    clients: dict[str, Any] | None = None,
    env_path: Path | None = None,
    queries: list[CorpusQuery] | None = None,
) -> CrossModalityRecord:
    """Run the full pre-flight-then-compare flow and return a :class:`CrossModalityRecord`.

    ``clients``/``store_root``/``workspace``/``queries`` are override points for tests, mirroring
    ``run_arm.run_arm``'s own convention.
    """
    registry = default_registry()
    # D-10: before any store read or client, prove each capability selector still picks the arm the
    # record names. The selectors themselves stay capability selectors (§18.4).
    cli.check_named_arm(Selector(capability=_LIGHTRAG_CAPABILITY), arm_id=_LIGHTRAG_ARM, registry=registry)
    cli.check_named_arm(Selector(capability=_HIPPORAG_CAPABILITY), arm_id=_HIPPORAG_ARM, registry=registry)

    snapshot = load_snapshot()
    resolved_store_root = store_root if store_root is not None else import_index.DEFAULT_STORE_ROOT
    resolved_workspace = workspace if workspace is not None else import_index._import_workspace()

    preflight_result = preflight(store_root=resolved_store_root, workspace=resolved_workspace)

    resolved_clients = clients
    if resolved_clients is None:
        env = _load_env_file(env_path or DEFAULT_V1_ENV_PARITY)
        resolved_clients = _build_clients(env)

    engine = Databasise(
        store_root=resolved_store_root,
        workspace=resolved_workspace,
        registry=registry,
        clients=resolved_clients,
    )

    selected_queries = list(queries) if queries is not None else list(snapshot.queries)
    corpus_hash, queries_hash = snapshot.corpus_hash, None
    if queries is not None:
        # The same json.dumps(sort_keys=True) form as CorpusSnapshot.queries_hash, over the queries
        # actually run, so a custom list can never record the default corpus_hash.
        queries_hash = hashlib.sha256(
            json.dumps([asdict(q) for q in selected_queries], sort_keys=True).encode("utf-8")
        ).hexdigest()
        corpus_hash = hashlib.sha256((snapshot.corpus_hash + queries_hash).encode("utf-8")).hexdigest()

    def record_of(done: list[CrossModalityQueryRecord]) -> CrossModalityRecord:
        return CrossModalityRecord(
            corpus_hash=corpus_hash,
            preflight=preflight_result,
            queries=list(done),
            queries_hash=queries_hash,
        )

    query_records: list[CrossModalityQueryRecord] = []
    for query in selected_queries:
        selectors = [Selector(capability=_LIGHTRAG_CAPABILITY), Selector(capability=_HIPPORAG_CAPABILITY)]
        result = await engine.compare(QueryObject(text=query.question), selectors)
        if not isinstance(result, dict):
            # RIG.md ## §RUN.3's degenerate-width rule never applies here: compare_arms is
            # reached at len(selectors) == 2, always. A bare envelope here would mean the seam's
            # own selector-count check regressed, not a legitimate outcome of this harness.
            raise RuntimeError(
                "engine.compare() returned a bare envelope for two selectors — expected a "
                f"{{selector_key: envelope}} mapping (query_id={query.id!r})"
            )
        arms = {key: _arm_result_from_envelope(key, envelope) for key, envelope in result.items()}
        query_records.append(CrossModalityQueryRecord(query_id=query.id, query=query.question, arms=arms))
        # A degraded but complete arm stays a refusal (15-RESEARCH Open Question 8): stop here and
        # keep what was collected, the offending query included.
        offending = next((key for key, arm in arms.items() if arm.partial or arm.degraded), None)
        if offending is not None:
            arm = arms[offending]
            state = "partial" if arm.partial else "degraded"
            why = arm.stop_reason if arm.partial else arm.degradation_reason
            raise DegradedCrossModalityRunError(
                f"arm {offending!r} reported {state} on query {query.id!r} ({why}) — refusing to "
                "record a confounded run as a clean comparison; the records so far are kept",
                query_id=query.id,
                arm_key=offending,
                record=record_of(query_records),
            )

    return record_of(query_records)


# --------------------------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------------------------- #

_RESULTS_DIR = Path(__file__).resolve().parent / ".comparison_results"


def _render_human_summary(record: CrossModalityRecord) -> str:
    lines = ["=" * 70, "  CROSS-MODALITY COMPARISON RESULT", "=" * 70]
    lines.append(f"\n  corpus_hash: {record.corpus_hash}")
    lines.append(
        f"  artifacts_overlap: {record.preflight.artifacts_overlap} "
        "(expected False — zero shared resolved input, RIG.md ## §RUN.2)"
    )
    lines.append(f"  directories_disjoint: {record.preflight.directories_disjoint}")
    for q in record.queries:
        lines.append(f"\n  query: {q.query_id!r}")
        for key, arm in q.arms.items():
            lines.append(
                f"    arm {key!r}: {arm.item_count} item(s), partial={arm.partial}, "
                f"degraded={arm.degraded}"
            )
    lines.append(f"\n  {record.structural_comparability_note}")
    lines.append("\n" + "=" * 70)
    return "\n".join(lines)


def _write_result(payload: dict[str, Any]) -> Path:
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_path = _RESULTS_DIR / "cross_modality.json"
    result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return result_path


def _print_estimate() -> None:
    """D-04: what a ``--spend`` run would do, from read-only facts. Takes no lock, builds no client,
    writes nothing; the preflight runs only when the workspace directory already exists."""
    snapshot = load_snapshot()
    question = snapshot.queries[0].question if snapshot.queries else ""
    print(f"queries: {len(snapshot.queries)} x 2 arms = {2 * len(snapshot.queries)} arm runs")
    for arm in (_LIGHTRAG_ARM, _HIPPORAG_ARM):
        print(json.dumps(estimate_arm(arm, question)))
    store_root, workspace = import_index.DEFAULT_STORE_ROOT, import_index._import_workspace()
    if (Path(store_root) / workspace).exists():
        try:
            print(f"preflight: {json.dumps(preflight(store_root=store_root, workspace=workspace).to_dict())}")
        except (MissingArmIndexError, OverlappingStoreDirectoriesError) as exc:
            print(f"preflight: refused - {exc}")
    else:
        print(f"preflight: skipped, no workspace directory at {Path(store_root) / workspace}")
    print("mode: estimate-only")


def main(argv: list[str] | None = None) -> int:
    """``uv run python -m databasise.parity.run_cross_modality --spend`` — the exact invocation this
    module's own docstring names. Without ``--spend`` it prints an estimate and ``mode:
    estimate-only`` and touches nothing. Exit codes: 0 done or estimate-only; 1 a named refusal (one
    stderr line), including a degraded or partial arm, whose records so far are written to
    ``cross_modality.json`` marked ``"status": "refused"``; 2 bad arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spend", action="store_true", default=False)
    args = parser.parse_args(argv)

    try:
        if not args.spend:
            _print_estimate()
            return cli.EXIT_OK
        with store_lock(import_index.DEFAULT_STORE_ROOT):  # D-03
            record = asyncio.run(run_cross_modality())
    except cli.offline_refusals(
        cli.ArmSelectorMismatchError,
        MissingArmIndexError,
        OverlappingStoreDirectoriesError,
        DegradedCrossModalityRunError,
    ) as exc:
        if isinstance(exc, DegradedCrossModalityRunError) and exc.record is not None:
            _write_result(
                {
                    **exc.record.to_dict(),
                    "status": "refused",
                    "reason": str(exc),
                    "query_id": exc.query_id,
                    "arm_key": exc.arm_key,
                }
            )
        return cli.refuse(exc)

    print(_render_human_summary(record))
    print(f"\n[result] JSON result written to: {_write_result(record.to_dict())}")
    return cli.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
