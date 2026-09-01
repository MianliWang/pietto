"""Convert generated ANTLR parse trees into Pietto-owned AST dataclasses."""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, cast

from antlr4 import ParserRuleContext
from antlr4.Token import Token
from antlr4.tree.Tree import TerminalNode

from pietto import _window_identity
from pietto.ast_nodes import (
    Annotation,
    AuthoredJoinKind,
    AuthoredWindowFrame,
    AuthoredWindowFrameExclusion,
    AuthoredWindowFrameKind,
    AuthoredWindowNthDirection,
    AuthoredWindowNullTreatment,
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    CheckDef,
    ComparisonExpr,
    ConstraintDef,
    DeriveDef,
    DottedNameExpr,
    EnsureClause,
    EnumDef,
    ExportItem,
    ExportStatement,
    Expression,
    FieldDef,
    FromClause,
    GroupByClause,
    GroupByItem,
    Header,
    IndexDef,
    ImportItem,
    ImportStatement,
    IsNullExpr,
    JoinClause,
    JoinTraversalStep,
    LetBinding,
    LetClause,
    LimitClause,
    LiteralExpr,
    NameExpr,
    ModuleDeclarationKind,
    NamedWindowDeclaration,
    NamedWindowReference,
    Nullability,
    OrderByClause,
    OrderItem,
    Parameter,
    QueryDef,
    RelationshipEndpoint,
    RelationshipMatchClause,
    RelationshipMetadata,
    Script,
    ShapeDef,
    ShapeItem,
    SourceDef,
    Span,
    SelectItem,
    SatisfyingClause,
    TableDef,
    TypeArgument,
    TypeDef,
    TypeExpr,
    UnaryExpr,
    UniqueDef,
    WhereClause,
    WindowExpr,
    WindowFrameBound,
    WindowFrameBoundKind,
    WindowFrameUnit,
    WindowNthDirectionKind,
    WindowNullTreatmentKind,
    WindowSpec,
    WindowUseKind,
)
from pietto.errors import AstBuildError, source_path
from pietto.generated.PiettoParser import PiettoParser

if TYPE_CHECKING:

    class PiettoVisitor:
        """Typing boundary for the dynamically typed generated visitor."""

        def visit(self, tree: Any) -> Any: ...

        def visitChildren(self, node: Any) -> Any: ...

else:
    from pietto.generated.PiettoVisitor import PiettoVisitor

_MAX_NUMERIC_LITERAL_LENGTH = 4096
_AntlrContext = Any


class _TerminalNode(Protocol):
    """ANTLR terminal operations used by the handwritten AST boundary."""

    def getText(self) -> str: ...

    def getSymbol(self) -> Token: ...


