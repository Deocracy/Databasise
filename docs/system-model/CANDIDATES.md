# Candidate Architectures — Diagrams

**Status:** superseded — candidates A, B, and C are superseded by `SELECTION.md` (the D4 One Machine selection, with its spike-005 amendment); tracked at `SYSTEM-MODEL.md ## §ST`.

Four candidate architectures over the same component inventory, each a different position on the five tension axes (SYNTHESIS.md §7), scored later against the ten-goal rubric (ARCHITECTURE-RUBRIC.md). Read the shared anatomy first; every candidate reuses its vocabulary.

---

## 0. Shared Anatomy — how everything nests

The machine (Databasise) sits inside Sourcerer. Parts sit inside the machine. Components sit inside parts. Harnesses wrap parts.

```mermaid
flowchart TB
    subgraph SORC["SOURCERER (GUI - Tauri desktop)"]
        APPLETS["Wiki / Library / Graph applets"]
        SEAM["REST + MCP seam (modality-agnostic)"]
        APPLETS --> SEAM
    end

    subgraph MACHINE["DATABASISE (the machine)"]
        SEAM --> SEL["Selector: choose harness + modality per query"]

        subgraph HARNESS["Harness tier (optional, stackable)"]
            H1["CRAG-style corrective"]
            H2["Router / iterative"]
        end

        subgraph PARTS["Parts (modalities) = wirings of versioned components"]
            M1["LightRAG-local
            (recipe ER1)"]
            M2["HippoRAG2
            (recipe PP1)"]
            M3["code-graph
            (recipe TS1)"]
        end

        SEL --> HARNESS --> PARTS

        subgraph SERVICES["Machine services"]
            REG["Component registry
            name@version + lineage"]
            BUD["Budget enforcer"]
            TRACE["Trace collector
            (versions + tokens)"]
            RIG["Comparison rig"]
        end

        subgraph STORES["Stores"]
            KV["KV / linked-record
            (chunks, doc-status, caches)"]
            VEC["Vector
            (namespaces, score_all, multi-vec)"]
            GR["Graph (Cozo)
            (pointwise + bulk-export)"]
            LEX["Lexical / BM25"]
            BLOB["Opaque blob"]
        end

        subgraph CLIENTS["API clients (role-addressable)"]
            LLM["LLM roles:
            extract/filter/answer"]
            EMB["Embed / encode-multi"]
            RER["Rerank"]
        end

        PARTS --> STORES
        PARTS --> CLIENTS
        PARTS -.metered by.-> BUD
        PARTS -.emit.-> TRACE
    end
```

How a part decomposes, and where sharing happens:

```mermaid
flowchart LR
    subgraph RECIPE["Index recipe ER1@v2 (shared artifact)"]
        CH["chunker@1.2"] --> EX["llm-extractor@2.0
        (ontology: entity/relation)"] --> ART[("graph + vectors + KV
        provenance: ER1@v2")]
    end

    subgraph W1["Query wiring: lightrag-local@3.1"]
        S1["seed-selector@1.0"] --> E1["one-hop expander@1.1"] --> R1["degree ranker@1.0"] --> A1["assembler@2.2"] --> G1["generator@1.0"]
    end

    subgraph W2["Query wiring: pathrag@0.9"]
        S2["seed-selector@1.0"] --> P2["path-DFS scorer@0.3"] --> A2["assembler@2.2"] --> G2["generator@1.0"]
    end

    ART --> W1
    ART --> W2
```

One recipe, many wirings: PathRAG reuses LightRAG's index verbatim (code-verified). Both wirings share `seed-selector@1.0`, `assembler@2.2`, `generator@1.0` — a new modality here is two new components, not a system.

---

## Candidate A — "Stage Bus" (normalized pipeline machine)

**Position:** normalization total; extraction shared; parts are code with manifests filling fixed stage slots; temporal in Cozo (machine); comparison at every stage boundary.

```mermaid
flowchart TB
    Q["query"] --> SB

    subgraph SB["Stage bus (fixed slots, plain-data contracts)"]
        direction LR
        SEED["SEED
        slot"] --> EXPAND["EXPAND
        slot"] --> RANK["RANK
        slot
        (List ScoredNode to List ScoredNode)"] --> ASM["ASSEMBLE
        slot"] --> GEN["GENERATE
        slot"]
    end

    subgraph SWAP["Registered components per slot (any name@version)"]
        SEED2["vector-seed / entity-seed / bm25-seed"]
        EXPAND2["one-hop / PPR / path-DFS / none"]
        RANK2["degree / rerank / RRF-fusion"]
    end
    SWAP -.plug into.-> SB

    SB --> CMP["Stage-level comparison:
    diff any slot output
    between two wirings"]

    STORE[("All artifacts in machine stores
    (KV/vector/graph/lexical)
    temporal validity in Cozo")] --- SB
```

- **Wins:** deepest observability and comparison (diff *stages*, not just answers); maximal artifact sharing; cheapest LightRAG port (its 4-stage refactor maps 1:1).
- **Loses:** cannot express loops/branches (four of six agentic shapes unrepresentable); black-box parts (codebase-memory-mcp) and CAG don't fit slots; the slot vocabulary risks freezing today's paradigms into the machine.
- **Fits when:** the corpus of modalities stays pipeline-shaped and comparison depth matters most.

---

## Candidate B — "Conductor" (declared-graph engine)

**Position:** normalization default with blob escape hatch; extraction shared where declared-compatible; modalities are *declared graphs* of versioned opaque components the machine executes; temporal in both layers; comparison at node boundaries where normalized, answer-level otherwise.

