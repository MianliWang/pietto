"""Phase-64 syntax retention, negative admission and existing boundary laws."""

from __future__ import annotations

import pytest
from pathlib import Path
from dataclasses import replace
import json

from pietto.ast_nodes import (
    QueryDef,
    TableDef,
    SetRelationDef,
    ComparisonExpr,
    LiteralExpr,
    ShapeDef,
    ImportStatement,
)
from pietto import cli
from pietto.semantic import analyze
from pietto.ir import build_ir
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
from pietto._project.project_relationship_uses import ProjectNonConcreteJoinUse
from pietto._project.project_query_block_ir import (
    build_project_query_block_ir,
    ProjectIRQueryBlockTerminal,
)
from pietto._project.project_query_block_ir_verification import (
    verify_project_query_block_ir,
    ProjectIRQueryBlockVerificationStatus,
    build_project_query_block_ir_analysis_bundle,
)
from pietto._project.project_query_block_ir_inspection import (
    build_project_query_block_ir_inspection,
)
from pietto._project.project_query_block import (
    build_project_query_block_from_relation,
    ProjectNonConcreteQueryBlock,
)
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.project_phase62_verification import (
    build_project_phase62_analysis_bundle,
)
from pietto._project.project_phase62_inspection import build_project_phase62_inspection
from pietto._project import project_phase62_pure_boundary as phase62_pure

from pietto.parser_api import parse_source


BASE = """shape Row:
    id: Int not null
source lhs: Row is postgres.table("lhs")
source rhs: Row is postgres.table("rhs")
relationship link:
    endpoint l: lhs
    endpoint r: rhs
    on l.id == r.id
"""


def _join(kind: str = "inner", tail: str = "", *, owner: str = "query") -> str:
    return (
        BASE
        + f"""{owner} result:
    from lhs
    {kind} join rhs as r:
        from lhs
{tail}    select:
        id = lhs.id
"""
    )


@pytest.mark.parametrize("kind", ("inner", "left"))
def test_old_join_shape_remains_parseable(kind: str) -> None:
    result = parse_source(_join(kind))
    assert result.ast is not None and not result.diagnostics
    relation = result.ast.definitions[-1]
    assert isinstance(relation, (TableDef, QueryDef))
    assert relation.join_clauses[0].kind.value == kind


@pytest.mark.parametrize(
    "kind", ("inner", "left", "right", "full", "semi", "anti", "cross")
)
def test_located_join_kinds_and_on_retention(kind: str) -> None:
    tail = "" if kind == "cross" else "        on lhs.id == r.id\n"
    result = parse_source(_join(kind, tail), path="joins.pietto")
    assert result.ast is not None and not result.diagnostics
    relation = result.ast.definitions[-1]
    assert isinstance(relation, (TableDef, QueryDef))
    join = relation.join_clauses[0]
    assert join.kind.value == kind
    if kind != "cross":
        assert join.on_clause is not None
        assert type(join.on_clause).__name__ == "JoinOnClause"
        assert join.on_clause.span.line == 13
        assert isinstance(join.on_clause.expression, ComparisonExpr)
        assert join.on_clause.expression.operator == "=="
    else:
        assert join.on_clause is None


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
    _join("inner", "        on false\n"),
    _join("left", "        via link: l -> r\n        on false\n"),
    _join("full"),
    _join("cross"),
    BASE + "query combined:\n    union all:\n        from lhs\n        from rhs\n",
    BASE + "table combined:\n    except:\n        from lhs\n        from lhs\n",
)


@pytest.mark.parametrize("source", NEW_SOURCES)
def test_single_file_and_legacy_ir_reject_new_semantics(source: str) -> None:
    parsed = parse_source(source)
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = analyze(parsed.ast)
    assert any(d.code == "PIE-S2334" for d in semantic.diagnostics)
    lowered = build_ir(parsed.ast, semantic.model)
    assert lowered.ir is None
    assert any(d.code == "PIE-I1000" for d in lowered.diagnostics)


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
    supported = schema == 2 and source in NEW_SOURCES[:4]
    assert result.ok is supported
    assert any(d.code == "PIE-S2334" for d in result.diagnostics) is not supported


