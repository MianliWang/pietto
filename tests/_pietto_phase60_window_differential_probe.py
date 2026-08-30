from __future__ import annotations

import argparse
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys

from _pietto_project_explain_scenarios import (
    _manifest,
    _project_config,
    _run_cli_pair,
    _write_package,
)
import _pietto_phase59_graph_differential_probe as graph_probe

import pietto._project.check as project_check
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.package_graph_inspection import (
    PackageGraphInspectionLinkKind,
    PackageGraphInspectionRecordKind,
    PackageGraphPureStatus,
    _evaluate_package_graph_inspection,
    _inspect_package_graph,
)
from pietto.ast_nodes import QueryDef, WindowExpr
from pietto.ir import build_ir
from pietto.ir.model import LiteralIR, RelationIR, WindowCallIR
from pietto.parser_api import parse_file
from pietto.semantic import analyze
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.postgres import emit_postgres_sql
from pietto.sql.window_strategy import (
    WindowTargetDialect,
    decide_named_window_lowering,
)


OBSERVATION_FORMAT = "pietto.phase60-window-differential.v1"
PREFIX = """shape Row:
    id: Int not null
    value: Int nullable
    category: Text nullable
"""
POSTGRES_NATIVE = (
    PREFIX
    + """source rows: Row is postgres.table("rows")
query result:
    from rows
    group by:
        category
    select:
        group_name = category
        total = sum(value)
        ranking = row_number() window child
        first = first_value(group_name) respect nulls window child
        nth = nth_value(group_name, 2) from first respect nulls window child
        previous = lag(group_name, 1, group_name) respect nulls window child
    window child = base
    window unused:
        order by:
            id
    window base:
        partition by:
            group_name
        order by:
            total desc
    satisfying:
        total > 0
    order by:
        ranking
    limit 5
"""
)
POSTGRES_FALLBACK = (
    PREFIX
    + """source rows: Row is postgres.table("rows")
query result:
    from rows
    select:
        result = nth_value(value, 2) from first respect nulls window derived
    window derived = framed
    window framed:
        partition by:
            category
        order by:
            id desc
        groups between 1 preceding and current row exclude ties
"""
)
POSTGRES_FALLBACK_INLINE = (
    PREFIX
    + """source rows: Row is postgres.table("rows")
query result:
    from rows
    select:
        result = nth_value(value, 2) from first respect nulls window:
            partition by:
                category
            order by:
                id desc
            groups between 1 preceding and current row exclude ties
"""
)
POSTGRES_FRAMES = (
    PREFIX
    + """source rows: Row is postgres.table("rows")
query result:
    from rows
    select:
        rows_value = last_value(value) respect nulls window:
            order by:
                id
            rows between 1 preceding and current row exclude current row
        range_value = first_value(value) window:
            order by:
                id
            range current row exclude group
"""
)
MYSQL_NATIVE = (
    PREFIX
    + """source rows: Row is mysql.table("rows")
query result:
    from rows
    select:
        result = nth_value(value, 2) from first respect nulls window child:
            rows between 1 preceding and current row
    window child = base
    window unused:
        order by:
            value
    window base:
        partition by:
            category
        order by:
            id desc
"""
)


def _negative_source(connector: str, call: str, frame: str | None) -> str:
    frame_source = "" if frame is None else f"        {frame}\n"
    return (
        PREFIX
        + f'source rows: Row is {connector}("rows")\n'
        + "query result:\n"
        + "    from rows\n"
        + "    select:\n"
        + f"        result = {call} window restricted\n"
        + "    window restricted:\n"
        + "        order by:\n"
        + "            id\n"
        + frame_source
    )


