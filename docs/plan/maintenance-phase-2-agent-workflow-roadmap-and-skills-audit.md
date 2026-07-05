# Maintenance Phase 2 Agent Workflow Roadmap And Skills Audit

## Status And Trusted Handoff

Maintenance Phase 2 Slice 2 is Agent Workflow Policy And Roadmap Lock. Slice 2
is docs/spec/plan/static-audit work only and implements no source/compiler
behavior change.

Maintenance Phase 2 Slice 3 is Code Audit And Security Review Checklist. Slice
3 is docs/spec/plan/static-audit work only and implements no source/compiler
behavior change.

Maintenance Phase 2 Slice 4 is AGENTS.md Adoption Pointer. Slice 4 is
docs/plan/static-audit plus one tiny `AGENTS.md` local-policy pointer only. It
implements no source/compiler behavior change.

Maintenance Phase 2 Slice 5 is External Skills Detailed Evaluation Matrix.
Slice 5 is docs/spec/plan/static-audit work only and implements no
source/compiler behavior change.

Trusted Gate 2 baseline:

- baseline HEAD: `e567ee0be3e8bbdb52570efa9c098589c9400b89`;
- baseline branch: `main`;
- baseline subject: `Complete Phase 44 project check MVP audit`;
- latest completed language phase: Phase 44 Project Source Selection And
  Parse-only Project Check MVP;
- package version remains `0.1.0`;
- no tag/release/publish/upload/signing/attestation is authorized by Slice 2.

Maintenance Phase 2 follows Maintenance Phase 1 as a policy and roadmap audit.
It does not reopen dependency maintenance, workflow pinning, package metadata,
CI hardening, or release operations from Maintenance Phase 1.

## Accepted External Audit Conclusions

Maintenance Phase 2 Slice 2 locks these accepted conclusions:

- do not install external skills/plugins by default;
- do not execute external repo scripts;
- borrow text-only workflow practices from `obra/superpowers`,
  `EveryInc/compound-engineering-plugin`, `trailofbits/skills`,
  `trailofbits/skills-curated`, and `trailofbits/claude-code-config`;
- create Pietto-specific workflow/checklist docs instead of importing external
  frameworks;
- keep `AGENTS.md` unchanged until a separate approval after docs/spec policy
  is locked;
- make Phase 45 target true project-wide semantic model design and MVP;
- treat true project-wide semantic model as mandatory, not optional;
- do not reduce Phase 45 to per-file semantic aggregation only.

## Slice 2 Deliverables

Phase 2 Slice 2 creates exactly these default Gate 2 artifacts:

- `docs/spec/pietto-roadmap-phase45-60-v1.md`;
- `docs/spec/agent-workflow-and-skills-adoption-v1.md`;
- `docs/plan/maintenance-phase-2-agent-workflow-roadmap-and-skills-audit.md`;
- `tests/test_maintenance_phase2_agent_workflow_and_roadmap.py`.

No other file is approved in this Gate 2.

## Slice 3 Deliverables

Maintenance Phase 2 Slice 3 creates and locks the local Pietto code audit and
security review checklist. Gate 2 is limited to:

- `docs/spec/pietto-code-audit-and-security-review-v1.md`;
- `docs/spec/agent-workflow-and-skills-adoption-v1.md`;
- `docs/plan/maintenance-phase-2-agent-workflow-roadmap-and-skills-audit.md`;
- `tests/test_maintenance_phase2_code_audit_security_review.py`;
- `tests/test_maintenance_phase2_agent_workflow_and_roadmap.py`.

No other file is approved in this Gate 2.

Slice 3 translates Trail of Bits-style audit practices into Pietto-owned
text-only process. It does not install external plugins, execute external repo
scripts, copy external code, import hooks, import MCP configs, run scanners,
change compiler behavior, or modify `AGENTS.md`.

The Slice 3 checklist must cover:

