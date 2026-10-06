# Pietto Identity And Authority Laws v1

These are the current durable cross-phase identity and authority rules. They
project existing contracts and introduce no registry, public type, runtime
handle, or semantic behavior.

## Identity domains stay distinct

- name != identity;
- alias != identity;
- binding != declaration;
- use occurrence != declaration;
- semantic field != output occurrence;
- semantic field != SQL alias;
- semantic field != Arrow field name.

Names and aliases are lookup or presentation material. Declarations, bindings,
uses, semantic fields, and outputs retain their owning occurrence identities;
serialization or lowering may not collapse them.

Relationship identities likewise remain distinct:

```text
relationship declaration
!= relationship direction
!= traversal path
!= authored JOIN use
!= binary JOIN node
```

One domain may refer to another through typed provenance. That reference does
not make the identities interchangeable.

## Data properties are not aliases

- candidate key != row uniqueness;
- candidate key != Value FD;
- candidate key != grain;
- row uniqueness != grain;
- Value FD != grain.

Each fact keeps its own assumptions, proof scope, null policy, source, and
owner. No downstream convenience inference may promote one fact into another.

## Observation is not authority

- canonical bytes != semantic identity;
- cache key != occurrence identity;
- runtime handle != semantic identity;
- equal serialization != semantic equivalence unless separately proven.

Canonical bytes support deterministic observation and comparison. Cache keys
and runtime handles support their own local lifecycles. None may become a
semantic identity or semantic-equivalence proof by reuse alone.

## Complete-candidate lookup

Lookup is owner-specific and complete:

- zero candidates yields the owning typed `ABSENT`, `UNKNOWN`, or other
  explicitly defined non-concrete state;
- exactly one candidate may yield `CONCRETE`;
- more than one candidate yields `AMBIGUOUS` with the complete candidate
  bucket.

Existing owners may distinguish `ABSENT` from `UNKNOWN`; zero candidates does
not create one universal enum. `not proven != false`, and `unknown != zero`.

No hidden winner may be selected by `first`, `latest`, `shortest`, `nearest`,
or `best` unless a later explicit product contract defines that semantics.
Source order, authority order, multiplicity, provenance, availability,
complete collision buckets, and exact occurrence identity must be preserved.

## Closed construction states

Construction publishes either a closed typed concrete result or a closed typed
non-concrete result carrying the complete blocker evidence owned by that
contract. No partially valid object may be published as a completed concrete
semantic result. Inspection, caching, serialization, and runtime adaptation
must consume those states without becoming alternate resolvers.

These laws refine the product boundary in [Pietto Product Architecture
v1](product-architecture-v1.md) and apply through the dependency direction in
[Layering And Coupling Laws v1](layering-and-coupling-laws-v1.md).


## Explicit compiled input identity

Phase68 [S10](../phases/phase-68/slice-10.md) separates canonical bundle content,
trusted producer, supported code/semantic/occurrence/profile compatibility, fresh
compiled-root identity, exact typed binding values, binding instance and native
attempt authority. Equality at one layer does not mint another layer's identity.
Stable declaration/use/port/field/output/slot addresses describe relationships;
a loader independently checks the complete graph and constructs fresh roots.
A serialized source/guard/refinement obligation is a requirement, never a live
receipt, provider retention guarantee, deployment acceptance or durable progress.
Later job/generation/publisher/checkpoint/sink identities remain separately owned.


## Durable job identity

Phase68 [S11](../phases/phase-68/slice-11.md) adds separately owned workspace, job,
binding-record, generation, attempt, publisher-instance/epoch and operation
identities. None is derived from content pins, equal parameters, process or
session identifiers, rowids or file names. A stored bundle pin, outcome or
operation replay is history and consistency data, never a trust anchor, execution
authority or remote acknowledgement; every reload takes fresh caller trust inputs.
Every job mutation checks the current publisher epoch inside its own write
transaction. Generation registration is not result completion.


## Captured result identity

