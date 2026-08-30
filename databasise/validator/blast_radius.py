"""The blast-radius rule (CONTRACT §3; D-02's load-time call site — the second call site, at the
artifact-write path itself, is plan 01-07's deliverable): a node MAY write into a shared artifact
namespace only at effective depth ``stage``.

Three properties this check must have, each one of D-03's named repairs to the spike-005
prototype (see ``tests/validator/test_taint_conformance.py`` for the ported case table that
proves them):

1. ``writes_quarantined`` is NOT one of the seventeen ``effects[]`` members and is never checked
   for. Scope is a property of the artifact *write*, not a capability declaration — carried on
   the writing part as ``artifact_scope`` over the three CONTRACT §3 scopes ``shared`` /
   ``quarantined`` / ``self_storage``, defaulting explicitly to ``shared`` when unstated (an
   opaque node MAY write ``quarantined`` and MUST NOT write ``shared``).
2. ``writes_artifact`` is distinguished from the four transient store-write effects
   (``writes_kv``/``writes_vector``/``writes_graph``/``writes_lexical``). Those sit OUTSIDE this
   rule by design (PARTS-04 D1, CONTRACT §7): a transient store write carries no artifact
   namespace, no sub-recipe stamp, no corpus and no producing-instance binding, so it is not a
   registry entry this rule's shared/quarantined/self_storage distinction applies to at all — the
   predicate below keys on ``writes_artifact`` alone, regardless of what else a node declares.
3. Every violation names the offending node id, its computed effective depth, and the scope it
   attempted, so a wiring author can act on the message without reading this module's source.

``artifact_scope`` is read via ``getattr(part, "artifact_scope", "shared")`` rather than as a
statically declared field on ``Part``: this plan's lane is ``databasise/validator/**``, and
``databasise/parts/schema.py`` — where the field is declared — is plan 01-04's file in this same
wave. Reading it by name with an explicit default keeps this module correct whether or not that
field has landed yet in a given worktree, and the default matches CONTRACT §3's own rule: an
unstated scope is judged ``shared``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from databasise.validator.errors import CODE_BLAST_RADIUS_REFUSAL, Violation

if TYPE_CHECKING:
    from databasise.validator.parse import ParsedWiring


def blast_radius_violations(parsed: ParsedWiring, depth_map: dict[str, str]) -> list[Violation]:
    """A node violates iff (a) it declares ``writes_artifact`` AND (b) the artifact scope of that
    write is ``shared`` (the explicit default when unstated) AND (c) its effective depth — read
    from ``depth_map``, as computed by ``validator.depth.effective_depth`` — is not ``stage``.
    """
    violations: list[Violation] = []
    for node_id, node in parsed.nodes.items():
        if "writes_artifact" not in node.effects:
            continue

        part = parsed.parts[node_id]
        scope = getattr(part, "artifact_scope", None) or "shared"
        if scope != "shared":
            continue

        depth = depth_map[node_id]
        if depth != "stage":
            violations.append(
                Violation(
                    code=CODE_BLAST_RADIUS_REFUSAL,
                    pointer=f"/nodes/{node_id}/effects",
                    message=(
                        f"node {node_id!r} declares a shared artifact write at effective depth "
                        f"{depth!r}; a shared write is legal only at effective depth 'stage' "
                        "(CONTRACT §3's blast-radius rule)"
                    ),
                )
            )
    return violations
