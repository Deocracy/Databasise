---
spike: 004
name: nix-leverage
type: research
validates: "Given the six self-improvement machine services and five contract clauses, when Nix's mechanisms (store, derivations, build sandbox, profiles/generations, flakes) are evaluated docs-verified against each, then Nix either thins a named service or hardens a named clause at acceptable coupling cost — or is ruled deployment-only and exits the architecture model"
verdict: VALIDATED (deployment-only — amended: evalModules proven as Static Mutation Validator implementation candidate; store/derivations/identity conclusions unchanged)
related: [002, 003]
tags: [nix, nixos, versioning, isolation, content-addressing, research]
---

# Spike 004: Nix Leverage — does Nix belong in the model, or only under it?

Side research spike. Its verdict feeds the **D3 "Nix Unit"** variant in spike 003 and the step 8 fitting contract.

## What This Validates

Given the six machine services and five contract clauses, when Nix's mechanisms are evaluated [docs-verified] against each, then Nix either thins a named service or hardens a named clause at acceptable coupling cost — or is ruled deployment-only and exits the architecture model.

## Why the question exists

The system model needs content-addressed identity, immutable versioned artifacts, dependency-closure hashing, deny-by-default isolation, and atomic promote/rollback. Nix implements all five for software builds, and Sourcerer v2.0's substrate is NixOS. Either we reuse that machinery or we reimplement it; this spike decides which, before D3 is drafted.

## Decision rule (fixed before research — do not revise mid-spike)

Nix enters the **architecture model** only if it:

