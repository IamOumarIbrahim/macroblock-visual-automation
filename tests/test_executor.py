import threading

import pytest

from macroblock.blocks import BlockInstance, ScriptGraph, create_default_registry
from macroblock.engine import ExecutionController, InputController, ScriptExecutor


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
    assert fake.actions == [("move", 20, 30), ("move", 20, 30)]
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
