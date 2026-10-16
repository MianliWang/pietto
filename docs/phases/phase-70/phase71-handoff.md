# Phase70 S20 handoff — Phase71 readiness

This handoff becomes effective only under the S20 closure rule in
`completion-audit.md`. It does not start Phase71, authorize a Phase71 route,
or grant implementation authority.

## Released baseline

The Phase70 release baseline is source head
`6ac82d682ea70056ffbecd64a9f53f72491a51c6` and its accepted 0.1.3 wheel and
sdist recorded in the completion audit. Its public boundary remains an alpha
SQL authoring compiler with an explicit Python execution API; the CLI does not
execute database queries.

Relation lets, named query parameters, typed VALUES bodies, closed relation
reads, correlated reads/LATERAL joins, and bounded PostgreSQL
`generate_series` retain their documented acceptance and refusal boundaries.
The release does not supply automatic migration: 0.1.2 bundles and saved jobs
are refused by the changed code identity and retain their original bytes.

## Inputs for Phase71 planning

Phase71 owns NestedRelation, Collect, and Unnest. Its phase-start gate must
independently decide syntax, semantics, compatibility, planning, SQL lowering,
execution, test witnesses, resource bounds, and public scope. Phase70 provides
the following inputs only:

- local-relation and source-closure facts, including the distinction between
  named CTE-style relation lets and correlated derived relations;
- the explicit multiplicity and outer-row-identity boundary for correlated
  reads and documented INNER/CROSS/LEFT LATERAL semantics;
- the accepted 0.1.3 package and channel identities, without authority to
  replace old bytes, relax code-identity checks, or claim a broader support
  domain;
- the retained failures, acquired profiles, and operator lessons in the
  completion audit as planning evidence, not as new performance guarantees.

## Boundaries that remain elsewhere

NestedRelation planning must not absorb the owners in the completion audit's
deferred-owner ledger. In particular, broad type/nullability work remains
Phase72, aggregation algebra Phase73, functions and more table functions
Phase74, editor partial analysis Phase75, deep database adaptation Phase76/77,
and rewrites Phase88/93. The VS Code extension remains the extension owner's
work.

No later phase may infer an automatic migration, a stable editor API, Windows
native support, optimizer behavior, recursive semantics, or a public execution
CLI command from this handoff.
