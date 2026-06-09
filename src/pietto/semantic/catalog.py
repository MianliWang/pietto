"""Small explicit catalogs used by the incremental semantic checker."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

BUILTIN_TYPE_NAMES = frozenset(
    {
        "Any",
        "Bool",
        "Bytes",
        "Date",
        "Decimal",
        "Float",
        "Int",
        "Json",
        "Text",
        "Timestamp",
        "UUID",
    }
)


@dataclass(frozen=True, slots=True)
class BuiltinFunction:
    """One exact, non-overloaded built-in function signature."""

    name: str
    parameter_types: tuple[str, ...]
    return_type: str


BUILTIN_FUNCTIONS: Mapping[str, BuiltinFunction] = MappingProxyType(
    {
        function.name: function
        for function in (
            BuiltinFunction("lower", ("Text",), "Text"),
            BuiltinFunction("trim", ("Text",), "Text"),
            BuiltinFunction("len", ("Text",), "Int"),
            BuiltinFunction("matches", ("Text", "Text"), "Bool"),
        )
    }
)
