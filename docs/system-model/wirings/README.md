# Wirings directory — illustrative only

Every file in this directory is illustrative only and is not a registered wiring — the same register `CONTRACT.md §1`'s own worked example uses at line 186 ("Illustrative only, not a registered wiring — the worked example below uses the conforming component names from `### §0.5`"). `PARTS.md`'s tagged entries govern node sets, capabilities, artifact scopes, admission verdicts, port costs and repairs; the files here are evidence those entries cite, never governing, per `PARTS.md`'s own preamble clause (b) and `CONTEXT D-04`. [docs-verified] [CONTRACT §1] [CONTEXT D-04]

Each individual file additionally carries its own status line, at the top of the file, stating the same fact locally so a reader who lands on one file directly — without having read this README first — still finds the rule in place.

## Naming convention

Plans 03-05 and 03-06 populate this directory following one convention:

- **LightRAG** — one base wiring, `lightrag-base.json`, plus one arm-delta file per mode: `lightrag-arm-<mode>.patch.json` for an RFC 7386 merge-patch (additive or overriding changes) or `lightrag-arm-<mode>.json-patch.json` for an RFC 6902 JSON-Patch (any subtractive change — merge-patch alone cannot fail-close a removal, per `CONTRACT.md §1`). Per `CONTEXT D-05`, this is one wiring family — a base plus patches — not per-mode fragments; the arm mechanism is the thing worth illustrating, since the PARTS-01 verdict turns on it.
- **HippoRAG 2** — one base wiring, `hipporag-base.json`, with no arm files, per `03-RESEARCH.md §H.5`.
- **codebase-memory-mcp** — deliberately has no file here. Its stress exercise is the eleven `CONTRACT.md §8` admission verdicts, not topology; a whole-engine opaque node has no wiring internals worth illustrating as JSON, per `CONTEXT D-04`.

## Why illustrative, not normative

A governing JSON file would have no position for a claim tag, a trace tag, or an `unresolved — <question>` marker, and `CONTRACT.md §2`'s undeclared-is-denied rule would turn every JSON omission into a normative denial rather than an open question. At most three of `ANATOMY.md ## §F`'s twelve DR rows are wiring-shaped at all — most of this phase's content is necessarily prose. `CONTEXT D-06` records the kill condition that would narrow this rule: a *structural* defect in `CONTRACT.md §1`'s five top-level members, surfaced by actually serialising a real wiring, that the prose entry demonstrably could not express. A vocabulary gap alone does not fire it. [docs-verified] [CONTEXT D-04] [CONTEXT D-06]
