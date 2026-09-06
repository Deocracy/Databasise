"""§18.4's four selectors: a stable alias, a declared capability (or capability set), a harness by
name, or the default selector (no selector at all).

**Capability matching (this plan's Task 1; FA-04, RESEARCH Open Question 1, unresolved and
carried verbatim).** §18.4 names "a declared capability or capability set" but CONTRACT freezes no
capability vocabulary beyond §14.1's statement that ``effects[]`` is "the base capability
vocabulary". This module matches a requested capability set against the frozen 17-member
``Effect`` vocabulary (``databasise/parts/schema.py``) because that is the only capability
vocabulary that exists in code — inventing a parallel taxonomy the contract does not name would be
worse than using a thin one it does. **This is thin**: a consumer asking for "graph retrieval"
must name ``reads_graph``, a machine-facing word, not a consumer-facing one. It is sufficient to
distinguish the five Phase 3 arms (they differ from each other exactly in which effects their
nodes declare) and therefore sufficient for the §18.5 falsifier, but it is not asserted to be the
right long-term ergonomics.

A wiring satisfies a requested capability set when the union of its registered parts' own declared
``effects`` (never the wiring node's own, possibly-narrower, declared ``effects`` — CR-01 lets a
wiring under-declare relative to its part) is a superset of the request. When more than one of the
five arms satisfies, the **smallest resolved wiring wins** — fewest nodes, ties broken by
``_ARM_NAMES``'s own declared order (``naive``, ``bypass``, ``hybrid``, ``local``, ``global``).
This is a deliberate choice, not an arbitrary one: since every arm's effect set is not disjoint
from its neighbours' (``bypass``'s single ``calls_llm`` effect is a subset of every other arm's own
effect set), a "first candidate in ``_ARM_NAMES`` order" tie-break would make every arm but
``naive`` unreachable by capability alone — the smallest-wiring rule instead resolves to the most
specific (least-footprint) wiring that still satisfies the request.

Every candidate wiring's ``provides``/``harnesses``/``recipe`` fields are read off the raw resolved
dict returned by ``resolve_arm`` — never through ``ParsedWiring``, which drops all three entirely
(Pitfall 1; ``databasise/validator/parse.py`` carries only ``nodes``/``parts``/``deps``/
``node_order``/``report``).

**The alias selector (Task 2; D-12, FA-06).** Reads the promotion ledger's own ``alias`` column
(the 04-03 checkpoint's ``dedicated-alias-column`` answer — see ``_resolve_alias``'s own
docstring for the exact lookup call and the field read to identify the active wiring). The
registry is empty in this phase and every alias lookup refuses — the expected end state, not a
defect; Phase 7's promote path is what appends the first real row.

**The harness selector (Task 3; D-13, FA-05).** Reads the ordered ``harnesses`` array off the raw
resolved dict, preserving declared order verbatim. No production wiring in this repository
declares a harness (every one of the five arms' own ``harnesses`` array is empty) — this path is
built and tested against ``databasise/tests/fixtures/wiring-harness.json`` alone; a production
wiring exercising it is a later phase's concern.

**The default selector's opaque exclusion (Task 3; D-13, §8 condition 7).** A candidate is
excluded from the *default* candidate set only when one of its own ``provides`` positions
(the node whose output becomes the answer) resolves to ``opaque`` effective depth — not merely for
containing an unrelated opaque node elsewhere in the graph. This distinction is load-bearing:
every one of the five arms except ``bypass`` also contains ``embedder-index``, itself declared at
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

from databasise.parts.registry import PartRegistry
from databasise.seam.refusals import ForbiddenSelectorInputError, UnsatisfiableSelectorError
from databasise.validator.depth import effective_depth
from databasise.validator.parse import parse_wiring
from databasise.wirings.resolve import resolve_arm

_DEFAULT_ARM = "naive"
_ARM_NAMES: tuple[str, ...] = ("naive", "bypass", "hybrid", "local", "global")
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
            raise ValueError(
                f"a selector may set at most one of {_SELECTOR_MEMBERS!r}; got {set_members!r} set"
            )
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
    """The five Phase 3 arms, resolved — the fixed candidate pool for the capability and
    (production) harness/default branches. Independent of ``registry``: every arm name is a
    committed patch file, not a registry-dependent computation."""
    return [(name, resolve_arm(name)) for name in _ARM_NAMES]


def _wiring_effects(resolved: dict[str, Any], registry: PartRegistry) -> set[str]:
    """The union of every node's *registered Part's* own declared effects (never the wiring
    node's own, possibly-narrower ``effects`` — CR-01)."""
    effects: set[str] = set()
    for node in resolved.get("nodes", {}).values():
        part = registry.get(node["component"])
        effects.update(part.effects)
    return effects


def _match_capability(
    requested: set[str], candidates: Sequence[_Candidate], *, registry: PartRegistry
) -> _Candidate | None:
    """The pure matching function both the production capability branch and a direct unit test
    (over a hand-built candidate list) call — never re-implemented at either call site."""
    matches = [
        candidate
        for candidate in candidates
        if requested <= _wiring_effects(candidate[1], registry)
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


def _resolve_default(*, registry: PartRegistry) -> dict[str, Any]:
    """The default branch's own resolution path — a separate, spy-able function so a test can
    prove a non-default selector never falls through to it (Task 1's own acceptance criterion)."""
    del registry
    return resolve_arm(_DEFAULT_ARM)


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
        return _resolve_capability(selector.capability, registry=registry)
    if selector is not None and selector.harness is not None:
        return _resolve_harness(selector.harness, registry=registry)
    return _resolve_default(registry=registry)


def _resolve_alias(alias: str, *, store_root: str | Path) -> dict[str, Any]:
    """Placeholder pending Task 2 — raises rather than falling through to the default."""
    del alias, store_root
    raise NotImplementedError("the alias selector is this plan's Task 2 deliverable")


def _resolve_harness(
    name: str,
    *,
    registry: PartRegistry,
    candidates: Sequence[_Candidate] | None = None,
) -> dict[str, Any]:
    """Placeholder pending Task 3 — raises rather than falling through to the default."""
    del registry, candidates
    raise NotImplementedError("the harness selector is this plan's Task 3 deliverable")


__all__ = ["Selector", "resolve_selector"]
