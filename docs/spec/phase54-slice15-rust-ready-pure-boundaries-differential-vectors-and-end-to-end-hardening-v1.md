# Phase 54 Slice 15 Rust-ready Pure Boundaries, Differential Vectors, And End-to-end Hardening v1

## Status And Authority

This document is the Gate 2 candidate contract for Phase 54 Slice 15. Phase 54
is `ACTIVE`; Slices 1 through 14 and the unnumbered post-Slice-12 workflow
hardening interlude are `COMPLETED`; Slice 15 remains incomplete until exact
reviewed-tree publication, natural exact-head pull-request continuous
integration, review closure, squash-tree equality, natural exact-head `main`
continuous integration, reconciliation, cleanup, and immutable Gate 3 evidence
all succeed.

Slice 15 prepares the settled private Phase 54 module product for a future
independent implementation. It defines one pure, deterministic, Rust-ready
boundary over the already published Slice 14 canonical serialization, one
private differential-vector corpus for that boundary, one deterministic Python
reference harness, and end-to-end hardening of the private schema-v2 pipeline.

Slice 15 implements **no production Rust**. It adds no foreign function
interface, PyO3 binding, Cargo metadata, native extension, second runtime, or
public artifact format. Slice 16 retains the Phase 54 completion audit, the
status lock, the final end-to-end closure, and the Phase 55 handoff.

## Authority Roots

Slice 15 introduces no new authority root. Its inputs are exactly the settled
products the Slice 14 contract already anchors:

| Input | Owner | Slice 15 use |
| --- | ---: | --- |
| the ten-root shared exact-authority predicate | 14 | unchanged admission |
| `ProjectModuleInspection` canonical projection | 14 | portable projection input |
| the canonical private byte payload | 14 | the exact expected output |
| the eleven-sidecar all-or-none invariant | 14 | unchanged integration posture |

`ProjectSemanticResult` keeps exactly eleven private module sidecars.
`src/pietto/_project/model.py` is unchanged and no twelfth sidecar is added.

## The Three Separate Layers

1. **Python authority-root admission.** The Slice 14 shared root predicate,
   validated as a whole by object identity. Slice 15 weakens nothing and adds
   nothing here.
2. **Python-side canonical projection.** `_project_pure_document` turns the
   settled `ProjectModuleInspection` into a portable document value. Object
   identity may be used up to and including this layer.
3. **Portable pure value boundary.** `evaluate_pure_document` is a total
   function from an explicitly supplied immutable document value to either the
   exact canonical bytes or one normalized rejection.

Portable pure-value validation is not Python authority admission, and neither
is a public external format. The three layers are never conflated.

## The Narrowest Sufficient Pure Boundary

The Slice 14 canonical serialization is already the deterministic product a
later independent implementation must reproduce, so the narrowest sufficient
pure boundary is the **canonical document boundary**: the record stream the
canonical projection produces, validated against one frozen declared record
schema and encoded into the exact Slice 14 private bytes.

No second inspection product and no second serialization product is invented.
`src/pietto/_project/module_pure_boundary.py` owns the boundary, its `__all__`
remains empty, and the production serializer **uses** that boundary rather than
merely comparing against it. Exactly one canonical serializer exists in the
repository, so no testing-only model can drift away from production behavior.

## Portable Input And Output Value Algebra

All carriers are private, frozen, slotted, keyword-only, and primitive-only.

```text
ProjectPureTag      := TEXT "s" | INTEGER "i" | BOOLEAN "b"
                     | ENUMERATION "e" | ABSENT "n"
ProjectPureValue    := tag, text: str | None, integer: int | None,
                       boolean: bool | None
ProjectPureField    := key: str, value: ProjectPureValue
ProjectPureRecord   := kind: str, fields: tuple[ProjectPureField, ...]
ProjectPureDocument := records: tuple[ProjectPureRecord, ...]
ProjectPureOutcome  := status, canonical_bytes: bytes | None,
                       record_position: int | None,
                       field_position: int | None
```

Carrier construction enforces exact primitive Python types and nothing else, so
every corruption the differential contract must reject stays constructible.
`bool` is refused where `int` is declared, because `bool` is an `int` subclass
in Python and would otherwise smuggle a boolean into an integer payload. A
Python enumeration member is refused as a text payload, so no Python
enumeration identity can cross the boundary; the projection supplies the
declared enumeration text instead.

