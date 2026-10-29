"""Project row-predicate normalization over exact module and input identities."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from pietto import ast_nodes as ast
from pietto._syntax_admission import unnest_lets
from pietto._project.existence_values import (
    ProjectAnyRowBinding,
    any_argument_scopes,
    any_bindings_for_expression,
)
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRowField,
    ProjectResolvedTypeKind,
    ProjectSemanticResult,
    ProjectSymbolNamespace,
)
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.module_relation_resolution import (
    ProjectResolvedModuleRelationReference,
    _resolved_row_type,
    _row_field_nullability,
)
from pietto._project.project_relationship_uses import (
    ProjectRelationBindingOccurrence,
    ProjectRelationJoinUseLedger,
    project_join_binding_visible,
)
from pietto._project.row_expression_type_facts import (
    project_row_field_to_semantic_value_type,
    scalar_field_reference_leaves,
)
from pietto.errors import Diagnostic
from pietto.semantic.model import (
    EffectiveNullability,
    RelationshipCallInfo,
    RelationshipTemplateInfo,
    ResolvedType,
)
from pietto.semantic.relationship_predicates import (
    RelationshipCallFailure,
    RowCandidate,
    _scalar_contracts,
    bind_relationship_expression,
    check_relationship_templates,
)

__all__ = ()


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectRelationshipPredicateCatalog:
    semantic_result: ProjectSemanticResult = field(repr=False)
    templates: Mapping[str, tuple[RelationshipTemplateInfo, ...]] = field(init=False)
    diagnostics: tuple[Diagnostic, ...] = field(init=False)

    def __post_init__(self) -> None:
        root = self.semantic_result
        catalogs = root.module_catalogs
        resolutions = root.module_type_source_resolutions
        if catalogs is None or resolutions is None:
            raise ValueError("Project predicates require resolved module authority.")
        checked: dict[str, tuple[RelationshipTemplateInfo, ...]] = {}
        diagnostics: list[Diagnostic] = []
        for module in root.modules:
            if module.parsed_input is None:
                continue
            script = module.parsed_input.script
            if not script.relationship_templates:
                continue
            environments = resolutions.find_module_path(module.path)
            local_catalogs = catalogs.find_module_path(module.path)
            if len(environments) != 1 or len(local_catalogs) != 1:
                raise ValueError("Project predicates require one exact module scope.")
            environment = environments[0]
            shape_candidates: dict[str, tuple[ast.Node, ...]] = {}
            value_types: dict[ast.TypeExpr, ResolvedType] = {}
            nullability: dict[ast.TypeExpr, EffectiveNullability] = {}
            for template in script.relationship_templates:
                for parameter in template.parameters:
                    symbols = environment.find_type_name(parameter.shape_name)
                    candidates = tuple(item.target_occurrence for item in symbols)
                    if not candidates:
                        local = local_catalogs[0].find_namespace_name(
                            ProjectSymbolNamespace.TYPE, parameter.shape_name
                        )
                        # A blocked unique name is not a successful local fallback.
                        candidates = local if len(local) > 1 else ()
                    shape_candidates[parameter.shape_name] = tuple(
                        item.definition for item in candidates
                    )
                    for candidate in candidates:
                        shape = candidate.definition
                        if type(shape) is not ast.ShapeDef:
                            continue
                        defining = resolutions.find_module_path(
                            candidate.identity.module_path
                        )
                        if len(defining) != 1:
                            continue
                        for item in shape.fields:
                            facts = defining[0].find_type_expr(item.type_expr)
                            if (
                                len(facts) != 1
                                or facts[0].canonical_kind
                                is ProjectResolvedTypeKind.UNKNOWN
                            ):
                                continue
                            value = project_row_field_to_semantic_value_type(
                                ProjectRowField(
                                    name=item.name,
                                    resolved_type=_resolved_row_type(
                                        facts[0], catalogs
                                    ),
                                    nullability=_row_field_nullability(
                                        item.type_expr.nullability
                                    ),
                                    field_def=item,
                                ),
                                _row_field_nullability(item.type_expr.nullability),
                            )
                            value_types[item.type_expr] = value.resolved_type
                            nullability[item.type_expr] = value.nullability
            templates, errors = check_relationship_templates(
                script,
                shape_candidates=shape_candidates,
                type_resolutions=value_types,
                type_expansions=value_types,
                type_nullability=nullability,
            )
            checked[module.path] = templates
            diagnostics.extend(errors)
        object.__setattr__(self, "templates", MappingProxyType(checked))
        object.__setattr__(self, "diagnostics", tuple(diagnostics))


def declared_source_shape(
    root: ProjectSemanticResult, owner: ProjectDeclarationOccurrence
) -> ast.ShapeDef | None:
    """Resolve a source in its declaring module, including imported shape aliases."""

    catalogs = root.module_catalogs
    resolutions = root.module_type_source_resolutions
    if catalogs is None or resolutions is None:
        raise ValueError("Project predicates require resolved module authority.")
    if not any(
        item is owner
        for module in catalogs.find_module_path(owner.identity.module_path)
        for item in module.relation_owners
    ):
        raise ValueError("Predicate input requires an exact declaration occurrence.")
    source = owner.definition
    if type(source) is not ast.SourceDef:
        return None
    environments = resolutions.find_module_path(owner.identity.module_path)
    if len(environments) != 1:
        return None
    shapes = environments[0].find_source(source)
    if len(shapes) != 1:
        return None
    shape = shapes[0].target_symbol.target_occurrence.definition
    return shape if type(shape) is ast.ShapeDef else None


type ProjectPredicateArgumentBinding = (
    ProjectRelationBindingOccurrence
    | ProjectResolvedModuleRelationReference
    | ProjectAnyRowBinding
)


def _binding_parts(
    binding: ProjectPredicateArgumentBinding,
) -> tuple[
    ProjectDeclarationOccurrence,
    ast.FromClause | ast.JoinClause | ast.AnyExpr,
    str,
    ProjectDeclarationOccurrence | None,
]:
    if type(binding) is ProjectAnyRowBinding:
        return binding.owner, binding.expression, binding.name, binding.target
    if type(binding) is ProjectRelationBindingOccurrence:
        return (
            binding.owner,
            binding.site,
            binding.name,
            None if binding.target is None else binding.target.target_occurrence,
        )
    if type(binding) is ProjectResolvedModuleRelationReference:
        owner = binding.reference.owner
        site = binding.reference.from_clause
        return (
            owner,
            site,
            site.binding_name or site.source_name,
            binding.target_symbol.target_occurrence,
        )
    raise TypeError(
        "Predicate arguments require an exact JOIN binding or FROM resolution."
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectRelationshipPredicateExpression:
    owner: ProjectDeclarationOccurrence = field(repr=False)
    context: ast.Node = field(repr=False)
    authored: ast.Expression = field(repr=False)
    expression: ast.Expression = field(repr=False)
    calls: tuple[RelationshipCallInfo, ...]
    argument_bindings: tuple[tuple[ProjectPredicateArgumentBinding, ...], ...]
    diagnostics: tuple[Diagnostic, ...]
    failed_calls: tuple[RelationshipCallFailure, ...] = ()
    any_expressions: tuple[tuple[ast.AnyExpr, ast.AnyExpr], ...] = ()
    any_bindings: tuple[ProjectAnyRowBinding, ...] = ()
    parent: ProjectRelationshipPredicateExpression | None = field(
        default=None, repr=False
    )

    def __post_init__(self) -> None:
        from pietto.semantic.inline_functions import _tree_nodes

        authored_any = tuple(
            node for node in _tree_nodes(self.authored) if type(node) is ast.AnyExpr
        )
        normalized_any = tuple(
            node for node in _tree_nodes(self.expression) if type(node) is ast.AnyExpr
        )
        if (
            len(self.any_bindings) != len(authored_any)
            or any(
                binding.owner is not self.owner or binding.expression is not node
                for binding, node in zip(self.any_bindings, authored_any)
            )
            or len(self.any_expressions) != len(authored_any)
            or len(self.any_expressions) != len(normalized_any)
            or len({id(before) for before, _ in self.any_expressions})
            != len(self.any_expressions)
            or len({id(after) for _, after in self.any_expressions})
            != len(self.any_expressions)
            or any(
                not any(before is node for node in authored_any)
                or not any(after is node for node in normalized_any)
                for before, after in self.any_expressions
            )
        ):
            raise ValueError(
                "Predicate ANY images require complete observed identity mappings."
            )
        authored_nodes = {id(node) for node in _tree_nodes(self.authored)}
        expression_nodes = {id(node) for node in _tree_nodes(self.expression)}
        failure_diagnostics = tuple(
            diagnostic
            for failure in self.failed_calls
            for diagnostic in failure.diagnostics
        )
        if (
            type(self.failed_calls) is not tuple
            or any(
                type(failure) is not RelationshipCallFailure
                for failure in self.failed_calls
            )
            or len({id(failure.call) for failure in self.failed_calls})
            != len(self.failed_calls)
            or len({id(failure.expression) for failure in self.failed_calls})
            != len(self.failed_calls)
            or any(
                id(failure.call) not in authored_nodes
                or id(failure.expression) not in expression_nodes
                or not failure.diagnostics
                for failure in self.failed_calls
            )
            or len(failure_diagnostics) != len(self.diagnostics)
            or any(
                actual is not expected
                for actual, expected in zip(failure_diagnostics, self.diagnostics)
            )
        ):
            raise ValueError(
                "Predicate failures require exact call and diagnostic identities."
            )
        if self.parent is not None:
            nodes = authored_nodes
            expected_failures = tuple(
                failure
                for failure in self.parent.failed_calls
                if id(failure.call) in nodes
            )
            if len(expected_failures) != len(self.failed_calls) or any(
                failure.call is not original.call
                or len(failure.diagnostics) != len(original.diagnostics)
                or any(
                    diagnostic is not original_diagnostic
                    for diagnostic, original_diagnostic in zip(
                        failure.diagnostics, original.diagnostics
                    )
                )
                for failure, original in zip(self.failed_calls, expected_failures)
            ):
                raise ValueError(
                    "Predicate failure view requires its exact canonical subset."
                )
            expected = tuple(
                (call, bindings)
                for call, bindings in zip(
                    self.parent.calls, self.parent.argument_bindings, strict=True
                )
                if id(call.call) in nodes
            )
            if (
                self.parent.parent is not None
                or self.parent.owner is not self.owner
                or self.parent.context is not self.context
                or not any(
                    node is self.authored for node in _tree_nodes(self.parent.authored)
                )
                or len(expected) != len(self.calls)
                or any(
                    call is not original or bindings is not original_bindings
                    for (call, bindings), (original, original_bindings) in zip(
                        zip(self.calls, self.argument_bindings, strict=True),
                        expected,
                        strict=True,
                    )
                )
            ):
                raise ValueError(
                    "Predicate argument view requires its exact canonical context and call subset."
                )
        if len(self.calls) != len(self.argument_bindings):
            raise ValueError("Predicate calls require complete input binding facts.")
        for call, bindings in zip(self.calls, self.argument_bindings, strict=True):
            if (
                call.owner is not self.owner.definition
                or call.context is not self.context
            ):
                raise ValueError(
                    "Predicate call requires its exact project owner and context."
                )
            if len(call.arguments) != len(bindings):
                raise ValueError("Predicate arguments require complete binding facts.")
            for argument, binding in zip(call.arguments, bindings, strict=True):
                owner, site, _, target = _binding_parts(binding)
                if (
                    owner is not self.owner
                    or argument.occurrence is not site
                    or target is None
                    or argument.relation is not target.definition
                ):
                    raise ValueError(
                        "Predicate argument lost its exact input occurrence."
                    )

    @property
    def failed_row_arguments(self) -> tuple[ast.NameExpr, ...]:
        return tuple(
            argument
            for failure in self.failed_calls
            for argument in failure.expression.arguments
            if type(argument) is ast.NameExpr
        )

    @property
    def scalar_references(self) -> tuple[ast.NameExpr | ast.DottedNameExpr, ...]:
        row_arguments = {id(argument) for argument in self.failed_row_arguments}
        return tuple(
            leaf
            for leaf in scalar_field_reference_leaves(self.expression)
            if id(leaf) not in row_arguments
        )


def bind_project_relationship_predicates(
    catalog: ProjectRelationshipPredicateCatalog,
    ledger: ProjectRelationJoinUseLedger,
) -> tuple[ProjectRelationshipPredicateExpression, ...]:
    """Bind all JOIN-owner clauses before collecting scalar references."""

    definition = ledger.owner.definition
    assert isinstance(definition, (ast.TableDef, ast.QueryDef))
    contexts: list[
        tuple[ast.Node, ast.Expression, tuple[ProjectPredicateArgumentBinding, ...]]
    ] = []
    for position, join in enumerate(definition.join_clauses):
        if join.on_clause is not None:
            contexts.append(
                (
                    join.on_clause,
                    join.on_clause.expression,
                    tuple(
                        binding
                        for binding in ledger.bindings[: position + 2]
                        if project_join_binding_visible(binding, ledger.uses[:position])
                    ),
                )
            )
    visible = tuple(
        binding
        for binding in ledger.bindings
        if project_join_binding_visible(binding, ledger.uses)
    )
    if definition.let_clause is not None:
        contexts.extend(
            (binding, binding.expression, visible)
            for binding in definition.let_clause.bindings
        )
    if definition.where_clause is not None:
        contexts.append(
            (definition.where_clause, definition.where_clause.expression, visible)
        )
    contexts.extend(
        (item, item.expression, visible) for item in definition.select_items
    )
    return _bind_project_predicates(catalog, ledger.owner, contexts)


def bind_project_no_join_relationship_predicates(
    catalog: ProjectRelationshipPredicateCatalog,
    owner: ProjectDeclarationOccurrence,
) -> tuple[ProjectRelationshipPredicateExpression, ...]:
    """Bind one real FROM occurrence, including repeated row arguments."""

    definition = owner.definition
    assert isinstance(definition, (ast.TableDef, ast.QueryDef))
    if definition.join_clauses:
        raise ValueError("Single-input predicate binding forbids JOIN owners.")
    resolutions = catalog.semantic_result.module_relation_resolutions
    assert resolutions is not None
    environments = resolutions.find_module_path(owner.identity.module_path)
    if len(environments) != 1:
        raise ValueError("Predicate owner requires one exact relation scope.")
    bindings = environments[0].find_from_clause(definition.from_clause)
    if any(binding.reference.owner is not owner for binding in bindings):
        raise ValueError("Predicate FROM resolution lost its exact owner.")
    contexts: list[
        tuple[ast.Node, ast.Expression, tuple[ProjectPredicateArgumentBinding, ...]]
    ] = []
    if definition.let_clause is not None:
        contexts.extend(
            (binding, binding.expression, bindings)
            for binding in definition.let_clause.bindings
        )
    if definition.where_clause is not None:
        contexts.append(
            (definition.where_clause, definition.where_clause.expression, bindings)
        )
    contexts.extend(
        (item, item.expression, bindings) for item in definition.select_items
    )
    return _bind_project_predicates(catalog, owner, contexts)


def _bind_project_predicates(
    catalog: ProjectRelationshipPredicateCatalog,
    owner: ProjectDeclarationOccurrence,
    contexts: list[
        tuple[ast.Node, ast.Expression, tuple[ProjectPredicateArgumentBinding, ...]]
    ],
) -> tuple[ProjectRelationshipPredicateExpression, ...]:
    root = catalog.semantic_result
    catalogs = root.module_catalogs
    assert catalogs is not None
    modules = catalogs.find_module_path(owner.identity.module_path)
    if not any(item is owner for module in modules for item in module.relation_owners):
        raise ValueError("Predicate owner requires exact module catalog membership.")
    assert len(modules) == 1 and modules[0].module.parsed_input is not None
    script = modules[0].module.parsed_input.script
    if not script.relationship_templates:
        return ()
    definition = owner.definition
    assert isinstance(definition, (ast.TableDef, ast.QueryDef))
    declared_names = frozenset(item.name for item in script.relationship_templates)
    scalar_names = frozenset(
        item.name for item in modules[0].module.parsed_input.scalar_callables
    )
    contexts.sort(key=lambda item: (item[0].span.line, item[0].span.column))
    results: list[ProjectRelationshipPredicateExpression] = []
    ordinal = 0
    for context, expression, visible in contexts:
        any_bindings = any_bindings_for_expression(root, owner, expression)
        any_scopes = any_argument_scopes(expression, any_bindings)

        def readable(
            argument: ast.NameExpr,
        ) -> tuple[ProjectPredicateArgumentBinding, ...]:
            local = any_scopes.get(argument, ())
            shadowed = frozenset(binding.name for binding in local)
            return (
                *(
                    binding
                    for binding in visible
                    if _binding_parts(binding)[2] not in shadowed
                ),
                *local,
            )

        def resolve(argument: ast.NameExpr) -> tuple[RowCandidate, ...]:
            found: list[RowCandidate] = []
            for binding in readable(argument):
                _, site, name, target = _binding_parts(binding)
                if name != argument.name or target is None:
                    continue
                shape = declared_source_shape(root, target)
                relation = target.definition
                if shape is not None and isinstance(
                    relation, (ast.SourceDef, ast.TableDef, ast.QueryDef)
                ):
                    found.append((site, relation, shape))
            return tuple(found)

        scalar_arguments: set[str] = set()
        for binding in visible:
            _, _, _, target = _binding_parts(binding)
            shape = None if target is None else declared_source_shape(root, target)
            if shape is not None:
                scalar_arguments.update(item.name for item in shape.fields)
        if (
            not isinstance(context, ast.JoinOnClause)
            and definition.let_clause is not None
        ):
            scalar_arguments.update(
                binding.name for binding in definition.let_clause.bindings
            )
        any_images: list[tuple[ast.AnyExpr, ast.AnyExpr]] = []

        def observe(before: object, after: object) -> None:
            if type(before) is ast.AnyExpr and type(after) is ast.AnyExpr:
                any_images.append((before, after))

        expanded, calls, diagnostics, failed_calls = bind_relationship_expression(
            expression,
            templates=catalog.templates.get(owner.identity.module_path, ()),
            declared_names=declared_names,
            resolve_row=resolve,
            owner=definition,
            context=context,
            scalar_names=scalar_names,
            first_ordinal=ordinal,
            scalar_argument_names=frozenset(scalar_arguments),
            scalar_argument_available=lambda argument: (
                argument.name in scalar_arguments
                and not any(
                    binding.name == argument.name
                    for binding in any_scopes.get(argument, ())
                )
            ),
            occurrence_observer=observe,
        )
        ordinal += len(calls)
        argument_bindings: list[tuple[ProjectPredicateArgumentBinding, ...]] = []
        for call in calls:
            bindings: list[ProjectPredicateArgumentBinding] = []
            for argument in call.arguments:
                matches = tuple(
                    binding
                    for binding in (*visible, *any_bindings)
                    if _binding_parts(binding)[1] is argument.occurrence
                )
                if len(matches) != 1:
                    raise ValueError(
                        "Predicate argument requires one exact visible binding."
                    )
                bindings.append(matches[0])
            argument_bindings.append(tuple(bindings))
        results.append(
            ProjectRelationshipPredicateExpression(
                owner=owner,
                context=context,
                authored=expression,
                expression=expanded,
                calls=calls,
                argument_bindings=tuple(argument_bindings),
                diagnostics=diagnostics,
                failed_calls=failed_calls,
                any_expressions=tuple(any_images),
                any_bindings=any_bindings,
            )
        )
    return tuple(results)


def select_project_predicate_expression(
    records: tuple[ProjectRelationshipPredicateExpression, ...],
    owner: ProjectDeclarationOccurrence,
    expression: ast.Expression,
) -> ProjectRelationshipPredicateExpression | None:
    """Return the exact normalized root, or its retained aggregate-argument subtree."""

    from pietto.semantic.inline_functions import _rebuild, _tree_nodes

    for record in records:
        if record.owner is not owner:
            continue
        if record.authored is expression:
            return (
                record
                if record.calls or record.diagnostics or record.any_bindings
                else None
            )
        if not any(node is expression for node in _tree_nodes(record.authored)):
            continue
        nodes = {id(node) for node in _tree_nodes(expression)}
        selected = tuple(
            (call, bindings)
            for call, bindings in zip(
                record.calls, record.argument_bindings, strict=True
            )
            if id(call.call) in nodes
        )
        selected_failures = tuple(
            failure for failure in record.failed_calls if id(failure.call) in nodes
        )
        if (
            not selected
            and not selected_failures
            and not any(
                id(binding.expression) in nodes for binding in record.any_bindings
            )
        ):
            return None
        expansions = {id(call.call): call.expanded for call, _ in selected}
        images: list[tuple[ast.AnyExpr, ast.AnyExpr]] = []
        failure_images: dict[int, ast.CallExpr] = {}

        def observe_view(before: object, after: object) -> None:
            if type(before) is ast.CallExpr and type(after) is ast.CallExpr:
                failure_images[id(before)] = after
            if type(before) is ast.AnyExpr and type(after) is ast.AnyExpr:
                images.append((before, after))

        def rewrite_view(original: object, rebuilt: object) -> object:
            if id(original) in expansions:
                return expansions[id(original)]
            return (
                _scalar_contracts(original, rebuilt) if selected_failures else rebuilt
            )

        normalized = _rebuild(
            expression,
            rewrite_view,
            occurrence_observer=observe_view,
        )
        assert isinstance(normalized, ast.Expression)
        return replace(
            record,
            parent=record,
            authored=expression,
            expression=normalized,
            calls=tuple(call for call, _ in selected),
            argument_bindings=tuple(bindings for _, bindings in selected),
            failed_calls=tuple(
                replace(failure, expression=failure_images[id(failure.call)])
                for failure in selected_failures
            ),
            diagnostics=tuple(
                diagnostic
                for diagnostic in record.diagnostics
                if any(
                    diagnostic is item
                    for failure in selected_failures
                    for item in failure.diagnostics
                )
            ),
            any_expressions=tuple(images),
            any_bindings=tuple(
                binding
                for binding in record.any_bindings
                if id(binding.expression) in nodes
            ),
        )
    return None


def normalize_project_query_names(
    parsed: ProjectParseCheckResult,
) -> ProjectParseCheckResult:
    """Resolve modern input aliases before the final module catalogs are frozen."""

    from pietto._project.model import ProjectParsedInput, ProjectSymbolNamespace
    from pietto._project.module_bindings import (
        _build_project_module_binding_environment_set,
    )
    from pietto._project.module_carrier import _build_project_logical_modules
    from pietto._project.module_catalog import _build_project_module_catalog_set
    from pietto.semantic.relationship_predicates import _diagnostic
    from pietto.semantic.existence_generators import (
        AnyValueTrace,
        rebind_any_values,
        rebind_existence_generators,
    )
    from pietto.semantic.inline_functions import _rebuild, _tree_nodes
    from pietto.semantic.modern_inputs import (
        _lexical_any_scopes,
        later_let_reads,
        shadowed_input,
        unknown_let_input,
    )

    if not any(
        isinstance(item, (ast.TableDef, ast.QueryDef, ast.SelectBody))
        and (item.naming_declarations or item.named_windows)
        for source in parsed.parsed_inputs
        for item in _tree_nodes(source.script)
    ):
        return parsed
    catalogs = _build_project_module_catalog_set(parsed.modules)
    assert parsed.selected_input_index is not None
    imports = _build_project_module_binding_environment_set(
        parsed.selected_input_index, parsed.modules, catalogs
    )
    diagnostics: list[Diagnostic] = []

    def candidates(
        path: str, namespace: ProjectSymbolNamespace, name: str
    ) -> tuple[ProjectDeclarationOccurrence, ...]:
        local = catalogs.find_module_path(path)
        environments = imports.find_module_path(path)
        if len(local) != 1 or len(environments) != 1:
            return ()
        return (
            *local[0].find_namespace_name(namespace, name),
            *(
                target
                for binding in environments[0].bindings
                if binding.identity.namespace is namespace
                and binding.identity.local_binding_name == name
                for target in catalogs.find_identity(binding.target_identity)
            ),
        )

    def field_names(occurrence: ProjectDeclarationOccurrence) -> set[str]:
        definition = occurrence.definition
        if isinstance(definition, ast.SourceDef):
            return {
                item.name
                for shape in candidates(
                    occurrence.identity.module_path,
                    ProjectSymbolNamespace.TYPE,
                    definition.shape_name or "",
                )
                if isinstance(shape.definition, ast.ShapeDef)
                for item in shape.definition.fields
            }
        if isinstance(definition, (ast.TableDef, ast.QueryDef)):
            return {
                item.alias
                or (
                    item.expression.name
                    if isinstance(item.expression, ast.NameExpr)
                    else item.expression.parts[-1]
                    if isinstance(item.expression, ast.DottedNameExpr)
                    else ""
                )
                for item in definition.select_items
            }
        return set()

    def input_field_names(
        occurrence: ProjectDeclarationOccurrence, seen: frozenset[int] = frozenset()
    ) -> set[str]:
        """The fields a window name cannot take: also VALUES columns and the
        labels of a set, which its first operand gives."""

        definition = occurrence.definition
        if isinstance(definition, ast.ValuesRelationDef):
            return {column.name for column in definition.body.columns}
        if not isinstance(definition, ast.SetRelationDef) or id(occurrence) in seen:
            return field_names(occurrence)
        path = occurrence.identity.module_path
        name = definition.body.operands[0].relation_name
        operands = (
            *(
                let
                for module in catalogs.find_module_path(path)
                for let in module.find_lets(occurrence.declaration_position)
                if let.identity.declared_name == name
            ),
            *candidates(path, ProjectSymbolNamespace.RELATION, name),
        )
        if len(operands) != 1:
            return set()
        return input_field_names(operands[0], seen | {id(occurrence)})

    normalized: list[ProjectParsedInput] = []
    unchanged = True
    for source in parsed.parsed_inputs:
        any_trace = AnyValueTrace(source.script, uses=source.existence_values)
        generated_joins = {id(use.clause) for use in source.existence_generators}
        # A lowered WHERE ANY still binds its row name over its hidden ON.
        lowered = {
            id(use.clause.on_clause): use.expression
            for use in source.existence_generators
        }
        (catalog,) = catalogs.find_module_path(source.path)

        def normalize_body(
            definition: ast.TableDef | ast.QueryDef | ast.SelectBody,
            local_lets: tuple[ProjectDeclarationOccurrence, ...],
            parameters: tuple[ast.QueryParameter, ...],
        ) -> ast.TableDef | ast.QueryDef | ast.SelectBody:
            declared = {let.identity.declared_name for let in local_lets}
            aliases: dict[
                str, tuple[tuple[str, ProjectDeclarationOccurrence], ...]
            ] = {}
            alias_sites: dict[str, ast.QueryLetDeclaration] = {}
            visible: list[ProjectDeclarationOccurrence] = []
            scalar_names = {parameter.name for parameter in parameters}
            window_names: set[str] = set()
            windows: list[tuple[ast.NamedWindowDeclaration, frozenset[str]]] = []
            scalar_bindings: list[ast.LetBinding] = []
            # S03 types each Unnest let in its companion facts (D71.02); its
            # JOIN stays one input in place, which no relation stands for
            # until S05 binds it.
            unnest_ids = {
                id(node)
                for let, joins_of_let in unnest_lets(definition)
                for node in (let, *joins_of_let)
            }
            from_clause = definition.from_clause
            joins: list[ast.JoinClause] = []
            # The input names a let cannot take, as PIE-S2329 refuses them.
            input_names: set[str] = set()

            def input_fields() -> set[str]:
                return {
                    name for target in visible for name in input_field_names(target)
                } | (
                    {from_clause.binding_name}
                    if isinstance(from_clause, ast.TableFunctionFromClause)
                    else set()
                )

            def relation_candidates(
                name: str,
            ) -> tuple[ProjectDeclarationOccurrence, ...]:
                return (
                    *(let for let in local_lets if let.identity.declared_name == name),
                    *candidates(source.path, ProjectSymbolNamespace.RELATION, name),
                )

            def relations(
                name: str,
            ) -> tuple[tuple[str, ProjectDeclarationOccurrence], ...]:
                return (
                    *aliases.get(name, ()),
                    *((name, target) for target in relation_candidates(name)),
                )

            for node in sorted(
                (
                    *definition.naming_declarations,
                    *definition.named_windows,
                    from_clause,
                    *definition.join_clauses,
                ),
                key=lambda item: (item.span.line, item.span.column),
            ):
                if isinstance(node, ast.NamedWindowDeclaration):
                    # Windows share the let namespace; two windows of one
                    # name keep their own named-window diagnostic.
                    if node.name in declared:
                        diagnostics.append(
                            _diagnostic(
                                node, f"Duplicate query local name: {node.name}"
                            )
                        )
                    elif shadow := shadowed_input(node, input_fields(), input_names):
                        diagnostics.append(shadow)
                    window_names.add(node.name)
                    windows.append((node, frozenset(declared)))
                elif isinstance(node, ast.QueryLetDeclaration):
                    if node.name in declared or node.name in window_names:
                        diagnostics.append(
                            _diagnostic(
                                node, f"Duplicate query local name: {node.name}"
                            )
                        )
                    declared.add(node.name)
                    if id(node) in unnest_ids:
                        continue
                    value = node.expression
                    name = value.name if isinstance(value, ast.NameExpr) else None
                    targets = relations(name) if name is not None else ()
                    is_scalar = name is not None and (
                        name in scalar_names
                        or any(name in field_names(target) for target in visible)
                    )
                    if targets and is_scalar:
                        diagnostics.append(
                            _diagnostic(
                                node.expression,
                                f"Ambiguous relation or scalar name: {name}",
                            )
                        )
                    elif len(targets) > 1:
                        diagnostics.append(
                            _diagnostic(
                                node.expression,
                                f"Ambiguous relation name: {name}",
                            )
                        )
                    elif targets:
                        aliases[node.name] = targets
                        alias_sites[node.name] = node
                    elif not is_scalar and (
                        unknown := unknown_let_input(
                            node,
                            definition.naming_declarations,
                            definition.join_clauses,
                            generated_joins,
                        )
                    ):
                        diagnostics.append(unknown)
                        continue
                    else:
                        position = (node.span.line, node.span.column)
                        last_input = max(
                            (item.span.line, item.span.column)
                            for item in (
                                definition.from_clause,
                                *definition.join_clauses,
                            )
                            if id(item) not in generated_joins
                        )
                        tail_contexts = (
                            *(
                                (definition.where_clause,)
                                if definition.where_clause is not None
                                else ()
                            ),
                            *(
                                use.context
                                for use in source.existence_generators
                                if use.owner is definition
                                and isinstance(use.context, ast.WhereClause)
                            ),
                        )
                        if position <= last_input or any(
                            position >= (where.span.line, where.span.column)
                            for where in tail_contexts
                        ):
                            diagnostics.append(
                                _diagnostic(
                                    node,
                                    "A row-value let must follow FROM and every JOIN and precede WHERE",
                                )
                            )
                            continue
                        diagnostics.extend(later_let_reads(windows, node.name))
                        scalar_names.add(node.name)
                        binding = ast.LetBinding(
                            span=node.span, name=node.name, expression=node.expression
                        )
                        any_trace.record(node, binding)
                        scalar_bindings.append(binding)
                elif isinstance(node, ast.TableFunctionFromClause):
                    # The binding also names the table function's scalar column.
                    scalar_names.add(node.binding_name)
                    input_names.add(node.binding_name)
                elif isinstance(node, ast.FromClause):
                    targets = relations(node.source_name)
                    if len(targets) > 1:
                        if definition.naming_declarations:
                            diagnostics.append(
                                _diagnostic(
                                    node, f"Ambiguous FROM input: {node.source_name}"
                                )
                            )
                    elif len(targets) == 1:
                        name, target = targets[0]
                        if node.source_name in aliases:
                            from_clause = replace(
                                node, source_name=name, binding_name=node.source_name
                            )
                        visible.append(target)
                    assert isinstance(from_clause, ast.FromClause)
                    input_names.add(from_clause.binding_name or from_clause.source_name)
                    if definition.join_clauses:
                        input_names.add(from_clause.source_name)
                else:
                    assert isinstance(node, ast.JoinClause)
                    targets = relations(node.target_relation_name)
                    # An Unnest let is one more local input of its name, so
                    # another one makes its JOIN ambiguous, as for an alias
                    # let; no candidate wins (D71.02).
                    if len(targets) > 1 or (targets and id(node) in unnest_ids):
                        if definition.naming_declarations:
                            diagnostics.append(
                                _diagnostic(
                                    node,
                                    f"Ambiguous JOIN input: {node.target_relation_name}",
                                )
                            )
                        joins.append(node)
                    elif len(targets) == 1:
                        name, target = targets[0]
                        joins.append(replace(node, target_relation_name=name))
                        if node.kind not in (
                            ast.AuthoredJoinKind.SEMI,
                            ast.AuthoredJoinKind.ANTI,
                        ):
                            visible.append(target)
                    else:
                        joins.append(node)
                    if id(node) not in generated_joins:
                        input_names.update(
                            (node.target_binding_name, joins[-1].target_relation_name)
                        )
            if not definition.naming_declarations:
                # Only windows: the check above leaves the body as written.
                return definition
            clause = definition.let_clause
            if scalar_bindings:
                clause = (
                    ast.LetClause(
                        span=scalar_bindings[0].span, bindings=tuple(scalar_bindings)
                    )
                    if clause is None
                    else replace(clause, bindings=(*clause.bindings, *scalar_bindings))
                )
            normalized_definition = replace(
                definition,
                from_clause=from_clause,
                join_clauses=tuple(joins),
                let_clause=clause,
                naming_declarations=(),
            )

            any_trace.record(definition, normalized_definition)
            scopes = _lexical_any_scopes(normalized_definition, lowered)
            from_binding = (
                from_clause.binding_name
                if isinstance(from_clause, ast.FromClause)
                else None
            )
            from_source = (
                from_clause.source_name
                if isinstance(from_clause, ast.FromClause)
                else None
            )
            from_fields = (
                frozenset(input_field_names(visible[0]))
                if from_binding is not None and visible
                else frozenset()
            )
            # The compatibility rule keeps only what 0.1.5 admitted: an
            # original-name read in a query without an authored JOIN, outside
            # any `any(...)` (a lowered one keeps its scope over its ON).
            original_reads = not any(
                id(join) not in generated_joins
                or join.target_binding_name == from_source
                for join in definition.join_clauses
            )

            def normalize_iterator(before: object, after: object) -> object:
                result = after
                if type(after) is ast.AnyExpr:
                    if any(
                        scope.binding_name == after.relation_name
                        for scope in scopes.get(id(before), ())
                    ):
                        # An enclosing binder hides the name, as in a single file.
                        return after
                    alias = alias_sites.get(after.relation_name)
                    targets = (
                        relations(after.relation_name)
                        if alias is None
                        or (alias.span.line, alias.span.column)
                        < (after.span.line, after.span.column)
                        else tuple(
                            (after.relation_name, target)
                            for target in relation_candidates(after.relation_name)
                        )
                    )
                    if len(targets) > 1:
                        diagnostics.append(
                            _diagnostic(
                                after, f"Ambiguous ANY input: {after.relation_name}"
                            )
                        )
                    if len(targets) == 1 and after.relation_name != targets[0][0]:
                        result = replace(after, relation_name=targets[0][0])
                    return _scalar_contracts(before, result)
                if (
                    type(after) is ast.DottedNameExpr
                    and from_binding is not None
                    and from_binding != from_source
                    and original_reads
                    and len(after.parts) == 2
                    and after.parts[0] == from_source
                    and after.parts[1] in from_fields
                    and not scopes.get(id(before))
                ):
                    result = replace(after, parts=(from_binding, after.parts[1]))
                return _scalar_contracts(before, result)

            rewritten = _rebuild(
                normalized_definition,
                normalize_iterator,
                occurrence_observer=any_trace.record,
            )
            assert isinstance(rewritten, (ast.TableDef, ast.QueryDef, ast.SelectBody))
            return rewritten

        definitions: list[ast.Definition] = []
        for position, definition in enumerate(source.script.definitions):
            if isinstance(definition, (ast.TableDef, ast.QueryDef)):
                rewritten = normalize_body(
                    definition,
                    (),
                    definition.parameters
                    if isinstance(definition, ast.QueryDef)
                    else (),
                )
                assert isinstance(rewritten, (ast.TableDef, ast.QueryDef))
                definitions.append(rewritten)
            elif isinstance(definition, ast.BlockRelationDef):
                local_lets = catalog.find_lets(position)
                parameters = definition.parameters

                def body(value: ast.RelationBody) -> ast.RelationBody:
                    if not isinstance(value, ast.SelectBody):
                        return value
                    rewritten = normalize_body(value, local_lets, parameters)
                    assert isinstance(rewritten, ast.SelectBody)
                    return rewritten

                let_relations = []
                for let in definition.let_relations:
                    normalized_body = body(let.body)
                    let_relations.append(
                        let
                        if normalized_body is let.body
                        else replace(let, body=normalized_body)
                    )
                normalized_body = body(definition.body)
                definitions.append(
                    definition
                    if normalized_body is definition.body
                    and all(
                        left is right
                        for left, right in zip(
                            let_relations, definition.let_relations, strict=True
                        )
                    )
                    else replace(
                        definition,
                        body=normalized_body,
                        let_relations=tuple(let_relations),
                    )
                )
            else:
                definitions.append(definition)
        unchanged = unchanged and all(
            left is right
            for left, right in zip(definitions, source.script.definitions, strict=True)
        )
        script = replace(source.script, definitions=tuple(definitions))
        normalized.append(
            replace(
                source,
                script=script,
                authored_script=source.authored_script or source.script,
                existence_generators=rebind_existence_generators(
                    source.script, script, source.existence_generators
                ),
                existence_values=rebind_any_values(
                    source.script, script, source.existence_values, trace=any_trace
                ),
            )
        )
    if unchanged and not diagnostics:
        # Windows alone, none taking an input's name: nothing to rewrite.
        return parsed
    inputs = tuple(normalized)
    return replace(
        parsed,
        parsed_inputs=inputs,
        modules=_build_project_logical_modules(
            parsed.compilation_mode, parsed.inputs, inputs
        ),
        diagnostics=(*parsed.diagnostics, *diagnostics),
    )


def project_owner_has_relationship_calls(
    root: ProjectSemanticResult, owner: ProjectDeclarationOccurrence
) -> bool:
    from pietto.semantic.inline_functions import _tree_nodes

    definition = owner.definition
    if not isinstance(definition, (ast.TableDef, ast.QueryDef)):
        return False
    modules = tuple(
        module for module in root.modules if module.path == owner.identity.module_path
    )
    if len(modules) != 1 or modules[0].parsed_input is None:
        return False
    names = {
        item.name for item in modules[0].parsed_input.script.relationship_templates
    }
    if not names:
        return False
    expressions = [
        binding.expression
        for binding in (
            definition.let_clause.bindings if definition.let_clause is not None else ()
        )
    ]
    if definition.where_clause is not None:
        expressions.append(definition.where_clause.expression)
    expressions.extend(item.expression for item in definition.select_items)
    return any(
        isinstance(node, ast.CallExpr)
        and isinstance(node.callee, ast.NameExpr)
        and node.callee.name in names
        for expression in expressions
        for node in _tree_nodes(expression)
    )
