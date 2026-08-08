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


def test_repeat_cavity_accepts_and_grows_with_child_blocks() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    scene = window.canvas.canvas_scene
    repeat = scene.add_block("control.repeat", QPointF(100, 80))
    empty_height = repeat.editor.height()
    first = scene.add_block("mouse.click", QPointF(500, 80))
    second = scene.add_block("timing.wait", QPointF(500, 180))

    scene.connect_blocks(repeat.block.instance_id, first.block.instance_id, as_child=True)
    one_child_height = repeat.editor.height()
    scene.connect_blocks(first.block.instance_id, second.block.instance_id)
    app.processEvents()

    assert repeat.block.child_id == first.block.instance_id
    assert first.block.next_id == second.block.instance_id
    assert first.pos().x() == repeat.pos().x() + scene.CONTAINER_INDENT
    assert first.pos().y() == repeat.pos().y() + repeat.editor.container_child_y
    assert one_child_height > empty_height
    assert repeat.editor.height() > one_child_height
    assert repeat.boundingRect().height() == repeat.editor.height()
    assert repeat.boundingRect().width() == repeat.editor.width()
    assert second.pos().y() < (
        repeat.pos().y() + repeat.editor.container_footer_top
    )
    window.close()


def test_nested_repeat_blocks_resize_recursively() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    scene = window.canvas.canvas_scene
    outer = scene.add_block("control.repeat", QPointF(90, 70))
    inner = scene.add_block("control.repeat", QPointF(500, 70))
    action = scene.add_block("keyboard.press", QPointF(850, 70))

    scene.connect_blocks(inner.block.instance_id, action.block.instance_id, as_child=True)
    scene.connect_blocks(outer.block.instance_id, inner.block.instance_id, as_child=True)
    app.processEvents()

    assert outer.block.child_id == inner.block.instance_id
    assert inner.block.child_id == action.block.instance_id
    assert inner.pos().x() == outer.pos().x() + scene.CONTAINER_INDENT
    assert action.pos().x() == inner.pos().x() + scene.CONTAINER_INDENT
    assert outer.editor.height() > inner.editor.height()
    assert outer.editor.width() > inner.editor.width()
    assert outer.boundingRect().size() == outer.editor.size()
    assert inner.boundingRect().size() == inner.editor.size()
    window.close()


def test_drop_position_inside_loop_uses_child_connector() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    scene = window.canvas.canvas_scene
    repeat = scene.add_block("control.repeat", QPointF(120, 100))
    candidate = scene.add_block("mouse.move_to", QPointF(700, 100))
    inside = repeat.pos() + QPointF(
        scene.CONTAINER_INDENT,
        repeat.editor.container_child_y + 8,
    )
    candidate.setPos(inside)

    match = scene.find_snap_target_for_position(
        candidate.pos(), exclude_id=candidate.block.instance_id
    )

    assert match is not None
    assert match.inside is True
    assert match.kind == "child"
    assert scene.snap_item(candidate) is True
    assert repeat.block.child_id == candidate.block.instance_id
    window.close()


def test_occupied_connector_inserts_without_orphaning_existing_chain() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    scene = window.canvas.canvas_scene
    first = scene.add_block("mouse.click", QPointF(80, 80))
    existing = scene.add_block("timing.wait", QPointF(80, 300))
    inserted = scene.add_block("keyboard.press", QPointF(500, 80))
    scene.connect_blocks(first.block.instance_id, existing.block.instance_id)

    scene.connect_blocks(first.block.instance_id, inserted.block.instance_id)

    assert first.block.next_id == inserted.block.instance_id
    assert inserted.block.next_id == existing.block.instance_id
    assert scene.incoming_reference(existing.block.instance_id) == (
        inserted.block.instance_id,
        "next",
    )

    repeat = scene.add_block("control.repeat", QPointF(800, 80))
    old_child = scene.add_block("mouse.click", QPointF(800, 300))
    new_child = scene.add_block("keyboard.press", QPointF(1100, 80))
    scene.connect_blocks(repeat.block.instance_id, old_child.block.instance_id, as_child=True)
    scene.connect_blocks(repeat.block.instance_id, new_child.block.instance_id, as_child=True)
    assert repeat.block.child_id == new_child.block.instance_id
    assert new_child.block.next_id == old_child.block.instance_id
    window.close()


def test_delete_repairs_sequence_and_preserves_container_children() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    scene = window.canvas.canvas_scene
    first = scene.add_block("mouse.click", QPointF(80, 80))
    repeat = scene.add_block("control.repeat", QPointF(80, 200))
    after = scene.add_block("timing.wait", QPointF(80, 500))
    child = scene.add_block("keyboard.press", QPointF(500, 200))
    scene.connect_blocks(first.block.instance_id, repeat.block.instance_id)
    scene.connect_blocks(repeat.block.instance_id, after.block.instance_id)
    scene.connect_blocks(repeat.block.instance_id, child.block.instance_id, as_child=True)

    scene.delete_block(repeat.block.instance_id)

    assert first.block.next_id == after.block.instance_id
    assert scene.incoming_reference(child.block.instance_id) is None
    assert child.block.instance_id in scene.block_items
    assert repeat.block.instance_id not in scene.block_items
    window.close()


def test_moving_a_connected_head_moves_its_entire_stack() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    scene = window.canvas.canvas_scene
    first = scene.add_block("control.repeat", QPointF(100, 100))
    child = scene.add_block("mouse.click", QPointF(500, 100))
    after = scene.add_block("timing.wait", QPointF(500, 300))
    scene.connect_blocks(first.block.instance_id, child.block.instance_id, as_child=True)
    scene.connect_blocks(first.block.instance_id, after.block.instance_id)
    starts = scene.connected_positions(first.block.instance_id)
    delta = QPointF(75, 48)

    first.setPos(starts[first.block.instance_id] + delta)
    scene.move_connected_items(first.block.instance_id, starts, delta)

    assert child.pos() == starts[child.block.instance_id] + delta
    assert after.pos() == starts[after.block.instance_id] + delta
    window.close()
