import threading

import pytest

from macroblock.blocks import BlockInstance, ScriptGraph, create_default_registry
from macroblock.engine import ExecutionController, InputController, ScriptExecutor
from macroblock.engine import handlers as handler_module


class FakeInput:
    def __init__(self) -> None:
        self.actions = []

    def move_to(self, x, y):
        self.actions.append(("move", x, y))
        return True

    def click(self, button, count):
        self.actions.append(("click", button, count))

    def drag(self, x1, y1, x2, y2):
        self.actions.append(("drag", x1, y1, x2, y2))
        return True

    def scroll(self, amount):
        self.actions.append(("scroll", amount))

    def press_key(self, key):
        self.actions.append(("press", key))

    def type_text(self, text):
        self.actions.append(("type", text))

    def key_combo(self, keys):
        self.actions.append(("combo", keys))

    def move_by(self, dx, dy):
        self.actions.append(("move_by", dx, dy))
        return True

    def button_down(self, button):
        self.actions.append(("button_down", button))

    def button_up(self, button):
        self.actions.append(("button_up", button))

    def key_down(self, key):
        self.actions.append(("key_down", key))

    def key_up(self, key):
        self.actions.append(("key_up", key))

    def hotkey_is_down(self, hotkey):
        self.actions.append(("hotkey_check", hotkey))
        return True


def test_executor_walks_nested_graph_and_variables() -> None:
    registry = create_default_registry()
    event = BlockInstance.create(registry, "events.hotkey", instance_id="event")
    repeat = BlockInstance.create(
        registry, "control.repeat", instance_id="repeat", params={"count": 2}
    )
    move = BlockInstance.create(
        registry,
        "mouse.move_to",
        instance_id="move",
        params={"x": 20, "y": 30},
    )
    change = BlockInstance.create(
        registry,
        "variables.change",
        instance_id="change",
        params={"name": "runs", "by": 1},
    )
    event.next_id = repeat.instance_id
    repeat.child_id = move.instance_id
    move.next_id = change.instance_id
    graph = ScriptGraph.from_blocks("Executor", [event, repeat, move, change])
    fake = FakeInput()

    result = ScriptExecutor(registry, fake).execute(graph, threading.Event())

    assert result.status == "completed"
    assert result.variables == {"runs": 2}
    assert fake.actions == [
        ("hotkey_check", "Ctrl+Alt+M"),
        ("move", 20, 30),
        ("move", 20, 30),
    ]
    assert result.executed_blocks == 6


def test_executor_runs_recursively_nested_repeat_blocks() -> None:
    registry = create_default_registry()
    outer = BlockInstance.create(
        registry, "control.repeat", instance_id="outer", params={"count": 2}
    )
    inner = BlockInstance.create(
        registry, "control.repeat", instance_id="inner", params={"count": 3}
    )
    click = BlockInstance.create(
        registry, "mouse.click", instance_id="click"
    )
    outer.child_id = inner.instance_id
    inner.child_id = click.instance_id
    fake = FakeInput()

    result = ScriptExecutor(registry, fake).execute(
        ScriptGraph.from_blocks("Nested loops", [outer, inner, click]),
        threading.Event(),
    )

    assert result.status == "completed"
    assert fake.actions == [("click", "left", 1)] * 6


def test_change_variable_reports_a_clear_type_error() -> None:
    registry = create_default_registry()
    set_value = BlockInstance.create(
        registry,
        "variables.set",
        instance_id="set",
        params={"name": "score", "value": "many"},
    )
    change = BlockInstance.create(
        registry,
        "variables.change",
        instance_id="change",
        params={"name": "score", "by": 1},
    )
    set_value.next_id = change.instance_id

    with pytest.raises(ValueError, match="cannot be changed numerically"):
        ScriptExecutor(registry, FakeInput()).execute(
            ScriptGraph.from_blocks("Bad variable", [set_value, change]),
            threading.Event(),
        )


def test_new_mouse_keyboard_and_event_blocks_execute() -> None:
    registry = create_default_registry()
    blocks = [
        BlockInstance.create(
            registry,
            "mouse.move_by",
            instance_id="move_by",
            params={"dx": 12, "dy": -4},
        ),
        BlockInstance.create(
            registry,
            "mouse.button_down",
            instance_id="mouse_down",
            params={"button": "left"},
        ),
        BlockInstance.create(
            registry,
            "mouse.button_up",
            instance_id="mouse_up",
            params={"button": "left"},
        ),
        BlockInstance.create(
            registry,
            "keyboard.press",
            instance_id="press",
            params={"key": "A"},
        ),
        BlockInstance.create(
            registry,
            "keyboard.combo",
            instance_id="combo",
            params={"keys": ["CTRL", "A"]},
        ),
        BlockInstance.create(
            registry,
            "keyboard.type_text",
            instance_id="type",
            params={"text": "Hello"},
        ),
        BlockInstance.create(
            registry,
            "keyboard.key_down",
            instance_id="key_down",
            params={"key": "SHIFT"},
        ),
        BlockInstance.create(
            registry,
            "keyboard.key_up",
            instance_id="key_up",
            params={"key": "SHIFT"},
        ),
        BlockInstance.create(
            registry,
            "events.wait_hotkey",
            instance_id="hotkey",
            params={"hotkey": "Ctrl+Shift+M"},
        ),
    ]
    for current, following in zip(blocks, blocks[1:]):
        current.next_id = following.instance_id
    fake = FakeInput()

    result = ScriptExecutor(registry, fake).execute(
        ScriptGraph.from_blocks("New handlers", blocks), threading.Event()
    )

    assert result.status == "completed"
    assert fake.actions == [
        ("move_by", 12, -4),
        ("button_down", "left"),
        ("button_up", "left"),
        ("press", "A"),
        ("combo", ["CTRL", "A"]),
        ("type", "Hello"),
        ("key_down", "SHIFT"),
        ("key_up", "SHIFT"),
        ("hotkey_check", "Ctrl+Shift+M"),
    ]


