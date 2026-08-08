"""Versioned, local-only `.mbk` document storage."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from macroblock.blocks import BlockRegistry, ScriptGraph
from macroblock.blocks.registry import BlockDefinitionError


class PersistenceError(RuntimeError):
    """A user-facing save/load failure that is safe to show in a dialog."""


def save_script(
    path: str | os.PathLike[str],
    graph: ScriptGraph,
    registry: BlockRegistry,
) -> Path:
    destination = Path(path)
    try:
        graph.validate(registry)
    except BlockDefinitionError as error:
        raise PersistenceError(f"Cannot save this script: {error}") from error

    temporary: Path | None = None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(graph.to_json())
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        temporary = None
    except OSError as error:
        raise PersistenceError(
            f"Could not save script to '{destination}': {error.strerror or error}."
        ) from error
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
    return destination


def load_script(
    path: str | os.PathLike[str], registry: BlockRegistry
) -> ScriptGraph:
    source = Path(path)
    try:
        payload = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        detail = getattr(error, "strerror", None) or str(error)
        raise PersistenceError(f"Could not read script '{source}': {detail}.") from error
    try:
        return ScriptGraph.from_json(payload, registry)
    except BlockDefinitionError as error:
        raise PersistenceError(f"Could not load script '{source}': {error}") from error

