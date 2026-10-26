from __future__ import annotations

from dataclasses import fields, replace
import json
from pathlib import Path
from typing import cast

import pytest

from _pietto_project_completion import POSITIVE_SOURCE

import pietto.cli as cli
from pietto._project import model as project_model
from pietto._project import project_joined_aggregation as joined_aggregation
from pietto._project import project_joined_qualify as joined_qualify
from pietto._project import project_joined_row_filter as joined_row_filter
from pietto._project import project_joined_windows as joined_windows
from pietto._project import project_scalar_namespaces as scalar_namespaces
from pietto._project import project_completed_semantics as completed_semantics
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.check import check_project_parse_only
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationRowSchemaStatus,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.project_completion import (
    ProjectEffectiveOutputTerminal,
    ProjectExistingEffectiveOutput,
)
from pietto._project.project_final_outputs import (
    ProjectCompletedEffectiveOutput,
    ProjectConcreteNoJoinReplay,
    ProjectNoJoinScalarExpression,
    ProjectNonConcreteRelationLimit,
    ProjectNonConcreteRelationOrdering,
)


from _pietto_project_completed_semantics import (
    REPO_ROOT,
    PRODUCTION,
    CLI,
    JSON_V2,
    SPEC,
    PROJECT_JSON_KEYS,
    PRECISE_FAILURE_SOURCE,
    FALLBACK_FAILURE_SOURCE,
    SOURCE_FAILURE_SOURCE,
    NESTED_WINDOW_FAILURE_SOURCE,
    _Built,
    _project,
    _build,
    positive as positive,
    foreign as foreign,
    diagnostic_matrix as diagnostic_matrix,
    _entry,
    _terminal_entry,
)


def test_concrete_result_closes_exact_existing_chain_and_all_positive_families(
    positive: _Built,
) -> None:
    result = positive.completed
    roots = result.roots
    assert not positive.semantic_result.ok
    assert result.ok
    assert result.diagnostics == ()
    assert result.semantic_result is roots.semantic_result is positive.semantic_result
    assert result.verification is roots.verification
    assert result.completion is roots.completion
    assert result.effective_outputs is roots.effective_outputs
    assert result.completion.verification is result.verification
    assert result.effective_outputs.base is result.completion
    assert (
        result.effective_outputs.joined_qualifies.window_set.aggregation_set.filter_set.completion
        is result.completion
    )
    assert tuple(
        entry.owner.identity.declared_name for entry in result.effective_outputs.entries
    ) == (
        "accounts",
        "events",
        "plain",
        "joined",
        "downstream",
        "grouped",
        "global",
        "qualified",
    )
    assert all(
        type(entry) in {ProjectExistingEffectiveOutput, ProjectCompletedEffectiveOutput}
        for entry in result.effective_outputs.entries
    )
    joined = cast(ProjectCompletedEffectiveOutput, _entry(positive, "joined"))
    downstream = cast(ProjectCompletedEffectiveOutput, _entry(positive, "downstream"))
    grouped = cast(ProjectCompletedEffectiveOutput, _entry(positive, "grouped"))
    global_ = cast(ProjectCompletedEffectiveOutput, _entry(positive, "global"))
    qualified = cast(ProjectCompletedEffectiveOutput, _entry(positive, "qualified"))
    downstream_root = cast(ProjectConcreteNoJoinReplay, downstream.root)
    assert downstream_root.upstream_entry is joined
    assert grouped.row_domain.kind.value == "grouped"
    assert global_.row_domain.kind.value == "global"
    assert tuple(field.output_name for field in qualified.fields) == (
        "event_id",
        "ranked",
    )
    (qualified_authority,) = tuple(
        item
        for tail in result.effective_outputs.current_tails
        for item in tail.results
        if item.window_stage.input_aggregation.input_filter.entry.owner
        is qualified.owner
    )
    assert qualified.root is qualified_authority


@pytest.mark.parametrize(
    ("mode", "reason"),
    (
        (
            ProjectCompilationMode.LEGACY_FLAT,
            completed_semantics.ProjectCompletedSemanticNonConcreteReason.LEGACY_FLAT_MODE,
        ),
        (
            ProjectCompilationMode.PACKAGE_ROOT,
            completed_semantics.ProjectCompletedSemanticNonConcreteReason.PACKAGE_ROOT_MODE,
        ),
    ),
)
def test_direct_builder_is_typed_fail_closed_for_non_positive_modes(
    mode: ProjectCompilationMode,
    reason: completed_semantics.ProjectCompletedSemanticNonConcreteReason,
) -> None:
    semantic = ProjectSemanticResult(
        root=None,
        config_path=None,
        model=None,
        compilation_mode=mode,
    )
    result = completed_semantics.build_project_completed_semantic_result(semantic)
    assert type(result) is completed_semantics.ProjectNonConcreteCompletedSemanticResult
    assert result.semantic_result is semantic
    assert result.reason is reason
    assert result.diagnostics is semantic.diagnostics
    assert result.verification is result.completion is result.effective_outputs is None
    assert not result.ok


