"""The complete verifier bodies that the verification budget counts.

tests/test_project_verification_scope.py counts their runs inside one call,
and the ten-node profile of tests/_pietto_harness_performance.py counts them
per top-level call; both read them here, so neither imports a test module.
"""

from __future__ import annotations

from pietto._project import model
from pietto._project import project_compiled_verification as compiled_verification
from pietto._project import project_completed_semantics as completed_semantics
from pietto._project import project_guard_preparation as guard_preparation
from pietto._project import project_query_block_ir_verification as ir_verification
from pietto._project import project_sql_plan_requirements as requirements
from pietto._project import project_sql_plan_verification as plan_verification


def _body(module, private, public):
    """The complete check: the memo's private body, else today's public one."""
    return getattr(module, private, None) or getattr(module, public)


# The complete bodies the budget counts: the eight memoized structural checks
# plus the description and semantics checks they call. The binding-layer
# verifiers are not memoized; their nested compiled checks are memo hits.
BODIES = {
    "verify(root)": getattr(model, "_verify_compiled_input", None)
    or model.CompiledProjectInput.verify,
    "verify_description": compiled_verification.verify_description,
    "verify_compiled_semantics": completed_semantics.verify_compiled_semantics,
    "verify_compiled_query_block_ir": _body(
        ir_verification,
        "_verify_compiled_query_block_ir",
        "verify_compiled_query_block_ir",
    ),
    "verify_compiled_sql_plan": _body(
        plan_verification, "_verify_compiled_sql_plan", "verify_compiled_sql_plan"
    ),
    "verify_compiled_emission": _body(
        compiled_verification,
        "_verify_compiled_emission",
        "verify_compiled_emission",
    ),
    "verify_compiled_requirement_report": _body(
        requirements,
        "_verify_compiled_requirement_report",
        "verify_compiled_requirement_report",
    ),
    "verify_scope": _body(guard_preparation, "_verify_scope", "verify_scope"),
    "verify_preparation": _body(
        guard_preparation, "_verify_preparation", "verify_preparation"
    ),
    "verify_project_sql_plan": _body(
        plan_verification, "_verify_project_sql_plan", "_verify"
    ),
}
