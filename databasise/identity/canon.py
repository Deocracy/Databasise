"""RFC 8785 (JCS) canonicalisation and config_hash computation, per CONTRACT.md §1.

config_hash MUST be computed over the author-supplied node config VERBATIM — never a tool's
normalised, defaulted, or reordered output ("re-hashing byte-identical input after a
defaulted-option change has already destroyed in-flight A/B baselines," CONTRACT.md §1). This
module never normalises, defaults, or reorders ``node_config``; the caller decides what to pass
when a node declares no config of its own.

RFC 8785 (JCS) collapses the int/float distinction, so ``1`` and ``1.0`` hash identically, and
orders object keys by UTF-16 code unit — not by Unicode code point, and not by locale. The
installed ``rfc8785`` package already raises on an integer outside the int64 range (its own
``IntegerDomainError``, verified this session against the installed package); this module
re-raises that as the named ``CanonicalisationError`` below so every caller depends on one error
type regardless of which specific canonicalisation rule tripped.
"""

from __future__ import annotations

import hashlib
from typing import Any

import rfc8785


class CanonicalisationError(ValueError):
    """An object could not be canonicalised per RFC 8785 (e.g. an int outside int64 range)."""


def canonicalise(obj: Any) -> bytes:
    """Return the RFC 8785 (JCS) canonical serialisation of ``obj`` as bytes."""
    try:
        return rfc8785.dumps(obj)
    except rfc8785.CanonicalizationError as exc:
        raise CanonicalisationError(str(exc)) from exc


def config_hash(node_config: dict[str, Any], env: str | None = None) -> str:
    """SHA-256 over the JCS canonicalisation of ``{"config": node_config, "environment": env}``.

    ``env`` defaults to :func:`databasise.identity.env.environment_hash` when omitted — imported
    locally below to avoid a module-import cycle (``env.py`` imports ``canonicalise`` from this
    module at module scope).
    """
    # Local import: avoids a module cycle (env.py imports canonicalise from this module).
    from databasise.identity.env import environment_hash

    resolved_env = env if env is not None else environment_hash()
    payload = {"config": node_config, "environment": resolved_env}
    return hashlib.sha256(canonicalise(payload)).hexdigest()
