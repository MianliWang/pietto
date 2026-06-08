"""Convert generated ANTLR parse trees into Pietto-owned AST dataclasses."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from antlr4 import ParserRuleContext
from antlr4.Token import Token
from antlr4.tree.Tree import TerminalNode

from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    ConstraintDef,
    DeriveDef,
    DottedNameExpr,
    EnsureClause,
    EnumDef,
    Expression,
    Header,
    IsNullExpr,
    LiteralExpr,
    NameExpr,
    Parameter,
    Script,
    Span,
    TypeArgument,
    TypeDef,
    TypeExpr,
    UnaryExpr,
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
    ) -> TypeDef | EnumDef | ConstraintDef | DeriveDef:
        if ctx.typeDefinition() is not None:
            return self.visit(ctx.typeDefinition())
        if ctx.enumDefinition() is not None:
            return self.visit(ctx.enumDefinition())
        if ctx.constraintDefinition() is not None:
            return self.visit(ctx.constraintDefinition())
        return self.visit(ctx.deriveDefinition())

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
        arguments: tuple[TypeArgument, ...] = ()
        if ctx.typeArguments() is not None:
            arguments = tuple(
                self.visit(item) for item in ctx.typeArguments().typeArgument()
            )
        return TypeExpr(
            span=self._span(ctx),
            name=ctx.IDENTIFIER().getText(),
            arguments=arguments,
            nullable=ctx.QUESTION() is not None,
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

        parts = tuple(token.getText() for token in ctx.dottedName().IDENTIFIER())
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
