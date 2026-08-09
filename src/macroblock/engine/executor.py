"""Background-safe graph interpreter."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from macroblock.blocks import BlockRegistry, FlowBehavior, ScriptGraph
from macroblock.engine.handlers import BlockHandlerRegistry, create_builtin_handlers

logger = logging.getLogger(__name__)


class InputProtocol(Protocol):
    def move_to(self, x: int, y: int) -> bool: ...
    def click(self, button: str, count: int) -> None: ...
    def drag(self, x1: int, y1: int, x2: int, y2: int) -> bool: ...
    def scroll(self, amount: int) -> None: ...
    def press_key(self, key: str) -> None: ...
    def type_text(self, text: str) -> None: ...
    def key_combo(self, keys: list[str]) -> None: ...
    def move_by(self, dx: int, dy: int) -> bool: ...
    def button_down(self, button: str) -> None: ...
    def button_up(self, button: str) -> None: ...
    def key_down(self, key: str) -> None: ...
    def key_up(self, key: str) -> None: ...
    def hotkey_is_down(self, hotkey: str) -> bool: ...


class ExecutionError(RuntimeError):
    pass


@dataclass(slots=True)
class ExecutionContext:
    input: InputProtocol
    abort_event: threading.Event
    variables: dict[str, Any] = field(default_factory=dict)
    stop_requested: bool = False
    executed_blocks: int = 0


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    status: str
    executed_blocks: int
    duration_seconds: float
    variables: dict[str, Any]


class ScriptExecutor:
    """Interprets graph flow; action behavior is supplied by a handler registry."""

    def __init__(
        self,
        registry: BlockRegistry,
        input_controller: InputProtocol,
        handlers: BlockHandlerRegistry | None = None,
    ) -> None:
        self.registry = registry
        self.input = input_controller
        self.handlers = handlers or create_builtin_handlers()

    def execute(
        self,
        graph: ScriptGraph,
        abort_event: threading.Event,
        *,
        entry_block_id: str | None = None,
    ) -> ExecutionResult:
        graph.validate(self.registry)
        started = time.monotonic()
        context = ExecutionContext(self.input, abort_event)
        roots = [entry_block_id] if entry_block_id else self._root_ids(graph)
        blocks = graph.block_map()
        for root_id in roots:
            if root_id not in blocks:
                raise ExecutionError(f"Entry block '{root_id}' does not exist.")
            self._execute_chain(root_id, blocks, context, set())
            if abort_event.is_set() or context.stop_requested:
                break
        status = "aborted" if abort_event.is_set() else "stopped" if context.stop_requested else "completed"
        return ExecutionResult(
            status,
            context.executed_blocks,
            time.monotonic() - started,
            dict(context.variables),
        )

    @staticmethod
    def _root_ids(graph: ScriptGraph) -> list[str]:
        referenced = {
            reference
            for block in graph.blocks
            for reference in (block.next_id, block.child_id)
            if reference is not None
        }
        return [block.instance_id for block in graph.blocks if block.instance_id not in referenced]

    def _execute_chain(
        self,
        block_id: str | None,
        blocks,
        context: ExecutionContext,
        active: set[str],
    ) -> None:
        current_id = block_id
        chain_seen = set(active)
        while current_id and not context.abort_event.is_set() and not context.stop_requested:
            if current_id in chain_seen:
                raise ExecutionError(f"Execution cycle detected at block '{current_id}'.")
            chain_seen.add(current_id)
            block = blocks[current_id]
            definition = self.registry.block(block.type_id)
            context.executed_blocks += 1

            if definition.flow is FlowBehavior.STOP:
                context.stop_requested = True
            elif definition.flow is FlowBehavior.REPEAT:
                for _ in range(block.params["count"]):
                    if context.abort_event.is_set() or context.stop_requested:
                        break
                    self._execute_chain(block.child_id, blocks, context, chain_seen)
            elif definition.flow is FlowBehavior.REPEAT_FOREVER:
                while not context.abort_event.is_set() and not context.stop_requested:
                    if block.child_id is None:
                        context.abort_event.wait(0.01)
                    else:
                        self._execute_chain(block.child_id, blocks, context, chain_seen)
            elif definition.flow is FlowBehavior.CONDITION:
                if context.variables.get(block.params["name"]) == block.params["value"]:
                    self._execute_chain(block.child_id, blocks, context, chain_seen)
            elif definition.flow is FlowBehavior.ENTRY:
                handler = self.handlers.handler(block.type_id)
                if handler is not None:
                    handler(block, context)
            else:
                handler = self.handlers.handler(block.type_id)
                if handler is None:
                    raise ExecutionError(
                        f"No execution handler is registered for block type '{block.type_id}'."
                    )
                handler(block, context)
            current_id = block.next_id
