"""Instance identity: (name@version, config_hash, resolved_dependency_ids), per CONTRACT.md §1.

A wiring node id is a position in the wiring, never an instance identity (the wiring-spec's
node-id-is-a-position rule: "two nodes MAY share the same component@version with identical
config as legitimate fan-out, and a validator that keys nodes by instance identity silently
drops one branch") — neither function below accepts a node id parameter.
"""

from __future__ import annotations

import hashlib
from typing import Any

from databasise.identity.canon import canonicalise


def instance_hash(
    name_at_version: str, config_hash: str, resolved_dependency_ids: list[str]
) -> str:
    """SHA-256 over the canonicalised ``[name_at_version, config_hash, sorted(dep_ids)]`` tuple."""
    payload = [name_at_version, config_hash, sorted(resolved_dependency_ids)]
    return hashlib.sha256(canonicalise(payload)).hexdigest()


def cache_partition_key(
    name_at_version: str,
    config_hash: str,
    resolved_dependency_ids: list[str],
    declared_input_values: Any,
) -> str:
    """Per the wiring-spec's cache-partition-key clause (PARTS-04 D7): derivable from exactly
    the ``(name@version, config_hash, resolved_dependency_ids)`` tuple plus declared input
    values, and MUST NOT include any field outside them.
    """
    payload = [
        name_at_version,
        config_hash,
        sorted(resolved_dependency_ids),
        declared_input_values,
    ]
    return hashlib.sha256(canonicalise(payload)).hexdigest()
