# Phase70 completion audit — S20 candidate

This is an audit-only candidate. Phase70 becomes `COMPLETED / PUBLISHED` only
after the ordinary S20 audit commit is fast-forward pushed and its natural
exact-head CI accepts all required consumers. This document does not authorize
another release, a rebuild, a database campaign, a deferred feature, or a
post-CI reader commit.

## Terminal identity ledger

| Record | Accepted identity / result |
| --- | --- |
| S18 recovery and closure | Failed head `61ed4df2a0ffc5e1183635f41163469a770880de` and natural CI `38783960633` are preserved. The owner-authorized empty child `fc561a5fd014de1cdb7e57af2cc3e31d105caf78` retained tree `f839f64166680df624cf7a81f26bea1c943b15e5`; natural CI `38798708844` accepted 19 jobs and 36 artifacts. |
| S19 source gate | `6ac82d682ea70056ffbecd64a9f53f72491a51c6`, tree `550c1fa0765cb209f3f8438e4b49d5f6329dd24a`; natural CI `38809622132` attempt 1 accepted 19 jobs and 36 artifacts. |
| Official distributions | One formal `uv_build==0.12.5` build: `pietto-0.1.3-py3-none-any.whl` SHA-256 `15f2a73da34dbf332ae19eebb32aa7e10830ddf46de79169be0bdad5a3e2e06b`; `pietto-0.1.3.tar.gz` SHA-256 `31c06e0b7ab3fe48b4a17ec28ae9b17ec957a4dd433ff5d50385d68f56da449f`. |
| Installation and native acceptance | Twelve formal installation cells, accepted sdist installation, S17, 12 native R2 cells, and owned cleanup with 36 registered workers reaped. |
| GitHub channel | Pre-release `v0.1.3`, release `414443229`, targets the S19 source head; public wheel and sdist bytes match the official distributions. The GitHub source tar and zip are distinct from the Python sdist and match the committed archive. |
| PyPI channel | PyPI `0.1.3` has verified public bytes, metadata, description, 12 readback installation cells, and accepted sdist installation. The owner entered the upload token; the agent did not access it. |
| S20 audit publication | Conditional on this audit's one ordinary commit and its natural exact-head CI. |

The published 0.1.0, 0.1.1, and 0.1.2 bytes remain historical identities and
are not replaced. The S19 release facts are evidence for this audit, not a
license to overwrite them.

## Acceptance reconciliation

The Phase70 brief remains normative. S20 reconciles its witnesses rather than
repeating their campaigns.

| Acceptance | Reconciled witnesses |
| --- | --- |
| A01 local and derived relations | S03/S05 semantic and two-target BAG/native evidence, including hidden-source closure. |
| A02 named parameters | S04/S11 template, binding, bundle, route, and refusal evidence. |
| A03 typed VALUES | S06 PostgreSQL zero-source qualification, MySQL refusal, and native evidence. |
| A04 scalar | S07/S14 forced-evaluation outcomes and `PIE-R3003` SQLSTATE evidence. |
| A05 EXISTS and IN | S08/S09/S14 three-valued oracle and two-target native evidence. |
| A06 capture and LATERAL | S10/S12/S13 outer-occurrence, NULL-extension, Top-K, and target-refusal evidence. |
| A07 bounded table function | S15 PostgreSQL `generate_series` admission and MySQL refusal evidence. |
| A08 effects authority | S15 UNKNOWN-effects refusal and the retained no-rewrite boundary. |
| A09 public artifacts and consumers | S16 decoder/documentation closure, S18 profiles, package readers, and natural CI. |
| A10 regression and lifecycle | S01/S02 preservation, S17/S18 integration, authoritative validation, and preserved failed history. |
| A11 release | S19's one formal build, 12 installation cells, channel byte/metadata/archive checks, and owner-operated upload. |
| A12 computed grouping and let aggregates | S05g/S05j two-target BAG/native evidence, including parameter-dependent grouping. |

S18 completed the phase-end acquisition review and ten slowest-node profiles;
those profiles are evidence about parent-process observation and do not turn
child verifier counts or unavailable resource measures into positive facts.

## Scope, accounting, and retained limits

The planning graph had 24 nodes: the historical 20-row route plus S04r, S04w,
S05g, and S05j. S04 was then split into S04a and S04b, yielding 25 delivery
positions including this S20 candidate; 24 are already published. They are: S01, S02, S03, S04a, S04b, S04r, S04w, S05, S05g, S05j, and S06–S20.
This reconciles the graph with delivery; it does not rewrite its historical
route or capacity decisions.

The final S19 record carries conservative repair accounting of C121/F107/D156/
S6 against limits C225/F180/D270/S9. Historical UNKNOWN classifications and
failed preparations remain retained evidence, not a claim of complete causal
attribution or unused budget.

The public alpha remains bounded to the documented compiler, CLI, three
explicit execution routes, and saved-result flows. Native evidence is limited
to the recorded CPython 3.13.13 Linux x86-64 qualified-host domain. Managed
operator compliance remains `NOT_INDEPENDENTLY_VERIFIED`, and native
all-definition lifetime exclusion remains `NOT_DEMONSTRATED / NOT CLAIMED`.

## Deferred-owner ledger

S20 does not implement any row below.

| Subject | Later owner |
| --- | --- |
| NestedRelation, Collect, and Unnest | Phase71 |
| Broader equality/nullability, Float row equivalence, time relations, and Decimal/Date/Timestamp/UUID parameter types | Phase72 |
| Cross-layer aggregation algebra | Phase73 |
| General functions/plugin SPI, more table functions, and scalar-function effects catalog | Phase74 |
| Editor/LSP/syntax-version work and selected-owner compilation amid project semantic errors | Phase75 |
| VS Code extension follow-up | Extension owner |
| PostgreSQL/MySQL deep adaptation, including MySQL wrappers, `JSON_TABLE`, and correlated `IN` with capture plus LIMIT | Phase76/77 |
| High-intensity real-database, differential, and performance guarantees | Phase81 |
| Public API freeze | Phase82 |
| Decorrelation, optimizer search/memo/CSE/materialization/evaluation-count promises, and rewrite-consumed effects | Phase88; formal rewrite certification: Phase93 |
| Persistent incremental cache | Phase91 |
| Recursion | Phase92 |

## Operator lessons retained

- Validate the public API through that API. Public `load_bundle` checks code
  identity before decoding; the private loader checks record shape before its
  own compatibility comparison.
- Preserve a virtual environment's `bin/python` entry point: resolving its
  symlink selects the base interpreter rather than the installed environment.
- Initialize a fresh operation ledger before registered workers begin, and
  test embedded Python at its actual consumer.
- A local-file installation can lack `archive_info`; the recorded command,
  file URI, wheel hash, import/distribution roots, and installed-byte equality
  are the relevant evidence, without inventing optional metadata.
- A corrected read-only inspector may inspect an already completed sdist
  installation; it does not justify rebuilding the accepted distribution.

## Closure rule and write boundary

This audit and `phase71-handoff.md` are the final Phase70 lifecycle documents.
The S20 ordinary commit updates the current lifecycle readers together. Phase70
is `COMPLETED / PUBLISHED` only when that commit is fast-forward pushed and its
natural exact-head CI passes. No documentation-only follow-up may be added just
to restate that commit, run, or result.

S20 changes no production, package, lock, generated, grammar, license, or CI
input. It reuses the accepted S19 package/native/channel evidence, then runs
the ordinary authoritative validation and natural CI for its own audit tree.