def test_variable_condition_executes_only_when_equal() -> None:
    registry = create_default_registry()
    set_score = BlockInstance.create(
        registry,
        "variables.set",
        instance_id="set",
        params={"name": "score", "value": 3},
    )
    condition = BlockInstance.create(
        registry,
        "control.if_variable_equals",
        instance_id="condition",
        params={"name": "score", "value": 3},
    )
    click = BlockInstance.create(registry, "mouse.click", instance_id="click")
    set_score.next_id = condition.instance_id
    condition.child_id = click.instance_id
    fake = FakeInput()

    ScriptExecutor(registry, fake).execute(
        ScriptGraph.from_blocks("Condition", [set_score, condition, click]),
        threading.Event(),
    )

    assert fake.actions == [("click", "left", 1)]


def test_system_blocks_open_and_launch_with_editable_values(
    tmp_path, monkeypatch
) -> None:
    registry = create_default_registry()
    document = tmp_path / "document.txt"
    document.write_text("ready", encoding="utf-8")
    opened_files = []
    opened_urls = []
    launched = []

    monkeypatch.setattr(
        handler_module.os,
        "startfile",
        lambda path: opened_files.append(path),
        raising=False,
    )
    monkeypatch.setattr(
        handler_module.webbrowser,
        "open",
        lambda url, new=0: opened_urls.append((url, new)) or True,
    )

    class FakeProcess:
        returncode = 0

        def poll(self):
            return 0

    monkeypatch.setattr(
        handler_module.subprocess,
        "Popen",
        lambda args, **kwargs: launched.append((args, kwargs)) or FakeProcess(),
    )

    blocks = [
        BlockInstance.create(
            registry,
            "system.open_file",
            instance_id="file",
            params={"path": str(document)},
        ),
        BlockInstance.create(
            registry,
            "system.open_url",
            instance_id="url",
            params={"url": "example.com/docs"},
        ),
        BlockInstance.create(
            registry,
            "system.run_powershell",
            instance_id="shell",
            params={"script": "Write-Output 'ok'"},
        ),
        BlockInstance.create(
            registry,
            "system.launch_program",
            instance_id="program",
            params={"path": "notepad.exe", "arguments": '"notes.txt"'},
        ),
    ]
    for current, following in zip(blocks, blocks[1:]):
        current.next_id = following.instance_id

    result = ScriptExecutor(registry, FakeInput()).execute(
        ScriptGraph.from_blocks("System", blocks), threading.Event()
    )

    assert result.status == "completed"
    assert opened_files == [str(document)]
    assert opened_urls == [("https://example.com/docs", 2)]
    assert launched[0][0][:4] == [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
    ]
    assert launched[1][0][0] == "notepad.exe"


def test_controller_refuses_to_run_without_ready_abort_monitor() -> None:
    registry = create_default_registry()
    wait = BlockInstance.create(
        registry, "timing.wait", params={"seconds": 0.01}
    )
    graph = ScriptGraph.from_blocks("Safety", [wait])

    class NotReadyMonitor:
        def __init__(self, _abort_event):
            self.ready_event = threading.Event()
            self.is_ready = False

        def start(self):
            self.ready_event.set()

        def stop(self):
            pass

    controller = ExecutionController(
        registry,
        input_controller=FakeInput(),
        monitor_factory=NotReadyMonitor,
    )
    with pytest.raises(RuntimeError, match="abort hotkey"):
        controller.start(graph)
    assert not controller.is_running


def test_outside_monitor_coordinate_is_skipped_and_logged(caplog) -> None:
    input_controller = InputController()
    with caplog.at_level("WARNING"):
        moved = input_controller.move_to(2_000_000_000, 2_000_000_000)
    assert moved is False
    assert "outside every connected monitor" in caplog.text


def test_win32_key_resolution_supports_letters_digits_and_hotkeys() -> None:
    controller = InputController.__new__(InputController)

    class FakeUser32:
        @staticmethod
        def VkKeyScanW(value):
            return ord(value)

        @staticmethod
        def GetAsyncKeyState(_value):
            return 0x8000

    controller.user32 = FakeUser32()

    assert controller.resolve_key("A") == 0x41
    assert controller.resolve_key("z") == 0x5A
    assert controller.resolve_key("7") == 0x37
    assert controller.resolve_key("F12") == 0x7B
    assert controller.resolve_key("Arrow Up") == 0x26
    assert controller.hotkey_is_down("Ctrl + A") is True
