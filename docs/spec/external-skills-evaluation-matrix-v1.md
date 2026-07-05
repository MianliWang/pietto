# External Skills Evaluation Matrix v1

## Status And Guardrail

Maintenance Phase 2 Slice 5 is External Skills Detailed Evaluation Matrix.
Slice 5 is docs/spec/plan/static-audit work only and implements no
source/compiler behavior change.

This document records a Pietto-owned evaluation matrix for already-inspected
external skills and agent-workflow repositories. It does not install external
plugins, execute external repo scripts, copy external code, import hooks,
import MCP configs, run scanners, change production source, change scripts,
change workflows, change dependencies, change package metadata, change release
behavior, or modify `AGENTS.md`.

Package version remains `0.1.0`.

## External Repo Snapshot Inventory

| Repo | Snapshot | Cheap skill count | Observed adoption surfaces |
| --- | ---: | ---: | --- |
| `obra/superpowers` | `d884ae0` | 14 | Multi-platform plugin manifests, install instructions, `scripts/`, `hooks/`, worktree/subagent workflows, PR/branch finishing workflow |
| `EveryInc/compound-engineering-plugin` | `d3f3529` | 35 local `SKILL.md`; README says 28 shipped skills | Multi-platform plugin manifests, `scripts/`, `src/commands`, `.github` workflows, package metadata, autonomous `/lfg`, commit/push/PR/CI flows |
| `trailofbits/skills` | `cfe5d7b` | 75 | Claude/Codex-compatible marketplace, many `.claude-plugin` manifests, `.github`, static-analysis skills, SARIF workflows, some `.mcp.json` files |
| `trailofbits/skills-curated` | `022fa09` | 27 | Curated marketplace, `.claude` commands, scripts, plugin manifests, converted OpenAI skills, GitHub/deploy/security skills |
| `trailofbits/claude-code-config` | `7db11a2` | 0 | Claude settings, hooks, commands, shell scripts, MCP template, package/tool install guidance, autonomous PR/issue/dependabot commands |

All repositories remain external read-only references. The snapshot inventory is
evidence for text-only evaluation, not an approval to fetch, update, install,
execute, import, or copy anything from those repositories.

## Detailed Evaluation Matrix

| Repo | Purpose and platforms | Security/workflow value | Direct adoption risk | Text-only practices worth borrowing | Forbidden elements |
| --- | --- | --- | --- | --- | --- |
| `obra/superpowers` | Full coding-agent methodology for Claude, Codex, Cursor, Kimi, OpenCode, Pi, Copilot, Droid, and Antigravity. | Strong plan-first, TDD, verification-before-completion, and review-before-merge discipline. | High: installs, session hooks, worktrees, subagents, and autonomous branch/PR workflow. | Socratic design refinement, chunked design approval, evidence-before-claims, and review gates. | Plugin install, hooks, worktree automation, subagent/autonomous execution, external eval scripts, and copied skill text. |
| `EveryInc/compound-engineering-plugin` | Compound Engineering workflow plugin across Claude, Codex, Cursor, Kimi, OpenCode, Pi, Copilot, Droid, Qwen, and Antigravity. | Strong planning, review personas, debugging, simplification, handoff, and PR-description discipline. | High: `/lfg` commits, pushes, opens PRs, watches/fixes CI, and relies on package/plugin manifests and scripts. | Plan/review loop, structured findings, scoped review personas, and compounding local lessons. | `/lfg`, commit/push/PR skills, browser/CI automation, plugin install, scripts, package metadata, and copied prompt assets. |
| `trailofbits/skills` | Security-focused Claude marketplace compatible with Codex marketplace loading. | Very high for audit process: context building, false-positive checks, static analysis, supply-chain review, and SARIF literacy. | High for direct use: scanner/tool assumptions, Bash/Write/Edit tools, SARIF output directories, MCP files, external rulesets, and CLIs. | Threat boundaries, source-to-sink tracing, scanner humility, false-positive verdicts, and supply-chain questions. | Running Semgrep or CodeQL, installing plugins, cloning rulesets, importing MCP configs, importing hooks/scripts, and copying scanner rules. |
| `trailofbits/skills-curated` | Reviewed/approved marketplace with security, development, research, and converted OpenAI skills. | Useful curation model and explicit concern about malicious hooks and backdoored skills. | Medium-high to high: still a plugin marketplace with scripts, commands, deploy/GitHub/PR skills, and automation assumptions. | Review every hook/script line, require attribution, prefer curated/portable process, and use threat-model docs. | Marketplace install, converted deployment/GitHub automation, `openai-yeet`, external scripts, and copied marketplace manifests. |
| `trailofbits/claude-code-config` | Opinionated Claude Code setup for sandboxing, permissions, hooks, MCP, and usage patterns. | Useful conceptual guardrails around secrets, dangerous commands, MCP default-off, and hook risk. | High: global config, shell setup, package installs, `--dangerously-skip-permissions`, hooks, and MCP servers. | Treat project MCP as untrusted, deny dangerous patterns, keep local handoff files, and reduce stale context. | Copying settings, hooks, MCP templates, install commands, bypass-permission workflow, autonomous commands, and shell aliases. |

## Code-audit And Security Practices Worth Borrowing

Pietto may borrow these practices as local text-only process:

- threat-model-lite before expanding behavior: assets, trust boundaries,
  entry points, attacker capabilities, and non-capabilities;
- context building before findings: modules, inputs, outputs, state/effects,
  invariants, call flow, and data flow;
- source-to-sink evidence before security claims;
- evidence-first findings with explicit verdicts;
- false-positive discipline that distinguishes confirmed issue, false
  positive, robustness issue, and deferred design risk;
- scanner humility: zero findings from tools or review are inconclusive
  without coverage evidence;
- supply-chain and dependency review as a policy surface, without running
  dependency scanners by default;
- path/config/source-read/resource review for project roots, source selection,
  TOML parsing, UTF-8 reads, diagnostics, and resource boundaries;
- generated, golden, workflow, package metadata, release, tag, publish,
  upload, signing, and attestation boundary review.

## Pietto-local Adoption Strategy

Pietto should create and maintain local workflow and audit documents rather
than importing external frameworks. External repositories remain text-only
references for process language only.

The local adoption boundary is:

- useful process language may be summarized in Pietto-owned docs;
- direct adoption risk must be recorded before any future change;
- forbidden automation, config, code, hook, MCP, dependency, workflow, and
  release surfaces must stay deny-by-default;
- external plugins, external repo scripts, external scanner execution, and
  copied external code remain prohibited unless separately approved;
- `AGENTS.md` remains unchanged by Slice 5.

## Next Maintenance Phase 2 Work

After Slice 5, Maintenance Phase 2 should likely use one completion
audit/status-lock slice before Phase 45 unless this matrix reveals a later
docs-only policy gap. Phase 45 remains `Project-wide Semantic Model Design And
MVP`; Slice 5 does not start Phase 45 behavior.

## Release Posture

Maintenance Phase 2 Slice 5 performs no release operation. It authorizes no
package version change, tag, release, publish, upload, signing, or attestation.
