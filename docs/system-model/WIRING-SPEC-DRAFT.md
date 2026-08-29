---
title: Wiring Spec — draft design
status: superseded — this draft's own "feeds step 8 (fitting contract spec)" is discharged by CONTRACT.md; tracked at SYSTEM-MODEL.md ## §ST
date: 2026-08-10
derives_from: spike 004 (Q1–Q10), spike 002 (five contract clauses, six machine services), two-plane note
independent_of: spike 003's D-variant selection — nothing here depends on which variant wins
---

# Wiring Spec — Draft Design

How the system is wired: the format, the identity, the validation, the arm mechanics, the promotion.

Everything here is settled by spike 004's evidence and does **not** depend on which D-variant spike 003 selects. It is the pre-drafted portion of step 8's fitting contract. What is deliberately *not* here: the component capability vocabulary and the socket type system, which are step 8's own work.

## 0. The one-paragraph version

A modality is a wiring. A wiring is a JSON document naming component instances, how their sockets connect, the index recipe, and the harness stack. It is data, never code. The machine validates it before execution — all violations at once — then executes it. Improvement is a merge-patch producing a new wiring, A/B'd against the incumbent, promoted by repointing an alias. Adding a modality is writing a wiring; adding software is a Nix rebuild. Those two paths never cross.

---

## 1. Format: JSON, and why not the alternatives

**Wirings are JSON.** Not Nix, not YAML-with-anchors, not a DSL.

The decisive evidence is spike 004 Q10: a Nix-authored spec is not merely no better, it is strictly worse in three measured ways — `imports` executes arbitrary Nix during validation, `disabledModules` deletes the validator's own checks, and Nix has no evaluation timeout or memory cap. A wiring is untrusted input whenever a mutation operator authors it, and an untrusted input must not be a program.

The general rule this instantiates: **the wiring format must have no evaluation semantics.** Anything the format can *compute* is something the validator must sandbox. JSON's poverty is the feature.

Consequences to hold onto:

- The mutation operator emits JSON. It never emits Nix, and never emits code in any language that the validator will evaluate.
- Component authors write component code (Nix-packaged software); they do not write wiring syntax.
- Any tool used to validate — including `lib.evalModules` — consumes JSON at its boundary and never lets wiring keys become that tool's keywords. If evalModules is the implementation, JSON enters only as `imports = [ { config = <json>; } ]`, never `imports = [ <json> ]`.

## 2. What a wiring declares

```json
{
  "wiring_version": "1",
  "nodes": {
    "chunk":   { "component": "recursive-chunker@1.2.0", "config": { "size": 1200, "overlap": 120 } },
    "embed":   { "component": "bge-m3@3.0.0", "config": { "batch": 32 }, "deps": ["chunk"] },
    "graph":   { "component": "lightrag-extractor@1.5.4", "config": {}, "deps": ["chunk"] },
    "retrieve":{ "component": "hybrid-retriever@1.0.0", "config": { "topK": 8 }, "deps": ["embed", "graph"] }
  },
  "recipe": { "chunker": "chunk", "extraction": "graph", "embedding": "embed" },
  "harnesses": [ { "component": "crag@1.0.0", "config": { "max_rounds": 3 } } ],
  "provides": ["retrieve"]
}
```

Five parts, each load-bearing:

1. **`nodes`** — a map of **node id → instance**. The node id is a *position in this wiring*, deliberately distinct from the component instance identity. Two nodes may use the same `component@version` with different configs, or with identical configs (legitimate fan-out). Keying nodes by instance identity silently deduplicates that fan-out — verified in the sweep, where the module system's `genericClosure` dropped a branch with no error.
2. **`deps`** — a **partial order over named nodes**, not a total order by priority. This was the sweep's own early mistake, caught by the completeness critic: socket wiring is a DAG of named dependencies, and NixOS itself models exactly this with per-node `deps` plus a topological closure, as does home-manager's `dagOf`.
3. **`recipe`** — which nodes constitute the index recipe, so SA-1 (recipe identity) and SA-2 (sub-recipe stamps for chunker / extraction / embedding) have a declared source. This is what makes artifact sharing across wirings decidable.
4. **`harnesses`** — the stacked strategy tier, ordered, wrapping the modality. Order is explicit in the array; it is never inferred from merge semantics.
5. **`provides`** — the universal-core claim. A wiring must provide `retrieve` or `answer` or it is not a usable modality.