There is no separate document-level format marker. The marker is exactly the
`format` key of the mandatory first `inspection` record, whose only accepted
value is the published Slice 14 marker `pietto.module-inspection.v1`, so two
views can never disagree about it. Any other value is
`UNKNOWN_FORMAT_MARKER`.

An accepted outcome carries the payload and no coordinate. Every rejection
carries no payload plus the deterministic structural coordinates of the first
violation in document order, and never echoes a supplied text, enumeration,
key, or kind.

The reporting order is itself part of the differential contract, because an
independent implementation must return the same triple:

1. violations are reported strictly in document order, and no rule about a
   later record may pre-empt a violation in an earlier one;
2. inside one record the declared field contract is checked before every
   structural rule, with the single unavoidable exception of an unknown record
   kind, which has no declared field contract to check;
3. a reported coordinate is always a position that exists in the supplied
   stream, so the absence of a required record carries no coordinate at all.

## Frozen Normalized Rejection Algebra

The status vocabulary is closed. No standard-library exception class is part of
the differential contract, so the behavior is identical on every supported
interpreter.

```text
EMPTY_DOCUMENT                 MISSING_HEADER_RECORD
UNEXPECTED_HEADER_RECORD       UNKNOWN_RECORD_KIND
UNKNOWN_FORMAT_MARKER          FIELD_ARITY_MISMATCH
FIELD_KEY_MISMATCH             VALUE_TAG_MISMATCH
ABSENT_VALUE_NOT_ALLOWED       MISSING_VALUE_PAYLOAD
EXTRA_VALUE_PAYLOAD            NEGATIVE_INTEGER
INTEGER_OUT_OF_RANGE           UNKNOWN_ENUMERATION
INCONSISTENT_RECORD_STATE      ORPHAN_RECORD
SCOPE_ORDINAL_MISMATCH         SECTION_ORDER_VIOLATION
CHILD_ORDER_VIOLATION          ORDINAL_SEQUENCE_VIOLATION
DUPLICATE_SINGLETON_RECORD     MISSING_REQUIRED_RECORD
CHILD_COUNT_MISMATCH           TRAILING_RECORD_AFTER_DOCUMENT
```

The integer domain is bounded explicitly at `PURE_MAX_INTEGER`, two to the
sixty-third minus one. Every integer in the canonical projection is a count, an
ordinal, a source position, or an opened-byte count, and an unbounded domain
would make the boundary neither total nor process independent, because
rendering an arbitrarily large integer depends on a process-level digit limit.
A value above the bound is `INTEGER_OUT_OF_RANGE`.

`TRAILING_RECORD_AFTER_DOCUMENT` fires at the first body record when the header
declares zero modules and any further record follows. `MISSING_HEADER_RECORD`
carries the position of the wrong record when one is present, and no coordinate
when the record is simply absent.

## Frozen Declared Record Schema

Thirty-four record kinds, exactly the Slice 14 set. Each declares a fixed
lowercase ASCII kind, a fixed ordered key list, a fixed tag per key, a fixed
optionality per key, and, for every enumeration key, a fixed vocabulary. The
mandatory `inspection` header opens the document scope, so the declared module
count, the module ordinal density, and every nested count are verified by one
scope machine rather than by a special case.

