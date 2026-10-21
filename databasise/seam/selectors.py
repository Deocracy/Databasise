"""§18.4's four selectors: a stable alias, a declared capability (or capability set), a harness by
name, or the default selector (no selector at all).

**Capability matching (FA-04, RESEARCH Open Question 1; WIRE-01, D-01).** §18.4 names "a declared
capability or capability set" but CONTRACT freezes no capability vocabulary beyond §14.1's
statement that ``effects[]`` is "the base capability vocabulary". A capability token here is
therefore either a member of the frozen 17-member ``Effect`` vocabulary
(``databasise/parts/schema.py``) or a Databasise read-namespace token ``<read effect>:<namespace>``
(for example ``reads_vector:entities``) that a part declares on its ``reads_namespaces`` field.
The namespace tokens exist because effects alone cannot tell ``local``, ``global`` and ``hybrid``
apart: all three declare the same effect union. **This is thin**: a consumer asking for "graph
retrieval" must name ``reads_graph``, a machine-facing word, not a consumer-facing one.

**The candidate pool** for the capability, harness and default branches is
``databasise.wirings.resolve.all_wirings()``: every LightRAG arm plus the HippoRAG base wiring,
in that function's own order.

A wiring satisfies a requested capability set when the union of its registered parts' own declared
``effects`` and ``reads_namespaces`` tokens (never the wiring node's own, possibly-narrower,
declared ``effects`` — CR-01 lets a wiring under-declare relative to its part) is a superset of the
request. When more than one candidate satisfies, the **smallest resolved wiring wins** — fewest
nodes, ties broken by the pool's own order (a stable sort).

Which capability set selects which arm, with no promote:

- ``[reads_vector]``, or ``[reads_vector:chunks]`` -> ``naive`` (7 nodes)
- ``[calls_llm]`` -> ``bypass`` (1 node)
- ``[reads_vector:entities]`` -> ``local``
- ``[reads_vector:relationships]`` -> ``global``
- ``[reads_vector:entities, reads_vector:relationships]`` (either order) -> ``hybrid``
- ``[reads_graph, reads_kv]`` -> ``hipporag``
- ``[reads_graph]`` and ``[reads_graph, calls_llm]`` -> ``hipporag``; ``[reads_graph, calls_rerank]``
  -> ``local`` (hipporag declares no rerank); ``[writes_graph]`` -> refused (no query wiring writes)

The effect-only ``reads_graph`` requests rest on a **one-node margin**: hipporag has 14 full nodes
against ``local`` and ``global`` at 15, so hipporag wins every request both can satisfy, until a
request names something hipporag lacks. Adding a node to hipporag, or removing one from ``local``
or ``global``, changes which arm an effect-only ``reads_graph`` request selects.

Capability matching sees the effects a query run of the candidate can have (HIPP-12, D-16): the
union is taken over ``without_recipe_only_nodes(candidate)``, so the write effects of index-side
nodes never select a query wiring. ``[writes_graph]`` no longer resolves to the HippoRAG wiring and
``[writes_artifact]`` resolves to nothing. The node-count tie-break above still uses the full wiring.

Every candidate wiring's ``provides``/``harnesses``/``recipe`` fields are read off the raw resolved
dict returned by ``resolve_arm`` — never through ``ParsedWiring``, which drops all three entirely
(Pitfall 1; ``databasise/validator/parse.py`` carries only ``nodes``/``parts``/``deps``/
``node_order``/``report``).

**The alias selector (Task 2; D-12, FA-06).** Reads the promotion ledger's own ``alias`` column
(the 04-03 checkpoint's ``dedicated-alias-column`` answer — see ``_resolve_alias``'s own
docstring for the exact lookup call and the field read to identify the active wiring). Promote,
rollback and retire write the rows this branch reads; the branch resolves any ``all_wirings()``
name through ``wiring_for_name``. A missing ``ledger.db``, an alias with no row, and a row naming a
wiring that does not resolve all refuse identically, and the read path never creates ``ledger.db``.

**The harness selector (Task 3; D-13, FA-05).** Reads the ordered ``harnesses`` array off the raw
resolved dict, preserving declared order verbatim. No production wiring in this repository
declares a harness (every candidate's own ``harnesses`` array is empty), so the production
harness branch refuses — this path is built and tested against
``databasise/tests/fixtures/wiring-harness.json`` alone.

**The default selector's opaque exclusion (Task 3; D-13, §8 condition 7).** A candidate is
excluded from the *default* candidate set only when one of its own ``provides`` positions
(the node whose output becomes the answer) resolves to ``opaque`` effective depth — not merely for
containing an unrelated opaque node elsewhere in the graph. This distinction is load-bearing:
every LightRAG arm except ``bypass`` also contains ``embedder-index``, itself declared at
``opaque`` structural depth (an isolated, dep-free ingest node, per
``databasise/tests/parity/test_arm_conformance.py``'s own conformance proof) — excluding a whole
wiring merely for *containing* an opaque node anywhere would make the default selector unable to
resolve ``naive`` at all, breaking 04-01/04-02's already-established default behaviour. Excluding
only on the *provides* node's own opaque depth keeps that behaviour exactly as it was (``naive``'s
``provides`` node, ``generate``, is always ``stage``) while still implementing §8 condition 7 for
a wiring whose actual answer *would* come from an opaque node. Exclusion from the default is never
exclusion from the seam: the same wiring remains reachable by alias, capability, or harness name.

**No selector value or refusal message ever discloses the machine's candidate set** (§18.2's
closed set, applied to the selector path): a refusal names only the consumer's own requested value
(``UnsatisfiableSelectorError``), never a candidate wiring id, arm name, or node id.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from databasise.ledger.ledger import Ledger
from databasise.parts.registry import PartRegistry
from databasise.seam.refusals import (
    EmptyCapabilitySelectorError,
    ForbiddenSelectorInputError,
    MultiMemberSelectorError,
    UnsatisfiableSelectorError,
)
from databasise.validator.depth import effective_depth
from databasise.validator.parse import parse_wiring
from databasise.wirings.resolve import all_wirings, without_recipe_only_nodes, wiring_for_name

_SELECTOR_MEMBERS: tuple[str, ...] = ("alias", "capability", "harness")

# A bare 64-hex-char string, optionally "sha256:"-prefixed — the shape every instance hash this
# codebase mints takes (``databasise/seam/engine.py``'s own ``wiring_instance_hash``,
# ``arm_instance_hashes`` in ``databasise/ledger/ledger.py``'s own test fixtures). A selector
# member matching this shape is refused at construction (T-04-12) — an internal identity smuggled
# in as an alias/capability/harness string, never resolved as if it were a legitimate name.
_INSTANCE_HASH_PATTERN = re.compile(r"^(sha256:)?[0-9a-f]{64}$", re.IGNORECASE)

_Candidate = tuple[str, dict[str, Any]]


class Selector(BaseModel):
    """The §18.4 selector input: the three named-modality forms as mutually exclusive optional
    members. Absent (``None``) or a ``Selector`` with every member unset means the default
    selector."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    alias: str | None = None
    capability: str | list[str] | None = None
    harness: str | None = None

    @model_validator(mode="after")
    def _at_most_one_member_set(self) -> "Selector":
        set_members = [name for name in _SELECTOR_MEMBERS if getattr(self, name) is not None]
        if len(set_members) > 1:
            raise MultiMemberSelectorError(set_members=set_members)
        return self

    @model_validator(mode="after")
    def _no_instance_hash_shaped_values(self) -> "Selector":
        candidates: list[tuple[str, str]] = []
        if self.alias is not None:
            candidates.append(("alias", self.alias))
        if self.harness is not None:
            candidates.append(("harness", self.harness))
        if self.capability is not None:
            values = self.capability if isinstance(self.capability, list) else [self.capability]
            candidates.extend(("capability", value) for value in values)

        for member_name, value in candidates:
            if _INSTANCE_HASH_PATTERN.match(value):
                raise ForbiddenSelectorInputError(member_name=member_name, value=value)
        return self


