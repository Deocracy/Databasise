# Phase 2: Falsifier Gate - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-31
**Phase:** 2-falsifier-gate
**Areas discussed:** Phase scope (defer vs front-load), test necessity, eval corpus, model/provider
choice, multi-LLM cross-checking, parallelization

---

## Phase scope — front-load the gate or build product first

| Option | Description | Selected |
|--------|-------------|----------|
| Run Phase 2 as roadmapped | Falsifiers 2 and 5 + bundle + doc passes before any rung-2 work | |
| Full deferral | All testing after the product is built, human-in-the-loop via GUI | |
| Re-scope (hybrid) | Keep Falsifier 2 (near-free, mostly built) + MACH-09 + recorded waiver; defer Falsifier 5 to point of need; defer doc passes | ✓ |

**User's choice:** Re-scope. "I would rather build the product then edit and fix it later
according to checks... are any of these tests essential to finishing the product?"
**Notes:** Claude's counterpoints, accepted by structure of the re-scope: (1) the ratified §VD
verdict names both falsifiers as conditions, so the deferral is recorded as an owner amendment,
not drift; (2) human eyes cannot separate sampling noise from subtle regression — sized as low
risk for Phase 3 since prompts/models are unchanged; retrieval-level deterministic parity covers
gross breakage. Deferring Falsifier 5 to the real pre-decomposition original was noted as
methodologically better than calibrating on a stand-in arm.

---

## Test necessity and cost

**User's question:** what are these tests, how important, what do they cost in tokens?
**Answer recorded:** 7 of 9 items cost zero LLM tokens; the bill concentrates in the T0
calibration (0.85–2.6M tokens) and, dominating everything if chosen, the index shape (graph
extraction ~8.6–11.9K tokens/chunk vs embed-only ~$0 local). Full brief published as artifact
"Falsifier Gate Test Plan" (2026-08-31) with live OpenRouter pricing.

**Free tests run on request (2026-08-31):** 233/233 pytest suite green; Falsifier 2 evidence
script over the three named wirings — taint rule overrides declared depth, both self-declaration
probes refused. Falsifier 2 does not fire.

---

## Eval corpus (banked for deferred Falsifier 5)

| Option | Description | Selected |
|--------|-------------|----------|
| HotpotQA distractor | Gold answers + gold passages ship with it; HippoRAG 2's benchmark family; size scales with question count | ✓ (recommendation accepted implicitly) |
| 2WikiMultihopQA / MuSiQue | Same family, alternates | |
| UltraDomain (LightRAG's own) | Fails §EV.2 — no gold passages | |
| BEIR subsets | Fails §EV.2 — no gold answers | |
| v1 sample_dataset.json | Both families but tiny; smoke fixture only | |

---

## Model / provider (banked)

| Option | Description | Selected |
|--------|-------------|----------|
| Free model everywhere | $0 but free variants re-route across providers; identity drift voids the floor | drafts only |
| qwen3.7-flash generator, pinned | $0.03/$0.13 per M; recorded calibration ≈ $0.10 | ✓ |
| Paid judge (gemini-3.1-flash-lite / gpt-5-mini), pinned + hashed | Judge is part of bundle identity; ~160 judgments ≈ $0.04 | ✓ |
| Ensemble judge (multi-LLM cross-check) | Multiplies T0 bill forever; locked into bundle identity; suppresses the variance A/A exists to measure | rejected — use different generator vs judge models instead (free, removes self-preference bias) |

**User's framing:** "preferably a free model... it also may not be a bad idea to use more than one
llm to cross check but that's not necessary I don't think."

---

## Parallelization

**User's question:** the old 3-runs-at-a-time cap — fixed? Can we get 1,000 runs at once at
20 tok/s?
**Answer recorded:** v1's cap (`DEFAULT_MAX_PARALLEL_INSERT=3`, global lock) is structurally gone
— v2 is per-node `max_concurrency`, no global cap. Free tier: hard 20 req/min (50/day unfunded,
1,000/day after $10 lifetime credits) — 1,000 concurrent impossible on free. Paid: no platform
cap; a few hundred concurrent realistic. Phase 2 needs only 240–2,240 calls. §AA.1 pins the
declared concurrency into the null's identity → pick 8 once, keep it.

## Claude's Discretion

- Evidence artifact shape/location; GATE-01 waiver record form
- MACH-09 implementation details within the refusals house style
- Test structure per existing conventions

## Deferred Ideas

- MACH-02/MACH-03 → Phase 3 point of need (roadmap amendment required)
- HARD-01/HARD-02 → later doc pass
- Review GUI for human-in-the-loop checking → possible future scope addition
- DuckDB scoreboard analytics → moves with the statistical machinery
