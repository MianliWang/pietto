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
        4,1,54,544,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,2,31,7,31,2,32,7,32,2,33,
        7,33,2,34,7,34,2,35,7,35,2,36,7,36,2,37,7,37,2,38,7,38,2,39,7,39,
        2,40,7,40,2,41,7,41,2,42,7,42,2,43,7,43,2,44,7,44,2,45,7,45,2,46,
        7,46,2,47,7,47,1,0,5,0,98,8,0,10,0,12,0,101,9,0,1,0,3,0,104,8,0,
        1,0,5,0,107,8,0,10,0,12,0,110,9,0,1,0,1,0,5,0,114,8,0,10,0,12,0,
        117,9,0,5,0,119,8,0,10,0,12,0,122,9,0,1,0,1,0,1,1,1,1,3,1,128,8,
        1,1,1,3,1,131,8,1,1,1,3,1,134,8,1,1,1,1,1,3,1,138,8,1,1,1,3,1,141,
        8,1,1,1,1,1,3,1,145,8,1,1,1,3,1,148,8,1,1,2,1,2,1,2,1,2,1,3,1,3,
        1,3,1,3,1,4,1,4,1,4,1,4,1,5,1,5,1,5,1,5,1,6,1,6,1,6,1,6,1,6,3,6,
        171,8,6,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,
        1,7,1,7,1,7,1,7,1,7,1,7,1,7,5,7,194,8,7,10,7,12,7,197,9,7,1,7,1,
        7,1,7,1,7,3,7,203,8,7,1,8,1,8,4,8,207,8,8,11,8,12,8,208,1,9,1,9,
        1,9,1,9,1,10,1,10,3,10,217,8,10,1,11,1,11,3,11,221,8,11,1,12,1,12,
        1,12,3,12,226,8,12,1,13,1,13,1,13,1,13,5,13,232,8,13,10,13,12,13,
        235,9,13,1,13,3,13,238,8,13,3,13,240,8,13,1,13,1,13,1,14,1,14,1,
        14,1,14,1,14,3,14,249,8,14,1,15,1,15,1,16,1,16,1,16,1,16,1,16,5,
        16,258,8,16,10,16,12,16,261,9,16,1,16,1,16,1,16,1,16,1,17,1,17,4,
        17,269,8,17,11,17,12,17,270,1,18,1,18,1,18,1,19,1,19,1,19,1,19,3,
        19,280,8,19,1,19,1,19,1,19,1,19,1,19,1,19,5,19,288,8,19,10,19,12,
        19,291,9,19,1,19,1,19,1,19,1,19,1,20,1,20,1,20,5,20,300,8,20,10,
        20,12,20,303,9,20,1,20,3,20,306,8,20,1,21,1,21,1,21,1,21,1,22,5,
        22,313,8,22,10,22,12,22,316,9,22,1,22,1,22,1,22,5,22,321,8,22,10,
        22,12,22,324,9,22,1,23,1,23,1,23,1,23,3,23,330,8,23,1,23,1,23,1,
        23,1,23,1,23,1,23,5,23,338,8,23,10,23,12,23,341,9,23,1,23,1,23,1,
        23,1,23,1,24,5,24,348,8,24,10,24,12,24,351,9,24,1,24,1,24,1,24,5,
        24,356,8,24,10,24,12,24,359,9,24,1,25,1,25,1,25,1,25,1,25,5,25,366,
        8,25,10,25,12,25,369,9,25,1,25,1,25,1,25,1,25,1,26,5,26,376,8,26,
        10,26,12,26,379,9,26,1,26,1,26,1,26,5,26,384,8,26,10,26,12,26,387,
        9,26,1,27,1,27,3,27,391,8,27,1,28,1,28,1,28,1,28,3,28,397,8,28,1,
        28,5,28,400,8,28,10,28,12,28,403,9,28,1,28,1,28,1,29,1,29,1,29,1,
        30,1,30,3,30,412,8,30,1,31,1,31,1,31,1,32,1,32,1,32,1,33,1,33,1,
        33,1,33,1,33,5,33,425,8,33,10,33,12,33,428,9,33,1,33,1,33,1,33,1,
        33,1,34,5,34,435,8,34,10,34,12,34,438,9,34,1,34,1,34,1,34,5,34,443,
        8,34,10,34,12,34,446,9,34,1,35,1,35,1,36,1,36,1,36,5,36,453,8,36,
        10,36,12,36,456,9,36,1,37,1,37,1,37,5,37,461,8,37,10,37,12,37,464,
        9,37,1,38,1,38,1,38,1,38,1,38,1,38,1,38,1,38,1,38,1,38,1,38,3,38,
        477,8,38,1,38,3,38,480,8,38,1,39,1,39,1,40,1,40,1,40,5,40,487,8,
        40,10,40,12,40,490,9,40,1,41,1,41,1,41,5,41,495,8,41,10,41,12,41,
        498,9,41,1,42,1,42,1,42,3,42,503,8,42,1,43,1,43,1,43,3,43,508,8,
        43,1,43,1,43,1,43,1,43,3,43,514,8,43,1,44,1,44,1,44,5,44,519,8,44,
        10,44,12,44,522,9,44,1,45,1,45,1,46,1,46,1,46,1,46,5,46,530,8,46,
        10,46,12,46,533,9,46,1,46,3,46,536,8,46,3,46,538,8,46,1,46,1,46,
        1,47,1,47,1,47,0,0,48,0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,
        32,34,36,38,40,42,44,46,48,50,52,54,56,58,60,62,64,66,68,70,72,74,
        76,78,80,82,84,86,88,90,92,94,0,7,1,0,5,7,2,0,4,4,48,48,2,0,22,22,
        25,30,1,0,33,34,1,0,35,37,2,0,13,13,48,48,3,0,20,20,23,24,46,47,
        565,0,99,1,0,0,0,2,147,1,0,0,0,4,149,1,0,0,0,6,153,1,0,0,0,8,157,
        1,0,0,0,10,161,1,0,0,0,12,170,1,0,0,0,14,202,1,0,0,0,16,206,1,0,
        0,0,18,210,1,0,0,0,20,214,1,0,0,0,22,218,1,0,0,0,24,225,1,0,0,0,
        26,227,1,0,0,0,28,248,1,0,0,0,30,250,1,0,0,0,32,252,1,0,0,0,34,268,
        1,0,0,0,36,272,1,0,0,0,38,275,1,0,0,0,40,296,1,0,0,0,42,307,1,0,
        0,0,44,314,1,0,0,0,46,325,1,0,0,0,48,349,1,0,0,0,50,360,1,0,0,0,
        52,377,1,0,0,0,54,390,1,0,0,0,56,392,1,0,0,0,58,406,1,0,0,0,60,411,
        1,0,0,0,62,413,1,0,0,0,64,416,1,0,0,0,66,419,1,0,0,0,68,436,1,0,
        0,0,70,447,1,0,0,0,72,449,1,0,0,0,74,457,1,0,0,0,76,465,1,0,0,0,
        78,481,1,0,0,0,80,483,1,0,0,0,82,491,1,0,0,0,84,502,1,0,0,0,86,513,
        1,0,0,0,88,515,1,0,0,0,90,523,1,0,0,0,92,525,1,0,0,0,94,541,1,0,
        0,0,96,98,5,49,0,0,97,96,1,0,0,0,98,101,1,0,0,0,99,97,1,0,0,0,99,
        100,1,0,0,0,100,103,1,0,0,0,101,99,1,0,0,0,102,104,3,2,1,0,103,102,
        1,0,0,0,103,104,1,0,0,0,104,108,1,0,0,0,105,107,5,49,0,0,106,105,
        1,0,0,0,107,110,1,0,0,0,108,106,1,0,0,0,108,109,1,0,0,0,109,120,
        1,0,0,0,110,108,1,0,0,0,111,115,3,12,6,0,112,114,5,49,0,0,113,112,
        1,0,0,0,114,117,1,0,0,0,115,113,1,0,0,0,115,116,1,0,0,0,116,119,
        1,0,0,0,117,115,1,0,0,0,118,111,1,0,0,0,119,122,1,0,0,0,120,118,
        1,0,0,0,120,121,1,0,0,0,121,123,1,0,0,0,122,120,1,0,0,0,123,124,
        5,0,0,1,124,1,1,0,0,0,125,127,3,4,2,0,126,128,3,6,3,0,127,126,1,
        0,0,0,127,128,1,0,0,0,128,130,1,0,0,0,129,131,3,8,4,0,130,129,1,
        0,0,0,130,131,1,0,0,0,131,133,1,0,0,0,132,134,3,10,5,0,133,132,1,
        0,0,0,133,134,1,0,0,0,134,148,1,0,0,0,135,137,3,6,3,0,136,138,3,
        8,4,0,137,136,1,0,0,0,137,138,1,0,0,0,138,140,1,0,0,0,139,141,3,
        10,5,0,140,139,1,0,0,0,140,141,1,0,0,0,141,148,1,0,0,0,142,144,3,
        8,4,0,143,145,3,10,5,0,144,143,1,0,0,0,144,145,1,0,0,0,145,148,1,
        0,0,0,146,148,3,10,5,0,147,125,1,0,0,0,147,135,1,0,0,0,147,142,1,
        0,0,0,147,146,1,0,0,0,148,3,1,0,0,0,149,150,5,1,0,0,150,151,5,46,
        0,0,151,152,5,49,0,0,152,5,1,0,0,0,153,154,5,2,0,0,154,155,7,0,0,
        0,155,156,5,49,0,0,156,7,1,0,0,0,157,158,5,3,0,0,158,159,5,48,0,
        0,159,160,5,49,0,0,160,9,1,0,0,0,161,162,5,4,0,0,162,163,5,48,0,
        0,163,164,5,49,0,0,164,11,1,0,0,0,165,171,3,14,7,0,166,171,3,32,
        16,0,167,171,3,38,19,0,168,171,3,46,23,0,169,171,3,50,25,0,170,165,
        1,0,0,0,170,166,1,0,0,0,170,167,1,0,0,0,170,168,1,0,0,0,170,169,
        1,0,0,0,171,13,1,0,0,0,172,173,5,8,0,0,173,174,5,48,0,0,174,175,
        5,31,0,0,175,176,3,20,10,0,176,177,5,49,0,0,177,203,1,0,0,0,178,
        179,5,8,0,0,179,180,5,48,0,0,180,181,5,31,0,0,181,182,3,20,10,0,
        182,183,5,14,0,0,183,184,3,70,35,0,184,185,5,49,0,0,185,203,1,0,
        0,0,186,187,5,8,0,0,187,188,5,48,0,0,188,189,5,31,0,0,189,190,3,
        20,10,0,190,191,5,43,0,0,191,195,5,49,0,0,192,194,5,49,0,0,193,192,
        1,0,0,0,194,197,1,0,0,0,195,193,1,0,0,0,195,196,1,0,0,0,196,198,
        1,0,0,0,197,195,1,0,0,0,198,199,5,53,0,0,199,200,3,16,8,0,200,201,
        5,54,0,0,201,203,1,0,0,0,202,172,1,0,0,0,202,178,1,0,0,0,202,186,
        1,0,0,0,203,15,1,0,0,0,204,207,3,18,9,0,205,207,5,49,0,0,206,204,
        1,0,0,0,206,205,1,0,0,0,207,208,1,0,0,0,208,206,1,0,0,0,208,209,
        1,0,0,0,209,17,1,0,0,0,210,211,5,14,0,0,211,212,3,70,35,0,212,213,
        5,49,0,0,213,19,1,0,0,0,214,216,3,22,11,0,215,217,3,24,12,0,216,
        215,1,0,0,0,216,217,1,0,0,0,217,21,1,0,0,0,218,220,5,48,0,0,219,
        221,3,26,13,0,220,219,1,0,0,0,220,221,1,0,0,0,221,23,1,0,0,0,222,
        226,5,15,0,0,223,224,5,19,0,0,224,226,5,20,0,0,225,222,1,0,0,0,225,
        223,1,0,0,0,226,25,1,0,0,0,227,239,5,39,0,0,228,233,3,28,14,0,229,
        230,5,41,0,0,230,232,3,28,14,0,231,229,1,0,0,0,232,235,1,0,0,0,233,
        231,1,0,0,0,233,234,1,0,0,0,234,237,1,0,0,0,235,233,1,0,0,0,236,
        238,5,41,0,0,237,236,1,0,0,0,237,238,1,0,0,0,238,240,1,0,0,0,239,
        228,1,0,0,0,239,240,1,0,0,0,240,241,1,0,0,0,241,242,5,40,0,0,242,
        27,1,0,0,0,243,244,3,30,15,0,244,245,5,31,0,0,245,246,3,70,35,0,
        246,249,1,0,0,0,247,249,3,70,35,0,248,243,1,0,0,0,248,247,1,0,0,
        0,249,29,1,0,0,0,250,251,7,1,0,0,251,31,1,0,0,0,252,253,5,9,0,0,
        253,254,5,48,0,0,254,255,5,43,0,0,255,259,5,49,0,0,256,258,5,49,
        0,0,257,256,1,0,0,0,258,261,1,0,0,0,259,257,1,0,0,0,259,260,1,0,
        0,0,260,262,1,0,0,0,261,259,1,0,0,0,262,263,5,53,0,0,263,264,3,34,
        17,0,264,265,5,54,0,0,265,33,1,0,0,0,266,269,3,36,18,0,267,269,5,
        49,0,0,268,266,1,0,0,0,268,267,1,0,0,0,269,270,1,0,0,0,270,268,1,
        0,0,0,270,271,1,0,0,0,271,35,1,0,0,0,272,273,5,48,0,0,273,274,5,
        49,0,0,274,37,1,0,0,0,275,276,5,10,0,0,276,277,5,48,0,0,277,279,
        5,39,0,0,278,280,3,40,20,0,279,278,1,0,0,0,279,280,1,0,0,0,280,281,
        1,0,0,0,281,282,5,40,0,0,282,283,5,32,0,0,283,284,3,20,10,0,284,
        285,5,43,0,0,285,289,5,49,0,0,286,288,5,49,0,0,287,286,1,0,0,0,288,
        291,1,0,0,0,289,287,1,0,0,0,289,290,1,0,0,0,290,292,1,0,0,0,291,
        289,1,0,0,0,292,293,5,53,0,0,293,294,3,44,22,0,294,295,5,54,0,0,
        295,39,1,0,0,0,296,301,3,42,21,0,297,298,5,41,0,0,298,300,3,42,21,
        0,299,297,1,0,0,0,300,303,1,0,0,0,301,299,1,0,0,0,301,302,1,0,0,
        0,302,305,1,0,0,0,303,301,1,0,0,0,304,306,5,41,0,0,305,304,1,0,0,
        0,305,306,1,0,0,0,306,41,1,0,0,0,307,308,5,48,0,0,308,309,5,43,0,
        0,309,310,3,20,10,0,310,43,1,0,0,0,311,313,5,49,0,0,312,311,1,0,
        0,0,313,316,1,0,0,0,314,312,1,0,0,0,314,315,1,0,0,0,315,317,1,0,
        0,0,316,314,1,0,0,0,317,318,3,70,35,0,318,322,5,49,0,0,319,321,5,
        49,0,0,320,319,1,0,0,0,321,324,1,0,0,0,322,320,1,0,0,0,322,323,1,
        0,0,0,323,45,1,0,0,0,324,322,1,0,0,0,325,326,5,11,0,0,326,327,5,
        48,0,0,327,329,5,39,0,0,328,330,3,40,20,0,329,328,1,0,0,0,329,330,
        1,0,0,0,330,331,1,0,0,0,331,332,5,40,0,0,332,333,5,32,0,0,333,334,
        3,20,10,0,334,335,5,43,0,0,335,339,5,49,0,0,336,338,5,49,0,0,337,
        336,1,0,0,0,338,341,1,0,0,0,339,337,1,0,0,0,339,340,1,0,0,0,340,
        342,1,0,0,0,341,339,1,0,0,0,342,343,5,53,0,0,343,344,3,48,24,0,344,
        345,5,54,0,0,345,47,1,0,0,0,346,348,5,49,0,0,347,346,1,0,0,0,348,
        351,1,0,0,0,349,347,1,0,0,0,349,350,1,0,0,0,350,352,1,0,0,0,351,
        349,1,0,0,0,352,353,3,70,35,0,353,357,5,49,0,0,354,356,5,49,0,0,
        355,354,1,0,0,0,356,359,1,0,0,0,357,355,1,0,0,0,357,358,1,0,0,0,
        358,49,1,0,0,0,359,357,1,0,0,0,360,361,5,12,0,0,361,362,5,48,0,0,
        362,363,5,43,0,0,363,367,5,49,0,0,364,366,5,49,0,0,365,364,1,0,0,
        0,366,369,1,0,0,0,367,365,1,0,0,0,367,368,1,0,0,0,368,370,1,0,0,
        0,369,367,1,0,0,0,370,371,5,53,0,0,371,372,3,52,26,0,372,373,5,54,
        0,0,373,51,1,0,0,0,374,376,5,49,0,0,375,374,1,0,0,0,376,379,1,0,
        0,0,377,375,1,0,0,0,377,378,1,0,0,0,378,380,1,0,0,0,379,377,1,0,
        0,0,380,385,3,54,27,0,381,384,3,54,27,0,382,384,5,49,0,0,383,381,
        1,0,0,0,383,382,1,0,0,0,384,387,1,0,0,0,385,383,1,0,0,0,385,386,
        1,0,0,0,386,53,1,0,0,0,387,385,1,0,0,0,388,391,3,56,28,0,389,391,
        3,66,33,0,390,388,1,0,0,0,390,389,1,0,0,0,391,55,1,0,0,0,392,393,
        5,48,0,0,393,394,5,43,0,0,394,396,3,20,10,0,395,397,3,58,29,0,396,
        395,1,0,0,0,396,397,1,0,0,0,397,401,1,0,0,0,398,400,3,60,30,0,399,
        398,1,0,0,0,400,403,1,0,0,0,401,399,1,0,0,0,401,402,1,0,0,0,402,
        404,1,0,0,0,403,401,1,0,0,0,404,405,5,49,0,0,405,57,1,0,0,0,406,
        407,5,11,0,0,407,408,3,70,35,0,408,59,1,0,0,0,409,412,3,62,31,0,
        410,412,3,64,32,0,411,409,1,0,0,0,411,410,1,0,0,0,412,61,1,0,0,0,
        413,414,5,38,0,0,414,415,5,48,0,0,415,63,1,0,0,0,416,417,5,14,0,
        0,417,418,3,70,35,0,418,65,1,0,0,0,419,420,5,13,0,0,420,421,5,48,
        0,0,421,422,5,43,0,0,422,426,5,49,0,0,423,425,5,49,0,0,424,423,1,
        0,0,0,425,428,1,0,0,0,426,424,1,0,0,0,426,427,1,0,0,0,427,429,1,
        0,0,0,428,426,1,0,0,0,429,430,5,53,0,0,430,431,3,68,34,0,431,432,
        5,54,0,0,432,67,1,0,0,0,433,435,5,49,0,0,434,433,1,0,0,0,435,438,
        1,0,0,0,436,434,1,0,0,0,436,437,1,0,0,0,437,439,1,0,0,0,438,436,
        1,0,0,0,439,440,3,70,35,0,440,444,5,49,0,0,441,443,5,49,0,0,442,
        441,1,0,0,0,443,446,1,0,0,0,444,442,1,0,0,0,444,445,1,0,0,0,445,
        69,1,0,0,0,446,444,1,0,0,0,447,448,3,72,36,0,448,71,1,0,0,0,449,
        454,3,74,37,0,450,451,5,17,0,0,451,453,3,74,37,0,452,450,1,0,0,0,
        453,456,1,0,0,0,454,452,1,0,0,0,454,455,1,0,0,0,455,73,1,0,0,0,456,
        454,1,0,0,0,457,462,3,76,38,0,458,459,5,16,0,0,459,461,3,76,38,0,
        460,458,1,0,0,0,461,464,1,0,0,0,462,460,1,0,0,0,462,463,1,0,0,0,
        463,75,1,0,0,0,464,462,1,0,0,0,465,479,3,80,40,0,466,467,3,78,39,
        0,467,468,3,80,40,0,468,480,1,0,0,0,469,470,5,21,0,0,470,471,3,80,
        40,0,471,472,5,16,0,0,472,473,3,80,40,0,473,480,1,0,0,0,474,476,
        5,18,0,0,475,477,5,19,0,0,476,475,1,0,0,0,476,477,1,0,0,0,477,478,
        1,0,0,0,478,480,5,20,0,0,479,466,1,0,0,0,479,469,1,0,0,0,479,474,
        1,0,0,0,479,480,1,0,0,0,480,77,1,0,0,0,481,482,7,2,0,0,482,79,1,
        0,0,0,483,488,3,82,41,0,484,485,7,3,0,0,485,487,3,82,41,0,486,484,
        1,0,0,0,487,490,1,0,0,0,488,486,1,0,0,0,488,489,1,0,0,0,489,81,1,
        0,0,0,490,488,1,0,0,0,491,496,3,84,42,0,492,493,7,4,0,0,493,495,
        3,84,42,0,494,492,1,0,0,0,495,498,1,0,0,0,496,494,1,0,0,0,496,497,
        1,0,0,0,497,83,1,0,0,0,498,496,1,0,0,0,499,500,7,3,0,0,500,503,3,
        84,42,0,501,503,3,86,43,0,502,499,1,0,0,0,502,501,1,0,0,0,503,85,
        1,0,0,0,504,514,3,94,47,0,505,507,3,88,44,0,506,508,3,92,46,0,507,
        506,1,0,0,0,507,508,1,0,0,0,508,514,1,0,0,0,509,510,5,39,0,0,510,
        511,3,70,35,0,511,512,5,40,0,0,512,514,1,0,0,0,513,504,1,0,0,0,513,
        505,1,0,0,0,513,509,1,0,0,0,514,87,1,0,0,0,515,520,3,90,45,0,516,
        517,5,42,0,0,517,519,3,90,45,0,518,516,1,0,0,0,519,522,1,0,0,0,520,
        518,1,0,0,0,520,521,1,0,0,0,521,89,1,0,0,0,522,520,1,0,0,0,523,524,
        7,5,0,0,524,91,1,0,0,0,525,537,5,39,0,0,526,531,3,70,35,0,527,528,
        5,41,0,0,528,530,3,70,35,0,529,527,1,0,0,0,530,533,1,0,0,0,531,529,
        1,0,0,0,531,532,1,0,0,0,532,535,1,0,0,0,533,531,1,0,0,0,534,536,
        5,41,0,0,535,534,1,0,0,0,535,536,1,0,0,0,536,538,1,0,0,0,537,526,
        1,0,0,0,537,538,1,0,0,0,538,539,1,0,0,0,539,540,5,40,0,0,540,93,
        1,0,0,0,541,542,7,6,0,0,542,95,1,0,0,0,61,99,103,108,115,120,127,
        130,133,137,140,144,147,170,195,202,206,208,216,220,225,233,237,
        239,248,259,268,270,279,289,301,305,314,322,329,339,349,357,367,
        377,383,385,390,396,401,411,426,436,444,454,462,476,479,488,496,
        502,507,513,520,531,535,537
    ]

