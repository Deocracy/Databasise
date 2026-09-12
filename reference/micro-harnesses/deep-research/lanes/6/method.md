# Lane 6 method

## Queries run

arXiv API (`export.arxiv.org/api/query`, 3s spacing; one bulk `id_list`
verification for 15 ids):
- `all:"Agentic Context Engineering"`, `all:"Dynamic Cheatsheet"`,
  `all:"Agent Workflow Memory"`, `all:"SOP-Agent"`,
  `all:"Defeating Prompt Injections by Design"`,
  `all:"prompt injection attack against LLM-integrated applications"`,
  `all:"memory poisoning" AND all:"LLM agent"` (surfaced the 2026 cluster used
  only as abstain leads), plus `id_list` verification for all 19 admitted
  papers and one failed check (`2405.04619`, returned a physics paper,
  which caught a BadChain id misrecall before it could enter the inventory).

Semantic Scholar API (1s spacing): citations of arXiv:2308.10144 (hit a 429
and returned no usable rows; recorded as failed) and references of
arXiv:2503.03704 (succeeded; surfaced the episodic-risks paper 2501.11739,
the memory-mechanism survey 2404.13501, INMS 2404.09982, and MemoryBank, all
subsequently verified via arXiv and admitted).

Web search (discovery + cross-checks): ExpeL, MINJA, AgentPoison, PoisonedRAG,
indirect-prompt-injection, Voyager, Reflexion, ACE, SOP-Agent, Agent Skills,
and the DeChant authorship confirmation. One ACE search call returned a 429
and was retried via direct abs-page fetch instead.

GitHub API (verified stars/push/license): MineDojo/Voyager, LeapLabTHU/ExpeL,
noahshinn/reflexion, joonspk-research/generative_agents, anthropics/skills,
sleeepeer/PoisonedRAG, AI-secure/AgentPoison (after following the move from
BillChan226/AgentPoison). Quota then exhausted (60/h), so the remaining eight
repos were verified via fetched GitHub project pages (stars + license visible;
exact push dates not extractable there and recorded as unknown).

Web fetches of primary pages: arXiv abs for 2510.04618, 2409.07429,
2501.09316; agentskills.io spec (SKILL.md format, progressive disclosure,
Anthropic origin, agentskills/agentskills spec repo); ACM DL (AISec 2023),
AAAI proceedings (ExpeL), NeurIPS proceedings (MINJA, AgentPoison), USENIX
Security 2025 (PoisonedRAG), IEEE SaTML (DeChant).

PDFs: 19 downloaded from `https://arxiv.org/pdf/<id>`, each checked to start
with `%PDF`; repo URLs in the inventory were extracted from the PDF bytes
themselves. Title confirmation via abs pages for all 19.

## Counts

Screened 27 (19 papers + 1 spec admitted; 7 abstained). Admitted 20. The lane
minimum (20 screened, 8 admitted) is met.

## What failed

- Semantic Scholar citation chaining for ExpeL: HTTP 429, no key available;
  forward-chaining evidence rests on the MINJA-references call, which
  succeeded.
- GitHub API rate limit hit mid-lane; fallback was page fetches (no push
  dates) — recorded honestly as `unknown` rather than estimated.
- arXiv API briefly rate-limited on a single-id recheck near the end; the
  fact (DeChant authorship/venue) was confirmed by web search instead.
- No primary source found for a "MemFS" file-memory paper; no verified id
  for BadChain or Progent; vendor material (instruction hierarchy) used only
  as abstain context, never as evidence.
