# Is there a Nix trick that makes a Nix-authored wiring spec easier?

## 1. The answer: no

107 candidates across 8 mechanism families. The 16 strongest went through adversarial verification. **15 were rejected outright; 1 survived as a conditional implementation detail.** Nothing found makes the wiring spec easier by being *authored or stored as Nix*.

The result is stronger than "no clear win". Three of the mechanisms that make a Nix-authored spec *possible* make it **actively more dangerous than JSON**:

- A wiring spec accepted as a bare module value can carry `imports` and execute arbitrary Nix during validation. Measured: `{"embedder":"e","topK":99,"imports":["/tmp/dm-refute/pwned.nix"]}` evaluated the file, returned `embedder="PWNED"` and `topK=83` where 83 = `length (attrNames (readDir /home/chris))` [code-verified].
- The same shape accepts `disabledModules`, which **removes the validator's own assertion module**: `assertions` evaluated to `[]` and an out-of-range `topK=99` passed, where the identical spec without that key produced `{"assertion":false,"message":"topK too large"}` [code-verified].
- Nix has **no evaluation timeout and no evaluation memory cap**. `max-call-depth` catches non-productive recursion in 50 ms but not a productive one: `genericClosure` with a never-repeating key generator ran until the host session had to be killed, despite a `timeout 8` wrapper [code-verified]. A validator that runs pre-execution on generated input inherits that as unbounded latency (C7 violated by construction).

The nearest thing to a "yes" was the module system's merge-priority algebra (`mkDefault`/`mkForce`/`mkOverride N`) for base + experiment overlay + per-arm override — the one capability CUE provably lacks at arbitrary depth. Adversarial verification killed it: `filterOverrides'` runs **before** the type check (nixpkgs `lib/modules.nix:1224`), so a `mkForce` in an arm silently masks a type violation in the base — `caps = ["quantum"]` (illegal enum) under an arm's `mkForce ["gpu"]` returns `{"caps":["gpu"]}`, exit 0 [code-verified]. Forcing cannot close it; it is override semantics.

The one thing Nix does that **no other config language does at all** is string contexts — automatic, unforgeable dependency capture through data. `getContext "${toFile "c.json" "{}"} and ${toFile "d.json" "{}"}"` returns both store paths with no declaration [code-verified]. It fails C5: the captured vocabulary is store paths, which is the standing disqualifier, and it captures nothing about component versions or embedder identity, which is most of what SA-1 needs.

---

## 2. What survived, ranked

Every survivor keeps the wiring spec as JSON. None argues for Nix authoring.

### R1 — The validator pipeline: `--argstr` path ingress, `--strict --json` egress, explicit assertion forcing
**Mechanism.** `nix-instantiate --eval --strict --json validate.nix --argstr wiringPath /abs/w.json`, where `validate.nix` is static human-written Nix doing `builtins.fromJSON (builtins.readFile wiringPath)` into `lib.evalModules`, then `if failures != [] then throw ... else builtins.deepSeq out out`.
**Buys.** Typed sockets, semver `strMatching`, capability enums, and hallucinated-key detection (`The option 'components.embedder.embeder_model' does not exist`) in 20–30 ms with no derivation and no store write. `nix-instantiate --eval` is read-only by default: an IFD probe failed with `path '...drv' is not valid` until `--read-write-mode` was passed [code-verified].
**Bounds.** Never `nix eval` (nix-command experimental, read-write by default, and `--apply 'f: f {...}'` is generated Nix source). Never `pkgs` — `import <nixpkgs/lib>` only, 0.02 s vs 0.20 s, and it structurally prevents a package attribute resolving into the spec. Never `--pure-eval` on a flake (blocks reading a just-generated wiring). Hash the **input** JSON, never the emitted config.
**Status:** the file route was **not** adversarially verified. The argv variant of it was, and rejected (see §3).

### R2 — `config.assertions` as an all-errors-at-once data channel
**Mechanism.** Every graph precondition contributes `{assertion = <pred>; message = "E0NN: ...";}`; the validator returns `map (a: a.message) (filter (a: !a.assertion) config.assertions)`.
**Buys.** This is the fix for the single loudest defect found across all 16 verifications: the module system reports **one** type error per evaluation and aborts. Three simultaneous socket violations produce one Nix error and three from a jsonschema pass [code-verified]. Assertions do not short-circuit — a wiring with three defects returned all three as JSON in one eval [code-verified]. In a repair loop, one-error-per-eval costs N LLM round trips per malformed wiring, and the round trips dominate, not the 22 ms.
**Bounds.** Assertions only run on a config that type-checked, so keep option types permissive and push rules into assertions. `assertions` is itself lazy and is **not** forced by emitting the config: `--strict --json` on a subtree that excludes it silently passes an invalid wiring [code-verified]. It must be explicitly consumed. Every new assertion is inert until it is in the consumed list — a per-assertion-class self-test is mandatory.
**Status:** not adversarially verified.

### R3 — `types.attrTag` inside the validator, if evalModules is built
The only candidate to survive verification (verdict: `build-phase-option`, not `adopt`). `types.either`/`oneOf` eagerly pick the first matching composite type, so `either (attrsOf int) (submodule {...})` always resolves to `attrsOf int` and every per-kind socket check evaporates [docs-verified, nixos manual `#sec-option-types-sums`]. If the validator is a module eval, component kind must be `attrTag`. The **contract** says "component kind is a tagged sum with per-kind schema" (serde external tagging / pydantic discriminated union), never `attrTag`.
**Bounds.** Confirmed C8 live: not forcing config left a bad-tag wiring passing. The claimed arm-swap benefit does not exist — kind swap needs `mkForce` at the `kind` leaf, param tweak needs it at the field leaf, and no fixed JSON shim serves both [code-verified].

