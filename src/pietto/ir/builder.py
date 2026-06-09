"""Semantic IR construction entry point."""

from __future__ import annotations

from pietto.ast_nodes import Script
from pietto.ir.model import IrResult, ScriptIR
from pietto.semantic import SemanticModel


def build_ir(
    script: Script,
    semantic_model: SemanticModel,
) -> IrResult:
    """Build the minimal IR scaffold from an already analyzed script."""

    # Definition lowering starts in a later slice. Keep the inputs explicit so
    # this API cannot silently parse source or rerun semantic analysis.
    del script, semantic_model
    return IrResult(ir=ScriptIR(definitions=()), diagnostics=())
