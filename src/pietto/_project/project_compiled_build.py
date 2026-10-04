"""Trusted export of resolved compiler products, never source syntax transport."""

from dataclasses import dataclass, field
from typing import Any
import hashlib
import json

from pietto._project.project_compiled_schema import (
    Address,
    CompiledError,
    Description,
    FIELDS,
    MEMBERS,
    Record,
    Scalar,
    content_pin,
    encode,
)
from pietto._project.project_compiled_loading import supported_compatibility
from pietto._project.project_compiled_verification import (
    MEMBER_KINDS,
    RELATIONS,
    verify_description,
)
from pietto._project.model import CompiledProjectInput
from pietto._project.project_sql_emission_contract import BoundSource
from pietto._project import project_sql_emission_ast as sql
from pietto._project import project_sql_emission_parameters as parameters
from pietto._project import project_sql_emission_rows as rows
from pietto._project import project_sql_emission_results as results
from pietto._project import project_sql_emission_aggregation as grouping
from pietto._project import project_sql_emission_windows as windowing
from pietto._project import project_sql_emission_sets as setting
from pietto._project import project_sql_emission_joins as joining

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class CompiledBuild:
    root: CompiledProjectInput = field(repr=False)
    payload: bytes = field(repr=False)
    pin: str
    producer: str
    compatibility: tuple


def _logical(value):
    return value.resolved_type.name, value.nullability.value


