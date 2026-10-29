"""Phase-64 syntax retention, negative admission and existing boundary laws."""

from __future__ import annotations

import pytest
from pathlib import Path
from dataclasses import replace
import json

from _pietto_parser_layout import layout_free
from pietto.ast_nodes import (
    AuthoredJoinKind,
    CallExpr,
    NameExpr,
    BlockRelationDef,
    JoinClause,
    JoinOnClause,
    SelectBody,
    Span,
    QueryDef,
    TableDef,
    SetRelationDef,
    ComparisonExpr,
    ShapeDef,
    ImportStatement,
)
from pietto import cli
from pietto.semantic import analyze
from pietto.ir import RelationIR, build_ir
from pietto._project.check import check_project_parse_only
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.model import ProjectRelationRowSchemaReason
from pietto._project.project_completed_semantics import (
    build_project_completed_semantic_result,
)
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
)
from pietto._project.project_completion import (
    ProjectEffectiveOutputTerminal,
    ProjectExistingEffectiveOutput,
)
from pietto._project.project_final_outputs import (
    ProjectCompletedSetOutput,
    ProjectEffectiveOutputCompletionTerminal,
)
from pietto._project.project_query_block_ir import (
    build_project_query_block_ir,
)
from pietto._project.project_query_block import (
    build_project_query_block_from_relation,
    ProjectNonConcreteQueryBlock,
)
from pietto._project.module_carrier import ProjectCompilationMode

from pietto.parser_api import parse_source


BASE = """shape Row:
    id: Int
source lhs: Row = postgres.table("lhs")
source rhs: Row = postgres.table("rhs")
relationship link(l: Row, r: Row):
    l.id == r.id
"""


def _join(
    kind: str = "inner", predicate: str | None = None, *, owner: str = "query"
) -> str:
    condition = (
        ""
        if kind == "cross" and predicate is None
        else f" on {predicate or 'lhs.id == r.id'}"
    )
    return (
        BASE + f"{owner} result:\n"
        "    from lhs\n"
        "    let r = rhs\n"
        f"    {kind} join r{condition}\n"
        "    select:\n"
        "        id = lhs.id\n"
    )


@pytest.mark.parametrize("kind", ("inner", "left"))
def test_named_join_shape_remains_parseable(kind: str) -> None:
    result = parse_source(_join(kind))
    assert result.ast is not None and not result.diagnostics
    relation = result.ast.definitions[-1]
    assert isinstance(relation, (TableDef, QueryDef))
    assert relation.join_clauses[0].kind.value == kind


@pytest.mark.parametrize("kind", ("inner", "left", "right", "full", "cross"))
def test_located_join_kinds_and_on_retention(kind: str) -> None:
    predicate = None if kind == "cross" else "lhs.id == r.id"
    result = parse_source(_join(kind, predicate), path="joins.pietto")
    assert result.ast is not None and not result.diagnostics
    relation = result.ast.definitions[-1]
    assert isinstance(relation, (TableDef, QueryDef))
    join = relation.join_clauses[0]
    assert join.kind.value == kind
    if kind != "cross":
        assert join.on_clause is not None
        assert type(join.on_clause).__name__ == "JoinOnClause"
        assert join.on_clause.span.line == 10
        assert isinstance(join.on_clause.expression, ComparisonExpr)
        assert join.on_clause.expression.operator == "=="
    else:
        assert join.on_clause is None


@pytest.mark.parametrize(("kind", "negation"), (("semi", ""), ("anti", "not ")))
def test_semi_and_anti_joins_are_retired_for_any_filters(
    kind: str, negation: str
) -> None:
    result = parse_source(_join(kind), path="joins.pietto")

    assert result.ast is None
    assert [
        (item.code, item.location.line, item.location.column, item.suggestion)
        for item in result.diagnostics
    ] == [
        (
            "PIE-P1000",
            10,
            5,
            f"Write 'where {negation}any(predicate for r in r)' instead of "
            f"'{kind} join r on predicate'.",
        )
    ]


_AS_REVIEW = "; relationship traversal requires an explicit migration review."


