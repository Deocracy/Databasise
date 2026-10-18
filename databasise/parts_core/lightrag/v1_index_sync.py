"""``lightrag/v1-index-sync`` — mirrors v1's committed index into the v2 stores the LightRAG query
arms read (11-01-PLAN.md, CONTEXT D-01, M-04 option b).

It runs as the second node of ``corpus-ingest.json`` and ``corpus-delete.json``, after v1's own
subprocess has ingested or deleted in the per-workspace working dir
(``<store_root>/<workspace>/lightrag-v1``, stamped into ``config["working_dir"]`` by the engine).
The body reads v1's files with :func:`databasise.parity.import_index.read_v1_snapshot` (PROCESSED
documents only) and writes only through ``ctx.stores``, so Phase 10's prepare-all/commit-all and
drop-on-failure cover it and MACH-11 observes its touches. It copies stored vectors and never
re-embeds, so it spends nothing (``counted_by="none"``).

Safety rules: an absent working dir or doc-status file is a no-op that touches no store (stub-body
corpus runs never create one); an unreadable file raises, so the engine drops the run's staged
writes.

Pruning (D-01, stale detection by set difference): the kv record ``V1_INDEX_SYNC_MANIFEST_KEY``
lists, per namespace, the ids the last sync wrote. Each sync upserts the current snapshot, deletes
``previous manifest ids - current ids``, then writes the new manifest, all staged in the same
commit. A row the sync never wrote (a parity ``import_v1_index`` corpus in the same store root) is
never deleted, and with no previous manifest nothing is deleted. Limit: an id that the sync and a
parity import both hold is overwritten by the sync's upsert (and pruned once v1 drops it); merging
the two is TOOL-02's job. The manifest record lives in the ``text_chunks`` kv namespace, so a future
reader that enumerates kv keys must skip it. ``kind="opaque"`` because ``mutates_store`` on a non-opaque part derives the unhosted
``confined-unit`` placement (research Finding 6); the body still runs in the engine process, so it
bounds itself with ``asyncio.wait_for``.
"""

from __future__ import annotations

import asyncio
import hashlib
import sys
from pathlib import Path
from typing import Any

from databasise.identity.canon import canonicalise
from databasise.parity.import_index import mirror_snapshot, read_v1_snapshot
from databasise.parts.admission import (
    MANIFEST_SOURCE_CODE_INSPECTED,
    AdmissionRecord,
    ConditionVerdict,
)
from databasise.runner.trace import TokenAccounting

# A local read of v1's index files plus in-memory staging; no model call.
V1_INDEX_SYNC_WALL_CLOCK_CEILING_SECONDS = 300.0

# One kv record listing, per namespace, the ids the last sync wrote; the next sync prunes against it.
V1_INDEX_SYNC_MANIFEST_KEY = "lightrag-v1-index-sync-manifest"


def _compute_environment_hash() -> str:
    """§8 condition 2: this part runs in the machine's own interpreter, so its closure is that
    interpreter plus the machine's lock file."""
    lock = Path(__file__).resolve().parents[2] / "uv.lock"
    payload = {
        "interpreter": sys.executable,
        "python_version": sys.version,
        "uv_lock": lock.read_text(encoding="utf-8") if lock.exists() else "",
    }
    return "sha256:" + hashlib.sha256(canonicalise(payload)).hexdigest()


async def v1_index_sync_body(ctx: Any) -> dict[str, Any]:
    """Mirror the PROCESSED rows of v1's index at ``config["working_dir"]`` into ``ctx.stores``.

    Never calls ``index_done_callback`` or ``finalize``: the engine owns commit.
    """
    # shortcut: full O(corpus) mirror per write, upgrade by diffing doc_status snapshots
    working_dir = Path((ctx.config or {})["working_dir"])

    async def _sync() -> dict[str, Any]:
        snapshot = await asyncio.to_thread(read_v1_snapshot, working_dir)
        if snapshot is None:
            return {"synced": False, "counts": {}, "tokens": TokenAccounting(counted_by="none")}
        kv, vector, graph = ctx.stores["kv"], ctx.stores["vector"], ctx.stores["graph"]
        previous = await kv.get_by_id(V1_INDEX_SYNC_MANIFEST_KEY)
        counts = await mirror_snapshot(snapshot, kv=kv, vector=vector, graph=graph, manifest=previous)
        await kv.upsert({V1_INDEX_SYNC_MANIFEST_KEY: snapshot.ids()})
        return {"synced": True, "counts": counts, "tokens": TokenAccounting(counted_by="none")}

    return await asyncio.wait_for(_sync(), timeout=V1_INDEX_SYNC_WALL_CLOCK_CEILING_SECONDS)


