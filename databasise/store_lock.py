"""Cross-process store lock: one engine process per store root (RUN-07, D-01, D-04, G-36).

``fcntl.flock`` on ``<store_root>/.engine.lock``. Cross-process only (D-04): it does not guard two
engines inside one process. The kernel releases the lock on any exit including SIGKILL, and the fd
is opened close-on-exec, so v1 driver subprocesses cannot keep it alive after the engine dies.
The holder writes its PID into the file so a refused second launcher can name it.

Only ``main()`` functions take this lock, never library functions. This module is deliberately not
under ``stores/``: it is a process-level lock, not the Phase 10 in-process graph handle (STOR-01).
"""

from __future__ import annotations

import contextlib
import fcntl
import os
import time
from collections.abc import Iterator
from pathlib import Path

LOCK_FILE_NAME = ".engine.lock"

# The holder is between flock() and write(); retry the PID read this many times.
_PID_READ_ATTEMPTS = 10
_PID_READ_DELAY_S = 0.1


class StoreLockedError(RuntimeError):
    """Another databasise process holds this store root."""

    def __init__(self, store_root: Path, holder_pid: int | None):
        self.store_root = store_root
        self.holder_pid = holder_pid
        super().__init__(
            f"store root {store_root} is held by databasise process {holder_pid or 'unknown'}; "
            "one engine process per store root (G-36)"
        )


def _read_holder_pid(fd: int) -> int | None:
    for attempt in range(_PID_READ_ATTEMPTS):
        raw = os.pread(fd, 32, 0).strip()
        if raw:
            try:
                return int(raw)
            except ValueError:
                return None
        if attempt < _PID_READ_ATTEMPTS - 1:
            time.sleep(_PID_READ_DELAY_S)
    return None


def acquire_store_lock(store_root: str | Path) -> int:
    """Take the exclusive lock, write this PID into it, and return the open fd.

    Closing the returned fd releases the lock. Raises :class:`StoreLockedError` if held.
    """
    root = Path(store_root)
    root.mkdir(parents=True, exist_ok=True)
    fd = os.open(root / LOCK_FILE_NAME, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        holder = _read_holder_pid(fd)
        os.close(fd)
        raise StoreLockedError(root, holder) from None
    except BaseException:
        os.close(fd)
        raise
    os.ftruncate(fd, 0)
    os.write(fd, str(os.getpid()).encode())
    return fd


@contextlib.contextmanager
def store_lock(store_root: str | Path) -> Iterator[int]:
    fd = acquire_store_lock(store_root)
    try:
        yield fd
    finally:
        os.close(fd)
