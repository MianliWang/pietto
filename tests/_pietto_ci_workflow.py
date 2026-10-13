"""Shared CI-workflow text fixtures."""

from __future__ import annotations

import re


def job(workflow: str, name: str) -> str:
    marker = f"  {name}:\n"
    assert workflow.count(marker) == 1
    return re.split(r"\n  [a-z_]+:\n", workflow.split(marker, 1)[1], maxsplit=1)[0]
