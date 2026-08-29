---
name: spike-findings-rag-graph-vector-raw
description: Implementation blueprint from spike experiments. Requirements, proven patterns, and verified knowledge for the RAG modality-swap system model (Databasise/Sourcerer). Auto-loaded during implementation work.
---

<context>
## Project: RAG Graph Vector Raw

System-model project: determine whether Databasise's RAG engine (stock LightRAG + Cozo plugin, inside the Sourcerer GUI) can be re-cut into an agnostic machine + fitting + versioned components, where any modality is a swappable wiring, several run in parallel for side-by-side comparison on our own corpus, harnesses stack over modalities, and improvement is a version operation (branch → A/B → promote). Deliverable is design documents; code only as spikes.

**The architecture is selected.** Spike 003 chose **D4 One Machine** and ruled that candidate D's two-regime structure collapsed — D4 is candidate B with the amendments the evidence forced. There is one executor, no sandbox regime, and no `regime` field in the contract. Start from `references/selected-architecture.md`.

**Falsifier 1 has been run.** Spike 005 (the laundering test, runnable `taint.py`, 12 cases) measured the taint rule sound and falsified the argument that justified it. The selection survives on a third artifact scope — see the spike-005 requirements below before relying on any artifact-write rule.

Spike sessions wrapped: 2026-08-10 (spikes 001, 002, 004, 003, then 005)
</context>

<requirements>
## Requirements

- Decompose below the modality: modality = index recipe × query wiring; never port monoliths
- Universal core `ingest` + (`retrieve`|`answer`); everything else declared capabilities, machine-ENFORCED (deny-by-default)
- Every component is `name@version`, immutable, lineage-tracked; instance identity closes over `(name@version, config_hash, dependency_ids)`; improvement = branch → A/B → promote/rollback
- Recipe identity = content hash of resolved inputs including embedder identity (SA-1); sub-recipe stamps chunker/extraction/embedder (SA-2)
- **Eval infrastructure before architecture**: eval bundle@version + promotion gate (A/A null, significance, confirmation, hard-gate regressions)
- Budget machine-enforced over the whole execution incl. ingest; traces name instance hashes
- Harnesses wrap any modality, stack, selectable; runtime-arity fan-out needs a contract home
- Bi-temporal + contradiction stay buildable (Cozo Validity or Graphiti lift); Sourcerer REST/MCP seam stays modality-agnostic
- `model-weight-access` modalities declared out of scope; never depend on live RAG frameworks (vendor pinned tags)
- Benchmarks never settle decisions — only local measurement; Opus/Sonnet for subagent work, Fable only for integration/judgment

Added by spike 004:

- **Wirings are JSON with no evaluation semantics** — never Nix source, never any format the validator must sandbox; the mutation operator emits JSON only
- **`config_hash` = RFC 8785 (JCS) over the author-supplied input JSON**, never over a tool's normalized output; no ints outside int64; `1` ≡ `1.0`
- **Arm deltas are RFC 7386 merge-patch** for additive/overriding changes and **RFC 6902 for subtraction** (amended by 003 — 7386 alone cannot fail-close a removal); a differing component-kind tag replaces the whole `kind` subtree
- **The validator returns all violations at once with JSON-Pointer paths**, and reports cycles as data (cyclic wirings are legal)
- **Socket wiring is a partial order over named nodes** (`deps` + topological sort), never a total order by priority; node ids are positions, never instance identities
- **Component kind is a tagged sum** stated in portable vocabulary (serde external tagging / pydantic discriminated unions)
- **Nix is substrate-only** — it names nothing in the model; NixOS hosts the system and Nix builds the software, while the machine builds the indexes
- **Ledger/projection split**: the promotion ledger is durable and the active pointer is derived from it; running an arm never appends to the ledger

Added by spike 003 (architecture selected):

- **One machine, no sandbox regime, no `regime` field** — a foreign engine is a node of `opaque` kind in the same wiring, same executor, same trace schema, same identity tuple, same gate
- **Depth is computed by the validator, never declared** (`{opaque, evidence, stage}` per node); **effective depth = min over transitive `deps`**, and a node may write a shared artifact namespace only at `stage`
- **`execution_mode` is derived from declared `effects`, never requested** — capabilities buy containment cost, never freedom; the arm is always its own confined process
- **Promotion of a part = node → subgraph in place**, node id unchanged, therefore idempotent; **mutation promotion = atomic alias repoint**; a decomposition is gated on **parity, not gain**
- **SA-3 migration component** is the eighth primitive; **`ItemKind` is an open recipe-declared registry over a typed union** (evidence is a union, not a node)
- **Gate policy over mixed depth**: greatest common depth, one paired statistic there, cross-tier evidence may veto but never support, `insufficient-depth` names the missing instrument
- **Edge semantics are named in the contract** (exactly-once dataflow per run; fan-out concurrency a declared executor property that keys the A/A null)
- Spike 002's **"shallowest-denominator" condition is rejected** — comparison is defined at the greatest common depth of the two arms

