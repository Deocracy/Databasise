#!/usr/bin/env python3
"""
Falsifier 1 of the spike-003 selection: the laundering test.

Implements the two rules the selection was adopted on, and runs them over
wirings drawn from the real LightRAG decomposition path.

  taint rule       effective_depth(n) = min(structural(n), effective_depth(d) for d in deps*)
  blast-radius     a node may write a SHARED artifact namespace only at effective depth `stage`
                   (self_storage is always legal, instance-scoped)

Depth order: opaque < evidence < stage.

stdlib only, no corpus, no network.  Run: python3 taint.py
"""
import sys
from functools import lru_cache

OPAQUE, EVIDENCE, STAGE = 0, 1, 2
NAMES = {OPAQUE: "opaque", EVIDENCE: "evidence", STAGE: "stage"}

# ---------------------------------------------------------------- registry
# structural depth is a property of the COMPONENT, resolved from the registry.
# `opaque` kind -> opaque.  opaque-internals that still emit machine-resolvable
# refs at its boundary -> evidence.  transparent primitive -> stage.
REGISTRY = {
    # transparent primitives (query side is already component-shaped, spike 001)
    "seed-selector@1.0":    dict(depth=STAGE,    effects=[]),
    "expander@1.1":         dict(depth=STAGE,    effects=["reads_graph"]),
    "ranker@1.0":           dict(depth=STAGE,    effects=[]),
    "assembler@2.2":        dict(depth=STAGE,    effects=[]),
    "generator@1.0":        dict(depth=STAGE,    effects=["calls_llm"]),
    "chunker@1.2":          dict(depth=STAGE,    effects=["writes_artifact"]),
    "extractor@2.0":        dict(depth=STAGE,    effects=["calls_llm", "writes_artifact"]),
    "embedder@3.0":         dict(depth=STAGE,    effects=["writes_artifact"]),
    "rerank-cache@1.0":     dict(depth=STAGE,    effects=["writes_artifact"]),
    # opaque parts
    "lightrag-ingest@1.5.4": dict(depth=OPAQUE,  effects=["calls_llm", "writes_artifact"]),
    # the proposed repair: same part, writing an instance-scoped quarantined namespace
    "lightrag-ingest-quarantined@1.5.4": dict(depth=OPAQUE, effects=["calls_llm", "writes_quarantined"]),
    "lightrag-query@1.5.4":  dict(depth=OPAQUE,  effects=["calls_llm"]),
    "cbm-mcp@0.3":           dict(depth=OPAQUE,  effects=["self_storage", "fs"]),
    # opaque internals, but names its refs at the boundary
    "hipporag@2.0":          dict(depth=EVIDENCE, effects=["calls_llm"]),
}


def structural(component):
    return REGISTRY[component]["depth"]


def effects(component):
    return REGISTRY[component]["effects"]


# ------------------------------------------------------------ the two rules
def effective_depth(wiring, node_id, _seen=None):
    """taint rule: min over own structural depth and all transitive deps."""
    _seen = _seen or set()
    if node_id in _seen:                      # cycles are legal; treat as no extra constraint
        return STAGE
    _seen = _seen | {node_id}
    node = wiring[node_id]
    d = structural(node["component"])
    for dep in node.get("deps", []):
        d = min(d, effective_depth(wiring, dep, _seen))
    return d


def blast_radius_violations(wiring):
    """a node may write a SHARED artifact namespace only at effective depth stage."""
    out = []
    for nid, node in wiring.items():
        eff = effective_depth(wiring, nid)
        writes_shared = "writes_artifact" in effects(node["component"])
        if writes_shared and eff != STAGE:
            out.append((nid, NAMES[eff]))
    return out


# ------------------------------------------------------------------- cases
def N(component, *deps):
    return dict(component=component, deps=list(deps))


