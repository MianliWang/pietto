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
    """One closed scalar built-in function signature."""

    name: str
    parameter_types: tuple[str, ...]
    return_type: str


BUILTIN_FUNCTIONS: Mapping[str, BuiltinFunction] = MappingProxyType(
    {
        function.name: function
        for function in (
            BuiltinFunction("lower", ("Text",), "Text"),
            BuiltinFunction("upper", ("Text",), "Text"),
            BuiltinFunction("trim", ("Text",), "Text"),
            BuiltinFunction("len", ("Text",), "Int"),
            BuiltinFunction("substr", ("Text", "Int", "Int"), "Text"),
            BuiltinFunction("replace", ("Text", "Text", "Text"), "Text"),
            BuiltinFunction("contains", ("Text", "Text"), "Bool"),
            BuiltinFunction("starts_with", ("Text", "Text"), "Bool"),
            BuiltinFunction("ends_with", ("Text", "Text"), "Bool"),
            BuiltinFunction("abs", ("Decimal",), "Decimal"),
            BuiltinFunction("date_of", ("Timestamp",), "Date"),
            BuiltinFunction("hour", ("Timestamp",), "Int"),
            BuiltinFunction("minute", ("Timestamp",), "Int"),
            BuiltinFunction("matches", ("Text", "Text"), "Bool"),
        )
    }
)

# These forms have closed semantic rules but cannot be represented by the
# fixed-arity, exact-type signature record above.
SPECIAL_BUILTIN_FUNCTION_NAMES = frozenset(
    {"coalesce", "nullif", "sign", "year", "month", "day", "round", "date_trunc"}
)


def is_builtin_function_name(name: str) -> bool:
    """Return whether ``name`` is admitted by the closed scalar catalog."""

    return name in BUILTIN_FUNCTIONS or name in SPECIAL_BUILTIN_FUNCTION_NAMES
