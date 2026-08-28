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


    # Visit a parse tree produced by PiettoParser#relationshipDefinition.
    def visitRelationshipDefinition(self, ctx:PiettoParser.RelationshipDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#relationshipBody.
    def visitRelationshipBody(self, ctx:PiettoParser.RelationshipBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#relationshipEndpoint.
    def visitRelationshipEndpoint(self, ctx:PiettoParser.RelationshipEndpointContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#moduleStatement.
    def visitModuleStatement(self, ctx:PiettoParser.ModuleStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#importStatement.
    def visitImportStatement(self, ctx:PiettoParser.ImportStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#importTarget.
    def visitImportTarget(self, ctx:PiettoParser.ImportTargetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#importBody.
    def visitImportBody(self, ctx:PiettoParser.ImportBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#importItem.
    def visitImportItem(self, ctx:PiettoParser.ImportItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#exportStatement.
    def visitExportStatement(self, ctx:PiettoParser.ExportStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#exportBody.
    def visitExportBody(self, ctx:PiettoParser.ExportBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#exportItem.
    def visitExportItem(self, ctx:PiettoParser.ExportItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#moduleDeclarationKind.
    def visitModuleDeclarationKind(self, ctx:PiettoParser.ModuleDeclarationKindContext):
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


    # Visit a parse tree produced by PiettoParser#typeReference.
    def visitTypeReference(self, ctx:PiettoParser.TypeReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#nullabilityModifier.
    def visitNullabilityModifier(self, ctx:PiettoParser.NullabilityModifierContext):
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


    # Visit a parse tree produced by PiettoParser#shapeDefinition.
    def visitShapeDefinition(self, ctx:PiettoParser.ShapeDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#shapeBody.
    def visitShapeBody(self, ctx:PiettoParser.ShapeBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#shapeItem.
    def visitShapeItem(self, ctx:PiettoParser.ShapeItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#fieldDefinition.
    def visitFieldDefinition(self, ctx:PiettoParser.FieldDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#fieldDeriveClause.
    def visitFieldDeriveClause(self, ctx:PiettoParser.FieldDeriveClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#fieldModifier.
    def visitFieldModifier(self, ctx:PiettoParser.FieldModifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#annotation.
    def visitAnnotation(self, ctx:PiettoParser.AnnotationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#fieldEnsureClause.
    def visitFieldEnsureClause(self, ctx:PiettoParser.FieldEnsureClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#checkDefinition.
    def visitCheckDefinition(self, ctx:PiettoParser.CheckDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#checkBody.
    def visitCheckBody(self, ctx:PiettoParser.CheckBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#uniqueDefinition.
    def visitUniqueDefinition(self, ctx:PiettoParser.UniqueDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#indexDefinition.
    def visitIndexDefinition(self, ctx:PiettoParser.IndexDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#sourceDefinition.
    def visitSourceDefinition(self, ctx:PiettoParser.SourceDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#tableDefinition.
    def visitTableDefinition(self, ctx:PiettoParser.TableDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#queryDefinition.
    def visitQueryDefinition(self, ctx:PiettoParser.QueryDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#tableBody.
    def visitTableBody(self, ctx:PiettoParser.TableBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#fromClause.
    def visitFromClause(self, ctx:PiettoParser.FromClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#letClause.
    def visitLetClause(self, ctx:PiettoParser.LetClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#letBody.
    def visitLetBody(self, ctx:PiettoParser.LetBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#letBinding.
    def visitLetBinding(self, ctx:PiettoParser.LetBindingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#whereClause.
    def visitWhereClause(self, ctx:PiettoParser.WhereClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#groupByClause.
    def visitGroupByClause(self, ctx:PiettoParser.GroupByClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#groupByBody.
    def visitGroupByBody(self, ctx:PiettoParser.GroupByBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#groupByItem.
    def visitGroupByItem(self, ctx:PiettoParser.GroupByItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#selectClause.
    def visitSelectClause(self, ctx:PiettoParser.SelectClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#selectBody.
    def visitSelectBody(self, ctx:PiettoParser.SelectBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#selectItem.
    def visitSelectItem(self, ctx:PiettoParser.SelectItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#windowExpression.
    def visitWindowExpression(self, ctx:PiettoParser.WindowExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#windowSpec.
    def visitWindowSpec(self, ctx:PiettoParser.WindowSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#windowSpecBody.
    def visitWindowSpecBody(self, ctx:PiettoParser.WindowSpecBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#partitionByClause.
    def visitPartitionByClause(self, ctx:PiettoParser.PartitionByClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#windowPartitionBody.
    def visitWindowPartitionBody(self, ctx:PiettoParser.WindowPartitionBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#windowPartitionItem.
    def visitWindowPartitionItem(self, ctx:PiettoParser.WindowPartitionItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#rowsFrameClause.
    def visitRowsFrameClause(self, ctx:PiettoParser.RowsFrameClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#frameBound.
    def visitFrameBound(self, ctx:PiettoParser.FrameBoundContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#satisfyingClause.
    def visitSatisfyingClause(self, ctx:PiettoParser.SatisfyingClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#orderByClause.
    def visitOrderByClause(self, ctx:PiettoParser.OrderByClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#orderByBody.
    def visitOrderByBody(self, ctx:PiettoParser.OrderByBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#orderItem.
    def visitOrderItem(self, ctx:PiettoParser.OrderItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#limitClause.
    def visitLimitClause(self, ctx:PiettoParser.LimitClauseContext):
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


    # Visit a parse tree produced by PiettoParser#namePart.
    def visitNamePart(self, ctx:PiettoParser.NamePartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#identifier.
    def visitIdentifier(self, ctx:PiettoParser.IdentifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#callSuffix.
    def visitCallSuffix(self, ctx:PiettoParser.CallSuffixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PiettoParser#literal.
    def visitLiteral(self, ctx:PiettoParser.LiteralContext):
        return self.visitChildren(ctx)



del PiettoParser