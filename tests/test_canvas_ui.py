from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
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


def test_add_block_button_is_persistent_and_builds_a_sequence() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    app.processEvents()

    assert window.add_block_button.isVisible()
    assert window.add_block_button.text() == "ADD BLOCK"

    window.select_block_type("mouse.move_to")
    window.add_selected_block()
    first = window.graph.blocks[-1]
    assert first.next_id is None

    window.select_block_type("timing.wait")
    window.add_selected_block()
    second = window.graph.blocks[-1]
    assert first.next_id == second.instance_id

    window.block_actions["mouse.click"].trigger()
    third = window.graph.blocks[-1]
    assert second.next_id == third.instance_id
    assert window.canvas.canvas_scene.last_added_id == third.instance_id
    window.close()


def test_palette_drop_near_connector_snaps_automatically() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    app.processEvents()
    scene = window.canvas.canvas_scene
    target = scene.add_block("mouse.move_to", QPointF(180, 160))
    app.processEvents()

    window.palette.show_category("timing")
    palette_block = window.palette.block_widgets[0]
    hotspot = QPoint(12, 12)
    expected = QPointF(
        target.x(),
        target.y() + target.boundingRect().height() + scene.BLOCK_GAP,
    )
    drop_point = window.canvas.mapFromScene(expected) + hotspot
    mime_data = palette_block.create_mime_data(hotspot)
    enter_event = QDragEnterEvent(
        drop_point,
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.canvas.dragEnterEvent(enter_event)
    move_event = QDragMoveEvent(
        drop_point,
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.canvas.dragMoveEvent(move_event)
    assert enter_event.isAccepted()
    assert move_event.isAccepted()
    assert window.canvas._drag_active is True
    assert window.canvas._drag_will_snap is True
    assert scene.snap_preview_item is not None
    event = QDropEvent(
        QPointF(drop_point),
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    window.canvas.dropEvent(event)
    app.processEvents()
    dropped = window.graph.blocks[-1]

    assert target.block.next_id == dropped.instance_id
    assert scene.block_items[dropped.instance_id].pos() == expected
    assert scene.snap_preview_item is None
    window.close()


def test_close_block_drag_shows_snap_preview_before_connection() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    scene = window.canvas.canvas_scene
    target = scene.add_block("mouse.move_to", QPointF(40, 40))
    candidate = scene.add_block("keyboard.press", QPointF(40, 40))
    candidate.setPos(
        target.x() + 20,
        target.y() + target.boundingRect().height() + scene.BLOCK_GAP + 12,
    )

    scene.preview_snap_for_item(candidate)

    assert scene.snap_preview_item is not None
    assert scene._snap_target_id == target.block.instance_id
    assert scene.snap_item(candidate) is True
    assert target.block.next_id == candidate.block.instance_id
    window.close()
