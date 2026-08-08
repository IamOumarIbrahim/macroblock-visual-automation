from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from macroblock.overlay import CursorOverlay


def test_overlay_is_nonfocusable_transparent_and_tracks_global_provider() -> None:
    app = QApplication.instance() or QApplication([])
    position = [320, 240]
    overlay = CursorOverlay(cursor_provider=lambda: tuple(position))

    assert overlay.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert overlay.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    assert overlay.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    assert overlay.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert overlay.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    assert overlay.windowFlags() & Qt.WindowType.WindowTransparentForInput

    overlay.show_overlay()
    app.processEvents()
    assert overlay.timer.isActive()
    assert overlay.global_cursor.x() == 320
    assert overlay.global_cursor.y() == 240
    position[:] = [500, 350]
    overlay.poll_cursor()
    assert overlay.global_cursor.x() == 500
    assert overlay.global_cursor.y() == 350
    overlay.hide_overlay()
    assert not overlay.isVisible()
    assert not overlay.timer.isActive()

