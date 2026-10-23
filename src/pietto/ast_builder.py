"""Convert generated ANTLR parse trees into Pietto-owned AST dataclasses."""

from __future__ import annotations

import math
import threading
from pathlib import Path
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Protocol, cast

from antlr4 import ParserRuleContext
from antlr4.Token import Token
from antlr4.tree.Tree import TerminalNode

from pietto import _window_identity
from pietto.ast_nodes import (
    DistinctClause,
    Annotation,
    AuthoredJoinKind,
    AuthoredWindowFrame,
    AuthoredWindowFrameExclusion,
    AuthoredWindowFrameKind,
    AuthoredWindowNthDirection,
    AuthoredWindowNullTreatment,
    BetweenExpr,
    BinaryExpr,
    BlockRelationDef,
    CaptureClause,
    CapturedFieldExpr,
    CastExpr,
    CallExpr,
    CheckDef,
    ComparisonExpr,
    ConditionalExpr,
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
    FunctionDef,
    GroupByClause,
    GroupByItem,
    Header,
    IndexDef,
    ImportItem,
    ImportStatement,
    IsNullExpr,
    JoinClause,
    JoinOnClause,
    JoinTraversalStep,
    LetBinding,
    LetClause,
    LimitClause,
    LetRelationDef,
    LiteralExpr,
    MembershipExpr,
    NameExpr,
    ModuleDeclarationKind,
    NamedWindowDeclaration,
    NamedWindowReference,
    Nullability,
    OrderByClause,
    OrderItem,
    Parameter,
    ParameterRefExpr,
    QualifyClause,
    QueryDef,
    QueryParameter,
    RelationBody,
    RelationExistsExpr,
    RelationMembershipExpr,
    RelationScalarExpr,
    RelationshipEndpoint,
    RelationshipMatchClause,
    RelationshipMetadata,
    Script,
    SelectBody,
    SetOperand,
    SetOperationBody,
    SetOperationKind,
    SetOperationQuantifier,
    SetRelationDef,
    ShapeDef,
    ShapeItem,
    SourceDef,
    Span,
    SelectItem,
    SatisfyingClause,
    TableDef,
    TableFunctionFromClause,
    TypeArgument,
    TypeDef,
    TypeExpr,
    UnaryExpr,
    UniqueDef,
    ValuesBody,
    ValuesColumn,
    ValuesRow,
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
from pietto.errors import AstBuildError, ParseCancelled, source_path
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
_HEADER_LINE_THEN_BLOCK = (
    "This clause already has its content on the header line after ':'; "
    "an indented block cannot follow it."
)
_WHERE_LINE_THEN_BLOCK = (
    "A `where` condition ends with its line; write one condition per line in "
    "a `where:` block, or continue a condition inside parentheses."
)
_TRAILING_COMMA = (
    "A trailing comma does not continue a list on the next line; remove the comma."
)
_WINDOW_ITEM_LINE = "A window item must be on its own line in a `select:` block."
_COMPOUND_SAME_LINE = (
    "A compound clause cannot follow ':' on the same line; put the window "
    "clauses in an indented block."
)
# Precedence levels that wrap a single operand build no AST node of their own,
# nor do parentheses; the builder steps through them without recursing.
_PASS_THROUGH = (
    PiettoParser.ExpressionContext,
    PiettoParser.ConditionalExpressionContext,
    PiettoParser.OrExpressionContext,
    PiettoParser.AndExpressionContext,
    PiettoParser.NotExpressionContext,
    PiettoParser.ComparisonExpressionContext,
    PiettoParser.AdditiveExpressionContext,
    PiettoParser.MultiplicativeExpressionContext,
    PiettoParser.UnaryExpressionContext,
    PiettoParser.QualifyExpressionContext,
    PiettoParser.QualifyConditionalExpressionContext,
    PiettoParser.QualifyOrExpressionContext,
    PiettoParser.QualifyAndExpressionContext,
    PiettoParser.QualifyNotExpressionContext,
    PiettoParser.QualifyComparisonExpressionContext,
    PiettoParser.QualifyAdditiveExpressionContext,
    PiettoParser.QualifyMultiplicativeExpressionContext,
    PiettoParser.QualifyUnaryExpressionContext,
)
_PRIMARY = (
    PiettoParser.PrimaryExpressionContext,
    PiettoParser.QualifyPrimaryExpressionContext,
)
_LAYOUT_TOKEN_TYPES = frozenset(
    {Token.EOF, PiettoParser.NEWLINE, PiettoParser.INDENT, PiettoParser.DEDENT}
)
_PREDICATE_LINE_OPERATOR = (
    "A condition line cannot start with `and` or `or`; the lines of a "
    "condition block are joined with `and`, and parentheses continue one "
    "condition across lines."
)


class _TerminalNode(Protocol):
    """ANTLR terminal operations used by the handwritten AST boundary."""

    def getText(self) -> str: ...

    def getSymbol(self) -> Token: ...


class AstBuilder(PiettoVisitor):
    """Build an ANTLR-independent AST from a successfully parsed script."""

    def __init__(
        self, path: str | Path | None, *, cancel: threading.Event | None = None
    ) -> None:
        """Create a builder whose AST spans use the supplied source path.

        A set ``cancel`` event stops the build at its next tree node.
        """

        self.path = source_path(path)
        self._cancel = cancel
        # Header parameters of the entry query whose body is being built.
        self._header: dict[str, tuple[int, QueryParameter]] = {}
        # Capture names of the let body being built, with their line ordinals.
        self._captures: dict[str, int] = {}
        # The start token of the most recently entered context, which locates
        # a recursion-limit failure at the deepest construct reached.
        self.deepest: Token | None = None

    def visit(self, tree: Any) -> Any:
        """Visit one tree, stepping iteratively through operand-only wrappers."""

        while True:
            if isinstance(tree, _PASS_THROUGH) and tree.getChildCount() == 1:
                tree = tree.getChild(0)
            elif (
                isinstance(tree, _PRIMARY)
                and tree.getChildCount() == 3
                and tree.LPAREN() is not None
            ):
                tree = tree.getChild(1)
            else:
                break
        if isinstance(tree, ParserRuleContext):
            self.deepest = tree.start
        if self._cancel is not None and self._cancel.is_set():
            raise ParseCancelled
        return cast(Any, tree).accept(self)

    def visitScript(self, ctx: _AntlrContext) -> Script:
        """Build the root script node."""

        header = self.visit(ctx.header()) if ctx.header() is not None else None
        # Building in source order makes a build error the first one in the file.
        built: dict[type, list[Any]] = {
            PiettoParser.DefinitionContext: [],
            PiettoParser.RelationshipDefinitionContext: [],
            PiettoParser.ModuleStatementContext: [],
        }
        for child in ctx.children or ():
            kind = type(child)
            if kind in built:
                built[kind].append(self.visit(child))
        return Script(
            span=self._span(ctx),
            header=cast(Header | None, header),
            definitions=tuple(built[PiettoParser.DefinitionContext]),
            relationships=tuple(built[PiettoParser.RelationshipDefinitionContext]),
            module_statements=tuple(built[PiettoParser.ModuleStatementContext]),
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
        | SetRelationDef
        | BlockRelationDef
        | FunctionDef
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
        if ctx.functionDefinition() is not None:
            return self.visit(ctx.functionDefinition())
        return self.visit(ctx.queryDefinition())

    def visitTypeDefinition(self, ctx: _AntlrContext) -> TypeDef:
        # The base type comes first in the source, so it is built first.
        base = cast(TypeExpr, self.visit(ctx.typeExpression()))
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
            base=base,
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
                item.getText()
                for line in self._clause_lines(ctx, "enumLine", "enumBody")
                for item in line.identifier()
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

    def visitFunctionDefinition(self, ctx: _AntlrContext) -> FunctionDef:
        """Build a pure inline function whose types state their nullability."""

        # Each type is checked as it is built, so errors come in source order.
        parameter_list = ctx.parameterList()
        parameters: list[Parameter] = []
        for item in () if parameter_list is None else parameter_list.parameter():
            parameter = cast(Parameter, self.visit(item))
            self._require_nullability(parameter.type, "parameter")
            parameters.append(parameter)
        return_type = cast(TypeExpr, self.visit(ctx.typeExpression()))
        self._require_nullability(return_type, "return type")
        body = ctx.functionBody()
        return FunctionDef(
            span=self._span(ctx),
            name=ctx.identifier().getText(),
            parameters=tuple(parameters),
            return_type=return_type,
            body=self.visit((body or ctx).expression()),
        )

    @staticmethod
    def _require_nullability(type_expr: TypeExpr, role: str) -> None:
        if type_expr.nullability is Nullability.IMPLICIT:
            raise AstBuildError(
                f"A `def` {role} must state its nullability: write "
                "`nullable` or `not null` after the type.",
                line=type_expr.span.line,
                column=type_expr.span.column,
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
            name=ctx.fieldName().getText(),
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
            expression=self._predicate_suite(ctx.predicateSuite()),
        )

    def visitUniqueDefinition(self, ctx: _AntlrContext) -> UniqueDef:
        """Build a unique clause without resolving or deduplicating fields."""

        return UniqueDef(
            span=self._span(ctx),
            name=ctx.identifier().getText(),
            field_names=tuple(name.getText() for name in ctx.fieldName()),
        )

    def visitIndexDefinition(self, ctx: _AntlrContext) -> IndexDef:
        """Build an index clause without applying physical or semantic checks."""

        return IndexDef(
            span=self._span(ctx),
            name=ctx.identifier().getText(),
            field_names=tuple(name.getText() for name in ctx.fieldName()),
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
        if body is None:
            return self._one_line_relationship(ctx)
        endpoints = tuple(self.visit(item) for item in body.relationshipEndpoint())
        assert len(endpoints) == 2
        match_clause = body.relationshipMatchClause()
        return RelationshipMetadata(
            span=self._span(ctx),
            name=ctx.identifier().getText(),
            endpoints=(endpoints[0], endpoints[1]),
            base_match=(None if match_clause is None else self.visit(match_clause)),
        )

    def _one_line_relationship(self, ctx: _AntlrContext) -> RelationshipMetadata:
        """Desugar ``relationship r: a.x == b.y and ...`` to its endpoint block.

        Each endpoint role is its relation name, in first-occurrence order and
        located at that occurrence, exactly as the block form
        ``endpoint a: a`` / ``endpoint b: b`` / ``on <expression>`` would be.
        """

        expression = cast(Expression, self.visit(ctx.expression()))
        first_seen: dict[str, Span] = {}
        pending: list[Expression] = [expression]
        while pending:
            item = pending.pop()
            if type(item) is BinaryExpr and item.operator == "and":
                pending.extend((item.right, item.left))
                continue
            sides = (
                (item.left, item.right)
                if type(item) is ComparisonExpr and item.operator == "=="
                else ()
            )
            names = tuple(
                side.parts[0]
                for side in sides
                if type(side) is DottedNameExpr and len(side.parts) == 2
            )
            if len(names) != 2 or names[0] == names[1]:
                raise self._relationship_shape_error(item.span)
            for side, name in zip(sides, names, strict=True):
                start = side.span
                first_seen.setdefault(
                    name,
                    Span(
                        path=self.path,
                        line=start.line,
                        column=start.column,
                        end_line=start.line,
                        end_column=start.column + len(name),
                    ),
                )
            if len(first_seen) > 2:
                raise self._relationship_shape_error(item.span)
        if len(first_seen) != 2:
            raise self._relationship_shape_error(expression.span)
        first, second = (
            RelationshipEndpoint(span=span, local_name=name, relation_name=name)
            for name, span in first_seen.items()
        )
        return RelationshipMetadata(
            span=self._span(ctx),
            name=ctx.identifier().getText(),
            endpoints=(first, second),
            base_match=RelationshipMatchClause(
                span=expression.span, expression=expression
            ),
        )

    @staticmethod
    def _relationship_shape_error(span: Span) -> AstBuildError:
        return AstBuildError(
            "A one-line relationship compares fields of two different relations "
            "with `==`, joined by `and`, as in `a.x == b.y`; use the endpoint "
            "block form for any other match.",
            line=span.line,
            column=span.column,
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

    def visitTableDefinition(
        self, ctx: _AntlrContext
    ) -> TableDef | QueryDef | SetRelationDef | BlockRelationDef:
        """Build a minimal table without resolving inputs or projection names."""

        return self._relation_definition(
            ctx, ModuleDeclarationKind.TABLE, ctx.identifier(), ()
        )

    def visitQueryDefinition(
        self, ctx: _AntlrContext
    ) -> TableDef | QueryDef | SetRelationDef | BlockRelationDef:
        """Build a minimal query without resolving or executing its input."""

        header = ctx.queryHeader()
        parameters: tuple[QueryParameter, ...] = ()
        if header.parameterList() is not None:
            parameters = tuple(
                QueryParameter(
                    span=self._span(item),
                    name=item.fieldName().getText(),
                    type=self.visit(item.typeExpression()),
                )
                for item in header.parameterList().parameter()
            )
        for ordinal, parameter in enumerate(parameters):
            self._header.setdefault(parameter.name, (ordinal, parameter))
        try:
            return self._relation_definition(
                ctx, ModuleDeclarationKind.QUERY, header.identifier(), parameters
            )
        finally:
            self._header = {}

    def _relation_definition(
        self,
        ctx: _AntlrContext,
        kind: ModuleDeclarationKind,
        name_ctx: _AntlrContext,
        parameters: tuple[QueryParameter, ...],
    ) -> TableDef | QueryDef | SetRelationDef | BlockRelationDef:
        """Keep existing classes for existing forms; any new form builds a block."""

        name = name_ctx.getText()
        let_relations = tuple(self.visit(item) for item in ctx.letRelationDefinition())
        body = self._relation_body_node(ctx)
        if not let_relations:
            if type(body) is SetOperationBody and not parameters:
                return SetRelationDef(
                    span=self._span(ctx), name=name, kind=kind, body=body
                )
            if type(body) is SelectBody and type(body.from_clause) is FromClause:
                relation = TableDef if kind is ModuleDeclarationKind.TABLE else QueryDef
                # Only an entry query has a header; it keeps the query class.
                header = {"parameters": parameters} if parameters else {}
                return relation(
                    **header,
                    span=self._span(ctx),
                    name=name,
                    from_clause=body.from_clause,
                    join_clauses=body.join_clauses,
                    where_clause=body.where_clause,
                    group_by_clause=body.group_by_clause,
                    select_items=body.select_items,
                    order_by_clause=body.order_by_clause,
                    limit_clause=body.limit_clause,
                    satisfying_clause=body.satisfying_clause,
                    qualify_clause=body.qualify_clause,
                    let_clause=body.let_clause,
                    named_windows=body.named_windows,
                    distinct_clause=body.distinct_clause,
                )
        return BlockRelationDef(
            span=self._span(ctx),
            name=name,
            kind=kind,
            parameters=parameters,
            let_relations=let_relations,
            body=body,
        )

    def visitLetRelationDefinition(self, ctx: _AntlrContext) -> LetRelationDef:
        """Build one relation let without entering any namespace."""

        captures = tuple(self.visit(item) for item in ctx.captureClause())
        for ordinal, capture in enumerate(captures):
            self._captures.setdefault(capture.name, ordinal)
        try:
            body = self._relation_body_node(ctx)
        finally:
            self._captures = {}
        return LetRelationDef(
            span=self._span(ctx),
            name=ctx.identifier().getText(),
            captures=captures,
            body=body,
        )

    def visitCaptureClause(self, ctx: _AntlrContext) -> CaptureClause:
        return CaptureClause(span=self._span(ctx), name=ctx.identifier().getText())

    def _relation_body_node(self, ctx: _AntlrContext) -> RelationBody:
        """Build the one complete body owned by a declaration or relation let."""

        if ctx.setOperationBody() is not None:
            return self.visit(ctx.setOperationBody())
        if ctx.valuesBody() is not None:
            return self.visit(ctx.valuesBody())
        body = ctx.tableBody()
        (
            from_clause,
            join_clauses,
            let_clause,
            where_clause,
            group_by_clause,
            select_items,
            named_windows,
            satisfying_clause,
            qualify_clause,
            order_by_clause,
            limit_clause,
        ) = self._relation_body(body)
        return SelectBody(
            span=self._span_between(body.fromClause(), body),
            from_clause=from_clause,
            join_clauses=join_clauses,
            where_clause=where_clause,
            group_by_clause=group_by_clause,
            select_items=select_items,
            order_by_clause=order_by_clause,
            limit_clause=limit_clause,
            satisfying_clause=satisfying_clause,
            qualify_clause=qualify_clause,
            let_clause=let_clause,
            named_windows=named_windows,
            distinct_clause=self._distinct_clause(body),
        )

    def visitValuesBody(self, ctx: _AntlrContext) -> ValuesBody:
        """Build a typed VALUES body without checking cells against the header."""

        return ValuesBody(
            span=self._span_from_token(ctx.VALUES().getSymbol(), ctx),
            columns=tuple(
                ValuesColumn(
                    span=self._span(item),
                    name=item.fieldName().getText(),
                    type=self.visit(item.typeExpression()),
                )
                for item in ctx.parameterList().parameter()
            ),
            rows=tuple(self.visit(item) for item in ctx.valuesRow()),
        )

    def visitValuesRow(self, ctx: _AntlrContext) -> ValuesRow:
        return ValuesRow(
            span=self._span(ctx),
            values=tuple(self.visit(item) for item in ctx.expression()),
        )

    def visitFromClause(
        self, ctx: _AntlrContext
    ) -> FromClause | TableFunctionFromClause:
        """Build one authored FROM input without resolving it."""

        identifiers = ctx.identifier()
        if ctx.callSuffix() is not None:
            function = identifiers[0]
            return TableFunctionFromClause(
                span=self._span(ctx),
                call=CallExpr(
                    span=self._span_between(function, ctx.callSuffix()),
                    callee=NameExpr(span=self._span(function), name=function.getText()),
                    arguments=tuple(
                        self.visit(item) for item in ctx.callSuffix().expression()
                    ),
                ),
                binding_name=identifiers[1].getText(),
            )
        return FromClause(
            span=self._span(ctx),
            source_name=identifiers[0].getText(),
        )

    def _distinct_clause(self, body: _AntlrContext) -> DistinctClause | None:
        token = body.selectClause().DISTINCT()
        if token is None:
            return None
        start = token.symbol
        end_line, end_column = self._end_position(start)
        return DistinctClause(
            span=Span(
                path=self.path,
                line=start.line,
                column=start.column + 1,
                end_line=end_line,
                end_column=end_column,
            )
        )

    def visitJoinClause(self, ctx: _AntlrContext) -> JoinClause:
        """Retain one exact authored JOIN without lowering it."""

        identifiers = ctx.identifier()
        body = ctx.joinBody()
        inline = ctx.joinInlineStep()
        if body is not None:
            source = body.identifier()
            steps = list(body.joinTraversalStep())
            on_clause = body.joinOnClause()
        elif inline is not None:
            source = inline.identifier()
            steps = (
                []
                if inline.joinTraversalStep() is None
                else [inline.joinTraversalStep()]
            )
            on_clause = inline.joinOnClause()
        else:
            # A bare JOIN has neither a block nor a header-line step.
            source, steps, on_clause = None, [], None
        return JoinClause(
            span=self._span(ctx),
            kind=AuthoredJoinKind(ctx.start.text),
            target_relation_name=identifiers[0].getText(),
            target_binding_name=identifiers[1].getText(),
            source_binding_name=None if source is None else source.getText(),
            traversal_steps=tuple(self.visit(step) for step in steps),
            on_clause=None if on_clause is None else self.visit(on_clause),
            target_binding_span=self._span(identifiers[1]),
        )

    def visitJoinOnClause(self, ctx: _AntlrContext) -> JoinOnClause:
        return JoinOnClause(
            span=self._span(ctx), expression=self.visit(ctx.expression())
        )

    def visitSetOperationBody(self, ctx: _AntlrContext) -> SetOperationBody:
        operator = ctx.setOperationKind()
        quantifier = ctx.setQuantifier()
        return SetOperationBody(
            span=self._span_between(operator, ctx),
            kind=SetOperationKind(operator.getText()),
            operator_span=self._span(operator),
            quantifier=(
                None
                if quantifier is None
                else SetOperationQuantifier(quantifier.getText())
            ),
            quantifier_span=(None if quantifier is None else self._span(quantifier)),
            operands=tuple(self.visit(item) for item in ctx.setOperand()),
        )

    def visitSetOperand(self, ctx: _AntlrContext) -> SetOperand:
        return SetOperand(
            span=self._span(ctx), relation_name=ctx.identifier().getText()
        )

    def visitJoinTraversalStep(self, ctx: _AntlrContext) -> JoinTraversalStep:
        """Retain one source-ordered VIA step with exact endpoint roles."""

        relationship, *roles = ctx.identifier()
        source, target = (None, None) if not roles else roles
        return JoinTraversalStep(
            span=self._span(ctx),
            relationship_name=relationship.getText(),
            source_endpoint_role=None if source is None else source.getText(),
            target_endpoint_role=None if target is None else target.getText(),
        )

    def visitWhereClause(self, ctx: _AntlrContext) -> WhereClause:
        """Build a relation filter without checking its expression type."""

        if ctx.COLON() is not None:
            expression = self._predicate_suite(ctx.predicateSuite())
        elif ctx.predicateBody() is not None:
            raise self._error(_WHERE_LINE_THEN_BLOCK, ctx.INDENT().getSymbol())
        else:
            expression = self.visit(ctx.expression())
        return WhereClause(span=self._span(ctx), expression=expression)

    def visitLetClause(self, ctx: _AntlrContext) -> LetClause:
        """Build a parse-only let block without binding or type checks."""

        return LetClause(
            span=self._span(ctx),
            bindings=tuple(
                self.visit(item)
                for line in self._clause_lines(ctx, "letLine", "letBody")
                for item in line.letBinding()
            ),
        )

    def visitLetBinding(self, ctx: _AntlrContext) -> LetBinding:
        """Build one source-ordered parse-only let binding."""

        return LetBinding(
            span=self._span(ctx),
            name=ctx.fieldName().getText(),
            expression=self.visit(ctx.expression()),
        )

    def visitGroupByClause(self, ctx: _AntlrContext) -> GroupByClause:
        """Build a non-empty grouping block without semantic validation."""

        return GroupByClause(
            span=self._span(ctx),
            items=tuple(
                self.visit(item)
                for line in self._clause_lines(ctx, "groupByLine", "groupByBody")
                for item in line.groupByItem()
            ),
        )

    def visitGroupByItem(self, ctx: _AntlrContext) -> GroupByItem:
        """Build one grouping key from the restricted dotted-name syntax."""

        if ctx.NUMBER() is not None:
            raise self._error(
                "Ordinal GROUP BY expressions are not supported.",
                ctx.NUMBER().getSymbol(),
            )
        return GroupByItem(
            span=self._span(ctx),
            key=self._dotted_name_expr(ctx.dottedName()),
        )

    def _select_items(self, ctx: _AntlrContext) -> tuple[SelectItem, ...]:
        """Build the projections of a ``select:`` header line or block lines."""

        header = ctx.selectLine()
        items: list[SelectItem] = []
        for line in self._clause_lines(ctx, "selectLine", "selectBody"):
            window = line.selectWindowItem()
            if window is not None and line is header:
                raise self._error(_WINDOW_ITEM_LINE, window.start)
            items.extend(self.visit(item) for item in line.selectItem())
            if window is not None:
                items.append(self.visit(window))
        return tuple(items)

    def visitSelectItem(self, ctx: _AntlrContext) -> SelectItem:
        """Build one projection; assignment syntax is confined to this rule."""

        return SelectItem(
            span=self._span(ctx),
            alias=ctx.fieldName().getText() if ctx.ASSIGN() is not None else None,
            expression=self.visit(ctx.expression()),
        )

    def visitSelectWindowItem(self, ctx: _AntlrContext) -> SelectItem:
        """Build one aliased window projection written alone on its line."""

        return SelectItem(
            span=self._span(ctx),
            alias=ctx.fieldName().getText(),
            expression=self.visit(ctx.windowExpression()),
        )

    def visitWindowExpression(self, ctx: _AntlrContext) -> WindowExpr:
        """Preserve one direct call and its exact inline or named use."""

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
        return self._window_expression(
            ctx, specification=use, use_kind=use_kind, base=base
        )

    def visitQualifyWindowExpression(self, ctx: _AntlrContext) -> WindowExpr:
        """Build one hidden inline window through the selected-use helper."""

        return self._window_expression(
            ctx,
            specification=ctx.qualifyInlineWindowSpec(),
            use_kind=WindowUseKind.INLINE,
            base=None,
        )

    def _window_expression(
        self,
        ctx: _AntlrContext,
        *,
        specification: _AntlrContext,
        use_kind: WindowUseKind,
        base: NamedWindowReference | None,
    ) -> WindowExpr:
        """Share exact call, modifier, identity, and specification construction.

        The call is built before its window use, which follows it in the source.
        """

        call = self._call_expr(ctx.dottedName(), ctx.callSuffix())
        callee = call.callee
        parts = (callee.name,) if isinstance(callee, NameExpr) else callee.parts
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
        if isinstance(specification, PiettoParser.WindowSpecContext):
            self._reject_inline_window_clause(specification)
        spec = cast(WindowSpec, self.visit(specification))
        return WindowExpr(
            span=self._span(ctx),
            call=call,
            spec=spec,
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

    def visitQualifyInlineWindowSpec(self, ctx: _AntlrContext) -> WindowSpec:
        """Build the shared nonempty inline specification."""

        return self._window_spec_from_body(
            ctx.windowSpecBody(),
            span=self._span(ctx),
        )

    def visitNamedWindowDeclaration(
        self,
        ctx: _AntlrContext,
    ) -> NamedWindowDeclaration:
        """Preserve one exact root, alias, or based declaration occurrence."""

        self._reject_inline_window_clause(ctx)
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
                for line in self._clause_lines(
                    partition_clause, "windowPartitionLine", "windowPartitionBody"
                )
                for item in line.windowPartitionItem()
            )
        order_by: tuple[OrderItem, ...] = ()
        if order_clause is not None:
            order_by = tuple(
                self._order_item(item, reject_ordinal=False)
                for item in self._order_items(order_clause)
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
            expression=self._predicate_suite(ctx.predicateSuite()),
        )

    def visitQualifyClause(self, ctx: _AntlrContext) -> QualifyClause:
        """Build one exact post-window predicate occurrence."""

        return QualifyClause(
            span=self._span(ctx),
            expression=self.visit(ctx.qualifyExpression()),
        )

    def visitOrderByClause(self, ctx: _AntlrContext) -> OrderByClause:
        """Build a non-empty sorting block without resolving its expressions."""

        return OrderByClause(
            span=self._span(ctx),
            items=tuple(self.visit(item) for item in self._order_items(ctx)),
        )

    def _order_items(self, ctx: _AntlrContext) -> Iterator[_AntlrContext]:
        """Yield the ordered item contexts of one ``order by:`` clause."""

        for line in self._clause_lines(ctx, "orderByLine", "orderByBody"):
            yield from line.orderItem()

    def _clause_lines(
        self, ctx: _AntlrContext, line_rule: str, body_rule: str
    ) -> Iterator[_AntlrContext]:
        """Yield the header line or the block lines of one list clause.

        A line ending in a comma, and a header line followed by an indented
        block, parse only so that they fail here with a targeted message.  Each
        fails when the caller asks for the next line, after it built this line's
        items, so build errors come in source order.
        """

        header = getattr(ctx, line_rule)()
        body = getattr(ctx, body_rule)()
        lines = [header] if header is not None else list(getattr(body, line_rule)())
        for line in lines:
            yield line
            # A comma directly before a line's closing NEWLINE trails.
            count = line.getChildCount()
            tokens = [
                cast(_TerminalNode, child).getSymbol()
                for child in (line.getChild(count - 2), line.getChild(count - 1))
                if isinstance(child, TerminalNode)
            ]
            if [token.type for token in tokens] == [
                PiettoParser.COMMA,
                PiettoParser.NEWLINE,
            ]:
                raise self._error(_TRAILING_COMMA, tokens[0])
        if header is not None and body is not None:
            raise self._error(_HEADER_LINE_THEN_BLOCK, ctx.INDENT().getSymbol())

    def _predicate_suite(self, ctx: _AntlrContext) -> Expression:
        """Join the lines of one condition block with ``and``, left to right.

        Each line stays one operand, as if parenthesized, and every fold node
        spans from the first line through the operand it adds.
        """

        first: _AntlrContext | None = None
        result: Expression | None = None
        for line in self._clause_lines(ctx, "predicateLine", "predicateBody"):
            operator = line.AND() or line.OR()
            if operator is not None:
                raise self._error(_PREDICATE_LINE_OPERATOR, operator.getSymbol())
            operand = cast(Expression, self.visit(line.expression()))
            if first is None or result is None:
                first, result = line, operand
                continue
            result = BinaryExpr(
                span=self._span_between(first, line),
                left=result,
                operator="and",
                right=operand,
            )
        assert result is not None
        return result

    def _reject_inline_window_clause(self, ctx: _AntlrContext) -> None:
        """Reject a window clause written on its window header line."""

        inline = ctx.windowInlineClause()
        if inline is not None:
            raise self._error(_COMPOUND_SAME_LINE, inline.start)

    @staticmethod
    def _error(message: str, token: Token) -> AstBuildError:
        """Build one source error located at a token."""

        return AstBuildError(message, line=token.line, column=token.column + 1)

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
        FromClause | TableFunctionFromClause,
        tuple[JoinClause, ...],
        LetClause | None,
        WhereClause | None,
        GroupByClause | None,
        tuple[SelectItem, ...],
        tuple[NamedWindowDeclaration, ...],
        SatisfyingClause | None,
        QualifyClause | None,
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
            self._select_items(ctx.selectClause()),
            tuple(self.visit(item) for item in ctx.namedWindowDeclaration()),
            (
                self.visit(ctx.satisfyingClause())
                if ctx.satisfyingClause() is not None
                else None
            ),
            (
                self.visit(ctx.qualifyClause())
                if ctx.qualifyClause() is not None
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
            name=ctx.fieldName().getText(),
            type=self.visit(ctx.typeExpression()),
        )

    def visitExpression(self, ctx: _AntlrContext) -> Expression:
        return self.visit(ctx.conditionalExpression())

    def visitQualifyExpression(self, ctx: _AntlrContext) -> Expression:
        return self.visit(ctx.qualifyConditionalExpression())

    def visitConditionalExpression(self, ctx: _AntlrContext) -> Expression:
        return self._conditional_expression(
            ctx,
            ctx.orExpression(),
            ctx.conditionalExpression(),
        )

    def visitQualifyConditionalExpression(self, ctx: _AntlrContext) -> Expression:
        return self._conditional_expression(
            ctx,
            ctx.qualifyOrExpression(),
            ctx.qualifyConditionalExpression(),
        )

    def _conditional_expression(
        self,
        ctx: _AntlrContext,
        operands: list[_AntlrContext],
        when_false: _AntlrContext | None,
    ) -> Expression:
        if when_false is None:
            return self.visit(operands[0])
        return ConditionalExpr(
            span=self._span(ctx),
            when_true=self.visit(operands[0]),
            condition=self.visit(operands[1]),
            when_false=self.visit(when_false),
        )

    def visitOrExpression(self, ctx: _AntlrContext) -> Expression:
        return self._fold_binary(ctx)

    def visitQualifyOrExpression(self, ctx: _AntlrContext) -> Expression:
        return self._fold_binary(ctx)

    def visitAndExpression(self, ctx: _AntlrContext) -> Expression:
        return self._fold_binary(ctx)

    def visitQualifyAndExpression(self, ctx: _AntlrContext) -> Expression:
        return self._fold_binary(ctx)

    def visitNotExpression(self, ctx: _AntlrContext) -> Expression:
        return self._not_expression(
            ctx, ctx.notExpression(), ctx.comparisonExpression()
        )

    def visitQualifyNotExpression(self, ctx: _AntlrContext) -> Expression:
        return self._not_expression(
            ctx,
            ctx.qualifyNotExpression(),
            ctx.qualifyComparisonExpression(),
        )

    def _not_expression(
        self,
        ctx: _AntlrContext,
        nested: _AntlrContext | None,
        comparison: _AntlrContext | None,
    ) -> Expression:
        if comparison is not None:
            return self.visit(comparison)
        assert nested is not None
        return UnaryExpr(
            span=self._span(ctx),
            operator="not",
            operand=self.visit(nested),
        )

    def visitComparisonExpression(self, ctx: _AntlrContext) -> Expression:
        return self._comparison_expression(
            ctx,
            ctx.additiveExpression(),
            ctx.expression(),
        )

    def visitQualifyComparisonExpression(self, ctx: _AntlrContext) -> Expression:
        return self._comparison_expression(
            ctx,
            ctx.qualifyAdditiveExpression(),
            ctx.qualifyExpression(),
        )

    def _comparison_expression(
        self,
        ctx: _AntlrContext,
        operands: list[_AntlrContext],
        membership_options: list[_AntlrContext],
    ) -> Expression:
        left = cast(Expression, self.visit(operands[0]))

        if ctx.comparisonOperator() is not None:
            operator = ctx.comparisonOperator().getText()
            return ComparisonExpr(
                span=self._span(ctx),
                left=left,
                operator="not like" if operator == "notlike" else operator,
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
        if ctx.IN() is not None and ctx.identifier() is not None:
            return RelationMembershipExpr(
                span=self._span(ctx),
                value=left,
                relation_name=ctx.identifier().getText(),
                negated=ctx.NOT() is not None,
            )
        if ctx.IN() is not None:
            return MembershipExpr(
                span=self._span(ctx),
                value=left,
                options=tuple(self.visit(option) for option in membership_options),
                negated=ctx.NOT() is not None,
            )
        return left

    def visitAdditiveExpression(self, ctx: _AntlrContext) -> Expression:
        return self._fold_binary(ctx)

    def visitQualifyAdditiveExpression(self, ctx: _AntlrContext) -> Expression:
        return self._fold_binary(ctx)

    def visitMultiplicativeExpression(self, ctx: _AntlrContext) -> Expression:
        return self._fold_binary(ctx)

    def visitQualifyMultiplicativeExpression(self, ctx: _AntlrContext) -> Expression:
        return self._fold_binary(ctx)

    def visitUnaryExpression(self, ctx: _AntlrContext) -> Expression:
        if ctx.primaryExpression() is not None:
            return self.visit(ctx.primaryExpression())
        return UnaryExpr(
            span=self._span(ctx),
            operator=ctx.getChild(0).getText(),
            operand=self.visit(ctx.unaryExpression()),
        )

    def visitQualifyUnaryExpression(self, ctx: _AntlrContext) -> Expression:
        if ctx.qualifyPrimaryExpression() is not None:
            return self.visit(ctx.qualifyPrimaryExpression())
        return UnaryExpr(
            span=self._span(ctx),
            operator=ctx.getChild(0).getText(),
            operand=self.visit(ctx.qualifyUnaryExpression()),
        )

    def visitPrimaryExpression(self, ctx: _AntlrContext) -> Expression:
        if ctx.literal() is not None:
            return self.visit(ctx.literal())
        if ctx.CAST() is not None:
            return CastExpr(
                span=self._span(ctx),
                value=self.visit(ctx.expression()),
                target=self.visit(ctx.typeExpression()),
            )
        if ctx.expression() is not None:
            return self.visit(ctx.expression())
        relation_read = self._relation_read(ctx)
        if relation_read is not None:
            return relation_read

        callee = self._dotted_name_expr(ctx.dottedName())
        if ctx.callSuffix() is None:
            return self._value_name(callee)
        return self._call_expr(ctx.dottedName(), ctx.callSuffix())

    def visitQualifyPrimaryExpression(self, ctx: _AntlrContext) -> Expression:
        if ctx.qualifyWindowExpression() is not None:
            return self.visit(ctx.qualifyWindowExpression())
        if ctx.literal() is not None:
            return self.visit(ctx.literal())
        if ctx.CAST() is not None:
            return CastExpr(
                span=self._span(ctx),
                value=self.visit(ctx.qualifyExpression()),
                target=self.visit(ctx.typeExpression()),
            )
        if ctx.qualifyExpression() is not None:
            return self.visit(ctx.qualifyExpression())
        relation_read = self._relation_read(ctx)
        if relation_read is not None:
            return relation_read

        callee = self._dotted_name_expr(ctx.dottedName())
        if ctx.qualifyCallSuffix() is None:
            return self._value_name(callee)
        return self._call_expr_from_arguments(
            ctx.dottedName(),
            ctx.qualifyCallSuffix(),
            ctx.qualifyCallSuffix().qualifyExpression(),
        )

    def _value_name(
        self, name: NameExpr | DottedNameExpr
    ) -> NameExpr | DottedNameExpr | ParameterRefExpr | CapturedFieldExpr:
        """A bare value name equal to a header parameter reads that parameter.

        Names that also denote a field, let, relation, output or window are a
        compile error, so this syntactic choice never changes meaning. Inside a
        let body, a two-part name qualified by a capture line reads that
        captured outer input; its capture name never binds an inner input.
        """

        if (
            type(name) is DottedNameExpr
            and len(name.parts) == 2
            and name.parts[0] in self._captures
        ):
            return CapturedFieldExpr(
                span=name.span,
                capture=name.parts[0],
                field=name.parts[1],
                ordinal=self._captures[name.parts[0]],
            )
        if type(name) is not NameExpr or name.name not in self._header:
            return name
        ordinal, parameter = self._header[name.name]
        return ParameterRefExpr(
            span=name.span,
            name=name.name,
            ordinal=ordinal,
            type_name=parameter.type.name,
            nullability=parameter.type.nullability,
        )

    def _relation_read(
        self, ctx: _AntlrContext
    ) -> RelationExistsExpr | RelationScalarExpr | None:
        """Build ``exists r`` or ``scalar r.c`` from either expression domain."""

        if ctx.EXISTS() is not None:
            return RelationExistsExpr(
                span=self._span(ctx), relation_name=ctx.identifier().getText()
            )
        if ctx.SCALAR() is not None:
            return RelationScalarExpr(
                span=self._span(ctx),
                relation_name=ctx.identifier().getText(),
                column_name=ctx.fieldName().getText(),
            )
        return None

    def _call_expr(
        self,
        dotted_name_ctx: _AntlrContext,
        call_suffix_ctx: _AntlrContext,
    ) -> CallExpr:
        """Build a call whose span ends at its call suffix, not a later suffix."""

        return self._call_expr_from_arguments(
            dotted_name_ctx,
            call_suffix_ctx,
            call_suffix_ctx.expression(),
        )

    def _call_expr_from_arguments(
        self,
        dotted_name_ctx: _AntlrContext,
        call_suffix_ctx: _AntlrContext,
        argument_contexts: list[_AntlrContext],
    ) -> CallExpr:
        """Build one call from either the global or QUALIFY expression domain."""

        return CallExpr(
            span=self._span_between(dotted_name_ctx, call_suffix_ctx),
            callee=self._dotted_name_expr(dotted_name_ctx),
            arguments=tuple(self.visit(argument) for argument in argument_contexts),
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
        if len(children) == 1:
            return result
        # Every fold node spans the whole chain, so the span is computed once.
        span = self._span(ctx)
        for index in range(1, len(children), 2):
            operator = cast(_TerminalNode, children[index]).getText()
            right = cast(Expression, self.visit(children[index + 1]))
            result = BinaryExpr(
                span=span,
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
        return self._span_from_token(start, end_ctx)

    def _span_from_token(self, start: Token, end_ctx: ParserRuleContext) -> Span:
        """Build a logical span from one token through another context."""

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

        # Right-to-left depth-first order without recursion or copying: the
        # first token met that is not layout is the last one in source order,
        # and only the nodes passed before it are touched.
        pending: list[Iterator[Any]] = [iter((node,))]
        while pending:
            current = next(pending[-1], None)
            if current is None:
                pending.pop()
            elif isinstance(current, TerminalNode):
                token = cast(_TerminalNode, current).getSymbol()
                if token.type not in _LAYOUT_TOKEN_TYPES:
                    return token
            else:
                pending.append(reversed(getattr(current, "children", None) or ()))
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
