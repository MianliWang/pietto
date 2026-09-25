"""Checked explicit projection of retained result facts, with no reconstruction."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

from pietto import ast_nodes as ast
from pietto._project import project_result_contract_pure_boundary as pure
from pietto._project.project_result_contract import ResultError, verify_result_contract
from pietto._project.project_ir_properties import ProjectIRProvidedRelationOrdering
from pietto._project.project_final_outputs import ProjectRelationOrdering

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class ResultContractExport:
    contract: Any = field(repr=False)
    verification: Any = field(repr=False)
    view: pure.ContractView

    @property
    def canonical_bytes(self):
        return self.view.canonical_bytes


class _Projection:
    def __init__(self, checked, limits):
        self.checked = checked
        self.budget = pure.Budget(limits)
        self.types: list[dict[str, Any]] = []
        self.type_keys = []

    def obj(self, **values):
        self.budget.value(values)
        for key, value in values.items():
            self.budget.value(key)
            if value is None or type(value) in (str, int, bool):
                self.budget.value(value)
        return values

    def sequence(self, values):
        pure.require(type(values) in (tuple, list), "DOCUMENT")
        pure.require(len(values) <= self.budget.limits.values, "LIMIT")
        return values

    def location(self, value):
        if value is None:
            return None
        return self.obj(
            path=value.path,
            line=value.line,
            column=value.column,
            end_line=value.end_line,
            end_column=value.end_column,
        )

    def nominal(self, value):
        return self.obj(
            module=value.module_path,
            namespace=value.namespace.value,
            kind=value.declaration_kind.value,
            name=value.declared_name,
        )

    def owner(self, value):
        return self.obj(
            identity=self.nominal(value.identity),
            module_position=value.module_position,
            declaration_position=value.declaration_position,
        )

    def coordinate(self, value):
        if value is None:
            return None
        self.budget.reference()
        return self.obj(kind=value.kind.value, position=value.position)

    def expression(self, value, depth=0):
        pure.require(depth <= self.budget.limits.depth, "LIMIT")
        span = self.location(value.span)
        if type(value) is ast.LiteralExpr:
            raw = value.value
            if type(raw) is int:
                kind, item = "Int", str(raw)
            elif type(raw) is float:
                pure.require(math.isfinite(raw), "NUMBER")
                kind, item = "Float", raw.hex()
            elif type(raw) is bool:
                kind, item = "Bool", raw
            elif type(raw) is str:
                kind, item = "Text", raw
            elif raw is None:
                kind, item = "Null", None
            else:
                raise pure.ContractDocumentError("TAG")
            return self.obj(tag="literal", kind=kind, value=item, location=span)
        if type(value) is ast.NameExpr:
            return self.obj(tag="name", name=value.name, location=span)
        if type(value) is ast.DottedNameExpr:
            parts = []
            for item in self.sequence(value.parts):
                self.budget.value(item)
                parts.append(item)
            return self.obj(tag="dotted", parts=parts, location=span)
        if type(value) is ast.CallExpr:
            return self.obj(
                tag="call",
                callee=self.expression(value.callee, depth + 1),
                arguments=[
                    self.expression(v, depth + 1)
                    for v in self.sequence(value.arguments)
                ],
                location=span,
            )
        if type(value) is ast.UnaryExpr:
            return self.obj(
                tag="unary",
                operator=value.operator,
                operand=self.expression(value.operand, depth + 1),
                location=span,
            )
        if type(value) in (ast.BinaryExpr, ast.ComparisonExpr):
            return self.obj(
                tag="binary" if type(value) is ast.BinaryExpr else "comparison",
                operator=value.operator,
                left=self.expression(value.left, depth + 1),
                right=self.expression(value.right, depth + 1),
                location=span,
            )
        if type(value) is ast.BetweenExpr:
            return self.obj(
                tag="between",
                value=self.expression(value.value, depth + 1),
                lower=self.expression(value.lower, depth + 1),
                upper=self.expression(value.upper, depth + 1),
                location=span,
            )
        if type(value) is ast.IsNullExpr:
            return self.obj(
                tag="is_null",
                value=self.expression(value.value, depth + 1),
                negated=value.negated,
                location=span,
            )
        raise pure.ContractDocumentError("TAG")

    def declared(self, value):
        if value is None:
            return None
        pure.require(type(value) is ast.TypeExpr, "TAG")
        return self.obj(
            name=value.name,
            arguments=[
                self.obj(name=a.name, value=self.expression(a.value))
                for a in self.sequence(value.arguments)
            ],
            nullability=value.nullability.value,
            location=self.location(value.span),
        )

    def symbol(self, value):
        if value is None:
            return None
        return self.obj(
            identity=self.obj(
                module=value.path,
                namespace=value.namespace.value,
                kind=value.kind.value,
                name=value.name,
            ),
            location=self.location(value.location),
        )

    def output(self, value):
        occurrence = value.occurrence
        return self.obj(
            kind="relation_output",
            position=occurrence.ref.position,
            producer=occurrence.producer.ref.position,
            owner=self.owner(occurrence.producer.anchor.identity),
            field_count=len(value.row_shape.fields),
        )

    def import_site(self, value):
        b = value.binding_identity
        return self.obj(
            module=b.owning_module_path,
            namespace=b.namespace.value,
            kind=b.declaration_kind.value,
            local_name=b.local_binding_name,
            target_module=value.target_module_path,
            exported_name=value.exported_name,
            statement=value.module_statement_position,
            item=value.item_position,
        )

    def origin(self, value):
        hops = []
        for hop in self.sequence(value.hops):
            facade = hop.facade_occurrence
            hops.append(
                {
                    "import": self.import_site(hop.import_occurrence),
                    "facade": self.obj(
                        module=facade.owning_module_path,
                        namespace=facade.namespace.value,
                        kind=facade.declaration_kind.value,
                        name=facade.exposed_name,
                        statement=facade.module_statement_position,
                        item=facade.item_position,
                    ),
                    "origin": hop.facade_origin.value,
                    "target": self.nominal(hop.target_identity),
                }
            )
            self.budget.value(hops[-1])
        result = self.obj(
            module=value.owning_module_path,
            namespace=value.namespace.value,
            kind=value.declaration_kind.value,
            local_name=value.local_name,
            target=self.owner(value.target_occurrence),
            local=None
            if value.local_occurrence is None
            else self.owner(value.local_occurrence),
            hops=hops,
        )
        result["import"] = (
            None
            if value.import_occurrence is None
            else self.import_site(value.import_occurrence)
        )
        return result

    def reference(self, value):
        return self.obj(
            owner=self.owner(value.owner),
            role=value.role.value,
            position=value.member_position,
        )

    def provenance_paths(self, value):
        return self.obj(
            reference=self.reference(value.reference),
            paths=[
                self.obj(
                    hops=[
                        self.obj(
                            reference=self.reference(hop.reference),
                            target=self.owner(hop.target),
                            origin=self.origin(hop.origin),
                        )
                        for hop in self.sequence(path.hops)
                    ],
                    builtin=path.terminal_builtin,
                    terminal_reference=None
                    if path.terminal_reference is None
                    else self.reference(path.terminal_reference),
                    terminal_target=None
                    if path.terminal_target is None
                    else self.owner(path.terminal_target),
                )
                for path in self.sequence(value.paths)
            ],
        )

    def value_type(self, value):
        definition = value.resolved_type.definition
        nominal = None
        if definition is not None:
            occurrences = tuple(
                o
                for catalog in self.checked.completed.semantic_result.module_catalogs.catalogs
                for o in catalog.occurrences
                if o.definition is definition
            )
            pure.require(len(occurrences) == 1, "REFERENCE")
            nominal = self.type_ref(occurrences[0].identity)
        return self.obj(
            kind=value.kind.value,
            type_kind=value.resolved_type.kind.value,
            name=value.resolved_type.name,
            nullability=value.nullability.value,
            declaration=nominal,
        )

    def prepared_order(self, item):
        plan = self.checked.plan
        keys = tuple(k for k in plan.order_items if k.source is item)
        pure.require(len(keys) == 1, "REFERENCE")
        key = keys[0]
        uses = []
        for ref in self.sequence(key.uses):
            matches = tuple(u for u in plan.order_uses if u.ref is ref)
            pure.require(len(matches) == 1, "REFERENCE")
            use = matches[0]
            uses.append(
                self.obj(
                    position=use.position,
                    expression=self.expression(use.source.expression),
                    value_type=self.value_type(use.source.value_type),
                    scope=self.coordinate(use.scope),
                    ports=[self.coordinate(v) for v in self.sequence(use.ports)],
                    requirement=self.coordinate(use.requirement),
                )
            )
        return self.obj(
            order=self.coordinate(key.ordering),
            item=self.coordinate(key.ref),
            expression=self.coordinate(key.expression),
            value=self.coordinate(key.value),
            value_type=self.value_type(item.value_type),
            uses=uses,
        )

    def type_ref(self, identity):
        catalogs = self.checked.completed.semantic_result.module_catalogs
        occurrences = catalogs.find_identity(identity)
        pure.require(len(occurrences) == 1, "REFERENCE")
        occurrence = occurrences[0]
        key = (occurrence.module_position, occurrence.declaration_position)
        if key not in self.type_keys:
            position = len(self.types)
            self.type_keys.append(key)
            definition = occurrence.definition
            pure.require(type(definition) in (ast.TypeDef, ast.EnumDef), "TAG")
            self.types.append(
                self.obj(
                    id=position,
                    owner=self.owner(occurrence),
                    base=self.declared(definition.base)
                    if type(definition) is ast.TypeDef
                    else None,
                    ensures=[
                        self.expression(e.expression)
                        for e in self.sequence(definition.ensures)
                    ]
                    if type(definition) is ast.TypeDef
                    else [],
                    members=list(self.sequence(definition.members))
                    if type(definition) is ast.EnumDef
                    else [],
                )
            )
        self.budget.reference()
        return self.obj(kind="type_declaration", index=self.type_keys.index(key))

    def resolution(self, declared):
        if declared is None:
            return None
        semantic = self.checked.completed.semantic_result
        resolutions = tuple(
            r
            for e in semantic.module_type_source_resolutions.environments
            for r in e.type_resolutions
            if r.reference.type_expr is declared
        )
        pure.require(len(resolutions) <= 1, "REFERENCE")
        if not resolutions:
            return None
        resolution = resolutions[0]
        origins = []
        relevant = [resolution]
        for identity in self.sequence(resolution.alias_chain):
            matches = tuple(
                r
                for e in semantic.module_type_source_resolutions.environments
                for r in e.type_resolutions
                if r.reference.owner.identity == identity
                and r.reference.role.value == "type_alias_base"
            )
            pure.require(len(matches) == 1, "REFERENCE")
            relevant.append(matches[0])
        for current in relevant:
            reference = current.reference
            for provenance in semantic.module_attribution_facts.reference_provenance:
                if (
                    provenance.reference.owner.identity == reference.owner.identity
                    and provenance.reference.member_position
                    == reference.member_position
                    and provenance.reference.role.value == reference.role.value
                ):
                    origins.append(self.provenance_paths(provenance))
        return self.obj(
            direct_kind=resolution.direct_kind.value,
            canonical_kind=resolution.canonical_kind.value,
            canonical_name=resolution.canonical_name,
            aliases=[self.type_ref(i) for i in self.sequence(resolution.alias_chain)],
            target=None
            if resolution.canonical_target_identity is None
            else self.type_ref(resolution.canonical_target_identity),
            origins=origins,
        )

    def leaf(self, leaf):
        port = leaf.port
        evidence = port.field.evidence
        provenance = leaf.provenance
        identity = port.identity
        return self.obj(
            ordinal=leaf.ordinal,
            label=leaf.label,
            identity=self.obj(
                owner=self.owner(identity.owner),
                kind=identity.kind.value,
                position=identity.field_position,
                name=identity.name,
            ),
            port=self.obj(
                coordinate=self.coordinate(port.ref),
                owner=self.coordinate(port.owner),
                producer=self.coordinate(port.producer_port),
            ),
            output=self.output(port.field.output),
            position=port.field.field_position,
            declared=self.declared(leaf.shape.declared),
            canonical=self.obj(
                kind=leaf.shape.canonical.kind.value,
                name=leaf.shape.canonical.name,
                symbol=self.symbol(leaf.shape.canonical.symbol),
            ),
            nullability=leaf.nullability.value,
            declared_nullability=evidence.nullability.value,
            role=evidence.result_role.value,
            provenance=None
            if provenance is None
            else self.obj(
                kind=provenance.kind.value,
                symbol=self.symbol(provenance.symbol),
                location=self.location(provenance.location),
            ),
            type_resolution=self.resolution(leaf.shape.declared),
        )

    def ordering(self, value):
        if value is None:
            return None
        pure.require(
            type(value) in (ProjectIRProvidedRelationOrdering, ProjectRelationOrdering),
            "TAG",
        )
        provided = type(value) is ProjectIRProvidedRelationOrdering
        owner = value.evidence.owner if provided else value.owner
        retained = tuple(
            o.source for o in self.checked.plan.orders if o.source.owner is owner
        )
        pure.require(len(retained) == 1, "REFERENCE")
        (prepared,) = retained
        pure.require(len(prepared.items) == len(value.items), "REFERENCE")
        keys = []
        for position, (item, source) in enumerate(
            zip(self.sequence(value.items), prepared.items, strict=True)
        ):
            authored = item if provided else item.item
            pure.require(source.item is authored, "REFERENCE")
            keys.append(
                self.obj(
                    position=position,
                    expression=self.expression(authored.expression),
                    authored_direction=authored.direction,
                    direction=source.direction.value,
                    nulls="unspecified",
                    prepared=self.prepared_order(source),
                )
            )
        return self.obj(
            kind="provided" if provided else "final", owner=self.owner(owner), keys=keys
        )

    def document(self, contract):
        pure.require(len(contract.shape.fields) <= self.budget.limits.fields, "LIMIT")
        leaves = [self.leaf(f) for f in self.sequence(contract.shape.fields)]
        return self.obj(
            format=pure.FORMAT,
            owner=self.owner(contract.owner),
            output=self.output(contract.output),
            field_count=len(leaves),
            fields=leaves,
            types=self.types,
            multiplicity=contract.multiplicity.value,
            ordering=self.ordering(contract.ordering),
        )


def export_result_contract(contract, verification, *, limits=pure.DocumentLimits()):
    """A prior PASS never substitutes for checking the supplied live root now."""
    try:
        verify_result_contract(contract, verification)
    except ResultError:
        raise
    except (ValueError, TypeError, AttributeError, IndexError) as exc:
        raise ResultError("ROOT") from exc
    try:
        document = _Projection(verification, limits).document(contract)
        canonical = pure.encode_document(document, limits=limits)
        view = pure.decode_contract(canonical, limits=limits)
    except pure.ContractDocumentError as exc:
        raise ResultError("DOCUMENT_" + exc.category) from exc
    return ResultContractExport(contract, verification, view)
