# Public Surface Stability Hardening v1

## Boundary

Phase 36 Slice 10 is tests-only hardening with a docs/spec decision record.
Slice 10 locks public surface stability after Phase 36 Slices 3 through 9 and
makes no behavior change.

Slice 10 does not modify source/compiler behavior, grammar, generated ANTLR
files, parser or AST behavior, semantic behavior, IR or SQL behavior, CLI
behavior, CLI text output, CLI JSON v1, Project JSON v2, Semantic Metadata
Artifact v1 schema or output, fixtures, goldens, examples, package metadata,
package version, lockfiles, validation scripts, workflows, tags, release,
publish/upload, signing, or attestation.

## Public Surface Inventory

The current public surfaces locked by this slice are:

- CLI text output;
- CLI JSON v1;
- Project JSON v2;
- Semantic Metadata Artifact v1 JSON and text output;
- PostgreSQL SQL output;
- private MySQL SQL and JSON output;
- diagnostic envelope shape;
- fixture and golden inventory;
- generated parser inventory;
- package metadata, package version, and package-smoke policy;
- validation scripts and CI workflow role;
- release, publish/upload, signing, and attestation non-authorization.

## CLI Text Output Posture

CLI text output remains current behavior. Slice 10 does not change command
formatting, exit-code policy, diagnostic text rendering, SQL text output,
metadata text output, output-file behavior, or CLI option behavior.

Any future CLI text output change requires separately approved Gate 1 and Gate
2 decisions, plus compatibility and golden/output evidence where applicable.

## CLI JSON v1 Posture

CLI JSON v1 remains `schema_version` 1. Single-file `pietto check --format
json` and `pietto emit-sql --format json` keep their current envelope shapes.
Diagnostic objects keep the current fields `code`, `severity`, `message`,
`location`, and `suggestion`.

Slice 10 does not add CLI JSON v1 fields for Decimal precision/scale, UUID
native behavior, Enum SQL behavior, temporal candidates, Any/Bytes/Json
posture, domain refinement, expanded operator matrix facts, native DB metadata,
package metadata, release metadata, signing, or attestation.

## Project JSON v2 Posture

Project JSON v2 remains `schema_version` 2. Project check JSON keeps the
current root/config discovery envelope with `command="check"` and
`mode="project"`. Slice 10 does not add project source selection, TOML schema
parsing, glob expansion, project source parsing, multi-file semantic analysis,
project IR/SQL, project emit-sql, project explain, metadata aggregation,
relationship/JOIN behavior, runtime/database execution, schema introspection,
db pull, graph/ERD export, or AI metadata export.

Project JSON v2 must remain separate from CLI JSON v1 and Semantic Metadata
Artifact v1 unless a later slice separately approves a compatibility policy.

## Semantic Metadata Artifact v1 JSON/Text Posture

Semantic Metadata Artifact v1 remains `schema_version` 1. The type object
fields remain:

- `status`;
- `name`;
- `kind`;
- `canonical_name`;
- `canonical_kind`;
- `nullability`;
- `support_posture`.

The current `support_posture` vocabulary used by Phase 36 candidates includes:

- `current`;
- `limited_frozen`;
- `metadata_only`;
- `deferred_builtin`;
- `unknown`.

Slice 10 does not add metadata fields for Decimal precision/scale, UUID native
storage, Enum SQL/native metadata, DateTime/Time/Interval timezone or
precision, Any dynamic behavior, Bytes encoding, Json structural typing, type
alias/domain refinement constraints, Currency/Money, expanded operator matrix
facts, native DB metadata, schema introspection, runtime/database execution,
package release metadata, signing, or attestation.

Semantic Metadata Artifact v1 text output remains current deterministic text
rendering over the existing Artifact v1 model. Slice 10 does not add new text
sections or candidate-specific text output.

## SQL Output And Golden Posture

PostgreSQL SQL output and private MySQL SQL/JSON output remain current. Slice
10 does not change SQL renderers, SQL dialect policy, SQL byte output, SQL
goldens, JSON goldens, or fixture inventory.

