---
title: Nix Leverage — adopt/avoid analysis and role verdict
spike: 004
date: 2026-08-10
verdict: DEPLOYMENT-ONLY (substrate) — AMENDED twice on 2026-08-10: Q9 added evalModules as a build-phase candidate for the Static Mutation Validator; Q10's 8-family/107-candidate sweep confirmed no trick exists for authoring wirings AS Nix (15 of 16 verified candidates rejected) and corrected several Q9 claims
sources: Nix 2.34 Reference Manual (nix.dev), NixOS option data (search.nixos.org via nixos MCP), NixOS 26.05 manual + nix.dev module-system deep dive, local measurement + working prototype on host `legion` (Nix 2.34.8, auto-optimise-store on)
---

# Nix Leverage — does Nix belong in the model, or only under it?

Answers spike 004. Consumed by spike 003's D3 variant and the step 8 fitting contract.

## Verdict

**DEPLOYMENT-ONLY.** Nix does not replace or substantially thin any of the six machine services, and the one clause it could harden (environment hash) is already settled on independent grounds. Nix exits the architecture model. NixOS hosts Sourcerer; sandbox parts run as confined systemd units; Nix returns at the build phase.

Two carve-outs survive, both smaller than the pre-research expectation:

1. **NAR hashing as a hash format** for directory-shaped artifacts — usable without the store, and therefore without any coupling.
2. **NixOS `systemd.services.<name>.confinement`** as the substrate implementation of machine service #2 — a *substrate* finding, explicitly not a Nix-in-the-model finding.

The decisive facts: the Nix store path is **not** SA-1's hash (it closes over the store directory and the artifact's *name*), and Nix's content address is obtainable **without** putting anything in the store. Together these remove both the identity argument and the store argument for adoption.

## Findings by question

### Q1 — Impure artifacts: can LLM-nondeterministic output be registered content-addressed? **Yes, and without a derivation.**

- `nix store add` — "Copy _path_ to the Nix store, and print the resulting store path on standard output." No derivation, no build, no evaluation involved. Modes `nar` (default) / `flat` / `text`; algorithms `blake3`, `md5`, `sha1`, `sha256`, `sha512`; `--name` overrides the path's name component. [docs-verified]
- Ran as an unprivileged user on the host, no daemon privileges required. [code-verified]
- Warning from the manual: "The resulting store path is **not registered as a garbage collector root**, so it could be deleted before you have a chance to register it." Registration is a second, separate step (`--add-root`, which also plants a symlink in `/nix/var/nix/gcroots/auto/`). [docs-verified]
- The *derivation* routes are all dead ends for this use case:
  - **Fixed-output derivations** require `outputHash` to be known in advance — impossible for LLM-produced output. [docs-verified]
  - **Impure derivations** (`__impure = true`, experimental) explicitly cannot be combined with content addressing: "an impure derivation cannot also be content-addressed", and "only fixed-output or other impure derivations can rely on impure derivations." [docs-verified]

So the only working route is exactly the one the pre-research inference predicted — post-hoc registration — and it needs none of Nix's build machinery.

### Q2 — Store residency: is the store required to get the content address? **No. This is the finding that decides the spike.**

- `nix hash path --mode nar --type sha256` computes the same NAR content hash with **zero** store residency. [docs-verified + code-verified]
- Measured on a 256 MB artifact, host `legion`:

  | Operation | Time | Effective rate |
  |---|---|---|
  | `nix hash path` (no store residency) | 192 ms | ~1.33 GB/s |
  | `nix store add` (first time, full copy) | 901 ms | ~284 MB/s |
  | `nix store add` (identical bytes again) | 204 ms | dedup — same path returned, no copy |

  [code-verified — `.planning/spikes/004-nix-leverage/bench.sh`]
- Extrapolated to a 10 GB index artifact: ~7.5 s to hash, ~35 s to hash *and* copy into the store. The store-residency tax is ~4.7× in time plus 100% of the artifact's size on disk.
- `auto-optimise-store` hard-links identical files store-wide (the host reports 23.6 GiB currently saved), and re-adding identical bytes returns the same path without recopying. Dedup is real but only helps for *identical* artifacts — distinct index builds each cost their full size.
- **Confirms PRIOR-ART's split**, and strengthens it: "hashes in the store, artifacts in dedicated stores" becomes "hashes computed by `nix hash path`, artifacts in dedicated stores, Nix store not involved at all."