@pytest.mark.parametrize(
    "kind", ("inner", "left", "cross", "right", "full", "semi", "anti")
)
@pytest.mark.parametrize("steps", (0, 1, 2))
def test_on_and_via_remain_distinct_from_historical_join_ir(
    kind: str, steps: int, tmp_path: Path
) -> None:
    tail = "        via link: l -> r\n" * steps + "        on false\n"
    source = _join(kind, tail)
    parsed = parse_source(source, path="join.pietto")
    assert parsed.ast is not None
    relation = parsed.ast.definitions[-1]
    assert isinstance(relation, QueryDef)
    clause = relation.join_clauses[0]
    assert len(clause.traversal_steps) == steps
    assert clause.on_clause is not None
    assert isinstance(clause.on_clause.expression, LiteralExpr)
    assert clause.on_clause.expression.value is False
    if steps:
        assert clause.traversal_steps[-1].span.line < clause.on_clause.span.line
    result = _completed(tmp_path, source)
    assert result.ok is (kind in {"inner", "left", "right", "full"} and steps <= 1)
    uses = result.verification.root.join_regions.uses
    ledger = next(
        item for item in uses.ledgers if item.owner.definition.name == "result"
    )
    assert isinstance(ledger.uses[0], ProjectNonConcreteJoinUse)
    assert ledger.uses[0].state.value != "concrete"
    assert len(ledger.uses[0].step_uses) == steps
    assert any(
        issue.kind.value == "syntax_unsupported" for issue in ledger.uses[0].issues
    )


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
    ) == (10, 5)
    assert definition.body.operator_span.end_column == 5 + len(operator)
    assert len(definition.body.operands) == 1
    result = _completed(tmp_path, source)
    assert not result.ok
    entries = {
        item.owner.definition.name: item for item in result.effective_outputs.entries
    }
    assert isinstance(entries["combined"], ProjectEffectiveOutputTerminal)
    assert entries["combined"].fragment.semantic_facts.select_facts == ()
    assert entries["combined"].fragment.semantic_facts.resolution is None
    assert entries["combined"].dependencies == ()  # Set operands await Slice 9.
    assert entries["combined"].output is None
    downstream, valid = entries["downstream"], entries["valid"]
    assert (
        isinstance(downstream, ProjectEffectiveOutputTerminal)
        and downstream.output is None
    )
    assert (
        isinstance(valid, ProjectExistingEffectiveOutput) and valid.output is not None
    )
    base = entries["combined"].fragment
    bridge = build_project_query_block_from_relation(
        compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
        owner=base.semantic_facts.owner,
        fragment=base,
    )
    assert isinstance(bridge, ProjectNonConcreteQueryBlock)
    snapshot = build_project_query_block_ir(result)
    verification = verify_project_query_block_ir(snapshot)
    assert verification.status is ProjectIRQueryBlockVerificationStatus.VERIFIED
    product = build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(verification)
    )
    assert product.canonical_bytes


def test_unsupported_set_and_old_cycles_preserve_partial_schedule(
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
    assert any(d.code == "PIE-S2334" for d in result.diagnostics)
    snapshot = build_project_query_block_ir(result)
    assert (
        verify_project_query_block_ir(snapshot).status
        is ProjectIRQueryBlockVerificationStatus.VERIFIED
    )
    for entry in snapshot.entries:
        if entry.owner.definition.name in {"combined", "a", "b", "blocked"}:
            assert isinstance(entry, ProjectIRQueryBlockTerminal)
            assert entry.output is None


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
    ),
)
def test_new_words_remain_contextual_names(word: str) -> None:
    source = f"""import "other.pietto":
    type {word} as local
export:
    query {word}
shape Row:
    {word}: Int not null
source {word}: Row is postgres.table("rows")
query result:
    from {word}
    inner join {word} as {word}:
        from {word}
    select:
        {word}.{word}
"""
    parsed = parse_source(source)
    assert parsed.ast is not None and not parsed.diagnostics
    assert isinstance(parsed.ast.definitions[0], ShapeDef)
    assert parsed.ast.definitions[0].fields[0].name == word
    assert isinstance(parsed.ast.module_statements[0], ImportStatement)
    assert parsed.ast.module_statements[0].items[0].exported_name == word


