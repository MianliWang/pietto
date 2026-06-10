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

## Common Vulnerability Category Checklist

In this table, `confirmed` means the category contained a confirmed audit
finding or control that was directly verified; the evidence states whether
the finding is now mitigated. `Suspected` is reserved for a concrete
robustness concern without a malicious `.pie` reproduction.

| Category | Status | Evidence | Existing coverage | Gap / next action | Blocks Phase 6? |
| -------- | ------ | -------- | ----------------- | ----------------- | --------------- |
| Injection vulnerabilities | future risk | `src/pietto/sql/render.py` always quotes identifiers, doubles embedded quotes, uses explicit PostgreSQL `E'...'` strings for backslashes, and rejects NUL. `src/pietto/sql/postgres.py` converts invalid relation rendering to `PIE-B1000`. `src/pietto/cli.py` escapes terminal-facing diagnostic text. SQL is emitted but never executed, so traditional SQL injection is not currently exploitable. JSON output does not exist. | `tests/test_sql_postgres_rendering.py`, `tests/test_sql_postgres_relations.py`, and `tests/test_sql_postgres_relations_integration.py` cover quote, backslash, comment/semicolon-style payloads, NUL, and backend diagnostics. CLI control-text coverage is listed separately below. | Define JSON escaping and structured-output tests in Phase 6. Create a separate SQL execution threat model before any database runtime; do not treat emitted SQL text as a parameterization boundary. | No; JSON safety is required within any Phase 6 JSON slice. |
| File path and filesystem vulnerabilities | confirmed | PSEC-005 was confirmed and is mitigated in `src/pietto/cli.py`: normalized/same-file and hard-link checks reject input overwrite, output symlinks are rejected, and a same-directory `NamedTemporaryFile` is closed before `os.replace()`. Compiler/backend errors do not write output. Missing parents return exit code `2`. User-selected input/output paths are an explicit local CLI capability, not a traversal across a server sandbox. A POSIX check observed new output mode `0600`. | `tests/test_cli_output.py` and `tests/test_cli_output_security.py` cover same file, hard link, symlink, replacement failure, old-file preservation, missing parent, successful overwrite, and temporary cleanup. | A portable permission assertion and adversarial concurrent directory-mutation test are optional. Final-component symlink races do not cause target writes because `os.replace()` replaces the directory entry rather than following it. | No. |
| Resource exhaustion / denial of service | future risk | `src/pietto/ast_builder.py` limits numeric literals to 4096 characters. `parse_source()` and `analyze()` contain `RecursionError`. Semantic relation, alias, and field-derive cycles produce diagnostics. No whole-file byte, token-count, expression-node, CPU, or memory budget exists. No additional confirmed malicious-source crash was found in this pass. | Numeric boundary and deep unary, binary, and alias-chain tests exist in `tests/test_diagnostics.py`, `tests/test_semantic_expressions.py`, `tests/test_semantic_type_aliases.py`, `tests/test_cli_check.py`, and `tests/test_cli_emit_sql.py`. Cycle suites cover alias, relation, and field-derive cycles. | Decide source-size and structural budgets, then add focused boundary tests. This is recommended before accepting untrusted batch/service workloads; avoid broad fuzzing in this documentation-only pass. | No for the current local CLI. |
| Exception leakage and traceback exposure | suspected | Numeric conversion and recursion failures are diagnosed; PostgreSQL relation emission catches renderer `TypeError`/`ValueError`; CLI file/write failures return `2`; malicious cases have no traceback. Six semantic `assert` statements and two explicit semantic `AssertionError` paths remain. A manually constructed `Script` containing an unsupported `Node` was verified to raise `AssertionError`, but parser-produced ASTs respect the closed definition/expression unions and no `.pie` reproduction was found. Backend exception reasons shown in diagnostics currently originate from controlled renderer messages. | CLI tests assert absence of `Traceback`, `ValueError`, and `RecursionError` for known malicious inputs. Backend tests verify `PIE-B1000` conversion. | Document or test the public AST precondition, or convert malformed manually constructed ASTs to diagnostics in a separate semantic robustness slice. Consider a `python -O` test before relying on assertions as invariants. | No, provided Phase 6 consumes the normal parser pipeline. |
| Unsafe command execution | not currently applicable | Runtime source contains no `subprocess`, `os.system`, `shell=True`, `eval`, `exec`, dynamic plugin loading, or source-triggered imports. `Makefile` invokes Java only for an explicit developer parser-generation command using the local ANTLR jar. | Completion-audit tests assert the absence of runtime/compiler wrapper features; repository search provides the command-execution check. | Reassess before adding plugins, hooks, user-defined execution, or connector runtimes. | No. |
| Network / SSRF / remote access | not currently applicable | Runtime source contains no HTTP client, socket, database driver, connection call, connector execution, or schema introspection. Download commands occur only in setup documentation. | CLI and SQL completion audits assert absence of database/runtime integrations. | A network allowlist, URL validation, timeout, redirect, and SSRF threat model is required before any remote connector or schema service. | No. |
| Deserialization / config loading risks | future risk | No `pietto.toml` or project configuration loader exists. Runtime source does not load YAML, pickle, TOML, or executable configuration. The only `tomllib` use is a test reading the repository's own `pyproject.toml`. | CLI completion tests assert that project configuration and multi-file behavior are absent. | Use non-executable formats and strict schemas if project configuration is introduced; reject unknown or dangerous path/network fields by default. | No. |
| Secrets and credentials | false positive | No tracked `.env`, private-key, database URL, cloud key, or token fixture was found. `.gitignore` covers `.env` and `.env.*`. A local read-only common-secret-pattern scan was clean. `detect-secrets` could not run because the execution policy denied third-party workspace-wide scanning, so this is not a proof of absence. | Ignore rules are present; no automated secret-scanner test or CI gate exists. | Run `detect-secrets` or an equivalent scanner in a trusted CI/developer environment and review any findings manually. | No. |
| Dependency and supply-chain risks | confirmed | PSEC-007 was confirmed and mitigated: `pydantic`, `rich`, `sqlglot`, and `typer` remain absent from imports, `pyproject.toml`, and `uv.lock`; production depends only on `antlr4-python3-runtime`. `uv lock --check` passes and `uv audit --locked` reports no known vulnerabilities or adverse statuses. Generated ANTLR Python files and `tools/antlr-4.13.2-complete.jar` are tracked; the observed jar SHA-256 is `eae2dfa119a64327444672aff63e9ec35a20180dc5b8090b7a6ab85125df4d76`, but generation does not automatically verify it. Bandit's six `B101 assert_used` reports are informational robustness findings: the assert statements are real, but no source-level vulnerability was demonstrated. | Full tests pass without the removed dependencies. Completion audits assert backend/CLI isolation. The lockfile is deterministic; Bandit found no medium/high issues. | Record and verify the ANTLR jar checksum before the next grammar regeneration or release. Consider scheduled `uv audit --locked`; review Bandit assertions in a semantic robustness slice. | No, unless Phase 6 requires parser regeneration before checksum verification. |
| Logging / terminal output safety | confirmed | PSEC-006 was confirmed and mitigated in `src/pietto/cli.py`: `_escape_cli_text()` escapes every C0 control and DEL, including newline, carriage return, tab, ESC, and NUL. Diagnostic paths use the escaped fallback path and stdout/stderr routing remains stable. SQL artifacts are intentionally emitted unchanged because escaping them would corrupt SQL; consumers should treat SQL stdout as an artifact channel rather than a log record. | `tests/test_cli_output_security.py` covers newline/ESC paths, missing-file errors, diagnostic message controls, and success output. `tests/test_cli_diagnostics.py`, `tests/test_cli_output.py`, and `tests/test_cli_emit_sql.py` cover record formatting and stream separation. | When JSON is added, prevent mixed human and machine records on the same stream. Raw SQL artifact control characters remain an intentional data-output property, not diagnostic rendering. | No. |
| Authorization / authentication / session risks | not currently applicable | Pietto has no users, accounts, authentication, authorization, cookies, sessions, tenants, or privileged service boundary. | Architecture and completion audits confirm a local single-process compiler/CLI only. | Create an authorization model only if a multi-user service is proposed. | No. |
| Web vulnerabilities | not currently applicable | There is no Web UI, HTTP server, upload endpoint, browser client, or API route. XSS, CSRF, CORS, auth bypass, upload vulnerabilities, and server-side SSRF therefore have no current surface. | Repository structure and feature-absence audits cover this boundary. | Perform a separate Web threat model before adding any server or browser surface. | No. |
| Runtime/database execution risks | not currently applicable | Pietto cannot execute emitted SQL, connect to PostgreSQL, run connectors, introspect schemas, apply migrations, or mutate databases. `emit_postgres_sql()` consumes `ScriptIR` and returns text artifacts only. | SQL and CLI completion audits forbid connection/execution APIs and verify frontend/backend stage isolation. | Before runtime work, define parameterization, credentials, least privilege, transaction boundaries, timeouts, cancellation, migration safety, connector sandboxing, and audit logging. | No; a separate threat model is mandatory before such features. |
| Serialization / machine-readable output risks | future risk | JSON output and structured CLI serialization are absent. Current diagnostics are immutable structured Python data rendered as escaped human text, with SQL artifacts separately routed. There is no schema version, JSON encoder, or machine-output stream contract yet. | Existing tests cover human diagnostics, SQL stdout, stderr separation, and exit codes only. | Phase 6 JSON work must use a real JSON encoder, version its schema, serialize diagnostics structurally, prohibit traceback fields, and keep machine stdout free of human text. | No to starting Phase 6; required before a JSON interface is complete. |
| Test coverage gaps | confirmed | Current tests cover all PSEC-001 through PSEC-007 regressions and the complete 902-test compiler suite, but no whole-source resource budget, malformed hand-built AST containment, optimized-mode invariant run, ANTLR jar checksum check, trusted secret scan, or JSON contract exists. | Security regressions are distributed across parser, semantic, SQL, CLI, completion-audit, and output-security suites. | Apply the priorities below. | No current gap blocks starting Phase 6. |