Added by spike 005 (Falsifier 1 run — amends the artifact-write rule above):

- **Artifact scopes are three, not two**: `shared` (effective depth `stage` only, SA-1-addressed) · `quarantined` (any depth including `opaque`; instance-scoped, single-provenance, readable only by explicit pin, never SA-1-shareable, GC'd with the instance) · `self_storage` (any depth, private). **An opaque node may write `quarantined`, never `shared`.**
- **Without the middle scope the architecture forbids its own entry state** — an opaque ingest cannot write the shared index, and producing the index is what ingest is. Accepted cost: no artifact sharing in the middle state, so two modalities over an opaque index each re-index (candidate C's N× token cost), paid only until decomposition. Decomposition is how a part *earns* artifact sharing.
- **The decomposition order is the reverse of what spike 003 assumed**: spike 001 [code-verified] — the query path is already component-shaped and decomposes **first**; the index side is the entangled ~1,786-line side and stays opaque **longest**. Any reasoning that assumes a clean ingest lane is falsified.
- **The taint rule itself is measured sound** — confirmed on opaque→stage chains, non-adjacent fan-in through a sibling, `evidence`-tier propagation, and non-over-blocking of parallel lanes; decomposition credit survives the artifact boundary (a decomposed query run reading an opaque-produced index still computes `stage` throughout).
- **Unmeasured**: cross-run *reads* of a quarantined artifact. `taint.py` models within-wiring dep taint only, so whether pinning a quarantined artifact constrains the reader's shared writes is an open contract decision, not a settled one.
</requirements>

<findings_index>
## Feature Areas

| Area | Reference | Key Finding |
|------|-----------|-------------|
| **★ Selected architecture** | references/selected-architecture.md | **Start here.** The frozen contract skeleton: one machine, computed depth, effects-derived containment, the taint/blast-radius rule, gate policy, promotion and migration, opaque-node admission. Direct input to SPIKE-PLAN step 8 |
| Databasise engine reality | references/databasise-engine-reality.md | Engine = stock LightRAG 1.5.4 + one Cozo plugin; fitting seam already exists one level low; temporal features designed-but-unbuilt; parity harness = rig precedent |
| **Architecture selection** | references/architecture-selection.md | **SETTLED — D4 One Machine selected AND D collapsed to B-with-amendments (the same act).** Why the regime had no work left; what each losing variant proved; the three falsifiers, one of which outranks the selection |
| Fitting contract & safety | references/fitting-contract-and-safety.md | Five load-bearing contract clauses; six self-improvement machine services; prior-art adopt/avoid (nothing does all four; novel seam = versioned node identity in declared graphs) |
| **Wiring spec & validation** | references/wiring-spec-and-validation.md | Wirings are JSON with no evaluation semantics; RFC 8785 identity over the input; validator returns all violations at once with cycles as data; arms are merge-patch; promote = alias repoint with ledger/projection split |
| **Nix substrate boundary** | references/nix-substrate-boundary.md | Nix rebuilds the machine, the machine rebuilds the indexes; store paths are never identity; carve-outs are NAR hashing, systemd confinement, nixos-containers, and evalModules as one validator candidate |
| **Laundering test (Falsifier 1)** | sources/005-laundering-test/README.md | **PARTIAL — the rules are sound, the argument for them is dead.** Taint measured correct; the base blast-radius rule forbids the port's own entry state; repaired by the `quarantined` scope. Run `python3 taint.py` (12 cases, exit 0) to reproduce |

## Source Files

Original spike documents preserved in `sources/001-modality-swap-viability/`, `sources/002-system-architecture-model/` (CANDIDATES, ANATOMY-REVIEW, three RT files, PRIOR-ART, GAP-SWEEP, SYNTHESIS), `sources/004-nix-leverage/` (NIX-LEVERAGE.md, the 8-family NIX-WIRING-SWEEP.md, the two-plane note, plus runnable `bench.sh` and the `modtest/` validator prototype), `sources/003-d-variants/` (BRIEF, the four independent variant drafts D1/D2/D4/D5, RED-TEAM, COMPLIANCE, SELECTION — 3,179 lines; SELECTION carries the spike-005 AMENDMENT at its end), and `sources/005-laundering-test/` (README plus the runnable `taint.py`).

The four variant documents are preserved deliberately: **losing variants record the roads not taken and the conditions under which they would win again.** D1 in particular is the design to revisit if Falsifier 1 fails.

Full wiring design draft: `.planning/architectures/WIRING-SPEC-DRAFT.md`.
</findings_index>

<metadata>
## Processed Spikes

- 001-modality-swap-viability
- 002-system-architecture-model
- 004-nix-leverage
- 003-d-variants
- 005-laundering-test

All spikes processed. The architecture is selected and Falsifier 1 has been run; the next project step is SPIKE-PLAN step 8 (write the fitting contract spec) from `references/selected-architecture.md`, whose §3 and §8 already carry the spike-005 amendment.
</metadata>
