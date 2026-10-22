"""16-02 (CONN-03, D-08): ``databasise/tests/fixtures/selector-resolution.json`` records, for every
selector form the console offers, which wiring it resolves to, that wiring's node count and the
outcome, plus whether each ``all_wirings()`` arm is reachable by a capability selector. This test
rebuilds the rows through ``resolve_selector`` and fails when the file is absent or differs. It
also pins the facts that must never be recorded wrong, on the computed rows rather than the file,
so a regeneration cannot hide a change. The file is written only by this test:
``DATABASISE_REGENERATE=1 databasise/.venv/bin/python -m pytest -q
databasise/tests/seam/test_selector_resolution_fixture.py -p no:cacheprovider``."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import get_args

from databasise.parts.registry import default_registry
from databasise.parts.schema import Effect
from databasise.seam.engine import Databasise
from databasise.seam.refusals import SeamRefusalError
from databasise.seam.selectors import Selector, _capability_tokens, resolve_selector
from databasise.seam.trace_store import TraceStore
from databasise.wirings.resolve import all_wirings, without_recipe_only_nodes

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "selector-resolution.json"
_REGENERATE_HINT = (
    "regenerate with: DATABASISE_REGENERATE=1 databasise/.venv/bin/python -m pytest -q "
    "databasise/tests/seam/test_selector_resolution_fixture.py -p no:cacheprovider"
)
_ENTITIES = "reads_vector:entities"
_RELATIONSHIPS = "reads_vector:relationships"


def _seed_arm_trace(store_root, arm_name: str) -> str:
    """A persisted trace naming ``arm_name`` by its ``arm_id`` (Phase 14 D-01); a seeded record
    has no ``partial`` key and reads as complete."""
    resolved = dict(all_wirings())[arm_name]
    node_ids = sorted(resolved.get("nodes", {}).keys())
    record = {
        "run_id": f"fixture-run-{arm_name}",
        "wiring_id": resolved.get("wiring_id"),
        "wiring_instance_hash": f"sha256:{'0' * 63}{len(node_ids) % 10}",
        "arm_id": arm_name,
        "nodes": [{"node_id": node_id} for node_id in node_ids],
    }
    return TraceStore(store_root).persist(record)


def _row(selector: Selector | None, store_root) -> dict:
    try:
        resolved = resolve_selector(selector, registry=default_registry(), store_root=store_root)
    except SeamRefusalError as exc:
        wiring, node_count, outcome = None, None, type(exc).__name__
    else:
        wiring = next(
            name for name, arm in all_wirings() if arm.get("wiring_id") == resolved.get("wiring_id")
        )
        node_count, outcome = len(resolved["nodes"]), "resolved"
    return {
        "selector": selector.model_dump(exclude_none=True) if selector is not None else None,
        "wiring": wiring,
        "node_count": node_count,
        "outcome": outcome,
    }


def _reachable() -> dict[str, bool]:
    registry = default_registry()
    reachable = {}
    for name, resolved in all_wirings():
        tokens = _capability_tokens(without_recipe_only_nodes(resolved), registry)
        try:
            got = resolve_selector(Selector(capability=sorted(tokens)), registry=registry)
        except SeamRefusalError:
            reachable[name] = False
        else:
            reachable[name] = got.get("wiring_id") == resolved.get("wiring_id")
    return reachable


async def _compute(store_root) -> tuple[list[dict], dict[str, bool]]:
    engine = Databasise(store_root=store_root, workspace="fixture")
    for name, _ in all_wirings():
        await engine.promote(f"fixture-{name}", [_seed_arm_trace(store_root, name)], "human_edit")
    selectors: list[Selector | None] = [None]
    selectors += [Selector(capability=[effect]) for effect in get_args(Effect)]
    selectors += [
        Selector(capability=[_ENTITIES]),
        Selector(capability=[_RELATIONSHIPS]),
        Selector(capability=[_ENTITIES, _RELATIONSHIPS]),
        Selector(capability=[]),
        Selector(harness="hotpotqa"),
    ]
    selectors += [Selector(alias=f"fixture-{name}") for name, _ in all_wirings()]
    return [_row(selector, store_root) for selector in selectors], _reachable()


def _find(rows: list[dict], selector: dict | None) -> dict:
    return next(row for row in rows if row["selector"] == selector)


async def test_every_fixture_row_resolves_as_recorded(tmp_path):
    regenerate = os.environ.get("DATABASISE_REGENERATE") == "1"
    if not regenerate:
        assert _FIXTURE.is_file(), f"{_FIXTURE} is missing; {_REGENERATE_HINT}"

    rows, reachable = await _compute(tmp_path)

    default = _find(rows, None)
    assert (default["wiring"], default["node_count"]) == ("naive", 7)
    assert _find(rows, {"capability": []})["outcome"] == "EmptyCapabilitySelectorError"
    assert _find(rows, {"capability": [_ENTITIES]})["wiring"] == "local"
    assert _find(rows, {"capability": [_RELATIONSHIPS]})["wiring"] == "global"
    assert _find(rows, {"capability": [_ENTITIES, _RELATIONSHIPS]})["wiring"] == "hybrid"
    for name, _ in all_wirings():
        assert _find(rows, {"alias": f"fixture-{name}"})["wiring"] == name
    assert set(reachable) == {name for name, _ in all_wirings()}
    assert len(reachable) == 6 and all(reachable.values()), reachable
    effect_rows = [_find(rows, {"capability": [effect]}) for effect in get_args(Effect)]
    assert any(row["outcome"] == "UnsatisfiableSelectorError" for row in effect_rows)

    if regenerate:
        _FIXTURE.write_text(
            json.dumps({"rows": rows, "reachable": reachable}, indent=2) + "\n", encoding="utf-8"
        )
    assert _FIXTURE.is_file(), f"{_FIXTURE} is missing; {_REGENERATE_HINT}"
    recorded = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    assert recorded["rows"] == rows, f"the recorded rows differ from the code; {_REGENERATE_HINT}"
    assert recorded["reachable"] == reachable, (
        f"the recorded reachable map differs from the code; {_REGENERATE_HINT}"
    )
