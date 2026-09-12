---
spike: 001
idea: melodyscribe
name: score-io-model
type: standard
validates: "Given a Score with directives, when compiled, then every section maps to a deterministic token plan and every model output to a typed op with no ambiguous case"
verdict: VALIDATED
related: []
tags: [score, compiler, schema, grammar]
---

# Spike 001: score-io-model

## What This Validates
Given a Score with directives, when compiled, then every section maps to a deterministic token plan and every model output to a typed op with no ambiguous case

## Research
Docs read, in order: `.planning/spikes/MANIFEST.md`, `SCORE-IO-SPEC.md` + `ops.schema.json`,
`reference/micro-harnesses/README.md` (esp. `score-format-and-cache.md`'s directive table,
`runtime-one-pass.md`'s grammar-constrained op list, and the unresolved ledger's warning that
no vendor number settles anything).

Approaches compared:
1. **XML for the Score wire format** (chosen): the spec's §3 example is already XML; Python's
   `xml.etree` gives entity unescaping and malformed-input rejection for free, and nested-markup
   refusal is one check (`len(el) != 0`). A custom line format would re-implement all of this.
2. **Vendored stdlib validator vs `jsonschema`** (vendored mirror chosen): the venv had no
   packages installed, and Proof needs content-aware checks (evidence spans, slug registry)
   that JSON Schema cannot express anyway. `ops_validate.py` mirrors every `ops.schema.json`
   constraint field-for-field, and `test_spike.py` re-reads the schema file from disk and
   asserts the mapping (`mirror.*` checks), so drift between the two is caught mechanically.
3. **Real tokenizer vs word-level stand-in** (stand-in chosen, honestly bounded): real token ids
   are per-model and owned by spike 002. The plan structure — ordered steps, named sequences,
   appended token strings, read positions, grammars, caps — is tokenizer-independent, and that
   is what this spike validates. `score.py` records `TOKENIZER_VERSION = "toy-word-v1"` in every
   plan; byte-identity claims (I1) are over the plan's token strings, and spike 002 re-runs them
   against real ids.

## How to Run
```
.planning/spikes/001-score-io-model/run.sh
```
One script reproduces everything: the 95-check Python suite (stdlib only, run on
`.planning/spikes/.venv/bin/python` with `LD_LIBRARY_PATH=/run/opengl-driver/lib`),
`node --check` on the demo page's embedded JS, and a stubbed-DOM smoke test of the demo's
`proveOp`/tokenizer. No model, no GPU, no GPU lock (nothing here loads a model).
Per-check JSON lines with ISO timestamps land in `logs/run-<utc>.jsonl`.

## What to Expect
- `95/95 checks passed`, `node --check: syntax OK`, six `ok` demo smoke lines, `SPIKE-001 ALL GREEN`.
- Open `demo.html` from disk (no server): paste a Score, compile to a colour-coded token plan,
  paste a model output, run Proof per op.
- Runtime: seconds.

## Investigation Trail
1. **Survey.** Spike folder held only the spec, schema, and stub README. Shared venv existed
   but empty (no `llama_cpp`/`jsonschema`, no `pip`, no models) — fine: this spike's contract
   (compiler, schema, grammar text, Proof) needs none of them. System `node v24` available for
   the demo check. Corpus loads through `databasise/parity/corpus.py`.
2. **Built `score.py`.** Parse (closed attribute/value sets, refusal on anything unknown) +
   compile (append / copy_prefix / read_vector / free / decode steps with grammars and caps).
   First structural finding while coding: exact S0 positions are unknowable past a decode step
   (generated count only bounded by cap), so reads/appends carry `pos_kind: exact|cap_relative`
   and the runtime resolves the latter. Recorded as a handoff note for spike 002, not hidden.
