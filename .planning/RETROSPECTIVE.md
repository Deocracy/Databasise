# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Fully Agnostic System

**Shipped:** 2026-09-12
**Phases:** 7 | **Plans:** 64 | **Sessions:** not tracked (569 commits over 15 days)

### What Was Built
- An embeddable machine (runner, identity, registry, embedded Cozo/Faiss/SQLite stores) that executes wiring graphs of versioned parts under structured concurrency with metered spend.
- The §18 seam: one closed envelope, four selectors, named refusals, reachable in-process, over REST and over MCP with proven parity.
- Two modalities behind that seam: LightRAG (query side decomposed, ingest admitted opaque) and HippoRAG 2 (fully decomposed), run side-by-side on one corpus and compared in one call.
- Append-only promotion ledger with atomic operator verbs; eval bundle and A/A driver ready for the first measured promotion.

### What Worked
- Verification that re-reproduces claims live instead of trusting SUMMARY.md caught every real gap (Phase 1 unmetered spend, Phase 3 silently-empty extraction, Phase 5 fabricated ingest success, Phase 7 check-then-act race).
- Refuse-don't-fabricate as a house rule: parity harness, evidence renderers and the A/A driver all record `inconclusive` or refuse rather than emit a number. No fabricated verdict shipped.
- Written gate amendments (02-GATE-01-WAIVER, 03/06/07-GATE-AMENDMENT) kept deferrals explicit and dated instead of silent.
- Cross-transport parity tests (in-process / REST / MCP, fixed-trace-token isolation) made every new surface cheap to prove equal.

### What Was Inefficient
- MACH-03 was re-timed four times. The decision to not spend on A/A calibration should have been taken once, early, and recorded as a milestone-level posture instead of re-litigated per phase.
- Mass requirement-status reverts on `gaps_found` (Phase 5, `7c5b9f1`) flipped requirements that were never defective and were only partly restored; the audit had to correct HARD-01/02/04 and the Phase 5 rows.
- Phase 3 needed three review-fix iterations plus a gap-closure wave (03-11..13) because the first parity run was measured against an index with no knowledge graph; an ingest sanity guard earlier would have saved the rework.
- Phase 6 grew to 18 plans, several of them paperwork-only (06-11, 06-17, 06-18) recording declined spend.
- VALIDATION.md was seeded for six phases but reconciled for only two; Nyquist coverage stayed a TODO through the whole milestone.

### Patterns Established
- Every store write goes through a machine primitive; opaque parts write `quarantined`, never `shared`.
- One event-shaping implementation per surface (streaming), one refusal mapper per transport, one shared engine instance under REST and MCP.
- Gate amendments live in the phase directory, cite `docs/system-model/` rather than editing the upstream mirror, and name the point of first need.
- Real-spend runs are dry-run by default and require an explicit flag.

### Key Lessons
1. Record spend posture once per milestone. A recurring "decline" costs a plan each time it recurs.
2. Never mass-revert requirement statuses; revert only the rows the verification actually names.
3. Guard ingest outputs for emptiness before any measurement rides on them.
4. Keep human-only items (CONTRACT §5 causes, spot-checks) out of phase gates; route them to a standing testing plan the owner works at their own pace.

### Cost Observations
- Model mix: not tracked this milestone (adaptive profile).
- Sessions: not tracked.
- Notable: the full suite grew from 233 tests (Phase 1) to 1068 passing at close with a 205 s runtime; no external services are needed to run it.

---

## Milestone: v1.1 — Engine Fixes + Operator Console

**Shipped:** 2026-11-01
**Phases:** 11 | **Plans:** 136 | **Sessions:** not tracked (1,096 commits over 18 days)

### What Was Built
- Installed `databasise-rest` and `databasise-mcp` launchers with a shared model client builder, loopback-only binds, Origin/Host guards and one engine process per store root.
- Every confirmed engine defect in CODEBASE-MAP.md §4 fixed against a test that failed first: one refusal shape on REST and MCP, all-or-nothing store commits, a LightRAG corpus path whose ingests reach the queried stores, HippoRAG evidence that resolves, truthful run records, operator verbs that never 500, and wheel-runnable CLIs that never spend by default.
- Operator read routes behind `--operator`, a frozen six-screen console mockup, and the live console served at GET /console under a hash-only CSP, wired screen by screen and approved by the owner on real clients.
- A closing debugging and security battery (three STRIDE audits, a 1,161-request probe, a ~60,000-input fuzz, a six-dimension sweep) whose 27 confirmed defects were all fixed and re-verified.