- path traversal and root containment;
- source selection and glob policy;
- TOML config parsing;
- UTF-8 and source-read boundaries;
- parser diagnostics and project-relative paths;
- Project JSON v2 schema stability;
- CLI JSON v1 separation;
- Semantic Metadata Artifact v1 separation;
- semantic, IR, and SQL fail-closed boundaries;
- generated, golden, and fixture boundaries;
- dependency, workflow, lockfile, and package metadata boundaries;
- release, tag, publish, upload, signing, and attestation boundaries;
- external plugin and script prohibition;
- false-positive handling discipline;
- evidence-first review;
- exact allowlist enforcement;
- Gate 1 / Gate 2 / Gate 3 discipline.

## Slice 4 Deliverables

Maintenance Phase 2 Slice 4 adopts the already-locked local policies into
`AGENTS.md` through a narrow pointer only. Gate 2 is limited to:

- `AGENTS.md`;
- `docs/plan/maintenance-phase-2-agent-workflow-roadmap-and-skills-audit.md`;
- `tests/test_maintenance_phase2_agent_workflow_and_roadmap.py`;
- `tests/test_maintenance_phase2_code_audit_security_review.py`.

No other file is approved in this Gate 2.

The `AGENTS.md` pointer must reference only local Pietto policy documents:

- `docs/spec/agent-workflow-and-skills-adoption-v1.md`;
- `docs/spec/pietto-code-audit-and-security-review-v1.md`;
- `docs/spec/pietto-roadmap-phase45-60-v1.md`.

Slice 4 does not copy external framework instructions into `AGENTS.md`, mention
external installation commands, add external script/hook/MCP setup
instructions, broaden agent authority, install plugins, execute external repo
scripts, copy external code, trigger CI, stage, commit, push, tag, release,
publish, upload, sign, or attest anything.

## Slice 5 Deliverables

Maintenance Phase 2 Slice 5 records a detailed Pietto-owned external skills
evaluation matrix. Gate 2 is limited to:

- `docs/spec/external-skills-evaluation-matrix-v1.md`;
- `docs/plan/maintenance-phase-2-agent-workflow-roadmap-and-skills-audit.md`;
- `tests/test_maintenance_phase2_external_skills_evaluation.py`;
- `tests/test_maintenance_phase2_agent_workflow_and_roadmap.py`;
- `tests/test_maintenance_phase2_code_audit_security_review.py`.

No other file is approved in this Gate 2.

Slice 5 records the inspected external repo snapshots, skill counts, direct
adoption risks, safe text-only process practices, forbidden adoption surfaces,
and recommended local adoption strategy. It does not install external plugins,
execute external repo scripts, run external scanners, copy external code,
import hooks, import MCP configs, change compiler behavior, change `AGENTS.md`,
trigger CI, stage, commit, push, tag, release, publish, upload, sign, or attest
anything.

The Slice 5 matrix must cover:

- `obra/superpowers` at snapshot `d884ae0`;
- `EveryInc/compound-engineering-plugin` at snapshot `d3f3529`;
- `trailofbits/skills` at snapshot `cfe5d7b`;
- `trailofbits/skills-curated` at snapshot `022fa09`;
- `trailofbits/claude-code-config` at snapshot `7db11a2`;
- observed skill counts and adoption surfaces;
- direct adoption risk ratings;
- safe text-only practices worth borrowing;
- forbidden elements not to adopt;
- Trail of Bits-style code-audit practices worth translating locally;
- the recommendation that Maintenance Phase 2 likely needs one completion
  audit/status-lock slice before Phase 45.

## Roadmap And Namespace Decisions

Slice 2 locks Phase 45 as `Project-wide Semantic Model Design And MVP`.

The Phase 45 target is a true project-wide semantic model. It is mandatory,
not optional, and must not be reduced to per-file semantic aggregation only.

Pietto's project-wide namespace preference is hybrid:

- type namespace includes `shape`, future type aliases, and future domain
  types;
- relation namespace includes `source`, `table`, and `query`.

Cross-file references should allow any selected project top-level symbol,
subject to namespace and reference-site rules.

The file/module model is not final. Phase 45 may use an implicit project
package model as an MVP stepping stone. Python-like import/export is a
required long-term target, but imports/modules/export require readiness before
behavior implementation.

The long-term same-name `source`/`table`/`query` preference is non-strict
warning and strict-mode error. Unqualified ambiguous references must fail
closed. Current fail-closed behavior may remain until warning/strict-mode
infrastructure is explicitly approved.

