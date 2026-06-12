# Phase 11: Release Readiness & Reproducible Validation

## Status

**Phase 11 Release Readiness & Reproducible Validation is complete.**

**Slice 1: Master Plan And Baseline Audit is complete.**

**Slice 2: Authoritative Validation Entry Point is complete.**

**Slice 3: ANTLR Provenance And Generated-File Guard is complete.**

**Slice 4: Golden Fixture Policy And Audit is complete.**

**Slice 5: GitHub Actions CI is complete.**

**Slice 6: Packaging And Installed CLI Smoke is complete.**

**Slice 7: Completion Audit And Documentation is complete.**

Phase 10 MySQL SQL Generation MVP is complete. Phase 11 strengthens the
release, validation, generated-code, golden-fixture, CI, and packaging
workflows around that completed compiler baseline. It does not expand the
Pietto language, compiler pipeline, CLI, JSON schema, SQL surface, public
Python API, or runtime capabilities.

## Goal

Make the completed single-file PostgreSQL and MySQL generation toolchain
repeatably verifiable from a clean checkout before any further language or SQL
feature expansion.

The preserved compiler pipeline is:

```text
Pietto source
    -> parse
    -> analyze
    -> build IR
    -> explicitly selected PostgreSQL or MySQL SQL backend
    -> CLI text or JSON v1 output
```

Phase 11 turns existing manual validation practices into explicit repository
contracts. The phase must preserve:

- `requires-python = ">=3.12"`;
- Python 3.12 as the declared compatibility floor;
- CI validation on Python 3.12 and Python 3.13;
- the handwritten PostgreSQL backend as the byte-exact reference;
- every existing PostgreSQL and MySQL reviewed golden output;
- `emit_postgres_sql(ScriptIR) -> SqlResult` as the public SQL emitter;
- the private `pietto.sql.mysql.emit_mysql_sql` boundary;
- the absence of a generic public `emit_sql(...)`;
- the current single-file CLI and JSON schema version 1;
- compiler-stage isolation and generation-only behavior;
- the current production dependency and lockfile surface.

The Python 3.12 value in `pyrightconfig.json` remains the static-analysis
language target. A later Python 3.12/3.13 CI interpreter matrix does not by
itself change that configuration or raise the package compatibility floor.

## Post-Phase-10 Baseline

At Slice 1 entry, the repository provides:

- one-file parsing, semantic analysis, immutable Semantic IR, and SQL
  generation;
- explicit PostgreSQL and MySQL CLI selection;
- CLI text and JSON v1 output;
- a public PostgreSQL emitter and private MySQL emitter;
- five reviewed PostgreSQL SQL goldens and three reviewed MySQL SQL goldens;
- structural JSON golden coverage;
- production and test Pyright configurations with zero diagnostics;
- tracked ANTLR 4.13.2 generated files and jar;
- one production dependency, `antlr4-python3-runtime`;
- a buildable Python package with a `pietto` console entry point.

