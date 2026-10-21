"""15-16-PLAN.md Task 1 (TOOL-12, D-13): ``FloorStore`` keeps ``<store_root>/floors.db`` the way
``JobFamilyStore`` keeps ``jobs.db``: created by the first write only, read-only lookups create nothing.
"""

from __future__ import annotations

import importlib

_HASH = f"sha256:{'a' * 64}"


def _module():
    try:
        module = importlib.import_module("databasise.seam.floors_store")
    except ImportError:
        module = None
    assert module is not None, "databasise.seam.floors_store does not exist"
    return module


def _row(floor: float = 0.1, **overrides):
    fields = {
        "wiring_instance_hash": _HASH,
        "bundle_at_v": "bundle@v1",
        "tier": "T1",
        "metric": "gold_passage_recall",
        "determinism_setting": "cache-bypassed",
        "concurrency_setting": "sequential",
        "floor": floor,
        "n_questions": 10,
        "n_resamples": 200,
        "seed": 1,
        "created_at": "2026-10-21T00:00:00+00:00",
    }
    fields.update(overrides)
    return _module().FloorRow(**fields)


def test_record_creates_floors_db_and_lookup_returns_the_row(tmp_path):
    store = _module().FloorStore(tmp_path)
    assert not (tmp_path / "floors.db").exists()

    store.record(_row())

    assert (tmp_path / "floors.db").is_file()
    assert store.any_floor() is True
    assert store.lookup(_HASH) == [_row()]
    assert store.lookup(f"sha256:{'b' * 64}") == []


def test_reads_on_an_absent_file_return_empty_and_create_nothing(tmp_path):
    store = _module().FloorStore(tmp_path / "no-such-root")

    assert store.any_floor() is False
    assert store.lookup(_HASH) == []
    assert not (tmp_path / "no-such-root").exists()


def test_a_second_record_with_the_same_key_replaces_the_row(tmp_path):
    store = _module().FloorStore(tmp_path)

    store.record(_row(floor=0.1))
    store.record(_row(floor=0.2))

    assert [row.floor for row in store.lookup(_HASH)] == [0.2]


def test_the_module_defines_no_promotion_verb_and_imports_no_ledger():
    module = _module()
    source = open(module.__file__, encoding="utf-8").read()

    assert not any(f"def {name}(" in source for name in ("promote", "promote_next", "promote_now", "rollback"))
    assert "databasise.ledger" not in source