def _capability_candidates() -> list[_Candidate]:
    """The registered candidate pool for the capability and (production) harness/default
    branches (06-01-PLAN.md): every LightRAG arm plus every non-LightRAG base wiring, via
    ``databasise.wirings.resolve.all_wirings()`` — no longer a LightRAG-only, five-arm list.
    Independent of ``registry``: every candidate name is a committed wiring/patch file, not a
    registry-dependent computation."""
    return all_wirings()


def _wiring_effects(resolved: dict[str, Any], registry: PartRegistry) -> set[str]:
    """The union of every node's *registered Part's* own declared effects (never the wiring
    node's own, possibly-narrower ``effects`` — CR-01)."""
    effects: set[str] = set()
    for node in resolved.get("nodes", {}).values():
        part = registry.get(node["component"])
        effects.update(part.effects)
    return effects


def _wiring_read_namespaces(resolved: dict[str, Any], registry: PartRegistry) -> set[str]:
    """The union of every node's registered Part's ``reads_namespaces`` tokens (WIRE-01, D-01).
    Matching only: kept apart from ``_wiring_effects`` because promotion and compare read that."""
    tokens: set[str] = set()
    for node in resolved.get("nodes", {}).values():
        tokens.update(registry.get(node["component"]).reads_namespaces)
    return tokens