@pytest.mark.parametrize("suffix", ("\n", ""))
def test_blank_comments_parentheses_windows_qualify_and_eof_keep_spans(
    suffix: str,
) -> None:
    source = _join(
        "left",
        "        # refinement\n        via link: l -> r\n\n        on (lhs.id == r.id and true)\n",
    )
    source += (
        """        rn = row_number() window ordered
    window ordered:
        order by:
            lhs.id
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
    assert (on.span.line, on.span.column, on.span.end_line) == (16, 9, 16)
    assert relation.join_clauses[0].traversal_steps[0].span.line == 14


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
    "tail",
    (
        "        on true\n        on false\n",
        "        on true\n        via link: l -> r\n",
        "        on lhs.id = r.id\n",
    ),
)
def test_malformed_on_order_or_assignment_is_rejected(tail: str) -> None:
    parsed = parse_source(_join("left", tail))
    assert parsed.ast is None and parsed.diagnostics


def test_scalar_multiline_continuation_matches_existing_where_rejection() -> None:
    on = parse_source(
        _join("inner", "        on (lhs.id == r.id\n            and true)\n")
    )
    where = parse_source(
        BASE
        + "query q:\n    from lhs\n    where (id == id\n        and true)\n    select:\n        id\n"
    )
    assert on.ast is None and where.ast is None
    assert on.diagnostics[0].code == where.diagnostics[0].code == "PIE-P1000"


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("mode", ("loose", "checked", "strict"))
@pytest.mark.parametrize("source", NEW_SOURCES)
def test_public_emit_and_check_cannot_accept_new_forms(
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
        assert cli.main(command) == 1
        captured = capsys.readouterr()
        assert not captured.err
        document = json.loads(captured.out)
        assert not document["ok"]
        assert any(
            d["code"] == "PIE-S2334" and d["severity"] == "error"
            for d in document["diagnostics"]
        )
        assert not document.get("artifacts", [])


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
    distinct: Int not null
source union: Row is postgres.table("rows")
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


@pytest.mark.parametrize(
    "kind", ("inner", "left", "cross", "right", "full", "semi", "anti")
)
def test_phase62_observer_retains_new_negative_uses_but_rejects_concrete_forgery(
    tmp_path: Path, kind: str
) -> None:
    tail = "        on false\n" if kind in {"inner", "left"} else ""
    result = _completed(tmp_path, _join(kind, tail))
    product = build_project_phase62_inspection(
        build_project_phase62_analysis_bundle(result.verification)
    )
    assert product.canonical_bytes
    document = product.document
    position = next(
        i
        for i, record in enumerate(document.records)
        if record.kind is phase62_pure.ProjectPhase62RecordKind.JOIN_USE
    )
    record = document.records[position]
    forged = replace(
        record,
        fields=tuple(
            replace(field, value=replace(field.value, enumeration="concrete"))
            if field.key == "state"
            else field
            for field in record.fields
        ),
    )
    corrupted = replace(
        document,
        records=(
            *document.records[:position],
            forged,
            *document.records[position + 1 :],
        ),
    )
    observed = phase62_pure.evaluate_project_phase62_document(corrupted)
    assert observed.status is not phase62_pure.ProjectPhase62PureStatus.OK
    assert observed.canonical_bytes is None


def test_new_kind_cannot_be_a_phase62_binary_ir_record(tmp_path: Path) -> None:
    result = _completed(tmp_path, _join())
    assert result.ok
    product = build_project_phase62_inspection(
        build_project_phase62_analysis_bundle(result.verification)
    )
    document = product.document
    position = next(
        i
        for i, record in enumerate(document.records)
        if record.kind is phase62_pure.ProjectPhase62RecordKind.BINARY_JOIN
    )
    record = document.records[position]
    forged = replace(
        record,
        fields=tuple(
            replace(field, value=replace(field.value, enumeration="right"))
            if field.key == "kind"
            else field
            for field in record.fields
        ),
    )
    corrupted = replace(
        document,
        records=(
            *document.records[:position],
            forged,
            *document.records[position + 1 :],
        ),
    )
    assert (
        phase62_pure.evaluate_project_phase62_document(corrupted).status
        is not phase62_pure.ProjectPhase62PureStatus.OK
    )


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
    assert "PIE-S2005" in codes  # Existing implicit-nullability warnings survive.
