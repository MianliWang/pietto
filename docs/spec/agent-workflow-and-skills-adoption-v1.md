# Agent Workflow And Skills Adoption v1

## Status And Guardrail

Maintenance Phase 2 Slice 2 locks Pietto's agent workflow and external skills
adoption policy as docs/spec/static-audit work only. It authorizes no
production source change, grammar change, generated artifact change, parser
change, semantic change, IR/SQL change, CLI change, JSON output change,
script change, workflow change, dependency change, package metadata change,
package version change, release, tag, publish, upload, signing, or
attestation.

Package version remains `0.1.0`.

This document does not modify `AGENTS.md`. Any future `AGENTS.md` change
requires a separate approval after this docs/spec policy is locked.

## Default Trust Policy

Pietto must not install external skills or plugins by default.

Pietto must not execute external repository scripts by default.

Pietto must not copy external code, hooks, MCP configs, plugin manifests, CI
configuration, package-manager logic, or dependency metadata into the
repository by default.

External repositories may be inspected as text-only references when a Gate
explicitly permits read-only inspection. Text-only inspection means reading
documentation, checklist language, and workflow descriptions. It does not mean
running commands from those repositories, installing their packages, importing
their plugin bundles, or trusting their automation.

## External Sources Reviewed For Text-only Borrowing

Maintenance Phase 2 may borrow text-only workflow practices from:

- `obra/superpowers`;
- `EveryInc/compound-engineering-plugin`;
- `trailofbits/skills`;
- `trailofbits/skills-curated`;
- `trailofbits/claude-code-config`.

The borrowing boundary is process language only. Pietto-specific workflow docs
and checklists should be written locally instead of importing external
frameworks.

## Useful Process Practices

Pietto may adapt the following practices into local docs when they fit the
existing gated workflow:

- explicit plan-first handoff packets;
- bounded allowlists;
- stop conditions before implementation;
- evidence-first reports;
- static audit checklists;
- test-first thinking where it is scoped and local;
- review checklists for security-sensitive or untrusted-input surfaces;
- deny-by-default posture around destructive actions, secrets, publishing, and
  external automation.

These are practices, not executable dependencies.

## Trail of Bits-style Audit Posture

Trail of Bits-style code audit practices are valuable for Pietto when they are
translated into local, text-only process:

- threat-model the surface before broadening behavior;
- define the trusted boundary before adding automation;
- treat untrusted inputs, hooks, scripts, and generated configs as explicit
  risk surfaces;
- prefer reproducible evidence over broad claims;
- keep security checks opt-in and scoped.

External code, scripts, hooks, MCP configs, plugins, and command bundles from
Trail of Bits repositories are not trusted by default and must not be executed
or imported without a separate approval.

## Agent Workflow For Pietto Gates

Pietto's local workflow remains repo-specific:

- Gate 1 is read-only planning and evidence gathering;
- Gate 2 is bounded implementation and focused validation over an approved
  allowlist;
- Gate 3 is publish work only when separately approved;
- each gate must preserve the current phase objective, allowed files, forbidden
  surfaces, validation plan, stop conditions, and release posture.

Gate 2 work should stop rather than widen scope when implementation appears to
require production code, dependency, workflow, package metadata, `AGENTS.md`,
external plugin, external script, CI, release, or publish changes outside the
approved allowlist.

## AGENTS.md Policy

`AGENTS.md` remains unchanged by default.

The agent workflow policy should first be locked in docs/spec and static-audit
tests. A later optional slice may propose an `AGENTS.md` update only after the
policy is stable, explicitly approved, and bounded by a new allowlist.

## Release Posture

Maintenance Phase 2 Slice 2 performs no release operation. It authorizes no
package version change, tag, release, publish, upload, signing, or
attestation.
