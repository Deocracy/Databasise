---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 1
total_count: 2
last_updated: 2026-09-06T23:20:55.764Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 04 | stub | databasise/seam/envelope.py |  | evidence/token_accounting fields declared empty per declare-upfront checkpoint decision; filled by 04-02 | fixed |  | 2026-09-06T22:23:03.911Z | 2026-09-06T23:20:55.764Z |
| 2 | 04 | stub | databasise/seam/envelope.py |  | trace_token/seam_events fields declared empty per declare-upfront checkpoint decision; filled by 04-04 | open |  | 2026-09-06T22:23:04.063Z |  |

````json
[
  {
    "id": 1,
    "kind": "stub",
    "phase": "04",
    "file": "databasise/seam/envelope.py",
    "line": null,
    "description": "evidence/token_accounting fields declared empty per declare-upfront checkpoint decision; filled by 04-02",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-09-06T22:23:03.911Z",
    "resolved_at": "2026-09-06T23:20:55.764Z"
  },
  {
    "id": 2,
    "kind": "stub",
    "phase": "04",
    "file": "databasise/seam/envelope.py",
    "line": null,
    "description": "trace_token/seam_events fields declared empty per declare-upfront checkpoint decision; filled by 04-04",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-06T22:23:04.063Z",
    "resolved_at": null
  }
]
````
