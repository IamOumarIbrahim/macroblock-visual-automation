"""Serializable instances and graph structure for visual programs."""

from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping
from uuid import uuid4

from macroblock.blocks.registry import BlockDefinitionError, BlockRegistry


@dataclass(slots=True)
class BlockInstance:
    type_id: str
    params: dict[str, Any]
    instance_id: str = field(default_factory=lambda: uuid4().hex)
    next_id: str | None = None
    child_id: str | None = None
    x: float = 0.0
    y: float = 0.0

    @classmethod
    def create(
        cls,
        registry: BlockRegistry,
        type_id: str,
        *,
        instance_id: str | None = None,
        params: Mapping[str, Any] | None = None,
        x: float = 0.0,
        y: float = 0.0,
    ) -> "BlockInstance":
        definition = registry.block(type_id)
        values = definition.defaults()
        if params:
            values.update(copy.deepcopy(dict(params)))
        definition.validate_params(values)
        return cls(type_id, values, instance_id or uuid4().hex, x=x, y=y)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.instance_id,
            "type": self.type_id,
            "params": self.params,
            "next": self.next_id,
        }
        if self.child_id is not None:
            data["child"] = self.child_id
        if self.x or self.y:
            data["position"] = {"x": self.x, "y": self.y}
        return data

    @classmethod
    def from_dict(
        cls, data: Mapping[str, Any], registry: BlockRegistry
    ) -> "BlockInstance":
        try:
            type_id = data["type"]
            instance_id = data["id"]
            params = data["params"]
        except KeyError as error:
            raise BlockDefinitionError(
                f"Block is missing required field '{error.args[0]}'."
            ) from error
        if not isinstance(type_id, str) or not isinstance(instance_id, str):
            raise BlockDefinitionError("Block id and type must be strings.")
        if not isinstance(params, dict):
            raise BlockDefinitionError(f"Block '{instance_id}' params must be an object.")
        position = data.get("position", {})
        if not isinstance(position, dict):
            raise BlockDefinitionError(f"Block '{instance_id}' position must be an object.")
        try:
            x = float(position.get("x", 0.0))
            y = float(position.get("y", 0.0))
        except (TypeError, ValueError) as error:
            raise BlockDefinitionError(
                f"Block '{instance_id}' position coordinates must be numbers."
            ) from error
        if not math.isfinite(x) or not math.isfinite(y):
            raise BlockDefinitionError(
                f"Block '{instance_id}' position coordinates must be finite."
            )
        block = cls.create(
            registry,
            type_id,
            instance_id=instance_id,
            params=params,
            x=x,
            y=y,
        )
        for key, attr in (("next", "next_id"), ("child", "child_id")):
            reference = data.get(key)
            if reference is not None and not isinstance(reference, str):
                raise BlockDefinitionError(
                    f"Block '{instance_id}' field '{key}' must be a block id or null."
                )
            setattr(block, attr, reference)
        return block


