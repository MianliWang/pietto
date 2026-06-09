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
        4,1,64,713,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,2,31,7,31,2,32,7,32,2,33,
        7,33,2,34,7,34,2,35,7,35,2,36,7,36,2,37,7,37,2,38,7,38,2,39,7,39,
        2,40,7,40,2,41,7,41,2,42,7,42,2,43,7,43,2,44,7,44,2,45,7,45,2,46,
        7,46,2,47,7,47,2,48,7,48,2,49,7,49,2,50,7,50,2,51,7,51,2,52,7,52,
        2,53,7,53,2,54,7,54,2,55,7,55,2,56,7,56,2,57,7,57,2,58,7,58,1,0,
        5,0,120,8,0,10,0,12,0,123,9,0,1,0,3,0,126,8,0,1,0,5,0,129,8,0,10,
        0,12,0,132,9,0,1,0,1,0,5,0,136,8,0,10,0,12,0,139,9,0,5,0,141,8,0,
        10,0,12,0,144,9,0,1,0,1,0,1,1,1,1,3,1,150,8,1,1,1,3,1,153,8,1,1,
        1,3,1,156,8,1,1,1,1,1,3,1,160,8,1,1,1,3,1,163,8,1,1,1,1,1,3,1,167,
        8,1,1,1,3,1,170,8,1,1,2,1,2,1,2,1,2,1,3,1,3,1,3,1,3,1,4,1,4,1,4,
        1,4,1,5,1,5,1,5,1,5,1,6,1,6,1,6,1,6,1,6,1,6,1,6,1,6,3,6,196,8,6,
        1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,
        1,7,1,7,1,7,1,7,1,7,5,7,219,8,7,10,7,12,7,222,9,7,1,7,1,7,1,7,1,
        7,3,7,228,8,7,1,8,1,8,4,8,232,8,8,11,8,12,8,233,1,9,1,9,1,9,1,9,
        1,10,1,10,3,10,242,8,10,1,11,1,11,3,11,246,8,11,1,12,1,12,1,12,3,
        12,251,8,12,1,13,1,13,1,13,1,13,5,13,257,8,13,10,13,12,13,260,9,
        13,1,13,3,13,263,8,13,3,13,265,8,13,1,13,1,13,1,14,1,14,1,14,1,14,
        1,14,3,14,274,8,14,1,15,1,15,1,16,1,16,1,16,1,16,1,16,5,16,283,8,
        16,10,16,12,16,286,9,16,1,16,1,16,1,16,1,16,1,17,1,17,4,17,294,8,
        17,11,17,12,17,295,1,18,1,18,1,18,1,19,1,19,1,19,1,19,3,19,305,8,
        19,1,19,1,19,1,19,1,19,1,19,1,19,5,19,313,8,19,10,19,12,19,316,9,
        19,1,19,1,19,1,19,1,19,1,20,1,20,1,20,5,20,325,8,20,10,20,12,20,
        328,9,20,1,20,3,20,331,8,20,1,21,1,21,1,21,1,21,1,22,5,22,338,8,
        22,10,22,12,22,341,9,22,1,22,1,22,1,22,5,22,346,8,22,10,22,12,22,
        349,9,22,1,23,1,23,1,23,1,23,3,23,355,8,23,1,23,1,23,1,23,1,23,1,
        23,1,23,5,23,363,8,23,10,23,12,23,366,9,23,1,23,1,23,1,23,1,23,1,
        24,5,24,373,8,24,10,24,12,24,376,9,24,1,24,1,24,1,24,5,24,381,8,
        24,10,24,12,24,384,9,24,1,25,1,25,1,25,1,25,1,25,5,25,391,8,25,10,
        25,12,25,394,9,25,1,25,1,25,1,25,1,25,1,26,5,26,401,8,26,10,26,12,
        26,404,9,26,1,26,1,26,1,26,5,26,409,8,26,10,26,12,26,412,9,26,1,
        27,1,27,1,27,1,27,3,27,418,8,27,1,28,1,28,1,28,1,28,3,28,424,8,28,
        1,28,5,28,427,8,28,10,28,12,28,430,9,28,1,28,1,28,1,29,1,29,1,29,
        1,30,1,30,3,30,439,8,30,1,31,1,31,1,31,1,32,1,32,1,32,1,33,1,33,
        1,33,1,33,1,33,5,33,452,8,33,10,33,12,33,455,9,33,1,33,1,33,1,33,
        1,33,1,34,5,34,462,8,34,10,34,12,34,465,9,34,1,34,1,34,1,34,5,34,
        470,8,34,10,34,12,34,473,9,34,1,35,1,35,1,35,1,35,1,35,1,35,5,35,
        481,8,35,10,35,12,35,484,9,35,1,35,1,35,1,36,1,36,1,36,1,36,1,36,
        1,36,5,36,494,8,36,10,36,12,36,497,9,36,1,36,1,36,3,36,501,8,36,
        1,36,1,36,1,37,1,37,1,37,1,37,3,37,509,8,37,1,37,1,37,1,37,1,37,
        1,38,1,38,1,38,1,38,1,38,5,38,520,8,38,10,38,12,38,523,9,38,1,38,
        1,38,1,38,1,38,1,39,1,39,1,39,1,39,1,39,5,39,534,8,39,10,39,12,39,
        537,9,39,1,39,1,39,1,39,1,39,1,40,5,40,544,8,40,10,40,12,40,547,
        9,40,1,40,1,40,5,40,551,8,40,10,40,12,40,554,9,40,1,40,3,40,557,
        8,40,1,40,5,40,560,8,40,10,40,12,40,563,9,40,1,40,1,40,5,40,567,
        8,40,10,40,12,40,570,9,40,1,41,1,41,1,41,1,41,1,42,1,42,1,42,1,42,
        1,43,1,43,1,43,1,43,5,43,584,8,43,10,43,12,43,587,9,43,1,43,1,43,
        1,43,1,43,1,44,5,44,594,8,44,10,44,12,44,597,9,44,1,44,1,44,1,44,
        5,44,602,8,44,10,44,12,44,605,9,44,1,45,1,45,1,45,1,45,1,45,1,45,
        1,45,1,45,3,45,615,8,45,1,46,1,46,1,47,1,47,1,47,5,47,622,8,47,10,
        47,12,47,625,9,47,1,48,1,48,1,48,5,48,630,8,48,10,48,12,48,633,9,
        48,1,49,1,49,1,49,1,49,1,49,1,49,1,49,1,49,1,49,1,49,1,49,3,49,646,
        8,49,1,49,3,49,649,8,49,1,50,1,50,1,51,1,51,1,51,5,51,656,8,51,10,
        51,12,51,659,9,51,1,52,1,52,1,52,5,52,664,8,52,10,52,12,52,667,9,
        52,1,53,1,53,1,53,3,53,672,8,53,1,54,1,54,1,54,3,54,677,8,54,1,54,
        1,54,1,54,1,54,3,54,683,8,54,1,55,1,55,1,55,5,55,688,8,55,10,55,
        12,55,691,9,55,1,56,1,56,1,57,1,57,1,57,1,57,5,57,699,8,57,10,57,
        12,57,702,9,57,1,57,3,57,705,8,57,3,57,707,8,57,1,57,1,57,1,58,1,
        58,1,58,0,0,59,0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,
        36,38,40,42,44,46,48,50,52,54,56,58,60,62,64,66,68,70,72,74,76,78,
        80,82,84,86,88,90,92,94,96,98,100,102,104,106,108,110,112,114,116,
        0,7,1,0,5,7,2,0,4,4,58,58,2,0,32,32,35,40,1,0,43,44,1,0,45,47,3,
        0,13,23,28,28,58,58,3,0,30,30,33,34,56,57,744,0,121,1,0,0,0,2,169,
        1,0,0,0,4,171,1,0,0,0,6,175,1,0,0,0,8,179,1,0,0,0,10,183,1,0,0,0,
        12,195,1,0,0,0,14,227,1,0,0,0,16,231,1,0,0,0,18,235,1,0,0,0,20,239,
        1,0,0,0,22,243,1,0,0,0,24,250,1,0,0,0,26,252,1,0,0,0,28,273,1,0,
        0,0,30,275,1,0,0,0,32,277,1,0,0,0,34,293,1,0,0,0,36,297,1,0,0,0,
        38,300,1,0,0,0,40,321,1,0,0,0,42,332,1,0,0,0,44,339,1,0,0,0,46,350,
        1,0,0,0,48,374,1,0,0,0,50,385,1,0,0,0,52,402,1,0,0,0,54,417,1,0,
        0,0,56,419,1,0,0,0,58,433,1,0,0,0,60,438,1,0,0,0,62,440,1,0,0,0,
        64,443,1,0,0,0,66,446,1,0,0,0,68,463,1,0,0,0,70,474,1,0,0,0,72,487,
        1,0,0,0,74,504,1,0,0,0,76,514,1,0,0,0,78,528,1,0,0,0,80,545,1,0,
        0,0,82,571,1,0,0,0,84,575,1,0,0,0,86,579,1,0,0,0,88,595,1,0,0,0,
        90,614,1,0,0,0,92,616,1,0,0,0,94,618,1,0,0,0,96,626,1,0,0,0,98,634,
        1,0,0,0,100,650,1,0,0,0,102,652,1,0,0,0,104,660,1,0,0,0,106,671,
        1,0,0,0,108,682,1,0,0,0,110,684,1,0,0,0,112,692,1,0,0,0,114,694,
        1,0,0,0,116,710,1,0,0,0,118,120,5,59,0,0,119,118,1,0,0,0,120,123,
        1,0,0,0,121,119,1,0,0,0,121,122,1,0,0,0,122,125,1,0,0,0,123,121,
        1,0,0,0,124,126,3,2,1,0,125,124,1,0,0,0,125,126,1,0,0,0,126,130,
        1,0,0,0,127,129,5,59,0,0,128,127,1,0,0,0,129,132,1,0,0,0,130,128,
        1,0,0,0,130,131,1,0,0,0,131,142,1,0,0,0,132,130,1,0,0,0,133,137,
        3,12,6,0,134,136,5,59,0,0,135,134,1,0,0,0,136,139,1,0,0,0,137,135,
        1,0,0,0,137,138,1,0,0,0,138,141,1,0,0,0,139,137,1,0,0,0,140,133,
        1,0,0,0,141,144,1,0,0,0,142,140,1,0,0,0,142,143,1,0,0,0,143,145,
        1,0,0,0,144,142,1,0,0,0,145,146,5,0,0,1,146,1,1,0,0,0,147,149,3,
        4,2,0,148,150,3,6,3,0,149,148,1,0,0,0,149,150,1,0,0,0,150,152,1,
        0,0,0,151,153,3,8,4,0,152,151,1,0,0,0,152,153,1,0,0,0,153,155,1,
        0,0,0,154,156,3,10,5,0,155,154,1,0,0,0,155,156,1,0,0,0,156,170,1,
        0,0,0,157,159,3,6,3,0,158,160,3,8,4,0,159,158,1,0,0,0,159,160,1,
        0,0,0,160,162,1,0,0,0,161,163,3,10,5,0,162,161,1,0,0,0,162,163,1,
        0,0,0,163,170,1,0,0,0,164,166,3,8,4,0,165,167,3,10,5,0,166,165,1,
        0,0,0,166,167,1,0,0,0,167,170,1,0,0,0,168,170,3,10,5,0,169,147,1,
        0,0,0,169,157,1,0,0,0,169,164,1,0,0,0,169,168,1,0,0,0,170,3,1,0,
        0,0,171,172,5,1,0,0,172,173,5,56,0,0,173,174,5,59,0,0,174,5,1,0,
        0,0,175,176,5,2,0,0,176,177,7,0,0,0,177,178,5,59,0,0,178,7,1,0,0,
        0,179,180,5,3,0,0,180,181,5,58,0,0,181,182,5,59,0,0,182,9,1,0,0,
        0,183,184,5,4,0,0,184,185,5,58,0,0,185,186,5,59,0,0,186,11,1,0,0,
        0,187,196,3,14,7,0,188,196,3,32,16,0,189,196,3,38,19,0,190,196,3,
        46,23,0,191,196,3,50,25,0,192,196,3,74,37,0,193,196,3,76,38,0,194,
        196,3,78,39,0,195,187,1,0,0,0,195,188,1,0,0,0,195,189,1,0,0,0,195,
        190,1,0,0,0,195,191,1,0,0,0,195,192,1,0,0,0,195,193,1,0,0,0,195,
        194,1,0,0,0,196,13,1,0,0,0,197,198,5,8,0,0,198,199,5,58,0,0,199,
        200,5,41,0,0,200,201,3,20,10,0,201,202,5,59,0,0,202,228,1,0,0,0,
        203,204,5,8,0,0,204,205,5,58,0,0,205,206,5,41,0,0,206,207,3,20,10,
        0,207,208,5,24,0,0,208,209,3,92,46,0,209,210,5,59,0,0,210,228,1,
        0,0,0,211,212,5,8,0,0,212,213,5,58,0,0,213,214,5,41,0,0,214,215,
        3,20,10,0,215,216,5,53,0,0,216,220,5,59,0,0,217,219,5,59,0,0,218,
        217,1,0,0,0,219,222,1,0,0,0,220,218,1,0,0,0,220,221,1,0,0,0,221,
        223,1,0,0,0,222,220,1,0,0,0,223,224,5,63,0,0,224,225,3,16,8,0,225,
        226,5,64,0,0,226,228,1,0,0,0,227,197,1,0,0,0,227,203,1,0,0,0,227,
        211,1,0,0,0,228,15,1,0,0,0,229,232,3,18,9,0,230,232,5,59,0,0,231,
        229,1,0,0,0,231,230,1,0,0,0,232,233,1,0,0,0,233,231,1,0,0,0,233,
        234,1,0,0,0,234,17,1,0,0,0,235,236,5,24,0,0,236,237,3,92,46,0,237,
        238,5,59,0,0,238,19,1,0,0,0,239,241,3,22,11,0,240,242,3,24,12,0,
        241,240,1,0,0,0,241,242,1,0,0,0,242,21,1,0,0,0,243,245,5,58,0,0,
        244,246,3,26,13,0,245,244,1,0,0,0,245,246,1,0,0,0,246,23,1,0,0,0,
        247,251,5,25,0,0,248,249,5,29,0,0,249,251,5,30,0,0,250,247,1,0,0,
        0,250,248,1,0,0,0,251,25,1,0,0,0,252,264,5,49,0,0,253,258,3,28,14,
        0,254,255,5,51,0,0,255,257,3,28,14,0,256,254,1,0,0,0,257,260,1,0,
        0,0,258,256,1,0,0,0,258,259,1,0,0,0,259,262,1,0,0,0,260,258,1,0,
        0,0,261,263,5,51,0,0,262,261,1,0,0,0,262,263,1,0,0,0,263,265,1,0,
        0,0,264,253,1,0,0,0,264,265,1,0,0,0,265,266,1,0,0,0,266,267,5,50,
        0,0,267,27,1,0,0,0,268,269,3,30,15,0,269,270,5,41,0,0,270,271,3,
        92,46,0,271,274,1,0,0,0,272,274,3,92,46,0,273,268,1,0,0,0,273,272,
        1,0,0,0,274,29,1,0,0,0,275,276,7,1,0,0,276,31,1,0,0,0,277,278,5,
        9,0,0,278,279,5,58,0,0,279,280,5,53,0,0,280,284,5,59,0,0,281,283,
        5,59,0,0,282,281,1,0,0,0,283,286,1,0,0,0,284,282,1,0,0,0,284,285,
        1,0,0,0,285,287,1,0,0,0,286,284,1,0,0,0,287,288,5,63,0,0,288,289,
        3,34,17,0,289,290,5,64,0,0,290,33,1,0,0,0,291,294,3,36,18,0,292,
        294,5,59,0,0,293,291,1,0,0,0,293,292,1,0,0,0,294,295,1,0,0,0,295,
        293,1,0,0,0,295,296,1,0,0,0,296,35,1,0,0,0,297,298,5,58,0,0,298,
        299,5,59,0,0,299,37,1,0,0,0,300,301,5,10,0,0,301,302,5,58,0,0,302,
        304,5,49,0,0,303,305,3,40,20,0,304,303,1,0,0,0,304,305,1,0,0,0,305,
        306,1,0,0,0,306,307,5,50,0,0,307,308,5,42,0,0,308,309,3,20,10,0,
        309,310,5,53,0,0,310,314,5,59,0,0,311,313,5,59,0,0,312,311,1,0,0,
        0,313,316,1,0,0,0,314,312,1,0,0,0,314,315,1,0,0,0,315,317,1,0,0,
        0,316,314,1,0,0,0,317,318,5,63,0,0,318,319,3,44,22,0,319,320,5,64,
        0,0,320,39,1,0,0,0,321,326,3,42,21,0,322,323,5,51,0,0,323,325,3,
        42,21,0,324,322,1,0,0,0,325,328,1,0,0,0,326,324,1,0,0,0,326,327,
        1,0,0,0,327,330,1,0,0,0,328,326,1,0,0,0,329,331,5,51,0,0,330,329,
        1,0,0,0,330,331,1,0,0,0,331,41,1,0,0,0,332,333,5,58,0,0,333,334,
        5,53,0,0,334,335,3,20,10,0,335,43,1,0,0,0,336,338,5,59,0,0,337,336,
        1,0,0,0,338,341,1,0,0,0,339,337,1,0,0,0,339,340,1,0,0,0,340,342,
        1,0,0,0,341,339,1,0,0,0,342,343,3,92,46,0,343,347,5,59,0,0,344,346,
        5,59,0,0,345,344,1,0,0,0,346,349,1,0,0,0,347,345,1,0,0,0,347,348,
        1,0,0,0,348,45,1,0,0,0,349,347,1,0,0,0,350,351,5,11,0,0,351,352,
        5,58,0,0,352,354,5,49,0,0,353,355,3,40,20,0,354,353,1,0,0,0,354,
        355,1,0,0,0,355,356,1,0,0,0,356,357,5,50,0,0,357,358,5,42,0,0,358,
        359,3,20,10,0,359,360,5,53,0,0,360,364,5,59,0,0,361,363,5,59,0,0,
        362,361,1,0,0,0,363,366,1,0,0,0,364,362,1,0,0,0,364,365,1,0,0,0,
        365,367,1,0,0,0,366,364,1,0,0,0,367,368,5,63,0,0,368,369,3,48,24,
        0,369,370,5,64,0,0,370,47,1,0,0,0,371,373,5,59,0,0,372,371,1,0,0,
        0,373,376,1,0,0,0,374,372,1,0,0,0,374,375,1,0,0,0,375,377,1,0,0,
        0,376,374,1,0,0,0,377,378,3,92,46,0,378,382,5,59,0,0,379,381,5,59,
        0,0,380,379,1,0,0,0,381,384,1,0,0,0,382,380,1,0,0,0,382,383,1,0,
        0,0,383,49,1,0,0,0,384,382,1,0,0,0,385,386,5,12,0,0,386,387,5,58,
        0,0,387,388,5,53,0,0,388,392,5,59,0,0,389,391,5,59,0,0,390,389,1,
        0,0,0,391,394,1,0,0,0,392,390,1,0,0,0,392,393,1,0,0,0,393,395,1,
        0,0,0,394,392,1,0,0,0,395,396,5,63,0,0,396,397,3,52,26,0,397,398,
        5,64,0,0,398,51,1,0,0,0,399,401,5,59,0,0,400,399,1,0,0,0,401,404,
        1,0,0,0,402,400,1,0,0,0,402,403,1,0,0,0,403,405,1,0,0,0,404,402,
        1,0,0,0,405,410,3,54,27,0,406,409,3,54,27,0,407,409,5,59,0,0,408,
        406,1,0,0,0,408,407,1,0,0,0,409,412,1,0,0,0,410,408,1,0,0,0,410,
        411,1,0,0,0,411,53,1,0,0,0,412,410,1,0,0,0,413,418,3,56,28,0,414,
        418,3,66,33,0,415,418,3,70,35,0,416,418,3,72,36,0,417,413,1,0,0,
        0,417,414,1,0,0,0,417,415,1,0,0,0,417,416,1,0,0,0,418,55,1,0,0,0,
        419,420,5,58,0,0,420,421,5,53,0,0,421,423,3,20,10,0,422,424,3,58,
        29,0,423,422,1,0,0,0,423,424,1,0,0,0,424,428,1,0,0,0,425,427,3,60,
        30,0,426,425,1,0,0,0,427,430,1,0,0,0,428,426,1,0,0,0,428,429,1,0,
        0,0,429,431,1,0,0,0,430,428,1,0,0,0,431,432,5,59,0,0,432,57,1,0,
        0,0,433,434,5,11,0,0,434,435,3,92,46,0,435,59,1,0,0,0,436,439,3,
        62,31,0,437,439,3,64,32,0,438,436,1,0,0,0,438,437,1,0,0,0,439,61,
        1,0,0,0,440,441,5,48,0,0,441,442,5,58,0,0,442,63,1,0,0,0,443,444,
        5,24,0,0,444,445,3,92,46,0,445,65,1,0,0,0,446,447,5,13,0,0,447,448,
        5,58,0,0,448,449,5,53,0,0,449,453,5,59,0,0,450,452,5,59,0,0,451,
        450,1,0,0,0,452,455,1,0,0,0,453,451,1,0,0,0,453,454,1,0,0,0,454,
        456,1,0,0,0,455,453,1,0,0,0,456,457,5,63,0,0,457,458,3,68,34,0,458,
        459,5,64,0,0,459,67,1,0,0,0,460,462,5,59,0,0,461,460,1,0,0,0,462,
        465,1,0,0,0,463,461,1,0,0,0,463,464,1,0,0,0,464,466,1,0,0,0,465,
        463,1,0,0,0,466,467,3,92,46,0,467,471,5,59,0,0,468,470,5,59,0,0,
        469,468,1,0,0,0,470,473,1,0,0,0,471,469,1,0,0,0,471,472,1,0,0,0,
        472,69,1,0,0,0,473,471,1,0,0,0,474,475,5,14,0,0,475,476,5,58,0,0,
        476,477,5,15,0,0,477,482,5,58,0,0,478,479,5,51,0,0,479,481,5,58,
        0,0,480,478,1,0,0,0,481,484,1,0,0,0,482,480,1,0,0,0,482,483,1,0,
        0,0,483,485,1,0,0,0,484,482,1,0,0,0,485,486,5,59,0,0,486,71,1,0,
        0,0,487,488,5,16,0,0,488,489,5,58,0,0,489,490,5,15,0,0,490,495,5,
        58,0,0,491,492,5,51,0,0,492,494,5,58,0,0,493,491,1,0,0,0,494,497,
        1,0,0,0,495,493,1,0,0,0,495,496,1,0,0,0,496,500,1,0,0,0,497,495,
        1,0,0,0,498,499,5,17,0,0,499,501,3,92,46,0,500,498,1,0,0,0,500,501,
        1,0,0,0,501,502,1,0,0,0,502,503,5,59,0,0,503,73,1,0,0,0,504,505,
        5,18,0,0,505,508,5,58,0,0,506,507,5,53,0,0,507,509,5,58,0,0,508,
        506,1,0,0,0,508,509,1,0,0,0,509,510,1,0,0,0,510,511,5,28,0,0,511,
        512,3,92,46,0,512,513,5,59,0,0,513,75,1,0,0,0,514,515,5,19,0,0,515,
        516,5,58,0,0,516,517,5,53,0,0,517,521,5,59,0,0,518,520,5,59,0,0,
        519,518,1,0,0,0,520,523,1,0,0,0,521,519,1,0,0,0,521,522,1,0,0,0,
        522,524,1,0,0,0,523,521,1,0,0,0,524,525,5,63,0,0,525,526,3,80,40,
        0,526,527,5,64,0,0,527,77,1,0,0,0,528,529,5,23,0,0,529,530,5,58,
        0,0,530,531,5,53,0,0,531,535,5,59,0,0,532,534,5,59,0,0,533,532,1,
        0,0,0,534,537,1,0,0,0,535,533,1,0,0,0,535,536,1,0,0,0,536,538,1,
        0,0,0,537,535,1,0,0,0,538,539,5,63,0,0,539,540,3,80,40,0,540,541,
        5,64,0,0,541,79,1,0,0,0,542,544,5,59,0,0,543,542,1,0,0,0,544,547,
        1,0,0,0,545,543,1,0,0,0,545,546,1,0,0,0,546,548,1,0,0,0,547,545,
        1,0,0,0,548,552,3,82,41,0,549,551,5,59,0,0,550,549,1,0,0,0,551,554,
        1,0,0,0,552,550,1,0,0,0,552,553,1,0,0,0,553,556,1,0,0,0,554,552,
        1,0,0,0,555,557,3,84,42,0,556,555,1,0,0,0,556,557,1,0,0,0,557,561,
        1,0,0,0,558,560,5,59,0,0,559,558,1,0,0,0,560,563,1,0,0,0,561,559,
        1,0,0,0,561,562,1,0,0,0,562,564,1,0,0,0,563,561,1,0,0,0,564,568,
        3,86,43,0,565,567,5,59,0,0,566,565,1,0,0,0,567,570,1,0,0,0,568,566,
        1,0,0,0,568,569,1,0,0,0,569,81,1,0,0,0,570,568,1,0,0,0,571,572,5,
        20,0,0,572,573,5,58,0,0,573,574,5,59,0,0,574,83,1,0,0,0,575,576,
        5,21,0,0,576,577,3,92,46,0,577,578,5,59,0,0,578,85,1,0,0,0,579,580,
        5,22,0,0,580,581,5,53,0,0,581,585,5,59,0,0,582,584,5,59,0,0,583,
        582,1,0,0,0,584,587,1,0,0,0,585,583,1,0,0,0,585,586,1,0,0,0,586,
        588,1,0,0,0,587,585,1,0,0,0,588,589,5,63,0,0,589,590,3,88,44,0,590,
        591,5,64,0,0,591,87,1,0,0,0,592,594,5,59,0,0,593,592,1,0,0,0,594,
        597,1,0,0,0,595,593,1,0,0,0,595,596,1,0,0,0,596,598,1,0,0,0,597,
        595,1,0,0,0,598,603,3,90,45,0,599,602,3,90,45,0,600,602,5,59,0,0,
        601,599,1,0,0,0,601,600,1,0,0,0,602,605,1,0,0,0,603,601,1,0,0,0,
        603,604,1,0,0,0,604,89,1,0,0,0,605,603,1,0,0,0,606,607,5,58,0,0,
        607,608,5,41,0,0,608,609,3,92,46,0,609,610,5,59,0,0,610,615,1,0,
        0,0,611,612,3,92,46,0,612,613,5,59,0,0,613,615,1,0,0,0,614,606,1,
        0,0,0,614,611,1,0,0,0,615,91,1,0,0,0,616,617,3,94,47,0,617,93,1,
        0,0,0,618,623,3,96,48,0,619,620,5,27,0,0,620,622,3,96,48,0,621,619,
        1,0,0,0,622,625,1,0,0,0,623,621,1,0,0,0,623,624,1,0,0,0,624,95,1,
        0,0,0,625,623,1,0,0,0,626,631,3,98,49,0,627,628,5,26,0,0,628,630,
        3,98,49,0,629,627,1,0,0,0,630,633,1,0,0,0,631,629,1,0,0,0,631,632,
        1,0,0,0,632,97,1,0,0,0,633,631,1,0,0,0,634,648,3,102,51,0,635,636,
        3,100,50,0,636,637,3,102,51,0,637,649,1,0,0,0,638,639,5,31,0,0,639,
        640,3,102,51,0,640,641,5,26,0,0,641,642,3,102,51,0,642,649,1,0,0,
        0,643,645,5,28,0,0,644,646,5,29,0,0,645,644,1,0,0,0,645,646,1,0,
        0,0,646,647,1,0,0,0,647,649,5,30,0,0,648,635,1,0,0,0,648,638,1,0,
        0,0,648,643,1,0,0,0,648,649,1,0,0,0,649,99,1,0,0,0,650,651,7,2,0,
        0,651,101,1,0,0,0,652,657,3,104,52,0,653,654,7,3,0,0,654,656,3,104,
        52,0,655,653,1,0,0,0,656,659,1,0,0,0,657,655,1,0,0,0,657,658,1,0,
        0,0,658,103,1,0,0,0,659,657,1,0,0,0,660,665,3,106,53,0,661,662,7,
        4,0,0,662,664,3,106,53,0,663,661,1,0,0,0,664,667,1,0,0,0,665,663,
        1,0,0,0,665,666,1,0,0,0,666,105,1,0,0,0,667,665,1,0,0,0,668,669,
        7,3,0,0,669,672,3,106,53,0,670,672,3,108,54,0,671,668,1,0,0,0,671,
        670,1,0,0,0,672,107,1,0,0,0,673,683,3,116,58,0,674,676,3,110,55,
        0,675,677,3,114,57,0,676,675,1,0,0,0,676,677,1,0,0,0,677,683,1,0,
        0,0,678,679,5,49,0,0,679,680,3,92,46,0,680,681,5,50,0,0,681,683,
        1,0,0,0,682,673,1,0,0,0,682,674,1,0,0,0,682,678,1,0,0,0,683,109,
        1,0,0,0,684,689,3,112,56,0,685,686,5,52,0,0,686,688,3,112,56,0,687,
        685,1,0,0,0,688,691,1,0,0,0,689,687,1,0,0,0,689,690,1,0,0,0,690,
        111,1,0,0,0,691,689,1,0,0,0,692,693,7,5,0,0,693,113,1,0,0,0,694,
        706,5,49,0,0,695,700,3,92,46,0,696,697,5,51,0,0,697,699,3,92,46,
        0,698,696,1,0,0,0,699,702,1,0,0,0,700,698,1,0,0,0,700,701,1,0,0,
        0,701,704,1,0,0,0,702,700,1,0,0,0,703,705,5,51,0,0,704,703,1,0,0,
        0,704,705,1,0,0,0,705,707,1,0,0,0,706,695,1,0,0,0,706,707,1,0,0,
        0,707,708,1,0,0,0,708,709,5,50,0,0,709,115,1,0,0,0,710,711,7,6,0,
        0,711,117,1,0,0,0,77,121,125,130,137,142,149,152,155,159,162,166,
        169,195,220,227,231,233,241,245,250,258,262,264,273,284,293,295,
        304,314,326,330,339,347,354,364,374,382,392,402,408,410,417,423,
        428,438,453,463,471,482,495,500,508,521,535,545,552,556,561,568,
        585,595,601,603,614,623,631,645,648,657,665,671,676,682,689,700,
        704,706
    ]