LIGHTRAG_V1_INDEX_SYNC_ADMISSION = AdmissionRecord(
    part_name_at_version="lightrag/v1-index-sync@0.1.0",
    entry_path="in-process opaque mirror, run in the machine's own interpreter at the subprocess placement",
    storage="machine",
    wall_clock_ceiling_seconds=V1_INDEX_SYNC_WALL_CLOCK_CEILING_SECONDS,
    wall_clock_ceiling_basis=(
        "a local read of v1's index files (doc_status and text_chunks JSON, three Faiss pairs, one "
        "Cozo db) plus in-memory staging; no model call. Enforced by the body's own "
        "asyncio.wait_for, since nothing else can stop an in-process body"
    ),
    feed_tier=(
        "v1-committed-index: reads the index v1 committed to its own working dir, never a "
        "machine-produced chunk or document feed"
    ),
    ttl_days=90,
    network_namespace="denied-by-construction: the body opens no socket and calls no client",
    environment_hash=_compute_environment_hash(),
    manifest_source=MANIFEST_SOURCE_CODE_INSPECTED,
    verdicts=(
        ConditionVerdict(
            condition=1,
            verdict="satisfied",
            evidence=(
                "manifest_source is 'code-inspected' (this record, written from the body in "
                "databasise/parts_core/lightrag/v1_index_sync.py), not a self-report; enforced "
                "structurally by validate_admission"
            ),
        ),
        ConditionVerdict(
            condition=2,
            verdict="satisfied",
            evidence=(
                "environment_hash covers the machine's own interpreter path and version plus "
                "databasise/uv.lock: the body runs in the engine process, so that is its whole "
                "resolved runtime closure"
            ),
        ),
        ConditionVerdict(
            condition=3,
            verdict="satisfied by construction",
            evidence=(
                "network denied by construction: the body opens no socket and declares no "
                "calls_llm/calls_embedding effect, so no client is reachable through ctx.clients; "
                "it copies stored vectors and never re-embeds, so its spend is a real zero "
                "(counted_by='none')"
            ),
        ),
        ConditionVerdict(
            condition=4,
            verdict="satisfied",
            evidence=(
                "V1_INDEX_SYNC_WALL_CLOCK_CEILING_SECONDS=300.0 is declared here and enforced by "
                "the body's asyncio.wait_for around the read and the mirror; "
                "databasise.validator.execution_mode.host refuses this placement without a "
                "positive ceiling"
            ),
        ),
        ConditionVerdict(
            condition=5,
            verdict="satisfied",
            evidence=(
                "storage='machine': the body writes only through ctx.stores (the engine's staged "
                "kv, vector and graph handles, committed by prepare-all/commit-all and dropped on "
                "failure) and declares no artifact scope (artifact_scope=None), so it never "
                "writes 'shared'"
            ),
        ),
        ConditionVerdict(
            condition=6,
            verdict="satisfied",
            evidence=(
                "feed_tier names v1's committed index: the node reads files v1 wrote and receives "
                "no machine-produced chunk feed, so the embedder-coupled chunk-tier refusal has "
                "nothing to apply to"
            ),
        ),
        ConditionVerdict(
            condition=7,
            verdict="satisfied (machine-side obligation)",
            evidence=(
                "this node is never a provides node: it is the second node of corpus-ingest.json "
                "and corpus-delete.json, whose provides stay full-ingest/full-delete, and corpus "
                "wirings are dispatched by operation, never offered to the default selector "
                "(databasise.seam.selectors._is_default_eligible)"
            ),
        ),
        ConditionVerdict(
            condition=8,
            verdict="machine-side-obligation",
            evidence=(
                "ttl_days=90 is declared on this record; renewal with a recorded reason is the "
                "same machine-side ledger mechanism the sibling LightRAG corpus ports rely on, "
                "not re-invented here"
            ),
        ),
        ConditionVerdict(
            condition=9,
            verdict="machine-side-obligation",
            evidence=(
                "the node is invoked only as a named wiring node, never through an implicit "
                "path; counting explicit part_ref invocations as data and never as a promotion "
                "trigger is a machine-side ledger mechanic with no source evidence here"
            ),
        ),
        ConditionVerdict(
            condition=10,
            verdict="satisfied",
            evidence=(
                "artifact_scope=None declares no artifact scope at all, and the machine keeps no "
                "artifact registry (removed in Phase 10, D-15), so nothing enumerates this part's "
                "inputs as an SA-1-shareable artifact"
            ),
        ),
        ConditionVerdict(
            condition=11,
            verdict="satisfied by construction",
            evidence=(
                "databasise.seam.query.QueryObject declares no 'as_of' member and the Effect "
                "vocabulary has no temporal-capability member; checked at registration by "
                "cross_check_conditions"
            ),
        ),
    ),
)


__all__ = [
    "LIGHTRAG_V1_INDEX_SYNC_ADMISSION",
    "V1_INDEX_SYNC_MANIFEST_KEY",
    "V1_INDEX_SYNC_WALL_CLOCK_CEILING_SECONDS",
    "v1_index_sync_body",
]
