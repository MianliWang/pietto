# Generated from grammar/Pietto.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .PiettoParser import PiettoParser
else:
    from PiettoParser import PiettoParser

# This class defines a complete generic visitor for a parse tree produced by PiettoParser.

class PiettoVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by PiettoParser#script.
    def visitScript(self, ctx:PiettoParser.ScriptContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#header.
    def visitHeader(self, ctx:PiettoParser.HeaderContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#versionDecl.
    def visitVersionDecl(self, ctx:PiettoParser.VersionDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#modeDecl.
    def visitModeDecl(self, ctx:PiettoParser.ModeDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#dialectDecl.
    def visitDialectDecl(self, ctx:PiettoParser.DialectDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#encodingDecl.
    def visitEncodingDecl(self, ctx:PiettoParser.EncodingDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#definition.
    def visitDefinition(self, ctx:PiettoParser.DefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#typeDefinition.
    def visitTypeDefinition(self, ctx:PiettoParser.TypeDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#typeBody.
    def visitTypeBody(self, ctx:PiettoParser.TypeBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#ensureClause.
    def visitEnsureClause(self, ctx:PiettoParser.EnsureClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#typeExpression.
    def visitTypeExpression(self, ctx:PiettoParser.TypeExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#typeArguments.
    def visitTypeArguments(self, ctx:PiettoParser.TypeArgumentsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#typeArgument.
    def visitTypeArgument(self, ctx:PiettoParser.TypeArgumentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#typeArgumentName.
    def visitTypeArgumentName(self, ctx:PiettoParser.TypeArgumentNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#enumDefinition.
    def visitEnumDefinition(self, ctx:PiettoParser.EnumDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#enumBody.
    def visitEnumBody(self, ctx:PiettoParser.EnumBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#enumItem.
    def visitEnumItem(self, ctx:PiettoParser.EnumItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#constraintDefinition.
    def visitConstraintDefinition(self, ctx:PiettoParser.ConstraintDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#parameterList.
    def visitParameterList(self, ctx:PiettoParser.ParameterListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#parameter.
    def visitParameter(self, ctx:PiettoParser.ParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#constraintBody.
    def visitConstraintBody(self, ctx:PiettoParser.ConstraintBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#deriveDefinition.
    def visitDeriveDefinition(self, ctx:PiettoParser.DeriveDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#deriveBody.
    def visitDeriveBody(self, ctx:PiettoParser.DeriveBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#expression.
    def visitExpression(self, ctx:PiettoParser.ExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#orExpression.
    def visitOrExpression(self, ctx:PiettoParser.OrExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#andExpression.
    def visitAndExpression(self, ctx:PiettoParser.AndExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#comparisonExpression.
    def visitComparisonExpression(self, ctx:PiettoParser.ComparisonExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#comparisonOperator.
    def visitComparisonOperator(self, ctx:PiettoParser.ComparisonOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#additiveExpression.
    def visitAdditiveExpression(self, ctx:PiettoParser.AdditiveExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#multiplicativeExpression.
    def visitMultiplicativeExpression(self, ctx:PiettoParser.MultiplicativeExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#unaryExpression.
    def visitUnaryExpression(self, ctx:PiettoParser.UnaryExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#primaryExpression.
    def visitPrimaryExpression(self, ctx:PiettoParser.PrimaryExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#dottedName.
    def visitDottedName(self, ctx:PiettoParser.DottedNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#callSuffix.
    def visitCallSuffix(self, ctx:PiettoParser.CallSuffixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#literal.
    def visitLiteral(self, ctx:PiettoParser.LiteralContext):
        return self.visitChildren(ctx)



del PiettoParser