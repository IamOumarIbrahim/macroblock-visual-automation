"""Macroblock's main application window."""

from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QMessageBox, QToolBar, QWidget

from macroblock.blocks import BlockRegistry, create_default_registry
from macroblock.engine import ExecutionController
from macroblock.ui.canvas import CanvasView
from macroblock.ui.palette import PalettePanel


class MainWindow(QMainWindow):
    def __init__(self, registry: BlockRegistry | None = None) -> None:
        super().__init__()
        self.registry = registry or create_default_registry()
        self.setWindowTitle("Macroblock")
        self.resize(1180, 760)
        self.setMinimumSize(850, 560)

        self.toolbar = QToolBar("Main")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)
        self.run_action = QAction("Run Script", self)
        self.run_action.setToolTip("Run in the background (hold Esc for 0.5 seconds to abort)")
        self.stop_action = QAction("Stop", self)
        self.stop_action.setEnabled(False)
        self.toolbar.addAction(self.run_action)
        self.toolbar.addAction(self.stop_action)

        host = QWidget()
        layout = QHBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.palette = PalettePanel(self.registry)
        self.canvas = CanvasView(self.registry)
        layout.addWidget(self.palette)
        layout.addWidget(self.canvas, 1)
        self.setCentralWidget(host)

        self.canvas.canvas_scene.warningChanged.connect(self._show_warning)
        self.execution = ExecutionController(self.registry, parent=self)
        self.execution.started.connect(self._execution_started)
        self.execution.finished.connect(self._execution_finished)
        self.execution.failed.connect(self._execution_failed)
        self.run_action.triggered.connect(self.run_script)
        self.stop_action.triggered.connect(self.execution.abort)
        self.statusBar().showMessage("Drag blocks from the palette onto the canvas.")

    @property
    def graph(self):
        return self.canvas.canvas_scene.graph

    def _show_warning(self, warning: str) -> None:
        self.statusBar().showMessage(
            warning or "Drag blocks from the palette onto the canvas."
        )

    def run_script(self) -> None:
        if not self.graph.blocks:
            self.statusBar().showMessage("Add at least one block before running.")
            return
        try:
            self.execution.start(self.graph)
        except Exception as error:
            QMessageBox.critical(self, "Cannot run script", str(error))

    def _execution_started(self) -> None:
        self.run_action.setEnabled(False)
        self.stop_action.setEnabled(True)
        self.statusBar().showMessage("Running — hold Esc for 0.5 seconds to abort.")

    def _execution_finished(self, result) -> None:
        self.run_action.setEnabled(True)
        self.stop_action.setEnabled(False)
        self.statusBar().showMessage(
            f"Script {result.status} after {result.executed_blocks} block(s)."
        )

    def _execution_failed(self, message: str) -> None:
        self.run_action.setEnabled(True)
        self.stop_action.setEnabled(False)
        QMessageBox.critical(self, "Script failed", message)

    def closeEvent(self, event) -> None:
        self.execution.shutdown()
        super().closeEvent(event)