def test_module_import_cycles_are_a_typed_terminal_in_builder_check_and_emit_sql(
    tmp_path: Path,
    positive: _Built,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def module(name: str, target: str, target_name: str) -> str:
        return (
            f"shape {name}:\n    id: Int\nexport (\n    shape {name})\n"
            f'from "{target}" import (\n    shape {target_name})\n'
        )

    def public(items: object) -> tuple[tuple[object, ...], ...]:
        facts: list[tuple[object, ...]] = []
        for item in cast(list[dict[str, object]], items):
            location = cast(dict[str, object], item["location"])
            facts.append(
                (
                    item["code"],
                    item["message"],
                    location["path"],
                    location["line"],
                    location["column"],
                )
            )
        return tuple(facts)

    root = tmp_path / "import-cycles"
    root.mkdir()
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    for path, source in {
        "a.pietto": module("A", "b.pietto", "B"),
        "b.pietto": module("B", "a.pietto", "A"),
        "c.pietto": module("C", "d.pietto", "D"),
        "d.pietto": module("D", "c.pietto", "C"),
        "e.pietto": (
            "shape E:\n"
            "    id: Int\n"
            'source rows: E = postgres.table("e")\n'
            "query bad:\n"
            "    from rows\n"
            "    select:\n"
            "        nope\n"
        ),
        # A source connector outside the cycles is still checked.
        "f.pietto": 'shape F:\n    id: Int\nsource bad: F = mysql.table("")\n',
        # Header parameter, WHERE typing and scalar read checks are made while
        # completing relations, so a cycle elsewhere holds them back.
        "g.pietto": (
            "shape G:\n"
            "    id: Int\n"
            "    k: Int\n"
            'source rows: G = postgres.table("g")\n'
            "query p(id: Int, k: Int):\n"
            "    from rows\n"
            "    where id > k\n"
            "    select:\n"
            "        x = rows.id\n"
            "query q:\n"
            "    from rows\n"
            "    where exists p\n"
            "    select:\n"
            "        id\n"
            "query n:\n"
            "    from rows\n"
            '    where 1 == "a"\n'
            "    select:\n"
            "        id\n"
            "        v = scalar rows.nope\n"
        ),
        "contract.json": "{}",
    }.items():
        (root / path).write_text(source, encoding="utf-8")
    expected = (
        (
            "PIE-S2703",
            "Module import cycle detected: a.pietto -> b.pietto -> a.pietto",
            "b.pietto",
            5,
            6,
        ),
        (
            "PIE-S2703",
            "Module import cycle detected: c.pietto -> d.pietto -> c.pietto",
            "d.pietto",
            5,
            6,
        ),
        ("PIE-S2102", "Unknown field: nope", "e.pietto", 7, 9),
        (
            "PIE-S2306",
            "Invalid source connector arguments for mysql.table",
            "f.pietto",
            3,
            17,
        ),
    )

    semantic = build_empty_project_semantic_result(check_project_parse_only(root))
    result = completed_semantics.build_project_completed_semantic_result(semantic)
    assert type(result) is completed_semantics.ProjectNonConcreteCompletedSemanticResult
    assert (
        result.reason
        is completed_semantics.ProjectCompletedSemanticNonConcreteReason.MODULE_IMPORT_CYCLE
    )
    assert result.diagnostics[: len(semantic.diagnostics)] == semantic.diagnostics
    assert result.verification is result.completion is result.effective_outputs is None
    assert not result.ok
    retained = tuple(
        (d.code, d.message, d.location.path, d.location.line, d.location.column)
        for d in result.diagnostics
    )
    assert retained == expected
    for semantic_root, reason in (
        (positive.semantic_result, result.reason),
        (
            semantic,
            completed_semantics.ProjectCompletedSemanticNonConcreteReason.LEGACY_FLAT_MODE,
        ),
    ):
        with pytest.raises(ValueError, match="exact reason"):
            completed_semantics.ProjectNonConcreteCompletedSemanticResult(
                semantic_result=semantic_root,
                reason=reason,
            )

    assert cli.main(["check", "--project", str(root)]) == 1
    text = capsys.readouterr()
    assert text.out == ""
    assert text.err == "".join(
        f"{path}:{line}:{column} {code} error: {message}\n"
        for code, message, path, line, column in expected
    )
    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    document = _read_json(capsys)
    assert tuple(document) == PROJECT_JSON_KEYS
    assert document["ok"] is False
    assert public(document["diagnostics"]) == expected

    emit = ["emit-sql", "--project", str(root), "--module", "e.pietto"]
    emit += ["--kind", "query", "--name", "bad", "--dialect", "postgres"]
    emit += ["--emission-contract", "contract.json", "--format", "json"]
    assert cli.main(emit) == 1
    emitted = _read_json(capsys)
    assert (emitted["status"], emitted["artifact"]) == ("BLOCKED", None)
    assert public(emitted["diagnostics"]) == expected

    # With every cycle fixed, the completed chain reports its own diagnostics
    # after the semantic and source connector ones.
    for path, name in (("b.pietto", "B"), ("d.pietto", "D")):
        (root / path).write_text(
            f"shape {name}:\n    id: Int\nexport (\n    shape {name})\n",
            encoding="utf-8",
        )
    collision = (
        "PIE-S2354",
        "Query parameter name is also a field, let, relation, output or window name.",
        "g.pietto",
        5,
    )
    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    fixed = public(_read_json(capsys)["diagnostics"])
    parameters = (
        (*collision, 9),
        (*collision, 18),
        (
            "PIE-S2356",
            "A query with parameters cannot be the input of another relation.",
            "g.pietto",
            12,
            11,
        ),
    )
    assert fixed[-3:] == parameters
    assert tuple(item for item in fixed if item[2] == "g.pietto") == (
        ("PIE-S2102", "Unknown field: rows.nope", "g.pietto", 20, 13),
        (
            "PIE-S2105",
            "Invalid operands for operator ==: expected comparable operands",
            "g.pietto",
            17,
            11,
        ),
        *parameters,
    )
    assert expected[3] in fixed


def test_completed_roots_reject_equal_looking_foreign_grafts(
    positive: _Built,
    foreign: _Built,
) -> None:
    local = positive.completed
    other = foreign.completed
    assert local.semantic_result is not other.semantic_result
    assert local.verification is not other.verification
    assert local.completion is not other.completion
    assert local.effective_outputs is not other.effective_outputs

    same_completion_foreign_overlay = replace(local.effective_outputs)
    assert same_completion_foreign_overlay is not local.effective_outputs
    with pytest.raises((TypeError, ValueError), match="exact|continuity|init=False"):
        replace(local.roots, effective_outputs=same_completion_foreign_overlay)

    for change in (
        {"verification": other.verification},
        {"completion": other.completion},
        {"effective_outputs": other.effective_outputs},
    ):
        with pytest.raises(
            (TypeError, ValueError), match="exact|continuity|init=False"
        ):
            replace(local.roots, **change)

    with pytest.raises(ValueError, match="Slice-7|exact"):
        replace(
            local.effective_outputs,
            joined_qualifies=other.effective_outputs.joined_qualifies,
        )
    with pytest.raises(ValueError, match="exact|owner-local"):
        replace(
            local.effective_outputs,
            entries=other.effective_outputs.entries,
        )
    with pytest.raises((TypeError, ValueError), match="init=False"):
        replace(local, semantic_result=other.semantic_result)
    with pytest.raises((TypeError, ValueError), match="init=False"):
        replace(local, diagnostics=other.diagnostics)

    exact = replace(local)
    assert exact.roots is local.roots
    assert exact.semantic_result is local.semantic_result
    assert exact.verification is local.verification
    assert exact.completion is local.completion
    assert exact.effective_outputs is local.effective_outputs


def test_no_join_predicate_lets_keep_normalized_typed_roots_and_aliases(
    tmp_path: Path,
) -> None:
    from pietto import ast_nodes as ast
    from pietto._project.let_scope_facts import (
        ProjectLetScopeFactsStatus,
        build_project_relation_let_scope_facts,
    )
    from pietto.semantic.inline_functions import _tree_nodes
    from pietto.semantic.model import ValueTypeKind

    built = _build(
        tmp_path,
        """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
relationship Positive(row: Row):
    row.id > 0
query result:
    from rows
    let keep = Positive(rows) and rows.id > 1
    let alias = keep
    let combined = alias and Positive(rows)
    where combined
    select:
        id
        accepted = alias
""",
    )
    assert built.completed.ok, built.completed.diagnostics
    entry = _entry(built, "result")
    assert type(entry) is ProjectCompletedEffectiveOutput
    replay = entry.root
    assert type(replay) is ProjectConcreteNoJoinReplay
    scope = replay.let_scope
    assert scope.status is ProjectLetScopeFactsStatus.CONCRETE
    assert tuple(scope.binding_expressions) == ("keep", "alias", "combined")
    records = tuple(
        record
        for binding in scope.bindings
        for record in replay.predicate_expressions
        if record.context is binding
    )
    assert len(records) == len(scope.bindings)
    literals = []
    for binding, record in zip(scope.bindings, records, strict=True):
        normalized = scope.binding_expressions[binding.name]
        value_type = scope.value_types[binding.name]
        assert record.owner is entry.owner and record.authored is binding.expression
        assert normalized is record.expression
        assert value_type.kind is ValueTypeKind.KNOWN
        assert value_type.resolved_type.name == "Bool"
        assert scope.expression_value_types[binding.expression] is value_type
        assert scope.expression_value_types[normalized] is value_type
        for node in _tree_nodes(normalized):
            if type(node) is ast.LiteralExpr:
                literals.append(node.value)
                assert scope.expression_value_types[node].resolved_type.name == "Int"
    assert literals == [0, 1, 0]
    assert [len(record.calls) for record in records] == [1, 0, 1]
    assert records[0].calls[0] is not records[2].calls[0]
    where = replay.where.expression_analysis
    assert where is not None and where.let_scope is scope
    assert (
        where.value_type is not None and where.value_type.resolved_type.name == "Bool"
    )
    accepted = entry.fields[1].source
    assert type(accepted) is ProjectNoJoinScalarExpression
    assert accepted.let_scope is scope
    assert accepted.value_type is not None
    assert accepted.value_type.resolved_type.name == "Bool"

    first = scope.bindings[0]
    overrides = {
        binding: record.expression
        for binding, record in zip(scope.bindings, records, strict=True)
    }
    assert scope.definition is not None
    for mapping in (
        {
            binding: value
            for binding, value in overrides.items()
            if binding is not first
        },
        dict(reversed(tuple(overrides.items()))),
        {
            replace(binding) if binding is first else binding: value
            for binding, value in overrides.items()
        },
        {**overrides, replace(first, name="foreign"): records[0].expression},
    ):
        with pytest.raises(ValueError, match="complete exact source order"):
            build_project_relation_let_scope_facts(
                definition=scope.definition,
                input_schema=scope.input_schema,
                upstream_definition=scope.upstream_definition,
                normalized_bindings=mapping,
            )
    normalized = scope.binding_expressions[first.name]
    for expressions in (
        {
            name: value
            for name, value in scope.binding_expressions.items()
            if name != first.name
        },
        {**scope.binding_expressions, first.name: first.expression},
        {**scope.binding_expressions, first.name: replace(normalized)},
    ):
        with pytest.raises(ValueError, match="exact LET normalization"):
            replace(replay, let_scope=replace(scope, binding_expressions=expressions))
    with pytest.raises(ValueError, match="exact LET normalization"):
        replace(replay, predicate_expressions=())


@pytest.mark.parametrize(
    ("declared", "expression", "expected"),
    (
        (True, "Positive(rows) and missing", ("PIE-S2102", "Unknown field: missing")),
        (
            True,
            "Positive(missing)",
            (
                "PIE-S2604",
                "Unavailable row argument for relationship Positive parameter row",
            ),
        ),
        (True, "Missing(1)", ("PIE-S2103", "Unknown function: Missing")),
        (False, "Positive(1)", ("PIE-S2103", "Unknown function: Positive")),
    ),
    ids=(
        "unknown-field",
        "unavailable-row",
        "unknown-function",
        "undeclared-same-name",
    ),
)
def test_no_join_predicate_let_routing_keeps_real_unknown_diagnostics(
    tmp_path: Path, declared: bool, expression: str, expected: tuple[str, str]
) -> None:
    declaration = (
        "relationship Positive(row: Row):\n    row.id > 0\n" if declared else ""
    )
    built = _build(
        tmp_path,
        "shape Row:\n    id: Int\n"
        'source rows: Row = postgres.table("rows")\n'
        + declaration
        + "query result:\n    from rows\n"
        + f"    let keep = {expression}\n"
        + "    select:\n        id\n        accepted = keep\n",
    )
    assert not built.completed.ok
    assert [(item.code, item.message) for item in built.completed.diagnostics] == [
        expected
    ]


@pytest.mark.parametrize("invalid", (False, True))
def test_no_join_any_checks_a_capture_of_an_earlier_normalized_predicate_let(
    tmp_path: Path, invalid: bool
) -> None:
    from pietto._project.existence_values import ProjectAnyLetValue, ProjectAnyValue
    from pietto._project.let_scope_facts import ProjectRelationLetScopeFacts
    from pietto._project.project_final_outputs import (
        ProjectEffectiveOutputCompletionTerminalReason,
    )

    predicate = (
        "keep and candidate.missing > 0" if invalid else "keep and Positive(candidate)"
    )
    built = _build(
        tmp_path,
        "shape Row:\n    id: Int\n"
        'source rows: Row = postgres.table("rows")\n'
        "relationship Positive(row: Row):\n    row.id > 0\n"
        "query result:\n    from rows\n"
        "    let keep = Positive(rows)\n"
        f"    let found = any({predicate} for candidate in rows)\n"
        "    select:\n        id\n        accepted = found\n",
    )
    if invalid:
        assert not built.completed.ok
        terminal = _terminal_entry(built, "result")
        assert (
            terminal.reason
            is ProjectEffectiveOutputCompletionTerminalReason.LET_NON_CONCRETE
        )
        assert terminal.output is None
        assert type(terminal.blocker) is tuple
        (value,) = terminal.blocker
        assert type(value) is ProjectAnyValue and value.diagnostics
        return
    assert built.completed.ok, built.completed.diagnostics
    entry = _entry(built, "result")
    assert type(entry) is ProjectCompletedEffectiveOutput
    assert type(entry.root) is ProjectConcreteNoJoinReplay
    scope = entry.root.let_scope
    (value,) = scope.existence_values
    (capture,) = value.captures
    target = capture.target
    assert type(target) is ProjectAnyLetValue
    assert target.binding is scope.bindings[0]
    assert target.expression is scope.binding_expressions["keep"]
    assert target.expression is not target.binding.expression
    assert type(target.authority) is ProjectRelationLetScopeFacts
    assert target.authority.value_types["keep"] is target.value_type


def test_final_diagnostics_report_an_equal_restated_error_once(
    tmp_path: Path,
) -> None:
    built = _build(tmp_path / "precise", PRECISE_FAILURE_SOURCE)
    result = built.completed
    terminal = next(
        entry
        for entry in result.effective_outputs.entries
        if entry.owner.identity.declared_name == "bad"
    )
    assert type(terminal) is ProjectEffectiveOutputTerminal
    helper_error = terminal.fragment.semantic_facts.helper_diagnostics[0]
    assert not result.ok
    # The relation facts restate the semantic error for the same occurrence;
    # the entry keeps its own object, the public result reports the value once.
    assert helper_error is not built.semantic_result.diagnostics[0]
    assert helper_error == built.semantic_result.diagnostics[0]
    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == ("PIE-S2102",)
    assert result.diagnostics[0] is built.semantic_result.diagnostics[0]
    assert not any(diagnostic.code == "PIE-S2333" for diagnostic in result.diagnostics)


RESTATED_JOIN_HEAD = """shape Row:
    id: Int
    uid: Int
    pk = unique(id)
source rows: Row = postgres.table("rows")
shape U:
    id: Int
    name: Text
    uk = unique(id)
source users: U = postgres.table("users")
query per_user:
    from rows
    group by:
        uid
    select:
        uid
        n = count()
"""
MINUS = "Invalid operands for operator -: expected numeric operands"


def _assert_current_join_inputs(
    built: _Built, name: str, inputs: tuple[str, ...]
) -> None:
    from pietto.ast_nodes import QueryDef
    from pietto._project.project_current_joins import ProjectCurrentBinaryJoin

    output = _entry(built, name)
    (region,) = tuple(
        region
        for region in built.completed.effective_outputs.current_regions
        if region.ledger.owner is output.owner
    )
    scope = region.input_scope
    assert scope is not None
    assert scope.ledger is region.ledger
    assert tuple(item.binding.relation_name for item in scope.bindings) == inputs
    assert len(scope.bindings) == len(region.ledger.bindings) == len(inputs)
    for current, binding, target in zip(
        scope.bindings, region.ledger.bindings, inputs, strict=True
    ):
        assert current.binding is binding
        assert current.authority is not None and current.dependency is not None
        producer = _entry(built, target)
        assert current.authority.entry is producer
        assert current.authority.owner is current.dependency.target is producer.owner
    assert len(region.joins) == len(inputs) - 1
    left_input = region.input_properties[0]
    for position, join in enumerate(region.joins):
        assert type(join) is ProjectCurrentBinaryJoin
        assert join.use is region.ledger.uses[position]
        assert join.condition.ready and join.condition.inputs is not None
        assert join.condition.inputs.scope is scope
        assert join.right_input is region.input_properties[position + 1]
        assert join.left_input is left_input
        left_input = join.properties.relational
    assert type(output) is ProjectCompletedEffectiveOutput
    assert all(field.owner is output.owner for field in output.fields)
    definition = output.owner.definition
    assert type(definition) is QueryDef
    assert len(output.fields) == len(definition.select_items)
    assert all(
        field.item is item
        for field, item in zip(output.fields, definition.select_items, strict=True)
    )


@pytest.mark.parametrize(
    ("body", "inputs"),
    (
        pytest.param(
            "query q:\n    from per_user\n    let x = users\n"
            "    right join x on per_user.uid == x.id\n"
            "    select:\n        uid = per_user.uid\n",
            ("per_user", "users"),
            id="right_grouped_input",
        ),
        pytest.param(
            "query q:\n    from per_user\n    let x = users\n"
            "    inner join x on per_user.uid == x.id\n"
            "    let y = users\n    inner join y on per_user.uid == y.id\n"
            "    select:\n        uid = per_user.uid\n        nm = y.name\n",
            ("per_user", "users", "users"),
            id="two_current_conditions",
        ),
    ),
)
def test_completed_grouped_input_joins_retain_each_current_producer(
    tmp_path: Path, body: str, inputs: tuple[str, ...]
) -> None:
    built = _build(tmp_path, RESTATED_JOIN_HEAD + body)
    assert built.completed.ok, built.completed.diagnostics
    assert built.completed.diagnostics == ()
    _assert_current_join_inputs(built, "q", inputs)
    (region,) = built.completed.effective_outputs.current_regions
    if len(region.joins) == 2:
        first, second = region.joins
        assert first.input_uses[1] is not second.input_uses[1]
        assert first.condition is not second.condition
        assert region.ledger.bindings[1].name == "x"
        assert region.ledger.bindings[2].name == "y"


@pytest.mark.parametrize(
    ("body", "line", "column", "operand_uses"),
    (
        pytest.param(
            "query q:\n    from rows\n    let c = users\n"
            "    left join c on rows.uid == c.id and c.name - 1 > 0\n"
            "    select:\n        id = rows.id\n",
            21,
            41,
            1,
            id="on_error",
        ),
        pytest.param(
            "def twice(x: Int | None) -> Bool | None: return x + x > 0\n"
            "query q:\n    from rows\n    let c = users\n"
            "    left join c on rows.uid == c.id and twice(c.name - 1)\n"
            "    select:\n        id = rows.id\n",
            22,
            47,
            2,
            id="on_error_from_a_def",
        ),
    ),
)
def test_final_diagnostics_report_a_restated_join_condition_error_once(
    tmp_path: Path, body: str, line: int, column: int, operand_uses: int
) -> None:
    from pietto.ast_nodes import BinaryExpr
    from pietto.semantic.inline_functions import _tree_nodes

    built = _build(tmp_path, RESTATED_JOIN_HEAD + body)
    result = built.completed
    assert not result.ok
    assert [
        (d.code, d.location.line, d.location.column, d.message)
        for d in result.diagnostics
    ] == [("PIE-S2105", line, column, MINUS)]
    (condition,) = result.roots.join_conditions.entries
    retained = result.diagnostics[0]
    assert any(diagnostic is retained for diagnostic in condition.diagnostics)
    assert condition.expression is not None
    operands = tuple(
        node
        for node in _tree_nodes(condition.expression)
        if type(node) is BinaryExpr and node.operator == "-"
    )
    assert len(operands) == operand_uses
    assert all(
        (node.span.line, node.span.column) == (line, column) for node in operands
    )


@pytest.mark.parametrize(
    ("second_on", "reference_states", "typed", "second_error"),
    (
        pytest.param(
            "missing.id == d.id",
            ("unknown", "resolved"),
            False,
            ("PIE-S2335", "JOIN ON reference is unknown."),
            id="unknown_reference_after_failed_prefix",
        ),
        pytest.param(
            "1",
            (),
            True,
            ("PIE-S2202", "Expected Bool expression in JOIN ON"),
            id="typed_literal_after_failed_prefix",
        ),
    ),
)
def test_failed_join_prefix_keeps_later_on_gate_and_all_condition_errors(
    tmp_path: Path,
    second_on: str,
    reference_states: tuple[str, ...],
    typed: bool,
    second_error: tuple[str, str],
) -> None:
    from pietto._project.project_final_outputs import (
        ProjectEffectiveOutputCompletionTerminalReason,
    )
    from pietto.errors import SourceLocation

    built = _build(
        tmp_path,
        RESTATED_JOIN_HEAD
        + "query q:\n    from rows\n    let c = users\n"
        + "    left join c on rows.uid == c.id and c.name - 1 > 0\n"
        + "    let d = users\n"
        + f"    left join d on {second_on}\n"
        + "    select:\n        id = rows.id\n",
    )
    result = built.completed
    assert not result.ok
    terminal = _terminal_entry(built, "q")
    assert (
        terminal.reason
        is ProjectEffectiveOutputCompletionTerminalReason.CURRENT_JOIN_CONDITION_NON_CONCRETE
    )
    assert terminal.output is None and terminal.current_region is None
    scope = terminal.current_inputs
    assert scope is not None
    assert tuple(item.binding.name for item in scope.bindings) == ("rows", "c", "d")
    assert all(item.authority is not None for item in scope.bindings)
    first, second = result.roots.join_conditions.entries
    assert first.ledger is second.ledger is scope.ledger
    assert first.ledger.owner is terminal.owner
    assert type(terminal.blocker) is tuple
    assert len(terminal.blocker) == 2
    assert terminal.blocker[0] is first and terminal.blocker[1] is second
    assert not first.ready and not second.ready
    assert first.value_type is not None
    assert first.environment.blocked_bindings == ()
    assert all(reference.target is not None for reference in first.references)
    # Unchanged raw-input conditions may retain their historical carrier;
    # the current attempt's exact ledger and blocker order prove this prefix.
    assert len(scope.ledger.uses) == 2
    assert scope.ledger.uses[0] is first.use
    assert scope.ledger.uses[1] is second.use
    assert len(second.environment.blocked_bindings) == 2
    assert all(
        blocked is current.binding
        for blocked, current in zip(
            second.environment.blocked_bindings, scope.bindings[:2], strict=True
        )
    )
    assert (
        tuple(reference.state.value for reference in second.references)
        == reference_states
    )
    assert (second.value_type is not None) is typed
    if typed:
        assert second.value_type is not None
        assert second.value_type.resolved_type.name == "Int"

    base = terminal.base_entry
    assert type(base) is ProjectEffectiveOutputTerminal
    original_gates = base.fragment.semantic_facts.helper_diagnostics
    assert len(original_gates) == 2
    message = (
        "JOIN-local ON is available only when an EXPLICIT_MODULES project "
        "(schema version 2) completes it."
    )
    for gate, condition, line in zip(
        original_gates, (first, second), (21, 23), strict=True
    ):
        on = condition.use.clause.on_clause
        assert on is not None
        span = on.span
        assert (gate.code, gate.message, span.line, span.column) == (
            "PIE-S2334",
            message,
            line,
            17,
        )
        assert gate.location == SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        )
    first_gate, second_gate = original_gates
    assert len(terminal.diagnostics) == 1
    assert terminal.diagnostics[0] is second_gate
    assert all(diagnostic != first_gate for diagnostic in result.diagnostics)
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in first.diagnostics
    ] == [("PIE-S2105", MINUS, 21, 41)]
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in second.diagnostics
    ] == [
        (
            "PIE-S2335",
            "JOIN pre-match input or relationship authority is unavailable.",
            23,
            5,
        ),
        (*second_error, 23, 20),
    ]
    expected = (second_gate, *first.diagnostics, *second.diagnostics)
    assert len(result.diagnostics) == len(expected)
    assert all(
        actual is retained
        for actual, retained in zip(result.diagnostics, expected, strict=True)
    )
    assert (
        sum(diagnostic is first.diagnostics[0] for diagnostic in result.diagnostics)
        == 1
    )


