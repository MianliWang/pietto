---
name: pietto-mechanical-closure
description: Close the Pietto reader, hash, digest, inventory, manifest, and heading surface after a semantic freeze - execution-based discovery, reader-of-reader graph, strongly connected component order, dependency-first expected values, reviewed dry-run patch, then zero-addition and zero-delta closure. Invoke explicitly after the semantic freeze.
disable-model-invocation: true
---

# Pietto Mechanical Closure

Normative contract: `docs/spec/pietto-semantic-slice-convergence-governance-v1.md`.
Deterministic helpers: `tests/_pietto_reader_closure.py`. Worked material:
`reference.md` next to this file.

Run this only after the semantic freeze. A new semantic edit invalidates the
freeze and every refresh below must be redone.

## 1. Reader and reader-of-reader discovery

A reader is a tracked file whose assertions consume another tracked path's
content, digest, inventory, heading structure, manifest, or repository-state
projection.

- Discover by execution, never by guess: project the planned change into an
  isolated copy, run the complete validation, take the failing set.
- Repeat until one full pass adds nothing.
- Then repeat with the expected values actually substituted, because a
  reader-of-reader keyed on a literal value only fails once that value moves.
- Discovery is read-only. No tool rewrites a repository file while discovering.

## 2. Reader classes to sweep

Hash and digest locks; byte and line counts; path and directory inventories;
repository-wide language and module counts; aggregate test-item counts;
Markdown heading structure; the active gate manifest; publication lifecycle
state. Adding one file moves every repository-wide inventory quantity.

## 3. Dependency graph and components

Build the reader graph, condense it into strongly connected components, and
refresh in dependency-first order so a reader of a value is refreshed after the
value it reads. A multi-node component means the members must be refreshed
together and re-verified as a unit.

## 4. Dependency-first expected values

Calculate expected replacements as exact literals with exact occurrence counts,
in condensation order. Never guess a count forward and never back-derive one
from a previous repair's modified set: the executing closure, the byte-modified
set, and the frozen allowlist are three different sets.

## 5. Reviewed patch proposal

The tooling proposes; the primary reviews and applies. Read the proposed plan
before applying it, and confirm the occurrence counts match the intent.

## 6. Zero addition and zero delta

Closure requires both, independently:

- **zero addition** — a full discovery pass finds no new reader;
- **zero delta** — no expected replacement still matches anywhere.

Re-run both after the final edit, not before it.

## 7. Projection sweep

Repeat the closure check under every publication projection, not only the local
one. Use `pietto-publication-topology` for the projection set. Include the
focused module of the current work in every projection sweep; omitting it has
historically produced integration failures after a green local run.

## 8. Formatter and budget discipline

Honor the latest published formatter authority. When write-mode formatting is
no longer authorized, repair formatting by exact edits and verify with check
mode over exact literal paths — never a glob, a directory, or a bare dot.
Budget correction allowances explicitly and stop before exhaustion.
