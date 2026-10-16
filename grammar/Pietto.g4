grammar Pietto;

tokens {
    INDENT,
    DEDENT
}

script
    : NEWLINE* header? NEWLINE* ((definition | relationshipDefinition | moduleStatement) NEWLINE*)* EOF
    ;

header
    : versionDecl modeDecl? dialectDecl? encodingDecl?
    | modeDecl dialectDecl? encodingDecl?
    | dialectDecl encodingDecl?
    | encodingDecl
    ;

versionDecl
    : PIETTO NUMBER NEWLINE
    ;

modeDecl
    : MODE (LOOSE | CHECKED | STRICT) NEWLINE
    ;

dialectDecl
    : DIALECT identifier NEWLINE
    ;

encodingDecl
    : ENCODING identifier NEWLINE
    ;

definition
    : typeDefinition
    | enumDefinition
    | constraintDefinition
    | deriveDefinition
    | shapeDefinition
    | sourceDefinition
    | tableDefinition
    | queryDefinition
    | functionDefinition
    ;

// Relationship declarations remain metadata outside semantic definitions.  The
// one-line form names its two endpoints by their relations; the builder checks
// its shape.
relationshipDefinition
    : RELATIONSHIP identifier COLON NEWLINE NEWLINE* INDENT relationshipBody DEDENT
    | RELATIONSHIP identifier COLON expression NEWLINE
    ;

relationshipBody
    : NEWLINE* relationshipEndpoint NEWLINE* relationshipEndpoint NEWLINE* relationshipMatchClause? NEWLINE*
    ;

relationshipEndpoint
    : ENDPOINT identifier COLON identifier NEWLINE
    ;

relationshipMatchClause
    : ON expression NEWLINE
    ;

// Module syntax is parser-only metadata outside semantic definitions.
moduleStatement
    : importStatement
    | exportStatement
    ;

importStatement
    : IMPORT importTarget COLON NEWLINE NEWLINE* INDENT importBody DEDENT
    ;

importTarget
    : STRING
    ;

importBody
    : NEWLINE* importItem (importItem | NEWLINE)*
    ;

importItem
    : moduleDeclarationKind identifier (AS identifier)? NEWLINE
    ;

exportStatement
    : EXPORT COLON NEWLINE NEWLINE* INDENT exportBody DEDENT
    ;

exportBody
    : NEWLINE* exportItem (exportItem | NEWLINE)*
    ;

exportItem
    : moduleDeclarationKind identifier NEWLINE
    ;

moduleDeclarationKind
    : TYPE
    | ENUM
    | SHAPE
    | SOURCE
    | TABLE
    | QUERY
    ;

// Pietto blocks use ':' plus NEWLINE/INDENT/DEDENT, never brace delimiters.
typeDefinition
    : TYPE identifier ASSIGN typeExpression NEWLINE
    | TYPE identifier ASSIGN typeExpression ENSURE expression NEWLINE
    | TYPE identifier ASSIGN typeExpression COLON NEWLINE NEWLINE* INDENT typeBody DEDENT
    ;

typeBody
    : (ensureClause | NEWLINE)+
    ;

ensureClause
    : ENSURE expression NEWLINE
    ;

typeExpression
    : typeReference nullabilityModifier?
    ;

typeReference
    : identifier typeArguments?
    ;

// Nullability syntax is explicit; absence of a modifier remains implicit.
nullabilityModifier
    : NULLABLE
    | NOT NULL
    ;

typeArguments
    : LPAREN (typeArgument (COMMA typeArgument)* COMMA?)? RPAREN
    ;

// Assignment is limited to declarations and named arguments, not expressions.
typeArgument
    : typeArgumentName ASSIGN expression
    | expression
    ;

typeArgumentName
    : identifier
    | ENCODING
    ;

// A list clause puts its items on the header line after ':' or in an indented
// block whose every line may itself be a comma list.  The optional block after
// a header line and a trailing comma are parsed only so the builder can reject
// them with a targeted message.
enumDefinition
    : ENUM identifier COLON NEWLINE NEWLINE* INDENT enumBody DEDENT
    | ENUM identifier COLON enumLine (INDENT enumBody DEDENT)?
    ;

enumBody
    : (enumLine | NEWLINE)+
    ;

enumLine
    : identifier (COMMA identifier)* COMMA? NEWLINE
    ;