class _Export:
    def __init__(self, artifact, guarded, refinement):
        from pietto._project.project_execution_binding_verification import inspect

        self.view = inspect(artifact, guarded)
        self.artifact, self.request = artifact, artifact.request
        self.records = {}
        self.counts = {}
        self.declarations, self.sources, self.source_ports = {}, {}, {}
        self.units, self.unit_ports = {}, {}
        self.join_refs, self.input_refs = {}, {}
        self.match_uses, self.paths, self.requests, self.steps = {}, {}, {}, {}
        self.guarded = guarded
        self.refinement = refinement
        if refinement is not None:
            from pietto._project.project_refinement_verification import (
                verify_refinement,
            )

            verify_refinement(refinement)
            if (
                refinement.original is not artifact
                or refinement.output.guarded is not guarded
            ):
                raise CompiledError("COMPILED_EXPORT_REFINEMENT_ROOT")
        self.sites, self.literals, self.slots = {}, {}, {}
        self.contexts, self.field_refs = {}, {}
        self.values = {}
        self.requirement_anchors = {}
        self.compatibility = supported_compatibility()
        parsed = self.request.verification.completed.semantic_result.module_attribution_facts._authority.parse_result
        origins = tuple(
            (s.position, s.path, s.sha256) for s in parsed.trusted_source_snapshots
        )
        identity = json.dumps(
            (self.compatibility, origins), separators=(",", ":")
        ).encode()
        self.producer_identity = hashlib.sha256(
            b"pietto.compiled-build.v1\0" + identity + self.request.accepted_bytes
        ).hexdigest()

    def reserve(self, kind):
        position = self.counts.get(kind, 0)
        self.counts[kind] = position + 1
        address = Address(kind, position)
        self.records[address] = None
        return address

    def finish(self, address, *values):
        if self.records[address] is not None or len(values) != len(
            FIELDS[address.kind]
        ):
            raise CompiledError("COMPILED_EXPORT_RECORD")
        self.records[address] = Record(address, tuple(values))
        return address

    def add(self, kind, *values):
        return self.finish(self.reserve(kind), *values)

    def declaration(self, owner):
        key = id(owner)
        if key not in self.declarations:
            self.declarations[key] = self.add(
                "declaration",
                owner.identity.module_path,
                owner.module_position,
                owner.declaration_position,
                owner.identity.namespace.value,
                owner.identity.declaration_kind.value,
                owner.identity.declared_name,
            )
        return self.declarations[key]

    def source_meaning(self, field):
        from pietto._project.project_scalar_meaning import _source_entry, verify_law

        entry = _source_entry(field.scalar_meaning, field.field)
        if entry is None:
            return None
        name = field.field.evidence.resolved_type.name
        verify_law(entry.law, name)
        return name

    def source_records(self):
        for source in self.request.sources:
            address = self.reserve("source")
            self.sources[id(source)] = address
            fields, ports = [], []
            for f in source.fields:
                logical = (
                    f.field.evidence.resolved_type.name,
                    f.field.effective_nullability.value,
                )
                record = self.add(
                    "field",
                    address,
                    f.ordinal,
                    f.name,
                    f.column,
                    logical,
                    f.representation.decode("utf-8"),
                    None
                    if f.decimal is None
                    else (f.decimal.precision, f.decimal.scale),
                    self.source_meaning(f),
                )
                fields.append(record)
                self.field_refs[id(f.field)] = record
                ports.append(
                    self.add("port", address, f.ordinal, f.name, record, logical)
                )
            self.source_ports[id(source)] = tuple(ports)
            from pietto._project.project_sql_emission_contract import source_family

            bindings = tuple(
                s for s in self.request.plan.sources if s.source.owner is source.owner
            )
            if len(bindings) != 1:
                raise CompiledError("COMPILED_EXPORT_SOURCE_BINDING")
            self.finish(
                address,
                self.declaration(source.owner),
                source.namespace,
                source.name,
                tuple(fields),
                source_family(bindings[0]),
            )

    def source_unique_records(self):
        seen = set()
        for source in self.request.sources:
            definitions = tuple(
                d
                for d in self.request.plan.bindings.definitions
                if d.entry.owner is source.owner
            )
            if len(definitions) != 1:
                raise CompiledError("COMPILED_SOURCE_KEY_OWNER")
            for key in definitions[0].entry.active_properties.relational.keys:
                for fact in key.supports:
                    for support in fact.supports:
                        if id(support) in seen:
                            continue
                        seen.add(id(support))
                        fields = tuple(
                            self.source_ports[id(source)][
                                d.source_field_identity.field_position
                            ]
                            for d in support.determinants
                        )
                        self.add(
                            "source_unique",
                            self.sources[id(source)],
                            self.declaration(support.declaration.shape_occurrence),
                            support.identity.declaration.shape_item_position,
                            fields,
                            support.null_policy.value,
                            support.origin.value,
                            support.trust.value,
                            support.enforcement.value,
                        )

    def premise_records(self):
        from pietto._project.project_sql_emission_scopes import reference_source_ports

        references = reference_source_ports(self.request.plan)
        for premise in self.request.premises:
            if premise.scope == "statement":
                scope = "statement"
            elif type(premise.scope) is tuple:
                owner, context = premise.scope
                if id(context) not in self.contexts:
                    fields = tuple(
                        self.field_refs[id(port.field)]
                        for expression, port in references.values()
                        if expression.site is context
                    )
                    self.contexts[id(context)] = self.add(
                        "expression_context",
                        self.declaration(context.owner),
                        context.ref.kind.value,
                        context.ref.position,
                        context.block.kind.value,
                        context.block.position,
                        fields,
                    )
                scope = (self.declaration(owner), self.contexts[id(context)])
            else:
                scope = self.declaration(premise.scope)
            self.add(
                "premise", premise.position, premise.key, scope, premise.value.decode()
            )

    def literal_records(self, *, plan=None):
        plan = self.request.plan if plan is None else plan
        from pietto.ast_nodes import (
            UnaryExpr,
            BinaryExpr,
            ComparisonExpr,
            IsNullExpr,
            BetweenExpr,
            CallExpr,
        )

        parents = {
            UnaryExpr: "unary",
            BinaryExpr: "binary",
            ComparisonExpr: "comparison",
            IsNullExpr: "null_test",
            BetweenExpr: "between",
            CallExpr: "call",
        }
        for index, site in enumerate(plan.literal_sites):
            p = site.position
            ancestry = []
            for parent, position in p.ancestry:
                if type(parent) not in parents:
                    raise CompiledError("COMPILED_EXPORT_ANCESTRY")
                ancestry.append((parents[type(parent)], position))
            ref = self.add(
                "site",
                self.declaration(p.owner),
                p.role.value,
                index,
                tuple(ancestry),
                site.disposition.value,
                None if site.reason is None else site.reason.value,
            )
            self.sites[id(site)] = ref
            value = p.literal.value
            tag = {bool: "Bool", int: "Int", float: "Float", str: "Text"}.get(
                type(value)
            )
            if value is None:
                self.literals[id(p.literal)] = self.add("null_literal", ref)
            elif tag is None:
                raise CompiledError("COMPILED_EXPORT_LITERAL")
            else:
                self.literals[id(p.literal)] = self.add(
                    "literal", tag, Scalar(tag, value), ref
                )
        for slot in plan.literal_slots:
            self.slots[id(slot)] = self.add(
                "slot",
                self.sites[id(slot.site)],
                self.literals[id(slot.site.position.literal)],
                slot.tag.value,
            )
        for use in self.artifact.parameter_uses if plan is self.request.plan else ():
            self.add(
                "native_use",
                self.slots[id(use.slot)],
                use.ordinal,
                use.server_index,
                use.physical_type,
            )

    def producer(self, scan):
        if type(scan) in (sql.RowScan, sql.SQLScan):
            return scan.realization
        if type(scan) is sql.SQLNamedUse:
            return scan.cte.body
        if type(scan) in (
            sql.RowNamedUse,
            sql.RowStageUse,
            sql.RowJoinUse,
            results.RowResultUse,
        ):
            return scan.body
        raise CompiledError("COMPILED_EXPORT_INPUT")

    def producer_ref(self, producer):
        return (
            self.sources[id(producer)]
            if id(producer) in self.sources
            else self.units[id(producer)]
        )

    def producer_ports(self, producer):
        return (
            self.source_ports[id(producer)]
            if id(producer) in self.sources
            else self.unit_ports[id(producer)]
        )

    def read(self, read, producer, use):
        if isinstance(producer, BoundSource):
            indexes = tuple(i for i, f in enumerate(producer.fields) if read.field is f)
        else:
            indexes = tuple(
                i
                for i, c in enumerate(producer.columns)
                if c.column.terminal is read.terminal
            )
        if len(indexes) != 1:
            raise CompiledError("COMPILED_EXPORT_READ")
        return self.add("read", self.producer_ports(producer)[indexes[0]], use, "value")

    def anchor(self, reference, address):
        if reference is None:
            return
        bucket = self.requirement_anchors.setdefault(reference, [])
        if address not in bucket:
            bucket.append(address)

    def scalar(self, value, producer, use, join_inputs=None):
        address = self.scalar_value(value, producer, use, join_inputs)
        self.anchor(value.original.ref, address)
        return address

    def scalar_value(self, value, producer, use, join_inputs=None):
        if type(value) is rows.SQLStageReference:
            if join_inputs is not None:
                matches = tuple(
                    (p, u) for symbol, p, u in join_inputs if symbol is value.scope
                )
                if len(matches) != 1:
                    raise CompiledError("COMPILED_EXPORT_MATCH_SCOPE")
                producer, use = matches[0]
            return self.read(value.column, producer, use)
        if type(value) is parameters.SQLAnchor:
            return self.scalar(value.operand, producer, use, join_inputs)
        if type(value) in (parameters.SQLLiteral, parameters.SQLParameter):
            return self.literals[id(value.original.expression)]
        if type(value) is parameters.SQLUnary:
            inner = self.scalar(value.operand, producer, use, join_inputs)
            return self.add(
                "operation",
                ("unary", value.original.expression.operator),
                (inner,),
                _logical(value.original.value_type),
                None,
            )
        if type(value) is rows.SQLOperation:
            original = value.original
            operator = original.expression
            token = (
                operator.operator
                if value.kind != "null_test"
                else ("is_not_null" if operator.negated else "is_null")
            )
            role = {
                "sign": "unary",
                "arithmetic": "binary",
                "logical": "binary",
                "comparison": "comparison",
                "null_test": "null_test",
            }[value.kind]
            return self.add(
                "operation",
                (role, token),
                tuple(
                    self.scalar(v, producer, use, join_inputs) for v in value.operands
                ),
                _logical(original.value_type),
                None,
            )
        raise CompiledError("COMPILED_EXPORT_SCALAR")

    def window_spec(self, specification, policy, producer, use, definitions):
        partitions = tuple(
            self.read(read, producer, use) for _, read in specification.partitions
        )
        ordering = tuple(
            (self.read(i.read, producer, use), i.direction, i.nulls)
            for i in specification.orders
        )
        frame = None
        if specification.frame is not None:
            resolved = policy.specification.frame.resolved
            frame = (
                resolved.unit.value,
                (
                    resolved.start.kind.value,
                    None
                    if resolved.start.offset is None
                    else self.literals[id(resolved.start.offset)],
                ),
                (
                    resolved.end.kind.value,
                    None
                    if resolved.end.offset is None
                    else self.literals[id(resolved.end.offset)],
                ),
                None if resolved.exclusion is None else resolved.exclusion.value,
            )
        named = (
            None
            if specification.symbol is None
            else definitions[id(specification.symbol)]
        )
        return self.add("window_spec", partitions, ordering, frame, named)

    def set_unit(self, unit, position):
        address = self.reserve("set")
        self.units[id(unit)] = address
        uses, aliases = [], []
        for operand in unit.operands:
            producer = operand.producer
            uses.append(
                self.add(
                    "use",
                    address,
                    self.producer_ref(producer),
                    operand.position,
                    self.producer_ports(producer),
                )
            )
            aliases.append(operand.symbol.name)
        ports = []
        for column in unit.columns:
            inputs = tuple(
                self.read(o.columns[column.ordinal], o.producer, use)
                for o, use in zip(unit.operands, uses, strict=True)
            )
            logical = (
                column.realization.tag,
                {False: "non_null", True: "nullable", "unknown": "unknown"}[
                    column.realization.nullable
                ],
            )
            value = self.add("set_value", address, inputs, logical)
            ports.append(
                self.add("port", address, column.ordinal, column.label, value, logical)
            )
        self.unit_ports[id(unit)] = tuple(ports)
        layout = (
            None if unit.symbol is None else unit.symbol.name,
            tuple(c.name for c in unit.cte_columns),
            tuple(aliases),
            unit.final,
            position,
        )
        return self.finish(
            address,
            self.declaration(unit.definition.original.entry.owner),
            unit.kind.value,
            unit.quantifier.value,
            tuple(uses),
            tuple(ports),
            layout,
        )

    def join_unit(self, unit, position):
        address = self.reserve("join")
        self.units[id(unit)] = address
        self.join_refs[id(unit.join.ref)] = address
        definitions = tuple(
            d
            for d in self.request.plan.bindings.definitions
            if d.ref is unit.join.definition
        )
        if len(definitions) != 1:
            raise CompiledError("COMPILED_EXPORT_JOIN_OWNER")
        uses, aliases, contexts = [], [], []
        for item in unit.inputs:
            producer = item.producer
            use = self.add(
                "use",
                address,
                self.producer_ref(producer),
                item.ordinal,
                self.producer_ports(producer),
            )
            uses.append(use)
            self.input_refs[id(item.original.ref)] = use
            aliases.append(item.symbol.name)
            contexts.append((item.symbol, producer, use))
        equalities = []
        for item in unit.equalities:
            left = self.read(item.left, unit.inputs[0].producer, uses[0])
            right = self.read(item.right, unit.inputs[1].producer, uses[1])
            equalities.append(self.add("join_equality", address, left, right))
        predicate = (
            None
            if unit.predicate is None
            else self.scalar(unit.predicate, None, None, tuple(contexts))
        )
        ports = []
        for column in unit.columns:
            matches = tuple(
                (p, u) for symbol, p, u in contexts if symbol is column.scope
            )
            if len(matches) != 1:
                raise CompiledError("COMPILED_EXPORT_JOIN_COLUMN")
            read = self.read(column.read, *matches[0])
            logical = (
                column.column.realization.tag,
                {False: "non_null", True: "nullable", "unknown": "unknown"}[
                    column.column.realization.nullable
                ],
            )
            value = self.add("join_value", address, read, logical)
            ports.append(
                self.add("port", address, column.position, column.label, value, logical)
            )
        self.unit_ports[id(unit)] = tuple(ports)
        from pietto._project.project_ir_joins import (
            ProjectIRBinaryJoinOccurrence,
            _source_slice_fields,
        )
        from pietto._project.project_current_joins import ProjectCurrentBinaryJoin

        original_join = unit.join.source.source
        if type(original_join) is ProjectIRBinaryJoinOccurrence:
            law = "relationship"
            source_positions = tuple(
                f.field_position for f in _source_slice_fields(original_join)
            )
            if original_join.guarantee.minimum.value != "zero_allowed":
                raise CompiledError("COMPILED_EXPLICIT_COVERAGE_INPUT")
        elif type(original_join) is ProjectCurrentBinaryJoin:
            law = "current"
            candidates = original_join.condition.environment.source_candidates
            source_positions = tuple(
                i
                for i, (binding, _) in enumerate(original_join.left_fields)
                if len(candidates) == 1 and binding is candidates[0]
            )
        else:
            raise CompiledError("COMPILED_JOIN_LAW")
        return self.finish(
            address,
            self.declaration(definitions[0].entry.owner),
            unit.join.position,
            unit.join.kind.value,
            law,
            source_positions,
            tuple(uses),
            tuple(equalities),
            predicate,
            tuple(ports),
            (
                unit.symbol.name,
                tuple(s.name for s in unit.cte_columns),
                tuple(aliases),
                False,
                position,
            ),
        )

    def ordinary_unit(self, unit, ctes, position):
        if type(unit) is joining.JoinBody:
            return self.join_unit(unit, position)
        if type(unit) is setting.SetBody:
            return self.set_unit(unit, position)
        if type(unit) not in (sql.SQLSelect, sql.RowBody, results.RowResultBody):
            raise CompiledError("COMPILED_EXPORT_UNIT")
        owner = unit.definition.original.entry.owner
        aggregation = getattr(unit, "aggregation", None)
        window = getattr(unit, "window", None)
        kind = (
            "aggregate"
            if aggregation is not None
            else "window"
            if window is not None
            else "result"
            if type(unit) is results.RowResultBody
            else "row"
        )
        address = self.reserve(kind)
        self.units[id(unit)] = address
        producer = self.producer(unit.scan)
        use = self.add(
            "use",
            address,
            self.producer_ref(producer),
            0,
            self.producer_ports(producer),
        )
        definitions = {}
        if window is not None:
            definitions = {
                id(d.symbol): self.reserve("window_definition")
                for d in window.definitions
            }
            for d in window.definitions:
                columns = tuple(
                    c for c in window.columns if c.specification.symbol is d.symbol
                )
                if not columns:
                    raise CompiledError("COMPILED_EXPORT_WINDOW_DEFINITION")
                policy = next(
                    p
                    for p in self.request.plan.window_policies
                    if p.ref is columns[0].window.policy
                )
                spec = self.window_spec(
                    d.specification, policy, producer, use, definitions
                )
                self.finish(definitions[id(d.symbol)], d.index, d.label, spec)
        values, ports = [], []
        for i, column in enumerate(unit.columns):
            if type(column) is sql.SQLColumn:
                if isinstance(producer, BoundSource):
                    positions = tuple(
                        j
                        for j, f in enumerate(producer.fields)
                        if f is column.source_field
                    )
                else:
                    positions = tuple(
                        j
                        for j, c in enumerate(producer.columns)
                        if c.export.ref is column.input_port.producer_port
                    )
                if len(positions) != 1:
                    raise CompiledError("COMPILED_EXPORT_PROJECTION")
                expr = self.add(
                    "read", self.producer_ports(producer)[positions[0]], use, "value"
                )
                logical = (
                    column.source_field.field.evidence.resolved_type.name,
                    column.source_field.field.effective_nullability.value,
                )
            elif type(column) in (
                sql.RowCarryColumn,
                results.ResultColumn,
                grouping.AggregateKeyColumn,
                grouping.AggregateProjectionColumn,
                windowing.WindowProjectionColumn,
            ):
                expr = self.read(column.read, producer, use)
                logical = (
                    column.column.realization.tag,
                    {False: "non_null", True: "nullable", "unknown": "unknown"}[
                        column.column.realization.nullable
                    ],
                )
            elif type(column) is windowing.WindowColumn:
                policy = next(
                    p
                    for p in self.request.plan.window_policies
                    if p.ref is column.window.policy
                )
                declared_arguments = tuple(
                    a
                    for a in self.request.plan.window_arguments
                    if a.window is column.window.ref
                )
                arguments = []
                for actual, original in zip(
                    column.arguments, declared_arguments, strict=True
                ):
                    value = (
                        self.read(actual.read, producer, use)
                        if actual.read is not None
                        else self.literals[id(original.expression)]
                    )
                    arguments.append((actual.role, value))
                spec = self.window_spec(
                    column.specification, policy, producer, use, definitions
                )
                logical = _logical(column.window.value_type)
                expr = self.add(
                    "window_value",
                    column.function,
                    tuple(arguments),
                    spec,
                    self.producer_ports(producer),
                    column.selected,
                    logical,
                )
            elif type(column) is grouping.AggregateValueColumn:
                logical = (
                    column.column.realization.tag,
                    {False: "non_null", True: "nullable", "unknown": "unknown"}[
                        column.column.realization.nullable
                    ],
                )
                arguments = (
                    ()
                    if column.argument is None
                    else (self.scalar(column.argument, producer, use),)
                )
                expr = self.add("aggregate_value", column.function, arguments, logical)
            elif type(column) is sql.RowValueColumn:
                expr = self.scalar(column.value, producer, use)
                logical = _logical(column.value.original.value_type)
            elif type(column) is sql.SQLLiteralColumn:
                value = (
                    column.value if column.value is not None else column.origin.value
                )
                if column.value is None:
                    if isinstance(producer, BoundSource) or column.producer is None:
                        raise CompiledError("COMPILED_EXPORT_LITERAL_CARRY")
                    positions = tuple(
                        j
                        for j, c in enumerate(producer.columns)
                        if c.export.ref is column.producer.canonical.ref
                    )
                    if len(positions) != 1:
                        raise CompiledError("COMPILED_EXPORT_LITERAL_CARRY")
                    expr = self.add(
                        "read",
                        self.producer_ports(producer)[positions[0]],
                        use,
                        "value",
                    )
                else:
                    expr = self.scalar(value, producer, use)
                logical = _logical(value.original.value_type)
            else:
                raise CompiledError("COMPILED_EXPORT_COLUMN")
            values.append(expr)
            ports.append(self.add("port", address, i, column.label, expr, logical))
        self.unit_ports[id(unit)] = tuple(ports)
        predicate = getattr(unit, "predicate", None)
        condition = (
            None if predicate is None else self.scalar(predicate.value, producer, use)
        )
        cte = ctes.get(id(unit))
        symbol = cte.symbol if cte is not None else getattr(unit, "symbol", None)
        columns = cte.columns if cte is not None else getattr(unit, "cte_columns", ())
        cte_names = tuple(s.name for s in columns)
        layout = (
            None if symbol is None else symbol.name,
            cte_names,
            unit.scan.symbol.name,
            getattr(unit, "final", symbol is None),
            position,
        )
        if kind == "window":
            self.finish(
                address,
                self.declaration(owner),
                use,
                self.producer_ref(producer),
                tuple(definitions.values()),
                tuple(values),
                tuple(ports),
                layout,
            )
        elif kind == "aggregate":
            if aggregation is None:
                raise CompiledError("COMPILED_EXPORT_AGGREGATION")
            from pietto._project.project_joined_aggregation import (
                ProjectConcreteJoinedAggregation,
            )
            from pietto._project.project_multifact import (
                ProjectCurrentMultiFactRegion,
                ProjectMultiFactConcreteRegion,
            )

            authority = aggregation.aggregation.authority.source
            risk_law = None
            if type(authority) is ProjectConcreteJoinedAggregation:
                region = authority.input_filter.joined_semantics.multifact_region
                if type(region) is ProjectCurrentMultiFactRegion:
                    risk_law = "current"
                elif type(region) is ProjectMultiFactConcreteRegion:
                    risk_law = "relationship"
                else:
                    raise CompiledError("COMPILED_AGGREGATE_RISK_INPUT")
            self.finish(
                address,
                self.declaration(owner),
                use,
                self.producer_ref(producer),
                aggregation.mode,
                risk_law,
                tuple(values[: len(aggregation.keys)]),
                tuple(values[len(aggregation.keys) :]),
                tuple(ports),
                layout,
            )
        elif kind == "row":
            stage = (
                "projection" if type(unit) is sql.SQLSelect else unit.block.kind.value
            )
            self.finish(
                address,
                self.declaration(owner),
                use,
                self.producer_ref(producer),
                stage,
                tuple(values),
                condition,
                tuple(ports),
                layout,
            )
        else:
            ordering = (
                ()
                if unit.order is None
                else tuple(
                    (self.read(i.read, producer, use), i.direction)
                    for i in unit.order.items
                )
            )
            self.finish(
                address,
                self.declaration(owner),
                self.producer_ref(producer),
                tuple(values),
                unit.distinct is not None,
                ordering,
                None if unit.limit is None else unit.limit.value,
                None
                if unit.limit is None
                else self.literals[id(unit.limit.limit.literal)],
                tuple(ports),
                layout,
            )
        return address

    def requirement_unit_anchors(self, unit):
        """Explicit correspondence for the original finite dialect carriers."""
        address = self.units[id(unit)]
        ports = self.unit_ports[id(unit)]
        if type(unit) is joining.JoinBody:
            self.anchor(unit.join.ref, address)
            for item, use in zip(
                unit.inputs, self.records[address].get("inputs"), strict=True
            ):
                self.anchor(item.original.ref, use)
                for old, target in zip(
                    item.original.ports, self.records[use].get("ports"), strict=True
                ):
                    self.anchor(old, target)
            for column, port in zip(unit.columns, ports, strict=True):
                self.anchor(column.port.ref, port)
            for equality, target in zip(
                unit.equalities, self.records[address].get("equalities"), strict=True
            ):
                self.anchor(equality.original.ref, target)
            return
        self.anchor(unit.definition.original.ref, address)
        if type(unit) is setting.SetBody:
            self.anchor(unit.body.ref, address)
            for operand, use in zip(
                unit.operands, self.records[address].get("operands"), strict=True
            ):
                self.anchor(operand.operand.ref, use)
            for column, port in zip(unit.columns, ports, strict=True):
                self.anchor(column.source.ref, self.records[port].get("source"))
                self.anchor(column.export.ref, port)
            return
        if type(unit) is sql.SQLSelect:
            blocks = tuple(
                b
                for b in self.request.plan.blocks
                if b.definition is unit.definition.original.ref
            )
            if len(blocks) != 1:
                raise CompiledError("COMPILED_REQUIREMENT_COMPACT_BLOCK")
            self.anchor(blocks[0].ref, address)
        elif type(unit) is results.RowResultBody:
            for boundary in unit.boundaries:
                self.anchor(boundary.ref, address)
            if unit.distinct is not None:
                self.anchor(unit.distinct.distinct.ref, address)
                for field, port in zip(unit.distinct.fields, ports, strict=True):
                    self.anchor(field.ref, port)
            if unit.order is not None:
                self.anchor(unit.order.order.ref, address)
                for item, (read, _direction) in zip(
                    unit.order.items, self.records[address].get("ordering"), strict=True
                ):
                    for reference in (item.item.ref, item.expression.ref, item.use.ref):
                        self.anchor(reference, read)
            if unit.limit is not None:
                self.anchor(
                    unit.limit.limit.ref, self.records[address].get("limit_literal")
                )
        else:
            self.anchor(unit.block.ref, address)
            if unit.aggregation is not None:
                self.anchor(unit.aggregation.aggregation.ref, address)
        columns: tuple[Any, ...] = unit.columns
        for column, port in zip(columns, ports, strict=True):
            value = self.records[port].get("source")
            self.anchor(column.export.ref, port)
            if type(column) in (sql.SQLColumn, sql.SQLLiteralColumn):
                self.anchor(column.projection.ref, port)
                self.anchor(column.projection.expression, value)
            else:
                self.anchor(column.column.terminal, port)
            if type(column) is grouping.AggregateKeyColumn:
                self.anchor(column.key.ref, value)
            elif type(column) is grouping.AggregateValueColumn:
                self.anchor(column.aggregate.ref, value)
            elif type(column) in (
                grouping.AggregateProjectionColumn,
                windowing.WindowProjectionColumn,
            ):
                self.anchor(column.projection.ref, port)
            elif type(column) is windowing.WindowColumn:
                self.anchor(column.window.ref, value)
                self.anchor(
                    column.window.policy, self.records[value].get("specification")
                )
            elif type(column) is results.ResultColumn:
                self.anchor(column.projection_port.ref, self.records[value].get("port"))
                for stage in column.stages:
                    self.anchor(stage.input_port.ref, port)
                    self.anchor(stage.output_port.ref, port)
                self.anchor(column.output.ref, port)

    def requirement_records(self):
        from pietto._project.project_sql_plan_requirements import (
            verify_project_sql_requirement_report,
        )
        from pietto._project.project_sql_plan import ProjectSQLPlanRef
        from pietto._project.project_sql_plan_expressions import (
            ProjectSQLLiteral,
            ProjectSQLBoundLiteral,
        )

        plan, report = self.request.plan, self.request.report.report
        if not verify_project_sql_requirement_report(
            report, self.request.verification
        ).verified:
            raise CompiledError("COMPILED_EXPORT_REQUIREMENT_ROOT")
        for source in self.request.sources:
            definition = next(
                d for d in plan.bindings.definitions if d.entry.owner is source.owner
            )
            self.anchor(definition.ref, self.sources[id(source)])
            for old, address in zip(
                definition.exports, self.source_ports[id(source)], strict=True
            ):
                self.anchor(old.ref, address)
        for site in plan.literal_sites:
            self.anchor(site.ref, self.sites[id(site)])
        for slot in plan.literal_slots:
            self.anchor(slot.ref, self.slots[id(slot)])
        for value, use in zip(plan.fixed_envelope.values, plan.bind_uses, strict=True):
            self.anchor(value.ref, self.slots[id(value.slot)])
            self.anchor(use.ref, self.slots[id(use.slot)])
        for expression in plan.expressions:
            if type(expression) in (ProjectSQLLiteral, ProjectSQLBoundLiteral):
                self.anchor(expression.ref, self.literals[id(expression.expression)])
        for obligation in plan.single_matches:
            self.anchor(obligation.ref, self.requests[id(obligation.request)])
        for proof in plan.single_match_proofs:
            original = next(o for o in plan.single_matches if o.ref is proof.obligation)
            self.anchor(proof.ref, self.requests[id(original.request)])
        for risk in plan.aggregate_risks:
            self.anchor(risk.ref, self.requirement_anchors[risk.aggregation][0])

        def reference(value):
            if value is plan.scope:
                return ("scope", 0)
            if type(value) is not ProjectSQLPlanRef or value.scope is not plan.scope:
                raise CompiledError("COMPILED_EXPORT_REQUIREMENT_REFERENCE")
            return (value.kind.value, value.position)

        origin_addresses = {
            origin.ref: self.reserve("requirement_origin") for origin in plan.origins
        }
        for origin in plan.origins:
            span = origin.cause.span
            self.finish(
                origin_addresses[origin.ref],
                reference(origin.subject),
                origin.role.value,
                origin.provenance.value,
                self.declaration(origin.owner),
                (span.path, span.line, span.column, span.end_line, span.end_column),
                tuple(reference(a) for a in origin.antecedents),
            )
        origins_by_subject = {}
        origins_by_ref = {origin.ref: origin for origin in plan.origins}
        for origin in plan.origins:
            origins_by_subject.setdefault(origin.subject, []).append(origin)

        def anchors(subject):
            found, pending, seen = [], [subject], set()
            while pending:
                current = pending.pop()
                if current in seen:
                    continue
                seen.add(current)
                if current in self.requirement_anchors:
                    found.extend(
                        a for a in self.requirement_anchors[current] if a not in found
                    )
                    continue
                origins = (
                    (origins_by_ref[current],)
                    if current in origins_by_ref
                    else origins_by_subject.get(current, ())
                )
                pending.extend(
                    a
                    for origin in reversed(origins)
                    for a in reversed(origin.antecedents)
                )
            return tuple(found)

        entries = []
        for entry in report.entries:
            entries.append(
                self.add(
                    "requirement",
                    entry.family.value,
                    None if entry.subkind is None else entry.subkind.value,
                    reference(entry.subject),
                    reference(entry.scope.definition),
                    tuple(reference(r) for r in entry.scope.stages),
                    tuple(reference(r) for r in entry.scope.input_uses),
                    origin_addresses[entry.origin.ref],
                    anchors(entry.subject),
                )
            )
        for link in report.links:
            self.add(
                "requirement_link",
                link.kind.value,
                entries[link.source.position],
                entries[link.target.position],
            )

    def request_records(self, *, plan=None):
        plan = self.request.plan if plan is None else plan
        from pietto._project.project_single_match import _boundaries
        from pietto._project.project_relationship_paths import (
            ProjectRelationshipPathStep,
        )
        from pietto._project.project_relationship_uses import ProjectTraversalStepUse

        completed = self.request.verification.completed
        reached_owners = tuple(d.entry.owner for d in plan.bindings.definitions)
        originals = tuple(
            r
            for r in completed.single_match_requests
            if any(r.owner is owner for owner in reached_owners)
        )
        for request in originals:
            if id(request) in self.requests:
                continue
            candidates = tuple(o for o in plan.single_matches if o.request is request)
            if not candidates:
                raise CompiledError("COMPILED_RETAINED_REQUEST_SCOPE")
            obligation = candidates[0]
            condition = obligation.assessment.condition
            if condition is None:
                raise CompiledError("COMPILED_REQUEST_CONDITION")
            if id(request.use) not in self.match_uses:
                path = condition.effective_use.path
                if path is not None and id(path) not in self.paths:
                    steps = []
                    for step in path.steps:
                        direction = step.guarantee.direction
                        declared = direction.declaration
                        if id(step) not in self.steps:
                            self.steps[id(step)] = self.add(
                                "match_step",
                                step.position,
                                declared.module.path,
                                declared.module_position,
                                declared.relationship_position,
                                direction.source.identity.endpoint_position,
                                direction.target.identity.endpoint_position,
                            )
                        steps.append(self.steps[id(step)])
                    self.paths[id(path)] = self.add("match_path", tuple(steps))
                boundaries = []
                for boundary in _boundaries(completed.effective_outputs, condition):
                    joins = tuple(
                        j
                        for j in plan.joins
                        if j.source is boundary or j.source.source is boundary
                    )
                    if len(joins) != 1:
                        raise CompiledError("COMPILED_REQUEST_BOUNDARY")
                    boundaries.append(self.join_refs[id(joins[0].ref)])
                authority = completed.effective_outputs.operative_conditions
                positions = tuple(
                    i for i, c in enumerate(authority.entries) if c is condition
                )
                if len(positions) != 1:
                    raise CompiledError("COMPILED_REQUEST_ORDER")
                self.match_uses[id(request.use)] = self.add(
                    "match_use",
                    self.declaration(request.owner),
                    positions[0],
                    tuple(boundaries),
                    None if path is None else self.paths[id(path)],
                )
            hop = None
            if type(request.hop) is ProjectRelationshipPathStep:
                positions = tuple(
                    i
                    for i, step in enumerate(request.path.steps)
                    if step is request.hop
                )
                if len(positions) != 1:
                    raise CompiledError("COMPILED_REQUEST_HOP")
                hop = ("path_step", positions[0])
            elif type(request.hop) is ProjectTraversalStepUse:
                positions = tuple(
                    i
                    for i, step in enumerate(condition.use.step_uses)
                    if step is request.hop
                )
                if len(positions) != 1:
                    raise CompiledError("COMPILED_REQUEST_HOP")
                hop = ("traversal_step", positions[0])
            elif request.hop is not None:
                raise CompiledError("COMPILED_REQUEST_HOP")
            pairs = tuple(
                tuple(self.input_refs[id(a)] for a in pair)
                for pair in obligation.input_pairs
            )
            self.requests[id(request)] = self.add(
                "request",
                self.declaration(request.owner),
                self.match_uses[id(request.use)],
                request.scope.value,
                request.unit.value,
                None if request.path is None else self.paths[id(request.path)],
                hop,
                pairs,
            )
        return tuple(self.requests[id(request)] for request in originals)

    def run(self):
        self.source_records()
        self.source_unique_records()
        self.premise_records()
        self.literal_records()
        ast = self.artifact.ast
        units = (
            tuple(c.body for c in ast.ctes) + (ast,)
            if type(ast) is sql.SQLSelect
            else ast.units
            if type(ast) is sql.SQLJoinQuery
            else ast.bodies
        )
        ctes = {id(c.body): c for c in ast.ctes} if type(ast) is sql.SQLSelect else {}
        for position, unit in enumerate(units):
            self.ordinary_unit(unit, ctes, position)
            self.requirement_unit_anchors(unit)
        terminal = self.units[id(units[-1])]
        ports = self.unit_ports[id(units[-1])]
        requests = self.request_records()
        self.requirement_records()
        query = self.add(
            "entry",
            self.declaration(self.request.verification.selected_owner),
            terminal,
            ports,
            requests,
            (),
        )
        self.add(
            "target",
            self.request.family,
            self.request.release,
            self.request.accepted_bytes.decode(),
            "finite_pg_v1" if self.request.family == "postgres" else "finite_mysql_v1",
        )
        requirements = (
            ()
            if self.refinement is None
            else tuple(
                self.add(
                    "provider",
                    self.sources[id(requirement.source)],
                    requirement.provider,
                    requirement.version,
                    requirement.revision,
                    (requirement.registry_namespace, requirement.registry_name),
                    requirement.definition,
                    requirement.token_columns,
                    requirement.role,
                    requirement.provider_guarantee,
                )
                for requirement in self.refinement.sources
            )
        )
        self.add(
            "policy",
            self.request.verification.literal_policy.value,
            self.guarded is not None,
            None if self.refinement is None else self.refinement.policy.choice,
            requirements,
        )
        for index, port in enumerate(ports):
            record = self.records[port]
            self.add(
                "output", index, record.get("label"), port, record.get("logical"), None
            )
        if any(r is None for r in self.records.values()):
            raise CompiledError("COMPILED_EXPORT_INCOMPLETE")
        members = tuple(
            (
                name,
                tuple(
                    r
                    for r in self.records.values()
                    if r.address.kind in MEMBER_KINDS[name]
                ),
            )
            for name in MEMBERS
        )
        return Description(self.compatibility, self.producer_identity, query, members)


