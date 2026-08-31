"""databasise — the agnostic machine.

Public entry point: ``run_wiring(wiring_doc, *, store_root, registry=None, determinism_setting,
concurrency_setting)``. This is the seam every later plan and every consumer calls: it composes
``validator.parse_wiring`` -> ``runner.scheduler.run_wiring`` (which itself composes
``validator.depth`` and ``identity`` internally) -> ``runner.trace.RunRecord``, then stamps the
run-level fields this module owns (``run_id``, ``wiring_id``, ``wiring_instance_hash``,
``arm_id``, ``arm_execution_order``) before returning the schema-valid run-record dict.

**Honesty fields, composer-threaded (01-10-PLAN.md Task 1).** ``partial``, ``degraded``,
``stop_reason`` and ``degradation_reason`` are threaded straight from ``scheduler.run_wiring``'s
own result dict into the ``RunRecord(...)`` call below — this is required, not cosmetic:
``RunRecord.__post_init__``'s honesty invariant (``runner/trace.py``) raises ``ValueError`` the
moment any node reports a halted budget state while the run itself is not marked partial, and a
scheduler-level node failure or budget halt must reach the consumer as a traced partial run
rather than a clean-looking record (CONTRACT §9's "MUST NOT be discarded").
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any

from databasise.identity.canon import canonicalise
from databasise.parts.registry import PartRegistry
from databasise.runner import scheduler as _scheduler
from databasise.runner.trace import RunRecord
from databasise.stores.kv import SqliteKVStore
from databasise.validator.parse import parse_wiring

__version__ = "0.1.0"

# This tracer proves the store lifecycle end-to-end with one hardcoded namespace/workspace pair;
# D-07's real per-namespace directory derivation (keyed off SA-1 recipe identity) is a later
# plan's deliverable. Exposed as constants so tests can verify against the same store this
# module actually writes to, rather than duplicating the literal strings.
TRACER_WORKSPACE = "tracer"
TRACER_KV_NAMESPACE = "kv"


async def run_wiring(
    wiring_doc: dict[str, Any],
    *,
    store_root: str | Path,
    registry: PartRegistry | None = None,
    determinism_setting: str,
    concurrency_setting: str,
) -> dict[str, Any]:
    """Parse, validate, resolve identity, execute and trace one wiring run."""
    if registry is None:
        registry = PartRegistry()

    parsed = parse_wiring(wiring_doc, registry)

    stores: dict[str, Any] = {
        "kv": SqliteKVStore(
            namespace=TRACER_KV_NAMESPACE, workspace=TRACER_WORKSPACE, store_root=Path(store_root)
        ),
    }

    scheduled = await _scheduler.run_wiring(
        parsed,
        registry,
        stores,
        determinism_setting=determinism_setting,
        concurrency_setting=concurrency_setting,
    )

    if "cycle" in scheduled:
        # Cyclic wirings are legal content (CONTRACT §1) — reported as data, never raised.
        # Falsifier 2's cycle-safe (Tarjan SCC) depth pass is plan 01-03's deliverable; this
        # tracer's acyclic path returns the cycle rather than attempting to run it.
        for store in stores.values():
            await store.finalize()
        return {"cycle": scheduled["cycle"]}

    for store in stores.values():
        await store.index_done_callback()
        await store.finalize()

    wiring_bytes = canonicalise(wiring_doc)
    wiring_instance_hash = f"sha256:{hashlib.sha256(wiring_bytes).hexdigest()}"
    wiring_id = wiring_doc.get("wiring_id") or (
        f"wiring:{hashlib.sha256(wiring_bytes).hexdigest()[:16]}"
    )

    record = RunRecord(
        run_id=str(uuid.uuid4()),
        wiring_id=wiring_id,
        wiring_instance_hash=wiring_instance_hash,
        arm_id="base",
        arm_execution_order=0,
        executor_version=f"databasise@{__version__}",
        concurrency_setting=concurrency_setting,
        determinism_setting=determinism_setting,
        nodes=scheduled["nodes"],
        partial=scheduled["partial"],
        degraded=scheduled["degraded"],
        stop_reason=scheduled["stop_reason"],
        degradation_reason=scheduled["degradation_reason"],
    )
    return record.to_dict()