// Phase 1 parses any return TypeExpr; semantic analysis later requires Bool.
constraintDefinition
    : CONSTRAINT identifier LPAREN parameterList? RPAREN ARROW typeExpression COLON NEWLINE NEWLINE* INDENT constraintBody DEDENT
    ;

parameterList
    : parameter (COMMA parameter)* COMMA?
    ;

parameter
    : fieldName COLON typeExpression
    ;

constraintBody
    : NEWLINE* expression NEWLINE NEWLINE*
    ;

// A pure inline function returns one expression, on its header line or as the
// only statement of its block.
functionDefinition
    : DEF identifier LPAREN parameterList? RPAREN ARROW typeExpression COLON NEWLINE NEWLINE* INDENT functionBody DEDENT
    | DEF identifier LPAREN parameterList? RPAREN ARROW typeExpression COLON RETURN expression NEWLINE
    ;

functionBody
    : NEWLINE* RETURN expression NEWLINE NEWLINE*
    ;

// Derive signatures and bodies are parsed only; Phase 2 checks their semantics.
deriveDefinition
    : DERIVE identifier LPAREN parameterList? RPAREN ARROW typeExpression COLON NEWLINE NEWLINE* INDENT deriveBody DEDENT
    ;

deriveBody
    : NEWLINE* expression NEWLINE NEWLINE*
    ;

// Phase 1 shapes preserve ordered items; their semantics come later.
shapeDefinition
    : SHAPE identifier COLON NEWLINE NEWLINE* INDENT shapeBody DEDENT
    ;

shapeBody
    : NEWLINE* shapeItem (shapeItem | NEWLINE)*
    ;

shapeItem
    : fieldDefinition
    | checkDefinition
    | uniqueDefinition
    | indexDefinition
    ;

fieldDefinition
    : fieldName COLON typeExpression fieldDeriveClause? fieldModifier* NEWLINE
    ;

// Field derive is parse-only and must precede annotations and ensure clauses.
fieldDeriveClause
    : DERIVE expression
    ;

// Field annotations and ensures are syntax-only until Phase 2 semantic checks.
fieldModifier
    : annotation
    | fieldEnsureClause
    ;

annotation
    : AT identifier
    ;

fieldEnsureClause
    : ENSURE expression
    ;

// Shape checks are named predicate clauses parsed only in Phase 1.
checkDefinition
    : CHECK identifier COLON predicateSuite
    ;

// Shape unique clauses record names and target fields only in Phase 1.
uniqueDefinition
    : UNIQUE identifier ON fieldName (COMMA fieldName)* NEWLINE
    ;

// Shape index clauses are parse-only physical-design hints in Phase 1.
indexDefinition
    : INDEX identifier ON fieldName (COMMA fieldName)* (WHEN expression)? NEWLINE
    ;

// Source bindings retain connector expressions without validating or executing them.
sourceDefinition
    : SOURCE identifier (COLON identifier)? IS expression NEWLINE
    ;

// Relations support from, optional where/group by, ordered select, optional
// satisfying/qualify, ordered order items, and limit.  Relation lets may precede
// a body; a body may also be a set operation or typed VALUES.
tableDefinition
    : TABLE identifier COLON NEWLINE NEWLINE* INDENT (NEWLINE* letRelationDefinition)* (tableBody | setOperationBody | valuesBody) DEDENT
    ;

// Phase 1 queries reuse the minimal table body without execution semantics.
queryDefinition
    : QUERY queryHeader COLON NEWLINE NEWLINE* INDENT (NEWLINE* letRelationDefinition)* (tableBody | setOperationBody | valuesBody) DEDENT
    ;

// Only an entry query header declares parameters.  The optional list ends this
// rule so a missing ':' keeps single-token recovery.
queryHeader
    : identifier (LPAREN parameterList RPAREN)?
    ;

// A relation let is one level deep; only its body may start with captures.
letRelationDefinition
    : LET identifier COLON NEWLINE NEWLINE* INDENT (NEWLINE* captureClause)* (tableBody | setOperationBody | valuesBody) DEDENT
    ;

captureClause
    : CAPTURE identifier NEWLINE
    ;

// Typed VALUES rows are one per line; a header without ':' has zero rows.
valuesBody
    : NEWLINE* VALUES LPAREN parameterList RPAREN (COLON NEWLINE NEWLINE* INDENT valuesRow (valuesRow | NEWLINE)* DEDENT | NEWLINE) NEWLINE*
    ;