```text
sec kind                        scope chain                       ordinal rule
--  --------------------------  --------------------------------  ------------
--  inspection                  (document)                        singleton
--  owner                       (document)                        singleton
00  module                      module                            dense
01  digest                      module                            singleton
02  readiness                   module                            singleton
02  readiness_cycle             module, cycle                     dense
02  readiness_cycle_member      module, cycle, member             dense
03  graph                       module                            singleton
03  graph_component_member      module, member                    dense
03  graph_dependency_target     module, target                    dense
03  graph_import_evidence       module, evidence                  dense
04  import                      module, request                   dense
04  import_issue                module, request, issue            dense
05  export                      module, request                   dense
05  export_issue                module, request, issue            dense
06  declaration                 module, declaration               dense
06  declaration_row_field       module, declaration, field        dense
07  origin                      module, origin                    dense
07  origin_hop                  module, origin, hop               dense
08  dependency                  module, dependency                dense
09  row_lineage                 module, lineage                   dense
09  row_lineage_field           module, lineage, field            dense
09  row_lineage_path            module, lineage, field, path      dense
09  row_lineage_hop             module, lineage, field, path, hop dense
10  type_resolution             module, resolution                dense
10  type_resolution_alias       module, resolution, alias         dense
11  source_shape_resolution     module, resolution                dense
12  relation_resolution         module, resolution                dense
13  semantic_facts              module, facts                     dense
13  semantic_let_binding        module, facts, binding            dense
13  semantic_select             module, facts, select             dense
13  semantic_clause_dependency  module, facts, dependency         dense
13  semantic_window_output      module, facts, output             dense
14  issue                       module, issue                     dense
```

`dense` means the ordinal equals the number of preceding siblings of the same
kind in the same parent scope, starting at zero. Every ordinal in the canonical
projection is dense, and there is deliberately no second ordinal rule.

For the enumeration-indexed kinds density holds by construction. For
`declaration` it holds by a validated authority invariant rather than by
assumption: `ProjectModuleCatalog` rejects any occurrence whose
`declaration_position` differs from its index in the module's complete
source-ordered occurrence tuple, and the Slice 14 root predicate requires the
Slice 13 declaration assets to be exactly that complete ordered projection.
Adopting the weaker "strictly increasing" rule instead would accept a document
with a dropped first or middle declaration, so density is the rule that matches
the authority rather than an over-broad one.

The portable boundary rejects a malformed record stream. It does not, and
cannot, detect a well-formed stream that simply describes different content:
truncating the tail of a module-level section that the Slice 14 format gives no
declared count is not a corruption but a different, valid document, and it is
detected by comparing canonical bytes against the authority rather than by
validation. Adding per-section counts to make it detectable would change the
canonical bytes and is therefore forbidden.

Every parent that declares a child count has that count verified exactly:
`inspection.modules`, `readiness.cycles`, `readiness_cycle.members`,
`graph.component_members`, `graph.dependency_targets`, `graph.import_evidence`,
`import.issues`, `export.issues`, `declaration.row_fields`, `origin.hops`,
`row_lineage.fields`, `row_lineage_field.paths`, `row_lineage_path.hops`,
`type_resolution.alias_chain`, `semantic_facts.let_bindings`,
`semantic_facts.selects`, `semantic_facts.clause_dependencies`, and
`semantic_facts.window_outputs`. Each module scope additionally requires
exactly one `digest`, one `readiness`, and one `graph`.

Twenty-four enumeration vocabularies are declared as portable literal data
inside the boundary and proved equal to the live Python enumerations by a
focused test, so a new enumeration member cannot silently escape the frozen
vocabulary. The `issue.status` key is text rather than an enumeration, because
its vocabulary is family dependent and the family check already belongs to the
Slice 14 projection layer.

## Frozen Encoding Algebra

