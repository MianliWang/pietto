"""plot_line and plot_scatter: two admitted fields as float64 on the caller's Axes."""

from __future__ import annotations

from typing import Any

# The kinds plot_line and plot_scatter admit, and those they admit nullable
# too (D80.03).
ADMITS = ("Int", "Float")
NULLABLE: tuple[str, ...] = ()


def _float64(data: Any, ordinal: int) -> Any:
    # Admission left a non-nullable Float field or an Int field whose values
    # all lie within ±2**53, which float64 holds exactly; astype copies.
    return data.column(ordinal).to_numpy(zero_copy_only=False).astype("float64")


def line(data: Any, x: int, y: int, ax: Any) -> Any:
    (artist,) = ax.plot(_float64(data, x), _float64(data, y))
    return artist


def scatter(data: Any, x: int, y: int, ax: Any) -> Any:
    return ax.scatter(_float64(data, x), _float64(data, y))
