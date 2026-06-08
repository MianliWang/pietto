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
        4,1,51,422,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,2,31,7,31,2,32,7,32,2,33,
        7,33,2,34,7,34,1,0,5,0,72,8,0,10,0,12,0,75,9,0,1,0,3,0,78,8,0,1,
        0,5,0,81,8,0,10,0,12,0,84,9,0,1,0,1,0,5,0,88,8,0,10,0,12,0,91,9,
        0,5,0,93,8,0,10,0,12,0,96,9,0,1,0,1,0,1,1,1,1,3,1,102,8,1,1,1,3,
        1,105,8,1,1,1,3,1,108,8,1,1,1,1,1,3,1,112,8,1,1,1,3,1,115,8,1,1,
        1,1,1,3,1,119,8,1,1,1,3,1,122,8,1,1,2,1,2,1,2,1,2,1,3,1,3,1,3,1,
        3,1,4,1,4,1,4,1,4,1,5,1,5,1,5,1,5,1,6,1,6,1,6,1,6,3,6,144,8,6,1,
        7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,
        7,1,7,1,7,1,7,1,7,5,7,167,8,7,10,7,12,7,170,9,7,1,7,1,7,1,7,1,7,
        3,7,176,8,7,1,8,1,8,4,8,180,8,8,11,8,12,8,181,1,9,1,9,1,9,1,9,1,
        10,1,10,3,10,190,8,10,1,10,3,10,193,8,10,1,11,1,11,1,11,1,11,5,11,
        199,8,11,10,11,12,11,202,9,11,1,11,3,11,205,8,11,3,11,207,8,11,1,
        11,1,11,1,12,1,12,1,12,1,12,1,12,3,12,216,8,12,1,13,1,13,1,14,1,
        14,1,14,1,14,1,14,5,14,225,8,14,10,14,12,14,228,9,14,1,14,1,14,1,
        14,1,14,1,15,1,15,4,15,236,8,15,11,15,12,15,237,1,16,1,16,1,16,1,
        17,1,17,1,17,1,17,3,17,247,8,17,1,17,1,17,1,17,1,17,1,17,1,17,5,
        17,255,8,17,10,17,12,17,258,9,17,1,17,1,17,1,17,1,17,1,18,1,18,1,
        18,5,18,267,8,18,10,18,12,18,270,9,18,1,18,3,18,273,8,18,1,19,1,
        19,1,19,1,19,1,20,5,20,280,8,20,10,20,12,20,283,9,20,1,20,1,20,1,
        20,5,20,288,8,20,10,20,12,20,291,9,20,1,21,1,21,1,21,1,21,3,21,297,
        8,21,1,21,1,21,1,21,1,21,1,21,1,21,5,21,305,8,21,10,21,12,21,308,
        9,21,1,21,1,21,1,21,1,21,1,22,5,22,315,8,22,10,22,12,22,318,9,22,
        1,22,1,22,1,22,5,22,323,8,22,10,22,12,22,326,9,22,1,23,1,23,1,24,
        1,24,1,24,5,24,333,8,24,10,24,12,24,336,9,24,1,25,1,25,1,25,5,25,
        341,8,25,10,25,12,25,344,9,25,1,26,1,26,1,26,1,26,1,26,1,26,1,26,
        1,26,1,26,1,26,1,26,3,26,357,8,26,1,26,3,26,360,8,26,1,27,1,27,1,
        28,1,28,1,28,5,28,367,8,28,10,28,12,28,370,9,28,1,29,1,29,1,29,5,
        29,375,8,29,10,29,12,29,378,9,29,1,30,1,30,1,30,3,30,383,8,30,1,
        31,1,31,1,31,3,31,388,8,31,1,31,1,31,1,31,1,31,3,31,394,8,31,1,32,
        1,32,1,32,5,32,399,8,32,10,32,12,32,402,9,32,1,33,1,33,1,33,1,33,
        5,33,408,8,33,10,33,12,33,411,9,33,1,33,3,33,414,8,33,3,33,416,8,
        33,1,33,1,33,1,34,1,34,1,34,0,0,35,0,2,4,6,8,10,12,14,16,18,20,22,
        24,26,28,30,32,34,36,38,40,42,44,46,48,50,52,54,56,58,60,62,64,66,
        68,0,6,1,0,5,7,2,0,4,4,45,45,2,0,19,19,22,27,1,0,30,31,1,0,32,34,
        3,0,17,17,20,21,43,44,443,0,73,1,0,0,0,2,121,1,0,0,0,4,123,1,0,0,
        0,6,127,1,0,0,0,8,131,1,0,0,0,10,135,1,0,0,0,12,143,1,0,0,0,14,175,
        1,0,0,0,16,179,1,0,0,0,18,183,1,0,0,0,20,187,1,0,0,0,22,194,1,0,
        0,0,24,215,1,0,0,0,26,217,1,0,0,0,28,219,1,0,0,0,30,235,1,0,0,0,
        32,239,1,0,0,0,34,242,1,0,0,0,36,263,1,0,0,0,38,274,1,0,0,0,40,281,
        1,0,0,0,42,292,1,0,0,0,44,316,1,0,0,0,46,327,1,0,0,0,48,329,1,0,
        0,0,50,337,1,0,0,0,52,345,1,0,0,0,54,361,1,0,0,0,56,363,1,0,0,0,
        58,371,1,0,0,0,60,382,1,0,0,0,62,393,1,0,0,0,64,395,1,0,0,0,66,403,
        1,0,0,0,68,419,1,0,0,0,70,72,5,46,0,0,71,70,1,0,0,0,72,75,1,0,0,
        0,73,71,1,0,0,0,73,74,1,0,0,0,74,77,1,0,0,0,75,73,1,0,0,0,76,78,
        3,2,1,0,77,76,1,0,0,0,77,78,1,0,0,0,78,82,1,0,0,0,79,81,5,46,0,0,
        80,79,1,0,0,0,81,84,1,0,0,0,82,80,1,0,0,0,82,83,1,0,0,0,83,94,1,
        0,0,0,84,82,1,0,0,0,85,89,3,12,6,0,86,88,5,46,0,0,87,86,1,0,0,0,
        88,91,1,0,0,0,89,87,1,0,0,0,89,90,1,0,0,0,90,93,1,0,0,0,91,89,1,
        0,0,0,92,85,1,0,0,0,93,96,1,0,0,0,94,92,1,0,0,0,94,95,1,0,0,0,95,
        97,1,0,0,0,96,94,1,0,0,0,97,98,5,0,0,1,98,1,1,0,0,0,99,101,3,4,2,
        0,100,102,3,6,3,0,101,100,1,0,0,0,101,102,1,0,0,0,102,104,1,0,0,
        0,103,105,3,8,4,0,104,103,1,0,0,0,104,105,1,0,0,0,105,107,1,0,0,
        0,106,108,3,10,5,0,107,106,1,0,0,0,107,108,1,0,0,0,108,122,1,0,0,
        0,109,111,3,6,3,0,110,112,3,8,4,0,111,110,1,0,0,0,111,112,1,0,0,
        0,112,114,1,0,0,0,113,115,3,10,5,0,114,113,1,0,0,0,114,115,1,0,0,
        0,115,122,1,0,0,0,116,118,3,8,4,0,117,119,3,10,5,0,118,117,1,0,0,
        0,118,119,1,0,0,0,119,122,1,0,0,0,120,122,3,10,5,0,121,99,1,0,0,
        0,121,109,1,0,0,0,121,116,1,0,0,0,121,120,1,0,0,0,122,3,1,0,0,0,
        123,124,5,1,0,0,124,125,5,43,0,0,125,126,5,46,0,0,126,5,1,0,0,0,
        127,128,5,2,0,0,128,129,7,0,0,0,129,130,5,46,0,0,130,7,1,0,0,0,131,
        132,5,3,0,0,132,133,5,45,0,0,133,134,5,46,0,0,134,9,1,0,0,0,135,
        136,5,4,0,0,136,137,5,45,0,0,137,138,5,46,0,0,138,11,1,0,0,0,139,
        144,3,14,7,0,140,144,3,28,14,0,141,144,3,34,17,0,142,144,3,42,21,
        0,143,139,1,0,0,0,143,140,1,0,0,0,143,141,1,0,0,0,143,142,1,0,0,
        0,144,13,1,0,0,0,145,146,5,8,0,0,146,147,5,45,0,0,147,148,5,28,0,
        0,148,149,3,20,10,0,149,150,5,46,0,0,150,176,1,0,0,0,151,152,5,8,
        0,0,152,153,5,45,0,0,153,154,5,28,0,0,154,155,3,20,10,0,155,156,
        5,12,0,0,156,157,3,46,23,0,157,158,5,46,0,0,158,176,1,0,0,0,159,
        160,5,8,0,0,160,161,5,45,0,0,161,162,5,28,0,0,162,163,3,20,10,0,
        163,164,5,40,0,0,164,168,5,46,0,0,165,167,5,46,0,0,166,165,1,0,0,
        0,167,170,1,0,0,0,168,166,1,0,0,0,168,169,1,0,0,0,169,171,1,0,0,
        0,170,168,1,0,0,0,171,172,5,50,0,0,172,173,3,16,8,0,173,174,5,51,
        0,0,174,176,1,0,0,0,175,145,1,0,0,0,175,151,1,0,0,0,175,159,1,0,
        0,0,176,15,1,0,0,0,177,180,3,18,9,0,178,180,5,46,0,0,179,177,1,0,
        0,0,179,178,1,0,0,0,180,181,1,0,0,0,181,179,1,0,0,0,181,182,1,0,
        0,0,182,17,1,0,0,0,183,184,5,12,0,0,184,185,3,46,23,0,185,186,5,
        46,0,0,186,19,1,0,0,0,187,189,5,45,0,0,188,190,3,22,11,0,189,188,
        1,0,0,0,189,190,1,0,0,0,190,192,1,0,0,0,191,193,5,35,0,0,192,191,
        1,0,0,0,192,193,1,0,0,0,193,21,1,0,0,0,194,206,5,36,0,0,195,200,
        3,24,12,0,196,197,5,38,0,0,197,199,3,24,12,0,198,196,1,0,0,0,199,
        202,1,0,0,0,200,198,1,0,0,0,200,201,1,0,0,0,201,204,1,0,0,0,202,
        200,1,0,0,0,203,205,5,38,0,0,204,203,1,0,0,0,204,205,1,0,0,0,205,
        207,1,0,0,0,206,195,1,0,0,0,206,207,1,0,0,0,207,208,1,0,0,0,208,
        209,5,37,0,0,209,23,1,0,0,0,210,211,3,26,13,0,211,212,5,28,0,0,212,
        213,3,46,23,0,213,216,1,0,0,0,214,216,3,46,23,0,215,210,1,0,0,0,
        215,214,1,0,0,0,216,25,1,0,0,0,217,218,7,1,0,0,218,27,1,0,0,0,219,
        220,5,9,0,0,220,221,5,45,0,0,221,222,5,40,0,0,222,226,5,46,0,0,223,
        225,5,46,0,0,224,223,1,0,0,0,225,228,1,0,0,0,226,224,1,0,0,0,226,
        227,1,0,0,0,227,229,1,0,0,0,228,226,1,0,0,0,229,230,5,50,0,0,230,
        231,3,30,15,0,231,232,5,51,0,0,232,29,1,0,0,0,233,236,3,32,16,0,
        234,236,5,46,0,0,235,233,1,0,0,0,235,234,1,0,0,0,236,237,1,0,0,0,
        237,235,1,0,0,0,237,238,1,0,0,0,238,31,1,0,0,0,239,240,5,45,0,0,
        240,241,5,46,0,0,241,33,1,0,0,0,242,243,5,10,0,0,243,244,5,45,0,
        0,244,246,5,36,0,0,245,247,3,36,18,0,246,245,1,0,0,0,246,247,1,0,
        0,0,247,248,1,0,0,0,248,249,5,37,0,0,249,250,5,29,0,0,250,251,3,
        20,10,0,251,252,5,40,0,0,252,256,5,46,0,0,253,255,5,46,0,0,254,253,
        1,0,0,0,255,258,1,0,0,0,256,254,1,0,0,0,256,257,1,0,0,0,257,259,
        1,0,0,0,258,256,1,0,0,0,259,260,5,50,0,0,260,261,3,40,20,0,261,262,
        5,51,0,0,262,35,1,0,0,0,263,268,3,38,19,0,264,265,5,38,0,0,265,267,
        3,38,19,0,266,264,1,0,0,0,267,270,1,0,0,0,268,266,1,0,0,0,268,269,
        1,0,0,0,269,272,1,0,0,0,270,268,1,0,0,0,271,273,5,38,0,0,272,271,
        1,0,0,0,272,273,1,0,0,0,273,37,1,0,0,0,274,275,5,45,0,0,275,276,
        5,40,0,0,276,277,3,20,10,0,277,39,1,0,0,0,278,280,5,46,0,0,279,278,
        1,0,0,0,280,283,1,0,0,0,281,279,1,0,0,0,281,282,1,0,0,0,282,284,
        1,0,0,0,283,281,1,0,0,0,284,285,3,46,23,0,285,289,5,46,0,0,286,288,
        5,46,0,0,287,286,1,0,0,0,288,291,1,0,0,0,289,287,1,0,0,0,289,290,
        1,0,0,0,290,41,1,0,0,0,291,289,1,0,0,0,292,293,5,11,0,0,293,294,
        5,45,0,0,294,296,5,36,0,0,295,297,3,36,18,0,296,295,1,0,0,0,296,
        297,1,0,0,0,297,298,1,0,0,0,298,299,5,37,0,0,299,300,5,29,0,0,300,
        301,3,20,10,0,301,302,5,40,0,0,302,306,5,46,0,0,303,305,5,46,0,0,
        304,303,1,0,0,0,305,308,1,0,0,0,306,304,1,0,0,0,306,307,1,0,0,0,
        307,309,1,0,0,0,308,306,1,0,0,0,309,310,5,50,0,0,310,311,3,44,22,
        0,311,312,5,51,0,0,312,43,1,0,0,0,313,315,5,46,0,0,314,313,1,0,0,
        0,315,318,1,0,0,0,316,314,1,0,0,0,316,317,1,0,0,0,317,319,1,0,0,
        0,318,316,1,0,0,0,319,320,3,46,23,0,320,324,5,46,0,0,321,323,5,46,
        0,0,322,321,1,0,0,0,323,326,1,0,0,0,324,322,1,0,0,0,324,325,1,0,
        0,0,325,45,1,0,0,0,326,324,1,0,0,0,327,328,3,48,24,0,328,47,1,0,
        0,0,329,334,3,50,25,0,330,331,5,14,0,0,331,333,3,50,25,0,332,330,
        1,0,0,0,333,336,1,0,0,0,334,332,1,0,0,0,334,335,1,0,0,0,335,49,1,
        0,0,0,336,334,1,0,0,0,337,342,3,52,26,0,338,339,5,13,0,0,339,341,
        3,52,26,0,340,338,1,0,0,0,341,344,1,0,0,0,342,340,1,0,0,0,342,343,
        1,0,0,0,343,51,1,0,0,0,344,342,1,0,0,0,345,359,3,56,28,0,346,347,
        3,54,27,0,347,348,3,56,28,0,348,360,1,0,0,0,349,350,5,18,0,0,350,
        351,3,56,28,0,351,352,5,13,0,0,352,353,3,56,28,0,353,360,1,0,0,0,
        354,356,5,15,0,0,355,357,5,16,0,0,356,355,1,0,0,0,356,357,1,0,0,
        0,357,358,1,0,0,0,358,360,5,17,0,0,359,346,1,0,0,0,359,349,1,0,0,
        0,359,354,1,0,0,0,359,360,1,0,0,0,360,53,1,0,0,0,361,362,7,2,0,0,
        362,55,1,0,0,0,363,368,3,58,29,0,364,365,7,3,0,0,365,367,3,58,29,
        0,366,364,1,0,0,0,367,370,1,0,0,0,368,366,1,0,0,0,368,369,1,0,0,
        0,369,57,1,0,0,0,370,368,1,0,0,0,371,376,3,60,30,0,372,373,7,4,0,
        0,373,375,3,60,30,0,374,372,1,0,0,0,375,378,1,0,0,0,376,374,1,0,
        0,0,376,377,1,0,0,0,377,59,1,0,0,0,378,376,1,0,0,0,379,380,7,3,0,
        0,380,383,3,60,30,0,381,383,3,62,31,0,382,379,1,0,0,0,382,381,1,
        0,0,0,383,61,1,0,0,0,384,394,3,68,34,0,385,387,3,64,32,0,386,388,
        3,66,33,0,387,386,1,0,0,0,387,388,1,0,0,0,388,394,1,0,0,0,389,390,
        5,36,0,0,390,391,3,46,23,0,391,392,5,37,0,0,392,394,1,0,0,0,393,
        384,1,0,0,0,393,385,1,0,0,0,393,389,1,0,0,0,394,63,1,0,0,0,395,400,
        5,45,0,0,396,397,5,39,0,0,397,399,5,45,0,0,398,396,1,0,0,0,399,402,
        1,0,0,0,400,398,1,0,0,0,400,401,1,0,0,0,401,65,1,0,0,0,402,400,1,
        0,0,0,403,415,5,36,0,0,404,409,3,46,23,0,405,406,5,38,0,0,406,408,
        3,46,23,0,407,405,1,0,0,0,408,411,1,0,0,0,409,407,1,0,0,0,409,410,
        1,0,0,0,410,413,1,0,0,0,411,409,1,0,0,0,412,414,5,38,0,0,413,412,
        1,0,0,0,413,414,1,0,0,0,414,416,1,0,0,0,415,404,1,0,0,0,415,416,
        1,0,0,0,416,417,1,0,0,0,417,418,5,37,0,0,418,67,1,0,0,0,419,420,
        7,5,0,0,420,69,1,0,0,0,49,73,77,82,89,94,101,104,107,111,114,118,
        121,143,168,175,179,181,189,192,200,204,206,215,226,235,237,246,
        256,268,272,281,289,296,306,316,324,334,342,356,359,368,376,382,
        387,393,400,409,413,415
    ]