class PiettoParser ( Parser ):

    grammarFileName = "Pietto.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'pietto'", "'mode'", "'dialect'", "'encoding'", 
                     "'loose'", "'checked'", "'strict'", "'type'", "'enum'", 
                     "'constraint'", "'derive'", "'shape'", "'check'", "'unique'", 
                     "'on'", "'index'", "'when'", "'source'", "'table'", 
                     "'from'", "'where'", "'select'", "'query'", "'ensure'", 
                     "'nullable'", "'and'", "'or'", "'is'", "'not'", "'null'", 
                     "'between'", "'like'", "'true'", "'false'", "'=='", 
                     "'!='", "'<='", "'>='", "'<'", "'>'", "'='", "'->'", 
                     "'+'", "'-'", "'*'", "'/'", "'%'", "'@'", "'('", "')'", 
                     "','", "'.'", "':'", "'{'", "'}'" ]

    symbolicNames = [ "<INVALID>", "PIETTO", "MODE", "DIALECT", "ENCODING", 
                      "LOOSE", "CHECKED", "STRICT", "TYPE", "ENUM", "CONSTRAINT", 
                      "DERIVE", "SHAPE", "CHECK", "UNIQUE", "ON", "INDEX", 
                      "WHEN", "SOURCE", "TABLE", "FROM", "WHERE", "SELECT", 
                      "QUERY", "ENSURE", "NULLABLE", "AND", "OR", "IS", 
                      "NOT", "NULL", "BETWEEN", "LIKE", "TRUE", "FALSE", 
                      "EQ", "NE", "LE", "GE", "LT", "GT", "ASSIGN", "ARROW", 
                      "PLUS", "MINUS", "STAR", "SLASH", "PERCENT", "AT", 
                      "LPAREN", "RPAREN", "COMMA", "DOT", "COLON", "LBRACE", 
                      "RBRACE", "NUMBER", "STRING", "IDENTIFIER", "NEWLINE", 
                      "COMMENT", "WS", "UNKNOWN", "INDENT", "DEDENT" ]

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
    RULE_sourceDefinition = 37
    RULE_tableDefinition = 38
    RULE_queryDefinition = 39
    RULE_tableBody = 40
    RULE_fromClause = 41
    RULE_whereClause = 42
    RULE_selectClause = 43
    RULE_selectBody = 44
    RULE_selectItem = 45
    RULE_expression = 46
    RULE_orExpression = 47
    RULE_andExpression = 48
    RULE_comparisonExpression = 49
    RULE_comparisonOperator = 50
    RULE_additiveExpression = 51
    RULE_multiplicativeExpression = 52
    RULE_unaryExpression = 53
    RULE_primaryExpression = 54
    RULE_dottedName = 55
    RULE_namePart = 56
    RULE_callSuffix = 57
    RULE_literal = 58

    ruleNames =  [ "script", "header", "versionDecl", "modeDecl", "dialectDecl", 
                   "encodingDecl", "definition", "typeDefinition", "typeBody", 
                   "ensureClause", "typeExpression", "typeReference", "nullabilityModifier", 
                   "typeArguments", "typeArgument", "typeArgumentName", 
                   "enumDefinition", "enumBody", "enumItem", "constraintDefinition", 
                   "parameterList", "parameter", "constraintBody", "deriveDefinition", 
                   "deriveBody", "shapeDefinition", "shapeBody", "shapeItem", 
                   "fieldDefinition", "fieldDeriveClause", "fieldModifier", 
                   "annotation", "fieldEnsureClause", "checkDefinition", 
                   "checkBody", "uniqueDefinition", "indexDefinition", "sourceDefinition", 
                   "tableDefinition", "queryDefinition", "tableBody", "fromClause", 
                   "whereClause", "selectClause", "selectBody", "selectItem", 
                   "expression", "orExpression", "andExpression", "comparisonExpression", 
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
    SOURCE=18
    TABLE=19
    FROM=20
    WHERE=21
    SELECT=22
    QUERY=23
    ENSURE=24
    NULLABLE=25
    AND=26
    OR=27
    IS=28
    NOT=29
    NULL=30
    BETWEEN=31
    LIKE=32
    TRUE=33
    FALSE=34
    EQ=35
    NE=36
    LE=37
    GE=38
    LT=39
    GT=40
    ASSIGN=41
    ARROW=42
    PLUS=43
    MINUS=44
    STAR=45
    SLASH=46
    PERCENT=47
    AT=48
    LPAREN=49
    RPAREN=50
    COMMA=51
    DOT=52
    COLON=53
    LBRACE=54
    RBRACE=55
    NUMBER=56
    STRING=57
    IDENTIFIER=58
    NEWLINE=59
    COMMENT=60
    WS=61
    UNKNOWN=62
    INDENT=63
    DEDENT=64

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
            self.state = 121
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,0,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 118
                    self.match(PiettoParser.NEWLINE) 
                self.state = 123
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,0,self._ctx)

            self.state = 125
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 30) != 0):
                self.state = 124
                self.header()


            self.state = 130
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 127
                self.match(PiettoParser.NEWLINE)
                self.state = 132
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 142
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 9182976) != 0):
                self.state = 133
                self.definition()
                self.state = 137
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==59:
                    self.state = 134
                    self.match(PiettoParser.NEWLINE)
                    self.state = 139
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 144
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 145
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
            self.state = 169
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [1]:
                self.enterOuterAlt(localctx, 1)
                self.state = 147
                self.versionDecl()
                self.state = 149
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==2:
                    self.state = 148
                    self.modeDecl()


                self.state = 152
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==3:
                    self.state = 151
                    self.dialectDecl()


                self.state = 155
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4:
                    self.state = 154
                    self.encodingDecl()


                pass
            elif token in [2]:
                self.enterOuterAlt(localctx, 2)
                self.state = 157
                self.modeDecl()
                self.state = 159
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==3:
                    self.state = 158
                    self.dialectDecl()


                self.state = 162
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4:
                    self.state = 161
                    self.encodingDecl()


                pass
            elif token in [3]:
                self.enterOuterAlt(localctx, 3)
                self.state = 164
                self.dialectDecl()
                self.state = 166
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4:
                    self.state = 165
                    self.encodingDecl()


                pass
            elif token in [4]:
                self.enterOuterAlt(localctx, 4)
                self.state = 168
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
            self.state = 171
            self.match(PiettoParser.PIETTO)
            self.state = 172
            self.match(PiettoParser.NUMBER)
            self.state = 173
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
            self.state = 175
            self.match(PiettoParser.MODE)
            self.state = 176
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 224) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 177
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
            self.state = 179
            self.match(PiettoParser.DIALECT)
            self.state = 180
            self.match(PiettoParser.IDENTIFIER)
            self.state = 181
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
            self.state = 183
            self.match(PiettoParser.ENCODING)
            self.state = 184
            self.match(PiettoParser.IDENTIFIER)
            self.state = 185
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


        def sourceDefinition(self):
            return self.getTypedRuleContext(PiettoParser.SourceDefinitionContext,0)


        def tableDefinition(self):
            return self.getTypedRuleContext(PiettoParser.TableDefinitionContext,0)


        def queryDefinition(self):
            return self.getTypedRuleContext(PiettoParser.QueryDefinitionContext,0)


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
            self.state = 195
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [8]:
                self.enterOuterAlt(localctx, 1)
                self.state = 187
                self.typeDefinition()
                pass
            elif token in [9]:
                self.enterOuterAlt(localctx, 2)
                self.state = 188
                self.enumDefinition()
                pass
            elif token in [10]:
                self.enterOuterAlt(localctx, 3)
                self.state = 189
                self.constraintDefinition()
                pass
            elif token in [11]:
                self.enterOuterAlt(localctx, 4)
                self.state = 190
                self.deriveDefinition()
                pass
            elif token in [12]:
                self.enterOuterAlt(localctx, 5)
                self.state = 191
                self.shapeDefinition()
                pass
            elif token in [18]:
                self.enterOuterAlt(localctx, 6)
                self.state = 192
                self.sourceDefinition()
                pass
            elif token in [19]:
                self.enterOuterAlt(localctx, 7)
                self.state = 193
                self.tableDefinition()
                pass
            elif token in [23]:
                self.enterOuterAlt(localctx, 8)
                self.state = 194
                self.queryDefinition()
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
            self.state = 227
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,14,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 197
                self.match(PiettoParser.TYPE)
                self.state = 198
                self.match(PiettoParser.IDENTIFIER)
                self.state = 199
                self.match(PiettoParser.ASSIGN)
                self.state = 200
                self.typeExpression()
                self.state = 201
                self.match(PiettoParser.NEWLINE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 203
                self.match(PiettoParser.TYPE)
                self.state = 204
                self.match(PiettoParser.IDENTIFIER)
                self.state = 205
                self.match(PiettoParser.ASSIGN)
                self.state = 206
                self.typeExpression()
                self.state = 207
                self.match(PiettoParser.ENSURE)
                self.state = 208
                self.expression()
                self.state = 209
                self.match(PiettoParser.NEWLINE)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 211
                self.match(PiettoParser.TYPE)
                self.state = 212
                self.match(PiettoParser.IDENTIFIER)
                self.state = 213
                self.match(PiettoParser.ASSIGN)
                self.state = 214
                self.typeExpression()
                self.state = 215
                self.match(PiettoParser.COLON)
                self.state = 216
                self.match(PiettoParser.NEWLINE)
                self.state = 220
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==59:
                    self.state = 217
                    self.match(PiettoParser.NEWLINE)
                    self.state = 222
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 223
                self.match(PiettoParser.INDENT)
                self.state = 224
                self.typeBody()
                self.state = 225
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
            self.state = 231 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 231
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [24]:
                    self.state = 229
                    self.ensureClause()
                    pass
                elif token in [59]:
                    self.state = 230
                    self.match(PiettoParser.NEWLINE)
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 233 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==24 or _la==59):
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
            self.state = 235
            self.match(PiettoParser.ENSURE)
            self.state = 236
            self.expression()
            self.state = 237
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
            self.state = 239
            self.typeReference()
            self.state = 241
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==25 or _la==29:
                self.state = 240
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
            self.state = 243
            self.match(PiettoParser.IDENTIFIER)
            self.state = 245
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==49:
                self.state = 244
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
            self.state = 250
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [25]:
                self.enterOuterAlt(localctx, 1)
                self.state = 247
                self.match(PiettoParser.NULLABLE)
                pass
            elif token in [29]:
                self.enterOuterAlt(localctx, 2)
                self.state = 248
                self.match(PiettoParser.NOT)
                self.state = 249
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
            self.state = 252
            self.match(PiettoParser.LPAREN)
            self.state = 264
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 504992523626733584) != 0):
                self.state = 253
                self.typeArgument()
                self.state = 258
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,20,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 254
                        self.match(PiettoParser.COMMA)
                        self.state = 255
                        self.typeArgument() 
                    self.state = 260
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,20,self._ctx)

                self.state = 262
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==51:
                    self.state = 261
                    self.match(PiettoParser.COMMA)




            self.state = 266
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
            self.state = 273
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,23,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 268
                self.typeArgumentName()
                self.state = 269
                self.match(PiettoParser.ASSIGN)
                self.state = 270
                self.expression()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 272
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
            self.state = 275
            _la = self._input.LA(1)
            if not(_la==4 or _la==58):
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
            self.state = 277
            self.match(PiettoParser.ENUM)
            self.state = 278
            self.match(PiettoParser.IDENTIFIER)
            self.state = 279
            self.match(PiettoParser.COLON)
            self.state = 280
            self.match(PiettoParser.NEWLINE)
            self.state = 284
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 281
                self.match(PiettoParser.NEWLINE)
                self.state = 286
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 287
            self.match(PiettoParser.INDENT)
            self.state = 288
            self.enumBody()
            self.state = 289
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
            self.state = 293 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 293
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [58]:
                    self.state = 291
                    self.enumItem()
                    pass
                elif token in [59]:
                    self.state = 292
                    self.match(PiettoParser.NEWLINE)
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 295 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==58 or _la==59):
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
            self.state = 297
            self.match(PiettoParser.IDENTIFIER)
            self.state = 298
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
            self.state = 300
            self.match(PiettoParser.CONSTRAINT)
            self.state = 301
            self.match(PiettoParser.IDENTIFIER)
            self.state = 302
            self.match(PiettoParser.LPAREN)
            self.state = 304
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==58:
                self.state = 303
                self.parameterList()


            self.state = 306
            self.match(PiettoParser.RPAREN)
            self.state = 307
            self.match(PiettoParser.ARROW)
            self.state = 308
            self.typeExpression()
            self.state = 309
            self.match(PiettoParser.COLON)
            self.state = 310
            self.match(PiettoParser.NEWLINE)
            self.state = 314
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 311
                self.match(PiettoParser.NEWLINE)
                self.state = 316
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 317
            self.match(PiettoParser.INDENT)
            self.state = 318
            self.constraintBody()
            self.state = 319
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
            self.state = 321
            self.parameter()
            self.state = 326
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,29,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 322
                    self.match(PiettoParser.COMMA)
                    self.state = 323
                    self.parameter() 
                self.state = 328
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,29,self._ctx)

            self.state = 330
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==51:
                self.state = 329
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
            self.state = 332
            self.match(PiettoParser.IDENTIFIER)
            self.state = 333
            self.match(PiettoParser.COLON)
            self.state = 334
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
            self.state = 339
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 336
                self.match(PiettoParser.NEWLINE)
                self.state = 341
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 342
            self.expression()
            self.state = 343
            self.match(PiettoParser.NEWLINE)
            self.state = 347
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 344
                self.match(PiettoParser.NEWLINE)
                self.state = 349
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
            self.state = 350
            self.match(PiettoParser.DERIVE)
            self.state = 351
            self.match(PiettoParser.IDENTIFIER)
            self.state = 352
            self.match(PiettoParser.LPAREN)
            self.state = 354
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==58:
                self.state = 353
                self.parameterList()


            self.state = 356
            self.match(PiettoParser.RPAREN)
            self.state = 357
            self.match(PiettoParser.ARROW)
            self.state = 358
            self.typeExpression()
            self.state = 359
            self.match(PiettoParser.COLON)
            self.state = 360
            self.match(PiettoParser.NEWLINE)
            self.state = 364
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 361
                self.match(PiettoParser.NEWLINE)
                self.state = 366
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 367
            self.match(PiettoParser.INDENT)
            self.state = 368
            self.deriveBody()
            self.state = 369
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
            self.state = 374
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 371
                self.match(PiettoParser.NEWLINE)
                self.state = 376
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 377
            self.expression()
            self.state = 378
            self.match(PiettoParser.NEWLINE)
            self.state = 382
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 379
                self.match(PiettoParser.NEWLINE)
                self.state = 384
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
            self.state = 385
            self.match(PiettoParser.SHAPE)
            self.state = 386
            self.match(PiettoParser.IDENTIFIER)
            self.state = 387
            self.match(PiettoParser.COLON)
            self.state = 388
            self.match(PiettoParser.NEWLINE)
            self.state = 392
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 389
                self.match(PiettoParser.NEWLINE)
                self.state = 394
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 395
            self.match(PiettoParser.INDENT)
            self.state = 396
            self.shapeBody()
            self.state = 397
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
            self.state = 402
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 399
                self.match(PiettoParser.NEWLINE)
                self.state = 404
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 405
            self.shapeItem()
            self.state = 410
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 864691128455225344) != 0):
                self.state = 408
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [13, 14, 16, 58]:
                    self.state = 406
                    self.shapeItem()
                    pass
                elif token in [59]:
                    self.state = 407
                    self.match(PiettoParser.NEWLINE)
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 412
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
            self.state = 417
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [58]:
                self.enterOuterAlt(localctx, 1)
                self.state = 413
                self.fieldDefinition()
                pass
            elif token in [13]:
                self.enterOuterAlt(localctx, 2)
                self.state = 414
                self.checkDefinition()
                pass
            elif token in [14]:
                self.enterOuterAlt(localctx, 3)
                self.state = 415
                self.uniqueDefinition()
                pass
            elif token in [16]:
                self.enterOuterAlt(localctx, 4)
                self.state = 416
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
            self.state = 419
            self.match(PiettoParser.IDENTIFIER)
            self.state = 420
            self.match(PiettoParser.COLON)
            self.state = 421
            self.typeExpression()
            self.state = 423
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==11:
                self.state = 422
                self.fieldDeriveClause()


            self.state = 428
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==24 or _la==48:
                self.state = 425
                self.fieldModifier()
                self.state = 430
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 431
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
            self.state = 433
            self.match(PiettoParser.DERIVE)
            self.state = 434
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
            self.state = 438
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [48]:
                self.enterOuterAlt(localctx, 1)
                self.state = 436
                self.annotation()
                pass
            elif token in [24]:
                self.enterOuterAlt(localctx, 2)
                self.state = 437
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
            self.state = 440
            self.match(PiettoParser.AT)
            self.state = 441
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
            self.state = 443
            self.match(PiettoParser.ENSURE)
            self.state = 444
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
            self.state = 446
            self.match(PiettoParser.CHECK)
            self.state = 447
            self.match(PiettoParser.IDENTIFIER)
            self.state = 448
            self.match(PiettoParser.COLON)
            self.state = 449
            self.match(PiettoParser.NEWLINE)
            self.state = 453
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 450
                self.match(PiettoParser.NEWLINE)
                self.state = 455
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 456
            self.match(PiettoParser.INDENT)
            self.state = 457
            self.checkBody()
            self.state = 458
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
            self.state = 463
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 460
                self.match(PiettoParser.NEWLINE)
                self.state = 465
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 466
            self.expression()
            self.state = 467
            self.match(PiettoParser.NEWLINE)
            self.state = 471
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 468
                self.match(PiettoParser.NEWLINE)
                self.state = 473
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
            self.state = 474
            self.match(PiettoParser.UNIQUE)
            self.state = 475
            self.match(PiettoParser.IDENTIFIER)
            self.state = 476
            self.match(PiettoParser.ON)
            self.state = 477
            self.match(PiettoParser.IDENTIFIER)
            self.state = 482
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==51:
                self.state = 478
                self.match(PiettoParser.COMMA)
                self.state = 479
                self.match(PiettoParser.IDENTIFIER)
                self.state = 484
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 485
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
            self.state = 487
            self.match(PiettoParser.INDEX)
            self.state = 488
            self.match(PiettoParser.IDENTIFIER)
            self.state = 489
            self.match(PiettoParser.ON)
            self.state = 490
            self.match(PiettoParser.IDENTIFIER)
            self.state = 495
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==51:
                self.state = 491
                self.match(PiettoParser.COMMA)
                self.state = 492
                self.match(PiettoParser.IDENTIFIER)
                self.state = 497
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 500
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==17:
                self.state = 498
                self.match(PiettoParser.WHEN)
                self.state = 499
                self.expression()


            self.state = 502
            self.match(PiettoParser.NEWLINE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SourceDefinitionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def SOURCE(self):
            return self.getToken(PiettoParser.SOURCE, 0)

        def IDENTIFIER(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.IDENTIFIER)
            else:
                return self.getToken(PiettoParser.IDENTIFIER, i)

        def IS(self):
            return self.getToken(PiettoParser.IS, 0)

        def expression(self):
            return self.getTypedRuleContext(PiettoParser.ExpressionContext,0)


        def NEWLINE(self):
            return self.getToken(PiettoParser.NEWLINE, 0)

        def COLON(self):
            return self.getToken(PiettoParser.COLON, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_sourceDefinition

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSourceDefinition" ):
                return visitor.visitSourceDefinition(self)
            else:
                return visitor.visitChildren(self)




    def sourceDefinition(self):

        localctx = PiettoParser.SourceDefinitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 74, self.RULE_sourceDefinition)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 504
            self.match(PiettoParser.SOURCE)
            self.state = 505
            self.match(PiettoParser.IDENTIFIER)
            self.state = 508
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==53:
                self.state = 506
                self.match(PiettoParser.COLON)
                self.state = 507
                self.match(PiettoParser.IDENTIFIER)


            self.state = 510
            self.match(PiettoParser.IS)
            self.state = 511
            self.expression()
            self.state = 512
            self.match(PiettoParser.NEWLINE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TableDefinitionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def TABLE(self):
            return self.getToken(PiettoParser.TABLE, 0)

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

        def tableBody(self):
            return self.getTypedRuleContext(PiettoParser.TableBodyContext,0)


        def DEDENT(self):
            return self.getToken(PiettoParser.DEDENT, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_tableDefinition

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTableDefinition" ):
                return visitor.visitTableDefinition(self)
            else:
                return visitor.visitChildren(self)




    def tableDefinition(self):

        localctx = PiettoParser.TableDefinitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 76, self.RULE_tableDefinition)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 514
            self.match(PiettoParser.TABLE)
            self.state = 515
            self.match(PiettoParser.IDENTIFIER)
            self.state = 516
            self.match(PiettoParser.COLON)
            self.state = 517
            self.match(PiettoParser.NEWLINE)
            self.state = 521
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 518
                self.match(PiettoParser.NEWLINE)
                self.state = 523
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 524
            self.match(PiettoParser.INDENT)
            self.state = 525
            self.tableBody()
            self.state = 526
            self.match(PiettoParser.DEDENT)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class QueryDefinitionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def QUERY(self):
            return self.getToken(PiettoParser.QUERY, 0)

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

        def tableBody(self):
            return self.getTypedRuleContext(PiettoParser.TableBodyContext,0)


        def DEDENT(self):
            return self.getToken(PiettoParser.DEDENT, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_queryDefinition

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitQueryDefinition" ):
                return visitor.visitQueryDefinition(self)
            else:
                return visitor.visitChildren(self)




    def queryDefinition(self):

        localctx = PiettoParser.QueryDefinitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 78, self.RULE_queryDefinition)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 528
            self.match(PiettoParser.QUERY)
            self.state = 529
            self.match(PiettoParser.IDENTIFIER)
            self.state = 530
            self.match(PiettoParser.COLON)
            self.state = 531
            self.match(PiettoParser.NEWLINE)
            self.state = 535
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 532
                self.match(PiettoParser.NEWLINE)
                self.state = 537
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 538
            self.match(PiettoParser.INDENT)
            self.state = 539
            self.tableBody()
            self.state = 540
            self.match(PiettoParser.DEDENT)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TableBodyContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def fromClause(self):
            return self.getTypedRuleContext(PiettoParser.FromClauseContext,0)


        def selectClause(self):
            return self.getTypedRuleContext(PiettoParser.SelectClauseContext,0)


        def NEWLINE(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.NEWLINE)
            else:
                return self.getToken(PiettoParser.NEWLINE, i)

        def whereClause(self):
            return self.getTypedRuleContext(PiettoParser.WhereClauseContext,0)


        def getRuleIndex(self):
            return PiettoParser.RULE_tableBody

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTableBody" ):
                return visitor.visitTableBody(self)
            else:
                return visitor.visitChildren(self)




    def tableBody(self):

        localctx = PiettoParser.TableBodyContext(self, self._ctx, self.state)
        self.enterRule(localctx, 80, self.RULE_tableBody)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 545
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 542
                self.match(PiettoParser.NEWLINE)
                self.state = 547
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 548
            self.fromClause()
            self.state = 552
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,55,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 549
                    self.match(PiettoParser.NEWLINE) 
                self.state = 554
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,55,self._ctx)

            self.state = 556
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==21:
                self.state = 555
                self.whereClause()


            self.state = 561
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 558
                self.match(PiettoParser.NEWLINE)
                self.state = 563
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 564
            self.selectClause()
            self.state = 568
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 565
                self.match(PiettoParser.NEWLINE)
                self.state = 570
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FromClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def FROM(self):
            return self.getToken(PiettoParser.FROM, 0)

        def IDENTIFIER(self):
            return self.getToken(PiettoParser.IDENTIFIER, 0)

        def NEWLINE(self):
            return self.getToken(PiettoParser.NEWLINE, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_fromClause

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFromClause" ):
                return visitor.visitFromClause(self)
            else:
                return visitor.visitChildren(self)




    def fromClause(self):

        localctx = PiettoParser.FromClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 82, self.RULE_fromClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 571
            self.match(PiettoParser.FROM)
            self.state = 572
            self.match(PiettoParser.IDENTIFIER)
            self.state = 573
            self.match(PiettoParser.NEWLINE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class WhereClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def WHERE(self):
            return self.getToken(PiettoParser.WHERE, 0)

        def expression(self):
            return self.getTypedRuleContext(PiettoParser.ExpressionContext,0)


        def NEWLINE(self):
            return self.getToken(PiettoParser.NEWLINE, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_whereClause

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitWhereClause" ):
                return visitor.visitWhereClause(self)
            else:
                return visitor.visitChildren(self)




    def whereClause(self):

        localctx = PiettoParser.WhereClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 84, self.RULE_whereClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 575
            self.match(PiettoParser.WHERE)
            self.state = 576
            self.expression()
            self.state = 577
            self.match(PiettoParser.NEWLINE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SelectClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def SELECT(self):
            return self.getToken(PiettoParser.SELECT, 0)

        def COLON(self):
            return self.getToken(PiettoParser.COLON, 0)

        def NEWLINE(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.NEWLINE)
            else:
                return self.getToken(PiettoParser.NEWLINE, i)

        def INDENT(self):
            return self.getToken(PiettoParser.INDENT, 0)

        def selectBody(self):
            return self.getTypedRuleContext(PiettoParser.SelectBodyContext,0)


        def DEDENT(self):
            return self.getToken(PiettoParser.DEDENT, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_selectClause

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSelectClause" ):
                return visitor.visitSelectClause(self)
            else:
                return visitor.visitChildren(self)




    def selectClause(self):

        localctx = PiettoParser.SelectClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 86, self.RULE_selectClause)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 579
            self.match(PiettoParser.SELECT)
            self.state = 580
            self.match(PiettoParser.COLON)
            self.state = 581
            self.match(PiettoParser.NEWLINE)
            self.state = 585
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 582
                self.match(PiettoParser.NEWLINE)
                self.state = 587
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 588
            self.match(PiettoParser.INDENT)
            self.state = 589
            self.selectBody()
            self.state = 590
            self.match(PiettoParser.DEDENT)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SelectBodyContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def selectItem(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PiettoParser.SelectItemContext)
            else:
                return self.getTypedRuleContext(PiettoParser.SelectItemContext,i)


        def NEWLINE(self, i:int=None):
            if i is None:
                return self.getTokens(PiettoParser.NEWLINE)
            else:
                return self.getToken(PiettoParser.NEWLINE, i)

        def getRuleIndex(self):
            return PiettoParser.RULE_selectBody

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSelectBody" ):
                return visitor.visitSelectBody(self)
            else:
                return visitor.visitChildren(self)




    def selectBody(self):

        localctx = PiettoParser.SelectBodyContext(self, self._ctx, self.state)
        self.enterRule(localctx, 88, self.RULE_selectBody)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 595
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 592
                self.match(PiettoParser.NEWLINE)
                self.state = 597
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 598
            self.selectItem()
            self.state = 603
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 1081453275930157056) != 0):
                self.state = 601
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 28, 30, 33, 34, 43, 44, 49, 56, 57, 58]:
                    self.state = 599
                    self.selectItem()
                    pass
                elif token in [59]:
                    self.state = 600
                    self.match(PiettoParser.NEWLINE)
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 605
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SelectItemContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENTIFIER(self):
            return self.getToken(PiettoParser.IDENTIFIER, 0)

        def ASSIGN(self):
            return self.getToken(PiettoParser.ASSIGN, 0)

        def expression(self):
            return self.getTypedRuleContext(PiettoParser.ExpressionContext,0)


        def NEWLINE(self):
            return self.getToken(PiettoParser.NEWLINE, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_selectItem

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSelectItem" ):
                return visitor.visitSelectItem(self)
            else:
                return visitor.visitChildren(self)




    def selectItem(self):

        localctx = PiettoParser.SelectItemContext(self, self._ctx, self.state)
        self.enterRule(localctx, 90, self.RULE_selectItem)
        try:
            self.state = 614
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,63,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 606
                self.match(PiettoParser.IDENTIFIER)
                self.state = 607
                self.match(PiettoParser.ASSIGN)
                self.state = 608
                self.expression()
                self.state = 609
                self.match(PiettoParser.NEWLINE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 611
                self.expression()
                self.state = 612
                self.match(PiettoParser.NEWLINE)
                pass


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
        self.enterRule(localctx, 92, self.RULE_expression)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 616
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
        self.enterRule(localctx, 94, self.RULE_orExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 618
            self.andExpression()
            self.state = 623
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==27:
                self.state = 619
                self.match(PiettoParser.OR)
                self.state = 620
                self.andExpression()
                self.state = 625
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
        self.enterRule(localctx, 96, self.RULE_andExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 626
            self.comparisonExpression()
            self.state = 631
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==26:
                self.state = 627
                self.match(PiettoParser.AND)
                self.state = 628
                self.comparisonExpression()
                self.state = 633
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
        self.enterRule(localctx, 98, self.RULE_comparisonExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 634
            self.additiveExpression()
            self.state = 648
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [32, 35, 36, 37, 38, 39, 40]:
                self.state = 635
                self.comparisonOperator()
                self.state = 636
                self.additiveExpression()
                pass
            elif token in [31]:
                self.state = 638
                self.match(PiettoParser.BETWEEN)
                self.state = 639
                self.additiveExpression()
                self.state = 640
                self.match(PiettoParser.AND)
                self.state = 641
                self.additiveExpression()
                pass
            elif token in [28]:
                self.state = 643
                self.match(PiettoParser.IS)
                self.state = 645
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==29:
                    self.state = 644
                    self.match(PiettoParser.NOT)


                self.state = 647
                self.match(PiettoParser.NULL)
                pass
            elif token in [24, 26, 27, 48, 50, 51, 59]:
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
        self.enterRule(localctx, 100, self.RULE_comparisonOperator)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 650
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 2168958484480) != 0)):
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
        self.enterRule(localctx, 102, self.RULE_additiveExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 652
            self.multiplicativeExpression()
            self.state = 657
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==43 or _la==44:
                self.state = 653
                _la = self._input.LA(1)
                if not(_la==43 or _la==44):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 654
                self.multiplicativeExpression()
                self.state = 659
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
        self.enterRule(localctx, 104, self.RULE_multiplicativeExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 660
            self.unaryExpression()
            self.state = 665
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 246290604621824) != 0):
                self.state = 661
                _la = self._input.LA(1)
                if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 246290604621824) != 0)):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 662
                self.unaryExpression()
                self.state = 667
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
        self.enterRule(localctx, 106, self.RULE_unaryExpression)
        self._la = 0 # Token type
        try:
            self.state = 671
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [43, 44]:
                self.enterOuterAlt(localctx, 1)
                self.state = 668
                _la = self._input.LA(1)
                if not(_la==43 or _la==44):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 669
                self.unaryExpression()
                pass
            elif token in [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 28, 30, 33, 34, 49, 56, 57, 58]:
                self.enterOuterAlt(localctx, 2)
                self.state = 670
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
        self.enterRule(localctx, 108, self.RULE_primaryExpression)
        self._la = 0 # Token type
        try:
            self.state = 682
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [30, 33, 34, 56, 57]:
                self.enterOuterAlt(localctx, 1)
                self.state = 673
                self.literal()
                pass
            elif token in [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 28, 58]:
                self.enterOuterAlt(localctx, 2)
                self.state = 674
                self.dottedName()
                self.state = 676
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==49:
                    self.state = 675
                    self.callSuffix()


                pass
            elif token in [49]:
                self.enterOuterAlt(localctx, 3)
                self.state = 678
                self.match(PiettoParser.LPAREN)
                self.state = 679
                self.expression()
                self.state = 680
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
        self.enterRule(localctx, 110, self.RULE_dottedName)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 684
            self.namePart()
            self.state = 689
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==52:
                self.state = 685
                self.match(PiettoParser.DOT)
                self.state = 686
                self.namePart()
                self.state = 691
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

        def SOURCE(self):
            return self.getToken(PiettoParser.SOURCE, 0)

        def IS(self):
            return self.getToken(PiettoParser.IS, 0)

        def TABLE(self):
            return self.getToken(PiettoParser.TABLE, 0)

        def FROM(self):
            return self.getToken(PiettoParser.FROM, 0)

        def WHERE(self):
            return self.getToken(PiettoParser.WHERE, 0)

        def SELECT(self):
            return self.getToken(PiettoParser.SELECT, 0)

        def QUERY(self):
            return self.getToken(PiettoParser.QUERY, 0)

        def getRuleIndex(self):
            return PiettoParser.RULE_namePart

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNamePart" ):
                return visitor.visitNamePart(self)
            else:
                return visitor.visitChildren(self)




    def namePart(self):

        localctx = PiettoParser.NamePartContext(self, self._ctx, self.state)
        self.enterRule(localctx, 112, self.RULE_namePart)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 692
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 288230376436916224) != 0)):
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
        self.enterRule(localctx, 114, self.RULE_callSuffix)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 694
            self.match(PiettoParser.LPAREN)
            self.state = 706
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 504992523626733568) != 0):
                self.state = 695
                self.expression()
                self.state = 700
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,74,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 696
                        self.match(PiettoParser.COMMA)
                        self.state = 697
                        self.expression() 
                    self.state = 702
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,74,self._ctx)

                self.state = 704
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==51:
                    self.state = 703
                    self.match(PiettoParser.COMMA)




            self.state = 708
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
        self.enterRule(localctx, 116, self.RULE_literal)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 710
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 216172808957329408) != 0)):
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





