"""``lightrag/full-ingest@0.2.0`` — the real, executable opaque `Part` body for LightRAG's ~1,786-line
ingest core. Dispatched by the real scheduler at the ``subprocess`` placement
(``databasise.validator.execution_mode``): the body itself never imports ``lightrag`` — it launches
``databasise/foreign/v1_corpus_driver_script.py`` under v1's own pinned interpreter via
``databasise.foreign.run_corpus_op``, exactly like the query side's Phase 3 subprocess precedent
(``databasise/parity/v1_arm.py``/``v1_driver_script.py``).

11-03-PLAN.md (D-06) is this port's one ``@0.2.0`` bump: the effects become ``calls_llm``,
``mutates_store``, ``reads_kv``, ``reads_graph`` (v1 mutates its own per-workspace working dir;
nothing is written as an artifact), the storage is ``self-contained``, and the driver protocol
gains file ingest, a targets filter, duplicate-aware ``enqueued`` and real token usage.

``LIGHTRAG_FULL_INGEST_ADMISSION`` names eleven ``ConditionVerdict`` entries, one per CONTRACT §8
condition, numbered as CONTRACT numbers them (LRAG-12):

- 3: the network namespace is denied by construction (the machine injects the only model
  endpoints), and spend is metered from v1's own ``TokenTracker`` usage when the provider reports
  it and ``unbudgetable`` when it does not — never estimated;
- 5: ``storage='self-contained'`` and no artifact scope;
- 8: ``ttl_days=90``, each renewal recorded in the ledger — a machine-side obligation;
- 9: explicit ``part_ref`` invocations are counted as data, not a promotion trigger — a
  machine-side obligation.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import contextvars
import hashlib
import logging
from pathlib import Path
from typing import Any

from databasise.foreign import run_corpus_op
from databasise.foreign.v1_corpus_adapter import DEFAULT_V1_INTERPRETER, redact_secrets
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

# A stable label for v1's TokenTracker counts: the tracker carries no tokenizer identity.
_V1_COUNTED_BY = "v1-subprocess"

_V1_ROOT = Path(__file__).resolve().parents[3] / "v1"

logger = logging.getLogger(__name__)


def tokens_from_usage(usage: Any) -> TokenAccounting:
    """The node's accounting from the driver's ``usage["llm"]`` (D-13). No model call is a real
    zero (``none``). Calls with zero tokens mean the provider sent no usage, so the spend is
    ``unbudgetable`` with that call count. A missing usage (a stub driver) is ``unbudgetable`` too.
    Embedding usage stays in the returned ``usage`` dict: a different tokenizer, never summed in.
    """
    llm = usage.get("llm") if isinstance(usage, dict) else None
    if not isinstance(llm, dict):
        return TokenAccounting(counted_by=_UNBUDGETABLE_TOKENS_SENTINEL)
    call_count = int(llm.get("call_count", 0))
    if call_count == 0:
        return TokenAccounting(counted_by="none")
    if int(llm.get("total_tokens", 0)) == 0:
        return TokenAccounting(call_count=call_count, counted_by=_UNBUDGETABLE_TOKENS_SENTINEL)
    return TokenAccounting(
        prompt_tokens=int(llm.get("prompt_tokens", 0)),
        completion_tokens=int(llm.get("completion_tokens", 0)),
        call_count=call_count,
        counted_by=_V1_COUNTED_BY,
    )


# 11 REVIEW A-CR-01 / A2-WR-01: the engine binds a list here while it holds a v1 write gate. A
# worker whose wait was given up (a cancel, or the sync's wall-clock timeout) is parked in it, and
# the engine releases the gate only once every parked worker has returned.
ABANDONED_WORKERS: contextvars.ContextVar[list[concurrent.futures.Future] | None] = contextvars.ContextVar(
    "abandoned_v1_workers", default=None
)
_WORKERS = concurrent.futures.ThreadPoolExecutor(thread_name_prefix="v1-corpus-worker")


def _log_discarded(worker: concurrent.futures.Future) -> None:
    """A2-WR-02: a given-up worker's outcome reaches no caller, so it is logged once, server-side:
    the failure class and the stderr tail (D-11), redacted (A-WR-05)."""
    if worker.cancelled():
        return
    exc = worker.exception()
    if exc is None:
        logger.warning("a cancelled or timed-out v1 write discarded the worker's result; v1 may have committed")
    else:
        logger.warning(
            "a cancelled or timed-out v1 write discarded the worker's failure: failure_class=%s %s",
            type(exc).__name__,
            redact_secrets(str(exc)),
        )


async def to_thread_until_done(func: Any, /, *args: Any, **kwargs: Any) -> Any:
    """``asyncio.to_thread`` whose worker outlives a given-up wait (11 REVIEW A-CR-01, A2-WR-01). A
    thread cannot be stopped, so on cancel (or a ``wait_for`` timeout) this stops waiting at once,
    parks the worker in :data:`ABANDONED_WORKERS` and re-raises. The engine's write gate stays held
    until the v1 subprocess (or the sync's read of v1's files) has returned."""
    worker = _WORKERS.submit(contextvars.copy_context().run, func, *args, **kwargs)
    try:
        return await asyncio.wrap_future(worker)
    except asyncio.CancelledError:
        parked = ABANDONED_WORKERS.get()
        if parked is not None:
            parked.append(worker)
        worker.add_done_callback(_log_discarded)
        raise


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
    part_name_at_version="lightrag/full-ingest@0.2.0",
    entry_path="in-process opaque core, hosted as a subprocess under v1's pinned interpreter",
    storage="self-contained",
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
                "network denial by construction: the subprocess calls only the machine's injected "
                "LLM_BINDING_HOST/EMBEDDING_BINDING_HOST (v1_corpus_driver_script.py's _build_rag) "
                "and configures no endpoint of its own; no OS-level namespace sandbox exists under "
                "the no-Docker constraint. Spend: the driver hands lightrag.utils.TokenTracker to "
                "both model functions (token_tracker=) and returns its usage; full_ingest_body "
                "reports the LLM half with counted_by='v1-subprocess', 'none' for no model call, "
                "and 'unbudgetable' when the provider reports no usage — never an estimate"
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
                "storage='self-contained': v1 writes only its per-workspace working dir "
                "<store_root>/<workspace>/lightrag-v1; the v2 rows are written by the "
                "lightrag/v1-index-sync node through ctx.stores. LIGHTRAG_FULL_INGEST_PART."
                "artifact_scope=None, so no artifact scope exists to be 'shared'"
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
            verdict="machine-side-obligation",
            evidence=(
                "ttl_days=90 is declared on this record; renewal only with a recorded reason, each "
                "renewal recorded in the ledger, is a machine-side ledger mechanic with no source "
                "evidence in this part"
            ),
        ),
        ConditionVerdict(
            condition=9,
            verdict="machine-side-obligation",
            evidence=(
                "this port is reached only by an explicit Databasise.ingest() call through the "
                "corpus-ingest wiring; counting explicit part_ref invocations as data and never as "
                "a promotion trigger is a machine-side ledger mechanic, not rounded up to a yes"
            ),
        ),
        ConditionVerdict(
            condition=10,
            verdict="satisfied (machine-side obligation)",
            evidence=(
                "enforced by databasise.parts.admission.cross_check_conditions: this part declares "
                "no artifact scope, and the machine keeps no artifact registry (removed in Phase "
                "10, D-15), so nothing enumerates this part's inputs as SA-1-shareable artifacts"
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
    """Reads ``documents``/``track_id`` (and, for a staged upload, ``file_paths``/``docs_format``/
    ``input_dir``; for a retry, ``retry_doc_ids``) from ``ctx.config``, launches the v1 corpus
    driver via ``run_corpus_op`` (blocking — run by :func:`to_thread_until_done`, so a cancel
    keeps the write gate until the subprocess returns) and returns the job handle plus this node's own metered token spend
    (:func:`tokens_from_usage`).
    """
    config = ctx.config or {}
    payload: dict[str, Any] = {
        "documents": config.get("documents") or [],
        "track_id": config.get("track_id"),
    }
    for key in ("file_paths", "docs_format", "input_dir", "retry_doc_ids"):
        if config.get(key) is not None:
            payload[key] = config[key]

    result = await to_thread_until_done(
        run_corpus_op,
        "ingest",
        payload,
        timeout=INGEST_WALL_CLOCK_CEILING_SECONDS,
        working_dir=config.get("working_dir"),  # 11-01 (LRAG-01): stamped by the engine
    )

    usage = result.get("usage")
    return {
        "track_id": result.get("track_id"),
        "enqueued": result.get("enqueued", 0),
        "usage": usage,
        "tokens": tokens_from_usage(usage),
    }


__all__ = [
    "ABANDONED_WORKERS",
    "INGEST_WALL_CLOCK_CEILING_SECONDS",
    "LIGHTRAG_FULL_INGEST_ADMISSION",
    "full_ingest_body",
    "to_thread_until_done",
    "tokens_from_usage",
]
