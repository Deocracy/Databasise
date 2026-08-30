"""Namespace derivation per RIG.md §RUN.1, and the one-directory-per-namespace layout (D-07).

This is a rule the machine applies, not a storage-keying design it invents: a namespace is
derived from the artifact-registry vocabulary CONTRACT §7 already froze — namespace, SA-2
sub-recipe stamps (chunker, extraction, embedding), corpus, ``space_id``, producing instance —
plus the arm's own SA-1 recipe identity from CONTRACT §1's ``(name@version, config_hash,
resolved_dependency_ids)`` tuple, exactly as RIG §RUN.1 states it. ``scope`` is included as an
explicit eighth input to the hash (alongside the seven RIG-named members) so a ``shared``
namespace and a ``quarantined`` namespace computed from an otherwise-identical recipe are
different namespaces — required because RIG §RUN.1 states an arm containing an ``opaque`` node
writes ``quarantined`` and never ``shared``, and its index is therefore instance-scoped and never
SA-1-shareable; collapsing the two scopes into one namespace would make that distinction
unimplementable.

D-07 (costly reversibility): this one-directory-per-namespace layout is baked into every
namespace-derivation call site and into every artifact-registry row written under it. Changing
the layout later is a migration of on-disk state, not a config edit.
"""

from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

from databasise.identity.canon import canonicalise

# Truncated hex-digest length for the namespace token: 32 hex chars = 128 bits, which keeps
# collision probability negligible for this project's namespace cardinality while staying
# readable as a directory name (versus the full 64-char SHA-256 digest).
_NAMESPACE_HEX_LENGTH = 32

# A derived namespace directory name is always `<scope>-<hex>` (scope is alnum/hyphen, hex is
# lowercase hex) — bare token, no path separator, no parent-directory reference, so a value
# handed to namespace_dir() can never escape store_root.
_NAMESPACE_TOKEN_RE = re.compile(r"^[A-Za-z0-9-]+$")


def derive_namespace(
    *,
    sa1_instance_hash: str,
    sa2_chunker: str,
    sa2_extraction: str,
    sa2_embedding: str,
    corpus_id: str,
    space_id: str | None,
    scope: str,
) -> str:
    """Derive a stable namespace identifier from exactly RIG §RUN.1's named inputs plus ``scope``.

    Computed as a SHA-256 over the RFC 8785 canonicalisation of the eight members below,
    truncated to a fixed hex prefix. ``space_id`` being ``None`` is a valid, stable input (not an
    error) — some producing instances have no space scoping.

    Returns ``"<scope>-<hex>"`` so the scope is visible in a plain ``ls`` of the store root,
    rather than being folded invisibly into an opaque hash.
    """
    payload = [
        sa1_instance_hash,
        sa2_chunker,
        sa2_extraction,
        sa2_embedding,
        corpus_id,
        space_id,
        scope,
    ]
    digest = hashlib.sha256(canonicalise(payload)).hexdigest()[:_NAMESPACE_HEX_LENGTH]
    return f"{scope}-{digest}"


def namespace_dir(store_root: Path, namespace: str) -> Path:
    """Return ``store_root / namespace``, refusing any namespace that could escape ``store_root``.

    ``namespace`` must be a bare token of hex digits, letters and hyphens only — no path
    separator, no parent-directory reference (``..``) — so a derived value can never resolve
    outside ``store_root``.
    """
    if not _NAMESPACE_TOKEN_RE.match(namespace):
        raise ValueError(
            f"invalid namespace token {namespace!r}: must match {_NAMESPACE_TOKEN_RE.pattern} "
            "(no path separator, no parent-directory reference)"
        )
    return Path(store_root) / namespace


def artifacts_overlap(recipe_hash_a: str, recipe_hash_b: str) -> bool:
    """RIG §RUN.2's artifact-overlap decision: an **iff** on index-recipe hashes, nothing else.

    Never a similarity judgment, never a prefix match, never a field-by-field comparison — hash
    equality only. The three §RUN.2 cases:

    1. Hash-identical recipes: the arms share the artifact and its single registry row —
       identical means shared, never a coincidence of two separately-built copies.
    2. Recipes differing in any resolved input: no overlap at all; each arm builds its own.
    3. The worked pair (VT-1's chunk/embed/upsert recipe vs. GR-1's LightRAG ingest core):
       structurally different recipes sharing no resolved input, so zero overlap and two full
       index costs — the concrete instance of case 2, not a hypothetical.
    """
    return recipe_hash_a == recipe_hash_b


def gc_namespace(store_root: Path, namespace: str) -> None:
    """Delete exactly ``namespace``'s directory tree under ``store_root``.

    This is what makes CONTRACT §3's "GC'd with the instance that produced it" rule for the
    ``quarantined`` scope a real operation rather than a promise. ``namespace_dir`` already
    refuses to resolve outside ``store_root``, so this never deletes anything else.
    """
    target = namespace_dir(store_root, namespace)
    shutil.rmtree(target, ignore_errors=True)
