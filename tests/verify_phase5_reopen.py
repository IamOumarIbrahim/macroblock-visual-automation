"""Explicit save, close, reopen, and exact-load verification."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from macroblock.main import enable_per_monitor_v2_awareness
from macroblock.ui.main_window import MainWindow


def main() -> int:
    enable_per_monitor_v2_awareness()
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="macroblock-phase5-") as folder:
        path = Path(folder) / "reopen.mbk"
        first = MainWindow()
        first.show()
        scene = first.canvas.canvas_scene
        move = scene.add_block("mouse.move_to", QPointF(40, 50))
        click = scene.add_block("mouse.click", QPointF(40, 150))
        move.block.params.update({"x": 500, "y": 300})
        scene.connect_blocks(move.block.instance_id, click.block.instance_id)
        first.graph.name = "Reopen Verification"
        expected = first.graph.to_dict()
        assert first.save_script_path(path)
        first.close()
        app.processEvents()

        reopened = MainWindow()
        reopened.show()
        assert reopened.load_script_path(path)
        app.processEvents()
        assert reopened.graph.to_dict() == expected
        assert len(reopened.canvas.canvas_scene.block_items) == 2
        reopened.close()
    print("PASS: saved .mbk, closed the app window, reopened, and loaded an exact graph match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

