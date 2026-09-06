"""The shared strict Pydantic v2 base every model across ``databasise/seam/`` inherits
(04-RESEARCH.md Pitfall 7 — Pydantic v2 does not cascade ``frozen=True, extra="forbid"`` through
nested model fields; each nested model must set its own ``model_config``, or inherit from a shared
strict base).

**Why this lives in its own leaf module, not in ``envelope.py`` directly.** ``envelope.py``'s
``ResponseEnvelope`` needs to import the per-item element types 04-02 defines
(``databasise.seam.evidence.EvidenceRef``, ``databasise.seam.tokens.TokenBreakdownEntry``) to bind
them into its own field annotations (D-04/D-05's closed-set rule is enforced at the envelope's own
field types, per 04-01-SUMMARY.md's ``declare-upfront`` derivation). Those element-type modules, in
turn, need the same strict base envelope.py's own top-level models use, so that a nested item is
just as extra-forbidding and frozen as the envelope itself (Pitfall 7). Defining the base directly
in ``envelope.py`` and having ``evidence.py``/``tokens.py`` import it back from there would make
``envelope.py`` and ``evidence.py``/``tokens.py`` import each other — a literal circular import at
the plain Python module level (envelope -> evidence -> envelope), which fails regardless of import
order. Extracting the base into this dependency-free leaf module breaks the cycle: every seam model
module imports downward from here, and nothing here imports back up.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


__all__ = ["_StrictModel"]
