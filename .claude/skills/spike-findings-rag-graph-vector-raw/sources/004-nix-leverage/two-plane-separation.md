---
title: Two-plane separation — artifact/lineage plane vs execution plane
date: 2026-08-10
context: Pre-003 exploration (NixOS fit). Binding design doctrine for all D-variants and the fitting contract.
---

# Two-Plane Separation

The system contains two graphs with different shapes and different owners. Conflating them reintroduces candidate A's failure (DAG-only execution).

## Artifact/lineage plane — DAG, content-addressed

- Holds: component versions, recipes, index artifacts, wiring specs, run traces, lineage
- Shape: acyclic by necessity — a version cannot be its own ancestor; an artifact cannot depend on itself
- Identity: content hash of resolved inputs (SA-1); instance identity closes over the dependency closure (contract clause 2)
- Nix-compatible: this is the plane Nix's model matches (derivations, closures, incremental invalidation, profiles). Whether Nix implements any of it is spike 004's question.

## Execution plane — loops and runtime branching, machine-owned

- Holds: query-time control flow — loops (CRAG/Self-RAG), branches, fan-out/join, planner-emitted ephemeral subgraphs, debate rounds
- Owner: the kernel executor (B-style declared-graph engine). Never Nix, never the artifact plane.

## The reconciliation

A wiring may contain loops, but every completed run's trace is an unrolled DAG. Specs and traces — the two things worth content-addressing — are both DAG-shaped data. The hardest case (Plan*RAG's runtime-emitted subgraph, GAP-SWEEP §4.1) resolves the same way: the planner is the versioned artifact; the emitted plan is recorded as trace data.

**The wiring spec is the boundary object, and it is not a contradiction.** A wiring spec is a DAG-plane artifact whose *content* describes a possibly-cyclic execution graph. The artifact is immutable data, hashed like any other; the cycles live inside the value, not in the dependency edges between artifacts. A cyclic wiring is therefore fully content-addressable, and no variant may be disqualified on the grounds that "its wirings have loops."

## Rule

- Versioned wirings and ephemeral plans have separate lifecycles (GAP-SWEEP §3.8.2)
- The executor executes; the artifact plane records. No component may treat the artifact plane as a runtime control channel.
- All spike 003 variants must respect this split; a variant that merges the planes is disqualified.
