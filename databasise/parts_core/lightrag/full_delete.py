"""``lightrag/full-delete`` — the second registered port of the LightRAG corpus-side engine
(05-03-PLAN.md Task 1): the deleting sibling of ``lightrag/full-ingest@0.1.0``, backed by the same
subprocess-hosted v1 engine but declaring a different §8 admission record and a different
``name_at_version``, per CONTRACT §19.6's separate-port rule ("two invocations MUST be separate
ports where they differ in ... declared effects"). Ingest declares ``writes_artifact``; delete
declares ``mutates_store`` — neither part exposes the other's operation.

``LIGHTRAG_FULL_DELETE_ADMISSION`` is this port's own eleven-``ConditionVerdict`` §8 admission
record. Where a verdict states the same underlying fact as
``databasise.parts_core.lightrag.full_ingest.LIGHTRAG_FULL_INGEST_ADMISSION``'s own verdict (both
ports share the same v1 subprocess closure, the same network-denial-by-construction technique, the
same open condition-8 scope boundary), it is stated here in this record's own words with its own
evidence — never imported from the ingest record's tuple, per §19.6's "two ports, two records"
reading. Conditions 7, 8 and the counting half of 9 are machine-side/open obligations this record
alone cannot prove; see each verdict's own ``evidence`` string.
"""

from __future__ import annotations

import asyncio
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
from databasise.runner.trace import TokenAccounting

# v1's own deletion path performs graph and vector surgery plus a bounded rebuild over surviving
# sources for a partially-affected entity/relation — the machine declares this ceiling, v1 never
# self-reports one (§8 condition 4). See 05-03-SUMMARY.md for the measured real-run duration this
# value is grounded against.
DELETE_WALL_CLOCK_CEILING_SECONDS = 300.0

# Mirrors full_ingest.py's own sentinel exactly (databasise.seam.tokens.UNBUDGETABLE_SENTINEL,
# duplicated as a bare literal for the same one-way parts_core -> seam layering reason that
# module's own comment states).
_UNBUDGETABLE_TOKENS_SENTINEL = "unbudgetable"

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
    part_name_at_version="lightrag/full-delete@0.1.0",
    entry_path="in-process opaque core, hosted as a subprocess under v1's pinned interpreter",
    storage="machine",
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
                "the delete subprocess never makes an independent outbound LLM/embedding call, "
                "including on the partial-rebuild path — it reaches the machine's own injected "
                "LLM_BINDING_HOST/EMBEDDING_BINDING_HOST via the same _build_rag/_llm_model_func "
                "the ingest driver already uses (one shared _build_rag, both ops)"
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
                "LIGHTRAG_FULL_DELETE_PART.artifact_scope=None — this port registers no artifact "
                "at all, so §8 condition 5's shared-scope prohibition (restating §3) is "
                "vacuously satisfied, never merely narrowly avoided"
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
            verdict="open — accepted as a scope boundary, not a clean yes",
            evidence=(
                "no OS-level network-namespace isolation mechanism exists in databasise/ "
                "(05-RESEARCH.md Open Question 3, restated here for this port); denial is "
                "achieved by construction (condition 3) rather than by a sandbox, consistent "
                "with the project's no-Docker, local-NixOS constraint — the same open finding "
                "LIGHTRAG_FULL_INGEST_ADMISSION records for the sibling port, not silently "
                "claimed solved here either"
            ),
        ),
        ConditionVerdict(
            condition=9,
            verdict="partially satisfied — spend always reported as unbudgetable, never estimated",
            evidence=(
                "full_delete_body reports tokens.counted_by='unbudgetable' unconditionally — "
                "v1's DeletionResult (v1/lightrag/base.py) carries no usage field at all, unlike "
                "ingest's occasionally-present usage; a partial-rebuild delete may reach the LLM "
                "yet v1 exposes no per-run token count for it back to this caller — the counting "
                "half of this condition is an open machine-side obligation, and the seam never "
                "substitutes a rounded or zero number in its place"
            ),
        ),
        ConditionVerdict(
            condition=10,
            verdict="satisfied (machine-side obligation)",
            evidence=(
                "enforced by databasise.parts.admission.cross_check_conditions: this part's "
                "artifact_scope=None can never be enumerated as an SA-1-shareable artifact by "
                "databasise.registry_artifact.index.ArtifactRegistry.discover, since it declares "
                "no artifact scope at all"
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
    """Reads ``doc_id``/``delete_llm_cache`` from ``ctx.config`` and launches the v1 corpus
    driver's ``delete`` branch via ``run_corpus_op`` (blocking — wrapped in ``asyncio.to_thread``
    per that function's own docstring note), returning the driver's payload with an
    always-unbudgetable token report (see condition 9's verdict above for why this is never a
    fabricated zero). 05-03-PLAN.md Task 2 adds this node's own MACH-11 store-touch reporting
    call to this body once ``NodeContext`` gains ``record_store_touch``.
    """
    config = ctx.config or {}
    payload: dict[str, Any] = {
        "doc_id": config.get("doc_id"),
        "delete_llm_cache": bool(config.get("delete_llm_cache", False)),
    }

    result = await asyncio.to_thread(
        run_corpus_op,
        "delete",
        payload,
        timeout=DELETE_WALL_CLOCK_CEILING_SECONDS,
    )

    return {
        **result,
        # §9/D-08, restated for this port: v1's DeletionResult carries no usage field at all —
        # the node reports the existing unbudgetable sentinel rather than substituting an
        # estimated, rounded, or zero number.
        "tokens": TokenAccounting(counted_by=_UNBUDGETABLE_TOKENS_SENTINEL),
    }


__all__ = [
    "DELETE_WALL_CLOCK_CEILING_SECONDS",
    "LIGHTRAG_FULL_DELETE_ADMISSION",
    "full_delete_body",
]
