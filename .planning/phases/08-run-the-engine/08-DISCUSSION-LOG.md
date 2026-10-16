# Phase 8: Run the Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-16
**Phase:** 08-run-the-engine
**Areas discussed:** Process topology & lock, Client failure behavior, Browser access (CORS), Test evidence records

---

## Process topology & lock

| Option | Description | Selected |
|--------|-------------|----------|
| One process, MCP mounted | databasise-rest also mounts MCP streamable-http | |
| Two separate processes | Independent launchers; one holds a store root at a time | |
| Other | Owner: unsure MCP adds anything over REST or is needed now | ✓ |

Follow-up after showing that MCP already exists (9 tools, all with REST equivalents):

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal launcher, 2 processes | databasise-mcp stdio as RUN-06 states, no mount | ✓ |
| Defer the MCP launcher | BAK deferral request for the MCP half of RUN-06/07 | |
| Drop MCP from the product | Milestone-level change | |

| Option | Description | Selected |
|--------|-------------|----------|
| Same lock, refuse | Parity CLIs take the launcher lock and refuse | ✓ |
| Run against a copy | Snapshot the store root | |
| Operator's responsibility | No guard | |

---

## Client failure behavior

| Question | Options | Selected |
|----------|---------|----------|
| RUN-02 no usage | call_count=1 'unbudgetable' / new sentinel / tiktoken | call_count=1 'unbudgetable' |
| RUN-03 content=None | raise named error / empty text + stop_reason | raise named error |
| RUN-05 rerank | not available / ship a rerank client | ship a rerank client |
| Launcher without clients | refuse unless --no-clients / always refuse / start degraded | refuse unless --no-clients |
| Rerank API shape | Cohere/Jina /rerank / v1 bindings / you decide | Cohere/Jina /rerank |
| Rerank env keys | optional / required | optional |
| Wiring live_rerank | client only / add rerank arm | client only |
| Live rerank test | fakes now, live later / have endpoint | fakes now, live later |

**Notes:** Shipping rerank changes RUN-05's wording ("No rerank client is built"); owner-approved amendment needed.

---

## Browser access (CORS)

| Question | Options | Selected |
|----------|---------|----------|
| How the console reaches REST | allow-list / same-origin serving / both | allow-list |
| Dev shortcuts | exact origins only / localhost regex | exact origins only |

---

## Test evidence records

| Question | Options | Selected |
|----------|---------|----------|
| RUN-01 COVERAGE.md home | databasise/evidence/ / docs/ / archive | databasise/evidence/ |
| RUN-11 threshold | measured floor / keep 0.999 + pin endpoint / retry N | measured floor |

---

## Claude's Discretion

- Lock mechanism, lock file location, error class name
- Launcher module layout and shared builder location
- Example MCP config location and format
- Rerank client class and error names

## Deferred Ideas

- MCP mounted in FastAPI (one process)
- A live_rerank wiring arm (Phase 13 or later)
- Same-origin console serving (Phases 16-18)
- Deterministic pinned embedding endpoint for a 0.999 threshold
