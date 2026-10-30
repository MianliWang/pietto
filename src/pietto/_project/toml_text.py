"""The one tomllib boundary of project configurations and package manifests."""

from __future__ import annotations

import tomllib
from typing import Any


class TomlTextError(ValueError):
    """tomllib refused a text: it is not TOML that tomllib can load."""


def load_toml_text(text: str) -> dict[str, Any]:
    """Parse TOML text, raising TomlTextError for every refusal of its value.

    tomllib reports invalid TOML as TOMLDecodeError, but a decimal integer
    longer than ``sys.get_int_max_str_digits()`` digits as the plain
    ValueError of ``int()``, whose advice to call a Python function is cut.
    Nesting deeper than the recursion limit stays RecursionError: callers
    report it as a resource limit, as they do when their validation recurses
    over the same document.
    """

    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise TomlTextError(str(error)) from None
    except ValueError as error:
        raise TomlTextError(str(error).partition(";")[0]) from None
