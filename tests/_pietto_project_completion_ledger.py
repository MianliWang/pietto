from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from pietto._project import check as project_check
from pietto._project import project_completion as completion
from pietto._project import project_grain
from pietto._project import project_ir_joins as joins
from pietto._project import project_ir_relational_properties as relational
from pietto._project import project_multifact as multifact
from pietto._project import project_phase62_verification as phase62
from pietto._project import project_relationship_uses as relationship_uses
from pietto._project import project_row_keys, project_value_fds
from pietto._project.model import (
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.project_ir import ProjectIRSnapshotScope
from pietto._project.project_ir_composition import (
    build_project_ir_project_plan,
)
from pietto._project.project_ir_construction import (
    ProjectIRAllocationState,
)
from pietto._project.project_ir_evaluation_context import (
    build_project_ir_evaluation_context_stage,
)
from pietto._project.project_ir_verification import (
    build_project_ir_analysis_bundle,
    verify_project_ir_stage,
)
from pietto._project.project_phase62_verification import (
    ProjectPhase62VerificationResult,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_completion.py"


def _project_files() -> dict[str, str]:
    return {
        "a.pietto": (
            'from "b.pietto" import query Public as JoinedInput\n'
            "shape LocalRow:\n"
            "    id: Int\n"
            'source local_rows: LocalRow = postgres.table("local_rows")\n'
            "query downstream_b:\n"
            "    from JoinedInput\n"
            "    select:\n"
            "        id\n"
            "query downstream_c:\n"
            "    from downstream_b\n"
            "    select:\n"
            "        id\n"
            "query unsupported_join:\n"
            "    from JoinedInput\n"
            "    let local = local_rows\n"
            "    inner join local\n"
            "    select:\n"
            "        id\n"
        ),
        "b.pietto": (
            'from "c.pietto" import query joined_a as Public\nexport query Public\n'
        ),
        "c.pietto": (
            "shape CustomerRow:\n"
            "    id: Int\n"
            "    customer_key = unique(id)\n"
            "shape OrderRow:\n"
            "    id: Int\n"
            "    customer_id: Int\n"
            "    amount: Int | None\n"
            "    order_key = unique(id)\n"
            'source customers: CustomerRow = postgres.table("customers")\n'
            'source orders: OrderRow = postgres.table("orders")\n'
            'source opaque = postgres.table("opaque")\n'
            "query plain:\n"
            "    from orders\n"
            "    select:\n"
            "        id\n"
            "relationship customer_orders(customer: CustomerRow, orders: OrderRow):\n"
            "    customer.id == orders.customer_id\n"
            "query joined_a:\n"
            "    from customers\n"
            "    let order_input = orders\n"
            "    inner join order_input on customer_orders(customers, order_input)\n"
            "    select:\n"
            "        id\n"
            "query repeated_join:\n"
            "    from customers\n"
            "    let first_orders = orders\n"
            "    inner join first_orders on customer_orders(customers, first_orders)\n"
            "    let second_orders = orders\n"
            "    inner join second_orders on customer_orders(customers, second_orders)\n"
            "    select:\n"
            "        id\n"
            "query computed_orders:\n"
            "    from orders\n"
            "    select:\n"
            "        customer_id\n"
            "        adjusted = amount + 1\n"
            "query lineage_blocked_join:\n"
            "    from customers\n"
            "    let computed = computed_orders\n"
            "    inner join computed on customers.id == computed.customer_id\n"
            "    select:\n"
            "        id\n"
            "query unknown_child:\n"
            "    from opaque\n"
            "    select:\n"
            "        id\n"
            "export query joined_a\n"
        ),
    }


def _semantic_project(
    root: Path,
    files: dict[str, str],
    *,
    reverse_creation: bool,
) -> ProjectSemanticResult:
    root.mkdir(parents=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    items = tuple(files.items())
    for path, source in items[::-1] if reverse_creation else items:
        (root / path).write_text(source, encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok, parsed.diagnostics
    semantic = build_empty_project_semantic_result(parsed)
    assert semantic.module_semantic_facts is not None
    assert semantic.module_attribution_facts is not None
    return semantic


def _phase62(semantic: ProjectSemanticResult) -> ProjectPhase62VerificationResult:
    row_keys = project_row_keys.build_project_row_keys(semantic)
    value_fds = project_value_fds.build_project_value_fds(row_keys)
    semantic_facts = semantic.module_semantic_facts
    attribution = semantic.module_attribution_facts
    assert semantic_facts is not None and attribution is not None
    plan = build_project_ir_project_plan(
        semantic_facts=semantic_facts,
        attribution=attribution,
        allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()),
    )
    evaluation = build_project_ir_evaluation_context_stage(plan)
    origins = project_grain.build_project_grain_origins(value_fds, evaluation)
    base_verification = verify_project_ir_stage(evaluation)
    base_relational = relational.build_project_ir_relational_property_stage(
        origins,
        build_project_ir_analysis_bundle(base_verification),
    )
    use_set = relationship_uses.build_project_relationship_uses(
        semantic, base_relational
    )
    join_stage = joins.build_project_ir_join_region(
        base_plan=plan,
        base_relational=base_relational,
        uses=use_set,
        allocation=plan.ending_allocation,
    )
    analysis = multifact.build_project_multifact_analysis(
        evaluation=evaluation,
        base_relational=base_relational,
        join_regions=join_stage,
    )
    return phase62.verify_project_phase62(analysis)


@dataclass(frozen=True, slots=True)
class _Built:
    semantic: ProjectSemanticResult
    verification: ProjectPhase62VerificationResult
    result: completion.ProjectCompletion
    reverse_result: completion.ProjectCompletion


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    root = tmp_path_factory.mktemp("p63s7")
    semantic = _semantic_project(
        root / "forward",
        _project_files(),
        reverse_creation=False,
    )
    verification = _phase62(semantic)
    result = completion.build_project_completion(verification)
    reverse_semantic = _semantic_project(
        root / "reverse",
        _project_files(),
        reverse_creation=True,
    )
    reverse_result = completion.build_project_completion(_phase62(reverse_semantic))
    return _Built(
        semantic=semantic,
        verification=verification,
        result=result,
        reverse_result=reverse_result,
    )


def _owner(
    result: completion.ProjectCompletion,
    module_path: str,
    name: str,
):
    matches = tuple(
        owner
        for owner in result.owners
        if owner.identity.module_path == module_path
        and owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _entry(
    result: completion.ProjectCompletion,
    module_path: str,
    name: str,
) -> completion.ProjectEffectiveOutputEntry:
    owner = _owner(result, module_path, name)
    matches = result.find_owner(owner)
    assert len(matches) == 1
    return matches[0]


def _coordinates(
    values: tuple,
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (item.identity.module_path, item.identity.declared_name) for item in values
    )
