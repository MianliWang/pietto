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
        4,1,48,323,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,1,0,5,0,60,8,0,10,0,12,0,63,9,0,1,0,3,0,66,8,
        0,1,0,5,0,69,8,0,10,0,12,0,72,9,0,1,0,1,0,5,0,76,8,0,10,0,12,0,79,
        9,0,5,0,81,8,0,10,0,12,0,84,9,0,1,0,1,0,1,1,1,1,3,1,90,8,1,1,1,3,
        1,93,8,1,1,1,3,1,96,8,1,1,1,1,1,3,1,100,8,1,1,1,3,1,103,8,1,1,1,
        1,1,3,1,107,8,1,1,1,3,1,110,8,1,1,2,1,2,1,2,1,2,1,3,1,3,1,3,1,3,
        1,4,1,4,1,4,1,4,1,5,1,5,1,5,1,5,1,6,1,6,3,6,130,8,6,1,7,1,7,1,7,
        1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,
        1,7,1,7,5,7,153,8,7,10,7,12,7,156,9,7,1,7,1,7,1,7,1,7,3,7,162,8,
        7,1,8,1,8,4,8,166,8,8,11,8,12,8,167,1,9,1,9,1,9,1,9,1,10,1,10,3,
        10,176,8,10,1,10,3,10,179,8,10,1,11,1,11,1,11,1,11,5,11,185,8,11,
        10,11,12,11,188,9,11,1,11,3,11,191,8,11,3,11,193,8,11,1,11,1,11,
        1,12,1,12,1,12,1,12,1,12,3,12,202,8,12,1,13,1,13,1,14,1,14,1,14,
        1,14,1,14,5,14,211,8,14,10,14,12,14,214,9,14,1,14,1,14,1,14,1,14,
        1,15,1,15,4,15,222,8,15,11,15,12,15,223,1,16,1,16,1,16,1,17,1,17,
        1,18,1,18,1,18,5,18,234,8,18,10,18,12,18,237,9,18,1,19,1,19,1,19,
        5,19,242,8,19,10,19,12,19,245,9,19,1,20,1,20,1,20,1,20,1,20,1,20,
        1,20,1,20,1,20,1,20,1,20,3,20,258,8,20,1,20,3,20,261,8,20,1,21,1,
        21,1,22,1,22,1,22,5,22,268,8,22,10,22,12,22,271,9,22,1,23,1,23,1,
        23,5,23,276,8,23,10,23,12,23,279,9,23,1,24,1,24,1,24,3,24,284,8,
        24,1,25,1,25,1,25,3,25,289,8,25,1,25,1,25,1,25,1,25,3,25,295,8,25,
        1,26,1,26,1,26,5,26,300,8,26,10,26,12,26,303,9,26,1,27,1,27,1,27,
        1,27,5,27,309,8,27,10,27,12,27,312,9,27,1,27,3,27,315,8,27,3,27,
        317,8,27,1,27,1,27,1,28,1,28,1,28,0,0,29,0,2,4,6,8,10,12,14,16,18,
        20,22,24,26,28,30,32,34,36,38,40,42,44,46,48,50,52,54,56,0,6,1,0,
        5,7,2,0,4,4,42,42,2,0,17,17,20,25,1,0,27,28,1,0,29,31,3,0,15,15,
        18,19,40,41,338,0,61,1,0,0,0,2,109,1,0,0,0,4,111,1,0,0,0,6,115,1,
        0,0,0,8,119,1,0,0,0,10,123,1,0,0,0,12,129,1,0,0,0,14,161,1,0,0,0,
        16,165,1,0,0,0,18,169,1,0,0,0,20,173,1,0,0,0,22,180,1,0,0,0,24,201,
        1,0,0,0,26,203,1,0,0,0,28,205,1,0,0,0,30,221,1,0,0,0,32,225,1,0,
        0,0,34,228,1,0,0,0,36,230,1,0,0,0,38,238,1,0,0,0,40,246,1,0,0,0,
        42,262,1,0,0,0,44,264,1,0,0,0,46,272,1,0,0,0,48,283,1,0,0,0,50,294,
        1,0,0,0,52,296,1,0,0,0,54,304,1,0,0,0,56,320,1,0,0,0,58,60,5,43,
        0,0,59,58,1,0,0,0,60,63,1,0,0,0,61,59,1,0,0,0,61,62,1,0,0,0,62,65,
        1,0,0,0,63,61,1,0,0,0,64,66,3,2,1,0,65,64,1,0,0,0,65,66,1,0,0,0,
        66,70,1,0,0,0,67,69,5,43,0,0,68,67,1,0,0,0,69,72,1,0,0,0,70,68,1,
        0,0,0,70,71,1,0,0,0,71,82,1,0,0,0,72,70,1,0,0,0,73,77,3,12,6,0,74,
        76,5,43,0,0,75,74,1,0,0,0,76,79,1,0,0,0,77,75,1,0,0,0,77,78,1,0,
        0,0,78,81,1,0,0,0,79,77,1,0,0,0,80,73,1,0,0,0,81,84,1,0,0,0,82,80,
        1,0,0,0,82,83,1,0,0,0,83,85,1,0,0,0,84,82,1,0,0,0,85,86,5,0,0,1,
        86,1,1,0,0,0,87,89,3,4,2,0,88,90,3,6,3,0,89,88,1,0,0,0,89,90,1,0,
        0,0,90,92,1,0,0,0,91,93,3,8,4,0,92,91,1,0,0,0,92,93,1,0,0,0,93,95,
        1,0,0,0,94,96,3,10,5,0,95,94,1,0,0,0,95,96,1,0,0,0,96,110,1,0,0,
        0,97,99,3,6,3,0,98,100,3,8,4,0,99,98,1,0,0,0,99,100,1,0,0,0,100,
        102,1,0,0,0,101,103,3,10,5,0,102,101,1,0,0,0,102,103,1,0,0,0,103,
        110,1,0,0,0,104,106,3,8,4,0,105,107,3,10,5,0,106,105,1,0,0,0,106,
        107,1,0,0,0,107,110,1,0,0,0,108,110,3,10,5,0,109,87,1,0,0,0,109,
        97,1,0,0,0,109,104,1,0,0,0,109,108,1,0,0,0,110,3,1,0,0,0,111,112,
        5,1,0,0,112,113,5,40,0,0,113,114,5,43,0,0,114,5,1,0,0,0,115,116,
        5,2,0,0,116,117,7,0,0,0,117,118,5,43,0,0,118,7,1,0,0,0,119,120,5,
        3,0,0,120,121,5,42,0,0,121,122,5,43,0,0,122,9,1,0,0,0,123,124,5,
        4,0,0,124,125,5,42,0,0,125,126,5,43,0,0,126,11,1,0,0,0,127,130,3,
        14,7,0,128,130,3,28,14,0,129,127,1,0,0,0,129,128,1,0,0,0,130,13,
        1,0,0,0,131,132,5,8,0,0,132,133,5,42,0,0,133,134,5,26,0,0,134,135,
        3,20,10,0,135,136,5,43,0,0,136,162,1,0,0,0,137,138,5,8,0,0,138,139,
        5,42,0,0,139,140,5,26,0,0,140,141,3,20,10,0,141,142,5,10,0,0,142,
        143,3,34,17,0,143,144,5,43,0,0,144,162,1,0,0,0,145,146,5,8,0,0,146,
        147,5,42,0,0,147,148,5,26,0,0,148,149,3,20,10,0,149,150,5,37,0,0,
        150,154,5,43,0,0,151,153,5,43,0,0,152,151,1,0,0,0,153,156,1,0,0,
        0,154,152,1,0,0,0,154,155,1,0,0,0,155,157,1,0,0,0,156,154,1,0,0,
        0,157,158,5,47,0,0,158,159,3,16,8,0,159,160,5,48,0,0,160,162,1,0,
        0,0,161,131,1,0,0,0,161,137,1,0,0,0,161,145,1,0,0,0,162,15,1,0,0,
        0,163,166,3,18,9,0,164,166,5,43,0,0,165,163,1,0,0,0,165,164,1,0,
        0,0,166,167,1,0,0,0,167,165,1,0,0,0,167,168,1,0,0,0,168,17,1,0,0,
        0,169,170,5,10,0,0,170,171,3,34,17,0,171,172,5,43,0,0,172,19,1,0,
        0,0,173,175,5,42,0,0,174,176,3,22,11,0,175,174,1,0,0,0,175,176,1,
        0,0,0,176,178,1,0,0,0,177,179,5,32,0,0,178,177,1,0,0,0,178,179,1,
        0,0,0,179,21,1,0,0,0,180,192,5,33,0,0,181,186,3,24,12,0,182,183,
        5,35,0,0,183,185,3,24,12,0,184,182,1,0,0,0,185,188,1,0,0,0,186,184,
        1,0,0,0,186,187,1,0,0,0,187,190,1,0,0,0,188,186,1,0,0,0,189,191,
        5,35,0,0,190,189,1,0,0,0,190,191,1,0,0,0,191,193,1,0,0,0,192,181,
        1,0,0,0,192,193,1,0,0,0,193,194,1,0,0,0,194,195,5,34,0,0,195,23,
        1,0,0,0,196,197,3,26,13,0,197,198,5,26,0,0,198,199,3,34,17,0,199,
        202,1,0,0,0,200,202,3,34,17,0,201,196,1,0,0,0,201,200,1,0,0,0,202,
        25,1,0,0,0,203,204,7,1,0,0,204,27,1,0,0,0,205,206,5,9,0,0,206,207,
        5,42,0,0,207,208,5,37,0,0,208,212,5,43,0,0,209,211,5,43,0,0,210,
        209,1,0,0,0,211,214,1,0,0,0,212,210,1,0,0,0,212,213,1,0,0,0,213,
        215,1,0,0,0,214,212,1,0,0,0,215,216,5,47,0,0,216,217,3,30,15,0,217,
        218,5,48,0,0,218,29,1,0,0,0,219,222,3,32,16,0,220,222,5,43,0,0,221,
        219,1,0,0,0,221,220,1,0,0,0,222,223,1,0,0,0,223,221,1,0,0,0,223,
        224,1,0,0,0,224,31,1,0,0,0,225,226,5,42,0,0,226,227,5,43,0,0,227,
        33,1,0,0,0,228,229,3,36,18,0,229,35,1,0,0,0,230,235,3,38,19,0,231,
        232,5,12,0,0,232,234,3,38,19,0,233,231,1,0,0,0,234,237,1,0,0,0,235,
        233,1,0,0,0,235,236,1,0,0,0,236,37,1,0,0,0,237,235,1,0,0,0,238,243,
        3,40,20,0,239,240,5,11,0,0,240,242,3,40,20,0,241,239,1,0,0,0,242,
        245,1,0,0,0,243,241,1,0,0,0,243,244,1,0,0,0,244,39,1,0,0,0,245,243,
        1,0,0,0,246,260,3,44,22,0,247,248,3,42,21,0,248,249,3,44,22,0,249,
        261,1,0,0,0,250,251,5,16,0,0,251,252,3,44,22,0,252,253,5,11,0,0,
        253,254,3,44,22,0,254,261,1,0,0,0,255,257,5,13,0,0,256,258,5,14,
        0,0,257,256,1,0,0,0,257,258,1,0,0,0,258,259,1,0,0,0,259,261,5,15,
        0,0,260,247,1,0,0,0,260,250,1,0,0,0,260,255,1,0,0,0,260,261,1,0,
        0,0,261,41,1,0,0,0,262,263,7,2,0,0,263,43,1,0,0,0,264,269,3,46,23,
        0,265,266,7,3,0,0,266,268,3,46,23,0,267,265,1,0,0,0,268,271,1,0,
        0,0,269,267,1,0,0,0,269,270,1,0,0,0,270,45,1,0,0,0,271,269,1,0,0,
        0,272,277,3,48,24,0,273,274,7,4,0,0,274,276,3,48,24,0,275,273,1,
        0,0,0,276,279,1,0,0,0,277,275,1,0,0,0,277,278,1,0,0,0,278,47,1,0,
        0,0,279,277,1,0,0,0,280,281,7,3,0,0,281,284,3,48,24,0,282,284,3,
        50,25,0,283,280,1,0,0,0,283,282,1,0,0,0,284,49,1,0,0,0,285,295,3,
        56,28,0,286,288,3,52,26,0,287,289,3,54,27,0,288,287,1,0,0,0,288,
        289,1,0,0,0,289,295,1,0,0,0,290,291,5,33,0,0,291,292,3,34,17,0,292,
        293,5,34,0,0,293,295,1,0,0,0,294,285,1,0,0,0,294,286,1,0,0,0,294,
        290,1,0,0,0,295,51,1,0,0,0,296,301,5,42,0,0,297,298,5,36,0,0,298,
        300,5,42,0,0,299,297,1,0,0,0,300,303,1,0,0,0,301,299,1,0,0,0,301,
        302,1,0,0,0,302,53,1,0,0,0,303,301,1,0,0,0,304,316,5,33,0,0,305,
        310,3,34,17,0,306,307,5,35,0,0,307,309,3,34,17,0,308,306,1,0,0,0,
        309,312,1,0,0,0,310,308,1,0,0,0,310,311,1,0,0,0,311,314,1,0,0,0,
        312,310,1,0,0,0,313,315,5,35,0,0,314,313,1,0,0,0,314,315,1,0,0,0,
        315,317,1,0,0,0,316,305,1,0,0,0,316,317,1,0,0,0,317,318,1,0,0,0,
        318,319,5,34,0,0,319,55,1,0,0,0,320,321,7,5,0,0,321,57,1,0,0,0,39,
        61,65,70,77,82,89,92,95,99,102,106,109,129,154,161,165,167,175,178,
        186,190,192,201,212,221,223,235,243,257,260,269,277,283,288,294,
        301,310,314,316
    ]