valuesRow
    : expression (COMMA expression)* NEWLINE
    ;

tableBody
    : NEWLINE* fromClause NEWLINE* (joinClause NEWLINE*)* letClause? NEWLINE* whereClause? NEWLINE* groupByClause? NEWLINE* selectClause NEWLINE* (namedWindowDeclaration NEWLINE*)* satisfyingClause? NEWLINE* qualifyClause? NEWLINE* orderByClause? NEWLINE* limitClause? NEWLINE*
    ;

// A FROM input is a relation name or a table function.
fromClause
    : FROM identifier (NEWLINE | callSuffix AS identifier NEWLINE)
    ;

// A JOIN may omit its block, or put one step on its header line; an omitted
// `from` binding or omitted VIA roles stay absent in the AST for inference.
joinClause
    : joinKind JOIN identifier AS identifier COLON NEWLINE NEWLINE* INDENT joinBody DEDENT
    | joinKind JOIN identifier AS identifier NEWLINE
    | joinKind JOIN identifier AS identifier COLON joinInlineStep
    ;

joinKind
    : INNER | LEFT | CROSS | RIGHT | FULL | SEMI | ANTI
    ;

joinInlineStep
    : FROM identifier NEWLINE
    | joinTraversalStep
    | joinOnClause
    ;

joinBody
    : NEWLINE* (FROM identifier NEWLINE NEWLINE*)? (joinTraversalStep NEWLINE*)* joinOnClause? NEWLINE*
    ;

joinTraversalStep
    : VIA identifier (COLON identifier ARROW identifier)? NEWLINE
    ;

joinOnClause
    : ON expression NEWLINE
    ;

setOperationBody
    : NEWLINE* setOperationKind setQuantifier? COLON NEWLINE NEWLINE* INDENT setOperand (setOperand | NEWLINE)* DEDENT NEWLINE*
    ;

setOperationKind
    : UNION | INTERSECT | EXCEPT
    ;

setQuantifier
    : ALL | DISTINCT
    ;

setOperand
    : FROM identifier NEWLINE
    ;

letClause
    : LET COLON NEWLINE NEWLINE* INDENT letBody DEDENT
    | LET COLON letLine (INDENT letBody DEDENT)?
    ;

letBody
    : NEWLINE* letLine (letLine | NEWLINE)*
    ;

letLine
    : letBinding (COMMA letBinding)* COMMA? NEWLINE
    ;

letBinding
    : fieldName ASSIGN expression
    ;

whereClause
    : WHERE expression NEWLINE (INDENT predicateBody DEDENT)?
    | WHERE COLON predicateSuite
    ;

// A predicate clause holds one condition on its header line, or one condition
// per line of an indented block; the builder joins block lines with `and`,
// each line as one operand.  A line may not start with `and` or `or`.
predicateSuite
    : NEWLINE NEWLINE* INDENT predicateBody DEDENT
    | predicateLine (INDENT predicateBody DEDENT)?
    ;

predicateBody
    : NEWLINE* predicateLine (predicateLine | NEWLINE)*
    ;

predicateLine
    : expression NEWLINE
    | (AND | OR) expression NEWLINE
    ;

groupByClause
    : GROUP BY COLON NEWLINE NEWLINE* INDENT groupByBody DEDENT
    | GROUP BY COLON groupByLine (INDENT groupByBody DEDENT)?
    ;

groupByBody
    : NEWLINE* groupByLine (groupByLine | NEWLINE)*
    ;

groupByLine
    : groupByItem (COMMA groupByItem)* COMMA? NEWLINE
    ;

groupByItem
    : dottedName
    | NUMBER
    ;

selectClause
    : SELECT DISTINCT? COLON NEWLINE NEWLINE* INDENT selectBody DEDENT
    | SELECT DISTINCT? COLON selectLine (INDENT selectBody DEDENT)?
    ;

selectBody
    : NEWLINE* selectLine (selectLine | NEWLINE)*
    ;

// A window item ends with its own window use, a name line or a block, so it
// stands alone on its line; the builder also rejects it on a header line.  The
// choice between the two forms looks no further than base's one-item choice.
selectLine
    : selectWindowItem
    | selectItem (COMMA selectItem)* COMMA? NEWLINE
    ;

// Alias assignment is local to select items, never a general expression.
selectWindowItem
    : fieldName ASSIGN windowExpression
    ;

