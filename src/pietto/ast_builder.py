"""Convert generated ANTLR parse trees into Pietto-owned AST dataclasses."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from antlr4 import ParserRuleContext
from antlr4.Token import Token
from antlr4.tree.Tree import TerminalNode

from pietto.ast_nodes import (
    Annotation,
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
    Expression,
    FieldDef,
    FromClause,
    Header,
    IndexDef,
    IsNullExpr,
    LiteralExpr,
    NameExpr,
    Nullability,
    Parameter,
    Script,
    ShapeDef,
    ShapeItem,
    SourceDef,
    Span,
    SelectItem,
    TableDef,
    TypeArgument,
    TypeDef,
    TypeExpr,
    UnaryExpr,
    UniqueDef,
    WhereClause,
)
from pietto.errors import AstBuildError, source_path
from pietto.generated.PiettoParser import PiettoParser
from pietto.generated.PiettoVisitor import PiettoVisitor


class AstBuilder(PiettoVisitor):
    """Build an ANTLR-independent AST from a successfully parsed script."""

    def __init__(self, path: str | Path | None) -> None:
        """Create a builder whose AST spans use the supplied source path."""

        self.path = source_path(path)

    def visitScript(self, ctx: PiettoParser.ScriptContext) -> Script:
        """Build the root script node."""

        header = self.visit(ctx.header()) if ctx.header() is not None else None
        definitions = tuple(self.visit(item) for item in ctx.definition())
        return Script(
            span=self._span(ctx),
            header=cast(Header | None, header),
            definitions=definitions,
        )

    def visitHeader(self, ctx: PiettoParser.HeaderContext) -> Header:
        version = (
            ctx.versionDecl().NUMBER().getText()
            if ctx.versionDecl() is not None
            else None
        )
        mode = self._mode(ctx.modeDecl()) if ctx.modeDecl() is not None else None
        dialect = (
            ctx.dialectDecl().IDENTIFIER().getText()
            if ctx.dialectDecl() is not None
            else None
        )
        encoding = (
            ctx.encodingDecl().IDENTIFIER().getText()
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
        self, ctx: PiettoParser.DefinitionContext
    ) -> (
        TypeDef | EnumDef | ConstraintDef | DeriveDef | ShapeDef | SourceDef | TableDef
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
        return self.visit(ctx.tableDefinition())

    def visitTypeDefinition(self, ctx: PiettoParser.TypeDefinitionContext) -> TypeDef:
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
            name=ctx.IDENTIFIER().getText(),
            base=self.visit(ctx.typeExpression()),
            ensures=tuple(ensures),
        )

    def visitEnsureClause(self, ctx: PiettoParser.EnsureClauseContext) -> EnsureClause:
        return EnsureClause(
            span=self._span(ctx),
            expression=self.visit(ctx.expression()),
        )

    def visitTypeExpression(self, ctx: PiettoParser.TypeExpressionContext) -> TypeExpr:
        return self._type_expression(
            ctx.typeReference(),
            span_context=ctx,
            nullability=self._nullability(ctx.nullabilityModifier()),
        )

    def visitTypeArgument(self, ctx: PiettoParser.TypeArgumentContext) -> TypeArgument:
        name = ctx.typeArgumentName().getText() if ctx.ASSIGN() is not None else None
        return TypeArgument(
            span=self._span(ctx),
            name=name,
            value=self.visit(ctx.expression()),
        )

    def visitEnumDefinition(self, ctx: PiettoParser.EnumDefinitionContext) -> EnumDef:
        return EnumDef(
            span=self._span(ctx),
            name=ctx.IDENTIFIER().getText(),
            members=tuple(
                item.IDENTIFIER().getText() for item in ctx.enumBody().enumItem()
            ),
        )

    def visitConstraintDefinition(
        self, ctx: PiettoParser.ConstraintDefinitionContext
    ) -> ConstraintDef:
        # Keep the declared return type as TypeExpr syntax. Enforcing a Bool
        # result belongs to Phase 2 rather than parse-tree construction.
        return ConstraintDef(
            span=self._span(ctx),
            name=ctx.IDENTIFIER().getText(),
            parameters=self._parameters(ctx.parameterList()),
            return_type=self.visit(ctx.typeExpression()),
            body=self.visit(ctx.constraintBody().expression()),
        )

    def visitDeriveDefinition(
        self, ctx: PiettoParser.DeriveDefinitionContext
    ) -> DeriveDef:
        """Build a derive declaration without applying semantic checks."""

        # Keep the return type as TypeExpr syntax. Names, purity, recursion, and
        # type compatibility are intentionally left to Phase 2.
        return DeriveDef(
            span=self._span(ctx),
            name=ctx.IDENTIFIER().getText(),
            parameters=self._parameters(ctx.parameterList()),
            return_type=self.visit(ctx.typeExpression()),
            body=self.visit(ctx.deriveBody().expression()),
        )

    def visitShapeDefinition(
        self, ctx: PiettoParser.ShapeDefinitionContext
    ) -> ShapeDef:
        """Build a shape while preserving mixed item source order."""

        return ShapeDef(
            span=self._span(ctx),
            name=ctx.IDENTIFIER().getText(),
            items=tuple(self.visit(item) for item in ctx.shapeBody().shapeItem()),
        )

    def visitShapeItem(self, ctx: PiettoParser.ShapeItemContext) -> ShapeItem:
        """Build one shape item without losing its source position."""

        if ctx.fieldDefinition() is not None:
            return self.visit(ctx.fieldDefinition())
        if ctx.checkDefinition() is not None:
            return self.visit(ctx.checkDefinition())
        if ctx.uniqueDefinition() is not None:
            return self.visit(ctx.uniqueDefinition())
        return self.visit(ctx.indexDefinition())

    def visitFieldDefinition(
        self, ctx: PiettoParser.FieldDefinitionContext
    ) -> FieldDef:
        """Build one field without resolving modifiers or type semantics."""

        field_type = ctx.typeExpression()
        modifiers = ctx.fieldModifier()
        return FieldDef(
            span=self._span(ctx),
            name=ctx.IDENTIFIER().getText(),
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

    def visitAnnotation(self, ctx: PiettoParser.AnnotationContext) -> Annotation:
        """Build a bare field annotation without validating its name."""

        return Annotation(
            span=self._span(ctx),
            name=ctx.IDENTIFIER().getText(),
        )

    def visitFieldEnsureClause(
        self, ctx: PiettoParser.FieldEnsureClauseContext
    ) -> EnsureClause:
        """Reuse EnsureClause for a parse-only field guarantee."""

        return EnsureClause(
            span=self._span(ctx),
            expression=self.visit(ctx.expression()),
        )

    def visitCheckDefinition(
        self, ctx: PiettoParser.CheckDefinitionContext
    ) -> CheckDef:
        """Build a shape check without validating names or expression type."""

        return CheckDef(
            span=self._span(ctx),
            name=ctx.IDENTIFIER().getText(),
            expression=self.visit(ctx.checkBody().expression()),
        )

    def visitUniqueDefinition(
        self, ctx: PiettoParser.UniqueDefinitionContext
    ) -> UniqueDef:
        """Build a unique clause without resolving or deduplicating fields."""

        identifiers = ctx.IDENTIFIER()
        return UniqueDef(
            span=self._span(ctx),
            name=identifiers[0].getText(),
            field_names=tuple(identifier.getText() for identifier in identifiers[1:]),
        )

    def visitIndexDefinition(
        self, ctx: PiettoParser.IndexDefinitionContext
    ) -> IndexDef:
        """Build an index clause without applying physical or semantic checks."""

        identifiers = ctx.IDENTIFIER()
        return IndexDef(
            span=self._span(ctx),
            name=identifiers[0].getText(),
            field_names=tuple(identifier.getText() for identifier in identifiers[1:]),
            predicate=(
                self.visit(ctx.expression()) if ctx.expression() is not None else None
            ),
        )

    def visitSourceDefinition(
        self, ctx: PiettoParser.SourceDefinitionContext
    ) -> SourceDef:
        """Build a source binding without validating or executing its connector."""

        identifiers = ctx.IDENTIFIER()
        return SourceDef(
            span=self._span(ctx),
            name=identifiers[0].getText(),
            shape_name=identifiers[1].getText() if ctx.COLON() is not None else None,
            connector=self.visit(ctx.expression()),
        )

    def visitTableDefinition(
        self, ctx: PiettoParser.TableDefinitionContext
    ) -> TableDef:
        """Build a minimal table without resolving inputs or projection names."""

        body = ctx.tableBody()
        return TableDef(
            span=self._span(ctx),
            name=ctx.IDENTIFIER().getText(),
            from_clause=self.visit(body.fromClause()),
            where_clause=(
                self.visit(body.whereClause())
                if body.whereClause() is not None
                else None
            ),
            select_items=tuple(
                self.visit(item)
                for item in body.selectClause().selectBody().selectItem()
            ),
        )

    def visitFromClause(self, ctx: PiettoParser.FromClauseContext) -> FromClause:
        """Build a table input reference without resolving it."""

        return FromClause(
            span=self._span(ctx),
            source_name=ctx.IDENTIFIER().getText(),
        )

    def visitWhereClause(self, ctx: PiettoParser.WhereClauseContext) -> WhereClause:
        """Build a table filter without checking its expression type."""

        return WhereClause(
            span=self._span(ctx),
            expression=self.visit(ctx.expression()),
        )

    def visitSelectItem(self, ctx: PiettoParser.SelectItemContext) -> SelectItem:
        """Build one projection; assignment syntax is confined to this rule."""

        return SelectItem(
            span=self._span(ctx),
            alias=ctx.IDENTIFIER().getText() if ctx.ASSIGN() is not None else None,
            expression=self.visit(ctx.expression()),
        )

    def visitParameter(self, ctx: PiettoParser.ParameterContext) -> Parameter:
        return Parameter(
            span=self._span(ctx),
            name=ctx.IDENTIFIER().getText(),
            type=self.visit(ctx.typeExpression()),
        )

    def visitExpression(self, ctx: PiettoParser.ExpressionContext) -> Expression:
        return self.visit(ctx.orExpression())

    def visitOrExpression(self, ctx: PiettoParser.OrExpressionContext) -> Expression:
        return self._fold_binary(ctx)

    def visitAndExpression(self, ctx: PiettoParser.AndExpressionContext) -> Expression:
        return self._fold_binary(ctx)

    def visitComparisonExpression(
        self, ctx: PiettoParser.ComparisonExpressionContext
    ) -> Expression:
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

    def visitAdditiveExpression(
        self, ctx: PiettoParser.AdditiveExpressionContext
    ) -> Expression:
        return self._fold_binary(ctx)

    def visitMultiplicativeExpression(
        self, ctx: PiettoParser.MultiplicativeExpressionContext
    ) -> Expression:
        return self._fold_binary(ctx)

    def visitUnaryExpression(
        self, ctx: PiettoParser.UnaryExpressionContext
    ) -> Expression:
        if ctx.primaryExpression() is not None:
            return self.visit(ctx.primaryExpression())
        return UnaryExpr(
            span=self._span(ctx),
            operator=ctx.getChild(0).getText(),
            operand=self.visit(ctx.unaryExpression()),
        )

    def visitPrimaryExpression(
        self, ctx: PiettoParser.PrimaryExpressionContext
    ) -> Expression:
        if ctx.literal() is not None:
            return self.visit(ctx.literal())
        if ctx.expression() is not None:
            return self.visit(ctx.expression())

        parts = tuple(part.getText() for part in ctx.dottedName().namePart())
        callee: NameExpr | DottedNameExpr
        if len(parts) == 1:
            callee = NameExpr(span=self._span(ctx.dottedName()), name=parts[0])
        else:
            callee = DottedNameExpr(
                span=self._span(ctx.dottedName()),
                parts=parts,
            )
        if ctx.callSuffix() is None:
            return callee
        return CallExpr(
            span=self._span(ctx),
            callee=callee,
            arguments=tuple(
                self.visit(argument) for argument in ctx.callSuffix().expression()
            ),
        )

    def visitLiteral(self, ctx: PiettoParser.LiteralContext) -> LiteralExpr:
        text = ctx.getText()
        value: str | int | float | bool | None
        if ctx.STRING() is not None:
            value = self._decode_string_literal(ctx)
        elif ctx.NUMBER() is not None:
            value = float(text) if "." in text else int(text)
        elif ctx.TRUE() is not None:
            value = True
        elif ctx.FALSE() is not None:
            value = False
        else:
            value = None
        return LiteralExpr(span=self._span(ctx), value=value)

    def _parameters(
        self, ctx: PiettoParser.ParameterListContext | None
    ) -> tuple[Parameter, ...]:
        """Build parameters shared by constraint and derive declarations."""

        if ctx is None:
            return ()
        return tuple(self.visit(parameter) for parameter in ctx.parameter())

    def _type_expression(
        self,
        ctx: PiettoParser.TypeReferenceContext,
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
            name=ctx.IDENTIFIER().getText(),
            arguments=arguments,
            nullability=nullability,
        )

    @staticmethod
    def _nullability(
        ctx: PiettoParser.NullabilityModifierContext | None,
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
            operator = cast(TerminalNode, children[index]).getText()
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
            token = node.getSymbol()
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
    def _decode_string_literal(ctx: PiettoParser.LiteralContext) -> str:
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
    def _mode(ctx: PiettoParser.ModeDeclContext) -> str:
        """Extract the selected mode keyword from a mode declaration."""

        for token_type in ("LOOSE", "CHECKED", "STRICT"):
            token = getattr(ctx, token_type)()
            if token is not None:
                return token.getText()
        raise ValueError("mode declaration has no mode token")

    def visitChildren(self, node: Any) -> Any:
        return super().visitChildren(node)
