"""``databasise.seam.redact`` — the D-05 two-tier leak gate (04-RESEARCH.md Pitfall 8), shipped as
library code under ``databasise/seam/`` rather than test-only code, because 04-05's REST transport
must assert against the exact same gate rather than a second copy of it.

**Why two tiers, not one blind substring search (Pitfall 8).** High-entropy identity values
(``wiring_instance_hash``, every node's ``instance_hash``, ``run_id`` — a random UUID) are
effectively unguessable digests (``databasise/identity/instance.py``) — astronomically improbable
to collide with real content, so a blind substring search over the envelope's full serialized JSON
text is safe and sufficient for them. Low-entropy identity values (``wiring_id``, ``arm_id``, every
node's ``node_id``) are short, human-readable, English-word-like strings — the LightRAG base
wiring's own node id ``keywords`` is an ordinary English word, and its ``wiring_id`` is the literal
``lightrag-base``. A blind substring search over free text produces a false positive the instant a
corpus, or an answer, legitimately contains one of those words.

**CR-04: the low-entropy tier is two checks, not one (structural key-walk plus a scoped value-walk)
— never one blind substring search over free text.** The key-walk (``assert_no_forbidden_keys``)
never inspects string *content*, only dict *keys*, at every nesting depth: safe over every field,
including freeform ones, since a real word never collides with a dict key. That alone misses a
low-entropy identity leaking as a plain string *value* rather than a key (e.g. a node id sitting in
``SeamEvent.component``). ``assert_no_forbidden_values`` closes that gap, but — to avoid
reintroducing the exact false-positive problem the two-tier split exists to avoid — it is scoped:
it walks every string *value* at every nesting depth and checks it for *equality* (never substring
containment, except under the two reason keys described below) against a forbidden low-entropy value, skipping only the fields named in
``FREEFORM_VALUE_KEYS`` (today: ``answer`` — the one field whose content is genuinely free text an
LLM composed, where a legitimate word could equal a low-entropy identity by coincidence, e.g. the
LightRAG base wiring's own ``keywords`` node id). Every other string-valued field in the envelope
(``SeamEvent.component``, ``stop_reason``, ``degradation_reason``, ``EvidenceRef.kind``/``namespace``
/``ref``, ``TokenBreakdownEntry.counted_by``, ...) is structured, program-controlled output — never
composed from a corpus or an LLM completion — so an exact-value match there is never a legitimate
coincidence and is always the leak this gate exists to catch.

**When the gate fires, the gate is not what changes (this phase's own prohibition).** If any check
below produces a false positive, the fix is a more precise version of the same two-tier split —
narrowing ``FREEFORM_VALUE_KEYS`` further if needed — never narrowing the forbidden set or swapping
the corpus for a quieter one. If it produces a true positive, the fix is the redaction bug, not this
module.

**The two reason fields are the one exception to equality (Phase 13 D-05).** ``stop_reason`` and
``degradation_reason`` (``REASON_VALUE_KEYS``) are closed codes, so ``assert_no_forbidden_values`` also
fails when one of them *contains* a forbidden low-entropy value as a substring: that is how
``"node 'chunk-vector': ..."`` is caught. Every other key keeps the equality check, so an answer or
any other value that merely contains a node-id word never trips it.

**The ``assert_*`` checks are a test-time gate.** They are called by tests and by the leak gate over
recorded responses, never on the response path while serving. They raise ``AssertionError``
explicitly rather than using ``assert``, so they still fire under ``python -O``.

**``node_free_reason`` is the response-time check (D-05, D-23).** The engine runs it on the two reason
fields only, of the envelope and of the non-debug trace: a value that is not one of the closed reason
codes becomes ``node_failed`` and is logged at error level. It never raises, so a regression or an
old stored free-text reason can never turn a served response into a 500.
"""

from __future__ import annotations

import logging
from typing import Any

from databasise.runner.trace import REASON_CODES, REASON_NODE_FAILED

logger = logging.getLogger(__name__)