3. **Built `ops_validate.py` + `grammar.py`.** Second finding: GBNF cannot count, so length caps
   (512/4096/32) live in Proof, never in the grammar — this is the spec's format-vs-accuracy
   split made mechanical, with a dedicated `split.*` test asserting a 513-char subject is
   shape-admissible but Proof-rejected.
4. **Corpus import failed** (`databasise/__init__` pulls `rfc8785`, absent from the venv).
   Rather than install packages for a stdlib-only spike, `test_spike.py` path-loads `corpus.py`
   (stdlib-only, hash-verifying) via importlib — plus a `sys.modules` registration the first
   attempt missed (dataclasses needs it). Lesson recorded: spikes stay decoupled from the
   package import chain.
5. **First run: 74/91.** Three distinct bugs, all in test/checker code, none in the contract:
   (a) the GBNF well-formedness checker counted parens inside `[...]` classes containing a bare
   `"` — fixed by stripping classes before literals; (b) my I3 forbidden-vocabulary list
   collided with the test's own content (which legitimately contains `<section` unescaped from
   `&lt;`) — fixed by testing instruction-vocabulary absence + content preservation, with the
   exact-shape check (`E_i == prefix+content+[EMB]`) carrying the real I3 weight; (c) subset
   count 15 vs 16 — `any` is an alias for the full set, already enumerated; expectation fixed.
6. **Depth pass.** Strengthened I2 to cover all three decode kinds (ops/text/rewrite) with
   generated tokens keyed per section; added direct assertions for read `form` values
   (`isolated`/`context`/`rewrite:propositions`), I5 uniqueness over a 4-read mixed score, and
   `pos_kind` exact-vs-cap-relative partitioning. 95/95.
7. **Demo page.** Single-file `demo.html`, no framework. Verified by `node --check` plus a
   stubbed-DOM smoke test of the pure functions (tokenizer parity with Python asserted
   byte-for-byte). The demo is labelled in-page as a display mirror; the Python suite is
   normative. XML parsing path in the demo relies on the browser DOMParser (unverifiable
   headless here) — stated openly, not asserted.

## Results
**Verdict: VALIDATED.** Every section of a Score maps to a deterministic token plan
(identical plan JSON across compiles; byte-identical `E_i` token lists for a section at
position 1 vs 4 with different neighbours), and every model output maps to a typed op with
no ambiguous case (closed directive sets refused at compile; 15/15 grammar subsets restrict
targets both ways; 9/9 seeded fuzz mutations refused; Proof catches fabricated spans and
mistyped dates, passes correct ops and `{"ops": []}`).

Head-to-head / counts (from `logs/run-20260912T072728Z.jsonl` via `run.sh`):
- 95/95 checks pass: 24 compile-refusal cases, I1 + determinism, I2 (3 decode kinds),
  I3 (exact shape + vocabulary), 15 grammar subsets × (well-formed + restricted + allowed-pass
  + disallowed-refused), 9 fuzz mutations, Proof correct/empty/fabricated/mistyped,
  11 value-type cases, evidence boundary/normalisation cases, folio slug lifecycle
  (first/dup/supersedes), permission cases, 32-vs-33 ops, schema-mirror cases, spec §8
  worked-example step sequence and caps.
- Grammar split confirmed: 0 length constraints in any grammar; 100% of over-long-string
  cases refused by Proof.
- Grounding: all section contents are real paragraphs from the 20 hash-verified parity
  documents; all evidence spans computed against that text.

Surprises and handoffs for later spikes:
- **002** must resolve `cap_relative` read positions at runtime (plan marks them; exact
  indices need the decoded count) and re-run I1 against real tokenizer ids; the toy
  tokenizer version string to replace is `toy-word-v1`.
- Spec-implementation choices needing owner review (all recorded in code + tests):
  `provenance` attribute (`chunker|frontier`, `model` refused); `file` duplicates and
  `any`-with-others are compile errors; post-decode positions are cap-relative.
- Demo XML-parse path verified by review only (no headless browser here); Python suite
  is the normative artifact.
