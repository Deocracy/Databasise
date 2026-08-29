---
title: Compliance Verification — spike 003 D-variants
spike: 003
date: 2026-08-10
role: adversarial verification of four self-certified DQ passes
standard: D-VARIANTS/BRIEF.md §2 (settled set) and §3 (disqualifiers), verified against sources not against the brief's summary
status: VERIFICATION — not a ranking, not a quality judgment
---

# Compliance Verification — spike 003 variants

All four variants self-certified passes on all five disqualifiers. This document tries to break each claimed pass.

Grades are strict: **CONFIRMED** = the document describes a mechanism that demonstrably satisfies the requirement. **ASSERTED** = the pass is claimed but the mechanism is missing, hand-waved, or does not entail the claim. **VIOLATED** = the document describes something that breaks the requirement. **UNCLEAR** = genuinely underdetermined by the text.

Sources consulted directly, not through the brief: `.planning/notes/two-plane-separation.md`, `.planning/research/GAP-SWEEP.md` §3.8/§4.1, `.planning/research/NIX-LEVERAGE.md` (Q8/Q9/Q10), `.planning/architectures/WIRING-SPEC-DRAFT.md`, `.planning/spikes/MANIFEST.md` Requirements, `.claude/skills/spike-findings-rag-graph-vector-raw/references/*.md`.

---

## Summary table

| Variant | DQ-1 executor primitives | DQ-2 two-plane | DQ-3 second identity vocab | DQ-4 environment-pinned identity | DQ-5 no evaluation semantics |
|---|---|---|---|---|---|
| **D1** Two Kingdoms | CONFIRMED | CONFIRMED | CONFIRMED | **ASSERTED** | CONFIRMED |
| **D2** Instrument Bus | CONFIRMED | CONFIRMED | CONFIRMED | CONFIRMED | **UNCLEAR** |
| **D4** One Machine | CONFIRMED | **ASSERTED** | CONFIRMED | CONFIRMED | **UNCLEAR** |
| **D5** Actor Kernel | **ASSERTED** | CONFIRMED | CONFIRMED | CONFIRMED | CONFIRMED |

No cell is VIOLATED. Nothing found disqualifies a variant. Four cells are soft, each repairable by a named addition of one to three sentences.

---

## Per-variant findings

Only non-CONFIRMED cells are argued. CONFIRMED cells are listed at the end of each variant with the load-bearing citation, so the reader can check that the confirmation was actually earned.

### D1 Two Kingdoms

**DQ-4 — ASSERTED.** Kernel-side identity is correct and explicit: `config_hash` over author-supplied JSON with the environment hash included, RFC 8785 canonicalized, `1 ≡ 1.0`, no ints outside int64 (`D1-two-kingdoms.md:466`, restated `:334`, `:436`). The failure is on the sandbox side, and it is exactly the failure shape the task flagged — identity that carries the environment hash where it is minted for kernel components and loses it for the foreign/opaque population.

D1 defines sandbox part identity as `(part_name@version, manifest_hash, resolved-dependency-set digest)` and glosses it as "**a content digest of the declared closure**, not a path" (`:393`, emphasis added). The DQ-4 row then asserts equivalence: "a sandbox part's identity includes its full resolved dependency-set digest, which is the same requirement expressed for an opaque engine" (`:394`).

The equivalence is asserted, not demonstrated, and the word `declared` is the evidence against it. A digest over a *declared* dependency closure is a digest over what the manifest says the part depends on — that is a version pin. The environment hash exists precisely to catch the case where the version pins are identical and the built environment is not; MANIFEST records it as killing "Feast-style version skew" (`.planning/spikes/MANIFEST.md:35`), and `references/nix-substrate-boundary.md:34-41` gives the intended mechanism: an engine update changes the closure, so *every* instance whose runtime includes it mints a new identity without a human bump. A declared-dependency digest does not move when the interpreter, native libraries, or model files move underneath it. [inference, on `[docs-verified]` source text]