@pytest.mark.parametrize(
    "tail",
    ("\n", ":\n        from lhs\n        on lhs.id == r.id\n", ": on lhs.id == r.id\n"),
)
@pytest.mark.parametrize(
    ("kind", "column", "suggestion"),
    (
        (
            "semi",
            19,
            "Write 'where any(predicate for r in rhs)' instead of "
            "'semi join rhs as r'" + _AS_REVIEW,
        ),
        (
            "anti",
            19,
            "Write 'where not any(predicate for r in rhs)' instead of "
            "'anti join rhs as r'" + _AS_REVIEW,
        ),
        (
            "inner",
            20,
            "Name the input with 'let alias = relation', then write "
            "'inner join alias on predicate'" + _AS_REVIEW,
        ),
        (
            "left",
            19,
            "Name the input with 'let alias = relation', then write "
            "'left join alias on predicate'" + _AS_REVIEW,
        ),
        (
            "right",
            20,
            "Name the input with 'let alias = relation', then write "
            "'right join alias on predicate'" + _AS_REVIEW,
        ),
        (
            "full",
            19,
            "Name the input with 'let alias = relation', then write "
            "'full join alias on predicate'" + _AS_REVIEW,
        ),
        (
            "cross",
            20,
            "Name the input with 'let alias = relation', then write "
            "'cross join alias'" + _AS_REVIEW,
        ),
    ),
)
def test_old_join_bindings_are_refused_at_as_with_their_rewrite(
    kind: str, column: int, suggestion: str, tail: str
) -> None:
    source = (
        BASE + "query result:\n    from lhs\n"
        f"    {kind} join rhs as r{tail}"
        "    select:\n        id = lhs.id\n"
    )
    result = parse_source(source, path="joins.pietto")

    assert result.ast is None
    assert [
        (
            item.code,
            item.location.line,
            item.location.column,
            item.message,
            item.suggestion,
        )
        for item in result.diagnostics
    ] == [
        (
            "PIE-P1000",
            9,
            column,
            "This spelling is not accepted by the modern syntax. " + suggestion,
            suggestion,
        )
    ]


@pytest.mark.parametrize("operator", ("union", "intersect", "except"))
@pytest.mark.parametrize("quantifier", ("all", "distinct", ""))
@pytest.mark.parametrize("owner", ("table", "query"))
def test_set_body_is_a_located_named_definition(
    operator: str, quantifier: str, owner: str
) -> None:
    suffix = f" {quantifier}" if quantifier else ""
    source = (
        BASE
        + f"""{owner} result:
    {operator}{suffix}:
        from lhs
        from rhs
        from lhs
"""
    )
    result = parse_source(source, path="sets.pietto")
    assert result.ast is not None and not result.diagnostics
    relation = result.ast.definitions[-1]
    assert isinstance(relation, SetRelationDef)
    assert relation.name == "result"
    assert relation.kind.value == owner
    assert relation.body.kind.value == operator
    assert tuple(item.relation_name for item in relation.body.operands) == (
        "lhs",
        "rhs",
        "lhs",
    )
    assert relation.body.operands[0] is not relation.body.operands[2]
    if quantifier:
        assert relation.body.quantifier is not None
        assert relation.body.quantifier.value == quantifier
    else:
        assert relation.body.quantifier is None
    assert (relation.body.quantifier_span is None) is (not quantifier)
    assert not hasattr(relation, "from_clause")
    assert not hasattr(relation, "select_items")


NEW_SOURCES = (
    _join("inner", "False"),
    _join("left", "link(lhs, r) and False"),
    _join("full"),
    _join("cross"),
    BASE + "query combined:\n    union all:\n        from lhs\n        from rhs\n",
    BASE + "table combined:\n    except:\n        from lhs\n        from lhs\n",
)


@pytest.mark.parametrize("source", NEW_SOURCES)
def test_single_file_join_ir_and_set_refusal_follow_current_support(
    source: str,
) -> None:
    parsed = parse_source(source)
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = analyze(parsed.ast)
    lowered = build_ir(semantic.script or parsed.ast, semantic.model)
    if isinstance(parsed.ast.definitions[-1], SetRelationDef):
        assert any(d.code == "PIE-S2334" for d in semantic.diagnostics)
        assert lowered.ir is None
        assert any(d.code == "PIE-I1000" for d in lowered.diagnostics)
    else:
        assert not semantic.diagnostics
        assert lowered.ir is not None and not lowered.diagnostics
        relation = lowered.ir.definitions[-1]
        assert isinstance(relation, RelationIR)
        assert len(relation.joins) == 1


@pytest.mark.parametrize("source", NEW_SOURCES)
@pytest.mark.parametrize("schema", (1, 2))
def test_project_forms_follow_current_owner_availability_without_traceback(
    tmp_path: Path, source: str, schema: int
) -> None:
    (tmp_path / "pietto.toml").write_text(
        f'schema_version = {schema}\n[sources]\ninclude = ["*.pietto"]\n'
    )
    (tmp_path / "main.pietto").write_text(
        source + "query valid:\n    from lhs\n    select:\n        id\n"
    )
    parsed = check_project_parse_only(tmp_path)
    assert parsed.ok
    semantic = build_empty_project_semantic_result(parsed)
    result = (
        build_project_completed_semantic_result(semantic) if schema == 2 else semantic
    )
    supported = schema == 2 and source in NEW_SOURCES[:5]
    assert result.ok is supported
    assert any(d.code == "PIE-S2334" for d in result.diagnostics) is not supported


