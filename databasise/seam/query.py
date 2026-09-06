"""§18.1's query object: ``QueryObject``, a frozen, extra-forbidding Pydantic v2 model carrying
exactly the five frozen members (``text``, ``embedding``, ``predicates``, ``profile_ref``,
``formal_query``), plus :func:`check_consumable` — the D-14 per-member consumption check that runs
before any wiring is resolved.

**Consumable set, this phase.** ``text`` is consumable: the ``keywords``, ``embedder-query`` and
``generate`` positions in the registered LightRAG parts all read it (``databasise.seam.engine``'s
``_inject_query`` stamps it onto their configs, mirroring ``databasise/parity/run_arm.py``).

The other four are refused as unconsumable **by absence, not by permanent exclusion** — each one
requires a capability no part or store in this milestone's registry declares yet:

- ``embedding`` requires a bound ``space_id`` and a part declaring a matching ``reads_space``
  (§18.1) — no part declares this capability today.
- ``predicates`` requires a store consuming it as a pointwise or bulk-export query per §14.2's
  sub-capability tables — no registered store declares one.
- ``profile_ref`` requires a part able to resolve the ref through §4's deref-raising discipline —
  none exists yet.
- ``formal_query`` requires a store declaring the ``formal-query-language`` sub-capability §14.2
  names explicitly — no registered store declares it.

A later phase that registers a part/store declaring the matching capability flips one of these four
from refused to consumable without changing this module's shape — :func:`check_consumable` reads
the registry's own declared capabilities each call, rather than hardcoding a permanent exclusion
list.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from databasise.parts.registry import PartRegistry
from databasise.seam.refusals import EmptyQueryObjectError, UnconsumableQueryMemberError

_QUERY_MEMBERS: tuple[str, ...] = ("text", "embedding", "predicates", "profile_ref", "formal_query")

# See module docstring: the §14/§14.2 capability each currently-unconsumable member would need a
# registered part or store to declare before it stops being refused by absence.
_MEMBER_REQUIRED_CAPABILITY: dict[str, str] = {
    "embedding": "reads_space",
    "predicates": "predicate-query",
    "profile_ref": "profile-ref-resolution",
    "formal_query": "formal-query-language",
}


class QueryObject(BaseModel):
    """§18.1's query object. Every member is optional and defaults to absent — never a bare query
    string convenience overload (the plan's own prohibition: a string overload reintroduces the
    re-parsing burden §18.1 exists to remove)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str | None = None
    embedding: list[float] | None = None
    predicates: dict[str, Any] | None = None
    profile_ref: str | None = None
    formal_query: str | None = None


def _registered_capabilities(registry: PartRegistry) -> set[str]:
    """Every effect any registered part declares — the capability vocabulary
    :func:`check_consumable` checks the four non-``text`` members against."""
    capabilities: set[str] = set()
    for name_at_version in registry.keys():
        capabilities.update(registry.get(name_at_version).effects)
    return capabilities


def check_consumable(query_object: QueryObject, registry: PartRegistry) -> None:
    """D-14: refuse a query object with zero set members, and refuse — by name — any set member
    no part in ``registry`` can consume. Runs before any wiring is resolved.
    """
    set_members = [name for name in _QUERY_MEMBERS if getattr(query_object, name) is not None]
    if not set_members:
        raise EmptyQueryObjectError(query_object)

    capabilities = _registered_capabilities(registry)
    for member_name in set_members:
        if member_name == "text":
            continue
        required_capability = _MEMBER_REQUIRED_CAPABILITY[member_name]
        if required_capability not in capabilities:
            raise UnconsumableQueryMemberError(member_name)


__all__ = ["QueryObject", "check_consumable"]
