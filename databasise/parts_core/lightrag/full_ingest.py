"""``lightrag/full-ingest`` — the real, executable opaque `Part` body for LightRAG's ~1,786-line
ingest core (05-01-PLAN.md Task 1), replacing the ``body=None`` stub
``databasise/parts_core/declared_only.py`` carried since Phase 1. Dispatched by the real scheduler
at the ``subprocess`` placement (``databasise.validator.execution_mode``): the body itself never
imports ``lightrag`` — it launches ``databasise/foreign/v1_corpus_driver_script.py`` under v1's own
pinned interpreter via ``databasise.foreign.run_corpus_op``, exactly like the query side's Phase 3
subprocess precedent (``databasise/parity/v1_arm.py``/``v1_driver_script.py``).

``LIGHTRAG_FULL_INGEST_ADMISSION`` is the §8 admission record naming eleven ``ConditionVerdict``
entries, one per condition — see each verdict's own ``evidence`` string for the concrete source it
rests on. Conditions 7, 8 and the counting half of 9 are machine-side obligations this record
cannot itself prove; their verdicts say so plainly (condition 7's own machine-side half is enforced
by ``databasise.parts.admission.cross_check_conditions`` at registration; condition 8 — a real
network-namespace-isolation mechanism — is out of this milestone's scope per 05-RESEARCH.md's Open
Question 3; condition 9's counting half is honestly ``"unbudgetable"`` today because
``apipeline_process_enqueue_documents`` exposes no per-run token count back to this caller — see
``full_ingest_body``'s own ``tokens`` construction below).
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

# One document at a time through v1's own extraction pipeline over the 20-document HotpotQA
# fixture (05-RESEARCH.md) — the machine declares this ceiling; v1 never self-reports one (§8
# condition 4).
INGEST_WALL_CLOCK_CEILING_SECONDS = 900.0

# §8's sentinel, this codebase's own convention (databasise.seam.tokens.UNBUDGETABLE_SENTINEL) —
# duplicated as a bare literal here rather than imported: parts_core is a lower layer than seam,
# and importing seam.tokens here would invert that one-way dependency direction for a single
# string constant.
_UNBUDGETABLE_TOKENS_SENTINEL = "unbudgetable"

_V1_ROOT = Path(__file__).resolve().parents[3] / "v1"


def _compute_environment_hash() -> str:
    """§8 condition 2's whole-resolved-runtime-closure rule: a digest over v1's own closure
    inputs — the resolved interpreter path, the text of ``v1/uv.lock``, and the text of
    ``v1/.python-version`` — computed once at import time. A missing file contributes an empty
    string rather than raising (this admission record must still import cleanly on a machine that
    has not yet built the v1 venv; the real ceiling/subprocess-launch refusals are what surface
    the actual absence at run time).
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