The contrast inside the lineup is the clearest evidence that this is a real gap rather than a wording quibble: D2 says the adapter's `config_hash` "covers the *whole external closure*" (`D2-instrument-bus.md:194`, `:435`); D4 says "a foreign engine's whole closure is its environment hash, so `lightrag-engine@1.5.4` built against a different Python or CUDA is a different instance automatically" (`D4-one-machine.md:339`); D5 says "a confined unit's closure is part of the environment digest of the actor it hosts" (`D5-actor-kernel.md:463`). Three variants state the runtime closure. D1 states the declared closure.

*What would resolve it:* one clause stating that a sandbox part's dependency-set digest is computed over its **resolved runtime closure** (interpreter, native libraries, model files, container image) rather than its declared dependency list. D1's own jail-policy machinery already materializes that closure per confined unit, so the field exists; only the identity clause needs to say so.

**Also noted, not a DQ finding.** D1's instrument table says the validator "runs at load, never per query" (`:263`) while the same table row and the execution model say it "also validates planner-emitted plans" (`:261`, `:186`) — which is necessarily per query. This is an internal inconsistency in the document, not a compliance failure; the per-query validation is the stronger behavior and is what D1's DQ-1 and DQ-5 answers rely on.

**Confirmations.** DQ-1 (`:185-187`, `:391`): `fan_out`/`join` as node kinds with static or `from_input` runtime arity and multiplicative budget accounting; planner versioned, emitted plan recorded verbatim as trace data, never registered / aliased / ledgered — separate lifecycles stated explicitly; non-adjacent fan-in falls out of `deps` being a partial order, with the `assemble` + `generate` eval case drawn (`:178`). This is a mechanism, not a naming. DQ-2 (`:392`): the strong form — "Components receive resolved inputs from the executor and cannot address the registry at runtime; the active-wiring alias is resolved at load, never per node." DQ-3 (`:393`): store paths, filesystem locations, import paths and systemd unit names named as deployment labels only. DQ-5 (`:395`, `:186`, `:332`): JSON everywhere including planner-emitted plans, which are explicitly validated by the same validator.

### D2 Instrument Bus

**DQ-5 — UNCLEAR.** The wiring format itself is clean and the answer is thorough on three of the four surfaces the disqualifier covers: wirings are JSON, the adapter kind's `config` is "opaque JSON validated against the adapter's declared schema and never evaluated by the validator", the mutation operator emits JSON only, and the `evalModules` wrapping rule is stated (`D2-instrument-bus.md:437`). Arm deltas are RFC 7386 merge-patch, JSON only (`:374`).

The gap is the planner-emitted plan. D2 says a `planner` node "emits a runtime graph" recorded as trace data (`:180`, `:158`) and never states what that emitted object *is* as a format, nor that anything validates it before the executor runs it. The DQ-5 answer at `:437` does not mention planner plans at all. This is the one surface where an LLM authors a structure that the machine then executes, so it is the surface where "no evaluation semantics" matters most, and it is left underdetermined. Nothing in the text suggests the emitted plan has evaluation semantics — this is a gap in the text, not evidence of a violation.

*What would resolve it:* one sentence in the execution model declaring the emitted plan's format (JSON data over the declared node-kind alphabet) and naming what checks it before execution. D1 supplies exactly this sentence at `D1-two-kingdoms.md:186`.

**Confirmations.** DQ-1 (`:179-181`, `:429`): `fanout`/`join` as tagged-sum node kinds with arity as an input socket driven by a planner's output — which gives runtime arity a home, the thing `references/architecture-selection.md:27` records as expressible in no candidate as drawn; planner versioned with the plan as trace data and separate lifecycles; non-adjacent fan-in from `deps` as a partial order. The adapter caveat ("an *adapter* hosts none of these internally") is a correct statement about parts, not about the executor, and DQ-1 tests the kernel style. DQ-2 (`:146`, `:431`): the strongest formulation in the lineup — the bus is touched from the execution plane at exactly two load-time moments (validation admits or refuses; ledger projection supplies the active pointer) and is "**write-only** from the execution plane's perspective" during a run. D2 also names the specific temptation (adaptive arm allocation reading the running scoreboard mid-bundle) and forbids it, which is the mark of a mechanism rather than an assertion. DQ-3 (`:433`): SA-1 throughout; `upstream_ref` explicitly provenance-only and "never used for resolution"; an adapter's internal addresses declared as a part-local projection with an auditable bijection. One unspecified field worth hardening at contract time: the adapter kind carries a `runtime_ref` (`:517`) that is never defined; if that resolves to a store path or filesystem location it must be a locator inside `config`, never an identity — the document never treats it as identity, so the cell stands. DQ-4 (`:194`, `:435`, `:490`): the strongest DQ-4 statement of the four — `config_hash` covers the whole external closure for an adapter, so "an engine upgrade beneath an adapter changes its instance hash automatically rather than depending on someone remembering to bump a label". Decomposition increments produce ordinary kernel components, so identity is not lost down the decomposition tree.

