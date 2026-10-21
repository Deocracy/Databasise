"""LEDG-12 (14-07, D-13): the production registry admits no part that no selector reaches.

An admitted part (one carrying a CONTRACT section 8 admission record) is runnable by any wiring
that names it, so one that no wiring names is surface nobody can exercise (CONTRACT section 14.4
point 3 for a ``mutates_store`` part). Every admitted ``default_registry()`` key must be a node
component of a wiring a selector or a corpus verb can run: ``all_wirings()`` (the selectors'
candidate pool) or a ``corpus-ingest`` / ``corpus-delete`` wiring of a ``WIRING_NAMES`` family
(``Databasise.ingest()`` / ``delete_document()``).
"""

from __future__ import annotations

from databasise.parts.registry import default_registry
from databasise.wirings.resolve import WIRING_NAMES, all_wirings, load_wiring


def _components(wiring: dict) -> set[str]:
    return {node["component"] for node in wiring.get("nodes", {}).values()}


def test_every_admitted_registered_part_is_reachable():
    registry = default_registry()
    # PartRegistry is not a dict, so `in registry` is not defined and .keys() is the iteration.
    admitted = {
        key
        for key in registry.keys()  # noqa: SIM118
        if getattr(registry.get(key), "admission", None) is not None
    }

    referenced: set[str] = set()
    for _name, wiring in all_wirings():
        referenced |= _components(wiring)
    for family in WIRING_NAMES:
        for op in ("ingest", "delete"):
            try:
                wiring = load_wiring(family, variant=f"corpus-{op}")
            except FileNotFoundError:
                continue
            referenced |= _components(wiring)

    unreachable = sorted(admitted - referenced)
    assert unreachable == [], (
        f"admitted parts in default_registry() that no selector or corpus wiring reaches: {unreachable}"
    )
