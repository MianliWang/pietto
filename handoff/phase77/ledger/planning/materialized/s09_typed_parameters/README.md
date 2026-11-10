# Phase77 S09 typed-header parameter qualification preparation

Prepared from the clean target clone at
`/tmp/pietto-p77-s09-typed-targets`, baseline
`f8ccd2c44a2d9adf431a496bd9bbae037783176f`.

This package is a pre-qualification design and test matrix only.  It opens no
product gate, target carrier, SQL spelling, driver codec, database campaign,
compatibility promise, Gate 2, or release.  In particular,
`HEADER_PHYSICAL["mysql"]` remains empty and the current MySQL declaration-time
`PIE-B1003 query_parameter_type_not_admitted_on_target` behavior remains the
only implemented behavior for `Decimal`, `Date`, `Timestamp`, and `UUID`.

The existing Bool prepared-statement work is a control, not work to repeat.
The smallest future experiment reuses the existing native statement helper and
its owning rotating MySQL execution parent; it adds neither a resource framework
nor a second runtime transport.

Read in this order:

1. [candidate-contract.md](candidate-contract.md) fixes the finite candidate
   boundary and the UUID decision stop.
2. [qualification-matrix.md](qualification-matrix.md) names the evidence that
   must exist before changing a carrier.
3. [write-set-and-checks.md](write-set-and-checks.md) records the exact roots,
   no-write inspection, and checks actually performed for this preparation.
