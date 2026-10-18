"""Phase 10 review WR-03 (D-08): a delete commits its staged store writes only when it reports
``success`` or ``not_found``. ``not_allowed`` is a refusal and drops them, like ``fail``."""

from __future__ import annotations

import pytest

from databasise.tests.stores.test_delete_commit_contract import _fixture_engine, _present, _seed


async def test_a_delete_reporting_not_allowed_drops_its_staged_deletes(store_root, monkeypatch):
    await _seed(store_root)
    engine = _fixture_engine(store_root, monkeypatch, "not_allowed")

    outcome = await engine.delete_document("doc-1")

    assert outcome.status == "not_allowed"
    assert await _present(store_root) == (True, True, True)


@pytest.mark.parametrize("status", ["success", "not_found"])
async def test_a_delete_reporting_success_or_not_found_commits(store_root, monkeypatch, status):
    await _seed(store_root)
    engine = _fixture_engine(store_root, monkeypatch, status)

    outcome = await engine.delete_document("doc-1")

    assert outcome.status == status
    assert await _present(store_root) == (False, False, False)