class _LogicalExport(_Export):
    """Build-only adapter over an actual verified retained plan, without SQL."""

    def __init__(self, artifact, guarded, checked):
        super().__init__(artifact, guarded, None)
        self.checked = checked
        self.plan = checked.plan
        self.references = {}
        self.terminals = {}
        self.ports = {}
        self.aliases = {}
        self.expressions = {e.ref: e for e in self.plan.expressions}
        self.original_ports = {
            p.ref: p
            for p in (
                *self.plan.source_ports,
                *self.plan.input_ports,
                *self.plan.all_exports,
            )
        }
        self.stage_ports = {p.ref: p for p in self.plan.stage_ports}
        self.result_ports = {p.ref: p for p in self.plan.result_ports}
        self.join_ports = {p.ref: p for p in self.plan.join_ports}

    def port(self, reference):
        seen = set()
        while reference not in self.ports:
            if reference in seen:
                raise CompiledError("COMPILED_RETAINED_PORT_CYCLE")
            seen.add(reference)
            if reference in self.aliases:
                reference = self.aliases[reference]
            elif reference in self.stage_ports:
                reference = self.stage_ports[reference].source
            elif reference in self.result_ports:
                reference = self.result_ports[reference].source
            elif reference in self.join_ports:
                reference = self.join_ports[reference].source
            elif (
                reference in self.original_ports
                and self.original_ports[reference].producer_port is not None
            ):
                reference = self.original_ports[reference].producer_port
            else:
                raise CompiledError("COMPILED_RETAINED_PORT")
        return self.ports[reference]

    def read_port(self, reference, uses):
        port = self.port(reference)
        matches = tuple(use for use in uses if port in self.records[use].get("ports"))
        if len(matches) != 1:
            # Repeated producers require the original input-use occurrence.
            original = self.join_ports.get(reference)
            if original is not None and original.input is not None:
                use = self.input_refs.get(id(original.input))
                if use in matches:
                    matches = (use,)
        if len(matches) != 1:
            raise CompiledError("COMPILED_RETAINED_USE")
        return self.add("read", port, matches[0], "value")

    def expression(self, reference, uses):
        from pietto._project import project_sql_plan_expressions as expressions
        from pietto._project.project_sql_plan_aggregation import (
            ProjectSQLResultReference,
        )
        from pietto._project.project_sql_plan_windows import ProjectSQLWindowReference

        original = self.expressions[reference]
        if type(original) in (
            expressions.ProjectSQLLiteral,
            expressions.ProjectSQLBoundLiteral,
        ):
            return self.literals[id(original.expression)]
        if type(original) in (
            expressions.ProjectSQLReference,
            expressions.ProjectSQLJoinedReference,
            expressions.ProjectSQLMatchReference,
            ProjectSQLResultReference,
            ProjectSQLWindowReference,
        ):
            return self.read_port(original.port, uses)
        if type(original) is expressions.ProjectSQLUnary:
            token, children = (
                ("unary", original.expression.operator),
                (original.operand,),
            )
        elif type(original) in (
            expressions.ProjectSQLBinary,
            expressions.ProjectSQLComparison,
        ):
            token = (
                "binary"
                if type(original) is expressions.ProjectSQLBinary
                else "comparison",
                original.expression.operator,
            )
            children = (original.left, original.right)
        elif type(original) is expressions.ProjectSQLIsNull:
            token = (
                "null_test",
                "is_not_null" if original.expression.negated else "is_null",
            )
            children = (original.value,)
        else:
            raise CompiledError("COMPILED_RETAINED_EXPRESSION")
        return self.add(
            "operation",
            token,
            tuple(self.expression(c, uses) for c in children),
            _logical(original.value_type),
            None,
        )

    def inputs(self, address, producers):
        return tuple(
            self.add(
                "use",
                address,
                producer,
                i,
                tuple(
                    p.address
                    for p in self.records.values()
                    if p is not None
                    and p.address.kind == "port"
                    and p.get("owner") == producer
                ),
            )
            for i, producer in enumerate(producers)
        )

    def layout(self, address, count):
        return (
            f"r{address.kind}{address.position}",
            tuple(f"c{i}" for i in range(count)),
            "s0",
            False,
            sum(a.kind in RELATIONS - {"source"} for a in self.records) - 1,
        )

    def source_inputs(self):
        from pietto._project.project_sql_emission_contract import (
            source_family,
            _logical_evidence,
        )

        for source in self.plan.sources:
            address = self.reserve("source")
            self.terminals[source.ref] = address
            self.references[source.ref] = address
            fields, ports = [], []
            original_ports = tuple(
                p for p in self.plan.source_ports if p.owner is source.ref
            )
            for i, port in enumerate(original_ports):
                field = port.field
                logical = (
                    field.evidence.resolved_type.name,
                    field.effective_nullability.value,
                )
                _, _, decimal = _logical_evidence(
                    field,
                    self.checked.completed.semantic_result.module_type_source_resolutions,
                )
                described = self.add(
                    "field",
                    address,
                    i,
                    field.evidence.name,
                    None,
                    logical,
                    None,
                    None if decimal is None else (decimal.precision, decimal.scale),
                    logical[0] if logical[0] in ("Timestamp", "UUID") else None,
                )
                fields.append(described)
                self.field_refs[id(field)] = described
                mapped = self.add(
                    "port", address, i, field.evidence.name, described, logical
                )
                self.ports[port.ref] = mapped
                ports.append(mapped)
            self.finish(
                address,
                self.declaration(source.source.owner),
                None,
                None,
                tuple(fields),
                source_family(source),
            )
            definition = next(
                d for d in self.plan.bindings.definitions if d.ref is source.ref
            )
            for old, mapped in zip(definition.exports, ports, strict=True):
                self.ports[old.ref] = mapped
            seen = set()
            for key in definition.entry.active_properties.relational.keys:
                for fact in key.supports:
                    for support in fact.supports:
                        if id(support) in seen:
                            continue
                        seen.add(id(support))
                        self.add(
                            "source_unique",
                            address,
                            self.declaration(support.declaration.shape_occurrence),
                            support.identity.declaration.shape_item_position,
                            tuple(
                                ports[d.source_field_identity.field_position]
                                for d in support.determinants
                            ),
                            support.null_policy.value,
                            support.origin.value,
                            support.trust.value,
                            support.enforcement.value,
                        )

    def logical_join(self, definition, join):
        from pietto._project.project_ir_joins import (
            ProjectIRBinaryJoinOccurrence,
            _source_slice_fields,
        )
        from pietto._project.project_current_joins import ProjectCurrentBinaryJoin

        address = self.reserve("join")
        original_inputs = tuple(
            next(i for i in self.plan.join_inputs if i.ref is r) for r in join.inputs
        )
        producers = tuple(
            self.references[i.predecessor]
            if i.predecessor is not None
            else self.terminals[i.producer]
            for i in original_inputs
        )
        uses = self.inputs(address, producers)
        for original, use in zip(original_inputs, uses, strict=True):
            self.input_refs[id(original.ref)] = use
            for reference, port in zip(
                original.ports, self.records[use].get("ports"), strict=True
            ):
                self.ports[reference] = port
        equalities = tuple(
            self.add(
                "join_equality",
                address,
                self.read_port(e.left, uses),
                self.read_port(e.right, uses),
            )
            for e in self.plan.relationship_matches
            if e.join is join.ref
        )
        predicate = None if join.on is None else self.expression(join.on, uses)
        outputs = []
        for i, reference in enumerate(join.outputs):
            original = self.join_ports[reference]
            read = self.read_port(original.source, uses)
            field = original.field
            logical = (
                field.evidence.resolved_type.name,
                field.effective_nullability.value,
            )
            value = self.add("join_value", address, read, logical)
            port = self.add("port", address, i, field.evidence.name, value, logical)
            self.ports[reference] = port
            outputs.append(port)
        actual = join.source.source
        if type(actual) is ProjectIRBinaryJoinOccurrence:
            law = "relationship"
            positions = tuple(f.field_position for f in _source_slice_fields(actual))
        elif type(actual) is ProjectCurrentBinaryJoin:
            law = "current"
            candidates = actual.condition.environment.source_candidates
            positions = tuple(
                i
                for i, (binding, _) in enumerate(actual.left_fields)
                if len(candidates) == 1 and binding is candidates[0]
            )
        else:
            raise CompiledError("COMPILED_RETAINED_JOIN")
        layout = self.layout(address, len(outputs))
        self.finish(
            address,
            self.declaration(definition.entry.owner),
            join.position,
            join.kind.value,
            law,
            positions,
            uses,
            equalities,
            predicate,
            tuple(outputs),
            (
                layout[0],
                layout[1],
                tuple(f"s{i}" for i in range(len(uses))),
                False,
                layout[4],
            ),
        )
        self.references[join.ref] = address
        self.join_refs[id(join.ref)] = address
        return address

    def logical_set(self, definition, original):
        address = self.reserve("set")
        operands = tuple(
            next(o for o in self.plan.set_operands if o.ref is r)
            for r in original.operands
        )
        uses = self.inputs(address, tuple(self.terminals[o.producer] for o in operands))
        columns = tuple(
            next(c for c in self.plan.set_columns if c.ref is r)
            for r in original.columns
        )
        ports = []
        for column in columns:
            values = tuple(
                self.add(
                    "read",
                    self.records[use].get("ports")[column.position],
                    use,
                    "value",
                )
                for use in uses
            )
            field = column.field
            logical = (
                field.evidence.resolved_type.name,
                field.effective_nullability.value,
            )
            value = self.add("set_value", address, values, logical)
            export = definition.exports[column.position]
            port = self.add(
                "port", address, column.position, export.identity.name, value, logical
            )
            ports.append(port)
            self.ports[column.output] = port
            self.ports[export.ref] = port
        layout = self.layout(address, len(ports))
        self.finish(
            address,
            self.declaration(definition.entry.owner),
            original.kind.value,
            original.quantifier.value,
            uses,
            tuple(ports),
            (
                layout[0],
                layout[1],
                tuple(f"s{i}" for i in range(len(uses))),
                False,
                layout[4],
            ),
        )
        self.references[original.ref] = address
        return address

    def logical_aggregate(self, definition, block, previous):
        from pietto._project.project_joined_aggregation import (
            ProjectConcreteJoinedAggregation,
        )
        from pietto._project.project_multifact import (
            ProjectCurrentMultiFactRegion,
            ProjectMultiFactConcreteRegion,
        )

        original = next(a for a in self.plan.aggregations if a.block is block.ref)
        address = self.reserve("aggregate")
        (use,) = self.inputs(address, (previous,))
        for reference, port in zip(
            block.inputs, self.records[use].get("ports"), strict=True
        ):
            self.ports[reference] = port
        keys, values, ports = [], [], []
        for key in (k for k in self.plan.group_keys if k.aggregation is original.ref):
            value = self.read_port(key.input, (use,))
            logical = self.records[self.records[value].get("port")].get("logical")
            keys.append(value)
            port = self.add(
                "port", address, len(ports), f"c{len(ports)}", value, logical
            )
            ports.append(port)
            self.ports[key.result] = port
        for item in (v for v in self.plan.aggregates if v.aggregation is original.ref):
            value = self.add(
                "aggregate_value",
                grouping.function_name(item.source),
                tuple(self.expression(a, (use,)) for a in item.arguments),
                _logical(item.value_type),
            )
            values.append(value)
            port = self.add(
                "port",
                address,
                len(ports),
                f"c{len(ports)}",
                value,
                _logical(item.value_type),
            )
            ports.append(port)
            self.ports[item.result] = port
        for reference, port in zip(block.exports, ports, strict=True):
            self.ports[reference] = port
        authority = original.authority.source
        law = None
        if type(authority) is ProjectConcreteJoinedAggregation:
            region = authority.input_filter.joined_semantics.multifact_region
            if type(region) not in (
                ProjectCurrentMultiFactRegion,
                ProjectMultiFactConcreteRegion,
            ):
                raise CompiledError("COMPILED_RETAINED_AGGREGATE_RISK")
            law = (
                "current"
                if type(region) is ProjectCurrentMultiFactRegion
                else "relationship"
            )
        self.finish(
            address,
            self.declaration(definition.entry.owner),
            use,
            previous,
            original.mode.value,
            law,
            tuple(keys),
            tuple(values),
            tuple(ports),
            self.layout(address, len(ports)),
        )
        self.references[block.ref] = address
        return address

    def logical_window(self, definition, block, previous):
        address = self.reserve("window")
        (use,) = self.inputs(address, (previous,))
        incoming = self.records[use].get("ports")
        for reference, port in zip(block.inputs, incoming, strict=True):
            self.ports[reference] = port
        values, ports, definitions, named = [], [], [], {}
        for old in incoming:
            value = self.add("read", old, use, "value")
            logical = self.records[old].get("logical")
            ports.append(
                self.add("port", address, len(ports), f"c{len(ports)}", value, logical)
            )
            values.append(value)
        for original in (w for w in self.plan.windows if w.block is block.ref):
            policy = next(
                p for p in self.plan.window_policies if p.ref is original.policy
            )
            actual_uses = tuple(
                u for u in self.plan.window_uses if u.window is original.ref
            )
            partitions = tuple(
                self.read_port(u.input, (use,))
                for u in actual_uses
                if u.role.value == "window_partition"
            )
            orders = tuple(
                (
                    self.read_port(u.input, (use,)),
                    policy.orders[u.role_position].effective_direction,
                    None,
                )
                for u in actual_uses
                if u.role.value == "window_order"
            )
            frame = None
            if (
                policy.specification.frame is not None
                and policy.specification.frame.resolved.unit is not None
            ):
                resolved = policy.specification.frame.resolved
                frame = (
                    resolved.unit.value,
                    (
                        resolved.start.kind.value,
                        None
                        if resolved.start.offset is None
                        else self.literals[id(resolved.start.offset)],
                    ),
                    (
                        resolved.end.kind.value,
                        None
                        if resolved.end.offset is None
                        else self.literals[id(resolved.end.offset)],
                    ),
                    None if resolved.exclusion is None else resolved.exclusion.value,
                )
            named_ref = None
            if policy.named_use is not None:
                declared = policy.named_use.composed.base.target_declaration
                key = (
                    id(declared),
                    tuple(self.records[v].get("port") for v in partitions),
                    tuple(
                        (self.records[v].get("port"), direction, nulls)
                        for v, direction, nulls in orders
                    ),
                    frame,
                )
                if key not in named:
                    spec = self.add("window_spec", partitions, orders, frame, None)
                    named[key] = self.add(
                        "window_definition",
                        len(definitions),
                        f"w{len(definitions)}",
                        spec,
                    )
                    definitions.append(named[key])
                named_ref = named[key]
            specification = self.add(
                "window_spec", partitions, orders, frame, named_ref
            )
            arguments = []
            for argument in (
                a for a in self.plan.window_arguments if a.window is original.ref
            ):
                if argument.use is None:
                    value = self.literals[id(argument.expression)]
                else:
                    input_use = next(u for u in actual_uses if u.ref is argument.use)
                    value = self.read_port(input_use.input, (use,))
                arguments.append((argument.role.value, value))
            value = self.add(
                "window_value",
                windowing.function_identity(original),
                tuple(arguments),
                specification,
                incoming,
                original.selected is not None,
                _logical(original.value_type),
            )
            port = self.add(
                "port",
                address,
                len(ports),
                f"c{len(ports)}",
                value,
                _logical(original.value_type),
            )
            ports.append(port)
            values.append(value)
            self.ports[original.result] = port
        for reference, port in zip(block.exports, ports, strict=True):
            self.ports[reference] = port
        self.finish(
            address,
            self.declaration(definition.entry.owner),
            use,
            previous,
            tuple(definitions),
            tuple(values),
            tuple(ports),
            self.layout(address, len(ports)),
        )
        self.references[block.ref] = address
        return address

    def logical_results(self, definition, boundaries, previous):
        address = self.reserve("result")
        (use,) = self.inputs(address, (previous,))
        incoming = self.records[use].get("ports")
        for boundary in boundaries:
            for references in (boundary.inputs, boundary.outputs):
                for reference, port in zip(references, incoming, strict=True):
                    self.ports[reference] = port
        ordering = []
        for order in self.plan.orders:
            if not any(order.boundary is b.ref for b in boundaries):
                continue
            for ref in order.items:
                item = next(i for i in self.plan.order_items if i.ref is ref)
                expression = next(
                    e for e in self.plan.order_expressions if e.ref is item.expression
                )
                if expression.use is None:
                    raise CompiledError("COMPILED_RETAINED_ORDER")
                input_use = next(
                    u for u in self.plan.order_uses if u.ref is expression.use
                )
                if input_use.requirement is not None or len(input_use.ports) != 1:
                    raise CompiledError("COMPILED_RETAINED_ORDER")
                ordering.append(
                    (
                        self.read_port(input_use.ports[0], (use,)),
                        item.source.direction.value,
                    )
                )
        values, ports = [], []
        for i, (original, source) in enumerate(
            zip(definition.exports, incoming, strict=True)
        ):
            value = self.add("read", source, use, "value")
            logical = self.records[source].get("logical")
            port = self.add("port", address, i, original.identity.name, value, logical)
            values.append(value)
            ports.append(port)
            self.ports[original.ref] = port
        limits = tuple(
            v
            for v in self.plan.result_limits
            if any(v.boundary is b.ref for b in boundaries)
        )
        if len(limits) > 1:
            raise CompiledError("COMPILED_RETAINED_LIMIT")
        limit = limits[0] if limits else None
        self.finish(
            address,
            self.declaration(definition.entry.owner),
            previous,
            tuple(values),
            any(b.kind.value == "distinct" for b in boundaries),
            tuple(ordering),
            None if limit is None else limit.value,
            None if limit is None else self.literals[id(limit.literal)],
            tuple(ports),
            self.layout(address, len(ports)),
        )
        for boundary in boundaries:
            self.references[boundary.ref] = address
        return address

    def run(self):
        self.source_inputs()
        self.literal_records(plan=self.plan)
        for definition in self.plan.bindings.definitions:
            if definition.ref in self.terminals:
                continue
            set_bodies = tuple(
                v for v in self.plan.set_bodies if v.definition is definition.ref
            )
            if set_bodies:
                if len(set_bodies) != 1:
                    raise CompiledError("COMPILED_RETAINED_SET")
                self.terminals[definition.ref] = self.logical_set(
                    definition, set_bodies[0]
                )
                continue
            previous = None
            for join in self.plan.joins:
                if join.definition is definition.ref:
                    previous = self.logical_join(definition, join)
            if previous is None:
                inputs = tuple(
                    u for u in self.plan.input_uses if u.consumer is definition.ref
                )
                if len(inputs) != 1:
                    raise CompiledError("COMPILED_RETAINED_INPUT")
                previous = self.terminals[inputs[0].producer]
                for port in inputs[0].ports:
                    self.aliases[port.ref] = port.producer_port
            blocks = tuple(
                b for b in self.plan.blocks if b.definition is definition.ref
            )
            for block in blocks:
                if block.kind.value == "aggregate":
                    previous = self.logical_aggregate(definition, block, previous)
                    continue
                if block.kind.value == "window":
                    previous = self.logical_window(definition, block, previous)
                    continue
                address = self.reserve("row")
                uses = self.inputs(address, (previous,))
                for reference, port in zip(
                    block.inputs, self.records[uses[0]].get("ports"), strict=True
                ):
                    self.ports[reference] = port
                values, ports = [], []
                projection = {
                    p.export: p for p in self.plan.projections if p.block is block.ref
                }
                result_projections = {
                    p.export: p
                    for p in (
                        *self.plan.aggregate_projections,
                        *self.plan.window_projections,
                    )
                    if p.block is block.ref
                }
                lets = {
                    p.port: p for p in self.plan.let_values if p.site.block is block.ref
                }
                for i, reference in enumerate(block.exports):
                    if reference in projection:
                        original = projection[reference]
                        value = self.expression(original.expression, uses)
                        logical = _logical(
                            self.expressions[original.expression].value_type
                        )
                        label = self.original_ports[reference].identity.name
                    elif reference in result_projections:
                        original = result_projections[reference]
                        value = self.read_port(original.input, uses)
                        logical = self.records[self.records[value].get("port")].get(
                            "logical"
                        )
                        label = self.original_ports[reference].identity.name
                    elif reference in lets:
                        original = lets[reference]
                        value = self.expression(original.expression, uses)
                        logical = _logical(
                            self.expressions[original.expression].value_type
                        )
                        label = f"c{i}"
                    else:
                        value = self.read_port(self.stage_ports[reference].source, uses)
                        logical = self.records[self.records[value].get("port")].get(
                            "logical"
                        )
                        label = f"c{i}"
                    values.append(value)
                    port = self.add("port", address, i, label, value, logical)
                    ports.append(port)
                    self.ports[reference] = port
                filters = tuple(
                    f for f in self.plan.filters if f.site.block is block.ref
                )
                predicate = (
                    None if not filters else self.expression(filters[0].predicate, uses)
                )
                self.finish(
                    address,
                    self.declaration(definition.entry.owner),
                    uses[0],
                    previous,
                    block.kind.value,
                    tuple(values),
                    predicate,
                    tuple(ports),
                    self.layout(address, len(ports)),
                )
                self.references[block.ref] = address
                previous = address
            boundaries = tuple(
                b for b in self.plan.result_boundaries if b.definition is definition.ref
            )
            if boundaries:
                previous = self.logical_results(definition, boundaries, previous)
            self.terminals[definition.ref] = previous
            final_ports = tuple(
                r.address
                for r in self.records.values()
                if r is not None
                and r.address.kind == "port"
                and r.get("owner") == previous
            )
            for old, port in zip(definition.exports, final_ports, strict=True):
                self.ports[old.ref] = port
        selected = next(
            d
            for d in self.plan.bindings.definitions
            if d.entry.owner is self.checked.selected_owner
        )
        terminal = self.terminals[selected.ref]
        ports = tuple(self.ports[p.ref] for p in selected.exports)
        requests = self.request_records(plan=self.plan)
        query = self.add(
            "entry",
            self.declaration(selected.entry.owner),
            terminal,
            ports,
            requests,
            (),
        )
        members = tuple(
            (
                name,
                tuple(
                    r
                    for r in self.records.values()
                    if r.address.kind in MEMBER_KINDS[name]
                ),
            )
            for name in MEMBERS
        )
        return Description(self.compatibility, self.producer_identity, query, members)


