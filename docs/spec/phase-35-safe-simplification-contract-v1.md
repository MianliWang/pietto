# Phase 35 Safe Simplification Contract v1

## 1. Purpose

This specification records the Phase 35 Slice 1 Safe Simplification contract.
It defines how Pietto may discuss maintainability and developer-experience
simplification without changing compiler behavior.

Slice 1 is docs/spec/static-audit-only. It implements no behavior change.

## 2. Title And Scope

The official Phase 35 title remains:

```text
Developer Experience And Delivery Pipeline MVP
```

Safe Simplification is a Slice 1 scope and future-slice discipline. It is not a
roadmap title change, not accepted Pietto syntax, not a compiler feature, and
not authorization for source refactors.

## 3. Phase 34 Handoff And Preservation

Phase 34 completion statement:

```text
Phase 34 Relationship Grain And Narrow JOIN readiness foundation is complete as docs/spec/static-audit/status-only work. The original behavior MVP remains future implementation deferred.
```

Phase 35 must preserve the Phase 34 handoff:

- no JOIN implementation;
- no JOIN syntax;
- no relationship grain syntax;
- no parser or AST behavior change;
- no semantic model change;
- no semantic validation change;
- no diagnostic behavior change;
- no Semantic IR change;
- no PostgreSQL/MySQL SQL lowering change;
- no CLI/JSON/project behavior change;
- no runtime/database/schema-introspection behavior;
- no relationship graph traversal, relationship chaining, or automatic join
  inference.

Phase 35 also preserves Phase 33 project and JSON boundaries: `pietto check
--project ROOT` remains root/config-only, project source selection remains
deferred, Project JSON v2 remains check root/config-only, project emit-sql and
project explain remain rejected, single-file `check` and `emit-sql` JSON remain
JSON v1, and single-file `explain --format json` remains Semantic Metadata
Artifact v1.

## 4. Safe Simplification Definition

Safe Simplification means:

- reducing duplication;
- clarifying local control flow;
- improving helper boundaries;
- improving developer guidance;
- doing any of the above only when public behavior is unchanged.

Safe Simplification is not large rewrite permission. It is not permission to
reshape outputs, diagnostics, SQL, JSON, generated files, goldens, package
metadata, dependencies, workflows, or public CLI behavior.

## 5. No-behavior-change Standard

A simplification is allowed only if it preserves:

- accepted/rejected programs;
- diagnostics code/message/order/span where applicable;
- SQL bytes;
- JSON v1;
- Project JSON v2;
- Semantic Metadata Artifact v1;
- generated inventory;
- goldens;
- package version;
- dependencies;
- workflows;
- public CLI behavior.

Any candidate that cannot prove this standard is not safe simplification.

## 6. Candidate Categories

Every simplification candidate must be classified as one of:

- `safe docs/status housekeeping`;
- `safe test-helper simplification`;
- `safe internal helper simplification with proof`;
- `behavior-risky refactor`;
- `defer / do not touch`.

Risk classification examples:

- `AGENTS.md`, `README.md`, and `docs/spec/pietto-v0.9.md` status cleanup is
  later dedicated housekeeping, not Slice 1.
- Repeated Phase 34 test helpers are later test-helper simplification
  candidates.
- CLI pipeline helper extraction requires full CLI JSON/text proof.
- SQL renderer de-duplication is behavior-risky because it can change SQL bytes
  and backend fail-closed behavior.
- Grammar, generated files, fixtures, goldens, package metadata, dependencies,
  and workflows are `defer / do not touch` in Slice 1.

## 7. Ponytail-inspired Pietto Style Rules

Pietto-compatible ponytail-inspired development style means:

- prefer boring, local, explicit code;
- prefer small pure helpers;
- keep the main path straight and readable;
- avoid speculative abstraction;
- avoid hidden side effects;
- remove duplication only with exact public-surface proof;
- preserve fail-closed branches over compact ambiguous control flow;
- preserve stable diagnostics and output over shorter code.

These rules are developer-experience guidance. They do not define Pietto source
syntax, AST nodes, semantic model fields, IR fields, SQL rendering behavior, or
CLI output behavior.

## 8. Evidence Requirements For Future Refactor Slices

Any future refactor slice must provide:

- pre-check raw output;
- full diff;
- focused diff for approved files;
- full `cat` output for changed files;
- replacement table;
- forbidden surface checks;
- validation raw output;
- package/tag proof;
- final integrity check.

For behavior-adjacent helper changes, the evidence must include focused tests
for the exact public surface at risk: diagnostics, SQL bytes, JSON v1, Project
JSON v2, Semantic Metadata Artifact v1, CLI text, package smoke, generated
inventory, and goldens as applicable.

## 9. Explicit Non-goals

Slice 1 does not authorize:

- source refactor;
- test-helper refactor;
- `README.md`, `AGENTS.md`, or `docs/spec/pietto-v0.9.md` status cleanup;
- behavior change;
- grammar or generated changes;
- fixture or golden changes;
- package metadata, dependency, lockfile, or workflow changes;
- JOIN implementation;
- JOIN syntax;
- relationship grain syntax;
- project source selection;
- multi-file semantic behavior;
- runtime/database behavior;
- release/tag/publish/upload/signing/attestation.
