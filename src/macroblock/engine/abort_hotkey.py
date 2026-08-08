"""Focus-independent hold-Escape abort monitor."""

from __future__ import annotations

import ctypes
import sys
import threading
import time
from collections.abc import Callable

VK_ESCAPE = 0x1B


class AbortHotkeyMonitor:
    """Polls global key state so holding Escape aborts from any foreground app."""

    def __init__(
        self,
        abort_event: threading.Event,
        *,
        hold_seconds: float = 0.5,
        poll_seconds: float = 0.015,
        key_state: Callable[[], bool] | None = None,
    ) -> None:
        if sys.platform != "win32" and key_state is None:
            raise RuntimeError("The global abort hotkey requires Windows.")
        self.abort_event = abort_event
        self.hold_seconds = hold_seconds
        self.poll_seconds = poll_seconds
        self._key_state = key_state or self._escape_is_down
        self._stop_event = threading.Event()
        self.ready_event = threading.Event()
        self._thread: threading.Thread | None = None

    @staticmethod
    def _escape_is_down() -> bool:
        return bool(ctypes.windll.user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self.ready_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="macroblock-abort-hotkey",
            daemon=True,
        )
        self._thread.start()

    def _run(self) -> None:
        pressed_since: float | None = None
        self.ready_event.set()
        while not self._stop_event.wait(self.poll_seconds):
            if self._key_state():
                pressed_since = pressed_since or time.monotonic()
                if time.monotonic() - pressed_since >= self.hold_seconds:
                    self.abort_event.set()
                    return
            else:
                pressed_since = None

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=1)

    @property
    def is_ready(self) -> bool:
        return self.ready_event.is_set() and bool(self._thread and self._thread.is_alive())