### D4 One Machine

**DQ-2 — ASSERTED.** D4's DQ-2 row states that the artifact plane "holds component versions, recipes, index artifacts, wiring specs, traces, lineage, and is **read-only to components at runtime**" (`D4-one-machine.md:337`).

That guards the wrong direction. The rule in `.planning/notes/two-plane-separation.md:32` is "The executor executes; the artifact plane records. **No component may treat the artifact plane as a runtime control channel.**" A control channel is a *read*: a component reads plane state and branches on it. Granting components runtime read access to the artifact plane is the enabling condition for the prohibited behavior, not a defense against it. The stated mechanism therefore does not entail the claimed pass. [docs-verified against the source note; inference on the consequence]

The other three variants all guard the read direction explicitly and D4 is the only one that does not — D1 `:392` ("cannot address the registry at runtime"), D2 `:431` ("write-only from the execution plane's perspective... nothing flows out"), D5 `:277` ("A wiring actor can read what it was handed; it can never query the plane during a run"). The uniformity of the other three is what makes D4's phrasing look like a slip rather than a position.

D4 describes no component that actually branches on artifact-plane state, which is why this is ASSERTED rather than VIOLATED. Its opaque-node hazard analysis in the same row is correct and well-handled ("registered in AREG as a row... the machine never reads it as control, only as provenance"), which shows the author had the right test in mind for the adjacent case.

*What would resolve it:* replace "read-only to components at runtime" with the D1/D2/D5 form — artifact-plane values are resolved by the executor before the run and passed in; components cannot query the registry, ledger, scoreboard, or artifact registry during a run.

**DQ-5 — UNCLEAR.** Same shape as D2, same one-sentence fix. Wirings are JSON; the mutation proposer emits "JSON only, never code, never a format with evaluation semantics" (`:293`); kind is a tagged sum; arm deltas are merge-patch with subtractive operations fail-closed (`:340`). The planner-emitted plan is described only as "a sub-query DAG as a *value*" that "the executor executes" (`:161`), with no format declared and no validation step described; the DQ-5 row (`:340`) does not cover it. In an executor where every other structure is JSON the intent is inferable, but DQ-5 asks about planner-emitted plans specifically and the text does not answer.

*What would resolve it:* declare the emitted plan's format and name what validates it before execution.

**Confirmations.** DQ-1 (`:159-163`, `:336`): `fanout` with runtime arity and multiplicative budget accounting, `join` with the two named socket signatures, `fixpoint` taking the loop away from iterative components; planner emits a plan as a value executed under a derived budget and recorded as trace data, never registered, never aliased — separate lifecycles by construction; non-adjacent fan-in as the default case with the `deps: ["retrieve", "generate"]` example. Cycles reported as data (`:163`). DQ-3 (`:338`): SA-1 everywhere; opaque nodes' internal paths confined and absent from wiring, registry and trace; AREG stores machine-minted namespace handles, never paths; and the one place a second vocabulary could creep in is handled correctly — "the environment hash may be *derived from* a Nix derivation hash, but it is a field value inside `config_hash`, not an addressing scheme", which is exactly the boundary `NIX-LEVERAGE.md:218` draws. DQ-4 (`:295`, `:339`): full canonicalization rules stated including int64 and `1 ≡ 1.0`; and the strongest statement of the opaque-part case — a foreign engine built against a different Python or CUDA is a different instance automatically.

### D5 Actor Kernel

**DQ-1 — ASSERTED, on the ephemeral-subgraph clause only.** Fan-out/join and non-adjacent fan-in are CONFIRMED (below). The ephemeral-subgraph clause is where the mechanism does not entail the claim.

