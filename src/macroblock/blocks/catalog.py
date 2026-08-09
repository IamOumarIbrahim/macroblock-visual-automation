"""Built-in category and block definitions."""

from __future__ import annotations

from macroblock.blocks.registry import (
    BlockDefinition,
    BlockRegistry,
    CategoryDefinition,
    FlowBehavior as Flow,
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
    CategoryDefinition("system", "System", "#0F766E"),
)

MOUSE_BUTTON_CHOICES = ("left", "right", "back", "forward", "middle")
MOUSE_BUTTON_LABELS = (
    "Left click",
    "Right click",
    "Previous (side button)",
    "Forward (side button)",
    "Scroll wheel click",
)


BLOCKS = (
    BlockDefinition(
        "mouse.move_to",
        "mouse",
        "Move Cursor To",
        (
            Param("x", "X", Type.INTEGER, 500),
            Param("y", "Y", Type.INTEGER, 300),
            Param("duration", "Move time", Type.NUMBER, 0.2, minimum=0),
        ),
    ),
    BlockDefinition(
        "mouse.click",
        "mouse",
        "Click",
        (
            Param(
                "button",
                "Button",
                Type.CHOICE,
                "left",
                MOUSE_BUTTON_CHOICES,
                choice_labels=MOUSE_BUTTON_LABELS,
            ),
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
        "mouse.move_by",
        "mouse",
        "Move Cursor By",
        (
            Param("dx", "X change", Type.INTEGER, 50),
            Param("dy", "Y change", Type.INTEGER, 0),
            Param("duration", "Move time", Type.NUMBER, 0.2, minimum=0),
        ),
    ),
    BlockDefinition(
        "mouse.button_down",
        "mouse",
        "Hold Mouse Button",
        (
            Param(
                "button",
                "Button",
                Type.CHOICE,
                "left",
                MOUSE_BUTTON_CHOICES,
                choice_labels=MOUSE_BUTTON_LABELS,
            ),
        ),
    ),
    BlockDefinition(
        "mouse.button_up",
        "mouse",
        "Release Mouse Button",
        (
            Param(
                "button",
                "Button",
                Type.CHOICE,
                "left",
                MOUSE_BUTTON_CHOICES,
                choice_labels=MOUSE_BUTTON_LABELS,
            ),
        ),
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
        "keyboard.key_down",
        "keyboard",
        "Hold Key",
        (Param("key", "Key", Type.TEXT, "SHIFT"),),
    ),
    BlockDefinition(
        "keyboard.key_up",
        "keyboard",
        "Release Key",
        (Param("key", "Key", Type.TEXT, "SHIFT"),),
    ),
    BlockDefinition(
        "timing.wait",
        "timing",
        "Wait",
        (Param("seconds", "Seconds", Type.NUMBER, 1.0, minimum=0),),
    ),
    BlockDefinition(
        "timing.random_wait",
        "timing",
        "Wait Random Duration",
        (
            Param("minimum", "Min seconds", Type.NUMBER, 0.5, minimum=0),
            Param("maximum", "Max seconds", Type.NUMBER, 2.0, minimum=0),
        ),
    ),
    BlockDefinition(
        "control.repeat",
        "control",
        "Repeat",
        (Param("count", "Count", Type.INTEGER, 3, minimum=1),),
        is_container=True,
        flow=Flow.REPEAT,
    ),
    BlockDefinition(
        "control.repeat_until_stopped",
        "control",
        "Repeat Until Stopped",
        is_container=True,
        flow=Flow.REPEAT_FOREVER,
    ),
    BlockDefinition(
        "control.stop", "control", "Stop Script", is_terminal=True, flow=Flow.STOP
    ),
    BlockDefinition(
        "control.if_variable_equals",
        "control",
        "If Variable Equals",
        (
            Param("name", "Variable", Type.TEXT, "score"),
            Param("value", "Equals", Type.VALUE, 1),
        ),
        is_container=True,
        flow=Flow.CONDITION,
    ),
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
        "variables.delete",
        "variables",
        "Delete Variable",
        (Param("name", "Name", Type.TEXT, "score"),),
    ),
    BlockDefinition(
        "events.start",
        "events",
        "When Script Starts",
        is_entry_point=True,
        flow=Flow.ENTRY,
    ),
    BlockDefinition(
        "events.hotkey",
        "events",
        "When Hotkey Pressed",
        (Param("hotkey", "Hotkey", Type.HOTKEY, "Ctrl+Alt+M"),),
        is_entry_point=True,
        flow=Flow.ENTRY,
    ),
    BlockDefinition(
        "events.wait_hotkey",
        "events",
        "Wait For Hotkey",
        (Param("hotkey", "Hotkey", Type.HOTKEY, "Ctrl+Shift+M"),),
    ),
    BlockDefinition(
        "events.wait_file",
        "events",
        "Wait Until File Exists",
        (
            Param("path", "File path", Type.TEXT, r"C:\Temp\ready.txt"),
            Param("poll_seconds", "Check every", Type.NUMBER, 0.25, minimum=0.05),
        ),
    ),
    BlockDefinition(
        "system.open_file",
        "system",
        "Open File or Folder",
        (Param("path", "Path", Type.TEXT, "C:\\"),),
    ),
    BlockDefinition(
        "system.open_url",
        "system",
        "Open URL",
        (Param("url", "URL", Type.TEXT, "https://example.com"),),
    ),
    BlockDefinition(
        "system.run_powershell",
        "system",
        "Run PowerShell Script",
        (
            Param(
                "script",
                "Script",
                Type.LONG_TEXT,
                'Write-Output "Hello from Macroblock"',
            ),
        ),
    ),
    BlockDefinition(
        "system.launch_program",
        "system",
        "Launch Program",
        (
            Param("path", "Program", Type.TEXT, "notepad.exe"),
            Param("arguments", "Arguments", Type.TEXT, ""),
        ),
    ),
)


def create_default_registry() -> BlockRegistry:
    return BlockRegistry(CATEGORIES, BLOCKS)