**Component kind is a tagged sum** where kind-specific schemas apply: a single-key object whose key selects the kind and whose value is validated by that kind's own socket schema. Stated in portable vocabulary — serde external tagging, pydantic discriminated unions, OpenAPI `discriminator` — never as a Nix type. The reason is a measured trap: type systems that dispatch on a *shallow* structural check (Nix's `either`/`oneOf`, and the same class of bug elsewhere) silently pick the first matching branch and evaporate every per-kind check.

## 3. Identity

**`config_hash` = SHA-256 over the author-supplied input JSON, canonicalized by RFC 8785 (JSON Canonicalization Scheme)** — or an explicitly specified variant, named in the contract.

Never hash a tool's normalized output. Spike 004 measured what goes wrong: adding a single option with a default re-hashed every existing wiring despite byte-identical input, destroying in-flight A/B baselines; and Nix's JSON printer diverges from JCS on four of seven test values, hashing `{"tau":1}` and `{"tau":1.0}` differently. The canonical form must be specified in prose plus a named standard and implemented in ~12 lines of the machine's own language. Nix must not appear in the identity path — that is what keeps the contract implementable without it.

Two rules pinned to the canonicalization:

- No integers outside int64.
- The int/float distinction collapses. `1` and `1.0` are the same value.

Layered on top, unchanged from spike 002:

- Instance identity closes over `(name@version, config_hash, dependency_ids)`, where `config_hash` includes the **environment hash** — a build/runtime environment digest. Where a component is Nix-built, its derivation hash is a convenient source for that field; the requirement stands on its own (it exists to kill Feast-style version skew) and names no tool.
- The wiring spec is itself a versioned, content-addressed artifact in the registry, hashed the same way.
- Every trace names the instance hashes that produced it.

Directory-shaped **artifacts** (indexes, not wirings) use a NAR-style hash over the artifact tree — the serialization format adopted from Nix, with no Nix store involvement, obtainable at ~1.3 GB/s.

## 4. Validation — machine service #5

Runs **before execution**, on every wiring, including ones a mutation operator generated seconds ago. Fails closed.

### What it checks

1. Every node's `component@version` resolves in the registry
2. Socket types line up across every `deps` edge
3. Every capability the wiring exercises is declared by the component that must provide it — deny-by-default, undeclared is denied and not warned
4. Component dependency constraints resolve within this wiring
5. `provides` is satisfied — at least one of `retrieve` | `answer`
6. Structural integrity — no dangling deps, no missing required inputs, no unresolvable recipe references

### Three properties that are not negotiable

**All violations at once, each with a JSON-Pointer path.** Not the first violation. The measured reason: one-error-per-run costs an LLM repair round trip *per defect*, and round trips dominate — three simultaneous socket violations produced one error from a module-system pass and three from a schema pass. The 22 ms of evaluation is noise next to a wasted model call.

