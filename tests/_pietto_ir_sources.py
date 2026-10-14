"""Shared Project IR source fixtures and bounded test oracles."""

from collections import Counter
from pathlib import Path

from _pietto_project_join import _source as _join_source
import pietto._project.project_ir as project_ir
import pietto._project.project_ir_construction as construction
import pietto._project.project_ir_pipeline as pipeline
from pietto._project import check as project_check
from pietto._project.project_final_outputs import (
    ProjectCompletedEffectiveOutput,
    ProjectCompletedSetOutput,
)
from pietto._project.model import (
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)


def set_source(
    operator: str = "union",
    quantifier: str = "all",
    *,
    right_type: str = "Int",
    operands: tuple[str, ...] = ("lhs", "rhs"),
    replay: bool = True,
) -> str:
    text = f"""shape Left:
    id: Int not null
shape Right:
    other: {right_type} nullable
source lhs: Left is postgres.table("lhs")
source rhs: Right is postgres.table("rhs")
table combined:
    {operator}{(" " + quantifier) if quantifier else ""}:
"""
    text += "".join(f"        from {name}\n" for name in operands)
    if replay:
        text += "query result:\n    from combined\n    select:\n        id\n"
    return text


def set_entry(completed, name: str = "combined"):
    entries = tuple(
        entry
        for entry in completed.effective_outputs.entries
        if entry.owner.definition.name == name
    )
    assert len(entries) == 1
    assert isinstance(
        entries[0], (ProjectCompletedSetOutput, ProjectCompletedEffectiveOutput)
    ), completed.diagnostics
    return entries[0]


SET_OPERATIONS = (
    ("union", "all"),
    ("union", "distinct"),
    ("intersect", "all"),
    ("intersect", "distinct"),
    ("except", "all"),
    ("except", "distinct"),
)


def bag_apply(kind: str, quantifier: str, left: Counter, right: Counter) -> Counter:
    """Independent bounded test oracle; production never evaluates these rows."""
    result = Counter()
    for row in left.keys() | right.keys():
        left_count, right_count = left[row], right[row]
        if kind == "union":
            count = (
                left_count + right_count
                if quantifier == "all"
                else int(left_count + right_count > 0)
            )
        elif kind == "intersect":
            count = (
                min(left_count, right_count)
                if quantifier == "all"
                else int(left_count > 0 and right_count > 0)
            )
        else:
            count = (
                max(left_count - right_count, 0)
                if quantifier == "all"
                else int(left_count > 0 and right_count == 0)
            )
        if count:
            result[row] = count
    return result


def distinct_source(type_name: str = "Int", *, distinct: bool = True) -> str:
    return f"""shape Row:
    value: {type_name} nullable
    hidden: Float nullable
source rows: Row is postgres.table("rows")
query result:
    from rows
    select{" distinct" if distinct else ""}:
        value
"""


def distinct_entry(completed, name="result") -> ProjectCompletedEffectiveOutput:
    matches = tuple(
        entry
        for entry in completed.effective_outputs.entries
        if entry.owner.definition.name == name
    )
    assert len(matches) == 1
    entry = matches[0]
    assert isinstance(entry, ProjectCompletedEffectiveOutput), (
        entry,
        completed.diagnostics,
    )
    return entry


def vertical_source(kind: str, side: str) -> str:
    source = _join_source("lhs.id == r.id", kind=kind)
    prepared = """table prepared:
    from rhs
    inner join lhs as x:
        from rhs
        on rhs.id == x.id
    select:
        id = rhs.id
"""
    source = source.replace("query result:\n", prepared + "query result:\n")
    head, query = source.split("query result:\n", 1)
    if side == "right":
        query = query.replace(f"{kind} join rhs as r:", f"{kind} join prepared as r:")
    else:
        query = query.replace("from lhs", "from prepared").replace(
            "lhs.id", "prepared.id"
        )
    return head + "query result:\n" + query