class PiettoParser ( Parser ):

    grammarFileName = "Pietto.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'pietto'", "'mode'", "'dialect'", "'encoding'", 
                     "'loose'", "'checked'", "'strict'", "'type'", "'enum'", 
                     "'ensure'", "'and'", "'or'", "'is'", "'not'", "'null'", 
                     "'between'", "'like'", "'true'", "'false'", "'=='", 
                     "'!='", "'<='", "'>='", "'<'", "'>'", "'='", "'+'", 
                     "'-'", "'*'", "'/'", "'%'", "'?'", "'('", "')'", "','", 
                     "'.'", "':'", "'{'", "'}'" ]

    symbolicNames = [ "<INVALID>", "PIETTO", "MODE", "DIALECT", "ENCODING", 
                      "LOOSE", "CHECKED", "STRICT", "TYPE", "ENUM", "ENSURE", 
                      "AND", "OR", "IS", "NOT", "NULL", "BETWEEN", "LIKE", 
                      "TRUE", "FALSE", "EQ", "NE", "LE", "GE", "LT", "GT", 
                      "ASSIGN", "PLUS", "MINUS", "STAR", "SLASH", "PERCENT", 
                      "QUESTION", "LPAREN", "RPAREN", "COMMA", "DOT", "COLON", 
                      "LBRACE", "RBRACE", "NUMBER", "STRING", "IDENTIFIER", 
                      "NEWLINE", "COMMENT", "WS", "UNKNOWN", "INDENT", "DEDENT" ]

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
    RULE_expression = 17
    RULE_orExpression = 18
    RULE_andExpression = 19
    RULE_comparisonExpression = 20
    RULE_comparisonOperator = 21
    RULE_additiveExpression = 22
    RULE_multiplicativeExpression = 23
    RULE_unaryExpression = 24
    RULE_primaryExpression = 25
    RULE_dottedName = 26
    RULE_callSuffix = 27
    RULE_literal = 28

    ruleNames =  [ "script", "header", "versionDecl", "modeDecl", "dialectDecl", 
                   "encodingDecl", "definition", "typeDefinition", "typeBody", 
                   "ensureClause", "typeExpression", "typeArguments", "typeArgument", 
                   "typeArgumentName", "enumDefinition", "enumBody", "enumItem", 
                   "expression", "orExpression", "andExpression", "comparisonExpression", 
                   "comparisonOperator", "additiveExpression", "multiplicativeExpression", 
                   "unaryExpression", "primaryExpression", "dottedName", 
                   "callSuffix", "literal" ]

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
    ENSURE=10
    AND=11
    OR=12
    IS=13
    NOT=14
    NULL=15
    BETWEEN=16
    LIKE=17
    TRUE=18
    FALSE=19
    EQ=20
    NE=21
    LE=22
    GE=23
    LT=24
    GT=25
    ASSIGN=26
    PLUS=27
    MINUS=28
    STAR=29
    SLASH=30
    PERCENT=31
    QUESTION=32
    LPAREN=33
    RPAREN=34
    COMMA=35
    DOT=36
    COLON=37
    LBRACE=38
    RBRACE=39
    NUMBER=40
    STRING=41
    IDENTIFIER=42
    NEWLINE=43
    COMMENT=44
    WS=45
    UNKNOWN=46
    INDENT=47
    DEDENT=48

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
            self.state = 61
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,0,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 58
                    self.match(PiettoParser.NEWLINE) 
                self.state = 63
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,0,self._ctx)

            self.state = 65
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 30) != 0):
                self.state = 64
                self.header()


            self.state = 70
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==43:
                self.state = 67
                self.match(PiettoParser.NEWLINE)
                self.state = 72
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 82
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==8 or _la==9:
                self.state = 73
                self.definition()
                self.state = 77
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==43:
                    self.state = 74
                    self.match(PiettoParser.NEWLINE)
                    self.state = 79
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 84
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 85
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
            self.state = 109
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [1]:
                self.enterOuterAlt(localctx, 1)
                self.state = 87
                self.versionDecl()
                self.state = 89
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==2:
                    self.state = 88
                    self.modeDecl()


                self.state = 92
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==3:
                    self.state = 91
                    self.dialectDecl()


                self.state = 95
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4:
                    self.state = 94
                    self.encodingDecl()


                pass
            elif token in [2]:
                self.enterOuterAlt(localctx, 2)
                self.state = 97
                self.modeDecl()
                self.state = 99
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==3:
                    self.state = 98
                    self.dialectDecl()


                self.state = 102
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4:
                    self.state = 101
                    self.encodingDecl()


                pass
            elif token in [3]:
                self.enterOuterAlt(localctx, 3)
                self.state = 104
                self.dialectDecl()
                self.state = 106
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4:
                    self.state = 105
                    self.encodingDecl()


                pass
            elif token in [4]:
                self.enterOuterAlt(localctx, 4)
                self.state = 108
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
            self.state = 111
            self.match(PiettoParser.PIETTO)
            self.state = 112
            self.match(PiettoParser.NUMBER)
            self.state = 113
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
            self.state = 115
            self.match(PiettoParser.MODE)
            self.state = 116
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 224) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 117
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
            self.state = 119
            self.match(PiettoParser.DIALECT)
            self.state = 120
            self.match(PiettoParser.IDENTIFIER)
            self.state = 121
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
            self.state = 123
            self.match(PiettoParser.ENCODING)
            self.state = 124
            self.match(PiettoParser.IDENTIFIER)
            self.state = 125
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
            self.state = 129
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [8]:
                self.enterOuterAlt(localctx, 1)
                self.state = 127
                self.typeDefinition()
                pass
            elif token in [9]:
                self.enterOuterAlt(localctx, 2)
                self.state = 128
                self.enumDefinition()
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
            self.state = 161
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,14,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 131
                self.match(PiettoParser.TYPE)
                self.state = 132
                self.match(PiettoParser.IDENTIFIER)
                self.state = 133
                self.match(PiettoParser.ASSIGN)
                self.state = 134
                self.typeExpression()
                self.state = 135
                self.match(PiettoParser.NEWLINE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 137
                self.match(PiettoParser.TYPE)
                self.state = 138
                self.match(PiettoParser.IDENTIFIER)
                self.state = 139
                self.match(PiettoParser.ASSIGN)
                self.state = 140
                self.typeExpression()
                self.state = 141
                self.match(PiettoParser.ENSURE)
                self.state = 142
                self.expression()
                self.state = 143
                self.match(PiettoParser.NEWLINE)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 145
                self.match(PiettoParser.TYPE)
                self.state = 146
                self.match(PiettoParser.IDENTIFIER)
                self.state = 147
                self.match(PiettoParser.ASSIGN)
                self.state = 148
                self.typeExpression()
                self.state = 149
                self.match(PiettoParser.COLON)
                self.state = 150
                self.match(PiettoParser.NEWLINE)
                self.state = 154
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==43:
                    self.state = 151
                    self.match(PiettoParser.NEWLINE)
                    self.state = 156
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 157
                self.match(PiettoParser.INDENT)
                self.state = 158
                self.typeBody()
                self.state = 159
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
            self.state = 165 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 165
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [10]:
                    self.state = 163
                    self.ensureClause()
                    pass
                elif token in [43]:
                    self.state = 164
                    self.match(PiettoParser.NEWLINE)
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 167 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==10 or _la==43):
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
            self.state = 169
            self.match(PiettoParser.ENSURE)
            self.state = 170
            self.expression()
            self.state = 171
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
            self.state = 173
            self.match(PiettoParser.IDENTIFIER)
            self.state = 175
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==33:
                self.state = 174
                self.typeArguments()


            self.state = 178
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==32:
                self.state = 177
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
            self.state = 180
            self.match(PiettoParser.LPAREN)
            self.state = 192
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 7705574801424) != 0):
                self.state = 181
                self.typeArgument()
                self.state = 186
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,19,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 182
                        self.match(PiettoParser.COMMA)
                        self.state = 183
                        self.typeArgument() 
                    self.state = 188
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,19,self._ctx)

                self.state = 190
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==35:
                    self.state = 189
                    self.match(PiettoParser.COMMA)




            self.state = 194
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
            self.state = 201
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,22,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 196
                self.typeArgumentName()
                self.state = 197
                self.match(PiettoParser.ASSIGN)
                self.state = 198
                self.expression()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 200
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
            self.state = 203
            _la = self._input.LA(1)
            if not(_la==4 or _la==42):
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
            self.state = 205
            self.match(PiettoParser.ENUM)
            self.state = 206
            self.match(PiettoParser.IDENTIFIER)
            self.state = 207
            self.match(PiettoParser.COLON)
            self.state = 208
            self.match(PiettoParser.NEWLINE)
            self.state = 212
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==43:
                self.state = 209
                self.match(PiettoParser.NEWLINE)
                self.state = 214
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 215
            self.match(PiettoParser.INDENT)
            self.state = 216
            self.enumBody()
            self.state = 217
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
            self.state = 221 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 221
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [42]:
                    self.state = 219
                    self.enumItem()
                    pass
                elif token in [43]:
                    self.state = 220
                    self.match(PiettoParser.NEWLINE)
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 223 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==42 or _la==43):
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
            self.state = 225
            self.match(PiettoParser.IDENTIFIER)
            self.state = 226
            self.match(PiettoParser.NEWLINE)
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
        self.enterRule(localctx, 34, self.RULE_expression)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 228
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
        self.enterRule(localctx, 36, self.RULE_orExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 230
            self.andExpression()
            self.state = 235
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==12:
                self.state = 231
                self.match(PiettoParser.OR)
                self.state = 232
                self.andExpression()
                self.state = 237
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
        self.enterRule(localctx, 38, self.RULE_andExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 238
            self.comparisonExpression()
            self.state = 243
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==11:
                self.state = 239
                self.match(PiettoParser.AND)
                self.state = 240
                self.comparisonExpression()
                self.state = 245
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
        self.enterRule(localctx, 40, self.RULE_comparisonExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 246
            self.additiveExpression()
            self.state = 260
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [17, 20, 21, 22, 23, 24, 25]:
                self.state = 247
                self.comparisonOperator()
                self.state = 248
                self.additiveExpression()
                pass
            elif token in [16]:
                self.state = 250
                self.match(PiettoParser.BETWEEN)
                self.state = 251
                self.additiveExpression()
                self.state = 252
                self.match(PiettoParser.AND)
                self.state = 253
                self.additiveExpression()
                pass
            elif token in [13]:
                self.state = 255
                self.match(PiettoParser.IS)
                self.state = 257
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==14:
                    self.state = 256
                    self.match(PiettoParser.NOT)


                self.state = 259
                self.match(PiettoParser.NULL)
                pass
            elif token in [11, 12, 34, 35, 43]:
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
        self.enterRule(localctx, 42, self.RULE_comparisonOperator)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 262
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 66191360) != 0)):
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
        self.enterRule(localctx, 44, self.RULE_additiveExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 264
            self.multiplicativeExpression()
            self.state = 269
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==27 or _la==28:
                self.state = 265
                _la = self._input.LA(1)
                if not(_la==27 or _la==28):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 266
                self.multiplicativeExpression()
                self.state = 271
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
        self.enterRule(localctx, 46, self.RULE_multiplicativeExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 272
            self.unaryExpression()
            self.state = 277
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 3758096384) != 0):
                self.state = 273
                _la = self._input.LA(1)
                if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 3758096384) != 0)):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 274
                self.unaryExpression()
                self.state = 279
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
        self.enterRule(localctx, 48, self.RULE_unaryExpression)
        self._la = 0 # Token type
        try:
            self.state = 283
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [27, 28]:
                self.enterOuterAlt(localctx, 1)
                self.state = 280
                _la = self._input.LA(1)
                if not(_la==27 or _la==28):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 281
                self.unaryExpression()
                pass
            elif token in [15, 18, 19, 33, 40, 41, 42]:
                self.enterOuterAlt(localctx, 2)
                self.state = 282
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
        self.enterRule(localctx, 50, self.RULE_primaryExpression)
        self._la = 0 # Token type
        try:
            self.state = 294
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [15, 18, 19, 40, 41]:
                self.enterOuterAlt(localctx, 1)
                self.state = 285
                self.literal()
                pass
            elif token in [42]:
                self.enterOuterAlt(localctx, 2)
                self.state = 286
                self.dottedName()
                self.state = 288
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==33:
                    self.state = 287
                    self.callSuffix()


                pass
            elif token in [33]:
                self.enterOuterAlt(localctx, 3)
                self.state = 290
                self.match(PiettoParser.LPAREN)
                self.state = 291
                self.expression()
                self.state = 292
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
        self.enterRule(localctx, 52, self.RULE_dottedName)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 296
            self.match(PiettoParser.IDENTIFIER)
            self.state = 301
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==36:
                self.state = 297
                self.match(PiettoParser.DOT)
                self.state = 298
                self.match(PiettoParser.IDENTIFIER)
                self.state = 303
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
        self.enterRule(localctx, 54, self.RULE_callSuffix)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 304
            self.match(PiettoParser.LPAREN)
            self.state = 316
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 7705574801408) != 0):
                self.state = 305
                self.expression()
                self.state = 310
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,36,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 306
                        self.match(PiettoParser.COMMA)
                        self.state = 307
                        self.expression() 
                    self.state = 312
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,36,self._ctx)

                self.state = 314
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==35:
                    self.state = 313
                    self.match(PiettoParser.COMMA)




            self.state = 318
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
        self.enterRule(localctx, 56, self.RULE_literal)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 320
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 3298535702528) != 0)):
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





