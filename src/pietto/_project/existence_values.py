"""Exact nested row scopes and checked scalar values of correlated ANY reads."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

from pietto import ast_nodes as ast
from pietto._project.model import (
    ProjectResolvedTypeKind,
    ProjectSemanticResult,
    ProjectRowField,
    ProjectRowSchema,
)
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.module_relation_resolution import (
    ProjectExpressionBlockPosition,
    ProjectResolvedExpressionBlockRead,
    ProjectResolvedModuleRelationReference,
)

from pietto._project.row_expression_type_facts import (
    is_nested_relation_field,
    merge_shape_typed_diagnostics,
    nested_value_diagnostic,
    project_row_field_to_semantic_value_type,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.expressions import (
    LetValues,
    infer_row_expression,
    is_unknown_function_call,
)
from pietto.semantic.let_bindings import let_expansion_diagnostics
from pietto.semantic.existence_generators import AnyUseInfo, AnyValueInfo
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    RowSchema,
    TypeKind,
    ValueType,
    ValueTypeKind,
)

if TYPE_CHECKING:
    from pietto.semantic.relationship_predicates import RelationshipCallFailure

    from pietto._project.module_semantic_fact_preservation import (
        ProjectModuleRelationSemanticFacts,
    )
    from pietto._project.let_scope_facts import ProjectRelationLetScopeFacts
    from pietto._project.project_final_outputs import (
        ProjectConcreteEffectiveOutputEntry,
        ProjectEffectiveOutputCompletionEntry,
    )
    from pietto._project.project_join_conditions import ProjectJoinConditionField
    from pietto._project.project_relationship_uses import (
        ProjectRelationBindingOccurrence,
    )
    from pietto._project.project_scalar_references import ProjectScalarEnvironmentField
    from pietto._project.project_scalar_namespaces import ProjectJoinedLetValue

__all__ = ()


def existence_uses_for_owner(
    root: ProjectSemanticResult, owner: ProjectDeclarationOccurrence
) -> tuple[AnyUseInfo, ...]:
    modules = tuple(
        module for module in root.modules if module.path == owner.identity.module_path
    )
    if len(modules) != 1 or modules[0].parsed_input is None:
        return ()
    return tuple(
        use
        for use in modules[0].parsed_input.existence_generators
        if use.owner is owner.definition
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectAnyRowBinding:
    """The local row of one exact, dependency-resolved ANY occurrence."""

    owner: ProjectDeclarationOccurrence
    resolution: ProjectResolvedExpressionBlockRead
    origin: AnyValueInfo

    def __post_init__(self) -> None:
        if (
            type(self.owner) is not ProjectDeclarationOccurrence
            or type(self.resolution) is not ProjectResolvedExpressionBlockRead
            or self.resolution.read.owner is not self.owner
            or type(self.resolution.read.expression) is not ast.AnyExpr
            or type(self.origin) is not AnyValueInfo
            or self.origin.expression is not self.resolution.read.expression
            or self.origin.owner is not self.owner.definition
        ):
            raise ValueError("ANY row binding requires its exact resolved read.")

    @property
    def expression(self) -> ast.AnyExpr:
        expression = self.resolution.read.expression
        assert type(expression) is ast.AnyExpr
        return expression

    @property
    def name(self) -> str:
        return self.expression.binding_name

    @property
    def target(self) -> ProjectDeclarationOccurrence | None:
        symbol = self.resolution.target_symbol
        return None if symbol is None else symbol.target_occurrence


def any_bindings_for_expression(
    root: ProjectSemanticResult,
    owner: ProjectDeclarationOccurrence,
    expression: ast.Expression,
) -> tuple[ProjectAnyRowBinding, ...]:
    """Use dependency resolution, including blocked/cyclic reads, never relookup."""

    from pietto.semantic.inline_functions import _tree_nodes

    expressions = tuple(
        node for node in _tree_nodes(expression) if type(node) is ast.AnyExpr
    )
    if not expressions:
        return ()
    resolutions = root.module_relation_resolutions
    if resolutions is None:
        raise ValueError("ANY binding requires its module dependency authority.")
    environments = resolutions.find_module_path(owner.identity.module_path)
    if len(environments) != 1:
        raise ValueError("ANY binding requires one exact module environment.")
    modules = tuple(
        module for module in root.modules if module.path == owner.identity.module_path
    )
    if len(modules) != 1 or modules[0].parsed_input is None:
        raise ValueError("ANY binding requires its exact authored source inventory.")
    origins = modules[0].parsed_input.existence_values
    bindings: list[ProjectAnyRowBinding] = []
    for node in expressions:
        matches = tuple(
            item
            for item in environments[0].expression_reads
            if item.read.owner is owner and item.read.expression is node
        )
        if len(matches) != 1:
            raise ValueError("ANY binding requires one complete dependency occurrence.")
        authored = tuple(
            info
            for info in origins
            if info.expression is node and info.owner is owner.definition
        )
        if len(authored) != 1:
            raise ValueError("ANY binding requires one exact authored origin.")
        bindings.append(
            ProjectAnyRowBinding(owner=owner, resolution=matches[0], origin=authored[0])
        )
    return tuple(bindings)


def any_argument_scopes(
    expression: ast.Expression,
    bindings: tuple[ProjectAnyRowBinding, ...],
) -> dict[ast.NameExpr, tuple[ProjectAnyRowBinding, ...]]:
    """Keep lexical binder shadowing local to each predicate body."""

    from pietto.semantic.inline_functions import _children

    by_expression = {id(binding.expression): binding for binding in bindings}
    scopes: dict[ast.NameExpr, tuple[ProjectAnyRowBinding, ...]] = {}
    pending: list[tuple[object, tuple[ProjectAnyRowBinding, ...]]] = [(expression, ())]
    while pending:
        node, scope = pending.pop()
        if type(node) is ast.AnyExpr:
            binding = by_expression.get(id(node))
            if binding is None:
                raise ValueError("ANY lexical scope lost its resolved occurrence.")
            nested = tuple(item for item in scope if item.name != binding.name)
            pending.append((node.predicate, (*nested, binding)))
            continue
        if type(node) is ast.NameExpr:
            scopes[node] = scope
        pending.extend((child, scope) for child in reversed(_children(node) or ()))
    return scopes


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectAnyInput:
    binding: ProjectAnyRowBinding
    schema: ProjectRowSchema | None
    semantic: ProjectModuleRelationSemanticFacts | None = None
    entry: ProjectConcreteEffectiveOutputEntry | None = None

    def __post_init__(self) -> None:
        if self.semantic is not None:
            if self.entry is not None or self.semantic.owner is not self.binding.target:
                raise ValueError("ANY input requires one exact producer authority.")
            if self.schema is not self.semantic.state.schema:
                raise ValueError("ANY input schema lost its semantic producer.")
        elif self.entry is not None:
            from pietto._project.project_final_outputs import _entry_schema

            if (
                self.entry.owner is not self.binding.target
                or self.schema is not _entry_schema(self.entry)
            ):
                raise ValueError("ANY input schema lost its completed producer.")
        elif self.schema is not None:
            raise ValueError("ANY input schema requires its producer authority.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectAnyField:
    binding: (
        ProjectAnyRowBinding
        | ProjectRelationBindingOccurrence
        | ProjectResolvedModuleRelationReference
    )
    source_field: (
        ProjectRowField | ProjectJoinConditionField | ProjectScalarEnvironmentField
    )

    def __post_init__(self) -> None:
        from pietto._project.project_join_conditions import ProjectJoinConditionField
        from pietto._project.project_scalar_references import (
            ProjectScalarEnvironmentField,
        )
        from pietto._project.project_relationship_uses import (
            ProjectRelationBindingOccurrence,
        )

        if type(self.source_field) not in (
            ProjectRowField,
            ProjectJoinConditionField,
            ProjectScalarEnvironmentField,
        ):
            raise TypeError("ANY field requires an exact checked input field.")
        if (
            type(self.source_field) is ProjectJoinConditionField
            and self.source_field.binding is not self.binding
        ):
            raise ValueError("ANY capture lost its exact pre-match row occurrence.")
        if (
            type(self.source_field) is ProjectScalarEnvironmentField
            and type(self.binding) is not ProjectRelationBindingOccurrence
        ):
            raise ValueError("ANY joined capture requires its exact row binding.")
        if (
            isinstance(self.binding, ProjectAnyRowBinding)
            and type(self.source_field) is not ProjectRowField
        ):
            raise ValueError("ANY local input requires a producer schema field.")

    @property
    def binding_name(self) -> str:
        from pietto._project.project_relationship_uses import (
            ProjectRelationBindingOccurrence,
        )

        if isinstance(
            self.binding, (ProjectAnyRowBinding, ProjectRelationBindingOccurrence)
        ):
            return self.binding.name
        clause = self.binding.reference.from_clause
        return clause.binding_name or clause.source_name

    @property
    def evidence(self) -> ProjectRowField:
        from pietto._project.project_join_conditions import ProjectJoinConditionField

        source = self.source_field
        from pietto._project.project_scalar_references import (
            ProjectScalarEnvironmentField,
        )

        if isinstance(source, ProjectRowField):
            return source
        if isinstance(source, ProjectJoinConditionField):
            return source.input_field.evidence
        if isinstance(source, ProjectScalarEnvironmentField):
            return source.evidence
        raise TypeError("ANY field requires an exact checked input field.")

    @property
    def value_type(self) -> ValueType:
        from pietto._project.project_join_conditions import ProjectJoinConditionField
        from pietto._project.project_scalar_references import (
            ProjectScalarEnvironmentField,
        )

        source = self.source_field
        if isinstance(source, ProjectRowField):
            return project_row_field_to_semantic_value_type(source, source.nullability)
        if isinstance(
            source, (ProjectJoinConditionField, ProjectScalarEnvironmentField)
        ):
            return source.value_type
        raise TypeError("ANY field requires an exact checked input field.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectAnyLetValue:
    binding: ast.LetBinding
    expression: ast.Expression
    value_type: ValueType
    authority: ProjectJoinedLetValue | ProjectRelationLetScopeFacts

    def __post_init__(self) -> None:
        from pietto._project.let_scope_facts import ProjectRelationLetScopeFacts
        from pietto._project.project_scalar_namespaces import ProjectJoinedLetValue

        if type(self.authority) is ProjectJoinedLetValue:
            valid = (
                self.authority.occurrence.binding is self.binding
                and self.authority.value_type is self.value_type
                and self.authority.normalized_expression is self.expression
            )
        elif type(self.authority) is ProjectRelationLetScopeFacts:
            valid = (
                any(binding is self.binding for binding in self.authority.bindings)
                and self.authority.value_types.get(self.binding.name) is self.value_type
            )
        else:
            valid = False
        if not valid:
            raise ValueError("ANY LET capture requires an exact admitted value.")

    @property
    def existence_values(self) -> tuple[ProjectAnyValue, ...]:
        from pietto._project.project_scalar_namespaces import ProjectJoinedLetValue

        if type(self.authority) is ProjectJoinedLetValue:
            return self.authority.existence_values
        return tuple(
            value
            for value in self.authority.existence_values
            if value.context is self.binding
        )

    @property
    def value_types(self) -> Mapping[ast.Expression, ValueType]:
        from pietto._project.project_scalar_namespaces import ProjectJoinedLetValue

        from pietto._project.let_scope_facts import ProjectRelationLetScopeFacts

        if isinstance(self.authority, ProjectJoinedLetValue):
            return self.authority.value_types
        if isinstance(self.authority, ProjectRelationLetScopeFacts):
            return self.authority.expression_value_types
        raise TypeError("ANY LET capture requires an exact admitted value.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectAnyReference:
    expression: ast.NameExpr | ast.DottedNameExpr
    candidates: tuple[ProjectAnyField | ProjectAnyLetValue, ...]

    @property
    def target(self) -> ProjectAnyField | ProjectAnyLetValue | None:
        return self.candidates[0] if len(self.candidates) == 1 else None


def _row_argument_ids(
    failures: Sequence[RelationshipCallFailure],
    direct_nodes: tuple[ast.Expression, ...],
) -> frozenset[int]:
    """The bare-name arguments of a failed relationship call, or of an unknown
    function, which typing reports first (PIE-S2103): each may name a row, as
    for a relationship the module does not declare, and is no field read."""

    return frozenset(
        id(argument)
        for call in (
            *(failure.expression for failure in failures),
            *(
                node
                for node in direct_nodes
                if type(node) is ast.CallExpr and is_unknown_function_call(node)
            ),
        )
        for argument in call.arguments
        if isinstance(argument, ast.NameExpr)
    )


def _direct_predicate_nodes(predicate: ast.Expression) -> tuple[ast.Expression, ...]:
    from pietto.semantic.aggregates import child_expressions

    nodes: list[ast.Expression] = []
    pending = [predicate]
    while pending:
        node = pending.pop()
        if isinstance(node, ast.AnyExpr):
            continue
        nodes.append(node)
        pending.extend(reversed(child_expressions(node)))
    return tuple(nodes)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectAnyValue:
    input: ProjectAnyInput
    context: ast.Node
    expression: ast.AnyExpr
    fields: tuple[ProjectAnyField, ...]
    references: tuple[ProjectAnyReference, ...]
    nested: tuple[ProjectAnyValue, ...]
    value_type: ValueType
    value_types: Mapping[ast.Expression, ValueType]
    diagnostics: tuple[Diagnostic, ...]
    failed_relationship_calls: tuple[RelationshipCallFailure, ...] = ()
    predicate_typed: bool = False

    def __post_init__(self) -> None:
        if self.expression.binding_name != self.input.binding.name:
            raise ValueError("ANY value lost its exact local row binding.")
        if any(field.binding is not self.input.binding for field in self.fields):
            raise ValueError("ANY local fields require their exact occurrence.")
        if self.value_types.get(self.expression) is not self.value_type:
            raise ValueError("ANY value requires its checked non-null Bool type.")
        from pietto._project.row_expression_type_facts import (
            scalar_field_reference_leaves,
        )

        direct_nodes = _direct_predicate_nodes(self.predicate)
        failures = self.failed_relationship_calls
        if len({id(failure.expression) for failure in failures}) != len(
            failures
        ) or any(
            not any(failure.expression is node for node in direct_nodes)
            for failure in failures
        ):
            raise ValueError("ANY failures require exact direct predicate occurrences.")
        if failures and self.value_type.kind is ValueTypeKind.KNOWN:
            raise ValueError("ANY with a failed relationship call cannot be ready.")
        if self.predicate_typed and any(
            not any(diagnostic is found for found in self.diagnostics)
            for failure in failures
            for diagnostic in failure.diagnostics
        ):
            raise ValueError("Typed ANY must retain relationship call diagnostics.")
        ignored_ids = _row_argument_ids(failures, direct_nodes)
        leaves = tuple(
            leaf
            for leaf in scalar_field_reference_leaves(self.predicate)
            if id(leaf) not in ignored_ids
        )
        if len(leaves) != len(self.references) or any(
            reference.expression is not leaf
            for reference, leaf in zip(self.references, leaves, strict=True)
        ):
            raise ValueError(
                "ANY references require every direct scoped field occurrence."
            )
        schema = self.input.schema
        if (
            schema is not None
            and not schema.is_unknown
            and (
                len(self.fields) != len(schema.fields)
                or any(
                    field.source_field is not source
                    for field, source in zip(
                        self.fields, schema.fields.values(), strict=True
                    )
                )
            )
        ):
            raise ValueError(
                "ANY local fields require the exact complete producer schema."
            )
        if self.value_type.kind is ValueTypeKind.KNOWN and (
            self.value_type != _BOOL
            or schema is None
            or schema.is_unknown
            or any(item.severity is Severity.ERROR for item in self.diagnostics)
            or any(reference.target is None for reference in self.references)
        ):
            raise ValueError(
                "Ready ANY requires a checked predicate and non-null Bool result."
            )
        object.__setattr__(
            self, "value_types", MappingProxyType(dict(self.value_types))
        )

    @property
    def authored_expression(self) -> ast.AnyExpr:
        return self.input.binding.origin.authored_expression

    @property
    def predicate(self) -> ast.Expression:
        return self.expression.predicate

    @property
    def captures(self) -> tuple[ProjectAnyReference, ...]:
        return tuple(
            reference
            for reference in self.references
            if isinstance(reference.target, ProjectAnyLetValue)
            or isinstance(reference.target, ProjectAnyField)
            and reference.target.binding is not self.input.binding
        )


def _input(
    root: ProjectSemanticResult,
    binding: ProjectAnyRowBinding,
    available: tuple[ProjectEffectiveOutputCompletionEntry, ...],
) -> ProjectAnyInput:
    from pietto._project.project_completion import ProjectExistingEffectiveOutput
    from pietto._project.project_final_outputs import (
        ProjectCompletedEffectiveOutput,
        ProjectCompletedSetOutput,
        ProjectCompletedValuesOutput,
        _entry_schema,
    )

    if binding.target is None:
        return ProjectAnyInput(binding=binding, schema=None)
    if available:
        matches = tuple(entry for entry in available if entry.owner is binding.target)
        if len(matches) != 1:
            raise ValueError("Scheduled ANY input lost its exact earlier producer.")
        entry = matches[0]
        if isinstance(
            entry,
            (
                ProjectExistingEffectiveOutput,
                ProjectCompletedEffectiveOutput,
                ProjectCompletedSetOutput,
                ProjectCompletedValuesOutput,
            ),
        ):
            return ProjectAnyInput(
                binding=binding, schema=_entry_schema(entry), entry=entry
            )
        return ProjectAnyInput(binding=binding, schema=None)
    facts = root.module_semantic_facts
    matches = () if facts is None else facts.find_owner(binding.target)
    if len(matches) == 1 and matches[0].state.schema is not None:
        return ProjectAnyInput(
            binding=binding, schema=matches[0].state.schema, semantic=matches[0]
        )
    return ProjectAnyInput(binding=binding, schema=None)


def _context(binding: ProjectAnyRowBinding) -> ast.Node:
    definition = binding.owner.definition
    assert isinstance(definition, (ast.TableDef, ast.QueryDef))
    read = binding.resolution.read
    position = read.position
    if position is ProjectExpressionBlockPosition.JOIN_ON:
        node = definition.join_clauses[read.container_ordinal].on_clause
    elif position is ProjectExpressionBlockPosition.WHERE:
        node = definition.where_clause
    elif position is ProjectExpressionBlockPosition.SELECT:
        node = definition.select_items[read.container_ordinal]
    elif position is ProjectExpressionBlockPosition.LET:
        assert definition.let_clause is not None
        node = definition.let_clause.bindings[read.container_ordinal]
    else:
        raise ValueError("ANY value requires an admitted scalar expression context.")
    assert node is not None
    return node


def analyze_any_values(
    *,
    root: ProjectSemanticResult,
    owner: ProjectDeclarationOccurrence,
    authored: ast.Expression,
    expression: ast.Expression,
    outer_fields: tuple[ProjectAnyField, ...],
    let_values: tuple[ProjectAnyLetValue, ...] = (),
    available: tuple[ProjectEffectiveOutputCompletionEntry, ...] = (),
    normalized_any: tuple[tuple[ast.AnyExpr, ast.AnyExpr], ...] = (),
    retained_bindings: tuple[ProjectAnyRowBinding, ...] | None = None,
    failed_relationship_calls: Sequence[RelationshipCallFailure] = (),
) -> tuple[ProjectAnyValue, ...]:
    """Check nested predicates at this actual scalar site's input checkpoint."""

    from pietto.semantic.aggregates import (
        child_expressions,
        contains_semantic_aggregate,
    )
    from pietto.semantic.inline_functions import _tree_nodes
    from pietto.semantic.predicate_checks import _check_bool_expression

    bindings = (
        any_bindings_for_expression(root, owner, authored)
        if retained_bindings is None
        else retained_bindings
    )
    if not bindings:
        return ()
    normalized = tuple(
        node for node in _tree_nodes(expression) if type(node) is ast.AnyExpr
    )
    if len(normalized) != len(bindings):
        raise ValueError("ANY normalization must retain every scoped occurrence.")
    rewritten = {id(before): after for before, after in normalized_any}
    if len(rewritten) != len(normalized_any):
        raise ValueError("ANY normalization cannot repeat an authored occurrence.")
    by_node: dict[int, ProjectAnyRowBinding] = {}
    for binding in bindings:
        current = rewritten.get(id(binding.expression), binding.expression)
        if not any(current is node for node in normalized):
            raise ValueError("ANY normalization lost its explicit identity mapping.")
        if id(current) in by_node:
            raise ValueError("ANY normalization cannot merge scoped occurrences.")
        by_node[id(current)] = binding

    def analyze(
        node: ast.AnyExpr,
        enclosing: tuple[ProjectAnyField, ...],
        shadows: frozenset[str],
        parent: ast.AnyExpr | None = None,
        unknown_rows: frozenset[str] = frozenset(),
    ) -> ProjectAnyValue:
        binding = by_node[id(node)]
        incoming = _input(root, binding, available)
        schema = incoming.schema
        # Generator rows of unknown type in scope: their own `any(...)` is
        # refused, and a read that may name one of their fields is not.
        unknown_rows = (
            unknown_rows | {binding.name}
            if schema is None or schema.is_unknown
            else unknown_rows - {binding.name}
        )
        fields = (
            ()
            if schema is None or schema.is_unknown
            else tuple(
                ProjectAnyField(binding=binding, source_field=field)
                for field in schema.fields.values()
            )
        )
        visible = tuple(
            field for field in enclosing if field.binding_name != binding.name
        )
        visible = (*visible, *fields)
        hidden = shadows | {binding.name}
        root_context = _context(binding)
        blocked_lets: frozenset[str] = frozenset()
        definition = owner.definition
        assert isinstance(definition, (ast.TableDef, ast.QueryDef))
        if type(root_context) is ast.LetBinding:
            assert definition.let_clause is not None
            positions = tuple(
                index
                for index, item in enumerate(definition.let_clause.bindings)
                if item is root_context
            )
            if len(positions) != 1:
                raise ValueError("ANY LET scope requires its exact prefix occurrence.")
            blocked_lets = frozenset(
                item.name for item in definition.let_clause.bindings[positions[0] :]
            )
        direct_nodes = _direct_predicate_nodes(node.predicate)
        local_failures = tuple(
            failure
            for failure in failed_relationship_calls
            if any(failure.expression is item for item in direct_nodes)
        )
        ignored_row_arguments = _row_argument_ids(local_failures, direct_nodes)
        references: list[ProjectAnyReference] = []
        nested: list[ProjectAnyValue] = []
        types: dict[ast.Expression, ValueType] = {}
        diagnostics: list[Diagnostic] = []
        # An input whose name does not resolve reports that itself, and an
        # earlier relation that fails reports its own failure.
        if (schema is None or schema.is_unknown) and not (
            binding.target is None
            or (
                incoming.entry is None
                and any(entry.owner is binding.target for entry in available)
            )
        ):
            diagnostics.append(_diagnostic(node, "ANY input relation is unavailable."))
        if contains_semantic_aggregate(node.predicate):
            diagnostics.append(
                _diagnostic(
                    node.predicate,
                    "Aggregate expressions are unavailable in ANY predicates.",
                    code="PIE-S2335",
                )
            )
        pending = [node.predicate]
        while pending:
            leaf = pending.pop()
            if type(leaf) is ast.AnyExpr:
                value = analyze(leaf, visible, hidden, node, unknown_rows)
                nested.append(value)
                types.update(value.value_types)
                diagnostics.extend(value.diagnostics)
                continue
            if isinstance(leaf, (ast.NameExpr, ast.DottedNameExpr)):
                if id(leaf) in ignored_row_arguments:
                    continue
                candidates: tuple[ProjectAnyField | ProjectAnyLetValue, ...]
                generator_only = False
                if type(leaf) is ast.NameExpr:
                    values = tuple(
                        value
                        for value in let_values
                        if value.binding.name == leaf.name and leaf.name not in hidden
                    )
                    named = (
                        ()
                        if values or leaf.name in hidden
                        else tuple(
                            field
                            for field in visible
                            if field.evidence.name == leaf.name
                        )
                    )
                    outer = tuple(
                        field
                        for field in named
                        if not isinstance(field.binding, ProjectAnyRowBinding)
                    )
                    # As in a single file, a bare name that a generator row
                    # also has is ambiguous; a project reads a generator
                    # field only qualified.
                    candidates = values or (named if len(named) > 1 else outer)
                    generator_only = bool(named) and not outer
                else:
                    assert isinstance(leaf, ast.DottedNameExpr)
                    parts = leaf.parts
                    candidates = tuple(
                        field
                        for field in visible
                        if parts == (field.binding_name, field.evidence.name)
                    )
                reference = ProjectAnyReference(expression=leaf, candidates=candidates)
                references.append(reference)
                if (
                    len(candidates) == 1
                    and type(candidates[0]) is ProjectAnyField
                    and is_nested_relation_field(candidates[0].evidence)
                ):
                    # A collected relation has no value to test (PIE-S2805).
                    diagnostics.append(nested_value_diagnostic(leaf, "an ANY test"))
                elif reference.target is None:
                    if (
                        type(leaf) is ast.NameExpr
                        and leaf.name in blocked_lets
                        and leaf.name not in hidden
                    ):
                        from pietto.semantic.let_bindings import (
                            _invalid_let_dependency_diagnostic,
                        )

                        assert type(root_context) is ast.LetBinding
                        diagnostics.append(
                            _invalid_let_dependency_diagnostic(
                                leaf,
                                leaf.name,
                                reason="Let binding cannot reference itself"
                                if leaf.name == root_context.name
                                else "Let binding cannot reference a later binding",
                            )
                        )
                    else:
                        # The generator row a read may name: any for a bare
                        # name, else the one its qualifier names.
                        head = None if isinstance(leaf, ast.NameExpr) else leaf.parts[0]
                        may_read_unknown = bool(unknown_rows) and (
                            head is None or head in unknown_rows
                        )
                        if candidates or not (generator_only or may_read_unknown):
                            spelling = (
                                leaf.name
                                if isinstance(leaf, ast.NameExpr)
                                else ".".join(leaf.parts)
                            )
                            diagnostics.append(
                                _diagnostic(
                                    leaf,
                                    (
                                        "Ambiguous"
                                        if candidates
                                        else "Unknown or unavailable"
                                    )
                                    + f" field in ANY predicate: {spelling}",
                                    code="PIE-S2102",
                                )
                            )
                        elif generator_only or not (
                            binding.name in unknown_rows
                            and head in {None, binding.name}
                        ):
                            # A read that may name a field of this generator's
                            # row of unknown type is not reported: its
                            # `any(...)` is.
                            diagnostics.append(
                                _diagnostic(
                                    leaf, "ANY predicate reference is unavailable."
                                )
                            )
                else:
                    types[leaf] = reference.target.value_type
                continue
            pending.extend(reversed(child_expressions(leaf)))
        definition = owner.definition
        assert isinstance(definition, (ast.TableDef, ast.QueryDef))
        diagnostics.extend(
            let_expansion_diagnostics(
                definition,
                {value.binding.name: value.value_type for value in let_values},
                extra_expressions=(node.predicate,),
            )
        )
        value_type = _UNKNOWN
        predicate_typed = not diagnostics
        if not diagnostics:

            def infer(
                read_types: dict[ast.Expression, ValueType], found: list[Diagnostic]
            ) -> ValueType:
                return infer_row_expression(
                    node.predicate,
                    RowSchema(),
                    read_types,
                    found,
                    report_unknown_name=True,
                    bare_value_types={
                        value.binding.name: value.value_type
                        for value in let_values
                        if value.binding.name not in hidden
                    },
                    bare_value_expressions=LetValues(
                        {
                            value.binding.name: value.expression
                            for value in let_values
                            if value.binding.name not in hidden
                        },
                        field_types={
                            expression: value_type
                            for value in let_values
                            if value.binding.name not in hidden
                            for expression, value_type in value.value_types.items()
                        },
                    ),
                    failed_relationship_calls=local_failures,
                )

            # A field of a shape is that shape, as in a single file, for the
            # operators and functions that refuse it (`home + 1`).
            shaped = {
                reference.expression: project_row_field_to_semantic_value_type(
                    shape, shape.nullability, shapes=True
                )
                for reference in references
                if isinstance(reference.target, ProjectAnyField)
                and isinstance(shape := reference.target.source_field, ProjectRowField)
                and shape.resolved_type.kind is ProjectResolvedTypeKind.SHAPE
            }
            read_types = {**types, **shaped}
            start = len(diagnostics)
            inferred = infer(types, diagnostics)
            if shaped:
                found: list[Diagnostic] = []
                infer(read_types, found)
                merge_shape_typed_diagnostics(diagnostics, start, found)
            for failure in local_failures:
                for diagnostic in failure.diagnostics:
                    if not any(diagnostic is item for item in diagnostics):
                        diagnostics.append(diagnostic)
            if (
                type(node.predicate) is ast.LiteralExpr
                and node.predicate.value is None
                and not diagnostics
            ):
                inferred = ValueType(
                    resolved_type=_BOOL.resolved_type,
                    nullability=EffectiveNullability.NULLABLE,
                )
                types[node.predicate] = inferred
            problem = _check_bool_expression(
                node.predicate, context="ANY", expression_value_types=types
            )
            if problem is not None:
                diagnostics.append(problem)
            elif (
                inferred.kind is ValueTypeKind.UNKNOWN
                and not diagnostics
                # An input with no row to read, also a nested `any(...)`'s,
                # reports why, or follows a failure that is reported.
                and schema is not None
                and not schema.is_unknown
                and all(
                    value.value_type.kind is ValueTypeKind.KNOWN for value in nested
                )
            ):
                diagnostics.append(
                    _diagnostic(
                        node.predicate,
                        "ANY predicate requires a known Bool expression.",
                        code="PIE-S2202",
                    )
                )
            if (
                inferred.kind is ValueTypeKind.KNOWN
                and schema is not None
                and not schema.is_unknown
                and not any(item.severity is Severity.ERROR for item in diagnostics)
            ):
                value_type = _BOOL
        types[node] = value_type
        if value_type.kind is ValueTypeKind.KNOWN:
            value_type = infer_row_expression(
                node, RowSchema(), types, diagnostics, report_unknown_name=True
            )
            types[node] = value_type
        return ProjectAnyValue(
            input=incoming,
            context=_context(binding) if parent is None else parent,
            expression=node,
            fields=fields,
            references=tuple(references),
            nested=tuple(nested),
            value_type=value_type,
            value_types=types,
            diagnostics=tuple(diagnostics),
            failed_relationship_calls=local_failures,
            predicate_typed=predicate_typed,
        )

    found: list[ProjectAnyValue] = []
    pending = [expression]
    while pending:
        node = pending.pop()
        if type(node) is ast.AnyExpr:
            found.append(analyze(node, outer_fields, frozenset()))
        else:
            pending.extend(reversed(child_expressions(node)))
    return tuple(found)