CASES = [
    # ---- the two cases named in SELECTION.md Falsifier 1 -------------------
    ("1. Fable's assumed middle state: decomposed ingest + opaque QUERY core",
     {
         "chunk":   N("chunker@1.2"),
         "extract": N("extractor@2.0", "chunk"),
         "qcore":   N("lightrag-query@1.5.4"),
         "asm":     N("assembler@2.2", "qcore"),
     },
     [],  # expect: no violations — ingest lane is clean, opaque core is downstream
     "ingest-adapter shared writes must be PERMITTED (rule (a))"),

    ("2. Index-side laundering: opaque core feeds a stage extractor that writes shared",
     {
         "ocore":   N("lightrag-query@1.5.4"),
         "extract": N("extractor@2.0", "ocore"),
     },
     ["extract"],  # expect: refused
     "opaque-derived shared write must be REFUSED (rule (b))"),

    # ---- the decomposition path spike 001 actually establishes -------------
    ("3. REAL LightRAG middle state: query side decomposed (already component-shaped),\n"
     "   ingest side still opaque (~1,786 lines, ontology-welded) and writing the index",
     {
         "ingest":  N("lightrag-ingest@1.5.4"),          # opaque, writes_artifact
         "seed":    N("seed-selector@1.0", "ingest"),
         "expand":  N("expander@1.1", "seed"),
         "rank":    N("ranker@1.0", "expand"),
         "asm":     N("assembler@2.2", "rank"),
         "gen":     N("generator@1.0", "asm"),
     },
     [],  # expectation per the SELECTION ruling: legitimate middle state, permitted
     "THE DECISIVE CASE — is the real first decomposition of LightRAG usable?"),

    # ---- controls and adversarial edges -----------------------------------
    ("3b. Same middle state, modelled correctly: ingest and query are SEPARATE runs\n"
     "    connected by an artifact, not one wiring with a runtime dep",
     {
         "ingest":  N("lightrag-ingest@1.5.4"),          # ingest run, on its own
     },
     ["ingest"],
     "isolates the mechanism: is it taint, or the base rule on the opaque node itself?"),

    ("3c. ...and the query run that reads that index, with no runtime dep on ingest",
     {
         "seed":    N("seed-selector@1.0"),
         "expand":  N("expander@1.1", "seed"),
         "rank":    N("ranker@1.0", "expand"),
         "asm":     N("assembler@2.2", "rank"),
         "gen":     N("generator@1.0", "asm"),
     },
     [],
     "decomposition credit survives across the artifact boundary — taint is NOT the culprit"),

    ("3d. PROPOSED REPAIR: opaque ingest writes an instance-scoped QUARANTINED namespace\n"
     "    (readable by explicit pin, never SA-1-shareable, GC'd with the instance)",
     {
         "ingest":  N("lightrag-ingest-quarantined@1.5.4"),
     },
     [],
     "does a quarantined write make the middle state usable WITHOUT admitting opaque data to the shared plane?"),

    ("4. Fully decomposed: every node stage",
     {
         "chunk":   N("chunker@1.2"),
         "extract": N("extractor@2.0", "chunk"),
         "embed":   N("embedder@3.0", "chunk"),
         "seed":    N("seed-selector@1.0", "embed"),
         "asm":     N("assembler@2.2", "seed"),
     },
     [],
     "control: fully decomposed must be permitted"),

    ("5. Fully opaque part using only self_storage",
     {"cbm": N("cbm-mcp@0.3")},
     [],
     "control: self_storage is always legal, never a shared write"),

    ("6. Opaque node writing a shared namespace directly",
     {"ingest": N("lightrag-ingest@1.5.4")},
     ["ingest"],
     "control: direct opaque shared write must be refused"),

    ("7. Non-adjacent fan-in: stage cache reads an opaque sibling, writes shared",
     {
         "ocore":  N("lightrag-query@1.5.4"),
         "rank":   N("ranker@1.0"),
         "cache":  N("rerank-cache@1.0", "rank", "ocore"),
     },
     ["cache"],
     "taint must follow non-adjacent fan-in, not just the direct chain"),

    ("8. Parallel lanes: stage ingest lane, opaque query lane, no dep edge between them",
     {
         "chunk":  N("chunker@1.2"),
         "embed":  N("embedder@3.0", "chunk"),
         "qcore":  N("lightrag-query@1.5.4"),
         "asm":    N("assembler@2.2", "qcore"),
     },
     [],
     "parallel opaque lane must not taint an independent ingest lane"),

    ("9. `evidence`-depth part (names its refs) writing shared",
     {
         "hippo":   N("hipporag@2.0"),
         "extract": N("extractor@2.0", "hippo"),
     },
     ["extract"],
     "evidence < stage, so evidence-derived shared writes are refused too"),
]


def main():
    print("=" * 78)
    print(" FALSIFIER 1 — the laundering test")
    print(" taint rule + blast-radius rule, over the real decomposition path")
    print("=" * 78)
    failures, decisive = [], None

    for title, wiring, expected, note in CASES:
        got = blast_radius_violations(wiring)
        got_ids = sorted(n for n, _ in got)
        ok = got_ids == sorted(expected)
        depths = {n: NAMES[effective_depth(wiring, n)] for n in wiring}

        print(f"\n{title}")
        print(f"   why: {note}")
        print(f"   effective depths: {depths}")
        if got:
            for nid, eff in got:
                print(f"   REFUSED  {nid}  (shared write at effective depth `{eff}`)")
        else:
            print("   PERMITTED  (no blast-radius violation)")
        print(f"   expected {sorted(expected) or 'no violations'} -> {'OK' if ok else 'UNEXPECTED'}")

        if not ok:
            failures.append(title)
        if title.startswith("3."):
            decisive = (got_ids, expected)

    print("\n" + "=" * 78)
    if decisive and decisive[0] != decisive[1]:
        print(" VERDICT: PARTIAL — the rules behave exactly as specified, and the")
        print(" realistic decomposition order needs a named contract amendment.")
        print()
        print(" What is blocked (cases 3, 3b, 6): the opaque LightRAG ingest core cannot")
        print(" write the shared index. But ingest is precisely the thing that PRODUCES")
        print(" the shared index, and spike 001 [code-verified] says the index side is the")
        print(" entangled ~1,786-line side — so it decomposes LAST. The realistic entry")
        print(" state of the port is therefore forbidden.")
        print()
        print(" Mis-attribution corrected (3b vs 3c): this is NOT the taint rule. Taint is")
        print(" sound — cases 2, 7, 9 confirm it, and 3c shows decomposition credit survives")
        print(" across the artifact boundary. The blocker is the base blast-radius rule")
        print(" applied to the opaque node itself.")
        print()
        print(" FALSIFIED: the reasoning that justified Condition 1 of the selection —")
        print(" 'the ingest lane sits upstream of the query-side opaque core, so an")
        print(" ingest-adapter's transitive deps are clean'. The decomposition runs the")
        print(" other way: the QUERY side is already component-shaped, ingest is opaque")
        print(" longest. The conclusion survives; the argument for it does not.")
        print()
        print(" REPAIR (case 3d, passes): an instance-scoped QUARANTINED namespace —")
        print(" readable by explicit pin, never SA-1-shareable, GC'd with the instance.")
        print(" Opaque-derived data still never enters the shared plane, so the standing")
        print(" disqualifier holds. Cost, stated honestly: no artifact sharing in the")
        print(" middle state, so two modalities over an opaque index each re-index (C's")
        print(" N-times token cost) — confined to the middle state, and it makes")
        print(" decomposition the way to EARN sharing. That is the ratchet, priced.")
    elif failures:
        print(f" VERDICT: unexpected results in {len(failures)} case(s) — inspect above.")
    else:
        print(" VERDICT: PASS — all cases behave as the selection claims.")
    print("=" * 78)
    # case 3 is an expected-to-fail probe; only OTHER unexpected results are errors
    real_failures = [f for f in failures if not f.startswith("3.")]
    return 1 if real_failures else 0


if __name__ == "__main__":
    sys.exit(main())