### What Worked
- The BAK ledger (169 rows, each with a test ref, a fail-first proof at a RED commit and a done status) made dropped requirements mechanically impossible; nothing was closed on a SUMMARY claim.
- Fingerprinted verifications (covered_files plus digest) caught every later edit that touched a verified phase, so re-verification ran exactly where code moved.
- Running independent work in parallel (re-verifications, trace checkers, audits, probes) while sequential fixers owned the tree kept a single working tree safe and still cut wall-clock time.
- Adversarial verification of findings (three refuters per candidate) killed 7 of 24 sweep candidates as documented design and caught two fixes that broke protected tests before they were accepted.
- Fuzzing found a whole class of 500s (lone surrogates, NaN/Infinity, deep nesting) that every hand-written test missed.

### What Was Inefficient
- Mid-milestone edits to shared files (serve_rest.py, pyproject.toml, refusals.py) tripped the fingerprints of up to eleven earlier verifications at once; each trip cost a full re-verification round.
- The frozen mockup embeds the refusal catalogue, so adding one refusal class forced an owner re-freeze and re-lock late in the close.
- BAK hooks block any Bash command that mentions the records directory or a tests path, and the stall watcher fires on idle turn-ends; both cost repeated retries until the rules were saved to memory.
- A one-off `uv build` left `databasise/build/` in the tree twice, and the posture test scanned it as source.
- The GSD archive step moved every file the BAK traces cite; repointing 33 traces was manual.

### Patterns Established
- Test-first fix commits in RED/GREEN pairs with a `phase/NN` trailer; `record-fail` proves each requirement's test failed at its RED commit.
- Owner-only verbs (approve, freeze-variant, lock-checks) stay with the owner; the agent drafts the exact command.
- Every owner question goes through the selectable question box with the recommended option first.
- Linking a test to a requirement locks the file, so any fix that needs a test change lands before the linking.
- Response builders sanitise every caller-derived value (UTF-8 safe, finite, bounded) at one point instead of per refusal.

### Key Lessons
1. Put shared-file edits early in a milestone, or batch them, because each one re-opens every verification that covers the file.
2. Do not embed generated catalogues in frozen artifacts; reference them, so the artifact survives a new entry.
3. Fuzz every public boundary once per milestone; hand-written tests do not find encoding and nesting classes.
4. Plan the BAK trace layout for the GSD archive move before the close: either cite archived paths from the start or script the repoint.
5. A test that reads `/proc/self/net/tcp` counts the whole network namespace; assert on process-owned sockets instead.

### Cost Observations
- Model mix: Opus and Fable (Claude 5 family) orchestrators; subagents inherited the session model; one code review ran on Sonnet.
- Sessions: not tracked.
- Notable: the full offline suite grew from 1068 (v1.0) to 3377 passing at close, about 11 minutes; the closing battery alone ran about 300 agents across five workflows.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | n/a | 7 | Gate amendments as first-class records; owner testing moved out of phases into TESTING-PLAN.md |
| v1.1 | n/a | 11 | BAK ledger with fail-first proofs per requirement; fingerprinted verifications; adversarial security battery at the close |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | 1068 passed / 1 skipped | not measured | FTS5 lexical store, blob store, namespace derivation, budget token arithmetic |
| v1.1 | 3377 passed (+ 1 environment-dependent) | not measured | operator console (vanilla JS, no framework), console package data, refusal sanitiser |

### Top Lessons (Verified Across Milestones)

1. Live re-reproduction beats summary trust (two milestones: v1.0 verification, v1.1 fingerprinted re-verification and adversarial verification).
2. Refuse rather than fabricate (two milestones: v1.0 inconclusive records, v1.1 named refusals for every caller fault).
3. Keep owner-only work out of phase gates and route it to a standing plan (two milestones: TESTING-PLAN.md in v1.0, RUN-11 deferral and owner verbs in v1.1).
