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
from pietto._project.model import ProjectResolvedTypeKind

__all__: tuple[str, ...] = ()

NESTED = ProjectResolvedTypeKind.NESTED_RELATION


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

    def let_owner(self, doc, value):
        self.owner(doc, value)
        same(doc["let_position"], value.let_position)

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
        elif type(value) is ast.ParameterRefExpr:
            same(
                (
                    doc["tag"],
                    doc["name"],
                    doc["ordinal"],
                    doc["type_name"],
                    doc["nullability"],
                ),
                (
                    "parameter",
                    value.name,
                    value.ordinal,
                    value.type_name,
                    value.nullability.value,
                ),
            )
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
        elif type(value) is ast.ConditionalExpr:
            same(doc["tag"], "conditional")
            self.expression(doc["when_true"], value.when_true)
            self.expression(doc["condition"], value.condition)
            self.expression(doc["when_false"], value.when_false)
        elif type(value) is ast.MembershipExpr:
            same((doc["tag"], doc["negated"]), ("membership", value.negated))
            self.expression(doc["value"], value.value)
            same(len(doc["options"]), len(value.options))
            for observed, retained in zip(doc["options"], value.options, strict=True):
                self.expression(observed, retained)
        elif type(value) is ast.CastExpr:
            same(doc["tag"], "cast")
            self.expression(doc["value"], value.value)
            self.declared(doc["target"], value.target)
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

    def output(self, doc, value, owner=None):
        occurrence = value.occurrence
        same(
            (doc["position"], doc["producer"], doc["field_count"]),
            (
                occurrence.ref.position,
                occurrence.producer.ref.position,
                len(value.row_shape.fields),
            ),
        )
        (owner or self.owner)(doc["owner"], occurrence.producer.anchor.identity)

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

    def scalar_meaning(self, bundle):
        if bundle is None:
            same("scalar_meaning" in self.doc, False)
            return
        from pietto._project.project_scalar_meaning import TimestampMeaning

        sources = self.doc["scalar_meaning"]["sources"]
        same(len(sources), len(bundle.entries))
        for described, entry in zip(sources, bundle.entries, strict=True):
            port = entry.source_port
            same(described["ordinal"], entry.ordinal)
            self.coordinate(described["port"], port.ref)
            self.output(described["output"], port.field.output)
            same(described["position"], port.field.field_position)
            self.declared(described["declared"], entry.declared)
            same(
                (described["canonical"]["kind"], described["canonical"]["name"]),
                (entry.canonical.kind, entry.canonical.name),
            )
            self.symbol(described["canonical"]["symbol"], entry.canonical.symbol)
            self.resolution(described["type_resolution"], entry.declared)
            law, expected = described["law"], entry.law
            if type(expected) is TimestampMeaning:
                same(
                    (
                        law["calendar"],
                        law["resolution"],
                        law["timezone"],
                        law["lower"],
                        law["upper"],
                    ),
                    (
                        expected.calendar,
                        expected.resolution,
                        expected.timezone,
                        list(expected.lower),
                        list(expected.upper),
                    ),
                )
            else:
                same(
                    (law["byte_order"], law["byte_width"]),
                    (expected.byte_order, expected.byte_width),
                )

    def fields(self, contract):
        # The denominator comes from upstream plan exports, never the supplied view.
        ports = self.checked.plan.exports
        same(self.doc["field_count"], len(ports))
        same(len(self.doc["fields"]), len(ports))
        for ordinal, port in enumerate(ports):
            doc = self.doc["fields"][ordinal]
            leaf = contract.shape.fields[ordinal]
            if port.field.evidence.resolved_type.kind is NESTED:
                self.collection(doc, ordinal, port, leaf)
            else:
                self.leaf(doc, ordinal, port, leaf.meaning, self.owner)

    def head(self, doc, ordinal, port, owner):
        evidence = port.field.evidence
        same(
            (doc["ordinal"], doc["label"], doc["position"]),
            (ordinal, port.identity.name, port.field.field_position),
        )
        identity = doc["identity"]
        owner(identity["owner"], port.identity.owner)
        same(
            (identity["kind"], identity["position"], identity["name"]),
            (port.identity.kind, port.identity.field_position, port.identity.name),
        )
        self.coordinate(doc["port"]["coordinate"], port.ref)
        self.coordinate(doc["port"]["owner"], port.owner)
        self.coordinate(doc["port"]["producer"], port.producer_port)
        self.output(doc["output"], port.field.output, owner)
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
            self.location(doc["provenance"]["location"], evidence.provenance.location)

    def leaf(self, doc, ordinal, port, meaning, owner):
        self.head(doc, ordinal, port, owner)
        evidence = port.field.evidence
        declared = None if evidence.field_def is None else evidence.field_def.type_expr
        self.declared(doc["declared"], declared)
        same(
            (doc["canonical"]["kind"], doc["canonical"]["name"]),
            (evidence.resolved_type.kind, evidence.resolved_type.name),
        )
        self.symbol(doc["canonical"]["symbol"], evidence.resolved_type.symbol)
        self.resolution(doc["type_resolution"], declared)
        if meaning is None:
            same("meaning" in doc, False)
        else:
            same(doc["meaning"], meaning.ordinal)

    def collection(self, doc, ordinal, port, leaf):
        """Enumerate the element from the S06 Collect read of this export and
        the S04 descriptor of its type, never from the contract's shape."""
        from pietto._project.project_sql_plan_nested import collect_of

        plan = self.checked.plan
        self.head(doc, ordinal, port, self.owner)
        same(doc["kind"], "collection")
        collect = collect_of(plan, port.ref)
        (definition,) = (
            d for d in plan.bindings.definitions if d.ref is collect.producer
        )
        entry, children = definition.entry, definition.exports
        descriptor = port.field.evidence.resolved_type.nested.element_fields
        same(len(collect.children), len(children))
        same(len(descriptor), len(children))
        # A rebuilt producer row (DISTINCT, QUALIFY) has other field evidence
        # than the descriptor: the children are the Collect read's, and the
        # descriptor agrees on their count, identity and nullability.
        for ref, child, item in zip(
            collect.children, children, descriptor, strict=True
        ):
            same(ref is child.ref, True)
            same(
                (child.identity, child.field.effective_nullability),
                (item.identity, item.effective_nullability),
            )
        element = doc["element"]
        self.let_owner(element["owner"], entry.owner)
        self.output(element["output"], entry.active_output, self.let_owner)
        same(
            (element["multiplicity"], element["nullability"]),
            (entry.active_properties.multiplicity, "non_null"),
        )
        same(element["field_count"], len(children))
        same(len(element["fields"]), len(children))
        for position, child in enumerate(children):
            meaning = leaf.shape.fields[position].meaning
            self.leaf(
                element["fields"][position], position, child, meaning, self.let_owner
            )
        self.ordering(
            element["ordering"],
            entry.active_properties.ordering,
            entry.owner,
            self.let_owner,
        )

    def ordering(self, doc, retained, relation, owner):
        if retained is None:
            same(doc, None)
            return
        if type(retained) is ProjectIRProvidedRelationOrdering:
            same(doc["kind"], "provided")
            owner(doc["owner"], retained.evidence.owner)
            authored = retained.items
        elif type(retained) is ProjectRelationOrdering:
            same(doc["kind"], "final")
            owner(doc["owner"], retained.owner)
            authored = tuple(i.item for i in retained.items)
        else:
            raise ResultError("CORRESPONDENCE")
        prepared = [
            order.source
            for order in self.checked.plan.orders
            if order.source.owner is relation
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
        # The format follows the upstream exports: v2 only with a collection.
        nested = any(
            port.field.evidence.resolved_type.kind is NESTED
            for port in verification.plan.exports
        )
        same(doc["format"], pure.FORMAT_V2 if nested else pure.FORMAT)
        checker.owner(doc["owner"], verification.selected_owner)
        checker.output(doc["output"], entry.active_output)
        same(doc["multiplicity"], entry.active_properties.multiplicity)
        checker.fields(contract)
        checker.scalar_meaning(contract.scalar_meaning)
        checker.ordering(
            doc["ordering"],
            entry.active_properties.ordering,
            verification.selected_owner,
            checker.owner,
        )
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
