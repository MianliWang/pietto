"""Authored fixed-literal SQL-plan source fixtures."""

BODY = """    let:
        a = 1
        b = 1.0
        c = true
        d = "text"
    where true and 1 == 1 and 1.0 > 0.0 and "x" == "x"
    select:
        n = -3
        z = -0.0
        f = 1.25
        t = "é\\n😀"
        flag = false
        huge = 123456789012345678901234567890123456789
        first = a
        again = a
"""
