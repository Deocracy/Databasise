# MelodyScribe naming convention

Decided 2026-09-11 by the owner. Applies to every artifact, model, store, skill, and tool that belongs to this work.

| Thing | Name | Form in code / paths |
|---|---|---|
| The project (this research side project and whatever it ships) | **MelodyScribe** | `melodyscribe` |
| The method inside Databasise (the wiring / modality that runs a micro-harness behind the §18 seam) | **MelodyScribe** | wiring id `melodyscribe` |
| The general pattern MelodyScribe is an instance of | micro-harness | `reference/micro-harnesses/` stays the folder name. **Not used inside Databasise**: the contract already uses "harness" for a stackable wrapper selected at the seam (CONTRACT §1, §18.4). Inside Databasise MelodyScribe is a *modality* / *wiring* |
| A fine-tuned model | **MelodyScribe-{size}-v{version}** | `MelodyScribe-2B-v0.1`, `MelodyScribe-1B-v0.1`, and for a mixture-of-experts base `MelodyScribe-30B-A3B-v0.1` (total parameters, then active parameters, the Hugging Face convention). Size is the base model class; version increments per training run that is promoted |
| The sandbox runtime the model runs in | MelodyScribe Scriptorium | Deployment name only. In contract terms it is CONTRACT §8 conditions 3 and 5 on an opaque node; SELECTION D4 allows no sandbox regime |
| A model-written skill file (micro-only) | MelodyScribe Folio | `melodyscribe-folio-{slug}/SKILL.md`, loaded only inside the Scriptorium |
| The skills store as a whole | MelodyScribe Folios | `melodyscribe/folios/` |
| A store or table built specifically for MelodyScribe | MelodyScribe {store} | prefix `melodyscribe_` on tables, namespaces, and collections |
| The deterministic validator a write must pass | MelodyScribe Proof | `melodyscribe_proof` |
| The one human-authored skill the frontier model reads | **MelodyScribe skill** | `.claude/skills/melodyscribe/SKILL.md`; the model cannot write to this path |
| The sectioned input format (embed / respond / file / link directives) — proposed | MelodyScribe Score | see `score-format-and-cache.md` |
| Internal wiring verbs | transcribe, file, recall, revise | Node names `melodyscribe/transcriber`, `/filer`, `/recaller`, `/reviser`. **Not seam tools**: CONTRACT §18.5 refuses per-modality tools for existing operations. The frontier selects MelodyScribe through the stable alias `melodyscribe` on the existing seam tools |
| Served model as machine clients | — | `core/llm-minicpm5-2b@…`, `core/embedder-melodyscribe-2b@…` (CONTRACT §8 cond. 3 makes the model a machine-injected client, not part of the node) |
| The frontier model used for distillation | teacher | plain word, no prefix |
| GSD artifacts (notes, seeds, spikes, todos) | — | slug `melodyscribe` |

Rules:

1. Anything purpose-built for MelodyScribe carries the MelodyScribe name so its origin is visible from the name alone.
2. Generic Databasise vocabulary (machine, modality, wiring, seam, rig, ledger, node, store) is not renamed. MelodyScribe is a wiring over those primitives, and its names sit beside them, not in place of them.
3. Model size is a rig variable, not a fixed choice (D-MS-05): 1B to 10B dense is the starting ground, starting small; a larger model, including a mixture of experts around 30B to 40B total, is used if the rig shows it is better. Model names carry size and version so the rig can compare `MelodyScribe-2B-v0.1` against `MelodyScribe-2B-v0.2` and against `MelodyScribe-1B-v0.1` without ambiguity.