DQ-1 requires the kernel to host "a planner emits a **runtime graph** per query". GAP-SWEEP §4.1 names the target shape precisely: "Plan\*RAG / TreeRare — the runtime-planned **DAG**", where "an LLM emits a fresh sub-query DAG per query" (`.planning/research/GAP-SWEEP.md:293-294`). A sub-query DAG has edges: sub-query C consumes the output of sub-query A but not B, and which edges exist is a per-query fact.

D5's mechanism is a `SpawnRequestList` — "a list of `(template_id, config)` pairs over templates already declared, validated, and capability-bounded in the wiring" — and the document's own summary of it is the problem: "**There is no runtime graph validation because there is no runtime graph — there is a runtime *multiset over a static alphabet*.**" (`D5-actor-kernel.md:187`). Each spawn request is checked against three things: the template exists, the config validates, the count is within the declared `max` (`:187`). None of those is an edge. The `sends` relation that supplies edges is declared at the *template* level and is static (`:150`, `:158`), so it says "a seed may send to an assemble", not "seed instance #3 feeds assemble instance #1".

So D5 either (a) cannot express a per-query inter-sub-query dependency structure, in which case the sharpest stress test in GAP-SWEEP §4.1 is not hosted; or (b) can express it via the typed unforgeable address passing D5 describes elsewhere — "received in a message field whose schema declares the mailbox type" (`:230-232`) — in which case a runtime graph *does* exist, it is assembled by handing addresses at spawn, none of the three spawn checks looks at it, and the document's central advantage claim ("no LLM-authored *structure* ever needs runtime validation", `:433`) is overstated by exactly that structure. The document never connects (b) to the DQ-1.2 answer, and never records the emitted plan's *edges* as plan structure — only the `SpawnRequestList` is recorded verbatim (`:187`, `:413`).

The lifecycle split itself — planner versioned, emitted list recorded as trace data, separate lifecycles, run reconstructable — is genuinely satisfied and is the part of §4.1's paper-test D5 answers well. The unhosted part is the graph. [inference, on `[docs-verified]` source text]

*What would resolve it:* state whether the `SpawnRequestList` carries inter-instance edges. If it does, extend the three spawn checks to cover them and record them in the trace as plan structure alongside the list, and soften the "no runtime structure needs validation" advantage claim accordingly. If it does not, walk GAP-SWEEP §4.1's Plan\*RAG shape explicitly and show the decomposition it forces — this is adjacent to D5's own falsifier 1 (`:516`), which tests address lookup by name but not per-query plan edges.

**DQ-2 — CONFIRMED, and the stated condition is both load-bearing and met.** The task asked for this specifically, so both halves are checked.

*Is the condition load-bearing?* Yes, and D5 is right about why. The rule is: kernel services (registry, artifact registry, ledger, validator, eval bundle, reindex planner) have no mailbox a wiring template may name; artifact-plane values reach an actor only as spawn-time frozen resolutions carried in the spawn message (`:277`, restated as contract item 8 at `:541`). In an actor model where every peer is addressed by mailbox, `ask(ledger, "what is active?")` is the natural idiom, and a component branching on the reply is verbatim the prohibited "artifact plane as a runtime control channel". Remove the rule and the model's own vocabulary produces the violation by default. D5 states this outright: "Without that rule an actor kernel merges the planes and is disqualified" (`:461`). The condition is not a hedge; it is the mechanism.

*Is the condition met?* I found no place in the document where a wiring actor is given a kernel-service mailbox or queries the plane mid-run. The six services are listed as kernel-owned and "unreachable from the wiring's mailbox namespace" (`:337`); the diagram routes services to the root supervisor and the validator to load (`:104`, `:113`), and every execution-plane arrow into the artifact plane is a trace write (`:103`). Two places stress it, and both survive:

- *Spawn-time artifact resolution* (`:374`, `:383`). Artifact bindings — including the query encoder's `reads_space` versus the namespace's `space_id` — resolve at spawn, which is during a run, and the namespace metadata lives in the artifact registry. So artifact-plane state does influence runtime control flow (a failed check refuses the spawn). But the resolution is performed by the kernel at spawn and frozen for the actor's lifetime; no component queries the plane. The two-plane rule is scoped to components (`two-plane-separation.md:32`), so this is inside the letter of the rule. It is a real narrowing of contract clause 1 and D5 states it as one — see settled-set findings below.
- *Reference counting over spawned instances* (`:496`). Direction is execution → artifact plane, i.e. recording. Fine.

**Confirmations.** DQ-1 fan-out/join (`:177-179`): send N / await N with a declared cap the validator *requires* (guard-presence, correctly distinguished from a proved bound) and budget as a capability token split at spawn, which makes GAP-SWEEP §3.7.2's multiplicative accounting structural rather than an extension. D5 hosts the primitive without naming it a node kind; the disqualifier tests hosting, so the semantics are immaterial. DQ-1 non-adjacent fan-in (`:193-195`): a mailbox accepting a union of message types with two declared senders — and the honest note that verification is one grade weaker than a declared graph (expression native, arrival and ordering not statically known) is disclosure, not a gap in hosting. DQ-3 (`:462`): the disqualifier's mailbox-address surface is answered head-on — addresses are runtime capabilities, not recorded as identity in traces, not stable across runs, not lookupable by name; unit names, socket paths and store paths name nothing in the model. DQ-4 (`:290`, `:463`): the only variant that shows the environment pin propagating down a spawn tree by construction — `instance_hash = H(template_instance_hash, JCS(spawn_config), parent_instance_hash, ordinal)`, where `template_instance_hash` carries `config_hash` and therefore the environment digest. This is the exact failure shape the task flagged ("loses it in a spawned child") and D5 is the variant that closes it explicitly. DQ-5 (`:464`): JSON; and it is the only variant that answers the routing/supervision surface — "routing and supervision strategies are enumerated tagged sums (`{round_robin:{}}`, `{by_message_type:{...}}`, `{restart:{max_restarts:3}}`), and spawn caps are integers or named machine-owned budget references — never expressions."

---

## Settled-set violations

Checked per variant against BRIEF §2 and `MANIFEST.md` Requirements. Stated explicitly where nothing was found.

### D1 — none found

All settled items present and correctly stated: SA-1/SA-2 (`:289`, `:291`), `config_hash` over author-supplied JSON RFC 8785 with int64 and `1 ≡ 1.0` (`:466`), environment hash in `config_hash` (`:334`, `:436`), merge-patch arms (`:332`), validator all-violations-at-once with JSON-Pointer paths and cycles as data (`:333`), `deps` as a partial order (`:187`), tagged sum in portable vocabulary (`:157`), the five clauses (`:435-439`), the six services (`:254-261`), ledger/projection with "running an arm does not append" (`:342`), promotion as atomic alias repoint (`:343`), eval-first sequencing accepted and not re-litigated (`:265`), Nix named only as substrate implementation (`:206`), `model-weight-access` declared out of scope (`:472`), no live RAG-framework dependency, no dependency on the three experimental Nix features.

*Noted for the ranker, not a violation:* D1 explicitly retires amendment C-1 from RT-upgradability (the refusal to compare across engines with differing embedder identity) at `:279`, arguing the refusal only protected the stage-tier comparison D1 already refuses. C-1 appears in neither BRIEF §2 nor MANIFEST Requirements, so it is not settled and D1 is entitled to argue it — but the retirement is a live decision the selection step should ratify or reject rather than inherit silently.

### D2 — two omissions, no contradictions

- **The two pinned canonicalization rules are absent.** D2 names RFC 8785 three times (`:194`, `:375`, `:490`) and never states "no integers outside int64" or "`1` ≡ `1.0`". BRIEF §2 (`:41`) and `references/wiring-spec-and-validation.md:39` pin both to the canonicalization, and `NIX-LEVERAGE.md:181` records the measured reasons (out-of-int64 integers silently becoming doubles; `{"tau":1}` and `{"tau":1.0}` hashing differently). Omission, not contradiction — D2 says nothing incompatible with them.
- **`model-weight-access` is not declared out of scope.** BRIEF §2 (`:82`) makes it a declared non-goal to be named rather than left as a gap; `references/fitting-contract-and-safety.md:22` says "state it in the verdict". D1 (`:472`), D4 (`:101`) and D5 (`:116`) all name it; D2 is the only variant that does not. Omission.
- **An LLM-authored plan reaches execution with no described validation** (`:180`). See systematic issue 2.