def _diagnostic(
    node: ast.Expression, message: str, *, code: str = "PIE-S2334"
) -> Diagnostic:
    span = node.span
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


_BOOL = ValueType(
    resolved_type=ResolvedType(name="Bool", kind=TypeKind.BUILTIN),
    nullability=EffectiveNullability.NON_NULL,
)
_UNKNOWN = ValueType(
    resolved_type=ResolvedType(name="<unknown>", kind=TypeKind.UNKNOWN),
    nullability=EffectiveNullability.UNKNOWN,
    kind=ValueTypeKind.UNKNOWN,
)


def validate_any_values(
    owner: ProjectDeclarationOccurrence,
    expression: ast.Expression,
    values: tuple[ProjectAnyValue, ...],
) -> None:
    """Require one checked fact for every scalar ANY scope, including nested ones."""

    from pietto.semantic.aggregates import child_expressions

    pending = [(expression, values)]
    while pending:
        root, facts = pending.pop()
        occurrences: list[ast.AnyExpr] = []
        nodes = [root]
        while nodes:
            node = nodes.pop()
            if type(node) is ast.AnyExpr:
                occurrences.append(node)
            else:
                nodes.extend(reversed(child_expressions(node)))
        if (
            type(facts) is not tuple
            or len(facts) != len(occurrences)
            or any(
                type(fact) is not ProjectAnyValue
                or fact.input.binding.owner is not owner
                or fact.expression is not occurrence
                for fact, occurrence in zip(facts, occurrences, strict=True)
            )
        ):
            raise ValueError("Scalar ANY requires complete exact checked occurrences.")
        pending.extend((fact.predicate, fact.nested) for fact in reversed(facts))


def any_value_origins(
    root: ProjectSemanticResult, owner: ProjectDeclarationOccurrence
) -> tuple[AnyValueInfo, ...]:
    modules = tuple(
        module for module in root.modules if module.path == owner.identity.module_path
    )
    if len(modules) != 1 or modules[0].parsed_input is None:
        return ()
    return tuple(
        value
        for value in modules[0].parsed_input.existence_values
        if value.owner is owner.definition
    )


def expression_has_any_values(
    root: ProjectSemanticResult,
    owner: ProjectDeclarationOccurrence,
    expression: ast.Expression,
) -> bool:
    from pietto.semantic.inline_functions import _tree_nodes

    nodes = {id(node) for node in _tree_nodes(expression)}
    return any(
        id(value.expression) in nodes for value in any_value_origins(root, owner)
    )