### Remaining Test Gaps

Must fix before Phase 6:

- None for starting Phase 6 on the current local compiler and CLI baseline.

Required as part of Phase 6 before machine-readable output is complete:

- JSON escaping tests for controls, quotes, Unicode, and malicious diagnostic
  text using a standard JSON encoder.
- A versioned output schema with structured diagnostics and no traceback or
  mixed human text on machine stdout.
- Exit-code and stdout/stderr contract tests for successful and failed JSON
  operations.

Recommended before or early in Phase 6:

- Define source byte/token/node/depth budgets and add focused boundary tests.
- Add a test or documented precondition for malformed hand-built AST input to
  public semantic APIs; include an optimized `python -O` invariant run if
  assertions remain.
- Verify the committed ANTLR jar against a documented checksum before parser
  regeneration.
- Run a trusted `detect-secrets` scan and consider a lightweight CI audit.
- Add a portable output-permission test where platform semantics are stable.

Can defer until the relevant surface exists:

- SQL parameterization, credentials, privilege, transactions, cancellation,
  connector sandboxing, and database mutation tests.
- Network timeout, redirect, URL allowlist, and SSRF tests.
- Authentication, authorization, session, tenant-isolation, Web, XSS, CSRF,
  CORS, and upload tests.
- Project-config deserialization, multi-file path-boundary, LSP, plugin, and
  remote-service tests.

No reviewed category blocks starting Phase 6. Any database/runtime, network,
connector, Web, plugin, or multi-user feature requires a new threat model
before implementation rather than inheriting this local-compiler assessment.

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
