"""Free-positioned visual block canvas with responsive LEGO-like snapping."""

from __future__ import annotations

import math
from dataclasses import dataclass

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
        self._dragged_positions: dict[str, QPointF] = {}
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
        self._dragged_positions = self.canvas_scene.connected_positions(
            self.block.instance_id
        )
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
            self.canvas_scene.move_connected_items(
                self.block.instance_id,
                self._dragged_positions,
                self.pos() - self._drag_start,
            )
            self.canvas_scene.preview_snap_for_item(self)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setZValue(1)
        self.canvas_scene.snap_item(self)
        self._dragged_positions.clear()

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
            if not self.canvas_scene._layout_in_progress:
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


@dataclass(frozen=True)
class SnapMatch:
    """A resolved snap destination, including container-cavity targets."""

    owner_id: str
    kind: str
    highlight_id: str
    expected_position: QPointF
    distance: float
    inside: bool = False


class CanvasScene(QGraphicsScene):
    graphChanged = Signal()
    warningChanged = Signal(str)
    interactionMessage = Signal(str)

    SNAP_DISTANCE = 92.0
    BLOCK_GAP = -7.0
    CONNECTOR_X = 54.0
    CONTAINER_INDENT = 31.0
    CONTAINER_RIGHT_PADDING = 14.0

    def __init__(self, registry: BlockRegistry, parent=None) -> None:
        super().__init__(parent)
        self.registry = registry
        self.graph = ScriptGraph()
        self.block_items: dict[str, BlockGraphicsItem] = {}
        self.connection_items: list[QGraphicsPathItem] = []
        self.snap_preview_item: QGraphicsPathItem | None = None
        self._snap_target_id: str | None = None
        self.last_added_id: str | None = None
        self._layout_in_progress = False
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
        self.relayout_all()
        self.on_graph_changed()

    def connect_blocks(
        self, previous_id: str, next_id: str, *, as_child: bool = False
    ) -> None:
        """Insert a block stack after a block or at the front of a container."""

        if previous_id == next_id:
            raise ValueError("A block cannot connect to itself.")
        blocks = self.graph.block_map()
        previous = blocks[previous_id]
        field = "child_id" if as_child else "next_id"
        if as_child and not self.registry.block(previous.type_id).is_container:
            raise ValueError("Only a container block can own a child chain.")
        if getattr(previous, field) == next_id:
            self.relayout_component(previous_id)
            self.on_graph_changed()
            return
        if self._would_cycle(previous_id, next_id):
            raise ValueError("That connection would create a graph cycle.")

        displaced_id = getattr(previous, field)
        self.disconnect_incoming(next_id, notify=False)
        setattr(previous, field, next_id)

        # Preserve an occupied connector by inserting the dragged stack above
        # its former content, matching a physical stack of blocks.
        if displaced_id and displaced_id not in self.sequence_ids(next_id):
            tail = blocks[self.sequence_tail(next_id)]
            tail.next_id = displaced_id

        self.relayout_component(previous_id)
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

    def incoming_reference(self, block_id: str) -> tuple[str, str] | None:
        for block in self.graph.blocks:
            if block.next_id == block_id:
                return block.instance_id, "next"
            if block.child_id == block_id:
                return block.instance_id, "child"
        return None

    def sequence_ids(self, start_id: str | None) -> list[str]:
        blocks = self.graph.block_map()
        sequence: list[str] = []
        seen: set[str] = set()
        current_id = start_id
        while current_id and current_id not in seen:
            sequence.append(current_id)
            seen.add(current_id)
            current_id = blocks[current_id].next_id
        return sequence

    def sequence_tail(self, start_id: str) -> str:
        return self.sequence_ids(start_id)[-1]

    def connected_ids(self, start_id: str) -> set[str]:
        blocks = self.graph.block_map()
        pending = [start_id]
        connected: set[str] = set()
        while pending:
            block_id = pending.pop()
            if block_id in connected:
                continue
            connected.add(block_id)
            block = blocks[block_id]
            pending.extend(ref for ref in (block.next_id, block.child_id) if ref)
        return connected

    def connected_positions(self, start_id: str) -> dict[str, QPointF]:
        return {
            block_id: QPointF(self.block_items[block_id].pos())
            for block_id in self.connected_ids(start_id)
            if block_id in self.block_items
        }

    def move_connected_items(
        self,
        source_id: str,
        starting_positions: dict[str, QPointF],
        delta: QPointF,
    ) -> None:
        self._layout_in_progress = True
        try:
            for block_id, start in starting_positions.items():
                if block_id != source_id and block_id in self.block_items:
                    self.block_items[block_id].setPos(start + delta)
        finally:
            self._layout_in_progress = False
        self.refresh_connections()

    def disconnect_incoming(
        self, block_id: str, *, notify: bool = True
    ) -> tuple[str, str] | None:
        incoming = self.incoming_reference(block_id)
        if incoming is None:
            return None
        owner_id, kind = incoming
        owner = self.graph.block_map()[owner_id]
        setattr(owner, "child_id" if kind == "child" else "next_id", None)
        self.relayout_component(owner_id)
        if notify:
            self.interactionMessage.emit(
                "Block stack detached — move it near a connector or loop cavity to snap."
            )
            self.on_graph_changed()
        return incoming

    def delete_block(self, block_id: str) -> None:
        self.clear_snap_preview()
        blocks = self.graph.block_map()
        block = blocks[block_id]
        incoming = self.incoming_reference(block_id)
        old_position = QPointF(self.block_items[block_id].pos())
        old_width = self.block_items[block_id].boundingRect().width()
        successor_id = block.next_id
        child_id = block.child_id

        if incoming:
            owner_id, kind = incoming
            owner = blocks[owner_id]
            setattr(
                owner,
                "child_id" if kind == "child" else "next_id",
                successor_id,
            )
        elif successor_id:
            self.block_items[successor_id].setPos(old_position)

        # Removing a C block must not delete its body. Its former child stack
        # becomes an independent root beside the repaired sequence.
        if child_id:
            child_position = (
                old_position + QPointF(old_width + 38, 0)
                if successor_id or incoming
                else old_position
            )
            self.block_items[child_id].setPos(child_position)

        block.next_id = None
        block.child_id = None
        self.graph.blocks.remove(block)
        item = self.block_items.pop(block_id)
        self.removeItem(item)
        if self.last_added_id == block_id:
            self.last_added_id = successor_id or child_id
            if self.last_added_id is None and self.graph.blocks:
                self.last_added_id = self.graph.blocks[-1].instance_id
        self.relayout_all()
        self.interactionMessage.emit("Block deleted; connected blocks were preserved.")
        self.on_graph_changed()

    def _component_root(self, block_id: str) -> str:
        current_id = block_id
        seen: set[str] = set()
        while current_id not in seen:
            seen.add(current_id)
            incoming = self.incoming_reference(current_id)
            if incoming is None:
                return current_id
            current_id = incoming[0]
        return block_id

    def relayout_component(self, block_id: str) -> None:
        if block_id not in self.block_items:
            return
        root_id = self._component_root(block_id)
        root_position = QPointF(self.block_items[root_id].pos())
        self._layout_in_progress = True
        try:
            self._layout_sequence(
                root_id,
                root_position.x(),
                root_position.y(),
                set(),
                depth=0,
            )
        finally:
            self._layout_in_progress = False
        self.refresh_connections()

    def relayout_all(self) -> None:
        referenced = {
            ref
            for block in self.graph.blocks
            for ref in (block.next_id, block.child_id)
            if ref
        }
        roots = [
            block.instance_id
            for block in self.graph.blocks
            if block.instance_id not in referenced
        ]
        visited: set[str] = set()
        self._layout_in_progress = True
        try:
            for root_id in roots:
                item = self.block_items[root_id]
                self._layout_sequence(
                    root_id,
                    item.x(),
                    item.y(),
                    visited,
                    depth=0,
                )
        finally:
            self._layout_in_progress = False
        self.refresh_connections()

    def _layout_sequence(
        self,
        start_id: str,
        x: float,
        y: float,
        visited: set[str],
        *,
        depth: int,
    ) -> tuple[float, float]:
        blocks = self.graph.block_map()
        current_id: str | None = start_id
        cursor_y = y
        max_right = x
        while current_id and current_id not in visited:
            visited.add(current_id)
            block = blocks[current_id]
            item = self.block_items[current_id]
            definition = self.registry.block(block.type_id)
            item.setPos(QPointF(x, cursor_y))
            item.setZValue(depth + 1)

            child_right = x
            if definition.is_container:
                editor = item.editor
                if block.child_id:
                    child_height, child_right = self._layout_sequence(
                        block.child_id,
                        x + self.CONTAINER_INDENT,
                        cursor_y + editor.container_child_y,
                        visited,
                        depth=depth + 1,
                    )
                    editor.set_container_layout(
                        child_height,
                        child_right - x + self.CONTAINER_RIGHT_PADDING,
                        has_children=True,
                    )
                else:
                    editor.set_container_layout(
                        editor.EMPTY_CONTAINER_BODY_HEIGHT,
                        editor._natural_width + 34,
                        has_children=False,
                    )
                # QGraphicsProxyWidget does not reliably pick up a QWidget
                # resize that occurs after setWidget(); keep its scene
                # geometry in lockstep so wide/deep C blocks are not clipped.
                proxy_width = float(editor.width())
                proxy_height = float(editor.height())
                item.setMinimumSize(proxy_width, proxy_height)
                item.setMaximumSize(proxy_width, proxy_height)
                item.resize(proxy_width, proxy_height)

            height = float(item.editor.height())
            width = float(item.editor.width())
            max_right = max(max_right, x + width, child_right)
            cursor_y += height + self.BLOCK_GAP
            current_id = block.next_id

        return max(0.0, cursor_y - y - self.BLOCK_GAP), max_right

    def find_snap_target_for_position(
        self, position: QPointF, *, exclude_id: str | None = None
    ) -> SnapMatch | None:
        matches: list[tuple[tuple[float, float, float], SnapMatch]] = []
        for target_id, target in self.block_items.items():
            if target_id == exclude_id:
                continue
            if exclude_id and self._would_cycle(target_id, exclude_id):
                continue
            expected = QPointF(
                target.x(),
                target.y() + target.boundingRect().height() + self.BLOCK_GAP,
            )
            distance = QLineF(position, expected).length()
            if distance <= self.SNAP_DISTANCE:
                match = SnapMatch(
                    target_id,
                    "next",
                    target_id,
                    expected,
                    distance,
                    inside=False,
                )
                matches.append(((1.0, distance, 0.0), match))

            definition = self.registry.block(target.block.type_id)
            if not definition.is_container:
                continue
            cavity = target.editor.container_body_rect().translated(target.pos())
            inside_cavity = cavity.adjusted(-12, -12, 12, 12).contains(position)
            if target.block.child_id:
                owner_id = self.sequence_tail(target.block.child_id)
                owner_item = self.block_items[owner_id]
                inside_expected = QPointF(
                    owner_item.x(),
                    owner_item.y()
                    + owner_item.boundingRect().height()
                    + self.BLOCK_GAP,
                )
                kind = "next"
            else:
                owner_id = target_id
                inside_expected = target.pos() + QPointF(
                    self.CONTAINER_INDENT,
                    target.editor.container_child_y,
                )
                kind = "child"
            if exclude_id and self._would_cycle(owner_id, exclude_id):
                continue
            inside_distance = QLineF(position, inside_expected).length()
            if inside_cavity or inside_distance <= self.SNAP_DISTANCE:
                match = SnapMatch(
                    owner_id,
                    kind,
                    target_id,
                    inside_expected,
                    inside_distance,
                    inside=True,
                )
                # A containing cavity wins over nearby external connectors;
                # the smallest cavity wins when loops are nested.
                score = (
                    0.0 if inside_cavity else 0.5,
                    cavity.width() * cavity.height()
                    if inside_cavity
                    else inside_distance,
                    inside_distance,
                )
                matches.append((score, match))
        return min(matches, key=lambda candidate: candidate[0])[1] if matches else None

    def preview_snap_for_item(self, item: BlockGraphicsItem) -> None:
        match = self.find_snap_target_for_position(
            item.pos(), exclude_id=item.block.instance_id
        )
        if match is None:
            self.clear_snap_preview()
            return
        end = item.pos() + QPointF(self.CONNECTOR_X, 7)
        self.show_snap_preview(match, end)

    def show_snap_preview(self, match: SnapMatch, end: QPointF) -> None:
        target_id = match.highlight_id
        if self._snap_target_id and self._snap_target_id != target_id:
            previous = self.block_items.get(self._snap_target_id)
            if previous:
                previous.set_snap_target(False)
        target = self.block_items[target_id]
        target.set_snap_target(True)
        self._snap_target_id = target_id
        if self.snap_preview_item is not None:
            self.removeItem(self.snap_preview_item)
        start = match.expected_position + QPointF(self.CONNECTOR_X, 7)
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
            self.connect_blocks(
                match.owner_id,
                item.block.instance_id,
                as_child=match.kind == "child",
            )
            label = self.registry.block(item.block.type_id).display_label
            self.interactionMessage.emit(
                f"Nested {label} inside the loop."
                if match.inside
                else f"Snapped {label} into the sequence."
            )
            return True
        self.on_graph_changed()
        self.interactionMessage.emit(
            "Block placed freely — drag it near a connector or into a loop."
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
                if is_child:
                    # The C-shaped cavity itself communicates containment.
                    continue
                start = source.pos() + QPointF(
                    self.CONNECTOR_X,
                    source.boundingRect().height() - 3,
                )
                end = target.pos() + QPointF(self.CONNECTOR_X, 7)
                if QLineF(start, end).length() < 24:
                    # Adjacent blocks are already joined by their visible tab
                    # and socket; a tiny bezier here reads as an oval artifact.
                    continue
                path = QPainterPath(start)
                vertical = max(8.0, abs(end.y() - start.y()) / 2)
                path.cubicTo(
                    start + QPointF(0, vertical),
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
        self._drag_target_inside = False
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
            self._drag_target_inside = bool(match and match.inside)
            if match:
                self.canvas_scene.show_snap_preview(
                    match,
                    position + QPointF(self.canvas_scene.CONNECTOR_X, 7),
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
        self._drag_target_inside = False
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
                "Release inside loop"
                if self._drag_target_inside
                else "Release to snap"
                if self._drag_will_snap
                else "Release to add block",
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