Phase size may reach up to 12 slices per phase when needed.

## Borrowing Policy

Malloy and Cube may be studied for concepts but must not be copied as
frameworks or behavior contracts. Python, Go, Rust, and C++ namespace
precedents may be compared as design context but must not be adopted
wholesale.

Trail of Bits-style code audit practices are valuable when translated into
local text-only process. External code, scripts, hooks, MCP configs, plugins,
and command bundles are not trusted by default.

Slice 5 keeps this borrowing policy explicit: external skills may inform local
Pietto docs, but plugin installation, external scripts, scanners, hooks, MCP
configs, package metadata, workflow files, command bundles, prompt assets, and
copied external code remain prohibited unless separately approved.

## Forbidden Surfaces

Slice 2 and Slice 3 do not authorize changes to:

- `AGENTS.md`;
- `README.md`;
- `docs/spec/pietto-v0.9.md`;
- `src/**`;
- `scripts/**`;
- `.github/**`;
- `pyproject.toml`;
- `uv.lock`;
- `tests/fixtures/**`;
- `tests/goldens/**`;
- generated artifacts;
- external repo files under `/tmp/pietto_maintenance_phase2_external_repos/**`.

Slice 2 and Slice 3 must not install plugins, run external scripts, copy external code,
change dependencies, change workflows, trigger CI, implement Phase 45 behavior,
or modify production compiler/runtime code.

Slice 4 authorizes only the tiny `AGENTS.md` local-policy pointer and the
approved plan/static-audit updates listed in Slice 4 Deliverables. Slice 4 does
not authorize changes to `README.md`, `docs/spec/pietto-v0.9.md`, `src/**`,
`scripts/**`, `.github/**`, `pyproject.toml`, `uv.lock`,
`tests/fixtures/**`, `tests/goldens/**`, generated artifacts, grammar,
external repo files, dependencies, workflows, package metadata, CI, release,
tag, publish, upload, signing, or attestation surfaces.

Slice 5 authorizes only the approved docs/spec/plan/static-audit updates listed
in Slice 5 Deliverables. Slice 5 does not authorize changes to `AGENTS.md`,
`README.md`, `docs/spec/pietto-v0.9.md`, `src/**`, `scripts/**`, `.github/**`,
`pyproject.toml`, `uv.lock`, `tests/fixtures/**`, `tests/goldens/**`,
generated artifacts, grammar, external repo files, dependencies, workflows,
package metadata, CI, release, tag, publish, upload, signing, or attestation
surfaces.

## Gate 2 Validation Plan

Slice 2 Gate 2 validation is limited to focused docs/static-audit checks:

```bash
git diff --check
uv run ruff format --check tests/test_maintenance_phase2_agent_workflow_and_roadmap.py
uv run ruff check tests/test_maintenance_phase2_agent_workflow_and_roadmap.py
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_maintenance_phase2_agent_workflow_and_roadmap.py
```

If local uv cache is read-only, Gate 2 may use:

```bash
UV_CACHE_DIR=/tmp/pietto_maintenance_phase2_uv_cache uv run ...
```

No broad validation, full test suite, codegen, formatter rewrite, external
script execution, commit, push, branch, tag, release, publish, upload, signing,
attestation, or CI action is authorized by Slice 2.

Slice 3 Gate 2 validation is limited to focused docs/static-audit checks:

```bash
git diff --check
uv run ruff format --check tests/test_maintenance_phase2_code_audit_security_review.py tests/test_maintenance_phase2_agent_workflow_and_roadmap.py
uv run ruff check tests/test_maintenance_phase2_code_audit_security_review.py tests/test_maintenance_phase2_agent_workflow_and_roadmap.py
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_maintenance_phase2_code_audit_security_review.py
uv run pytest tests/test_maintenance_phase2_agent_workflow_and_roadmap.py
```

If local uv cache is read-only, Slice 3 Gate 2 may use:

```bash
UV_CACHE_DIR=/tmp/pietto_maintenance_phase2_uv_cache uv run ...
```