def _capability_tokens(resolved: dict[str, Any], registry: PartRegistry) -> set[str]:
    return _wiring_effects(resolved, registry) | _wiring_read_namespaces(resolved, registry)


def _match_capability(
    requested: set[str], candidates: Sequence[_Candidate], *, registry: PartRegistry
) -> _Candidate | None:
    """The pure matching function both the production capability branch and a direct unit test
    (over a hand-built candidate list) call — never re-implemented at either call site."""
    matches = [
        candidate
        for candidate in candidates
        if requested <= _capability_tokens(without_recipe_only_nodes(candidate[1]), registry)
    ]
    if not matches:
        return None
    # Smallest resolved wiring wins (most specific match) — see module docstring for why a
    # declared-order tie-break alone would make every arm but naive unreachable.
    matches.sort(key=lambda candidate: len(candidate[1].get("nodes", {})))
    return matches[0]


def _resolve_capability(
    requested: str | list[str],
    *,
    registry: PartRegistry,
    candidates: Sequence[_Candidate] | None = None,
) -> dict[str, Any]:
    requested_set = set(requested) if isinstance(requested, list) else {requested}
    pool = candidates if candidates is not None else _capability_candidates()

    match = _match_capability(requested_set, pool, registry=registry)
    if match is None:
        raise UnsatisfiableSelectorError(selector_kind="capability", requested=sorted(requested_set))
    return match[1]


def _is_default_eligible(resolved: dict[str, Any], registry: PartRegistry) -> bool:
    """§8 condition 7: excluded from the *default* candidate set only when one of the wiring's
    own ``provides`` positions — the node whose output becomes the answer — resolves to
    ``opaque`` effective depth. See the module docstring for why this is scoped to the provides
    node rather than to "contains an opaque node anywhere": every LightRAG arm except
    ``bypass`` also contains the unrelated, dep-free ``embedder-index`` node at opaque structural
    depth, and excluding on that alone would make the default selector unable to resolve
    ``naive`` at all.

    A wiring that fails to parse against ``registry`` is treated as ineligible rather than
    raising — it has nothing meaningful to say about depth yet (mirrors ``validator/parse.py``'s
    own precedent of gating the depth pass on a structurally sound parse).
    """
    parsed = parse_wiring(resolved, registry)
    if not parsed.report.ok:
        return False
    depths = effective_depth(parsed)
    provides = resolved.get("provides") or []
    return all(depths.get(node_id) != "opaque" for node_id in provides)


def _resolve_default(
    *,
    registry: PartRegistry,
    candidates: Sequence[_Candidate] | None = None,
) -> dict[str, Any]:
    """The default branch's own resolution path — a separate, spy-able function so a test can
    prove a non-default selector never falls through to it (Task 1's own acceptance criterion).
    Iterates the candidate pool (``all_wirings()`` in production) in order and returns the first
    candidate whose ``provides`` position is not opaque-depth (§8 condition 7); ``naive`` is
    first and its own ``provides`` node (``generate``) is always ``stage``, so this is
    behaviourally identical to 04-01/04-02's hardcoded ``naive`` default for every wiring this
    repository actually publishes.
    """
    pool = candidates if candidates is not None else _capability_candidates()
    for _name, resolved in pool:
        if _is_default_eligible(resolved, registry):
            return resolved
    raise UnsatisfiableSelectorError(selector_kind="default", requested=None)