NEGATIVE_CASES = (
    (
        "postgres_ignore_nulls",
        WindowTargetDialect.POSTGRESQL,
        _negative_source("postgres.table", "first_value(value) ignore nulls", None),
    ),
    (
        "postgres_from_last",
        WindowTargetDialect.POSTGRESQL,
        _negative_source("postgres.table", "nth_value(value, 2) from last", None),
    ),
    (
        "postgres_range_offset",
        WindowTargetDialect.POSTGRESQL,
        _negative_source("postgres.table", "first_value(value)", "range 1 preceding"),
    ),
    (
        "mysql_groups",
        WindowTargetDialect.MYSQL,
        _negative_source("mysql.table", "first_value(value)", "groups current row"),
    ),
    (
        "mysql_exclude",
        WindowTargetDialect.MYSQL,
        _negative_source(
            "mysql.table",
            "first_value(value)",
            "rows current row exclude no others",
        ),
    ),
    (
        "mysql_ignore_nulls",
        WindowTargetDialect.MYSQL,
        _negative_source("mysql.table", "first_value(value) ignore nulls", None),
    ),
    (
        "mysql_from_last",
        WindowTargetDialect.MYSQL,
        _negative_source("mysql.table", "nth_value(value, 2) from last", None),
    ),
    (
        "mysql_range_offset",
        WindowTargetDialect.MYSQL,
        _negative_source("mysql.table", "first_value(value)", "range 1 preceding"),
    ),
)