@pytest.mark.parametrize("kind", ("inner", "left", "right", "full", "cross"))
@pytest.mark.parametrize("occurrences", (1, 2, 3))
def test_named_join_occurrences_preserve_order_and_on_identity(
    kind: str, occurrences: int
) -> None:
    joins = "".join(
        f"    let r{index} = rhs\n"
        f"    {kind} join r{index}"
        + ("" if kind == "cross" else f" on link(lhs, r{index})")
        + "\n"
        for index in range(occurrences)
    )
    parsed = parse_source(
        BASE + "query q:\n    from lhs\n" + joins + "    select lhs.id\n"
    )
    assert parsed.diagnostics == () and parsed.ast is not None
    relation = parsed.ast.definitions[-1]
    assert isinstance(relation, QueryDef)
    assert [item.name for item in relation.naming_declarations] == [
        f"r{i}" for i in range(occurrences)
    ]
    assert [item.target_binding_name for item in relation.join_clauses] == [
        f"r{i}" for i in range(occurrences)
    ]
    assert len({item.span for item in relation.join_clauses}) == occurrences
    for ordinal, clause in enumerate(relation.join_clauses):
        assert clause.uses_named_input and clause.traversal_steps == ()
        assert clause.source_binding_name is None
        assert clause.span.line == 10 + 2 * ordinal
        if kind == "cross":
            assert clause.on_clause is None
        else:
            assert clause.on_clause is not None
            assert isinstance(clause.on_clause.expression, CallExpr)
            assert [
                item.name
                for item in clause.on_clause.expression.arguments
                if isinstance(item, NameExpr)
            ] == ["lhs", f"r{ordinal}"]


def _completed(root: Path, source: str) -> ProjectConcreteCompletedSemanticResult:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    (root / "main.pietto").write_text(source)
    parsed = check_project_parse_only(root)
    assert parsed.ok
    result = build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )
    assert isinstance(result, ProjectConcreteCompletedSemanticResult)
    return result


@pytest.mark.parametrize("owner", ("table", "query"))
@pytest.mark.parametrize("operator", ("union", "intersect", "except"))
def test_set_spans_omission_short_body_and_downstream_failure(
    owner: str, operator: str, tmp_path: Path
) -> None:
    source = (
        BASE
        + f"""{owner} combined:
    {operator}:
        from lhs
query downstream:
    from combined
    select:
        id
query valid:
    from lhs
    select:
        id
"""
    )
    parsed = parse_source(source, path="main.pietto")
    assert parsed.ast is not None
    definition = parsed.ast.definitions[-3]
    assert isinstance(definition, SetRelationDef)
    assert definition.kind.value == owner
    assert definition.body.quantifier is None
    assert definition.body.quantifier_span is None
    assert (
        definition.body.operator_span.line,
        definition.body.operator_span.column,
    ) == (8, 5)
    assert definition.body.operator_span.end_column == 5 + len(operator)
    assert len(definition.body.operands) == 1
    result = _completed(tmp_path, source)
    assert not result.ok
    entries = {
        item.owner.definition.name: item for item in result.effective_outputs.entries
    }
    terminal = entries["combined"]
    assert isinstance(terminal, ProjectEffectiveOutputCompletionTerminal)
    assert isinstance(terminal.base_entry, ProjectEffectiveOutputTerminal)
    base = terminal.base_entry.fragment
    assert base.semantic_facts.select_facts == ()
    assert base.semantic_facts.resolution is None
    assert len(terminal.dependencies) == 1
    assert terminal.dependencies[0].target is entries["lhs"].owner
    assert terminal.dependencies[0].dependency_ordinal == 0
    assert terminal.output is None
    assert any(d.code == "PIE-S2341" for d in result.diagnostics)
    downstream, valid = entries["downstream"], entries["valid"]
    assert isinstance(downstream, ProjectEffectiveOutputCompletionTerminal)
    assert downstream.output is None and downstream.upstream_entry is terminal
    assert (
        isinstance(valid, ProjectExistingEffectiveOutput) and valid.output is not None
    )
    bridge = build_project_query_block_from_relation(
        compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
        owner=base.semantic_facts.owner,
        fragment=base,
    )
    assert isinstance(bridge, ProjectNonConcreteQueryBlock)
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
    )

    snapshot = build_project_query_block_ir(result)
    assert verify_project_query_block_ir(snapshot).verified
    assert tuple(entry.owner for entry in snapshot.entries) == tuple(
        entry.owner for entry in result.effective_outputs.entries
    )
    for entry in snapshot.entries:
        if entry.output is None:
            assert entry.starting_allocation is entry.ending_allocation


