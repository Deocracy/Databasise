# Nix / NixOS Substrate Boundary

Where Nix belongs and where it must not appear. Settled by spike 004; verdict DEPLOYMENT-ONLY with narrow, named carve-outs.

## Requirements

- Nix names **nothing** in the architecture model; the fitting contract must stay implementable without it
- Component identity is SA-1, never a store path (store paths close over the store directory and the artifact name → a second identity vocabulary, which is a standing disqualifier)
- Machine service #2 (isolation) is specified **behaviorally**; the substrate implementation is named only in deployment docs
- No design may depend on `ca-derivations`, `dynamic-derivations`, or `impure-derivations` — all experimental

## How to Build It

### The dividing line

**Nix rebuilds the machine; the machine rebuilds the indexes.** Two loops, and Nix is only in the first.

| Nix-packaged (software — things you install) | Never Nix (registry objects — things the machine operates on) |
|---|---|
| The machine: kernel executor, registry, eval runner, promotion gate | Modalities — a modality is a wiring, which is JSON in the registry |
| DB engines (DuckDB, Cozo, vector stores) | Index artifacts — NAR-hashed, in our own stores |
| Component *implementations* — chunker, embedder client, PPR ranker | Recipes, wiring specs, traces, eval bundles, A/B arms, promotions |
| Sandbox part runtimes — each confined unit's closure | |

The test: **did the software change, or did the configuration of parts change?** Frequent operations (swap, A/B, promote, rollback) never touch Nix; the rare operation (install new software) is the only one that does. The coupling cost lands on the slow path by construction.

### Adding a modality — two acts, only one involves Nix

1. **New component code, if any** — implement against the fitting contract, Nix-package, install. Note what you do *not* install: there is no "HippoRAG" package.
2. **The modality itself** — a wiring JSON plus a recipe, validated, index built. No Nix.

As the component library grows, act 1 disappears for more and more modalities. A new graph-RAG approach that reuses existing parts is wiring-only, and can share index artifacts with a sibling modality wherever the sub-recipe stamps match.

### Updating an engine (e.g. DuckDB) — the version-skew guard

1. Nix updates the engine; the old closure remains in the store alongside the new one
2. The **environment hash changes**, so every component whose runtime includes it gets a new instance identity — automatic, not a human remembering to bump something
3. The registry knows which artifacts were built against which engine instance; survival is a recipe-compatibility question the machine answers, never an assumption
4. Because both closures coexist, old-engine and new-engine instances run **side by side as A/B arms** — the engine upgrade goes through the same promotion gate as any component change

This closes the "version pin without environment pin" failure (Feast skew) from the prior-art avoid list.

### The carve-outs, all substrate or build-phase

- **NAR hashing as a hash format** for directory-shaped artifacts — used without the store, therefore with no coupling
- **`systemd.services.<name>.confinement`** (`enable`, `mode = "full-apivfs"`) as the substrate implementation of machine service #2 — FS-level deny-by-default, per-arm process
- **Declarative `nixos-containers` with `privateNetwork = true`** for the network namespace that unit confinement does not cover
- **`lib.evalModules`** as one of three build-phase implementation candidates for the Static Mutation Validator — see `wiring-spec-and-validation.md` for the mandatory hardening rules

## What to Avoid

- **The Nix store as the artifact store.** Full copy per distinct artifact (~4.7× the hash-only time plus 100% of its size), GC roots to manage — and the content address is obtainable without it (`nix hash path`, ~1.3 GB/s, zero residency).
- **Store paths as identity.** They close over the store directory and the artifact name. Not SA-1. Second identity vocabulary.
- **Derivations as the mutation or promotion mechanism.** Requires generated Nix from the mutation operator; the build-time model does not fit a long-lived query-serving part.
- **The Nix build sandbox as the runtime isolation domain.** Build-time only. A sandbox-regime part is a service, not a build.
- **Fixed-output or impure derivations for index artifacts.** FODs need the hash in advance (impossible for LLM output); impure derivations *cannot be content-addressed* — the manual states it outright.
- **Flake registry / `flake.lock` as the alias table.** Registry rewrite is not atomic, resolution is order-dependent first-match, repoint does not propagate (the lock freezes it), the lock bakes in an mtime, and evaluating a wiring *writes* the lock — changing the artifact's own hash.
- **`nix flake check` as a gate.** A flake whose outputs are entirely `throw` prints "all checks passed!", exit 0.
- **Store-based lineage tooling** (`diff-closures`, `why-depends`, `path-info`). `nix store add` records no references, so `why-depends` reports "does not depend on" for an artifact literally containing the target's path. SA-1 is also unrepresentable: `name@version` → "name contains illegal character '@'".

## Constraints

- Measured on host `legion` (Nix 2.34.8, `auto-optimise-store` on): hash-only 192 ms / 256 MB (~1.33 GB/s); `nix store add` 901 ms first time (~284 MB/s); identical re-add 204 ms (dedup, same path, no copy); alias repoint 1.38 ms
- Unit confinement is **file-system level only** — "This doesn't cover network namespaces" per the option documentation
- The entire modern `nix` CLI is behind the experimental `nix-command` flag; stable-CLI equivalents (`nix-store --add`, `nix-hash`) are not
- Nix has no evaluation timeout and no evaluation memory cap

## Origin

Synthesized from spike 004 (verdict + two amendments).
Source files in `sources/004-nix-leverage/` — NIX-LEVERAGE.md (per-question findings, adopt/avoid, falsifiers), NIX-WIRING-SWEEP.md (8-family sweep, 107 candidates, attractive-failures table), `bench.sh` and `modtest/` (the measurements).