def test_missing_terminal_errors_receive_one_ordered_public_fallback_each(
    tmp_path: Path,
) -> None:
    built = _build(tmp_path / "fallback", FALLBACK_FAILURE_SOURCE)
    result = built.completed
    assert not result.ok
    # `bad`, whose FROM does not resolve, reports only that, as in a single
    # file; before, a PIE-S2333 at `bad` followed.
    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == (
        "PIE-S2301",
        "PIE-S2333",
    )
    assert tuple(diagnostic.message for diagnostic in result.diagnostics[1:]) == (
        "Project relation semantic completion is unavailable: downstream",
    )
    assert tuple(
        (diagnostic.location.path, diagnostic.location.line, diagnostic.location.column)
        for diagnostic in result.diagnostics[1:]
    ) == (("main.pietto", 5, 1),)
    rendered = " ".join(diagnostic.message for diagnostic in result.diagnostics)
    for private in (
        "HISTORICAL_NON_CONCRETE",
        "UPSTREAM_EFFECTIVE_OUTPUT_NON_CONCRETE",
        "ProjectEffectiveOutputTerminal",
        "ProjectIR",
        "object id",
    ):
        assert private not in rendered


@pytest.mark.parametrize(
    ("body", "expected"),
    (
        (
            'source sa: Row = postgres.table("a")\n'
            'source sa: Row = postgres.table("b")\n',
            [("PIE-S2001", "Duplicate symbol name in relation namespace: sa", 4, 1)],
        ),
        (
            'source sa: Row = postgres.table("a")\n'
            'source sa: Row = postgres.table("b")\n'
            "export (\n"
            "    source sa)\n",
            [("PIE-S2704", "Ambiguous local export declaration: source sa", 6, 12)],
        ),
        (
            "query q:\n    from nowhere\n    select:\n        id\n",
            [("PIE-S2301", "Unknown relation: nowhere", 4, 5)],
        ),
    ),
    ids=("duplicate", "exported_duplicate", "unknown_from"),
)
def test_a_relation_whose_name_or_from_does_not_resolve_reports_only_why(
    tmp_path: Path,
    body: str,
    expected: list[tuple[str, str, int, int]],
) -> None:
    """A source, table or query whose own name or FROM does not resolve gets
    only the error that says why, as in a single file. Before, each such
    declaration also reported a bare PIE-S2333."""
    built = _build(tmp_path, "shape Row:\n    id: Int\n" + body)
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in built.completed.diagnostics
    ] == expected


_DEFERRED_JOIN_INPUT_SOURCE = """shape Sale:
    id: Int
    uid: Int
    amount: Int
shape User:
    id: Int
    name: Text
source sales: Sale = postgres.table("sales")
source users: User = postgres.table("users")
query per_user:
    from sales
    group by:
        uid
    select:
        uid
        total = sum(amount)
query ranked:
    from sales
    select:
        uid
        rn = row_number() window(order by id)
query bound:
    from sales
    let key = uid
    select:
        uid = key
query copied:
    from per_user
    select:
        uid
query nested:
    let picked:
        from sales
        select:
            uid
    from picked
    select:
        uid
query grouped_input:
    from per_user
    let x = users
    inner join x on per_user.uid == x.id
    select:
        n = x.name
query grouped_left:
    from per_user
    let x = users
    left join x on per_user.uid == x.id
    select:
        n = x.name
query grouped_twice:
    from per_user
    let x = users
    inner join x on per_user.uid == x.id
    let y = sales
    inner join y on per_user.uid == y.uid
    select:
        n = x.name
query windowed:
    from ranked
    let x = users
    inner join x on ranked.uid == x.id
    select:
        n = x.name
query let_bound:
    from bound
    let x = users
    inner join x on bound.uid == x.id
    select:
        n = x.name
query chained:
    from copied
    let x = users
    inner join x on copied.uid == x.id
    select:
        n = x.name
query relation_let:
    from nested
    let x = users
    inner join x on nested.uid == x.id
    select:
        n = x.name
query grouped_target:
    from users
    let x = per_user
    inner join x on users.id == x.uid
    select:
        t = x.total
query grouped_on:
    from per_user
    let x = users
    inner join x on per_user.uid == x.id
    select:
        n = x.name
query reads_grouped:
    from grouped_input
    select:
        n
"""


def test_current_joins_keep_completed_input_and_downstream_output_identities(
    tmp_path: Path,
) -> None:
    from pietto._project.model import ProjectRowFieldNullability

    built = _build(tmp_path / "completed-join-input", _DEFERRED_JOIN_INPUT_SOURCE)
    assert built.completed.ok, built.completed.diagnostics
    assert built.completed.diagnostics == ()
    # Dependency-first FIFO scheduling releases all per_user readers before
    # ranked/bound readers, then copied and the nested relation-let reader.
    expected = (
        ("grouped_input", ("per_user", "users")),
        ("grouped_left", ("per_user", "users")),
        ("grouped_twice", ("per_user", "users", "sales")),
        ("grouped_target", ("users", "per_user")),
        ("grouped_on", ("per_user", "users")),
        ("windowed", ("ranked", "users")),
        ("let_bound", ("bound", "users")),
        ("chained", ("copied", "users")),
        ("relation_let", ("nested", "users")),
    )
    assert tuple(
        region.ledger.owner.identity.declared_name
        for region in built.completed.effective_outputs.current_regions
    ) == tuple(name for name, _ in expected)
    for name, inputs in expected:
        _assert_current_join_inputs(built, name, inputs)
        output = cast(ProjectCompletedEffectiveOutput, _entry(built, name))
        assert tuple(field.output_name for field in output.fields) == (
            "t" if name == "grouped_target" else "n",
        )
    left = cast(ProjectCompletedEffectiveOutput, _entry(built, "grouped_left"))
    assert left.fields[0].field.nullability is ProjectRowFieldNullability.NULLABLE
    for name, producer in (("copied", "per_user"), ("reads_grouped", "grouped_input")):
        entry = _entry(built, name)
        (dependency,) = entry.dependencies
        assert dependency.target is _entry(built, producer).owner
    downstream = cast(ProjectCompletedEffectiveOutput, _entry(built, "reads_grouped"))
    assert type(downstream.root) is ProjectConcreteNoJoinReplay
    assert downstream.root.upstream_entry is _entry(built, "grouped_input")
    nested = _entry(built, "nested")
    (dependency,) = nested.dependencies
    (picked,) = tuple(
        entry
        for entry in built.completed.effective_outputs.entries
        if entry.owner is dependency.target
    )
    assert picked.owner.definition.name == "picked"
    assert dependency.consumer is nested.owner


def test_non_concrete_source_relation_receives_public_fallback_without_traceback(
    tmp_path: Path,
) -> None:
    built = _build(tmp_path / "source-failure", SOURCE_FAILURE_SOURCE)
    result = built.completed
    assert not result.ok
    fallbacks = tuple(
        diagnostic
        for diagnostic in result.diagnostics
        if diagnostic.code == "PIE-S2333"
    )
    assert len(fallbacks) == 1
    assert fallbacks[0].message == (
        "Project relation semantic completion is unavailable: rows"
    )
    assert (
        fallbacks[0].location.path,
        fallbacks[0].location.line,
        fallbacks[0].location.column,
    ) == ("main.pietto", 1, 1)


def test_nested_window_error_is_retained_by_identity_instead_of_fallback(
    tmp_path: Path,
) -> None:
    built = _build(tmp_path / "nested-window", NESTED_WINDOW_FAILURE_SOURCE)
    entry = next(
        item
        for item in built.completed.effective_outputs.entries
        if item.owner.identity.declared_name == "result"
    )
    assert type(entry) is ProjectEffectiveOutputTerminal
    retained = entry.fragment.semantic_facts.window_outputs[0].diagnostics[0]
    assert retained.code == "PIE-S2103"
    assert any(diagnostic is retained for diagnostic in built.completed.diagnostics)
    assert not any(
        diagnostic.code == "PIE-S2333" for diagnostic in built.completed.diagnostics
    )


