"""Application entry point."""

from __future__ import annotations

import ctypes
import os
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMainWindow


def enable_per_monitor_v2_awareness() -> None:
    """Request physical-pixel coordinates before Qt initializes."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Macroblock")
        self.resize(1100, 720)


def main() -> int:
    enable_per_monitor_v2_awareness()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Macroblock")
    window = MainWindow()
    window.show()

    smoke_ms = os.environ.get("MACROBLOCK_SMOKE_TEST_MS")
    if smoke_ms:
        QTimer.singleShot(int(smoke_ms), window.close)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

