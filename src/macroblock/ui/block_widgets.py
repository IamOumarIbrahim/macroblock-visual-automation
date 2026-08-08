"""Inline block parameter editors shared by the palette and canvas."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QPainter, QPainterPath, QPen
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
    CONTAINER_FOOTER_HEIGHT = 42
    EMPTY_CONTAINER_BODY_HEIGHT = 62

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
        self._visual_state = "normal"
        self._base_color = QColor(definition.color)
        self._is_container = definition.is_container
        self._container_has_children = False
        self._container_body_height = self.EMPTY_CONTAINER_BODY_HEIGHT
        text_color = _text_color(definition.color)
        self.setObjectName("blockEditor")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(
            "QFrame#blockEditor { background: transparent; border: none; }"
            f"QLabel {{ color: {text_color}; font-weight: 600; background: transparent; }}"
            "QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {"
            "background: rgba(255,255,255,235); color: #111827; border: 1px solid rgba(0,0,0,50);"
            "border-radius: 7px; padding: 2px 5px; min-height: 22px;}"
        )
        self.setMinimumWidth(238)

        root = QVBoxLayout(self)
        root.setContentsMargins(13, 15, 13, 16)
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
        self._header_height = max(66, self.sizeHint().height())
        self._natural_width = max(238, self.sizeHint().width())
        if self._is_container:
            root.addStretch(1)
            self.set_container_layout(
                self.EMPTY_CONTAINER_BODY_HEIGHT,
                self._natural_width + 34,
                has_children=False,
            )

    @property
    def container_header_height(self) -> float:
        return float(self._header_height)

    @property
    def container_child_y(self) -> float:
        return float(self._header_height - 7)

    @property
    def container_footer_top(self) -> float:
        return float(self._header_height + self._container_body_height - 7)

    def container_body_rect(self) -> QRectF:
        """Return the visible cavity used as an inside drop target."""

        return QRectF(
            30,
            self.container_child_y,
            max(1, self.width() - 42),
            max(1, self._container_body_height),
        )

    def set_container_layout(
        self, body_height: float, width: float, *, has_children: bool
    ) -> None:
        if not self._is_container:
            return
        self._container_body_height = max(
            self.EMPTY_CONTAINER_BODY_HEIGHT if not has_children else 34,
            int(round(body_height)),
        )
        self._container_has_children = has_children
        target_width = max(self._natural_width + 34, int(round(width)))
        target_height = (
            self._header_height
            + self._container_body_height
            + self.CONTAINER_FOOTER_HEIGHT
            - 7
        )
        self.setFixedSize(target_width, target_height)
        self.updateGeometry()
        self.update()

    def set_visual_state(self, state: str) -> None:
        if state != self._visual_state:
            self._visual_state = state
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self._base_color)
        if self._visual_state == "snap":
            border = QColor("#22C55E")
            border_width = 4
            color = color.lighter(108)
        elif self._visual_state == "selected":
            border = QColor("#FFFFFF")
            border_width = 3
        elif self._visual_state == "hover":
            border = QColor(255, 255, 255, 185)
            border_width = 3
            color = color.lighter(105)
        else:
            border = QColor(15, 23, 42, 105)
            border_width = 2

        if self._is_container:
            header = QPainterPath()
            header.addRoundedRect(
                QRectF(2, 7, self.width() - 4, self._header_height - 5),
                15,
                15,
            )
            spine = QPainterPath()
            spine.addRect(
                QRectF(
                    2,
                    self._header_height - 2,
                    31,
                    self._container_body_height + 7,
                )
            )
            footer = QPainterPath()
            footer.addRoundedRect(
                QRectF(
                    2,
                    self.container_footer_top,
                    self.width() - 4,
                    self.CONTAINER_FOOTER_HEIGHT - 8,
                ),
                13,
                13,
            )
            shape = header.united(spine).united(footer)
        else:
            body = QRectF(2, 7, self.width() - 4, self.height() - 15)
            shape = QPainterPath()
            shape.addRoundedRect(body, 15, 15)

        # The lower tab and transparent upper socket interlock when snapped,
        # giving the sequence a compact LEGO/Scratch-like silhouette.
        tab_path = QPainterPath()
        tab_path.addRoundedRect(QRectF(27, self.height() - 13, 54, 12), 6, 6)
        shape = shape.united(tab_path)
        painter.setPen(QPen(border, border_width))
        painter.setBrush(color)
        painter.drawPath(shape)

        if self._is_container:
            if not self._container_has_children:
                hint_rect = self.container_body_rect().adjusted(14, 12, -14, -12)
                painter.setPen(QPen(QColor(100, 116, 139, 150), 2, Qt.PenStyle.DashLine))
                painter.setBrush(QColor(255, 255, 255, 75))
                painter.drawRoundedRect(hint_rect, 10, 10)
                painter.setPen(QColor(71, 85, 105, 190))
                painter.drawText(
                    hint_rect,
                    Qt.AlignmentFlag.AlignCenter,
                    "Drop blocks inside",
                )
            loop_font = painter.font()
            loop_font.setPointSize(18)
            loop_font.setBold(True)
            painter.setFont(loop_font)
            painter.setPen(QColor(255, 255, 255, 225))
            painter.drawText(
                QRectF(
                    self.width() - 47,
                    self.container_footer_top + 1,
                    31,
                    29,
                ),
                Qt.AlignmentFlag.AlignCenter,
                "\u21bb",
            )

        socket = QRectF(27, 2, 54, 12)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Qt.GlobalColor.transparent)
        painter.drawRoundedRect(socket, 6, 6)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setPen(QPen(border, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(socket, 0, 180 * 16)
        painter.end()
        super().paintEvent(event)

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
    HOTSPOT_MIME_TYPE = "application/x-macroblock-hotspot"
    selected = Signal(str)
    dragStarted = Signal(str)
    dragFinished = Signal(str, bool)

    def __init__(self, definition: BlockDefinition, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.definition = definition
        self._press_position: QPoint | None = None
        self._drag_started = False
        self._selected = False
        self._hovered = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setObjectName("paletteBlock")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        self.label = QLabel(definition.display_label)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.label)
        self._update_style()

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._update_style()

    def _update_style(self) -> None:
        border = "#FFFFFF" if self._selected else "rgba(15,23,42,75)"
        width = 3 if self._selected else 1
        lift = "background" if self._hovered or self._selected else "background"
        self.setStyleSheet(
            "QFrame#paletteBlock {"
            f"{lift}: {self.definition.color}; border: {width}px solid {border};"
            "border-radius: 11px; padding: 4px;}"
            f"QLabel {{ color: {_text_color(self.definition.color)}; font-weight: 700;"
            " background: transparent; border: none; }}"
        )

    def create_mime_data(self, hotspot: QPoint | None = None):
        from PySide6.QtCore import QMimeData

        hotspot = hotspot or QPoint(12, 12)
        mime = QMimeData()
        mime.setData(self.MIME_TYPE, self.definition.id.encode("utf-8"))
        mime.setData(
            self.HOTSPOT_MIME_TYPE,
            f"{hotspot.x()},{hotspot.y()}".encode("ascii"),
        )
        return mime

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_position = event.position().toPoint()
            self._drag_started = False
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if not (event.buttons() & Qt.MouseButton.LeftButton) or self._press_position is None:
            return super().mouseMoveEvent(event)
        if (event.position().toPoint() - self._press_position).manhattanLength() < 8:
            return
        self._drag_started = True
        self.selected.emit(self.definition.id)
        self.dragStarted.emit(self.definition.id)
        drag = QDrag(self)
        drag.setMimeData(self.create_mime_data(self._press_position))
        drag.setPixmap(self.grab())
        drag.setHotSpot(self._press_position)
        result = drag.exec(Qt.DropAction.CopyAction)
        self.dragFinished.emit(
            self.definition.id, result == Qt.DropAction.CopyAction
        )
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseReleaseEvent(self, event) -> None:
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._press_position is not None
            and not self._drag_started
        ):
            self.selected.emit(self.definition.id)
        self._press_position = None
        super().mouseReleaseEvent(event)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self._update_style()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self._update_style()
        super().leaveEvent(event)
