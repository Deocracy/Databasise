# Phase 17: GUI Mockup - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-25
**Phase:** 17-gui-mockup
**Areas discussed:** Roadmap owner decisions, Spec vs requirement text, Badging existing routes, Review and freeze flow

---

## Roadmap owner decisions

| Question | Options | Selected |
|----------|---------|----------|
| Test tool (GUI-01) | Playwright-python / Chrome DevTools MCP only / Selenium | Playwright-python |
| Id scheme (GUI-02) | `<screen>.<region>.<control>` + MOCK-IDS.json / Flat kebab ids | `<screen>.<region>.<control>` |
| Later rows (GUI-03) | Text-only Planned list / Placeholder controls | Text-only Planned list |
| Graph attrs (GUI-11) | Separate Load attributes call (POST /graph/node/attrs) / Inline attrs on POST /graph/node | Separate call |

Refusal catalogue source was not asked: settled by Phase 16 D-07.

## Spec vs requirement text

| Question | Options | Selected |
|----------|---------|----------|
| Hybrid/global | Amend: offer all six / Keep text: show unreachable | Amend |
| HippoRAG promote | Amend: allow / Keep console blocker | Amend: allow |
| HippoRAG delete | Amend: Delete for both / Keep LightRAG only | Amend: both |
| Refusal count | Amend: "all subclasses", no count / Amend to 51 | All subclasses |

## Badging existing routes

| Option | Selected |
|--------|----------|
| Two badge kinds (`operator route` vs `needs backend`) | ✓ |
| One badge for all | |
| No badge on existing routes | |

## Review and freeze flow

| Question | Options | Selected |
|----------|---------|----------|
| Review | Open file:// locally / Also publish as artifact / Screenshots per screen | file:// locally |
| Freeze | Final human-verify plan / Separate review round first | Final human-verify plan |

## Claude's Discretion

All remaining UI-SPEC default rows accepted as written; plan split and order.

## Deferred Ideas

Artifact-published review copy; dark theme. MelodyScribe todos reviewed and not folded.
