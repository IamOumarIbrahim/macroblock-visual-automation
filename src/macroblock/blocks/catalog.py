"""Built-in category and block definitions."""

from __future__ import annotations

from macroblock.blocks.registry import (
    BlockDefinition,
    BlockRegistry,
    CategoryDefinition,
    ParameterDefinition as Param,
    ParameterType as Type,
)


CATEGORIES = (
    CategoryDefinition("mouse", "Mouse", "#3B82F6"),
    CategoryDefinition("keyboard", "Keyboard", "#8B5CF6"),
    CategoryDefinition("timing", "Timing", "#EAB308"),
    CategoryDefinition("control", "Control", "#F97316"),
    CategoryDefinition("variables", "Variables", "#EF4444"),
    CategoryDefinition("events", "Events", "#22C55E"),
)


BLOCKS = (
    BlockDefinition(
        "mouse.move_to",
        "mouse",
        "Move Cursor To",
        (Param("x", "X", Type.INTEGER, 500), Param("y", "Y", Type.INTEGER, 300)),
    ),
    BlockDefinition(
        "mouse.click",
        "mouse",
        "Click",
        (
            Param("button", "Button", Type.CHOICE, "left", ("left", "right", "middle")),
            Param("count", "Count", Type.INTEGER, 1, minimum=1),
        ),
    ),
    BlockDefinition(
        "mouse.drag",
        "mouse",
        "Drag From",
        (
            Param("x1", "X", Type.INTEGER, 100),
            Param("y1", "Y", Type.INTEGER, 100),
            Param("x2", "To X", Type.INTEGER, 500),
            Param("y2", "To Y", Type.INTEGER, 300),
        ),
    ),
    BlockDefinition(
        "mouse.scroll",
        "mouse",
        "Scroll",
        (Param("amount", "Amount", Type.INTEGER, -3),),
    ),
    BlockDefinition(
        "keyboard.press",
        "keyboard",
        "Press Key",
        (Param("key", "Key", Type.TEXT, "A"),),
    ),
    BlockDefinition(
        "keyboard.type_text",
        "keyboard",
        "Type Text",
        (Param("text", "Text", Type.TEXT, "Hello"),),
    ),
    BlockDefinition(
        "keyboard.combo",
        "keyboard",
        "Key Combo",
        (Param("keys", "Keys", Type.KEY_LIST, ["CTRL", "C"]),),
    ),
    BlockDefinition(
        "timing.wait",
        "timing",
        "Wait",
        (Param("seconds", "Seconds", Type.NUMBER, 1.0, minimum=0),),
    ),
    BlockDefinition(
        "control.repeat",
        "control",
        "Repeat",
        (Param("count", "Count", Type.INTEGER, 3, minimum=1),),
        is_container=True,
    ),
    BlockDefinition(
        "control.repeat_until_stopped",
        "control",
        "Repeat Until Stopped",
        is_container=True,
    ),
    BlockDefinition("control.stop", "control", "Stop Script", is_terminal=True),
    BlockDefinition(
        "variables.set",
        "variables",
        "Set Variable",
        (Param("name", "Name", Type.TEXT, "score"), Param("value", "Value", Type.VALUE, 0)),
    ),
    BlockDefinition(
        "variables.change",
        "variables",
        "Change Variable",
        (Param("name", "Name", Type.TEXT, "score"), Param("by", "By", Type.NUMBER, 1)),
    ),
    BlockDefinition(
        "events.hotkey",
        "events",
        "When Hotkey Pressed",
        (Param("hotkey", "Hotkey", Type.HOTKEY, "Ctrl+Alt+M"),),
        is_entry_point=True,
    ),
)


def create_default_registry() -> BlockRegistry:
    return BlockRegistry(CATEGORIES, BLOCKS)

