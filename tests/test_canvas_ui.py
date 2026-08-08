from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QApplication, QSpinBox

from macroblock.ui.main_window import MainWindow


def _drop_palette_block(window: MainWindow, category_id: str, position: QPointF):
    __tracebackhide__ = True
    window.palette.show_category(category_id)
    QApplication.processEvents()
    palette_block = window.palette.block_widgets[0]
    mime_data = palette_block.create_mime_data()
    event = QDropEvent(
        position,
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.canvas.dropEvent(event)
    return window.graph.blocks[-1]


def test_palette_drop_connect_edit_disconnect_and_delete() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    app.processEvents()

    dropped = []
    for index, category_id in enumerate(
        ("mouse", "keyboard", "timing", "control", "variables", "events")
    ):
        dropped.append(
            _drop_palette_block(window, category_id, QPointF(80 + index * 35, 80 + index * 85))
        )

    scene = window.canvas.canvas_scene
    scene.connect_blocks(dropped[0].instance_id, dropped[1].instance_id)
    scene.connect_blocks(dropped[1].instance_id, dropped[2].instance_id)
    assert dropped[0].next_id == dropped[1].instance_id
    assert dropped[1].next_id == dropped[2].instance_id

    mouse_item = scene.block_items[dropped[0].instance_id]
    x_editor = mouse_item.editor.editors["x"]
    assert isinstance(x_editor, QSpinBox)
    x_editor.setValue(777)
    app.processEvents()
    assert dropped[0].params["x"] == 777

    scene.disconnect_incoming(dropped[2].instance_id)
    assert dropped[1].next_id is None
    count_before = len(window.graph.blocks)
    scene.delete_block(dropped[2].instance_id)
    assert len(window.graph.blocks) == count_before - 1
    assert dropped[2].instance_id not in scene.block_items

    window.close()


def test_duplicate_event_hotkeys_produce_warning() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    scene = window.canvas.canvas_scene
    first = scene.add_block("events.hotkey", QPointF(10, 10))
    second = scene.add_block("events.hotkey", QPointF(10, 100))
    app.processEvents()
    assert first.block.params["hotkey"] == second.block.params["hotkey"]
    assert "duplicate event hotkey" in scene.hotkey_warning().lower()
    window.close()