def build_compiled(artifact, *, guarded=None, refinement=None) -> CompiledBuild:
    """Export selected execution plus every actual retained request owner."""
    from pietto._project.project_sql_emission import EmissionArtifact
    from pietto._project.project_guard_preparation import GuardedArtifact
    from pietto._project.project_execution_template import BindingError
    from pietto._project.project_sql_plan import build_project_sql_plan
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan
    from pietto._project.project_sql_plan_literals import ProjectSQLLiteralPolicy
    from pietto._project.project_compiled_verification import verify_export

    if type(artifact) not in (EmissionArtifact, GuardedArtifact):
        raise BindingError("BINDING_ARTIFACT")
    primary = _Export(artifact, guarded, refinement)
    description = primary.run()
    verify_export(description, artifact, guarded=guarded, refinement=refinement)
    completed = artifact.request.verification.completed
    missing = tuple(
        owner
        for owner in completed.effective_outputs.schedule
        if any(
            request.owner is owner and id(request) not in primary.requests
            for request in completed.single_match_requests
        )
    )
    components = [(primary, description)]
    for owner in missing:
        verification = artifact.request.verification
        plan = build_project_sql_plan(
            completed,
            verification.analysis_bundle,
            owner,
            literal_policy=ProjectSQLLiteralPolicy.PRESERVE_LITERALS,
        )
        checked = verify_project_sql_plan(
            plan,
            completed,
            verification.analysis_bundle,
            owner,
            literal_policy=ProjectSQLLiteralPolicy.PRESERVE_LITERALS,
        )
        exporter = _LogicalExport(artifact, guarded, checked)
        child = exporter.run()
        from pietto._project.project_compiled_verification import verify_logical_export

        verify_logical_export(child, checked, exporter.references)
        components.append((exporter, child))
    if len(components) > 1:
        description = merge_retained_components(
            components, completed.single_match_requests
        )
    verify_description(description)
    raw = encode(description)
    pin = content_pin(raw)
    root = CompiledProjectInput(
        description, pin, description.producer, description.compatibility
    )
    return CompiledBuild(
        root, raw, pin, description.producer, description.compatibility
    )


