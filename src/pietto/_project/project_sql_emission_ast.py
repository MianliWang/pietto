"""Closed direct SELECT structure, exact ports, and finite realization rules."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
from pietto.ast_nodes import SourceDef

from pietto._project import project_sql_plan_expressions as row
from pietto._project.model import ProjectResolvedTypeKind
from pietto._project.project_sql_emission_contract import (
    Blocker,
    BoundField,
    BoundSource,
    PreparedEmission,
    RELEASES,
    MAX_NODES,
    MAX_SQL_BYTES,
    MAX_ARTIFACT_BYTES,
    MAX_PARAMETERS,
    source_family,
)

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class SQLSymbol:
    position: int
    binding: object
    name: str


@dataclass(frozen=True, slots=True, eq=False)
class SQLScan:
    source: Any
    realization: BoundSource
    use: Any
    symbol: SQLSymbol


@dataclass(frozen=True, slots=True, eq=False)
class SQLColumn:
    ordinal: int
    scan: SQLScan
    source_field: BoundField
    source_port: Any
    input_port: Any
    export: Any
    projection: Any
    symbol: SQLSymbol
    label: str


@dataclass(frozen=True, slots=True, eq=False)
class SQLSelect:
    request: PreparedEmission
    scan: SQLScan
    columns: tuple[SQLColumn, ...]


@dataclass(frozen=True, slots=True, eq=False)
class OriginalRequirement:
    entry: Any
    rule: str


@dataclass(frozen=True, slots=True, eq=False)
class GeneratedRequirement:
    kind: str
    subject: object
    rule: str
    premises: tuple[Any, ...]


def identifier_valid(name, family, *, label=False, relation=False):
    if type(name) is not str or not name or "\0" in name:
        return False
    try:
        encoded = name.encode("utf-8")
    except UnicodeError:
        return False
    if family == "postgres":
        return len(encoded) <= 63
    if (
        family != "mysql"
        or len(name) > (256 if label else 64)
        or any(ord(c) > 0xFFFF for c in name)
    ):
        return False
    if not label and name.endswith(" "):
        return False
    return not relation or not any(c in name for c in (".", "/", "\\"))


def direct_shape(plan):
    return (
        len(plan.sources) == len(plan.input_uses) == len(plan.blocks) == 1
        and tuple(o.kind.value for o in plan.blocks[0].operators)
        == ("relation_input", "final_projection")
        and plan.input_uses[0].producer is plan.sources[0].ref
        and len(plan.bindings.definitions) == 2
        and plan.bindings.definitions[0].entry.owner is plan.sources[0].source.owner
        and plan.bindings.definitions[1].entry.owner is plan.scope.selected_owner
        and len(plan.projections)
        == len(plan.exports)
        == len(plan.expressions)
        == len(plan.expression_sites)
        and bool(plan.exports)
        and all(type(e) is row.ProjectSQLReference for e in plan.expressions)
        and not any(
            (
                plan.let_values,
                plan.filters,
                plan.joins,
                plan.aggregations,
                plan.windows,
                plan.distincts,
                plan.orders,
                plan.result_limits,
                plan.set_bodies,
                plan.operands,
                plan.bind_uses,
                plan.literal_slots,
                plan.fixed_envelope.values,
            )
        )
    )


def applicable_premises(request, owner, field=None):
    plan = request.plan
    sites = (
        ()
        if field is None
        else tuple(
            p.site
            for p in plan.projections
            if p.source_port is not None
            and any(
                port.ref is p.source_port and port.field is field.field
                for port in plan.source_ports
            )
        )
    )
    return tuple(
        p
        for p in request.premises
        if p.scope == "statement"
        or p.scope is owner
        or (
            type(p.scope) is tuple
            and p.scope[0] is owner
            and any(p.scope[1] is s for s in sites)
        )
    )


def resource_limits(request):
    limits = {
        "sql_bytes": MAX_SQL_BYTES,
        "artifact_bytes": MAX_ARTIFACT_BYTES,
        "nodes": MAX_NODES,
        "parameters": MAX_PARAMETERS,
        "columns": 1664 if request.family == "postgres" else 4096,
    }
    for premise in request.premises:
        if premise.scope == "statement" and premise.key == "resource_limits":
            for key, value in json.loads(premise.value).items():
                limits[key] = min(limits[key], value)
    return limits


def representation_problem(field: BoundField, family: str):
    value = json.loads(field.representation)
    storage, domain = value["storage"], value["domain"]
    evidence = field.field.evidence
    logical = evidence.resolved_type
    resolution = field.resolution
    if (
        resolution is None
        or resolution.reference.type_expr is not evidence.field_def.type_expr
        or resolution.canonical_kind is not logical.kind
        or resolution.canonical_name != logical.name
    ):
        return "PIE-B1004", "logical_type_evidence_missing"
    if logical.kind is not ProjectResolvedTypeKind.BUILTIN:
        return "PIE-B1003", "representation_not_in_initial_domain"
    if logical.name in {"Timestamp", "UUID"}:
        return "PIE-B1004", "logical_temporal_or_uuid_meaning_missing"
    nullability = {"non_null": False, "nullable": True, "unknown": "unknown"}[
        field.field.effective_nullability.value
    ]
    if value["nullable"] != nullability or type(value["nullable"]) is not type(
        nullability
    ):
        return "PIE-B1002", "nullability_mismatch"
    kind = storage["kind"]
    prefix = "pg_" if family == "postgres" else "my_"
    valid = kind.startswith(prefix)
    if logical.name == "Int":
        bits = {
            "pg_int2": 16,
            "pg_int4": 32,
            "pg_int8": 64,
            "my_smallint": 16,
            "my_int": 32,
            "my_bigint": 64,
        }.get(kind)
        valid = valid and bits is not None and domain["kind"] == "int_range"
        if valid and bits is not None:
            valid = (
                -(1 << (bits - 1))
                <= int(domain["min"])
                <= int(domain["max"])
                < 1 << (bits - 1)
            )
    elif logical.name == "Bool":
        valid = (
            valid and kind in {"pg_bool", "my_bool01"} and domain["kind"] == "bool01"
        )
    elif logical.name == "Text":
        valid = valid and kind in {"pg_text", "my_varchar"} and domain["kind"] == "text"
        if valid:
            expected = (
                ("UTF8", "C", "NO PAD")
                if family == "postgres"
                else ("utf8mb4", "utf8mb4_0900_bin", "NO PAD")
            )
            valid = (
                tuple(domain[k] for k in ("encoding", "collation", "padding"))
                == expected
            )
            if kind == "my_varchar":
                valid = valid and domain["max_characters"] <= storage["length"] <= 16383
    elif logical.name == "Decimal":
        if field.decimal is None:
            return "PIE-B1004", "validated_decimal_parameters_missing"
        valid = (
            valid
            and kind in {"pg_numeric", "my_decimal"}
            and domain["kind"] == "decimal"
        )
        if valid:
            pair = (field.decimal.precision, field.decimal.scale)
            valid = (
                pair
                == (storage["precision"], storage["scale"])
                == (domain["precision"], domain["scale"])
                and 1 <= pair[0] <= 65
                and 0 <= pair[1] <= min(pair[0], 30)
            )
    elif logical.name == "Float":
        valid = (
            valid
            and kind in {"pg_float8", "my_double"}
            and domain["kind"] == "finite_float"
        )
    else:
        return "PIE-B1003", "representation_not_in_initial_domain"
    return None if valid else ("PIE-B1002", "physical_storage_or_domain_mismatch")


def emission_blockers(request: PreparedEmission):
    plan = request.plan
    result = list(request.input_blockers)

    def add(code, detail, subject=None, location=None):
        result.append(Blocker(code, detail, subject, location))

    if RELEASES.get(request.family) != request.release:
        add("PIE-B1003", "target_release_not_reviewed")
    if not direct_shape(plan):
        shape_start = len(result)
        for definition in plan.bindings.definitions:
            if (
                definition.entry.owner is not plan.scope.selected_owner
                and type(definition.entry.owner.definition) is not SourceDef
            ):
                add("PIE-B1003", "named_producers_require_slice4", definition.ref)
        for block in plan.blocks:
            for operator in block.operators:
                if operator.kind.value not in {"relation_input", "final_projection"}:
                    add("PIE-B1003", "operator_not_implemented_in_slice3", block.ref)
        expressions = {e.ref: e for e in plan.expressions}
        for projection in plan.projections:
            if (
                type(expressions.get(projection.expression))
                is not row.ProjectSQLReference
            ):
                add(
                    "PIE-B1003",
                    "scalar_projection_requires_later_slice",
                    projection.ref,
                    projection.site.occurrence.span,
                )
        for body in plan.set_bodies:
            add("PIE-B1003", "set_lowering_requires_slice11", body.ref)
        if len(result) == shape_start:
            add("PIE-B1003", "non_field_projection_or_later_shape", plan.scope)
    for issue in request.target_request.issues:
        if issue.value == "profile_target_family_or_release_mismatch":
            add("PIE-B1005", "target_evidence_scope_conflict", request.target_request)
        elif issue.value == "profile_composition_blocked":
            add(
                "PIE-B1006",
                "original_profile_composition_unresolved",
                request.target_request,
            )
    limits = resource_limits(request)
    if (
        len(plan.exports) > limits["columns"]
        or 3 + 2 * len(plan.projections) > limits["nodes"]
    ):
        add("PIE-B1007", "generated_structure_limit", plan.scope)
    for aspect in request.assessment.assessment.aspects:
        if any(
            state.value in {"exact_negative", "conflicting_facts"}
            for state in aspect.outcomes
        ):
            add("PIE-B1006", "negative_original_target_evidence", aspect.entry.subject)
    for obligation in request.report.report.summary.enforcement_required:
        add("PIE-B1006", "original_enforcement_not_fulfilled", obligation.entry.subject)
    for source in plan.sources:
        if source_family(source) != request.family:
            add(
                "PIE-B1001",
                "source_family_mismatch",
                source.ref,
                source.declaration.span,
            )
        matches = tuple(s for s in request.sources if s.owner is source.source.owner)
        if len(matches) != 1:
            add(
                "PIE-B1001",
                "source_mapping_missing",
                source.ref,
                source.declaration.span,
            )
            continue
        bound = matches[0]
        original = tuple(p for p in plan.source_ports if p.owner is source.ref)
        if tuple(f.ordinal for f in bound.fields) != tuple(range(len(original))) or any(
            f.field is not p.field for f, p in zip(bound.fields, original)
        ):
            add("PIE-B1001", "complete_ordered_source_schema_required", source.ref)
        if not all(
            identifier_valid(n, request.family, relation=True)
            for n in (bound.namespace, bound.name)
        ):
            add("PIE-B1001", "source_identifier_unrepresentable", source.ref)
        used = applicable_premises(request, bound.owner)
        for key in ("row_domain_matches", "read_only_object"):
            values = [p for p in used if p.key == key]
            if not values or any(p.value != b"true" for p in values):
                add("PIE-B1001", key + "_declaration_required", source.ref)
        clients = [p for p in used if p.key == "client_encoding"]
        if not clients:
            add("PIE-B1004", "client_encoding_declaration_missing", source.ref)
        elif any(
            json.loads(p.value)
            != ("UTF8" if request.family == "postgres" else "utf8mb4")
            for p in clients
        ):
            add("PIE-B1005", "client_encoding_mismatch", source.ref)
        columns = set()
        for field in bound.fields:
            subject = original[field.ordinal].ref
            column_key = (
                field.column
                if request.family == "postgres"
                else field.column.casefold()
            )
            if (
                not identifier_valid(field.column, request.family)
                or column_key in columns
            ):
                add(
                    "PIE-B1001",
                    "column_identifier_unrepresentable_or_colliding",
                    subject,
                )
            columns.add(column_key)
            problem = representation_problem(field, request.family)
            if problem is not None:
                add(
                    *problem,
                    subject,
                    field.field.evidence.field_def.span
                    if field.field.evidence.field_def
                    else None,
                )
            domain = json.loads(field.representation)["domain"]
            for premise in applicable_premises(request, bound.owner, field):
                expected = (
                    domain if premise.key == "value_domain" else domain.get(premise.key)
                )
                if expected is not None and json.loads(premise.value) != expected:
                    add("PIE-B1005", "field_domain_premise_mismatch", subject)
    for port in plan.exports:
        if not identifier_valid(port.identity.name, request.family, label=True):
            add("PIE-B1002", "output_label_unrepresentable", port.ref)
    return tuple(result)


def build_sql_ast(request: PreparedEmission):
    plan = request.plan
    (source,), (use,) = plan.sources, plan.input_uses
    (bound,) = tuple(s for s in request.sources if s.owner is source.source.owner)
    scan = SQLScan(source, bound, use, SQLSymbol(0, use.ref, "s0"))
    columns = []
    for position, projection in enumerate(plan.projections):
        (source_port,) = tuple(
            p for p in plan.source_ports if p.ref is projection.source_port
        )
        (input_port,) = tuple(
            p for p in plan.input_ports if p.ref is projection.input_port
        )
        export = plan.exports[position]
        (field,) = tuple(f for f in bound.fields if f.field is source_port.field)
        columns.append(
            SQLColumn(
                position,
                scan,
                field,
                source_port,
                input_port,
                export,
                projection,
                SQLSymbol(position + 1, input_port.ref, field.column),
                export.identity.name,
            )
        )
    return SQLSelect(request, scan, tuple(columns))


def build_requirements(request, ast):
    original = tuple(
        OriginalRequirement(
            entry,
            "R01"
            if entry.family.value in {"source_realization", "expression", "scope"}
            else "R02",
        )
        for entry in request.report.report.entries
    )
    generated = [
        GeneratedRequirement(
            "qualified_scan",
            ast.scan,
            "R01",
            applicable_premises(request, ast.scan.realization.owner),
        )
    ]
    generated.extend(
        GeneratedRequirement(
            "source_representation",
            field,
            "R02",
            applicable_premises(request, ast.scan.realization.owner, field),
        )
        for field in ast.scan.realization.fields
    )
    generated.extend(
        GeneratedRequirement(
            "field_projection",
            column,
            "R02",
            applicable_premises(
                request, ast.scan.realization.owner, column.source_field
            ),
        )
        for column in ast.columns
    )
    generated.append(GeneratedRequirement("read_only_select_bytes", ast, "R23", ()))
    return original, tuple(generated)
