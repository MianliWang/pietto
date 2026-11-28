"""Argparse parsers whose help, usage and errors are never coloured."""

from __future__ import annotations

import argparse
import sys
from typing import Any


class PlainArgumentParser(argparse.ArgumentParser):
    """An ArgumentParser that never colours its text or asks the terminal.

    From Python 3.14 argparse colours help and usage when PYTHON_COLORS,
    FORCE_COLOR or a terminal on stdout asks for it, and it asks even while
    it builds a parser, where a closed stdout raises ValueError. Pietto's
    help, usage and error text stays plain wherever it runs, so colour is
    off both for the parser and for its help formatter, which argparse
    builds with colour on before it applies the parser's. Subparsers share
    the class.
    """

    def __init__(self, **kwargs: Any) -> None:
        kwargs["formatter_class"] = _PlainHelpFormatter
        if sys.version_info >= (3, 14):
            kwargs["color"] = False
        super().__init__(**kwargs)


class _PlainHelpFormatter(argparse.HelpFormatter):
    def __init__(self, prog: str, **kwargs: Any) -> None:
        if sys.version_info >= (3, 14):
            kwargs["color"] = False
        super().__init__(prog, **kwargs)
