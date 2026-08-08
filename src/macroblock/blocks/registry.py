"""Definitions and registry for Macroblock's extensible block catalog."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Iterable, Mapping


class BlockDefinitionError(ValueError):
    """Raised when a block or parameter definition is invalid."""


class UnknownBlockTypeError(BlockDefinitionError):
    """Raised when a document references a block type not in the registry."""


class ParameterType(str, Enum):
    INTEGER = "integer"
    NUMBER = "number"
    TEXT = "text"
    CHOICE = "choice"
    KEY_LIST = "key_list"
    HOTKEY = "hotkey"
    VALUE = "value"


@dataclass(frozen=True, slots=True)
class ParameterDefinition:
    id: str
    label: str
    type: ParameterType
    default: Any
    choices: tuple[str, ...] = ()
    minimum: float | None = None

    def validate(self, value: Any) -> None:
        if self.type is ParameterType.INTEGER:
            valid = isinstance(value, int) and not isinstance(value, bool)
        elif self.type is ParameterType.NUMBER:
            valid = isinstance(value, (int, float)) and not isinstance(value, bool)
        elif self.type in (ParameterType.TEXT, ParameterType.HOTKEY):
            valid = isinstance(value, str)
        elif self.type is ParameterType.CHOICE:
            valid = isinstance(value, str) and value in self.choices
        elif self.type is ParameterType.KEY_LIST:
            valid = (
                isinstance(value, list)
                and all(isinstance(item, str) and item for item in value)
            )
        else:
            valid = value is None or isinstance(value, (str, int, float, bool))

        if not valid:
            raise BlockDefinitionError(
                f"Parameter '{self.id}' expects {self.type.value}, got {value!r}."
            )
        if (
            self.minimum is not None
            and isinstance(value, (int, float))
            and value < self.minimum
        ):
            raise BlockDefinitionError(
                f"Parameter '{self.id}' must be at least {self.minimum}."
            )


@dataclass(frozen=True, slots=True)
class CategoryDefinition:
    id: str
    label: str
    color: str


@dataclass(frozen=True, slots=True)
class BlockDefinition:
    id: str
    category: str
    display_label: str
    parameters: tuple[ParameterDefinition, ...] = ()
    color: str = ""
    is_container: bool = False
    is_entry_point: bool = False
    is_terminal: bool = False

    def defaults(self) -> dict[str, Any]:
        return {parameter.id: parameter.default for parameter in self.parameters}

    def validate_params(self, params: Mapping[str, Any]) -> None:
        expected = {parameter.id for parameter in self.parameters}
        supplied = set(params)
        if missing := expected - supplied:
            raise BlockDefinitionError(
                f"Block '{self.id}' is missing parameters: {', '.join(sorted(missing))}."
            )
        if extra := supplied - expected:
            raise BlockDefinitionError(
                f"Block '{self.id}' has unknown parameters: {', '.join(sorted(extra))}."
            )
        for parameter in self.parameters:
            parameter.validate(params[parameter.id])


class BlockRegistry:
    """Holds all category and block metadata used by UI and execution."""

    def __init__(
        self,
        categories: Iterable[CategoryDefinition] = (),
        blocks: Iterable[BlockDefinition] = (),
    ) -> None:
        self._categories: dict[str, CategoryDefinition] = {}
        self._blocks: dict[str, BlockDefinition] = {}
        for category in categories:
            self.register_category(category)
        for block in blocks:
            self.register_block(block)

    @property
    def categories(self) -> tuple[CategoryDefinition, ...]:
        return tuple(self._categories.values())

    @property
    def blocks(self) -> tuple[BlockDefinition, ...]:
        return tuple(self._blocks.values())

    def register_category(self, category: CategoryDefinition) -> None:
        if category.id in self._categories:
            raise BlockDefinitionError(f"Duplicate category id '{category.id}'.")
        self._categories[category.id] = category

    def register_block(self, block: BlockDefinition) -> None:
        if block.id in self._blocks:
            raise BlockDefinitionError(f"Duplicate block id '{block.id}'.")
        try:
            category = self._categories[block.category]
        except KeyError as error:
            raise BlockDefinitionError(
                f"Block '{block.id}' uses unknown category '{block.category}'."
            ) from error
        registered = replace(block, color=category.color)
        registered.validate_params(registered.defaults())
        self._blocks[registered.id] = registered

    def category(self, category_id: str) -> CategoryDefinition:
        try:
            return self._categories[category_id]
        except KeyError as error:
            raise BlockDefinitionError(f"Unknown category '{category_id}'.") from error

    def block(self, type_id: str) -> BlockDefinition:
        try:
            return self._blocks[type_id]
        except KeyError as error:
            raise UnknownBlockTypeError(
                f"Unknown block type '{type_id}'. This script may require a newer "
                "or different version of Macroblock."
            ) from error

    def blocks_for_category(self, category_id: str) -> tuple[BlockDefinition, ...]:
        return tuple(block for block in self.blocks if block.category == category_id)