Identical to the published Slice 14 canonical serialization, restated as the
portable contract: UTF-8 without a byte order mark; one record per line with
every line terminated by exactly one line feed including the last, so the
payload is never empty and always ends with exactly one newline; a record is
its kind followed by `\t` separated `key=token` pairs in the fixed declared key
order; `s:` text, `i:` integer, `b:` boolean, `e:` enumeration, and `n:`
absence, where `n:` is exactly two characters and is the only representation of
absence; text and enumeration payloads escape `\` as `\\`, tab as `\t`, line
feed as `\n`, carriage return as `\r`, every other code point below U+0020 plus
U+007F as `\x` and two lowercase hexadecimal digits, and every code point from
U+D800 through U+DFFF as `\u` and four lowercase hexadecimal digits; every
other code point is emitted literally as UTF-8; integers are canonical
non-negative decimal with no sign and no leading zero except the single digit
`0`; booleans are exactly `true` or `false`; and no floating point value,
representation string, object address, process identifier, or host path is ever
encoded.

## Exactness And Negative-compatibility

The refactor preserves behavior exactly, and each obligation is tested
separately:

- canonical bytes for every fixture are byte-identical to the published Slice
  14 product;
- authority-root admission is unchanged and remains at least as strong;
- schema v1 remains byte-exact and behavior-exact;
- schema v2 remains private and keeps `model=None`;
- no public output, export, command-line surface, or serializer key changes;
- the eleven-sidecar all-or-none invariant is unchanged.

The new portable validation now runs on every production serialization, so its
negative-compatibility matrix is explicit: every currently accepted inspection
still serializes identically; `declaration` density is the validated catalog
invariant rather than a new assumption, so no accepted inspection can violate
it; the retained
text checks stay type-only so an empty or unresolvable retained text is still
accepted; and every enumeration reaching the boundary is produced by a live
enumeration, which the vocabulary-equality test proves.

Cross-field state is not left to independent per-field checks. Validating the
enumeration values of a record one at a time accepts combinations the authority
forbids, so each such invariant is declared as portable data and enforced as
`INCONSISTENT_RECORD_STATE`. Every declared rule mirrors an invariant an
upstream carrier already enforces atomically, so none of them narrows the
accepted language beyond what the projection can produce:

The table is derived from each upstream carrier's own validation, one carrier
at a time, rather than assembled by inspection. Deriving it any other way is
what produced two rounds of isomorphic findings.

| Record | Declared rule | Upstream authority |
| --- | --- | --- |
| `owner` | the kind is the project root, which stays unnamed, in the reserved empty local namespace | `ProjectLayeredOwnerIdentity` |
| `digest` | the digest is exactly sixty-four lowercase hexadecimal characters | `ProjectLayeredSourceDigestIdentity` |
| `readiness` | the `status`, `reason`, and cycle-count triple is one of exactly two combinations | `ProjectLayeredLoaderReadinessFact` |
| `readiness_cycle` | the member count is positive | `ProjectInspectionModuleCycle` |
| `graph` | the component-member count is positive, and any multi-member component proves a cycle | `ProjectInspectionGraph`, `ProjectModuleStronglyConnectedComponent` |
| `import` | the namespace and declaration kind form an eligible pair, and the four resolved-target keys are present together or absent together | `ProjectImportedBindingIdentity`, `ProjectInspectionImport` |
| `export` | the namespace and declaration kind form an eligible pair, and the six facade-entry keys are present together or absent together | `ProjectModuleExportRequest`, `ProjectInspectionExport` |
| `declaration` | the owner kind is the module and its namespace is the reserved empty local namespace; the relation status and reason are one atomic pair; a retained relation state maps its exact availability; a positive row-field count requires the relation state; the occurrence count is positive; the occurrence index is inside its bucket | `ProjectInspectionDeclaration`, `ProjectLayeredDeclarationAsset`, `ProjectLayeredOwnerIdentity` |
| `origin` | a local origin is one self path with no hop; an imported origin always carries its access chain | `ProjectModuleOriginPath` |
| `origin_hop` | the chain re-exports at every interior hop and terminates at a local declaration | `ProjectModuleOriginPath` |
| `row_lineage` | a non-concrete lineage carries no field | `ProjectModuleRelationLineage` |
| `row_lineage_field` | every retained field keeps at least one complete path | `ProjectModuleRowFieldLineage` |
| `dependency` | each target group is atomic, and the kind decides which single group is present | `ProjectModuleDependencyFact` |
| `type_resolution` | the canonical-target pair is atomic; an enumeration or shape canonical kind requires that target and a builtin or unknown one forbids it; a canonical kind never terminates at an alias; only a direct alias carries an alias chain | `ProjectResolvedModuleTypeReference` |
| `issue` | the status belongs to its declared family | `ProjectInspectionIssue` |

### What the portable layer does and does not re-validate

The declared set is complete against a mechanical enumeration of every
``__post_init__`` guard in the ten contributing carrier modules. Each guard was
classified once, and the classification is the boundary:

- **Declared here** — every guard whose operands are all serialized values of
  one record, plus the one positional relationship the record stream itself
  carries, namely whether a child is the last declared sibling of its kind.
- **Not declarable, by construction** — a guard that compares a serialized
  value against a *retained authority object* (`is not self.fact.status`,
  `!= self.request.local_name`, `is not self.asset.owner`). These are decided by
  object identity, which must never cross the portable boundary. They are the
  Python authority-admission layer, which owns the roots, and re-deriving them
  portably would create the second authority for the same fact that the
  convergence governance forbids.
- **Not declarable, cross-record** — a guard relating values in different
  records, such as a declaration owner name against its enclosing module path,
  or an alias chain against the resolutions around it. The record stream carries
  each record independently, so expressing these would require the portable
  layer to rebuild the projection it is validating.

A later independent implementation therefore reproduces the canonical bytes and
this rejection algebra; it does not reproduce the Slice 5 through Slice 14
semantic model, which stays where its roots are.

Text content is deliberately not re-validated beyond the declared digest shape.
Slice 14 keeps its retained-text checks type-only because upstream stages
retain an unresolvable or empty decoded target, exported name, or output name
and report it through their own issue facts; re-validating that content at the
portable layer would reject a pre-existing accepted case.

A key may contribute its presence rather than its value to a combination, so
one declared table expresses a correlation between an enumeration and whether
an optional group is supplied. That single mechanism replaced a separate
exclusivity rule, because "exactly one target, chosen by the kind" is stronger
than "not both" and is what the authority actually enforces.

A declared state that contradicts its accompanying records rather than its own
fields remains `CHILD_COUNT_MISMATCH` or `MISSING_REQUIRED_RECORD`.

## Differential-vector Schema And Ownership

The corpus is an internal test asset. It is not a public fixture, a package
manifest, a cache format, or a compatibility promise to any external consumer.

`tests/_pietto_differential_vectors.py` owns the frozen corpus data.
`tests/_pietto_differential_harness.py` owns the vector carrier, the schema
validation, the runner, the comparison, the machine-readable summary, and the
reviewed authoring proposal. Neither is imported by production code, and
neither imports the production inspection module.

Frozen vector-format marker: `pietto.differential-vectors.v1`.

```text
DifferentialVector := vector_format, vector_id, purpose, classification,
                      document, expected_status, expected_bytes,
                      expected_record_position, expected_field_position
