"""17-13 (ROADMAP Phase 17 success criterion 2, D-02, D-03): every API-INVENTORY control is stamped or planned.

The keys come from ``docs/gui/API-INVENTORY.md``: each section 3 route heading
(``#### 3.x.y METHOD /path``) and the first cell of each section 5.1 gap-table row.
``docs/gui/INVENTORY-MAP.json`` must hold exactly those keys. Each value is one of:

- ``{"ids": [...]}``: every id is in ``docs/gui/MOCK-IDS.json``;
- ``{"planned": "<screen>.planned.list", "item": "..."}``: the id is in MOCK-IDS.json and the item text
  appears verbatim in the built mockup;
- ``{"not_a_control": "<reason>"}``: a server process, serving or engine change with no console control.

A row that is a console capability with neither ids nor a planned item is a missing planned item
(D-03): add it to the screen's planned list, not to ``not_a_control``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GUI_DOCS = ROOT / "docs" / "gui"

_ROUTE_HEADING = re.compile(r"^#### 3\.\d+\.\d+ (GET|POST|DELETE|PUT|PATCH) (\S+)")
_UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")


def _inventory_keys() -> tuple[list[str], list[str]]:
    lines = (GUI_DOCS / "API-INVENTORY.md").read_text(encoding="utf-8").split("\n")
    start3 = next(i for i, line in enumerate(lines) if line.startswith("## 3."))
    start4 = next(i for i, line in enumerate(lines) if line.startswith("## 4."))
    routes = []
    for line in lines[start3:start4]:
        match = _ROUTE_HEADING.match(line)
        if match:
            routes.append(f"{match.group(1)} {match.group(2)}")

    gap_start = next(i for i, line in enumerate(lines) if line.startswith("### 5.1 Gap table"))
    rows = []
    for line in lines[gap_start + 1 :]:
        if line.startswith("###"):
            break
        if line.startswith("|"):
            rows.append(_UNESCAPED_PIPE.split(line)[1].strip())
    # drop the header row and the |--- separator
    return routes, rows[2:]


def test_every_inventory_control_is_stamped_or_planned(mockup_path):
    routes, gaps = _inventory_keys()
    assert "POST /query" in routes and "DELETE /documents/{document_id}" in routes, routes
    assert len(gaps) >= 40, f"only {len(gaps)} section 5.1 rows parsed"
    keys = set(routes) | set(gaps)

    mapping = json.loads((GUI_DOCS / "INVENTORY-MAP.json").read_text(encoding="utf-8"))
    unmapped = sorted(keys - set(mapping))
    stale = sorted(set(mapping) - keys)
    assert not unmapped and not stale, f"unmapped inventory keys: {unmapped}; stale map keys: {stale}"

    mock_ids = set(json.loads((GUI_DOCS / "MOCK-IDS.json").read_text(encoding="utf-8")))
    mockup_text = mockup_path.read_text(encoding="utf-8")
    shapes = ({"ids"}, {"planned", "item"}, {"not_a_control"})
    problems = []
    for key, value in mapping.items():
        if not isinstance(value, dict) or set(value) not in shapes:
            problems.append(f"{key}: value must have exactly one of ids, planned+item, not_a_control")
        elif "ids" in value:
            ids = value["ids"]
            if not isinstance(ids, list) or not ids:
                problems.append(f"{key}: ids must be a non-empty list")
            else:
                missing = [i for i in ids if i not in mock_ids]
                if missing:
                    problems.append(f"{key}: ids not in MOCK-IDS.json: {missing}")
        elif "planned" in value:
            if not re.fullmatch(r"[a-z]+\.planned\.list", str(value["planned"])) or value["planned"] not in mock_ids:
                problems.append(f"{key}: planned id {value['planned']!r} is not a <screen>.planned.list in MOCK-IDS.json")
            if not isinstance(value["item"], str) or not value["item"] or value["item"] not in mockup_text:
                problems.append(f"{key}: planned item {value['item']!r} is not in the mockup text")
        elif not isinstance(value["not_a_control"], str) or not value["not_a_control"].strip():
            problems.append(f"{key}: not_a_control needs a non-empty reason")
    assert not problems, "\n".join(problems)
