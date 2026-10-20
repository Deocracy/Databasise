"""WIRE-18 (D-17): the runner exposes no scheduling or budget API that nothing uses. The unused
budget-apportionment API is deleted, the run result echoes the two settings it was given, and the
per-node semaphore that the HippoRAG openie part uses stays. The wiring-string leg follows in 13-12.
"""

from __future__ import annotations

import ast
import json
import typing
from pathlib import Path

import pytest

from databasise.parts.registry import PartRegistry
from databasise.parts.schema import NodeContext, Part, WiringNode
from databasise.runner import budget, scheduler
from databasise.validator.errors import ValidationReport
from databasise.validator.parse import ParsedWiring

_PACKAGE_ROOT = Path(scheduler.__file__).resolve().parent.parent


@pytest.mark.parametrize(
    "name", ["split_allowance", "apportion", "ApportionmentPolicy", "Allowance", "BudgetHalted"]
)
def test_the_unused_apportionment_api_is_deleted(name):
    assert not hasattr(budget, name), f"databasise.runner.budget.{name} has no production caller"


def test_budget_state_has_no_degraded_member():
    assert "degraded" not in typing.get_args(budget.BudgetState)


async def test_run_wiring_echoes_both_settings():
    async def body(ctx: NodeContext):
        return {}

    part = Part(
        name_at_version="test/echo@1.0.0",
        kind="passthrough",
        structural_depth="stage",
        effects=[],
        upstream_ref=None,
        body=body,
    )
    parsed = ParsedWiring(
        nodes={"only": WiringNode(component="test/echo@1.0.0", kind="passthrough", deps=[])},
        parts={"only": part},
        deps={"only": ()},
        node_order=("only",),
        report=ValidationReport(),
    )

    result = await scheduler.run_wiring(
        parsed, PartRegistry(), {}, determinism_setting="cache-bypassed", concurrency_setting="sequential"
    )

    assert result.get("determinism_setting") == "cache-bypassed"
    assert result.get("concurrency_setting") == "sequential"


def test_the_node_semaphore_has_a_production_user():
    scheduler_path = Path(scheduler.__file__).resolve()
    users = []
    for top in sorted(_PACKAGE_ROOT.iterdir()):
        if not top.is_dir() or top.name.startswith(".") or top.name == "tests":
            continue
        for path in top.rglob("*.py"):
            if path.resolve() == scheduler_path:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            # openie reads it as getattr(ctx, "_semaphore", None); a body may also use ctx._semaphore.
            if any(
                (isinstance(n, ast.Attribute) and n.attr == "_semaphore")
                or (isinstance(n, ast.Constant) and n.value == "_semaphore")
                for n in ast.walk(tree)
            ):
                users.append(path.name)
    assert users, "no production part reads ctx._semaphore, so the scheduler's per-node semaphore is unused"
    assert "openie.py" in users


def test_no_wiring_json_carries_an_apportionment_string():
    """WIRE-18 (D-17): no wiring document under ``databasise/wirings`` declares an apportionment
    policy; no node apportions a metered budget, so the keys were prose with no behaviour."""
    keys = {"apportionment_policy", "apportioning_node"}

    def _found(value) -> set[str]:
        if isinstance(value, dict):
            return (keys & set(value)) | {k for v in value.values() for k in _found(v)}
        if isinstance(value, list):
            return {k for v in value for k in _found(v)}
        return set()

    offenders = {
        str(path.relative_to(_PACKAGE_ROOT)): sorted(found)
        for path in sorted((_PACKAGE_ROOT / "wirings").rglob("*.json"))
        if (found := _found(json.loads(path.read_text(encoding="utf-8"))))
    }

    assert offenders == {}
