"""``lightrag/full-delete@0.2.0`` — the second registered port of the LightRAG corpus-side engine
(05-03-PLAN.md Task 1): the deleting sibling of ``lightrag/full-ingest@0.2.0``, backed by the same
subprocess-hosted v1 engine but with its own §8 admission record and its own ``name_at_version``,
per CONTRACT §19.6's separate-port rule. Neither part exposes the other's operation.

11-03-PLAN.md (D-06) is this port's one ``@0.2.0`` bump: it declares ``calls_llm`` (a
partial-rebuild delete can reach the LLM), its storage is ``self-contained``, and the driver
returns token usage, which the body meters (D-13).

``LIGHTRAG_FULL_DELETE_ADMISSION`` is this port's own eleven-``ConditionVerdict`` record, numbered
as CONTRACT §8 numbers it (LRAG-12): 3 carries network denial by construction and the spend rule,
8 the 90-day TTL with ledger renewal, 9 the ``part_ref`` counting. Where a verdict states the same
fact as the ingest record, it is stated here in this record's own words — never imported from the
ingest record's tuple, per §19.6's "two ports, two records" reading.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from databasise.foreign import run_corpus_op
from databasise.foreign.v1_corpus_adapter import DEFAULT_V1_INTERPRETER
from databasise.identity.canon import canonicalise
from databasise.parts.admission import (
    MANIFEST_SOURCE_CODE_INSPECTED,
    AdmissionRecord,
    ConditionVerdict,
)
from databasise.parts.schema import NodeContext
from databasise.parts_core.lightrag.full_ingest import (
    to_thread_until_done,
    tokens_from_usage,
)

# v1's own deletion path performs graph and vector surgery plus a bounded rebuild over surviving
# sources for a partially-affected entity/relation — the machine declares this ceiling, v1 never
# self-reports one (§8 condition 4). See 05-03-SUMMARY.md for the measured real-run duration this
# value is grounded against.
DELETE_WALL_CLOCK_CEILING_SECONDS = 300.0

_V1_ROOT = Path(__file__).resolve().parents[3] / "v1"


def _compute_environment_hash() -> str:
    """§8 condition 2's whole-resolved-runtime-closure rule, computed independently of
    ``full_ingest.py``'s own identically-shaped function — two ports, two records, per this
    module's own docstring; the digest covers the same three inputs (resolved interpreter path,
    ``v1/uv.lock`` text, ``v1/.python-version`` text) and so resolves to the same value on a given
    machine, without either port's record importing the other's.
    """
    interpreter = str(DEFAULT_V1_INTERPRETER)
    uv_lock_path = _V1_ROOT / "uv.lock"
    python_version_path = _V1_ROOT / ".python-version"
    payload = {
        "interpreter": interpreter,
        "uv_lock": uv_lock_path.read_text(encoding="utf-8") if uv_lock_path.exists() else "",
        "python_version": (
            python_version_path.read_text(encoding="utf-8") if python_version_path.exists() else ""
        ),
    }
    return "sha256:" + hashlib.sha256(canonicalise(payload)).hexdigest()


LIGHTRAG_FULL_DELETE_ADMISSION = AdmissionRecord(
    part_name_at_version="lightrag/full-delete@0.2.0",
    entry_path="in-process opaque core, hosted as a subprocess under v1's pinned interpreter",
    storage="self-contained",
    wall_clock_ceiling_seconds=DELETE_WALL_CLOCK_CEILING_SECONDS,
    wall_clock_ceiling_basis=(
        "v1's own deletion path (adelete_by_doc_id) performs graph and vector surgery plus a "
        "bounded rebuild over surviving sources for a partially-affected entity/relation; the "
        "machine declares this ceiling, v1 never self-reports one"
    ),
    feed_tier="n/a — this port consumes a document id, never a machine-produced feed",
    ttl_days=90,
    network_namespace=(
        "denied-by-construction: the same machine-injected LLM_BINDING_HOST/EMBEDDING_BINDING_HOST "
        "env the ingest driver script uses (v1_corpus_driver_script.py's shared _build_rag/"
        "_llm_model_func) — the delete driver configures no independent outbound endpoint, even "
        "when a partial-rebuild path reaches the LLM"
    ),
    environment_hash=_compute_environment_hash(),
    manifest_source=MANIFEST_SOURCE_CODE_INSPECTED,
    verdicts=(
        ConditionVerdict(
            condition=1,
            verdict="satisfied",
            evidence=(
                "manifest_source is 'code-inspected' (this record), not the engine's own "
                "self-report — enforced structurally by validate_admission"
            ),
        ),
        ConditionVerdict(
            condition=2,
            verdict="satisfied",
            evidence=(
                "environment_hash covers the resolved interpreter path plus v1/uv.lock and "
                "v1/.python-version's own text, computed by this record's own "
                "_compute_environment_hash — the whole resolved runtime closure the delete "
                "subprocess launches under"
            ),
        ),
        ConditionVerdict(
            condition=3,
            verdict="satisfied by construction",
            evidence=(
                "network denial by construction: the delete subprocess, including its "
                "partial-rebuild path, reaches only the machine's injected "
                "LLM_BINDING_HOST/EMBEDDING_BINDING_HOST via the same _build_rag/_llm_model_func "
                "the ingest op uses; no OS-level namespace sandbox exists under the no-Docker "
                "constraint. Spend: the driver hands lightrag.utils.TokenTracker to both model "
                "functions and returns its usage; full_delete_body reports the LLM half with "
                "counted_by='v1-subprocess', 'none' for no model call, and 'unbudgetable' when "
                "the provider reports no usage — never an estimate"
            ),
        ),
        ConditionVerdict(
            condition=4,
            verdict="satisfied",
            evidence=(
                "DELETE_WALL_CLOCK_CEILING_SECONDS=300.0 is declared here and enforced by "
                "databasise.foreign.run_corpus_op's timeout= parameter, raising "
                "CorpusOpTimeoutError on breach — databasise.validator.execution_mode.host "
                "refuses to host this placement at all without a positive ceiling"
            ),
        ),
        ConditionVerdict(
            condition=5,
            verdict="satisfied",
            evidence=(
                "storage='self-contained': v1 deletes only inside its per-workspace working dir "
                "<store_root>/<workspace>/lightrag-v1; the v2 rows are pruned by the "
                "lightrag/v1-index-sync node through ctx.stores. LIGHTRAG_FULL_DELETE_PART."
                "artifact_scope=None, so the shared-scope prohibition is vacuously satisfied"
            ),
        ),
        ConditionVerdict(
            condition=6,
            verdict="satisfied",
            evidence=(
                "feed_tier='n/a — this port consumes a document id, never a machine-produced "
                "feed' — a delete call carries a caller-supplied document id, structurally "
                "distinct from the machine-typed evidence feed condition 6 governs"
            ),
        ),
        ConditionVerdict(
            condition=7,
            verdict="satisfied (machine-side obligation)",
            evidence=(
                "enforced by databasise.parts.admission.cross_check_conditions at registration "
                "time: the corpus-delete wiring's own provides node must be excluded from the "
                "default selector's candidate set (databasise.seam.selectors._is_default_eligible)"
            ),
        ),
        ConditionVerdict(
            condition=8,
            verdict="machine-side-obligation",
            evidence=(
                "ttl_days=90 is declared on this record; renewal only with a recorded reason, each "
                "renewal recorded in the ledger, is a machine-side ledger mechanic this port "
                "cannot itself prove"
            ),
        ),
        ConditionVerdict(
            condition=9,
            verdict="machine-side-obligation",
            evidence=(
                "this port is reached only by an explicit Databasise.delete_document() call "
                "through the corpus-delete wiring; counting explicit part_ref invocations as data "
                "and never as a promotion trigger is a machine-side ledger mechanic"
            ),
        ),
        ConditionVerdict(
            condition=10,
            verdict="satisfied (machine-side obligation)",
            evidence=(
                "enforced by databasise.parts.admission.cross_check_conditions: this part's "
                "artifact_scope=None declares no artifact scope at all, and the machine keeps no "
                "artifact registry (removed in Phase 10, D-15), so nothing enumerates this part's "
                "output as an SA-1-shareable artifact"
            ),
        ),
        ConditionVerdict(
            condition=11,
            verdict="satisfied by construction",
            evidence=(
                "databasise.seam.query.QueryObject declares no 'as_of' member and the Effect "
                "vocabulary (databasise.parts.schema.Effect) has no temporal-capability member — "
                "structurally impossible to violate, checked at registration by "
                "cross_check_conditions"
            ),
        ),
    ),
)


async def full_delete_body(ctx: NodeContext) -> dict[str, Any]:
    """Reads ``doc_id``/``delete_llm_cache`` from ``ctx.config``, launches the v1 corpus driver's
    ``delete`` branch via ``run_corpus_op`` (blocking — run by ``to_thread_until_done``, so a
    cancel waits for the subprocess, A-CR-01), and returns the driver's payload with the spend metered from
    its ``usage`` (``tokens_from_usage``, the same rule as ingest; condition 3's verdict above).

    11-01-PLAN.md (LRAG-02): this body reports no store touches. v1's subprocess changes v1's own
    working dir, not the v2 stores; the v2 change is made by the ``lightrag/v1-index-sync`` node
    that follows it, whose touches the machine observes, so the delete's MACH-11 event comes from
    that node.
    """
    config = ctx.config or {}
    payload: dict[str, Any] = {
        "doc_id": config.get("doc_id"),
        "delete_llm_cache": bool(config.get("delete_llm_cache", False)),
    }

    result = await to_thread_until_done(
        run_corpus_op,
        "delete",
        payload,
        timeout=DELETE_WALL_CLOCK_CEILING_SECONDS,
        working_dir=config.get("working_dir"),  # 11-01 (LRAG-01): stamped by the engine
    )

    return {**result, "tokens": tokens_from_usage(result.get("usage"))}


__all__ = [
    "DELETE_WALL_CLOCK_CEILING_SECONDS",
    "LIGHTRAG_FULL_DELETE_ADMISSION",
    "full_delete_body",
]
