"""09-01-PLAN.md Task 2 (SEAM-14): ``databasise.seam.refusals.__all__`` is the one refusal
catalogue -- every ``SeamRefusalError`` subclass either transport can return is defined there and
named there. Names are compared as sets, so declaration order carries no meaning.
"""

from __future__ import annotations

import importlib

import pytest

from databasise.seam import refusals


def _load_every_seam_module() -> None:
    importlib.import_module("databasise.seam")
    importlib.import_module("databasise.seam.rest")
    importlib.import_module("databasise.mcp")


def _all_subclasses() -> set[type]:
    found: set[type] = set()
    frontier = list(refusals.SeamRefusalError.__subclasses__())
    while frontier:
        cls = frontier.pop()
        if cls in found:
            continue
        found.add(cls)
        frontier.extend(cls.__subclasses__())
    return found


def test_every_refusal_subclass_is_named_in_the_catalogue():
    pytest.importorskip("fastapi")
    _load_every_seam_module()
    defined = {
        cls.__name__
        for cls in _all_subclasses()
        if not cls.__module__.startswith("databasise.tests")
    }
    assert defined - set(refusals.__all__) == set()


def test_the_catalogue_names_only_refusals_defined_in_refusals_py_exactly_once():
    assert len(refusals.__all__) == len(set(refusals.__all__))
    for name in refusals.__all__:
        cls = getattr(refusals, name)
        assert issubclass(cls, refusals.SeamRefusalError), name
        assert cls.__module__ == "databasise.seam.refusals", name


@pytest.mark.parametrize(
    ("module", "name"),
    [
        ("databasise.seam.trace_store", "UnknownTraceReferenceError"),
        ("databasise.seam.evidence", "UnresolvableEvidenceReferenceError"),
        ("databasise.seam.tokens", "UnbudgetableParticipantError"),
    ],
)
def test_the_moved_refusals_keep_their_old_import_path(module, name):
    assert getattr(importlib.import_module(module), name) is getattr(refusals, name)