**Cycle detection returns the offending node names as data, never an exception.** A wiring is permitted to describe cycles — the two-plane rule says so explicitly, since a CRAG-style retry loop is a legal modality. What must be rejected is an *unintended* cycle, reported as `{cycle: [...]}`, not as an interpreter crash. Mechanisms that convert a cycle into an uncatchable stack overflow (Nix's `lib.fix` and `callPackage` both do) are disqualified as implementations for exactly this reason.

**Removal is fail-closed by specification.** An operation that deletes a node or a key must error if the target does not exist. RFC 6902 `remove` has this property; subtractive mechanisms that treat an unknown key as a silent no-op do not — measured in the sweep, where a one-character typo produced an arm that reported "reranker dropped" and shipped with the reranker still in it.

### Implementation: two candidates, contract-neutral

The contract specifies the **behavior** above. The implementation is a build-phase choice between:

- **A bespoke validator** — JSON Schema 2020-12 for shape plus a graph validator in the machine's host language. Maximum portability. The split is forced rather than chosen: JSON Schema cannot express cross-field rules like "the dtype of the socket at the far end of this edge must match".
- **`lib.evalModules`** — proven working (typed sockets, capability enums, fail-closed graph checks, arm overlay, 22 ms in-process / ~210 ms wall clock per invocation) with the hardening rules below.
- **CUE** — measured at 5 ms validating plain JSON in place, expresses the cross-field rules natively, and has no lazy-checking hole. Its limitation is exactly one override level, which matters only if arm overlays were done in-language; done outside as merge-patch (§5), the limitation disappears.

If `evalModules` is chosen, these are mandatory and each was found the hard way:

- JSON enters wrapped: `imports = [ { config = <json>; } ]`
- Force all four surfaces: option thunks, assertions, options excluded from the emit, freeform buckets, override-filtered definitions
- Assertions are data — the validator filters for `assertion == false` and throws itself; the module system does not do this
- Fork per wiring with an exit-code verdict; `tryEval` returns one bit and cannot contain five failure classes that would otherwise destroy an entire batch's verdicts
- Validate each arm independently **and** the base with no arms applied — an arm's override is filtered *before* type checking, so it silently masks base type errors
- No root `freeformType`; `_module.check` stays true; no lazy attribute types; no path types; `import <nixpkgs/lib>` only
- External resource limits (`MemoryMax`, `RuntimeMaxSec`) — Nix provides none

## 5. Arms, deltas, and the A/B cycle

**An arm is a base wiring plus an RFC 7386 merge-patch** (or RFC 6902 for operation-level precision). One documented exception: a differing component-kind tag **replaces** the whole `kind` subtree rather than merging into it — otherwise a kind swap leaves orphaned fields from the previous kind.

The cycle:

1. **Branch** — mutation operator emits a merge-patch against the incumbent wiring
2. **Validate** — patch applied, resulting wiring validated in full; the base independently re-validated
3. **Run** — each arm executes under the machine's budget, against the versioned eval bundle
4. **Gate** — promotion gate decides: A/A null, paired significance, confirmation rule, hard-gate regression suite
5. **Promote or discard** — promotion is an alias repoint

Every arm's evidence records the instance hashes that produced it, and the evidence-depth tier, so cross-regime comparisons can never silently mix quality levels.

## 6. Promotion

**Promote = atomic alias repoint.** A `rename(2)` over a symlink or its equivalent: measured at ~1 ms, atomic by the filesystem, switching a whole set of artifacts at once. Never a build.

**Ledger and projection are separate.** The promotion ledger is the durable, append-only, ordered record of decisions. The active-wiring pointer is a *projection* — derivable from the ledger, regenerated rather than independently maintained. Crash-safety falls out of this for free: if the pointer and the ledger disagree, the ledger wins.

**Running an arm SHALL NOT append to the promotion ledger.** Evaluation is not a decision. This is the rule that keeps the ledger a record of what was *chosen* rather than a log of what was *tried*.

**Verb ladder**, borrowed wholesale from NixOS's activation vocabulary, with no Nix content:

| Verb | Meaning |
|---|---|
| `check` | validate only, nothing runs |
| `preview` | show what would change, including the closure diff against the incumbent |
| `run` | execute without promoting — the A/B arm verb |
| `promote-next` | becomes active at next restart |
| `promote-now` | becomes active immediately |

One gate implementation serves every transition; the verb is a parameter to it.

## 7. The two-plane rule, restated where it bites

The wiring spec is **artifact-plane data** that may *describe* a cyclic execution graph. That is not a contradiction: the cycles live inside the value, not in the dependency edges between artifacts, so a cyclic wiring is fully content-addressable.

- The **executor** owns runtime decisions: how many loop iterations, which branch, what a planner emits.
- The **artifact plane** records: specs, traces, lineage. Every completed run's trace is an unrolled DAG naming instance hashes.
- No component may treat the artifact plane as a runtime control channel.

## 8. What is not decided here

- The component capability vocabulary and socket type system — step 8's own deliverable
- Which D-variant's kernel hosts the executor — spike 003
- Whether the validator is bespoke, `evalModules`, or CUE — build phase, and the contract is written so all three work
- The eval bundle's internal format and the promotion gate's statistical parameters — step 10

## 9. Verification status

Settled on measured evidence: format choice, identity/canonicalization, promotion mechanics, validator hardening rules, arm-delta semantics. All [code-verified] in spike 004, most through dedicated adversarial refutation.

Provisional, single-pass evidence only: the validator pipeline shape and the assertion-channel discipline, the DAG-valued `deps` pattern, and the CUE / JSON-Schema / Nickel comparison. Each was measured on host `legion` but none survived a dedicated refutation pass. The two most load-bearing — the validator pipeline and the assertion channel — deserve one before the build plan commits, specifically to test whether the violation channel stays complete under schema evolution.
