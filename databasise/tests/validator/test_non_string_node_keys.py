"""Fuzz F8: a wiring document whose ``nodes`` mixes non-string and string keys (Python API) must be
reported as ``CODE_INVALID_WIRING_DOCUMENT``, never raise (``sorted(all_nodes)`` in
``validator/cycles.py`` raised ``TypeError`` on the mixed key types).
"""

from __future__ import annotations

from databasise.parts.registry import PartRegistry
from databasise.validator.errors import CODE_INVALID_WIRING_DOCUMENT
from databasise.validator.parse import parse_wiring

_NODE = {"kind": "passthrough", "component": "core/passthrough@1.0.0", "deps": [], "effects": []}


def test_mixed_non_string_node_keys_are_reported_not_raised():
    parsed = parse_wiring({"nodes": {1: dict(_NODE), "a": dict(_NODE)}}, PartRegistry())

    assert not parsed.report.ok
    assert [v.pointer for v in parsed.report.violations if v.code == CODE_INVALID_WIRING_DOCUMENT] == ["/nodes"]


def test_string_keyed_nodes_still_parse_alongside_a_bad_key():
    bad_dep = dict(_NODE, deps=["ghost"])
    parsed = parse_wiring({"nodes": {None: dict(_NODE), "a": bad_dep}}, PartRegistry())

    codes = {v.code for v in parsed.report.violations}
    assert codes == {CODE_INVALID_WIRING_DOCUMENT, "dangling-dep"}