def test_nested_where_scalar_error_is_retained_by_identity(
    diagnostic_matrix: _Built,
) -> None:
    entry = _terminal_entry(diagnostic_matrix, "where_bad")
    qualify = entry.joined_qualify
    assert type(qualify) is joined_qualify.ProjectNonConcreteJoinedQualify
    stage = qualify.window_stage
    assert type(stage) is joined_windows.ProjectNonConcreteJoinedWindowStage
    aggregation = stage.input_aggregation
    assert type(aggregation) is joined_aggregation.ProjectNonConcreteJoinedAggregation
    row_filter = aggregation.input_filter
    assert type(row_filter) is joined_row_filter.ProjectNonConcreteJoinedRowFilter
    retained = row_filter.diagnostics[0]
    assert retained.code == "PIE-S2103"
    assert any(
        diagnostic is retained for diagnostic in diagnostic_matrix.completed.diagnostics
    )
    assert not any(
        diagnostic.code == "PIE-S2333" and diagnostic.message.endswith("where_bad")
        for diagnostic in diagnostic_matrix.completed.diagnostics
    )

    replay = _terminal_entry(diagnostic_matrix, "downstream_where_bad")
    replay_blocker = replay.blocker
    assert type(replay_blocker) is ProjectNoJoinScalarExpression
    assert replay.replay_root is not None
    assert replay.replay_root.blocker is replay_blocker
    replay_error = replay_blocker.diagnostics[0]
    assert replay_error.code == "PIE-S2103"
    assert any(
        diagnostic is replay_error
        for diagnostic in diagnostic_matrix.completed.diagnostics
    )
    assert (
        sum(
            diagnostic is replay_error
            for diagnostic in completed_semantics._entry_error_diagnostics(replay)
        )
        == 1
    )


def test_qualify_error_is_retained_by_identity_without_fallback(
    diagnostic_matrix: _Built,
) -> None:
    entry = _terminal_entry(diagnostic_matrix, "qualify_bad")
    blocker = entry.blocker
    assert type(blocker) is joined_qualify.ProjectNonConcreteJoinedQualify
    retained = blocker.diagnostics[0]
    assert retained.code == "PIE-S2332"
    assert any(
        diagnostic is retained for diagnostic in diagnostic_matrix.completed.diagnostics
    )
    assert not any(
        diagnostic.code == "PIE-S2333" and diagnostic.message.endswith("qualify_bad")
        for diagnostic in diagnostic_matrix.completed.diagnostics
    )


def test_order_terminal_projects_exact_blocker_error_before_fallback(
    diagnostic_matrix: _Built,
) -> None:
    entry = _terminal_entry(diagnostic_matrix, "order_precise")
    blocker = entry.blocker
    assert type(blocker) is ProjectNonConcreteRelationOrdering
    retained = blocker.diagnostics[0]
    assert retained.code == "PIE-S2321"
    assert any(
        diagnostic is retained for diagnostic in diagnostic_matrix.completed.diagnostics
    )
    assert not any(
        diagnostic.code == "PIE-S2333" and diagnostic.message.endswith("order_precise")
        for diagnostic in diagnostic_matrix.completed.diagnostics
    )


def test_superseded_base_diagnostic_is_not_a_current_terminal_error(
    diagnostic_matrix: _Built,
) -> None:
    entry = _terminal_entry(diagnostic_matrix, "order_bad")
    blocker = entry.blocker
    assert type(blocker) is ProjectNonConcreteRelationOrdering
    assert (
        type(blocker.blocker)
        is scalar_namespaces.ProjectNonConcreteJoinedNamespaceExpression
    )
    current = entry.joined_qualify
    assert type(current) is joined_qualify.ProjectConcreteJoinedQualify
    assert type(current.window_stage) is joined_windows.ProjectConcreteJoinedWindowStage
    superseded = entry.base_entry.fragment.semantic_facts.window_outputs[0].diagnostics[
        0
    ]
    assert superseded.code == "PIE-S2103"
    assert not any(
        diagnostic is superseded
        for diagnostic in diagnostic_matrix.completed.diagnostics
    )
    assert (
        sum(
            diagnostic.code == "PIE-S2333" and diagnostic.message.endswith("order_bad")
            for diagnostic in diagnostic_matrix.completed.diagnostics
        )
        == 1
    )


def test_limit_error_identity_dedup_and_equal_value_multiplicity_are_exact(
    diagnostic_matrix: _Built,
) -> None:
    entry = _terminal_entry(diagnostic_matrix, "limit_bad")
    blocker = entry.blocker
    assert type(blocker) is ProjectNonConcreteRelationLimit
    retained = blocker.diagnostics[0]
    assert retained.code == "PIE-S2307"
    assert entry.diagnostics[0] is retained
    raw = completed_semantics._diagnostics_from_carrier(entry)
    assert sum(diagnostic is retained for diagnostic in raw) == 2
    projected = completed_semantics._entry_error_diagnostics(entry)
    assert tuple(diagnostic for diagnostic in projected if diagnostic is retained) == (
        retained,
    )

    equal_but_distinct = replace(retained)
    assert equal_but_distinct == retained and equal_but_distinct is not retained
    foreign_blocker = replace(blocker, diagnostics=(equal_but_distinct,))
    grafted = replace(entry, blocker=foreign_blocker)
    distinct_projection = completed_semantics._entry_error_diagnostics(grafted)
    assert distinct_projection[:2] == (retained, equal_but_distinct)
    assert distinct_projection[0] is retained
    assert distinct_projection[1] is equal_but_distinct


def test_explicit_project_cli_uses_completed_success_with_unchanged_text_and_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(tmp_path / "cli-success", POSITIVE_SOURCE)
    semantic_builder = project_model.build_empty_project_semantic_result
    completed_builder = completed_semantics.build_project_completed_semantic_result
    semantic_results: list[ProjectSemanticResult] = []
    completed_results: list[completed_semantics.ProjectCompletedSemanticResult] = []

    def build_semantic(parse_result: ProjectParseCheckResult) -> ProjectSemanticResult:
        result = semantic_builder(parse_result)
        semantic_results.append(result)
        return result

    def build_completed(
        semantic_result: ProjectSemanticResult,
    ) -> completed_semantics.ProjectCompletedSemanticResult:
        result = completed_builder(semantic_result)
        completed_results.append(result)
        return result

    monkeypatch.setattr(
        project_model, "build_empty_project_semantic_result", build_semantic
    )
    monkeypatch.setattr(
        completed_semantics, "build_project_completed_semantic_result", build_completed
    )

    assert cli.main(["check", "--project", str(root)]) == 0
    text = capsys.readouterr()
    assert text.out == "Project check OK: .\nFiles checked: 1\n"
    assert text.err == ""
    assert not semantic_results[-1].ok
    assert completed_results[-1].ok

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 0
    document = _read_json(capsys)
    assert tuple(document) == PROJECT_JSON_KEYS
    assert document["schema_version"] == 2
    assert document["ok"] is completed_results[-1].ok is True
    assert document["diagnostics"] == []
    serialized = json.dumps(document)
    for private in (
        "completion",
        "effective_outputs",
        "field identities",
        "ProjectIR",
        "terminal reason",
    ):
        assert private not in serialized


def test_explicit_project_cli_renders_completed_failure_in_text_and_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(tmp_path / "cli-failure", FALLBACK_FAILURE_SOURCE)

    assert cli.main(["check", "--project", str(root)]) == 1
    text = capsys.readouterr()
    assert text.out == ""
    assert text.err == (
        "main.pietto:2:5 PIE-S2301 error: Unknown relation: missing\n"
        "main.pietto:5:1 PIE-S2333 error: Project relation semantic completion "
        "is unavailable: downstream\n"
    )

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    document = _read_json(capsys)
    assert tuple(document) == PROJECT_JSON_KEYS
    assert document["ok"] is False
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert tuple(item["code"] for item in diagnostics) == ("PIE-S2301", "PIE-S2333")
    assert document["result"] == {
        "check": {
            "files_total": 1,
            "files_ok": 1,
            "files_with_errors": 0,
        }
    }


def test_explicit_project_cli_shares_the_comparison_family_check(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(
        tmp_path / "cli-comparison",
        "shape Row:\n"
        "    id: Int\n"
        'source rows: Row = postgres.table("app.rows")\n'
        "query result:\n"
        "    from rows\n"
        '    where id == "x"\n'
        "    select:\n"
        "        id\n",
    )

    assert cli.main(["check", "--project", str(root)]) == 1
    text = capsys.readouterr()
    assert text.out == ""
    assert text.err == (
        "main.pietto:6:11 PIE-S2105 error: Invalid operands for operator ==: "
        "expected comparable operands\n"
    )


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            '    where name like "a!"\n    select:\n        id\n',
            "main.pietto:7:11 PIE-S2105 error: Invalid operands for operator like: "
            "expected a pattern that does not end in the escape character ! "
            "(write !! for a literal !)\n",
        ),
        (
            '\n    let p = "a!"\n    where name like p\n    select:\n        id\n',
            "main.pietto:9:11 PIE-S2105 error: Invalid operands for operator like: "
            "expected a pattern that does not end in the escape character ! "
            "(write !! for a literal !)\n",
        ),
        (
            '\n    let p = "a!"\n    select:\n        id\n        m = name like p\n',
            "main.pietto:11:13 PIE-S2105 error: Invalid operands for operator like: "
            "expected a pattern that does not end in the escape character ! "
            "(write !! for a literal !)\n",
        ),
        (
            "\n"
            '    let p = "a!"\n'
            "    let m = name like p\n"
            "    where m\n"
            "    select:\n"
            "        id\n",
            "main.pietto:9:13 PIE-S2105 error: Invalid operands for operator like: "
            "expected a pattern that does not end in the escape character ! "
            "(write !! for a literal !)\n",
        ),
        (
            "    select:\n        id\n        c = Float(None)\n",
            "main.pietto:9:13 PIE-S2105 error: Invalid cast from null to Float: "
            "only Int-to-Float conversion is supported; write Float(expression)\n",
        ),
    ],
    ids=(
        "like-literal",
        "like-let-where",
        "like-let-select",
        "like-let-binding",
        "cast-null",
    ),
)
def test_explicit_project_check_refuses_like_escape_and_null_cast(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    body: str,
    expected: str,
) -> None:
    root = _project(
        tmp_path / "q1",
        "shape Row:\n"
        "    id: Int\n"
        "    name: Text\n"
        'source rows: Row = postgres.table("app.rows")\n'
        "query result:\n"
        "    from rows\n" + body,
    )

    # Before: like "a!" through a let and cast(null) passed or gave PIE-S2333.
    assert cli.main(["check", "--project", str(root)]) == 1
    text = capsys.readouterr()
    assert text.out == ""
    assert text.err == expected


_LIKE_PATTERN = (
    "PIE-S2105 error: Invalid operands for operator like: expected a pattern "
    "that does not end in the escape character ! (write !! for a literal !)\n"
)
_UNAVAILABLE = (
    "main.pietto:5:1 PIE-S2333 error: Project relation semantic completion is "
    "unavailable: result\n"
)


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            "\n    let n = None\n    select:\n        id\n        f = n\n",
            _UNAVAILABLE,
        ),
        (
            "\n    let n = None\n    select:\n        id\n        n\n",
            _UNAVAILABLE,
        ),
        (
            "\n    let n = None\n    select:\n        id\n        f = n is None\n",
            _UNAVAILABLE,
        ),
        (
            '\n    let m = name like "a!"\n    select:\n        id\n        mm = m\n',
            "main.pietto:8:13 " + _LIKE_PATTERN,
        ),
        (
            "\n"
            '    let p = "a!"\n'
            "    let m = name like p\n"
            "    select:\n"
            "        id\n"
            "        mm = m\n",
            "main.pietto:9:13 " + _LIKE_PATTERN,
        ),
        (
            "\n"
            "    let n = None\n"
            "    let c = Float(n)\n"
            "    select:\n"
            "        id\n"
            "        cc = c\n",
            "main.pietto:9:13 PIE-S2105 error: Invalid cast from null to Float: "
            "only Int-to-Float conversion is supported; write Float(expression)\n",
        ),
        (
            "\n"
            '    let p = "a!"\n'
            "    let n = None\n"
            "    select:\n"
            "        id\n"
            "        m = name like p\n",
            "main.pietto:12:13 " + _LIKE_PATTERN,
        ),
        (
            "\n"
            "    let n = None\n"
            "    let n = 1\n"
            "    select:\n"
            "        id\n"
            "        a = n\n",
            "main.pietto:9:5 PIE-S2604 error: Duplicate query local name: n\n",
        ),
        (
            "\n    let f = zz\n    select:\n        id\n        g = f\n",
            "main.pietto:8:13 PIE-S2102 error: Unknown field: zz\n",
        ),
        (
            "\n    let n = 1\n    let n = 2\n    select:\n        id\n        f = n\n",
            "main.pietto:9:5 PIE-S2604 error: Duplicate query local name: n\n",
        ),
        (
            "\n"
            "    let n = None\n"
            "    select:\n"
            "        id\n"
            "        f = n\n"
            "        g = zz\n"
            "        h = rows.n\n",
            "main.pietto:12:13 PIE-S2102 error: Unknown field: zz\n"
            "main.pietto:13:13 PIE-S2102 error: Unknown field: rows.n\n",
        ),
    ],
    ids=(
        "unknown-type-aliased",
        "unknown-type-unaliased",
        "unknown-type-in-expression",
        "own-error",
        "own-error-through-let",
        "null-cast-through-let",
        "like-pattern-let-beside-untyped-let",
        "duplicate-untyped-let",
        "unknown-name-in-let",
        "duplicate-let",
        "other-names-stay-unknown",
    ),
)
def test_explicit_project_select_read_of_an_untyped_let_is_not_an_unknown_field(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    body: str,
    expected: str,
) -> None:
    root = _project(
        tmp_path / "q1",
        "shape Row:\n"
        "    id: Int\n"
        "    name: Text\n"
        'source rows: Row = postgres.table("app.rows")\n'
        "query result:\n"
        "    from rows\n" + body,
    )

    # Before: each read of the let was also PIE-S2102 "Unknown field".
    assert cli.main(["check", "--project", str(root)]) == 1
    text = capsys.readouterr()
    assert text.out == ""
    assert text.err == expected