### Q3 — Experimental-feature dependency: **every content-addressing feature beyond the basics is experimental.**

Manual definition: "Experimental features are considered unstable, which means that they can be changed or removed at any time." [docs-verified]

| Feature | Status | Relevance |
|---|---|---|
| `ca-derivations` (`__contentAddressed`, floating CA outputs) | experimental, milestone 35 | would be required for build-time CA of our parts |
| `dynamic-derivations` (text-hashing outputs, drv-producing drvs) | experimental, milestone 39 | the only route to runtime-generated build graphs |
| `impure-derivations` (`__impure`) | experimental, milestone 42 | and cannot be content-addressed anyway (Q1) |
| `git-hashing` | experimental | alternative hash method |
| `nix-command` (the entire new `nix` CLI) | **experimental**, milestone 28 | `nix store add` and `nix hash path` are both new-CLI |

The last row matters more than it looks: `nix store add` and `nix hash path` are themselves behind an experimental flag. The stable-CLI equivalents (`nix-store --add`, `nix-hash`) exist and are not flagged, so an adoption can avoid the gate — but any design written against the modern commands is written against an interface Nix reserves the right to change.

*Footnote (folded-in Q6 from the original draft):* `flake.lock` pins **input revisions** (a flake reference at a git revision), not the content hash of a resolved component config. It does not overlap registry version pinning; it solves a different problem one layer down. No conflict, no leverage.

### Q4a — Is the Nix build sandbox usable for runtime isolation? **No. Build-time only.**

Nix's sandbox is a property of *building a derivation*. There is no mechanism to run an already-built service under it; it is not a general-purpose runtime jail. A sandbox-regime part is a long-lived process serving queries, not a build. [docs-verified — sandboxing is documented exclusively as a build setting]

### Q4b — Does declarative systemd hardening satisfy machine service #2? **Mostly, and it is a substrate finding.**

NixOS exposes `systemd.services.<name>.confinement.*`: [docs-verified — NixOS option data]

- `confinement.enable` — "all the required runtime store paths for this service are bind-mounted into a tmpfs-based `chroot(2)`"
- `confinement.mode` — `full-apivfs` (default) "sets up private `/dev`, `/proc`, `/sys`, `/tmp` and `/var/tmp` file systems in a separate user name space"; or `chroot-only`
- `confinement.packages` / `fullUnit` — control exactly what enters the chroot closure
- **Critical limitation, quoted:** "This doesn't cover network namespaces and is solely for file system level isolation."

So FS-level deny-by-default is declarative and available; **network** denial and the wall-clock watchdog are separate systemd directives (`PrivateNetwork=`, `RestrictAddressFamilies=`, `RuntimeMaxSec=`) set through `serviceConfig` [inference — systemd directives, not verified against systemd docs in this spike]. Per-arm process isolation is what a unit *is*.

This is a good answer for the build phase and a **non-answer for the architecture model**: it says NixOS is a convenient host, not that the model should contain Nix concepts. Labelled as required by the spike's question 4(b).

### Q5 — Promotion via profiles: **the mechanism works, and it is a symlink swap we can do ourselves.**

- Profile layout, verbatim: `path` is a symlink to `path-N-link`, which is a symlink to a store path. "Each of these symlinks is a root for the Nix garbage collector." Profiles live in `$XDG_STATE_HOME/nix/profiles` for regular users — **no root required**. [docs-verified]
- A profile's store path is "a tree of symlinks to the files of the installed packages", so one repoint switches a whole *set* of artifacts at once — genuine multi-artifact atomicity. [docs-verified]
- `nix profile rollback [--to N]`, `nix profile history`, `nix profile diff-closures`, `nix profile wipe-history` provide the generation history. [docs-verified]
- Atomicity comes from `rename(2)` on the symlink, not from anything Nix-specific. Measured cost of the equivalent bare swap: **1.38 ms per repoint** including two process spawns; the syscall itself is microseconds. [code-verified]