def _write_source(root: Path, name: str, source: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    path.write_text(source, encoding="utf-8")
    return path


def _compile(path: Path):
    parsed = parse_file(path)
    assert parsed.ast is not None and parsed.diagnostics == ()
    semantic = analyze(parsed.ast)
    assert semantic.diagnostics == ()
    lowered = build_ir(parsed.ast, semantic.model)
    assert lowered.ir is not None and lowered.diagnostics == ()
    definition = next(item for item in parsed.ast.definitions if type(item) is QueryDef)
    relation = next(item for item in lowered.ir.definitions if type(item) is RelationIR)
    return definition, semantic, lowered.ir, relation


def _bound_value(bound) -> list[object]:
    offset = bound.offset
    return [
        bound.kind.value,
        None
        if offset is None
        else offset.value
        if type(offset) is LiteralIR
        else "other",
    ]


def _frame_value(frame) -> object:
    if frame is None:
        return None
    return {
        "unit": frame.unit.value,
        "start": _bound_value(frame.start),
        "end": _bound_value(frame.end),
        "exclusion": frame.exclusion.value,
        "frame_explicit": frame.frame_is_explicit,
        "end_explicit": frame.end_is_explicit,
        "exclusion_explicit": frame.exclusion_is_explicit,
    }


def _call_value(name: str | None, call: WindowCallIR) -> dict[str, object]:
    named = call.named_use
    return {
        "output": name,
        "function": call.identity.name,
        "semantic_type": [
            call.value_type.canonical_name,
            call.value_type.nullability.value,
        ],
        "use": (
            [
                named.occurrence.kind.value,
                named.target.ordinal,
                named.reference_spelling,
                len(named.local_spec.partition_by),
                len(named.local_spec.order_by),
                named.local_spec.frame is not None,
            ]
            if named is not None
            else ["inline", None, None, 0, 0, False]
        ),
        "partition_count": len(call.spec.partition_by),
        "order": [
            [item.direction.value, item.direction_is_explicit]
            for item in call.spec.order_by
        ],
        "frame": _frame_value(call.spec.frame),
        "null_treatment": (
            None if call.null_treatment is None else call.null_treatment.value
        ),
        "null_explicit": call.null_treatment_is_explicit,
        "nth_direction": (
            None if call.nth_direction is None else call.nth_direction.value
        ),
        "nth_explicit": call.nth_direction_is_explicit,
    }


def _capability_fact_value(fact) -> object:
    if fact is None:
        return None
    key = fact.key
    return {
        "key": [
            key.domain.value,
            key.subject,
            key.operation,
            list(key.operands),
            key.context,
            key.dialect,
            key.extension,
        ],
        "support": fact.support.value,
        "evidence": [
            [
                item.source.value,
                item.source_path,
                item.source_reference,
                None if item.reason is None else item.reason.value,
                item.dialect,
                item.backend,
                item.extension,
            ]
            for item in fact.evidence
        ],
    }


def _evidence_value(item) -> dict[str, object]:
    return {
        "kind": item.kind.value,
        "outcome": item.outcome.value,
        "detail": item.detail,
        "occurrence": item.occurrence_ordinal,
        "capability": _capability_fact_value(item.capability_fact),
    }


def _decision_value(decision) -> object:
    if decision is None:
        return None
    return {
        "strategy": decision.strategy.value,
        "reachable": [
            [item.occurrence.ordinal, item.name]
            for item in decision.reachable_declarations
        ],
        "emission": [
            [item.occurrence.ordinal, item.name]
            for item in decision.emission_declarations
        ],
        "reason": decision.reason,
        "evidence": [_evidence_value(item) for item in decision.evidence],
        "inline": [
            {
                "output": item.call.named_use.occurrence.selected_output_ordinal,
                "supported": item.supported,
                "reason": item.failure_reason,
                "evidence": [_evidence_value(evidence) for evidence in item.evidence],
            }
            for item in decision.inline_decisions
        ],
    }


def _semantic_value(definition: QueryDef, semantic, relation: RelationIR):
    calls = {
        projection.name: projection.expression
        for projection in relation.projections
        if type(projection.expression) is WindowCallIR
    }
    values = []
    for item in definition.select_items:
        if type(item.expression) is not WindowExpr:
            continue
        call = calls[item.alias]
        assert type(call) is WindowCallIR
        analysis = semantic.model.window_expression_analyses[item.expression]
        result_type = analysis.semantic_fact.result.value_type
        assert result_type is not None
        values.append(
            {
                "output": item.alias,
                "semantic_type": [
                    result_type.resolved_type.name,
                    result_type.nullability.value,
                ],
                "analysis_use": analysis.authored_expression.use_kind.value,
                "target": (
                    None
                    if analysis.resolved_named_use is None
                    else analysis.resolved_named_use.composed.target_template.occurrence.declaration_position
                ),
                "ir": _call_value(item.alias, call),
            }
        )
    return values


def _diagnostic_value(diagnostic) -> dict[str, object]:
    location = diagnostic.location
    return {
        "code": diagnostic.code,
        "severity": diagnostic.severity.value,
        "message": diagnostic.message,
        "location": [
            Path(location.path).name,
            location.line,
            location.column,
            location.end_line,
            location.end_column,
        ],
    }


def _target_observation(root: Path, name: str, source: str, dialect):
    definition, semantic, script_ir, relation = _compile(
        _write_source(root, f"{name}.pietto", source)
    )
    decision = decide_named_window_lowering(relation, dialect)
    repeated_decision = decide_named_window_lowering(relation, dialect)
    decision_value = _decision_value(decision)
    assert _decision_value(repeated_decision) == decision_value
    emitter = (
        emit_postgres_sql
        if dialect is WindowTargetDialect.POSTGRESQL
        else emit_mysql_sql
    )
    first = emitter(script_ir)
    second = emitter(script_ir)
    assert first == second
    return relation, {
        "semantic": _semantic_value(definition, semantic, relation),
        "decision": decision_value,
        "artifacts": [
            [item.name, item.kind.value, item.sql] for item in first.artifacts
        ],
        "diagnostics": [_diagnostic_value(item) for item in first.diagnostics],
    }


def _write_graph_project(root: Path) -> Path:
    manifest = _manifest(1)
    package = root / "package"
    digest = _write_package(package, manifest, POSTGRES_NATIVE.encode())
    graph_probe._write_semantic_config(package)
    (root / "pietto.toml").write_text(
        _project_config("package", digest), encoding="utf-8"
    )
    return root


def _provenance_value(item) -> dict[str, object]:
    witness = item.witness
    return {
        "output": [
            item.output.declaration.module.package.position,
            item.output.declaration.module.position,
            item.output.declaration.position,
            item.output.position,
        ],
        "function": witness.function_identity.name,
        "use_kind": witness.use_kind.value,
        "target": None if item.named_target is None else item.named_target.position,
        "origins": [
            witness.partition_origin.value,
            witness.order_origin.value,
            witness.frame_origin.value,
        ],
        "frame": [
            witness.frame_applicability.value,
            None if witness.frame_unit is None else witness.frame_unit.value,
            None if witness.frame_start is None else witness.frame_start.kind.value,
            None if witness.frame_end is None else witness.frame_end.kind.value,
            None if witness.frame_exclusion is None else witness.frame_exclusion.value,
        ],
        "modifiers": [
            None if witness.null_treatment is None else witness.null_treatment.value,
            witness.null_treatment_is_explicit,
            None if witness.nth_direction is None else witness.nth_direction.value,
            witness.nth_direction_is_explicit,
        ],
    }


def _graph_observation(root: Path):
    _packages, _capabilities, snapshot = graph_probe._real_graph(
        _write_graph_project(root)
    )
    inspection = _inspect_package_graph(snapshot)
    evaluation = _evaluate_package_graph_inspection(inspection)
    assert evaluation.status is PackageGraphPureStatus.OK
    named_records = [
        graph_probe._record_value(item)
        for item in inspection.records
        if item.kind is PackageGraphInspectionRecordKind.NAMED_WINDOW
    ]
    semantic_records = [
        graph_probe._record_value(item)
        for item in inspection.records
        if item.kind is PackageGraphInspectionRecordKind.WINDOW_SEMANTIC
    ]
    named_links = [
        graph_probe._link_value(item)
        for item in inspection.links
        if item.kind
        in {
            PackageGraphInspectionLinkKind.NAMED_WINDOW_BASE,
            PackageGraphInspectionLinkKind.WINDOW_NAMED_TARGET,
        }
    ]
    return snapshot, {
        "canonical_sha256": graph_probe._digest(inspection.canonical_bytes),
        "canonical_size": len(inspection.canonical_bytes),
        "named_records": named_records,
        "semantic_records": semantic_records,
        "named_links": named_links,
        "provenance": [
            _provenance_value(item) for item in snapshot.window_semantic_provenance
        ],
        "lineage": [
            [
                item.output.position,
                item.role.value,
                item.global_position,
                item.role_position,
                type(item.upstream).__name__,
            ]
            for item in snapshot.current_window_lineage
        ],
    }


def _negative_project(root: Path, source: str) -> dict[str, object]:
    root.mkdir()
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    (root / "main.pietto").write_text(source, encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok
    semantic = build_empty_project_semantic_result(parsed)
    facts = semantic.module_semantic_facts
    assert facts is not None
    relation = next(
        item
        for environment in facts.environments
        for item in environment.relation_facts
        if item.owner.identity.declared_name == "result"
    )
    output = relation.window_outputs[0]
    assert output.project_fact is not None
    provenance = output.project_fact.semantic_provenance
    return {
        "status": output.status.value,
        "use_kind": provenance.use_kind.value,
        "target": (
            None
            if provenance.named_target is None
            else provenance.named_target.declaration_position
        ),
        "null_treatment": (
            None
            if provenance.null_treatment is None
            else provenance.null_treatment.value
        ),
        "null_explicit": provenance.null_treatment_is_explicit,
        "roles": [
            item.role.value for item in output.project_fact.dependency_occurrences
        ],
    }


def _cli_order(root: Path, reverse: bool) -> dict[str, object]:
    _write_source(root, "postgres.pietto", POSTGRES_NATIVE)
    _write_source(root, "mysql.pietto", MYSQL_NATIVE)
    postgres = ("emit-sql", "postgres.pietto", "--dialect", "postgres")
    mysql = ("emit-sql", "mysql.pietto", "--dialect", "mysql")
    commands = (mysql, postgres) if reverse else (postgres, mysql)
    first, second = _run_cli_pair(*commands, root)
    by_target = {item.args[-1]: item for item in (first, second)}
    return {
        target: [
            by_target[target].returncode,
            by_target[target].stdout.decode("utf-8"),
            by_target[target].stderr.decode("utf-8"),
        ]
        for target in ("postgres", "mysql")
    }


def _construction(root: Path, reverse: bool):
    root.mkdir()
    targets = {}
    postgres_relation: RelationIR | None = None
    order = (
        (
            ("mysql_native", MYSQL_NATIVE, WindowTargetDialect.MYSQL),
            ("postgres_native", POSTGRES_NATIVE, WindowTargetDialect.POSTGRESQL),
        )
        if reverse
        else (
            ("postgres_native", POSTGRES_NATIVE, WindowTargetDialect.POSTGRESQL),
            ("mysql_native", MYSQL_NATIVE, WindowTargetDialect.MYSQL),
        )
    )
    for name, source, dialect in order:
        relation, value = _target_observation(
            root / f"target-{name}", name, source, dialect
        )
        targets[name] = value
        if name == "postgres_native":
            postgres_relation = relation
    _fallback_relation, fallback = _target_observation(
        root / "target-fallback",
        "postgres_fallback",
        POSTGRES_FALLBACK,
        WindowTargetDialect.POSTGRESQL,
    )
    _inline_relation, inline = _target_observation(
        root / "target-inline",
        "postgres_inline",
        POSTGRES_FALLBACK_INLINE,
        WindowTargetDialect.POSTGRESQL,
    )
    _frames_relation, frames = _target_observation(
        root / "target-frames",
        "postgres_frames",
        POSTGRES_FRAMES,
        WindowTargetDialect.POSTGRESQL,
    )
    negatives = []
    for name, dialect, source in NEGATIVE_CASES:
        _negative_relation, value = _target_observation(
            root / f"negative-{name}", name, source, dialect
        )
        assert value["semantic"]
        assert value["decision"]["strategy"] == "not_lowerable"
        assert value["artifacts"] == []
        assert [item["code"] for item in value["diagnostics"]] == ["PIE-B1000"]
        negatives.append([name, value])
    assert fallback["artifacts"] == inline["artifacts"]
    snapshot, graph = _graph_observation(root / "graph-project")
    project = _negative_project(
        root / "negative-project",
        NEGATIVE_CASES[0][2],
    )
    cli = _cli_order(root / "cli", reverse)
    assert postgres_relation is not None
    return (
        snapshot,
        postgres_relation,
        {
            "targets": {
                "postgres_native": targets["postgres_native"],
                "mysql_native": targets["mysql_native"],
                "postgres_fallback": fallback,
                "postgres_inline": inline,
                "postgres_frames": frames,
            },
            "negatives": negatives,
            "negative_project": project,
            "graph": graph,
            "cli": cli,
        },
    )


def observation(workspace: Path) -> dict[str, object]:
    workspace.mkdir(parents=True, exist_ok=True)
    first_snapshot, first_relation, first = _construction(workspace / "first", False)
    second_snapshot, second_relation, second = _construction(workspace / "second", True)
    assert first == second
    assert first_snapshot.scope is not second_snapshot.scope
    assert first_snapshot.named_windows[0].ref != second_snapshot.named_windows[0].ref
    assert first_relation is not second_relation
    first_call = next(
        item.expression
        for item in first_relation.projections
        if type(item.expression) is WindowCallIR
    )
    second_call = next(
        item.expression
        for item in second_relation.projections
        if type(item.expression) is WindowCallIR
    )
    assert first_call.named_use is not None and second_call.named_use is not None
    assert first_call.named_use.occurrence != second_call.named_use.occurrence
    return {
        "observation_format": OBSERVATION_FORMAT,
        "package_version": version("pietto"),
        "runtime_identities_distinct": True,
        **first,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    namespace = parser.parse_args(argv)
    value = observation(namespace.workspace)
    document = (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=False,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    assert str(namespace.workspace).encode() not in document
    assert os.getcwd().encode() not in document
    irrelevant = os.environ.get("PIETTO_SLICE12_IRRELEVANT")
    if irrelevant is not None:
        assert irrelevant.encode() not in document
    assert b"0x" not in document
    sys.stdout.buffer.write(document)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