*Not a violation:* D2 uses the component **instance** hash in cache keys (`:260`, `:376`) where the settled item says "cache keys include component version" — strictly stronger, and the failure it prevents (cache poisoning) is prevented a fortiori. D2's reassignment of the containment axis from the sandbox to the arm runner is disclosed at `:25` and is exactly the move BRIEF §1 authorizes ("if your assigned position forces an incoherence, say so... naming what you changed and why").

### D4 — none found

Every settled item is present, including the two the others most often drop: the full canonicalization rules with int64 and `1 ≡ 1.0` (`:295`), and `model-weight-access` as declared-not-hosted, drawn on the anatomy (`:101`). Also correct: SA-1/SA-2 (`:252`, `:425`), environment hash (`:295`, `:339`), merge-patch with subtractive fail-closed (`:340`), validator behavior (`:224`, `:294`), partial order with node ids as positions never instance identities (`:155`), tagged sum in portable vocabulary (`:155`, `:416`), five clauses (`:376-380`), six services (`:219-224`), ledger/projection and no ledger append on a run (`:196`, `:302`), alias repoint (`:303`), eval-first sequencing (`:219`), Nix as substrate only with the contract "behavioral and names no tool" (`:224`).

*Noted:* the S2 narrative makes "Nix-packaged" read as a precondition of admitting an opaque node (`:279`), while the contract skeleton's admission conditions name no Nix (`:424`). The contract text governs and is correct; the narrative phrasing is loose.

*And:* an LLM-authored plan reaches execution with no described validation (`:161`). See systematic issue 2.

### D5 — two disclosed narrowings and two omissions

The narrowings are real and are the only place in the lineup where a variant materially reduces a settled item. Both are disclosed in the document's own position paragraph (`:14`), argued, and priced — this is the honest form of the move, not a covert violation, but the selection step must accept them explicitly.

- **Contract clause 1 / WIRING-SPEC-DRAFT §4 check 5 — `provides` weakens from a load-time check to reachability plus a runtime hard gate** (`:257-259`, `:504`, `:542`). The settled clause requires declarations to be machine-enforced preconditions with the validator running before execution and failing closed (`references/fitting-contract-and-safety.md:11`; `WIRING-SPEC-DRAFT.md:91`). Under D5 a wiring can be fully valid and emit no answer; the defect is caught by a rig run rather than by the validator. D5's counter-argument (`:504`) — that the clause requires declarations checked before execution, not that the run be statically total — is reasonable but does not fully cover this case, because `provides` is a declaration in the wiring and its satisfaction is what moves.
- **The query-encoder `space_id` check moves from load to spawn, i.e. from before execution to during it** (`:383`, `:504`). `WIRING-SPEC-DRAFT.md:88` lists socket-type conformance across every `deps` edge as a load-time check, and D1 (`:302`), D2 (`:333`) and D4 (`:262`, `:294`) all keep it there. It still fails closed in D5, but it fails during a run.
- **The two pinned canonicalization rules are absent** — D5 names JCS (`:130`, `:285`, `:408`) and incorporates WIRING-SPEC-DRAFT §2–§5 by reference, never restating int64 or `1` ≡ `1.0`. Same omission as D2.
- **Subtractive fail-closed is not restated**, only incorporated by reference at `:130`. Given systematic issue 1 below, this matters more than a bare omission normally would.

Everything else is present: SA-1/SA-2 (`:368`, `:372`), environment hash including down the spawn tree (`:290`, `:463`), merge-patch arms (`:407`), validator all-violations/JSON-Pointer/cycles-as-data (`:409`), partial orders over named templates (`:158`), tagged sums (`:130`, `:238`, `:464`), the five clauses (`:504-508`), the six services (`:341-346`), ledger/projection and no ledger append on a run (`:345`, `:413`), alias repoint (`:319`, `:426`), Nix as substrate only with store paths naming nothing (`:301`, `:462`), `model-weight-access` non-goal (`:116`), no live RAG-framework dependency (`:452`).

