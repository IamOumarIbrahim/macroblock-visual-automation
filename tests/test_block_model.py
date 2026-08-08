import math

import pytest

from macroblock.blocks import BlockInstance, ScriptGraph, create_default_registry
from macroblock.blocks.registry import BlockDefinitionError


def test_block_graph_json_round_trip_is_identical() -> None:
    registry = create_default_registry()
    event = BlockInstance.create(
        registry,
        "events.hotkey",
        instance_id="b1",
        params={"hotkey": "Ctrl+Alt+M"},
        x=24,
        y=30,
    )
    repeat = BlockInstance.create(
        registry,
        "control.repeat",
        instance_id="b2",
        params={"count": 2},
        x=24,
        y=92,
    )
    move = BlockInstance.create(
        registry,
        "mouse.move_to",
        instance_id="b3",
        params={"x": 640, "y": 480},
        x=52,
        y=152,
    )
    wait = BlockInstance.create(
        registry,
        "timing.wait",
        instance_id="b4",
        params={"seconds": 0.25},
        x=52,
        y=212,
    )
    event.next_id = repeat.instance_id
    repeat.child_id = move.instance_id
    move.next_id = wait.instance_id

    original = ScriptGraph.from_blocks("Round Trip", [event, repeat, move, wait])
    original.validate(registry)
    restored = ScriptGraph.from_json(original.to_json(), registry)

    assert restored == original
    assert restored.to_dict() == original.to_dict()


def test_mutable_parameter_defaults_are_isolated_per_block() -> None:
    registry = create_default_registry()
    first = BlockInstance.create(registry, "keyboard.combo")
    second = BlockInstance.create(registry, "keyboard.combo")

    first.params["keys"].append("V")

    assert first.params["keys"] == ["CTRL", "C", "V"]
    assert second.params["keys"] == ["CTRL", "C"]
    assert registry.block("keyboard.combo").defaults()["keys"] == ["CTRL", "C"]


def test_graph_rejects_cycles_and_blocks_with_multiple_parents() -> None:
    registry = create_default_registry()
    first = BlockInstance.create(registry, "timing.wait", instance_id="first")
    second = BlockInstance.create(registry, "timing.wait", instance_id="second")
    first.next_id = second.instance_id
    second.next_id = first.instance_id
    with pytest.raises(BlockDefinitionError, match="cycle"):
        ScriptGraph.from_blocks("Cycle", [first, second]).validate(registry)

    first.next_id = None
    second.next_id = None
    third = BlockInstance.create(registry, "timing.wait", instance_id="third")
    first.next_id = third.instance_id
    second.next_id = third.instance_id
    with pytest.raises(BlockDefinitionError, match="multiple parents"):
        ScriptGraph.from_blocks("Two parents", [first, second, third]).validate(
            registry
        )


@pytest.mark.parametrize("coordinate", [math.nan, math.inf, -math.inf])
def test_graph_rejects_non_finite_positions(coordinate: float) -> None:
    registry = create_default_registry()
    block = BlockInstance.create(registry, "timing.wait")
    block.x = coordinate

    with pytest.raises(BlockDefinitionError, match="finite"):
        ScriptGraph.from_blocks("Bad position", [block]).validate(registry)


def test_parser_rejects_non_object_blocks_and_boolean_versions() -> None:
    registry = create_default_registry()
    with pytest.raises(BlockDefinitionError, match="index 0"):
        ScriptGraph.from_dict(
            {"version": 1, "name": "Bad block", "blocks": ["not a block"]},
            registry,
        )
    with pytest.raises(BlockDefinitionError, match="version"):
        ScriptGraph.from_dict(
            {"version": True, "name": "Bad version", "blocks": []}, registry
        )