Phase68 [S12](../phases/phase-68/slice-12.md) adds separately owned chunk `chk-`,
checkpoint `ckp-` and retention `ret-` identities. A chunk file digest protects
only a file boundary and stays private; equal payload bytes can belong to two
legitimate chunks, and file names never encode an occurrence. A checkpoint is an
immutable member set with a recomputed contiguous frontier, not a completed
generation, ACK or source-resume right; refined coordinate atoms are data only.
Every chunk publication and retention change is fenced by the current publisher.


## Saved-result consumer identity

Phase68 [S13](../phases/phase-68/slice-13.md) adds consumer `csm-`, replay session
`rps-` and delivery `dlv-` identities. A consumer is bound to one exact immutable
checkpoint and fixed extent; its progress is derived from acknowledgements, never
supplied. A saved-result read needs a fresh process-local caller acceptance whose
trust inputs, binding values, route and output contract are rechecked; no stored
row, receipt or copy mints one, and it grants no source or R2 authority. The
occurrence label is `(generation, position)`; delivery, session and operation
identities may change on redelivery. A local acknowledgement is not a sink ACK.


## Extraction-recovery identity

Phase68 [S14](../phases/phase-68/slice-14.md) keeps `(generation, logical output
position)` as the occurrence identity across every extraction attempt and R1
rebatching; attempt, session, epoch, page and chunk identities never rename an
occurrence. Each chunk keeps its real producing attempt. Only a generation whose
extraction specification and owner-linked stable source description were written
with its first capture may continue; a recovery needs a fresh process-local,
purpose-scoped acceptance and a new attempt whose real owner requalifies the
complete source vector and guards. Stored descriptions, barrier rows and
persisted success are compared, never trusted as authority. Complete coverage is
not a transaction ACK, delivery, sink effect or generation publication.


## Cooperative-delivery identity

Phase68 [S15](../phases/phase-68/slice-15.md) names one effect by the destination
incarnation plus the occurrence: `(sink instance, namespace, namespace epoch,
source workspace, generation, position)`. Attempt, checkpoint, chunk, batch,
session, consumer, operation, size, path and payload hash never name an effect;
equal rows at two positions are two effects. A stream (`stm-`) is the one
registration of a generation to one sink incarnation; sessions (`sts-`),
issuances (`sti-`) and sink commits (`skc-`) are history, not authority. Reading
and submitting need distinct fresh process-local acceptances; the sink
description is read from its owner and compared with independent expectations.
A sink reply is data, a local observation is not a sink commit, and neither is an
S13 acknowledgement, source EOF or generation publication. A changed namespace,
epoch or retention contract is a different destination, never recovery.


## Complete-publication identity

Phase68 [S16](../phases/phase-68/slice-16.md) publishes at most one immutable
reference per generation, keyed by the generation; it adds no new identity
class. The reference names one exact checkpoint, extent `[0, N)`, output
contract, coordinate scheme, closing attempt, closing observation and
publication-owned retention, and the original operation is the only handle a
caller needs after a lost reply. Eligibility is recomputed from raw recorded
facts, never from a stored success flag, files, timing, sink effects or a later
unrelated success; a new attempt never acknowledges an older transaction.
Publishing needs a fresh process-local, purpose-scoped acceptance that
authenticates no one, and the record grants no read: a new reader still needs a
fresh S13 saved-result acceptance. Preparation protection is not publication,
and a later cancellation or publisher change never withdraws a publication.


## Bounded-runtime and collection identity

Phase68 [S17](../phases/phase-68/slice-17.md) adds three identity classes to the
explicit v7 workspace only: a runtime incarnation (`run`, with a monotone epoch),
an admission (`adm`) and a collection decision (`gcd`). None is authority by
itself: a runtime incarnation proves only that its process held the workspace's
runtime lock when it claimed the epoch; an admission is the process-local
allowance a v7 capture needs to claim files, settled exactly once by its own
epoch or reconciled by a later one; a collection decision authorizes deleting
only the exact objects it pinned, after the roots were recomputed under the
generation's exclusive lease. A chunk claim names one future file before it can
exist. Retirement is an explicit, fenced, monotone local decision about one
unpublished generation; it is never inferred from cancellation, time, a PID or
pressure, and it never withdraws a publication. History rows keep their
identities after collection; a tombstoned subject is refused, never resurrected.
