"""§18.4's four selectors: a stable alias, a declared capability (or capability set), a harness by
name, or the default selector (no selector at all).

Only the default branch is implemented in this plan — it resolves to the ``naive`` arm's wiring
document via ``databasise.wirings.resolve.resolve_arm``, exactly the arm
``databasise/tests/parity/test_naive_arm_end_to_end.py`` already exercises. The alias, capability
and harness branches raise ``NotImplementedError`` naming 04-03 as their owner: a placeholder that
fails loudly is correct here, since a placeholder that silently fell through to the default would
answer from a modality the consumer did not select — exactly the silent fallback §18.4 forbids.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from databasise.parts.registry import PartRegistry
from databasise.wirings.resolve import resolve_arm

_DEFAULT_ARM = "naive"
_SELECTOR_MEMBERS: tuple[str, ...] = ("alias", "capability", "harness")


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


def resolve_selector(selector: Selector | None, *, registry: PartRegistry) -> dict[str, Any]:
    """Resolve ``selector`` to a raw wiring dict, ready for ``parse_wiring`` — never through
    ``ParsedWiring``, which drops ``provides``/``harnesses`` entirely (Pitfall 1). ``registry`` is
    accepted now for the alias/capability/harness branches 04-03 adds; the default branch this
    plan implements does not consult it.
    """
    if selector is not None and selector.alias is not None:
        raise NotImplementedError("the alias selector is 04-03's deliverable")
    if selector is not None and selector.capability is not None:
        raise NotImplementedError("the capability selector is 04-03's deliverable")
    if selector is not None and selector.harness is not None:
        raise NotImplementedError("the harness selector is 04-03's deliverable")
    del registry  # unused by the default branch — see docstring
    return resolve_arm(_DEFAULT_ARM)


__all__ = ["Selector", "resolve_selector"]