---

## Systematic issues

### 1. All four inherit a requirement pair that is not satisfiable as stated — and it originates above them

BRIEF §2 (`:48`) reads: "**Arm deltas are RFC 7386 merge-patch.** ... Subtractive operations are fail-closed: a mistyped key errors, never silently no-ops."

RFC 7386 has no error case for removal. Its removal idiom is `{"key": null}`, which deletes the key if present and is a **silent no-op** if absent. Fail-closed removal is RFC 6902's property, and the sources say so explicitly:

- `WIRING-SPEC-DRAFT.md:100` — "**Removal is fail-closed by specification.** An operation that deletes a node or a key must error if the target does not exist. **RFC 6902 `remove` has this property**; subtractive mechanisms that treat an unknown key as a silent no-op do not."
- `references/wiring-spec-and-validation.md:51` — "**Removal errors on a missing target.** RFC 6902 `remove` has this; silent-no-op mechanisms do not." — sitting two sections away from `:57` "Arm = base wiring + **RFC 7386 merge-patch**".
- `NIX-LEVERAGE.md:182` and `MANIFEST.md:52` both say "RFC 7386 merge-patch (**or 6902**)" — the alternative that the brief dropped.

The brief compressed "7386 **or 6902**, and fail-closed removal is 6902's property" into "7386, and removal is fail-closed", producing a requirement that plain RFC 7386 cannot meet. All four variants restated the brief's form verbatim and none noticed: D1 `:332`, D2 `:262` and `:374`, D4 `:340`, D5 `:130` (by reference). [docs-verified]

This is the failure shape the task named — a constraint the brief compressed such that a variant honored the summary and missed the source — and it is the only one found. It is also cheap to fix, because it is a contract-wording problem rather than a design problem: the fitting contract must either specify RFC 6902 for arm deltas, or specify RFC 7386 **plus a named extension** in which a null-valued key whose target is absent is an error. The measured consequence of getting this wrong is on record: a one-character typo produced an arm that reported "reranker dropped" and shipped with the reranker still in it (`NIX-LEVERAGE.md:182`). No variant is penalized for this; the brief and the source summaries carry it.

### 2. Two of four execute an LLM-authored runtime plan with no validation step described

DQ-1 requires only that the planner be versioned and the emitted plan be recorded as trace data, and all four satisfy that. But contract clause 1 and `WIRING-SPEC-DRAFT.md:83` set a broader rule — the validator "runs **before execution**, on every wiring, including ones a mutation operator generated seconds ago" — and a planner-emitted plan is the same category of object: an LLM-authored structure the machine then executes.

- **D1** validates it: the emitted plan "passes through the *same* static validator as any mutation-authored wiring, against a restricted node-kind allowlist plus the caps the planner's own manifest declares" (`:186`).
- **D5** validates each spawn request against three pre-resolved facts (template exists, config validates, count within the declared cap) (`:187`) — narrower than D1's check, but a check.
- **D2** (`:180`) and **D4** (`:161`) describe the executor running the emitted plan with no validation step and no declared format.

This is the same root as the two UNCLEAR DQ-5 cells and has the same one-sentence fix. It is worth flagging as systematic because the split is 2-2 and because D5 identifies the underlying dilemma correctly (`:185`): a declared-graph kernel must either validate an arbitrary graph mid-run or accept an unvalidated structure. D1 chose the first and said so; D2 and D4 left the choice unmade.

### 3. Three of four independently reject a spike-002 condition the brief did not carry forward

`references/architecture-selection.md:20` lists among D's conditions: "cross-regime comparison honestly labeled shallowest-denominator." BRIEF §2 does not carry it into the settled set — it appears only as a named risk in §1.

D2 (`:23`, `:266`, `:285`), D4 (`:24`, `:238`), and D5 (`:26`, `:358`) each independently replace the regime label with a computed, machine-stamped evidence-depth field and argue that the shallowest-denominator collapse is a consequence of deriving depth from location rather than a fact about cross-regime comparison. D1 (`:24`, `:277`) accepts the condition and complies by deleting cross-regime deep comparison outright.