The validated Slice 1 entry commands are:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pyright --project pyrightconfig.tests.json
uv run pytest
uv lock --check
```

The entry result was 1290 passing tests, zero Ruff findings, zero production
or test Pyright diagnostics, and a valid lock resolving 19 packages.

Slice 2 implements the repository validation entry point. Slice 3 implements
the reviewed ANTLR jar checksum and an independent generated-file guard.
Slice 4 implements the golden fixture policy and independent inventory,
ownership, and JSON-validity audit. Slice 5 implements minimal-permission
GitHub Actions orchestration for the accepted local commands. Slice 6
implements the independent package build, archive inspection, clean-install,
and installed-CLI smoke. Slice 7 completes the cross-slice workflow,
compatibility, scope, and deferred-capability audit.

## Phase Boundary

Phase 11 may add only repository release-readiness infrastructure:

- one authoritative non-mutating validation entry point;
- ANTLR jar provenance verification and generated-file comparison;
- a documented and audited golden-fixture policy;
- GitHub Actions CI with minimal permissions;
- package build, clean-install, and installed-CLI smoke tests;
- focused planning and completion audits;
- scope-aware release-readiness documentation.

Phase 11 does not add or change:

- Pietto grammar, generated ANTLR content, AST, semantic analysis, or IR;
- PostgreSQL or MySQL SQL rendering behavior;
- CLI commands, flags, exit codes, streams, or output-file behavior;
- JSON schema version 1 or a JSON version 2 implementation;
- public Python APIs or SQL result models;
- production or development dependencies;
- `pyproject.toml` or `uv.lock`;
- SQL syntax or features, including `ORDER BY` or `LIMIT`;
- SQLGlot or a generic backend abstraction;
- SQL execution, database connections, connector execution, or schema
  introspection;
- project or multi-file mode, `pietto.toml`, watch mode, LSP/editor support,
  Web UI, online playground, or runtime server.

Phase 11 does not add or modify Makefile targets by default. Makefile
integration is allowed only when the repository already contains a Makefile
and that integration receives separate explicit authorization, or when the
user explicitly requests it in a later slice.

Actual package publication, registry credentials, release signing, provenance
attestations, and automated version changes remain outside Phase 11.

## Slice Sequence

1. **Master Plan And Baseline Audit**: complete. Record the post-Phase-10
   baseline, seven-slice sequence, Python compatibility policy, hard
   boundaries, validation commands, and static planning locks.
2. **Authoritative Validation Entry Point**: complete. Add one non-mutating
   standard-library Python validation script for lock, format, lint, typing,
   and tests.
3. **ANTLR Provenance And Generated-File Guard**: complete. Verify the
   tracked ANTLR jar checksum, regenerate into a temporary directory, and
   compare the complete tracked generated output.
4. **Golden Fixture Policy And Audit**: complete. Publish the reviewed
   fixture policy and add deterministic inventory and orphan checks without
   automatic fixture updates.
5. **GitHub Actions CI**: complete. Run the accepted validation contracts
   with minimal permissions on Python 3.12 and 3.13 and Java 21.
6. **Packaging And Installed CLI Smoke**: complete. Build sdist and wheel,
   install the wheel into a clean temporary environment, and exercise the
   installed CLI outside the repository.
7. **Completion Audit And Documentation**: complete. Verify all Phase 11
   workflow contracts and prove compiler, API, SQL, CLI, JSON, dependency,
   grammar, and runtime boundaries remain unchanged.

The order is fixed. CI must consume accepted local validation commands rather
than becoming a second independent implementation of those checks. Packaging
smoke coverage follows the core validation, generated-file, and golden
contracts.

## Slice 1: Master Plan And Baseline Audit

### Goal

Establish the Phase 11 authority and record the exact release-readiness
baseline without implementing later workflow infrastructure.

### Allowed Changes

Slice 1 may change only:

- this master plan;
- one focused planning and boundary audit test module;
- scope-aware current-phase text in `README.md`, `AGENTS.md`, and
  `docs/spec/pietto-v0.9.md`.

### Hard Boundaries

Slice 1 must not add:

- `.github/workflows/`;
- `scripts/`;
- an ANTLR checksum file;
- a generated-file guard;
- a golden inventory command or policy document;
- a package smoke implementation;
- production code, dependencies, grammar, generated files, SQL fixtures, or
  build metadata changes.

The planning audit locks `pyproject.toml`, `uv.lock`, grammar, generated
ANTLR, frontend/AST, semantic, IR, SQL, CLI, and JSON implementation bytes.
Directory locks hash sorted relative paths, a NUL separator, file bytes, and
a trailing NUL separator so file names and boundaries are unambiguous.

### Validation

```bash
uv run ruff format .
uv run ruff check .
uv run pyright
uv run pyright --project pyrightconfig.tests.json
uv run pytest
uv lock --check
git diff --check
```

## Slice 2: Authoritative Validation Entry Point

**Slice 2 is complete.**

### Goal

Provide one local command that runs the accepted non-mutating repository
quality gates in a deterministic fail-fast order.

### Allowed Changes

Slice 2 adds `scripts/validate.py`, focused script tests, and usage
documentation. The script uses only the Python standard library and
subprocesses already provided by the locked developer environment. It must
not add or modify Makefile targets unless separately and explicitly
authorized under the Phase 11 Makefile policy. No such authorization was
given, so Slice 2 leaves the Makefile unchanged.

The authoritative command will be:

```bash
uv run python scripts/validate.py
```

The same entry point also supports direct invocation:

```bash
python scripts/validate.py
```

The script resolves the repository root from its own file path, so child
commands do not depend on the caller's current directory. Before each gate it
prints the gate name and shell-readable command, leaves child stdout and
stderr attached normally, stops after the first failure, and returns that
gate's exit code. On success it returns `0`.

It runs:

```bash
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pyright --project pyrightconfig.tests.json
uv run pytest
```

### Hard Boundaries

The validation path must not format or rewrite files, install tools, download
unlocked dependencies, regenerate parsers, build packages, update goldens, or
change compiler behavior. It must preserve child exit status and stop at the
first failed gate.

Slice 2 does not add CI, an ANTLR checksum file, a generated-file guard, a
golden policy or audit script, packaging smoke tests, or Makefile integration.

### Validation

```bash
uv run python scripts/validate.py
uv run pytest tests/test_phase11_validation_entrypoint.py
git diff --check
```

## Slice 3: ANTLR Provenance And Generated-File Guard

**Slice 3 is complete.**

### Goal

Prove that parser generation uses the reviewed ANTLR 4.13.2 jar and that a
clean regeneration exactly reproduces every tracked generated parser file.

### Allowed Changes

Slice 3 adds:

- `tools/antlr-4.13.2-complete.jar.sha256`;
- `scripts/check_generated.py`;
- focused tests and documentation.

Slice 3 must not add or modify Makefile targets unless separately and
explicitly authorized under the Phase 11 Makefile policy.

The checksum file records the currently reviewed SHA-256:

```text
eae2dfa119a64327444672aff63e9ec35a20180dc5b8090b7a6ab85125df4d76
```

The guard verifies the jar before invoking Java, generates into a temporary
directory, creates the generated package marker consistently, compares the
exact tracked file inventory and bytes, and leaves the repository untouched.

The authoritative independent command is:

```bash
uv run python scripts/check_generated.py
```

It is intentionally not part of `scripts/validate.py`; CI orchestration
remains deferred to Slice 5.

### Hard Boundaries

Slice 3 must not edit the grammar or tracked generated files, download a jar,
accept missing or extra generated files, normalize generated content, or
replace byte comparison with timestamps.

### Validation

```bash
uv run python scripts/check_generated.py
uv run pytest tests/test_phase11_generated_guard.py
uv run python scripts/validate.py
git diff --check
```

## Slice 4: Golden Fixture Policy And Audit

**Slice 4 is complete.**

### Goal

Make fixture ownership, comparison semantics, review requirements, and
inventory completeness explicit and mechanically auditable.

### Allowed Changes

Slice 4 adds one golden policy document, a standard-library audit script,
focused tests, and documentation links. It does not add a separate manifest;
the script's explicit classification and fixture-to-input map make the
current inventory auditable without duplicating test case ownership in
another data file.

The policy must preserve:

- byte-exact SQL comparison, including artifact separators and final newline;
- structural JSON comparison after standard-library decoding;
- paired review of Pietto input and expected output;
- explicit human review for every fixture change;
- focused behavioral tests for dynamic paths and failures;
- no snapshot dependency and no automatic update command.

The authoritative independent command is:

```bash
uv run python scripts/check_goldens.py
```

The command checks complete fixture classification, missing and orphan
references, paired Pietto inputs, and standard-library JSON decoding. It reads
SQL fixtures as bytes without normalization. It does not invoke the compiler,
`scripts/validate.py`, or `scripts/check_generated.py`.

### Hard Boundaries

Slice 4 must not rewrite, normalize, regenerate, or expand existing golden
content merely to populate an inventory. It must not make JSON object member
order or insignificant whitespace normative.

### Validation

```bash
uv run python scripts/check_goldens.py
uv run pytest tests/test_phase11_golden_policy.py
uv run python scripts/validate.py
git diff --check
```

## Slice 5: GitHub Actions CI

**Slice 5 is complete.**

### Goal

Run the accepted local release-readiness gates on every supported pull request
and branch update without granting write access or duplicating validation
logic.

### Allowed Changes

Slice 5 adds `.github/workflows/ci.yml`, focused static workflow audits, and
CI documentation. The workflow:

- declare `permissions: contents: read`;
- use Python 3.12 and Python 3.13;
- use Java 21 for the generated-file guard;
- invoke the authoritative local validation and audit commands;
- pin every action to a reviewed full commit SHA;
- avoid secrets, publishing, artifact signing, deployment, and write tokens.

The reviewed action pins are:

- `actions/checkout` v4.3.1 at
  `34e114876b0b11c390a56381ad16ebd13914f8d5`;
- `actions/setup-python` v6.2.0 at
  `a309ff8b426b58ec0e2a45f0f869d46889d02405`;
- `actions/setup-java` v5.2.0 at
  `be666c2fcd27ec809703dec50e508c2fdc7f6654`;
- `astral-sh/setup-uv` v7.6.0 at
  `37802adc94f370d6bfd71619e3f0bf239e1f3b78`.

The workflow installs the locally reviewed uv version `0.11.19`, disables
setup-uv cache persistence, keeps uv's project environment and cache under
the runner temporary directory, and runs:

```bash
uv run python scripts/validate.py
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
```

It triggers for pull requests and pushes to `main`. Checkout credential
persistence is disabled, and Java setup does not create Maven publishing
settings.

Python 3.12 is required because `pyproject.toml` declares it as the package
compatibility floor. Python 3.13 is required as the newer interpreter target.
The matrix does not change `requires-python` or `pyrightconfig.json`.

### Hard Boundaries

Slice 5 must not publish packages, create releases, push commits, update
goldens, regenerate tracked parser files, use mutable action tags, add
dependencies, or introduce platform-specific compiler behavior. Additional
operating systems remain outside the MVP CI matrix unless separately
approved.

### Validation

```bash
uv run pytest tests/test_phase11_ci_workflow.py
uv run python scripts/validate.py
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
git diff --check
```

## Slice 6: Packaging And Installed CLI Smoke

**Slice 6 is complete.**

### Goal

Verify that release artifacts contain the required runtime package, generated
ANTLR modules, metadata, dependency declaration, and console entry point, and
that the installed wheel behaves correctly outside a source checkout.

### Allowed Changes

Slice 6 may add one standard-library packaging smoke script, focused tests,
CI integration, and documentation. It must use temporary build and virtual
environment directories and remove them through normal temporary-directory
lifecycle.

The authoritative independent command is:

```bash
uv run python scripts/package_smoke.py
```

The smoke path must:

- build both sdist and wheel from the current checkout;
- inspect required package metadata and generated module inventory;
- install the wheel into a clean temporary environment;
- run from outside the repository;
- exercise `pietto --version` and `pietto --help`;
- exercise one successful `check`;
- compare installed PostgreSQL text output byte-for-byte with its reviewed
  golden;
- compare installed MySQL JSON v1 output structurally with its reviewed
  golden.

The implemented command builds one sdist and one wheel under a temporary
directory, checks package and generated ANTLR inventory, validates core
metadata, the declared ANTLR runtime dependency, README metadata, and the
`pietto = pietto.cli:main` console entry point, and installs the wheel into a
clean temporary `venv`. It removes `PYTHONPATH` and `PYTHONHOME` from the
installed-process environment and invokes the installed console script from a
temporary cwd outside the repository.

The existing CI workflow invokes this command after validation, generated-file
verification, and golden audit. The package smoke remains independent from
`scripts/validate.py`, `scripts/check_generated.py`, and
`scripts/check_goldens.py`.

### Hard Boundaries

Slice 6 must not publish artifacts, change package version, alter build
metadata, add dependencies, execute SQL, connect to a database, or treat a
source-tree import as an installed-package test.

The implementation does not publish, upload, sign, or change package metadata,
version, dependencies, credentials, or workflow permissions. It writes build,
environment, and scratch files only under `tempfile.TemporaryDirectory`.

### Validation

```bash
uv run python scripts/package_smoke.py
uv run pytest tests/test_phase11_packaging_smoke.py
uv run python scripts/validate.py
git diff --check
```

## Slice 7: Completion Audit And Documentation

**Slice 7 is complete.**

### Goal

Prove that the seven slices form one reproducible release-readiness contract
and that no compiler or runtime capability changed accidentally.

### Allowed Changes

Slice 7 may add a focused completion audit and update Phase 11 status
documentation. It may correct defects found in Phase 11 workflow
infrastructure, but it must not use the audit as authorization for unrelated
refactoring.

The completion audit must verify:

- the authoritative local validation command;
- ANTLR checksum and exact regeneration;
- golden policy and inventory;
- minimal-permission Python 3.12/3.13 CI;
- sdist, wheel, clean installation, and installed CLI smoke behavior;
- unchanged PostgreSQL and MySQL reviewed output;
- unchanged JSON v1, CLI, public API, dependency, grammar, generated, and
  compiler-stage boundaries;
- absence of every deferred runtime and project capability.

The implemented `tests/test_phase11_completion_audit.py` locks the four
independent workflow scripts and CI workflow to their reviewed committed
bytes. It also locks package metadata, lockfile, Makefile, grammar, generated
ANTLR files, compiler groups, PostgreSQL and MySQL reviewed goldens, JSON v1,
and the public SQL API. Static negative checks confirm that deferred SQL,
runtime, database, project, editor, Web, publication, and credential
capabilities remain absent.

### Hard Boundaries

Slice 7 must not add release publication, credentials, signing, version
automation, SQL features, execution, database access, project mode, editor
features, or Web capabilities.

### Validation

```bash
uv run python scripts/validate.py
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
uv run pytest tests/test_phase11_completion_audit.py
uv lock --check
git diff --check
```

## Compatibility Gates

### Python

- `pyproject.toml` remains authoritative: `requires-python = ">=3.12"`.
- Python 3.12 is the compatibility floor and must remain tested.
- Python 3.13 is added as a CI interpreter target in Slice 5.
- Raising the floor or dropping Python 3.12 requires a separate compatibility
  decision outside Phase 11.

### PostgreSQL

All existing PostgreSQL SQL fixtures remain byte-exact. The public
`emit_postgres_sql` signature, exports, diagnostics, formatting, artifact
ordering, identifiers, literals, and expressions remain unchanged.

### MySQL

All existing MySQL SQL fixtures remain byte-exact. The dedicated emitter
remains private to `pietto.sql.mysql`, and explicit CLI dispatch remains the
only supported access path outside that internal module.

### CLI And JSON

Phase 11 adds no command or option. JSON schema version 1 remains the only
runtime machine-readable contract, and output-file safety and stdout/stderr
separation remain unchanged.

### Dependencies And Generated Code

Phase 11 adds no project dependency. `pyproject.toml` and `uv.lock` remain
unchanged. Generated ANTLR files are verified but not edited unless a separate
future grammar phase explicitly authorizes regeneration.

## Explicit Non-Goals

Phase 11 does not implement:

- `ORDER BY`, `LIMIT`, or any other SQL feature expansion;
- joins, grouping, aggregates, windows, unions, CTEs, or subqueries;
- DDL, DML, migrations, optimizer behavior, or SQLGlot;
- SQL execution, database connection, schema introspection, or connector
  runtime;
- a generic public `emit_sql(...)` or public `emit_mysql_sql` export;
- JSON v2, project or multi-file mode, or `pietto.toml`;
- watch mode, LSP/editor integration, Web UI, online playground, or server;
- package publication, registry credentials, release signing, or automatic
  versioning;
- automatic golden or generated-file updates.

Phase 11 completion does not start another phase. Phase 12 / SQL Feature
Expansion I may be considered as future planning, but it is not authorized by
this audit.