```

`vector_id` is a stable lowercase ASCII private identifier, unique across the
corpus, never derived from a path, a digest, or a timestamp. `classification`
is exactly one of `PORTABLE_EVALUATION` or `PORTABLE_REJECTION`. Python
authority-root admission is deliberately not a classification value: it is
decided by object identity, which must never be encoded as cross-language data,
so the end-to-end suite exercises that layer and no vector can carry it. A
declared member no vector could ever hold would make the schema contradict this
contract. An accepted
vector stores its expected payload as an exact byte literal and carries no
coordinate; a rejected vector stores the expected status and coordinates and
carries no payload. Corpus order is the declared tuple order and is
deterministic. No vector depends on an absolute path, a temporary directory, a
memory address, an object identifier, host metadata, a timestamp, or
version-control state.

Python object identity is never encoded as cross-language data. The Python
authority-admission layer is therefore exercised by the end-to-end suite rather
than by a portable vector.

## Vector Property Matrix

Accepted dimensions: empty project; one module; several modules; declaration
order and multiplicity; the same spelling in distinct modules; the same
spelling in distinct namespaces; an alias distinct from its nominal target; two
aliases to one target; explicit re-export; every availability state; a module
cycle with blocked loader readiness; a duplicate nominal identity bucket with no
winner; equal opened-byte digests on distinct modules; direct and renamed
lineage; preserved generic, nullability, aggregate, grouped, window,
result-role, and capability facts; the nullability and result-role matrix;
surrogate text; control-character text; non-ASCII text; absent versus empty
text; boundary cardinalities zero, one, two, and three; a larger repeated
bucket; issue families; a type alias chain; import and export issue buckets;
dependency target variants; boolean values; and an unresolved import.

Rejected dimensions: empty document; missing header; unexpected header;
trailing record; wrong format marker; stale format marker; unknown record kind;
unknown key; missing key; extra key; wrong key order; wrong value tag; absent
where absence is not allowed; missing payload; extra payload; negative integer;
unknown enumeration; orphan record; wrong parent ordinal; reordered sections;
reordered sibling kinds; duplicated record; missing record; non-dense ordinal;
non-dense declaration ordinal; child count too large; missing required
singleton; duplicate singleton; module count mismatch; and an impossible state
combination.

Every dimension is exercised at least once, and combinations are used only
where the interaction is the property under test. Final vector counts are facts
of the sealed tree.

Two coverage guards keep the corpus honest against future drift rather than by
inspection: every one of the thirty-four declared record kinds must appear in at
least one accepted vector, and every key declared optional must appear absent in
at least one vector. A declared optionality mirrors the Slice 14 carrier's own
optional type and its `_optional_*` emitter; it is never narrowed to whatever
the current grammar happens to produce, because that would encode a language
accident into the portable schema.

A vector's declared purpose is additionally checked against what its document
really contains for every mechanically checkable dimension, so a mislabelled
vector cannot silently satisfy the matrix.

## Harness Independence

The harness loads or constructs the corpus, validates the vector schema, runs
the portable boundary, compares the exact payload or the exact normalized
rejection with its coordinates, and emits one concise machine-readable summary
line. It performs no network access, no version-control access, and no
repository-file mutation, and it fails closed on a malformed vector, a non-text
or duplicate identifier, a missing expected payload, an accepted vector carrying
a coordinate, a rejected vector carrying a payload, and a rejection that omits a
record coordinate its status always carries. The accepted vectors are declared
as ordered identifier triples rather than a mapping, so a repeated identifier
reaches that check instead of being folded away before it.

Expected outputs are stored literals in one clearly marked block of the vector
module, exported through an immutable view so no in-process assignment can
replace one. `propose_expected_updates` is the only authoring path; it returns a
proposed diff for review and writes nothing, so an expectation can never be
silently regenerated. It proposes for every real disagreement, including a
rejection whose coordinates moved, and a run that finds a disagreement reports a
failure.

The harness never derives an expected value from the implementation under test,
so the comparison is not tautological. Separately, a bootstrap suite builds real
Slice 14 schema-v2 projects, projects each settled inspection into a portable
document, evaluates it, and requires exact equality with the published
`canonical_bytes`. Surrogate paths, non-ASCII paths, cycles, and duplicate
identity buckets are part of that bootstrap set.

## End-to-end Hardening

The hardened path is the settled roots, the Slice 13 package-neutral facts, the
Slice 14 inspection projection, the Slice 14 canonical bytes, the Slice 15
portable document, the Slice 15 pure evaluation, and the differential-vector
comparison.

Before the portable boundary is ever reached, an omitted root, an injected
foreign root, a value-equal foreign root, a same-path foreign project,
reordered roots, a coordinated mixed-root replacement, a forged derived
inspection, forged canonical bytes, and deletion of any one of the eleven
sidecars all fail closed. Legacy-flat results still forbid all eleven sidecars.

At or after the portable boundary, an altered portable value with an unchanged
expected output, an altered expected output with an unchanged portable value, a
duplicate vector identity, a partial vector, an impossible status and reason
combination, a stale format marker, and a one-field mutation across every
load-bearing identity, order, state, and digest family all fail closed.

The vector layer proves portable behavior only after exact Python authority
admission and never replaces that admission.

## Performance

The portable projection is one pass over the settled canonical projection. The
pure evaluation is one pass over the record stream with an explicit scope
stack: no record rescans the document and no child rescans its parent. The
declared schema is frozen module-level data built once, never per record and
never per document. When the production path does fail closed it reports the
normalized status and its structural coordinates, which carry no supplied
content, so a fail-closed build stays diagnosable. The harness indexes vector identifiers once and never
rescans the corpus per vector. Bounded evidence records that the field
validator is invoked exactly once per record and that payload size stays linear
in the number of records, including a repeated-identity bucket case. No broad
performance framework and no timing threshold is added.

## Privacy

The pure-value layer, the vector layer, the harness summary, and every
rejection contain and emit no absolute host path, invocation path, canonical
real path, symbolic-link target, device or inode identity, file size or
timestamp beyond the already authorized Slice 13 opened-byte count, environment
variable, credential, memory address, `id()` value, Python representation
string, raw or decoded source text, temporary path, version-control or forge or
continuous-integration identity, and no runtime journal content.

Project-relative module identity and the already authorized opened-byte digest
identity remain allowed exactly where the Slice 14 product already includes
them.

## Rust Readiness And Retained Later Work

Rust readiness here means explicit private pure inputs and outputs,
deterministic total behavior for admitted inputs, normalized rejection
behavior, no ambient input or output, documented ordering, multiplicity,
scalar, string, enumeration, byte, and optional representations, differential
vectors sufficient for a later independent implementation, and a Python
reference harness suitable for later cross-language comparison.

It does not mean adding Rust source, Cargo metadata, a crate layout, PyO3, a
foreign function interface, WebAssembly, a C application binary interface, a
subprocess protocol, or a build-system dependency, and it claims no
Rust-and-Python equivalence before a Rust implementation exists.

Recorded as retained later work rather than decided here:

- production Rust, a Rust crate layout, differential execution against Rust,
  and the integration technology choice (Phase 68);
- native builds, packaging, wheels, and source distributions (a separate
  Release authority);
- a public inspection, portability, vector, or artifact format (Phase 58);
- package manifests, asset schemas, registries, discovery, installation,
  caches, trust, and dependency solving (Phases 55, 59, 67, and 68);
- deserialization and persisted runtime restoration;
- Project IR, relationship, JOIN, grain, fanout, project SQL, and QUALIFY
  (Phases 61 through 63);
- new grammar, abstract syntax tree, diagnostics, type, aggregate, window, or
  language semantics;
- release, publishing, signing, and attestation (a separate Release Gate).

## Negative Boundary

Slice 15 adds no public export, command-line option, command-line text or JSON
v1 field, Project JSON v2 key or key order, Semantic Metadata Artifact v1 key,
diagnostic code, diagnostic message, grammar, generated artifact, abstract
syntax tree node, intermediate representation node, PostgreSQL or MySQL SQL
behavior, fixture, golden, example, package dependency, lockfile, workflow,
package version, release, signing, attestation, runtime behavior, or database
behavior.

A material unresolved public-format, external-compatibility, package-identity,
loader-behavior, Rust-integration, or Slice 16 ownership question is a
substantive stop rather than an invitation to invent a public product.

## Validation Lock

The focused property matrix covers the private module surface and its privacy;
the thirty-four declared record kinds and their exact key orders against a real
canonical payload; vocabulary equality with every live enumeration; scope
chains, child counts, ordinal rules, singletons, and section order; the token
and escaping algebra including the complete surrogate range, control
characters, DEL, and non-ASCII text; the final-newline rule and canonical
integer form; production use of the portable core; byte-exact reproduction of
real projects through the boundary; the absence of Python enumeration or object
identity in the projected document; forged-payload and grafted-projection
rejection; ambient-dependency freedom; totality and determinism; repeated
processes and varied `PYTHONHASHSEED`; agreement across every discoverable
supported interpreter; working-directory and environment independence;
reachability and normalization of every rejection status; leak-free rejections;
carrier and outcome atomicity; corpus coverage of the frozen property matrix;
unique, deterministic, lowercase vector identifiers; deterministic corpus
order; stored literal expectations; no silent regeneration; vector privacy;
harness fail-closed behavior on malformed and duplicate vectors; the
machine-readable summary; the non-writing authoring mode; harness and
production implementation-path independence; one validation pass per record;
bounded repeated-identity buckets; end-to-end root integrity; the eleventh
all-or-none sidecar boundary with schema-v1 exactness; the unchanged public
surface; and the retained Rust and Slice 16 boundaries. Dimensions are covered
without a Cartesian product.

Gate 2 additionally requires the exact 59-reader zero-addition and zero-delta
fixed point, check-only Ruff over the exact 65 Python paths, production and test
Pyright, focused and compatibility suites, the applicable publication-topology
projections, generated count 8, golden count 37, package smoke, lock check,
authoritative offline validation, an independent full pytest run, the exact
`A5_M64_D0` allowlist, an empty Git index, a reviewed tree, and immutable
evidence.

Gate 3 alone may make Slice 15 `COMPLETED`; the next valid resume point is then
`PHASE54_SLICE16_GATE0_GATE1`.
