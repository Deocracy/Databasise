---
spike: 008
idea: melodyscribe
name: graph-prompt-design
type: comparison
validates: "Given spike 003's teacher labels and its student harness, when MiniCPM5-2B and Qwen3-4B emit ops under the v0.2 grammar with different prompt designs, then routing_exact, Proof-pass rate, recall and F1 against the teacher, and tokens per paragraph per design"
verdict: PENDING
related: [001, 003]
tags: [prompts, graph, extraction, few-shot]
---

# Spike 008: graph-prompt-design

## What This Validates

Which prompt gets the most correct graph and SQL ops out of a small model before any fine-tuning, and what the cache-friendly placement of the instruction costs. Spike 003 used one schema-only zero-shot instruction; this spike varies it on identical inputs. Read `.claude/skills/spike-findings-melodyscribe/references/model-size-and-training.md` and `score-io-contract.md` first; reuse `.planning/spikes/003-op-emission-size-sweep/student.py`, `evaluate.py`, `common.py`, `resolve.py`, `v02_grammar.py`, and `teacher.json` read-only through `sys.path` (copy what you must change into this folder; never edit spike 003).

## Plan

Models: MiniCPM5-2B Q8 and Qwen3-4B Q8 (GGUF), raw completion, temperature 0, seed fixed, 1024-token cap, think tags scanned, exactly as spike 003.

Held-out rule: few-shot examples come only from documents that are not scored. Choose 4 example documents by a fixed rule (for instance the four with the median op count in `teacher.json`), score the other 16 for every design, including the zero-shot baseline, so all designs share one scored set.

Designs:

- D0: spike 003's schema-only zero-shot instruction (baseline, must reproduce 003's numbers on the 16-document subset).
- D1: one-shot, one held-out example (section plus its teacher ops).
- D2: three-shot.
- D3: two-step: first emit the entity list under a grammar, then emit ops with that list in context; report the combined tokens.
- D4: a LightRAG-style extraction instruction adapted to the schema (entity types named, relation descriptions, "extract all").
- D5: predicate vocabulary hint: the 30 most frequent predicates and attributes from the example documents' teacher ops listed in the instruction.
- D6: D0 with the instruction placed after the section instead of before it (the placement the one-pass design prefers so the section prefix is shared across tasks).
- D7: D0 with a one-line plan prefix ("List the entities, then the facts with dates, then the relations.") and thinking still disabled.

Metrics from `evaluate.py`: routing_exact, subject/value recall, op precision, recall, F1, parse rate, Proof-pass rate with failure categories, tokens and seconds per paragraph. Report each design on both models in one table.

Pass conditions, stated before the run: the best design must beat D0 by at least 0.10 routing_exact or 0.10 Proof-pass rate on a model to be recommended; D6's penalty relative to D0 is reported as the cost of cache-friendly placement; the recommended instruction text is written to `results/best-prompt.md` with its numbers.

Environment: `.venv`, `env.sh`, GPU lock on every model load, one model per process; the 003 harness already handles this when called per arm.

## Research

(to fill: docs read, approaches compared)

## How to Run

(to fill)

## What to Expect

(to fill)

## Investigation Trail

(to fill: every iteration with its log)

## Results

(to fill: verdict with sub-claims and the head-to-head table)