- **(a)** replaces or substantially thins a named machine service — candidates: isolation domain (#2), artifact ownership + store (#3), identity hashing (SA-1 / contract clause 2); **or**
- **(b)** hardens a contract clause at no design cost (environment hash inside instance identity).

Otherwise the verdict is **deployment-only**: NixOS hosts Sourcerer, sandbox parts run as systemd units, Nix is excluded from design documents until the build phase. This is a valid outcome, not a failure.

**Standing disqualifier:** if adoption would leave the system carrying *two* identity vocabularies (Q8), that is a strike against adoption regardless of how the other questions land — "every trace names the component versions" must have exactly one answer.

The verdict must name which mechanism, if any, is adopted, and at which point in the lifecycle it applies.

## Research questions (all answers [docs-verified] against the Nix manual, RFCs, and NixOS options)

Revised from the pre-003 draft: one question cut (`flake.lock` overlap — predictable answer, folded into Q3), one reframed (store cost → store residency), one split (isolation, which conflated build-time and runtime), three added (Q6–Q8, which probe the coupling cost the decision rule assumes but never measured).

1. **Impure artifacts.** Can externally produced, LLM-nondeterministic artifacts be registered content-addressed after the fact (`nix store add` / fixed-output derivation semantics)? This is make-or-break: index artifacts cannot be pure derivations.
2. **Store residency.** Does anything *force* artifacts into `/nix/store`, or can the store hold hashes and manifests only, with GB-scale artifacts in dedicated stores? (Tests PRIOR-ART's adopt: "Nix content-addressing at promotion only.")
3. **Experimental-feature dependency.** Do `ca-derivations` or dynamic derivations gate any adoption path, and what is their current stability status? *Footnote:* does `flake.lock` overlap registry version pinning, or pin a different thing (input revisions vs resolved-config content)?
4. **Isolation, split in two:**
   - **(a)** Is the Nix *build* sandbox usable for runtime isolation of a sandbox-regime part, or is it build-time only?
   - **(b)** Does declarative systemd unit hardening satisfy machine service #2 (deny-by-default net/FS/store-write, wall-clock watchdog, per-arm process)? A "yes" here is a **substrate** finding, not a Nix-in-the-model finding, and must be labelled as such.
5. **Promotion.** Do profiles/generations give atomic multi-artifact repoint with rollback for a *non-root* service? (PRIOR-ART already adopts "promote = repoint a mutable alias"; this asks whether Nix is the thing doing the repointing.)
6. **Coupling cost.** If a mutation operator authors a new sandbox part, can it reach the store and run without a human writing a derivation? This is the question most likely to produce a "no."
7. **Mutation-loop latency.** If promotion is a Nix build, what is the wall-clock cost of one branch → A/B → promote cycle? Minutes per mutation is a design constraint on the self-improvement loop, not an ops detail.
8. **One identity or two.** Does a Nix output hash *replace* SA-1's recipe hash, or would the system maintain two identity systems side by side? See standing disqualifier.
9. **Module system (amendment, added after the initial verdict).** Can `lib.evalModules` — Nix's actual composition layer, which the original question set missed — serve as the wiring/swap layer: typed component slots, capability enforcement, swap-by-override? And what else does the module system offer (containers, generated units, docs, tests)?
10. **Exhaustive mechanism sweep (second amendment).** Q9 asked whether Nix can validate a JSON wiring. Q10 asks the different question: is there any Nix mechanism — across all families, not just the module system — that makes things easier if the wiring spec were **authored or stored as Nix** rather than JSON?

## Established context (from exploration 2026-08-10, do not re-derive)

- Derivation identity = content hash of resolved inputs = SA-1's formula; dependency closure = contract clause 2; incremental invalidation = SA-2; profiles/generations = promote-by-repoint [inference, to verify]
- Nix graphs are build-time DAGs — correct shape for the artifact/lineage plane, never the executor (see `.planning/notes/two-plane-separation.md`)
- LLM non-determinism means index artifacts cannot be pure derivations; the workaround is content-address registration after the fact — SA-1 already separates recipe identity (input hash) from artifact identity (content hash + provenance)
- **Environment hash in instance identity is already settled** and does not depend on this spike's verdict — it is justified independently by the Feast version-skew failure in PRIOR-ART's avoid list. Nix is one possible *source* of that hash, not its justification.

## Method

Inline, no subagents (user directive for this session). Primary sources: the `nixos` MCP (live search.nixos.org / nix.dev / NixOS wiki / option data) plus direct fetches of the Nix manual and relevant RFCs. Every claim carries a tag; nothing is answered from model memory.

## Landing pad

`.planning/research/NIX-LEVERAGE.md` — adopt/avoid table (PRIOR-ART format) + role verdict: substrate-only / environment-pinning / identity-layer.

## What to Expect

Adopt/avoid table + role verdict. No code: if Nix is adopted, "one promotion executed as a profile switch" joins step 12's code-spike list.

## How to Run

The latency measurement (Q7) is reproducible:

```bash
cd .planning/spikes/004-nix-leverage
head -c 268435456 /dev/urandom > blob.bin && sync && bash bench.sh && rm -f blob.bin
```

Requires Nix with `nix-command` enabled. Adds one 256 MB path to `/nix/store` and deletes it at the end.

## Investigation Trail

- 2026-08-10: Spike defined during pre-003 exploration; committed then reverted with the rest of that exploration capture
- 2026-08-10 (this session): redefined from scratch. Question set revised — 1 cut, 1 reframed, 1 split, 3 added. Standing disqualifier on dual identity added. Execution changed from background subagents to inline.
- 2026-08-10: Q1/Q3/Q5/Q8 answered [docs-verified] against the Nix 2.34 manual; Q4b against NixOS option data. Q2 turned on a fact the original framing missed — `nix hash path` yields the same NAR content address with zero store residency, which removes most of the reason to adopt the store.
- 2026-08-10: Q7 escalated from inference to measurement (`bench.sh`, 256 MB artifact on host `legion`): hash-only 192 ms, store-add 901 ms, identical re-add 204 ms (dedup, no copy), alias repoint 1.38 ms. Latency is not the constraint.
- 2026-08-10: Q8 fired the standing disqualifier — the store path digest closes over the store directory and the artifact name, so it is not SA-1 and adopting it would create a second identity vocabulary.
- 2026-08-10 (second amendment, Q10): User asked whether a Nix trick exists that we had not considered, if the wiring spec were built into Nix. 8 mechanism families swept in parallel, 107 candidates, the 16 strongest adversarially refuted (25 agents, ~947k tokens; a host crash mid-run cost nothing — the sweep resumed from cache). Answer: no. 15 of 16 rejected, 1 conditional. Three mechanisms found that make a Nix-authored spec actively *worse* than JSON: `imports` executes arbitrary Nix during validation, `disabledModules` disables the validator itself, and Nix has no eval timeout or memory cap. The sweep also **corrected several Q9 claims** — see Results. Full analysis in `.planning/research/NIX-LEVERAGE.md` §Q10.
- 2026-08-10 (amendment): User challenge surfaced a decomposition gap — the question set covered the store, derivations, sandbox, profiles, and flakes, but never the NixOS module system, Nix's actual composition layer. Q9 added and answered: docs pass (NixOS 26.05 manual, nix.dev deep dive), then a working prototype (`modtest/`) — a miniature fitting contract as an `evalModules` module, standalone, no NixOS. All six tests pass: JSON-authored wirings, typed sockets, capability enum enforcement, fail-closed graph assertions, swap via overlay + `mkForce`, 22 ms per cold validation. One caveat found in testing: checking is lazy, so the validator must force the full config or violations pass silently.

## Results

**Verdict: VALIDATED — DEPLOYMENT-ONLY.** The spike's question is answered, and the answer is that Nix exits the architecture model. Full analysis in `.planning/research/NIX-LEVERAGE.md`.

Against the decision rule fixed before research:

- **(a) Thins a named machine service?** No. Isolation domain (#2) — the Nix build sandbox is build-time only; runtime confinement is systemd, a substrate finding. Artifact store (#3) — the store costs a full copy per distinct artifact (~4.7× the hash-only time plus 100% of its size) and its content address is obtainable without it. Identity hashing (SA-1) — the store path is not SA-1's hash.
- **(b) Hardens a clause at no design cost?** No. The environment hash was already settled on independent grounds; Nix is one convenient source for that field, not its justification.
- **Standing disqualifier:** fired (Q8, dual identity vocabulary).

Two carve-outs survived the initial research: NAR hashing as a hash *format* for directory-shaped artifacts (usable with no store and therefore no coupling), and NixOS systemd confinement as the substrate implementation of machine service #2.

**Amendment (Q9, same day): a third carve-out, and the largest.** The module system — unexamined in the initial pass — partially fires decision rule (a): `lib.evalModules` substantially thins machine service #5 (Static Mutation Validator). Proven with a working prototype (`modtest/`): standalone evaluation with only nixpkgs `lib`; wirings authored as **JSON** so component authors and the mutation operator never write Nix (dissolving Q6's coupling cost on this path); typed sockets via option types; capability manifests as enums enforced at eval; graph preconditions as fail-closed assertions (contract clause 1's shape); **swap = JSON overlay + `mkForce`** with full revalidation; 22 ms per cold validation. Layered merge priorities (`mkDefault`/`mkForce`/`mkOverride N`) express base wiring + experiment overlay + per-arm override — the branch → A/B arm mechanic — declaratively, which JSON Schema cannot.

**Q10 (second amendment) corrects three Q9 claims.** Recorded here because they were committed before the sweep ran, all [code-verified]:

1. **"Graph preconditions as fail-closed `assertions`" is false as stated.** A failed assertion evaluates *successfully* to `{assertion = false; message = "…";}` — `deepSeq` walks past it and `tryEval` sees no throw. The `modtest/` prototype is correct because `eval.nix` filters and throws explicitly, but that guarantee is ours, not the module system's.
2. **C8 is four forcing surfaces, not one** — option thunks, assertions, options excluded from the emit, plus freeform buckets and override-filtered definitions (never type-checked at all: `filterOverrides'` runs before the type check). A consequence: **`mkForce` in an arm silently masks a base type violation**, so each arm must be validated independently *and* the base validated with no arms applied.
3. **~210 ms per `nix-instantiate` invocation**, not 22 ms — both numbers are correct, they measure in-process evaluation versus wall clock, and the wall-clock figure is the one that belongs in a build plan.

Plus a genuine security finding: **never hand LLM-authored JSON to the module system unwrapped.** `imports = [ { config = <json>; } ]`, never `imports = [ <json> ]` — otherwise the wiring can carry `disabledModules` and delete the validator's own assertion module (verified: `topK=99` passed with `assertions` evaluating to `[]`), or carry `imports` and execute arbitrary Nix during validation.

Bounds on the carve-out: the contract stays **behaviorally specified** — `evalModules` is a build-phase implementation candidate against a bespoke validator, and the contract must remain implementable without Nix. It validates the artifact plane only; clauses 3–5 (runtime data properties) remain machine-owned at runtime. Caveat: module-system checking is lazy — the validator must force the full config strictly or violations pass silently. The store, derivations, identity, and runtime-sandbox conclusions are unchanged; DEPLOYMENT-ONLY stands for all of those, now with "except: the validator has an off-the-shelf candidate" recorded.

Also from Q9: declarative NixOS containers (`privateNetwork = true`) fill Q4b's network gap — unit confinement is FS-only, nspawn containers add the private network namespace declaratively.

**Surprises:**

1. The decisive fact was not the LLM-nondeterminism problem everyone expected. Post-hoc registration works fine (`nix store add`, no derivation, no privileges). What killed adoption is that you never need the store at all — `nix hash path` gives the same content address at 1.3 GB/s with nothing written.
2. The entire modern CLI (`nix store add`, `nix hash path`) is itself behind the experimental `nix-command` flag, alongside `ca-derivations`, `dynamic-derivations`, and `impure-derivations`.
3. `impure-derivations` and content addressing are mutually exclusive by design — the manual states it outright — so the "impure derivation" route was never available.

**Impact on remaining spikes:** D3 "Nix Unit" does not survive as specified. Recommendation recorded in NIX-LEVERAGE.md: replace it rather than degrade it, since with Nix removed it differs from D1 mainly by a typed spine that is already the lineup's most likely casualty of the executor-primitive disqualifier. Decide at the start of 003.
