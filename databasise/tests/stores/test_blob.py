"""Tests for databasise/stores/blob.py: FilesystemBlobStore's content addressing, fan-out
layout, and range reads. One test per <behavior> claim in 01-05-PLAN.md's Task 3 (tests 1-8).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from databasise.stores.blob import BlobNotFoundError, FilesystemBlobStore


def test_1_put_returns_sha256_digest_and_get_returns_identical_bytes(tmp_path: Path):
    store = FilesystemBlobStore(namespace="ns", workspace="ws", store_root=tmp_path)
    content = b"hello world"

    digest = store.put(content)

    assert digest == hashlib.sha256(content).hexdigest()
    assert store.get(digest) == content


def test_2_put_on_identical_content_twice_is_a_no_op(tmp_path: Path):
    store = FilesystemBlobStore(namespace="ns", workspace="ws", store_root=tmp_path)
    content = b"repeated content"

    digest1 = store.put(content)
    digest2 = store.put(content)  # must not raise, must not create a second file

    assert digest1 == digest2
    files = [p for p in (tmp_path / "ws" / "ns" / "blobs").rglob("*") if p.is_file()]
    assert len(files) == 1


def test_3_on_disk_path_is_derivable_from_digest_alone_and_matches_fan_out_layout(
    tmp_path: Path,
):
    store = FilesystemBlobStore(namespace="ns", workspace="ws", store_root=tmp_path)
    digest = store.put(b"fan-out layout check")

    expected = tmp_path / "ws" / "ns" / "blobs" / digest[:2] / digest[2:4] / digest
    assert expected.exists()
    assert store._path_for(digest) == expected


def test_4_get_on_unknown_digest_raises_named_error(tmp_path: Path):
    store = FilesystemBlobStore(namespace="ns", workspace="ws", store_root=tmp_path)

    with pytest.raises(BlobNotFoundError):
        store.get("ab" * 32)


def test_5_put_of_zero_length_content_succeeds_and_round_trips(tmp_path: Path):
    store = FilesystemBlobStore(namespace="ns", workspace="ws", store_root=tmp_path)

    digest = store.put(b"")

    assert digest == hashlib.sha256(b"").hexdigest()
    assert store.get(digest) == b""


def test_6_delete_removes_blob_and_leaves_siblings_intact_and_is_a_no_op_on_absent(
    tmp_path: Path,
):
    store = FilesystemBlobStore(namespace="ns", workspace="ws", store_root=tmp_path)
    digest_a = store.put(b"blob a")
    digest_b = store.put(b"blob b")

    store.delete(digest_a)

    with pytest.raises(BlobNotFoundError):
        store.get(digest_a)
    assert store.get(digest_b) == b"blob b"

    store.delete("cd" * 32)  # absent digest — no-op, not an error


def test_7_read_range_returns_the_requested_bytes_and_raises_past_the_end(tmp_path: Path):
    store = FilesystemBlobStore(namespace="ns", workspace="ws", store_root=tmp_path)
    content = b"0123456789"
    digest = store.put(content)

    assert store.read_range(digest, offset=2, length=4) == b"2345"

    with pytest.raises(ValueError):
        store.read_range(digest, offset=8, length=10)


def test_8_blob_written_under_one_namespace_is_not_visible_from_a_different_namespace(
    tmp_path: Path,
):
    store_a = FilesystemBlobStore(namespace="ns-a", workspace="ws", store_root=tmp_path)
    store_b = FilesystemBlobStore(namespace="ns-b", workspace="ws", store_root=tmp_path)

    digest = store_a.put(b"only in a")

    with pytest.raises(BlobNotFoundError):
        store_b.get(digest)
