"""Inline block parameter editors shared by the palette and canvas."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from macroblock.blocks import BlockDefinition, BlockInstance, ParameterDefinition, ParameterType


def _text_color(background: str) -> str:
    color = QColor(background)
    luminance = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
    return "#111827" if luminance > 155 else "#FFFFFF"


class BlockEditorWidget(QFrame):
    """A colored block whose parameter values are edited directly in its face."""

    parameterChanged = Signal(str, object)

    def __init__(
        self,
        definition: BlockDefinition,
        block: BlockInstance,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.definition = definition
        self.block = block
        self.editors: dict[str, QWidget] = {}
        text_color = _text_color(definition.color)
        self.setObjectName("blockEditor")
        self.setStyleSheet(
            "QFrame#blockEditor {"
            f"background: {definition.color}; border: 2px solid rgba(0,0,0,45);"
            "border-radius: 10px;}"
            f"QLabel {{ color: {text_color}; font-weight: 600; background: transparent; }}"
            "QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {"
            "background: rgba(255,255,255,235); color: #111827; border: 1px solid rgba(0,0,0,50);"
            "border-radius: 7px; padding: 2px 5px; min-height: 22px;}"
        )
        self.setMinimumWidth(238)

        root = QVBoxLayout(self)
        root.setContentsMargins(11, 8, 11, 8)
        root.setSpacing(5)
        title = QLabel(definition.display_label)
        title.setObjectName("blockTitle")
        root.addWidget(title)

        if not definition.parameters:
            hint = QLabel("End" if definition.is_terminal else "No parameters")
            hint.setStyleSheet(f"color: {text_color}; font-weight: 400;")
            root.addWidget(hint)

        for parameter in definition.parameters:
            row = QHBoxLayout()
            row.setSpacing(6)
            label = QLabel(parameter.label)
            row.addWidget(label)
            editor, read = self._create_editor(parameter, block.params[parameter.id])
            self.editors[parameter.id] = editor
            row.addWidget(editor, 1)

            def update(
                param: ParameterDefinition = parameter,
                reader: Callable[[], Any] = read,
            ) -> None:
                value = reader()
                param.validate(value)
                self.block.params[param.id] = value
                self.parameterChanged.emit(param.id, value)

            if isinstance(editor, QComboBox):
                editor.currentTextChanged.connect(lambda _text, callback=update: callback())
            elif isinstance(editor, (QSpinBox, QDoubleSpinBox)):
                editor.valueChanged.connect(lambda _value, callback=update: callback())
            else:
                editor.editingFinished.connect(update)
            root.addLayout(row)
        self.adjustSize()

    def _create_editor(
        self, parameter: ParameterDefinition, value: Any
    ) -> tuple[QWidget, Callable[[], Any]]:
        if parameter.type is ParameterType.INTEGER:
            editor = QSpinBox()
            editor.setRange(
                int(parameter.minimum) if parameter.minimum is not None else -1_000_000,
                1_000_000,
            )
            editor.setValue(value)
            return editor, editor.value
        if parameter.type is ParameterType.NUMBER:
            editor = QDoubleSpinBox()
            editor.setDecimals(3)
            editor.setRange(
                parameter.minimum if parameter.minimum is not None else -1_000_000,
                1_000_000,
            )
            editor.setValue(value)
            return editor, editor.value
        if parameter.type is ParameterType.CHOICE:
            editor = QComboBox()
            editor.addItems(parameter.choices)
            editor.setCurrentText(value)
            return editor, editor.currentText

        editor = QLineEdit()
        if parameter.type is ParameterType.KEY_LIST:
            editor.setText(" + ".join(value))
            return editor, lambda: [part.strip().upper() for part in editor.text().split("+") if part.strip()]
        if parameter.type is ParameterType.VALUE:
            editor.setText(json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value)

            def read_value() -> Any:
                try:
                    parsed = json.loads(editor.text())
                except json.JSONDecodeError:
                    return editor.text()
                return parsed if parsed is None or isinstance(parsed, (str, int, float, bool)) else editor.text()

            return editor, read_value
        editor.setText(str(value))
        return editor, editor.text


class PaletteBlockWidget(QFrame):
    """Compact, draggable representation of a registered block type."""

    MIME_TYPE = "application/x-macroblock-type"

    def __init__(self, definition: BlockDefinition, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.definition = definition
        self._press_position = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setStyleSheet(
            f"background: {definition.color}; border-radius: 9px; padding: 5px;"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        label = QLabel(definition.display_label)
        label.setStyleSheet(
            f"color: {_text_color(definition.color)}; font-weight: 650; background: transparent;"
        )
        layout.addWidget(label)

    def create_mime_data(self):
        from PySide6.QtCore import QMimeData

        mime = QMimeData()
        mime.setData(self.MIME_TYPE, self.definition.id.encode("utf-8"))
        return mime

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_position = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if not (event.buttons() & Qt.MouseButton.LeftButton) or self._press_position is None:
            return super().mouseMoveEvent(event)
        if (event.position().toPoint() - self._press_position).manhattanLength() < 8:
            return
        from PySide6.QtGui import QDrag

        drag = QDrag(self)
        drag.setMimeData(self.create_mime_data())
        drag.exec(Qt.DropAction.CopyAction)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseReleaseEvent(self, event) -> None:
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)

