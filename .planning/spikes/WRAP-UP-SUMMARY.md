# Spike Wrap-Up Summary

**Date:** 2026-09-12
**Spikes processed:** 5
**Feature areas:** Score I/O contract; One-pass runtime; Model size and training
**Skill output:** `./.claude/skills/spike-findings-melodyscribe/`

## Processed Spikes
| # | Name | Type | Verdict | Feature Area |
|---|------|------|---------|--------------|
| 001 | score-io-model | standard | VALIDATED | Score I/O contract |
| 002 | one-pass-runtime | standard | VALIDATED | One-pass runtime |
| 003 | op-emission-size-sweep | comparison | VALIDATED | Model size and training (v0.2 evidence to Score I/O contract) |
| 004 | self-embedding-parity | comparison | PARTIAL | Model size and training |
| 005 | kv-composition-quality | standard | PARTIAL | One-pass runtime |

All five were built by Muse Spark 1.3 agents through `run-spike.sh` (total agent cost about USD 0.32) and accepted only after an owner-side re-run of each `run.sh` reproduced the numbers; 003's re-run reproduced all 126 student decodes byte-identically.

## Key Findings
1. The one-pass mechanism is real at 2B: embedding and logits from one decode, isolated sequences, bit-exact prefix copy, grammar-constrained ops, prefill about 3.7k tokens/s (002).
2. The contract holds: Score compilation is deterministic and neighbour-independent, and Proof passes 95/95 acceptance checks (001). Evidence must be a verbatim quote the harness resolves to offsets; model-emitted offsets fail for frontier and small models alike (003, spec v0.2 candidate, owner review pending).
3. Scale alone does not buy accuracy pre-fine-tune: 1B emits an empty op list on every document; routing is flat 0.30 to 0.45 from 2B to 8B while tokens and seconds per paragraph grow about a hundredfold. Cost is the size differentiator today; the starting candidate is 2B-class and the question reopens after training (003, D-MS-05).
4. Untrained self-embedding is not usable: the dedicated 0.6B embedder wins by a wide margin because untrained states are anisotropic (pairwise cosine 0.91 to 0.95 versus 0.28); a ridge head does not close the gap; the contrastive adapter is the open test and needs query-passage pairs (004).
5. KV modules are second-order at 2B: TTFT 2.4x to 8.5x relative but 20 to 110 ms absolute; shift reuse about 1.1x; saved state not bit-exact. Keep runtime prefix reuse, skip a persisted module store (005).
6. Fine-tune targets from Proof's failure categories: evidence quotes must contain the subject or value, ISO dates, termination under the cap (003).