No broad validation, full test suite, codegen, formatter rewrite, external
script execution, commit, push, branch, tag, release, publish, upload, signing,
attestation, or CI action is authorized by Slice 3.

Slice 4 Gate 2 validation is limited to focused AGENTS/docs/static-audit checks:

```bash
git diff --check
uv run ruff format --check tests/test_maintenance_phase2_agent_workflow_and_roadmap.py tests/test_maintenance_phase2_code_audit_security_review.py
uv run ruff check tests/test_maintenance_phase2_agent_workflow_and_roadmap.py tests/test_maintenance_phase2_code_audit_security_review.py
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_maintenance_phase2_agent_workflow_and_roadmap.py
uv run pytest tests/test_maintenance_phase2_code_audit_security_review.py
```

If local uv cache is read-only, Slice 4 Gate 2 may use:

```bash
UV_CACHE_DIR=/tmp/pietto_maintenance_phase2_uv_cache uv run ...
```

No broad validation, full test suite, codegen, formatter rewrite, external
script execution, commit, push, branch, tag, release, publish, upload, signing,
attestation, CI trigger, CI rerun, or CI cancellation is authorized by Slice 4.

Slice 5 Gate 2 validation is limited to focused docs/static-audit checks:

```bash
git diff --check
uv run ruff format --check tests/test_maintenance_phase2_external_skills_evaluation.py tests/test_maintenance_phase2_agent_workflow_and_roadmap.py tests/test_maintenance_phase2_code_audit_security_review.py
uv run ruff check tests/test_maintenance_phase2_external_skills_evaluation.py tests/test_maintenance_phase2_agent_workflow_and_roadmap.py tests/test_maintenance_phase2_code_audit_security_review.py
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_maintenance_phase2_external_skills_evaluation.py
uv run pytest tests/test_maintenance_phase2_agent_workflow_and_roadmap.py
uv run pytest tests/test_maintenance_phase2_code_audit_security_review.py
```

If local uv cache is read-only, Slice 5 Gate 2 may use:

```bash
UV_CACHE_DIR=/tmp/pietto_maintenance_phase2_slice5_uv_cache uv run ...
```

No broad validation, full test suite, codegen, formatter rewrite, external
script execution, external scanner execution, commit, push, branch, tag,
release, publish, upload, signing, attestation, CI trigger, CI rerun, or CI
cancellation is authorized by Slice 5.

## Stop Conditions

Stop and return to Gate 1 if any of these appears necessary:

- any `src/**` change;
- any `AGENTS.md` change beyond the approved local-policy pointer;
- external plugin installation;
- external script execution;
- external scanner execution;
- dependency, workflow, package metadata, or lockfile changes;
- release, tag, publish, upload, signing, or attestation work;
- scope expansion beyond docs/spec/plan/static-audit files;
- copying external framework instructions into `AGENTS.md`;
- mentioning external installation commands;
- adding external script, hook, or MCP setup instructions;
- broadening agent authority;
- need to implement Phase 45 compiler behavior instead of documenting
  roadmap/policy.

## Gate 2 Evidence Requirements

Gate 2 reporting should include:

- baseline proof for branch, HEAD SHA, subject, package version, and tag
  absence;
- changed-file proof with `git diff --name-status`;
- forbidden-surface proof showing only the approved allowlist changed;
- validation command outputs;
- `git diff --check` output;
- static audit test body or clear diff excerpt;
- confirmation that no external plugin was installed and no external repo
  script was executed;
- confirmation that no external scanner was executed and no external code,
  hook, MCP config, package manifest, workflow file, command bundle, or prompt
  asset was copied into Pietto;
- confirmation that `AGENTS.md` changed only as the approved local-policy
  pointer;
- confirmation that production code, dependencies, workflows, package
  metadata, release artifacts, and CI were untouched.

## Release Posture

Maintenance Phase 2 Slice 2 performs no release operation. Package version
remains `0.1.0`. Maintenance Phase 2 Slice 3 also performs no release
operation. Maintenance Phase 2 Slice 4 also performs no release operation.
Maintenance Phase 2 Slice 5 also performs no release operation. No package
version change, tag, release, publish, upload, signing, or attestation is
authorized.