selectItem
    : fieldName ASSIGN expression
    | expression
    ;

windowExpression
    : dottedName callSuffix nthValueDirection? nullTreatment? windowSpec
    ;

nthValueDirection
    : FROM (FIRST | LAST)
    ;

nullTreatment
    : (RESPECT | IGNORE) NULLS
    ;

// A window block holds compound clauses, so like a Python compound statement
// it never starts on its header line; that form is parsed only to be rejected.
windowSpec
    : WINDOW COLON NEWLINE NEWLINE* INDENT windowSpecBody DEDENT
    | WINDOW identifier NEWLINE
    | WINDOW identifier COLON NEWLINE NEWLINE* INDENT windowSpecBody DEDENT
    | WINDOW identifier? COLON windowInlineClause
    ;

qualifyInlineWindowSpec
    : WINDOW COLON NEWLINE NEWLINE* INDENT windowSpecBody DEDENT
    ;

namedWindowDeclaration
    : WINDOW identifier (ASSIGN identifier)? NEWLINE
    | WINDOW identifier (ASSIGN identifier)? COLON NEWLINE NEWLINE* INDENT windowSpecBody DEDENT
    | WINDOW identifier (ASSIGN identifier)? COLON windowInlineClause
    ;

windowInlineClause
    : partitionByClause
    | orderByClause
    | windowFrameClause
    ;

windowSpecBody
    : NEWLINE* partitionByClause NEWLINE* orderByClause? NEWLINE* windowFrameClause? NEWLINE*
    | NEWLINE* orderByClause NEWLINE* windowFrameClause? NEWLINE*
    | NEWLINE* windowFrameClause NEWLINE*
    ;

partitionByClause
    : PARTITION BY COLON NEWLINE NEWLINE* INDENT windowPartitionBody DEDENT
    | PARTITION BY COLON windowPartitionLine (INDENT windowPartitionBody DEDENT)?
    ;

windowPartitionBody
    : NEWLINE* windowPartitionLine (windowPartitionLine | NEWLINE)*
    ;

windowPartitionLine
    : windowPartitionItem (COMMA windowPartitionItem)* COMMA? NEWLINE
    ;

windowPartitionItem
    : expression
    ;

windowFrameClause
    : (ROWS | RANGE | GROUPS) (BETWEEN frameBound AND frameBound | frameBound)
      (EXCLUDE (NO OTHERS | CURRENT ROW | GROUP | TIES))? NEWLINE
    ;

frameBound
    : UNBOUNDED (PRECEDING | FOLLOWING)
    | CURRENT ROW
    | expression (PRECEDING | FOLLOWING)
    ;

satisfyingClause
    : SATISFYING COLON predicateSuite
    ;

qualifyClause
    : QUALIFY COLON NEWLINE NEWLINE* INDENT qualifyExpression NEWLINE NEWLINE* DEDENT
    ;

qualifyExpression
    : qualifyConditionalExpression
    ;

qualifyConditionalExpression
    : qualifyOrExpression (IF qualifyOrExpression ELSE qualifyConditionalExpression)?
    ;

qualifyOrExpression
    : qualifyAndExpression (OR qualifyAndExpression)*
    ;

qualifyAndExpression
    : qualifyNotExpression (AND qualifyNotExpression)*
    ;

qualifyNotExpression
    : NOT qualifyNotExpression
    | qualifyComparisonExpression
    ;

qualifyComparisonExpression
    : qualifyAdditiveExpression (
        comparisonOperator qualifyAdditiveExpression
        | BETWEEN qualifyAdditiveExpression AND qualifyAdditiveExpression
        | IS NOT? NULL
        | NOT? IN (LPAREN (qualifyExpression (COMMA qualifyExpression)* COMMA?)? RPAREN | identifier)
    )?
    ;

qualifyAdditiveExpression
    : qualifyMultiplicativeExpression ((PLUS | MINUS) qualifyMultiplicativeExpression)*
    ;

qualifyMultiplicativeExpression
    : qualifyUnaryExpression ((STAR | SLASH | PERCENT) qualifyUnaryExpression)*
    ;

qualifyUnaryExpression
    : (PLUS | MINUS) qualifyUnaryExpression
    | qualifyPrimaryExpression
    ;

qualifyPrimaryExpression
    : qualifyWindowExpression
    | literal
    | CAST LPAREN qualifyExpression AS typeExpression RPAREN
    | dottedName qualifyCallSuffix?
    | LPAREN qualifyExpression RPAREN
    | EXISTS identifier
    | SCALAR identifier DOT identifier
    ;

