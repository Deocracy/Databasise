"""Phase 14 (14-03, D-05): ``wiring_for_name`` is the one name-to-wiring lookup. It equals
``all_wirings()`` filtered by name, returns None for every other string and never raises. The helper
is resolved with ``getattr`` so the file collects (and fails by assertion) on code that predates it."""

from __future__ import annotations

from databasise.wirings import resolve


def _lookup():
    fn = getattr(resolve, "wiring_for_name", None)
    assert fn is not None, "databasise.wirings.resolve.wiring_for_name is not defined"
    return fn


def test_every_candidate_resolves_to_its_all_wirings_dict():
    lookup = _lookup()
    pairs = resolve.all_wirings()
    assert pairs
    for name, resolved in pairs:
        assert lookup(name) == resolved, f"wiring_for_name({name!r}) differs from all_wirings()"


def test_names_outside_the_candidate_pool_return_none():
    lookup = _lookup()
    for name in ("lightrag", "codebase-memory-mcp", "nonexistent", ""):
        assert lookup(name) is None, f"wiring_for_name({name!r}) should be None"


def test_a_path_like_or_non_ascii_name_returns_none():
    lookup = _lookup()
    for name in ("../lightrag", "hipporag/base", "naïve"):
        assert lookup(name) is None, f"wiring_for_name({name!r}) should be None"
