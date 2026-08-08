"""Free-positioned visual block canvas with responsive LEGO-like snapping."""

from __future__ import annotations

import math

from PySide6.QtCore import QLineF, QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QGraphicsPathItem,
    QGraphicsProxyWidget,
    QGraphicsScene,
    QGraphicsView,
    QMenu,
)

from macroblock.blocks import BlockInstance, BlockRegistry, ScriptGraph
from macroblock.ui.block_widgets import BlockEditorWidget, PaletteBlockWidget


class BlockGraphicsItem(QGraphicsProxyWidget):
    """Movable proxy that keeps editor input usable while exposing drag feedback."""

    def __init__(
        self,
        scene: "CanvasScene",
        definition,
        block: BlockInstance,
    ) -> None:
        super().__init__()
        self.canvas_scene = scene
        self.block = block
        self._drag_start = QPointF()
        self._detached = False
        self._hovered = False
        self._snap_target = False
        editor = BlockEditorWidget(definition, block)
        editor.parameterChanged.connect(lambda *_args: scene.on_graph_changed())
        self.setWidget(editor)
        self.setFlag(self.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(self.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setCacheMode(self.CacheMode.DeviceCoordinateCache)
        self.setZValue(1)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(17)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(15, 23, 42, 70))
        self.setGraphicsEffect(shadow)

    @property
    def editor(self) -> BlockEditorWidget:
        return self.widget()

    def set_snap_target(self, active: bool) -> None:
        self._snap_target = active
        self._sync_visual_state()

    def _sync_visual_state(self) -> None:
        if self._snap_target:
            state = "snap"
        elif self.isSelected():
            state = "selected"
        elif self._hovered:
            state = "hover"
        else:
            state = "normal"
        self.editor.set_visual_state(state)

    def mousePressEvent(self, event) -> None:
        self._drag_start = self.pos()
        self._detached = False
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        self.setZValue(10)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)
        if (self.pos() - self._drag_start).manhattanLength() > 6:
            if not self._detached:
                self.canvas_scene.disconnect_incoming(self.block.instance_id)
                self._detached = True
            self.canvas_scene.preview_snap_for_item(self)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setZValue(1)
        self.canvas_scene.snap_item(self)

    def hoverEnterEvent(self, event) -> None:
        self._hovered = True
        self._sync_visual_state()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._hovered = False
        self._sync_visual_state()
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        result = super().itemChange(change, value)
        if change == self.GraphicsItemChange.ItemPositionHasChanged:
            self.block.x = float(value.x())
            self.block.y = float(value.y())
            self.canvas_scene.refresh_connections()
        elif change == self.GraphicsItemChange.ItemSelectedHasChanged:
            self._sync_visual_state()
        return result

    def contextMenuEvent(self, event) -> None:
        menu = QMenu()
        disconnect = menu.addAction("Disconnect from above")
        delete = menu.addAction("Delete block")
        selected = menu.exec(event.screenPos())
        if selected is disconnect:
            self.canvas_scene.disconnect_incoming(self.block.instance_id)
        elif selected is delete:
            self.canvas_scene.delete_block(self.block.instance_id)


