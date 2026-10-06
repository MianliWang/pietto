# Pietto Layering And Coupling Laws v1

These laws are the current durable dependency contract. They assign ownership
without claiming that future lowering, execution, interchange, adapter,
optimizer, or physical layers are implemented.

## Primary semantic / compilation / result flow

```text
AST
-> Semantic Authority
-> Project IR / Query Block IR
-> ProjectSQLPlan
-> Dialect SQL AST
-> optional Execution Plane
-> ResultContract / Arrow
-> Ecosystem Adapter Plane
```

Dependencies flow forward within this primary structure. Downstream layers may
consume upstream authority, but may not silently re-decide upstream semantic
facts. A downstream representation retains typed provenance to the fact it
projects instead of substituting names, positions, bytes, handles, or
observations for that fact. Result interchange and ecosystem adapters remain
downstream consumers, not normative planning inputs.

## Optimizer / physical planning side-plane

Logical optimizer and rewrite search consume already-established
semantic/logical authority. They may derive alternative semantically equivalent
logical or planning candidates and feed later planning/lowering only after the
required legality and verification. They never become name, path, identity, or
semantic-resolution authority.

Physical strategy selection consumes selected logical/planning authority. It
may influence later lowering or execution strategy and therefore occurs before
the execution/result boundary it affects. ResultContract / Arrow and ecosystem
adapters are not normative optimizer or physical-planning authority.

Accordingly:

- optimizer/physical plane is downstream of semantic authority;
- optimizer/physical plane is upstream of, or a planning side-plane to,
  lowering and execution;
- optimizer/physical plane is not downstream of ResultContract / Arrow;
- optimizer/physical plane is not downstream of ecosystem adapters.

Phases 88–89 own the exact future internal optimizer/physical IR topology. This
document does not implement those phases or define an optimizer IR, physical
IR, memo shape, cost model, optimizer API, or physical-plan representation.

## Coupling distinctions

- normative fact != compiled index;
- interface != capability;
- semantic requirement != optimization hint;
- semantic state != runtime resource state;
- cache != authority;
- inspection != resolver;
- optimizer != path resolver;
- optimizer != name resolver;
- verification != semantic authority;
- serialization != semantic authority;
- canonical bytes != semantic authority.

Compiled indexes accelerate an already-defined query. Interfaces describe a
surface, while capability evidence says what a selected provider supports.
Verification independently checks authority; it neither creates nor repairs
semantic facts. Inspection and serialization expose existing results without
becoming construction paths.

## Explicit boundaries

- Legality boundaries are explicit and unsupported shapes fail closed.
- Target requirements and provider capabilities are matched explicitly; one
  does not imply the other.
- Invalidation follows changed semantic roots through their derived facts.
- Verification is independently rerun wherever its contract requires fresh
  evidence.
- Snapshot-local derived analyses do not become persistent authority by
  observation alone.
- Compiler core has no ambient network, database, credential, or transaction
  authority.
- Plugins and adapters are explicit dependencies rather than ambient lookup or
  fallback mechanisms.

SQL planning/lowering, dialect lowering, optimizer search, physical strategy,
execution, result interchange, and ecosystem adapters remain separate
architectural owners. A later phase may implement one only through a fresh
[Product/Phase Initiation Gate v1](phase-initiation-gate-v1.md) and the
phase-level ownership in the [roadmap](../roadmap.md). This extraction
implements none of them.

Identity and candidate completeness remain governed by [Identity And Authority
Laws v1](identity-and-authority-laws-v1.md); the complete layer map is in
[Pietto Product Architecture v1](product-architecture-v1.md).


## Source and compiled preparation

Phase68 [S10](../phases/phase-68/slice-10.md) permits closed resolved compiled
inputs at the original semantic/IR/plan owners. Source and compiled adapters
share original derivation laws; source parsing/name/type/connector elaboration
stays in the source branch. The compiled graph is not a serialized AST, SQL
parser, driver callback, plugin registry or second semantic engine.
Build/export, externally pinned loading, value rederivation and native execution
are distinct accepting boundaries. Actual Psycopg and ADBC catalog acquisition
share PG qualification laws through their own native reply/context types; MySQL
retains its separate definition/security rules. Fresh live authorization and
transaction checks cannot be cached as immutable compiled structure.


## Durable metadata store

Phase68 [S11](../phases/phase-68/slice-11.md) keeps the private SQLite store beside,
not inside, the S10 compiled/execution owners: it persists their exact bytes and
portable descriptions and calls their loader, binder, describer and owner outcome
projection. It exposes closed domain operations only, never a raw database
callback, and stores no connection, credential, live qualification, guard receipt
or result row. Later chunk, reader, sink and scheduler owners extend its fenced
transaction pattern rather than adding a competing registry.


## Captured result plane

Phase68 [S12](../phases/phase-68/slice-12.md) extends the S11 store with chunk files
and checkpoints: a capture session consumes checked batches from a real S10 owner,
reuses the original IPC writer/reader, and reads back through a stored-chunk
producer purpose in the original result owner. Metadata-only operations stay
Arrow- and driver-free. No raw database callback, live handle or second store is
exposed; future readers, sinks and GC extend the same fenced operations.


## Saved-result replay plane

Phase68 [S13](../phases/phase-68/slice-13.md) reads committed S12 chunks through the
original stored-output producer, `SnapshotReader` and S10 batch checks; it adds no
second encoder, store, clock or authorization service. Consumer, session,
issuance and acknowledgement rows extend the S11 fenced operation pattern in the
explicit v3 workspace. Acceptance, registration and observations stay Arrow- and
driver-free; only the data step imports Arrow. Sinks, extraction recovery and GC
extend these operations rather than bypassing them.


## Extraction-recovery plane

Phase68 [S14](../phases/phase-68/slice-14.md) recovers extraction through the S10
common entry, the real route owners and S06 `Enumeration` from position 0; it
adds no seek, frontier import, source table, scheduler or second encoder. The
read-only S10 bridge `compiled_source_description` projects an open owner's own
checked qualification. Continuation, reconciliation and end rows extend the S11
fenced operation pattern in the explicit v4 workspace, new chunks reuse the S12
file protocol and publication, and readers admit later producing attempts only
through those rows. Sinks, publication and GC extend these operations.


## Cooperative-delivery plane

Phase68 [S15](../phases/phase-68/slice-15.md) delivers committed S12/S14 chunks
through the S13 checked rebatch and the original atom/coordinate codec into a
separate reference sink owner; it adds no second result store, query engine,
scalar interpreter, process adapter, scheduler or callback inside a transaction.
Stream, window, session, issuance, observation and retirement rows extend the S11
fenced operation pattern in the explicit v5 workspace; window protection reuses
S12 retention. The sink reuses the workspace profile and connection settings but
never shares a connection, transaction or ATTACH with a job store. Publication
and GC extend these operations.


## Complete-publication plane

Phase68 [S16](../phases/phase-68/slice-16.md) publishes committed S12/S14
checkpoints by reference in one short S11 fenced operation of the explicit v6
workspace; it rewrites no data file and adds no second store, latest register,
notification service, sink policy or cross-database transaction. The read-only
S10 bridge `compiled_closing_facts` projects an owner's own closing facts into
the v6 attempt terminal; preparation reuses S12 retention and the bounded
`SnapshotReader`, and publication converts that retention by reference. Readers
reach a publication only through S13, sinks stay independent of it, and
scheduling and GC extend these operations.