def test_explicit_project_order_keys_follow_the_name_rule_after_select(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(
        tmp_path / "order-names",
        "shape AccountRow:\n    id: Int\n    name: Text\n"
        "    account_key = unique(id)\n"
        "shape EventRow:\n    id: Int\n    account_id: Int\n"
        "    kind: Text\n"
        'source accounts: AccountRow = postgres.table("accounts")\n'
        'source events: EventRow = postgres.table("events")\n'
        "query renamed:\n    from events\n    select id, label = lower(kind)\n"
        "    order by label\n"
        "query shadowed:\n    from events\n    select id, kind = lower(kind)\n"
        "    order by kind\n"
        "query joined_output:\n    from events\n"
        "    inner join accounts on events.account_id == accounts.id\n"
        "    select id = events.id, who = accounts.name\n    order by who\n"
        "query joined_shadow:\n    from events\n"
        "    inner join accounts on events.account_id == accounts.id\n"
        "    select id = events.id, kind = lower(events.kind)\n    order by kind\n"
        "query joined_let:\n    from events\n"
        "    inner join accounts on events.account_id == accounts.id\n"
        "    let who = accounts.name\n    select id = events.id, who\n"
        "    order by who\n",
    )
    ambiguous = (
        "PIE-S2102 error: Ambiguous field: kind is both the input field "
        "events.kind and a SELECT output; write events.kind, or give the output "
        "another name\n"
    )

    # Before: both `kind` keys silently sorted by the input field, and `who`
    # after a JOIN said an ORDER BY key cannot name a SELECT output. A key that
    # names only an output passes without JOIN inputs; project SQL does not yet
    # order by one.
    assert cli.main(["check", "--project", str(root)]) == 1
    text = capsys.readouterr()
    assert text.out == ""
    assert text.err == (
        f"main.pietto:18:14 {ambiguous}"
        "main.pietto:23:14 PIE-S2102 error: Unknown field: who; a project relation "
        "with JOIN inputs cannot order by a SELECT output yet (restate its "
        "expression, or bind it with `let` and order by that name)\n"
        f"main.pietto:28:14 {ambiguous}"
    )


_SPEC_JOIN = "    let p = oth\n\n    inner join p on src.id == p.ref\n"
_UNSUPPORTED_WINDOW = "PIE-S2103 error: Unsupported window computation for function"


def test_explicit_project_window_specification_read_of_a_computed_let(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A PARTITION BY or ORDER BY name of a scalar `let` binding whose value is not
    a field is refused as that value written in its place is, at the window
    call, with or without JOIN inputs, grouped and in QUALIFY; a binding that
    names a field stays a field (`alias`)."""

    root = _project(
        tmp_path / "windows",
        """shape S:
    id: Int
    t: Text | None
    u: Text
    s_key = unique(id)
shape O:
    oid: Int
    ref: Int | None
    label: Text | None
    o_key = unique(oid)
source src: S = postgres.table("app.src")
source oth: O = postgres.table("app.oth")
table plain:
    from src

    let k = lower(t)
    select:
        id
        r = first_value(u) window(
            order by
                k)
table joined:
    from src
"""
        + _SPEC_JOIN
        + """
    let k = lower(p.label)
    select:
        id = src.id
        r = first_value(src.u) window(
            partition by
                k
            order by
                src.id)
table alias:
    from src
"""
        + _SPEC_JOIN
        + """
    let k = p.label
    select:
        id = src.id
        r = first_value(src.u) window(
            order by
                k)
query grouped:
    from src

    let k = lower(t)
    group by:
        k
    select:
        k
        n = count()
        r = rank() window(
            order by
                k)
query hidden:
    from src

    let k = lower(t)
    select:
        id
    qualify:
        row_number() window(
            order by
                k
        ) <= 3
query hidden_joined:
    from src
"""
        + _SPEC_JOIN
        + """
    let k = lower(src.t)
    select:
        id = src.id
    qualify:
        row_number() window(
            order by
                k
        ) <= 3
""",
    )

    # Before: PIE-S2102 "Unknown field: k" at each read of `k`.
    assert cli.main(["check", "--project", str(root)]) == 1
    text = capsys.readouterr()
    assert text.out == ""
    order = "window order expression must be a direct field"
    assert text.err == (
        f"main.pietto:19:13 {_UNSUPPORTED_WINDOW} first_value: {order}\n"
        f"main.pietto:31:13 {_UNSUPPORTED_WINDOW} first_value: window partition "
        "expression must be a direct field\n"
        f"main.pietto:57:13 {_UNSUPPORTED_WINDOW} rank: {order}\n"
        f"main.pietto:67:9 {_UNSUPPORTED_WINDOW} row_number: {order}\n"
        f"main.pietto:81:9 {_UNSUPPORTED_WINDOW} row_number: {order}\n"
    )


_NEVER_TRUE = "comparison with null is never true"


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            "    where age == None\n    select:\n        id\n",
            f"main.pietto:7:11 PIE-S2105 error: Invalid operands for operator ==: "
            f"{_NEVER_TRUE}; write `is None` instead\n",
        ),
        (
            "    where None != age\n    select:\n        id\n",
            f"main.pietto:7:11 PIE-S2105 error: Invalid operands for operator !=: "
            f"{_NEVER_TRUE}; write `is not None` instead\n",
        ),
        (
            "    select:\n        id\n        f = age >= None\n",
            f"main.pietto:9:13 PIE-S2105 error: Invalid operands for operator >=: "
            f"{_NEVER_TRUE}\n",
        ),
        (
            "\n"
            "    let nothing = None\n"
            "    let f = age < nothing\n"
            "    where f\n"
            "    select:\n"
            "        id\n",
            f"main.pietto:9:13 PIE-S2105 error: Invalid operands for operator <: "
            f"{_NEVER_TRUE}\n",
        ),
        (
            "    where None <= age <= None\n    select:\n        id\n",
            f"main.pietto:7:11 PIE-S2105 error: Invalid operands for operator between: "
            f"{_NEVER_TRUE}\n",
        ),
        (
            "    where age not in (None)\n    select:\n        id\n",
            f"main.pietto:7:11 PIE-S2105 error: Invalid operands for operator not in: "
            f"{_NEVER_TRUE}; write `is not None` instead\n",
        ),
    ],
    ids=("where-eq", "where-ne", "select", "let", "between", "not-in"),
)
def test_explicit_project_check_refuses_comparison_with_null(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    body: str,
    expected: str,
) -> None:
    root = _project(
        tmp_path / "null-comparison",
        "shape Row:\n"
        "    id: Int\n"
        "    age: Int | None\n"
        'source rows: Row = postgres.table("app.rows")\n'
        "query result:\n"
        "    from rows\n" + body,
    )

    # Before: each passed check, or the SELECT one gave PIE-S2333.
    assert cli.main(["check", "--project", str(root)]) == 1
    text = capsys.readouterr()
    assert text.out == ""
    assert text.err == expected


def test_project_and_single_file_checks_agree_on_alias_comparison_operands(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(
        tmp_path / "alias-comparison",
        "type Age = Int\n"
        "type Years = Age\n"
        "type Tag = Text\n"
        "shape Row:\n"
        "    id: Int\n"
        "    age: Age\n"
        "    years: Years\n"
        "    tag: Tag\n"
        'source rows: Row = postgres.table("app.rows")\n'
        "query by_where:\n"
        "    from rows\n"
        '    where years == "x"\n'
        "    select:\n"
        "        id\n"
        "query by_select:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        '        flag = age == "x"\n'
        "query by_let:\n"
        "    from rows\n"
        "\n"
        "    let bad = tag > 5\n"
        "    where bad\n"
        "    select:\n"
        "        id\n"
        "query same_family:\n"
        "    from rows\n"
        '    where years >= age and tag == "x"\n'
        "    select:\n"
        "        id\n",
    )

    def facts(document: dict[str, object]) -> list[tuple[object, ...]]:
        diagnostics = cast(list[dict[str, object]], document["diagnostics"])
        return [
            (
                item["code"],
                item["severity"],
                item["message"],
                cast(dict[str, object], item["location"])["line"],
                cast(dict[str, object], item["location"])["column"],
            )
            for item in diagnostics
        ]

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    project = facts(_read_json(capsys))
    assert cli.main(["check", str(root / "main.pietto"), "--format", "json"]) == 1
    single_file = facts(_read_json(capsys))
    message = "Invalid operands for operator {}: expected comparable operands"
    expected = [
        ("PIE-S2105", "error", message.format("=="), 12, 11),
        ("PIE-S2105", "error", message.format("=="), 19, 16),
        ("PIE-S2105", "error", message.format(">"), 23, 15),
    ]
    assert project == expected
    assert single_file == expected


_NO_GROUP = "`having` requires GROUP BY"
_COUNT_IN_SATISFYING = (
    "Aggregate count() is not allowed in having clause; "
    "use it only as a direct aliased select projection"
)


def _public_facts(items: object) -> list[tuple[object, ...]]:
    return [
        (
            item["code"],
            item["severity"],
            item["message"],
            cast(dict[str, object], item["location"])["line"],
            cast(dict[str, object], item["location"])["column"],
        )
        for item in cast(list[dict[str, object]], items)
    ]


_CHAIN_HEAD = (
    "shape Item:\n"
    "    id: Int\n"
    'source a: Item = postgres.table("a")\n'
    'source b: Item = postgres.table("b")\n'
    "def dbl(v: Int) -> Int | None: return v + v\n"
    "query q:\n"
    "    from a\n"
)
_CROSS = "    cross join b\n"
_SELECT_A = "    select:\n        id = a.id\n"
_QUALIFY = _SELECT_A + "    qualify:\n        "
CHAIN_CHECKS = {
    # A1-F1: each inner operand is its own occurrence in every reader.
    "join_select": (_CROSS + "    select x = 0 < a.id < 10\n", []),
    "join_where": (_CROSS + "    where 0 < a.id < b.id\n" + _SELECT_A, []),
    "join_on": ("    inner join b on a.id < b.id < 10\n" + _SELECT_A, []),
    "qualify": (_QUALIFY + "0 < row_number() window(order by a.id) < 3\n", []),
    "join_qualify": (
        _CROSS + _QUALIFY + "0 < row_number() window(order by a.id) < 3\n",
        [],
    ),
    "any_operand": (
        _CROSS + "    select x = False == any(z.id > a.id for z in b) == True\n",
        [],
    ),
    "def_call_operand": ("    select x = 0 < dbl(id) < 10\n", []),
    # An error in an inner operand is reported once, before analysis too.
    "unknown_operand": (
        _CROSS + "    select x = 0 < a.id < nope < 10\n",
        [("PIE-S2102", "error", "Unknown field: nope", 9, 27)],
    ),
    "def_call_check": (
        "    select x = 0 < dbl(1, 2) < 10\n",
        [
            (
                "PIE-S2395",
                "error",
                "Invalid arguments for def dbl: expected 1, got 2",
                8,
                20,
            )
        ],
    ),
    "any_check": (
        _QUALIFY + "False == any(z.id > 0 for z in b) == True\n",
        [("PIE-S2334", "error", "ANY is not supported in this context", 11, 18)],
    ),
}


@pytest.mark.parametrize(("body", "expected"), CHAIN_CHECKS.values(), ids=CHAIN_CHECKS)
def test_project_and_single_file_checks_agree_on_comparison_chains(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    body: str,
    expected: list[tuple[object, ...]],
) -> None:
    root = _project(tmp_path / "chain", _CHAIN_HEAD + body)

    # Before, the project check raised for the JOIN select, WHERE and unknown
    # operand, both QUALIFY chains and the any operand (the single-file check
    # too for that one), and both checks reported the def and ANY errors twice.
    code = 1 if expected else 0
    assert cli.main(["check", "--project", str(root), "--format", "json"]) == code
    assert _public_facts(_read_json(capsys)["diagnostics"]) == expected
    assert cli.main(["check", str(root / "main.pietto"), "--format", "json"]) == code
    assert _public_facts(_read_json(capsys)["diagnostics"]) == expected


_ROW = 'shape Row:\n    id: Int\nsource rows: Row = postgres.table("rows")\n'
_ARITY = "Invalid arguments for constructor Float: expected 1, got 2"
CHAIN_ONCE_IN_TEXT_ORDER = {
    "relationship_before_a_chain": (
        _ROW
        + "relationship Broken(row: Row):\n    0 < Float(1, 2) < 10\n"
        + "query q:\n    from rows\n    select ok = 0 < id < 10\n",
        5,
        9,
    ),
    "query_before_a_relationship_chain": (
        "relationship First(row: Row):\n    row.id > 0\n"
        + _ROW
        + "query q:\n    from rows\n    select ok = 0 < Float(1, 2) < 10\n"
        + "relationship Later(row: Row):\n    0 < row.id < 10\n",
        8,
        21,
    ),
}


@pytest.mark.parametrize("schema_version", (1, 2))
@pytest.mark.parametrize(
    ("source", "line", "column"),
    CHAIN_ONCE_IN_TEXT_ORDER.values(),
    ids=CHAIN_ONCE_IN_TEXT_ORDER,
)
def test_a_chain_operand_error_beside_a_relationship_is_reported_once(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    source: str,
    line: int,
    column: int,
    schema_version: int,
) -> None:
    """A project of either schema version, as a single file, reports an
    error in a chain operand once also when a declaration of another kind
    after it holds a chain; it reported it twice."""
    root = _project(tmp_path / "chain", source, schema_version=schema_version)
    expected = [("PIE-S2104", "error", _ARITY, line, column)]
    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    assert _public_facts(_read_json(capsys)["diagnostics"]) == expected
    assert cli.main(["check", str(root / "main.pietto"), "--format", "json"]) == 1
    assert _public_facts(_read_json(capsys)["diagnostics"]) == expected


def test_a_chain_operand_error_is_reported_once_in_each_module(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Each module places the repeated text of its own declarations in text
    order, and two modules that repeat the same text each report its error."""
    root = _project(
        tmp_path / "modules",
        'from "models.pietto" import (\n    shape Row,\n    source rows,\n)\n'
        "relationship Small(row: Row):\n    0 < Float(1, 2) < 10\n"
        "query r:\n    from rows\n    select ok = 0 < id < 10\n",
    )
    (root / "models.pietto").write_text(
        "export (\n    shape Row,\n    source rows,\n)\n"
        + _ROW
        + "relationship Broken(row: Row):\n    0 < Float(1, 2) < 10\n"
        + "query q:\n    from rows\n    select ok = 0 < id < 10\n",
        encoding="utf-8",
    )
    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    diagnostics = cast(
        list[dict[str, dict[str, object]]], _read_json(capsys)["diagnostics"]
    )
    assert [
        (item["location"]["path"], item["location"]["line"], item["code"])
        for item in diagnostics
    ] == [("main.pietto", 6, "PIE-S2104"), ("models.pietto", 9, "PIE-S2104")]


def test_project_and_single_file_checks_refuse_range_offsets_alike(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Both checks reject invalid offsets in selected, JOIN and QUALIFY windows.
    # A well-typed RANGE offset also gives the single-file emission warning.
    root = _project(
        tmp_path / "range-offsets",
        "shape Order:\n"
        "    id: Int\n"
        "    customer_id: Int\n"
        "    amount: Int | None\n"
        "shape Customer:\n"
        "    id: Int\n"
        "    name: Text\n"
        'source orders: Order = postgres.table("orders")\n'
        'source customers: Customer = postgres.table("customers")\n'
        "relationship order_customer(order: Order, customer: Customer):\n"
        "    order.customer_id == customer.id\n"
        "query named:\n"
        "    from orders\n"
        "\n"
        "    let k = 2\n"
        "    select:\n"
        "        id\n"
        "        a = last_value(amount) window(\n"
        "            order by id\n"
        "            range nonexistent preceding)\n"
        "        b = last_value(amount) window(\n"
        "            order by id\n"
        '            range "abc" preceding)\n'
        "        c = last_value(amount) window(\n"
        "            order by id\n"
        "            range between k preceding and 2 following)\n"
        "query joined:\n"
        "    from orders\n"
        "    let customer = customers\n"
        "    inner join customer on order_customer(orders, customer)\n"
        "    select:\n"
        "        order_id = orders.id\n"
        "        d = last_value(orders.amount) window(\n"
        "            order by orders.id\n"
        "            range -1 preceding)\n"
        "query qualified:\n"
        "    from orders\n"
        "    select:\n"
        "        id\n"
        "        rn = row_number() window(\n"
        "            order by id)\n"
        "    qualify:\n"
        "        coalesce(last_value(amount) window(\n"
        "            order by id\n"
        "            range 1.5 preceding)\n"
        "        , 0) > rn\n",
    )

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    project = _public_facts(_read_json(capsys)["diagnostics"])
    assert cli.main(["check", str(root / "main.pietto"), "--format", "json"]) == 1
    single_file = _public_facts(_read_json(capsys)["diagnostics"])
    message = (
        "Invalid window frame for function last_value: RANGE offsets must be "
        "nonnegative integer literals up to 9223372036854775807"
    )
    assert single_file == [
        ("PIE-S2104", "error", message, 18, 13),
        ("PIE-S2104", "error", message, 21, 13),
        (
            "PIE-S2385",
            "warning",
            "Single-file SQL emission is unavailable because this RANGE window "
            "frame has an offset; this warning does not change check's exit "
            "status, but emit-sql will refuse this relation.",
            24,
            13,
        ),
        ("PIE-S2104", "error", message, 33, 13),
        ("PIE-S2104", "error", message, 43, 18),
    ]
    assert project == [
        ("PIE-S2104", "error", message, line, column)
        for line, column in ((18, 13), (21, 13), (33, 13), (43, 18))
    ]


def test_project_and_single_file_checks_refuse_decimal_quotient_uses_alike(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Before: a single file passed every query, and the project passed
    # `where a / 2` and gave a bare PIE-S2333 for the SELECT uses. A quotient
    # with a Decimal operand has no type yet but is a number, so a use that
    # takes no number is refused alike, and a use beside numbers passes.
    root = _project(
        tmp_path / "decimal-quotient",
        "shape Row:\n"
        "    id: Int\n"
        "    a: Decimal(10, 2)\n"
        'source rows: Row = postgres.table("app.rows")\n'
        "query by_where:\n"
        "    from rows\n"
        "    where a / 2\n"
        "    select:\n"
        "        id\n"
        "query by_let:\n"
        "    from rows\n"
        "\n"
        "    let q = a / 2 + 1\n"
        "    where q\n"
        "    select:\n"
        "        id\n"
        "query by_select:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        '        p = a / 2 - "x"\n'
        "        l = lower(a / 2)\n"
        '        c = a / 2 == "x"\n'
        '        i = a / 2 in ("x", "y")\n'
        '        o = coalesce("x", a / 2)\n'
        '        z = coalesce("x", a / 2, None)\n'
        "query accepted:\n"
        "    from rows\n"
        "    where a / 2 > 1 and (a / 2) % 2.5 > 0\n"
        "    select:\n"
        "        id\n",
    )

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    project = _public_facts(_read_json(capsys)["diagnostics"])
    assert cli.main(["check", str(root / "main.pietto"), "--format", "json"]) == 1
    single_file = _public_facts(_read_json(capsys)["diagnostics"])
    where = "Expected Bool expression in where clause"
    operands = "Invalid operands for operator {}: expected {} operands"
    expected = [
        ("PIE-S2202", "error", where, 7, 11),
        ("PIE-S2202", "error", where, 14, 11),
        ("PIE-S2105", "error", operands.format("-", "numeric"), 21, 13),
        (
            "PIE-S2104",
            "error",
            "Invalid argument type for function lower at position 1: "
            "expected Text, got numeric",
            22,
            13,
        ),
        ("PIE-S2105", "error", operands.format("==", "comparable"), 23, 13),
        (
            "PIE-S2105",
            "error",
            operands.format("in", "same canonical membership"),
            24,
            13,
        ),
        *(
            (
                "PIE-S2104",
                "error",
                "Invalid argument types for function coalesce: expected same "
                "canonical type",
                line,
                13,
            )
            for line in (25, 26)
        ),
    ]
    assert project == expected
    assert single_file == expected


def test_project_and_single_file_checks_refuse_satisfying_without_group_by(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(
        tmp_path / "no-group-satisfying",
        "shape Row:\n"
        "    id: Int\n"
        "    key: Int | None\n"
        'source rows: Row = postgres.table("rows")\n'
        "query plain:\n"
        "    from rows\n"
        "    select:\n"
        "        a = rows.id\n"
        "    having:\n"
        "        a > 0\n"
        "query aggregate_call:\n"
        "    from rows\n"
        "    select:\n"
        "        a = rows.id\n"
        "    having:\n"
        "        count() > 0\n"
        "query global_total:\n"
        "    from rows\n"
        "    select:\n"
        "        n = count()\n"
        "    having:\n"
        "        n > 0\n"
        "query windowed:\n"
        "    from rows\n"
        "    select:\n"
        "        a = rows.id\n"
        "        r = row_number() window(\n"
        "            order by\n"
        "                rows.id)\n"
        "    having:\n"
        "        a > 0\n"
        "query with_let:\n"
        "    from rows\n"
        "\n"
        "    let b = id + 1\n"
        "    select:\n"
        "        c = b\n"
        "    having:\n"
        "        c > 0\n"
        "query qualified:\n"
        "    from rows\n"
        "    select:\n"
        "        a = rows.id\n"
        "    having:\n"
        "        a > 0\n"
        "    qualify:\n"
        "        row_number() window(\n"
        "            order by\n"
        "                a\n"
        "        ) <= 3\n"
        "query grouped:\n"
        "    from rows\n"
        "    group by:\n"
        "        rows.key\n"
        "    select:\n"
        "        k = rows.key\n"
        "        n = count()\n"
        "    having:\n"
        "        n > 0\n",
    )
    (root / "contract.json").write_text("{}", encoding="utf-8")
    expected = [
        ("PIE-S2323", "error", _NO_GROUP, 9, 5),
        ("PIE-S2308", "error", _COUNT_IN_SATISFYING, 16, 9),
        ("PIE-S2323", "error", _NO_GROUP, 21, 5),
        ("PIE-S2323", "error", _NO_GROUP, 30, 5),
        ("PIE-S2323", "error", _NO_GROUP, 38, 5),
        ("PIE-S2323", "error", _NO_GROUP, 44, 5),
    ]

    assert cli.main(["check", "--project", str(root)]) == 1
    text = capsys.readouterr()
    assert text.out == ""
    assert text.err == "".join(
        f"main.pietto:{line}:{column} {code} error: {message}\n"
        for code, _, message, line, column in expected
    )
    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    assert _public_facts(_read_json(capsys)["diagnostics"]) == expected
    assert cli.main(["check", str(root / "main.pietto"), "--format", "json"]) == 1
    assert _public_facts(_read_json(capsys)["diagnostics"]) == [
        *expected,
        # A hidden QUALIFY window reads its pre-window input namespace only.
        ("PIE-S2102", "error", "Unknown field: a", 49, 17),
    ]

    emit = ["emit-sql", "--project", str(root), "--module", "main.pietto"]
    emit += ["--kind", "query", "--name", "plain", "--dialect", "postgres"]
    emit += ["--emission-contract", "contract.json", "--format", "json"]
    assert cli.main(emit) == 1
    emitted = _read_json(capsys)
    assert (emitted["status"], emitted["artifact"]) == ("BLOCKED", None)
    assert _public_facts(emitted["diagnostics"]) == expected

    # Each refusal is the relation's own semantic fact, retained once.
    built = _build(tmp_path / "builder", (root / "main.pietto").read_text())
    plain = next(
        entry
        for entry in built.completed.effective_outputs.entries
        if entry.owner.identity.declared_name == "plain"
    )
    assert type(plain) is ProjectEffectiveOutputTerminal
    facts = plain.fragment.semantic_facts
    assert facts.state.status is ProjectRelationRowSchemaStatus.UNKNOWN
    (refusal,) = facts.helper_diagnostics
    assert refusal is built.completed.diagnostics[0]
    assert type(_entry(built, "grouped")) is ProjectExistingEffectiveOutput


def test_project_refuses_satisfying_without_group_by_in_every_no_join_body(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(
        tmp_path / "no-group-satisfying-bodies",
        "shape Row:\n"
        "    id: Int\n"
        "    key: Int | None\n"
        'source rows: Row = postgres.table("rows")\n'
        'source others: Row = postgres.table("others")\n'
        "query both:\n"
        "    union all:\n"
        "        from rows\n"
        "        from others\n"
        "query set_reader:\n"
        "    from both\n"
        "    select:\n"
        "        a = both.id\n"
        "    having:\n"
        "        a > 0\n"
        "query seed:\n"
        "    values(id: Int):\n"
        "        1\n"
        "query values_reader:\n"
        "    from seed\n"
        "    select:\n"
        "        a = seed.id\n"
        "    having:\n"
        "        count() > 0\n"
        "query joined:\n"
        "    from rows\n"
        "    let o = others\n"
        "\n"
        "    inner join o on rows.id == o.id\n"
        "    select:\n"
        "        a = rows.id\n"
        "query joined_reader:\n"
        "    from joined\n"
        "    select:\n"
        "        a = joined.a\n"
        "    having:\n"
        "        a > 0\n"
        "query let_body:\n"
        "    let w1:\n"
        "        from rows\n"
        "        select:\n"
        "            a = rows.id\n"
        "        having:\n"
        "            a > 0\n"
        "    from w1\n"
        "    select:\n"
        "        a\n"
        "query let_reader:\n"
        "    let w2:\n"
        "        from rows\n"
        "        select:\n"
        "            id\n"
        "    from w2\n"
        "    select:\n"
        "        a = w2.id\n"
        "    having:\n"
        "        a > 0\n"
        "query distinct_rows:\n"
        "    from rows\n"
        "    select distinct:\n"
        "        a = rows.id\n"
        "    having:\n"
        "        a > 0\n"
        "query ordered:\n"
        "    from rows\n"
        "    select:\n"
        "        a = rows.id\n"
        "    having:\n"
        "        a > 0\n"
        "    order by:\n"
        "        a asc\n"
        "    limit 3\n"
        "query downstream:\n"
        "    from ordered\n"
        "    select:\n"
        "        a\n",
    )
    unavailable = "Project relation semantic completion is unavailable: {}"

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    document = _read_json(capsys)
    assert document["ok"] is False
    assert _public_facts(document["diagnostics"]) == [
        ("PIE-S2323", "error", _NO_GROUP, 14, 5),
        ("PIE-S2308", "error", _COUNT_IN_SATISFYING, 24, 9),
        ("PIE-S2323", "error", _NO_GROUP, 36, 5),
        ("PIE-S2323", "error", _NO_GROUP, 43, 9),
        ("PIE-S2333", "error", unavailable.format("let_body"), 38, 1),
        ("PIE-S2323", "error", _NO_GROUP, 56, 5),
        ("PIE-S2323", "error", _NO_GROUP, 62, 5),
        ("PIE-S2323", "error", _NO_GROUP, 68, 5),
        ("PIE-S2333", "error", unavailable.format("downstream"), 73, 1),
    ]


def test_satisfying_without_group_by_beside_parameters_and_table_functions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Header parameters and generate_series inputs reach the same refusal."""
    root = _project(
        tmp_path / "no-group-satisfying-phase70",
        "shape Row:\n"
        "    id: Int\n"
        'source rows: Row = postgres.table("rows")\n'
        "query param_plain(low: Int):\n"
        "    from rows\n"
        "    where id > low\n"
        "    select:\n"
        "        a = rows.id\n"
        "    having:\n"
        "        a > low\n"
        "query param_count(low: Int):\n"
        "    from rows\n"
        "    select:\n"
        "        a = rows.id\n"
        "    having:\n"
        "        count() > low\n"
        "query param_let(low: Int):\n"
        "    let w:\n"
        "        from rows\n"
        "        where id > low\n"
        "        select:\n"
        "            a = rows.id\n"
        "        having:\n"
        "            a > low\n"
        "    from w\n"
        "    select:\n"
        "        a\n"
        "query series_plain:\n"
        "    from generate_series(1, 5, 1) as n\n"
        "    select:\n"
        "        a = n\n"
        "    having:\n"
        "        a > 0\n"
        "query series_count:\n"
        "    from generate_series(1, 5, 1) as n\n"
        "    select:\n"
        "        a = n\n"
        "    having:\n"
        "        count() > 0\n"
        "query series_let:\n"
        "    let s:\n"
        "        from generate_series(1, 5, 1) as n\n"
        "        select:\n"
        "            a = n\n"
        "        having:\n"
        "            a > 0\n"
        "    from s\n"
        "    select:\n"
        "        a\n",
    )
    (root / "contract.json").write_text("{}", encoding="utf-8")
    unavailable = "Project relation semantic completion is unavailable: param_let"
    expected = [
        ("PIE-S2323", "error", _NO_GROUP, 9, 5),
        ("PIE-S2308", "error", _COUNT_IN_SATISFYING, 16, 9),
        ("PIE-S2323", "error", _NO_GROUP, 23, 9),
        ("PIE-S2333", "error", unavailable, 17, 1),
        ("PIE-S2323", "error", _NO_GROUP, 32, 5),
        ("PIE-S2308", "error", _COUNT_IN_SATISFYING, 39, 9),
        ("PIE-S2323", "error", _NO_GROUP, 45, 9),
    ]
    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    assert _public_facts(_read_json(capsys)["diagnostics"]) == expected
    for name in ("param_plain", "series_plain"):
        emit = ["emit-sql", "--project", str(root), "--module", "main.pietto"]
        emit += ["--kind", "query", "--name", name, "--dialect", "postgres"]
        emit += ["--emission-contract", "contract.json", "--format", "json"]
        assert cli.main(emit) == 1
        emitted = _read_json(capsys)
        assert (emitted["status"], emitted["artifact"]) == ("BLOCKED", None)
        assert _public_facts(emitted["diagnostics"]) == expected


def test_parse_failure_runs_neither_semantic_builder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(tmp_path / "parse-failure", "shape Broken\n    id: Int\n")

    def unexpected(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("semantic builders must not run after parse failure")

    monkeypatch.setattr(
        project_model, "build_empty_project_semantic_result", unexpected
    )
    monkeypatch.setattr(
        completed_semantics, "build_project_completed_semantic_result", unexpected
    )
    assert cli.main(["check", "--project", str(root)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-P1000" in captured.err


def test_legacy_project_and_single_file_checks_never_enter_completed_builder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    legacy = _project(
        tmp_path / "legacy",
        'shape Row:\n    id: Int\nsource rows: Row = postgres.table("rows")\n',
        schema_version=1,
    )
    single = tmp_path / "single.pietto"
    single.write_text("shape Row:\n    id: Int\n", encoding="utf-8")

    def unexpected(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("non-explicit checks must not enter completed semantics")

    monkeypatch.setattr(
        completed_semantics, "build_project_completed_semantic_result", unexpected
    )
    assert cli.main(["check", "--project", str(legacy)]) == 0
    legacy_text = capsys.readouterr()
    assert legacy_text.out == "Project check OK: .\nFiles checked: 1\n"
    assert legacy_text.err == ""

    assert cli.main(["check", str(single)]) == 0
    single_text = capsys.readouterr()
    assert single_text.out == f"OK: {single}\n"
    assert single_text.err == ""

    assert cli.main(["check", str(single), "--format", "json"]) == 0
    single_json = _read_json(capsys)
    assert single_json["schema_version"] == 1
    assert single_json["command"] == "check"
    assert "mode" not in single_json


def test_json_v2_and_public_private_boundaries_remain_exact(positive: _Built) -> None:
    direct = project_check_result_to_json_dict(
        positive.parse_result,
        semantic_diagnostics=positive.completed.diagnostics,
    )
    assert tuple(direct) == PROJECT_JSON_KEYS
    assert direct["schema_version"] == 2
    assert direct["ok"] is True

    production = PRODUCTION.read_text(encoding="utf-8")
    cli_source = CLI.read_text(encoding="utf-8")
    json_source = JSON_V2.read_text(encoding="utf-8")
    assert completed_semantics.__all__ == ()
    assert "ProjectConcreteCompletedSemanticResult" not in (
        REPO_ROOT / "src/pietto/__init__.py"
    ).read_text(encoding="utf-8")
    assert "build_project_completed_semantic_result" not in json_source
    assert "ProjectCompletedSemanticResult" not in json_source
    assert "_run_check" in cli_source
    single_file_body = cli_source.split("def _run_check(", 1)[1].split(
        "def _run_emit_sql(", 1
    )[0]
    assert "build_project_completed_semantic_result" not in single_file_body
    project_explain_body = cli_source.split("def _run_project_explain(", 1)[1]
    assert "build_project_completed_semantic_result" not in project_explain_body
    assert "build_project_ir_project_plan(" in production
    projection = production.split("def _diagnostics_from_carrier(", 1)[1].split(
        "def _fallback_diagnostic(", 1
    )[0]
    for forbidden in (
        "vars(",
        "__dict__",
        "fields(",
        "is_dataclass(",
        "serialize",
        "analyze_",
        "build_",
        "sorted(",
        ".sort(",
    ):
        assert forbidden not in projection
    for forbidden in (
        "ProjectIRUnary",
        "unary_tail",
        "emit_postgres_sql",
        "emit_mysql_sql",
        "pyarrow",
        "executor",
        "optimizer",
        "serialize_project_ir",
    ):
        assert forbidden not in production
    exposed_fields = {item.name for item in fields(positive.completed)}
    assert exposed_fields >= {
        "roots",
        "semantic_result",
        "verification",
        "completion",
        "effective_outputs",
        "diagnostics",
        "ok",
    }
    assert positive.completed.single_match_requests == ()
    assert positive.completed.single_matches.obligations == ()
    assert positive.completed.single_matches.diagnostics == ()
    assert not exposed_fields.intersection(
        {"plan", "node", "use", "slot", "coordinate", "canonical_bytes"}
    )


def test_spec_records_exact_contract_and_frozen_closure() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for phrase in (
        "ProjectConcreteCompletedSemanticResult",
        "ProjectNonConcreteCompletedSemanticResult",
        "ProjectPhase62VerificationResult",
        "ProjectEffectiveOutputCompletion",
        "PIE-S2333",
        "Project JSON v2",
        "EXPLICIT_MODULES",
        "LEGACY_FLAT",
        "PACKAGE_ROOT",
        "A3/M7/D0",
        "A3/M14/D0",
        "7/10",
        "mechanical expansion",
        "closed typed visitor",
        "174 -> 175",
        "417 -> 418",
        "Slice 14",
    ):
        assert phrase in text


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    return cast(dict[str, object], json.loads(captured.out))


def test_failed_relationship_on_keeps_errors_and_blocks_current_region(
    tmp_path: Path,
) -> None:
    source = """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
relationship Positive(row: Row):
    row.id > 0
query q:
    from rows
    let current = rows
    inner join current on Positive(future) and Missing()
    let future = rows
    inner join future on rows.id == future.id
    select:
        id = rows.id
"""
    built = _build(tmp_path, source)
    result = built.completed
    assert not result.ok
    first, second = result.roots.join_conditions.entries
    assert not first.ready
    assert first.references == ()
    assert first.mandatory_equalities == () and first.key_matches == ()
    unavailable = "Unavailable row argument for relationship Positive parameter row"
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in first.diagnostics
    ] == [
        ("PIE-S2604", unavailable, 9, 36),
        ("PIE-S2103", "Unknown function: Missing", 9, 48),
    ]
    terminal = _terminal_entry(built, "q")
    assert terminal.current_region is None
    # The failed ON's own gate retires; the later JOIN keeps the failed-prefix
    # contract: its ON gate, its unavailable pre-match input and its blocked
    # read of the prior rows.
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == [
        (
            "PIE-S2334",
            "JOIN-local ON is available only when an EXPLICIT_MODULES project "
            "(schema version 2) completes it.",
            11,
            23,
        ),
        ("PIE-S2604", unavailable, 9, 36),
        ("PIE-S2103", "Unknown function: Missing", 9, 48),
        (
            "PIE-S2335",
            "JOIN pre-match input or relationship authority is unavailable.",
            11,
            5,
        ),
        ("PIE-S2335", "JOIN ON reference is unavailable.", 11, 26),
    ]
    assert all(
        actual is retained
        for actual, retained in zip(
            result.diagnostics[1:],
            (*first.diagnostics, *second.diagnostics),
            strict=True,
        )
    )


def test_failed_relationship_let_keeps_nested_errors_and_distinct_calls(
    tmp_path: Path,
) -> None:
    source = """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
relationship Broken(row: Row):
    row.missing > 0
query q:
    from rows
    let n = 1
    let answer = Broken(n + Missing()) and Broken(rows) and Missing()
    select:
        id = rows.id
"""
    built = _build(tmp_path, source)
    assert not built.completed.ok
    diagnostics = built.completed.diagnostics
    refused = "Relationship predicate Broken has no unambiguous checked declaration"
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in diagnostics
    ] == [
        ("PIE-S2604", refused, 9, 18),
        ("PIE-S2604", refused, 9, 44),
        ("PIE-S2103", "Unknown function: Missing", 9, 29),
        ("PIE-S2103", "Unknown function: Missing", 9, 61),
        ("PIE-S2604", "Unknown relationship parameter field: row.missing", 5, 5),
    ]
    assert diagnostics[0] is not diagnostics[1]


def test_failed_relationship_aggregate_argument_reports_call_then_scanned_child(
    tmp_path: Path,
) -> None:
    built = _build(
        tmp_path,
        """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
relationship Same(a: Row, b: Row):
    a.id == b.id
query q:
    from rows
    select:
        total = sum(Same(1 + Missing(), 2))
""",
    )
    assert not built.completed.ok
    # Both row-argument errors of the rejected call, then the Missing() its
    # complex argument holds, instead of the unavailable-completion fallback.
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in built.completed.diagnostics
    ] == [
        (
            "PIE-S2604",
            "Unavailable row argument for relationship Same parameter a",
            9,
            26,
        ),
        (
            "PIE-S2604",
            "Unavailable row argument for relationship Same parameter b",
            9,
            41,
        ),
        ("PIE-S2103", "Unknown function: Missing", 9, 30),
    ]


def test_invalid_relationship_declaration_keeps_its_error_and_call_owner(
    tmp_path: Path,
) -> None:
    built = _build(
        tmp_path,
        """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
relationship Broken(row: Row):
    row.missing > 0
query q:
    from rows
    let current = rows
    inner join current on Broken(current)
    select:
        id = rows.id
""",
    )
    result = built.completed
    assert not result.ok
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == [
        (
            "PIE-S2604",
            "Relationship predicate Broken has no unambiguous checked declaration",
            9,
            27,
        ),
        ("PIE-S2604", "Unknown relationship parameter field: row.missing", 5, 5),
    ]
    (condition,) = result.roots.join_conditions.entries
    assert not condition.ready and condition.references == ()
    assert condition.mandatory_equalities == () and condition.key_matches == ()
    assert (
        condition.value_type is not None
        and condition.value_type.kind.value == "unknown"
    )
    assert len(condition.diagnostics) == 1
    assert condition.diagnostics[0] is result.diagnostics[0]
    assert any(
        item is result.diagnostics[1]
        for item in result.roots.join_conditions.diagnostics
    )
    assert _terminal_entry(built, "q").current_region is None


def test_failed_relationship_subtree_keeps_only_its_exact_call_errors(
    tmp_path: Path,
) -> None:
    from pietto._project.project_relationship_predicates import (
        select_project_predicate_expression,
    )

    built = _build(
        tmp_path,
        """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
relationship Broken(row: Row):
    row.missing > 0
query q:
    from rows
    let current = rows
    inner join current on Broken(current) and Broken(rows)
    select:
        id = rows.id
""",
    )
    (condition,) = built.completed.roots.join_conditions.entries
    record = condition.environment.predicate_expression
    assert record is not None and record.calls == ()
    first, second = record.failed_calls
    view = select_project_predicate_expression((record,), record.owner, first.call)
    assert view is not None and view.parent is record and view.calls == ()
    (failure,) = view.failed_calls
    assert failure.call is first.call and failure.expression is view.expression
    assert len(view.diagnostics) == 1
    assert view.diagnostics[0] is first.diagnostics[0]
    assert all(item is not second.diagnostics[0] for item in view.diagnostics)
    with pytest.raises(ValueError, match="failure"):
        replace(view, failed_calls=(second,))
    with pytest.raises(ValueError, match="failure"):
        replace(view, diagnostics=record.diagnostics)


def test_failed_predicate_keeps_an_ambiguous_namespace_untyped(tmp_path: Path) -> None:
    built = _build(
        tmp_path,
        """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
relationship Positive(row: Row):
    row.id > 0
query q:
    from rows
    let other = rows
    inner join other on True
    where Positive(missing) and id > 0 and Missing()
    select:
        id = rows.id
""",
    )
    result = built.completed
    assert not result.ok
    # The ambiguous `id` keeps the completion fallback; the rejected call's
    # error stays on its record and is not published.
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == [
        (
            "PIE-S2333",
            "Project relation semantic completion is unavailable: q",
            6,
            1,
        )
    ]
    (analysis,) = (
        aggregate.input_filter.expression_analysis
        for tail in result.effective_outputs.current_tails
        for aggregate in tail.window_set.aggregation_set.results
        if aggregate.input_filter.entry.owner.definition.name == "q"
    )
    assert (
        type(analysis) is scalar_namespaces.ProjectNonConcreteJoinedNamespaceExpression
    )
    assert analysis.reason.value == "reference_resolution_non_concrete"
    assert analysis.kernel_value_type is None and not analysis.value_types
    assert analysis.diagnostics == ()
    (blocker,) = analysis.blocking_resolutions
    assert blocker.status.value == "ambiguous" and blocker.target is None
    assert len(blocker.candidates) == 2
    record = analysis.predicate_expression
    assert record is not None
    (failure,) = record.failed_calls
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in record.diagnostics
    ] == [
        (
            "PIE-S2604",
            "Unavailable row argument for relationship Positive parameter row",
            10,
            20,
        )
    ]
    assert failure.diagnostics[0] is record.diagnostics[0]


def test_failed_predicate_row_argument_is_no_ambiguous_namespace_read(
    tmp_path: Path,
) -> None:
    built = _build(
        tmp_path,
        """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
relationship Positive(row: Row):
    row.id > 0
query q:
    from rows
    let other = rows
    inner join other on True
    where Positive(id) and Missing()
    select:
        id = rows.id
""",
    )
    result = built.completed
    assert not result.ok
    # Only the rejected row argument names `id`: no scalar read of the
    # joined namespace is ambiguous, so the WHERE is typed as in a file.
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == [
        (
            "PIE-S2604",
            "Unavailable row argument for relationship Positive parameter row",
            10,
            20,
        ),
        ("PIE-S2103", "Unknown function: Missing", 10, 28),
    ]


_FAILED_ANY_INPUTS = """shape Item:
    id: Int
    owner_id: Int
    item_key = unique(id)
shape Owner:
    id: Int
    status: Text | None
    owner_key = unique(id)
source items: Item = postgres.table("shop.items")
source owners: Owner = postgres.table("shop.owners")
relationship ActiveOwner(item: Item, owner: Owner):
    item.owner_id == owner.id and owner.status == "active"
query q:
    from items
"""
_FAILED_ANY = (
    "any(ActiveOwner(items, candidate.id + Missing()) and items.id > 0 "
    "for candidate in owners)"
)
# Each query body after `from items`, with the ANY line and the columns of the
# rejected call's complex row argument and of the real unknown call inside it.
_FAILED_ANY_QUERIES = {
    "on": (
        "    let buyer = owners\n"
        f"    inner join buyer on {_FAILED_ANY}\n"
        "    select:\n"
        "        id = items.id\n",
        (16, 48, 63),
    ),
    "where": (
        f"    where {_FAILED_ANY}\n    select:\n        id = items.id\n",
        (15, 34, 49),
    ),
    "select": (
        f"    select:\n        id = items.id\n        ok = {_FAILED_ANY}\n",
        (17, 37, 52),
    ),
    "let": (
        f"    let ok = {_FAILED_ANY}\n"
        "    select:\n"
        "        id = items.id\n"
        "        flag = ok\n",
        (15, 37, 52),
    ),
    "joined_where": (
        "    let buyer = owners\n"
        "    inner join buyer on ActiveOwner(items, buyer)\n"
        f"    where {_FAILED_ANY}\n"
        "    select:\n"
        "        id = items.id\n",
        (17, 34, 49),
    ),
}


@pytest.mark.parametrize("placement", tuple(_FAILED_ANY_QUERIES))
def test_failed_relationship_in_any_keeps_real_errors_in_each_project_reader(
    tmp_path: Path, placement: str
) -> None:
    from pietto._project.existence_values import ProjectAnyValue

    body, (line, argument, missing) = _FAILED_ANY_QUERIES[placement]
    built = _build(tmp_path, _FAILED_ANY_INPUTS + body)
    result = built.completed
    assert not result.ok
    unavailable = (
        "Unavailable row argument for relationship ActiveOwner parameter owner"
    )
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == [
        ("PIE-S2604", unavailable, line, argument),
        ("PIE-S2103", "Unknown function: Missing", line, missing),
    ]
    values: tuple[ProjectAnyValue, ...]
    if placement == "on":
        (condition,) = result.roots.join_conditions.entries
        assert not condition.ready and condition.references == ()
        values = condition.environment.existence_values
    elif placement == "joined_where":
        (analysis,) = (
            aggregate.input_filter.expression_analysis
            for tail in result.effective_outputs.current_tails
            for aggregate in tail.window_set.aggregation_set.results
            if aggregate.input_filter.entry.owner.definition.name == "q"
        )
        assert (
            type(analysis)
            is scalar_namespaces.ProjectNonConcreteJoinedNamespaceExpression
        )
        assert analysis.reason.value == "type_kernel_non_concrete"
        values = analysis.existence_values
    else:
        terminal = _terminal_entry(built, "q")
        values = (
            cast(tuple[ProjectAnyValue, ...], terminal.blocker)
            if placement == "let"
            else cast(ProjectNoJoinScalarExpression, terminal.blocker).existence_values
        )
        # The terminal holds each error once, the restated call error included.
        assert [item.message for item in terminal.diagnostics] == [
            unavailable,
            "Unknown function: Missing",
        ]
        assert terminal.diagnostics[1] is values[0].diagnostics[0]
    # The checked ANY keeps the rejected call and its exact error, never ready.
    (value,) = values
    (failure,) = value.failed_relationship_calls
    assert value.predicate_typed and value.value_type.kind.value == "unknown"
    assert [item.message for item in value.diagnostics] == [
        "Unknown function: Missing",
        unavailable,
    ]
    assert value.diagnostics[1] is failure.diagnostics[0]


def test_failed_any_on_with_an_unknown_reference_holds_each_error_once(
    tmp_path: Path,
) -> None:
    built = _build(
        tmp_path,
        _FAILED_ANY_INPUTS
        + "    let buyer = owners\n"
        + f"    inner join buyer on {_FAILED_ANY} and nowhere.id > 0\n"
        + "    select:\n        id = items.id\n",
    )
    assert not built.completed.ok
    (condition,) = built.completed.roots.join_conditions.entries
    assert not condition.ready and condition.value_type is None
    unavailable = (
        "Unavailable row argument for relationship ActiveOwner parameter owner"
    )
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in condition.diagnostics
    ] == [
        ("PIE-S2604", unavailable, 16, 48),
        ("PIE-S2103", "Unknown function: Missing", 16, 63),
        ("PIE-S2335", "JOIN ON reference is unknown.", 16, 120),
    ]
    (value,) = condition.environment.existence_values
    assert condition.diagnostics[0] is value.diagnostics[1]


def test_failed_any_joined_let_with_a_blocked_read_holds_each_error_once(
    tmp_path: Path,
) -> None:
    from pietto._project.project_joined_row_semantics import (
        ProjectNonConcreteJoinedRowSemantics,
    )

    built = _build(
        tmp_path,
        _FAILED_ANY_INPUTS
        + "    let buyer = owners\n"
        + "    inner join buyer on ActiveOwner(items, buyer)\n"
        + f"    let first = {_FAILED_ANY} and second\n"
        + "    let second = True\n"
        + "    select:\n        id = items.id\n",
    )
    result = built.completed
    assert not result.ok
    expected = [
        (
            "PIE-S2604",
            "Unavailable row argument for relationship ActiveOwner parameter owner",
            17,
            40,
        ),
        (
            "PIE-S2330",
            "Let binding cannot reference a later binding: second",
            17,
            112,
        ),
        ("PIE-S2103", "Unknown function: Missing", 17, 55),
    ]
    semantics = _terminal_entry(built, "q").blocker
    assert type(semantics) is ProjectNonConcreteJoinedRowSemantics
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in semantics.namespaces.diagnostics
    ] == expected
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == expected


_UNAVAILABLE_OWNER = (
    "Unavailable row argument for relationship ActiveOwner parameter owner"
)
_UNAVAILABLE_ANY = "ANY predicate reference is unavailable."


@pytest.mark.parametrize(
    ("first", "expected"),
    (
        pytest.param(
            "ActiveOwner(items, missing)",
            [
                ("PIE-S2604", _UNAVAILABLE_OWNER, 15, 32),
                ("PIE-S2102", "Unknown field: items.nofield", 16, 13),
            ],
            id="rejected_call",
        ),
        pytest.param(
            "any(c.nope > 0 for c in owners)",
            [("PIE-S2334", _UNAVAILABLE_ANY, 15, 17)],
            id="any_error",
        ),
        pytest.param(
            "any(ActiveOwner(items, c) and c.nope > 0 for c in owners)",
            [("PIE-S2334", _UNAVAILABLE_ANY, 15, 43)],
            id="successful_call_any_error",
        ),
    ),
)
def test_no_join_let_terminal_adds_scanned_errors_only_for_rejected_calls(
    tmp_path: Path, first: str, expected: list[tuple[str, str, int, int]]
) -> None:
    built = _build(
        tmp_path,
        _FAILED_ANY_INPUTS
        + f"    let a = {first}\n"
        + "    let b = items.nofield + 1\n"
        + "    select:\n        id = items.id\n        flag = a\n        n = b\n",
    )
    result = built.completed
    assert not result.ok
    # A rejected call keeps the independent LET error its scope already
    # scanned; any other first LET error, a successful call's included,
    # keeps only its own diagnostics.
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == expected
