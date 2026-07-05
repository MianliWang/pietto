# Pietto Code Audit And Security Review v1

## Status And Guardrail

Maintenance Phase 2 Slice 3 is Code Audit And Security Review Checklist.
Slice 3 is docs/spec/static-audit work only and implements no behavior change.

This document records a Pietto-specific audit checklist inspired by text-only
review practices from the prior external skills audit, especially Trail of
Bits-style security review discipline. It does not install external plugins,
run external scripts, copy external code, import hooks, import MCP configs,
run scanners, change production source, change scripts, change workflows,
change dependencies, change package metadata, change release behavior, or
modify `AGENTS.md`.

Package version remains `0.1.0`.

## Review Posture

Pietto code audit and security review should be evidence-first. A reviewer
must identify the exact claim, affected surface, trust boundary, source path,
validation points, sink, and expected impact before reporting a security issue.

The lightweight review flow is:

1. restate the exact claim and execution context;
2. identify whether the input is trusted, project-controlled, user-controlled,
   filesystem-controlled, environment-controlled, or external-tool-controlled;
3. trace source-to-sink data flow through parsing, validation, normalization,
   semantic analysis, IR construction, SQL lowering, or output serialization;
4. record existing validation, containment, fail-closed behavior, and output
   separation;
5. classify the result as confirmed issue, false positive, robustness issue,
   or deferred design risk;
6. report only claims supported by concrete evidence.

Unsupported, unsafe, ambiguous, contradictory, or unproven compiler semantics
must fail closed. Fail closed means deterministic diagnostics or handled
project errors and no approximate SQL. It is not a runtime security control.

## Pietto Audit Surface Matrix

| Surface | Review questions |
| --- | --- |
| Path traversal / root containment | Are project roots explicit, canonicalized for containment, and checked by component relationship rather than string prefix? Are symlinks, hard links, aliases, `..`, absolute paths, Windows drive paths, UNC paths, backslashes, repeated separators, NUL, and Unicode/case duplicate identities handled according to the path contract? |
| Source selection / glob policy | Are include patterns validated before expansion, excludes applied after includes, unsupported glob forms rejected rather than ignored, hidden directory rules preserved, final selected files sorted deterministically, and source selection bounded before source reads? |
| TOML config parsing | Are `schema_version`, `[sources]`, `include`, and `exclude` validated by type and known-key policy? Are unknown keys, duplicate TOML keys/tables, shell expansion, tilde expansion, environment expansion, and executable configuration rejected or kept inert? |
| UTF-8 / source-read boundaries | Are source-read and UTF-8 failures handled as project errors at the read boundary, before parser aggregation, semantic analysis, IR, SQL, metadata, or runtime behavior? |
| Parser diagnostics and location paths | Are parser diagnostics attributed to normalized project-relative paths without leaking canonical absolute roots or fabricating unrelated locations? Are diagnostic order and related-location behavior deterministic? |
| Project JSON v2 schema stability | Does project check preserve `schema_version: 2`, Project JSON v2 fields, `inputs[]`, `diagnostics[]`, `cli_errors[]`, and `result.check` counters without adding SQL, metadata, graph, runtime, database, or release data? |
| CLI JSON v1 separation | Do single-file `check` and `emit-sql` remain in CLI JSON v1 without accidental Project JSON v2 fields or project-only `cli_errors`? |
| Semantic Metadata Artifact v1 separation | Does single-file `explain` remain Semantic Metadata Artifact v1 without Project JSON v2 or project-check payloads? |
| Semantic / IR / SQL boundaries | Does semantic acceptance require representable IR and faithful selected-dialect SQL lowering? Do unsupported IR or backend cases fail closed before emitting approximate SQL? |
| Generated / golden / fixture changes | Are generated artifacts, SQL golden bytes, fixtures, and examples changed only when explicitly authorized by the current gate? |
| Dependency / workflow / lockfile / package metadata changes | Are `pyproject.toml`, `uv.lock`, `.github/**`, pinned actions, dependency groups, and package metadata unchanged unless explicitly approved? |
| Release / tag / publish / signing / attestation boundaries | Are package version changes, tags, releases, publishing, uploads, signing, and attestations absent unless the gate explicitly authorizes them? |
| External plugin / script prohibition | Are external skills, plugins, scripts, hooks, MCP configs, package managers, installers, and scanners not installed or executed by default? |

## Finding Discipline

A finding should use one of these review outcomes:

- confirmed issue: the claim has evidence for reachability, affected data,
  missing or insufficient validation, and user-visible impact;
- false positive: evidence shows the claim is unreachable, already validated,
  outside the threat model, or blocked by current fail-closed behavior;
- robustness issue: the behavior may be undesirable but does not support a
  security claim;
- deferred design risk: the risk belongs to a future feature or policy surface
  and needs a later readiness slice before implementation.

Security reports must not rely on pattern matching alone. A dangerous-looking
operation is not a confirmed issue until source-to-sink tracing shows that
untrusted or attacker-controlled data reaches the operation without the
required Pietto validation or fail-closed boundary.

False-positive handling should document the reason for rejection rather than
silently deleting the concern. Common rejection reasons include missing
attacker control, unreachable path, existing validation, output-domain
separation, fail-closed diagnostics, or future-only design status.

## Evidence Template

Use a compact local evidence form:

```text
Claim:
Surface:
Entry/source:
Trust boundary:
Validation points:
Sink/output:
Impact:
Verdict: confirmed issue | false positive | robustness issue | deferred design risk
Evidence:
```

Evidence should cite local file paths, line numbers when available, commands
run, relevant diagnostics, and exact output shapes. Do not report a security
claim when the evidence is only an intuition or a resemblance to an external
pattern.

## Gate Workflow

Pietto security review must preserve the existing Gate workflow:

- Gate 1 is read-only planning, scope, and evidence gathering;
- Gate 2 is bounded implementation or docs/static-audit work over the exact
  approved allowlist;
- Gate 3 is stage, commit, push, and natural CI observation only when
  separately approved.

Reviewers must enforce exact allowlists, forbidden surfaces, validation plans,
stop conditions, and release posture. If a review requires production code,
scripts, dependencies, workflows, package metadata, release operations,
external plugin installation, external script execution, manual CI action, or
`AGENTS.md` changes outside the approved allowlist, stop and return to Gate 1.

## Relationship To External Audit Practices

Trail of Bits-style review practices are useful as text-only process:

- trace concrete data flow;
- require evidence before reporting;
- separate reachability, exploitability, impact, and environment assumptions;
- explicitly classify false positives;
- use adversarial review questions to avoid both false positives and missed
  issues.

Compound Engineering-style security review personas are useful as text-only
prompting context for diff review. `obra/superpowers` planning and review
habits are useful only as local process ideas. None of these sources are
trusted automation for Pietto by default.

External code, scripts, hooks, MCP configs, package manifests, scanner rules,
and plugin bundles must not be imported, installed, or executed without a
separate explicit approval.

## Release Posture

Maintenance Phase 2 Slice 3 performs no release operation. It authorizes no
package version change, tag, release, publish, upload, signing, or attestation.