PRIOR-ART already adopted "promote = repoint a mutable alias." This spike confirms the pattern and shows Nix is not needed to implement it — a symlink swap plus our own generation table gives the same semantics, scoped to our own vocabulary, with no store coupling.

### Q6 — Coupling cost: **cheap for registration, expensive for execution.**

- Registering an artifact: no derivation, no Nix expression, no privileges. A mutation operator can call `nix store add` (or just `nix hash path`) directly on its output. Zero human in the loop. [code-verified]
- Running a mutation-authored *part* as a Nix-built unit: requires a derivation, which requires Nix expression code, which requires either a human author or an LLM emitting valid Nix that must then evaluate and build. This is the coupling the decision rule was worried about, and it is real — but it only bites on the *execution* path, which Q4a already ruled out.

The asymmetry is the useful result: the cheap half of Nix (hash a directory) is the half we do not need Nix for, and the expensive half (build and run under it) is the half that does not fit.

### Q7 — Mutation-loop latency: **not a constraint, given promotion is a repoint.**

From the Q2 table plus the repoint measurement: registration is I/O-bound and linear in artifact size (~1.3 GB/s hash-only, ~284 MB/s with store copy); promotion is ~1 ms. A branch → A/B → promote cycle pays seconds of hashing on multi-GB artifacts and nothing measurable on the promote itself. [code-verified]

The latency risk was never the repoint — it is the alternative design where promotion means *building a derivation*, whose cost is the build and therefore unbounded. Since that design is ruled out by Q4a and Q6, latency is a non-issue.

### Q8 — One identity or two: **two. The standing disqualifier fires.**

The store path digest is "solely computed from" the file system object graph, **references**, the **store directory**, and the **name** of the store object. [docs-verified — Nix manual, Content-Addressing Store Objects; and `store-path = store-dir "/" digest "-" name`, Store Path Specification]

Consequences:

- Identical bytes registered under a different `--name` produce a **different** store path. Identical bytes on a host with a different store directory produce a **different** store path.
- SA-1 requires the content hash of *resolved inputs*, including embedder identity. A Nix store path closes over none of that and adds two things SA-1 deliberately excludes.
- Adopting the store path as artifact identity would leave the system carrying two identity vocabularies — the store path for Nix-registered artifacts and the SA-1 hash for everything else — with no total order between them and traces that could name either.

Per the spike's standing disqualifier, this is a strike against adoption independent of every other answer. The NAR hash *inside* the store path is fine as a component of an artifact stamp; the store path is not.

### Q9 (amendment, 2026-08-10) — Module system: can `evalModules` be the wiring/swap layer? **Yes as an implementation candidate for one named service. No as the contract.**

The original question set aimed at the store and never examined Nix's actual composition layer. Corrected here, docs-verified against the NixOS 26.05 manual and the nix.dev module-system deep dive, then code-verified with a working prototype (`modtest/` in the spike directory).

**What the prototype proved** (miniature fitting contract as a module: typed component slots, capability enum, dependency assertions; run `modtest/run-tests.sh`):

| Test | Result |
|---|---|
| Standalone `evalModules`, no NixOS, only nixpkgs `lib` | works [code-verified]; nix.dev deep dive uses exactly this pattern [docs-verified] |
| **Wirings authored as JSON**, read via `builtins.fromJSON` — component authors and the mutation operator never write Nix | works [code-verified] — this dissolves most of Q6's coupling cost |
| Type violation (bad semver via `strMatching`) | fails at eval [code-verified] |
| Undeclared capability (`"telepathy"` against the capability enum) | fails at eval with the allowed list in the error [code-verified] |
| Graph-level precondition (edge referencing undeclared component) as `assertions` | reported as data; the *validator* must filter and throw — see the Q10 correction below, which shows "fail-closed" was wrong as originally stated [code-verified] |
| **Swap = JSON overlay + `mkForce`**: embedder v2.1.0 → v3.0.0 replaced, whole wiring revalidated | works [code-verified] |
| Full validation latency, cold process each run | **22 ms** [code-verified] |

**What the docs add:**

