"""Category selector and scrollable palette."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from macroblock.blocks import BlockRegistry
from macroblock.ui.block_widgets import PaletteBlockWidget


class PalettePanel(QWidget):
    categoryChanged = Signal(str)

    def __init__(self, registry: BlockRegistry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.registry = registry
        self.category_buttons: dict[str, QPushButton] = {}
        self.block_widgets: list[PaletteBlockWidget] = []
        self.setFixedWidth(300)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 8, 10)
        heading = QLabel("Blocks")
        heading.setStyleSheet("font-size: 20px; font-weight: 700;")
        root.addWidget(heading)

        category_host = QWidget()
        category_layout = QGridLayout(category_host)
        category_layout.setContentsMargins(0, 0, 0, 4)
        category_layout.setSpacing(5)
        group = QButtonGroup(self)
        group.setExclusive(True)
        for index, category in enumerate(registry.categories):
            button = QPushButton(category.label)
            button.setCheckable(True)
            button.setStyleSheet(
                "QPushButton {"
                f"border: 2px solid {category.color}; border-radius: 8px; padding: 7px;"
                "background: white; color: #1F2937;}"
                f"QPushButton:checked {{ background: {category.color}; color: white; }}"
            )
            button.clicked.connect(
                lambda _checked=False, category_id=category.id: self.show_category(category_id)
            )
            group.addButton(button)
            self.category_buttons[category.id] = button
            category_layout.addWidget(button, index // 2, index % 2)
        root.addWidget(category_host)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.palette_host = QWidget()
        self.palette_layout = QVBoxLayout(self.palette_host)
        self.palette_layout.setContentsMargins(2, 4, 5, 4)
        self.palette_layout.setSpacing(7)
        self.palette_layout.addStretch(1)
        self.scroll.setWidget(self.palette_host)
        root.addWidget(self.scroll, 1)

        first = registry.categories[0]
        self.category_buttons[first.id].setChecked(True)
        self.show_category(first.id)

    def show_category(self, category_id: str) -> None:
        for widget in self.block_widgets:
            self.palette_layout.removeWidget(widget)
            widget.deleteLater()
        self.block_widgets.clear()
        for definition in self.registry.blocks_for_category(category_id):
            widget = PaletteBlockWidget(definition)
            self.palette_layout.insertWidget(self.palette_layout.count() - 1, widget)
            self.block_widgets.append(widget)
        self.category_buttons[category_id].setChecked(True)
        self.categoryChanged.emit(category_id)

