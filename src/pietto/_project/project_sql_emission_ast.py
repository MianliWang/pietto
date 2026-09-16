"""Closed direct SELECT structure, exact ports, and finite realization rules."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from typing import Any
from pietto.ast_nodes import SourceDef

from pietto._project import project_sql_plan_expressions as row
from pietto._project.model import ProjectResolvedTypeKind
from pietto._project.project_sql_emission_scopes import (
    ScopeDefinition,
    ScopeUse,
    TerminalBinding,
    projection_sources,
)
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
    binding: ScopeUse


@dataclass(frozen=True, slots=True, eq=False)
class SQLNamedUse:
    cte: SQLCTE
    use: Any
    symbol: SQLSymbol
    binding: ScopeUse


@dataclass(frozen=True, slots=True, eq=False)
class SQLColumn:
    ordinal: int
    scan: SQLScan | SQLNamedUse
    source_field: BoundField
    source_port: Any
    input_port: Any
    export: Any
    projection: Any
    symbol: SQLSymbol
    label: str
    producer: TerminalBinding
    origin: SQLScan


@dataclass(frozen=True, slots=True, eq=False)
class SQLSelect:
    request: PreparedEmission
    scan: SQLScan | SQLNamedUse
    columns: tuple[SQLColumn, ...]
    definition: ScopeDefinition
    ctes: tuple[SQLCTE, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class SQLCTE:
    definition: ScopeDefinition
    symbol: SQLSymbol
    columns: tuple[SQLSymbol, ...]
    body: SQLSelect


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


def projection_chain_shape(plan):
    named = tuple(
        d
        for d in plan.bindings.definitions
        if type(d.entry.owner.definition) is not SourceDef
    )
    return (
        bool(named)
        and len(plan.sources) == 1
        and len(plan.blocks) == len(named) == len(plan.input_uses)
        and all(
            tuple(o.kind.value for o in block.operators)
            == ("relation_input", "final_projection")
            for block in plan.blocks
        )
        and all(
            sum(block.definition is d.ref for block in plan.blocks) == 1
            and sum(use.consumer is d.ref for use in plan.input_uses) == 1
            and bool(d.exports)
            for d in named
        )
        and len(plan.projections)
        == len(plan.all_exports)
        == len(plan.expressions)
        == len(plan.expression_sites)
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
                plan.fixed_envelope.slots,
                plan.fixed_envelope.values,
            )
        )
    )


def applicable_premises(request, owner, field=None):
    plan = request.plan
    sources = projection_sources(plan)
    sites = (
        ()
        if field is None
        else tuple(
            p.site
            for p in plan.projections
            if p.source_port in sources and sources[p.source_port].field is field.field
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
    admitted = projection_chain_shape(plan)
    if not admitted:
        shape_start = len(result)
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
    bodies = tuple(
        d
        for d in request.layout.definitions
        if type(d.original.entry.owner.definition) is not SourceDef
    )
    intermediate = tuple(
        d for d in bodies if d.original.entry.owner is not plan.scope.selected_owner
    )
    nodes = (
        3 * len(bodies)
        + 2 * len(plan.projections)
        + sum(2 + len(d.terminals) for d in intermediate)
    )
    if admitted and (
        any(len(d.terminals) > limits["columns"] for d in bodies)
        or nodes > limits["nodes"]
    ):
        add("PIE-B1007", "generated_structure_limit", plan.scope)
    if admitted and intermediate:
        names = [p for p in request.premises if p.key == "identifier_case"]
        expected = (
            "quoted_exact"
            if request.family == "postgres"
            else "lower_case_table_names=0"
        )
        if not names:
            add("PIE-B1004", "identifier_case_declaration_missing", plan.scope)
        elif any(json.loads(p.value) != expected for p in names):
            add("PIE-B1005", "identifier_case_declaration_mismatch", plan.scope)
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
    sources = {source.ref: source for source in plan.sources}
    bindings = {use.consumer.original.ref: use for use in request.layout.uses}
    blocks = {block.definition: block for block in plan.blocks}
    ctes: dict[Any, SQLCTE] = {}
    selected = None
    for definition in request.layout.definitions:
        original = definition.original
        if original.ref in sources:
            continue
        binding = bindings[original.ref]
        use = binding.original
        alias = SQLSymbol(0, use.ref, f"s{use.ref.position}")
        scan: SQLScan | SQLNamedUse
        if use.producer in sources:
            source = sources[use.producer]
            (bound,) = tuple(
                s for s in request.sources if s.owner is source.source.owner
            )
            scan = SQLScan(source, bound, use, alias, binding)
        else:
            scan = SQLNamedUse(ctes[use.producer], use, alias, binding)
        projections = tuple(
            p for p in plan.projections if p.block is blocks[original.ref].ref
        )
        by_input = {b.input_port.ref: (i, b) for i, b in enumerate(binding.bindings)}
        columns = []
        final = original.entry.owner is plan.scope.selected_owner
        for position, (projection, export) in enumerate(
            zip(projections, original.exports, strict=True)
        ):
            port_position, producer = by_input[projection.input_port]
            if type(scan) is SQLScan:
                origin = scan
                source_port = producer.canonical
                (field,) = tuple(
                    f for f in scan.realization.fields if f.field is source_port.field
                )
                name = field.column
            else:
                assert type(scan) is SQLNamedUse
                previous = scan.cte.body.columns[port_position]
                origin, source_port, field = (
                    previous.origin,
                    previous.source_port,
                    previous.source_field,
                )
                name = scan.cte.columns[port_position].name
            columns.append(
                SQLColumn(
                    position,
                    scan,
                    field,
                    source_port,
                    producer.input_port,
                    export,
                    projection,
                    SQLSymbol(position + 1, producer.input_port.ref, name),
                    export.identity.name if final else f"c{position}",
                    producer,
                    origin,
                )
            )
        body = SQLSelect(request, scan, tuple(columns), definition)
        if final:
            selected = body
        else:
            ctes[original.ref] = SQLCTE(
                definition,
                SQLSymbol(len(ctes), original.ref, f"p{len(ctes)}"),
                tuple(
                    SQLSymbol(i, terminal.ref, f"c{i}")
                    for i, terminal in enumerate(definition.terminals)
                ),
                body,
            )
    assert selected is not None
    return replace(selected, ctes=tuple(ctes.values()))


def build_requirements(request, ast):
    original = tuple(
        OriginalRequirement(
            entry,
            "R03"
            if ast.ctes and entry.family.value == "scope"
            else "R01"
            if entry.family.value in {"source_realization", "expression", "scope"}
            else "R02",
        )
        for entry in request.report.report.entries
    )
    generated = []
    naming = tuple(
        p
        for p in request.premises
        if p.scope == "statement" and p.key == "identifier_case"
    )
    for cte in ast.ctes:
        generated.append(
            GeneratedRequirement(
                "cte_definition", cte.definition.original.ref, "R03", naming
            )
        )
        generated.extend(
            GeneratedRequirement("terminal_column", terminal.ref, "R03", naming)
            for terminal in cte.definition.terminals
        )
    for body in (*[cte.body for cte in ast.ctes], ast):
        scan = body.scan
        if type(scan) is SQLScan:
            generated.append(
                GeneratedRequirement(
                    "qualified_scan",
                    scan,
                    "R01",
                    applicable_premises(request, scan.realization.owner),
                )
            )
            generated.extend(
                GeneratedRequirement(
                    "source_representation",
                    field,
                    "R02",
                    applicable_premises(request, scan.realization.owner, field),
                )
                for field in scan.realization.fields
            )
        else:
            generated.append(
                GeneratedRequirement("named_use", scan.use.ref, "R03", naming)
            )
            generated.extend(
                GeneratedRequirement(
                    "immediate_terminal", link.terminal.ref, "R03", naming
                )
                for link in scan.binding.bindings
            )
        for column in body.columns:
            generated.append(
                GeneratedRequirement(
                    "field_projection",
                    column,
                    "R02",
                    applicable_premises(
                        request, column.origin.realization.owner, column.source_field
                    ),
                )
            )
        generated.append(
            GeneratedRequirement("read_only_select_bytes", body, "R23", ())
        )
    if ast.ctes:
        generated.append(
            GeneratedRequirement("nonrecursive_with_bytes", ast, "R23", ())
        )
    return original, tuple(generated)