@dataclass(slots=True)
class ScriptGraph:
    name: str = "Untitled Script"
    blocks: list[BlockInstance] = field(default_factory=list)
    version: int = 1

    def add(self, block: BlockInstance) -> None:
        if any(existing.instance_id == block.instance_id for existing in self.blocks):
            raise BlockDefinitionError(f"Duplicate block id '{block.instance_id}'.")
        self.blocks.append(block)

    def block_map(self) -> dict[str, BlockInstance]:
        return {block.instance_id: block for block in self.blocks}

    def validate(self, registry: BlockRegistry) -> None:
        if (
            not isinstance(self.version, int)
            or isinstance(self.version, bool)
            or self.version != 1
        ):
            raise BlockDefinitionError(
                f"Unsupported script version {self.version}; this app supports version 1."
            )
        if not isinstance(self.name, str):
            raise BlockDefinitionError("Script name must be a string.")
        for block in self.blocks:
            if not isinstance(block.instance_id, str) or not block.instance_id:
                raise BlockDefinitionError("Every block must have a non-empty string id.")
            if not isinstance(block.params, Mapping):
                raise BlockDefinitionError(
                    f"Block '{block.instance_id}' params must be an object."
                )
            if (
                isinstance(block.x, bool)
                or isinstance(block.y, bool)
                or not isinstance(block.x, (int, float))
                or not isinstance(block.y, (int, float))
                or not math.isfinite(block.x)
                or not math.isfinite(block.y)
            ):
                raise BlockDefinitionError(
                    f"Block '{block.instance_id}' position coordinates must be finite numbers."
                )
        ids = [block.instance_id for block in self.blocks]
        if len(ids) != len(set(ids)):
            raise BlockDefinitionError("Script contains duplicate block ids.")
        known = set(ids)
        incoming: dict[str, tuple[str, str]] = {}
        for block in self.blocks:
            definition = registry.block(block.type_id)
            definition.validate_params(block.params)
            if block.child_id is not None and not definition.is_container:
                raise BlockDefinitionError(
                    f"Block '{block.instance_id}' cannot contain child blocks."
                )
            for label, reference in (("next", block.next_id), ("child", block.child_id)):
                if reference is not None and not isinstance(reference, str):
                    raise BlockDefinitionError(
                        f"Block '{block.instance_id}' field '{label}' must be a block id or null."
                    )
                if reference is not None and reference not in known:
                    raise BlockDefinitionError(
                        f"Block '{block.instance_id}' has missing {label} block '{reference}'."
                    )
                if reference is not None:
                    if previous := incoming.get(reference):
                        raise BlockDefinitionError(
                            f"Block '{reference}' has multiple parents: "
                            f"'{previous[0]}' ({previous[1]}) and "
                            f"'{block.instance_id}' ({label})."
                        )
                    incoming[reference] = (block.instance_id, label)

        blocks = self.block_map()
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(block_id: str) -> None:
            if block_id in visiting:
                raise BlockDefinitionError(
                    f"Script contains a connection cycle at block '{block_id}'."
                )
            if block_id in visited:
                return
            visiting.add(block_id)
            block = blocks[block_id]
            for reference in (block.child_id, block.next_id):
                if reference is not None:
                    visit(reference)
            visiting.remove(block_id)
            visited.add(block_id)

        for block_id in ids:
            visit(block_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "name": self.name,
            "blocks": [block.to_dict() for block in self.blocks],
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(
        cls, data: Mapping[str, Any], registry: BlockRegistry
    ) -> "ScriptGraph":
        if not isinstance(data, Mapping):
            raise BlockDefinitionError("Script document must be a JSON object.")
        version = data.get("version")
        name = data.get("name")
        raw_blocks = data.get("blocks")
        if (
            not isinstance(version, int)
            or isinstance(version, bool)
            or not isinstance(name, str)
        ):
            raise BlockDefinitionError("Script version must be an integer and name a string.")
        if not isinstance(raw_blocks, list):
            raise BlockDefinitionError("Script blocks must be a list.")
        blocks = []
        for index, item in enumerate(raw_blocks):
            if not isinstance(item, Mapping):
                raise BlockDefinitionError(
                    f"Script block at index {index} must be a JSON object."
                )
            blocks.append(BlockInstance.from_dict(item, registry))
        graph = cls(name=name, blocks=blocks, version=version)
        graph.validate(registry)
        return graph

    @classmethod
    def from_json(cls, payload: str, registry: BlockRegistry) -> "ScriptGraph":
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as error:
            raise BlockDefinitionError(
                f"Invalid script JSON at line {error.lineno}, column {error.colno}: {error.msg}."
            ) from error
        return cls.from_dict(data, registry)

    @classmethod
    def from_blocks(
        cls, name: str, blocks: Iterable[BlockInstance]
    ) -> "ScriptGraph":
        return cls(name=name, blocks=list(blocks))
