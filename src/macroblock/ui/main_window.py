"""Macroblock's main application window."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QToolBar, QWidget

from macroblock.blocks import BlockRegistry, create_default_registry
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
        self.statusBar().showMessage("Drag blocks from the palette onto the canvas.")

    @property
    def graph(self):
        return self.canvas.canvas_scene.graph

    def _show_warning(self, warning: str) -> None:
        self.statusBar().showMessage(
            warning or "Drag blocks from the palette onto the canvas."
        )

