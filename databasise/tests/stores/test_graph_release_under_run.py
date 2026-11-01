"""Phase 10 sweep (graph-release-race): the last release of a shared client while another thread is
still inside ``client.run()`` — an asyncio-cancelled ``_run`` whose executor thread outlived the
await — makes pycozo refuse ``close()`` with ``RuntimeError('Already borrowed')``. The registry must
not let that escape (it would replace the refusal the engine is raising with a bare 500) and must keep
the still-open client, so the next open on the path reuses it instead of reading RocksDB's held LOCK
as ``GraphStoreBusyError``; the next last release retries the close."""

from __future__ import annotations

import logging
import threading

from databasise.stores.graph import CozoGraphStore, _ClientRegistry


class _BorrowedClient:
    """The real client behind a gate: ``run`` waits for ``gate`` before delegating, and ``close``
    refuses with pycozo's own borrow text while a run is in flight (PyO3's ``&mut`` borrow)."""

    def __init__(self, real):
        self._real = real
        self.gate = threading.Event()
        self.started = threading.Event()
        self.in_flight = 0
        self.closed = False

    def run(self, *args, **kwargs):
        self.in_flight += 1
        self.started.set()
        try:
            self.gate.wait()
            return self._real.run(*args, **kwargs)
        finally:
            self.in_flight -= 1

    def close(self):
        if self.in_flight:
            raise RuntimeError("Already borrowed")
        self.closed = True
        self._real.close()

    def __getattr__(self, name):
        return getattr(self._real, name)


def _hold_a_run(store):
    client = store._shared.client = _BorrowedClient(store._shared.client)
    # daemon: a failing assertion must not leave the gated run holding the interpreter open
    worker = threading.Thread(target=client.run, args=("?[id] := *nodes{id}", {}), daemon=True)
    worker.start()
    client.started.wait()
    return client, worker


def _assert_kept_then_reusable(store_root, key, client, worker, caplog):
    assert not client.closed
    assert _ClientRegistry._entries[key].client is client
    assert _ClientRegistry._entries[key].refcount == 0
    assert any("Already borrowed" in rec.getMessage() for rec in caplog.records)

    client.gate.set()
    worker.join()

    again = CozoGraphStore("g", "ws", store_root)  # must not raise GraphStoreBusyError
    assert again._client is client
    assert again._client.run("?[id] := *nodes{id}", {}) is not None  # still usable
    again._release()  # last release again: the close now succeeds
    assert client.closed
    assert key not in _ClientRegistry._entries


def test_a_release_under_an_in_flight_run_keeps_the_open_client_for_the_next_acquire(store_root, caplog):
    store = CozoGraphStore("g", "ws", store_root)
    client, worker = _hold_a_run(store)
    with caplog.at_level(logging.WARNING, logger="databasise.stores.graph"):
        store._release()  # refcount -> 0: close() refuses; nothing may escape
    _assert_kept_then_reusable(store_root, store._registry_key, client, worker, caplog)


async def test_finalize_under_an_in_flight_run_does_not_propagate_the_close_failure(store_root, caplog):
    store = CozoGraphStore("g", "ws", store_root)
    client, worker = _hold_a_run(store)
    with caplog.at_level(logging.WARNING, logger="databasise.stores.graph"):
        await store.finalize()  # the engine's finally: a refusal in flight must not be masked
    _assert_kept_then_reusable(store_root, store._registry_key, client, worker, caplog)
