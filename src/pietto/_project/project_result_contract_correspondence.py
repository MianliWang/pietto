"""Independent supplied-document comparison against explicit retained authority.

This module deliberately does not import the writer or its projection. Closed
wire validation can be shared; semantic field enumeration cannot.
"""

from __future__ import annotations

from typing import Any

from pietto import ast_nodes as ast
from pietto._project import project_result_contract_pure_boundary as pure
from pietto._project.project_result_contract import ResultError, verify_result_contract
from pietto._project.project_ir_properties import ProjectIRProvidedRelationOrdering
from pietto._project.project_final_outputs import ProjectRelationOrdering

__all__: tuple[str, ...] = ()


def same(actual, expected):
    if actual != expected:
        raise ResultError("CORRESPONDENCE")


class _Correspondence:
    def __init__(self, doc, checked):
        self.doc = doc
        self.checked = checked
        self.seen_types: list[Any] = []

    def location(self, doc, value):
        if value is None:
            same(doc, None)
            return
        same(doc["path"], value.path)
        same(
            (doc["line"], doc["column"], doc["end_line"], doc["end_column"]),
            (value.line, value.column, value.end_line, value.end_column),
        )

    def nominal(self, doc, value):
        same(
            (doc["module"], doc["namespace"], doc["kind"], doc["name"]),
            (
                value.module_path,
                value.namespace,
                value.declaration_kind,
                value.declared_name,
            ),
        )

    def owner(self, doc, value):
        self.nominal(doc["identity"], value.identity)
        same(
            (doc["module_position"], doc["declaration_position"]),
            (value.module_position, value.declaration_position),
        )

    def coordinate(self, doc, value):
        if value is None:
            same(doc, None)
        else:
            same((doc["kind"], doc["position"]), (value.kind, value.position))

    def expression(self, doc, value):
        self.location(doc["location"], value.span)
        if type(value) is ast.LiteralExpr:
            raw = value.value
            kind = {
                int: "Int",
                float: "Float",
                bool: "Bool",
                str: "Text",
                type(None): "Null",
            }.get(type(raw))
            same((doc["tag"], doc["kind"]), ("literal", kind))
            expected = (
                str(raw)
                if type(raw) is int
                else raw.hex()
                if type(raw) is float
                else raw
            )
            same(doc["value"], expected)
        elif type(value) is ast.NameExpr:
            same((doc["tag"], doc["name"]), ("name", value.name))
        elif type(value) is ast.DottedNameExpr:
            same((doc["tag"], tuple(doc["parts"])), ("dotted", value.parts))
        elif type(value) is ast.CallExpr:
            same(doc["tag"], "call")
            self.expression(doc["callee"], value.callee)
            same(len(doc["arguments"]), len(value.arguments))
            for observed, retained in zip(
                doc["arguments"], value.arguments, strict=True
            ):
                self.expression(observed, retained)
        elif type(value) is ast.UnaryExpr:
            same((doc["tag"], doc["operator"]), ("unary", value.operator))
            self.expression(doc["operand"], value.operand)
        elif type(value) in (ast.BinaryExpr, ast.ComparisonExpr):
            same(
                (doc["tag"], doc["operator"]),
                (
                    "binary" if type(value) is ast.BinaryExpr else "comparison",
                    value.operator,
                ),
            )
            self.expression(doc["left"], value.left)
            self.expression(doc["right"], value.right)
        elif type(value) is ast.BetweenExpr:
            same(doc["tag"], "between")
            self.expression(doc["value"], value.value)
            self.expression(doc["lower"], value.lower)
            self.expression(doc["upper"], value.upper)
        elif type(value) is ast.IsNullExpr:
            same((doc["tag"], doc["negated"]), ("is_null", value.negated))
            self.expression(doc["value"], value.value)
        else:
            raise ResultError("CORRESPONDENCE")

    def declared(self, doc, value):
        if value is None:
            same(doc, None)
            return
        same(
            (doc["name"], doc["nullability"], len(doc["arguments"])),
            (value.name, value.nullability, len(value.arguments)),
        )
        self.location(doc["location"], value.span)
        for argument, expected in zip(doc["arguments"], value.arguments, strict=True):
            same(argument["name"], expected.name)
            self.expression(argument["value"], expected.value)

    def symbol(self, doc, value):
        if value is None:
            same(doc, None)
            return
        identity = doc["identity"]
        same(
            (
                identity["module"],
                identity["namespace"],
                identity["kind"],
                identity["name"],
            ),
            (value.path, value.namespace, value.kind, value.name),
        )
        self.location(doc["location"], value.location)

    def output(self, doc, value):
        occurrence = value.occurrence
        same(
            (doc["position"], doc["producer"], doc["field_count"]),
            (
                occurrence.ref.position,
                occurrence.producer.ref.position,
                len(value.row_shape.fields),
            ),
        )
        self.owner(doc["owner"], occurrence.producer.anchor.identity)

    def import_site(self, doc, value):
        binding = value.binding_identity
        same(
            (
                doc["module"],
                doc["namespace"],
                doc["kind"],
                doc["local_name"],
                doc["target_module"],
                doc["exported_name"],
                doc["statement"],
                doc["item"],
            ),
            (
                binding.owning_module_path,
                binding.namespace,
                binding.declaration_kind,
                binding.local_binding_name,
                value.target_module_path,
                value.exported_name,
                value.module_statement_position,
                value.item_position,
            ),
        )

    def origin(self, doc, value):
        same(
            (doc["module"], doc["namespace"], doc["kind"], doc["local_name"]),
            (
                value.owning_module_path,
                value.namespace,
                value.declaration_kind,
                value.local_name,
            ),
        )
        self.owner(doc["target"], value.target_occurrence)
        if value.local_occurrence is None:
            same(doc["local"], None)
            self.import_site(doc["import"], value.import_occurrence)
        else:
            self.owner(doc["local"], value.local_occurrence)
            same(doc["import"], None)
        same(len(doc["hops"]), len(value.hops))
        for hop, expected in zip(doc["hops"], value.hops, strict=True):
            self.import_site(hop["import"], expected.import_occurrence)
            self.nominal(hop["target"], expected.target_identity)
            same(hop["origin"], expected.facade_origin)
            facade = expected.facade_occurrence
            actual = hop["facade"]
            same(
                (
                    actual["module"],
                    actual["namespace"],
                    actual["kind"],
                    actual["name"],
                    actual["statement"],
                    actual["item"],
                ),
                (
                    facade.owning_module_path,
                    facade.namespace,
                    facade.declaration_kind,
                    facade.exposed_name,
                    facade.module_statement_position,
                    facade.item_position,
                ),
            )

    def reference(self, doc, value):
        self.owner(doc["owner"], value.owner)
        same((doc["role"], doc["position"]), (value.role, value.member_position))

    def provenance_paths(self, doc, value):
        self.reference(doc["reference"], value.reference)
        same(len(doc["paths"]), len(value.paths))
        for path, retained in zip(doc["paths"], value.paths, strict=True):
            same(path["builtin"], retained.terminal_builtin)
            if retained.terminal_reference is None:
                same(path["terminal_reference"], None)
            else:
                self.reference(path["terminal_reference"], retained.terminal_reference)
            if retained.terminal_target is None:
                same(path["terminal_target"], None)
            else:
                self.owner(path["terminal_target"], retained.terminal_target)
            same(len(path["hops"]), len(retained.hops))
            for hop, expected in zip(path["hops"], retained.hops, strict=True):
                self.reference(hop["reference"], expected.reference)
                self.owner(hop["target"], expected.target)
                self.origin(hop["origin"], expected.origin)

    def value_type(self, doc, value):
        same(
            (doc["kind"], doc["type_kind"], doc["name"], doc["nullability"]),
            (
                value.kind,
                value.resolved_type.kind,
                value.resolved_type.name,
                value.nullability,
            ),
        )
        definition = value.resolved_type.definition
        if definition is None:
            same(doc["declaration"], None)
        else:
            found = [
                item
                for catalog in self.checked.completed.semantic_result.module_catalogs.catalogs
                for item in catalog.occurrences
                if item.definition is definition
            ]
            same(len(found), 1)
            self.type_ref(doc["declaration"], found[0].identity)

    def prepared_order(self, doc, source):
        plan = self.checked.plan
        keys = [item for item in plan.order_items if item.source is source]
        same(len(keys), 1)
        key = keys[0]
        for name, value in (
            ("order", key.ordering),
            ("item", key.ref),
            ("expression", key.expression),
            ("value", key.value),
        ):
            self.coordinate(doc[name], value)
        retained = [use for use in plan.order_uses if use.item is key.ref]
        same(len(doc["uses"]), len(key.uses))
        same(len(doc["uses"]), len(retained))
        for actual, use in zip(doc["uses"], retained, strict=True):
            same(actual["position"], use.source.position)
            self.expression(actual["expression"], use.source.expression)
            self.value_type(actual["value_type"], use.source.value_type)
            self.coordinate(actual["scope"], use.scope)
            self.coordinate(actual["requirement"], use.requirement)
            same(len(actual["ports"]), len(use.ports))
            for coordinate, expected in zip(actual["ports"], use.ports, strict=True):
                self.coordinate(coordinate, expected)
        self.value_type(doc["value_type"], source.value_type)

    def type_ref(self, ref, identity):
        semantic = self.checked.completed.semantic_result
        candidates = tuple(
            o
            for catalog in semantic.module_catalogs.catalogs
            for o in catalog.occurrences
            if o.identity == identity
        )
        same(len(candidates), 1)
        occurrence = candidates[0]
        if not any(occurrence is item for item in self.seen_types):
            self.seen_types.append(occurrence)
        position = next(
            i for i, item in enumerate(self.seen_types) if item is occurrence
        )
        same(ref["index"], position)
        doc = self.doc["types"][position]
        self.owner(doc["owner"], occurrence)
        definition = occurrence.definition
        if type(definition) is ast.TypeDef:
            self.declared(doc["base"], definition.base)
            same(len(doc["ensures"]), len(definition.ensures))
            for observed, retained in zip(
                doc["ensures"], definition.ensures, strict=True
            ):
                self.expression(observed, retained.expression)
            same(doc["members"], [])
        elif type(definition) is ast.EnumDef:
            same(
                (doc["base"], doc["ensures"], doc["members"]),
                (None, [], list(definition.members)),
            )
        else:
            raise ResultError("CORRESPONDENCE")

    def resolution(self, doc, declared):
        semantic = self.checked.completed.semantic_result
        matches = []
        if declared is not None:
            for environment in semantic.module_type_source_resolutions.environments:
                matches.extend(
                    r
                    for r in environment.type_resolutions
                    if r.reference.type_expr is declared
                )
        if not matches:
            same(doc, None)
            return
        same(len(matches), 1)
        retained = matches[0]
        same(
            (doc["direct_kind"], doc["canonical_kind"], doc["canonical_name"]),
            (retained.direct_kind, retained.canonical_kind, retained.canonical_name),
        )
        same(len(doc["aliases"]), len(retained.alias_chain))
        for ref, identity in zip(doc["aliases"], retained.alias_chain, strict=True):
            self.type_ref(ref, identity)
        if retained.canonical_target_identity is None:
            same(doc["target"], None)
        else:
            self.type_ref(doc["target"], retained.canonical_target_identity)
        references = [retained.reference]
        for alias in retained.alias_chain:
            base = [
                r.reference
                for e in semantic.module_type_source_resolutions.environments
                for r in e.type_resolutions
                if r.reference.role.value == "type_alias_base"
                and r.reference.owner.identity == alias
            ]
            same(len(base), 1)
            references.extend(base)
        expected_origins = []
        for reference in references:
            for provenance in semantic.module_attribution_facts.reference_provenance:
                key = provenance.reference
                if (
                    key.owner.identity == reference.owner.identity
                    and key.role.value == reference.role.value
                    and key.member_position == reference.member_position
                ):
                    expected_origins.append(provenance)
        same(len(doc["origins"]), len(expected_origins))
        for observed, origin in zip(doc["origins"], expected_origins, strict=True):
            self.provenance_paths(observed, origin)

    def fields(self):
        # The denominator comes from upstream plan exports, never the supplied view.
        ports = self.checked.plan.exports
        same(self.doc["field_count"], len(ports))
        same(len(self.doc["fields"]), len(ports))
        for ordinal, port in enumerate(ports):
            doc = self.doc["fields"][ordinal]
            evidence = port.field.evidence
            same(
                (doc["ordinal"], doc["label"], doc["position"]),
                (ordinal, port.identity.name, port.field.field_position),
            )
            identity = doc["identity"]
            self.owner(identity["owner"], port.identity.owner)
            same(
                (identity["kind"], identity["position"], identity["name"]),
                (port.identity.kind, port.identity.field_position, port.identity.name),
            )
            self.coordinate(doc["port"]["coordinate"], port.ref)
            self.coordinate(doc["port"]["owner"], port.owner)
            self.coordinate(doc["port"]["producer"], port.producer_port)
            self.output(doc["output"], port.field.output)
            declared = (
                None if evidence.field_def is None else evidence.field_def.type_expr
            )
            self.declared(doc["declared"], declared)
            same(
                (doc["canonical"]["kind"], doc["canonical"]["name"]),
                (evidence.resolved_type.kind, evidence.resolved_type.name),
            )
            self.symbol(doc["canonical"]["symbol"], evidence.resolved_type.symbol)
            same(
                (doc["nullability"], doc["declared_nullability"], doc["role"]),
                (
                    port.field.effective_nullability,
                    evidence.nullability,
                    evidence.result_role,
                ),
            )
            if evidence.provenance is None:
                same(doc["provenance"], None)
            else:
                same(doc["provenance"]["kind"], evidence.provenance.kind)
                self.symbol(doc["provenance"]["symbol"], evidence.provenance.symbol)
                self.location(
                    doc["provenance"]["location"], evidence.provenance.location
                )
            self.resolution(doc["type_resolution"], declared)

    def ordering(self, retained):
        doc = self.doc["ordering"]
        if retained is None:
            same(doc, None)
            return
        if type(retained) is ProjectIRProvidedRelationOrdering:
            same(doc["kind"], "provided")
            self.owner(doc["owner"], retained.evidence.owner)
            authored = retained.items
        elif type(retained) is ProjectRelationOrdering:
            same(doc["kind"], "final")
            self.owner(doc["owner"], retained.owner)
            authored = tuple(i.item for i in retained.items)
        else:
            raise ResultError("CORRESPONDENCE")
        prepared = [
            order.source
            for order in self.checked.plan.orders
            if order.source.owner is self.checked.selected_owner
        ]
        same(len(prepared), 1)
        same(len(prepared[0].items), len(authored))
        same(len(doc["keys"]), len(authored))
        for ordinal, item in enumerate(authored):
            key = doc["keys"][ordinal]
            same(
                (
                    key["position"],
                    key["authored_direction"],
                    key["direction"],
                    key["nulls"],
                ),
                (ordinal, item.direction, item.direction or "asc", "unspecified"),
            )
            self.expression(key["expression"], item.expression)
            self.prepared_order(key["prepared"], prepared[0].items[ordinal])


