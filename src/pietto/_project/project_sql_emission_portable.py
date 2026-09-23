"""Private emission observation: runtime export and independent correspondence.

`export_emission_observation` turns one verified runtime artifact and its exact
prepared request into canonical `pietto.sql-emission-observation.v1` bytes.
It only reads that artifact and invokes the existing read-only verifier: it
never prepares, emits, renders, reopens a file or reaches a database.

`verify_emission_observation` independently binds a document back to those
runtime roots. It walks the decoded document (never the exporter), binds every
record to exactly one runtime object and back, recomputes each derived field
through the retained plan, source map and assessment rather than the export
path, and compares the result with the existing public artifact projection
and the Slice12 inspection view.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from enum import Enum, StrEnum
import json
from typing import Any

from pietto._project import project_sql_emission_portable_schema as schema
from pietto._project import project_sql_emission_pure_boundary as pure
from pietto._project import project_sql_emission_aggregation as grouping
from pietto._project import project_sql_emission_ast as sql_ast
from pietto._project import project_sql_emission_joins as joining
from pietto._project import project_sql_emission_parameters as parameters
from pietto._project import project_sql_emission_results as resulting
from pietto._project import project_sql_emission_rows as rows
from pietto._project import project_sql_emission_scopes as scopes
from pietto._project import project_sql_emission_sets as setting
from pietto._project import project_sql_emission_windows as windowing
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.project_sql_emission import (
    EmissionArtifact,
    EmissionOutcome,
    serialize_project_sql_emission,
)
from pietto._project.project_sql_emission_contract import (
    BoundField,
    BoundSource,
    Premise,
    PreparedEmission,
)
from pietto._project.project_sql_emission_inspection import (
    inspect_project_sql_emission,
)
from pietto._project.project_sql_emission_rendering import (
    RenderedSQL,
    RenderingEvent,
)
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
)
from pietto._project.project_sql_plan import ProjectSQLPlanRef, ProjectSQLPlanScope
from pietto._project.project_sql_plan_literals import ProjectSQLFixedLiteralValue
from pietto._project.project_sql_plan_source_maps import (
    ProjectSQLSourceAssociation,
    ProjectSQLSourceMapEntry,
)

__all__: tuple[str, ...] = ()

KINDS: dict[type, str] = {
    EmissionArtifact: "artifact",
    PreparedEmission: "request",
    ProjectDeclarationOccurrence: "owner",
    BoundSource: "bound_source",
    BoundField: "bound_field",
    Premise: "premise",
    scopes.ScopeDefinition: "scope_definition",
    scopes.ScopeUse: "scope_use",
    scopes.TerminalBinding: "terminal_binding",
    sql_ast.SQLSymbol: "sql_symbol",
    sql_ast.SQLSelect: "sql_select",
    sql_ast.SQLCTE: "sql_cte",
    sql_ast.SQLScan: "sql_scan",
    sql_ast.SQLNamedUse: "sql_named_use",
    sql_ast.SQLColumn: "sql_column",
    sql_ast.SQLLiteralColumn: "sql_literal_column",
    parameters.LiteralOrigin: "literal_origin",
    parameters.SQLUnary: "sql_unary",
    parameters.SQLAnchor: "sql_anchor",
    parameters.SQLLiteral: "sql_literal",
    parameters.SQLParameter: "sql_parameter",
    parameters.NativeUse: "native_use",
    ProjectSQLFixedLiteralValue: "fixed_value",
    sql_ast.SQLRowQuery: "sql_row_query",
    sql_ast.SQLJoinQuery: "sql_join_query",
    sql_ast.RowBody: "row_body",
    sql_ast.RowScan: "row_scan",
    sql_ast.RowNamedUse: "row_named_use",
    sql_ast.RowStageUse: "row_stage_use",
    sql_ast.RowJoinUse: "row_join_use",
    sql_ast.RowCarryColumn: "row_carry_column",
    sql_ast.RowValueColumn: "row_value_column",
    sql_ast.RowPredicate: "row_predicate",
    rows.Realization: "realization",
    rows.StageColumn: "stage_column",
    rows.SQLStageReference: "sql_stage_reference",
    rows.SQLOperation: "sql_operation",
    joining.JoinBody: "join_body",
    joining.JoinInput: "join_input",
    joining.JoinEquality: "join_equality",
    joining.JoinColumn: "join_column",
    grouping.AggregateStage: "aggregate_stage",
    grouping.AggregateKeyColumn: "aggregate_key_column",
    grouping.AggregateValueColumn: "aggregate_value_column",
    grouping.AggregateProjectionColumn: "aggregate_projection_column",
    grouping.AggregateOrigin: "aggregate_origin",
    windowing.WindowStage: "window_stage",
    windowing.WindowDefinition: "window_definition",
    windowing.WindowSpecification: "window_specification",
    windowing.WindowOrderItem: "window_order_item",
    windowing.WindowFrameSpec: "window_frame",
    windowing.WindowArgument: "window_argument",
    windowing.WindowColumn: "window_column",
    windowing.WindowProjectionColumn: "window_projection_column",
    windowing.WindowOrigin: "window_origin",
    resulting.RowResultBody: "row_result_body",
    resulting.RowResultUse: "row_result_use",
    resulting.ResultColumn: "result_column",
    resulting.ResultStage: "result_stage",
    resulting.ResultDistinct: "result_distinct",
    resulting.ResultOrder: "result_order",
    resulting.ResultOrderItem: "result_order_item",
    resulting.ResultLimit: "result_limit",
    setting.SetBody: "set_body",
    setting.SetOperandBody: "set_operand_body",
    setting.SetColumn: "set_column",
    RenderedSQL: "rendered",
    RenderingEvent: "event",
    ProjectSQLSourceMapEntry: "origin",
    ProjectSQLSourceAssociation: "association",
    sql_ast.OriginalRequirement: "original_requirement",
    sql_ast.GeneratedRequirement: "generated_requirement",
}
# A window partition is retained as a (binding, read) pair object.
PAIR_KIND = "window_partition"


class ObservationStatus(StrEnum):
    OK = "ok"
    INVALID_ROOT = "invalid_root"
    UNVERIFIED = "unverified"
    OUTSIDE_SCHEMA = "outside_schema"
    RESOURCE_LIMIT = "resource_limit"


@dataclass(frozen=True, slots=True)
class EmissionObservation:
    status: ObservationStatus
    canonical_bytes: bytes | None = None


@dataclass(frozen=True, slots=True)
class ObservationCorrespondence:
    issues: tuple[str, ...]

    @property
    def corresponds(self) -> bool:
        return not self.issues


class _Outside(Exception):
    """The runtime graph holds a shape the closed schema does not describe."""


class _Limit(Exception):
    """A private codec limit was reached."""


class _Mismatch(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason


@dataclass(frozen=True, slots=True)
class _Node:
    value: Any
    kinds: tuple[str, ...]


def _kind_of(value: Any, kinds: tuple[str, ...]) -> str:
    if type(value) is tuple and PAIR_KIND in kinds and len(value) == 2:
        return PAIR_KIND
    kind = KINDS.get(type(value))
    if kind is None or kind not in kinds:
        raise _Outside
    return kind


def _plan(value: Any) -> dict[str, Any]:
    if type(value) is ProjectSQLPlanScope:
        return {"kind": schema.SCOPE_KIND, "position": 0}
    ref = value if type(value) is ProjectSQLPlanRef else getattr(value, "ref", None)
    if type(ref) is not ProjectSQLPlanRef:
        raise _Outside
    return {"kind": ref.kind.value, "position": ref.position}


def _text(value: Any, limit: int = schema.MAX_TEXT_BYTES) -> str:
    if isinstance(value, Enum):
        value = value.value
    if type(value) is bytes:
        value = value.decode("utf-8")
    if type(value) is not str:
        raise _Outside
    if len(value.encode("utf-8")) > limit:
        raise _Limit
    return value


def _data(value: Any) -> Any:
    """Plain sorted-key JSON of retained data; enums become their values."""

    def plain(item):
        if isinstance(item, Enum):
            return item.value
        if type(item) in (list, tuple):
            return [plain(child) for child in item]
        if type(item) is dict:
            return {str(k): plain(item[k]) for k in sorted(item)}
        if item is None or type(item) in (bool, str):
            return item
        if type(item) is int and 0 <= item <= schema.MAX_NAT:
            return item
        raise _Outside

    return plain(value)


def _encode(spec: str, value: Any) -> Any:
    if spec.startswith("?"):
        return None if value is None else _encode(spec[1:], value)
    if spec.startswith("*"):
        if type(value) is not tuple:
            raise _Outside
        return [_encode(spec[1:], item) for item in value]
    if spec.startswith("@"):
        return _Node(value, tuple(spec[1:].split("|")))
    if spec == "nat":
        if type(value) is not int or not 0 <= value <= schema.MAX_NAT:
            raise _Outside
        return value
    if spec == "text":
        return _text(value)
    if spec == "sql":
        return _text(value, schema.MAX_SQL_BYTES)
    if spec == "bool":
        if type(value) is not bool:
            raise _Outside
        return value
    if spec == "none":
        if value is not None:
            raise _Outside
        return None
    if spec == "nullable":
        if type(value) is not bool and value != "unknown":
            raise _Outside
        return value
    if spec in ("data", "fixed"):
        return _data(value)
    if spec == "plan":
        return _plan(value)
    if spec == "subject":
        if type(value) in (ProjectSQLPlanRef, ProjectSQLPlanScope):
            return _plan(value)
        return _Node(value, tuple(schema.RECORDS))
    if spec == "scope":
        if value == "statement":
            return "statement"
        if type(value) is tuple and len(value) == 2:
            return [_Node(value[0], ("owner",)), _plan(value[1])]
        return _Node(value, ("owner",))
    raise _Outside


# -- derived upstream evidence (export path) --------------------------------


def _nominal(identity):
    return {
        "module_path": identity.module_path,
        "namespace": identity.namespace,
        "declaration_kind": identity.declaration_kind,
        "declared_name": identity.declared_name,
    }


def _occurrence(occurrence):
    if occurrence is None:
        return None
    return {
        "identity": _nominal(occurrence.identity),
        "module_position": occurrence.module_position,
        "declaration_position": occurrence.declaration_position,
    }


def _import(occurrence):
    if occurrence is None:
        return None
    binding = occurrence.binding_identity
    return {
        "binding_identity": {
            "owning_module_path": binding.owning_module_path,
            "namespace": binding.namespace,
            "declaration_kind": binding.declaration_kind,
            "local_binding_name": binding.local_binding_name,
        },
        "target_module_path": occurrence.target_module_path,
        "exported_name": occurrence.exported_name,
        "module_statement_position": occurrence.module_statement_position,
        "item_position": occurrence.item_position,
    }


def _hop(hop):
    if hop is None:
        return None
    facade = hop.facade_occurrence
    return {
        "import_occurrence": _import(hop.import_occurrence),
        "facade_occurrence": {
            "owning_module_path": facade.owning_module_path,
            "namespace": facade.namespace,
            "declaration_kind": facade.declaration_kind,
            "exposed_name": facade.exposed_name,
            "module_statement_position": facade.module_statement_position,
            "item_position": facade.item_position,
        },
        "facade_origin": hop.facade_origin,
        "target_identity": _nominal(hop.target_identity),
    }


def _path(path):
    if path is None:
        return None
    return {
        "owning_module_path": path.owning_module_path,
        "namespace": path.namespace,
        "declaration_kind": path.declaration_kind,
        "local_name": path.local_name,
        "target_occurrence": _occurrence(path.target_occurrence),
        "local_occurrence": _occurrence(path.local_occurrence),
        "import_occurrence": _import(path.import_occurrence),
        "hops": [_hop(hop) for hop in path.hops],
    }


def _location(location):
    return {
        "path": location.path,
        "line": location.line,
        "column": location.column,
        "end_line": location.end_line,
        "end_column": location.end_column,
        "availability": location.availability,
    }


def _operator(original, kind):
    if kind == "null_test":
        return "is not null" if original.expression.negated else "is null"
    return original.expression.operator


def _tag(original):
    return original.value_type.resolved_type.name


def _decimal(decimal):
    if decimal is None:
        return None
    return {"precision": decimal.precision, "scale": decimal.scale}


def _target(request):
    target = request.target_request.target
    return {
        "target": None
        if target is None
        else {"kind": target.kind, "family": target.family, "release": target.release},
        "issues": [issue for issue in request.target_request.issues],
    }


class _Export:
    def __init__(self, artifact: EmissionArtifact, request: PreparedEmission):
        self.artifact = artifact
        self.request = request
        self.semantic = request.verification.completed.semantic_result
        self.requirement_index = {
            id(item): i for i, item in enumerate(artifact.original_requirements)
        }

    def binding(self, binding, role):
        attribute = "partitions" if role == "partition" else "orders"
        for policy in self.request.plan.window_policies:
            for position, item in enumerate(getattr(policy, attribute)):
                if item is binding:
                    return {"policy": _plan(policy), "role": role, "position": position}
        raise _Outside

    def derived(self, kind: str, name: str, obj: Any) -> Any:
        request = self.request
        if kind == "artifact":
            return [asdict(d) for d in request.verification.completed.diagnostics]
        if kind == "request":
            if name == "owner":
                return request.verification.selected_owner
            if name == "literal_policy":
                return request.verification.literal_policy
            if name == "modules":
                return [
                    {
                        "module": item.identity.path,
                        "sha256": item.sha256,
                        "byte_count": item.byte_count,
                    }
                    for item in self.semantic.trusted_source_snapshots
                ]
            if name == "target_request":
                return _target(request)
            if name == "definitions":
                return request.layout.definitions
            if name == "uses":
                return request.layout.uses
            return [{"code": b.code, "detail": b.detail} for b in obj.input_blockers]
        if kind == "owner":
            if name == "module":
                return self.semantic.modules[obj.module_position].path
            if name == "kind":
                return obj.identity.declaration_kind
            return obj.definition.name
        if kind == "bound_field":
            if name == "logical":
                logical = obj.field.evidence.resolved_type
                return {"kind": logical.kind, "name": logical.name}
            if name == "nullability":
                return obj.field.effective_nullability
            return _decimal(obj.decimal)
        if kind in ("sql_unary", "sql_operation"):
            return _operator(obj.original, getattr(obj, "kind", "sign"))
        if kind == "sql_anchor":
            return _tag(obj.original)
        if kind == "sql_literal":
            return schema.fixed_wire(_tag(obj.original), obj.value)
        if kind == "fixed_value":
            if name == "site":
                return obj.slot.site
            return schema.fixed_wire(obj.tag.value, obj.value)
        if kind == "row_body":
            return obj.block.kind
        if kind == "join_body":
            return obj.join.kind if name == "join_kind" else obj.join.on
        if kind == "join_column":
            return [join.position for join in obj.port.nulling]
        if kind == "window_definition":
            for policy in request.plan.window_policies:
                if policy.named_use is obj.named_use:
                    return policy
            raise _Outside
        if kind == "window_partition":
            return self.binding(obj[0], "partition") if name == "binding" else obj[1]
        if kind == "window_order_item":
            return self.binding(obj.binding, "order")
        if kind == "set_body":
            return getattr(obj.body, name)
        if kind == "origin":
            if name == "role":
                return obj.original.role
            return request.source_map.source_map.indexes.associations[obj.ref]
        if kind == "association":
            if name == "source":
                return obj.site.source.display_path
            if name == "site":
                return obj.site.position
            if name == "location":
                return _location(obj.site.location)
            return _path(obj.path) if name == "path" else _hop(obj.hop)
        assert kind == "original_requirement"
        entry = obj.entry
        if name == "evidence":
            demand = request.assessment.assessment.demands[
                self.requirement_index[id(obj)]
            ]
            return [[state.value for state in a.outcomes] for a in demand.aspects]
        return getattr(entry, name)

    def fields(self, kind: str, obj: Any) -> dict[str, Any]:
        derived = schema.DERIVED.get(kind, frozenset())
        return {
            name: _encode(
                spec,
                self.derived(kind, name, obj)
                if name in derived
                else getattr(obj, name),
            )
            for name, spec in schema.RECORDS[kind]
        }

    def run(self) -> bytes:
        records: list[dict[str, Any]] = []
        index: dict[int, tuple[str, int]] = {}
        counters: dict[str, int] = {}
        edges = 0
        stack: list[_Node] = [_Node(self.artifact, ("artifact",))]
        while stack:
            node = stack.pop()
            if id(node.value) in index:
                if index[id(node.value)][0] not in node.kinds:
                    raise _Outside
                continue
            kind = _kind_of(node.value, node.kinds)
            position = counters.get(kind, 0)
            counters[kind] = position + 1
            index[id(node.value)] = (kind, position)
            if len(records) >= schema.MAX_RECORDS:
                raise _Limit
            fields = self.fields(kind, node.value)
            records.append({"ref": [kind, position], "fields": fields})
            children = list(_children(fields))
            edges += len(children)
            if edges > schema.MAX_EDGES:
                raise _Limit
            stack.extend(reversed(children))

        def wire(value):
            if type(value) is _Node:
                return list(index[id(value.value)])
            if type(value) is list:
                return [wire(item) for item in value]
            if type(value) is dict:
                return {key: wire(item) for key, item in value.items()}
            return value

        document = {
            "format": schema.FORMAT,
            "root": list(schema.ROOT),
            "records": [
                {"ref": row["ref"], "fields": wire(row["fields"])} for row in records
            ],
        }
        data = schema.canonical_bytes(document)
        if len(data) > schema.MAX_DOCUMENT_BYTES:
            raise _Limit
        return data


def _children(value: Any):
    if type(value) is _Node:
        yield value
    elif type(value) is list:
        for item in value:
            yield from _children(item)
    elif type(value) is dict:
        for item in value.values():
            yield from _children(item)


def _roots_valid(artifact, request) -> bool:
    return (
        type(artifact) is EmissionArtifact
        and type(request) is PreparedEmission
        and artifact.request is request
    )


def export_emission_observation(artifact, request) -> EmissionObservation:
    """Canonical private observation of one verified artifact, or a typed refusal."""

    if not _roots_valid(artifact, request):
        return EmissionObservation(ObservationStatus.INVALID_ROOT)
    if not verify_project_sql_emission(artifact, request).verified:
        return EmissionObservation(ObservationStatus.UNVERIFIED)
    try:
        return EmissionObservation(
            ObservationStatus.OK, _Export(artifact, request).run()
        )
    except _Limit:
        return EmissionObservation(ObservationStatus.RESOURCE_LIMIT)
    except (_Outside, AttributeError, KeyError, TypeError, ValueError, IndexError):
        return EmissionObservation(ObservationStatus.OUTSIDE_SCHEMA)


# -- independent runtime correspondence ---------------------------------------


def _plain(value: Any) -> Any:
    """A decoded view value as plain JSON data (refs and tags stay typed)."""
    if isinstance(value, pure.Ref):
        return [value.kind, value.index]
    if isinstance(value, pure.PlanRef):
        return {"kind": value.kind, "position": value.position}
    if isinstance(value, pure.Fixed):
        return {"tag": value.tag, "value": value.wire}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    return value


def _need(condition: object, reason: str) -> None:
    if not condition:
        raise _Mismatch(reason)


class _Binder:
    """Bind every document record to exactly one runtime object, and back."""

    def __init__(self, view: pure.View, artifact, request) -> None:
        self.view = view
        self.artifact = artifact
        self.request = request
        plan = request.plan
        self.plan = plan
        self.semantic = plan.scope.completed.semantic_result
        self.bound: dict[pure.Ref, Any] = {}
        self.claimed: dict[int, pure.Ref] = {}
        self.policies = {
            (policy.ref.kind.value, policy.ref.position): policy
            for policy in plan.window_policies
        }
        self.associations: dict[int, list[Any]] = {}
        for association in request.source_map.source_map.associations:
            self.associations.setdefault(id(association.entry), []).append(association)
        self.expressions = {e.ref: e for e in plan.expressions}
        self.blocks = {block.ref: block for block in plan.blocks}
        self.joins = {join.ref: join for join in plan.joins}
        self.ports = {port.ref: port for port in plan.join_ports}
        self.sets = {body.ref: body for body in plan.set_bodies}
        self.source_map = request.source_map.source_map
        self.entries = request.report.report.entries

    def bind(self, ref: pure.Ref, obj: Any, pending: list[pure.Ref]) -> None:
        if ref in self.bound:
            _need(self.bound[ref] is obj, "record_binding")
            return
        _need(self.claimed.get(id(obj), ref) == ref, "record_sharing")
        try:
            _need(_kind_of(obj, (ref.kind,)) == ref.kind, "record_kind")
        except _Outside:
            raise _Mismatch("record_kind") from None
        self.bound[ref] = obj
        self.claimed[id(obj)] = ref
        pending.append(ref)

    def run(self) -> None:
        pending: list[pure.Ref] = []
        self.bind(pure.Ref(*schema.ROOT), self.artifact, pending)
        while pending:
            ref = pending.pop()
            obj = self.bound[ref]
            fields = self.view.record(ref).fields
            derived = schema.DERIVED.get(ref.kind, frozenset())
            for name, spec in schema.RECORDS[ref.kind]:
                if name in derived:
                    value = self.derived(ref.kind, name, obj, fields[name])
                else:
                    value = getattr(obj, name)
                self.compare(spec, fields[name], value, pending)
        _need(len(self.bound) == len(self.view.records), "record_binding")

    def expression(self, original: Any) -> Any:
        found = self.expressions.get(original.ref)
        _need(found is original, "plan_expression")
        return found

    def derived(self, kind: str, name: str, obj: Any, documented: Any) -> Any:
        scope = self.plan.scope
        if kind == "artifact":
            return [asdict(d) for d in scope.completed.diagnostics]
        if kind == "request":
            if name == "owner":
                return scope.selected_owner
            if name == "literal_policy":
                return self.source_map.literal_policy
            if name == "modules":
                return [
                    {
                        "module": item.identity.path,
                        "sha256": item.sha256,
                        "byte_count": item.byte_count,
                    }
                    for item in self.semantic.trusted_source_snapshots
                ]
            if name == "target_request":
                target_request = self.request.assessment.assessment.request
                _need(target_request is obj.target_request, "target_request")
                return _target(obj)
            if name in ("definitions", "uses"):
                return getattr(obj.layout, name)
            return [{"code": b.code, "detail": b.detail} for b in obj.input_blockers]
        if kind == "owner":
            identity = obj.identity
            return {
                "module": identity.module_path,
                "kind": identity.declaration_kind,
                "name": identity.declared_name,
            }[name]
        if kind == "bound_field":
            if name == "logical":
                logical = obj.field.evidence.resolved_type
                return {"kind": logical.kind, "name": logical.name}
            if name == "nullability":
                return obj.field.effective_nullability
            return _decimal(obj.decimal)
        if kind in ("sql_unary", "sql_operation"):
            expression = self.expression(obj.original)
            if getattr(obj, "kind", None) == "null_test":
                negated = expression.expression.negated
                return "is not null" if negated else "is null"
            return expression.expression.operator
        if kind == "sql_anchor":
            return _tag(self.expression(obj.original))
        if kind == "sql_literal":
            expression = self.expression(obj.original)
            return schema.fixed_wire(_tag(expression), expression.expression.value)
        if kind == "fixed_value":
            if name == "site":
                return obj.slot.site
            return schema.fixed_wire(obj.tag.value, obj.value)
        if kind == "row_body":
            _need(self.blocks.get(obj.block.ref) is obj.block, "plan_block")
            return obj.block.kind
        if kind == "join_body":
            _need(self.joins.get(obj.join.ref) is obj.join, "plan_join")
            return obj.join.kind if name == "join_kind" else obj.join.on
        if kind == "join_column":
            _need(self.ports.get(obj.port.ref) is obj.port, "plan_join_port")
            return [join.position for join in obj.port.nulling]
        if kind == "window_definition":
            binding = obj.symbol.binding
            policy = self.policies.get((binding.kind.value, binding.position))
            _need(
                policy is not None and policy.named_use is obj.named_use, "named_window"
            )
            return policy
        if kind in ("window_partition", "window_order_item"):
            if kind == "window_partition" and name == "read":
                return obj[1]
            binding = obj[0] if kind == "window_partition" else obj.binding
            key = (documented["policy"]["kind"], documented["policy"]["position"])
            policy = self.policies.get(key)
            attribute = "partitions" if documented["role"] == "partition" else "orders"
            _need(
                policy is not None
                and getattr(policy, attribute)[documented["position"]] is binding,
                "window_binding",
            )
            return _plain(documented)
        if kind == "set_body":
            body = self.sets.get(obj.body.ref)
            _need(body is obj.body, "plan_set_body")
            return getattr(body, name)
        if kind == "origin":
            _need(self.source_map.entries[obj.position] is obj, "source_map_entry")
            if name == "role":
                return obj.original.role
            return tuple(
                sorted(self.associations.get(id(obj), ()), key=lambda a: a.position)
            )
        if kind == "association":
            if name == "source":
                return obj.site.source.display_path
            if name == "site":
                return obj.site.position
            if name == "location":
                return _location(obj.site.location)
            return _path(obj.path) if name == "path" else _hop(obj.hop)
        assert kind == "original_requirement"
        entry = obj.entry
        _need(self.entries[entry.position] is entry, "demand_entry")
        if name == "evidence":
            demand = self.request.assessment.assessment.by_demand[entry.ref]
            return [[state.value for state in a.outcomes] for a in demand.aspects]
        return getattr(entry, name)

    def compare(self, spec: str, documented: Any, value: Any, pending) -> None:
        if spec.startswith("?"):
            if documented is None or value is None:
                _need(documented is None and value is None, "field_absence")
                return
            spec = spec[1:]
        if spec.startswith("*"):
            _need(type(value) in (tuple, list), "field_list")
            _need(len(documented) == len(value), "field_list")
            for item, runtime in zip(documented, value, strict=True):
                self.compare(spec[1:], item, runtime, pending)
            return
        if spec.startswith("@") or (spec == "subject" and type(documented) is pure.Ref):
            self.bind(documented, value, pending)
            return
        if spec in ("plan", "subject"):
            _need(_plain(documented) == _plan(value), "plan_reference")
            return
        if spec == "scope":
            if documented == "statement":
                _need(value == "statement", "premise_scope")
            elif type(documented) is tuple:
                _need(type(value) is tuple and len(value) == 2, "premise_scope")
                self.bind(documented[0], value[0], pending)
                _need(_plain(documented[1]) == _plan(value[1]), "premise_scope")
            else:
                self.bind(documented, value, pending)
            return
        if spec in ("data", "fixed"):
            _need(_plain(documented) == _data(value), "field_data")
            return
        if spec in ("text", "sql"):
            limit = schema.MAX_SQL_BYTES if spec == "sql" else schema.MAX_TEXT_BYTES
            _need(documented == _text(value, limit), "field_text")
            return
        _need(type(documented) is type(value) and documented == value, "field_value")


def _final_columns(view: pure.View) -> tuple[Any, ...]:
    artifact = view.record(pure.Ref(*schema.ROOT)).fields
    ast = view.record(artifact["ast"])
    if ast.ref.kind == "sql_select":
        return ast.fields["columns"]
    units = ast.fields["bodies" if ast.ref.kind == "sql_row_query" else "units"]
    return view.record(units[-1]).fields["columns"]


def _public(view: pure.View, artifact, request) -> None:
    """Compare against the independently written public artifact projection."""
    outcome = EmissionOutcome(
        "VERIFIED", request.verification.completed.diagnostics, artifact
    )
    public = json.loads(serialize_project_sql_emission(outcome))
    _need(public["status"] == "VERIFIED", "public_projection")
    record = view.record
    fields = record(pure.Ref(*schema.ROOT)).fields
    requested = record(fields["request"]).fields
    rendered = record(fields["rendered"]).fields
    contract = json.loads(requested["normalized_bytes"])
    owner = record(requested["owner"]).fields
    _need(public["sql"] == rendered["sql"], "public_sql")
    _need(
        public["target"]
        == {
            "family": requested["family"],
            "release": requested["release"],
            "environment": contract["environment"],
        },
        "public_target",
    )
    _need(
        public["request"]
        == {
            "owner": {
                "module": owner["module"],
                "kind": owner["kind"],
                "name": owner["name"],
            },
            "sources": _plain(requested["modules"]),
            "contract": contract,
            "literal_policy": requested["literal_policy"],
        },
        "public_request",
    )
    fixed = [record(ref).fields for ref in fields["fixed_values"]]
    _need(
        public["fixed_values"]
        == [
            {
                "slot": i,
                "reference": _plain(value["slot"]),
                "site": _plain(value["site"]),
                "tag": value["value"].tag,
                "value": value["value"].wire,
            }
            for i, value in enumerate(fixed)
        ],
        "public_fixed_values",
    )
    slots = {value["slot"]: i for i, value in enumerate(fixed)}
    tokens = [r for r in view.ranges if r.kind == "parameter"]
    uses = [record(ref).fields for ref in fields["parameter_uses"]]
    _need(len(tokens) == len(uses), "public_parameter_uses")
    _need(
        public["parameter_uses"]
        == [
            {
                "use": use["ordinal"],
                "slot": slots[use["slot"]],
                "server_index": use["server_index"],
                "physical_type": use["physical_type"],
                "range": {"start": token.start, "end": token.end},
            }
            for use, token in zip(uses, tokens, strict=True)
        ],
        "public_parameter_uses",
    )
    _need(
        [(c["ordinal"], c["label"]) for c in public["columns"]]
        == [
            (record(ref).fields["ordinal"], record(ref).fields["label"])
            for ref in _final_columns(view)
        ],
        "public_columns",
    )
    _need(
        [
            (r["start"], r["end"], r["kind"], r["role"], r["subject"])
            + ([o["position"] for o in r["origins"]],)
            for r in public["ranges"]
        ]
        == [
            (r.start, r.end, r.kind, r.role, _plain(r.subject))
            + ([record(o).fields["position"] for o in r.origins],)
            for r in view.ranges
        ],
        "public_ranges",
    )
    originals = [record(ref).fields for ref in fields["original_requirements"]]
    generated = [record(ref).fields for ref in fields["generated_requirements"]]
    expected = [
        ("original", i, item["family"], item["rule"], [], _plain(item["evidence"]))
        for i, item in enumerate(originals)
    ] + [
        (
            "generated",
            i,
            item["kind"],
            item["rule"],
            [record(p).fields["position"] for p in item["premises"]],
            None,
        )
        for i, item in enumerate(generated)
    ]
    _need(
        [
            (
                r["denominator"],
                r["ordinal"],
                r["kind"],
                r["rule"],
                r["premises"],
                r["evidence"] if r["denominator"] == "original" else None,
            )
            for r in public["requirements"]
        ]
        == expected,
        "public_requirements",
    )
    _need(
        [r["subject"] for r in public["requirements"][: len(originals)]]
        == [_plain(item["subject"]) for item in originals],
        "public_requirements",
    )
    _need(public["diagnostics"] == _plain(fields["diagnostics"]), "public_diagnostics")


def _inspection(view: pure.View, artifact, request) -> None:
    """Compare against the Slice12 artifact-bound runtime inspection view."""
    inspected = inspect_project_sql_emission(artifact, request)
    _need(inspected.sql == view.sql, "inspection_sql")
    _need(
        [(r.start, r.end, r.kind, r.role, _plan(r.subject)) for r in inspected.ranges]
        == [(r.start, r.end, r.kind, r.role, _plain(r.subject)) for r in view.ranges],
        "inspection_ranges",
    )
    _need(
        [column.label for column in inspected.columns]
        == [view.record(ref).fields["label"] for ref in _final_columns(view)],
        "inspection_columns",
    )
    tokens = [r for r in view.ranges if r.kind == "parameter"]
    _need(
        [
            (use.server_index, token.start, token.end)
            for use, token in inspected.parameter_uses
        ]
        == [
            (view.record(ref).fields["server_index"], t.start, t.end)
            for ref, t in zip(
                view.record(pure.Ref(*schema.ROOT)).fields["parameter_uses"],
                tokens,
                strict=True,
            )
        ],
        "inspection_parameter_uses",
    )


def verify_emission_observation(
    document, artifact, request
) -> ObservationCorrespondence:
    """Check canonical observation bytes against the exact runtime roots."""

    if not _roots_valid(artifact, request):
        return ObservationCorrespondence(("invalid_runtime_root",))
    if not verify_project_sql_emission(artifact, request).verified:
        return ObservationCorrespondence(("unverified_artifact",))
    outcome = pure.parse_emission_observation(document)
    if outcome.status is not pure.Status.OK or outcome.view is None:
        return ObservationCorrespondence(("document_" + outcome.status.value,))
    view = outcome.view
    issues = []
    for name, check in (
        ("record_binding", lambda: _Binder(view, artifact, request).run()),
        ("public_projection", lambda: _public(view, artifact, request)),
        ("inspection_projection", lambda: _inspection(view, artifact, request)),
    ):
        try:
            check()
        except _Mismatch as error:
            issues.append(error.reason)
        except (
            _Outside,
            _Limit,
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
            IndexError,
        ):
            issues.append(name)
    return ObservationCorrespondence(tuple(issues))
