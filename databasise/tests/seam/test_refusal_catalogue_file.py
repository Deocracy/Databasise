"""16-02 (CONN-02, D-07): ``docs/gui/refusals.json`` is the machine-readable refusal catalogue the
console renders. This test rebuilds every entry from the code (the factories, ``refusal_body`` and
``rest._status_for``) and fails when the file is absent or differs. The file is written only by
this test: ``DATABASISE_REGENERATE=1 databasise/.venv/bin/python -m pytest -q
databasise/tests/seam/test_refusal_catalogue_file.py -p no:cacheprovider``."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from databasise.seam import refusals as refusals_module
from databasise.seam import rest as rest_module
from databasise.seam.refusals import refusal_body
from databasise.tests.seam.test_rest_transport import (
    _REFUSAL_FACTORIES,
    _all_seam_refusal_subclasses,
)

_CATALOGUE = Path(__file__).resolve().parents[3] / "docs" / "gui" / "refusals.json"
_REGENERATE_HINT = (
    "regenerate with: DATABASISE_REGENERATE=1 databasise/.venv/bin/python -m pytest -q "
    "databasise/tests/seam/test_refusal_catalogue_file.py -p no:cacheprovider"
)
_ALLOWED_STATUSES = {404, 409, 422, 502, 503}


def _runtime_subclasses():
    return [
        cls
        for cls in _all_seam_refusal_subclasses()
        if not cls.__module__.startswith("databasise.tests")
    ]


def _expected_entries() -> list[dict]:
    entries = []
    for cls in _runtime_subclasses():
        instance = _REFUSAL_FACTORIES[cls]()
        entries.append(
            {
                "refusal_type": cls.__name__,
                "module": cls.__module__,
                "attribute_keys": sorted(set(refusal_body(instance)) - {"refusal_type", "message"}),
                "http_status": rest_module._status_for(instance),
            }
        )
    return sorted(entries, key=lambda entry: entry["refusal_type"])


def test_the_refusal_catalogue_file_matches_the_code():
    expected = _expected_entries()
    if os.environ.get("DATABASISE_REGENERATE") == "1":
        _CATALOGUE.parent.mkdir(parents=True, exist_ok=True)
        _CATALOGUE.write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")

    assert _CATALOGUE.is_file(), f"{_CATALOGUE} is missing; {_REGENERATE_HINT}"
    actual = json.loads(_CATALOGUE.read_text(encoding="utf-8"))

    actual_by_name = {entry["refusal_type"]: entry for entry in actual}
    expected_by_name = {entry["refusal_type"]: entry for entry in expected}
    missing = sorted(set(expected_by_name) - set(actual_by_name))
    extra = sorted(set(actual_by_name) - set(expected_by_name))
    differing = sorted(
        name
        for name in set(actual_by_name) & set(expected_by_name)
        if actual_by_name[name] != expected_by_name[name]
    )
    assert actual == expected, (
        f"docs/gui/refusals.json differs from the code: missing={missing} extra={extra} "
        f"differing={differing}; {_REGENERATE_HINT}"
    )

    exported = set(refusals_module.__all__)
    assert {entry["refusal_type"] for entry in actual} <= exported
    assert all(entry["http_status"] in _ALLOWED_STATUSES for entry in actual)
    assert len(actual) == len(_runtime_subclasses())
