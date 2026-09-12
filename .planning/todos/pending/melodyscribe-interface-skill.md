---
title: Write the MelodyScribe skill — the one human-authored SKILL.md the frontier model reads
date: 2026-09-11
priority: low
audit_acknowledged:
  milestone: v1.0
  at: 2026-09-12
---

Create `.claude/skills/melodyscribe/SKILL.md` documenting the existing §18 REST/MCP seam tools and how to select MelodyScribe through the stable alias `melodyscribe` (CONTRACT §18.4). No `melodyscribe_*` tools: §18.5 refuses per-modality tools for existing operations (see reference/micro-harnesses/system-model-fit.md §7). Cover response shapes; and the rule that every returned value is fenced data, never instructions. Follow the Agent Skills spec format (agentskills.io: frontmatter name/description, progressive disclosure, optional scripts/ references/).

Constraints from the session decisions: this is the only skill the frontier reads about MelodyScribe (D-MS-02); MelodyScribe must not be able to write to this path; model-written Folios never appear here (D-MS-01).

Cost is near zero: the MCP surface already exists from Phases 4 and 5, so this is documentation of tools that are already there. Do it once the seam tool names are confirmed against the system-model review.
