grammar Pietto;

tokens {
    INDENT,
    DEDENT
}

script
    : NEWLINE* header? NEWLINE* (definition NEWLINE*)* EOF
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
    : DIALECT IDENTIFIER NEWLINE
    ;

encodingDecl
    : ENCODING IDENTIFIER NEWLINE
    ;

definition
    : typeDefinition
    | enumDefinition
    | constraintDefinition
    | deriveDefinition
    | shapeDefinition
    ;

// Pietto blocks use ':' plus NEWLINE/INDENT/DEDENT, never brace delimiters.
typeDefinition
    : TYPE IDENTIFIER ASSIGN typeExpression NEWLINE
    | TYPE IDENTIFIER ASSIGN typeExpression ENSURE expression NEWLINE
    | TYPE IDENTIFIER ASSIGN typeExpression COLON NEWLINE NEWLINE* INDENT typeBody DEDENT
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
    : IDENTIFIER typeArguments?
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
    : IDENTIFIER
    | ENCODING
    ;

enumDefinition
    : ENUM IDENTIFIER COLON NEWLINE NEWLINE* INDENT enumBody DEDENT
    ;

enumBody
    : (enumItem | NEWLINE)+
    ;

enumItem
    : IDENTIFIER NEWLINE
    ;

// Phase 1 parses any return TypeExpr; semantic analysis later requires Bool.
constraintDefinition
    : CONSTRAINT IDENTIFIER LPAREN parameterList? RPAREN ARROW typeExpression COLON NEWLINE NEWLINE* INDENT constraintBody DEDENT
    ;

parameterList
    : parameter (COMMA parameter)* COMMA?
    ;

parameter
    : IDENTIFIER COLON typeExpression
    ;

constraintBody
    : NEWLINE* expression NEWLINE NEWLINE*
    ;

// Derive signatures and bodies are parsed only; Phase 2 checks their semantics.
deriveDefinition
    : DERIVE IDENTIFIER LPAREN parameterList? RPAREN ARROW typeExpression COLON NEWLINE NEWLINE* INDENT deriveBody DEDENT
    ;

deriveBody
    : NEWLINE* expression NEWLINE NEWLINE*
    ;

// Phase 1 shapes preserve ordered items; their semantics come later.
shapeDefinition
    : SHAPE IDENTIFIER COLON NEWLINE NEWLINE* INDENT shapeBody DEDENT
    ;

shapeBody
    : NEWLINE* shapeItem (shapeItem | NEWLINE)*
    ;

shapeItem
    : fieldDefinition
    | checkDefinition
    | uniqueDefinition
    ;

fieldDefinition
    : IDENTIFIER COLON typeExpression fieldDeriveClause? fieldModifier* NEWLINE
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
    : AT IDENTIFIER
    ;

fieldEnsureClause
    : ENSURE expression
    ;

// Shape checks are named, single-expression blocks parsed only in Phase 1.
checkDefinition
    : CHECK IDENTIFIER COLON NEWLINE NEWLINE* INDENT checkBody DEDENT
    ;

checkBody
    : NEWLINE* expression NEWLINE NEWLINE*
    ;

// Shape unique clauses record names and target fields only in Phase 1.
uniqueDefinition
    : UNIQUE IDENTIFIER ON IDENTIFIER (COMMA IDENTIFIER)* NEWLINE
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
    : IDENTIFIER
    | CHECK
    | UNIQUE
    | ON
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