qualifyWindowExpression
    : dottedName callSuffix nthValueDirection? nullTreatment? qualifyInlineWindowSpec
    ;

qualifyCallSuffix
    : LPAREN (qualifyExpression (COMMA qualifyExpression)* COMMA?)? RPAREN
    ;

orderByClause
    : ORDER BY COLON NEWLINE NEWLINE* INDENT orderByBody DEDENT
    | ORDER BY COLON orderByLine (INDENT orderByBody DEDENT)?
    ;

orderByBody
    : NEWLINE* orderByLine (orderByLine | NEWLINE)*
    ;

orderByLine
    : orderItem (COMMA orderItem)* COMMA? NEWLINE
    ;

orderItem
    : expression (ASC | DESC)?
    ;

// Semantic analysis restricts the captured operand to a bounded static integer.
limitClause
    : LIMIT expression NEWLINE
    ;

// Conditional expressions are lowest precedence and right associative.  Precedence
// then rises through or, and, not, comparisons, arithmetic, unary, and primary.
expression
    : conditionalExpression
    ;

conditionalExpression
    : orExpression (IF orExpression ELSE conditionalExpression)?
    ;

orExpression
    : andExpression (OR andExpression)*
    ;

andExpression
    : notExpression (AND notExpression)*
    ;

notExpression
    : NOT notExpression
    | comparisonExpression
    ;

comparisonExpression
    : additiveExpression (
        comparisonOperator additiveExpression
        | BETWEEN additiveExpression AND additiveExpression
        | IS NOT? NULL
        | NOT? IN (LPAREN (expression (COMMA expression)* COMMA?)? RPAREN | identifier)
    )?
    ;

comparisonOperator
    : EQ
    | NE
    | LT
    | LE
    | GT
    | GE
    | LIKE
    | NOT LIKE
    ;

additiveExpression
    : multiplicativeExpression ((PLUS | MINUS) multiplicativeExpression)*
    ;

multiplicativeExpression
    : unaryExpression ((STAR | SLASH | PERCENT) unaryExpression)*
    ;

unaryExpression
    : (PLUS | MINUS) unaryExpression
    | primaryExpression
    ;

primaryExpression
    : literal
    | CAST LPAREN expression AS typeExpression RPAREN
    | dottedName callSuffix?
    | LPAREN expression RPAREN
    | EXISTS identifier
    | SCALAR identifier DOT identifier
    ;

dottedName
    : namePart (DOT namePart)*
    ;

// A name read in an expression, or a declared field, output, let binding or
// parameter name, may also be a soft keyword: a declaration or clause word
// that cannot start or continue an expression where a name is read.  Operator,
// literal and modifier words (`and`, `or`, `not`, `null`, `true`, `false`,
// `between`, `like`, `nullable`) and `window` stay reserved.
namePart
    : identifier
    | softKeyword
    ;

fieldName
    : namePart
    ;

softKeyword
    : PIETTO | MODE | DIALECT | ENCODING | LOOSE | CHECKED | STRICT
    | TYPE | ENUM | CONSTRAINT | DERIVE | SHAPE | CHECK | UNIQUE | ON | INDEX
    | WHEN | SOURCE | TABLE | FROM | WHERE | SELECT | QUERY | LIMIT | ENSURE
    | IS
    ;

// New language keywords remain valid in identifier positions for compatibility.
identifier
    : IDENTIFIER
    | IMPORT
    | EXPORT
    | AS
    | ORDER
    | BY
    | ASC
    | DESC
    | PARTITION
    | ROWS
    | RANGE
    | GROUPS
    | CURRENT
    | ROW
    | UNBOUNDED
    | PRECEDING
    | FOLLOWING
    | EXCLUDE
    | NO
    | OTHERS
    | TIES
    | FIRST
    | LAST
    | RESPECT
    | IGNORE
    | NULLS
    | GROUP
    | LET
    | SATISFYING
    | QUALIFY
    | RELATIONSHIP
    | ENDPOINT
    | INNER
    | LEFT
    | JOIN
    | VIA
    | CROSS | RIGHT | FULL | SEMI | ANTI
    | UNION | INTERSECT | EXCEPT | ALL | DISTINCT
    | IF | ELSE | IN | CAST
    | VALUES | EXISTS | CAPTURE | SCALAR
    | DEF | RETURN
    ;