def resolve_selector(
    selector: Selector | None,
    *,
    registry: PartRegistry,
    store_root: str | Path | None = None,
) -> dict[str, Any]:
    """Resolve ``selector`` to a raw wiring dict, ready for ``parse_wiring`` — never through
    ``ParsedWiring`` (Pitfall 1). ``store_root`` is required only for the alias branch, which
    opens the promotion ledger at that path; every other branch ignores it.
    """
    if selector is not None and selector.alias is not None:
        if store_root is None:
            raise ValueError("resolving an alias selector requires store_root")
        return _resolve_alias(selector.alias, store_root=store_root)
    if selector is not None and selector.capability is not None:
        if selector.capability == []:
            raise EmptyCapabilitySelectorError()
        return _resolve_capability(selector.capability, registry=registry)
    if selector is not None and selector.harness is not None:
        return _resolve_harness(selector.harness, registry=registry)
    return _resolve_default(registry=registry)


def _resolve_alias(alias: str, *, store_root: str | Path) -> dict[str, Any]:
    """The §18.4 alias branch (D-12, FA-06). Read-only: it opens the ledger with
    ``Ledger.open_existing(read_only=True)``, a ``query_only`` connection, and closes it, so it
    never creates ``ledger.db``, never changes its journal mode, schema or indexes, and never
    appends (CONTRACT §6; 14-REVIEW A-WR-01 narrows D-08's migrating open to the writer verbs).
    Its close does not checkpoint the WAL where ``sqlite3`` supports that; hot-journal recovery
    can still write the file (see ``Ledger.open_existing``).
    Promote, rollback and retire write the rows this branch reads.

    The lookup is ``by_alias(alias)``, the active-pointer projection over the ``alias`` column. The
    row's ``mutation_id`` names the active wiring and resolves through ``wiring_for_name``, the one
    lookup over every ``all_wirings()`` name, HippoRAG included.

    A missing ``ledger.db``, a file with no ``ledger`` table (a zero-byte file included), an alias
    with no row, and a row whose ``mutation_id`` no wiring answers to all raise the identical :class:`UnsatisfiableSelectorError`, naming only the
    consumer's own ``alias`` value, never the row's ``mutation_id`` or a wiring id (§18.2's closed
    set, applied to this branch: telling "no aliases exist" from "your alias is not one of them" is
    itself the disclosure the no-enumeration rule forbids).
    """
    refusal = UnsatisfiableSelectorError(selector_kind="alias", requested=alias)
    ledger = Ledger.open_existing(store_root, read_only=True)
    if ledger is None:
        raise refusal
    with ledger:
        record = ledger.by_alias(alias)
    resolved = wiring_for_name(record.mutation_id) if record is not None else None
    if resolved is None:
        raise refusal
    return resolved


def _wiring_declares_harness(resolved: dict[str, Any], name: str) -> bool:
    """Membership in the wiring's own ordered ``harnesses`` array, read off the raw resolved
    dict — never sorted, deduped, or reordered."""
    return name in resolved.get("harnesses", [])


def _match_harness(name: str, candidates: Sequence[_Candidate]) -> _Candidate | None:
    """The pure matching function both the production harness branch and a direct unit test
    (over a hand-built candidate list, e.g. the wiring-harness.json fixture) call."""
    for candidate in candidates:
        if _wiring_declares_harness(candidate[1], name):
            return candidate
    return None


def _resolve_harness(
    name: str,
    *,
    registry: PartRegistry,
    candidates: Sequence[_Candidate] | None = None,
) -> dict[str, Any]:
    """The §18.4 harness branch (D-13, FA-05). No production wiring in this repository declares a
    harness — every candidate's own ``harnesses`` array is empty — so in production this
    branch always raises :class:`UnsatisfiableSelectorError`; it is proven against
    ``databasise/tests/fixtures/wiring-harness.json`` alone (see that fixture's own ``title``).
    """
    del registry
    pool = candidates if candidates is not None else _capability_candidates()

    match = _match_harness(name, pool)
    if match is None:
        raise UnsatisfiableSelectorError(selector_kind="harness", requested=name)
    return match[1]


__all__ = ["Selector", "resolve_selector"]
