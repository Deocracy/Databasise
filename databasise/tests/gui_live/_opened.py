"""18-02: the list of ``LiveUI`` objects opened during a run.

It lives in its own module, imported only by its full dotted name, so there is one list. pytest loads
``conftest.py`` as ``gui_live.conftest``, while a test that does ``from databasise.tests.gui_live.conftest
import open_live_ui`` loads a second copy of that file; a list kept in the conftest would be split
between the two copies and the call-phase page-error check would miss the UIs a test opens itself.
"""

from __future__ import annotations

from typing import Any

OPENED: list[Any] = []