- Merge with priorities (`mkDefault` / `mkForce` / `mkOverride N`) gives deterministic layered config: base wiring + experiment overlay + per-arm override is exactly the branch → A/B arm-definition mechanic, expressed declaratively. This is beyond what JSON Schema offers. [docs-verified]
- Proper sum types exist (`attrTag`); the manual warns `either`/`oneOf` decide eagerly on a shallow check and misdispatch composite types — use `attrTag` for discriminated unions. [docs-verified]
- Checking is **lazy**: a type error fires only when the value is forced. A validator must force the whole config strictly (the prototype does via `--strict` plus building the full output) or violations pass silently. [code-verified — the T2 error fired at access, not at definition]

**What it still cannot do:** clauses 3–5 are runtime properties of data in flight (refs with provenance, score semantics, typed context blocks). The module system never sees that data. It validates the artifact plane only — which is precisely machine service #5's job (Static Mutation Validator: "type-check wirings, caps, before execution") and nothing more.

**Verdict impact:** decision rule (a) partially fires — the Static Mutation Validator is the one machine service Nix substantially thins, via `lib.evalModules`, at 22 ms per validation and with zero Nix exposure to component authors (wirings stay JSON). This does **not** re-open the store, derivations, identity, or runtime-sandbox conclusions, and it must not put Nix vocabulary into the contract: the contract specifies the validator behaviorally; `evalModules` is a build-phase implementation candidate against a bespoke JSON-Schema-plus-graph-checks validator. The contract must remain implementable without Nix.

**What else the module system offers (all substrate/build-phase, recorded for step 12+):**

1. **Declarative NixOS containers** (`containers.<name>` with `privateNetwork = true`) — fills Q4b's network gap: unit confinement is FS-only, but nspawn containers get a private network namespace declaratively. Strongest available containment for sandbox-regime parts on this substrate. [docs-verified]
2. **Generated systemd units from wirings** — a NixOS module can map "promoted wiring" → confined unit definitions, making deployment a function of the registry. [inference — standard module-system usage, not prototyped]
3. **Auto-generated option documentation** — the contract's wiring schema would self-document the way NixOS options do. [docs-verified — the NixOS manual is generated this way]
4. **NixOS test framework** (`extendNixOS`, multi-machine VM tests) — integration tests of the deployed rig. [docs-verified]

### Q10 (second amendment, 2026-08-10) — Exhaustive mechanism sweep: is there a trick if the wiring spec were *authored as Nix*? **No, and three mechanisms make it worse than JSON.**

Q9 answered "can the module system validate a JSON wiring" (yes, bounded). Q10 asks the different question: would authoring or storing the wiring spec **as Nix** buy anything? Method: 8 mechanism families swept in parallel (nixpkgs `formats`/`settings`, advanced module mechanics, scope/fixed-point/overlay, flake-level, build integration, system analogues, tooling and non-Nix alternatives, plus a completeness-critic pass), 107 candidates found, the 16 strongest put through dedicated adversarial refutation. **15 rejected, 1 survived as a conditional implementation detail.** Every survivor keeps the wiring as JSON.

**Three ways a Nix-authored spec is actively worse than JSON** [all code-verified]:

1. **Arbitrary code execution during validation.** A spec accepted as a bare module value carries `imports`: `{"embedder":"e","topK":99,"imports":["/tmp/pwned.nix"]}` evaluated the file and returned `topK=83`, where 83 was `length (attrNames (readDir /home/chris))`.
2. **The spec can disable its own validator.** The same shape accepts `disabledModules`, which removed the assertion module: `assertions` evaluated to `[]` and an out-of-range `topK=99` passed, where the identical spec without that key failed correctly.
3. **Unbounded evaluation.** Nix has no eval timeout and no eval memory cap. `max-call-depth` catches non-productive recursion in 50 ms but not productive recursion: `genericClosure` with a never-repeating key generator ran until the host session had to be killed, despite a `timeout 8` wrapper. A validator on generated input inherits this — C7 violated by construction.

