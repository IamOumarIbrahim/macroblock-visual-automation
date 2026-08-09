"""Inline block parameter editors shared by the palette and canvas."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QDrag, QKeyEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from macroblock.blocks import BlockDefinition, BlockInstance, ParameterDefinition, ParameterType


def _text_color(background: str) -> str:
    color = QColor(background)
    luminance = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
    return "#111827" if luminance > 155 else "#FFFFFF"


class CommitPlainTextEdit(QPlainTextEdit):
    """Multiline editor that commits its value when focus leaves the field."""

    editingFinished = Signal()

    def focusOutEvent(self, event) -> None:
        self.editingFinished.emit()
        super().focusOutEvent(event)


_KEY_TOKENS = {
    int(Qt.Key.Key_Backspace): "BACKSPACE",
    int(Qt.Key.Key_Tab): "TAB",
    int(Qt.Key.Key_Backtab): "TAB",
    int(Qt.Key.Key_CapsLock): "CAPSLOCK",
    int(Qt.Key.Key_Return): "ENTER",
    int(Qt.Key.Key_Enter): "ENTER",
    int(Qt.Key.Key_Shift): "SHIFT",
    int(Qt.Key.Key_Control): "CTRL",
    int(Qt.Key.Key_Alt): "ALT",
    int(Qt.Key.Key_AltGr): "ALT",
    int(Qt.Key.Key_Escape): "ESC",
    int(Qt.Key.Key_Space): "SPACE",
    int(Qt.Key.Key_PageUp): "PAGEUP",
    int(Qt.Key.Key_PageDown): "PAGEDOWN",
    int(Qt.Key.Key_End): "END",
    int(Qt.Key.Key_Home): "HOME",
    int(Qt.Key.Key_Left): "LEFT",
    int(Qt.Key.Key_Up): "UP",
    int(Qt.Key.Key_Right): "RIGHT",
    int(Qt.Key.Key_Down): "DOWN",
    int(Qt.Key.Key_Insert): "INSERT",
    int(Qt.Key.Key_Delete): "DELETE",
    int(Qt.Key.Key_Print): "PRINTSCREEN",
    int(Qt.Key.Key_Meta): "WIN",
    int(Qt.Key.Key_Menu): "MENU",
    int(Qt.Key.Key_NumLock): "NUMLOCK",
    int(Qt.Key.Key_ScrollLock): "SCROLLLOCK",
    int(Qt.Key.Key_Pause): "PAUSE",
    int(Qt.Key.Key_Plus): "PLUS",
    int(Qt.Key.Key_Minus): "MINUS",
    int(Qt.Key.Key_Comma): "COMMA",
    int(Qt.Key.Key_Period): "PERIOD",
    int(Qt.Key.Key_Slash): "SLASH",
    int(Qt.Key.Key_Backslash): "BACKSLASH",
    int(Qt.Key.Key_Semicolon): "SEMICOLON",
    int(Qt.Key.Key_Apostrophe): "QUOTE",
    int(Qt.Key.Key_BracketLeft): "LEFTBRACKET",
    int(Qt.Key.Key_BracketRight): "RIGHTBRACKET",
    int(Qt.Key.Key_QuoteLeft): "BACKTICK",
}


def _recorded_key_token(event: QKeyEvent) -> str | None:
    """Translate a Qt key event into the names understood by SendInput."""

    key = event.key()
    if token := _KEY_TOKENS.get(key):
        return token
    if int(Qt.Key.Key_F1) <= key <= int(Qt.Key.Key_F24):
        return f"F{key - int(Qt.Key.Key_F1) + 1}"
    if int(Qt.Key.Key_A) <= key <= int(Qt.Key.Key_Z):
        return chr(key)
    if int(Qt.Key.Key_0) <= key <= int(Qt.Key.Key_9):
        return chr(key)
    text = event.text()
    if len(text) == 1 and text.isprintable():
        return text.upper()
    return None


class KeystrokeRecordButton(QToolButton):
    """Captures one key or a complete chord without leaving the block."""

    valueRecorded = Signal(object)
    statusMessage = Signal(str)

    def __init__(self, *, multiple: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.multiple = multiple
        self._recording = False
        self._held: set[int] = set()
        self._recorded: list[str] = []
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.timeout.connect(self.cancel_recording)
        self.setCheckable(True)
        self.setFixedSize(24, 24)
        self.setText("\u25cf")
        self.setAccessibleName("Record key combination" if multiple else "Record key")
        self.setToolTip(
            "Record a new key combination" if multiple else "Record a new key"
        )
        self.setStyleSheet(
            "QToolButton { background: #EF4444; color: white; border: 2px solid "
            "rgba(255,255,255,210); border-radius: 12px; padding: 0; }"
            "QToolButton:hover { background: #DC2626; border-color: white; }"
            "QToolButton:checked { background: #B91C1C; border: 3px solid white; }"
        )
        self.clicked.connect(self._toggle_recording)

    @property
    def is_recording(self) -> bool:
        return self._recording

    def _toggle_recording(self, checked: bool) -> None:
        if checked:
            self.start_recording()
        else:
            self.cancel_recording()

    def start_recording(self) -> None:
        app = QApplication.instance()
        if app is None:
            self.setChecked(False)
            return
        if not self._recording:
            app.installEventFilter(self)
        self._recording = True
        self._held.clear()
        self._recorded.clear()
        self.setChecked(True)
        self._timeout.start(10_000)
        target = "the chord" if self.multiple else "one key"
        self.statusMessage.emit(
            f"Recording {target} - press and release it now; Esc cancels."
        )

    def cancel_recording(self) -> None:
        if not self._recording:
            self.setChecked(False)
            return
        self._stop_recording(commit=False)
        self.statusMessage.emit("Key recording cancelled; the existing value was kept.")

    def _stop_recording(self, *, commit: bool) -> None:
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        self._timeout.stop()
        self._recording = False
        self.setChecked(False)
        if not commit or not self._recorded:
            return
        value: object = list(self._recorded) if self.multiple else self._recorded[0]
        self.valueRecorded.emit(value)
        self.statusMessage.emit(f"Recorded {' + '.join(self._recorded)}.")

    def eventFilter(self, watched, event) -> bool:
        if not self._recording:
            return False
        if event.type() == QEvent.Type.ShortcutOverride:
            event.accept()
            return True
        if event.type() == QEvent.Type.KeyPress:
            key_event = event
            if key_event.isAutoRepeat():
                return True
            if key_event.key() == int(Qt.Key.Key_Escape):
                self.cancel_recording()
                return True
            token = _recorded_key_token(key_event)
            if token is not None and (self.multiple or not self._recorded):
                self._held.add(key_event.key())
                if token not in self._recorded:
                    self._recorded.append(token)
                self.statusMessage.emit(
                    f"Recording: {' + '.join(self._recorded)} - release to save."
                )
            return True
        if event.type() == QEvent.Type.KeyRelease:
            key_event = event
            if key_event.isAutoRepeat():
                return True
            self._held.discard(key_event.key())
            if self._recorded and not self._held:
                self._stop_recording(commit=True)
            return True
        return False


class BlockDragHandle(QLabel):
    """An explicit drag affordance that does not interfere with input fields."""

    pointerPressed = Signal(object, object)
    pointerMoved = Signal(object, object)
    pointerReleased = Signal(object, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("⠿ DRAG", parent)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip("Drag to move this stack · Alt+click to duplicate")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "background: rgba(15,23,42,55); border-radius: 7px;"
            "padding: 3px 7px; font-size: 9px; font-weight: 800;"
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.pointerPressed.emit(event.globalPosition(), event.modifiers())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.pointerMoved.emit(event.globalPosition(), event.modifiers())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.pointerReleased.emit(event.globalPosition(), event.modifiers())
            event.accept()
            return
        super().mouseReleaseEvent(event)


class BlockEditorWidget(QFrame):
    """A colored block whose parameter values are edited directly in its face."""

    parameterChanged = Signal(str, object)
    pointerPressed = Signal(object, object)
    pointerMoved = Signal(object, object)
    pointerReleased = Signal(object, object)
    interactionMessage = Signal(str)
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
        self.record_buttons: dict[str, KeystrokeRecordButton] = {}
        self._visual_state = "normal"
        self._display_number = 0
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
            "QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {"
            "background: rgba(255,255,255,235); color: #111827; border: 1px solid rgba(0,0,0,50);"
            "border-radius: 7px; padding: 2px 5px; min-height: 22px;}"
            "QSpinBox, QDoubleSpinBox { padding-right: 22px; }"
            "QSpinBox::up-button, QDoubleSpinBox::up-button,"
            "QSpinBox::down-button, QDoubleSpinBox::down-button {"
            "width: 20px; border-left: 1px solid rgba(0,0,0,45); }"
            "QSpinBox::up-button, QDoubleSpinBox::up-button {"
            "subcontrol-origin: border; subcontrol-position: top right; }"
            "QSpinBox::down-button, QDoubleSpinBox::down-button {"
            "subcontrol-origin: border; subcontrol-position: bottom right; }"
            "QComboBox { padding-right: 31px; min-width: 190px; }"
            "QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: "
            "top right; width: 27px; border-left: 1px solid rgba(0,0,0,45); }"
            "QComboBox QAbstractItemView { background: white; color: #111827; "
            "border: 1px solid #94A3B8; border-radius: 7px; padding: 5px; "
            "selection-background-color: #DBEAFE; selection-color: #111827; }"
        )
        self.setMinimumWidth(238)

        root = QVBoxLayout(self)
        root.setContentsMargins(13, 15, 39, 16)
        root.setSpacing(5)
        header = QHBoxLayout()
        header.setSpacing(8)
        title = QLabel(definition.display_label)
        title.setObjectName("blockTitle")
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        header.addWidget(title, 1)
        self.drag_handle = BlockDragHandle()
        self.drag_handle.pointerPressed.connect(self.pointerPressed.emit)
        self.drag_handle.pointerMoved.connect(self.pointerMoved.emit)
        self.drag_handle.pointerReleased.connect(self.pointerReleased.emit)
        header.addWidget(self.drag_handle)
        root.addLayout(header)

        if not definition.parameters:
            hint = QLabel("End" if definition.is_terminal else "No parameters")
            hint.setStyleSheet(f"color: {text_color}; font-weight: 400;")
            hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            root.addWidget(hint)

        for parameter in definition.parameters:
            row = QHBoxLayout()
            row.setSpacing(6)
            label = QLabel(parameter.label)
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
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
                editor.currentIndexChanged.connect(
                    lambda _index, callback=update: callback()
                )
            elif isinstance(editor, (QSpinBox, QDoubleSpinBox)):
                editor.valueChanged.connect(lambda _value, callback=update: callback())
            else:
                editor.editingFinished.connect(update)

            if (
                definition.id == "keyboard.combo"
                and parameter.id == "keys"
            ) or (
                definition.id in {"keyboard.key_down", "keyboard.key_up"}
                and parameter.id == "key"
            ):
                recorder = KeystrokeRecordButton(
                    multiple=parameter.type is ParameterType.KEY_LIST,
                    parent=self,
                )
                recorder.statusMessage.connect(self.interactionMessage.emit)

                def apply_recording(
                    value: object,
                    target: QWidget = editor,
                    callback: Callable[[], Any] = update,
                ) -> None:
                    if isinstance(target, QLineEdit):
                        target.setText(
                            " + ".join(value) if isinstance(value, list) else str(value)
                        )
                    callback()

                recorder.valueRecorded.connect(apply_recording)
                self.record_buttons[parameter.id] = recorder
                row.addWidget(recorder)
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

    def set_display_number(self, number: int) -> None:
        if number != self._display_number:
            self._display_number = number
            self.update()

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
        elif self._visual_state == "drag":
            border = QColor("#38BDF8")
            border_width = 5
            color = color.lighter(112)
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
        if self._display_number:
            badge = QRectF(self.width() - 34, 10, 25, 25)
            painter.setPen(QPen(QColor(255, 255, 255, 225), 2))
            painter.setBrush(QColor(15, 23, 42, 215))
            painter.drawEllipse(badge)
            badge_font = painter.font()
            badge_font.setPointSize(8)
            badge_font.setBold(True)
            painter.setFont(badge_font)
            painter.setPen(QColor("white"))
            painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, str(self._display_number))
        painter.end()
        super().paintEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.pointerPressed.emit(event.globalPosition(), event.modifiers())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.pointerMoved.emit(event.globalPosition(), event.modifiers())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.pointerReleased.emit(event.globalPosition(), event.modifiers())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _create_editor(
        self, parameter: ParameterDefinition, value: Any
    ) -> tuple[QWidget, Callable[[], Any]]:
        if parameter.type is ParameterType.INTEGER:
            editor = QSpinBox()
            editor.setAccelerated(True)
            editor.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
            editor.setRange(
                int(parameter.minimum) if parameter.minimum is not None else -1_000_000,
                1_000_000,
            )
            editor.setValue(value)
            return editor, editor.value
        if parameter.type is ParameterType.NUMBER:
            editor = QDoubleSpinBox()
            editor.setAccelerated(True)
            editor.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
            editor.setDecimals(3)
            editor.setRange(
                parameter.minimum if parameter.minimum is not None else -1_000_000,
                1_000_000,
            )
            editor.setValue(value)
            return editor, editor.value
        if parameter.type is ParameterType.CHOICE:
            editor = QComboBox()
            labels = parameter.choice_labels or parameter.choices
            for choice, label in zip(parameter.choices, labels):
                editor.addItem(label, choice)
            index = editor.findData(value)
            editor.setCurrentIndex(max(0, index))
            editor.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
            editor.setMaxVisibleItems(max(5, len(parameter.choices)))
            editor.view().setMinimumWidth(260)
            return editor, editor.currentData

        if parameter.type is ParameterType.LONG_TEXT:
            editor = CommitPlainTextEdit()
            editor.setPlainText(str(value))
            editor.setFixedHeight(82)
            editor.setMinimumWidth(210)
            editor.setPlaceholderText("Enter a PowerShell script…")
            return editor, editor.toPlainText

        editor = QLineEdit()
        editor.setClearButtonEnabled(True)
        editor.setMinimumWidth(132)
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
    doubleClicked = Signal(str)

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

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.definition.id)
            self.doubleClicked.emit(self.definition.id)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self._update_style()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self._update_style()
        super().leaveEvent(event)
