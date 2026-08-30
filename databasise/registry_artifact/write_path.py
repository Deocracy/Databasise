"""D-02's second blast-radius call site: the artifact-write path itself.

D-02: the blast-radius rule is enforced at **both** the validator (load time,
``databasise/validator/blast_radius.py``) and here, at the artifact-write path, before writing.
Depth is stamped data by run time, so this second check is nearly free — it reads the effective
depth the runner already computed rather than recomputing it. What it buys is that no path
reaching the artifact registry can bypass the rule: not a test helper, not a repair script, not a
later phase's opaque-node admission. Reversibility: reversible — two call sites, no stored state.

This module reuses ``validator.blast_radius.blast_radius_violations`` — the identical predicate
the load-time check uses — rather than restating the shared/stage condition here, by constructing
the minimal single-node ``ParsedWiring`` that function expects. This guarantees the two call
sites cannot drift: they are, literally, one function.

``write_artifact`` is the only sanctioned route to ``registry_artifact.index.register`` — it is
the sole caller anywhere in this codebase that holds ``REGISTER_AUTHORIZATION``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from databasise.parts.schema import Part, WiringNode
from databasise.registry_artifact.index import (
    REGISTER_AUTHORIZATION,
    ArtifactRecord,
    ArtifactRegistry,
)
from databasise.validator.blast_radius import blast_radius_violations
from databasise.validator.parse import ParsedWiring

if TYPE_CHECKING:
    from databasise.stores.blob import FilesystemBlobStore
    from databasise.validator.errors import Violation

_WRITE_PATH_NODE_ID = "artifact_write"


class BlastRadiusRefusal(RuntimeError):
    """Raised by ``write_artifact`` when the blast-radius rule refuses the write. Carries the
    same ``Violation`` (and therefore the same violation code) the load-time check would raise
    for the identical situation, since both call sites run the same predicate.
    """

    def __init__(self, violation: Violation) -> None:
        self.violation = violation
        super().__init__(violation.message)


def _blast_radius_check(*, scope: str, effective_depth: str | None) -> Violation | None:
    """Delegate to ``blast_radius_violations`` by constructing the minimal single-node
    ``ParsedWiring`` it expects, rather than restating the shared/stage condition here.
    """
    node = WiringNode(
        component="artifact-write@write-path", kind="stage", effects=["writes_artifact"], deps=[]
    )
    part = Part(
        name_at_version="artifact-write@write-path",
        kind="stage",
        structural_depth="opaque",  # unused: blast_radius_violations reads depth_map, not this
        effects=["writes_artifact"],
        upstream_ref=None,
        artifact_scope=scope,
    )
    parsed = ParsedWiring(
        nodes={_WRITE_PATH_NODE_ID: node},
        parts={_WRITE_PATH_NODE_ID: part},
        deps={_WRITE_PATH_NODE_ID: ()},
        node_order=(_WRITE_PATH_NODE_ID,),
    )
    violations = blast_radius_violations(parsed, {_WRITE_PATH_NODE_ID: effective_depth})
    return violations[0] if violations else None


def write_artifact(
    *,
    content: bytes,
    scope: str,
    effective_depth: str | None,
    namespace: str,
    sa2_chunker: str,
    sa2_extraction: str,
    sa2_embedding: str,
    corpus_id: str,
    space_id: str | None,
    producer_instance_hash: str,
    recipe_hash: str,
    blob_store: FilesystemBlobStore,
    registry: ArtifactRegistry,
    retention_tier: str = "runnable",
) -> ArtifactRecord:
    """Write ``content`` and register it, refusing before touching the blob store if the
    blast-radius rule refuses the write — so a refusal leaves no orphan content behind. A missing
    or ``None`` ``effective_depth`` is treated as a refusal, never defaulted to ``stage``:
    absence of a depth stamp means the runner did not compute one, and defaulting to the
    permissive value would make the whole rule bypassable by omission (this falls out of
    ``blast_radius_violations``'s own ``!= "stage"`` comparison, which is true for ``None``).

    On success, the content is put into the blob store first, then the row is registered against
    the returned content hash; if registration fails, the blob remains but is unreferenced, which
    is safe because the blob store is content-addressed and a later identical ``put`` is a no-op.
    """
    violation = _blast_radius_check(scope=scope, effective_depth=effective_depth)
    if violation is not None:
        raise BlastRadiusRefusal(violation)

    content_hash = blob_store.put(content)
    return registry.register(
        _authorization=REGISTER_AUTHORIZATION,
        effect="writes_artifact",
        content_hash=content_hash,
        namespace=namespace,
        scope=scope,
        sa2_chunker=sa2_chunker,
        sa2_extraction=sa2_extraction,
        sa2_embedding=sa2_embedding,
        corpus_id=corpus_id,
        space_id=space_id,
        producer_instance_hash=producer_instance_hash,
        recipe_hash=recipe_hash,
        retention_tier=retention_tier,
    )