**The best near-miss.** Merge-priority algebra (`mkDefault`/`mkForce`/`mkOverride N`) for base + overlay + per-arm override is the one capability CUE provably lacks at arbitrary depth. Killed on verification: `filterOverrides'` runs **before** the type check (`lib/modules.nix:1224` vs 1270/1279), so a `mkForce` in an arm silently masks a type violation in the base — `caps = ["quantum"]` (illegal enum) under an arm's `mkForce ["gpu"]` returns `{"caps":["gpu"]}`, exit 0. Not fixable by forcing; it is override semantics.

**The one thing Nix does that no other config system does at all:** string contexts — automatic, unforgeable dependency capture through data. It fails C5: the captured vocabulary is store paths (the standing disqualifier), and it captures nothing about component versions or embedder identity, which is most of what SA-1 needs.

#### Corrections to the Q9 amendment (all [code-verified] — these supersede what Q9 recorded)

- **"Graph preconditions as fail-closed `assertions`" was wrong as stated.** A failed assertion evaluates *successfully* to `{assertion = false; message = "…";}`. `deepSeq` walks past it; `tryEval` sees no throw. The prototype in `modtest/` is correct because `eval.nix` explicitly filters and throws — but the guarantee belongs to our code, not to the module system.
- **C8 is not one forcing surface, it is four**: option thunks, assertions, options excluded from the emit, and the two originally missed — freeform buckets (forced but untyped) and override-filtered definitions (never type-checked at all).
- **Each arm must be validated independently, and the base validated with no arms applied** — see the `mkForce` masking result above.
- **Real cost is ~210 ms wall clock** per `nix-instantiate` invocation, not the 22 ms measured in-process. Both numbers are right; they measure different things.
- **The validator must run fork-per-wiring with an exit-code verdict.** `tryEval` returns one bit and discards the error string; it does not catch `abort`, builtin type errors, malformed `fromJSON`, infinite recursion, or stack overflow — five classes that each kill a whole batch and destroy every sibling arm's verdict.
- **Never hand LLM-authored JSON to the module system unwrapped.** Always `imports = [ { config = <json>; } ]`, never `imports = [ <json> ]`. Seven Nix keywords otherwise live in the wiring namespace; `_file` even forges provenance.
- **Schema prohibitions:** no root `freeformType` (a typo `startegy` is retained as garbage while the real option silently defaults — and freeform suppresses the "Did you mean" hint, the best repair signal the module system offers an LLM); `_module.check` stays `true` (with it false, `{"bogusKnob":1}` was silently *dropped*); no `types.lazyAttrsOf` (a poisoned sibling is never checked); no `types.path` (emits a store path); no unconstrained `lib.types.json` (`check` returns true for a derivation, which then serializes as `/nix/store/…`); `import <nixpkgs/lib>` only, never `import <nixpkgs> {}` (0.02 s vs 0.20 s, and it structurally prevents a package attribute resolving into the spec).
- **Module `key` must be the wiring node id (position), never the SA-1 instance id** — `genericClosure` dedupes by key, so fan-out silently loses branches.
- **External resource limits are mandatory** (`systemd-run --property=MemoryMax= --property=RuntimeMaxSec=`), since Nix provides none. `--restrict-eval --option allowed-uris ""` works at 24 ms and blocks `readFile /etc/shadow`.

#### Findings that change the plan (none of them Nix)

