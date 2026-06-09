"""Readonly public models produced by semantic analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping

from pietto.ast_nodes import Definition
from pietto.errors import Diagnostic


class CheckMode(StrEnum):
    """Semantic checking modes supported by Pietto."""

    LOOSE = "loose"
    CHECKED = "checked"
    STRICT = "strict"


def _readonly_namespace(
    values: Mapping[str, Definition] | None = None,
) -> Mapping[str, Definition]:
    """Copy namespace values into an immutable public mapping."""

    return MappingProxyType(dict(values or {}))


@dataclass(frozen=True, slots=True)
class SemanticModel:
    """Readonly semantic state built incrementally across Phase 2."""

    mode: CheckMode
    type_symbols: Mapping[str, Definition] = field(default_factory=_readonly_namespace)
    callable_symbols: Mapping[str, Definition] = field(
        default_factory=_readonly_namespace
    )
    relation_symbols: Mapping[str, Definition] = field(
        default_factory=_readonly_namespace
    )

    def __post_init__(self) -> None:
        """Copy namespace inputs into immutable public mappings."""

        object.__setattr__(self, "type_symbols", _readonly_namespace(self.type_symbols))
        object.__setattr__(
            self,
            "callable_symbols",
            _readonly_namespace(self.callable_symbols),
        )
        object.__setattr__(
            self,
            "relation_symbols",
            _readonly_namespace(self.relation_symbols),
        )


@dataclass(frozen=True, slots=True)
class SemanticResult:
    """A semantic model and its ordered diagnostics."""

    model: SemanticModel
    diagnostics: tuple[Diagnostic, ...]
