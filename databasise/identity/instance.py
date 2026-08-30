"""Instance identity: (name@version, config_hash, resolved_dependency_ids), per CONTRACT.md §1.

A name is not an instance identity, and a wiring node id is not an instance identity — a node id
is a position in the wiring (the wiring-spec's node-id-is-a-position rule: "two nodes MAY share
the same component@version with identical config as legitimate fan-out, and a validator that
keys nodes by instance identity silently drops one branch"). None of the three functions below
accepts a node id parameter, structurally: their own signatures are the enforcement, not a
docstring promise a caller could ignore.

``cache_partition_key`` takes exactly four arguments, and its docstring below names the four
§1-admitted members. No optional keyword is added for a caller's convenience — §1 says the key
MUST NOT include any field outside the tuple plus declared input values, and the LightRAG
measured case (a doubly-mode-partitioned key that made arms partition apart) is what happens
when it does.
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
    the four §1-admitted members — ``name_at_version``, ``config_hash``,
    ``resolved_dependency_ids``, ``declared_input_values`` — and MUST NOT include any field
    outside them: not a node id, not an arm id, not a run id, not a query mode.
    """
    payload = [
        name_at_version,
        config_hash,
        sorted(resolved_dependency_ids),
        declared_input_values,
    ]
    return hashlib.sha256(canonicalise(payload)).hexdigest()


def runtime_instance_hash(
    component_instance_hash: str,
    runtime_config: dict[str, Any],
    parent_instance_hash: str,
    ordinal: int,
) -> str:
    """Runtime-minted identity for planner-emitted plan nodes, per CONTRACT.md §1: such nodes
    carry no author-supplied ``config_hash`` to hash, so their identity is instead
    ``H(component_instance_hash, JCS(runtime_config), parent_instance_hash, ordinal)`` — composed
    from exactly these four members. ``JCS(runtime_config)`` is embedded as canonicalised UTF-8
    text inside the outer tuple that is itself canonicalised and hashed, matching this module's
    own ``instance_hash``/``cache_partition_key`` pattern (one outer SHA-256 over one
    canonicalised tuple) rather than a bespoke concatenation scheme.
    """
    canonical_runtime_config = canonicalise(runtime_config).decode("utf-8")
    payload = [component_instance_hash, canonical_runtime_config, parent_instance_hash, ordinal]
    return hashlib.sha256(canonicalise(payload)).hexdigest()