def test_supported_set_and_old_cycles_preserve_partial_schedule(
    tmp_path: Path,
) -> None:
    source = (
        NEW_SOURCES[4]
        + """query a:
    from b
    select:
        id
query b:
    from a
    select:
        id
query blocked:
    from a
    select:
        id
query valid:
    from lhs
    select:
        id
"""
    )
    result = _completed(tmp_path, source)
    assert not result.ok
    assert {item.owner.definition.name for item in result.completion.entries} == {
        "lhs",
        "rhs",
        "combined",
        "a",
        "b",
        "blocked",
        "valid",
    }
    topology = result.completion.topology
    assert tuple(owner.definition.name for owner in topology.blocked_owners) == (
        "a",
        "b",
        "blocked",
    )
    assert tuple(owner.definition.name for owner in topology.cycles[0].members) == (
        "a",
        "b",
    )
    original = next(
        d for d in result.semantic_result.diagnostics if d.code == "PIE-S2302"
    )
    assert any(d is original for d in result.diagnostics)
    assert not any(d.code == "PIE-S2334" for d in result.diagnostics)
    current = {
        entry.owner.definition.name: entry for entry in result.effective_outputs.entries
    }
    assert isinstance(current["combined"], ProjectCompletedSetOutput)
    for name in ("a", "b", "blocked"):
        entry = current[name]
        assert isinstance(entry, ProjectEffectiveOutputTerminal)
        assert entry.output is None
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
    )

    snapshot = build_project_query_block_ir(result)
    assert verify_project_query_block_ir(snapshot).verified
    assert tuple(entry.owner for entry in snapshot.entries) == tuple(
        entry.owner for entry in result.effective_outputs.entries
    )
    for entry in snapshot.entries:
        if entry.output is None:
            assert entry.starting_allocation is entry.ending_allocation


@pytest.mark.parametrize(
    "word",
    (
        "cross",
        "right",
        "full",
        "semi",
        "anti",
        "union",
        "intersect",
        "except",
        "all",
        "distinct",
        "values",
        "exists",
        "capture",
        "scalar",
    ),
)
def test_new_words_remain_contextual_names(word: str) -> None:
    source = f"""from "other.pietto" import type {word} as local
export query {word}
shape Row:
    {word}: Int
source {word}: Row = postgres.table("rows")
query result:
    from {word}
    let joined = {word}
    inner join joined on {word}.{word} == joined.{word}
    select:
        {word}.{word}
"""
    parsed = parse_source(source)
    assert parsed.ast is not None and not parsed.diagnostics
    assert isinstance(parsed.ast.definitions[0], ShapeDef)
    assert parsed.ast.definitions[0].fields[0].name == word
    assert isinstance(parsed.ast.module_statements[0], ImportStatement)
    assert parsed.ast.module_statements[0].items[0].exported_name == word


@pytest.mark.parametrize(("kind", "tail"), (("left", " on True"), ("cross", "")))
def test_lateral_uses_existing_join_syntax_over_a_local_relation(
    kind: str, tail: str
) -> None:
    parsed = parse_source(
        "query latest_order:\n"
        "    let latest:\n"
        "        capture customers\n"
        "        from orders\n"
        "        where orders.customer_id == customers.id\n"
        "        select:\n"
        "            id\n"
        "        limit 1\n"
        "    from customers\n"
        "    let l = latest\n"
        f"    {kind} join l{tail}\n"
        "    select:\n"
        "        customer_id = customers.id\n"
        "        last_order = l.id\n"
    )
    assert parsed.ast is not None and not parsed.diagnostics
    (definition,) = parsed.ast.definitions
    assert type(definition) is BlockRelationDef
    assert type(definition.body) is SelectBody
    (join,) = definition.body.join_clauses
    assert join.kind is AuthoredJoinKind(kind)
    assert (join.target_relation_name, join.target_binding_name) == ("l", "l")
    assert join.source_binding_name is None
    assert join.uses_named_input
    assert (type(join.on_clause) is JoinOnClause) is bool(tail)


@pytest.mark.parametrize("suffix", ("\n", ""))
def test_blank_comments_parentheses_windows_qualify_and_eof_keep_spans(
    suffix: str,
) -> None:
    source = (
        BASE
        + """query result:
    from lhs
    let r = rhs
    # refinement

    left join r on (lhs.id == r.id and True)
    let ordered = window(order by lhs.id)
    select:
        id = lhs.id
        rn = row_number() window ordered
    qualify:
        rn <= 1"""
        + suffix
    )
    parsed = parse_source(source, path="layout.pietto")
    assert parsed.ast is not None and not parsed.diagnostics
    relation = parsed.ast.definitions[-1]
    assert isinstance(relation, QueryDef)
    assert len(relation.named_windows) == 1 and relation.qualify_clause is not None
    on = relation.join_clauses[0].on_clause
    assert on is not None
    assert (on.span.line, on.span.column, on.span.end_line) == (12, 17, 12)
    assert relation.naming_declarations[0].span.line == 9