```mermaid
flowchart TB
    Q["query"] --> EXEC

    subgraph EXEC["Graph executor (checkpoints, meters, records)"]
        direction TB
        N1["retrieve@2.1"] --> N2{"grade@1.0
        sufficient?"}
        N2 -- no --> N3["rewrite@1.3"] --> N1
        N2 -- yes --> N4["assemble@2.2"] --> N5["generate@1.0"]
    end

    MAN["Each modality =
    graph spec (JSON/DSL):
    nodes = name@version
    edges = data flow + conditions
    loops with machine budgets"] -.defines.-> EXEC

    EXEC --> TR["Trace: every node run
    = versions + tokens + IO"]
    BUDG["Budget object
    (steps, tokens, time)"] -.halts.-> EXEC

    MUT["Self-improvement:
    branch graph spec,
    mutate one node version,
    A/B both specs on rig"] -.operates on.-> MAN
```

- **Wins:** expresses all control-flow shapes (loops, branches, agent walks); versioning-native — the graph spec *is* the pinned, mutable, A/B-able artifact; budgets built into the executor; the natural substrate for self-improvement.
- **Loses:** highest machine complexity (an execution engine to build and debug); contract design for node boundaries is the hard intellectual work; opaque nodes tempt teams to stuff whole modalities into one node, quietly becoming Candidate C.
- **Fits when:** harnesses, custom modalities, and machine-driven mutation are first-class goals — which they are.

---

## Candidate C — "Federation" (capability broker over whole engines)

**Position:** normalization minimal; no shared extraction; parts are whole engines behind manifests; temporal is a part (Graphiti); comparison at evidence/answer level only.

```mermaid
flowchart TB
    Q["query"] --> BR["Capability broker
    (reads manifests, routes, meters)"]

    subgraph ENGINES["Federated parts (whole engines, self-contained allowed)"]
        E1["LightRAG server
        manifest: ingest/index/
        retrieve/answer"]
        E2["HippoRAG2
        manifest: ingest/index/
        retrieve/answer"]
        E3["codebase-memory-mcp
        manifest: ingest(repo)/
        retrieve only - no LLM"]
        E4["Graphiti
        manifest: ingest(stream)/
        retrieve/temporal"]
        E5["CAG
        manifest: ingest/answer
        - no index, no retrieve"]
    end

    BR --> E1 & E2 & E3 & E4 & E5

    FEED[("Shared corpus feed:
    machine-owned KV of
    chunks + doc-status only")] --> ENGINES

    E1 & E2 & E3 & E4 & E5 --> NORM["Evidence/Answer normalizer"] --> RIG2["Comparison rig:
    answers, references,
    tokens - overlap of
    declared capabilities only"]
```

- **Wins:** cheapest hosting of *anything* — a new paper is runnable in days unmodified; black boxes are first-class; zero port cost; upstream updates keep flowing.
- **Loses:** shallow comparison (answers only, never stages); near-zero artifact sharing (every engine re-indexes: N× token cost); no component versioning inside parts — self-improvement limited to selection, never mutation.
- **Fits when:** the goal is rapid *evaluation* of externals rather than evolution of internals — the survey phase, permanently.

---

## Candidate D — "Kernel + Sandbox" (hybrid, promotion path)

**Position:** two regimes with a documented promotion path — a Conductor-style kernel for house modalities, a Federation-style sandbox for trials; extraction shared inside the kernel only; temporal in kernel Cozo *and* hostable as sandbox part; comparison deep in kernel, answer-level in sandbox.

```mermaid
flowchart TB
    Q["query"] --> SEL2["Selector"]

    subgraph KERNEL["KERNEL (Conductor regime)"]
        KG["Declared graphs of
        versioned components
        on machine stores
        deep traces, mutation, A/B"]
    end

    subgraph SANDBOX["SANDBOX (Federation regime)"]
        SB1["Whole engines behind
        manifests, self-contained,
        answer-level comparison"]
    end

    SEL2 --> KERNEL
    SEL2 --> SANDBOX

    SANDBOX -- "proves valuable?
    port = decompose into
    kernel components" --> KERNEL
    KERNEL -.same corpus feed.- SANDBOX

    RIG3["Comparison rig spans both:
    kernel parts compare at stages,
    sandbox parts at answers,
    all parts on tokens + quality"]
    KERNEL --> RIG3
    SANDBOX --> RIG3
```

- **Wins:** resolves the try-fast vs evolve-deep tension instead of picking a side; the promotion path ("prove in sandbox, port to kernel") is exactly how LightRAG→components would proceed anyway; sandbox failures cost nothing.
- **Loses:** two regimes to maintain; the promotion path can rot into "everything stays in the sandbox forever" without discipline; selector and rig must handle both regimes.
- **Fits when:** both rapid external trials *and* deep self-improvement are goals — which is the stated goal ladder. The red team's job is to test whether the two-regime cost is real or exaggerated.

---

## The axes at a glance

| Axis | A Stage Bus | B Conductor | C Federation | D Kernel+Sandbox |
|---|---|---|---|---|
| Normalization stops at | everything | default + blob hatch | corpus feed only | kernel: all / sandbox: feed |
| Extraction | one shared, ontology-config | shared where compatible | per-engine | shared in kernel |
| Part representation | code in fixed slots | declared graph of versions | whole engine + manifest | both, by regime |
| Temporal | machine (Cozo) | both | part (Graphiti) | both |
| Comparison depth | every stage | node boundaries | answers only | deep / shallow by regime |

**Honest prior before red team:** B and D are the only candidates consistent with the versioning-as-improvement mandate; A maximizes science but can't host the survey's edge cases; C is unbeatable for trials but a dead end for self-improvement. D's two-regime cost is the live question.

---
*Drafted 2026-08-10 from SYNTHESIS.md + ARCHITECTURE-RUBRIC.md. Next: red-team round.*
