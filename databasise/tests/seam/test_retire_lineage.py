"""14-09-PLAN.md Task 1 (LEDG-04, D-06): the retire and rollback guards go by version through the
rollback lineage. Retiring any version in the active row's lineage is refused and appends nothing; a
rollback onto a lineage holding a tombstoned version is refused, so an alias never serves a
tombstoned generation. The guard is by version, never by wiring identity (RIG §PR.2).

The file imports only names that exist at the phase base and copies its own helpers, so it collects
and fails by assertion there.
"""

from __future__ import annotations

import pytest

from databasise.ledger.ledger import Ledger
from databasise.seam.engine import Databasise
from databasise.seam.trace_store import TraceStore
from databasise.wirings.resolve import all_wirings

pytest.importorskip("fastapi")
from databasise.seam.rest import create_app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

_ALIAS = "lineage-alias"


async def _capture(awaitable):
    try:
        return await awaitable
    except Exception as caught:  # noqa: BLE001 - the assertion is on the captured type
        return caught


def _seed_trace(store_root, arm_name: str = "naive") -> str:
    resolved = next(resolved for name, resolved in all_wirings() if name == arm_name)
    node_ids = sorted(resolved.get("nodes", {}).keys())
    return TraceStore(store_root).persist(
        {
            "run_id": f"fake-run-{arm_name}",
            "wiring_id": resolved.get("wiring_id"),
            "wiring_instance_hash": f"sha256:{'0' * 63}{len(node_ids) % 10}",
            "arm_id": "seam",
            "nodes": [{"node_id": node_id} for node_id in node_ids],
        }
    )


def _rows(store_root) -> int:
    ledger = Ledger(store_root)
    try:
        return ledger._conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
    finally:
        ledger._conn.close()  # Ledger.close() does not exist at the phase base


def _active(store_root):
    ledger = Ledger(store_root)
    try:
        return ledger.by_alias(_ALIAS)
    finally:
        ledger._conn.close()


class _Chain:
    """Drives the verbs on one store root; each verb gets a fresh seeded trace."""

    def __init__(self, store_root) -> None:
        self.store_root = store_root
        self.engine = Databasise(store_root=store_root, workspace="retire-lineage")

    def _trace(self) -> str:
        return _seed_trace(self.store_root)

    async def promote(self, arm: str) -> str:
        result = await self.engine.promote(_ALIAS, [_seed_trace(self.store_root, arm)], "human_edit")
        return result.version

    async def rollback(self, version: str) -> str:
        result = await self.engine.rollback(_ALIAS, version, [self._trace()], "human_edit")
        return result.version

    async def retire(self, version: str):
        return await _capture(self.engine.retire(_ALIAS, version, [self._trace()], "human_edit"))

    async def rollback_captured(self, version: str):
        return await _capture(self.engine.rollback(_ALIAS, version, [self._trace()], "human_edit"))


async def test_retiring_the_target_of_an_active_rollback_is_refused(tmp_path):
    chain = _Chain(tmp_path)
    first = await chain.promote("naive")
    second = await chain.promote("hybrid")
    rollback = await chain.rollback(first)
    rows = _rows(tmp_path)

    caught = await chain.retire(first)
    assert type(caught).__name__ == "ActiveGenerationRetirementError", (
        f"retire of the rollback's target gave {type(caught).__name__}: {caught}"
    )
    assert _rows(tmp_path) == rows, "the refused retire appended a row"
    active = _active(tmp_path)
    assert active.record_kind == "rollback" and active.minted_version == rollback
    assert active.targets_version == first

    retired = await chain.retire(second)
    assert type(retired).__name__ == "PromotionResult", f"retire of the second version gave {retired!r}"
    assert _rows(tmp_path) == rows + 1


async def test_every_version_in_the_active_lineage_is_protected(tmp_path):
    chain = _Chain(tmp_path)
    naive = await chain.promote("naive")
    hybrid = await chain.promote("hybrid")
    first_rollback = await chain.rollback(naive)
    local = await chain.promote("local")
    second_rollback = await chain.rollback(first_rollback)
    rows = _rows(tmp_path)

    for protected in (naive, first_rollback, second_rollback):
        caught = await chain.retire(protected)
        assert type(caught).__name__ == "ActiveGenerationRetirementError", (
            f"retire of lineage version {protected} gave {type(caught).__name__}: {caught}"
        )
    assert _rows(tmp_path) == rows, "a refused retire appended a row"

    for free in (hybrid, local):
        result = await chain.retire(free)
        assert type(result).__name__ == "PromotionResult", f"retire of {free} gave {result!r}"
    assert _rows(tmp_path) == rows + 2


async def test_a_rollback_onto_a_tombstoned_lineage_is_refused(tmp_path):
    chain = _Chain(tmp_path)
    naive = await chain.promote("naive")
    await chain.promote("hybrid")
    rollback = await chain.rollback(naive)
    local = await chain.promote("local")

    # naive is not in the active (local) lineage, so retiring it is allowed.
    retired = await chain.retire(naive)
    assert type(retired).__name__ == "PromotionResult", f"retire of {naive} gave {retired!r}"
    rows = _rows(tmp_path)

    caught = await chain.rollback_captured(rollback)
    assert type(caught).__name__ == "TombstonedGenerationError", (
        f"rollback onto a tombstoned lineage gave {type(caught).__name__}: {caught}"
    )
    assert getattr(caught, "version", None) == rollback
    assert _rows(tmp_path) == rows, "the refused rollback appended a row"
    assert _active(tmp_path).minted_version == local


async def test_a_repromoted_arm_keeps_its_older_generation_retirable(tmp_path):
    chain = _Chain(tmp_path)
    first = await chain.promote("naive")
    await chain.promote("hybrid")
    await chain.promote("naive")

    result = await chain.retire(first)
    assert type(result).__name__ == "PromotionResult", (
        f"retire of the older naive generation gave {type(result).__name__}: {result}"
    )


async def test_rest_retire_of_an_active_rollback_target_is_a_422(tmp_path):
    chain = _Chain(tmp_path)
    first = await chain.promote("naive")
    await chain.promote("hybrid")
    await chain.rollback(first)
    rows = _rows(tmp_path)

    client = TestClient(
        create_app(store_root=tmp_path, workspace="retire-lineage"), raise_server_exceptions=False
    )
    response = client.post(
        "/retire",
        json={
            "alias": _ALIAS,
            "version": first,
            "trace_ids": [_seed_trace(tmp_path)],
            "change_origin": "human_edit",
        },
    )
    assert response.status_code == 422, f"{response.status_code} {response.text}"
    assert response.json()["refusal_type"] == "ActiveGenerationRetirementError", response.text
    assert _rows(tmp_path) == rows