LIGHTRAG_FULL_INGEST_ADMISSION = AdmissionRecord(
    part_name_at_version="lightrag/full-ingest@0.1.0",
    entry_path="in-process opaque core, hosted as a subprocess under v1's pinned interpreter",
    storage="machine",
    wall_clock_ceiling_seconds=INGEST_WALL_CLOCK_CEILING_SECONDS,
    wall_clock_ceiling_basis=(
        "one document at a time through v1's own extraction pipeline over the 20-document "
        "HotpotQA fixture (05-RESEARCH.md); the machine declares this ceiling, v1 never "
        "self-reports one"
    ),
    feed_tier="document",
    ttl_days=90,
    network_namespace=(
        "denied-by-construction: the machine's own OpenAI-compatible base_url and key are "
        "injected into the subprocess env via LLM_BINDING_HOST/EMBEDDING_BINDING_HOST; the "
        "subprocess configures no independent outbound endpoint"
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
                "v1/.python-version's own text — the whole resolved runtime closure this "
                "subprocess launches under"
            ),
        ),
        ConditionVerdict(
            condition=3,
            verdict="satisfied by construction",
            evidence=(
                "the subprocess never makes an independent outbound LLM/embedding call — it "
                "calls the machine's own injected LLM_BINDING_HOST/EMBEDDING_BINDING_HOST "
                "(databasise/foreign/v1_corpus_driver_script.py's _build_rag), mirroring "
                "Phase 3's parity harness technique"
            ),
        ),
        ConditionVerdict(
            condition=4,
            verdict="satisfied",
            evidence=(
                "INGEST_WALL_CLOCK_CEILING_SECONDS=900.0 is declared here and enforced by "
                "databasise.foreign.run_corpus_op's timeout= parameter, raising "
                "CorpusOpTimeoutError on breach — databasise.validator.execution_mode.host "
                "refuses to host this placement at all without a positive ceiling"
            ),
        ),
        ConditionVerdict(
            condition=5,
            verdict="satisfied",
            evidence=(
                "LIGHTRAG_FULL_INGEST_PART.artifact_scope='quarantined', never 'shared' — "
                "enforced by validate_admission's ForbiddenSharedScopeError for any opaque part "
                "declaring the shared scope"
            ),
        ),
        ConditionVerdict(
            condition=6,
            verdict="satisfied",
            evidence=(
                "feed_tier='document' — this node receives whole documents via Databasise.ingest, "
                "never machine-produced chunks"
            ),
        ),
        ConditionVerdict(
            condition=7,
            verdict="satisfied (machine-side obligation)",
            evidence=(
                "enforced by databasise.parts.admission.cross_check_conditions at registration "
                "time: the corpus-ingest wiring's own provides node must be excluded from the "
                "default selector's candidate set (databasise.seam.selectors._is_default_eligible)"
            ),
        ),
        ConditionVerdict(
            condition=8,
            verdict="open — accepted as a scope boundary, not a clean yes",
            evidence=(
                "no OS-level network-namespace isolation mechanism exists in databasise/ "
                "(05-RESEARCH.md Open Question 3); denial is achieved by construction (condition "
                "3) rather than by a sandbox, consistent with the project's no-Docker, local-"
                "NixOS constraint — recorded here as the same open finding PARTS.md's own §X row "
                "N12 records for codebase-memory-mcp, not silently claimed solved"
            ),
        ),
        ConditionVerdict(
            condition=9,
            verdict="partially satisfied — spend reported as unbudgetable, never estimated",
            evidence=(
                "full_ingest_body reports tokens.counted_by='unbudgetable' when the subprocess's "
                "own usage field is null (v1's apipeline_process_enqueue_documents exposes no "
                "per-run token count today) — the counting half of this condition is an open "
                "machine-side obligation; the seam refuses to substitute a rounded or zero number "
                "in its place (databasise.seam.tokens.assemble_token_breakdown's existing "
                "UnbudgetableParticipantError mechanism, exercised here for the first time "
                "against a real, non-fixture part)"
            ),
        ),
        ConditionVerdict(
            condition=10,
            verdict="satisfied (machine-side obligation)",
            evidence=(
                "enforced by databasise.parts.admission.cross_check_conditions: this part's "
                "quarantined artifact_scope can never be enumerated as an SA-1-shareable artifact "
                "by databasise.registry_artifact.index.ArtifactRegistry.discover"
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


async def full_ingest_body(ctx: NodeContext) -> dict[str, Any]:
    """Reads ``documents``/``track_id`` (and, for a raw-payload ingest, ``file_paths``/
    ``docs_format``, 05-01-PLAN.md Task 3) from ``ctx.config``, launches the v1 corpus driver via
    ``run_corpus_op`` (blocking — wrapped in ``asyncio.to_thread`` per that function's own
    docstring note) and returns the job handle plus this node's own reported token spend.
    """
    config = ctx.config or {}
    payload: dict[str, Any] = {
        "documents": config.get("documents") or [],
        "track_id": config.get("track_id"),
    }
    if config.get("file_paths") is not None:
        payload["file_paths"] = config["file_paths"]
    if config.get("docs_format") is not None:
        payload["docs_format"] = config["docs_format"]

    result = await asyncio.to_thread(
        run_corpus_op,
        "ingest",
        payload,
        timeout=INGEST_WALL_CLOCK_CEILING_SECONDS,
    )

    usage = result.get("usage")
    if usage:
        tokens = TokenAccounting(
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            call_count=int(usage.get("call_count", 1)),
            counted_by=str(usage.get("model") or "v1-subprocess"),
        )
    else:
        # §9/D-08: v1 reported no usage at all — the node reports the existing unbudgetable
        # sentinel rather than substituting an estimated, rounded, or zero number. A real,
        # honestly-reported zero (counted_by="none") is a different fact this branch never claims.
        tokens = TokenAccounting(counted_by=_UNBUDGETABLE_TOKENS_SENTINEL)

    return {
        "track_id": result.get("track_id"),
        "enqueued": result.get("enqueued", 0),
        "usage": usage,
        "tokens": tokens,
    }


__all__ = [
    "INGEST_WALL_CLOCK_CEILING_SECONDS",
    "LIGHTRAG_FULL_INGEST_ADMISSION",
    "full_ingest_body",
]
