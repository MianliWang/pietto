"""Private source-preserving identities for parsed window-function calls."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__: tuple[str, ...] = ()


class WindowFunctionRole(StrEnum):
    """The syntactic role carried by a parsed window-function identity."""

    WINDOW_FUNCTION = "window_function"


@dataclass(frozen=True, slots=True)
class WindowFunctionIdentity:
    """A private, source-preserving window-function identity value."""

    namespace: tuple[str, ...]
    name: str
    role: WindowFunctionRole

    def __post_init__(self) -> None:
        """Reject malformed identity values without normalizing source text."""

        if type(self.namespace) is not tuple:
            raise TypeError("namespace must be an exact tuple")
        if any(type(component) is not str for component in self.namespace):
            raise TypeError("namespace components must be strings")
        if any(not component for component in self.namespace):
            raise ValueError("namespace components must be non-empty")
        if type(self.name) is not str:
            raise TypeError("name must be a string")
        if not self.name:
            raise ValueError("name must be non-empty")
        if type(self.role) is not WindowFunctionRole:
            raise TypeError("role must be a WindowFunctionRole")
