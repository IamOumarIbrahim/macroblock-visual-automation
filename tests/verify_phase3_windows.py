"""Explicit live-input verification; run directly, never by normal pytest."""

from __future__ import annotations

import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton

from macroblock.blocks import BlockInstance, ScriptGraph, create_default_registry
from macroblock.engine import ExecutionController, InputController
from macroblock.main import enable_per_monitor_v2_awareness


def wait_for(controller: ExecutionController, app: QApplication, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while controller.is_running and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    app.processEvents()
    assert not controller.is_running, "execution did not finish before timeout"


def main() -> int:
    enable_per_monitor_v2_awareness()
    app = QApplication.instance() or QApplication([])
    registry = create_default_registry()
    win32_input = InputController()
    original_cursor = win32_input.cursor_position()
    target = QPushButton("Macroblock SendInput target")
    target.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    # Cover the primary screen briefly so concurrent physical mouse movement
    # cannot redirect the verification click into an unrelated application.
    target.setGeometry(app.primaryScreen().geometry())
    target.show()
    target.raise_()
    target.activateWindow()
    app.processEvents()
    clicked = []
    target.clicked.connect(lambda: clicked.append(True))

    center = target.mapToGlobal(target.rect().center())
    move = BlockInstance.create(
        registry,
        "mouse.move_to",
        instance_id="move",
        params={"x": center.x(), "y": center.y()},
    )
    wait = BlockInstance.create(
        registry,
        "timing.wait",
        instance_id="wait",
        params={"seconds": 0.2},
    )
    click = BlockInstance.create(
        registry,
        "mouse.click",
        instance_id="click",
        params={"button": "left", "count": 1},
    )
    move.next_id = wait.instance_id
    wait.next_id = click.instance_id
    click_graph = ScriptGraph.from_blocks("Live Click", [move, wait, click])
    click_controller = ExecutionController(registry, input_controller=win32_input)

    try:
        click_controller.start(click_graph)
        assert click_controller.abort_monitor_ready
        wait_for(click_controller, app, 3)
        assert click_controller.last_result is not None
        assert click_controller.last_result.status == "completed"
        assert clicked, "SendInput click did not reach the known Qt target"
        target.close()
        app.processEvents()

        loop = BlockInstance.create(
            registry, "control.repeat_until_stopped", instance_id="loop"
        )
        loop_wait = BlockInstance.create(
            registry,
            "timing.wait",
            instance_id="loop_wait",
            params={"seconds": 0.1},
        )
        loop.child_id = loop_wait.instance_id
        abort_graph = ScriptGraph.from_blocks("Abort", [loop, loop_wait])
        abort_controller = ExecutionController(registry, input_controller=win32_input)
        abort_controller.start(abort_graph)
        assert abort_controller.abort_monitor_ready
        win32_input.key_down("ESC")
        time.sleep(0.65)
        win32_input.key_up("ESC")
        wait_for(abort_controller, app, 3)
        assert abort_controller.last_result is not None
        assert abort_controller.last_result.status == "aborted"
        print(
            "PASS: background move/wait/click reached target; global 0.5s Esc hold "
            "aborted an infinite script."
        )
    finally:
        try:
            win32_input.key_up("ESC")
            win32_input.move_to(*original_cursor)
        finally:
            target.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
