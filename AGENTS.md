# AGENTS.md

## Pietto

Pietto is a gradual, semantic SQL authoring DSL and compiler. It turns Pietto
source into a parsed AST, semantic facts, immutable IR, and explicitly selected
PostgreSQL or MySQL SQL, with CLI text or JSON output.

Pietto is not a database, runtime language, job scheduler, concurrency
framework, transaction manager, query optimizer, web UI, DML executor, or a
way to run arbitrary Python, network, or file I/O from Pietto programs.

Communicate with users in Chinese by default. Keep code, identifiers, paths,
commands, diagnostics, and commit messages in English.

## Language and product rules

- Use Python-style `:` plus spaces-only indentation. Do not introduce braces
  as block delimiters, tabs, or gratuitous keywords.
- Keep accepted syntax readable and minimal. Unsupported semantics or selected
  backend shapes must fail closed with deterministic diagnostics.
- Preserve parser/AST source locations, semantic identity, complete collections,
  source and authority ordering, multiplicity, and availability. Do not choose
  arbitrary winners for collisions, omissions, grafts, or cycles.
- Preserve public CLI/JSON shapes, diagnostic codes and ordering, stable SQL
  output, and the public PostgreSQL emitter unless explicitly authorized.
- Treat trusted opened bytes, package/dependency identity, generated artifacts,
  and pinned external actions as trust boundaries. Git detects ordinary edits;
  add a digest only when a real cross-boundary consumer needs content identity.

## Working rules

- Prefer deletion, existing code, the standard library, and the smallest
  behavior-equivalent change. Fix causal roots rather than sibling symptoms.
- Keep production behavior, parser/AST, semantics, IR, SQL, diagnostics, CLI,
  JSON, package behavior, and generated reproducibility covered by current
  behavior tests. Do not retain historical repository-shape snapshots.
- Do not edit generated parser files by hand. Change the grammar and run the
  documented generation and reproducibility checks.
- Use focused tests and Ruff while implementing. Before a normal Gate 2 seal,
  run the authoritative Python 3.13 validation. Run generated, golden, and
  package checks when their paths change. Publication/Git infrastructure needs
  a depth-one validation. Natural CI owns final Python 3.12 and 3.13 coverage.

## Decisions and authority

Classify work as follows:

- `USER_DECISION_REQUIRED`: product semantics, public compatibility, durable
  architecture, or high-risk trust/algorithm choices.
- `ARCHITECTURE_DECISION`: a long-lived internal boundary with material
  alternatives; present alternatives and assumptions.
- `IMPLEMENTATION_FREEDOM`: the simplest behavior-equivalent local choice.
- `DERIVED_MECHANICAL`: formatting, stale references, dead imports, and other
  consequences of an approved change.

Do not promote implementation details into user decisions. Every retained
abstraction needs a current caller or invariant.

## Lean Gate v2

- Gate 0: synchronize `main`, verify a clean repository and no active Git
  operation, then freeze the baseline.
- Gate 1: record only substantive decisions; no historical authority dump.
- Gate 2: implement the minimum change, run focused checks, review the complete
  finding set, make at most one root-cause repair batch, run appropriate final
  validation, and seal the Git tree.
- Gate 3: rebind the baseline, stage exactly the sealed tree, make one ordinary
  commit, fast-forward push, and require natural exact-head CI. A failed head
  is preserved; repair a new child and push it normally. Do not rerun it.

Default records are a concise decision note when needed, Gate 2 baseline/tree/
validation facts, and Git plus natural CI for Gate 3. Mechanical counts,
paths, formatting, and ordinary hashes do not require new authority.

## Git and runtime safety

- Never commit, push, tag, publish, sign, attest, or trigger external CI unless
  explicitly authorized. Before publication verify `HEAD`, tracked tree,
  staging, remote, and fast-forward status.
- `origin/HEAD` is not publication authority. The published branch and natural
  exact-head CI are.
- Use the installed Ponytail runtime: `FULL` for normal work, `ULTRA` for
  minimization, and `ponytail-review` for a candidate review. Do not copy its
  rules here; Pietto's overrides are the semantic, output, and trust boundaries
  above.

## Current documentation

- [Language](docs/language.md): source surface and semantic boundaries.
- [Project and package](docs/project-package.md): projects, modules, packaging,
  trusted loading, and identity.
- [Development](docs/development.md): validation, generated artifacts, and
  Lean Gate v2.
- [Roadmap](docs/roadmap.md): authorized future work.
- [Status](docs/status.md): current lifecycle state; live Git and CI are the
  publication authority.
- Current public contracts: [CLI JSON v1](docs/spec/cli-json-v1.md),
  [diagnostics](docs/spec/diagnostics.md), [project JSON v2](docs/spec/project-cli-json-v2.md),
  [semantic metadata artifact v1](docs/spec/semantic-metadata-artifact-v1.md),
  [configuration](docs/spec/pietto-config-v1.md), and
  [golden fixtures](docs/spec/golden-fixture-policy-v1.md).
