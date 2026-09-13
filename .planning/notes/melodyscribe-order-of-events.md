---
title: MelodyScribe moves to its own repository — order of events (pointer)
date: 2026-09-13
context: Owner decision after the round-4 harness research and the post-011 training conversation.
---

MelodyScribe continues in `/home/chris/coding/MelodyScribe` (GitHub `DeBIOS-Foundation/MelodyScribe`), with GSD started fresh there by the owner. The order of events is `docs/ORDER-OF-EVENTS.md` in that repository. Standing rules that override earlier notes in this repository: one 1B model only (no 2B, 4B, 8B arms; no second model inside the harness; the 0.6B embedder is an evaluation reference at most); the harness is designed and built first with the untrained 1B, the dataset is generated inside the harness afterwards; Databasise 2.0 stays the foundation, with tweaks recorded as contract-update proposals.

Superseded here: spike 012 and 013 stubs (2B, 0.6B parity bar, dataset before harness) and the harness-frameworks note's frozen-0.6B-index assumption. Copied to the new repository: `.planning/spikes/` (tracked files), `reference/micro-harnesses/`, `docs/system-model/`, `.planning/notes/melodyscribe-*`, the spike-findings skill, the parity corpus fixtures and loader, the embeddings-sidelined report, and the thinking-embeddings report. Spike environments (`.venv`, `.venv-train`, `.models`) and secrets (`v1/.env.parity`) stay on disk here and are referenced by path.
