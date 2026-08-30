"""RFC 8785 (JCS) canonicalisation and config_hash computation, per CONTRACT.md §1.

config_hash MUST be computed over the author-supplied node config VERBATIM — never a tool's
normalised, defaulted, or reordered output ("re-hashing byte-identical input after a
defaulted-option change has already destroyed in-flight A/B baselines," CONTRACT.md §1). This
module never normalises, defaults, or reorders ``node_config``; the caller decides what to pass
when a node declares no config of its own. An absent ``config`` key is therefore NOT normalised
into an empty object here: ``config_hash(None)`` (config key absent) and ``config_hash({})``
(config key explicitly empty) are pinned to hash differently, because an absent key and an
explicitly empty object are not the same author-supplied input.

Pinned contract a later reader MUST NOT silently change (CONTRACT.md §1; RFC 8785 §3.2.3): object
key ordering is by UTF-16 code-unit sequence, never by Unicode code point and never by locale
collation; no Unicode normalisation form (NFC or NFD) is applied, so two canonically-equivalent
strings that differ in bytes hash differently.

RFC 8785 (JCS) collapses the int/float distinction, so ``1`` and ``1.0`` hash identically
(verified empirically against the installed package this session). CONTRACT.md §1 requires
excluding integers outside the SIGNED 64-BIT range; the installed ``rfc8785==0.1.4`` enforces a
narrower domain than that (JavaScript's ``Number.isSafeInteger`` range, ±(2**53-1)) as a
library-imposed guard, not a real precision limit — its own integer-serialisation path writes
``str(int)`` exactly and losslessly for any magnitude (verified by reading
``rfc8785._impl.dump``'s ``int`` branch this session). This module therefore (1) walks every
integer in the input itself first and raises ``CanonicalisationError`` naming the offending
JSON-Pointer path for anything outside int64, then (2) temporarily widens ``rfc8785``'s internal
domain constants to int64 for the duration of the call so its own exact serialisation path
executes for the CONTRACT-legal range it would otherwise reject. This is a documented deviation
from a bare ``rfc8785.dumps()`` call, not a change to JCS's canonical output for any value both
the library's default domain and CONTRACT.md §1 already accept.
"""

from __future__ import annotations

import hashlib
import threading
from typing import Any

import rfc8785
import rfc8785._impl as _rfc8785_impl

INT64_MIN = -(2**63)
INT64_MAX = 2**63 - 1

# Serialises the widen-then-restore of rfc8785's private domain constants below, so two
# canonicalise() calls interleaved across threads (e.g. via loop.run_in_executor) cannot observe
# each other's temporarily-widened bounds. Single-threaded asyncio callers never contend on this
# lock, since nothing inside the widened block awaits.
_domain_patch_lock = threading.Lock()


class CanonicalisationError(ValueError):
    """An object could not be canonicalised per RFC 8785 (e.g. an int outside int64 range)."""


def _walk_int64_range(obj: Any, path: str = "") -> None:
    """Raise ``CanonicalisationError`` naming the offending JSON-Pointer ``path`` for any
    integer in ``obj`` outside the signed 64-bit range CONTRACT.md §1 requires. ``bool`` is a
    subclass of ``int`` in Python but is never a numeric config value here, so it is excluded.
    """
    if isinstance(obj, bool):
        return
    if isinstance(obj, int):
        if obj < INT64_MIN or obj > INT64_MAX:
            raise CanonicalisationError(
                f"integer {obj} at {path or '<root>'} exceeds the signed 64-bit range "
                f"CONTRACT.md §1 admits ([{INT64_MIN}, {INT64_MAX}])"
            )
        return
    if isinstance(obj, dict):
        for key, value in obj.items():
            _walk_int64_range(value, f"{path}/{key}")
        return
    if isinstance(obj, (list, tuple)):
        for idx, value in enumerate(obj):
            _walk_int64_range(value, f"{path}/{idx}")
        return


def canonicalise(obj: Any) -> bytes:
    """Return the RFC 8785 (JCS) canonical serialisation of ``obj`` as bytes."""
    _walk_int64_range(obj)
    with _domain_patch_lock:
        original_bounds = (_rfc8785_impl._INT_MIN, _rfc8785_impl._INT_MAX)
        _rfc8785_impl._INT_MIN, _rfc8785_impl._INT_MAX = INT64_MIN, INT64_MAX
        try:
            return rfc8785.dumps(obj)
        except rfc8785.CanonicalizationError as exc:
            raise CanonicalisationError(str(exc)) from exc
        finally:
            _rfc8785_impl._INT_MIN, _rfc8785_impl._INT_MAX = original_bounds


def config_hash(node_config: dict[str, Any] | None, env: str | None = None) -> str:
    """SHA-256 over the JCS canonicalisation of ``{"config": node_config, "environment": env}``.

    ``node_config=None`` (the config key is absent entirely) omits the ``"config"`` member from
    the hashed payload rather than normalising it to ``{}`` — see the module docstring's pinned
    absent-vs-empty rule.

    ``env`` defaults to :func:`databasise.identity.env.environment_hash` when omitted — imported
    locally below to avoid a module-import cycle (``env.py`` imports ``canonicalise`` from this
    module at module scope).
    """
    # Local import: avoids a module cycle (env.py imports canonicalise from this module).
    from databasise.identity.env import environment_hash

    resolved_env = env if env is not None else environment_hash()
    payload: dict[str, Any] = {"environment": resolved_env}
    if node_config is not None:
        payload["config"] = node_config
    return hashlib.sha256(canonicalise(payload)).hexdigest()
