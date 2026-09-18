"""Private scan/projection emission and production public artifact serialization."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any

from pietto._project.project_sql_emission_contract import (
    Blocker,
    InputError,
    PreparationFailure,
    PreparedEmission,
    Premise,
    CODES,
    canonical,
    prepare_project_sql_emission,
)
from pietto._project.project_sql_emission_ast import (
    SQLSelect,
    SQLLiteralColumn,
    build_sql_ast,
    build_requirements,
    emission_blockers,
    resource_limits,
)
from pietto._project import project_sql_emission_parameters as parameters
from pietto._project.project_sql_plan_literals import ProjectSQLFixedLiteralValue
from pietto._project.project_sql_emission_rendering import (
    RenderedSQL,
    SQLSizeLimit,
    render_sql,
)
from pietto._project.project_sql_emission_verification import (
    verify_sql_ast,
    verify_project_sql_emission,
)

__all__: tuple[str, ...] = ()
FORMAT = "pietto.sql-emission.v1"


@dataclass(frozen=True, slots=True, eq=False)
class EmissionArtifact:
    request: PreparedEmission
    ast: SQLSelect
    rendered: RenderedSQL
    original_requirements: tuple[Any, ...]
    generated_requirements: tuple[Any, ...]
    fixed_values: tuple[ProjectSQLFixedLiteralValue, ...] = ()
    parameter_uses: tuple[parameters.NativeUse, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class EmissionOutcome:
    status: str
    diagnostics: tuple[Any, ...]
    artifact: EmissionArtifact | None = None
    blockers: tuple[Blocker, ...] = ()
    cli_errors: tuple[InputError, ...] = ()


def emit_project_sql(verification, contract_bytes, *, target_request=None):
    request = prepare_project_sql_emission(
        verification, contract_bytes, target_request=target_request
    )
    if type(request) is PreparationFailure:
        return EmissionOutcome(
            "INPUT_REJECTED" if request.errors else "BLOCKED",
            request.diagnostics,
            blockers=request.blockers,
            cli_errors=request.errors,
        )
    return realize_project_sql(request)


def realize_project_sql(request):
    from pietto._project.project_sql_emission_verification import prepared_current

    if not prepared_current(request):
        return EmissionOutcome(
            "INPUT_REJECTED",
            (),
            cli_errors=(
                InputError("emission_selector", "Invalid prepared emission roots."),
            ),
        )
    diagnostics = request.verification.completed.diagnostics
    blockers = emission_blockers(request)
    if blockers:
        return EmissionOutcome("BLOCKED", diagnostics, blockers=blockers)
    ast = build_sql_ast(request)
    if not verify_sql_ast(request, ast):
        return EmissionOutcome(
            "BLOCKED",
            diagnostics,
            blockers=(Blocker("PIE-B1008", "plan_ast_correspondence"),),
        )
    try:
        rendered = render_sql(ast)
    except SQLSizeLimit:
        return EmissionOutcome(
            "BLOCKED", diagnostics, blockers=(Blocker("PIE-B1007", "sql_byte_limit"),)
        )
    original, generated = build_requirements(request, ast)
    uses = tuple(
        node.use
        for body in (*[cte.body for cte in ast.ctes], ast)
        for column in body.columns
        if type(column) is SQLLiteralColumn and column.value is not None
        for node in parameters.value_nodes(column.value)
        if type(node) is parameters.SQLParameter
    )
    artifact = EmissionArtifact(
        request,
        ast,
        rendered,
        original,
        generated,
        request.plan.fixed_envelope.values,
        uses,
    )
    checked = verify_project_sql_emission(artifact, request)
    if not checked.verified:
        return EmissionOutcome(
            "BLOCKED",
            diagnostics,
            blockers=tuple(Blocker("PIE-B1008", issue) for issue in checked.issues),
        )
    outcome = EmissionOutcome("VERIFIED", diagnostics, artifact)
    if (
        len(canonical(_public_document(outcome))) + 1
        > resource_limits(request)["artifact_bytes"]
    ):
        return EmissionOutcome(
            "BLOCKED",
            diagnostics,
            blockers=(Blocker("PIE-B1007", "public_artifact_byte_limit"),),
        )
    return outcome


def _ref(value):
    if type(value) is Premise:
        return {"kind": "premise", "position": value.position}
    if hasattr(value, "kind") and hasattr(value, "position"):
        return {"kind": value.kind.value, "position": value.position}
    return {"kind": "selected_plan", "position": 0}


def _location(value):
    if value is None:
        return None
    return {
        key: getattr(value, key, None)
        for key in ("path", "line", "column", "end_line", "end_column")
    }


def _failure(outcome):
    return {
        "format": FORMAT,
        "status": outcome.status,
        "artifact": None,
        "blockers": [
            {
                "code": blocker.code,
                "reason": CODES[blocker.code],
                "subject": {
                    "reference": _ref(blocker.subject),
                    "detail": blocker.detail,
                },
                "location": _location(blocker.location),
                "related": [_location(location) for location in blocker.related],
            }
            for blocker in outcome.blockers
        ],
        "diagnostics": [asdict(d) for d in outcome.diagnostics],
        "cli_errors": [asdict(error) for error in outcome.cli_errors],
    }


def _public_document(outcome):
    artifact = outcome.artifact
    assert artifact is not None
    request, ast = artifact.request, artifact.ast
    checked = request.verification
    semantic = checked.completed.semantic_result
    owner = checked.selected_owner
    source_map = request.source_map.source_map
    slots = {slot: i for i, slot in enumerate(request.plan.literal_slots)}
    columns = []
    for column in ast.columns:
        if type(column) is SQLLiteralColumn:
            origin = column.origin
            leaf = parameters.value_nodes(origin.value)[-1]
            producer = column.producer
            columns.append(
                {
                    "ordinal": column.ordinal,
                    "label": column.label,
                    "logical_type": {
                        "kind": "builtin",
                        "name": parameters.tag_of(origin.value.original),
                        "parameters": None,
                    },
                    "nullable": False,
                    "representation": parameters.representation(
                        origin.value, request.family
                    ),
                    "correspondence": {
                        "literal_origin": {
                            "expression": _ref(origin.value.original.ref),
                            "leaf": _ref(leaf.original.ref),
                            "site": _ref(leaf.site.ref),
                            "slot": slots[leaf.fixed.slot]
                            if type(leaf) is parameters.SQLParameter
                            else None,
                            "export": _ref(origin.export.ref),
                            "terminal": _ref(origin.terminal.ref),
                        },
                        "expression": _ref(column.projection.expression),
                        "input_port": None
                        if producer is None
                        else _ref(producer.input_port.ref),
                        "producer": None
                        if producer is None
                        else {
                            "export": _ref(producer.canonical.ref),
                            "terminal": _ref(producer.terminal.ref),
                        },
                        "export": _ref(column.export.ref),
                        "projection": _ref(column.projection.ref),
                        "sql_symbol": column.symbol.position,
                    },
                }
            )
            continue
        field = column.source_field
        logical = field.field.evidence.resolved_type
        columns.append(
            {
                "ordinal": column.ordinal,
                "label": column.label,
                "logical_type": {
                    "kind": logical.kind.value,
                    "name": logical.name,
                    "parameters": None
                    if field.decimal is None
                    else {
                        "precision": field.decimal.precision,
                        "scale": field.decimal.scale,
                    },
                },
                "nullable": json.loads(field.representation)["nullable"],
                "representation": json.loads(field.representation),
                "correspondence": {
                    "source": json.loads(column.origin.realization.selector),
                    "field": field.ordinal,
                    "source_port": _ref(column.source_port.ref),
                    "input_port": _ref(column.input_port.ref),
                    "export": _ref(column.export.ref),
                    "projection": _ref(column.projection.ref),
                    "sql_symbol": column.symbol.position,
                },
            }
        )
    ranges = []
    for event in (*artifact.rendered.events, *artifact.rendered.expression_ranges):
        ranges.append(
            {
                "start": event.start,
                "end": event.end,
                "kind": event.kind,
                "role": event.role,
                "subject": _ref(event.subject),
                "origins": [
                    {
                        "position": entry.position,
                        "role": entry.original.role.value,
                        "sources": [
                            {
                                "path": a.site.source.display_path,
                                "kind": a.kind.value,
                                "location": _location(a.site.location),
                            }
                            for a in source_map.indexes.associations[entry.ref]
                        ],
                    }
                    for entry in event.origins
                ],
            }
        )
    requirements = []
    for i, item in enumerate(artifact.original_requirements):
        requirements.append(
            {
                "denominator": "original",
                "ordinal": i,
                "kind": item.entry.family.value,
                "subject": _ref(item.entry.subject),
                "rule": item.rule,
                "disposition": "checked_rule",
                "premises": [],
                "evidence": [
                    [state.value for state in aspect.outcomes]
                    for aspect in request.assessment.assessment.demands[i].aspects
                ],
            }
        )
    for i, item in enumerate(artifact.generated_requirements):
        evidence = []
        if item.kind in {"literal", "unary"}:
            expression = request.plan.expressions[item.subject.position]
            if item.kind == "literal":
                tag = parameters.tag_of(expression)
                evidence = [
                    {
                        "tag": tag,
                        "value": parameters.wire_value(
                            tag, expression.expression.value
                        ),
                    }
                ]
            else:
                evidence = [{"operator": expression.expression.operator}]
        requirements.append(
            {
                "denominator": "generated",
                "ordinal": i,
                "kind": item.kind,
                "subject": _ref(item.subject)
                if item.kind
                in {
                    "cte_definition",
                    "terminal_column",
                    "named_use",
                    "immediate_terminal",
                    "value_projection",
                    "literal",
                    "parameter",
                    "type_anchor",
                    "unary",
                }
                else {"kind": item.kind, "position": i},
                "rule": item.rule,
                "disposition": "checked_rule",
                "premises": [p.position for p in item.premises],
                "evidence": evidence,
            }
        )
    return {
        "format": FORMAT,
        "status": "VERIFIED",
        "target": {
            "family": request.family,
            "release": request.release,
            "environment": json.loads(request.normalized_bytes)["environment"],
        },
        "request": {
            "owner": {
                "module": semantic.modules[owner.module_position].path,
                "kind": owner.identity.declaration_kind.value,
                "name": owner.definition.name,
            },
            "sources": [
                {
                    "module": source.identity.path,
                    "sha256": source.sha256,
                    "byte_count": source.byte_count,
                }
                for source in semantic.trusted_source_snapshots
            ],
            "contract": json.loads(request.normalized_bytes),
            "literal_policy": checked.literal_policy.value,
        },
        "sql": artifact.rendered.sql.decode("utf-8"),
        "fixed_values": [
            {
                "slot": i,
                "reference": _ref(value.slot.ref),
                "site": _ref(value.slot.site.ref),
                "tag": value.tag.value,
                "value": parameters.wire_value(value.tag.value, value.value),
            }
            for i, value in enumerate(artifact.fixed_values)
        ],
        "parameter_uses": [
            {
                "use": use.ordinal,
                "slot": slots[use.slot],
                "server_index": use.server_index,
                "physical_type": use.physical_type,
                "range": {"start": token.start, "end": token.end},
            }
            for use, token in zip(
                artifact.parameter_uses,
                (e for e in artifact.rendered.events if e.kind == "parameter"),
                strict=True,
            )
        ],
        "columns": columns,
        "ranges": ranges,
        "requirements": requirements,
        "diagnostics": [asdict(d) for d in outcome.diagnostics],
    }


def serialize_project_sql_emission(outcome: EmissionOutcome) -> bytes:
    if type(outcome) is not EmissionOutcome:
        raise TypeError("Public serialization requires an emission outcome.")
    if outcome.status == "VERIFIED":
        artifact = outcome.artifact
        if (
            artifact is None
            or outcome.blockers
            or outcome.cli_errors
            or outcome.diagnostics
            is not artifact.request.verification.completed.diagnostics
            or not verify_project_sql_emission(artifact, artifact.request).verified
        ):
            outcome = EmissionOutcome(
                "BLOCKED",
                outcome.diagnostics,
                blockers=(Blocker("PIE-B1008", "artifact_correspondence"),),
            )
        else:
            data = canonical(_public_document(outcome)) + b"\n"
            if len(data) <= resource_limits(artifact.request)["artifact_bytes"]:
                return data
            outcome = EmissionOutcome(
                "BLOCKED",
                outcome.diagnostics,
                blockers=(Blocker("PIE-B1007", "public_artifact_byte_limit"),),
            )
    if (
        outcome.status not in {"INPUT_REJECTED", "BLOCKED"}
        or outcome.artifact is not None
        or (outcome.status == "INPUT_REJECTED") != bool(outcome.cli_errors)
        or (
            outcome.status == "BLOCKED"
            and not outcome.blockers
            and not any(d.severity.value == "error" for d in outcome.diagnostics)
        )
        or any(b.code not in CODES for b in outcome.blockers)
    ):
        raise ValueError("Invalid emission failure branch.")
    return canonical(_failure(outcome)) + b"\n"
