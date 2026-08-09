"""Extensible action-handler catalog for built-in block definitions."""

from __future__ import annotations

import os
import random
import shlex
import subprocess
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

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
            block.params["x"],
            block.params["y"],
            block.params["duration"],
            context.abort_event,
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
        "mouse.move_by",
        lambda block, context: context.input.move_by(
            block.params["dx"],
            block.params["dy"],
            block.params["duration"],
            context.abort_event,
        ),
    )
    handlers.register(
        "mouse.button_down",
        lambda block, context: context.input.button_down(block.params["button"]),
    )
    handlers.register(
        "mouse.button_up",
        lambda block, context: context.input.button_up(block.params["button"]),
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
        "keyboard.key_down",
        lambda block, context: context.input.key_down(block.params["key"]),
    )
    handlers.register(
        "keyboard.key_up",
        lambda block, context: context.input.key_up(block.params["key"]),
    )
    handlers.register(
        "timing.wait",
        lambda block, context: context.abort_event.wait(block.params["seconds"]),
    )

    def random_wait(block: BlockInstance, context: "ExecutionContext") -> None:
        minimum = block.params["minimum"]
        maximum = block.params["maximum"]
        if maximum < minimum:
            raise ValueError("Random wait maximum must be greater than or equal to minimum.")
        context.abort_event.wait(random.uniform(minimum, maximum))

    handlers.register("timing.random_wait", random_wait)

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
    handlers.register(
        "variables.delete",
        lambda block, context: context.variables.pop(block.params["name"], None),
    )

    def wait_for_hotkey(block: BlockInstance, context: "ExecutionContext") -> None:
        while not context.abort_event.is_set():
            if context.input.hotkey_is_down(block.params["hotkey"]):
                return
            context.abort_event.wait(0.04)

    def wait_for_file(block: BlockInstance, context: "ExecutionContext") -> None:
        path = Path(os.path.expandvars(block.params["path"])).expanduser()
        while not context.abort_event.is_set() and not path.exists():
            context.abort_event.wait(block.params["poll_seconds"])

    handlers.register("events.hotkey", wait_for_hotkey)
    handlers.register("events.wait_hotkey", wait_for_hotkey)
    handlers.register("events.wait_file", wait_for_file)

    def _expanded_path(value: str) -> str:
        return os.path.expandvars(str(Path(value).expanduser()))

    def open_file(block: BlockInstance, _context: "ExecutionContext") -> None:
        path = _expanded_path(block.params["path"])
        if not Path(path).exists():
            raise FileNotFoundError(f"File or folder does not exist: {path}")
        startfile = getattr(os, "startfile", None)
        if startfile is None:
            raise RuntimeError("Opening files is only supported on Windows.")
        startfile(path)

    def open_url(block: BlockInstance, _context: "ExecutionContext") -> None:
        url = block.params["url"].strip()
        if not urlparse(url).scheme:
            url = "https://" + url
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Open URL requires a valid http:// or https:// address.")
        if not webbrowser.open(url, new=2):
            raise RuntimeError("Windows could not open the default web browser.")

    def run_powershell(block: BlockInstance, context: "ExecutionContext") -> None:
        script = block.params["script"].strip()
        if not script:
            raise ValueError("PowerShell script cannot be empty.")
        process = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        while process.poll() is None:
            if context.abort_event.wait(0.05):
                process.terminate()
                process.wait(timeout=2)
                return
        if process.returncode:
            raise RuntimeError(
                f"PowerShell script exited with code {process.returncode}."
            )

    def launch_program(block: BlockInstance, _context: "ExecutionContext") -> None:
        program = os.path.expandvars(block.params["path"].strip())
        if not program:
            raise ValueError("Program path cannot be empty.")
        arguments = [
            argument[1:-1]
            if len(argument) >= 2
            and argument[0] == argument[-1]
            and argument[0] in {'"', "'"}
            else argument
            for argument in shlex.split(block.params["arguments"], posix=False)
        ]
        subprocess.Popen(
            [program, *arguments],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    handlers.register("system.open_file", open_file)
    handlers.register("system.open_url", open_url)
    handlers.register("system.run_powershell", run_powershell)
    handlers.register("system.launch_program", launch_program)
    return handlers
