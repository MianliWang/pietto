# Generated from grammar/Pietto.g4 by ANTLR 4.13.2
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO

def serializedATN():
    return [
        4,1,50,382,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,2,31,7,31,2,32,7,32,1,0,
        5,0,68,8,0,10,0,12,0,71,9,0,1,0,3,0,74,8,0,1,0,5,0,77,8,0,10,0,12,
        0,80,9,0,1,0,1,0,5,0,84,8,0,10,0,12,0,87,9,0,5,0,89,8,0,10,0,12,
        0,92,9,0,1,0,1,0,1,1,1,1,3,1,98,8,1,1,1,3,1,101,8,1,1,1,3,1,104,
        8,1,1,1,1,1,3,1,108,8,1,1,1,3,1,111,8,1,1,1,1,1,3,1,115,8,1,1,1,
        3,1,118,8,1,1,2,1,2,1,2,1,2,1,3,1,3,1,3,1,3,1,4,1,4,1,4,1,4,1,5,
        1,5,1,5,1,5,1,6,1,6,1,6,3,6,139,8,6,1,7,1,7,1,7,1,7,1,7,1,7,1,7,
        1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,5,7,162,
        8,7,10,7,12,7,165,9,7,1,7,1,7,1,7,1,7,3,7,171,8,7,1,8,1,8,4,8,175,
        8,8,11,8,12,8,176,1,9,1,9,1,9,1,9,1,10,1,10,3,10,185,8,10,1,10,3,
        10,188,8,10,1,11,1,11,1,11,1,11,5,11,194,8,11,10,11,12,11,197,9,
        11,1,11,3,11,200,8,11,3,11,202,8,11,1,11,1,11,1,12,1,12,1,12,1,12,
        1,12,3,12,211,8,12,1,13,1,13,1,14,1,14,1,14,1,14,1,14,5,14,220,8,
        14,10,14,12,14,223,9,14,1,14,1,14,1,14,1,14,1,15,1,15,4,15,231,8,
        15,11,15,12,15,232,1,16,1,16,1,16,1,17,1,17,1,17,1,17,3,17,242,8,
        17,1,17,1,17,1,17,1,17,1,17,1,17,5,17,250,8,17,10,17,12,17,253,9,
        17,1,17,1,17,1,17,1,17,1,18,1,18,1,18,5,18,262,8,18,10,18,12,18,
        265,9,18,1,18,3,18,268,8,18,1,19,1,19,1,19,1,19,1,20,5,20,275,8,
        20,10,20,12,20,278,9,20,1,20,1,20,1,20,5,20,283,8,20,10,20,12,20,
        286,9,20,1,21,1,21,1,22,1,22,1,22,5,22,293,8,22,10,22,12,22,296,
        9,22,1,23,1,23,1,23,5,23,301,8,23,10,23,12,23,304,9,23,1,24,1,24,
        1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,3,24,317,8,24,1,24,
        3,24,320,8,24,1,25,1,25,1,26,1,26,1,26,5,26,327,8,26,10,26,12,26,
        330,9,26,1,27,1,27,1,27,5,27,335,8,27,10,27,12,27,338,9,27,1,28,
        1,28,1,28,3,28,343,8,28,1,29,1,29,1,29,3,29,348,8,29,1,29,1,29,1,
        29,1,29,3,29,354,8,29,1,30,1,30,1,30,5,30,359,8,30,10,30,12,30,362,
        9,30,1,31,1,31,1,31,1,31,5,31,368,8,31,10,31,12,31,371,9,31,1,31,
        3,31,374,8,31,3,31,376,8,31,1,31,1,31,1,32,1,32,1,32,0,0,33,0,2,
        4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48,
        50,52,54,56,58,60,62,64,0,6,1,0,5,7,2,0,4,4,44,44,2,0,18,18,21,26,
        1,0,29,30,1,0,31,33,3,0,16,16,19,20,42,43,400,0,69,1,0,0,0,2,117,
        1,0,0,0,4,119,1,0,0,0,6,123,1,0,0,0,8,127,1,0,0,0,10,131,1,0,0,0,
        12,138,1,0,0,0,14,170,1,0,0,0,16,174,1,0,0,0,18,178,1,0,0,0,20,182,
        1,0,0,0,22,189,1,0,0,0,24,210,1,0,0,0,26,212,1,0,0,0,28,214,1,0,
        0,0,30,230,1,0,0,0,32,234,1,0,0,0,34,237,1,0,0,0,36,258,1,0,0,0,
        38,269,1,0,0,0,40,276,1,0,0,0,42,287,1,0,0,0,44,289,1,0,0,0,46,297,
        1,0,0,0,48,305,1,0,0,0,50,321,1,0,0,0,52,323,1,0,0,0,54,331,1,0,
        0,0,56,342,1,0,0,0,58,353,1,0,0,0,60,355,1,0,0,0,62,363,1,0,0,0,
        64,379,1,0,0,0,66,68,5,45,0,0,67,66,1,0,0,0,68,71,1,0,0,0,69,67,
        1,0,0,0,69,70,1,0,0,0,70,73,1,0,0,0,71,69,1,0,0,0,72,74,3,2,1,0,
        73,72,1,0,0,0,73,74,1,0,0,0,74,78,1,0,0,0,75,77,5,45,0,0,76,75,1,
        0,0,0,77,80,1,0,0,0,78,76,1,0,0,0,78,79,1,0,0,0,79,90,1,0,0,0,80,
        78,1,0,0,0,81,85,3,12,6,0,82,84,5,45,0,0,83,82,1,0,0,0,84,87,1,0,
        0,0,85,83,1,0,0,0,85,86,1,0,0,0,86,89,1,0,0,0,87,85,1,0,0,0,88,81,
        1,0,0,0,89,92,1,0,0,0,90,88,1,0,0,0,90,91,1,0,0,0,91,93,1,0,0,0,
        92,90,1,0,0,0,93,94,5,0,0,1,94,1,1,0,0,0,95,97,3,4,2,0,96,98,3,6,
        3,0,97,96,1,0,0,0,97,98,1,0,0,0,98,100,1,0,0,0,99,101,3,8,4,0,100,
        99,1,0,0,0,100,101,1,0,0,0,101,103,1,0,0,0,102,104,3,10,5,0,103,
        102,1,0,0,0,103,104,1,0,0,0,104,118,1,0,0,0,105,107,3,6,3,0,106,
        108,3,8,4,0,107,106,1,0,0,0,107,108,1,0,0,0,108,110,1,0,0,0,109,
        111,3,10,5,0,110,109,1,0,0,0,110,111,1,0,0,0,111,118,1,0,0,0,112,
        114,3,8,4,0,113,115,3,10,5,0,114,113,1,0,0,0,114,115,1,0,0,0,115,
        118,1,0,0,0,116,118,3,10,5,0,117,95,1,0,0,0,117,105,1,0,0,0,117,
        112,1,0,0,0,117,116,1,0,0,0,118,3,1,0,0,0,119,120,5,1,0,0,120,121,
        5,42,0,0,121,122,5,45,0,0,122,5,1,0,0,0,123,124,5,2,0,0,124,125,
        7,0,0,0,125,126,5,45,0,0,126,7,1,0,0,0,127,128,5,3,0,0,128,129,5,
        44,0,0,129,130,5,45,0,0,130,9,1,0,0,0,131,132,5,4,0,0,132,133,5,
        44,0,0,133,134,5,45,0,0,134,11,1,0,0,0,135,139,3,14,7,0,136,139,
        3,28,14,0,137,139,3,34,17,0,138,135,1,0,0,0,138,136,1,0,0,0,138,
        137,1,0,0,0,139,13,1,0,0,0,140,141,5,8,0,0,141,142,5,44,0,0,142,
        143,5,27,0,0,143,144,3,20,10,0,144,145,5,45,0,0,145,171,1,0,0,0,
        146,147,5,8,0,0,147,148,5,44,0,0,148,149,5,27,0,0,149,150,3,20,10,
        0,150,151,5,11,0,0,151,152,3,42,21,0,152,153,5,45,0,0,153,171,1,
        0,0,0,154,155,5,8,0,0,155,156,5,44,0,0,156,157,5,27,0,0,157,158,
        3,20,10,0,158,159,5,39,0,0,159,163,5,45,0,0,160,162,5,45,0,0,161,
        160,1,0,0,0,162,165,1,0,0,0,163,161,1,0,0,0,163,164,1,0,0,0,164,
        166,1,0,0,0,165,163,1,0,0,0,166,167,5,49,0,0,167,168,3,16,8,0,168,
        169,5,50,0,0,169,171,1,0,0,0,170,140,1,0,0,0,170,146,1,0,0,0,170,
        154,1,0,0,0,171,15,1,0,0,0,172,175,3,18,9,0,173,175,5,45,0,0,174,
        172,1,0,0,0,174,173,1,0,0,0,175,176,1,0,0,0,176,174,1,0,0,0,176,
        177,1,0,0,0,177,17,1,0,0,0,178,179,5,11,0,0,179,180,3,42,21,0,180,
        181,5,45,0,0,181,19,1,0,0,0,182,184,5,44,0,0,183,185,3,22,11,0,184,
        183,1,0,0,0,184,185,1,0,0,0,185,187,1,0,0,0,186,188,5,34,0,0,187,
        186,1,0,0,0,187,188,1,0,0,0,188,21,1,0,0,0,189,201,5,35,0,0,190,
        195,3,24,12,0,191,192,5,37,0,0,192,194,3,24,12,0,193,191,1,0,0,0,
        194,197,1,0,0,0,195,193,1,0,0,0,195,196,1,0,0,0,196,199,1,0,0,0,
        197,195,1,0,0,0,198,200,5,37,0,0,199,198,1,0,0,0,199,200,1,0,0,0,
        200,202,1,0,0,0,201,190,1,0,0,0,201,202,1,0,0,0,202,203,1,0,0,0,
        203,204,5,36,0,0,204,23,1,0,0,0,205,206,3,26,13,0,206,207,5,27,0,
        0,207,208,3,42,21,0,208,211,1,0,0,0,209,211,3,42,21,0,210,205,1,
        0,0,0,210,209,1,0,0,0,211,25,1,0,0,0,212,213,7,1,0,0,213,27,1,0,
        0,0,214,215,5,9,0,0,215,216,5,44,0,0,216,217,5,39,0,0,217,221,5,
        45,0,0,218,220,5,45,0,0,219,218,1,0,0,0,220,223,1,0,0,0,221,219,
        1,0,0,0,221,222,1,0,0,0,222,224,1,0,0,0,223,221,1,0,0,0,224,225,
        5,49,0,0,225,226,3,30,15,0,226,227,5,50,0,0,227,29,1,0,0,0,228,231,
        3,32,16,0,229,231,5,45,0,0,230,228,1,0,0,0,230,229,1,0,0,0,231,232,
        1,0,0,0,232,230,1,0,0,0,232,233,1,0,0,0,233,31,1,0,0,0,234,235,5,
        44,0,0,235,236,5,45,0,0,236,33,1,0,0,0,237,238,5,10,0,0,238,239,
        5,44,0,0,239,241,5,35,0,0,240,242,3,36,18,0,241,240,1,0,0,0,241,
        242,1,0,0,0,242,243,1,0,0,0,243,244,5,36,0,0,244,245,5,28,0,0,245,
        246,3,20,10,0,246,247,5,39,0,0,247,251,5,45,0,0,248,250,5,45,0,0,
        249,248,1,0,0,0,250,253,1,0,0,0,251,249,1,0,0,0,251,252,1,0,0,0,
        252,254,1,0,0,0,253,251,1,0,0,0,254,255,5,49,0,0,255,256,3,40,20,
        0,256,257,5,50,0,0,257,35,1,0,0,0,258,263,3,38,19,0,259,260,5,37,
        0,0,260,262,3,38,19,0,261,259,1,0,0,0,262,265,1,0,0,0,263,261,1,
        0,0,0,263,264,1,0,0,0,264,267,1,0,0,0,265,263,1,0,0,0,266,268,5,
        37,0,0,267,266,1,0,0,0,267,268,1,0,0,0,268,37,1,0,0,0,269,270,5,
        44,0,0,270,271,5,39,0,0,271,272,3,20,10,0,272,39,1,0,0,0,273,275,
        5,45,0,0,274,273,1,0,0,0,275,278,1,0,0,0,276,274,1,0,0,0,276,277,
        1,0,0,0,277,279,1,0,0,0,278,276,1,0,0,0,279,280,3,42,21,0,280,284,
        5,45,0,0,281,283,5,45,0,0,282,281,1,0,0,0,283,286,1,0,0,0,284,282,
        1,0,0,0,284,285,1,0,0,0,285,41,1,0,0,0,286,284,1,0,0,0,287,288,3,
        44,22,0,288,43,1,0,0,0,289,294,3,46,23,0,290,291,5,13,0,0,291,293,
        3,46,23,0,292,290,1,0,0,0,293,296,1,0,0,0,294,292,1,0,0,0,294,295,
        1,0,0,0,295,45,1,0,0,0,296,294,1,0,0,0,297,302,3,48,24,0,298,299,
        5,12,0,0,299,301,3,48,24,0,300,298,1,0,0,0,301,304,1,0,0,0,302,300,
        1,0,0,0,302,303,1,0,0,0,303,47,1,0,0,0,304,302,1,0,0,0,305,319,3,
        52,26,0,306,307,3,50,25,0,307,308,3,52,26,0,308,320,1,0,0,0,309,
        310,5,17,0,0,310,311,3,52,26,0,311,312,5,12,0,0,312,313,3,52,26,
        0,313,320,1,0,0,0,314,316,5,14,0,0,315,317,5,15,0,0,316,315,1,0,
        0,0,316,317,1,0,0,0,317,318,1,0,0,0,318,320,5,16,0,0,319,306,1,0,
        0,0,319,309,1,0,0,0,319,314,1,0,0,0,319,320,1,0,0,0,320,49,1,0,0,
        0,321,322,7,2,0,0,322,51,1,0,0,0,323,328,3,54,27,0,324,325,7,3,0,
        0,325,327,3,54,27,0,326,324,1,0,0,0,327,330,1,0,0,0,328,326,1,0,
        0,0,328,329,1,0,0,0,329,53,1,0,0,0,330,328,1,0,0,0,331,336,3,56,
        28,0,332,333,7,4,0,0,333,335,3,56,28,0,334,332,1,0,0,0,335,338,1,
        0,0,0,336,334,1,0,0,0,336,337,1,0,0,0,337,55,1,0,0,0,338,336,1,0,
        0,0,339,340,7,3,0,0,340,343,3,56,28,0,341,343,3,58,29,0,342,339,
        1,0,0,0,342,341,1,0,0,0,343,57,1,0,0,0,344,354,3,64,32,0,345,347,
        3,60,30,0,346,348,3,62,31,0,347,346,1,0,0,0,347,348,1,0,0,0,348,
        354,1,0,0,0,349,350,5,35,0,0,350,351,3,42,21,0,351,352,5,36,0,0,
        352,354,1,0,0,0,353,344,1,0,0,0,353,345,1,0,0,0,353,349,1,0,0,0,
        354,59,1,0,0,0,355,360,5,44,0,0,356,357,5,38,0,0,357,359,5,44,0,
        0,358,356,1,0,0,0,359,362,1,0,0,0,360,358,1,0,0,0,360,361,1,0,0,
        0,361,61,1,0,0,0,362,360,1,0,0,0,363,375,5,35,0,0,364,369,3,42,21,
        0,365,366,5,37,0,0,366,368,3,42,21,0,367,365,1,0,0,0,368,371,1,0,
        0,0,369,367,1,0,0,0,369,370,1,0,0,0,370,373,1,0,0,0,371,369,1,0,
        0,0,372,374,5,37,0,0,373,372,1,0,0,0,373,374,1,0,0,0,374,376,1,0,
        0,0,375,364,1,0,0,0,375,376,1,0,0,0,376,377,1,0,0,0,377,378,5,36,
        0,0,378,63,1,0,0,0,379,380,7,5,0,0,380,65,1,0,0,0,45,69,73,78,85,
        90,97,100,103,107,110,114,117,138,163,170,174,176,184,187,195,199,
        201,210,221,230,232,241,251,263,267,276,284,294,302,316,319,328,
        336,342,347,353,360,369,373,375
    ]