class CanvasScene(QGraphicsScene):
    graphChanged = Signal()
    warningChanged = Signal(str)
    interactionMessage = Signal(str)

    SNAP_DISTANCE = 92.0
    BLOCK_GAP = -7.0
    CONNECTOR_X = 54.0

    def __init__(self, registry: BlockRegistry, parent=None) -> None:
        super().__init__(parent)
        self.registry = registry
        self.graph = ScriptGraph()
        self.block_items: dict[str, BlockGraphicsItem] = {}
        self.connection_items: list[QGraphicsPathItem] = []
        self.snap_preview_item: QGraphicsPathItem | None = None
        self._snap_target_id: str | None = None
        self.last_added_id: str | None = None
        self.setSceneRect(-2000, -2000, 6000, 6000)

    def add_block(
        self,
        type_id: str,
        position: QPointF,
        *,
        instance_id: str | None = None,
    ) -> BlockGraphicsItem:
        block = BlockInstance.create(
            self.registry,
            type_id,
            instance_id=instance_id,
            x=position.x(),
            y=position.y(),
        )
        self.graph.add(block)
        item = self._add_existing_block(block)
        self.last_added_id = block.instance_id
        self.on_graph_changed()
        return item

    def add_block_after_last(
        self, type_id: str, fallback_position: QPointF
    ) -> tuple[BlockGraphicsItem, bool]:
        previous_id = (
            self.last_added_id if self.last_added_id in self.block_items else None
        )
        if previous_id is None:
            item = self.add_block(type_id, fallback_position)
            return item, False
        previous_item = self.block_items[previous_id]
        position = QPointF(
            previous_item.x(),
            previous_item.y()
            + previous_item.boundingRect().height()
            + self.BLOCK_GAP,
        )
        item = self.add_block(type_id, position)
        self.connect_blocks(previous_id, item.block.instance_id)
        return item, True

    def _add_existing_block(self, block: BlockInstance) -> BlockGraphicsItem:
        item = BlockGraphicsItem(self, self.registry.block(block.type_id), block)
        self.addItem(item)
        self.block_items[block.instance_id] = item
        item.setPos(QPointF(block.x, block.y))
        return item

    def load_graph(self, graph: ScriptGraph) -> None:
        graph.validate(self.registry)
        snapshot = ScriptGraph.from_dict(graph.to_dict(), self.registry)
        self.clear_snap_preview()
        for connection in self.connection_items:
            self.removeItem(connection)
        self.connection_items.clear()
        for item in self.block_items.values():
            self.removeItem(item)
        self.block_items.clear()
        self.graph = snapshot
        for block in self.graph.blocks:
            self._add_existing_block(block)
        self.last_added_id = self.graph.blocks[-1].instance_id if self.graph.blocks else None
        self.on_graph_changed()

    def connect_blocks(self, previous_id: str, next_id: str, *, as_child: bool = False) -> None:
        if previous_id == next_id:
            raise ValueError("A block cannot connect to itself.")
        blocks = self.graph.block_map()
        previous = blocks[previous_id]
        if self._would_cycle(previous_id, next_id):
            raise ValueError("That connection would create a graph cycle.")
        self.disconnect_incoming(next_id, notify=False)
        if as_child:
            if not self.registry.block(previous.type_id).is_container:
                raise ValueError("Only a container block can own a child chain.")
            previous.child_id = next_id
        else:
            previous.next_id = next_id
        previous_item = self.block_items[previous_id]
        next_item = self.block_items[next_id]
        indent = 28.0 if as_child else 0.0
        next_item.setPos(
            previous_item.x() + indent,
            previous_item.y()
            + previous_item.boundingRect().height()
            + self.BLOCK_GAP,
        )
        self.on_graph_changed()

    def _would_cycle(self, previous_id: str, next_id: str) -> bool:
        blocks = self.graph.block_map()
        pending = [next_id]
        seen: set[str] = set()
        while pending:
            current_id = pending.pop()
            if current_id == previous_id:
                return True
            if current_id in seen:
                continue
            seen.add(current_id)
            current = blocks[current_id]
            pending.extend(ref for ref in (current.next_id, current.child_id) if ref)
        return False

    def disconnect_incoming(self, block_id: str, *, notify: bool = True) -> None:
        changed = False
        for block in self.graph.blocks:
            if block.next_id == block_id:
                block.next_id = None
                changed = True
            if block.child_id == block_id:
                block.child_id = None
                changed = True
        if changed and notify:
            self.interactionMessage.emit("Block detached — move it near another block to snap.")
            self.on_graph_changed()

    def delete_block(self, block_id: str) -> None:
        self.clear_snap_preview()
        self.disconnect_incoming(block_id, notify=False)
        block = self.graph.block_map()[block_id]
        self.graph.blocks.remove(block)
        item = self.block_items.pop(block_id)
        self.removeItem(item)
        if self.last_added_id == block_id:
            self.last_added_id = (
                self.graph.blocks[-1].instance_id if self.graph.blocks else None
            )
        self.interactionMessage.emit("Block deleted.")
        self.on_graph_changed()

    def find_snap_target_for_position(
        self, position: QPointF, *, exclude_id: str | None = None
    ) -> tuple[str, float] | None:
        best: tuple[str, float] | None = None
        for target_id, target in self.block_items.items():
            if target_id == exclude_id or target.block.next_id is not None:
                continue
            if exclude_id and self._would_cycle(target_id, exclude_id):
                continue
            expected = QPointF(
                target.x(),
                target.y() + target.boundingRect().height() + self.BLOCK_GAP,
            )
            distance = QLineF(position, expected).length()
            if distance <= self.SNAP_DISTANCE and (
                best is None or distance < best[1]
            ):
                best = (target_id, distance)
        return best

    def preview_snap_for_item(self, item: BlockGraphicsItem) -> None:
        match = self.find_snap_target_for_position(
            item.pos(), exclude_id=item.block.instance_id
        )
        if match is None:
            self.clear_snap_preview()
            return
        end = item.pos() + QPointF(self.CONNECTOR_X, 7)
        self.show_snap_preview(match[0], end)

    def show_snap_preview(self, target_id: str, end: QPointF) -> None:
        if self._snap_target_id and self._snap_target_id != target_id:
            previous = self.block_items.get(self._snap_target_id)
            if previous:
                previous.set_snap_target(False)
        target = self.block_items[target_id]
        target.set_snap_target(True)
        self._snap_target_id = target_id
        if self.snap_preview_item is not None:
            self.removeItem(self.snap_preview_item)
        start = target.pos() + QPointF(
            self.CONNECTOR_X, target.boundingRect().height() - 3
        )
        path = QPainterPath(start)
        midpoint = (start.y() + end.y()) / 2
        path.cubicTo(
            QPointF(start.x(), midpoint),
            QPointF(end.x(), midpoint),
            end,
        )
        preview = QGraphicsPathItem(path)
        preview.setPen(
            QPen(
                QColor("#22C55E"),
                4,
                Qt.PenStyle.DashLine,
                Qt.PenCapStyle.RoundCap,
            )
        )
        preview.setZValue(0)
        self.addItem(preview)
        self.snap_preview_item = preview

    def clear_snap_preview(self) -> None:
        if self._snap_target_id:
            target = self.block_items.get(self._snap_target_id)
            if target:
                target.set_snap_target(False)
        self._snap_target_id = None
        if self.snap_preview_item is not None:
            self.removeItem(self.snap_preview_item)
            self.snap_preview_item = None

    def snap_item(self, item: BlockGraphicsItem) -> bool:
        match = self.find_snap_target_for_position(
            item.pos(), exclude_id=item.block.instance_id
        )
        self.clear_snap_preview()
        if match:
            self.connect_blocks(match[0], item.block.instance_id)
            label = self.registry.block(item.block.type_id).display_label
            self.interactionMessage.emit(f"Snapped {label} into the sequence.")
            return True
        self.on_graph_changed()
        self.interactionMessage.emit(
            "Block placed freely — drag it near a connector to snap."
        )
        return False

    def on_graph_changed(self) -> None:
        self.refresh_connections()
        self.warningChanged.emit(self.hotkey_warning())
        self.graphChanged.emit()

    def hotkey_warning(self) -> str:
        used: dict[str, int] = {}
        for block in self.graph.blocks:
            if block.type_id == "events.hotkey":
                normalized = str(block.params["hotkey"]).strip().casefold()
                used[normalized] = used.get(normalized, 0) + 1
        duplicates = sorted(key for key, count in used.items() if count > 1)
        return (
            "Duplicate event hotkey: " + ", ".join(duplicates)
            if duplicates
            else ""
        )

    def refresh_connections(self) -> None:
        for connection in self.connection_items:
            self.removeItem(connection)
        self.connection_items.clear()
        if not self.block_items:
            return
        for block in self.graph.blocks:
            if block.instance_id not in self.block_items:
                continue
            for target_id, is_child in ((block.next_id, False), (block.child_id, True)):
                if target_id is None or target_id not in self.block_items:
                    continue
                source = self.block_items[block.instance_id]
                target = self.block_items[target_id]
                start = source.pos() + QPointF(
                    self.CONNECTOR_X,
                    source.boundingRect().height() - 3,
                )
                end = target.pos() + QPointF(self.CONNECTOR_X, 7)
                if not is_child and QLineF(start, end).length() < 24:
                    # Adjacent blocks are already joined by their visible tab
                    # and socket; a tiny bezier here reads as an oval artifact.
                    continue
                path = QPainterPath(start)
                vertical = max(8.0, abs(end.y() - start.y()) / 2)
                path.cubicTo(
                    start + QPointF(28 if is_child else 0, vertical),
                    end - QPointF(0, vertical),
                    end,
                )
                line = QGraphicsPathItem(path)
                line.setPen(
                    QPen(
                        QColor("#64748B"),
                        4,
                        Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap,
                    )
                )
                line.setZValue(-1)
                self.addItem(line)
                self.connection_items.append(line)