class AstBuilder(PiettoVisitor):
    """Build an ANTLR-independent AST from a successfully parsed script."""

    def __init__(self, path: str | Path | None) -> None:
        """Create a builder whose AST spans use the supplied source path."""

        self.path = source_path(path)

    def visitScript(self, ctx: _AntlrContext) -> Script:
        """Build the root script node."""

        header = self.visit(ctx.header()) if ctx.header() is not None else None
        definitions = tuple(self.visit(item) for item in ctx.definition())
        relationships = tuple(self.visit(item) for item in ctx.relationshipDefinition())
        module_statements = tuple(self.visit(item) for item in ctx.moduleStatement())
        return Script(
            span=self._span(ctx),
            header=cast(Header | None, header),
            definitions=definitions,
            relationships=relationships,
            module_statements=module_statements,
        )

    def visitModuleStatement(
        self, ctx: _AntlrContext
    ) -> ImportStatement | ExportStatement:
        """Build one source-ordered parser-only module statement."""

        if ctx.importStatement() is not None:
            return self.visit(ctx.importStatement())
        return self.visit(ctx.exportStatement())

    def visitImportStatement(self, ctx: _AntlrContext) -> ImportStatement:
        """Build an import block without resolving its target or names."""

        target = ctx.importTarget()
        return ImportStatement(
            span=self._span(ctx),
            target=self._decode_string_literal(target),
            target_span=self._span(target),
            items=tuple(self.visit(item) for item in ctx.importBody().importItem()),
        )

    def visitImportItem(self, ctx: _AntlrContext) -> ImportItem:
        """Build one import item and retain both sides of an optional alias."""

        identifiers = ctx.identifier()
        local_name = identifiers[1].getText() if ctx.AS() is not None else None
        return ImportItem(
            span=self._span(ctx),
            declaration_kind=ModuleDeclarationKind(
                ctx.moduleDeclarationKind().getText()
            ),
            exported_name=identifiers[0].getText(),
            local_name=local_name,
            declaration_kind_span=self._span(ctx.moduleDeclarationKind()),
            exported_name_span=self._span(identifiers[0]),
            local_name_span=(
                self._span(identifiers[1]) if local_name is not None else None
            ),
        )

    def visitExportStatement(self, ctx: _AntlrContext) -> ExportStatement:
        """Build an export block without validating visibility or bindings."""

        return ExportStatement(
            span=self._span(ctx),
            items=tuple(self.visit(item) for item in ctx.exportBody().exportItem()),
        )

    def visitExportItem(self, ctx: _AntlrContext) -> ExportItem:
        """Build one parser-only export item."""

        identifier = ctx.identifier()
        return ExportItem(
            span=self._span(ctx),
            declaration_kind=ModuleDeclarationKind(
                ctx.moduleDeclarationKind().getText()
            ),
            local_name=identifier.getText(),
            declaration_kind_span=self._span(ctx.moduleDeclarationKind()),
            local_name_span=self._span(identifier),
        )

    def visitHeader(self, ctx: _AntlrContext) -> Header:
        version = (
            ctx.versionDecl().NUMBER().getText()
            if ctx.versionDecl() is not None
            else None
        )
        mode = self._mode(ctx.modeDecl()) if ctx.modeDecl() is not None else None
        dialect = (
            ctx.dialectDecl().identifier().getText()
            if ctx.dialectDecl() is not None
            else None
        )
        encoding = (
            ctx.encodingDecl().identifier().getText()
            if ctx.encodingDecl() is not None
            else None
        )
        return Header(
            span=self._span(ctx),
            version=version,
            mode=mode,
            dialect=dialect,
            encoding=encoding,
        )

    def visitDefinition(
        self, ctx: _AntlrContext
    ) -> (
        TypeDef
        | EnumDef
        | ConstraintDef
        | DeriveDef
        | ShapeDef
        | SourceDef
        | TableDef
        | QueryDef
    ):
        if ctx.typeDefinition() is not None:
            return self.visit(ctx.typeDefinition())
        if ctx.enumDefinition() is not None:
            return self.visit(ctx.enumDefinition())
        if ctx.constraintDefinition() is not None:
            return self.visit(ctx.constraintDefinition())
        if ctx.deriveDefinition() is not None:
            return self.visit(ctx.deriveDefinition())
        if ctx.shapeDefinition() is not None:
            return self.visit(ctx.shapeDefinition())
        if ctx.sourceDefinition() is not None:
            return self.visit(ctx.sourceDefinition())
        if ctx.tableDefinition() is not None:
            return self.visit(ctx.tableDefinition())
        return self.visit(ctx.queryDefinition())

    def visitTypeDefinition(self, ctx: _AntlrContext) -> TypeDef:
        ensures: list[EnsureClause] = []
        if ctx.expression() is not None:
            expression = cast(Expression, self.visit(ctx.expression()))
            ensures.append(
                EnsureClause(
                    span=self._span(ctx.expression()),
                    expression=expression,
                )
            )
        if ctx.typeBody() is not None:
            ensures.extend(self.visit(item) for item in ctx.typeBody().ensureClause())

        return TypeDef(
            span=self._span(ctx),
            name=ctx.identifier().getText(),
            base=self.visit(ctx.typeExpression()),
            ensures=tuple(ensures),
        )

    def visitEnsureClause(self, ctx: _AntlrContext) -> EnsureClause:
        return EnsureClause(
            span=self._span(ctx),
            expression=self.visit(ctx.expression()),
        )

    def visitTypeExpression(self, ctx: _AntlrContext) -> TypeExpr:
        return self._type_expression(
            ctx.typeReference(),
            span_context=ctx,
            nullability=self._nullability(ctx.nullabilityModifier()),
        )

    def visitTypeArgument(self, ctx: _AntlrContext) -> TypeArgument:
        name = ctx.typeArgumentName().getText() if ctx.ASSIGN() is not None else None
        return TypeArgument(
            span=self._span(ctx),
            name=name,
            value=self.visit(ctx.expression()),
        )

    def visitEnumDefinition(self, ctx: _AntlrContext) -> EnumDef:
        return EnumDef(
            span=self._span(ctx),
            name=ctx.identifier().getText(),
            members=tuple(
                item.identifier().getText() for item in ctx.enumBody().enumItem()
            ),
        )

    def visitConstraintDefinition(self, ctx: _AntlrContext) -> ConstraintDef:
        # Keep the declared return type as TypeExpr syntax. Enforcing a Bool
        # result belongs to Phase 2 rather than parse-tree construction.
        return ConstraintDef(
            span=self._span(ctx),
            name=ctx.identifier().getText(),
            parameters=self._parameters(ctx.parameterList()),
            return_type=self.visit(ctx.typeExpression()),
            body=self.visit(ctx.constraintBody().expression()),
        )

    def visitDeriveDefinition(self, ctx: _AntlrContext) -> DeriveDef:
        """Build a derive declaration without applying semantic checks."""

        # Keep the return type as TypeExpr syntax. Names, purity, recursion, and
        # type compatibility are intentionally left to Phase 2.
        return DeriveDef(
            span=self._span(ctx),
            name=ctx.identifier().getText(),
            parameters=self._parameters(ctx.parameterList()),
            return_type=self.visit(ctx.typeExpression()),
            body=self.visit(ctx.deriveBody().expression()),
        )

    def visitShapeDefinition(self, ctx: _AntlrContext) -> ShapeDef:
        """Build a shape while preserving mixed item source order."""

        return ShapeDef(
            span=self._span(ctx),
            name=ctx.identifier().getText(),
            items=tuple(self.visit(item) for item in ctx.shapeBody().shapeItem()),
        )

    def visitShapeItem(self, ctx: _AntlrContext) -> ShapeItem:
        """Build one shape item without losing its source position."""

        if ctx.fieldDefinition() is not None:
            return self.visit(ctx.fieldDefinition())
        if ctx.checkDefinition() is not None:
            return self.visit(ctx.checkDefinition())
        if ctx.uniqueDefinition() is not None:
            return self.visit(ctx.uniqueDefinition())
        return self.visit(ctx.indexDefinition())

    def visitFieldDefinition(self, ctx: _AntlrContext) -> FieldDef:
        """Build one field without resolving modifiers or type semantics."""

        field_type = ctx.typeExpression()
        modifiers = ctx.fieldModifier()
        return FieldDef(
            span=self._span(ctx),
            name=ctx.identifier().getText(),
            type_expr=self.visit(field_type),
            # Grammar placement makes derive singular and keeps it ahead of
            # repeatable annotations and ensure clauses.
            derive_expression=(
                self.visit(ctx.fieldDeriveClause().expression())
                if ctx.fieldDeriveClause() is not None
                else None
            ),
            # Filtering the ordered modifier contexts preserves source order
            # within each public modifier collection.
            annotations=tuple(
                self.visit(modifier.annotation())
                for modifier in modifiers
                if modifier.annotation() is not None
            ),
            ensure_clauses=tuple(
                self.visit(modifier.fieldEnsureClause())
                for modifier in modifiers
                if modifier.fieldEnsureClause() is not None
            ),
        )

    def visitAnnotation(self, ctx: _AntlrContext) -> Annotation:
        """Build a bare field annotation without validating its name."""

        return Annotation(
            span=self._span(ctx),
            name=ctx.identifier().getText(),
        )

    def visitFieldEnsureClause(self, ctx: _AntlrContext) -> EnsureClause:
        """Reuse EnsureClause for a parse-only field guarantee."""

        return EnsureClause(
            span=self._span(ctx),
            expression=self.visit(ctx.expression()),
        )

    def visitCheckDefinition(self, ctx: _AntlrContext) -> CheckDef:
        """Build a shape check without validating names or expression type."""

        return CheckDef(
            span=self._span(ctx),
            name=ctx.identifier().getText(),
            expression=self.visit(ctx.checkBody().expression()),
        )

    def visitUniqueDefinition(self, ctx: _AntlrContext) -> UniqueDef:
        """Build a unique clause without resolving or deduplicating fields."""

        identifiers = ctx.identifier()
        return UniqueDef(
            span=self._span(ctx),
            name=identifiers[0].getText(),
            field_names=tuple(identifier.getText() for identifier in identifiers[1:]),
        )

    def visitIndexDefinition(self, ctx: _AntlrContext) -> IndexDef:
        """Build an index clause without applying physical or semantic checks."""

        identifiers = ctx.identifier()
        return IndexDef(
            span=self._span(ctx),
            name=identifiers[0].getText(),
            field_names=tuple(identifier.getText() for identifier in identifiers[1:]),
            predicate=(
                self.visit(ctx.expression()) if ctx.expression() is not None else None
            ),
        )

    def visitSourceDefinition(self, ctx: _AntlrContext) -> SourceDef:
        """Build a source binding without validating or executing its connector."""

        identifiers = ctx.identifier()
        return SourceDef(
            span=self._span(ctx),
            name=identifiers[0].getText(),
            shape_name=identifiers[1].getText() if ctx.COLON() is not None else None,
            connector=self.visit(ctx.expression()),
        )

    def visitRelationshipDefinition(self, ctx: _AntlrContext) -> RelationshipMetadata:
        """Build parse-only relationship metadata outside semantic definitions."""

        body = ctx.relationshipBody()
        endpoints = tuple(self.visit(item) for item in body.relationshipEndpoint())
        assert len(endpoints) == 2
        match_clause = body.relationshipMatchClause()
        return RelationshipMetadata(
            span=self._span(ctx),
            name=ctx.identifier().getText(),
            endpoints=(endpoints[0], endpoints[1]),
            base_match=(None if match_clause is None else self.visit(match_clause)),
        )

    def visitRelationshipEndpoint(self, ctx: _AntlrContext) -> RelationshipEndpoint:
        """Build one endpoint without resolving either metadata name."""

        identifiers = ctx.identifier()
        return RelationshipEndpoint(
            span=self._span(ctx),
            local_name=identifiers[0].getText(),
            relation_name=identifiers[1].getText(),
        )

    def visitRelationshipMatchClause(
        self,
        ctx: _AntlrContext,
    ) -> RelationshipMatchClause:
        """Build one authored base match over the shared expression AST."""

        return RelationshipMatchClause(
            span=self._span(ctx),
            expression=self.visit(ctx.expression()),
        )

    def visitTableDefinition(self, ctx: _AntlrContext) -> TableDef:
        """Build a minimal table without resolving inputs or projection names."""

        (
            from_clause,
            join_clauses,
            let_clause,
            where_clause,
            group_by_clause,
            select_items,
            named_windows,
            satisfying_clause,
            order_by_clause,
            limit_clause,
        ) = self._relation_body(ctx.tableBody())
        return TableDef(
            span=self._span(ctx),
            name=ctx.identifier().getText(),
            from_clause=from_clause,
            join_clauses=join_clauses,
            where_clause=where_clause,
            group_by_clause=group_by_clause,
            select_items=select_items,
            order_by_clause=order_by_clause,
            limit_clause=limit_clause,
            satisfying_clause=satisfying_clause,
            let_clause=let_clause,
            named_windows=named_windows,
        )

    def visitQueryDefinition(self, ctx: _AntlrContext) -> QueryDef:
        """Build a minimal query without resolving or executing its input."""

        (
            from_clause,
            join_clauses,
            let_clause,
            where_clause,
            group_by_clause,
            select_items,
            named_windows,
            satisfying_clause,
            order_by_clause,
            limit_clause,
        ) = self._relation_body(ctx.tableBody())
        return QueryDef(
            span=self._span(ctx),
            name=ctx.identifier().getText(),
            from_clause=from_clause,
            join_clauses=join_clauses,
            where_clause=where_clause,
            group_by_clause=group_by_clause,
            select_items=select_items,
            order_by_clause=order_by_clause,
            limit_clause=limit_clause,
            satisfying_clause=satisfying_clause,
            let_clause=let_clause,
            named_windows=named_windows,
        )

    def visitFromClause(self, ctx: _AntlrContext) -> FromClause:
        """Build a relation input reference without resolving it."""

        return FromClause(
            span=self._span(ctx),
            source_name=ctx.identifier().getText(),
        )

    def visitJoinClause(self, ctx: _AntlrContext) -> JoinClause:
        """Retain one exact authored JOIN without lowering it."""

        identifiers = ctx.identifier()
        body = ctx.joinBody()
        return JoinClause(
            span=self._span(ctx),
            kind=(
                AuthoredJoinKind.INNER
                if ctx.INNER() is not None
                else AuthoredJoinKind.LEFT
            ),
            target_relation_name=identifiers[0].getText(),
            target_binding_name=identifiers[1].getText(),
            source_binding_name=body.identifier().getText(),
            traversal_steps=tuple(
                self.visit(step) for step in body.joinTraversalStep()
            ),
        )

    def visitJoinTraversalStep(self, ctx: _AntlrContext) -> JoinTraversalStep:
        """Retain one source-ordered VIA step with exact endpoint roles."""

        identifiers = ctx.identifier()
        return JoinTraversalStep(
            span=self._span(ctx),
            relationship_name=identifiers[0].getText(),
            source_endpoint_role=identifiers[1].getText(),
            target_endpoint_role=identifiers[2].getText(),
        )

    def visitWhereClause(self, ctx: _AntlrContext) -> WhereClause:
        """Build a relation filter without checking its expression type."""

        return WhereClause(
            span=self._span(ctx),
            expression=self.visit(ctx.expression()),
        )

    def visitLetClause(self, ctx: _AntlrContext) -> LetClause:
        """Build a parse-only let block without binding or type checks."""

        return LetClause(
            span=self._span(ctx),
            bindings=tuple(self.visit(item) for item in ctx.letBody().letBinding()),
        )

    def visitLetBinding(self, ctx: _AntlrContext) -> LetBinding:
        """Build one source-ordered parse-only let binding."""

        return LetBinding(
            span=self._span(ctx),
            name=ctx.identifier().getText(),
            expression=self.visit(ctx.expression()),
        )

    def visitGroupByClause(self, ctx: _AntlrContext) -> GroupByClause:
        """Build a non-empty grouping block without semantic validation."""

        return GroupByClause(
            span=self._span(ctx),
            items=tuple(self.visit(item) for item in ctx.groupByBody().groupByItem()),
        )

    def visitGroupByItem(self, ctx: _AntlrContext) -> GroupByItem:
        """Build one grouping key from the restricted dotted-name syntax."""

        return GroupByItem(
            span=self._span(ctx),
            key=self._dotted_name_expr(ctx.dottedName()),
        )

    def visitSelectItem(self, ctx: _AntlrContext) -> SelectItem:
        """Build one projection; assignment syntax is confined to this rule."""

        return SelectItem(
            span=self._span(ctx),
            alias=ctx.identifier().getText() if ctx.ASSIGN() is not None else None,
            expression=self.visit(
                ctx.windowExpression()
                if ctx.windowExpression() is not None
                else ctx.expression()
            ),
        )

    def visitWindowExpression(self, ctx: _AntlrContext) -> WindowExpr:
        """Preserve one direct call and its exact inline or named use."""

        call = self._call_expr(ctx.dottedName(), ctx.callSuffix())
        callee = call.callee
        parts = (callee.name,) if isinstance(callee, NameExpr) else callee.parts
        use = ctx.windowSpec()
        identifier = use.identifier()
        base = (
            None
            if identifier is None
            else NamedWindowReference(
                span=self._span(identifier),
                name=identifier.getText(),
            )
        )
        if base is None:
            use_kind = WindowUseKind.INLINE
        elif use.windowSpecBody() is None:
            use_kind = WindowUseKind.NAMED_DIRECT
        else:
            use_kind = WindowUseKind.NAMED_EXTENDED
        nth_direction = (
            None
            if ctx.nthValueDirection() is None
            else AuthoredWindowNthDirection(
                span=self._span(ctx.nthValueDirection()),
                kind=(
                    WindowNthDirectionKind.FIRST
                    if ctx.nthValueDirection().FIRST() is not None
                    else WindowNthDirectionKind.LAST
                ),
            )
        )
        null_treatment = (
            None
            if ctx.nullTreatment() is None
            else AuthoredWindowNullTreatment(
                span=self._span(ctx.nullTreatment()),
                kind=(
                    WindowNullTreatmentKind.RESPECT
                    if ctx.nullTreatment().RESPECT() is not None
                    else WindowNullTreatmentKind.IGNORE
                ),
            )
        )
        return WindowExpr(
            span=self._span(ctx),
            call=call,
            spec=self.visit(use),
            identity=_window_identity.WindowFunctionIdentity(
                namespace=parts[:-1],
                name=parts[-1],
                role=_window_identity.WindowFunctionRole.WINDOW_FUNCTION,
            ),
            use_kind=use_kind,
            base=base,
            nth_direction=nth_direction,
            null_treatment=null_treatment,
        )

    def visitWindowSpec(self, ctx: _AntlrContext) -> WindowSpec:
        """Build one local component bundle in source order."""

        body = ctx.windowSpecBody()
        if body is None:
            return WindowSpec(
                span=self._span(ctx),
                partition_by=(),
                order_by=(),
            )
        return self._window_spec_from_body(body, span=self._span(ctx))

    def visitNamedWindowDeclaration(
        self,
        ctx: _AntlrContext,
    ) -> NamedWindowDeclaration:
        """Preserve one exact root, alias, or based declaration occurrence."""

        identifiers = ctx.identifier()
        base = (
            None
            if len(identifiers) == 1
            else NamedWindowReference(
                span=self._span(identifiers[1]),
                name=identifiers[1].getText(),
            )
        )
        body = ctx.windowSpecBody()
        return NamedWindowDeclaration(
            span=self._span(ctx),
            name=identifiers[0].getText(),
            base=base,
            spec=(
                None
                if body is None
                else self._window_spec_from_body(body, span=self._span(body))
            ),
        )

    def _window_spec_from_body(
        self,
        body: _AntlrContext,
        *,
        span: Span,
    ) -> WindowSpec:
        """Build one grammar-proven nonempty local component bundle."""

        partition_clause = body.partitionByClause()
        order_clause = body.orderByClause()
        partition_by: tuple[Expression, ...] = ()
        if partition_clause is not None:
            partition_by = tuple(
                self.visit(item)
                for item in partition_clause.windowPartitionBody().windowPartitionItem()
            )
        order_by: tuple[OrderItem, ...] = ()
        if order_clause is not None:
            order_by = tuple(
                self._order_item(item, reject_ordinal=False)
                for item in order_clause.orderByBody().orderItem()
            )
        frame_clause = body.windowFrameClause()
        frame = (
            AuthoredWindowFrame(kind=AuthoredWindowFrameKind.OMITTED)
            if frame_clause is None
            else self.visit(frame_clause)
        )
        return WindowSpec(
            span=span,
            partition_by=partition_by,
            order_by=order_by,
            frame=frame,
        )

    def visitWindowPartitionItem(self, ctx: _AntlrContext) -> Expression:
        """Preserve one window partition expression without a wrapper node."""

        return self.visit(ctx.expression())

    def visitWindowFrameClause(self, ctx: _AntlrContext) -> AuthoredWindowFrame:
        """Preserve frame unit and shorthand versus BETWEEN authorship."""

        bounds = tuple(self.visit(bound) for bound in ctx.frameBound())
        if ctx.ROWS() is not None:
            unit = WindowFrameUnit.ROWS
        elif ctx.RANGE() is not None:
            unit = WindowFrameUnit.RANGE
        else:
            unit = WindowFrameUnit.GROUPS
        exclusion = AuthoredWindowFrameExclusion.OMITTED
        if ctx.EXCLUDE() is not None:
            if ctx.NO() is not None:
                exclusion = AuthoredWindowFrameExclusion.NO_OTHERS
            elif ctx.CURRENT() is not None:
                exclusion = AuthoredWindowFrameExclusion.CURRENT_ROW
            elif ctx.GROUP() is not None:
                exclusion = AuthoredWindowFrameExclusion.GROUP
            else:
                exclusion = AuthoredWindowFrameExclusion.TIES
        if ctx.BETWEEN() is None:
            assert len(bounds) == 1
            return AuthoredWindowFrame(
                kind=AuthoredWindowFrameKind.SHORTHAND,
                unit=unit,
                start=bounds[0],
                exclusion=exclusion,
            )
        assert len(bounds) == 2
        return AuthoredWindowFrame(
            kind=AuthoredWindowFrameKind.BETWEEN,
            unit=unit,
            start=bounds[0],
            end=bounds[1],
            exclusion=exclusion,
        )

    def visitFrameBound(self, ctx: _AntlrContext) -> WindowFrameBound:
        """Build one frozen frame-bound variant with its exact offset expression."""

        if ctx.UNBOUNDED() is not None:
            kind = (
                WindowFrameBoundKind.UNBOUNDED_PRECEDING
                if ctx.PRECEDING() is not None
                else WindowFrameBoundKind.UNBOUNDED_FOLLOWING
            )
            return WindowFrameBound(kind=kind)
        if ctx.CURRENT() is not None:
            return WindowFrameBound(kind=WindowFrameBoundKind.CURRENT_ROW)
        kind = (
            WindowFrameBoundKind.OFFSET_PRECEDING
            if ctx.PRECEDING() is not None
            else WindowFrameBoundKind.OFFSET_FOLLOWING
        )
        return WindowFrameBound(kind=kind, offset=self.visit(ctx.expression()))

    def visitSatisfyingClause(self, ctx: _AntlrContext) -> SatisfyingClause:
        """Build a parse-only result predicate without semantic validation."""

        return SatisfyingClause(
            span=self._span(ctx),
            expression=self.visit(ctx.expression()),
        )

    def visitOrderByClause(self, ctx: _AntlrContext) -> OrderByClause:
        """Build a non-empty sorting block without resolving its expressions."""

        return OrderByClause(
            span=self._span(ctx),
            items=tuple(self.visit(item) for item in ctx.orderByBody().orderItem()),
        )

    def visitOrderItem(self, ctx: _AntlrContext) -> OrderItem:
        """Build one sorting item while keeping omitted direction explicit."""

        return self._order_item(ctx, reject_ordinal=True)

    def _order_item(
        self,
        ctx: _AntlrContext,
        *,
        reject_ordinal: bool,
    ) -> OrderItem:
        """Build an order item under its owning clause's ordinal policy."""

        expression = cast(Expression, self.visit(ctx.expression()))
        if (
            reject_ordinal
            and isinstance(expression, LiteralExpr)
            and type(expression.value) is int
        ):
            span = expression.span
            raise AstBuildError(
                "Ordinal ORDER BY expressions are not supported.",
                line=span.line,
                column=span.column,
            )
        direction = None
        if ctx.ASC() is not None:
            direction = "asc"
        elif ctx.DESC() is not None:
            direction = "desc"
        return OrderItem(
            span=self._span(ctx),
            expression=expression,
            direction=direction,
        )

    def visitLimitClause(self, ctx: _AntlrContext) -> LimitClause:
        """Build a limit clause without accepting its operand semantically."""

        return LimitClause(
            span=self._span(ctx),
            expression=self.visit(ctx.expression()),
        )

    def _relation_body(
        self, ctx: _AntlrContext
    ) -> tuple[
        FromClause,
        tuple[JoinClause, ...],
        LetClause | None,
        WhereClause | None,
        GroupByClause | None,
        tuple[SelectItem, ...],
        tuple[NamedWindowDeclaration, ...],
        SatisfyingClause | None,
        OrderByClause | None,
        LimitClause | None,
    ]:
        """Build clauses shared by minimal table and query definitions."""

        return (
            self.visit(ctx.fromClause()),
            tuple(self.visit(item) for item in ctx.joinClause()),
            self.visit(ctx.letClause()) if ctx.letClause() is not None else None,
            self.visit(ctx.whereClause()) if ctx.whereClause() is not None else None,
            (
                self.visit(ctx.groupByClause())
                if ctx.groupByClause() is not None
                else None
            ),
            tuple(
                self.visit(item)
                for item in ctx.selectClause().selectBody().selectItem()
            ),
            tuple(self.visit(item) for item in ctx.namedWindowDeclaration()),
            (
                self.visit(ctx.satisfyingClause())
                if ctx.satisfyingClause() is not None
                else None
            ),
            (
                self.visit(ctx.orderByClause())
                if ctx.orderByClause() is not None
                else None
            ),
            self.visit(ctx.limitClause()) if ctx.limitClause() is not None else None,
        )

    def visitParameter(self, ctx: _AntlrContext) -> Parameter:
        return Parameter(
            span=self._span(ctx),
            name=ctx.identifier().getText(),
            type=self.visit(ctx.typeExpression()),
        )

    def visitExpression(self, ctx: _AntlrContext) -> Expression:
        return self.visit(ctx.orExpression())

    def visitOrExpression(self, ctx: _AntlrContext) -> Expression:
        return self._fold_binary(ctx)

    def visitAndExpression(self, ctx: _AntlrContext) -> Expression:
        return self._fold_binary(ctx)

    def visitComparisonExpression(self, ctx: _AntlrContext) -> Expression:
        operands = ctx.additiveExpression()
        left = cast(Expression, self.visit(operands[0]))

        if ctx.comparisonOperator() is not None:
            return ComparisonExpr(
                span=self._span(ctx),
                left=left,
                operator=ctx.comparisonOperator().getText(),
                right=self.visit(operands[1]),
            )
        if ctx.BETWEEN() is not None:
            return BetweenExpr(
                span=self._span(ctx),
                value=left,
                lower=self.visit(operands[1]),
                upper=self.visit(operands[2]),
            )
        if ctx.IS() is not None:
            return IsNullExpr(
                span=self._span(ctx),
                value=left,
                negated=ctx.NOT() is not None,
            )
        return left

    def visitAdditiveExpression(self, ctx: _AntlrContext) -> Expression:
        return self._fold_binary(ctx)

    def visitMultiplicativeExpression(self, ctx: _AntlrContext) -> Expression:
        return self._fold_binary(ctx)

    def visitUnaryExpression(self, ctx: _AntlrContext) -> Expression:
        if ctx.primaryExpression() is not None:
            return self.visit(ctx.primaryExpression())
        return UnaryExpr(
            span=self._span(ctx),
            operator=ctx.getChild(0).getText(),
            operand=self.visit(ctx.unaryExpression()),
        )

    def visitPrimaryExpression(self, ctx: _AntlrContext) -> Expression:
        if ctx.literal() is not None:
            return self.visit(ctx.literal())
        if ctx.expression() is not None:
            return self.visit(ctx.expression())

        callee = self._dotted_name_expr(ctx.dottedName())
        if ctx.callSuffix() is None:
            return callee
        return self._call_expr(ctx.dottedName(), ctx.callSuffix())

    def _call_expr(
        self,
        dotted_name_ctx: _AntlrContext,
        call_suffix_ctx: _AntlrContext,
    ) -> CallExpr:
        """Build a call whose span ends at its call suffix, not a later suffix."""

        return CallExpr(
            span=self._span_between(dotted_name_ctx, call_suffix_ctx),
            callee=self._dotted_name_expr(dotted_name_ctx),
            arguments=tuple(
                self.visit(argument) for argument in call_suffix_ctx.expression()
            ),
        )

    def _dotted_name_expr(self, ctx: _AntlrContext) -> NameExpr | DottedNameExpr:
        """Build the AST representation for a bare or dotted name context."""

        parts = tuple(part.getText() for part in ctx.namePart())
        if len(parts) == 1:
            return NameExpr(span=self._span(ctx), name=parts[0])
        return DottedNameExpr(
            span=self._span(ctx),
            parts=parts,
        )

    def visitLiteral(self, ctx: _AntlrContext) -> LiteralExpr:
        value: str | int | float | bool | None
        if ctx.STRING() is not None:
            value = self._decode_string_literal(ctx)
        elif ctx.NUMBER() is not None:
            value = self._decode_numeric_literal(ctx)
        elif ctx.TRUE() is not None:
            value = True
        elif ctx.FALSE() is not None:
            value = False
        else:
            value = None
        return LiteralExpr(span=self._span(ctx), value=value)

    def _parameters(self, ctx: _AntlrContext | None) -> tuple[Parameter, ...]:
        """Build parameters shared by constraint and derive declarations."""

        if ctx is None:
            return ()
        return tuple(self.visit(parameter) for parameter in ctx.parameter())

    def _type_expression(
        self,
        ctx: _AntlrContext,
        *,
        span_context: ParserRuleContext,
        nullability: Nullability,
    ) -> TypeExpr:
        """Build a TypeExpr shared by declarations and shape fields."""

        arguments: tuple[TypeArgument, ...] = ()
        if ctx.typeArguments() is not None:
            arguments = tuple(
                self.visit(item) for item in ctx.typeArguments().typeArgument()
            )
        return TypeExpr(
            span=self._span(span_context),
            name=ctx.identifier().getText(),
            arguments=arguments,
            nullability=nullability,
        )

    @staticmethod
    def _nullability(
        ctx: _AntlrContext | None,
    ) -> Nullability:
        """Map optional nullability syntax to its AST state."""

        if ctx is None:
            return Nullability.IMPLICIT
        if ctx.NULLABLE() is not None:
            return Nullability.NULLABLE
        return Nullability.NOT_NULL

    def _fold_binary(self, ctx: ParserRuleContext) -> Expression:
        """Fold a flat precedence-rule context into left-associative AST nodes."""

        children = ctx.children or []
        result = cast(Expression, self.visit(children[0]))
        for index in range(1, len(children), 2):
            operator = cast(_TerminalNode, children[index]).getText()
            right = cast(Expression, self.visit(children[index + 1]))
            result = BinaryExpr(
                span=self._span(ctx),
                left=result,
                operator=operator,
                right=right,
            )
        return result

    def _span(self, ctx: ParserRuleContext) -> Span:
        """Build a one-based, half-open span excluding layout-only tokens."""

        start = ctx.start
        assert start is not None
        stop = self._last_significant_token(ctx)
        if stop is None:
            end_line = start.line
            end_column = start.column + 1
        else:
            end_line, end_column = self._end_position(stop)
        return Span(
            path=self.path,
            line=start.line,
            column=start.column + 1,
            end_line=end_line,
            end_column=end_column,
        )

    def _span_between(
        self,
        start_ctx: ParserRuleContext,
        end_ctx: ParserRuleContext,
    ) -> Span:
        """Build a logical span from one context through another context."""

        start = start_ctx.start
        assert start is not None
        stop = self._last_significant_token(end_ctx)
        assert stop is not None
        end_line, end_column = self._end_position(stop)
        return Span(
            path=self.path,
            line=start.line,
            column=start.column + 1,
            end_line=end_line,
            end_column=end_column,
        )

    @staticmethod
    def _end_position(token: Token) -> tuple[int, int]:
        """Return the exclusive one-based end position of a token."""

        text = token.text or ""
        line_breaks = text.count("\n")
        if line_breaks:
            return token.line + line_breaks, len(text.rsplit("\n", 1)[-1]) + 1
        return token.line, token.column + len(text) + 1

    @staticmethod
    def _last_significant_token(node: Any) -> Token | None:
        """Find the last token that contributes source text to an AST node."""

        if isinstance(node, TerminalNode):
            token = cast(_TerminalNode, node).getSymbol()
            ignored_types = {
                Token.EOF,
                PiettoParser.NEWLINE,
                PiettoParser.INDENT,
                PiettoParser.DEDENT,
            }
            return None if token.type in ignored_types else token

        for child in reversed(getattr(node, "children", None) or ()):
            token = AstBuilder._last_significant_token(child)
            if token is not None:
                return token
        return None

    @staticmethod
    def _decode_string_literal(ctx: _AntlrContext) -> str:
        """Decode supported escapes and reject invalid escapes as source errors."""

        token = ctx.STRING().getSymbol()
        text = token.text or ""
        body = text[1:-1]
        result: list[str] = []
        escapes = {
            "\\": "\\",
            '"': '"',
            "'": "'",
            "n": "\n",
            "r": "\r",
            "t": "\t",
            "b": "\b",
            "f": "\f",
        }

        index = 0
        while index < len(body):
            character = body[index]
            if character != "\\":
                result.append(character)
                index += 1
                continue

            if index + 1 >= len(body):
                raise AstBuildError(
                    "String literal ends with an incomplete escape sequence.",
                    line=token.line,
                    column=token.column + index + 2,
                )

            escaped = body[index + 1]
            if escaped not in escapes:
                # AstBuildError is translated by parser_api into a diagnostic, so
                # malformed source never leaks a Python decoding exception.
                raise AstBuildError(
                    f'Unsupported string escape "\\{escaped}".',
                    line=token.line,
                    column=token.column + index + 2,
                )

            result.append(escapes[escaped])
            index += 2

        return "".join(result)

    @staticmethod
    def _decode_numeric_literal(ctx: _AntlrContext) -> int | float:
        """Decode a bounded finite numeric literal as an ordinary source value."""

        token = ctx.NUMBER().getSymbol()
        text = token.text or ""
        if len(text) > _MAX_NUMERIC_LITERAL_LENGTH:
            raise AstBuildError(
                "Numeric literal exceeds the maximum supported length of "
                f"{_MAX_NUMERIC_LITERAL_LENGTH} characters.",
                line=token.line,
                column=token.column + 1,
            )

        try:
            value = float(text) if "." in text else int(text)
        except (OverflowError, ValueError) as error:
            raise AstBuildError(
                "Numeric literal cannot be represented safely.",
                line=token.line,
                column=token.column + 1,
            ) from error

        if isinstance(value, float) and not math.isfinite(value):
            raise AstBuildError(
                "Numeric literal must be finite.",
                line=token.line,
                column=token.column + 1,
            )
        return value

    @staticmethod
    def _mode(ctx: _AntlrContext) -> str:
        """Extract the selected mode keyword from a mode declaration."""

        for token_type in ("LOOSE", "CHECKED", "STRICT"):
            token = getattr(ctx, token_type)()
            if token is not None:
                return token.getText()
        raise ValueError("mode declaration has no mode token")

    def visitChildren(self, node: Any) -> Any:
        return super().visitChildren(node)
