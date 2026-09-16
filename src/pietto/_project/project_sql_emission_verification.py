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
from pietto._project.project_sql_emission_ast import (
    SQLSelect,
    SQLScan,
    SQLColumn,
    SQLSymbol,
    OriginalRequirement,
    GeneratedRequirement,
    direct_shape,
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
        if (
            not direct_shape(plan)
            or emission_blockers(request)
            or type(ast.scan) is not SQLScan
            or type(ast.scan.symbol) is not SQLSymbol
        ):
            return False
        scan = ast.scan
        if (
            scan.source is not plan.sources[0]
            or scan.use is not plan.input_uses[0]
            or scan.symbol.binding is not scan.use.ref
            or type(scan.symbol.position) is not int
            or scan.symbol.position != 0
            or scan.symbol.name != "s0"
        ):
            return False
        if (
            not any(scan.realization is source for source in request.sources)
            or scan.realization.owner is not scan.source.source.owner
        ):
            return False
        if len(ast.columns) != len(plan.exports) or type(ast.columns) is not tuple:
            return False
        for position, column in enumerate(ast.columns):
            projection, export = plan.projections[position], plan.exports[position]
            if (
                type(column) is not SQLColumn
                or type(column.ordinal) is not int
                or column.ordinal != position
                or column.scan is not scan
                or column.projection is not projection
                or column.export is not export
                or column.label != export.identity.name
            ):
                return False
            if (
                not any(column.source_field is f for f in scan.realization.fields)
                or not any(column.source_port is p for p in plan.source_ports)
                or not any(column.input_port is p for p in plan.input_ports)
            ):
                return False
            if (
                column.source_field.field is not column.source_port.field
                or projection.source_port is not column.source_port.ref
                or projection.input_port is not column.input_port.ref
                or projection.export is not export.ref
                or projection.input_use is not scan.use.ref
                or column.input_port.producer_port is not column.source_port.ref
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
                or symbol.binding is not column.input_port.ref
                or symbol.name != column.source_field.column
                or symbol is scan.symbol
            ):
                return False
            if not identifier_valid(
                symbol.name, request.family
            ) or not identifier_valid(column.label, request.family, label=True):
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
        take("syntax", "select", plan.scope, "SELECT ")
        for position, column in enumerate(ast.columns):
            if position:
                take("syntax", "separator", column.projection.ref, ", ")
            take(
                "identifier",
                "column_scope",
                column.input_port.ref,
                ast.scan.symbol.name,
                identifier=True,
            )
            take("syntax", "qualifier", column.projection.ref, ".")
            take(
                "identifier",
                "column",
                column.source_port.ref,
                column.source_field.column,
                identifier=True,
            )
            take("syntax", "alias", column.projection.ref, " AS ")
            take(
                "identifier", "label", column.export.ref, column.label, identifier=True
            )
        take("syntax", "from", ast.scan.source.ref, " FROM ")
        take(
            "identifier",
            "namespace",
            ast.scan.source.ref,
            ast.scan.realization.namespace,
            identifier=True,
        )
        take("syntax", "qualifier", ast.scan.source.ref, ".")
        take(
            "identifier",
            "relation",
            ast.scan.source.ref,
            ast.scan.realization.name,
            identifier=True,
        )
        take("syntax", "alias", ast.scan.use.ref, " AS ")
        take(
            "identifier",
            "relation_scope",
            ast.scan.use.ref,
            ast.scan.symbol.name,
            identifier=True,
        )
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
            "R01"
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
    if type(generated) is not tuple or len(generated) != 2 + len(
        ast.scan.realization.fields
    ) + len(ast.columns):
        return False
    subjects = (ast.scan, *ast.scan.realization.fields, *ast.columns, ast)
    for index, (requirement, subject) in enumerate(
        zip(generated, subjects, strict=True)
    ):
        if index == 0:
            kind, rule, premises = (
                "qualified_scan",
                "R01",
                applicable_premises(request, ast.scan.realization.owner),
            )
        elif index == len(subjects) - 1:
            kind, rule, premises = "read_only_select_bytes", "R23", ()
        elif index <= len(ast.scan.realization.fields):
            kind, rule, premises = (
                "source_representation",
                "R02",
                applicable_premises(request, ast.scan.realization.owner, subject),
            )
        else:
            kind, rule, premises = (
                "field_projection",
                "R02",
                applicable_premises(
                    request, ast.scan.realization.owner, subject.source_field
                ),
            )
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
