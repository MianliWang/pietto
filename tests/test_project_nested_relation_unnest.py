"""Unnest binding (S05): each Unnest let of a declaration body is its own
catalog occurrence that its one JOIN binds by identity; its argument, its
uses and its place are admitted or refused, before lowering exists."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from pietto._project import (
    project_query_block_ir_inspection,
    project_sql_emission_portable,
)
from pietto._project.check import check_project_parse_only
from pietto._project.model import (
    ProjectModuleRowFieldKind,
    ProjectParseCheckResult,
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowSchema,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
    project_declaration_occurrence_identity,
)
from pietto._project.module_catalog import (
    ProjectDeclarationOccurrence,
    _build_project_module_catalog_set,
)
from pietto._project.module_semantic_fact_preservation import unnest_field_diagnostic
from pietto._project.project_completed_semantics import (
    build_project_completed_semantic_result,
)
from pietto._project.project_current_joins import current_forward_at_most_one
from pietto._project.project_ir import ProjectIRSnapshotScope
from pietto._project.project_ir_construction import ProjectIRAllocationState
from pietto._project.project_ir_pipeline import build_project_ir_pipeline
from pietto._project.project_ir_composition import build_project_ir_project_plan
from pietto._project.project_ir_evaluation_context import (
    build_project_ir_evaluation_context_stage,
)
from pietto._project.project_ir_verification import (
    ProjectIRVerificationStatus,
    verify_project_ir_stage,
)
from pietto._project.project_joined_row_filter import ProjectJoinedRowFilterKind
from pietto.ast_nodes import (
    AuthoredJoinKind,
    BlockRelationDef,
    ModuleDeclarationKind,
    QueryDef,
    SelectBody,
    UnnestRelationDef,
)
from pietto.cli import main as cli_main

# Twenty lines, as in the Gate-1 probes: the Collect read is 20:18, so a
# body's first line is 22, its Unnest let usually 23 (argument 23:20) and its
# JOIN 24.
HEAD = """shape Customer:
    id: Int
    name: Text
shape Order:
    id: Int
    customer_id: Int
    total: Int
source customers: Customer = postgres.table("customers")
source orders: Order = postgres.table("orders")
query parent:
    let all_orders:
        from orders
        select:
            id
            total
        order by id
    from customers
    select:
        id
        nested = collect all_orders
