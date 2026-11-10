# C76-06 run-2 errata

The inherited `db/judge.py` could report PASS without a campaign receipt and
did not judge record TLS parameters, successful route applications, or TLS
observations. Its self-test therefore failed to catch disabled TLS, a swapped
route application, and missing campaign evidence. This is a checker defect,
not a product verdict.

`db-run2/ORACLE.md` was registered before any run with the corrected 18-cell
matrix, controlled ambient fixture, same-run receipt and strict observation
requirements. The original Oracle and all inherited evidence are retained
unchanged. No raw output exists for either package.
