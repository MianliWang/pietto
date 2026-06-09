"""Semantic IR construction entry point."""

from __future__ import annotations

from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    EnumDef,
    LiteralExpr,
    NameExpr,
    Node,
    Script,
    ShapeDef,
    SourceDef,
    TypeDef,
    TypeExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.ir.lowering import (
    lower_canonical_type_ref,
    lower_row_schema,
    lower_span,
    lower_type_ref,
)
from pietto.ir.model import (
    ConnectorIR,
    DefinitionIR,
    EnumIR,
    IrResult,
    NullabilityIR,
    ScriptIR,
    ShapeFieldIR,
    ShapeIR,
    SourceIR,
    StaticValue,
    SymbolId,
    SymbolNamespace,
    TypeIR,
)
from pietto.semantic import SemanticModel


def build_ir(
    script: Script,
    semantic_model: SemanticModel,
) -> IrResult:
    """Lower supported declarations from an already analyzed script."""

    definitions: list[DefinitionIR] = []
    diagnostics: list[Diagnostic] = []

    for definition in script.definitions:
        try:
            lowered = _lower_definition(definition, semantic_model)
        except _MissingSemanticFact as error:
            diagnostics.append(_missing_fact_diagnostic(error.node, error.message))
            continue
        if lowered is not None:
            definitions.append(lowered)

    if diagnostics:
        return IrResult(ir=None, diagnostics=tuple(diagnostics))
    return IrResult(ir=ScriptIR(definitions=tuple(definitions)), diagnostics=())


def _lower_definition(
    definition: Node,
    semantic_model: SemanticModel,
) -> DefinitionIR | None:
    """Lower one supported declaration and skip later-slice definitions."""

    if isinstance(definition, TypeDef):
        return _lower_type(definition, semantic_model)
    if isinstance(definition, EnumDef):
        return EnumIR(
            symbol=_symbol(SymbolNamespace.TYPE, definition.name),
            name=definition.name,
            members=definition.members,
            span=lower_span(definition.span),
        )
    if isinstance(definition, ShapeDef):
        return _lower_shape(definition, semantic_model)
    if isinstance(definition, SourceDef):
        return _lower_source(definition, semantic_model)
    return None


def _lower_type(
    definition: TypeDef,
    semantic_model: SemanticModel,
) -> TypeIR:
    """Lower one type definition after checking required semantic facts."""

    _require_type_facts(definition.base, semantic_model)
    return TypeIR(
        symbol=_symbol(SymbolNamespace.TYPE, definition.name),
        name=definition.name,
        declared_type=lower_type_ref(definition.base, semantic_model),
        canonical_type=lower_canonical_type_ref(definition.base, semantic_model),
        span=lower_span(definition.span),
    )


def _lower_shape(
    definition: ShapeDef,
    semantic_model: SemanticModel,
) -> ShapeIR:
    """Lower ordered shape fields without lowering modifiers or predicates."""

    fields: list[ShapeFieldIR] = []
    for field in definition.fields:
        _require_type_facts(field.type_expr, semantic_model)
        type_ref = lower_type_ref(field.type_expr, semantic_model)
        fields.append(
            ShapeFieldIR(
                name=field.name,
                type_ref=type_ref,
                nullability=NullabilityIR(type_ref.nullability),
                span=lower_span(field.span),
            )
        )
    return ShapeIR(
        symbol=_symbol(SymbolNamespace.TYPE, definition.name),
        name=definition.name,
        fields=tuple(fields),
        span=lower_span(definition.span),
    )


def _lower_source(
    definition: SourceDef,
    semantic_model: SemanticModel,
) -> SourceIR:
    """Lower one source using its analyzed row schema and static connector."""

    schema = semantic_model.source_row_schemas.get(definition)
    if schema is None:
        raise _MissingSemanticFact(definition, "source row schema")

    shape_symbol = None
    if definition.shape_name is not None:
        shape = semantic_model.type_symbols.get(definition.shape_name)
        if not isinstance(shape, ShapeDef):
            raise _MissingSemanticFact(definition, "resolved source shape")
        shape_symbol = _symbol(SymbolNamespace.TYPE, shape.name)

    return SourceIR(
        symbol=_symbol(SymbolNamespace.RELATION, definition.name),
        name=definition.name,
        shape_symbol=shape_symbol,
        row_schema=lower_row_schema(schema, semantic_model),
        connector=_lower_connector(definition),
        span=lower_span(definition.span),
    )


def _lower_connector(definition: SourceDef) -> ConnectorIR:
    """Copy a semantically validated connector call as static metadata."""

    connector = definition.connector
    if not isinstance(connector, CallExpr):
        raise _MissingSemanticFact(definition, "static source connector call")

    arguments: list[StaticValue] = []
    for argument in connector.arguments:
        if not isinstance(argument, LiteralExpr):
            raise _MissingSemanticFact(definition, "static connector argument")
        arguments.append(argument.value)

    if isinstance(connector.callee, NameExpr):
        name = connector.callee.name
    elif isinstance(connector.callee, DottedNameExpr):
        name = ".".join(connector.callee.parts)
    else:  # pragma: no cover - CallExpr constrains this union.
        raise _MissingSemanticFact(definition, "static connector name")

    return ConnectorIR(
        name=name,
        arguments=tuple(arguments),
        span=lower_span(connector.span),
    )


def _require_type_facts(
    type_expr: TypeExpr,
    semantic_model: SemanticModel,
) -> None:
    """Require all Phase 2 facts consumed by type metadata lowering."""

    if type_expr not in semantic_model.type_resolutions:
        raise _MissingSemanticFact(type_expr, "type resolution")
    if type_expr not in semantic_model.type_expansions:
        raise _MissingSemanticFact(type_expr, "canonical type expansion")
    if type_expr not in semantic_model.type_nullability:
        raise _MissingSemanticFact(type_expr, "effective nullability")


def _symbol(namespace: SymbolNamespace, name: str) -> SymbolId:
    """Build a stable IR symbol identity."""

    return SymbolId(namespace=namespace, name=name)


def _missing_fact_diagnostic(node: Node, fact: str) -> Diagnostic:
    """Report an absent semantic prerequisite at the affected declaration."""

    span = node.span
    return Diagnostic(
        code="PIE-I1000",
        severity=Severity.ERROR,
        message=f"Missing semantic fact required for IR lowering: {fact}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


class _MissingSemanticFact(Exception):
    """Internal control flow for expected IR prerequisite failures."""

    def __init__(self, node: Node, message: str) -> None:
        super().__init__(message)
        self.node = node
        self.message = message