@pytest.mark.parametrize(
    "body",
    (
        "    union all distinct:\n        from lhs\n        from rhs\n",
        "    union all all:\n        from lhs\n        from rhs\n",
        "    union:\n",
        "    union all:\n        lhs\n        rhs\n",
        "    union all:\n        from lhs, rhs\n",
        "    union all:\n        from lhs\n        from rhs\n    limit 1\n",
        "    union by name:\n        from lhs\n        from rhs\n",
        "    union all:\n\tfrom lhs\n        from rhs\n",
    ),
)
def test_malformed_set_bodies_are_syntax_errors(body: str) -> None:
    result = parse_source(BASE + "query result:\n" + body)
    assert result.ast is None and result.diagnostics


@pytest.mark.parametrize(
    "predicate", ("True on False", "True via link: l -> r", "lhs.id = r.id")
)
def test_malformed_on_order_or_assignment_is_rejected(predicate: str) -> None:
    parsed = parse_source(_join("left", predicate))
    assert parsed.ast is None and parsed.diagnostics


def test_scalar_multiline_continuation_is_joined_like_where() -> None:
    on = parse_source(_join("inner", "(lhs.id == r.id\n            and True)"))
    where = parse_source(
        BASE
        + "query q:\n    from lhs\n    where (id == id\n        and True)\n    select:\n        id\n"
    )
    assert on.diagnostics == where.diagnostics == ()
    assert on.ast is not None and where.ast is not None
    joined = on.ast.definitions[-1]
    filtered = where.ast.definitions[-1]
    assert isinstance(joined, QueryDef) and isinstance(filtered, QueryDef)
    on_clause = joined.join_clauses[0].on_clause
    assert on_clause is not None and filtered.where_clause is not None
    spans = (on_clause.expression.span, filtered.where_clause.expression.span)
    assert [(s.line, s.column, s.end_line, s.end_column) for s in spans] == [
        (10, 22, 11, 21),
        (9, 12, 10, 17),
    ]


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("mode", ("loose", "checked", "strict"))
@pytest.mark.parametrize("source", NEW_SOURCES)
def test_public_join_emission_and_set_refusal_follow_dialect_support(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    mode: str,
    source: str,
) -> None:
    path = tmp_path / "main.pietto"
    path.write_text(
        f"mode {mode}\n" + source.replace("postgres.table", f"{dialect}.table")
    )
    for command in (
        ["check", str(path), "--format", "json"],
        ["emit-sql", str(path), "--dialect", dialect, "--format", "json"],
    ):
        refused = source in NEW_SOURCES[4:]
        assert cli.main(command) == int(refused)
        captured = capsys.readouterr()
        assert not captured.err
        document = json.loads(captured.out)
        assert document["ok"] is not refused
        if refused:
            assert any(
                d["code"] == "PIE-S2334" and d["severity"] == "error"
                for d in document["diagnostics"]
            )
            assert not document.get("artifacts", [])
        else:
            assert not document["diagnostics"]
            if command[0] == "emit-sql":
                assert len(document["artifacts"]) == 1


def test_corrupt_set_body_and_omitted_quantifier_spans_are_rejected() -> None:
    parsed = parse_source(NEW_SOURCES[4])
    assert parsed.ast is not None
    relation = parsed.ast.definitions[-1]
    assert isinstance(relation, SetRelationDef)
    with pytest.raises(ValueError, match="omitted"):
        replace(relation.body, quantifier=None)
    with pytest.raises(TypeError, match="operand"):
        replace(relation.body, operands=("lhs",))
    with pytest.raises(TypeError, match="declaration kind"):
        replace(relation, kind="query")


def test_contextual_words_do_not_blanket_reject_ordinary_programs(
    tmp_path: Path,
) -> None:
    result = _completed(
        tmp_path,
        """shape Row:
    distinct: Int
source union: Row = postgres.table("rows")
query except:
    from union
    select:
        distinct
""",
    )
    assert result.ok and not result.diagnostics


def test_package_root_keeps_its_pre_language_selection_boundary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "pietto.toml").write_text(
        '''schema_version = 3
[package]
path = "pkg"
namespace = "test"
name = "example"
version = "1.0.0"
sha256 = "'''
        + "a" * 64
        + """"
"""
    )
    (tmp_path / "main.pietto").write_text(NEW_SOURCES[4])
    parsed = check_project_parse_only(tmp_path)
    assert not parsed.ok and not parsed.parsed_inputs
    assert any(
        "does not use project source selection" in error.message
        for error in parsed.errors
    )
    assert cli.main(["check", "--project", str(tmp_path), "--format", "json"]) == 2
    captured = capsys.readouterr()
    assert not captured.err
    assert not json.loads(captured.out)["ok"]


