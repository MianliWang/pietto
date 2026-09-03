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
