"""Semantic analysis entry point."""

from __future__ import annotations

from pietto.ast_nodes import Script
from pietto.semantic.model import CheckMode, SemanticModel, SemanticResult


def analyze(
    script: Script,
    *,
    mode_override: CheckMode | None = None,
) -> SemanticResult:
    """Create an initial semantic model without running semantic checks."""

    mode = mode_override or _mode_from_script(script)
    return SemanticResult(
        model=SemanticModel(mode=mode),
        diagnostics=(),
    )


def _mode_from_script(script: Script) -> CheckMode:
    """Select the declared mode or the checked default."""

    if script.header is None or script.header.mode is None:
        return CheckMode.CHECKED
    return CheckMode(script.header.mode)
