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
        4,1,58,580,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,2,31,7,31,2,32,7,32,2,33,
        7,33,2,34,7,34,2,35,7,35,2,36,7,36,2,37,7,37,2,38,7,38,2,39,7,39,
        2,40,7,40,2,41,7,41,2,42,7,42,2,43,7,43,2,44,7,44,2,45,7,45,2,46,
        7,46,2,47,7,47,2,48,7,48,2,49,7,49,1,0,5,0,102,8,0,10,0,12,0,105,
        9,0,1,0,3,0,108,8,0,1,0,5,0,111,8,0,10,0,12,0,114,9,0,1,0,1,0,5,
        0,118,8,0,10,0,12,0,121,9,0,5,0,123,8,0,10,0,12,0,126,9,0,1,0,1,
        0,1,1,1,1,3,1,132,8,1,1,1,3,1,135,8,1,1,1,3,1,138,8,1,1,1,1,1,3,
        1,142,8,1,1,1,3,1,145,8,1,1,1,1,1,3,1,149,8,1,1,1,3,1,152,8,1,1,
        2,1,2,1,2,1,2,1,3,1,3,1,3,1,3,1,4,1,4,1,4,1,4,1,5,1,5,1,5,1,5,1,
        6,1,6,1,6,1,6,1,6,3,6,175,8,6,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,
        7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,5,7,198,8,7,10,
        7,12,7,201,9,7,1,7,1,7,1,7,1,7,3,7,207,8,7,1,8,1,8,4,8,211,8,8,11,
        8,12,8,212,1,9,1,9,1,9,1,9,1,10,1,10,3,10,221,8,10,1,11,1,11,3,11,
        225,8,11,1,12,1,12,1,12,3,12,230,8,12,1,13,1,13,1,13,1,13,5,13,236,
        8,13,10,13,12,13,239,9,13,1,13,3,13,242,8,13,3,13,244,8,13,1,13,
        1,13,1,14,1,14,1,14,1,14,1,14,3,14,253,8,14,1,15,1,15,1,16,1,16,
        1,16,1,16,1,16,5,16,262,8,16,10,16,12,16,265,9,16,1,16,1,16,1,16,
        1,16,1,17,1,17,4,17,273,8,17,11,17,12,17,274,1,18,1,18,1,18,1,19,
        1,19,1,19,1,19,3,19,284,8,19,1,19,1,19,1,19,1,19,1,19,1,19,5,19,
        292,8,19,10,19,12,19,295,9,19,1,19,1,19,1,19,1,19,1,20,1,20,1,20,
        5,20,304,8,20,10,20,12,20,307,9,20,1,20,3,20,310,8,20,1,21,1,21,
        1,21,1,21,1,22,5,22,317,8,22,10,22,12,22,320,9,22,1,22,1,22,1,22,
        5,22,325,8,22,10,22,12,22,328,9,22,1,23,1,23,1,23,1,23,3,23,334,
        8,23,1,23,1,23,1,23,1,23,1,23,1,23,5,23,342,8,23,10,23,12,23,345,
        9,23,1,23,1,23,1,23,1,23,1,24,5,24,352,8,24,10,24,12,24,355,9,24,
        1,24,1,24,1,24,5,24,360,8,24,10,24,12,24,363,9,24,1,25,1,25,1,25,
        1,25,1,25,5,25,370,8,25,10,25,12,25,373,9,25,1,25,1,25,1,25,1,25,
        1,26,5,26,380,8,26,10,26,12,26,383,9,26,1,26,1,26,1,26,5,26,388,
        8,26,10,26,12,26,391,9,26,1,27,1,27,1,27,1,27,3,27,397,8,27,1,28,
        1,28,1,28,1,28,3,28,403,8,28,1,28,5,28,406,8,28,10,28,12,28,409,
        9,28,1,28,1,28,1,29,1,29,1,29,1,30,1,30,3,30,418,8,30,1,31,1,31,
        1,31,1,32,1,32,1,32,1,33,1,33,1,33,1,33,1,33,5,33,431,8,33,10,33,
        12,33,434,9,33,1,33,1,33,1,33,1,33,1,34,5,34,441,8,34,10,34,12,34,
        444,9,34,1,34,1,34,1,34,5,34,449,8,34,10,34,12,34,452,9,34,1,35,
        1,35,1,35,1,35,1,35,1,35,5,35,460,8,35,10,35,12,35,463,9,35,1,35,
        1,35,1,36,1,36,1,36,1,36,1,36,1,36,5,36,473,8,36,10,36,12,36,476,
        9,36,1,36,1,36,3,36,480,8,36,1,36,1,36,1,37,1,37,1,38,1,38,1,38,
        5,38,489,8,38,10,38,12,38,492,9,38,1,39,1,39,1,39,5,39,497,8,39,
        10,39,12,39,500,9,39,1,40,1,40,1,40,1,40,1,40,1,40,1,40,1,40,1,40,
        1,40,1,40,3,40,513,8,40,1,40,3,40,516,8,40,1,41,1,41,1,42,1,42,1,
        42,5,42,523,8,42,10,42,12,42,526,9,42,1,43,1,43,1,43,5,43,531,8,
        43,10,43,12,43,534,9,43,1,44,1,44,1,44,3,44,539,8,44,1,45,1,45,1,
        45,3,45,544,8,45,1,45,1,45,1,45,1,45,3,45,550,8,45,1,46,1,46,1,46,
        5,46,555,8,46,10,46,12,46,558,9,46,1,47,1,47,1,48,1,48,1,48,1,48,
        5,48,566,8,48,10,48,12,48,569,9,48,1,48,3,48,572,8,48,3,48,574,8,
        48,1,48,1,48,1,49,1,49,1,49,0,0,50,0,2,4,6,8,10,12,14,16,18,20,22,
        24,26,28,30,32,34,36,38,40,42,44,46,48,50,52,54,56,58,60,62,64,66,
        68,70,72,74,76,78,80,82,84,86,88,90,92,94,96,98,0,7,1,0,5,7,2,0,
        4,4,52,52,2,0,26,26,29,34,1,0,37,38,1,0,39,41,2,0,13,17,52,52,3,
        0,24,24,27,28,50,51,604,0,103,1,0,0,0,2,151,1,0,0,0,4,153,1,0,0,
        0,6,157,1,0,0,0,8,161,1,0,0,0,10,165,1,0,0,0,12,174,1,0,0,0,14,206,
        1,0,0,0,16,210,1,0,0,0,18,214,1,0,0,0,20,218,1,0,0,0,22,222,1,0,
        0,0,24,229,1,0,0,0,26,231,1,0,0,0,28,252,1,0,0,0,30,254,1,0,0,0,
        32,256,1,0,0,0,34,272,1,0,0,0,36,276,1,0,0,0,38,279,1,0,0,0,40,300,
        1,0,0,0,42,311,1,0,0,0,44,318,1,0,0,0,46,329,1,0,0,0,48,353,1,0,
        0,0,50,364,1,0,0,0,52,381,1,0,0,0,54,396,1,0,0,0,56,398,1,0,0,0,
        58,412,1,0,0,0,60,417,1,0,0,0,62,419,1,0,0,0,64,422,1,0,0,0,66,425,
        1,0,0,0,68,442,1,0,0,0,70,453,1,0,0,0,72,466,1,0,0,0,74,483,1,0,
        0,0,76,485,1,0,0,0,78,493,1,0,0,0,80,501,1,0,0,0,82,517,1,0,0,0,
        84,519,1,0,0,0,86,527,1,0,0,0,88,538,1,0,0,0,90,549,1,0,0,0,92,551,
        1,0,0,0,94,559,1,0,0,0,96,561,1,0,0,0,98,577,1,0,0,0,100,102,5,53,
        0,0,101,100,1,0,0,0,102,105,1,0,0,0,103,101,1,0,0,0,103,104,1,0,
        0,0,104,107,1,0,0,0,105,103,1,0,0,0,106,108,3,2,1,0,107,106,1,0,
        0,0,107,108,1,0,0,0,108,112,1,0,0,0,109,111,5,53,0,0,110,109,1,0,
        0,0,111,114,1,0,0,0,112,110,1,0,0,0,112,113,1,0,0,0,113,124,1,0,
        0,0,114,112,1,0,0,0,115,119,3,12,6,0,116,118,5,53,0,0,117,116,1,
        0,0,0,118,121,1,0,0,0,119,117,1,0,0,0,119,120,1,0,0,0,120,123,1,
        0,0,0,121,119,1,0,0,0,122,115,1,0,0,0,123,126,1,0,0,0,124,122,1,
        0,0,0,124,125,1,0,0,0,125,127,1,0,0,0,126,124,1,0,0,0,127,128,5,
        0,0,1,128,1,1,0,0,0,129,131,3,4,2,0,130,132,3,6,3,0,131,130,1,0,
        0,0,131,132,1,0,0,0,132,134,1,0,0,0,133,135,3,8,4,0,134,133,1,0,
        0,0,134,135,1,0,0,0,135,137,1,0,0,0,136,138,3,10,5,0,137,136,1,0,
        0,0,137,138,1,0,0,0,138,152,1,0,0,0,139,141,3,6,3,0,140,142,3,8,
        4,0,141,140,1,0,0,0,141,142,1,0,0,0,142,144,1,0,0,0,143,145,3,10,
        5,0,144,143,1,0,0,0,144,145,1,0,0,0,145,152,1,0,0,0,146,148,3,8,
        4,0,147,149,3,10,5,0,148,147,1,0,0,0,148,149,1,0,0,0,149,152,1,0,
        0,0,150,152,3,10,5,0,151,129,1,0,0,0,151,139,1,0,0,0,151,146,1,0,
        0,0,151,150,1,0,0,0,152,3,1,0,0,0,153,154,5,1,0,0,154,155,5,50,0,
        0,155,156,5,53,0,0,156,5,1,0,0,0,157,158,5,2,0,0,158,159,7,0,0,0,
        159,160,5,53,0,0,160,7,1,0,0,0,161,162,5,3,0,0,162,163,5,52,0,0,
        163,164,5,53,0,0,164,9,1,0,0,0,165,166,5,4,0,0,166,167,5,52,0,0,
        167,168,5,53,0,0,168,11,1,0,0,0,169,175,3,14,7,0,170,175,3,32,16,
        0,171,175,3,38,19,0,172,175,3,46,23,0,173,175,3,50,25,0,174,169,
        1,0,0,0,174,170,1,0,0,0,174,171,1,0,0,0,174,172,1,0,0,0,174,173,
        1,0,0,0,175,13,1,0,0,0,176,177,5,8,0,0,177,178,5,52,0,0,178,179,
        5,35,0,0,179,180,3,20,10,0,180,181,5,53,0,0,181,207,1,0,0,0,182,
        183,5,8,0,0,183,184,5,52,0,0,184,185,5,35,0,0,185,186,3,20,10,0,
        186,187,5,18,0,0,187,188,3,74,37,0,188,189,5,53,0,0,189,207,1,0,
        0,0,190,191,5,8,0,0,191,192,5,52,0,0,192,193,5,35,0,0,193,194,3,
        20,10,0,194,195,5,47,0,0,195,199,5,53,0,0,196,198,5,53,0,0,197,196,
        1,0,0,0,198,201,1,0,0,0,199,197,1,0,0,0,199,200,1,0,0,0,200,202,
        1,0,0,0,201,199,1,0,0,0,202,203,5,57,0,0,203,204,3,16,8,0,204,205,
        5,58,0,0,205,207,1,0,0,0,206,176,1,0,0,0,206,182,1,0,0,0,206,190,
        1,0,0,0,207,15,1,0,0,0,208,211,3,18,9,0,209,211,5,53,0,0,210,208,
        1,0,0,0,210,209,1,0,0,0,211,212,1,0,0,0,212,210,1,0,0,0,212,213,
        1,0,0,0,213,17,1,0,0,0,214,215,5,18,0,0,215,216,3,74,37,0,216,217,
        5,53,0,0,217,19,1,0,0,0,218,220,3,22,11,0,219,221,3,24,12,0,220,
        219,1,0,0,0,220,221,1,0,0,0,221,21,1,0,0,0,222,224,5,52,0,0,223,
        225,3,26,13,0,224,223,1,0,0,0,224,225,1,0,0,0,225,23,1,0,0,0,226,
        230,5,19,0,0,227,228,5,23,0,0,228,230,5,24,0,0,229,226,1,0,0,0,229,
        227,1,0,0,0,230,25,1,0,0,0,231,243,5,43,0,0,232,237,3,28,14,0,233,
        234,5,45,0,0,234,236,3,28,14,0,235,233,1,0,0,0,236,239,1,0,0,0,237,
        235,1,0,0,0,237,238,1,0,0,0,238,241,1,0,0,0,239,237,1,0,0,0,240,
        242,5,45,0,0,241,240,1,0,0,0,241,242,1,0,0,0,242,244,1,0,0,0,243,
        232,1,0,0,0,243,244,1,0,0,0,244,245,1,0,0,0,245,246,5,44,0,0,246,
        27,1,0,0,0,247,248,3,30,15,0,248,249,5,35,0,0,249,250,3,74,37,0,
        250,253,1,0,0,0,251,253,3,74,37,0,252,247,1,0,0,0,252,251,1,0,0,
        0,253,29,1,0,0,0,254,255,7,1,0,0,255,31,1,0,0,0,256,257,5,9,0,0,
        257,258,5,52,0,0,258,259,5,47,0,0,259,263,5,53,0,0,260,262,5,53,
        0,0,261,260,1,0,0,0,262,265,1,0,0,0,263,261,1,0,0,0,263,264,1,0,
        0,0,264,266,1,0,0,0,265,263,1,0,0,0,266,267,5,57,0,0,267,268,3,34,
        17,0,268,269,5,58,0,0,269,33,1,0,0,0,270,273,3,36,18,0,271,273,5,
        53,0,0,272,270,1,0,0,0,272,271,1,0,0,0,273,274,1,0,0,0,274,272,1,
        0,0,0,274,275,1,0,0,0,275,35,1,0,0,0,276,277,5,52,0,0,277,278,5,
        53,0,0,278,37,1,0,0,0,279,280,5,10,0,0,280,281,5,52,0,0,281,283,
        5,43,0,0,282,284,3,40,20,0,283,282,1,0,0,0,283,284,1,0,0,0,284,285,
        1,0,0,0,285,286,5,44,0,0,286,287,5,36,0,0,287,288,3,20,10,0,288,
        289,5,47,0,0,289,293,5,53,0,0,290,292,5,53,0,0,291,290,1,0,0,0,292,
        295,1,0,0,0,293,291,1,0,0,0,293,294,1,0,0,0,294,296,1,0,0,0,295,
        293,1,0,0,0,296,297,5,57,0,0,297,298,3,44,22,0,298,299,5,58,0,0,
        299,39,1,0,0,0,300,305,3,42,21,0,301,302,5,45,0,0,302,304,3,42,21,
        0,303,301,1,0,0,0,304,307,1,0,0,0,305,303,1,0,0,0,305,306,1,0,0,
        0,306,309,1,0,0,0,307,305,1,0,0,0,308,310,5,45,0,0,309,308,1,0,0,
        0,309,310,1,0,0,0,310,41,1,0,0,0,311,312,5,52,0,0,312,313,5,47,0,
        0,313,314,3,20,10,0,314,43,1,0,0,0,315,317,5,53,0,0,316,315,1,0,
        0,0,317,320,1,0,0,0,318,316,1,0,0,0,318,319,1,0,0,0,319,321,1,0,
        0,0,320,318,1,0,0,0,321,322,3,74,37,0,322,326,5,53,0,0,323,325,5,
        53,0,0,324,323,1,0,0,0,325,328,1,0,0,0,326,324,1,0,0,0,326,327,1,
        0,0,0,327,45,1,0,0,0,328,326,1,0,0,0,329,330,5,11,0,0,330,331,5,
        52,0,0,331,333,5,43,0,0,332,334,3,40,20,0,333,332,1,0,0,0,333,334,
        1,0,0,0,334,335,1,0,0,0,335,336,5,44,0,0,336,337,5,36,0,0,337,338,
        3,20,10,0,338,339,5,47,0,0,339,343,5,53,0,0,340,342,5,53,0,0,341,
        340,1,0,0,0,342,345,1,0,0,0,343,341,1,0,0,0,343,344,1,0,0,0,344,
        346,1,0,0,0,345,343,1,0,0,0,346,347,5,57,0,0,347,348,3,48,24,0,348,
        349,5,58,0,0,349,47,1,0,0,0,350,352,5,53,0,0,351,350,1,0,0,0,352,
        355,1,0,0,0,353,351,1,0,0,0,353,354,1,0,0,0,354,356,1,0,0,0,355,
        353,1,0,0,0,356,357,3,74,37,0,357,361,5,53,0,0,358,360,5,53,0,0,
        359,358,1,0,0,0,360,363,1,0,0,0,361,359,1,0,0,0,361,362,1,0,0,0,
        362,49,1,0,0,0,363,361,1,0,0,0,364,365,5,12,0,0,365,366,5,52,0,0,
        366,367,5,47,0,0,367,371,5,53,0,0,368,370,5,53,0,0,369,368,1,0,0,
        0,370,373,1,0,0,0,371,369,1,0,0,0,371,372,1,0,0,0,372,374,1,0,0,
        0,373,371,1,0,0,0,374,375,5,57,0,0,375,376,3,52,26,0,376,377,5,58,
        0,0,377,51,1,0,0,0,378,380,5,53,0,0,379,378,1,0,0,0,380,383,1,0,
        0,0,381,379,1,0,0,0,381,382,1,0,0,0,382,384,1,0,0,0,383,381,1,0,
        0,0,384,389,3,54,27,0,385,388,3,54,27,0,386,388,5,53,0,0,387,385,
        1,0,0,0,387,386,1,0,0,0,388,391,1,0,0,0,389,387,1,0,0,0,389,390,
        1,0,0,0,390,53,1,0,0,0,391,389,1,0,0,0,392,397,3,56,28,0,393,397,
        3,66,33,0,394,397,3,70,35,0,395,397,3,72,36,0,396,392,1,0,0,0,396,
        393,1,0,0,0,396,394,1,0,0,0,396,395,1,0,0,0,397,55,1,0,0,0,398,399,
        5,52,0,0,399,400,5,47,0,0,400,402,3,20,10,0,401,403,3,58,29,0,402,
        401,1,0,0,0,402,403,1,0,0,0,403,407,1,0,0,0,404,406,3,60,30,0,405,
        404,1,0,0,0,406,409,1,0,0,0,407,405,1,0,0,0,407,408,1,0,0,0,408,
        410,1,0,0,0,409,407,1,0,0,0,410,411,5,53,0,0,411,57,1,0,0,0,412,
        413,5,11,0,0,413,414,3,74,37,0,414,59,1,0,0,0,415,418,3,62,31,0,
        416,418,3,64,32,0,417,415,1,0,0,0,417,416,1,0,0,0,418,61,1,0,0,0,
        419,420,5,42,0,0,420,421,5,52,0,0,421,63,1,0,0,0,422,423,5,18,0,
        0,423,424,3,74,37,0,424,65,1,0,0,0,425,426,5,13,0,0,426,427,5,52,
        0,0,427,428,5,47,0,0,428,432,5,53,0,0,429,431,5,53,0,0,430,429,1,
        0,0,0,431,434,1,0,0,0,432,430,1,0,0,0,432,433,1,0,0,0,433,435,1,
        0,0,0,434,432,1,0,0,0,435,436,5,57,0,0,436,437,3,68,34,0,437,438,
        5,58,0,0,438,67,1,0,0,0,439,441,5,53,0,0,440,439,1,0,0,0,441,444,
        1,0,0,0,442,440,1,0,0,0,442,443,1,0,0,0,443,445,1,0,0,0,444,442,
        1,0,0,0,445,446,3,74,37,0,446,450,5,53,0,0,447,449,5,53,0,0,448,
        447,1,0,0,0,449,452,1,0,0,0,450,448,1,0,0,0,450,451,1,0,0,0,451,
        69,1,0,0,0,452,450,1,0,0,0,453,454,5,14,0,0,454,455,5,52,0,0,455,
        456,5,15,0,0,456,461,5,52,0,0,457,458,5,45,0,0,458,460,5,52,0,0,
        459,457,1,0,0,0,460,463,1,0,0,0,461,459,1,0,0,0,461,462,1,0,0,0,
        462,464,1,0,0,0,463,461,1,0,0,0,464,465,5,53,0,0,465,71,1,0,0,0,
        466,467,5,16,0,0,467,468,5,52,0,0,468,469,5,15,0,0,469,474,5,52,
        0,0,470,471,5,45,0,0,471,473,5,52,0,0,472,470,1,0,0,0,473,476,1,
        0,0,0,474,472,1,0,0,0,474,475,1,0,0,0,475,479,1,0,0,0,476,474,1,
        0,0,0,477,478,5,17,0,0,478,480,3,74,37,0,479,477,1,0,0,0,479,480,
        1,0,0,0,480,481,1,0,0,0,481,482,5,53,0,0,482,73,1,0,0,0,483,484,
        3,76,38,0,484,75,1,0,0,0,485,490,3,78,39,0,486,487,5,21,0,0,487,
        489,3,78,39,0,488,486,1,0,0,0,489,492,1,0,0,0,490,488,1,0,0,0,490,
        491,1,0,0,0,491,77,1,0,0,0,492,490,1,0,0,0,493,498,3,80,40,0,494,
        495,5,20,0,0,495,497,3,80,40,0,496,494,1,0,0,0,497,500,1,0,0,0,498,
        496,1,0,0,0,498,499,1,0,0,0,499,79,1,0,0,0,500,498,1,0,0,0,501,515,
        3,84,42,0,502,503,3,82,41,0,503,504,3,84,42,0,504,516,1,0,0,0,505,
        506,5,25,0,0,506,507,3,84,42,0,507,508,5,20,0,0,508,509,3,84,42,
        0,509,516,1,0,0,0,510,512,5,22,0,0,511,513,5,23,0,0,512,511,1,0,
        0,0,512,513,1,0,0,0,513,514,1,0,0,0,514,516,5,24,0,0,515,502,1,0,
        0,0,515,505,1,0,0,0,515,510,1,0,0,0,515,516,1,0,0,0,516,81,1,0,0,
        0,517,518,7,2,0,0,518,83,1,0,0,0,519,524,3,86,43,0,520,521,7,3,0,
        0,521,523,3,86,43,0,522,520,1,0,0,0,523,526,1,0,0,0,524,522,1,0,
        0,0,524,525,1,0,0,0,525,85,1,0,0,0,526,524,1,0,0,0,527,532,3,88,
        44,0,528,529,7,4,0,0,529,531,3,88,44,0,530,528,1,0,0,0,531,534,1,
        0,0,0,532,530,1,0,0,0,532,533,1,0,0,0,533,87,1,0,0,0,534,532,1,0,
        0,0,535,536,7,3,0,0,536,539,3,88,44,0,537,539,3,90,45,0,538,535,
        1,0,0,0,538,537,1,0,0,0,539,89,1,0,0,0,540,550,3,98,49,0,541,543,
        3,92,46,0,542,544,3,96,48,0,543,542,1,0,0,0,543,544,1,0,0,0,544,
        550,1,0,0,0,545,546,5,43,0,0,546,547,3,74,37,0,547,548,5,44,0,0,
        548,550,1,0,0,0,549,540,1,0,0,0,549,541,1,0,0,0,549,545,1,0,0,0,
        550,91,1,0,0,0,551,556,3,94,47,0,552,553,5,46,0,0,553,555,3,94,47,
        0,554,552,1,0,0,0,555,558,1,0,0,0,556,554,1,0,0,0,556,557,1,0,0,
        0,557,93,1,0,0,0,558,556,1,0,0,0,559,560,7,5,0,0,560,95,1,0,0,0,
        561,573,5,43,0,0,562,567,3,74,37,0,563,564,5,45,0,0,564,566,3,74,
        37,0,565,563,1,0,0,0,566,569,1,0,0,0,567,565,1,0,0,0,567,568,1,0,
        0,0,568,571,1,0,0,0,569,567,1,0,0,0,570,572,5,45,0,0,571,570,1,0,
        0,0,571,572,1,0,0,0,572,574,1,0,0,0,573,562,1,0,0,0,573,574,1,0,
        0,0,574,575,1,0,0,0,575,576,5,44,0,0,576,97,1,0,0,0,577,578,7,6,
        0,0,578,99,1,0,0,0,64,103,107,112,119,124,131,134,137,141,144,148,
        151,174,199,206,210,212,220,224,229,237,241,243,252,263,272,274,
        283,293,305,309,318,326,333,343,353,361,371,381,387,389,396,402,
        407,417,432,442,450,461,474,479,490,498,512,515,524,532,538,543,
        549,556,567,571,573
    ]