callSuffix
    : LPAREN (expression (COMMA expression)* COMMA?)? RPAREN
    ;

literal
    : NUMBER
    | STRING
    | TRUE
    | FALSE
    | NULL
    ;

PIETTO: 'pietto';
MODE: 'mode';
DIALECT: 'dialect';
ENCODING: 'encoding';
LOOSE: 'loose';
CHECKED: 'checked';
STRICT: 'strict';
TYPE: 'type';
ENUM: 'enum';
CONSTRAINT: 'constraint';
DERIVE: 'derive';
SHAPE: 'shape';
CHECK: 'check';
UNIQUE: 'unique';
ON: 'on';
INDEX: 'index';
WHEN: 'when';
SOURCE: 'source';
TABLE: 'table';
FROM: 'from';
LET: 'let';
WHERE: 'where';
GROUP: 'group';
SELECT: 'select';
QUERY: 'query';
ORDER: 'order';
BY: 'by';
ASC: 'asc';
DESC: 'desc';
LIMIT: 'limit';
SATISFYING: 'satisfying';
QUALIFY: 'qualify';
RELATIONSHIP: 'relationship';
ENDPOINT: 'endpoint';
IMPORT: 'import';
EXPORT: 'export';
AS: 'as';
INNER: 'inner';
LEFT: 'left';
CROSS: 'cross';
RIGHT: 'right';
FULL: 'full';
SEMI: 'semi';
ANTI: 'anti';
UNION: 'union';
INTERSECT: 'intersect';
EXCEPT: 'except';
ALL: 'all';
DISTINCT: 'distinct';
JOIN: 'join';
VIA: 'via';
WINDOW: 'window';
PARTITION: 'partition';
ROWS: 'rows';
RANGE: 'range';
GROUPS: 'groups';
CURRENT: 'current';
ROW: 'row';
UNBOUNDED: 'unbounded';
PRECEDING: 'preceding';
FOLLOWING: 'following';
EXCLUDE: 'exclude';
NO: 'no';
OTHERS: 'others';
TIES: 'ties';
FIRST: 'first';
LAST: 'last';
RESPECT: 'respect';
IGNORE: 'ignore';
NULLS: 'nulls';
ENSURE: 'ensure';
NULLABLE: 'nullable';
AND: 'and';
OR: 'or';
IS: 'is';
NOT: 'not';
NULL: 'null';
BETWEEN: 'between';
LIKE: 'like';
IF: 'if';
ELSE: 'else';
IN: 'in';
CAST: 'cast';
VALUES: 'values';
EXISTS: 'exists';
CAPTURE: 'capture';
SCALAR: 'scalar';
DEF: 'def';
RETURN: 'return';
TRUE: 'true';
FALSE: 'false';

EQ: '==';
NE: '!=';
LE: '<=';
GE: '>=';
LT: '<';
GT: '>';
ASSIGN: '=';
ARROW: '->';
PLUS: '+';
MINUS: '-';
STAR: '*';
SLASH: '/';
PERCENT: '%';
AT: '@';
LPAREN: '(';
RPAREN: ')';
COMMA: ',';
DOT: '.';
COLON: ':';
LBRACE: '{';
RBRACE: '}';

NUMBER
    : DIGIT+ ('.' DIGIT+)?
    ;

STRING
    : '"' (ESCAPE_SEQUENCE | ~["\\\r\n])* '"'
    | '\'' (ESCAPE_SEQUENCE | ~['\\\r\n])* '\''
    ;

// A quote whose string reaches the end of its line; never a valid token, it
// lets the parser API report the literal itself instead of a lone quote.
UNTERMINATED_STRING
    : '"' (ESCAPE_SEQUENCE | ~["\\\r\n])*
    | '\'' (ESCAPE_SEQUENCE | ~['\\\r\n])*
    ;

IDENTIFIER
    : [a-zA-Z_] [a-zA-Z_0-9]*
    ;

NEWLINE
    : ('\r'? '\n' | '\r') [ \t]*
    ;

COMMENT
    : '#' ~[\r\n]* -> skip
    ;

WS
    : [ \t]+ -> skip
    ;

UNKNOWN
    : .
    ;

fragment DIGIT
    : [0-9]
    ;

fragment ESCAPE_SEQUENCE
    : '\\' .
    ;