1. **`config_hash` is computed over the author-supplied input JSON**, canonicalized by a named standard (RFC 8785 JCS or an explicitly specified variant, ~12 lines), never over the module-normalized output. Measured reasons: Nix's JSON printer is not JCS (`1e10`→`10000000000.0`, `1e20`→`1e+20`, four of seven test values diverge), `{"tau":1}` and `{"tau":1.0}` hash differently, out-of-int64 integers silently become doubles, and adding one option with a default re-hashed every wiring with byte-identical input — destroying in-flight A/B baselines. 12 lines of Python reproduce the same bytes 2200× faster.
2. **Arm deltas are RFC 7386 merge-patch** (or 6902), with one documented exception: a differing component-kind tag replaces the whole `kind` subtree rather than merging into it. `remove` is fail-closed by specification; `disabledModules` is not — a one-character typo in a key is a silent no-op, so an arm reports "reranker dropped" and ships with the reranker in.
3. **The validator returns all violations with JSON-Pointer paths in one pass.** The module system reports one type error per evaluation and aborts; three simultaneous socket violations produced one Nix error and three from a JSON-Schema pass. In an LLM repair loop the round trips dominate, not the 22 ms.
4. **Socket wiring is a partial order over named nodes, not a total order by integer priority.** The sweep's own advanced-module family got this wrong before the critic caught it. NixOS solves it with per-node `deps` + `textClosureMap` (`activation-script.nix:101-107`), and home-manager generalises it as `dagOf` with `topoSort` returning `{cycle; loops;}` **as data**. Adopt the shape, not the Nix: `deps` + Kahn's algorithm, ~30 lines, and per C1 the cycle check must return the offending node names rather than throwing.
5. **Tagged sums stay in portable vocabulary.** `types.either`/`oneOf` eagerly pick the first matching composite type, so per-kind socket checks evaporate; if `evalModules` is built, component kind must be `attrTag`. The *contract* says "a component's kind is a tagged sum: a single-key object whose key selects the kind and whose value is validated by that kind's own schema" — citing serde external tagging / pydantic discriminated unions / OpenAPI discriminator, never `attrTag`.
6. **Ledger/projection separation, borrowed with zero Nix content.** Profile generations are the durable ordered record; bootloader entries are a derived projection regenerated from them. Rule for the A/B rig: running an arm SHALL NOT append to the promotion ledger, and the active-wiring pointer SHALL be derivable from the ledger. Crash-safety falls out. The `check | dry-activate | test | boot | switch` verb ladder is the promotion vocabulary — pass the verb to the gate so one gate implementation serves all transitions.

#### Alternatives, measured

- **CUE** — `cue vet -c schema.cue wiring.json` validates plain JSON in place at 5 ms, expresses cross-field edge-dtype rules as comprehensions, and has **no C8 hole** (a hidden `_edgeTypeCheck` still failed under `vet -c`). Loss: unification is commutative, so exactly one override level; doing the overlay outside the language (RFC 7386, ~15 lines) removes the gap.
- **JSON Schema + a graph validator in the machine's language** — maximum C4 compliance. The split is forced, not chosen: JSON Schema 2020-12 cannot evaluate cross-field expressions like `components[split(edge.from,'.')[0]].outputs[…].dtype == …`.
- **Nickel** — structured `--error-format json` diagnostics with source byte-ranges by design; multi-error reporting is a plural schema, not a demonstrated behavior. Unbenchmarked.
- **Schema generation from module options is a dead end in every ecosystem.** clan's `lib.jsonschema` and zod's `toJSONSchema` both drop exactly the half that matters — `strMatching` regexes vanished (a bad version validated clean), and `assertions`/`superRefine` are unexportable. Direction must be contract → schema → renderer, never module → schema.

#### Verification status

16 candidates adversarially verified (high confidence). **Not** adversarially verified, single-pass evidence only, treat as provisional: the `--argstr` file-route validator pipeline, the forced-assertion discipline, the `restrict-eval` sandbox and no-timeout finding, the DAG-valued option pattern, `runTests`/`repl`, the ledger/verb-ladder borrowings, and the CUE/JSON-Schema/Nickel comparisons. All were measured on host `legion`; none survived a dedicated refutation pass. The two most load-bearing — the validator pipeline and the assertion channel — deserve one before they enter the build plan, specifically to test whether the assertion channel stays complete under schema evolution.

## Adopt / Avoid