@pytest.mark.parametrize("newline", ("\n", ""))
def test_set_comments_blank_lines_and_eof_keep_distinct_occurrences(
    newline: str,
) -> None:
    source = (
        """query result:
    # operator comment
    union distinct:
        # operand comment
        from lhs

        from lhs"""
        + newline
    )
    parsed = parse_source(source, path="set-layout.pietto")
    assert parsed.ast is not None and not parsed.diagnostics
    relation = parsed.ast.definitions[0]
    assert isinstance(relation, SetRelationDef)
    assert relation.body.operator_span.line == 3
    assert relation.body.quantifier_span is not None
    assert (
        relation.body.quantifier_span.line,
        relation.body.quantifier_span.column,
    ) == (3, 11)
    assert tuple(operand.span.line for operand in relation.body.operands) == (5, 7)


def test_set_semantic_carrier_rejects_stolen_concrete_source_state(
    tmp_path: Path,
) -> None:
    result = _completed(tmp_path, NEW_SOURCES[4])
    facts = tuple(
        fragment.semantic_facts for fragment in result.completion.plan.fragments
    )
    source_fact = next(fact for fact in facts if fact.owner.definition.name == "lhs")
    set_fact = next(fact for fact in facts if fact.owner.definition.name == "combined")
    assert (
        set_fact.state.reason
        is ProjectRelationRowSchemaReason.RELATIONAL_SYNTAX_UNSUPPORTED
    )
    with pytest.raises(ValueError, match="Set syntax"):
        replace(
            set_fact,
            state=source_fact.state,
            base_row_fact=replace(set_fact.base_row_fact, state=source_fact.state),
        )


def test_precise_earlier_errors_precede_availability_diagnostics() -> None:
    parsed = parse_source(
        "type Duplicate = Int\ntype Duplicate = Text\n" + NEW_SOURCES[4]
    )
    assert parsed.ast is not None
    result = analyze(parsed.ast)
    codes = tuple(d.code for d in result.diagnostics)
    assert codes.index("PIE-S2001") < codes.index("PIE-S2334")


@pytest.mark.parametrize("kind", ("inner", "left"))
def test_parenthesized_on_layouts_preserve_the_same_ast(kind: str) -> None:
    short = parse_source(_join(kind, "lhs.id == r.id and r.id > 0"))
    long = parse_source(_join(kind, "(lhs.id == r.id\n        and r.id > 0)"))
    assert short.diagnostics == long.diagnostics == ()
    assert short.ast is not None and long.ast is not None
    assert layout_free(short.ast) == layout_free(long.ast)


def test_named_cross_join_keeps_optional_parts_absent() -> None:
    result = parse_source(_join("cross"))
    assert result.diagnostics == () and result.ast is not None
    query = result.ast.definitions[-1]
    assert isinstance(query, QueryDef)
    (join,) = query.join_clauses
    assert join.kind is AuthoredJoinKind.CROSS and join.uses_named_input
    assert (join.source_binding_name, join.traversal_steps, join.on_clause) == (
        None,
        (),
        None,
    )
    assert (join.span.line, join.span.column, join.span.end_column) == (10, 5, 17)
    assert query.naming_declarations[0].name == "r"


def test_modern_join_inputs_are_named_separately_and_calls_remain_ordinary() -> None:
    from pietto.ast_nodes import CallExpr

    result = parse_source(
        "query q:\n"
        "    from orders\n"
        "    let buyer = customers\n"
        "    left join buyer on ActiveOrderCustomer(orders, buyer)\n"
        "    let region = regions\n"
        "    left join region on CustomerRegion(buyer, region)\n"
        "    select order_id = orders.id, region_name = region.name\n"
    )
    assert result.diagnostics == ()
    assert result.ast is not None
    query = result.ast.definitions[0]
    assert isinstance(query, QueryDef)
    first, second = query.join_clauses
    assert first.target_relation_name == first.target_binding_name == "buyer"
    assert second.target_relation_name == second.target_binding_name == "region"
    assert first.source_binding_name is None
    assert first.uses_named_input is second.uses_named_input is True
    assert first.target_binding_span is not None
    assert first.target_binding_span.column == 15
    assert first.on_clause is not None and isinstance(
        first.on_clause.expression, CallExpr
    )
    assert second.on_clause is not None and isinstance(
        second.on_clause.expression, CallExpr
    )

    from pietto.parser_api import _parse_legacy_source

    legacy = _parse_legacy_source(
        "query q:\n"
        "    from orders\n"
        "    left join customers as buyer\n"
        "    select: orders.id\n"
    )
    assert legacy.diagnostics == () and legacy.ast is not None
    legacy_query = legacy.ast.definitions[0]
    assert isinstance(legacy_query, QueryDef)
    assert legacy_query.join_clauses[0].source_binding_name is None
    assert legacy_query.join_clauses[0].uses_named_input is False


