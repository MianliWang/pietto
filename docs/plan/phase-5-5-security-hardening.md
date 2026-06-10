# Phase 5.5: Security Hardening

## Status

**Phase 5.5 security hardening: Complete for PSEC-001 through PSEC-007.**

This follow-up hardens source-level failure handling, PostgreSQL rendering,
CLI file output, terminal-facing text, and the production dependency surface.
It does not add runtime or execution behavior.

## Completed Findings

- PSEC-001: excessively long numeric literals produce parser diagnostics
  instead of uncaught Python conversion exceptions.
- PSEC-002: parser and semantic recursion exhaustion is contained at the
  public API boundaries and produces structured diagnostics. Full depth
  budgets and iterative algorithm rewrites remain deferred.
- PSEC-003: PostgreSQL strings containing backslashes use explicit `E'...'`
  constants with escaped backslashes and quotes.
- PSEC-004: NUL in PostgreSQL identifiers or string literals is rejected;
  public relation emission returns `PIE-B1000`.
- PSEC-005: CLI output rejects the input file, hard links to it, and symbolic
  links. Successful writes use a same-directory temporary file followed by
  `os.replace()`.
- PSEC-006: CLI paths, errors, and diagnostics escape C0 controls and DEL
  before writing plain-text terminal or CI output.
- PSEC-007: unused direct production dependencies were removed after a
  repository-wide usage check.

## Dependency Audit

The only production dependency required by the implemented compiler is
`antlr4-python3-runtime`.

The following former direct dependencies had no imports in `src`, tests, or
repository scripts and were removed:

| Dependency | Audit result |
|---|---|
| `pydantic` | Unused; Pietto models use standard-library dataclasses |
| `rich` | Unused; CLI output uses plain standard-library streams |
| `sqlglot` | Not integrated; references describe a possible future backend direction or assert current isolation |
| `typer` | Unused; the implemented CLI uses `argparse` |

Removing these dependencies also removed their now-unreachable transitive
packages from `uv.lock`. Future work should add a dependency only when an
implemented slice imports and validates it.

## Security Tooling

Run the locked dependency audit with:

```bash
uv audit --locked
```

The Phase 5.5 audit found no known vulnerabilities and no adverse package
statuses before dependency cleanup. After cleanup, the repeated audit found no
known vulnerabilities or adverse statuses in the 18 locked third-party
packages. The command should be rerun after dependency or lockfile changes.

Bandit can be run as a one-off tool without adding a project dependency:

```bash
uvx bandit -r src/pietto -x src/pietto/generated
```

The Phase 5.5 run reported six low-severity `B101 assert_used` findings in
semantic internal-invariant checks and no medium- or high-severity findings.
They were not changed in this dependency-focused slice because doing so would
alter semantic implementation behavior. They remain candidates for a
separate, focused robustness review.

The recommended secrets scan is:

```bash
uvx detect-secrets scan --all-files
```

That third-party scan could not be executed in the Phase 5.5 environment
because workspace-wide third-party scanning was denied by the execution
policy. A local read-only scan found no tracked environment/private-key files
and no common private-key, cloud-key, GitHub-token, Slack-token, or Google API
key patterns. `.env` and `.env.*` are ignored to reduce accidental commits.

Generated scan output and tool-specific baselines are not committed. These
commands are a lightweight manual baseline rather than mandatory CI gates.

## Non-Goals

Phase 5.5 does not add:

- SQL execution;
- database connections;
- connector execution;
- schema introspection;
- runtime behavior;
- a Web UI;
- project or multi-file support;
- JSON output;
- LSP/editor integration;
- `compile_to_ir()` or `compile_to_sql()`.
