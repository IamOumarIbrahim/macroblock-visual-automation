import json

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication, QMessageBox

from macroblock.blocks import BlockInstance, ScriptGraph, create_default_registry
from macroblock.persistence import PersistenceError, load_script, save_script
from macroblock.ui.main_window import MainWindow


def test_mbk_save_and_load_exact_round_trip(tmp_path) -> None:
    registry = create_default_registry()
    move = BlockInstance.create(
        registry,
        "mouse.move_to",
        instance_id="b1",
        params={"x": 500, "y": 300},
        x=20,
        y=30,
    )
    click = BlockInstance.create(
        registry,
        "mouse.click",
        instance_id="b2",
        params={"button": "left", "count": 1},
        x=20,
        y=110,
    )
    move.next_id = click.instance_id
    graph = ScriptGraph.from_blocks("Example Script", [move, click])
    path = tmp_path / "example.mbk"

    save_script(path, graph, registry)
    restored = load_script(path, registry)

    assert restored == graph
    assert json.loads(path.read_text(encoding="utf-8")) == graph.to_dict()


def test_corrupted_and_unknown_block_files_name_the_problem(tmp_path) -> None:
    registry = create_default_registry()
    corrupt = tmp_path / "corrupt.mbk"
    corrupt.write_text('{"version": 1, broken', encoding="utf-8")
    with pytest.raises(PersistenceError, match="Invalid script JSON at line"):
        load_script(corrupt, registry)

    unknown = tmp_path / "unknown.mbk"
    unknown.write_text(
        json.dumps(
            {
                "version": 1,
                "name": "Future",
                "blocks": [
                    {"id": "x", "type": "future.teleport", "params": {}, "next": None}
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(PersistenceError, match="future.teleport"):
        load_script(unknown, registry)


def test_ui_load_failure_shows_dialog_instead_of_raising(tmp_path, monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    bad = tmp_path / "bad.mbk"
    bad.write_text("not json", encoding="utf-8")
    messages = []
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda _parent, title, message: messages.append((title, message)),
    )
    window = MainWindow()

    assert window.load_script_path(bad) is False
    assert messages and messages[0][0] == "Unable to load script"
    assert "Invalid script JSON" in messages[0][1]
    window.close()