class PiettoParser ( Parser ):

    grammarFileName = "Pietto.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'pietto'", "'mode'", "'dialect'", "'encoding'", 
                     "'loose'", "'checked'", "'strict'", "'type'", "'enum'", 
                     "'constraint'", "'derive'", "'shape'", "'check'", "'ensure'", 
                     "'nullable'", "'and'", "'or'", "'is'", "'not'", "'null'", 
                     "'between'", "'like'", "'true'", "'false'", "'=='", 
                     "'!='", "'<='", "'>='", "'<'", "'>'", "'='", "'->'", 
                     "'+'", "'-'", "'*'", "'/'", "'%'", "'@'", "'('", "')'", 
                     "','", "'.'", "':'", "'{'", "'}'" ]

    symbolicNames = [ "<INVALID>", "PIETTO", "MODE", "DIALECT", "ENCODING", 
                      "LOOSE", "CHECKED", "STRICT", "TYPE", "ENUM", "CONSTRAINT", 
                      "DERIVE", "SHAPE", "CHECK", "ENSURE", "NULLABLE", 
                      "AND", "OR", "IS", "NOT", "NULL", "BETWEEN", "LIKE", 
                      "TRUE", "FALSE", "EQ", "NE", "LE", "GE", "LT", "GT", 
                      "ASSIGN", "ARROW", "PLUS", "MINUS", "STAR", "SLASH", 
                      "PERCENT", "AT", "LPAREN", "RPAREN", "COMMA", "DOT", 
                      "COLON", "LBRACE", "RBRACE", "NUMBER", "STRING", "IDENTIFIER", 
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
    RULE_typeReference = 11
    RULE_nullabilityModifier = 12
    RULE_typeArguments = 13
    RULE_typeArgument = 14
    RULE_typeArgumentName = 15
    RULE_enumDefinition = 16
    RULE_enumBody = 17
    RULE_enumItem = 18
    RULE_constraintDefinition = 19
    RULE_parameterList = 20
    RULE_parameter = 21
    RULE_constraintBody = 22
    RULE_deriveDefinition = 23
    RULE_deriveBody = 24
    RULE_shapeDefinition = 25
    RULE_shapeBody = 26
    RULE_shapeItem = 27
    RULE_fieldDefinition = 28
    RULE_fieldDeriveClause = 29
    RULE_fieldModifier = 30
    RULE_annotation = 31
    RULE_fieldEnsureClause = 32
    RULE_checkDefinition = 33
    RULE_checkBody = 34
    RULE_expression = 35
    RULE_orExpression = 36
    RULE_andExpression = 37
    RULE_comparisonExpression = 38
    RULE_comparisonOperator = 39
    RULE_additiveExpression = 40
    RULE_multiplicativeExpression = 41
    RULE_unaryExpression = 42
    RULE_primaryExpression = 43
    RULE_dottedName = 44
    RULE_namePart = 45
    RULE_callSuffix = 46
    RULE_literal = 47

    ruleNames =  [ "script", "header", "versionDecl", "modeDecl", "dialectDecl", 
                   "encodingDecl", "definition", "typeDefinition", "typeBody", 
                   "ensureClause", "typeExpression", "typeReference", "nullabilityModifier", 
                   "typeArguments", "typeArgument", "typeArgumentName", 
                   "enumDefinition", "enumBody", "enumItem", "constraintDefinition", 
                   "parameterList", "parameter", "constraintBody", "deriveDefinition", 
                   "deriveBody", "shapeDefinition", "shapeBody", "shapeItem", 
                   "fieldDefinition", "fieldDeriveClause", "fieldModifier", 
                   "annotation", "fieldEnsureClause", "checkDefinition", 
                   "checkBody", "expression", "orExpression", "andExpression", 
                   "comparisonExpression", "comparisonOperator", "additiveExpression", 
                   "multiplicativeExpression", "unaryExpression", "primaryExpression", 
                   "dottedName", "namePart", "callSuffix", "literal" ]

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
    SHAPE=12
    CHECK=13
    ENSURE=14
    NULLABLE=15
    AND=16
    OR=17
    IS=18
    NOT=19
    NULL=20
    BETWEEN=21
    LIKE=22
    TRUE=23
    FALSE=24
    EQ=25
    NE=26
    LE=27
    GE=28
    LT=29
    GT=30
    ASSIGN=31
    ARROW=32
    PLUS=33
    MINUS=34
    STAR=35
    SLASH=36
    PERCENT=37
    AT=38
    LPAREN=39
    RPAREN=40
    COMMA=41
    DOT=42
    COLON=43
    LBRACE=44
    RBRACE=45
    NUMBER=46
    STRING=47
    IDENTIFIER=48
    NEWLINE=49
    COMMENT=50
    WS=51
    UNKNOWN=52
    INDENT=53
    DEDENT=54

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
            self.state = 99
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,0,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 96
                    self.match(PiettoParser.NEWLINE) 
                self.state = 101
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,0,self._ctx)

            self.state = 103
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 30) != 0):
                self.state = 102
                self.header()


            self.state = 108
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==49:
                self.state = 105
                self.match(PiettoParser.NEWLINE)
                self.state = 110
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 120
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 7936) != 0):
                self.state = 111
                self.definition()
                self.state = 115
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==49:
                    self.state = 112
                    self.match(PiettoParser.NEWLINE)
                    self.state = 117
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 122
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 123
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
            self.state = 147
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [1]:
                self.enterOuterAlt(localctx, 1)
                self.state = 125
                self.versionDecl()
                self.state = 127
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==2:
                    self.state = 126
                    self.modeDecl()


                self.state = 130
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==3:
                    self.state = 129
                    self.dialectDecl()


                self.state = 133
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4:
                    self.state = 132
                    self.encodingDecl()


                pass
            elif token in [2]:
                self.enterOuterAlt(localctx, 2)
                self.state = 135
                self.modeDecl()
                self.state = 137
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==3:
                    self.state = 136
                    self.dialectDecl()


                self.state = 140
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4:
                    self.state = 139
                    self.encodingDecl()


                pass
            elif token in [3]:
                self.enterOuterAlt(localctx, 3)
                self.state = 142
                self.dialectDecl()
                self.state = 144
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4:
                    self.state = 143
                    self.encodingDecl()


                pass
            elif token in [4]:
                self.enterOuterAlt(localctx, 4)
                self.state = 146
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
            self.state = 149
            self.match(PiettoParser.PIETTO)
            self.state = 150
            self.match(PiettoParser.NUMBER)
            self.state = 151
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
            self.state = 153
            self.match(PiettoParser.MODE)
            self.state = 154
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 224) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 155
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
            self.state = 157
            self.match(PiettoParser.DIALECT)
            self.state = 158
            self.match(PiettoParser.IDENTIFIER)
            self.state = 159
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
            self.state = 161
            self.match(PiettoParser.ENCODING)
            self.state = 162
            self.match(PiettoParser.IDENTIFIER)
            self.state = 163
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


        def shapeDefinition(self):
            return self.getTypedRuleContext(PiettoParser.ShapeDefinitionContext,0)


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
            self.state = 170
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [8]:
                self.enterOuterAlt(localctx, 1)
                self.state = 165
                self.typeDefinition()
                pass
            elif token in [9]:
                self.enterOuterAlt(localctx, 2)
                self.state = 166
                self.enumDefinition()
                pass
            elif token in [10]:
                self.enterOuterAlt(localctx, 3)
                self.state = 167
                self.constraintDefinition()
                pass
            elif token in [11]:
                self.enterOuterAlt(localctx, 4)
                self.state = 168
                self.deriveDefinition()
                pass
            elif token in [12]:
                self.enterOuterAlt(localctx, 5)
                self.state = 169
                self.shapeDefinition()
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
            self.state = 202
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,14,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 172
                self.match(PiettoParser.TYPE)
                self.state = 173
                self.match(PiettoParser.IDENTIFIER)
                self.state = 174
                self.match(PiettoParser.ASSIGN)
                self.state = 175
                self.typeExpression()
                self.state = 176
                self.match(PiettoParser.NEWLINE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 178
                self.match(PiettoParser.TYPE)
                self.state = 179
                self.match(PiettoParser.IDENTIFIER)
                self.state = 180
                self.match(PiettoParser.ASSIGN)
                self.state = 181
                self.typeExpression()
                self.state = 182
                self.match(PiettoParser.ENSURE)
                self.state = 183
                self.expression()
                self.state = 184
                self.match(PiettoParser.NEWLINE)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 186
                self.match(PiettoParser.TYPE)
                self.state = 187
                self.match(PiettoParser.IDENTIFIER)
                self.state = 188
                self.match(PiettoParser.ASSIGN)
                self.state = 189
                self.typeExpression()
                self.state = 190
                self.match(PiettoParser.COLON)
                self.state = 191
                self.match(PiettoParser.NEWLINE)
                self.state = 195
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==49:
                    self.state = 192
                    self.match(PiettoParser.NEWLINE)
                    self.state = 197
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 198
                self.match(PiettoParser.INDENT)
                self.state = 199
                self.typeBody()
                self.state = 200
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
            self.state = 206 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 206
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [14]:
                    self.state = 204
                    self.ensureClause()
                    pass
                elif token in [49]:
                    self.state = 205
                    self.match(PiettoParser.NEWLINE)
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 208 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==14 or _la==49):
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
            self.state = 210
            self.match(PiettoParser.ENSURE)
            self.state = 211
            self.expression()
            self.state = 212
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

        def typeReference(self):
            return self.getTypedRuleContext(PiettoParser.TypeReferenceContext,0)


        def nullabilityModifier(self):
            return self.getTypedRuleContext(PiettoParser.NullabilityModifierContext,0)


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
            self.state = 214
            self.typeReference()
            self.state = 216
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==15 or _la==19:
                self.state = 215
                self.nullabilityModifier()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TypeReferenceContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENTIFIER(self):
            return self.getToken(PiettoParser.IDENTIFIER, 0)

        def typeArguments(self):
            return self.getTypedRuleContext(PiettoParser.TypeArgumentsContext,0)


        def getRuleIndex(self):
            return PiettoParser.RULE_typeReference

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTypeReference" ):
                return visitor.visitTypeReference(self)
            else:
                return visitor.visitChildren(self)




    def typeReference(self):

        localctx = PiettoParser.TypeReferenceContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_typeReference)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 218
            self.match(PiettoParser.IDENTIFIER)
            self.state = 220
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==39:
                self.state = 219
                self.typeArguments()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class NullabilityModifierContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NULLABLE(self):
            return self.getToken(PiettoParser.NULLABLE, 0)

        def NOT(self):
            return self.getToken(PiettoParser.NOT, 0)

        def NULL(self):
            return self.getToken(PiettoParser.NULL, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_nullabilityModifier

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNullabilityModifier" ):
                return visitor.visitNullabilityModifier(self)
            else:
                return visitor.visitChildren(self)




    def nullabilityModifier(self):

        localctx = PiettoParser.NullabilityModifierContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_nullabilityModifier)
        try:
            self.state = 225
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [15]:
                self.enterOuterAlt(localctx, 1)
                self.state = 222
                self.match(PiettoParser.NULLABLE)
                pass
            elif token in [19]:
                self.enterOuterAlt(localctx, 2)
                self.state = 223
                self.match(PiettoParser.NOT)
                self.state = 224
                self.match(PiettoParser.NULL)
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
        self.enterRule(localctx, 26, self.RULE_typeArguments)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 227
            self.match(PiettoParser.LPAREN)
            self.state = 239
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 493156761083920) != 0):
                self.state = 228
                self.typeArgument()
                self.state = 233
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,20,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 229
                        self.match(PiettoParser.COMMA)
                        self.state = 230
                        self.typeArgument() 
                    self.state = 235
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,20,self._ctx)

                self.state = 237
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==41:
                    self.state = 236
                    self.match(PiettoParser.COMMA)




            self.state = 241
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
        self.enterRule(localctx, 28, self.RULE_typeArgument)
        try:
            self.state = 248
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,23,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 243
                self.typeArgumentName()
                self.state = 244
                self.match(PiettoParser.ASSIGN)
                self.state = 245
                self.expression()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 247
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
        self.enterRule(localctx, 30, self.RULE_typeArgumentName)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 250
            _la = self._input.LA(1)
            if not(_la==4 or _la==48):
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
        self.enterRule(localctx, 32, self.RULE_enumDefinition)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 252
            self.match(PiettoParser.ENUM)
            self.state = 253
            self.match(PiettoParser.IDENTIFIER)
            self.state = 254
            self.match(PiettoParser.COLON)
            self.state = 255
            self.match(PiettoParser.NEWLINE)
            self.state = 259
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==49:
                self.state = 256
                self.match(PiettoParser.NEWLINE)
                self.state = 261
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 262
            self.match(PiettoParser.INDENT)
            self.state = 263
            self.enumBody()
            self.state = 264
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
        self.enterRule(localctx, 34, self.RULE_enumBody)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 268 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 268
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [48]:
                    self.state = 266
                    self.enumItem()
                    pass
                elif token in [49]:
                    self.state = 267
                    self.match(PiettoParser.NEWLINE)
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 270 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==48 or _la==49):
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
        self.enterRule(localctx, 36, self.RULE_enumItem)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 272
            self.match(PiettoParser.IDENTIFIER)
            self.state = 273
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
        self.enterRule(localctx, 38, self.RULE_constraintDefinition)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 275
            self.match(PiettoParser.CONSTRAINT)
            self.state = 276
            self.match(PiettoParser.IDENTIFIER)
            self.state = 277
            self.match(PiettoParser.LPAREN)
            self.state = 279
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==48:
                self.state = 278
                self.parameterList()


            self.state = 281
            self.match(PiettoParser.RPAREN)
            self.state = 282
            self.match(PiettoParser.ARROW)
            self.state = 283
            self.typeExpression()
            self.state = 284
            self.match(PiettoParser.COLON)
            self.state = 285
            self.match(PiettoParser.NEWLINE)
            self.state = 289
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==49:
                self.state = 286
                self.match(PiettoParser.NEWLINE)
                self.state = 291
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 292
            self.match(PiettoParser.INDENT)
            self.state = 293
            self.constraintBody()
            self.state = 294
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
        self.enterRule(localctx, 40, self.RULE_parameterList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 296
            self.parameter()
            self.state = 301
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,29,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 297
                    self.match(PiettoParser.COMMA)
                    self.state = 298
                    self.parameter() 
                self.state = 303
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,29,self._ctx)

            self.state = 305
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==41:
                self.state = 304
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
        self.enterRule(localctx, 42, self.RULE_parameter)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 307
            self.match(PiettoParser.IDENTIFIER)
            self.state = 308
            self.match(PiettoParser.COLON)
            self.state = 309
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
        self.enterRule(localctx, 44, self.RULE_constraintBody)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 314
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==49:
                self.state = 311
                self.match(PiettoParser.NEWLINE)
                self.state = 316
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 317
            self.expression()
            self.state = 318
            self.match(PiettoParser.NEWLINE)
            self.state = 322
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==49:
                self.state = 319
                self.match(PiettoParser.NEWLINE)
                self.state = 324
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
        self.enterRule(localctx, 46, self.RULE_deriveDefinition)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 325
            self.match(PiettoParser.DERIVE)
            self.state = 326
            self.match(PiettoParser.IDENTIFIER)
            self.state = 327
            self.match(PiettoParser.LPAREN)
            self.state = 329
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==48:
                self.state = 328
                self.parameterList()


            self.state = 331
            self.match(PiettoParser.RPAREN)
            self.state = 332
            self.match(PiettoParser.ARROW)
            self.state = 333
            self.typeExpression()
            self.state = 334
            self.match(PiettoParser.COLON)
            self.state = 335
            self.match(PiettoParser.NEWLINE)
            self.state = 339
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==49:
                self.state = 336
                self.match(PiettoParser.NEWLINE)
                self.state = 341
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 342
            self.match(PiettoParser.INDENT)
            self.state = 343
            self.deriveBody()
            self.state = 344
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
        self.enterRule(localctx, 48, self.RULE_deriveBody)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 349
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==49:
                self.state = 346
                self.match(PiettoParser.NEWLINE)
                self.state = 351
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 352
            self.expression()
            self.state = 353
            self.match(PiettoParser.NEWLINE)
            self.state = 357
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==49:
                self.state = 354
                self.match(PiettoParser.NEWLINE)
                self.state = 359
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ShapeDefinitionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def SHAPE(self):
            return self.getToken(PiettoParser.SHAPE, 0)

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

        def shapeBody(self):
            return self.getTypedRuleContext(PiettoParser.ShapeBodyContext,0)


        def DEDENT(self):
            return self.getToken(PiettoParser.DEDENT, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_shapeDefinition

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitShapeDefinition" ):
                return visitor.visitShapeDefinition(self)
            else:
                return visitor.visitChildren(self)




    def shapeDefinition(self):

        localctx = PiettoParser.ShapeDefinitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_shapeDefinition)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 360
            self.match(PiettoParser.SHAPE)
            self.state = 361
            self.match(PiettoParser.IDENTIFIER)
            self.state = 362
            self.match(PiettoParser.COLON)
            self.state = 363
            self.match(PiettoParser.NEWLINE)
            self.state = 367
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==49:
                self.state = 364
                self.match(PiettoParser.NEWLINE)
                self.state = 369
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 370
            self.match(PiettoParser.INDENT)
            self.state = 371
            self.shapeBody()
            self.state = 372
            self.match(PiettoParser.DEDENT)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ShapeBodyContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def shapeItem(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PiettoParser.ShapeItemContext)
            else:
                return self.getTypedRuleContext(PiettoParser.ShapeItemContext,i)


        def NEWLINE(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.NEWLINE)
            else:
                return self.getToken(PiettoParser.NEWLINE, i)

        def getRuleIndex(self):
            return PiettoParser.RULE_shapeBody

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitShapeBody" ):
                return visitor.visitShapeBody(self)
            else:
                return visitor.visitChildren(self)




    def shapeBody(self):

        localctx = PiettoParser.ShapeBodyContext(self, self._ctx, self.state)
        self.enterRule(localctx, 52, self.RULE_shapeBody)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 377
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==49:
                self.state = 374
                self.match(PiettoParser.NEWLINE)
                self.state = 379
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 380
            self.shapeItem()
            self.state = 385
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 844424930140160) != 0):
                self.state = 383
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [13, 48]:
                    self.state = 381
                    self.shapeItem()
                    pass
                elif token in [49]:
                    self.state = 382
                    self.match(PiettoParser.NEWLINE)
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 387
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ShapeItemContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def fieldDefinition(self):
            return self.getTypedRuleContext(PiettoParser.FieldDefinitionContext,0)


        def checkDefinition(self):
            return self.getTypedRuleContext(PiettoParser.CheckDefinitionContext,0)


        def getRuleIndex(self):
            return PiettoParser.RULE_shapeItem

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitShapeItem" ):
                return visitor.visitShapeItem(self)
            else:
                return visitor.visitChildren(self)




    def shapeItem(self):

        localctx = PiettoParser.ShapeItemContext(self, self._ctx, self.state)
        self.enterRule(localctx, 54, self.RULE_shapeItem)
        try:
            self.state = 390
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [48]:
                self.enterOuterAlt(localctx, 1)
                self.state = 388
                self.fieldDefinition()
                pass
            elif token in [13]:
                self.enterOuterAlt(localctx, 2)
                self.state = 389
                self.checkDefinition()
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


    class FieldDefinitionContext(ParserRuleContext):
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


        def NEWLINE(self):
            return self.getToken(PiettoParser.NEWLINE, 0)

        def fieldDeriveClause(self):
            return self.getTypedRuleContext(PiettoParser.FieldDeriveClauseContext,0)


        def fieldModifier(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PiettoParser.FieldModifierContext)
            else:
                return self.getTypedRuleContext(PiettoParser.FieldModifierContext,i)


        def getRuleIndex(self):
            return PiettoParser.RULE_fieldDefinition

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFieldDefinition" ):
                return visitor.visitFieldDefinition(self)
            else:
                return visitor.visitChildren(self)




    def fieldDefinition(self):

        localctx = PiettoParser.FieldDefinitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 56, self.RULE_fieldDefinition)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 392
            self.match(PiettoParser.IDENTIFIER)
            self.state = 393
            self.match(PiettoParser.COLON)
            self.state = 394
            self.typeExpression()
            self.state = 396
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==11:
                self.state = 395
                self.fieldDeriveClause()


            self.state = 401
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==14 or _la==38:
                self.state = 398
                self.fieldModifier()
                self.state = 403
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 404
            self.match(PiettoParser.NEWLINE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FieldDeriveClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def DERIVE(self):
            return self.getToken(PiettoParser.DERIVE, 0)

        def expression(self):
            return self.getTypedRuleContext(PiettoParser.ExpressionContext,0)


        def getRuleIndex(self):
            return PiettoParser.RULE_fieldDeriveClause

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFieldDeriveClause" ):
                return visitor.visitFieldDeriveClause(self)
            else:
                return visitor.visitChildren(self)




    def fieldDeriveClause(self):

        localctx = PiettoParser.FieldDeriveClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 58, self.RULE_fieldDeriveClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 406
            self.match(PiettoParser.DERIVE)
            self.state = 407
            self.expression()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FieldModifierContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def annotation(self):
            return self.getTypedRuleContext(PiettoParser.AnnotationContext,0)


        def fieldEnsureClause(self):
            return self.getTypedRuleContext(PiettoParser.FieldEnsureClauseContext,0)


        def getRuleIndex(self):
            return PiettoParser.RULE_fieldModifier

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFieldModifier" ):
                return visitor.visitFieldModifier(self)
            else:
                return visitor.visitChildren(self)




    def fieldModifier(self):

        localctx = PiettoParser.FieldModifierContext(self, self._ctx, self.state)
        self.enterRule(localctx, 60, self.RULE_fieldModifier)
        try:
            self.state = 411
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [38]:
                self.enterOuterAlt(localctx, 1)
                self.state = 409
                self.annotation()
                pass
            elif token in [14]:
                self.enterOuterAlt(localctx, 2)
                self.state = 410
                self.fieldEnsureClause()
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


    class AnnotationContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def AT(self):
            return self.getToken(PiettoParser.AT, 0)

        def IDENTIFIER(self):
            return self.getToken(PiettoParser.IDENTIFIER, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_annotation

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAnnotation" ):
                return visitor.visitAnnotation(self)
            else:
                return visitor.visitChildren(self)




    def annotation(self):

        localctx = PiettoParser.AnnotationContext(self, self._ctx, self.state)
        self.enterRule(localctx, 62, self.RULE_annotation)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 413
            self.match(PiettoParser.AT)
            self.state = 414
            self.match(PiettoParser.IDENTIFIER)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FieldEnsureClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ENSURE(self):
            return self.getToken(PiettoParser.ENSURE, 0)

        def expression(self):
            return self.getTypedRuleContext(PiettoParser.ExpressionContext,0)


        def getRuleIndex(self):
            return PiettoParser.RULE_fieldEnsureClause

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFieldEnsureClause" ):
                return visitor.visitFieldEnsureClause(self)
            else:
                return visitor.visitChildren(self)




    def fieldEnsureClause(self):

        localctx = PiettoParser.FieldEnsureClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 64, self.RULE_fieldEnsureClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 416
            self.match(PiettoParser.ENSURE)
            self.state = 417
            self.expression()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CheckDefinitionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def CHECK(self):
            return self.getToken(PiettoParser.CHECK, 0)

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

        def checkBody(self):
            return self.getTypedRuleContext(PiettoParser.CheckBodyContext,0)


        def DEDENT(self):
            return self.getToken(PiettoParser.DEDENT, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_checkDefinition

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCheckDefinition" ):
                return visitor.visitCheckDefinition(self)
            else:
                return visitor.visitChildren(self)




    def checkDefinition(self):

        localctx = PiettoParser.CheckDefinitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 66, self.RULE_checkDefinition)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 419
            self.match(PiettoParser.CHECK)
            self.state = 420
            self.match(PiettoParser.IDENTIFIER)
            self.state = 421
            self.match(PiettoParser.COLON)
            self.state = 422
            self.match(PiettoParser.NEWLINE)
            self.state = 426
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==49:
                self.state = 423
                self.match(PiettoParser.NEWLINE)
                self.state = 428
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 429
            self.match(PiettoParser.INDENT)
            self.state = 430
            self.checkBody()
            self.state = 431
            self.match(PiettoParser.DEDENT)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CheckBodyContext(ParserRuleContext):
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
            return PiettoParser.RULE_checkBody

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCheckBody" ):
                return visitor.visitCheckBody(self)
            else:
                return visitor.visitChildren(self)




    def checkBody(self):

        localctx = PiettoParser.CheckBodyContext(self, self._ctx, self.state)
        self.enterRule(localctx, 68, self.RULE_checkBody)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 436
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==49:
                self.state = 433
                self.match(PiettoParser.NEWLINE)
                self.state = 438
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 439
            self.expression()
            self.state = 440
            self.match(PiettoParser.NEWLINE)
            self.state = 444
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==49:
                self.state = 441
                self.match(PiettoParser.NEWLINE)
                self.state = 446
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
        self.enterRule(localctx, 70, self.RULE_expression)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 447
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
        self.enterRule(localctx, 72, self.RULE_orExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 449
            self.andExpression()
            self.state = 454
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==17:
                self.state = 450
                self.match(PiettoParser.OR)
                self.state = 451
                self.andExpression()
                self.state = 456
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
        self.enterRule(localctx, 74, self.RULE_andExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 457
            self.comparisonExpression()
            self.state = 462
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==16:
                self.state = 458
                self.match(PiettoParser.AND)
                self.state = 459
                self.comparisonExpression()
                self.state = 464
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
        self.enterRule(localctx, 76, self.RULE_comparisonExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 465
            self.additiveExpression()
            self.state = 479
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [22, 25, 26, 27, 28, 29, 30]:
                self.state = 466
                self.comparisonOperator()
                self.state = 467
                self.additiveExpression()
                pass
            elif token in [21]:
                self.state = 469
                self.match(PiettoParser.BETWEEN)
                self.state = 470
                self.additiveExpression()
                self.state = 471
                self.match(PiettoParser.AND)
                self.state = 472
                self.additiveExpression()
                pass
            elif token in [18]:
                self.state = 474
                self.match(PiettoParser.IS)
                self.state = 476
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==19:
                    self.state = 475
                    self.match(PiettoParser.NOT)


                self.state = 478
                self.match(PiettoParser.NULL)
                pass
            elif token in [14, 16, 17, 38, 40, 41, 49]:
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
        self.enterRule(localctx, 78, self.RULE_comparisonOperator)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 481
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 2118123520) != 0)):
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
        self.enterRule(localctx, 80, self.RULE_additiveExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 483
            self.multiplicativeExpression()
            self.state = 488
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==33 or _la==34:
                self.state = 484
                _la = self._input.LA(1)
                if not(_la==33 or _la==34):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 485
                self.multiplicativeExpression()
                self.state = 490
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
        self.enterRule(localctx, 82, self.RULE_multiplicativeExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 491
            self.unaryExpression()
            self.state = 496
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 240518168576) != 0):
                self.state = 492
                _la = self._input.LA(1)
                if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 240518168576) != 0)):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 493
                self.unaryExpression()
                self.state = 498
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
        self.enterRule(localctx, 84, self.RULE_unaryExpression)
        self._la = 0 # Token type
        try:
            self.state = 502
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [33, 34]:
                self.enterOuterAlt(localctx, 1)
                self.state = 499
                _la = self._input.LA(1)
                if not(_la==33 or _la==34):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 500
                self.unaryExpression()
                pass
            elif token in [13, 20, 23, 24, 39, 46, 47, 48]:
                self.enterOuterAlt(localctx, 2)
                self.state = 501
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
        self.enterRule(localctx, 86, self.RULE_primaryExpression)
        self._la = 0 # Token type
        try:
            self.state = 513
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [20, 23, 24, 46, 47]:
                self.enterOuterAlt(localctx, 1)
                self.state = 504
                self.literal()
                pass
            elif token in [13, 48]:
                self.enterOuterAlt(localctx, 2)
                self.state = 505
                self.dottedName()
                self.state = 507
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==39:
                    self.state = 506
                    self.callSuffix()


                pass
            elif token in [39]:
                self.enterOuterAlt(localctx, 3)
                self.state = 509
                self.match(PiettoParser.LPAREN)
                self.state = 510
                self.expression()
                self.state = 511
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

        def namePart(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PiettoParser.NamePartContext)
            else:
                return self.getTypedRuleContext(PiettoParser.NamePartContext,i)


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
        self.enterRule(localctx, 88, self.RULE_dottedName)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 515
            self.namePart()
            self.state = 520
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==42:
                self.state = 516
                self.match(PiettoParser.DOT)
                self.state = 517
                self.namePart()
                self.state = 522
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class NamePartContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENTIFIER(self):
            return self.getToken(PiettoParser.IDENTIFIER, 0)

        def CHECK(self):
            return self.getToken(PiettoParser.CHECK, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_namePart

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNamePart" ):
                return visitor.visitNamePart(self)
            else:
                return visitor.visitChildren(self)




    def namePart(self):

        localctx = PiettoParser.NamePartContext(self, self._ctx, self.state)
        self.enterRule(localctx, 90, self.RULE_namePart)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 523
            _la = self._input.LA(1)
            if not(_la==13 or _la==48):
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
        self.enterRule(localctx, 92, self.RULE_callSuffix)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 525
            self.match(PiettoParser.LPAREN)
            self.state = 537
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 493156761083904) != 0):
                self.state = 526
                self.expression()
                self.state = 531
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,58,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 527
                        self.match(PiettoParser.COMMA)
                        self.state = 528
                        self.expression() 
                    self.state = 533
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,58,self._ctx)

                self.state = 535
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==41:
                    self.state = 534
                    self.match(PiettoParser.COMMA)




            self.state = 539
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
        self.enterRule(localctx, 94, self.RULE_literal)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 541
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 211106258747392) != 0)):
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





