"""Independent correspondence checks; no construction, rendering or type inference."""

from __future__ import annotations

from dataclasses import dataclass
import json

from pietto._project import project_sql_plan as plans
from pietto._project.project_query_block_ir import ProjectIRReusedEffectiveOutput
from pietto._project import project_sql_plan_expressions as row
from pietto._project.project_sql_plan_verification import verify_project_sql_plan
from pietto._project.project_sql_plan_requirements import (
    verify_project_sql_requirement_report,
)
from pietto._project.project_sql_plan_source_maps import verify_project_sql_source_map
from pietto._project.project_sql_plan_target_assessment import (
    verify_project_sql_target_assessment,
)
from pietto._project.project_sql_emission_contract import PreparedEmission
from pietto._project.project_sql_emission_scopes import verify_emission_layout
from pietto._project.project_sql_emission_ast import (
    SQLSelect,
    SQLScan,
    SQLColumn,
    SQLSymbol,
    SQLCTE,
    SQLNamedUse,
    OriginalRequirement,
    GeneratedRequirement,
    projection_chain_shape,
    identifier_valid,
    applicable_premises,
    resource_limits,
    emission_blockers,
)
from pietto._project.project_sql_emission_rendering import RenderedSQL, RenderingEvent

__all__: tuple[str, ...] = ()


def _same(actual, expected):
    return (
        type(actual) is tuple
        and len(actual) == len(expected)
        and all(a is b for a, b in zip(actual, expected, strict=True))
    )


