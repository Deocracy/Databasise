# Wiring Spec & Validation

The blueprint for how the system is wired: format, identity, validation, arms, promotion. Full draft at `.planning/architectures/WIRING-SPEC-DRAFT.md`.

## Requirements

- Modality = index recipe × query wiring; a wiring is **data**, never code — swapping a modality is a registry operation, not a rebuild
- Universal core `ingest` + (`retrieve`|`answer`); all other capabilities declared and machine-enforced deny-by-default
- Instance identity closes over `(name@version, config_hash incl. environment hash, dependency_ids)`; recipe identity = SA-1, sub-recipe stamps = SA-2
- Static Mutation Validator (machine service #5) type-checks wirings and capabilities **before execution**, fails closed
- Improvement = branch → A/B → promote/rollback; promotion is a version operation, nothing edited in place
- Two-plane rule: wiring specs are artifact-plane data that may describe cycles; the executor owns runtime control flow

## How to Build It

### Format — JSON with no evaluation semantics

```json
{
  "wiring_version": "1",
  "nodes": {
    "chunk":    { "component": "recursive-chunker@1.2.0", "config": { "size": 1200 } },
    "embed":    { "component": "bge-m3@3.0.0", "config": { "batch": 32 }, "deps": ["chunk"] },
    "retrieve": { "component": "hybrid-retriever@1.0.0", "config": { "topK": 8 }, "deps": ["embed"] }
  },
  "recipe":     { "chunker": "chunk", "embedding": "embed" },
  "harnesses":  [ { "component": "crag@1.0.0", "config": { "max_rounds": 3 } } ],
  "provides":   ["retrieve"]
}
```

- **Node id is a position**, distinct from instance identity. Two nodes may share `component@version` with identical config — that is legitimate fan-out, and keying nodes by instance id silently drops one branch.
- **`deps` is a partial order over named nodes.** Topological sort (Kahn), ~30 lines. Not a total order by integer priority.
- **Component kind is a tagged sum**: single-key object, key selects kind, value validated by that kind's schema. Portable vocabulary — serde external tagging / pydantic discriminated unions / OpenAPI `discriminator`.
- **Harness order is explicit in the array**, never inferred from merge semantics.
- **Edge semantics are a named contract property** (added by spike 003): an edge means *exactly-once dataflow per run*, and whether fan-out branches execute concurrently is a **declared executor property**. Every static guarantee a declared-graph kernel has over a message-passing one turns out to rest on this, so it must be stated rather than inherited — and the A/A null must be calibrated under the same concurrency/determinism setting as the arms it judges.
- **Runtime-minted identity for planner-emitted plan nodes** (added by spike 003): `instance_hash = H(component_instance_hash, JCS(runtime_config), parent_instance_hash, ordinal)`. `config_hash` alone assumes an author, so ephemeral plan nodes have no identity without this.

### Identity — RFC 8785 over the input

`config_hash` = SHA-256 over the **author-supplied input JSON**, canonicalized by RFC 8785 (JCS). ~12 lines in the host language. Two pinned rules: no integers outside int64; the int/float distinction collapses (`1` ≡ `1.0`).

Artifacts (indexes, not wirings) use a NAR-style hash over the artifact tree — the serialization format only, no store.

### Validation — all violations at once

Checks: components resolve · socket types line up per edge · capabilities declared for everything exercised · dependencies resolve · `provides` satisfied · no dangling deps.

Three non-negotiable properties:

1. **Every violation returned in one pass, each with a JSON-Pointer path.** One-error-per-run costs an LLM repair round trip per defect; round trips dominate, not the 22 ms.
2. **Cycle detection returns node names as data**, never an exception — cyclic wirings are legal (CRAG loops), so only *unintended* cycles are rejected, and they must be reportable.
3. **Removal errors on a missing target.** RFC 6902 `remove` has this; silent-no-op mechanisms do not.

Implementation is a build-phase choice — bespoke (JSON Schema + graph validator), `lib.evalModules`, or CUE. The contract specifies behavior only, so all three work.

### Arms and promotion

- Arm = base wiring + **RFC 7386 merge-patch for additive/overriding deltas**, plus **RFC 6902 for any subtractive operation**; a differing kind tag **replaces** the whole `kind` subtree
  > **AMENDED by spike 003.** The earlier form — 7386 alone, with fail-closed subtraction — is **unsatisfiable**: RFC 7386 expresses removal as a `null` sentinel, so an unknown or mistyped key is a silent no-op *by construction* and can never error. Only RFC 6902 `remove` (or an explicitly fail-closed equivalent) supplies the property. All four spike-003 variant documents restated the unsatisfiable form before it was caught.
- Validate each arm independently **and** the base with no arms applied
- Promote = **atomic alias repoint** (~1 ms, `rename(2)`), never a build
- **Ledger is the durable record; the active pointer is a projection derivable from it.** Running an arm SHALL NOT append to the ledger — evaluation is not a decision
- Verb ladder: `check | preview | run | promote-next | promote-now`, one gate implementation parameterized by verb

## What to Avoid

- **Never make the wiring format a program.** A Nix-authored spec was measured executing arbitrary code via `imports` and disabling its own validator via `disabledModules`. Whatever the format can compute, the validator must sandbox.
- **Never hash a tool's normalized output as `config_hash`.** Adding one defaulted option re-hashed every wiring with byte-identical input, destroying in-flight A/B baselines. Nix's JSON printer also diverges from JCS on 4 of 7 test values.
- **Never key nodes by instance identity** — fan-out with identical instances silently loses branches.
- **Never order sockets by integer priority.** Socket wiring is a partial order; priority-sorted merges also leak loader state (definition order is the *reverse* of module-list order) into any hash over the result.
- **Never use a type union that dispatches on a shallow structural check** — it picks the first matching branch and every per-kind check evaporates.
- **Never let an unknown key be a silent no-op** in a subtractive operation. Measured: a one-character typo shipped an arm with the component it claimed to have removed.
- **If using `evalModules`**: JSON enters wrapped as `imports = [ { config = <json>; } ]`; assertions are data and the validator must filter and throw itself; force all four surfaces (thunks, assertions, non-emitted options, freeform buckets, override-filtered definitions); fork per wiring with an exit-code verdict; no root `freeformType`; `_module.check` stays true; `import <nixpkgs/lib>` only; external `MemoryMax`/`RuntimeMaxSec` because Nix has none.
- **Schema generation from module options is a dead end in every ecosystem** — regex constraints and cross-field rules are unexportable. Direction is contract → schema → renderer, never module → schema.

## Constraints

- Validator cost: 22 ms in-process, **~210 ms wall clock** per `nix-instantiate` invocation. CUE: 5 ms in-place on plain JSON.
- JSON Schema 2020-12 **cannot** express cross-field rules (dtype at the far end of an edge) — the shape/graph split is forced, not chosen.
- CUE unification is commutative → exactly one override level. Irrelevant if arm overlays are merge-patch applied outside the language.
- Nix has no evaluation timeout and no memory cap; `max-call-depth` catches non-productive recursion only.
- Artifact hashing: ~1.3 GB/s hash-only; ~284 MB/s if also copied into a store.

## Origin

Synthesized from spike 004 (Q1–Q10), with the contract clauses and machine services from spike 002.
Source files in `sources/004-nix-leverage/` — includes NIX-LEVERAGE.md, the full 8-family sweep, and the working `modtest/` validator prototype.
