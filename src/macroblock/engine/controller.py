"""Coordinates the abort monitor and worker thread for the Qt UI."""

from __future__ import annotations

import threading
from collections.abc import Callable

from PySide6.QtCore import QObject, Signal

from macroblock.blocks import BlockRegistry, ScriptGraph
from macroblock.engine.abort_hotkey import AbortHotkeyMonitor
from macroblock.engine.executor import ExecutionResult, ScriptExecutor
from macroblock.engine.win32_input import InputController


class ExecutionController(QObject):
    started = Signal()
    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        registry: BlockRegistry,
        *,
        input_controller=None,
        monitor_factory: Callable[[threading.Event], AbortHotkeyMonitor] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.registry = registry
        self.input = input_controller or InputController()
        self._monitor_factory = monitor_factory or AbortHotkeyMonitor
        self._abort_event = threading.Event()
        self._monitor: AbortHotkeyMonitor | None = None
        self._worker: threading.Thread | None = None
        self.last_result: ExecutionResult | None = None
        self.last_error: str | None = None

    @property
    def is_running(self) -> bool:
        return bool(self._worker and self._worker.is_alive())

    @property
    def abort_monitor_ready(self) -> bool:
        return bool(self._monitor and self._monitor.is_ready)

    def start(self, graph: ScriptGraph, *, entry_block_id: str | None = None) -> None:
        if self.is_running:
            raise RuntimeError("A script is already running.")
        graph.validate(self.registry)
        snapshot = ScriptGraph.from_dict(graph.to_dict(), self.registry)
        self._abort_event = threading.Event()
        self._monitor = self._monitor_factory(self._abort_event)
        self._monitor.start()
        if not self._monitor.ready_event.wait(timeout=1) or not self._monitor.is_ready:
            self._monitor.stop()
            raise RuntimeError("The global abort hotkey could not be activated; script not started.")

        self.last_result = None
        self.last_error = None
        self._worker = threading.Thread(
            target=self._run,
            args=(snapshot, entry_block_id),
            name="macroblock-executor",
            daemon=True,
        )
        self._worker.start()
        self.started.emit()

    def _run(self, graph: ScriptGraph, entry_block_id: str | None) -> None:
        try:
            executor = ScriptExecutor(self.registry, self.input)
            self.last_result = executor.execute(
                graph, self._abort_event, entry_block_id=entry_block_id
            )
            self.finished.emit(self.last_result)
        except Exception as error:  # worker boundary: surface all errors to the UI
            self.last_error = str(error)
            self.failed.emit(self.last_error)
        finally:
            if self._monitor:
                self._monitor.stop()

    def abort(self) -> None:
        self._abort_event.set()

    def wait(self, timeout: float | None = None) -> bool:
        if self._worker:
            self._worker.join(timeout)
        return not self.is_running

    def shutdown(self) -> None:
        self.abort()
        if self._monitor:
            self._monitor.stop()
        self.wait(1)