def merge_retained_components(components, requests):
    """Merge exact shared declarations/uses, preserving each retained sibling.

    Each component was independently checked against its actual source plan.
    Only the selected component contributes transport slots, target premises,
    native layout and emitted requirements. Retained components supply typed
    derivation inputs and requests, never another executable statement.
    """
    from pietto._project.project_compiled_verification import RELATIONS

    global_keys, global_records, counts, projections = {}, {}, {}, []
    request_ids, retained = {}, []
    ignored = {
        "entry",
        "target",
        "policy",
        "output",
        "slot",
        "native_use",
        "provider",
        "premise",
        "expression_context",
        "requirement",
        "requirement_origin",
        "requirement_link",
    }
    for component_position, (exporter, description) in enumerate(components):
        records = {r.address: r for r in description.records}
        keys = {}
        for record in records.values():
            if record.address.kind == "declaration":
                keys[record.address] = ("declaration", record.values)
        for record in records.values():
            if record.address.kind == "source":
                keys[record.address] = ("source", keys[record.get("declaration")])
        local_units = {}
        for record in records.values():
            if record.address.kind in RELATIONS - {"source"}:
                owner = keys[record.get("owner")]
                ordinal = local_units.get(owner, 0)
                local_units[owner] = ordinal + 1
                keys[record.address] = ("unit", owner, ordinal, record.address.kind)
        for record in records.values():
            kind = record.address.kind
            if kind == "field":
                keys[record.address] = (
                    "field",
                    keys[record.get("source")],
                    record.get("ordinal"),
                )
            elif kind == "port":
                keys[record.address] = (
                    "port",
                    keys[record.get("owner")],
                    record.get("ordinal"),
                )
            elif kind == "use":
                keys[record.address] = (
                    "use",
                    keys[record.get("consumer")],
                    record.get("ordinal"),
                )
            elif kind == "source_unique":
                keys[record.address] = (
                    "source_unique",
                    keys[record.get("source")],
                    keys[record.get("shape")],
                    record.get("position"),
                )
        for identity, address in exporter.literals.items():
            keys[address] = ("literal", identity)
            keys[records[address].get("site")] = ("site", identity)
        for name, mapping in (
            ("request", exporter.requests),
            ("match_use", exporter.match_uses),
            ("match_path", exporter.paths),
            ("match_step", exporter.steps),
        ):
            for identity, address in mapping.items():
                keys[address] = (name, identity)

        def child_references(value, path=()):
            if type(value) is Address:
                yield value, path
            elif type(value) is tuple:
                for i, item in enumerate(value):
                    yield from child_references(item, (*path, i))

        # An occurrence is identified by its actual owning relation and ordered
        # field path. Equal payloads never merge different occurrences.
        for record in records.values():
            if record.address.kind not in RELATIONS:
                continue
            pending = [(record.address, keys[record.address])]
            visited = set()
            while pending:
                address, parent = pending.pop()
                if address in visited:
                    continue
                visited.add(address)
                current = records[address]
                for name, value in zip(
                    FIELDS[address.kind], current.values, strict=True
                ):
                    for child, path in child_references(value):
                        if child not in keys:
                            keys[child] = ("child", parent, name, path, child.kind)
                        if child not in visited:
                            pending.append((child, keys[child]))
        kept = tuple(
            r
            for r in records.values()
            if component_position == 0 or r.address.kind not in ignored
        )
        translated = {}
        new = []
        for record in kept:
            key = keys.get(
                record.address, ("selected", component_position, record.address)
            )
            if key in global_keys:
                translated[record.address] = global_keys[key]
                continue
            kind = record.address.kind
            address = Address(kind, counts.get(kind, 0))
            counts[kind] = address.position + 1
            global_keys[key] = address
            translated[record.address] = address
            new.append(record.address)

        def remap(value):
            if type(value) is Address:
                if value not in translated:
                    raise CompiledError("COMPILED_RETAINED_REFERENCE")
                return translated[value]
            if type(value) is tuple:
                return tuple(remap(item) for item in value)
            return value

        for record in kept:
            address = translated[record.address]
            values = list(remap(record.values))
            if record.address.kind == "site":
                values[FIELDS["site"].index("ordinal")] = address.position
            if record.address in new:
                if record.address.kind in RELATIONS - {"source"} and component_position:
                    layout = list(values[-1])
                    layout[-1] = sum(
                        a.kind in RELATIONS - {"source"} for a in global_records
                    )
                    values[-1] = tuple(layout)
                global_records[address] = Record(address, tuple(values))
            else:
                expected = global_records[address]
                # Native names belong to the selected view. Logical input/use/
                # output correspondence is checked in full after reference mapping.
                if address.kind in RELATIONS - {"source"}:
                    values[-1] = expected.values[-1]
                elif address.kind == "site":
                    values[-2:] = expected.values[-2:]
                elif address.kind == "port" and component_position:
                    # Wire port labels in the execution view are its native
                    # intermediate labels; ordered resolved identities stay exact.
                    values[2] = expected.values[2]
                elif address.kind == "source" and component_position:
                    # A retained logical source does not replace the selected
                    # source's actual physical mapping.
                    values[1:3] = expected.values[1:3]
                elif address.kind == "field" and component_position:
                    values[3] = expected.values[3]
                    values[5] = expected.values[5]
                if tuple(values) != expected.values:
                    raise CompiledError("COMPILED_RETAINED_SHARED_INPUT")
        for identity, address in exporter.requests.items():
            mapped = translated[address]
            if identity in request_ids and request_ids[identity] != mapped:
                raise CompiledError("COMPILED_RETAINED_REQUEST_ALIAS")
            request_ids[identity] = mapped
        terminal = records[description.query].get("terminal")
        if component_position:
            retained.append(translated[terminal])
        projections.append(translated)
    primary = components[0][1]
    selected = global_records[projections[0][primary.query]]
    values = list(selected.values)
    values[FIELDS["entry"].index("requests")] = tuple(
        request_ids[id(request)] for request in requests
    )
    values[FIELDS["entry"].index("retained")] = tuple(retained)
    global_records[selected.address] = Record(selected.address, tuple(values))
    members = tuple(
        (
            name,
            tuple(
                r
                for r in global_records.values()
                if r.address.kind in MEMBER_KINDS[name]
            ),
        )
        for name in MEMBERS
    )
    result = Description(
        primary.compatibility, primary.producer, selected.address, members
    )
    verify_description(result)
    from pietto._project.project_compiled_verification import verify_retained_export

    verify_retained_export(
        result, components[0][1], components[0][0].artifact, requests
    )
    return result