def test_modern_union_shorthand_preserves_repeated_operand_occurrences() -> None:
    result = parse_source("query all_rows:\n    union all a, b, a\n")
    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, SetRelationDef)
    assert [item.relation_name for item in definition.body.operands] == ["a", "b", "a"]
    assert definition.body.operands[0].span != definition.body.operands[2].span


# Blank lines may follow a one-line set body, as they follow a block body.
@pytest.mark.parametrize(
    "after", ["\n", "\n\n", "\n\nquery other:\n    union all b, a\n"]
)
def test_blank_lines_may_follow_a_one_line_set_body(after: str) -> None:
    result = parse_source("query all_rows:\n    union all a, b" + after)

    assert result.diagnostics == ()
    assert result.ast is not None
    assert [
        [item.relation_name for item in definition.body.operands]
        for definition in result.ast.definitions
        if isinstance(definition, SetRelationDef)
    ] == [["a", "b"], ["b", "a"]][: 1 + after.count("query")]


@pytest.mark.parametrize(
    "entry", [{}, {"single_file": True}, {"explicit_modules": True}]
)
@pytest.mark.parametrize("kind", ["left", "cross"])
def test_modern_named_input_admission_preserves_legacy_source_requirement(
    entry: dict[str, bool], kind: str
) -> None:
    from pietto._syntax_admission import unadmitted_syntax_diagnostics
    from pietto.parser_api import _parse_legacy_source

    condition = " on orders.id == buyer.id" if kind == "left" else ""
    modern = parse_source(
        "query q:\n"
        "    from orders\n"
        "    let buyer = customers\n"
        f"    {kind} join buyer{condition}\n"
        "    select orders.id\n"
    )
    assert modern.diagnostics == () and modern.ast is not None
    assert unadmitted_syntax_diagnostics(modern.ast, **entry) == ()

    legacy_condition = ":" + condition if condition else ""
    legacy = _parse_legacy_source(
        "query q:\n"
        "    from orders\n"
        f"    {kind} join customers as buyer{legacy_condition}\n"
        "    select: orders.id\n"
    )
    assert legacy.diagnostics == () and legacy.ast is not None
    diagnostics = unadmitted_syntax_diagnostics(legacy.ast, **entry)
    assert [(item.code, item.location.line) for item in diagnostics] == [
        ("PIE-S2378", 3)
    ]


