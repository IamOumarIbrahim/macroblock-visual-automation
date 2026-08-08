from macroblock.blocks import BlockInstance, ScriptGraph, create_default_registry


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

