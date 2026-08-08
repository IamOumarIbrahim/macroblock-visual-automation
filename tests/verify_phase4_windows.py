"""Explicit live verification of Win32 overlay styles and Alt+Tab survival."""

from __future__ import annotations

import ctypes
import os
import time
from ctypes import wintypes

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint

from macroblock.engine import InputController
from macroblock.main import enable_per_monitor_v2_awareness
from macroblock.overlay.cursor_overlay import (
    GWL_EXSTYLE,
    GWL_STYLE,
    WS_CAPTION,
    WS_EX_LAYERED,
    WS_EX_NOACTIVATE,
    WS_EX_TOOLWINDOW,
    WS_EX_TOPMOST,
    WS_EX_TRANSPARENT,
)
from macroblock.ui.main_window import MainWindow


def pump(app: QApplication, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)


def main() -> int:
    enable_per_monitor_v2_awareness()
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    window.raise_()
    window.activateWindow()
    pump(app, 0.15)

    window.cursor_action.trigger()
    pump(app, 0.1)
    overlay = window.cursor_overlay
    assert overlay is not None and overlay.isVisible() and overlay.timer.isActive()
    assert window.cursor_action.text() == "Hide Cursor"

    user32 = ctypes.windll.user32
    hwnd = int(overlay.winId())
    ex_style = user32.GetWindowLongPtrW(wintypes.HWND(hwnd), GWL_EXSTYLE)
    required = (
        WS_EX_LAYERED
        | WS_EX_TRANSPARENT
        | WS_EX_NOACTIVATE
        | WS_EX_TOOLWINDOW
        | WS_EX_TOPMOST
    )
    assert ex_style & required == required, hex(ex_style)
    style = user32.GetWindowLongPtrW(wintypes.HWND(hwnd), GWL_STYLE)
    assert not style & WS_CAPTION, hex(style)
    assert user32.GetForegroundWindow() != hwnd

    samples = []
    provider = overlay._cursor_provider
    overlay._cursor_provider = lambda: samples.append(provider()) or samples[-1]
    pump(app, 0.08)
    assert len(samples) >= 2
    assert overlay.global_cursor == QPoint(*samples[-1])
    assert overlay.timer.isActive()

    main_hwnd = int(window.winId())
    foreground_before = user32.GetForegroundWindow()
    try:
        user32.SetForegroundWindow(wintypes.HWND(main_hwnd))
        pump(app, 0.08)
        InputController().key_combo(["ALT", "TAB"])
        pump(app, 0.25)
        foreground_after = user32.GetForegroundWindow()
        assert foreground_after != main_hwnd, "Alt+Tab did not leave Macroblock"
        _, foreground_pid = _window_process_id(foreground_after)
        assert foreground_pid != os.getpid(), "Alt+Tab did not reach another application"
        assert overlay.isVisible() and overlay.timer.isActive()
    finally:
        user32.SetForegroundWindow(wintypes.HWND(main_hwnd))
        pump(app, 0.08)

    window.cursor_action.trigger()
    pump(app, 0.05)
    assert not overlay.isVisible() and not overlay.timer.isActive()
    assert window.cursor_action.text() == "Show Cursor"
    window.close()
    print(
        "PASS: layered/no-activate/click-through overlay tracked globally, stayed "
        "visible after Alt+Tab, and Hide Cursor removed it."
    )
    return 0


def _window_process_id(hwnd: int) -> tuple[int, int]:
    pid = wintypes.DWORD()
    thread_id = ctypes.windll.user32.GetWindowThreadProcessId(
        wintypes.HWND(hwnd), ctypes.byref(pid)
    )
    return thread_id, pid.value


if __name__ == "__main__":
    raise SystemExit(main())
