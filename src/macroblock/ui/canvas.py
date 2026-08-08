"""Free-positioned visual block canvas with top-to-bottom snapping."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsPathItem,
    QGraphicsProxyWidget,
    QGraphicsScene,
    QGraphicsView,
    QMenu,
)

from macroblock.blocks import BlockInstance, BlockRegistry, ScriptGraph
from macroblock.ui.block_widgets import BlockEditorWidget, PaletteBlockWidget


class BlockGraphicsItem(QGraphicsProxyWidget):
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
        editor = BlockEditorWidget(definition, block)
        editor.parameterChanged.connect(lambda *_args: scene.on_graph_changed())
        self.setWidget(editor)
        self.setFlag(self.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(self.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCacheMode(self.CacheMode.DeviceCoordinateCache)
        self.setZValue(1)

    @property
    def editor(self) -> BlockEditorWidget:
        return self.widget()

    def mousePressEvent(self, event) -> None:
        self._drag_start = self.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if (self.pos() - self._drag_start).manhattanLength() > 6:
            self.canvas_scene.disconnect_incoming(self.block.instance_id)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self.canvas_scene.snap_item(self)

    def itemChange(self, change, value):
        result = super().itemChange(change, value)
        if change == self.GraphicsItemChange.ItemPositionHasChanged:
            self.block.x = float(value.x())
            self.block.y = float(value.y())
            self.canvas_scene.refresh_connections()
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

    SNAP_DISTANCE = 64.0
    BLOCK_GAP = 12.0

    def __init__(self, registry: BlockRegistry, parent=None) -> None:
        super().__init__(parent)
        self.registry = registry
        self.graph = ScriptGraph()
        self.block_items: dict[str, BlockGraphicsItem] = {}
        self.connection_items: list[QGraphicsPathItem] = []
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
        item = BlockGraphicsItem(self, self.registry.block(type_id), block)
        self.addItem(item)
        item.setPos(position)
        self.block_items[block.instance_id] = item
        self.on_graph_changed()
        return item

    def connect_blocks(self, previous_id: str, next_id: str, *, as_child: bool = False) -> None:
        if previous_id == next_id:
            raise ValueError("A block cannot connect to itself.")
        blocks = self.graph.block_map()
        previous = blocks[previous_id]
        following = blocks[next_id]
        if self.registry.block(following.type_id).is_entry_point:
            raise ValueError("An event entry block cannot connect below another block.")
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
            previous_item.y() + previous_item.boundingRect().height() + self.BLOCK_GAP,
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
            self.on_graph_changed()

    def delete_block(self, block_id: str) -> None:
        self.disconnect_incoming(block_id, notify=False)
        block = self.graph.block_map()[block_id]
        self.graph.blocks.remove(block)
        item = self.block_items.pop(block_id)
        self.removeItem(item)
        self.on_graph_changed()

    def snap_item(self, item: BlockGraphicsItem) -> None:
        if self.registry.block(item.block.type_id).is_entry_point:
            self.on_graph_changed()
            return
        item_top_center = item.mapToScene(item.boundingRect().topLeft()) + QPointF(
            item.boundingRect().width() / 2, 0
        )
        best: tuple[float, str] | None = None
        for target_id, target in self.block_items.items():
            if target is item or target.block.next_id is not None:
                continue
            target_bottom_center = target.mapToScene(target.boundingRect().bottomLeft()) + QPointF(
                target.boundingRect().width() / 2, self.BLOCK_GAP
            )
            distance = (item_top_center - target_bottom_center).manhattanLength()
            if distance <= self.SNAP_DISTANCE and (best is None or distance < best[0]):
                best = (distance, target_id)
        if best:
            self.connect_blocks(best[1], item.block.instance_id)
        else:
            self.on_graph_changed()

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
            for target_id, is_child in ((block.next_id, False), (block.child_id, True)):
                if target_id is None or target_id not in self.block_items:
                    continue
                source = self.block_items[block.instance_id]
                target = self.block_items[target_id]
                start = source.mapToScene(source.boundingRect().bottomLeft()) + QPointF(
                    source.boundingRect().width() / 2, 0
                )
                end = target.mapToScene(target.boundingRect().topLeft()) + QPointF(
                    target.boundingRect().width() / 2, 0
                )
                path = QPainterPath(start)
                vertical = max(18.0, (end.y() - start.y()) / 2)
                path.cubicTo(
                    start + QPointF(28 if is_child else 0, vertical),
                    end - QPointF(0, vertical),
                    end,
                )
                line = QGraphicsPathItem(path)
                line.setPen(QPen(QColor("#64748B"), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                line.setZValue(-1)
                self.addItem(line)
                self.connection_items.append(line)


class CanvasView(QGraphicsView):
    def __init__(self, registry: BlockRegistry, parent=None) -> None:
        self.canvas_scene = CanvasScene(registry)
        super().__init__(self.canvas_scene, parent)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(self.DragMode.RubberBandDrag)
        self.setViewportUpdateMode(self.ViewportUpdateMode.BoundingRectViewportUpdate)
        self.setBackgroundBrush(QColor("#F7F8FC"))
        self.setStyleSheet("border: 0; background: #F7F8FC;")

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(PaletteBlockWidget.MIME_TYPE):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat(PaletteBlockWidget.MIME_TYPE):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        if not event.mimeData().hasFormat(PaletteBlockWidget.MIME_TYPE):
            return super().dropEvent(event)
        type_id = bytes(event.mimeData().data(PaletteBlockWidget.MIME_TYPE)).decode("utf-8")
        self.canvas_scene.add_block(type_id, self.mapToScene(event.position().toPoint()))
        event.acceptProposedAction()

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