def verify_contract_correspondence(view, contract, verification):
    try:
        verify_result_contract(contract, verification)
    except ResultError:
        raise
    except (ValueError, TypeError, AttributeError, IndexError) as exc:
        raise ResultError("ROOT") from exc
    if type(view) is not pure.ContractView:
        raise ResultError("DOCUMENT_INPUT")
    try:
        doc = pure.decode_contract(view.canonical_bytes).document
    except pure.ContractDocumentError as exc:
        raise ResultError("DOCUMENT_" + exc.category) from exc
    checker = _Correspondence(doc, verification)
    # Read the fresh retained upstream entry after verifying exact runtime continuity.
    (entry,) = verification.analysis_bundle.root.find_owner(verification.selected_owner)
    try:
        checker.owner(doc["owner"], verification.selected_owner)
        checker.output(doc["output"], entry.active_output)
        same(doc["multiplicity"], entry.active_properties.multiplicity)
        checker.fields()
        checker.ordering(entry.active_properties.ordering)
        same(len(doc["types"]), len(checker.seen_types))
    except (KeyError, TypeError, IndexError, AttributeError) as exc:
        raise ResultError("CORRESPONDENCE") from exc


def verify_bound_export(export, verification):
    # Import only the wrapper type, never its construction or projection helpers.
    from pietto._project.project_result_contract_portable import ResultContractExport

    if (
        type(export) is not ResultContractExport
        or export.verification is not verification
    ):
        raise ResultError("ROOT")
    verify_contract_correspondence(export.view, export.contract, verification)