def prepared_current(request):
    if type(request) is not PreparedEmission:
        return False
    names = (
        "verification",
        "accepted_bytes",
        "normalized_bytes",
        "family",
        "release",
        "sources",
        "premises",
        "target_request",
        "report",
        "source_map",
        "assessment",
        "layout",
        "input_blockers",
    )
    if not _same(tuple(getattr(request, n) for n in names), request._accepted):
        return False
    checked = request.verification
    if (
        type(checked.plan) is not plans.ProjectSQLPlan
        or not verify_project_sql_plan(
            checked.plan,
            checked.completed,
            checked.analysis_bundle,
            checked.selected_owner,
            literal_policy=checked.literal_policy,
            envelope=checked.envelope,
        ).verified
    ):
        return False
    if (
        not verify_project_sql_requirement_report(
            request.report.report, checked
        ).verified
        or request.report.source_verification is not checked
    ):
        return False
    if (
        not verify_project_sql_source_map(
            request.source_map.source_map, checked
        ).verified
        or request.source_map.source_verification is not checked
    ):
        return False
    if (
        not verify_project_sql_target_assessment(
            request.assessment.assessment, checked, request.target_request
        ).verified
        or request.assessment.source_verification is not checked
    ):
        return False
    if not verify_emission_layout(request.layout, checked):
        return False
    # Binding was done once. Check retained occurrence/ordinal correspondence,
    # without running a selector resolver or the construction-time Decimal rule.
    document = json.loads(request.normalized_bytes)
    if len(document["sources"]) != len(request.sources):
        return False
    for source, description in zip(request.sources, document["sources"], strict=True):
        if (
            source.selector
            != json.dumps(
                description["selector"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
            or (source.namespace, source.name)
            != (description["relation"]["namespace"], description["relation"]["name"])
            or len(source.fields) != len(description["fields"])
        ):
            return False
        entries = checked.analysis_bundle.root.find_owner(source.owner)
        if (
            len(entries) != 1
            or type(entries[0]) is not ProjectIRReusedEffectiveOutput
            or not any(
                source.owner is owner for owner in checked.analysis_bundle.root.owners
            )
        ):
            return False
        fields = entries[0].active_properties.relational.fields
        for field, field_description in zip(
            source.fields, description["fields"], strict=True
        ):
            if (field.ordinal, field.name, field.column) != (
                field_description["ordinal"],
                field_description["name"],
                field_description["column"],
            ) or json.loads(field.representation) != field_description[
                "representation"
            ]:
                return False
            if (
                type(field.ordinal) is not int
                or not 0 <= field.ordinal < len(fields)
                or field.field is not fields[field.ordinal]
                or field.name != field.field.evidence.name
            ):
                return False
            if field.resolution is not None:
                types = checked.completed.semantic_result.module_type_source_resolutions
                if types is None or not any(
                    field.resolution is value
                    for env in types.environments
                    for value in env.type_resolutions
                ):
                    return False
            if field.decimal is not None:
                # This is correspondence to the retained checked argument values,
                # not creation/validation of a Pietto Decimal semantic fact.
                expression = field.decimal_expression
                if (
                    expression is None
                    or len(expression.arguments) != 2
                    or tuple(
                        getattr(a.value, "value", None) for a in expression.arguments
                    )
                    != (field.decimal.precision, field.decimal.scale)
                ):
                    return False
    return True


def verify_sql_ast(request, ast):
    try:
        if (
            not prepared_current(request)
            or type(ast) is not SQLSelect
            or ast.request is not request
        ):
            return False
        plan = request.plan
        if not projection_chain_shape(plan) or emission_blockers(request):
            return False
        sources = {s.ref: s for s in plan.sources}
        definitions = tuple(
            d for d in request.layout.definitions if d.original.ref not in sources
        )
        if (
            type(ast.ctes) is not tuple
            or len(ast.ctes) != len(definitions) - 1
            or ast.definition is not definitions[-1]
            or definitions[-1].original.entry.owner is not plan.scope.selected_owner
        ):
            return False
        available = {}
        provenance = {}
        symbols = []
        nodes = []
        bodies = (*[cte.body for cte in ast.ctes], ast)
        for index, (definition, body) in enumerate(
            zip(definitions, bodies, strict=True)
        ):
            final = body is ast
            if (
                type(body) is not SQLSelect
                or body.request is not request
                or body.definition is not definition
                or (not final and body.ctes != ())
            ):
                return False
            matches = tuple(u for u in request.layout.uses if u.consumer is definition)
            if len(matches) != 1:
                return False
            binding = matches[0]
            use = binding.original
            scan = body.scan
            if use.producer in sources:
                if (
                    type(scan) is not SQLScan
                    or scan.source is not sources[use.producer]
                    or not any(scan.realization is s for s in request.sources)
                    or scan.realization.owner is not scan.source.source.owner
                ):
                    return False
            elif type(scan) is not SQLNamedUse or scan.cte is not available.get(
                use.producer
            ):
                return False
            if (
                scan.use is not use
                or scan.binding is not binding
                or type(scan.symbol) is not SQLSymbol
                or type(scan.symbol.position) is not int
                or scan.symbol.position != 0
                or scan.symbol.binding is not use.ref
                or scan.symbol.name != f"s{use.ref.position}"
            ):
                return False
            symbols.append(scan.symbol)
            nodes.extend((body, scan))
            blocks = tuple(
                b for b in plan.blocks if b.definition is definition.original.ref
            )
            if len(blocks) != 1:
                return False
            projections = tuple(p for p in plan.projections if p.block is blocks[0].ref)
            exports = definition.original.exports
            if (
                type(body.columns) is not tuple
                or len(body.columns) != len(exports)
                or len(projections) != len(exports)
            ):
                return False
            for position, (column, projection, export) in enumerate(
                zip(body.columns, projections, exports, strict=True)
            ):
                if (
                    type(column) is not SQLColumn
                    or type(column.ordinal) is not int
                    or column.ordinal != position
                    or column.scan is not scan
                    or column.projection is not projection
                    or column.export is not export
                    or column.label
                    != (export.identity.name if final else f"c{position}")
                ):
                    return False
                pairs = tuple(
                    (i, b)
                    for i, b in enumerate(binding.bindings)
                    if b.input_port.ref is projection.input_port
                )
                if len(pairs) != 1:
                    return False
                input_position, link = pairs[0]
                if (
                    column.producer is not link
                    or column.input_port is not link.input_port
                    or projection.source_port is not link.canonical.ref
                    or projection.export is not export.ref
                    or projection.input_use is not use.ref
                ):
                    return False
                if type(scan) is SQLScan:
                    physical = link.canonical
                    fields = tuple(
                        f for f in scan.realization.fields if f.field is physical.field
                    )
                    if len(fields) != 1 or not any(
                        physical is p for p in plan.source_ports
                    ):
                        return False
                    field, origin = fields[0], scan
                    name = field.column
                else:
                    if type(scan) is not SQLNamedUse:
                        return False
                    physical, field, origin = provenance[link.canonical.ref]
                    name = scan.cte.columns[input_position].name
                    if (
                        scan.cte.columns[input_position].binding
                        is not link.terminal.ref
                    ):
                        return False
                if (
                    column.source_port is not physical
                    or column.source_field is not field
                    or column.origin is not origin
                ):
                    return False
                for port in (link.canonical, link.input_port, export):
                    logical, original_type = (
                        port.field.evidence.resolved_type,
                        field.field.evidence.resolved_type,
                    )
                    if (
                        logical.kind is not original_type.kind
                        or logical.name != original_type.name
                        or port.field.effective_nullability
                        is not field.field.effective_nullability
                    ):
                        return False
                expressions = tuple(
                    e for e in plan.expressions if e.ref is projection.expression
                )
                if (
                    len(expressions) != 1
                    or type(expressions[0]) is not row.ProjectSQLReference
                ):
                    return False
                symbol = column.symbol
                if (
                    type(symbol) is not SQLSymbol
                    or type(symbol.position) is not int
                    or symbol.position != position + 1
                    or symbol.binding is not link.input_port.ref
                    or symbol.name != name
                    or not identifier_valid(name, request.family)
                    or not identifier_valid(column.label, request.family, label=final)
                ):
                    return False
                symbols.append(symbol)
                nodes.append(column)
                provenance[export.ref] = (physical, field, origin)
            if not final:
                cte = ast.ctes[index]
                if (
                    type(cte) is not SQLCTE
                    or cte.definition is not definition
                    or type(cte.symbol) is not SQLSymbol
                    or type(cte.symbol.position) is not int
                    or cte.symbol.position != index
                    or cte.symbol.binding is not definition.original.ref
                    or cte.symbol.name != f"p{index}"
                    or type(cte.columns) is not tuple
                    or len(cte.columns) != len(exports)
                ):
                    return False
                for i, (symbol, terminal) in enumerate(
                    zip(cte.columns, definition.terminals, strict=True)
                ):
                    if (
                        type(symbol) is not SQLSymbol
                        or type(symbol.position) is not int
                        or symbol.position != i
                        or symbol.binding is not terminal.ref
                        or symbol.name != f"c{i}"
                    ):
                        return False
                symbols.extend((cte.symbol, *cte.columns))
                nodes.append(cte)
                available[definition.original.ref] = cte
        if (
            len({id(s) for s in symbols}) != len(symbols)
            or len(nodes) + len(symbols) > resource_limits(request)["nodes"]
        ):
            return False
        if (
            plan.bind_uses
            or plan.literal_slots
            or plan.fixed_envelope.slots
            or plan.fixed_envelope.values
            or request.verification.envelope is not plan.fixed_envelope
            or request.verification.literal_policy is not plan.literal_policy
        ):
            return False
        return True
    except (AttributeError, TypeError, ValueError, IndexError, KeyError):
        return False


def verify_sql_bytes(ast, rendered):
    try:
        if (
            type(rendered) is not RenderedSQL
            or rendered.ast is not ast
            or type(rendered.sql) is not bytes
            or type(rendered.events) is not tuple
        ):
            return False
        data = rendered.sql
        data.decode("utf-8")
        if len(data) > resource_limits(ast.request)["sql_bytes"]:
            return False
        events = iter(rendered.events)
        offset = 0
        subjects = ast.request.source_map.source_map.indexes.subjects
        quote = '"' if ast.request.family == "postgres" else "`"

        def take(kind, role, subject, expected, *, identifier=False):
            nonlocal offset
            event = next(events)
            if (
                type(event) is not RenderingEvent
                or event.kind != kind
                or event.role != role
                or event.subject is not subject
                or type(event.start) is not int
                or type(event.end) is not int
                or event.start != offset
                or not event.start < event.end <= len(data)
            ):
                raise ValueError("token range or ownership")
            if not _same(event.origins, getattr(subjects.get(subject), "origins", ())):
                raise ValueError("source map correspondence")
            token = data[event.start : event.end].decode("utf-8")
            if identifier:
                if not token.startswith(quote) or not token.endswith(quote):
                    raise ValueError("quoting")
                inner = token[1:-1]
                i, decoded = 0, []
                while i < len(inner):
                    char = inner[i]
                    if char == quote:
                        if i + 1 >= len(inner) or inner[i + 1] != quote:
                            raise ValueError("undoubled identifier quote")
                        i += 1
                    decoded.append(char)
                    i += 1
                if "".join(decoded) != expected:
                    raise ValueError("identifier binding")
            elif token != expected:
                raise ValueError("SQL token")
            offset = event.end

        plan = ast.request.plan

        def select(body, owner):
            scan = body.scan
            take("syntax", "select", owner, "SELECT ")
            for position, column in enumerate(body.columns):
                if position:
                    take("syntax", "separator", column.projection.ref, ", ")
                take(
                    "identifier",
                    "column_scope",
                    column.input_port.ref,
                    scan.symbol.name,
                    identifier=True,
                )
                take("syntax", "qualifier", column.projection.ref, ".")
                port = (
                    column.source_port
                    if type(scan) is SQLScan
                    else column.producer.terminal
                )
                take(
                    "identifier",
                    "column",
                    port.ref,
                    column.symbol.name,
                    identifier=True,
                )
                take("syntax", "alias", column.projection.ref, " AS ")
                take(
                    "identifier",
                    "label",
                    column.export.ref,
                    column.label,
                    identifier=True,
                )
            if type(scan) is SQLScan:
                ref = scan.source.ref
                take("syntax", "from", ref, " FROM ")
                take(
                    "identifier",
                    "namespace",
                    ref,
                    scan.realization.namespace,
                    identifier=True,
                )
                take("syntax", "qualifier", ref, ".")
                take(
                    "identifier",
                    "relation",
                    ref,
                    scan.realization.name,
                    identifier=True,
                )
            else:
                if type(scan) is not SQLNamedUse:
                    raise ValueError("unknown SQL relation")
                ref = scan.cte.definition.original.ref
                take("syntax", "from", ref, " FROM ")
                take(
                    "identifier",
                    "cte_reference",
                    ref,
                    scan.cte.symbol.name,
                    identifier=True,
                )
            take("syntax", "alias", scan.use.ref, " AS ")
            take(
                "identifier",
                "relation_scope",
                scan.use.ref,
                scan.symbol.name,
                identifier=True,
            )

        if ast.ctes:
            take("syntax", "with", plan.scope, "WITH ")
            for i, cte in enumerate(ast.ctes):
                ref = cte.definition.original.ref
                if i:
                    take("syntax", "cte_separator", ref, ", ")
                take("identifier", "cte_name", ref, cte.symbol.name, identifier=True)
                take("syntax", "cte_columns_open", ref, " (")
                for j, symbol in enumerate(cte.columns):
                    if j:
                        take("syntax", "terminal_separator", symbol.binding, ", ")
                    take(
                        "identifier",
                        "terminal_column",
                        symbol.binding,
                        symbol.name,
                        identifier=True,
                    )
                take("syntax", "cte_body_open", ref, ") AS (")
                select(cte.body, ref)
                take("syntax", "cte_body_close", ref, ")")
            take("syntax", "with_body", ast.definition.original.ref, " ")
        select(ast, plan.scope)
        return next(events, None) is None and offset == len(data)
    except (
        AttributeError,
        TypeError,
        ValueError,
        IndexError,
        KeyError,
        StopIteration,
        UnicodeError,
    ):
        return False


def verify_requirements(request, ast, original, generated):
    plan = request.plan
    entries = request.report.report.entries
    if (
        type(original) is not tuple
        or len(original) != len(plan.demands)
        or len(entries) != len(plan.demands)
    ):
        return False
    for item, entry, demand in zip(original, entries, plan.demands, strict=True):
        rule = (
            "R03"
            if ast.ctes and entry.family.value == "scope"
            else "R01"
            if entry.family.value in {"source_realization", "expression", "scope"}
            else "R02"
        )
        if (
            type(item) is not OriginalRequirement
            or item.entry is not entry
            or entry.demand is not demand
            or item.rule != rule
        ):
            return False
    if type(generated) is not tuple:
        return False
    # The denominator comes from every actual definition/header/reference/body,
    # not from the supplied requirement list or a construction success tag.
    expected = []
    naming = tuple(
        p
        for p in request.premises
        if p.key == "identifier_case" and p.scope == "statement"
    )
    for cte in ast.ctes:
        expected.append(("cte_definition", cte.definition.original.ref, "R03", naming))
        for column in cte.columns:
            expected.append(("terminal_column", column.binding, "R03", naming))
    for body in (*[cte.body for cte in ast.ctes], ast):
        scan = body.scan
        if type(scan) is SQLScan:
            expected.append(
                (
                    "qualified_scan",
                    scan,
                    "R01",
                    applicable_premises(request, scan.realization.owner),
                )
            )
            for field in scan.realization.fields:
                expected.append(
                    (
                        "source_representation",
                        field,
                        "R02",
                        applicable_premises(request, scan.realization.owner, field),
                    )
                )
        else:
            expected.append(("named_use", scan.use.ref, "R03", naming))
            for symbol in scan.cte.columns:
                expected.append(("immediate_terminal", symbol.binding, "R03", naming))
        for column in body.columns:
            expected.append(
                (
                    "field_projection",
                    column,
                    "R02",
                    applicable_premises(
                        request, column.origin.realization.owner, column.source_field
                    ),
                )
            )
        expected.append(("read_only_select_bytes", body, "R23", ()))
    if ast.ctes:
        expected.append(("nonrecursive_with_bytes", ast, "R23", ()))
    if len(expected) != len(generated):
        return False
    for requirement, (kind, subject, rule, premises) in zip(
        generated, expected, strict=True
    ):
        if (
            type(requirement) is not GeneratedRequirement
            or requirement.subject is not subject
            or (requirement.kind, requirement.rule) != (kind, rule)
            or not _same(requirement.premises, premises)
        ):
            return False
    return True


@dataclass(frozen=True, slots=True)
class EmissionVerification:
    issues: tuple[str, ...]

    @property
    def verified(self):
        return not self.issues


def verify_project_sql_emission(artifact, request):
    from pietto._project.project_sql_emission import EmissionArtifact

    issues = []
    try:
        if (
            type(artifact) is not EmissionArtifact
            or artifact.request is not request
            or not verify_sql_ast(request, artifact.ast)
        ):
            issues.append("plan_ast_correspondence")
        if not verify_sql_bytes(artifact.ast, artifact.rendered):
            issues.append("sql_bytes_or_ranges")
        if not verify_requirements(
            request,
            artifact.ast,
            artifact.original_requirements,
            artifact.generated_requirements,
        ):
            issues.append("requirement_denominators")
        if artifact.fixed_values != () or artifact.parameter_uses != ():
            issues.append("unexpected_parameters")
        # Accepted bytes are retained, not reopened; semantic target changes
        # invalidate this product even when a query's spelling is unchanged.
        document = json.loads(request.normalized_bytes)
        if document["target"] != {"family": request.family, "release": request.release}:
            issues.append("target_input_binding")
    except (AttributeError, TypeError, ValueError, IndexError, KeyError):
        issues.append("artifact_structure")
    return EmissionVerification(tuple(issues))
