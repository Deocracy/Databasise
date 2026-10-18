"""Phase 10 review WR-01: the last release closes the shared client under the registry lock, so an
acquire that races a slow close waits for it instead of reading RocksDB's still-held LOCK as a
``GraphStoreBusyError`` (HTTP 409 on a store nothing else holds)."""

from __future__ import annotations

import threading
import time

from databasise.stores.graph import CozoGraphStore


class _SlowCloseClient:
    def __init__(self, real):
        self._real = real

    def close(self):
        time.sleep(0.5)
        self._real.close()

    def __getattr__(self, name):
        return getattr(self._real, name)


def test_an_acquire_during_a_slow_close_waits_and_opens_without_a_busy_error(store_root):
    first = CozoGraphStore("g", "ws", store_root)
    first._shared.client = _SlowCloseClient(first._shared.client)
    releasing = threading.Thread(target=first._release)
    releasing.start()
    time.sleep(0.1)  # the close is now in flight

    second = CozoGraphStore("g", "ws", store_root)  # must not raise GraphStoreBusyError

    releasing.join()
    second._release()
