"""07-05-PLAN.md: closes G-07-1 (07-UAT.md, carried through two review rounds as 07-REVIEW.md
WR-01) — all three operator verbs (``promote``/``rollback``/``retire``) did check-then-act across
separate autocommit statements, so a concurrent writer could commit between any guard's read and
its own append. Both races reproduced here were measured pre-fix on unmodified library code:

- ``retire(v)`` racing ``rollback(v)``, two concurrent calls: 134/200 trials (07-UAT.md; re-measured
  here at plan-authoring time: 17/25) committed a rollback row naming the same generation as an
  already-committed tombstone, both calls returning ok, no refusal for the loser.
- Six concurrent ``promote()`` calls: 13/300 trials (07-UAT.md; re-measured here: 6/60) minted a
  duplicate semver.

Fixed by ``Ledger.transaction()`` (a ``BEGIN IMMEDIATE`` span enclosing each verb's guard read
through its ``append()``) plus a ``UNIQUE(alias, minted_version)`` index as a database-level
backstop (Task 2). Each trial gets its own store root — the ``store_root`` fixture gives one root
for the whole test, and trials must not share a ledger.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from databasise.ledger.ledger import Ledger
from databasise.seam.engine import Databasise
from databasise.seam.envelope import PromotionResult
from databasise.seam.refusals import SeamRefusalError, TombstonedGenerationError
from databasise.seam.trace_store import TraceStore
from databasise.wirings.resolve import all_wirings

_ALIAS = "prod-lightrag"

# Measured pre-fix detection rate: ~68% per trial (134/200, 07-UAT.md). 20 trials costs ~2.6s and
# makes a regression essentially certain to be caught.
_RETIRE_ROLLBACK_TRIALS = 20

# Measured pre-fix rate: ~10% per trial (13/300, 07-UAT.md) — this race needs high concurrency;
# two concurrent promotes never reproduced it. 20 trials costs ~5.4s.
_SIX_WAY_PROMOTE_TRIALS = 20

_SIX_ARMS = ("naive", "local", "global", "hybrid", "bypass", "hipporag")


def _seed_trace(store_root, arm_name: str) -> str:
    resolved = next(resolved for name, resolved in all_wirings() if name == arm_name)
    node_ids = sorted(resolved.get("nodes", {}).keys())
    fake_record = {
        "run_id": f"fake-run-{arm_name}",
        "wiring_id": resolved.get("wiring_id"),
        "wiring_instance_hash": f"sha256:{'0' * 63}{len(node_ids) % 10}",
        "arm_id": "seam",
        "nodes": [{"node_id": node_id} for node_id in node_ids],
    }
    return TraceStore(store_root).persist(fake_record)


def _engine(store_root) -> Databasise:
    return Databasise(store_root=store_root, workspace="concurrency-test")


def _rows_targeting(store_root, version: str) -> list[tuple[int, str]]:
    """Raw ``(id, record_kind)`` pairs for every ledger row naming ``version`` as either the
    version it minted or the version it acted on, oldest first — ``LedgerRecord`` itself does not
    expose ``id``, and the row-order invariant this test checks needs it directly.
    """
    ledger = Ledger(store_root)
    cur = ledger._conn.execute(
        "SELECT id, record_kind FROM ledger WHERE alias = ? "
        "AND (minted_version = ? OR targets_version = ?) ORDER BY id ASC",
        (_ALIAS, version, version),
    )
    return [(row["id"], row["record_kind"]) for row in cur.fetchall()]


async def test_retire_vs_rollback_race_never_lets_a_rollback_outrun_a_tombstone():
    for _trial in range(_RETIRE_ROLLBACK_TRIALS):
        with tempfile.TemporaryDirectory() as tmp:
            store_root = Path(tmp)
            engine = _engine(store_root)
            trace_naive = _seed_trace(store_root, "naive")
            trace_bypass = _seed_trace(store_root, "bypass")
            trace_retire = _seed_trace(store_root, "naive")
            trace_rollback = _seed_trace(store_root, "naive")

            first = await engine.promote(_ALIAS, [trace_naive], "human_edit")
            await engine.promote(_ALIAS, [trace_bypass], "human_edit")  # now active; naive is not

            results = await asyncio.gather(
                engine.retire(_ALIAS, first.version, [trace_retire], "human_edit"),
                engine.rollback(_ALIAS, first.version, [trace_rollback], "human_edit"),
                return_exceptions=True,
            )

            # Every outcome is either a PromotionResult or a SeamRefusalError subclass — never a
            # raw sqlite3.OperationalError/IntegrityError reaching the caller.
            for outcome in results:
                assert isinstance(outcome, (PromotionResult, SeamRefusalError)), outcome

            # If one call refused, it refused as the already-shipped TombstonedGenerationError —
            # never a bare sqlite3 exception and never a new refusal class.
            refusals = [r for r in results if isinstance(r, BaseException)]
            for refusal in refusals:
                assert isinstance(refusal, TombstonedGenerationError), refusal

            # Row-order invariant: no ROLLBACK row targeting this generation may carry a ledger id
            # greater than a TOMBSTONE row also targeting it. A rollback landing after an
            # already-committed tombstone must have refused instead (asserted above); this checks
            # the same fact directly against the append order rather than only the call outcome.
            rows = _rows_targeting(store_root, first.version)
            tombstone_ids = [row_id for row_id, kind in rows if kind == "tombstone"]
            rollback_ids = [row_id for row_id, kind in rows if kind == "rollback"]
            if tombstone_ids and rollback_ids:
                # Every rollback id must be less than every tombstone id — i.e. the rollback (if
                # any) always precedes the tombstone in append order; it never lands after one.
                assert max(rollback_ids) < min(tombstone_ids), (
                    "a rollback row committed after a tombstone naming the same generation "
                    f"(rows={rows})"
                )