class PiettoParser ( Parser ):

    grammarFileName = "Pietto.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'pietto'", "'mode'", "'dialect'", "'encoding'", 
                     "'loose'", "'checked'", "'strict'", "'type'", "'enum'", 
                     "'constraint'", "'derive'", "'shape'", "'check'", "'unique'", 
                     "'on'", "'index'", "'when'", "'ensure'", "'nullable'", 
                     "'and'", "'or'", "'is'", "'not'", "'null'", "'between'", 
                     "'like'", "'true'", "'false'", "'=='", "'!='", "'<='", 
                     "'>='", "'<'", "'>'", "'='", "'->'", "'+'", "'-'", 
                     "'*'", "'/'", "'%'", "'@'", "'('", "')'", "','", "'.'", 
                     "':'", "'{'", "'}'" ]

    symbolicNames = [ "<INVALID>", "PIETTO", "MODE", "DIALECT", "ENCODING", 
                      "LOOSE", "CHECKED", "STRICT", "TYPE", "ENUM", "CONSTRAINT", 
                      "DERIVE", "SHAPE", "CHECK", "UNIQUE", "ON", "INDEX", 
                      "WHEN", "ENSURE", "NULLABLE", "AND", "OR", "IS", "NOT", 
                      "NULL", "BETWEEN", "LIKE", "TRUE", "FALSE", "EQ", 
                      "NE", "LE", "GE", "LT", "GT", "ASSIGN", "ARROW", "PLUS", 
                      "MINUS", "STAR", "SLASH", "PERCENT", "AT", "LPAREN", 
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
    RULE_uniqueDefinition = 35
    RULE_indexDefinition = 36
    RULE_expression = 37
    RULE_orExpression = 38
    RULE_andExpression = 39
    RULE_comparisonExpression = 40
    RULE_comparisonOperator = 41
    RULE_additiveExpression = 42
    RULE_multiplicativeExpression = 43
    RULE_unaryExpression = 44
    RULE_primaryExpression = 45
    RULE_dottedName = 46
    RULE_namePart = 47
    RULE_callSuffix = 48
    RULE_literal = 49

    ruleNames =  [ "script", "header", "versionDecl", "modeDecl", "dialectDecl", 
                   "encodingDecl", "definition", "typeDefinition", "typeBody", 
                   "ensureClause", "typeExpression", "typeReference", "nullabilityModifier", 
                   "typeArguments", "typeArgument", "typeArgumentName", 
                   "enumDefinition", "enumBody", "enumItem", "constraintDefinition", 
                   "parameterList", "parameter", "constraintBody", "deriveDefinition", 
                   "deriveBody", "shapeDefinition", "shapeBody", "shapeItem", 
                   "fieldDefinition", "fieldDeriveClause", "fieldModifier", 
                   "annotation", "fieldEnsureClause", "checkDefinition", 
                   "checkBody", "uniqueDefinition", "indexDefinition", "expression", 
                   "orExpression", "andExpression", "comparisonExpression", 
                   "comparisonOperator", "additiveExpression", "multiplicativeExpression", 
                   "unaryExpression", "primaryExpression", "dottedName", 
                   "namePart", "callSuffix", "literal" ]

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
    UNIQUE=14
    ON=15
    INDEX=16
    WHEN=17
    ENSURE=18
    NULLABLE=19
    AND=20
    OR=21
    IS=22
    NOT=23
    NULL=24
    BETWEEN=25
    LIKE=26
    TRUE=27
    FALSE=28
    EQ=29
    NE=30
    LE=31
    GE=32
    LT=33
    GT=34
    ASSIGN=35
    ARROW=36
    PLUS=37
    MINUS=38
    STAR=39
    SLASH=40
    PERCENT=41
    AT=42
    LPAREN=43
    RPAREN=44
    COMMA=45
    DOT=46
    COLON=47
    LBRACE=48
    RBRACE=49
    NUMBER=50
    STRING=51
    IDENTIFIER=52
    NEWLINE=53
    COMMENT=54
    WS=55
    UNKNOWN=56
    INDENT=57
    DEDENT=58

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
            self.state = 103
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,0,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 100
                    self.match(PiettoParser.NEWLINE) 
                self.state = 105
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,0,self._ctx)

            self.state = 107
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 30) != 0):
                self.state = 106
                self.header()


            self.state = 112
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==53:
                self.state = 109
                self.match(PiettoParser.NEWLINE)
                self.state = 114
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 124
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 7936) != 0):
                self.state = 115
                self.definition()
                self.state = 119
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==53:
                    self.state = 116
                    self.match(PiettoParser.NEWLINE)
                    self.state = 121
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 126
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 127
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
            self.state = 151
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [1]:
                self.enterOuterAlt(localctx, 1)
                self.state = 129
                self.versionDecl()
                self.state = 131
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==2:
                    self.state = 130
                    self.modeDecl()


                self.state = 134
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==3:
                    self.state = 133
                    self.dialectDecl()


                self.state = 137
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4:
                    self.state = 136
                    self.encodingDecl()


                pass
            elif token in [2]:
                self.enterOuterAlt(localctx, 2)
                self.state = 139
                self.modeDecl()
                self.state = 141
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==3:
                    self.state = 140
                    self.dialectDecl()


                self.state = 144
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4:
                    self.state = 143
                    self.encodingDecl()


                pass
            elif token in [3]:
                self.enterOuterAlt(localctx, 3)
                self.state = 146
                self.dialectDecl()
                self.state = 148
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4:
                    self.state = 147
                    self.encodingDecl()


                pass
            elif token in [4]:
                self.enterOuterAlt(localctx, 4)
                self.state = 150
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
            self.state = 153
            self.match(PiettoParser.PIETTO)
            self.state = 154
            self.match(PiettoParser.NUMBER)
            self.state = 155
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
            self.state = 157
            self.match(PiettoParser.MODE)
            self.state = 158
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 224) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 159
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
            self.state = 161
            self.match(PiettoParser.DIALECT)
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
            self.state = 165
            self.match(PiettoParser.ENCODING)
            self.state = 166
            self.match(PiettoParser.IDENTIFIER)
            self.state = 167
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
            self.state = 174
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [8]:
                self.enterOuterAlt(localctx, 1)
                self.state = 169
                self.typeDefinition()
                pass
            elif token in [9]:
                self.enterOuterAlt(localctx, 2)
                self.state = 170
                self.enumDefinition()
                pass
            elif token in [10]:
                self.enterOuterAlt(localctx, 3)
                self.state = 171
                self.constraintDefinition()
                pass
            elif token in [11]:
                self.enterOuterAlt(localctx, 4)
                self.state = 172
                self.deriveDefinition()
                pass
            elif token in [12]:
                self.enterOuterAlt(localctx, 5)
                self.state = 173
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
            self.state = 206
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,14,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 176
                self.match(PiettoParser.TYPE)
                self.state = 177
                self.match(PiettoParser.IDENTIFIER)
                self.state = 178
                self.match(PiettoParser.ASSIGN)
                self.state = 179
                self.typeExpression()
                self.state = 180
                self.match(PiettoParser.NEWLINE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 182
                self.match(PiettoParser.TYPE)
                self.state = 183
                self.match(PiettoParser.IDENTIFIER)
                self.state = 184
                self.match(PiettoParser.ASSIGN)
                self.state = 185
                self.typeExpression()
                self.state = 186
                self.match(PiettoParser.ENSURE)
                self.state = 187
                self.expression()
                self.state = 188
                self.match(PiettoParser.NEWLINE)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 190
                self.match(PiettoParser.TYPE)
                self.state = 191
                self.match(PiettoParser.IDENTIFIER)
                self.state = 192
                self.match(PiettoParser.ASSIGN)
                self.state = 193
                self.typeExpression()
                self.state = 194
                self.match(PiettoParser.COLON)
                self.state = 195
                self.match(PiettoParser.NEWLINE)
                self.state = 199
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==53:
                    self.state = 196
                    self.match(PiettoParser.NEWLINE)
                    self.state = 201
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 202
                self.match(PiettoParser.INDENT)
                self.state = 203
                self.typeBody()
                self.state = 204
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
            self.state = 210 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 210
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [18]:
                    self.state = 208
                    self.ensureClause()
                    pass
                elif token in [53]:
                    self.state = 209
                    self.match(PiettoParser.NEWLINE)
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 212 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==18 or _la==53):
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
            self.state = 214
            self.match(PiettoParser.ENSURE)
            self.state = 215
            self.expression()
            self.state = 216
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
            self.state = 218
            self.typeReference()
            self.state = 220
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==19 or _la==23:
                self.state = 219
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
            self.state = 222
            self.match(PiettoParser.IDENTIFIER)
            self.state = 224
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==43:
                self.state = 223
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
            self.state = 229
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [19]:
                self.enterOuterAlt(localctx, 1)
                self.state = 226
                self.match(PiettoParser.NULLABLE)
                pass
            elif token in [23]:
                self.enterOuterAlt(localctx, 2)
                self.state = 227
                self.match(PiettoParser.NOT)
                self.state = 228
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
            self.state = 231
            self.match(PiettoParser.LPAREN)
            self.state = 243
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 7890508177465360) != 0):
                self.state = 232
                self.typeArgument()
                self.state = 237
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,20,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 233
                        self.match(PiettoParser.COMMA)
                        self.state = 234
                        self.typeArgument() 
                    self.state = 239
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,20,self._ctx)

                self.state = 241
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==45:
                    self.state = 240
                    self.match(PiettoParser.COMMA)




            self.state = 245
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
            self.state = 252
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,23,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 247
                self.typeArgumentName()
                self.state = 248
                self.match(PiettoParser.ASSIGN)
                self.state = 249
                self.expression()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 251
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
            self.state = 254
            _la = self._input.LA(1)
            if not(_la==4 or _la==52):
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
            self.state = 256
            self.match(PiettoParser.ENUM)
            self.state = 257
            self.match(PiettoParser.IDENTIFIER)
            self.state = 258
            self.match(PiettoParser.COLON)
            self.state = 259
            self.match(PiettoParser.NEWLINE)
            self.state = 263
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==53:
                self.state = 260
                self.match(PiettoParser.NEWLINE)
                self.state = 265
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 266
            self.match(PiettoParser.INDENT)
            self.state = 267
            self.enumBody()
            self.state = 268
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
            self.state = 272 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 272
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [52]:
                    self.state = 270
                    self.enumItem()
                    pass
                elif token in [53]:
                    self.state = 271
                    self.match(PiettoParser.NEWLINE)
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 274 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==52 or _la==53):
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
            self.state = 276
            self.match(PiettoParser.IDENTIFIER)
            self.state = 277
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
            self.state = 279
            self.match(PiettoParser.CONSTRAINT)
            self.state = 280
            self.match(PiettoParser.IDENTIFIER)
            self.state = 281
            self.match(PiettoParser.LPAREN)
            self.state = 283
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==52:
                self.state = 282
                self.parameterList()


            self.state = 285
            self.match(PiettoParser.RPAREN)
            self.state = 286
            self.match(PiettoParser.ARROW)
            self.state = 287
            self.typeExpression()
            self.state = 288
            self.match(PiettoParser.COLON)
            self.state = 289
            self.match(PiettoParser.NEWLINE)
            self.state = 293
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==53:
                self.state = 290
                self.match(PiettoParser.NEWLINE)
                self.state = 295
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 296
            self.match(PiettoParser.INDENT)
            self.state = 297
            self.constraintBody()
            self.state = 298
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
            self.state = 300
            self.parameter()
            self.state = 305
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,29,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 301
                    self.match(PiettoParser.COMMA)
                    self.state = 302
                    self.parameter() 
                self.state = 307
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,29,self._ctx)

            self.state = 309
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==45:
                self.state = 308
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
            self.state = 311
            self.match(PiettoParser.IDENTIFIER)
            self.state = 312
            self.match(PiettoParser.COLON)
            self.state = 313
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
            self.state = 318
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==53:
                self.state = 315
                self.match(PiettoParser.NEWLINE)
                self.state = 320
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 321
            self.expression()
            self.state = 322
            self.match(PiettoParser.NEWLINE)
            self.state = 326
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==53:
                self.state = 323
                self.match(PiettoParser.NEWLINE)
                self.state = 328
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
            self.state = 329
            self.match(PiettoParser.DERIVE)
            self.state = 330
            self.match(PiettoParser.IDENTIFIER)
            self.state = 331
            self.match(PiettoParser.LPAREN)
            self.state = 333
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==52:
                self.state = 332
                self.parameterList()


            self.state = 335
            self.match(PiettoParser.RPAREN)
            self.state = 336
            self.match(PiettoParser.ARROW)
            self.state = 337
            self.typeExpression()
            self.state = 338
            self.match(PiettoParser.COLON)
            self.state = 339
            self.match(PiettoParser.NEWLINE)
            self.state = 343
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==53:
                self.state = 340
                self.match(PiettoParser.NEWLINE)
                self.state = 345
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 346
            self.match(PiettoParser.INDENT)
            self.state = 347
            self.deriveBody()
            self.state = 348
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
            self.state = 353
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==53:
                self.state = 350
                self.match(PiettoParser.NEWLINE)
                self.state = 355
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 356
            self.expression()
            self.state = 357
            self.match(PiettoParser.NEWLINE)
            self.state = 361
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==53:
                self.state = 358
                self.match(PiettoParser.NEWLINE)
                self.state = 363
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
            self.state = 364
            self.match(PiettoParser.SHAPE)
            self.state = 365
            self.match(PiettoParser.IDENTIFIER)
            self.state = 366
            self.match(PiettoParser.COLON)
            self.state = 367
            self.match(PiettoParser.NEWLINE)
            self.state = 371
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==53:
                self.state = 368
                self.match(PiettoParser.NEWLINE)
                self.state = 373
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 374
            self.match(PiettoParser.INDENT)
            self.state = 375
            self.shapeBody()
            self.state = 376
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
            self.state = 381
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==53:
                self.state = 378
                self.match(PiettoParser.NEWLINE)
                self.state = 383
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 384
            self.shapeItem()
            self.state = 389
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 13510798882201600) != 0):
                self.state = 387
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [13, 14, 16, 52]:
                    self.state = 385
                    self.shapeItem()
                    pass
                elif token in [53]:
                    self.state = 386
                    self.match(PiettoParser.NEWLINE)
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 391
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


        def uniqueDefinition(self):
            return self.getTypedRuleContext(PiettoParser.UniqueDefinitionContext,0)


        def indexDefinition(self):
            return self.getTypedRuleContext(PiettoParser.IndexDefinitionContext,0)


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
            self.state = 396
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [52]:
                self.enterOuterAlt(localctx, 1)
                self.state = 392
                self.fieldDefinition()
                pass
            elif token in [13]:
                self.enterOuterAlt(localctx, 2)
                self.state = 393
                self.checkDefinition()
                pass
            elif token in [14]:
                self.enterOuterAlt(localctx, 3)
                self.state = 394
                self.uniqueDefinition()
                pass
            elif token in [16]:
                self.enterOuterAlt(localctx, 4)
                self.state = 395
                self.indexDefinition()
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
            self.state = 398
            self.match(PiettoParser.IDENTIFIER)
            self.state = 399
            self.match(PiettoParser.COLON)
            self.state = 400
            self.typeExpression()
            self.state = 402
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==11:
                self.state = 401
                self.fieldDeriveClause()


            self.state = 407
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==18 or _la==42:
                self.state = 404
                self.fieldModifier()
                self.state = 409
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 410
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
            self.state = 412
            self.match(PiettoParser.DERIVE)
            self.state = 413
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
            self.state = 417
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [42]:
                self.enterOuterAlt(localctx, 1)
                self.state = 415
                self.annotation()
                pass
            elif token in [18]:
                self.enterOuterAlt(localctx, 2)
                self.state = 416
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
            self.state = 419
            self.match(PiettoParser.AT)
            self.state = 420
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
            self.state = 422
            self.match(PiettoParser.ENSURE)
            self.state = 423
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
            self.state = 425
            self.match(PiettoParser.CHECK)
            self.state = 426
            self.match(PiettoParser.IDENTIFIER)
            self.state = 427
            self.match(PiettoParser.COLON)
            self.state = 428
            self.match(PiettoParser.NEWLINE)
            self.state = 432
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==53:
                self.state = 429
                self.match(PiettoParser.NEWLINE)
                self.state = 434
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 435
            self.match(PiettoParser.INDENT)
            self.state = 436
            self.checkBody()
            self.state = 437
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
            self.state = 442
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==53:
                self.state = 439
                self.match(PiettoParser.NEWLINE)
                self.state = 444
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 445
            self.expression()
            self.state = 446
            self.match(PiettoParser.NEWLINE)
            self.state = 450
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==53:
                self.state = 447
                self.match(PiettoParser.NEWLINE)
                self.state = 452
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class UniqueDefinitionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def UNIQUE(self):
            return self.getToken(PiettoParser.UNIQUE, 0)

        def IDENTIFIER(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.IDENTIFIER)
            else:
                return self.getToken(PiettoParser.IDENTIFIER, i)

        def ON(self):
            return self.getToken(PiettoParser.ON, 0)

        def NEWLINE(self):
            return self.getToken(PiettoParser.NEWLINE, 0)

        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.COMMA)
            else:
                return self.getToken(PiettoParser.COMMA, i)

        def getRuleIndex(self):
            return PiettoParser.RULE_uniqueDefinition

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitUniqueDefinition" ):
                return visitor.visitUniqueDefinition(self)
            else:
                return visitor.visitChildren(self)




    def uniqueDefinition(self):

        localctx = PiettoParser.UniqueDefinitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 70, self.RULE_uniqueDefinition)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 453
            self.match(PiettoParser.UNIQUE)
            self.state = 454
            self.match(PiettoParser.IDENTIFIER)
            self.state = 455
            self.match(PiettoParser.ON)
            self.state = 456
            self.match(PiettoParser.IDENTIFIER)
            self.state = 461
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==45:
                self.state = 457
                self.match(PiettoParser.COMMA)
                self.state = 458
                self.match(PiettoParser.IDENTIFIER)
                self.state = 463
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 464
            self.match(PiettoParser.NEWLINE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class IndexDefinitionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def INDEX(self):
            return self.getToken(PiettoParser.INDEX, 0)

        def IDENTIFIER(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.IDENTIFIER)
            else:
                return self.getToken(PiettoParser.IDENTIFIER, i)

        def ON(self):
            return self.getToken(PiettoParser.ON, 0)

        def NEWLINE(self):
            return self.getToken(PiettoParser.NEWLINE, 0)

        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.COMMA)
            else:
                return self.getToken(PiettoParser.COMMA, i)

        def WHEN(self):
            return self.getToken(PiettoParser.WHEN, 0)

        def expression(self):
            return self.getTypedRuleContext(PiettoParser.ExpressionContext,0)


        def getRuleIndex(self):
            return PiettoParser.RULE_indexDefinition

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIndexDefinition" ):
                return visitor.visitIndexDefinition(self)
            else:
                return visitor.visitChildren(self)




    def indexDefinition(self):

        localctx = PiettoParser.IndexDefinitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 72, self.RULE_indexDefinition)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 466
            self.match(PiettoParser.INDEX)
            self.state = 467
            self.match(PiettoParser.IDENTIFIER)
            self.state = 468
            self.match(PiettoParser.ON)
            self.state = 469
            self.match(PiettoParser.IDENTIFIER)
            self.state = 474
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==45:
                self.state = 470
                self.match(PiettoParser.COMMA)
                self.state = 471
                self.match(PiettoParser.IDENTIFIER)
                self.state = 476
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 479
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==17:
                self.state = 477
                self.match(PiettoParser.WHEN)
                self.state = 478
                self.expression()


            self.state = 481
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
        self.enterRule(localctx, 74, self.RULE_expression)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 483
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
        self.enterRule(localctx, 76, self.RULE_orExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 485
            self.andExpression()
            self.state = 490
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==21:
                self.state = 486
                self.match(PiettoParser.OR)
                self.state = 487
                self.andExpression()
                self.state = 492
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
        self.enterRule(localctx, 78, self.RULE_andExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 493
            self.comparisonExpression()
            self.state = 498
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==20:
                self.state = 494
                self.match(PiettoParser.AND)
                self.state = 495
                self.comparisonExpression()
                self.state = 500
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
        self.enterRule(localctx, 80, self.RULE_comparisonExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 501
            self.additiveExpression()
            self.state = 515
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [26, 29, 30, 31, 32, 33, 34]:
                self.state = 502
                self.comparisonOperator()
                self.state = 503
                self.additiveExpression()
                pass
            elif token in [25]:
                self.state = 505
                self.match(PiettoParser.BETWEEN)
                self.state = 506
                self.additiveExpression()
                self.state = 507
                self.match(PiettoParser.AND)
                self.state = 508
                self.additiveExpression()
                pass
            elif token in [22]:
                self.state = 510
                self.match(PiettoParser.IS)
                self.state = 512
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==23:
                    self.state = 511
                    self.match(PiettoParser.NOT)


                self.state = 514
                self.match(PiettoParser.NULL)
                pass
            elif token in [18, 20, 21, 42, 44, 45, 53]:
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
        self.enterRule(localctx, 82, self.RULE_comparisonOperator)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 517
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 33889976320) != 0)):
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
        self.enterRule(localctx, 84, self.RULE_additiveExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 519
            self.multiplicativeExpression()
            self.state = 524
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==37 or _la==38:
                self.state = 520
                _la = self._input.LA(1)
                if not(_la==37 or _la==38):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 521
                self.multiplicativeExpression()
                self.state = 526
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
        self.enterRule(localctx, 86, self.RULE_multiplicativeExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 527
            self.unaryExpression()
            self.state = 532
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 3848290697216) != 0):
                self.state = 528
                _la = self._input.LA(1)
                if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 3848290697216) != 0)):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 529
                self.unaryExpression()
                self.state = 534
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
        self.enterRule(localctx, 88, self.RULE_unaryExpression)
        self._la = 0 # Token type
        try:
            self.state = 538
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [37, 38]:
                self.enterOuterAlt(localctx, 1)
                self.state = 535
                _la = self._input.LA(1)
                if not(_la==37 or _la==38):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 536
                self.unaryExpression()
                pass
            elif token in [13, 14, 15, 16, 17, 24, 27, 28, 43, 50, 51, 52]:
                self.enterOuterAlt(localctx, 2)
                self.state = 537
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
        self.enterRule(localctx, 90, self.RULE_primaryExpression)
        self._la = 0 # Token type
        try:
            self.state = 549
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [24, 27, 28, 50, 51]:
                self.enterOuterAlt(localctx, 1)
                self.state = 540
                self.literal()
                pass
            elif token in [13, 14, 15, 16, 17, 52]:
                self.enterOuterAlt(localctx, 2)
                self.state = 541
                self.dottedName()
                self.state = 543
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==43:
                    self.state = 542
                    self.callSuffix()


                pass
            elif token in [43]:
                self.enterOuterAlt(localctx, 3)
                self.state = 545
                self.match(PiettoParser.LPAREN)
                self.state = 546
                self.expression()
                self.state = 547
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
        self.enterRule(localctx, 92, self.RULE_dottedName)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 551
            self.namePart()
            self.state = 556
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==46:
                self.state = 552
                self.match(PiettoParser.DOT)
                self.state = 553
                self.namePart()
                self.state = 558
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

        def UNIQUE(self):
            return self.getToken(PiettoParser.UNIQUE, 0)

        def ON(self):
            return self.getToken(PiettoParser.ON, 0)

        def INDEX(self):
            return self.getToken(PiettoParser.INDEX, 0)

        def WHEN(self):
            return self.getToken(PiettoParser.WHEN, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_namePart

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNamePart" ):
                return visitor.visitNamePart(self)
            else:
                return visitor.visitChildren(self)




    def namePart(self):

        localctx = PiettoParser.NamePartContext(self, self._ctx, self.state)
        self.enterRule(localctx, 94, self.RULE_namePart)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 559
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 4503599627624448) != 0)):
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
        self.enterRule(localctx, 96, self.RULE_callSuffix)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 561
            self.match(PiettoParser.LPAREN)
            self.state = 573
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 7890508177465344) != 0):
                self.state = 562
                self.expression()
                self.state = 567
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,61,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 563
                        self.match(PiettoParser.COMMA)
                        self.state = 564
                        self.expression() 
                    self.state = 569
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,61,self._ctx)

                self.state = 571
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==45:
                    self.state = 570
                    self.match(PiettoParser.COMMA)




            self.state = 575
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
        self.enterRule(localctx, 98, self.RULE_literal)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 577
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 3377700139958272) != 0)):
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





