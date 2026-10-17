"""In-process tests of ``databasise.store_lock`` (08-06, RUN-07).

A second ``open()`` of the lock file in the same process is refused by flock (it binds the open
file description), so no subprocess is needed. Names this phase creates are imported inside the tests.
"""

from __future__ import annotations

import fcntl
import os

import pytest


def test_acquire_creates_a_missing_root_and_writes_the_pid(tmp_path):
    from databasise.store_lock import LOCK_FILE_NAME, acquire_store_lock

    root = tmp_path / "does" / "not" / "exist"
    fd = acquire_store_lock(root)
    try:
        assert (root / LOCK_FILE_NAME).read_text() == str(os.getpid())
    finally:
        os.close(fd)


def test_a_second_acquire_in_the_same_process_is_refused_with_this_pid(tmp_path):
    from databasise.store_lock import StoreLockedError, acquire_store_lock

    root = tmp_path / "store"
    fd = acquire_store_lock(root)
    try:
        with pytest.raises(StoreLockedError) as excinfo:
            acquire_store_lock(root)
        assert excinfo.value.holder_pid == os.getpid()
        assert str(root) in str(excinfo.value)
    finally:
        os.close(fd)


def test_a_symlinked_spelling_of_a_held_root_is_refused(tmp_path, monkeypatch):
    from databasise.store_lock import StoreLockedError, acquire_store_lock

    root = tmp_path / "store"
    link = tmp_path / "link"
    link.symlink_to(root)
    fd = acquire_store_lock(root)
    try:
        with pytest.raises(StoreLockedError):
            acquire_store_lock(link)
        monkeypatch.chdir(root.parent)
        with pytest.raises(StoreLockedError):
            acquire_store_lock(os.path.relpath(root))
    finally:
        os.close(fd)


def test_a_holder_that_wrote_no_pid_is_reported_as_unknown(tmp_path):
    from databasise.store_lock import (
        LOCK_FILE_NAME,
        StoreLockedError,
        acquire_store_lock,
    )

    root = tmp_path / "store"
    root.mkdir()
    holder = os.open(root / LOCK_FILE_NAME, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(StoreLockedError) as excinfo:
            acquire_store_lock(root)
        assert excinfo.value.holder_pid is None
        assert "unknown" in str(excinfo.value)
    finally:
        os.close(holder)


def test_the_context_manager_releases_on_exit(tmp_path):
    from databasise.store_lock import acquire_store_lock, store_lock

    root = tmp_path / "store"
    with store_lock(root):
        pass
    os.close(acquire_store_lock(root))


def test_the_lock_fd_is_not_inheritable(tmp_path):
    from databasise.store_lock import acquire_store_lock

    fd = acquire_store_lock(tmp_path / "store")
    try:
        assert os.get_inheritable(fd) is False
    finally:
        os.close(fd)
