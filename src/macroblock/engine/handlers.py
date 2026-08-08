"""Extensible action-handler catalog for built-in block definitions."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from macroblock.blocks import BlockInstance

if TYPE_CHECKING:
    from macroblock.engine.executor import ExecutionContext

BlockHandler = Callable[[BlockInstance, "ExecutionContext"], None]


class BlockHandlerRegistry:
    """Lets new definitions add behavior without modifying the interpreter."""

    def __init__(self) -> None:
        self._handlers: dict[str, BlockHandler] = {}

    def register(self, type_id: str, handler: BlockHandler) -> None:
        if type_id in self._handlers:
            raise ValueError(f"Duplicate execution handler for '{type_id}'.")
        self._handlers[type_id] = handler

    def handler(self, type_id: str) -> BlockHandler | None:
        return self._handlers.get(type_id)


def create_builtin_handlers() -> BlockHandlerRegistry:
    handlers = BlockHandlerRegistry()

    handlers.register(
        "mouse.move_to",
        lambda block, context: context.input.move_to(
            block.params["x"], block.params["y"]
        ),
    )
    handlers.register(
        "mouse.click",
        lambda block, context: context.input.click(
            block.params["button"], block.params["count"]
        ),
    )
    handlers.register(
        "mouse.drag",
        lambda block, context: context.input.drag(
            block.params["x1"],
            block.params["y1"],
            block.params["x2"],
            block.params["y2"],
        ),
    )
    handlers.register(
        "mouse.scroll",
        lambda block, context: context.input.scroll(block.params["amount"]),
    )
    handlers.register(
        "keyboard.press",
        lambda block, context: context.input.press_key(block.params["key"]),
    )
    handlers.register(
        "keyboard.type_text",
        lambda block, context: context.input.type_text(block.params["text"]),
    )
    handlers.register(
        "keyboard.combo",
        lambda block, context: context.input.key_combo(block.params["keys"]),
    )
    handlers.register(
        "timing.wait",
        lambda block, context: context.abort_event.wait(block.params["seconds"]),
    )

    def set_variable(block: BlockInstance, context: "ExecutionContext") -> None:
        context.variables[block.params["name"]] = block.params["value"]

    def change_variable(block: BlockInstance, context: "ExecutionContext") -> None:
        name = block.params["name"]
        current = context.variables.get(name, 0)
        if isinstance(current, bool) or not isinstance(current, (int, float)):
            raise ValueError(
                f"Variable '{name}' contains {current!r} and cannot be changed numerically."
            )
        context.variables[name] = current + block.params["by"]

    handlers.register("variables.set", set_variable)
    handlers.register("variables.change", change_variable)
    return handlers