# The only field this gate treats as genuinely free text (composed by an LLM from corpus content,
# where a legitimate word could coincidentally equal a low-entropy identity — see module docstring,
# CR-04). Every other string-valued field in the envelope is structured, program-controlled output,
# so `assert_no_forbidden_values` checks it for an exact match against the forbidden set.
FREEFORM_VALUE_KEYS = frozenset({"answer"})

# The two consumer reason fields, closed codes by D-05: a forbidden identity anywhere inside one is a
# leak, so these keys are substring-checked while every other key keeps the equality check.
REASON_VALUE_KEYS = frozenset({"stop_reason", "degradation_reason"})


def forbidden_identities(run_record: dict[str, Any]) -> tuple[set[str], set[str]]:
    """Build the ground-truth forbidden set from a run record dict (the shape
    ``RunRecord.to_dict()`` produces), returning ``(high_entropy, low_entropy)``. Built from the
    record's own fields at call time — never a literal restated by a caller — so the set can never
    drift out of date with what a real run actually carries.

    High entropy: the run's ``wiring_instance_hash``, its ``run_id`` (a random UUID — CR-04), and
    every node's ``instance_hash``. Low entropy: the run's ``wiring_id``, its ``arm_id``, and every
    node's ``node_id`` — short, human-readable strings a blind substring search would
    false-positive on.
    """
    high_entropy = {run_record["wiring_instance_hash"], run_record["run_id"]}
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
            if key in low_entropy:
                raise AssertionError(f"forbidden key {key!r} found at {path}.{key}")
            assert_no_forbidden_keys(value, low_entropy, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            assert_no_forbidden_keys(item, low_entropy, f"{path}[{i}]")


def assert_no_forbidden_values(
    obj: Any,
    low_entropy: set[str],
    *,
    freeform_keys: frozenset[str] = FREEFORM_VALUE_KEYS,
    path: str = "$",
) -> None:
    """Walk a parsed (not re-serialized) structure and fail if any string *value*, at any nesting
    depth, under a key not in ``freeform_keys``, equals a forbidden low-entropy value — the value
    half of the leak gate CR-04 adds. Equality only, never substring containment, and never over a
    freeform field's own value: see module docstring for why this scoping is what keeps this check
    from reintroducing the false-positive problem the two-tier split exists to avoid.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            child_path = f"{path}.{key}"
            if key in freeform_keys:
                continue
            if isinstance(value, str):
                if value in low_entropy:
                    raise AssertionError(f"forbidden low-entropy value {value!r} found at {child_path}")
                if key in REASON_VALUE_KEYS and any(identity in value for identity in low_entropy if identity):
                    raise AssertionError(f"forbidden low-entropy value found inside the reason at {child_path}")
            else:
                assert_no_forbidden_values(value, low_entropy, freeform_keys=freeform_keys, path=child_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            assert_no_forbidden_values(item, low_entropy, freeform_keys=freeform_keys, path=f"{path}[{i}]")


def node_free_reason(value: Any, low_entropy: set[str]) -> Any:
    """The response-time check for one consumer reason field (Phase 13 D-05, D-23): ``None`` stays
    ``None``, a closed reason code passes unchanged, and anything else (free text, a code with text
    appended, a non-string) becomes ``node_failed`` with one error-level log line saying whether a
    forbidden identity was found in it. The value itself is never logged. Never raises."""
    if value is None or (isinstance(value, str) and value in REASON_CODES):
        return value
    try:
        leaked = isinstance(value, str) and any(identity in value for identity in low_entropy if identity)
    except Exception:  # noqa: BLE001 - this check must never turn a served response into a 500
        leaked = False
    logger.error(
        "a consumer reason field was not a closed code and was served as %s (forbidden identity found: %s)",
        REASON_NODE_FAILED,
        leaked,
    )
    return REASON_NODE_FAILED


__all__ = [
    "FREEFORM_VALUE_KEYS",
    "REASON_VALUE_KEYS",
    "node_free_reason",
    "forbidden_identities",
    "assert_no_forbidden_keys",
    "assert_no_forbidden_values",
]