### R4 — Sandbox and resource limits, mandatory if Nix eval ever touches generated input
`--restrict-eval --option allowed-uris "" -I wlib=<pinned lib store path> --argstr` works end to end at 24 ms and blocks `readFile /etc/shadow` [code-verified]. Pair with external limits (`systemd-run --property=MemoryMax= --property=RuntimeMaxSec=`) because Nix has none. Note `getEnv` returns `""` **silently** under pure eval rather than erroring — treat any `getEnv` in a validator as a schema violation. This finding cuts both ways: it makes Nix-authored wirings safe, and it is the strongest argument that JSON, which has no attack surface to sandbox, is the right shape.
**Status:** not adversarially verified.

### R5 — DAG-valued option pattern (the one structural gap the 7-family sweep missed)
`nixos/modules/system/activation/activation-script.nix:101-107` declares `deps = mkOption { type = listOf str; }` per named node and resolves with `textClosureMap` at line 223 [code-verified]. home-manager generalises it as `lib.hm.types.dagOf` with `dag.topoSort` returning `{cycle; loops;}` as **data**, not an exception [code-verified]. The advanced-module family concluded ordering was `mkOrder` — a total order by integer priority. That is wrong for socket wiring, which is a partial order over named nodes.
**Adopt the shape, not the Nix.** `{"retriever":{"deps":["embedder"]}}` plus Kahn's algorithm with cycle-as-data is ~30 lines in any language, and C1 explicitly permits a wiring spec to describe cycles — so the cycle check must return the offending node names, never throw.
**Status:** not adversarially verified.

### R6 — Zero-cost development conveniences
`lib.debug.runTests` (contract rules as executable tests, 24 ms, no flake, no runner, no closure) and `nix repl --file` / `nix-instantiate --eval` for authoring-time exploration. Both are fine; neither is a reason to adopt anything. `runTests` silently skips any test whose name does not begin with `test`.

### R7 — Design borrowings with no Nix content at all
- **Ledger/projection separation.** Profile generations are the durable ordered record; bootloader entries are a derived projection regenerated from them. `nixos-rebuild test` activates without writing either [docs-verified]. Rule for the A/B rig: running an arm SHALL NOT append to the promotion ledger, and the active-wiring pointer SHALL be derivable from the ledger. Crash-safety falls out.
- **Verb ladder.** `check | dry-activate | test | boot | switch` is the promotion vocabulary, separating validate / preview / run-without-promoting / promote-next / promote-now. Pass the verb to the gate so one gate implementation serves all transitions.
- **Gates that fail the operation but do not appear in its output.** `system.checks` is passed to the builder purely to create a dependency; its source comment says it produces "no output of value" and including it "runs the risk of accidentally adding unneeded paths to the system closure" [code-verified, `top-level.nix:365-376`]. That is C8's shape, solved structurally rather than by discipline.

