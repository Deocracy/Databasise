# MelodyScribe naming convention

Decided 2026-09-11 by the owner. Applies to every artifact, model, store, skill, and tool that belongs to this work.

| Thing | Name | Form in code / paths |
|---|---|---|
| The project (this research side project and whatever it ships) | **MelodyScribe** | `melodyscribe` |
| The method inside Databasise (the wiring / modality that runs a micro-harness behind the §18 seam) | **MelodyScribe** | wiring id `melodyscribe` |
| The general pattern MelodyScribe is an instance of | micro-harness | `reference/micro-harnesses/` stays the folder name |
| A fine-tuned model | **MelodyScribe-{size}-v{version}** | `MelodyScribe-2B-v0.1`, `MelodyScribe-1B-v0.1`. Size is the base model class; version increments per training run that is promoted |
| The sandbox runtime the model runs in | MelodyScribe Scriptorium | `melodyscribe/scriptorium` |
| A model-written skill file (micro-only) | MelodyScribe Folio | `melodyscribe-folio-{slug}/SKILL.md`, loaded only inside the Scriptorium |
| The skills store as a whole | MelodyScribe Folios | `melodyscribe/folios/` |
| A store or table built specifically for MelodyScribe | MelodyScribe {store} | prefix `melodyscribe_` on tables, namespaces, and collections |
| The deterministic validator a write must pass | MelodyScribe Proof | `melodyscribe_proof` |
| The one human-authored skill the frontier model reads | **MelodyScribe skill** | `.claude/skills/melodyscribe/SKILL.md`; the model cannot write to this path |
| Seam tools | transcribe, file, recall, revise | `melodyscribe_transcribe`, `melodyscribe_file`, `melodyscribe_recall`, `melodyscribe_revise` |
| The frontier model used for distillation | teacher | plain word, no prefix |
| GSD artifacts (notes, seeds, spikes, todos) | — | slug `melodyscribe` |

Rules:

1. Anything purpose-built for MelodyScribe carries the MelodyScribe name so its origin is visible from the name alone.
2. Generic Databasise vocabulary (machine, modality, wiring, seam, rig, ledger, node, store) is not renamed. MelodyScribe is a wiring over those primitives, and its names sit beside them, not in place of them.
3. Model names carry size and version so the rig can compare `MelodyScribe-2B-v0.1` against `MelodyScribe-2B-v0.2` and against `MelodyScribe-1B-v0.1` without ambiguity.