SQL/golden inventory remains unchanged by Slice 10. Any future public SQL
output change must be separately approved and must include golden ownership and
review evidence.

## Diagnostic Envelope Posture

The diagnostic envelope shape remains stable. Slice 5 changed the unsafe Enum
aggregate path so that `count(Enum field)` now fails closed at semantic
aggregate validation with existing diagnostic `PIE-S2314` instead of reaching
backend diagnostic `PIE-B1000`. That migration is a code/diagnostic behavior
boundary and does not change CLI JSON v1, Project JSON v2, or Semantic
Metadata Artifact v1 diagnostic envelope shape.

Slice 10 does not add diagnostic codes, diagnostic envelope fields, related
location fields, package metadata fields, release metadata fields, signing
fields, or attestation fields.

## Fixture And Golden Inventory Posture

Slice 10 does not add, remove, regenerate, or rewrite fixtures or goldens.
Fixture and golden classification remains owned by `scripts/check_goldens.py`.

## Generated Parser Inventory Posture

Slice 10 does not change grammar or generated ANTLR artifacts. Generated
parser inventory remains owned by `scripts/check_generated.py`, which verifies
ANTLR jar provenance, tracked generated-file inventory, and byte-for-byte
reproducibility.

## Package Metadata, Version, And Smoke Posture

Package version remains `0.1.0`. Slice 10 does not change `pyproject.toml`,
`uv.lock`, dependencies, package metadata, console entry points, build system
configuration, package artifacts, release tags, publishing, upload, signing, or
attestation.

`scripts/package_smoke.py` remains release-readiness smoke only. It builds,
inspects, installs, and smoke tests local package artifacts. It verifies
installed CLI version/help/check behavior, Project JSON v2 project check,
Semantic Metadata Artifact v1 explain output, PostgreSQL byte-exact text
output, and private MySQL JSON v1 structure. It does not publish, upload,
sign, or attest packages.

## Validation Scripts And CI Workflow Posture

`scripts/validate.py`, `scripts/check_generated.py`,
`scripts/check_goldens.py`, and `scripts/package_smoke.py` remain unchanged in
Slice 10. The GitHub Actions workflow remains unchanged and keeps its current
role: run validation, generated-file verification, golden audit, and package
smoke checks. Slice 10 does not start, rerun, dispatch, or poll CI.

## Status-doc Boundary

`README.md`, `AGENTS.md`, and `docs/spec/pietto-v0.9.md` remain deferred to
Slice 11 status housekeeping unless separately approved. Slice 10 does not
perform global status housekeeping and does not refresh status-doc wording.

## Package Smoke DNS/PyPI Policy

When `scripts/package_smoke.py` fails only because of sandbox DNS, PyPI, name
resolution, dependency fetch, or package index access, the failure is
environment-only. Gate 2 evidence must record the raw failure and must not
modify repository files for that environment-only failure.

## Release Non-authorization

Slice 10 authorizes no tag, release, publish/upload, signing, attestation,
package metadata change, package version change, lockfile change, workflow
change, or CI operation.

## Future Prerequisites

Any future public surface change requires separately approved Gate 1 and Gate
2 decisions. Future work must define:

- public schema compatibility policy;
- diagnostic envelope compatibility policy;
- SQL/golden compatibility and review policy;
- fixture and generated inventory policy;
- package metadata and version policy;
- validation script and workflow policy;
- release, publish/upload, signing, and attestation boundaries;
- migration and deprecation policy where compatibility cannot be preserved.

## Explicit Non-authorization

Slice 10 does not authorize source/compiler behavior changes, output schema
changes, public API changes, SQL output changes, fixture/golden changes,
generated parser changes, validation script changes, workflow changes, package
metadata changes, package version changes, lockfile changes, status-doc
housekeeping, tags, releases, publishing, uploads, signing, attestation, CI
operations, runtime/database execution, schema introspection, db pull,
relationship/JOIN behavior, project/multi-file behavior, graph/ERD export, or
AI metadata export.