class PiettoParser ( Parser ):

    grammarFileName = "Pietto.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'pietto'", "'mode'", "'dialect'", "'encoding'", 
                     "'loose'", "'checked'", "'strict'", "'type'", "'enum'", 
                     "'constraint'", "'ensure'", "'and'", "'or'", "'is'", 
                     "'not'", "'null'", "'between'", "'like'", "'true'", 
                     "'false'", "'=='", "'!='", "'<='", "'>='", "'<'", "'>'", 
                     "'='", "'->'", "'+'", "'-'", "'*'", "'/'", "'%'", "'?'", 
                     "'('", "')'", "','", "'.'", "':'", "'{'", "'}'" ]

    symbolicNames = [ "<INVALID>", "PIETTO", "MODE", "DIALECT", "ENCODING", 
                      "LOOSE", "CHECKED", "STRICT", "TYPE", "ENUM", "CONSTRAINT", 
                      "ENSURE", "AND", "OR", "IS", "NOT", "NULL", "BETWEEN", 
                      "LIKE", "TRUE", "FALSE", "EQ", "NE", "LE", "GE", "LT", 
                      "GT", "ASSIGN", "ARROW", "PLUS", "MINUS", "STAR", 
                      "SLASH", "PERCENT", "QUESTION", "LPAREN", "RPAREN", 
                      "COMMA", "DOT", "COLON", "LBRACE", "RBRACE", "NUMBER", 
                      "STRING", "IDENTIFIER", "NEWLINE", "COMMENT", "WS", 
                      "UNKNOWN", "INDENT", "DEDENT" ]

    RULE_script = 0
    RULE_header = 1
    RULE_versionDecl = 2
    RULE_modeDecl = 3
    RULE_dialectDecl = 4
    RULE_encodingDecl = 5
    RULE_definition = 6
    RULE_typeDefinition = 7
    RULE_typeBody = 8
    RULE_ensureClause = 9
    RULE_typeExpression = 10
    RULE_typeArguments = 11
    RULE_typeArgument = 12
    RULE_typeArgumentName = 13
    RULE_enumDefinition = 14
    RULE_enumBody = 15
    RULE_enumItem = 16
    RULE_constraintDefinition = 17
    RULE_parameterList = 18
    RULE_parameter = 19
    RULE_constraintBody = 20
    RULE_expression = 21
    RULE_orExpression = 22
    RULE_andExpression = 23
    RULE_comparisonExpression = 24
    RULE_comparisonOperator = 25
    RULE_additiveExpression = 26
    RULE_multiplicativeExpression = 27
    RULE_unaryExpression = 28
    RULE_primaryExpression = 29
    RULE_dottedName = 30
    RULE_callSuffix = 31
    RULE_literal = 32

    ruleNames =  [ "script", "header", "versionDecl", "modeDecl", "dialectDecl", 
                   "encodingDecl", "definition", "typeDefinition", "typeBody", 
                   "ensureClause", "typeExpression", "typeArguments", "typeArgument", 
                   "typeArgumentName", "enumDefinition", "enumBody", "enumItem", 
                   "constraintDefinition", "parameterList", "parameter", 
                   "constraintBody", "expression", "orExpression", "andExpression", 
                   "comparisonExpression", "comparisonOperator", "additiveExpression", 
                   "multiplicativeExpression", "unaryExpression", "primaryExpression", 
                   "dottedName", "callSuffix", "literal" ]

    EOF = Token.EOF
    PIETTO=1
    MODE=2
    DIALECT=3
    ENCODING=4
    LOOSE=5
    CHECKED=6
    STRICT=7
    TYPE=8
    ENUM=9
    CONSTRAINT=10
    ENSURE=11
    AND=12
    OR=13
    IS=14
    NOT=15
    NULL=16
    BETWEEN=17
    LIKE=18
    TRUE=19
    FALSE=20
    EQ=21
    NE=22
    LE=23
    GE=24
    LT=25
    GT=26
    ASSIGN=27
    ARROW=28
    PLUS=29
    MINUS=30
    STAR=31
    SLASH=32
    PERCENT=33
    QUESTION=34
    LPAREN=35
    RPAREN=36
    COMMA=37
    DOT=38
    COLON=39
    LBRACE=40
    RBRACE=41
    NUMBER=42
    STRING=43
    IDENTIFIER=44
    NEWLINE=45
    COMMENT=46
    WS=47
    UNKNOWN=48
    INDENT=49
    DEDENT=50

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.2")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class ScriptContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def EOF(self):
            return self.getToken(PiettoParser.EOF, 0)

        def NEWLINE(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.NEWLINE)
            else:
                return self.getToken(PiettoParser.NEWLINE, i)

        def header(self):
            return self.getTypedRuleContext(PiettoParser.HeaderContext,0)


        def definition(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PiettoParser.DefinitionContext)
            else:
                return self.getTypedRuleContext(PiettoParser.DefinitionContext,i)


        def getRuleIndex(self):
            return PiettoParser.RULE_script

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitScript" ):
                return visitor.visitScript(self)
            else:
                return visitor.visitChildren(self)




    def script(self):

        localctx = PiettoParser.ScriptContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_script)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 69
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,0,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 66
                    self.match(PiettoParser.NEWLINE) 
                self.state = 71
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,0,self._ctx)

            self.state = 73
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 30) != 0):
                self.state = 72
                self.header()


            self.state = 78
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==45:
                self.state = 75
                self.match(PiettoParser.NEWLINE)
                self.state = 80
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 90
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 1792) != 0):
                self.state = 81
                self.definition()
                self.state = 85
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==45:
                    self.state = 82
                    self.match(PiettoParser.NEWLINE)
                    self.state = 87
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 92
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 93
            self.match(PiettoParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class HeaderContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def versionDecl(self):
            return self.getTypedRuleContext(PiettoParser.VersionDeclContext,0)


        def modeDecl(self):
            return self.getTypedRuleContext(PiettoParser.ModeDeclContext,0)


        def dialectDecl(self):
            return self.getTypedRuleContext(PiettoParser.DialectDeclContext,0)


        def encodingDecl(self):
            return self.getTypedRuleContext(PiettoParser.EncodingDeclContext,0)


        def getRuleIndex(self):
            return PiettoParser.RULE_header

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitHeader" ):
                return visitor.visitHeader(self)
            else:
                return visitor.visitChildren(self)




    def header(self):

        localctx = PiettoParser.HeaderContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_header)
        self._la = 0 # Token type
        try:
            self.state = 117
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [1]:
                self.enterOuterAlt(localctx, 1)
                self.state = 95
                self.versionDecl()
                self.state = 97
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==2:
                    self.state = 96
                    self.modeDecl()


                self.state = 100
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==3:
                    self.state = 99
                    self.dialectDecl()


                self.state = 103
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4:
                    self.state = 102
                    self.encodingDecl()


                pass
            elif token in [2]:
                self.enterOuterAlt(localctx, 2)
                self.state = 105
                self.modeDecl()
                self.state = 107
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==3:
                    self.state = 106
                    self.dialectDecl()


                self.state = 110
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4:
                    self.state = 109
                    self.encodingDecl()


                pass
            elif token in [3]:
                self.enterOuterAlt(localctx, 3)
                self.state = 112
                self.dialectDecl()
                self.state = 114
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4:
                    self.state = 113
                    self.encodingDecl()


                pass
            elif token in [4]:
                self.enterOuterAlt(localctx, 4)
                self.state = 116
                self.encodingDecl()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class VersionDeclContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def PIETTO(self):
            return self.getToken(PiettoParser.PIETTO, 0)

        def NUMBER(self):
            return self.getToken(PiettoParser.NUMBER, 0)

        def NEWLINE(self):
            return self.getToken(PiettoParser.NEWLINE, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_versionDecl

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVersionDecl" ):
                return visitor.visitVersionDecl(self)
            else:
                return visitor.visitChildren(self)




    def versionDecl(self):

        localctx = PiettoParser.VersionDeclContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_versionDecl)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 119
            self.match(PiettoParser.PIETTO)
            self.state = 120
            self.match(PiettoParser.NUMBER)
            self.state = 121
            self.match(PiettoParser.NEWLINE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ModeDeclContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def MODE(self):
            return self.getToken(PiettoParser.MODE, 0)

        def NEWLINE(self):
            return self.getToken(PiettoParser.NEWLINE, 0)

        def LOOSE(self):
            return self.getToken(PiettoParser.LOOSE, 0)

        def CHECKED(self):
            return self.getToken(PiettoParser.CHECKED, 0)

        def STRICT(self):
            return self.getToken(PiettoParser.STRICT, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_modeDecl

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitModeDecl" ):
                return visitor.visitModeDecl(self)
            else:
                return visitor.visitChildren(self)




    def modeDecl(self):

        localctx = PiettoParser.ModeDeclContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_modeDecl)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 123
            self.match(PiettoParser.MODE)
            self.state = 124
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 224) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 125
            self.match(PiettoParser.NEWLINE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DialectDeclContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def DIALECT(self):
            return self.getToken(PiettoParser.DIALECT, 0)

        def IDENTIFIER(self):
            return self.getToken(PiettoParser.IDENTIFIER, 0)

        def NEWLINE(self):
            return self.getToken(PiettoParser.NEWLINE, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_dialectDecl

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDialectDecl" ):
                return visitor.visitDialectDecl(self)
            else:
                return visitor.visitChildren(self)




    def dialectDecl(self):

        localctx = PiettoParser.DialectDeclContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_dialectDecl)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 127
            self.match(PiettoParser.DIALECT)
            self.state = 128
            self.match(PiettoParser.IDENTIFIER)
            self.state = 129
            self.match(PiettoParser.NEWLINE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class EncodingDeclContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ENCODING(self):
            return self.getToken(PiettoParser.ENCODING, 0)

        def IDENTIFIER(self):
            return self.getToken(PiettoParser.IDENTIFIER, 0)

        def NEWLINE(self):
            return self.getToken(PiettoParser.NEWLINE, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_encodingDecl

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitEncodingDecl" ):
                return visitor.visitEncodingDecl(self)
            else:
                return visitor.visitChildren(self)




    def encodingDecl(self):

        localctx = PiettoParser.EncodingDeclContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_encodingDecl)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 131
            self.match(PiettoParser.ENCODING)
            self.state = 132
            self.match(PiettoParser.IDENTIFIER)
            self.state = 133
            self.match(PiettoParser.NEWLINE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DefinitionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def typeDefinition(self):
            return self.getTypedRuleContext(PiettoParser.TypeDefinitionContext,0)


        def enumDefinition(self):
            return self.getTypedRuleContext(PiettoParser.EnumDefinitionContext,0)


        def constraintDefinition(self):
            return self.getTypedRuleContext(PiettoParser.ConstraintDefinitionContext,0)


        def getRuleIndex(self):
            return PiettoParser.RULE_definition

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDefinition" ):
                return visitor.visitDefinition(self)
            else:
                return visitor.visitChildren(self)




    def definition(self):

        localctx = PiettoParser.DefinitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_definition)
        try:
            self.state = 138
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [8]:
                self.enterOuterAlt(localctx, 1)
                self.state = 135
                self.typeDefinition()
                pass
            elif token in [9]:
                self.enterOuterAlt(localctx, 2)
                self.state = 136
                self.enumDefinition()
                pass
            elif token in [10]:
                self.enterOuterAlt(localctx, 3)
                self.state = 137
                self.constraintDefinition()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TypeDefinitionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def TYPE(self):
            return self.getToken(PiettoParser.TYPE, 0)

        def IDENTIFIER(self):
            return self.getToken(PiettoParser.IDENTIFIER, 0)

        def ASSIGN(self):
            return self.getToken(PiettoParser.ASSIGN, 0)

        def typeExpression(self):
            return self.getTypedRuleContext(PiettoParser.TypeExpressionContext,0)


        def NEWLINE(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.NEWLINE)
            else:
                return self.getToken(PiettoParser.NEWLINE, i)

        def ENSURE(self):
            return self.getToken(PiettoParser.ENSURE, 0)

        def expression(self):
            return self.getTypedRuleContext(PiettoParser.ExpressionContext,0)


        def COLON(self):
            return self.getToken(PiettoParser.COLON, 0)

        def INDENT(self):
            return self.getToken(PiettoParser.INDENT, 0)

        def typeBody(self):
            return self.getTypedRuleContext(PiettoParser.TypeBodyContext,0)


        def DEDENT(self):
            return self.getToken(PiettoParser.DEDENT, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_typeDefinition

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTypeDefinition" ):
                return visitor.visitTypeDefinition(self)
            else:
                return visitor.visitChildren(self)




    def typeDefinition(self):

        localctx = PiettoParser.TypeDefinitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_typeDefinition)
        self._la = 0 # Token type
        try:
            self.state = 170
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,14,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 140
                self.match(PiettoParser.TYPE)
                self.state = 141
                self.match(PiettoParser.IDENTIFIER)
                self.state = 142
                self.match(PiettoParser.ASSIGN)
                self.state = 143
                self.typeExpression()
                self.state = 144
                self.match(PiettoParser.NEWLINE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 146
                self.match(PiettoParser.TYPE)
                self.state = 147
                self.match(PiettoParser.IDENTIFIER)
                self.state = 148
                self.match(PiettoParser.ASSIGN)
                self.state = 149
                self.typeExpression()
                self.state = 150
                self.match(PiettoParser.ENSURE)
                self.state = 151
                self.expression()
                self.state = 152
                self.match(PiettoParser.NEWLINE)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 154
                self.match(PiettoParser.TYPE)
                self.state = 155
                self.match(PiettoParser.IDENTIFIER)
                self.state = 156
                self.match(PiettoParser.ASSIGN)
                self.state = 157
                self.typeExpression()
                self.state = 158
                self.match(PiettoParser.COLON)
                self.state = 159
                self.match(PiettoParser.NEWLINE)
                self.state = 163
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==45:
                    self.state = 160
                    self.match(PiettoParser.NEWLINE)
                    self.state = 165
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 166
                self.match(PiettoParser.INDENT)
                self.state = 167
                self.typeBody()
                self.state = 168
                self.match(PiettoParser.DEDENT)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TypeBodyContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ensureClause(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PiettoParser.EnsureClauseContext)
            else:
                return self.getTypedRuleContext(PiettoParser.EnsureClauseContext,i)


        def NEWLINE(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.NEWLINE)
            else:
                return self.getToken(PiettoParser.NEWLINE, i)

        def getRuleIndex(self):
            return PiettoParser.RULE_typeBody

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTypeBody" ):
                return visitor.visitTypeBody(self)
            else:
                return visitor.visitChildren(self)




    def typeBody(self):

        localctx = PiettoParser.TypeBodyContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_typeBody)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 174 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 174
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [11]:
                    self.state = 172
                    self.ensureClause()
                    pass
                elif token in [45]:
                    self.state = 173
                    self.match(PiettoParser.NEWLINE)
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 176 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==11 or _la==45):
                    break

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class EnsureClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ENSURE(self):
            return self.getToken(PiettoParser.ENSURE, 0)

        def expression(self):
            return self.getTypedRuleContext(PiettoParser.ExpressionContext,0)


        def NEWLINE(self):
            return self.getToken(PiettoParser.NEWLINE, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_ensureClause

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitEnsureClause" ):
                return visitor.visitEnsureClause(self)
            else:
                return visitor.visitChildren(self)




    def ensureClause(self):

        localctx = PiettoParser.EnsureClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 18, self.RULE_ensureClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 178
            self.match(PiettoParser.ENSURE)
            self.state = 179
            self.expression()
            self.state = 180
            self.match(PiettoParser.NEWLINE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TypeExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENTIFIER(self):
            return self.getToken(PiettoParser.IDENTIFIER, 0)

        def typeArguments(self):
            return self.getTypedRuleContext(PiettoParser.TypeArgumentsContext,0)


        def QUESTION(self):
            return self.getToken(PiettoParser.QUESTION, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_typeExpression

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTypeExpression" ):
                return visitor.visitTypeExpression(self)
            else:
                return visitor.visitChildren(self)




    def typeExpression(self):

        localctx = PiettoParser.TypeExpressionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_typeExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 182
            self.match(PiettoParser.IDENTIFIER)
            self.state = 184
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==35:
                self.state = 183
                self.typeArguments()


            self.state = 187
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==34:
                self.state = 186
                self.match(PiettoParser.QUESTION)


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TypeArgumentsContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LPAREN(self):
            return self.getToken(PiettoParser.LPAREN, 0)

        def RPAREN(self):
            return self.getToken(PiettoParser.RPAREN, 0)

        def typeArgument(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PiettoParser.TypeArgumentContext)
            else:
                return self.getTypedRuleContext(PiettoParser.TypeArgumentContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.COMMA)
            else:
                return self.getToken(PiettoParser.COMMA, i)

        def getRuleIndex(self):
            return PiettoParser.RULE_typeArguments

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTypeArguments" ):
                return visitor.visitTypeArguments(self)
            else:
                return visitor.visitChildren(self)




    def typeArguments(self):

        localctx = PiettoParser.TypeArgumentsContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_typeArguments)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 189
            self.match(PiettoParser.LPAREN)
            self.state = 201
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 30822297567248) != 0):
                self.state = 190
                self.typeArgument()
                self.state = 195
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,19,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 191
                        self.match(PiettoParser.COMMA)
                        self.state = 192
                        self.typeArgument() 
                    self.state = 197
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,19,self._ctx)

                self.state = 199
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==37:
                    self.state = 198
                    self.match(PiettoParser.COMMA)




            self.state = 203
            self.match(PiettoParser.RPAREN)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TypeArgumentContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def typeArgumentName(self):
            return self.getTypedRuleContext(PiettoParser.TypeArgumentNameContext,0)


        def ASSIGN(self):
            return self.getToken(PiettoParser.ASSIGN, 0)

        def expression(self):
            return self.getTypedRuleContext(PiettoParser.ExpressionContext,0)


        def getRuleIndex(self):
            return PiettoParser.RULE_typeArgument

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTypeArgument" ):
                return visitor.visitTypeArgument(self)
            else:
                return visitor.visitChildren(self)




    def typeArgument(self):

        localctx = PiettoParser.TypeArgumentContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_typeArgument)
        try:
            self.state = 210
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,22,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 205
                self.typeArgumentName()
                self.state = 206
                self.match(PiettoParser.ASSIGN)
                self.state = 207
                self.expression()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 209
                self.expression()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TypeArgumentNameContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENTIFIER(self):
            return self.getToken(PiettoParser.IDENTIFIER, 0)

        def ENCODING(self):
            return self.getToken(PiettoParser.ENCODING, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_typeArgumentName

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTypeArgumentName" ):
                return visitor.visitTypeArgumentName(self)
            else:
                return visitor.visitChildren(self)




    def typeArgumentName(self):

        localctx = PiettoParser.TypeArgumentNameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_typeArgumentName)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 212
            _la = self._input.LA(1)
            if not(_la==4 or _la==44):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class EnumDefinitionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ENUM(self):
            return self.getToken(PiettoParser.ENUM, 0)

        def IDENTIFIER(self):
            return self.getToken(PiettoParser.IDENTIFIER, 0)

        def COLON(self):
            return self.getToken(PiettoParser.COLON, 0)

        def NEWLINE(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.NEWLINE)
            else:
                return self.getToken(PiettoParser.NEWLINE, i)

        def INDENT(self):
            return self.getToken(PiettoParser.INDENT, 0)

        def enumBody(self):
            return self.getTypedRuleContext(PiettoParser.EnumBodyContext,0)


        def DEDENT(self):
            return self.getToken(PiettoParser.DEDENT, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_enumDefinition

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitEnumDefinition" ):
                return visitor.visitEnumDefinition(self)
            else:
                return visitor.visitChildren(self)




    def enumDefinition(self):

        localctx = PiettoParser.EnumDefinitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_enumDefinition)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 214
            self.match(PiettoParser.ENUM)
            self.state = 215
            self.match(PiettoParser.IDENTIFIER)
            self.state = 216
            self.match(PiettoParser.COLON)
            self.state = 217
            self.match(PiettoParser.NEWLINE)
            self.state = 221
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==45:
                self.state = 218
                self.match(PiettoParser.NEWLINE)
                self.state = 223
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 224
            self.match(PiettoParser.INDENT)
            self.state = 225
            self.enumBody()
            self.state = 226
            self.match(PiettoParser.DEDENT)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class EnumBodyContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def enumItem(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PiettoParser.EnumItemContext)
            else:
                return self.getTypedRuleContext(PiettoParser.EnumItemContext,i)


        def NEWLINE(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.NEWLINE)
            else:
                return self.getToken(PiettoParser.NEWLINE, i)

        def getRuleIndex(self):
            return PiettoParser.RULE_enumBody

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitEnumBody" ):
                return visitor.visitEnumBody(self)
            else:
                return visitor.visitChildren(self)




    def enumBody(self):

        localctx = PiettoParser.EnumBodyContext(self, self._ctx, self.state)
        self.enterRule(localctx, 30, self.RULE_enumBody)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 230 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 230
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [44]:
                    self.state = 228
                    self.enumItem()
                    pass
                elif token in [45]:
                    self.state = 229
                    self.match(PiettoParser.NEWLINE)
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 232 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==44 or _la==45):
                    break

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class EnumItemContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENTIFIER(self):
            return self.getToken(PiettoParser.IDENTIFIER, 0)

        def NEWLINE(self):
            return self.getToken(PiettoParser.NEWLINE, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_enumItem

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitEnumItem" ):
                return visitor.visitEnumItem(self)
            else:
                return visitor.visitChildren(self)




    def enumItem(self):

        localctx = PiettoParser.EnumItemContext(self, self._ctx, self.state)
        self.enterRule(localctx, 32, self.RULE_enumItem)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 234
            self.match(PiettoParser.IDENTIFIER)
            self.state = 235
            self.match(PiettoParser.NEWLINE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ConstraintDefinitionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def CONSTRAINT(self):
            return self.getToken(PiettoParser.CONSTRAINT, 0)

        def IDENTIFIER(self):
            return self.getToken(PiettoParser.IDENTIFIER, 0)

        def LPAREN(self):
            return self.getToken(PiettoParser.LPAREN, 0)

        def RPAREN(self):
            return self.getToken(PiettoParser.RPAREN, 0)

        def ARROW(self):
            return self.getToken(PiettoParser.ARROW, 0)

        def typeExpression(self):
            return self.getTypedRuleContext(PiettoParser.TypeExpressionContext,0)


        def COLON(self):
            return self.getToken(PiettoParser.COLON, 0)

        def NEWLINE(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.NEWLINE)
            else:
                return self.getToken(PiettoParser.NEWLINE, i)

        def INDENT(self):
            return self.getToken(PiettoParser.INDENT, 0)

        def constraintBody(self):
            return self.getTypedRuleContext(PiettoParser.ConstraintBodyContext,0)


        def DEDENT(self):
            return self.getToken(PiettoParser.DEDENT, 0)

        def parameterList(self):
            return self.getTypedRuleContext(PiettoParser.ParameterListContext,0)


        def getRuleIndex(self):
            return PiettoParser.RULE_constraintDefinition

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitConstraintDefinition" ):
                return visitor.visitConstraintDefinition(self)
            else:
                return visitor.visitChildren(self)




    def constraintDefinition(self):

        localctx = PiettoParser.ConstraintDefinitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 34, self.RULE_constraintDefinition)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 237
            self.match(PiettoParser.CONSTRAINT)
            self.state = 238
            self.match(PiettoParser.IDENTIFIER)
            self.state = 239
            self.match(PiettoParser.LPAREN)
            self.state = 241
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==44:
                self.state = 240
                self.parameterList()


            self.state = 243
            self.match(PiettoParser.RPAREN)
            self.state = 244
            self.match(PiettoParser.ARROW)
            self.state = 245
            self.typeExpression()
            self.state = 246
            self.match(PiettoParser.COLON)
            self.state = 247
            self.match(PiettoParser.NEWLINE)
            self.state = 251
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==45:
                self.state = 248
                self.match(PiettoParser.NEWLINE)
                self.state = 253
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 254
            self.match(PiettoParser.INDENT)
            self.state = 255
            self.constraintBody()
            self.state = 256
            self.match(PiettoParser.DEDENT)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ParameterListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def parameter(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PiettoParser.ParameterContext)
            else:
                return self.getTypedRuleContext(PiettoParser.ParameterContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.COMMA)
            else:
                return self.getToken(PiettoParser.COMMA, i)

        def getRuleIndex(self):
            return PiettoParser.RULE_parameterList

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitParameterList" ):
                return visitor.visitParameterList(self)
            else:
                return visitor.visitChildren(self)




    def parameterList(self):

        localctx = PiettoParser.ParameterListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 36, self.RULE_parameterList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 258
            self.parameter()
            self.state = 263
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,28,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 259
                    self.match(PiettoParser.COMMA)
                    self.state = 260
                    self.parameter() 
                self.state = 265
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,28,self._ctx)

            self.state = 267
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==37:
                self.state = 266
                self.match(PiettoParser.COMMA)


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ParameterContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENTIFIER(self):
            return self.getToken(PiettoParser.IDENTIFIER, 0)

        def COLON(self):
            return self.getToken(PiettoParser.COLON, 0)

        def typeExpression(self):
            return self.getTypedRuleContext(PiettoParser.TypeExpressionContext,0)


        def getRuleIndex(self):
            return PiettoParser.RULE_parameter

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitParameter" ):
                return visitor.visitParameter(self)
            else:
                return visitor.visitChildren(self)




    def parameter(self):

        localctx = PiettoParser.ParameterContext(self, self._ctx, self.state)
        self.enterRule(localctx, 38, self.RULE_parameter)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 269
            self.match(PiettoParser.IDENTIFIER)
            self.state = 270
            self.match(PiettoParser.COLON)
            self.state = 271
            self.typeExpression()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ConstraintBodyContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def expression(self):
            return self.getTypedRuleContext(PiettoParser.ExpressionContext,0)


        def NEWLINE(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.NEWLINE)
            else:
                return self.getToken(PiettoParser.NEWLINE, i)

        def getRuleIndex(self):
            return PiettoParser.RULE_constraintBody

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitConstraintBody" ):
                return visitor.visitConstraintBody(self)
            else:
                return visitor.visitChildren(self)




    def constraintBody(self):

        localctx = PiettoParser.ConstraintBodyContext(self, self._ctx, self.state)
        self.enterRule(localctx, 40, self.RULE_constraintBody)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 276
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==45:
                self.state = 273
                self.match(PiettoParser.NEWLINE)
                self.state = 278
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 279
            self.expression()
            self.state = 280
            self.match(PiettoParser.NEWLINE)
            self.state = 284
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==45:
                self.state = 281
                self.match(PiettoParser.NEWLINE)
                self.state = 286
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def orExpression(self):
            return self.getTypedRuleContext(PiettoParser.OrExpressionContext,0)


        def getRuleIndex(self):
            return PiettoParser.RULE_expression

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitExpression" ):
                return visitor.visitExpression(self)
            else:
                return visitor.visitChildren(self)




    def expression(self):

        localctx = PiettoParser.ExpressionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 42, self.RULE_expression)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 287
            self.orExpression()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class OrExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def andExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PiettoParser.AndExpressionContext)
            else:
                return self.getTypedRuleContext(PiettoParser.AndExpressionContext,i)


        def OR(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.OR)
            else:
                return self.getToken(PiettoParser.OR, i)

        def getRuleIndex(self):
            return PiettoParser.RULE_orExpression

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOrExpression" ):
                return visitor.visitOrExpression(self)
            else:
                return visitor.visitChildren(self)




    def orExpression(self):

        localctx = PiettoParser.OrExpressionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 44, self.RULE_orExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 289
            self.andExpression()
            self.state = 294
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==13:
                self.state = 290
                self.match(PiettoParser.OR)
                self.state = 291
                self.andExpression()
                self.state = 296
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class AndExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def comparisonExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PiettoParser.ComparisonExpressionContext)
            else:
                return self.getTypedRuleContext(PiettoParser.ComparisonExpressionContext,i)


        def AND(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.AND)
            else:
                return self.getToken(PiettoParser.AND, i)

        def getRuleIndex(self):
            return PiettoParser.RULE_andExpression

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAndExpression" ):
                return visitor.visitAndExpression(self)
            else:
                return visitor.visitChildren(self)




    def andExpression(self):

        localctx = PiettoParser.AndExpressionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 46, self.RULE_andExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 297
            self.comparisonExpression()
            self.state = 302
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==12:
                self.state = 298
                self.match(PiettoParser.AND)
                self.state = 299
                self.comparisonExpression()
                self.state = 304
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ComparisonExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def additiveExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PiettoParser.AdditiveExpressionContext)
            else:
                return self.getTypedRuleContext(PiettoParser.AdditiveExpressionContext,i)


        def comparisonOperator(self):
            return self.getTypedRuleContext(PiettoParser.ComparisonOperatorContext,0)


        def BETWEEN(self):
            return self.getToken(PiettoParser.BETWEEN, 0)

        def AND(self):
            return self.getToken(PiettoParser.AND, 0)

        def IS(self):
            return self.getToken(PiettoParser.IS, 0)

        def NULL(self):
            return self.getToken(PiettoParser.NULL, 0)

        def NOT(self):
            return self.getToken(PiettoParser.NOT, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_comparisonExpression

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitComparisonExpression" ):
                return visitor.visitComparisonExpression(self)
            else:
                return visitor.visitChildren(self)




    def comparisonExpression(self):

        localctx = PiettoParser.ComparisonExpressionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 48, self.RULE_comparisonExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 305
            self.additiveExpression()
            self.state = 319
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [18, 21, 22, 23, 24, 25, 26]:
                self.state = 306
                self.comparisonOperator()
                self.state = 307
                self.additiveExpression()
                pass
            elif token in [17]:
                self.state = 309
                self.match(PiettoParser.BETWEEN)
                self.state = 310
                self.additiveExpression()
                self.state = 311
                self.match(PiettoParser.AND)
                self.state = 312
                self.additiveExpression()
                pass
            elif token in [14]:
                self.state = 314
                self.match(PiettoParser.IS)
                self.state = 316
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==15:
                    self.state = 315
                    self.match(PiettoParser.NOT)


                self.state = 318
                self.match(PiettoParser.NULL)
                pass
            elif token in [12, 13, 36, 37, 45]:
                pass
            else:
                pass
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ComparisonOperatorContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def EQ(self):
            return self.getToken(PiettoParser.EQ, 0)

        def NE(self):
            return self.getToken(PiettoParser.NE, 0)

        def LT(self):
            return self.getToken(PiettoParser.LT, 0)

        def LE(self):
            return self.getToken(PiettoParser.LE, 0)

        def GT(self):
            return self.getToken(PiettoParser.GT, 0)

        def GE(self):
            return self.getToken(PiettoParser.GE, 0)

        def LIKE(self):
            return self.getToken(PiettoParser.LIKE, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_comparisonOperator

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitComparisonOperator" ):
                return visitor.visitComparisonOperator(self)
            else:
                return visitor.visitChildren(self)




    def comparisonOperator(self):

        localctx = PiettoParser.ComparisonOperatorContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_comparisonOperator)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 321
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 132382720) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class AdditiveExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def multiplicativeExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PiettoParser.MultiplicativeExpressionContext)
            else:
                return self.getTypedRuleContext(PiettoParser.MultiplicativeExpressionContext,i)


        def PLUS(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.PLUS)
            else:
                return self.getToken(PiettoParser.PLUS, i)

        def MINUS(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.MINUS)
            else:
                return self.getToken(PiettoParser.MINUS, i)

        def getRuleIndex(self):
            return PiettoParser.RULE_additiveExpression

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAdditiveExpression" ):
                return visitor.visitAdditiveExpression(self)
            else:
                return visitor.visitChildren(self)




    def additiveExpression(self):

        localctx = PiettoParser.AdditiveExpressionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 52, self.RULE_additiveExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 323
            self.multiplicativeExpression()
            self.state = 328
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==29 or _la==30:
                self.state = 324
                _la = self._input.LA(1)
                if not(_la==29 or _la==30):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 325
                self.multiplicativeExpression()
                self.state = 330
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class MultiplicativeExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def unaryExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PiettoParser.UnaryExpressionContext)
            else:
                return self.getTypedRuleContext(PiettoParser.UnaryExpressionContext,i)


        def STAR(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.STAR)
            else:
                return self.getToken(PiettoParser.STAR, i)

        def SLASH(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.SLASH)
            else:
                return self.getToken(PiettoParser.SLASH, i)

        def PERCENT(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.PERCENT)
            else:
                return self.getToken(PiettoParser.PERCENT, i)

        def getRuleIndex(self):
            return PiettoParser.RULE_multiplicativeExpression

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMultiplicativeExpression" ):
                return visitor.visitMultiplicativeExpression(self)
            else:
                return visitor.visitChildren(self)




    def multiplicativeExpression(self):

        localctx = PiettoParser.MultiplicativeExpressionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 54, self.RULE_multiplicativeExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 331
            self.unaryExpression()
            self.state = 336
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 15032385536) != 0):
                self.state = 332
                _la = self._input.LA(1)
                if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 15032385536) != 0)):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 333
                self.unaryExpression()
                self.state = 338
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class UnaryExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def unaryExpression(self):
            return self.getTypedRuleContext(PiettoParser.UnaryExpressionContext,0)


        def PLUS(self):
            return self.getToken(PiettoParser.PLUS, 0)

        def MINUS(self):
            return self.getToken(PiettoParser.MINUS, 0)

        def primaryExpression(self):
            return self.getTypedRuleContext(PiettoParser.PrimaryExpressionContext,0)


        def getRuleIndex(self):
            return PiettoParser.RULE_unaryExpression

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitUnaryExpression" ):
                return visitor.visitUnaryExpression(self)
            else:
                return visitor.visitChildren(self)




    def unaryExpression(self):

        localctx = PiettoParser.UnaryExpressionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 56, self.RULE_unaryExpression)
        self._la = 0 # Token type
        try:
            self.state = 342
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [29, 30]:
                self.enterOuterAlt(localctx, 1)
                self.state = 339
                _la = self._input.LA(1)
                if not(_la==29 or _la==30):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 340
                self.unaryExpression()
                pass
            elif token in [16, 19, 20, 35, 42, 43, 44]:
                self.enterOuterAlt(localctx, 2)
                self.state = 341
                self.primaryExpression()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PrimaryExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def literal(self):
            return self.getTypedRuleContext(PiettoParser.LiteralContext,0)


        def dottedName(self):
            return self.getTypedRuleContext(PiettoParser.DottedNameContext,0)


        def callSuffix(self):
            return self.getTypedRuleContext(PiettoParser.CallSuffixContext,0)


        def LPAREN(self):
            return self.getToken(PiettoParser.LPAREN, 0)

        def expression(self):
            return self.getTypedRuleContext(PiettoParser.ExpressionContext,0)


        def RPAREN(self):
            return self.getToken(PiettoParser.RPAREN, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_primaryExpression

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPrimaryExpression" ):
                return visitor.visitPrimaryExpression(self)
            else:
                return visitor.visitChildren(self)




    def primaryExpression(self):

        localctx = PiettoParser.PrimaryExpressionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 58, self.RULE_primaryExpression)
        self._la = 0 # Token type
        try:
            self.state = 353
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [16, 19, 20, 42, 43]:
                self.enterOuterAlt(localctx, 1)
                self.state = 344
                self.literal()
                pass
            elif token in [44]:
                self.enterOuterAlt(localctx, 2)
                self.state = 345
                self.dottedName()
                self.state = 347
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==35:
                    self.state = 346
                    self.callSuffix()


                pass
            elif token in [35]:
                self.enterOuterAlt(localctx, 3)
                self.state = 349
                self.match(PiettoParser.LPAREN)
                self.state = 350
                self.expression()
                self.state = 351
                self.match(PiettoParser.RPAREN)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DottedNameContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENTIFIER(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.IDENTIFIER)
            else:
                return self.getToken(PiettoParser.IDENTIFIER, i)

        def DOT(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.DOT)
            else:
                return self.getToken(PiettoParser.DOT, i)

        def getRuleIndex(self):
            return PiettoParser.RULE_dottedName

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDottedName" ):
                return visitor.visitDottedName(self)
            else:
                return visitor.visitChildren(self)




    def dottedName(self):

        localctx = PiettoParser.DottedNameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 60, self.RULE_dottedName)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 355
            self.match(PiettoParser.IDENTIFIER)
            self.state = 360
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==38:
                self.state = 356
                self.match(PiettoParser.DOT)
                self.state = 357
                self.match(PiettoParser.IDENTIFIER)
                self.state = 362
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CallSuffixContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LPAREN(self):
            return self.getToken(PiettoParser.LPAREN, 0)

        def RPAREN(self):
            return self.getToken(PiettoParser.RPAREN, 0)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PiettoParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(PiettoParser.ExpressionContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.COMMA)
            else:
                return self.getToken(PiettoParser.COMMA, i)

        def getRuleIndex(self):
            return PiettoParser.RULE_callSuffix

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCallSuffix" ):
                return visitor.visitCallSuffix(self)
            else:
                return visitor.visitChildren(self)




    def callSuffix(self):

        localctx = PiettoParser.CallSuffixContext(self, self._ctx, self.state)
        self.enterRule(localctx, 62, self.RULE_callSuffix)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 363
            self.match(PiettoParser.LPAREN)
            self.state = 375
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 30822297567232) != 0):
                self.state = 364
                self.expression()
                self.state = 369
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,42,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 365
                        self.match(PiettoParser.COMMA)
                        self.state = 366
                        self.expression() 
                    self.state = 371
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,42,self._ctx)

                self.state = 373
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==37:
                    self.state = 372
                    self.match(PiettoParser.COMMA)




            self.state = 377
            self.match(PiettoParser.RPAREN)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LiteralContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NUMBER(self):
            return self.getToken(PiettoParser.NUMBER, 0)

        def STRING(self):
            return self.getToken(PiettoParser.STRING, 0)

        def TRUE(self):
            return self.getToken(PiettoParser.TRUE, 0)

        def FALSE(self):
            return self.getToken(PiettoParser.FALSE, 0)

        def NULL(self):
            return self.getToken(PiettoParser.NULL, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_literal

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLiteral" ):
                return visitor.visitLiteral(self)
            else:
                return visitor.visitChildren(self)




    def literal(self):

        localctx = PiettoParser.LiteralContext(self, self._ctx, self.state)
        self.enterRule(localctx, 64, self.RULE_literal)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 379
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 13194141171712) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx





