"""Tarjan's strongly-connected-components algorithm, hand-rolled and iterative.

No third-party graph library dependency: 01-RESEARCH.md's "Pattern 2: SCC-condensation depth
computation" explicitly rejects adding one for this one algorithm, and pulling such a dependency
into ``databasise/`` here would reopen D-14's "nothing in ``databasise/`` imports from v1"
boundary question for no real gain — v1 carries one only as its quick-start default graph
backend, an unrelated use this module does not share.

Iterative, not recursive: a wiring is author-supplied data, and Python's default recursion limit
(~1000) is well within reach of a deep dependency chain a hostile or merely large wiring could
declare. Recursive Tarjan would exhaust it; this implementation simulates the recursion with an
explicit work stack instead, so depth is bounded only by available memory.
"""

from __future__ import annotations


def strongly_connected_components(deps: dict[str, set[str]]) -> list[set[str]]:
    """Tarjan's algorithm, iterative. Returns each strongly-connected component as a ``set`` of
    node ids, in reverse topological order (a component is emitted only after every component it
    depends on has already been emitted — Tarjan's natural output order, preserved here rather
    than re-sorted).

    ``deps`` maps a node id to the set of node ids it depends on. A node id that appears only as
    a value (never as a key) is treated as a leaf with no further dependencies of its own — the
    caller need not pre-populate every node as a key with an empty set.

    A self-loop (``node in deps[node]``) yields a valid one-member component; this function never
    special-cases it away, and never recurses, so a self-loop cannot cause infinite recursion.
    """
    index_counter = 0
    index: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: dict[str, bool] = {}
    tarjan_stack: list[str] = []
    result: list[set[str]] = []

    all_nodes: set[str] = set(deps.keys())
    for node_deps in deps.values():
        all_nodes |= node_deps

    for start in sorted(all_nodes):
        if start in index:
            continue

        # Explicit work stack simulating recursion: each frame is
        # (node, sorted successors, next successor index to visit).
        work: list[tuple[str, list[str], int]] = [(start, sorted(deps.get(start, ())), 0)]
        index[start] = index_counter
        lowlink[start] = index_counter
        index_counter += 1
        tarjan_stack.append(start)
        on_stack[start] = True

        while work:
            node, successors, i = work[-1]
            if i < len(successors):
                work[-1] = (node, successors, i + 1)
                succ = successors[i]
                if succ not in index:
                    index[succ] = index_counter
                    lowlink[succ] = index_counter
                    index_counter += 1
                    tarjan_stack.append(succ)
                    on_stack[succ] = True
                    work.append((succ, sorted(deps.get(succ, ())), 0))
                elif on_stack.get(succ, False):
                    lowlink[node] = min(lowlink[node], index[succ])
                # else: succ is already resolved into an earlier, completed component — a cross
                # edge into that component, which contributes nothing further to this one.
            else:
                work.pop()
                if work:
                    parent = work[-1][0]
                    lowlink[parent] = min(lowlink[parent], lowlink[node])
                if lowlink[node] == index[node]:
                    component: set[str] = set()
                    while True:
                        w = tarjan_stack.pop()
                        on_stack[w] = False
                        component.add(w)
                        if w == node:
                            break
                    result.append(component)

    return result


def condensation(deps: dict[str, set[str]], sccs: list[set[str]]) -> dict[int, set[int]]:
    """Map each SCC's index (its position in ``sccs``) to the set of SCC indices it depends on,
    excluding self-edges. Acyclic by construction: any two nodes that could form a cycle across
    the mapping are, by definition, mutually reachable and therefore already merged into one SCC
    by ``strongly_connected_components`` above.
    """
    scc_of: dict[str, int] = {}
    for i, component in enumerate(sccs):
        for node in component:
            scc_of[node] = i

    result: dict[int, set[int]] = {i: set() for i in range(len(sccs))}
    for node, node_deps in deps.items():
        i = scc_of[node]
        for dep in node_deps:
            j = scc_of[dep]
            if i != j:
                result[i].add(j)
    return result