### R8 — The non-Nix alternatives, if the contract wants an executable form
- **CUE.** `cue vet -c schema.cue wiring.json` validates plain JSON in place at 5 ms, expresses the cross-field edge dtype rule as a comprehension, and has **no C8 hole** — a hidden field `_edgeTypeCheck` still failed under `vet -c` [code-verified]. Loss: unification is commutative, so exactly one override level; no `mkOverride N` analogue. Doing the overlay outside the language (RFC 7386, ~15 lines) removes the gap.
- **JSON Schema + graph validator in the machine's language.** Maximum C4 compliance. The split is forced, not chosen: JSON Schema 2020-12 cannot evaluate `components[split(edge.from,'.')[0]].outputs[...].dtype == ...` [code-verified].
- **Nickel** was named in the brief and was skipped by the alternatives family. Structured `--error-format json` diagnostics with source byte-ranges by design [code-verified, built and run]. Multi-error reporting is a plural schema, not a demonstrated behaviour — verify before relying on it. Unbenchmarked against the 22 ms baseline.

---

## 3. Attractive failures

| Mechanism | Killed by |
|---|---|
| `formats.generate` as the emit route | **C5.** Measured: `{ corpus = /tmp/fmt/data.txt; }` emits `{"corpus":"/tmp/fmt/data.txt"}` via eval but `{"corpus":"/nix/store/y9dm...-data.txt"}` via `generate`. The derivation copies path values into the store and rewrites them in the spec body. Second identity vocabulary, measured, not hypothetical. Also 698 ms vs 21 ms. |
| `freeformType` / the `settings` idiom | **C3.** Typo `startegy` emits `{"modality":"lightrag","startegy":"selfrag","strategy":"crag"}` — garbage retained, real option silently defaulted, machine runs crag while the author asked selfrag. Without freeform: hard error plus a Levenshtein "Did you mean" — the single best repair signal the module system offers an LLM, and freeform is exactly what suppresses it. |
| `_module.check = false` | **C3.** Worse than freeform: `{"bogusKnob":1}` produced `{"components":{}}` — silently **dropped**, not even preserved. |
| Hashing the emitted/normalized config as `config_hash` | **C4 + C5.** Canonical form becomes 4110 unspecified lines of nixpkgs merge semantics plus a C++ printer that is not RFC 8785: `1e10`→`10000000000.0`, `1e20`→`1e+20`, `1.0`→`1.0`, `-0.0`→`-0.0`; four of seven test values diverge from JCS. `{"tau":1}` and `{"tau":1.0}` hash differently — weaker than JCS at the job proposed. Out-of-int64 integers silently become doubles. Adding one option with a default re-hashed every wiring with byte-identical input (e6499b83→820b27e4), destroying in-flight A/B baselines. 12 lines of Python reproduce the same bytes and the same sha256, 2200× faster. |
| `deferredModule` accepting bare JSON | **C2/C8.** Seven Nix keywords live in the wiring namespace. `disabledModules` disables the validator; `imports` executes arbitrary Nix; `key`/`_file` are silently swallowed and `_file` **forges provenance** (error reported "In 'f'" for a file that does not exist). Wrapping as `{ config = <json>; }` fixes it — and once wrapped, `deferredModule` is unnecessary. |
| evalModules result `.type` | Same injection surface (`shorthandOnlyDefinesConfig ? false`), plus 9 magic names stripped without error. And the prototype/instance arm story fails on every real arm: `conflicting definition values: "vec" / "graph". Use lib.mkForce` — and `mkForce` cannot appear in JSON. |
| `graph` as the lineage record | **Not validated, and it disagrees with what ran.** `graph` is a second, deliberately unshared `collectStructuredModules` call (`modules.nix:589-595`). It evaluates cleanly on a wiring whose `config` throws. Keying by SA-1 id makes fan-out lose branches: the same instance at two positions dedupes via `genericClosure`, one silently vanishes, and `graph` reports both as present with `disabled:false`. Every field is a value the loader put in. |
| `disabledModules` as the subtractive arm operator | **Fail-open.** A one-character typo in the key is a silent no-op — arm reports "reranker dropped" and ships with the reranker in. `isDisabled` is a bare `elem`; there is nothing to force. RFC 6902 `remove` is fail-closed *by specification*. |
| `mkOrder` / `mkBefore` / `mkAfter` for harness order | **C8, unfixable by forcing.** The priority is not part of the option value, so `types.listOf str` never sees it: `"500"`/`"1000"`/`"1500"` as JSON strings sort lexicographically with no error, and `"10"` sorts before `"9"`. Separately, definition order is the **reverse** of module-list order with or without `mkOrder` (`modules.nix:275`), leaking loader state into any hash over the resolved list. |
| `tryEval` as the fail-closed gate returning a verdict | **Returns one bit.** The error string is discarded; `{success=false; value=false;}`. It does not catch `abort`, builtin type errors, malformed `fromJSON` (`{ ` → rc=1, no output), infinite recursion, or stack overflow — five failure classes each of which kills the whole batch and every sibling arm's verdict. And `deepSeq` does not fail on assertions, which evaluate *successfully* to `{assertion=false;}`. |
| Flake registry / lock as alias table and dependency manifest | Registry rewrite is **not atomic** (same inode before and after); resolution is order-dependent first-match so an unversioned alias silently breaks later version-qualified lookups; repoint **does not propagate** — `flake.lock` freezes it until `nix flake update` on every consumer; the lock bakes in `lastModified` (an mtime); and evaluating a wiring **writes** the lock, changing the artifact's own hash. |
| `nix flake check` as the pre-execution gate | A flake whose outputs are entirely `throw` prints `all checks passed!`, exit 0. Non-standard outputs are warned about, never forced. |
| Git-flake-stored wiring directory | Evaluates only **tracked** files: a wiring the operator just wrote is invisible and evaluation succeeds against stale content. Fails at the fetcher layer, before evaluation. |
| IFD / `recursive-nix` / `__structuredAttrs` / `toFile` / `writeText` | **C3/C7.** All require a build in the validation path. IFD: 0.31 s cold for a no-op. `toFile` additionally cannot reference derivations at all, and its digest closes over the artifact name. |
| `nix store diff-closures`, `why-depends`, `path-info` | `nix store add` records **no references**: `why-depends` says "does not depend on" for an artifact whose file literally contains the target's store path. `--graph` draws one node. Injecting references needs root (`nix-store --load-db`). SA-1 is also unrepresentable: `name@version` → "name contains illegal character '@'". |
| `callPackage` / `lib.fix` as the wiring resolver | An unfilled socket **aborts uncatchably**; a legal cyclic wiring spec is `stack overflow; max-call-depth exceeded`, not trapped by `tryEval` — so C1's explicit permission for cycle-describing specs becomes an interpreter crash the validator cannot report. |
| `packagesFromDirectoryRecursive` as component registry | Only `.nix` files are loaded; a JSON component manifest is **silently dropped**, so a validator over it passes a wiring referencing a component that is not in the scope. |
| Module-options → JSON Schema export (clan `lib.jsonschema`, and zod's `toJSONSchema`) | Both drop exactly the half that matters: `strMatching` regexes vanished (`bad-ver.json` validated clean), and `assertions`/`superRefine` are unexportable. **No schema-generation path in any ecosystem preserves cross-field rules.** Direction must be contract → schema → renderer, never module → schema. |
| Poisoning `extendModules` to bound eval | `lib` is a baseline module argument **outside** `_module.args` and cannot be poisoned; re-entry succeeded with the poison installed. Plain recursion burns eval anyway. And `deepSeq ev` then always throws, giving a universal false rejection indistinguishable from a real finding. |

---

## 4. Does the current position change?

**No. It is confirmed, and hardened.**

- Wirings stay JSON. Confirmed on every axis, and the sweep found three ways a Nix-authored spec is *worse* than JSON (keyword collision, arbitrary import, unbounded eval).
- `evalModules` stays a **build-phase implementation candidate** for the Static Mutation Validator, unchanged in scope. Nothing overturns it; nothing extends it.
- The contract stays implementable without Nix. Reinforced: the one adoption that would have broken this — hashing the module-normalized form — is refuted with measured numbers.

Three additions to the plan, none of them Nix:
1. `config_hash` is over the **author-supplied input JSON**, canonicalized by a named standard (RFC 8785 or an explicitly specified variant, ~12 lines), with two rules pinned: no integers outside int64, and the int/float distinction collapses.
2. Arm deltas are **RFC 7386 merge-patch** (or 6902), with one documented exception: a differing component-kind tag replaces the whole `kind` subtree rather than merging into it. `remove` is fail-closed by spec; `disabledModules` is not.
3. The validator returns **all** violations with JSON-Pointer paths in one pass, not the first.

---

## 5. Amendments to record

**Spike 004 — corrections to the existing evalModules amendment (all [code-verified]):**
- "Graph preconditions as fail-closed `assertions`" is **false as stated**. Forcing `assertions` does not fail; they evaluate successfully to `{assertion=false;}`. The validator must filter for `assertion == false` and throw itself. `deepSeq` is necessary for option thunks and insufficient for preconditions.
- The C8 rule is not "force strictly", it is **four forcing surfaces**: option thunks, assertions, options excluded from the emit, and — the two the original missed — freeform buckets (forced but untyped) and override-filtered definitions (never type-checked at all, `modules.nix:1224` runs `filterOverrides'` before the check at 1270/1279).
- **`mkForce` in an arm masks base type errors.** Each arm must be validated independently *and* the base validated with no arms applied.
- Real per-validation cost is **210 ms wall clock** via `nix-instantiate`, not 22 ms in-process.
- The validator must run **fork-per-wiring with an exit-code verdict**. `tryEval` does not contain module-eval errors; five failure classes exit rc=1 and destroy every arm's verdict in a batch.
- **Never hand LLM JSON to the module system unwrapped.** Always `imports = [ { config = <json>; } ]`.
- Prohibitions for the schema: no root `freeformType`; `_module.check` stays `true`; no `types.lazyAttrsOf` (a poisoned sibling is never checked — `{good="x"; bad=throw "LAZY_BOMB";}` evaluates `good` fine); no `types.path` (emits a store path); no `lib.types.json` unconstrained (`types.json.check` returns **true** for a derivation, which then serializes as `/nix/store/...`); never `import <nixpkgs> {}`, only `import <nixpkgs/lib>`.
- Module `key` must be the wiring **node id (position)**, never the SA-1 instance id — `genericClosure` dedupes by key and fan-out silently loses branches.
- Nix has no eval timeout and no eval memory cap; external limits are mandatory.

**Spike 003 (D-variants) — constraints:**
- No D-variant may make a wiring spec's identity a function of nixpkgs merge/default semantics or of Nix's JSON printer.
- Any variant that admits a store path in any spec leaf has a second identity vocabulary by construction. Silent string-context discard is the leak path: `"${pkgs.hello}/bin/hello"` emits a full store path with the context dropped and the path not realized (`ls` → No such file).
- Cycle detection must return the cycle **as data**, per C1. `lib.fix` and `callPackage` both convert it into an uncatchable crash.
- Socket wiring is a partial order over named nodes (`deps` + closure), not a total order by integer priority.

---

## 6. Verification status

**Adversarially verified (16, high confidence):** `nix eval --json` as C8 force · free canonicalization · `tryEval`+`deepSeq` · `attrTag` · `deferredModule` · `mkOrder` · `disabledModules` (both framings) · `graph` (both framings) · result `.type` · `specialArgs` · `apply`+`toJSON` · `mkRenamed*` · revoking `extendModules` · whole-JSON `--argstr`. Fifteen rejected; `attrTag` returned `build-phase-option`.

**Not adversarially verified (single-pass evidence only, treat as provisional):** the `--argstr` **file**-route pipeline and forced-assertion discipline (R1, R2) · `restrict-eval` sandbox and the no-timeout finding (R4) · DAG-valued option pattern (R5) · `runTests` / `repl` (R6) · ledger/projection and verb-ladder borrowings (R7) · CUE, JSON Schema, Nickel (R8) · `mergeAttrDefinitionsWithPrio` · `--log-format internal-json`. Every one of these was measured on this host, but none was subjected to a dedicated refutation pass. The two most load-bearing — R1 and R2 — deserve one before they are written into the build plan, specifically to test whether the assertion channel stays complete under schema evolution.

Scratch artifacts (outside the workspace, read-only, nothing in the project directory was touched): /tmp/fmt, /tmp/wiring-mod, /tmp/nixprobe, /tmp/nixwiring, /tmp/cuetest, /tmp/pkltest, /tmp/wiretest, /tmp/canon, /tmp/attrtag-adv, /tmp/dm-refute, /tmp/mkorder-adv, /tmp/graphtest, /tmp/wr-adv, /tmp/sa-refute, /tmp/renametest, /tmp/wv, /tmp/adv, /tmp/tryeval-adv.