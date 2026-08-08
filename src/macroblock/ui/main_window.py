"""Macroblock's main application window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMessageBox,
    QToolBar,
    QToolButton,
    QWidget,
)

from macroblock.blocks import BlockRegistry, create_default_registry
from macroblock.engine import ExecutionController
from macroblock.overlay import CursorOverlay
from macroblock.persistence import PersistenceError, load_script, save_script
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
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(self.toolbar)
        self.selected_block_type = self.registry.blocks[0].id
        self.block_actions: dict[str, QAction] = {}
        self.block_action_group = QActionGroup(self)
        self.block_action_group.setExclusive(True)
        self.add_block_button = QToolButton()
        self.add_block_button.setObjectName("addBlockButton")
        self.add_block_button.setText("ADD BLOCK")
        self.add_block_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.add_block_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_block_button.setStyleSheet(
            "QToolButton#addBlockButton { background: #2563EB; color: white;"
            " border: none; border-radius: 9px; padding: 7px 15px;"
            " font-weight: 800; letter-spacing: 0.5px; }"
            "QToolButton#addBlockButton:hover { background: #1D4ED8; }"
            "QToolButton#addBlockButton:pressed { background: #1E40AF; }"
            "QToolButton#addBlockButton::menu-button { width: 22px; border-left:"
            " 1px solid rgba(255,255,255,80); border-radius: 0 9px 9px 0; }"
        )
        add_menu = QMenu(self.add_block_button)
        for category in self.registry.categories:
            category_menu = add_menu.addMenu(category.label)
            category_menu.setStyleSheet(
                f"QMenu::item:selected {{ background: {category.color}; color: white; }}"
            )
            for definition in self.registry.blocks_for_category(category.id):
                action = category_menu.addAction(definition.display_label)
                action.setCheckable(True)
                action.setData(definition.id)
                action.triggered.connect(
                    lambda _checked=False, type_id=definition.id: self._choose_and_add_block(
                        type_id
                    )
                )
                self.block_action_group.addAction(action)
                self.block_actions[definition.id] = action
        self.add_block_button.setMenu(add_menu)
        self.add_block_button.clicked.connect(self.add_selected_block)
        self.toolbar.addWidget(self.add_block_button)
        self.toolbar.addSeparator()
        self.load_action = QAction("Load", self)
        self.save_action = QAction("Save", self)
        self.toolbar.addAction(self.load_action)
        self.toolbar.addAction(self.save_action)
        self.toolbar.addSeparator()
        self.run_action = QAction("Run Script", self)
        self.run_action.setToolTip("Run in the background (hold Esc for 0.5 seconds to abort)")
        self.stop_action = QAction("Stop", self)
        self.stop_action.setEnabled(False)
        self.toolbar.addAction(self.run_action)
        self.toolbar.addAction(self.stop_action)
        self.toolbar.addSeparator()
        self.cursor_action = QAction("Show Cursor", self)
        self.cursor_action.setCheckable(True)
        self.toolbar.addAction(self.cursor_action)
        self.cursor_overlay: CursorOverlay | None = None
        self.current_file: Path | None = None

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
        self.canvas.interactionMessage.connect(self.statusBar().showMessage)
        self.palette.blockSelected.connect(self.select_block_type)
        self.palette.blockDragStarted.connect(self._palette_drag_started)
        self.palette.blockDragFinished.connect(self._palette_drag_finished)
        self.execution = ExecutionController(self.registry, parent=self)
        self.execution.started.connect(self._execution_started)
        self.execution.finished.connect(self._execution_finished)
        self.execution.failed.connect(self._execution_failed)
        self.run_action.triggered.connect(self.run_script)
        self.stop_action.triggered.connect(self.execution.abort)
        self.cursor_action.toggled.connect(self._toggle_cursor_overlay)
        self.load_action.triggered.connect(self.choose_load_script)
        self.save_action.triggered.connect(self.choose_save_script)
        self.select_block_type(self.palette.selected_type_id or self.selected_block_type)
        self.statusBar().showMessage(
            "Choose a block and drag it in, or use ADD BLOCK for an automatic sequence."
        )

    @property
    def graph(self):
        return self.canvas.canvas_scene.graph

    def _show_warning(self, warning: str) -> None:
        if warning:
            self.statusBar().showMessage(warning)

    def select_block_type(self, type_id: str) -> None:
        self.selected_block_type = type_id
        definition = self.registry.block(type_id)
        action = self.block_actions.get(type_id)
        if action:
            action.setChecked(True)
        self.add_block_button.setToolTip(
            f"Add {definition.display_label}; click the arrow to choose another block."
        )

    def _choose_and_add_block(self, type_id: str) -> None:
        self.select_block_type(type_id)
        self.add_selected_block()

    def add_selected_block(self) -> None:
        self.canvas.add_block_from_toolbar(self.selected_block_type)

    def _palette_drag_started(self, type_id: str) -> None:
        self.select_block_type(type_id)
        label = self.registry.block(type_id).display_label
        self.statusBar().showMessage(
            f"Dragging {label} — move over the canvas; green feedback means snap-ready."
        )

    def _palette_drag_finished(self, _type_id: str, dropped: bool) -> None:
        if not dropped:
            self.statusBar().showMessage(
                "Drag cancelled — use ADD BLOCK if you prefer automatic placement."
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

    def _toggle_cursor_overlay(self, shown: bool) -> None:
        if shown:
            if self.cursor_overlay is None:
                self.cursor_overlay = CursorOverlay()
            self.cursor_overlay.show_overlay()
            self.cursor_action.setText("Hide Cursor")
            self.statusBar().showMessage("Cursor overlay shown — it will not intercept clicks.")
        else:
            if self.cursor_overlay is not None:
                self.cursor_overlay.hide_overlay()
            self.cursor_action.setText("Show Cursor")
            self.statusBar().showMessage("Cursor overlay hidden.")

    def choose_save_script(self) -> None:
        suggested = str(self.current_file) if self.current_file else f"{self.graph.name}.mbk"
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Macroblock Script",
            suggested,
            "Macroblock Scripts (*.mbk);;JSON Files (*.json);;All Files (*)",
        )
        if path:
            if not Path(path).suffix:
                path += ".mbk"
            self.save_script_path(path)

    def choose_load_script(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Load Macroblock Script",
            str(self.current_file.parent) if self.current_file else "",
            "Macroblock Scripts (*.mbk);;JSON Files (*.json);;All Files (*)",
        )
        if path:
            self.load_script_path(path)

    def save_script_path(self, path: str | Path) -> bool:
        try:
            saved = save_script(path, self.graph, self.registry)
        except PersistenceError as error:
            QMessageBox.critical(self, "Unable to save script", str(error))
            return False
        self.current_file = saved
        self.setWindowTitle(f"Macroblock — {self.graph.name}")
        self.statusBar().showMessage(f"Saved {saved.name}.")
        return True

    def load_script_path(self, path: str | Path) -> bool:
        try:
            graph = load_script(path, self.registry)
        except PersistenceError as error:
            QMessageBox.critical(self, "Unable to load script", str(error))
            return False
        self.canvas.canvas_scene.load_graph(graph)
        self.current_file = Path(path)
        self.setWindowTitle(f"Macroblock — {graph.name}")
        self.statusBar().showMessage(f"Loaded {self.current_file.name}.")
        return True

    def closeEvent(self, event) -> None:
        if self.cursor_overlay is not None:
            self.cursor_overlay.close()
        self.execution.shutdown()
        super().closeEvent(event)
