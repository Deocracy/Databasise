"""Tests for identity/canon.py and identity/env.py, per plan 01-04's <behavior> Tests 1-10.

Every CONTRACT.md §1 identity rule this plan hardens — int64 exclusion, int/float collapse,
byte sensitivity, key-order insensitivity, UTF-16 code-unit key ordering, no Unicode
normalisation, absent-vs-empty config, environment participation, and environment content — is
covered by one test each, numbered to match the plan's own behavior list.
"""

from __future__ import annotations

import hashlib
import unicodedata
from unittest.mock import patch

from databasise.identity import env as env_module
from databasise.identity.canon import CanonicalisationError, canonicalise, config_hash


class _FakeDistribution:
    """A minimal ``importlib.metadata.Distribution``-shaped stub for Test 9's version-change
    sensitivity assertion — avoids depending on which real distributions happen to be installed.
    """

    def __init__(self, name: str, version: str, record_text: str | None = None):
        self.metadata = {"Name": name}
        self.version = version
        self._record_text = record_text

    def read_text(self, filename: str) -> str | None:
        return self._record_text if filename == "RECORD" else None


def _hash_payload(payload: object) -> str:
    return hashlib.sha256(canonicalise(payload)).hexdigest()


def test_1_int_and_float_collapse_to_the_same_digest():
    assert config_hash({"n": 1}) == config_hash({"n": 1.0})


def test_2_int64_boundary_is_asserted_on_both_ends():
    # In range: the exact int64 boundary on both ends succeeds.
    config_hash({"n": 2**63 - 1})
    config_hash({"n": -(2**63)})

    # One step outside the boundary on both ends raises.
    try:
        config_hash({"n": 2**63})
    except CanonicalisationError:
        pass
    else:
        raise AssertionError("expected CanonicalisationError for 2**63")

    try:
        config_hash({"n": -(2**63) - 1})
    except CanonicalisationError:
        pass
    else:
        raise AssertionError("expected CanonicalisationError for -(2**63)-1")


def test_3_a_single_byte_difference_in_a_string_value_changes_the_digest():
    base = {"note": "tracer-fixture"}
    changed = {"note": "tracer-fixturd"}  # last char differs by one byte
    assert config_hash(base) != config_hash(changed)


def test_4_key_order_does_not_affect_the_digest():
    assert config_hash({"a": 1, "b": 2}) == config_hash({"b": 2, "a": 1})


def test_5_jcs_key_ordering_is_by_utf16_code_unit_not_unicode_code_point():
    # U+E000 is a single UTF-16 code unit (0xE000); U+10000 requires a UTF-16 surrogate pair
    # whose first code unit is 0xD800 — smaller than 0xE000. UTF-16 code-unit order therefore
    # puts the supplementary-plane key FIRST, the opposite of Unicode code-point order (where
    # U+10000 > U+E000 puts it last). This pins that divergence with a literal expected digest
    # so a future canonicaliser swap cannot silently flip the answer.
    key_bmp = ""
    key_supplementary = "\U00010000"
    assert ord(key_supplementary) > ord(key_bmp)  # code-point order disagrees with the pin below

    canonical_bytes = canonicalise({key_bmp: 1, key_supplementary: 2})

    assert canonical_bytes == b'{"\xf0\x90\x80\x80":2,"\xee\x80\x80":1}'
    assert (
        hashlib.sha256(canonical_bytes).hexdigest()
        == "9d4cdc71dda603c42f9b21d88d0c2ffc31a76cd1bd461d7359406cf169845f1e"
    )


def test_6_no_unicode_normalisation_is_applied():
    nfc = "café"
    nfd = unicodedata.normalize("NFD", nfc)
    assert nfc != nfd  # distinct byte sequences, canonically equivalent
    assert unicodedata.normalize("NFC", nfd) == nfc

    assert config_hash({"s": nfc}) != config_hash({"s": nfd})


def test_7_absent_config_key_hashes_differently_from_an_explicitly_empty_one():
    assert config_hash({}) == config_hash({})  # stable across repeated calls
    assert config_hash(None) != config_hash({})


def test_8_environment_participates_in_config_hash():
    node_config = {"k": "v"}
    with patch("databasise.identity.env.environment_hash", return_value="env-a"):
        hash_with_env_a = config_hash(node_config)
    with patch("databasise.identity.env.environment_hash", return_value="env-b"):
        hash_with_env_b = config_hash(node_config)
    assert hash_with_env_a != hash_with_env_b


def test_9_environment_hash_is_stable_reflects_version_changes_and_excludes_nix_store_paths():
    # Stable across two calls in the same process (functools.cache-backed memoisation).
    assert env_module.environment_hash() == env_module.environment_hash()

    # Sensitive to a distribution's version — exercised via the uncached collector, since the
    # public environment_hash() is cached per process and would not observe a mocked swap.
    dists_v1 = [_FakeDistribution("fixture-pkg", "1.0.0")]
    dists_v2 = [_FakeDistribution("fixture-pkg", "2.0.0")]
    with patch.object(env_module, "distributions", return_value=dists_v1):
        payload_v1 = env_module._collect_environment_payload()
    with patch.object(env_module, "distributions", return_value=dists_v2):
        payload_v2 = env_module._collect_environment_payload()
    assert _hash_payload(payload_v1) != _hash_payload(payload_v2)

    # The real digest input never embeds a Nix store path (D-12; Nix is substrate-only).
    real_payload = env_module._collect_environment_payload()
    assert b"/nix/store/" not in canonicalise(real_payload)


def test_10_max_concurrency_participates_in_config_hash():
    base = {"max_concurrency": 2, "note": "tracer-fixture"}
    changed = {"max_concurrency": 3, "note": "tracer-fixture"}
    assert config_hash(base) != config_hash(changed)