def test_modern_any_filters_keep_exact_authored_join_prefixes_and_tail_where() -> None:
    from pietto.ast_nodes import AnyExpr, BinaryExpr, UnaryExpr

    source = (
        "query q:\n"
        "    from orders\n"
        "    where any(Match(orders, buyer) for buyer in customers)\n"
        "    let buyer = customers\n"
        "    left join buyer on Match(orders, buyer)\n"
        "    where:\n"
        "        any(RegionMatch(buyer, region) for region in regions)\n"
        "        not any(Blocked(buyer, banned) for banned in bans)\n"
        "    where any(Match(orders, buyer) for buyer in archived)\n"
        "    let region = regions\n"
        "    left join region on RegionMatch(buyer, region)\n"
        "    where orders.id > 0 or region.id is None\n"
        "    select orders.id\n"
    )
    parsed = parse_source(source, path="any.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    query = parsed.ast.definitions[0]
    assert isinstance(query, QueryDef)
    assert len(query.join_clauses) == 2
    assert [item.preceding_join_count for item in query.join_filters] == [0, 1, 1]
    assert [item.span.line for item in query.join_filters] == [3, 6, 9]
    first, conjunction, repeated = [item.expression for item in query.join_filters]
    assert isinstance(first, AnyExpr) and isinstance(repeated, AnyExpr)
    assert first.binding_name == repeated.binding_name == "buyer"
    assert first.binding_span != repeated.binding_span
    assert first.relation_name == "customers" and repeated.relation_name == "archived"
    assert first.binding_span.line == first.relation_span.line == 3
    line = source.splitlines()[2]
    assert (
        line[first.binding_span.column - 1 : first.binding_span.end_column - 1]
        == "buyer"
    )
    assert (
        line[first.relation_span.column - 1 : first.relation_span.end_column - 1]
        == "customers"
    )
    assert first.binding_span.path == first.relation_span.path == "any.pietto"
    assert isinstance(conjunction, BinaryExpr) and conjunction.operator == "and"
    assert isinstance(conjunction.left, AnyExpr)
    assert (
        isinstance(conjunction.right, UnaryExpr) and conjunction.right.operator == "not"
    )
    assert isinstance(conjunction.right.operand, AnyExpr)
    assert query.where_clause is not None and query.where_clause.span.line == 12
    assert isinstance(query.where_clause.expression, BinaryExpr)
    assert query.where_clause.expression.operator == "or"
    assert [(item.name, item.span.line) for item in query.naming_declarations] == [
        ("buyer", 4),
        ("region", 10),
    ]


def test_modern_any_binder_shadows_parameter_only_inside_its_predicate() -> None:
    from pietto.ast_nodes import (
        AnyExpr,
        BinaryExpr,
        CallExpr,
        NameExpr,
        ParameterRefExpr,
    )

    parsed = parse_source(
        "query q(buyer: Int):\n"
        "    from orders\n"
        "    where any(Match(orders, buyer) for buyer in customers) and buyer > 0\n"
        "    select buyer\n"
    )
    assert parsed.diagnostics == () and parsed.ast is not None
    query = parsed.ast.definitions[0]
    assert isinstance(query, QueryDef) and query.where_clause is not None
    predicate = query.where_clause.expression
    assert isinstance(predicate, BinaryExpr) and isinstance(predicate.left, AnyExpr)
    assert isinstance(predicate.left.predicate, CallExpr)
    bound_row = predicate.left.predicate.arguments[1]
    assert isinstance(bound_row, NameExpr) and bound_row.name == "buyer"
    assert isinstance(predicate.right, ComparisonExpr)
    assert isinstance(predicate.right.left, ParameterRefExpr)
    assert isinstance(query.select_items[0].expression, ParameterRefExpr)
    assert query.join_clauses == query.join_filters == query.naming_declarations == ()


def test_modern_any_binder_restores_capture_scope_after_its_parentheses() -> None:
    from pietto.ast_nodes import AnyExpr, CallExpr, CapturedFieldExpr, DottedNameExpr

    parsed = parse_source(
        "query q:\n"
        "    let inside:\n"
        "        capture buyer\n"
        "        from orders\n"
        "        where any(Match(buyer.id) for buyer in customers)\n"
        "        select buyer.id\n"
        "    from inside\n"
        "    select id\n"
    )
    assert parsed.diagnostics == () and parsed.ast is not None
    query = parsed.ast.definitions[0]
    assert isinstance(query, BlockRelationDef)
    body = query.let_relations[0].body
    assert isinstance(body, SelectBody) and body.where_clause is not None
    expression = body.where_clause.expression
    assert isinstance(expression, AnyExpr) and isinstance(
        expression.predicate, CallExpr
    )
    assert isinstance(expression.predicate.arguments[0], DottedNameExpr)
    assert isinstance(body.select_items[0].expression, CapturedFieldExpr)


@pytest.mark.parametrize(
    "predicate",
    [
        "True",
        "any(True)",
        "any(True for x in rows) or any(False for y in rows)",
        "not (any(True for x in rows) and any(False for y in rows))",
        "any(True for x in rows) == True",
    ],
)
def test_modern_inter_join_where_refuses_nonconjunctive_generator_filters(
    predicate: str,
) -> None:
    parsed = parse_source(
        "query q:\n    from orders\n"
        f"    where {predicate}\n"
        "    cross join customers\n    select orders.id\n"
    )
    assert parsed.ast is None
    assert len(parsed.diagnostics) == 1
    assert "only conjunctions" in parsed.diagnostics[0].message
    assert parsed.diagnostics[0].location.line == 3


@pytest.mark.parametrize(
    "expression",
    [
        "any(True for x in rows for y in rows)",
        "any(True for x in rows if x.id > 0)",
        "any(True for x in rows, False)",
        "other(True for x in rows)",
    ],
)
def test_modern_any_generator_refuses_extra_generator_forms(expression: str) -> None:
    parsed = parse_source(
        f"query q:\n    from orders\n    where {expression}\n    select orders.id\n"
    )
    assert parsed.ast is None
    assert parsed.diagnostics


def _joined(join: str) -> str:
    return BASE + f"query q:\n    from lhs\n{join}    select:\n        id = lhs.id\n"


def test_a_join_binding_name_keeps_its_own_span() -> None:
    result = parse_source(
        _joined(
            "    let r = rhs\n    inner join r\n"
            "    let second = rhs\n    left join second\n"
            "    let r3 = rhs\n    cross join r3\n"
        ),
        path="as.pietto",
    )
    assert result.diagnostics == () and result.ast is not None
    query = result.ast.definitions[-1]
    assert isinstance(query, QueryDef)
    assert [
        None
        if span is None
        else (span.path, span.line, span.column, span.end_line, span.end_column)
        for span in (clause.target_binding_span for clause in query.join_clauses)
    ] == [
        ("as.pietto", 10, 16, 10, 17),
        ("as.pietto", 12, 15, 12, 21),
        ("as.pietto", 14, 16, 14, 18),
    ]
    span = Span(path=None, line=1, column=1, end_line=1, end_column=2)
    built = JoinClause(
        span=span,
        kind=AuthoredJoinKind.INNER,
        target_relation_name="rhs",
        target_binding_name="r",
        source_binding_name=None,
    )
    assert built.target_binding_span is None