| | Item | Where | Why |
|---|---|---|---|
| **Adopt** | NAR content hashing (`nix hash path --mode nar`, or the NAR serialization spec) as the hash format for directory-shaped artifacts | fitting contract, artifact stamp | Well-specified, fast (~1.3 GB/s), zero store coupling, standard serialization for directory trees — the problem plain file hashing does not solve |
| **Adopt** | `systemd` unit confinement (`confinement.enable`, `mode = "full-apivfs"`, plus `PrivateNetwork` / `RuntimeMaxSec`) as the *substrate* implementation of machine service #2 | build phase, deployment docs | Declarative deny-by-default FS isolation, per-arm process, on the substrate we already run |
| **Adopt** | Promote = atomic alias repoint with a generation history and rollback | already adopted from PRIOR-ART; confirmed here | ~1 ms, `rename(2)`-atomic, multi-artifact in one swap, no root needed. Implement directly; do not route through `nix profile` |
| **Adopt (candidate)** | `lib.evalModules` as the implementation of the Static Mutation Validator (machine service #5) | build phase; contract stays behaviorally specified | Proven standalone: JSON wirings in, typed sockets + capability enums + fail-closed assertions, swap = overlay + `mkForce`, 22 ms/validation. Compare against a bespoke validator at build time; contract must remain implementable without it |
| **Adopt (substrate)** | Declarative NixOS containers (`privateNetwork = true`) for sandbox-regime parts needing network isolation | deployment docs | Unit confinement is FS-only; nspawn containers add the private network namespace declaratively |
| **Avoid** | The Nix store as the artifact store | — | Full copy per distinct artifact (~4.7× the hash-only time, plus disk), GC roots to manage, and the content address is obtainable without it |
| **Avoid** | Store paths as component or artifact identity | — | Closes over store directory and name; is not SA-1; creates a second identity vocabulary (standing disqualifier) |
| **Avoid** | Derivations as the mutation/promotion mechanism | — | Requires generated Nix expressions from the mutation operator; build-time model does not fit a long-lived query-serving part |
| **Avoid** | Any design depending on `ca-derivations`, `dynamic-derivations`, or `impure-derivations` | — | All experimental; manual states they "can be changed or removed at any time"; impure cannot be content-addressed at all |
| **Avoid** | Nix's build sandbox as the runtime isolation domain | — | Build-time only; a sandbox-regime part is a service, not a build |

## Role verdict

**Substrate-only.** Not environment-pinning as a model concept, not an identity layer.

The environment-hash requirement stands on its own (Feast version-skew, PRIOR-ART avoid list) and is satisfied by *any* deterministic hash of the resolved runtime environment. Where a component happens to be Nix-built, its derivation hash is a convenient source for that field — an implementation detail recorded at the build phase, not a contract clause that names Nix.

## What would falsify this verdict

- If the machine ever needs to *build* components reproducibly from source as part of the mutation loop (rather than register produced artifacts), the derivation model becomes relevant and Q4a/Q6 must be re-run.
- If `ca-derivations` stabilizes **and** a route appears to content-address non-deterministic output, Q1's dead end reopens.
- If artifacts turn out to be small (sub-100 MB) and highly redundant across arms, the store's hard-linking dedup could outweigh the copy tax and Q2's arithmetic flips.
- If a second host or a distributed rig enters scope, the store's copy/substitute protocol becomes a distribution mechanism worth its coupling — not a consideration in a single-host design.

## Consequences for spike 003

**D3 "Nix Unit" as specified does not survive.** Its distinguishing properties were a Nix-derivation sandbox and content-addressed promotion through the store; Q4a removes the first and Q2/Q8 remove the second. Per the 003 amendment ("if 004's verdict is deployment-only, D3 degrades to a substrate-only containment choice and says so"), D3 has two honest futures:

1. **Redraw as "D3 Substrate Unit"** — systemd-confined sandbox parts, our own hashing and alias repoint, Nix nowhere in the model. This is a legitimate containment position, but it is now much closer to D1, whose containment axis already reads "OS container / Nix unit, hard."
2. **Replace it** with a genuinely different fourth position, and let D1 absorb the containment argument.

Recommendation: **replace it.** With Nix gone, D3 differs from D1 mainly in kernel style (typed spine vs full declared-graph engine) — and that spine is already the lineup's most likely casualty of the executor-primitive disqualifier (fan-out/join, ephemeral subgraph, non-adjacent fan-in). A variant that is doubly weakened before drafting is not worth one of four slots. Decide this at the start of 003, not mid-draft.

## Consequences for the fitting contract (step 8)

- Artifact stamp specifies **NAR-hash over the artifact tree** as the content-hash function; no store path, no Nix vocabulary.
- Promotion is specified as **alias repoint + generation record**, implemented directly.
- Machine service #2 is specified behaviorally (deny-by-default net/FS/store-write, wall-clock watchdog, per-arm process); the deployment document names systemd confinement as the substrate implementation.
- Environment hash stays a required field of `config_hash` with its source left to the build phase.
