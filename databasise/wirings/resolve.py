"""Loads the committed LightRAG base wiring and applies a named arm's RFC 6902 patch, producing a
plain resolved dict ready for ``databasise.validator.parse.parse_wiring`` (03-04-PLAN.md Task 2).

Uses ``jsonpatch`` (D-13) rather than a hand-written JSON-Pointer walker: CONTRACT depends on
``remove`` erroring on a missing target for its fail-closed subtraction guarantee — an arm patch
that names a node absent from the base MUST raise rather than silently succeeding — and
JSON-Pointer escaping and array-index semantics are exactly where a hand-rolled version goes
quietly wrong. ``jsonpatch.apply_patch`` already raises ``jsonpatch.JsonPatchConflict`` for a
``remove`` whose target does not exist; this module does not swallow or reinterpret that.

The base itself is also independently loadable with no arm applied (``load_base``) — CONTRACT
requires the base be independently validatable. Note, though: parsing the *unpatched* base needs
all fifteen new components registered (this plan's Task 2 only ports seven), so
``parse_wiring(load_base(), default_registry())`` only clears cleanly once plan 03-06 lands. Until
then, only the ``naive`` and ``bypass`` arms resolve to a fully-registered node set — every node
either arm keeps is one of the seven this plan ports.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonpatch

_WIRINGS_DIR = Path(__file__).resolve().parent / "lightrag"

_ARM_NAMES: tuple[str, ...] = ("naive", "bypass", "hybrid", "local", "global")


class UnknownArmError(ValueError):
    """Raised by :func:`resolve_arm`/:func:`resolved_node_ids` for an arm name with no
    corresponding ``arm-<name>.json-patch.json`` file under ``databasise/wirings/lightrag/``.
    """

    def __init__(self, arm_name: str):
        self.arm_name = arm_name
        super().__init__(
            f"unknown arm {arm_name!r}; known arms: {sorted(_ARM_NAMES)}"
        )


def _base_path() -> Path:
    return _WIRINGS_DIR / "base.json"


def _patch_path(arm_name: str) -> Path:
    if arm_name not in _ARM_NAMES:
        raise UnknownArmError(arm_name)
    return _WIRINGS_DIR / f"arm-{arm_name}.json-patch.json"


def load_base() -> dict[str, Any]:
    """The committed base wiring, unpatched, as a plain dict — independently loadable per
    CONTRACT (see module docstring for why it does not necessarily *parse* clean yet).
    """
    return json.loads(_base_path().read_text(encoding="utf-8"))


def resolve_arm(arm_name: str) -> dict[str, Any]:
    """Load the base, apply ``arm_name``'s RFC 6902 ``operations`` list, and return the resolved
    plain dict — ready for ``parse_wiring``. Raises :class:`UnknownArmError` for an unrecognised
    arm name, or lets ``jsonpatch.JsonPatchConflict`` propagate for a patch whose ``remove``
    targets a node absent from the base (the fail-closed subtraction guarantee this module exists
    to preserve — never caught or downgraded here).
    """
    base = load_base()
    patch_doc = json.loads(_patch_path(arm_name).read_text(encoding="utf-8"))
    operations = patch_doc["operations"]
    return jsonpatch.apply_patch(base, operations, in_place=False)


def resolved_node_ids(arm_name: str) -> set[str]:
    """The resolved node id set for ``arm_name`` — the set a conformance test compares against
    the patch file's own ``resulting_node_id_set`` field.
    """
    resolved = resolve_arm(arm_name)
    return set(resolved.get("nodes", {}).keys())


def declared_node_ids(arm_name: str) -> tuple[str, ...]:
    """The arm patch's own declared ``resulting_node_id_set`` field, read without resolving —
    the conformance-test comparison target for :func:`resolved_node_ids`.
    """
    patch_doc = json.loads(_patch_path(arm_name).read_text(encoding="utf-8"))
    return tuple(patch_doc["resulting_node_id_set"])


__all__ = [
    "UnknownArmError",
    "load_base",
    "resolve_arm",
    "resolved_node_ids",
    "declared_node_ids",
]
