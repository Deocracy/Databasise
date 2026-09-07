"""``databasise.seam.redact`` — the D-05 two-tier leak gate (04-RESEARCH.md Pitfall 8), shipped as
library code under ``databasise/seam/`` rather than test-only code, because 04-05's REST transport
must assert against the exact same gate rather than a second copy of it.

**Why two tiers, not one blind substring search (Pitfall 8).** High-entropy identity values
(``wiring_instance_hash``, every node's ``instance_hash``) are 64-hex-char SHA-256 digests
(``databasise/identity/instance.py``) — astronomically improbable to collide with real content, so
a blind substring search over the envelope's full serialized JSON text is safe and sufficient for
them. Low-entropy identity values (``wiring_id``, ``arm_id``, every node's ``node_id``) are short,
human-readable, English-word-like strings — the LightRAG base wiring's own node id ``keywords`` is
an ordinary English word, and its ``wiring_id`` is the literal ``lightrag-base``. A blind substring
search over free text produces a false positive the instant a corpus, or an answer, legitimately
contains one of those words. The low-entropy check below is therefore structural instead: it never
inspects string *content*, only dict *keys*, at every nesting depth — the leak vector a redaction
bug is far likelier to produce (a value accidentally left keyed by a node id) than the word leaking
into free text.

**When the gate fires, the gate is not what changes (this phase's own prohibition).** If either
check below produces a false positive, the fix is a more precise version of the same two-tier
split, never narrowing the forbidden set or swapping the corpus for a quieter one. If it produces a
true positive, the fix is the redaction bug, not this module.
"""

from __future__ import annotations

from typing import Any


def forbidden_identities(run_record: dict[str, Any]) -> tuple[set[str], set[str]]:
    """Build the ground-truth forbidden set from a run record dict (the shape
    ``RunRecord.to_dict()`` produces), returning ``(high_entropy, low_entropy)``. Built from the
    record's own fields at call time — never a literal restated by a caller — so the set can never
    drift out of date with what a real run actually carries.

    High entropy: the run's ``wiring_instance_hash`` and every node's ``instance_hash`` — 64-hex
    -char SHA-256 digests. Low entropy: the run's ``wiring_id``, its ``arm_id``, and every node's
    ``node_id`` — short, human-readable strings a blind substring search would false-positive on.
    """
    high_entropy = {run_record["wiring_instance_hash"]}
    low_entropy = {run_record["wiring_id"], run_record["arm_id"]}
    for node in run_record["nodes"]:
        high_entropy.add(node["instance_hash"])
        low_entropy.add(node["node_id"])
    return high_entropy, low_entropy


def assert_no_forbidden_keys(obj: Any, low_entropy: set[str], path: str = "$") -> None:
    """Walk a parsed (not re-serialized) structure and fail if any dict *key* at any nesting depth
    equals a forbidden low-entropy value — the structural half of the leak gate (Pitfall 8). Never
    inspects string content, so a corpus or an answer that legitimately contains a low-entropy
    value as a *word* never trips this check; only a value left *keyed* by one does.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            assert key not in low_entropy, f"forbidden key {key!r} found at {path}.{key}"
            assert_no_forbidden_keys(value, low_entropy, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            assert_no_forbidden_keys(item, low_entropy, f"{path}[{i}]")


__all__ = ["forbidden_identities", "assert_no_forbidden_keys"]
