"""Topmost, transparent, click-through global cursor crosshair."""

from __future__ import annotations

import ctypes
import sys
from collections.abc import Callable
from ctypes import wintypes

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget

WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
GWL_EXSTYLE = -20
GWL_STYLE = -16
WS_CAPTION = 0x00C00000
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


def global_cursor_position() -> tuple[int, int]:
    point = wintypes.POINT()
    if not ctypes.windll.user32.GetCursorPos(ctypes.byref(point)):
        raise ctypes.WinError(ctypes.get_last_error())
    return point.x, point.y


class CursorOverlay(QWidget):
    """One virtual-desktop window that never activates or consumes input."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        cursor_provider: Callable[[], tuple[int, int]] = global_cursor_position,
    ) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput,
        )
        self.setWindowTitle("Macroblock Cursor Overlay")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._cursor_provider = cursor_provider
        self._global_cursor = QPoint()
        self._physical_origin = QPoint()
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.poll_cursor)

    @property
    def global_cursor(self) -> QPoint:
        return QPoint(self._global_cursor)

    @staticmethod
    def virtual_desktop_geometry() -> QRect:
        screens = QGuiApplication.screens()
        if not screens:
            return QRect()
        geometry = QRect(screens[0].geometry())
        for screen in screens[1:]:
            geometry = geometry.united(screen.geometry())
        return geometry

    def show_overlay(self) -> None:
        geometry = self.virtual_desktop_geometry()
        self._physical_origin = geometry.topLeft()
        self.setGeometry(geometry)
        self.poll_cursor()
        self.show()
        self._apply_win32_styles()
        self.timer.start()

    def hide_overlay(self) -> None:
        self.timer.stop()
        self.hide()

    def poll_cursor(self) -> None:
        x, y = self._cursor_provider()
        point = QPoint(x, y)
        if point != self._global_cursor:
            self._global_cursor = point
            self.update()

    def _apply_win32_styles(self) -> None:
        if sys.platform != "win32" or QApplication.platformName() != "windows":
            return
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        get_style = user32.GetWindowLongPtrW
        set_style = user32.SetWindowLongPtrW
        get_style.argtypes = (wintypes.HWND, ctypes.c_int)
        get_style.restype = ctypes.c_ssize_t
        set_style.argtypes = (wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t)
        set_style.restype = ctypes.c_ssize_t
        hwnd = wintypes.HWND(int(self.winId()))
        style = get_style(hwnd, GWL_EXSTYLE)
        style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        ctypes.set_last_error(0)
        previous = set_style(hwnd, GWL_EXSTYLE, style)
        if previous == 0 and ctypes.get_last_error():
            raise ctypes.WinError(ctypes.get_last_error())
        left, top, width, height = (
            user32.GetSystemMetrics(metric)
            for metric in (
                SM_XVIRTUALSCREEN,
                SM_YVIRTUALSCREEN,
                SM_CXVIRTUALSCREEN,
                SM_CYVIRTUALSCREEN,
            )
        )
        self._physical_origin = QPoint(left, top)
        if not user32.SetWindowPos(
            hwnd,
            wintypes.HWND(HWND_TOPMOST),
            left,
            top,
            width,
            height,
            SWP_NOACTIVATE | SWP_SHOWWINDOW,
        ):
            raise ctypes.WinError(ctypes.get_last_error())

    def paintEvent(self, _event) -> None:
        # GetCursorPos and the native virtual-screen rectangle are physical
        # pixels. QPainter coordinates are device-independent, so divide by
        # this window's DPR to keep the crosshair on the same physical pixel.
        dpr = self.devicePixelRatioF() or 1.0
        local = QPoint(
            round((self._global_cursor.x() - self._physical_origin.x()) / dpr),
            round((self._global_cursor.y() - self._physical_origin.y()) / dpr),
        )
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(239, 68, 68, 220), 2))
        painter.drawLine(0, local.y(), self.width(), local.y())
        painter.drawLine(local.x(), 0, local.x(), self.height())

        label = f"X: {self._global_cursor.x()}, Y: {self._global_cursor.y()}"
        font = QFont("Segoe UI", 10)
        font.setBold(True)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        label_size = metrics.size(Qt.TextFlag.TextSingleLine, label)
        label_rect = QRect(
            local.x() + 14,
            local.y() + 14,
            label_size.width() + 18,
            label_size.height() + 10,
        )
        if label_rect.right() > self.width() - 6:
            label_rect.moveRight(local.x() - 14)
        if label_rect.bottom() > self.height() - 6:
            label_rect.moveBottom(local.y() - 14)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(17, 24, 39, 220))
        painter.drawRoundedRect(label_rect, 6, 6)
        painter.setPen(QColor("white"))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label)

    def closeEvent(self, event) -> None:
        self.timer.stop()
        super().closeEvent(event)
