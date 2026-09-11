---
title: Write the MelodyScribe skill — the one human-authored SKILL.md the frontier model reads
date: 2026-09-11
priority: low
---

Create `.claude/skills/melodyscribe/SKILL.md` documenting the §18 REST/MCP tools a frontier model uses to talk to MelodyScribe: `melodyscribe_transcribe`, `melodyscribe_file`, `melodyscribe_recall`, `melodyscribe_revise`; response shapes; and the rule that every returned value is fenced data, never instructions. Follow the Agent Skills spec format (agentskills.io: frontmatter name/description, progressive disclosure, optional scripts/ references/).

Constraints from the session decisions: this is the only skill the frontier reads about MelodyScribe (D-MS-02); MelodyScribe must not be able to write to this path; model-written Folios never appear here (D-MS-01).

Cost is near zero: the MCP surface already exists from Phases 4 and 5, so this is documentation of tools that are already there. Do it once the seam tool names are confirmed against the system-model review.