"""
# Completion builds the row of a producer with an authored JOIN, a set or a
# table function; its Collect output is typed before it, its other fields
# against the completed row.
JOINED_HEAD = HEAD.replace(
    "    from customers\n",
    "    from customers\n    let c2 = customers\n"
    "    inner join c2 on customers.id == c2.id\n",
).replace("        id\n        nested", "        id = customers.id\n        nested")


def _query(*lines: str, name: str = "expanded") -> str:
    return f"query {name}:\n" + "".join(f"    {line}\n" for line in lines)


def _root(tmp_path: Path, sources: dict[str, str]) -> Path:
    root = tmp_path / "project"
    root.mkdir(parents=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    for name, source in sources.items():
        (root / name).write_text(source, encoding="utf-8")
    return root


def _parsed(tmp_path: Path, source: str) -> ProjectParseCheckResult:
    return check_project_parse_only(_root(tmp_path, {"main.pietto": source}))


def _semantic(tmp_path: Path, source: str) -> ProjectSemanticResult:
    parsed = _parsed(tmp_path, source)
    assert parsed.ok, parsed.diagnostics
    return build_empty_project_semantic_result(parsed)


_Checked = list[tuple[str, int, int, str, str | None]]


def _checked(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, sources: dict[str, str]
) -> _Checked:
    """The complete ordered diagnostics of `pietto check --project`."""

    root = _root(tmp_path, sources)
    code = cli_main(["check", "--project", str(root), "--format", "json"])
    document = json.loads(capsys.readouterr().out)
    assert code == (1 if document["diagnostics"] else 0)
    return [
        (
            item["code"],
            item["location"]["line"],
            item["location"]["column"],
            item["message"],
            item["suggestion"],
        )
        for item in document["diagnostics"]
    ]


def _located(items: _Checked) -> list[tuple[str, int, int, str]]:
    return [(code, line, column, message) for code, line, column, message, _ in items]


def _completed(semantic: ProjectSemanticResult) -> Any:
    return build_project_completed_semantic_result(semantic)


def _region(completed: Any, name: str = "expanded") -> Any:
    (region,) = (
        region
        for region in completed.roots.effective_outputs.current_regions
        if region.ledger.owner.identity.declared_name == name
    )
    return region


def _unnest_entry(completed: Any, name: str = "o") -> Any:
    (entry,) = (
        entry
        for entry in completed.roots.effective_outputs.entries
        if entry.owner.unnest is not None and entry.owner.identity.declared_name == name
    )
    return entry


# --- AC-01: catalog occurrences and identity ---


def test_each_declaration_unnest_is_one_catalog_occurrence_in_source_order(
    tmp_path: Path,
) -> None:
    source = (
        HEAD
        + _query(
            "from parent",
            "let o = unnest(parent.nested)",
            "cross join o",
            "select:",
            "    id = parent.id",
            name="first",
        )
        + "query second:\n"
        "    let inner_rows:\n"
        "        from parent\n"
        "        let hidden = unnest(parent.nested)\n"
        "        cross join hidden\n"
        "        select:\n"
        "            t = hidden.total\n"
        "    from parent\n"
        "    let c = customers\n"
        "    inner join c on parent.id == c.id\n"
        "    let o = unnest(parent.nested)\n"
        "    left join o on True\n"
        "    select:\n"
        "        id = parent.id\n"
    )
    parsed = _parsed(tmp_path, source)
    # The relation let's Unnest is refused alone (PIE-S2807 L): it has no
    # occurrence.
    assert [(d.code, d.location.line) for d in parsed.diagnostics] == [
        ("PIE-S2807", 30)
    ]
    (catalog,) = _build_project_module_catalog_set(parsed.modules).catalogs
    script = parsed.parsed_inputs[0].authored_script or parsed.parsed_inputs[0].script
    first, second = script.definitions[-2:]
    assert isinstance(first, QueryDef) and isinstance(second, BlockRelationDef)
    assert isinstance(second.body, SelectBody)
    assert [
        (o.declaration_position, o.unnest_position, o.identity.declared_name)
        for o in catalog.unnests
    ] == [(5, 0, "o"), (6, 1, "o")]
    assert catalog.unnests[0].unnest is first.naming_declarations[0]
    assert catalog.unnests[1].unnest is second.body.naming_declarations[1]
    for occurrence in catalog.unnests:
        definition = occurrence.definition
        assert type(definition) is UnnestRelationDef
        assert definition.source is occurrence.unnest is occurrence.authored
        assert definition.kind is ModuleDeclarationKind.QUERY
        assert occurrence.block_local and occurrence.let_position is None
        assert occurrence not in catalog.occurrences
    # Each Unnest occurrence comes right before the declaration that writes
    # it among the relation owners.
    owners = catalog.relation_owners
    for occurrence in catalog.unnests:
        position = next(i for i, o in enumerate(owners) if o is occurrence)
        reader = owners[position + 1]
        assert not reader.block_local
        assert reader.declaration_position == occurrence.declaration_position
    with pytest.raises(ValueError, match="every Unnest let"):
        replace(catalog, unnests=catalog.unnests[:1])
    with pytest.raises(ValueError, match="must match their lets"):
        replace(catalog, unnests=catalog.unnests[::-1])


def test_the_unnest_view_and_its_occurrence_keep_their_exact_let(
    tmp_path: Path,
) -> None:
    semantic = _semantic(
        tmp_path,
        HEAD
        + _query("from parent", "let o = unnest(parent.nested)", "cross join o")
        + "    select:\n        id = parent.id\n",
    )
    assert semantic.module_catalogs is not None
    ((occurrence,),) = (c.unnests for c in semantic.module_catalogs.catalogs)
    let = occurrence.unnest
    assert let is not None
    with pytest.raises(TypeError, match="exact let"):
        UnnestRelationDef(
            span=let.span, name="other", kind=ModuleDeclarationKind.QUERY, source=let
        )
    with pytest.raises(ValueError, match="exact let"):
        replace(occurrence, unnest_position=None)
    with pytest.raises(ValueError, match="exact let"):
        replace(occurrence, let_position=0)
    other = replace(let, name="o")
    with pytest.raises(ValueError, match="exact let"):
        replace(occurrence, unnest=other)


def test_the_unnest_locator_separates_identities_and_keeps_its_invariant(
    tmp_path: Path,
) -> None:
    source = (
        HEAD
        + _query(
            "from generate_series(1, 3, 1) as n",
            "let p = parent",
            "cross join p",
            "let o = unnest(p.nested)",
            "cross join o",
            "select:",
            "    x = n.n",
            "    total = o.total",
        )
        + _query(
            "from parent",
            "let p = parent",
            "inner join p on parent.id == p.id",
            "let o = unnest(p.nested)",
            "cross join o",
            "select:",
            "    total = o.total",
            name="again",
        )
    )
    semantic = _semantic(tmp_path, source)
    facts = semantic.module_attribution_facts
    assert facts is not None and semantic.module_catalogs is not None
    (catalog,) = semantic.module_catalogs.catalogs
    first, second = catalog.unnests
    (function,) = catalog.table_functions
    declaration = catalog.occurrences[first.declaration_position]
    identities = [
        project_declaration_occurrence_identity(item)
        for item in (first, declaration, function, second)
    ]
    # Pairwise different: the Unnest, its declaration, the table function of
    # the same body, and the Unnest at the same position of another body.
    assert len(set(identities)) == 4
    unnest_identity = identities[0]
    assert (unnest_identity.unnest_position, identities[3].unnest_position) == (1, 1)
    assert unnest_identity.block_local and not identities[1].block_local
    assert identities[2].table_function and identities[2].unnest_position is None
    # Every reader takes the one locator: attribution lineage, the Unnest
    # input fact and its element outputs.
    lineage_owners = {lineage.owner for lineage in facts.row_lineages}
    assert unnest_identity in lineage_owners
    nested = semantic.nested_relation_facts
    assert nested is not None
    assert [fact.occurrence for fact in nested.unnest_inputs] == [
        identities[0],
        identities[3],
    ]
    assert all(
        field.owner == unnest_identity
        and field.kind is ProjectModuleRowFieldKind.RELATION_OUTPUT
        for field in nested.unnest_inputs[0].element_fields
    )
    with pytest.raises(ValueError, match="neither a relation let"):
        replace(unnest_identity, let_position=0)
    with pytest.raises(ValueError, match="neither a relation let"):
        replace(unnest_identity, table_function=True)
    with pytest.raises(ValueError, match="Unnest position must be a non-negative"):
        replace(unnest_identity, unnest_position=-1)


def test_the_portable_identity_omits_an_absent_unnest_locator_and_refuses_one(
    tmp_path: Path,
) -> None:
    semantic = _semantic(
        tmp_path,
        HEAD
        + _query("from parent", "let o = unnest(parent.nested)", "cross join o")
        + "    select:\n        id = parent.id\n",
    )
    assert semantic.module_catalogs is not None
    (catalog,) = semantic.module_catalogs.catalogs
    encode = project_query_block_ir_inspection._identity_data
    declared = project_declaration_occurrence_identity(catalog.occurrences[-1])
    data = encode(declared)
    assert isinstance(data, dict) and "unnest_position" not in data
    assert "table_function" not in data and "let_position" not in data
    with pytest.raises(TypeError, match="Portable identity has no Unnest locator."):
        encode(project_declaration_occurrence_identity(catalog.unnests[0]))
    with pytest.raises(TypeError, match="Portable emission has no Unnest locator."):
        project_sql_emission_portable._occurrence(catalog.unnests[0])


# --- AC-02: resolution by identity ---


def test_an_unnest_join_binds_its_occurrence_by_identity_never_by_name(
    tmp_path: Path,
) -> None:
    semantic = _semantic(
        tmp_path,
        HEAD
        + _query("from parent", "let o = unnest(parent.nested)", "cross join o")
        + "    select:\n        id = parent.id\n",
    )
    facts = semantic.module_semantic_facts
    assert facts is not None and semantic.module_catalogs is not None
    (catalog,) = semantic.module_catalogs.catalogs
    (occurrence,) = catalog.unnests
    (environment,) = facts.environments
    resolution = environment.resolution_environment
    declaration = catalog.occurrences[occurrence.declaration_position]
    assert isinstance(declaration.definition, QueryDef)
    assert resolution.find_scoped_relation_name(declaration, "o") == ()
    (symbol,) = resolution.find_unnest_symbol(occurrence)
    assert resolution.unnest_symbols == (symbol,)
    assert symbol.target_occurrence is occurrence
    (join,) = declaration.definition.join_clauses
    assert catalog.find_unnest(declaration, join) is occurrence
    assert catalog.find_unnest(occurrence, join) is None
    completed = _completed(semantic)
    (ledger,) = (
        ledger
        for ledger in completed.roots.effective_outputs.operative_conditions.uses.ledgers
        if ledger.owner is declaration
    )
    assert [binding.name for binding in ledger.bindings] == ["parent", "o"]
    assert ledger.bindings[1].target is symbol


def test_an_unnest_name_that_a_relation_also_has_stays_ambiguous(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert _checked(
        capsys,
        tmp_path,
        {
            "main.pietto": HEAD
            + _query("from parent", "let o = unnest(parent.nested)", "cross join o")
            + "    select:\n        id = parent.id\n"
            + _query("from orders", "select:", "    id", name="o")
        },
    ) == [("PIE-S2604", 24, 5, "Ambiguous JOIN input: o", None)]


# --- AC-03: an admitted Unnest checks like any other JOIN (D-S06-1) ---


ADMITTED = {
    "cross": ("cross join o",),
    "inner": ("inner join o on o.total > 10",),
    "left-true": ("left join o on True",),
    "left-where": ("left join o on True", "where o.total > 10"),
    "left-on-match": ("left join o on o.total > 10",),
    "on-reads-parent": ("left join o on o.total > parent.id",),
}


@pytest.mark.parametrize("join", ADMITTED.values(), ids=ADMITTED.keys())
def test_an_admitted_unnest_checks(
    tmp_path: Path,
    join: tuple[str, ...],
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = HEAD + _query(
        "from parent",
        "let o = unnest(parent.nested)",
        *join,
        "select:",
        "    id = parent.id",
        "    total = o.total",
        "order by total desc",
        "limit 3",
    )
    assert _checked(capsys, tmp_path, {"main.pietto": source}) == []


@pytest.mark.parametrize(
    "body",
    [
        (
            "let p = parent",
            "from p",
            "let o = unnest(p.nested)",
            "cross join o",
            "select:",
            "    id = p.id",
        ),
        (
            "from customers",
            "let p = parent",
            "left join p on customers.id == p.id",
            "let o = unnest(p.nested)",
            "left join o on True",
            "select:",
            "    name",
            "    total = o.total",
        ),
        (
            "from customers",
            "let p = parent",
            "inner join p on customers.id == p.id",
            "let o = unnest(p.nested)",
            "cross join o",
            "select:",
            "    name",
            "    total = o.total",
        ),
        (
            "from customers",
            "let p = parent",
            "cross join p",
            "let o = unnest(p.nested)",
            "cross join o",
            "select:",
            "    name",
            "    total = o.total",
        ),
    ],
    ids=["from-alias", "left-joined-parent", "join-binding", "cross-joined-parent"],
)
def test_an_unnest_of_an_alias_or_join_binding_checks(
    tmp_path: Path,
    body: tuple[str, ...],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert _checked(capsys, tmp_path, {"main.pietto": HEAD + _query(*body)}) == []


def test_an_unnest_of_an_imported_relation_and_of_a_joined_producer(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    producer = JOINED_HEAD + "export (\n    query parent,\n)\n"
    reader = 'from "main.pietto" import (\n    query parent,\n)\n' + _query(
        "from parent",
        "let o = unnest(parent.nested)",
        "cross join o",
        "select:",
        "    total = o.total",
    )
    # A producer whose row completion builds still types its Collect output.
    diagnostics = _checked(
        capsys, tmp_path, {"main.pietto": producer, "reader.pietto": reader}
    )
    assert diagnostics == []


def test_the_language_example_checks(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = (
        HEAD
        + _query("from parent", "let o = unnest(parent.nested)", "cross join o")
        + "    select:\n        id = parent.id\n        total = o.total\n"
    )
    root = _root(tmp_path, {"main.pietto": source})
    assert cli_main(["check", "--project", str(root)]) == 0
    assert capsys.readouterr().out == "Project check OK: .\nFiles checked: 1\n"
    assert _checked(capsys, tmp_path / "json", {"main.pietto": source}) == []


# --- AC-04 to AC-06: fields, references, nullability, presence and grain ---


def test_the_unnest_outputs_are_the_collected_fields_with_child_provenance(
    tmp_path: Path,
) -> None:
    semantic = _semantic(
        tmp_path,
        HEAD.replace("    total: Int\n", "    total: Int | None\n")
        + _query("from parent", "let o = unnest(parent.nested)", "cross join o")
        + "    select:\n        id = parent.id\n        total = o.total\n",
    )
    nested = semantic.nested_relation_facts
    assert nested is not None
    (fact,) = nested.unnest_inputs
    (collect,) = nested.collect_facts
    nested_type = fact.nested_type
    assert nested_type is not None and nested_type is collect.nested_type
    assert fact.collect_read is collect.collect_read
    assert fact.source_field == collect.output
    assert fact.source_binding_position == 0
    assert fact.join is not None and fact.join.kind is AuthoredJoinKind.CROSS
    assert nested_type.element_relation.identity.declared_name == "all_orders"
    entry = _unnest_entry(_completed(semantic))
    assert [
        (field.output_name, field.field.resolved_type.name, field.field.nullability)
        for field in entry.fields
    ] == [
        ("id", "Int", ProjectRowFieldNullability.NON_NULL),
        ("total", "Int", ProjectRowFieldNullability.NULLABLE),
    ]
    assert tuple(field.identity for field in entry.fields) == fact.element_fields
    assert [field.identity.field_position for field in entry.fields] == [0, 1]
    # Each output is provenanced by its child field.
    assert [field.source.child for field in entry.fields] == list(
        nested_type.element_fields
    )
    assert entry.root.fact is fact


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        (
            ("cross join o", "where o.missing > 1", "select:", "    id = parent.id"),
            [("PIE-S2102", 25, 11, "Unknown field: o.missing")],
        ),
        (
            ("cross join o", "select:", "    id = parent.id", "    m = o.missing"),
            [("PIE-S2102", 27, 13, "Unknown field: o.missing")],
        ),
        (
            ("left join o on o.missing == 1", "select:", "    id = parent.id"),
            [("PIE-S2335", 24, 20, "JOIN ON reference is unknown: o.missing")],
        ),
        (
            (
                "cross join o",
                "where parent.nested == parent.nested",
                "select:",
                "    id = parent.id",
            ),
            [
                (
                    "PIE-S2805",
                    25,
                    column,
                    "Nested relation field parent.nested cannot be read in WHERE: "
                    "a collected relation has no comparison, ordering, grouping or "
                    "scalar value.",
                )
                for column in (11, 28)
            ],
        ),
        (
            # `o` has an `id` too, so a bare `id` names no one input.
            ("cross join o", "select:", "    id", "    total = o.total"),
            [("PIE-S2335", 26, 9, "Ambiguous field: id; write parent.id or o.id")],
        ),
    ],
    ids=[
        "where-unknown",
        "select-unknown",
        "on-unknown",
        "parent-nested-read",
        "shared-name-alone",
    ],
)
def test_unnest_field_reads_report_what_alias_let_reads_report(
    tmp_path: Path,
    lines: tuple[str, ...],
    expected: list[tuple[str, int, int, str]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = HEAD + _query("from parent", "let o = unnest(parent.nested)", *lines)
    unnest = _checked(capsys, tmp_path / "unnest", {"main.pietto": source})
    alias = _checked(
        capsys,
        tmp_path / "alias",
        {
            "main.pietto": HEAD
            + _query("from parent", "let o = kids", *lines)
            + _query("from orders", "select:", "    id", "    total", name="kids")
        },
    )
    assert _located(alias) == expected
    assert unnest == alias


def _join_facts(tmp_path: Path, *lines: str, head: str = HEAD) -> tuple[Any, Any]:
    semantic = _semantic(
        tmp_path,
        head + _query("from parent", "let o = unnest(parent.nested)", *lines),
    )
    completed = _completed(semantic)
    return _region(completed), completed


def _nullability(join: Any) -> list[tuple[str, list[int]]]:
    return [
        (
            field.effective_nullability.value,
            [ref.position for ref in field.nulling_joins],
        )
        for field in join.properties.null_extension.fields
    ]


@pytest.mark.parametrize(
    ("join", "nullability"),
    [
        ("cross join o", ("non_null", "nullable")),
        ("inner join o on True", ("non_null", "nullable")),
        # Only the existing null-rejection proof of an INNER ON narrows.
        ("inner join o on o.total > 10", ("non_null", "non_null")),
        ("left join o on True", ("nullable", "nullable")),
    ],
    ids=["cross", "inner", "inner-null-rejecting", "left"],
)
def test_unnest_outputs_keep_child_nullability_unless_left_nulls_them(
    tmp_path: Path, join: str, nullability: tuple[str, str]
) -> None:
    _, completed = _join_facts(
        tmp_path,
        join,
        "select:",
        "    id = parent.id",
        "    oid = o.id",
        "    total = o.total",
        head=HEAD.replace("    total: Int\n", "    total: Int | None\n"),
    )
    (entry,) = (
        e
        for e in completed.roots.effective_outputs.entries
        if e.owner.identity.declared_name == "expanded"
    )
    assert [(f.output_name, f.field.nullability.value) for f in entry.fields] == [
        ("id", "non_null"),
        ("oid", nullability[0]),
        ("total", nullability[1]),
    ]


def test_a_left_unnest_nulls_every_element_field_by_its_own_join(
    tmp_path: Path,
) -> None:
    semantic = _semantic(
        tmp_path,
        HEAD
        + _query(
            "from customers",
            "let p = parent",
            "left join p on customers.id == p.id",
            "let o = unnest(p.nested)",
            "left join o on True",
            "select:",
            "    name",
            "    total = o.total",
        ),
    )
    region = _region(_completed(semantic))
    parent_join, unnest_join = region.joins
    assert (parent_join.kind, unnest_join.kind) == (
        AuthoredJoinKind.LEFT,
        AuthoredJoinKind.LEFT,
    )
    p_ref, o_ref = parent_join.node.ref.position, unnest_join.node.ref.position
    # customers.id, customers.name; p.id, p.nested (the container, nulled by
    # `left join p`); o.id, o.total (nulled by the Unnest JOIN alone).
    assert _nullability(unnest_join) == [
        ("non_null", []),
        ("non_null", []),
        ("nullable", [p_ref]),
        ("nullable", [p_ref]),
        ("nullable", [o_ref]),
        ("nullable", [o_ref]),
    ]


def test_an_unnest_has_no_key_fd_or_bound_and_unkeys_its_parent(
    tmp_path: Path,
) -> None:
    keyed = (
        HEAD.replace(
            "    name: Text\n", "    name: Text\n    customer_key = unique(id)\n"
        )
        .replace("    total: Int\n", "    total: Int\n    order_key = unique(id)\n")
        .replace("        order by id\n", "        order by id\n        limit 1\n")
        # A scalar beside the key: no FD names the nested field (D-S04-3).
        .replace(
            "        id\n        nested", "        id\n        name\n        nested"
        )
    )
    region, completed = _join_facts(
        tmp_path,
        "cross join o",
        "select:",
        "    id = parent.id",
        "    total = o.total",
        head=keyed,
    )
    parent_input, unnest_input = region.input_properties
    assert parent_input.keys, "the parent keeps its proven key"
    assert (unnest_input.keys, unnest_input.fds) == ((), ())
    (join,) = region.joins
    relational = join.properties.relational
    assert relational.keys == ()
    # The parent's FDs survive; no key or FD reads its nested field (2) or an
    # Unnest field (3, 4).
    assert relational.fds
    assert all(
        member.field_position < 2
        for fd in relational.fds
        for value_class in (*fd.determinants, *fd.dependents)
        for member in value_class.members
    )
    assert current_forward_at_most_one(join.condition) is False
    entry = _unnest_entry(completed)
    assert entry.row_domain.kind.value == "values"
    assert entry.origin.witness is entry.root
    assert not hasattr(entry.root, "rows")


# --- AC-07: a test-local oracle of the Unnest operators ---


def _unnest_rows(
    parents: list[tuple[str, list[int | None] | None]], kind: str, on: Any
) -> list[tuple[str, int | None]]:
    """Each output row of one Unnest JOIN over (parent, nested value) rows: a
    child row matches only when `on` is True (None and False never match),
    and a LEFT JOIN keeps one placeholder row per parent without a match."""

    rows: list[tuple[str, int | None]] = []
    for parent, nested in parents:
        matched = [child for child in (nested or []) if on(child) is True]
        rows.extend((parent, child) for child in matched)
        if kind == "left" and not matched:
            rows.append((parent, None))
    return rows


def _greater(limit: int) -> Any:
    return lambda value: None if value is None else value > limit


def test_the_unnest_oracle_minimal_counterexamples() -> None:
    parents: list[tuple[str, list[int | None] | None]] = [
        ("A", [7, 7]),
        ("A", [7, 7]),
        ("B", []),
    ]
    always = _greater(-1)
    assert len(_unnest_rows(parents, "cross", always)) == 4
    assert len(_unnest_rows(parents, "inner", always)) == 4
    assert len(_unnest_rows(parents, "left", always)) == 5
    assert _unnest_rows(parents, "left", _greater(10)) == [
        ("A", None),
        ("A", None),
        ("B", None),
    ]
    assert _unnest_rows([("C", None)], "left", always) == [("C", None)]
    assert _unnest_rows([("C", None)], "cross", always) == []
    # An UNKNOWN condition never matches: a None child joins no row.
    assert _unnest_rows([("D", [None])], "inner", _greater(10)) == []
    assert _unnest_rows([("D", [None])], "left", _greater(10)) == [("D", None)]


@pytest.mark.parametrize(
    ("lines", "kind", "on_join", "where"),
    [
        (("cross join o",), AuthoredJoinKind.CROSS, False, False),
        (("inner join o on o.total > 10",), AuthoredJoinKind.INNER, True, False),
        (("left join o on True",), AuthoredJoinKind.LEFT, True, False),
        (("left join o on o.total > 10",), AuthoredJoinKind.LEFT, True, False),
        (
            ("left join o on True", "where o.total > 10"),
            AuthoredJoinKind.LEFT,
            True,
            True,
        ),
    ],
    ids=["cross", "inner", "left-true", "left-on", "left-where"],
)
def test_the_unnest_facts_select_the_oracle_operator(
    tmp_path: Path,
    lines: tuple[str, ...],
    kind: AuthoredJoinKind,
    on_join: bool,
    where: bool,
) -> None:
    region, completed = _join_facts(
        tmp_path, *lines, "select:", "    id = parent.id", "    total = o.total"
    )
    (join,) = region.joins
    assert join.kind is kind
    # The ON stays JOIN-local; a WHERE is the joined row filter after it.
    assert (join.condition.expression is not None) is on_join
    if on_join:
        assert join.condition.expression is join.use.clause.on_clause.expression
    (entry,) = (
        e
        for e in completed.roots.effective_outputs.entries
        if e.owner.identity.declared_name == "expanded"
    )
    (result,) = entry.root.window_set.aggregation_set.results
    assert result.input_filter.kind is (
        ProjectJoinedRowFilterKind.AUTHORED_WHERE
        if where
        else ProjectJoinedRowFilterKind.ABSENT
    )
    nulled = [
        field.field_position
        for field in getattr(join.properties.null_extension, "fields", ())
        if field.nulling_joins
    ]
    assert nulled == ([2, 3] if kind is AuthoredJoinKind.LEFT else [])


# --- AC-08, AC-09: PIE-S2807 and PIE-S2806, each alone ---


_REFUSED_USE = (
    "Read `o.field` after its JOIN; to use the unnested rows elsewhere, read "
    "this table or query with `from`."
)


def _read(use: str) -> str:
    return f"Unnest o is read only by its JOIN, not by {use}."


def _beside(construct: str, name: str = "o") -> str:
    return (
        f"Unnest {name} is not yet available beside {construct} in the same table "
        "or query: unnest in one table or query, and read it with `from` in "
        "another that does the rest."
    )


STD = ("from parent", "let o = unnest(parent.nested)")
REFUSED = {
    "right": (
        (*STD, "right join o on True", "select:", "    total = o.total"),
        [
            (
                24,
                5,
                "Unnest o can be joined only by cross, inner or left join.",
                "Write `cross join o`, `inner join o on ...` or `left join o on True`.",
            )
        ],
    ),
    "full": (
        (*STD, "full join o on True", "select:", "    total = o.total"),
        [
            (
                24,
                5,
                "Unnest o can be joined only by cross, inner or left join.",
                "Write `cross join o`, `inner join o on ...` or `left join o on True`.",
            )
        ],
    ),
    "two-joins": (
        (*STD, "cross join o", "cross join o", "select:", "    id = parent.id"),
        [(25, 5, "Unnest o is joined more than once: one JOIN reads an Unnest.", None)],
    ),
    "group-by": (
        (
            *STD,
            "cross join o",
            "group by parent.id",
            "select:",
            "    id = parent.id",
            "    n = count()",
        ),
        [(23, 5, _beside("GROUP BY"), None)],
    ),
    "aggregate": (
        (*STD, "cross join o", "select:", "    n = count()"),
        [(23, 5, _beside("an aggregate"), None)],
    ),
    "having": (
        (*STD, "cross join o", "select:", "    id = parent.id", "having count() > 1"),
        [(23, 5, _beside("HAVING"), None)],
    ),
    "window": (
        (
            *STD,
            "cross join o",
            "select:",
            "    id = parent.id",
            "    r = row_number() window(order by o.total)",
        ),
        [(23, 5, _beside("a window"), None)],
    ),
    "qualify": (
        (
            *STD,
            "cross join o",
            "select:",
            "    id = parent.id",
            "qualify row_number() window(order by parent.id) == 1",
        ),
        [(23, 5, _beside("QUALIFY"), None)],
    ),
    "distinct": (
        (*STD, "cross join o", "select distinct:", "    id = parent.id"),
        [(23, 5, _beside("SELECT DISTINCT"), None)],
    ),
    "any": (
        (
            *STD,
            "cross join o",
            "where any(x.total > 1 for x in o)",
            "select:",
            "    id = parent.id",
        ),
        [(23, 5, _beside("any(...)"), None)],
    ),
    "collect-other": (
        (
            "let k:",
            "    from orders",
            "    select:",
            "        id",
            "    order by id",
            *STD,
            "cross join o",
            "select:",
            "    id = parent.id",
            "    ks = collect k",
        ),
        [(28, 5, _beside("a Collect read"), None)],
    ),
    "two-unnests": (
        (
            *STD,
            "let o2 = unnest(parent.nested)",
            "cross join o",
            "cross join o2",
            "select:",
            "    id = parent.id",
        ),
        [
            (23, 5, _beside("another Unnest"), None),
            (24, 5, _beside("another Unnest", "o2"), None),
        ],
    ),
    "unnest-of-unnest": (
        (
            *STD,
            "cross join o",
            "let o2 = unnest(o.total)",
            "cross join o2",
            "select:",
            "    id = parent.id",
        ),
        [
            (23, 5, _beside("another Unnest"), None),
            (25, 5, _beside("another Unnest", "o2"), None),
        ],
    ),
    "right-before": (
        (
            "from parent",
            "let c = customers",
            "right join c on parent.id == c.id",
            "let o = unnest(parent.nested)",
            "cross join o",
            "select:",
            "    total = o.total",
        ),
        [
            (
                25,
                5,
                _beside("a RIGHT or FULL JOIN that may null-extend parent"),
                None,
            )
        ],
    ),
    # A FULL JOIN target is refused here, never by PIE-S2806, whose CROSS,
    # INNER or LEFT JOIN text refuses a RIGHT JOIN target.
    "full-join-target": (
        (
            "from customers",
            "let p = parent",
            "full join p on customers.id == p.id",
            "let o = unnest(p.nested)",
            "cross join o",
            "select:",
            "    total = o.total",
        ),
        [(25, 5, _beside("a RIGHT or FULL JOIN that may null-extend p"), None)],
    ),
    "relation-let": (
        (
            "let inner_rows:",
            "    from parent",
            "    let o = unnest(parent.nested)",
            "    cross join o",
            "    select:",
            "        t = o.total",
            "from inner_rows",
            "select:",
            "    t",
        ),
        [
            (
                24,
                9,
                "Unnest o is not yet available in a relation let: unnest in the "
                "table or query itself.",
                None,
            )
        ],
    ),
    "from": (
        (
            "let o = unnest(parent.nested)",
            "from o",
            "cross join o",
            "select:",
            "    t = o.total",
        ),
        [(23, 5, _read("from"), _REFUSED_USE)],
    ),
    "join-before-let": (
        (
            "from parent",
            "cross join o",
            "let o = unnest(parent.nested)",
            "cross join o",
            "select:",
            "    id = parent.id",
        ),
        [(23, 5, _read("a JOIN written before the let"), _REFUSED_USE)],
    ),
    "exists": (
        (*STD, "cross join o", "where exists o", "select:", "    id = parent.id"),
        [(25, 11, _read("exists"), _REFUSED_USE)],
    ),
    "scalar": (
        (*STD, "cross join o", "select:", "    x = scalar o.total"),
        [(26, 13, _read("scalar"), _REFUSED_USE)],
    ),
    "in": (
        (*STD, "cross join o", "where parent.id in o", "select:", "    x = parent.id"),
        [(25, 11, _read("in"), _REFUSED_USE)],
    ),
    "not-in": (
        (
            *STD,
            "cross join o",
            "where parent.id not in o",
            "select:",
            "    x = parent.id",
        ),
        [(25, 11, _read("not in"), _REFUSED_USE)],
    ),
    "collect": (
        (*STD, "cross join o", "select:", "    x = parent.id", "    again = collect o"),
        [(27, 17, _read("collect"), _REFUSED_USE)],
    ),
    "set-operation": (
        (
            "let a:",
            "    from orders",
            "    select:",
            "        id",
            "let b:",
            "    union all a, o",
            *STD,
            "cross join o",
            "select:",
            "    id = parent.id",
        ),
        [(27, 22, _read("a set operation"), _REFUSED_USE)],
    ),
    "let": (
        (
            *STD,
            "let o2 = o",
            "cross join o",
            "cross join o2",
            "select:",
            "    id = parent.id",
        ),
        [(24, 5, _read("a let"), _REFUSED_USE)],
    ),
}


@pytest.mark.parametrize(("body", "expected"), REFUSED.values(), ids=REFUSED.keys())
def test_an_unnest_use_or_place_that_is_not_admitted_is_one_pie_s2807(
    tmp_path: Path,
    body: tuple[str, ...],
    expected: list[tuple[int, int, str, str | None]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert _checked(capsys, tmp_path, {"main.pietto": HEAD + _query(*body)}) == [
        ("PIE-S2807", line, column, message, suggestion)
        for line, column, message, suggestion in expected
    ]


def test_a_capture_line_of_an_unnest_is_one_pie_s2807(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = HEAD + (
        "query expanded:\n"
        "    let same:\n"
        "        capture o\n"
        "        from orders\n"
        "        where orders.id == o.id\n"
        "        select:\n"
        "            id\n"
        "    from parent\n"
        "    let o = unnest(parent.nested)\n"
        "    cross join o\n"
        "    where exists same\n"
        "    select:\n"
        "        total = o.total\n"
    )
    assert _checked(capsys, tmp_path, {"main.pietto": source}) == [
        ("PIE-S2807", 23, 9, _read("a capture line"), _REFUSED_USE)
    ]


@pytest.mark.parametrize(
    "local",
    [
        ("    let o = orders", "    from o"),
        (
            "    from customers",
            "    let o = orders",
            "    inner join o on o.customer_id == customers.id",
        ),
    ],
    ids=["from", "join"],
)
def test_a_relation_let_that_names_its_own_o_reads_that_one(
    tmp_path: Path,
    local: tuple[str, ...],
    capsys: pytest.CaptureFixture[str],
) -> None:
    # The Unnest is not visible in a let body, which reads its own `o`.
    body = (
        "let side:",
        *local,
        "    select:",
        "        oid = o.id",
        "from parent",
        "let o = unnest(parent.nested)",
        "cross join o",
        "let s = side",
        "inner join s on s.oid == o.id",
        "select:",
        "    t = o.total",
    )
    assert _checked(capsys, tmp_path, {"main.pietto": HEAD + _query(*body)}) == []


_NOT_BEFORE = (
    "Write `let o = unnest(binding.field)` after the FROM or JOIN whose binding "
    "has the nested field."
)


def _not_visible(argument: str, binding: str) -> str:
    return (
        f"Unnest argument {argument} is not available: {binding} is not the FROM "
        "input or a CROSS, INNER or LEFT JOIN written before let o."
    )


ARGUMENTS = {
    "unknown-binding": (
        ("from parent", "let o = unnest(nobody.nested)", "cross join o"),
        [(23, 20, _not_visible("nobody.nested", "nobody"), _NOT_BEFORE)],
    ),
    "later-binding": (
        (
            "from customers",
            "let o = unnest(pp.nested)",
            "let pp = parent",
            "inner join pp on customers.id == pp.id",
            "cross join o",
        ),
        [(23, 20, _not_visible("pp.nested", "pp"), _NOT_BEFORE)],
    ),
    "let-before-from": (
        ("let o = unnest(parent.nested)", "from parent", "cross join o"),
        [(22, 20, _not_visible("parent.nested", "parent"), _NOT_BEFORE)],
    ),
    "right-join-target": (
        (
            "from customers",
            "let p = parent",
            "right join p on customers.id == p.id",
            "let o = unnest(p.nested)",
            "cross join o",
        ),
        [(25, 20, _not_visible("p.nested", "p"), _NOT_BEFORE)],
    ),
    "from-alias-name": (
        ("let p = parent", "from p", "let o = unnest(parent.nested)", "cross join o"),
        [
            (
                24,
                20,
                "Unnest argument parent.nested is not available: FROM reads parent "
                "as p; write `unnest(p.nested)`.",
                "Write `unnest(p.nested)`.",
            )
        ],
    ),
    "table-function": (
        (
            "from generate_series(1, 3, 1) as n",
            "let o = unnest(n.nested)",
            "cross join o",
        ),
        [
            (
                23,
                20,
                "Unnest argument n.nested is not available: n is a table function, "
                "which has no nested fields.",
                None,
            )
        ],
    ),
}


@pytest.mark.parametrize(("body", "expected"), ARGUMENTS.values(), ids=ARGUMENTS.keys())
def test_an_unnest_argument_binding_that_is_not_admitted_is_one_pie_s2806(
    tmp_path: Path,
    body: tuple[str, ...],
    expected: list[tuple[int, int, str, str | None]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = HEAD + _query(*body, "select:", "    x = 1")
    assert _checked(capsys, tmp_path, {"main.pietto": source}) == [
        ("PIE-S2806", line, column, message, suggestion)
        for line, column, message, suggestion in expected
    ]


def _field_type(argument: str, field: str, binding: str, type_name: str) -> str:
    return (
        f"Unnest argument {argument} is not available: field {field} of {binding} "
        f"has type {type_name}; only a field that a `collect` SELECT item outputs "
        "can be unnested."
    )


SET_HEAD = HEAD + "query both:\n    union all customers, customers\n"
SERIES = (
    "let v:",
    "    from generate_series(1, 3, 1) as n",
    "    select:",
    "        n",
    "from v",
)
FIELDS = {
    "unknown-field": (
        HEAD + _query("from parent", "let o = unnest(parent.missing)", "cross join o"),
        [("PIE-S2102", 23, 20, "Unknown field: parent.missing")],
    ),
    "scalar-field": (
        HEAD + _query("from parent", "let o = unnest(parent.id)", "cross join o"),
        [("PIE-S2806", 23, 20, _field_type("parent.id", "id", "parent", "Int"))],
    ),
    "joined-producer-unknown-field": (
        JOINED_HEAD
        + _query("from parent", "let o = unnest(parent.missing)", "cross join o"),
        [("PIE-S2102", 25, 20, "Unknown field: parent.missing")],
    ),
    "joined-producer-scalar-field": (
        JOINED_HEAD
        + _query("from parent", "let o = unnest(parent.id)", "cross join o"),
        [("PIE-S2806", 25, 20, _field_type("parent.id", "id", "parent", "Int"))],
    ),
    "set-producer-unknown-field": (
        SET_HEAD + _query("from both", "let o = unnest(both.missing)", "cross join o"),
        [("PIE-S2102", 25, 20, "Unknown field: both.missing")],
    ),
    "series-let-scalar-field": (
        HEAD + _query(*SERIES, "let o = unnest(v.n)", "cross join o"),
        [("PIE-S2806", 27, 20, _field_type("v.n", "n", "v", "Int"))],
    ),
    "series-let-unknown-field": (
        HEAD + _query(*SERIES, "let o = unnest(v.missing)", "cross join o"),
        [("PIE-S2102", 27, 20, "Unknown field: v.missing")],
    ),
}


@pytest.mark.parametrize(("source", "expected"), FIELDS.values(), ids=FIELDS.keys())
def test_an_unnest_field_that_is_no_typed_collect_output_reports_once(
    tmp_path: Path,
    source: str,
    expected: list[tuple[str, int, int, str]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    # With no PIE-S2333, PIE-S2334 or PIE-S2335 of its JOIN.
    assert (
        _located(
            _checked(
                capsys,
                tmp_path,
                {"main.pietto": source + "    select:\n        x = 1\n"},
            )
        )
        == expected
    )


def test_an_unnest_field_check_names_each_kind_of_field(tmp_path: Path) -> None:
    semantic = _semantic(
        tmp_path,
        HEAD
        + _query("from parent", "let o = unnest(parent.id)", "cross join o")
        + "    select:\n        x = 1\n",
    )
    assert semantic.module_catalogs is not None
    (catalog,) = semantic.module_catalogs.catalogs
    let = catalog.unnests[0].unnest
    assert let is not None

    def field(kind: ProjectResolvedTypeKind, name: str) -> ProjectRowSchema:
        return ProjectRowSchema(
            fields={
                "id": ProjectRowField(
                    name="id",
                    resolved_type=ProjectResolvedType(name=name, kind=kind),
                    nullability=ProjectRowFieldNullability.NON_NULL,
                )
            }
        )

    unknown = unnest_field_diagnostic(let, field(ProjectResolvedTypeKind.UNKNOWN, "?"))
    scalar = unnest_field_diagnostic(let, field(ProjectResolvedTypeKind.BUILTIN, "Int"))
    missing = unnest_field_diagnostic(let, ProjectRowSchema(fields={}))
    assert [
        (item.code, item.message)
        for item in (unknown, scalar, missing)
        if item is not None
    ] == [
        (
            "PIE-S2806",
            "Unnest argument parent.id is not available: the type of field id of "
            "parent is not known.",
        ),
        ("PIE-S2806", _field_type("parent.id", "id", "parent", "Int")),
        ("PIE-S2102", "Unknown field: parent.id"),
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            HEAD
            + "query both:\n    union all parent, parent\n"
            + _query("from both", "let o = unnest(both.nested)", "cross join o"),
            [
                *(
                    (
                        "PIE-S2805",
                        22,
                        column,
                        "Set operand parent outputs nested relation field nested: a "
                        "set operation over a collected relation is not available.",
                    )
                    for column in (15, 23)
                ),
            ],
        ),
        (
            HEAD.replace(
                "        nested = collect all_orders\n",
                "        nested = collect all_orders\n        z = None\n",
            )
            + _query("from parent", "let o = unnest(parent.z)", "cross join o"),
            [
                (
                    "PIE-S2333",
                    10,
                    1,
                    "Project relation semantic completion is unavailable: parent",
                )
            ],
        ),
    ],
    ids=["set-of-collected", "producer-not-completed"],
)
def test_an_unnest_field_whose_producer_reports_its_own_error_reports_nothing(
    tmp_path: Path,
    source: str,
    expected: list[tuple[str, int, int, str]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        _located(
            _checked(
                capsys,
                tmp_path,
                {"main.pietto": source + "    select:\n        x = 1\n"},
            )
        )
        == expected
    )


def test_an_unnest_of_a_refused_collect_reports_only_the_producer_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = HEAD.replace("        order by id\n", "") + _query(
        "from parent",
        "let o = unnest(parent.nested)",
        "cross join o",
        "select:",
        "    total = o.total",
    )
    assert [
        (code, line, column)
        for code, line, column, _, _ in _checked(
            capsys, tmp_path, {"main.pietto": source}
        )
    ] == [("PIE-S2804", 19, 18)]


@pytest.mark.parametrize(
    ("argument", "join", "expected"),
    [
        (
            "parent.id",
            "cross join o on True",
            [("PIE-S2806", 23, 20), ("PIE-S2336", 24, 5)],
        ),
        (
            "parent.zzz",
            "cross join o on True",
            [("PIE-S2102", 23, 20), ("PIE-S2336", 24, 5)],
        ),
        (
            "parent.id",
            "inner join o on parent.id",
            [("PIE-S2806", 23, 20), ("PIE-S2202", 24, 21)],
        ),
        (
            "parent.id",
            'inner join o on parent.id + "x"',
            [("PIE-S2806", 23, 20), ("PIE-S2105", 24, 21)],
        ),
    ],
)
def test_an_unnest_argument_error_retires_only_the_input_diagnostics_of_its_join(
    tmp_path: Path,
    argument: str,
    join: str,
    expected: list[tuple[str, int, int]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = HEAD + _query(
        "from parent", f"let o = unnest({argument})", join, "select:", "    x = 1"
    )
    assert [
        (code, line, column)
        for code, line, column, _, _ in _checked(
            capsys, tmp_path, {"main.pietto": source}
        )
    ] == expected


@pytest.mark.parametrize(
    "before",
    [
        ("from parent", "cross join parent"),
        ("from parent", "cross join nosuch"),
        ("from nosuch",),
    ],
    ids=["several-inputs", "unknown-join", "unknown-from"],
)
def test_an_unnest_of_a_binding_that_is_not_one_relation_keeps_its_join_diagnostics(
    tmp_path: Path,
    before: tuple[str, ...],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """D-S05-2: no input wins, and its JOIN reports what any JOIN reports."""

    binding = before[-1].split()[-1]
    lines = ("cross join o", "select:", "    t = o.total")
    unnest = _checked(
        capsys,
        tmp_path / "unnest",
        {
            "main.pietto": HEAD
            + _query(*before, f"let o = unnest({binding}.nested)", *lines)
        },
    )
    alias = _checked(
        capsys,
        tmp_path / "alias",
        {
            "main.pietto": HEAD
            + _query(*before, "let o = kids", *lines)
            + _query("from orders", "select:", "    id", "    total", name="kids")
        },
    )
    assert unnest == alias
    # The JOIN follows the reported failure of an earlier input or JOIN, as
    # any JOIN does, so it reports nothing of its own.
    assert 23 + len(before) not in {item[1] for item in alias}


def test_a_header_parameter_named_like_an_unnest_field_collides_as_after_an_alias_let(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lines = ("cross join o", "select:", "    pid = parent.id", "    t = total")
    name = "expanded(total: Int)"
    unnest = _checked(
        capsys,
        tmp_path / "unnest",
        {
            "main.pietto": HEAD
            + _query("from parent", "let o = unnest(parent.nested)", *lines, name=name)
        },
    )
    alias = _checked(
        capsys,
        tmp_path / "alias",
        {
            "main.pietto": HEAD
            + _query("from parent", "let o = orders", *lines, name=name)
        },
    )
    collision = (
        "PIE-S2354",
        21,
        16,
        "Query parameter name is also a field, let, relation, output or window name.",
    )
    assert _located(alias) == [collision]
    assert _located(unnest) == [collision]


# --- AC-10, AC-11: inherited JOIN diagnostics and unchanged neighbours ---


def test_a_right_join_after_an_unnest_reports_what_it_reports_after_an_alias_let(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lines = (
        "cross join o",
        "let r = orders",
        "right join r",
        "select:",
        "    x = parent.id",
    )
    unnest = _checked(
        capsys,
        tmp_path / "unnest",
        {
            "main.pietto": HEAD
            + _query("from parent", "let o = unnest(parent.nested)", *lines)
        },
    )
    alias = _checked(
        capsys,
        tmp_path / "alias",
        {
            "main.pietto": HEAD
            + _query("from parent", "let o = kids", *lines)
            + _query("from orders", "select:", "    id", "    total", name="kids")
        },
    )
    assert unnest == alias
    assert alias == [
        ("PIE-S2335", 26, 5, "JOIN source binding is unknown.", unnest[0][4]),
        (
            "PIE-S2333",
            26,
            5,
            "Project relation semantic completion is unavailable: expanded (JOIN r: "
            "write `on` with the condition that matches parent or o to orders)",
            unnest[1][4],
        ),
    ]


def test_an_unnest_let_without_its_join_keeps_its_ordinary_call(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = HEAD + _query(
        "from parent", "let o = unnest(parent.nested)", "select:", "    id"
    )
    assert [
        (code, line, column)
        for code, line, column, _, _ in _checked(
            capsys, tmp_path, {"main.pietto": source}
        )
    ] == [("PIE-S2103", 23, 13), ("PIE-S2805", 23, 20)]


# --- AC-12, AC-13: one authority, one visibility rule, determinism ---


def test_the_sidecar_holds_the_semantic_unnest_facts_themselves(
    tmp_path: Path,
) -> None:
    semantic = _semantic(
        tmp_path,
        HEAD
        + _query("from parent", "let o = unnest(parent.nested)", "cross join o")
        + "    select:\n        id = parent.id\n",
    )
    nested = semantic.nested_relation_facts
    facts = semantic.module_semantic_facts
    assert nested is not None and facts is not None
    owned = tuple(
        relation.unnest_occurrence
        for environment in facts.environments
        for relation in environment.relation_facts
        if relation.unnest_occurrence is not None
    )
    assert len(owned) == 1 and nested.unnest_inputs[0] is owned[0]
    (fact,) = owned
    with pytest.raises(ValueError, match="one visible binding"):
        replace(fact, binding_candidates=(None,))
    # A typed Unnest checks without a diagnostic of its own (D-S06-1).
    assert semantic.diagnostics == ()
    missing = unnest_field_diagnostic(fact.query_let, ProjectRowSchema(fields={}))
    with pytest.raises(ValueError, match="typed Unnest has no diagnostic"):
        replace(fact, diagnostic=missing)


def test_the_project_ir_verifies_an_unnest_and_inspection_fails_closed(
    tmp_path: Path,
) -> None:
    semantic = _semantic(
        tmp_path,
        HEAD
        + _query("from parent", "let o = unnest(parent.nested)", "left join o on True")
        + "    select:\n        id = parent.id\n        total = o.total\n",
    )
    assert semantic.module_semantic_facts is not None
    assert semantic.module_attribution_facts is not None
    plan = build_project_ir_project_plan(
        semantic_facts=semantic.module_semantic_facts,
        attribution=semantic.module_attribution_facts,
        allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()),
    )
    verification = verify_project_ir_stage(
        build_project_ir_evaluation_context_stage(plan)
    )
    assert verification.status is ProjectIRVerificationStatus.VERIFIED
    assert not verification.issues
    # The private phase-62 inspection has no Unnest locator (D-S06-8): it
    # refuses deterministically.
    for _ in range(2):
        with pytest.raises(ValueError, match="IR inspection has no Unnest locator"):
            build_project_ir_pipeline(
                semantic_result=semantic,
                allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()),
            )


def test_unnest_checks_are_independent_of_their_order(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sources = [
        HEAD + _query(*body, "select:", "    x = 1")
        for body in (
            *(body for body, _ in REFUSED.values()),
            *(body for body, _ in ARGUMENTS.values()),
        )
    ]
    forward = [
        _checked(capsys, tmp_path / f"f{index}", {"main.pietto": source})
        for index, source in enumerate(sources)
    ]
    backward = [
        _checked(capsys, tmp_path / f"b{index}", {"main.pietto": source})
        for index, source in reversed(list(enumerate(sources)))
    ]
    assert forward == backward[::-1]
    assert all(items for items in forward)


def test_a_declaration_occurrence_built_by_hand_needs_its_exact_unnest(
    tmp_path: Path,
) -> None:
    semantic = _semantic(
        tmp_path,
        HEAD
        + _query("from parent", "let o = unnest(parent.nested)", "cross join o")
        + "    select:\n        id = parent.id\n",
    )
    assert semantic.module_catalogs is not None
    (catalog,) = semantic.module_catalogs.catalogs
    (occurrence,) = catalog.unnests
    declaration = catalog.occurrences[occurrence.declaration_position]
    with pytest.raises(ValueError):
        ProjectDeclarationOccurrence(
            identity=declaration.identity,
            module_position=declaration.module_position,
            declaration_position=declaration.declaration_position,
            definition=declaration.definition,
            unnest=occurrence.unnest,
            unnest_position=0,
        )