def decimal_source(mode: str, tmp_path: Path) -> str:
    if mode == "direct":
        return distinct_source("Decimal(10, 2)")
    if mode == "imported":
        (tmp_path / "types.pietto").write_text(
            "type Base = Decimal(10, 2)\nexport:\n    type Base\n"
        )
        (tmp_path / "facade.pietto").write_text(
            'import "types.pietto":\n    type Base as Public\nexport:\n    type Public\n'
        )
        return 'import "facade.pietto":\n    type Public as Alias\n' + distinct_source(
            "Alias"
        )
    source = "type Base = Decimal(10, 2)\ntype Alias = Base\n" + distinct_source(
        "Alias"
    )
    if mode in {"inherited", "repeated"}:
        source = source.replace("query result:", "table dedup:")
        source += (
            "table combined:\n    union all:\n        from dedup\n        from dedup\n"
        )
        source += (
            "query result:\n    from combined\n    select distinct:\n        value\n"
            if mode == "inherited"
            else "query result:\n    union all:\n        from combined\n        from combined\n"
        )
    return source


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice10-real-authored-multi-module-project-ir-e2e-v1.md"
)
SPEC_HEADINGS = (
    "Answer And Exact Owner",
    "Starting Authority",
    "Frozen Reader And Changed-path Closure",
    "Real-authored Semantic Entry And Exact Roots",
    "Explicit Allocation And One-way Pipeline",
    "Mandatory Independent Verification",
    "Complete E2E Result And Authority Continuity",
    "Real Multi-module Assurance Corpus",
    "Mixed Concrete And Non-concrete Project",
    "Canonical Observation And Bounded Determinism",
    "Privacy Compatibility And Non-goals",
    "Focused Assurance",
    "Slice 11 Handoff",
    "Gate Lifecycle And Publication",
)


def _project_files() -> dict[str, str]:
    return {
        "a.pietto": (
            'import "b.pietto":\n    table Public as Input\n'
            "query final:\n"
            "    from consumer\n"
            "    select:\n"
            "        id\n"
            "query consumer:\n"
            "    from Input\n"
            "    select:\n"
            "        id\n"
            "query second:\n"
            "    from Input\n"
            "    select:\n"
            "        id\n"
            "query full:\n"
            "    from Input\n"
            "    let:\n"
            "        floor = 0\n"
            "    where id > floor\n"
            "    group by:\n"
            "        category\n"
            "    select:\n"
            "        category\n"
            "        total = sum(amount)\n"
            "        ranking = row_number() window child\n"
            "    window child = base\n"
            "    window base:\n"
            "        partition by:\n"
            "            category\n"
            "        order by:\n"
            "            total desc\n"
            "    satisfying:\n"
            "        total > 0\n"
            "    order by:\n"
            "        ranking\n"
            "    limit 5\n"
            "query broken:\n"
            "    from Input\n"
            "    select:\n"
            "        missing\n"
        ),
        "b.pietto": (
            'import "c.pietto":\n    table projected as Public\n'
            "export:\n"
            "    table Public\n"
        ),
        "c.pietto": (
            "shape Row:\n"
            "    id: Int not null\n"
            "    amount: Int nullable\n"
            "    category: Text nullable\n"
            'source rows: Row is postgres.table("rows")\n'
            "table projected:\n"
            "    from rows\n"
            "    select:\n"
            "        id\n"
            "        amount\n"
            "        category\n"
            "export:\n"
            "    table projected\n"
        ),
        "d.pietto": (
            "shape Other:\n"
            "    key: Int not null\n"
            'source other: Other is postgres.table("other")\n'
            "query other_result:\n"
            "    from other\n"
            "    select:\n"
            "        key\n"
        ),
    }


def _semantic_project(root: Path) -> ProjectSemanticResult:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    for path, source in _project_files().items():
        (root / path).write_text(source, encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok
    semantic = build_empty_project_semantic_result(parsed)
    assert semantic.module_semantic_facts is not None
    assert semantic.module_attribution_facts is not None
    return semantic


def _allocation() -> construction.ProjectIRAllocationState:
    return construction.ProjectIRAllocationState(
        scope=project_ir.ProjectIRSnapshotScope()
    )


def _build(
    semantic: ProjectSemanticResult,
    allocation: construction.ProjectIRAllocationState | None = None,
) -> pipeline.ProjectIRPipelineResult:
    return pipeline.build_project_ir_pipeline(
        semantic_result=semantic,
        allocation=_allocation() if allocation is None else allocation,
    )


def _fragment(
    result: pipeline.ProjectIRPipelineResult,
    module_path: str,
    name: str,
) -> construction.ProjectIRSingleRelationFragment:
    matches = tuple(
        fragment
        for fragment in result.project_plan.fragments
        if fragment.semantic_facts.owner.identity.module_path == module_path
        and fragment.semantic_facts.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _concrete(
    result: pipeline.ProjectIRPipelineResult,
    module_path: str,
    name: str,
) -> construction.ProjectIRConcreteSingleRelationFragment:
    fragment = _fragment(result, module_path, name)
    assert type(fragment) is construction.ProjectIRConcreteSingleRelationFragment
    return fragment


def _edge(
    result: pipeline.ProjectIRPipelineResult,
    consumer: construction.ProjectIRConcreteSingleRelationFragment,
):
    matches = tuple(
        edge
        for edge in result.project_plan.cross_relation_edges
        if edge.consumer is consumer
    )
    assert len(matches) == 1
    return matches[0]
