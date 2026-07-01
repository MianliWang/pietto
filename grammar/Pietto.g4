grammar Pietto;

tokens {
    INDENT,
    DEDENT
}

script
    : NEWLINE* header? NEWLINE* ((definition | relationshipDefinition) NEWLINE*)* EOF
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
    ;

// Relationship declarations are parse-only metadata outside semantic definitions.
relationshipDefinition
    : RELATIONSHIP identifier COLON NEWLINE NEWLINE* INDENT relationshipBody DEDENT
    ;

relationshipBody
    : NEWLINE* relationshipEndpoint NEWLINE* relationshipEndpoint NEWLINE*
    ;

relationshipEndpoint
    : ENDPOINT identifier COLON identifier NEWLINE
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

enumDefinition
    : ENUM identifier COLON NEWLINE NEWLINE* INDENT enumBody DEDENT
    ;

enumBody
    : (enumItem | NEWLINE)+
    ;

enumItem
    : identifier NEWLINE
    ;

// Phase 1 parses any return TypeExpr; semantic analysis later requires Bool.
constraintDefinition
    : CONSTRAINT identifier LPAREN parameterList? RPAREN ARROW typeExpression COLON NEWLINE NEWLINE* INDENT constraintBody DEDENT
    ;

parameterList
    : parameter (COMMA parameter)* COMMA?
    ;

parameter
    : identifier COLON typeExpression
    ;

constraintBody
    : NEWLINE* expression NEWLINE NEWLINE*
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
    : identifier COLON typeExpression fieldDeriveClause? fieldModifier* NEWLINE
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

// Shape checks are named, single-expression blocks parsed only in Phase 1.
checkDefinition
    : CHECK identifier COLON NEWLINE NEWLINE* INDENT checkBody DEDENT
    ;

checkBody
    : NEWLINE* expression NEWLINE NEWLINE*
    ;

// Shape unique clauses record names and target fields only in Phase 1.
uniqueDefinition
    : UNIQUE identifier ON identifier (COMMA identifier)* NEWLINE
    ;

// Shape index clauses are parse-only physical-design hints in Phase 1.
indexDefinition
    : INDEX identifier ON identifier (COMMA identifier)* (WHEN expression)? NEWLINE
    ;

// Source bindings retain connector expressions without validating or executing them.
sourceDefinition
    : SOURCE identifier (COLON identifier)? IS expression NEWLINE
    ;

// Relations support from, optional where/group by, ordered select, optional
// satisfying, ordered order items, and limit.
tableDefinition
    : TABLE identifier COLON NEWLINE NEWLINE* INDENT tableBody DEDENT
    ;

// Phase 1 queries reuse the minimal table body without execution semantics.
queryDefinition
    : QUERY identifier COLON NEWLINE NEWLINE* INDENT tableBody DEDENT
    ;

tableBody
    : NEWLINE* fromClause NEWLINE* letClause? NEWLINE* whereClause? NEWLINE* groupByClause? NEWLINE* selectClause NEWLINE* satisfyingClause? NEWLINE* orderByClause? NEWLINE* limitClause? NEWLINE*
    ;

fromClause
    : FROM identifier NEWLINE
    ;

letClause
    : LET COLON NEWLINE NEWLINE* INDENT letBody DEDENT
    ;

letBody
    : NEWLINE* letBinding (letBinding | NEWLINE)*
    ;

letBinding
    : identifier ASSIGN expression NEWLINE
    ;

whereClause
    : WHERE expression NEWLINE
    ;

groupByClause
    : GROUP BY COLON NEWLINE NEWLINE* INDENT groupByBody DEDENT
    ;

groupByBody
    : NEWLINE* groupByItem (groupByItem | NEWLINE)*
    ;

groupByItem
    : dottedName NEWLINE
    ;

selectClause
    : SELECT COLON NEWLINE NEWLINE* INDENT selectBody DEDENT
    ;

selectBody
    : NEWLINE* selectItem (selectItem | NEWLINE)*
    ;

// Alias assignment is local to select items, never a general expression.
selectItem
    : identifier ASSIGN expression NEWLINE
    | expression NEWLINE
    ;

satisfyingClause
    : SATISFYING COLON NEWLINE NEWLINE* INDENT expression NEWLINE NEWLINE* DEDENT
    ;

orderByClause
    : ORDER BY COLON NEWLINE NEWLINE* INDENT orderByBody DEDENT
    ;

orderByBody
    : NEWLINE* orderItem (orderItem | NEWLINE)*
    ;

orderItem
    : expression (ASC | DESC)? NEWLINE
    ;

// Semantic analysis restricts the captured operand to a bounded static integer.
limitClause
    : LIMIT expression NEWLINE
    ;

// First-slice expressions intentionally omit CASE and general assignment syntax.
// Precedence rises from or through and, comparisons, arithmetic, unary, primary.
expression
    : orExpression
    ;

orExpression
    : andExpression (OR andExpression)*
    ;

andExpression
    : comparisonExpression (AND comparisonExpression)*
    ;

comparisonExpression
    : additiveExpression (
        comparisonOperator additiveExpression
        | BETWEEN additiveExpression AND additiveExpression
        | IS NOT? NULL
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
    | dottedName callSuffix?
    | LPAREN expression RPAREN
    ;

dottedName
    : namePart (DOT namePart)*
    ;

namePart
    : identifier
    | CHECK
    | UNIQUE
    | ON
    | INDEX
    | WHEN
    | SOURCE
    | IS
    | TABLE
    | FROM
    | LET
    | WHERE
    | GROUP
    | SELECT
    | QUERY
    | LIMIT
    | SATISFYING
    | RELATIONSHIP
    | ENDPOINT
    ;

// New language keywords remain valid in identifier positions for compatibility.
identifier
    : IDENTIFIER
    | ORDER
    | BY
    | ASC
    | DESC
    | GROUP
    | LET
    | SATISFYING
    | RELATIONSHIP
    | ENDPOINT
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
RELATIONSHIP: 'relationship';
ENDPOINT: 'endpoint';
ENSURE: 'ensure';
NULLABLE: 'nullable';
AND: 'and';
OR: 'or';
IS: 'is';
NOT: 'not';
NULL: 'null';
BETWEEN: 'between';
LIKE: 'like';
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
