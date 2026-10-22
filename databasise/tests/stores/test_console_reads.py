"""16-07: store-level spies for the operator console reads (CONN-10 here; CONN-11 and CONN-13 are
added by later plans). A console read must not rebuild what it only lists.
"""

from __future__ import annotations

import numpy as np

from databasise.stores.vector import FaissVectorStore, load_committed


async def test_list_ids_never_reconstructs(store_root, monkeypatch):
    list_ids = getattr(FaissVectorStore, "list_ids", None)
    assert callable(list_ids), "FaissVectorStore has no list_ids (CONN-10)"

    writer = FaissVectorStore(namespace="ns", workspace="ws", store_root=store_root)
    await writer.upsert(
        ids=["c", "a", "b"],
        embeddings=np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]),
    )
    await writer.index_done_callback()

    # The narrowest object a reconstructing read would call: the loaded index's own class.
    index_class = type(load_committed(store_root / "ws" / "ns").index)

    def _forbidden(self, *args, **kwargs):
        raise AssertionError("list_ids reconstructed a vector")

    monkeypatch.setattr(index_class, "reconstruct", _forbidden)

    reader = FaissVectorStore(namespace="ns", workspace="ws", store_root=store_root)
    assert list_ids(reader, 0, 2) == (["a", "b"], 3)
    assert list_ids(reader, 2, 2) == (["c"], 3)

    missing = FaissVectorStore(namespace="never", workspace="ws", store_root=store_root)
    assert list_ids(missing, 0, 10) == ([], 0)
    assert not (store_root / "ws" / "never").exists()