class PiettoParser ( Parser ):

    grammarFileName = "Pietto.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'pietto'", "'mode'", "'dialect'", "'encoding'", 
                     "'loose'", "'checked'", "'strict'", "'type'", "'enum'", 
                     "'constraint'", "'derive'", "'ensure'", "'and'", "'or'", 
                     "'is'", "'not'", "'null'", "'between'", "'like'", "'true'", 
                     "'false'", "'=='", "'!='", "'<='", "'>='", "'<'", "'>'", 
                     "'='", "'->'", "'+'", "'-'", "'*'", "'/'", "'%'", "'?'", 
                     "'('", "')'", "','", "'.'", "':'", "'{'", "'}'" ]

    symbolicNames = [ "<INVALID>", "PIETTO", "MODE", "DIALECT", "ENCODING", 
                      "LOOSE", "CHECKED", "STRICT", "TYPE", "ENUM", "CONSTRAINT", 
                      "DERIVE", "ENSURE", "AND", "OR", "IS", "NOT", "NULL", 
                      "BETWEEN", "LIKE", "TRUE", "FALSE", "EQ", "NE", "LE", 
                      "GE", "LT", "GT", "ASSIGN", "ARROW", "PLUS", "MINUS", 
                      "STAR", "SLASH", "PERCENT", "QUESTION", "LPAREN", 
                      "RPAREN", "COMMA", "DOT", "COLON", "LBRACE", "RBRACE", 
                      "NUMBER", "STRING", "IDENTIFIER", "NEWLINE", "COMMENT", 
                      "WS", "UNKNOWN", "INDENT", "DEDENT" ]

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
    RULE_deriveDefinition = 21
    RULE_deriveBody = 22
    RULE_expression = 23
    RULE_orExpression = 24
    RULE_andExpression = 25
    RULE_comparisonExpression = 26
    RULE_comparisonOperator = 27
    RULE_additiveExpression = 28
    RULE_multiplicativeExpression = 29
    RULE_unaryExpression = 30
    RULE_primaryExpression = 31
    RULE_dottedName = 32
    RULE_callSuffix = 33
    RULE_literal = 34

    ruleNames =  [ "script", "header", "versionDecl", "modeDecl", "dialectDecl", 
                   "encodingDecl", "definition", "typeDefinition", "typeBody", 
                   "ensureClause", "typeExpression", "typeArguments", "typeArgument", 
                   "typeArgumentName", "enumDefinition", "enumBody", "enumItem", 
                   "constraintDefinition", "parameterList", "parameter", 
                   "constraintBody", "deriveDefinition", "deriveBody", "expression", 
                   "orExpression", "andExpression", "comparisonExpression", 
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
    CONSTRAINT=10
    DERIVE=11
    ENSURE=12
    AND=13
    OR=14
    IS=15
    NOT=16
    NULL=17
    BETWEEN=18
    LIKE=19
    TRUE=20
    FALSE=21
    EQ=22
    NE=23
    LE=24
    GE=25
    LT=26
    GT=27
    ASSIGN=28
    ARROW=29
    PLUS=30
    MINUS=31
    STAR=32
    SLASH=33
    PERCENT=34
    QUESTION=35
    LPAREN=36
    RPAREN=37
    COMMA=38
    DOT=39
    COLON=40
    LBRACE=41
    RBRACE=42
    NUMBER=43
    STRING=44
    IDENTIFIER=45
    NEWLINE=46
    COMMENT=47
    WS=48
    UNKNOWN=49
    INDENT=50
    DEDENT=51

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
            self.state = 73
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,0,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 70
                    self.match(PiettoParser.NEWLINE) 
                self.state = 75
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,0,self._ctx)

            self.state = 77
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 30) != 0):
                self.state = 76
                self.header()


            self.state = 82
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==46:
                self.state = 79
                self.match(PiettoParser.NEWLINE)
                self.state = 84
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 94
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 3840) != 0):
                self.state = 85
                self.definition()
                self.state = 89
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==46:
                    self.state = 86
                    self.match(PiettoParser.NEWLINE)
                    self.state = 91
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 96
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 97
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
            self.state = 121
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [1]:
                self.enterOuterAlt(localctx, 1)
                self.state = 99
                self.versionDecl()
                self.state = 101
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==2:
                    self.state = 100
                    self.modeDecl()


                self.state = 104
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==3:
                    self.state = 103
                    self.dialectDecl()


                self.state = 107
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4:
                    self.state = 106
                    self.encodingDecl()


                pass
            elif token in [2]:
                self.enterOuterAlt(localctx, 2)
                self.state = 109
                self.modeDecl()
                self.state = 111
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==3:
                    self.state = 110
                    self.dialectDecl()


                self.state = 114
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4:
                    self.state = 113
                    self.encodingDecl()


                pass
            elif token in [3]:
                self.enterOuterAlt(localctx, 3)
                self.state = 116
                self.dialectDecl()
                self.state = 118
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4:
                    self.state = 117
                    self.encodingDecl()


                pass
            elif token in [4]:
                self.enterOuterAlt(localctx, 4)
                self.state = 120
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
            self.state = 123
            self.match(PiettoParser.PIETTO)
            self.state = 124
            self.match(PiettoParser.NUMBER)
            self.state = 125
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
            self.state = 127
            self.match(PiettoParser.MODE)
            self.state = 128
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 224) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 129
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
            self.state = 131
            self.match(PiettoParser.DIALECT)
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
            self.state = 135
            self.match(PiettoParser.ENCODING)
            self.state = 136
            self.match(PiettoParser.IDENTIFIER)
            self.state = 137
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


        def deriveDefinition(self):
            return self.getTypedRuleContext(PiettoParser.DeriveDefinitionContext,0)


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
            self.state = 143
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [8]:
                self.enterOuterAlt(localctx, 1)
                self.state = 139
                self.typeDefinition()
                pass
            elif token in [9]:
                self.enterOuterAlt(localctx, 2)
                self.state = 140
                self.enumDefinition()
                pass
            elif token in [10]:
                self.enterOuterAlt(localctx, 3)
                self.state = 141
                self.constraintDefinition()
                pass
            elif token in [11]:
                self.enterOuterAlt(localctx, 4)
                self.state = 142
                self.deriveDefinition()
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
            self.state = 175
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,14,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 145
                self.match(PiettoParser.TYPE)
                self.state = 146
                self.match(PiettoParser.IDENTIFIER)
                self.state = 147
                self.match(PiettoParser.ASSIGN)
                self.state = 148
                self.typeExpression()
                self.state = 149
                self.match(PiettoParser.NEWLINE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 151
                self.match(PiettoParser.TYPE)
                self.state = 152
                self.match(PiettoParser.IDENTIFIER)
                self.state = 153
                self.match(PiettoParser.ASSIGN)
                self.state = 154
                self.typeExpression()
                self.state = 155
                self.match(PiettoParser.ENSURE)
                self.state = 156
                self.expression()
                self.state = 157
                self.match(PiettoParser.NEWLINE)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 159
                self.match(PiettoParser.TYPE)
                self.state = 160
                self.match(PiettoParser.IDENTIFIER)
                self.state = 161
                self.match(PiettoParser.ASSIGN)
                self.state = 162
                self.typeExpression()
                self.state = 163
                self.match(PiettoParser.COLON)
                self.state = 164
                self.match(PiettoParser.NEWLINE)
                self.state = 168
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==46:
                    self.state = 165
                    self.match(PiettoParser.NEWLINE)
                    self.state = 170
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 171
                self.match(PiettoParser.INDENT)
                self.state = 172
                self.typeBody()
                self.state = 173
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
            self.state = 179 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 179
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [12]:
                    self.state = 177
                    self.ensureClause()
                    pass
                elif token in [46]:
                    self.state = 178
                    self.match(PiettoParser.NEWLINE)
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 181 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==12 or _la==46):
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
            self.state = 183
            self.match(PiettoParser.ENSURE)
            self.state = 184
            self.expression()
            self.state = 185
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
            self.state = 187
            self.match(PiettoParser.IDENTIFIER)
            self.state = 189
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==36:
                self.state = 188
                self.typeArguments()


            self.state = 192
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==35:
                self.state = 191
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
            self.state = 194
            self.match(PiettoParser.LPAREN)
            self.state = 206
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 61644595134480) != 0):
                self.state = 195
                self.typeArgument()
                self.state = 200
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,19,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 196
                        self.match(PiettoParser.COMMA)
                        self.state = 197
                        self.typeArgument() 
                    self.state = 202
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,19,self._ctx)

                self.state = 204
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==38:
                    self.state = 203
                    self.match(PiettoParser.COMMA)




            self.state = 208
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
            self.state = 215
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,22,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 210
                self.typeArgumentName()
                self.state = 211
                self.match(PiettoParser.ASSIGN)
                self.state = 212
                self.expression()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 214
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
            self.state = 217
            _la = self._input.LA(1)
            if not(_la==4 or _la==45):
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
            self.state = 219
            self.match(PiettoParser.ENUM)
            self.state = 220
            self.match(PiettoParser.IDENTIFIER)
            self.state = 221
            self.match(PiettoParser.COLON)
            self.state = 222
            self.match(PiettoParser.NEWLINE)
            self.state = 226
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==46:
                self.state = 223
                self.match(PiettoParser.NEWLINE)
                self.state = 228
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 229
            self.match(PiettoParser.INDENT)
            self.state = 230
            self.enumBody()
            self.state = 231
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
            self.state = 235 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 235
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [45]:
                    self.state = 233
                    self.enumItem()
                    pass
                elif token in [46]:
                    self.state = 234
                    self.match(PiettoParser.NEWLINE)
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 237 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==45 or _la==46):
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
            self.state = 239
            self.match(PiettoParser.IDENTIFIER)
            self.state = 240
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
            self.state = 242
            self.match(PiettoParser.CONSTRAINT)
            self.state = 243
            self.match(PiettoParser.IDENTIFIER)
            self.state = 244
            self.match(PiettoParser.LPAREN)
            self.state = 246
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==45:
                self.state = 245
                self.parameterList()


            self.state = 248
            self.match(PiettoParser.RPAREN)
            self.state = 249
            self.match(PiettoParser.ARROW)
            self.state = 250
            self.typeExpression()
            self.state = 251
            self.match(PiettoParser.COLON)
            self.state = 252
            self.match(PiettoParser.NEWLINE)
            self.state = 256
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==46:
                self.state = 253
                self.match(PiettoParser.NEWLINE)
                self.state = 258
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 259
            self.match(PiettoParser.INDENT)
            self.state = 260
            self.constraintBody()
            self.state = 261
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
            self.state = 263
            self.parameter()
            self.state = 268
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,28,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 264
                    self.match(PiettoParser.COMMA)
                    self.state = 265
                    self.parameter() 
                self.state = 270
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,28,self._ctx)

            self.state = 272
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==38:
                self.state = 271
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
            self.state = 274
            self.match(PiettoParser.IDENTIFIER)
            self.state = 275
            self.match(PiettoParser.COLON)
            self.state = 276
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
            self.state = 281
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==46:
                self.state = 278
                self.match(PiettoParser.NEWLINE)
                self.state = 283
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 284
            self.expression()
            self.state = 285
            self.match(PiettoParser.NEWLINE)
            self.state = 289
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==46:
                self.state = 286
                self.match(PiettoParser.NEWLINE)
                self.state = 291
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DeriveDefinitionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def DERIVE(self):
            return self.getToken(PiettoParser.DERIVE, 0)

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

        def deriveBody(self):
            return self.getTypedRuleContext(PiettoParser.DeriveBodyContext,0)


        def DEDENT(self):
            return self.getToken(PiettoParser.DEDENT, 0)

        def parameterList(self):
            return self.getTypedRuleContext(PiettoParser.ParameterListContext,0)


        def getRuleIndex(self):
            return PiettoParser.RULE_deriveDefinition

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDeriveDefinition" ):
                return visitor.visitDeriveDefinition(self)
            else:
                return visitor.visitChildren(self)




    def deriveDefinition(self):

        localctx = PiettoParser.DeriveDefinitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 42, self.RULE_deriveDefinition)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 292
            self.match(PiettoParser.DERIVE)
            self.state = 293
            self.match(PiettoParser.IDENTIFIER)
            self.state = 294
            self.match(PiettoParser.LPAREN)
            self.state = 296
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==45:
                self.state = 295
                self.parameterList()


            self.state = 298
            self.match(PiettoParser.RPAREN)
            self.state = 299
            self.match(PiettoParser.ARROW)
            self.state = 300
            self.typeExpression()
            self.state = 301
            self.match(PiettoParser.COLON)
            self.state = 302
            self.match(PiettoParser.NEWLINE)
            self.state = 306
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==46:
                self.state = 303
                self.match(PiettoParser.NEWLINE)
                self.state = 308
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 309
            self.match(PiettoParser.INDENT)
            self.state = 310
            self.deriveBody()
            self.state = 311
            self.match(PiettoParser.DEDENT)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DeriveBodyContext(ParserRuleContext):
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
            return PiettoParser.RULE_deriveBody

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDeriveBody" ):
                return visitor.visitDeriveBody(self)
            else:
                return visitor.visitChildren(self)




    def deriveBody(self):

        localctx = PiettoParser.DeriveBodyContext(self, self._ctx, self.state)
        self.enterRule(localctx, 44, self.RULE_deriveBody)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 316
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==46:
                self.state = 313
                self.match(PiettoParser.NEWLINE)
                self.state = 318
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 319
            self.expression()
            self.state = 320
            self.match(PiettoParser.NEWLINE)
            self.state = 324
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==46:
                self.state = 321
                self.match(PiettoParser.NEWLINE)
                self.state = 326
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
        self.enterRule(localctx, 46, self.RULE_expression)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 327
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
        self.enterRule(localctx, 48, self.RULE_orExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 329
            self.andExpression()
            self.state = 334
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==14:
                self.state = 330
                self.match(PiettoParser.OR)
                self.state = 331
                self.andExpression()
                self.state = 336
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
        self.enterRule(localctx, 50, self.RULE_andExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 337
            self.comparisonExpression()
            self.state = 342
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==13:
                self.state = 338
                self.match(PiettoParser.AND)
                self.state = 339
                self.comparisonExpression()
                self.state = 344
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
        self.enterRule(localctx, 52, self.RULE_comparisonExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 345
            self.additiveExpression()
            self.state = 359
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [19, 22, 23, 24, 25, 26, 27]:
                self.state = 346
                self.comparisonOperator()
                self.state = 347
                self.additiveExpression()
                pass
            elif token in [18]:
                self.state = 349
                self.match(PiettoParser.BETWEEN)
                self.state = 350
                self.additiveExpression()
                self.state = 351
                self.match(PiettoParser.AND)
                self.state = 352
                self.additiveExpression()
                pass
            elif token in [15]:
                self.state = 354
                self.match(PiettoParser.IS)
                self.state = 356
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==16:
                    self.state = 355
                    self.match(PiettoParser.NOT)


                self.state = 358
                self.match(PiettoParser.NULL)
                pass
            elif token in [13, 14, 37, 38, 46]:
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
        self.enterRule(localctx, 54, self.RULE_comparisonOperator)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 361
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 264765440) != 0)):
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
        self.enterRule(localctx, 56, self.RULE_additiveExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 363
            self.multiplicativeExpression()
            self.state = 368
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==30 or _la==31:
                self.state = 364
                _la = self._input.LA(1)
                if not(_la==30 or _la==31):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 365
                self.multiplicativeExpression()
                self.state = 370
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
        self.enterRule(localctx, 58, self.RULE_multiplicativeExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 371
            self.unaryExpression()
            self.state = 376
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 30064771072) != 0):
                self.state = 372
                _la = self._input.LA(1)
                if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 30064771072) != 0)):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 373
                self.unaryExpression()
                self.state = 378
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
        self.enterRule(localctx, 60, self.RULE_unaryExpression)
        self._la = 0 # Token type
        try:
            self.state = 382
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [30, 31]:
                self.enterOuterAlt(localctx, 1)
                self.state = 379
                _la = self._input.LA(1)
                if not(_la==30 or _la==31):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 380
                self.unaryExpression()
                pass
            elif token in [17, 20, 21, 36, 43, 44, 45]:
                self.enterOuterAlt(localctx, 2)
                self.state = 381
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
        self.enterRule(localctx, 62, self.RULE_primaryExpression)
        self._la = 0 # Token type
        try:
            self.state = 393
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [17, 20, 21, 43, 44]:
                self.enterOuterAlt(localctx, 1)
                self.state = 384
                self.literal()
                pass
            elif token in [45]:
                self.enterOuterAlt(localctx, 2)
                self.state = 385
                self.dottedName()
                self.state = 387
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==36:
                    self.state = 386
                    self.callSuffix()


                pass
            elif token in [36]:
                self.enterOuterAlt(localctx, 3)
                self.state = 389
                self.match(PiettoParser.LPAREN)
                self.state = 390
                self.expression()
                self.state = 391
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
        self.enterRule(localctx, 64, self.RULE_dottedName)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 395
            self.match(PiettoParser.IDENTIFIER)
            self.state = 400
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==39:
                self.state = 396
                self.match(PiettoParser.DOT)
                self.state = 397
                self.match(PiettoParser.IDENTIFIER)
                self.state = 402
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
        self.enterRule(localctx, 66, self.RULE_callSuffix)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 403
            self.match(PiettoParser.LPAREN)
            self.state = 415
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 61644595134464) != 0):
                self.state = 404
                self.expression()
                self.state = 409
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,46,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 405
                        self.match(PiettoParser.COMMA)
                        self.state = 406
                        self.expression() 
                    self.state = 411
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,46,self._ctx)

                self.state = 413
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==38:
                    self.state = 412
                    self.match(PiettoParser.COMMA)




            self.state = 417
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
        self.enterRule(localctx, 68, self.RULE_literal)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 419
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 26388282343424) != 0)):
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