class CanvasView(QGraphicsView):
    interactionMessage = Signal(str)

    def __init__(self, registry: BlockRegistry, parent=None) -> None:
        self.canvas_scene = CanvasScene(registry)
        super().__init__(self.canvas_scene, parent)
        self._drag_active = False
        self._drag_position = QPoint()
        self._drag_will_snap = False
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(self.DragMode.RubberBandDrag)
        self.setViewportUpdateMode(self.ViewportUpdateMode.BoundingRectViewportUpdate)
        self.setBackgroundBrush(QColor("#F8FAFC"))
        self.setStyleSheet("border: 0; background: #F8FAFC;")
        self.canvas_scene.interactionMessage.connect(self.interactionMessage)

    @staticmethod
    def _type_from_mime(mime) -> str:
        return bytes(mime.data(PaletteBlockWidget.MIME_TYPE)).decode("utf-8")

    @staticmethod
    def _hotspot_from_mime(mime) -> QPoint:
        if not mime.hasFormat(PaletteBlockWidget.HOTSPOT_MIME_TYPE):
            return QPoint(12, 12)
        try:
            x, y = bytes(
                mime.data(PaletteBlockWidget.HOTSPOT_MIME_TYPE)
            ).decode("ascii").split(",", 1)
            return QPoint(int(x), int(y))
        except (TypeError, ValueError):
            return QPoint(12, 12)

    def _drop_scene_position(self, event) -> QPointF:
        cursor = event.position().toPoint()
        top_left = cursor - self._hotspot_from_mime(event.mimeData())
        return self.mapToScene(top_left)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(PaletteBlockWidget.MIME_TYPE):
            self._drag_active = True
            self._drag_position = event.position().toPoint()
            label = self.canvas_scene.registry.block(
                self._type_from_mime(event.mimeData())
            ).display_label
            self.interactionMessage.emit(
                f"Dragging {label} — green means it will snap."
            )
            event.acceptProposedAction()
            self.viewport().update()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat(PaletteBlockWidget.MIME_TYPE):
            self._drag_position = event.position().toPoint()
            position = self._drop_scene_position(event)
            match = self.canvas_scene.find_snap_target_for_position(position)
            self._drag_will_snap = match is not None
            if match:
                self.canvas_scene.show_snap_preview(
                    match[0], position + QPointF(self.canvas_scene.CONNECTOR_X, 7)
                )
            else:
                self.canvas_scene.clear_snap_preview()
            event.acceptProposedAction()
            self.viewport().update()
        else:
            super().dragMoveEvent(event)

    def dragLeaveEvent(self, event) -> None:
        self._finish_drag_feedback()
        self.interactionMessage.emit("Drag cancelled.")
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        if not event.mimeData().hasFormat(PaletteBlockWidget.MIME_TYPE):
            return super().dropEvent(event)
        type_id = self._type_from_mime(event.mimeData())
        item = self.canvas_scene.add_block(type_id, self._drop_scene_position(event))
        snapped = self.canvas_scene.snap_item(item)
        self._finish_drag_feedback()
        if not snapped:
            label = self.canvas_scene.registry.block(type_id).display_label
            self.interactionMessage.emit(f"Added {label} to the canvas.")
        event.acceptProposedAction()

    def _finish_drag_feedback(self) -> None:
        self._drag_active = False
        self._drag_will_snap = False
        self.canvas_scene.clear_snap_preview()
        self.viewport().update()

    def add_block_from_toolbar(self, type_id: str) -> tuple[BlockGraphicsItem, bool]:
        center = self.mapToScene(self.viewport().rect().center()) - QPointF(120, 45)
        item, connected = self.canvas_scene.add_block_after_last(type_id, center)
        self.ensureVisible(item, 70, 70)
        label = self.canvas_scene.registry.block(type_id).display_label
        self.interactionMessage.emit(
            f"Added {label} and connected it to the previous block."
            if connected
            else f"Added {label} as the first block."
        )
        return item, connected

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        painter.fillRect(rect, QColor("#F8FAFC"))
        spacing = 24
        start_x = math.floor(rect.left() / spacing) * spacing
        start_y = math.floor(rect.top() / spacing) * spacing
        minor = QPen(QColor("#D8E1EC"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        major = QPen(QColor("#B8C7D9"), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        x = start_x
        while x <= rect.right():
            y = start_y
            while y <= rect.bottom():
                painter.setPen(major if x % 120 == 0 and y % 120 == 0 else minor)
                painter.drawPoint(QPointF(x, y))
                y += spacing
            x += spacing

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.canvas_scene.graph.blocks:
            card = QRectF(
                self.viewport().width() / 2 - 190,
                self.viewport().height() / 2 - 58,
                380,
                116,
            )
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.setBrush(QColor(255, 255, 255, 225))
            painter.drawRoundedRect(card, 16, 16)
            title_font = painter.font()
            title_font.setPointSize(13)
            title_font.setBold(True)
            painter.setFont(title_font)
            painter.setPen(QColor("#334155"))
            painter.drawText(
                card.adjusted(18, 20, -18, -48),
                Qt.AlignmentFlag.AlignCenter,
                "Build your first automation",
            )
            body_font = painter.font()
            body_font.setPointSize(9)
            body_font.setBold(False)
            painter.setFont(body_font)
            painter.setPen(QColor("#64748B"))
            painter.drawText(
                card.adjusted(18, 56, -18, -16),
                Qt.AlignmentFlag.AlignCenter,
                "Drag a palette block here or use ADD BLOCK above.",
            )
        if self._drag_active:
            color = QColor("#22C55E") if self._drag_will_snap else QColor("#3B82F6")
            painter.setPen(QPen(color, 3, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(self.viewport().rect().adjusted(4, 4, -5, -5), 14, 14)
            painter.setPen(QPen(color, 3))
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 45))
            painter.drawEllipse(self._drag_position, 18, 18)
            pill = QRectF(18, 18, 205, 34)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(15, 23, 42, 225))
            painter.drawRoundedRect(pill, 10, 10)
            painter.setPen(QColor("white"))
            painter.drawText(
                pill,
                Qt.AlignmentFlag.AlignCenter,
                "Release to snap" if self._drag_will_snap else "Release to add block",
            )
        painter.end()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Delete:
            selected = [
                item.block.instance_id
                for item in self.canvas_scene.selectedItems()
                if isinstance(item, BlockGraphicsItem)
            ]
            for block_id in selected:
                self.canvas_scene.delete_block(block_id)
            if selected:
                return
        super().keyPressEvent(event)
