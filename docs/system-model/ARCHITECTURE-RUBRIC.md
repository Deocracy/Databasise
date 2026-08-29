# Component Goals — the Architecture Rubric

Ten properties every candidate architecture must give its components. The red team scores each architecture against these. Goals 1–6 make modalities cheap to try, 7–8 cheap to evolve, 9–10 trustworthy.

## Identity

1. **Single responsibility** — each component does one stage-sized job (extract, retrieve, rank, assemble, generate, grade, external-tool)
2. **Explicit contract** — plain-data in/out at every boundary, paradigm-neutral vocabulary (seeds/evidence, not entities/relations)
3. **Capability manifest** — declares what it implements and what machine primitives it requires; nothing assumed

## Interchange

4. **Swappable** — replaceable by any component honoring the same contract, without touching neighbours
5. **Composable** — wireable into declared graphs (loops and branches included), wrappable by stacking harnesses
6. **Artifact-shareable** — components on the same index recipe read each other's stored vectors/graphs; provenance tracked so compatibility is checkable

## Evolution

7. **Version-controlled — every part, as the improvement mechanism** (user-mandated, load-bearing):
   - **Every component is a versioned artifact.** Identity = `name@version`; a version is immutable once referenced. Two version axes: contract version (its boundary — breaking changes rev this) and behavior version (its internals — free to rev under a stable contract).
   - **Wirings pin versions.** A modality is a declared graph of `name@version` references, so a modality is itself reproducible and versionable; "the system as run yesterday" is reconstructable.
   - **Lineage is recorded.** Every new version names its parent and the change (human edit or machine mutation). Improvement history is a tree, not a pile.
   - **The improvement loop is a version operation:** branch a component → mutated version → A/B both versions in parallel wirings on the same corpus (same index recipe ⇒ near-zero extra cost for query-side components) → promote winner or roll back. Nothing is edited in place; rollback is re-pinning.
   - **Index recipes version too.** Stored artifacts carry `recipe@version` provenance; a part declares which recipe versions it can read, making artifact-sharing checkable rather than hoped.
   - **Traces name versions.** Every run records exactly which component versions produced it (goal 9 depends on this) — a quality regression is attributable to a version diff.
8. **Mutable** — a component (especially a query wiring) can be varied, budgeted, and A/B-run against its original; with goal 7, mutation = branch, never overwrite

## Accountability

9. **Observable** — every component emits its trace: what it consumed, produced, and spent (tokens/time), tagged with the component versions involved
10. **Budget-obedient** — the machine meters and can halt any component; no component owns its own loop limits

## Note for the candidate architectures

The five tension axes (SYNTHESIS.md §7) trade these goals against each other — e.g. a self-contained black-box part maximizes 4 but sacrifices 9, and per-component versioning (7) pulls toward the declared-graph side of tension 3, since graphs of `name@version` nodes are the representation that makes branch/A-B/promote cheap. Architectures must state their position honestly rather than claim all ten.