Three unconnected drafters converging on the same replacement is a signal, not a defect. Recording it here because the selection step should ratify or reject the condition explicitly rather than inheriting it as settled — it was never in the settled set, and three of four variants have now argued against it.

### 4. Minor shared omissions

- **The two pinned canonicalization rules (int64, `1 ≡ 1.0`)** appear in D1 and D4 and are absent from D2 and D5. They are settled (BRIEF §2 `:41`) and measured (`NIX-LEVERAGE.md:181`).
- **"Node ids are positions, never instance identities"** is stated explicitly by D4 (`:155`) and D5 (`:158`), and is only implicit in D1 (`:465`, as "id → instance") and D2 (`:152`). The rule has a measured failure behind it — keying nodes by instance identity silently drops a fan-out branch (`NIX-LEVERAGE.md:176`, `WIRING-SPEC-DRAFT.md:54`) — and should be explicit in the contract regardless of which variant wins.

Nothing else was found that all four got wrong the same way. In particular, all four correctly kept Nix out of the model, correctly treated a cyclic wiring as legal artifact-plane data rather than a plane merge, correctly placed all six machine services, correctly separated the ledger from its projection with "running an arm SHALL NOT append", and correctly kept the ingest path inside the budget enclosure with per-chunk provenance and the embedder-coupled-chunker hazard named. No variant was found satisfying a DQ in the query path and violating it in the ingest path, and none was found satisfying a constraint by renaming the violating thing.

---

## Verdict

**No variant is disqualified.** All twenty DQ cells are CONFIRMED, ASSERTED, or UNCLEAR; none is VIOLATED. Every soft cell is repairable by a named addition of one to three sentences and none requires a design change, so nothing here should remove a variant from the ranking.

**Cleared to be ranked without caveat: D2, D4.** Their soft cells are the same UNCLEAR — the planner-emitted plan's format and pre-execution check are undeclared — which is a documentation gap shared by half the lineup and traceable to a question the brief did not ask directly. Neither variant's design is implicated.

**Cleared to be ranked, carrying one caveat each: D1, D5.**

- **D1** — DQ-4 holds for kernel components and is ASSERTED for sandbox parts, because sandbox identity is a digest of the *declared* closure (`:393`) rather than the resolved runtime closure. This is a one-clause fix, but it should be fixed before D1's identity discipline is scored, because "every kernel run is completely attributable" is D1's central claim and its weakest identity surface is the population it most needs to hold at arm's length.
- **D5** — DQ-1's ephemeral-subgraph clause is ASSERTED, because the mechanism hosts a runtime multiset over a static template alphabet, not the per-query sub-query DAG GAP-SWEEP §4.1 names. This one is not a documentation fix: it is a question about the executor's expressiveness that D5 must answer either by extending the spawn checks and trace to cover inter-instance edges (and softening its "no LLM-authored structure needs runtime validation" advantage), or by showing that no target modality requires per-query plan edges. **D5's DQ-1.2 is currently its loudest advantage claim (`:189`, `:433`) and its softest verified cell — the ranking should treat that claim as unproven until resolved.**

**D5's conditional DQ-2 pass is real.** The condition (kernel services have no mailbox in the wiring namespace; artifact-plane values reach actors only as spawn-time frozen resolutions) is genuinely load-bearing — without it an actor kernel merges the planes by default, because the model's own vocabulary makes `ask(ledger, ...)` the natural idiom — and it is met throughout the document, with the one stress point (spawn-time artifact resolution) inside the letter of the rule and disclosed as a cost. It is correctly carried into the contract skeleton as item 8 (`:541`).

**One thing the ranking must decide rather than inherit.** Systematic issue 1 is a defect in the brief and the source summaries, not in any variant: "RFC 7386 merge-patch" and "subtractive operations are fail-closed" cannot both hold of plain RFC 7386. The fitting contract must resolve it — 6902, or 7386 plus a named error-on-absent-target extension — and until it does, all four variants' arm-delta mechanics inherit a measured failure mode.

---
*Verification pass, spike 003. Uncommitted. No variant document was edited. Every finding cites file and line; claims tagged `[docs-verified]` are checked against the named source text, `[inference]` marks a consequence drawn from it.*
