"""Application entry point."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from macroblock.ui.main_window import MainWindow


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


def app_icon_path() -> Path:
    if bundle_root := getattr(sys, "_MEIPASS", None):
        return Path(bundle_root) / "assets" / "icons" / "macroblock.ico"
    return Path(__file__).resolve().parents[2] / "assets" / "icons" / "macroblock.ico"


def is_administrator() -> bool:
    """Return whether the current Windows process has an elevated token."""

    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def ensure_administrator() -> bool:
    """Relaunch through UAC when source entry points are not elevated."""

    if sys.platform != "win32":
        raise RuntimeError("Macroblock requires Windows administrator privileges.")
    if is_administrator():
        return True
    if getattr(sys, "frozen", False):
        executable = sys.executable
        arguments = subprocess.list2cmdline(sys.argv[1:])
    else:
        executable = sys.executable
        arguments = subprocess.list2cmdline(
            [str(Path(__file__).resolve()), *sys.argv[1:]]
        )
    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        executable,
        arguments,
        os.getcwd(),
        1,
    )
    if result <= 32:
        raise PermissionError(
            "Macroblock requires administrator access; the elevation request was declined."
        )
    return False


def main() -> int:
    if not ensure_administrator():
        return 0
    enable_per_monitor_v2_awareness()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Macroblock")
    app.setOrganizationName("Macroblock")
    icon_path = app_icon_path()
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    window.show()

    smoke_ms = os.environ.get("MACROBLOCK_SMOKE_TEST_MS")
    if smoke_ms:
        QTimer.singleShot(int(smoke_ms), window.close)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
