"""The parameter an argument of an inlined ``def`` call must fit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pietto.ast_nodes import Span

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class InlinedArgument:
    """One argument position of one inlined call: semantic inlining writes it
    on the argument expression, and typing checks the argument against it."""

    call: Span
    function: str
    position: int
    parameter: str
    type_name: str
    nullable: bool
