# Phase 59 Slice 11 Differential Compatibility Assurance v1

## Scope

Phase 59 Slice 11 proves that one real authored private package-graph corpus
has the same authoritative semantic and provenance result across Python
versions, hash seeds, repository and project relocation, independent repeated
construction, source-checkout imports, and an isolated installed wheel.

It adds no production semantics, public graph artifact, Project Explain field,
CLI route, package behavior, persistent identity, golden file, workflow,
dependency, version, or performance optimization. Expected production semantic
changes remain zero.

## Reused Real Corpus

The test-side probe
`tests/_pietto_phase59_graph_differential_probe.py` reuses the exact Slice 10
module bytes plus the existing authored project/package fixture vocabulary. It
writes:

- one schema-v4 project with a real root-package activation and target;
- one root package with one authored dependency occurrence;
- one dependency package with extension-signature and logical-type
  requirements plus the typed selector;
- one identical `main.pietto` module in each package; and
- per-package schema-v2 semantic compilation configs.

The authored source exercises source, direct, renamed, computed, let,
aggregate, and current-window lineage. The logical requirement reaches the
existing typed `unknown` why-not terminal; the extension requirement reaches
the existing selected catalog/provider/source evidence.

No final `PackageGraphSnapshot` or lineage section is hand-built. The probe
follows the existing discovery, loading, inspection, capability, semantic,
graph, integrity, canonical inspection, and query entry points.

## One Common Expectation

`tests/test_phase59_slice11_differential_compatibility_assurance.py` owns one
common expectation named `EXPECTED_COMMON_MANIFEST`. Python 3.12 and Python
3.13, every hash seed, every relocated run, source checkout, and the installed
wheel consume it unchanged. There is no environment-specific expectation.

The manifest combines:

- the exact Slice 9 private canonical-byte digest and size;
- one digest of the complete ordered record/link/state projection;
- the complete human-reviewable direct/all-path/why-not query projection;
- human-reviewable package, module, declaration, capability, catalog, count,
  and Project Explain/CLI facts; and
- an explicit true result for runtime-scope inequality.

Byte-valued evidence is represented in the test observation by its exact size
and SHA-256. No path, collection, whitespace, status, ordinal, role, or
multiplicity is normalized. This test-local comparison manifest is not a new
public schema or canonical golden file.

## Equivalence And Identity Laws

Across every run, the complete observation remains equal. It retains:

- dependency-first package order and the exact authored dependency link;
- ordered package/module/declaration/field local coordinates;
- requirement/selector/capability/catalog/provider/source attribution;
- sparse positive topology plus typed negative evidence;
- source/direct/renamed/computed/let/aggregate/current-window roles and input
  positions;
- duplicate-looking n-ary inputs with distinct occurrence positions;
- every ordered direct and all-path query result;
- the exact typed why-not terminal; and
- the exact private canonical inspection and successful integrity verdict.

Each process also constructs two equivalent graphs. Their runtime scopes and
runtime refs remain intentionally unequal, while their private inspections and
canonical bytes are equal. Opaque scope tokens are neither compared nor
emitted.

Package dependencies create package provenance only. Every semantic-lineage
link remains within one package position, so dependency loading grants no
semantic visibility and creates no cross-package graft.

## Hash Seed And Python Matrix

The isolated subprocess matrix is exact:

```text
PYTHONHASHSEED = 0, 1, 7, 4294967295
```

Every seed runs the full corpus from a distinct project root and cwd. The
comparator does not sort or deduplicate results. Existing authored occurrence
order is the only ordering authority.

Available trusted local Python 3.12 and Python 3.13 interpreters run the same
probe and common expectation. Combined version/seed/relocation branches run
Python 3.12 with seed 1 and Python 3.13 with seed 4294967295 when those
interpreters are locally available. Natural CI independently runs the complete
committed suite under both supported versions.

This matrix does not start `scripts/validate.py`; the authoritative validator
remains one separate post-review execution.

## Relocation Boundary

Project roots, run cwd values, and irrelevant ambient values differ for every
subprocess. A source-relocation branch copies only `src/` plus the probe and its
existing authored-scenario helper to a temporary repository root. The complete
observation must equal the source baseline without stripping paths.

Absolute repository paths, temporary names, cwd, object addresses, runtime
scope tokens, and installation paths never enter authoritative output.
Published logical and physical evidence remains unmodified; equivalent
relocation is established at the Slice 9 semantic/canonical boundary.

## Installed-Wheel Boundary

The focused harness reuses the existing fresh-cache wheel helper. It builds the
exact candidate wheel offline, installs only that local wheel with
`--offline --no-deps --target`, places the wheel target first on `PYTHONPATH`,
and runs the same graph probe from a neutral external cwd. `pietto.__file__`
must resolve under the wheel target and outside the source repository.

The installed run imports and executes the Phase 59 package graph and graph
inspection modules through all production entry points. Its complete
observation equals the source-checkout observation. The unchanged central
`scripts/package_smoke.py` separately owns sdist/wheel inventory, isolated
environment installation, private-module imports, and installed CLI behavior.

## Compatibility And Zero Delta

The real project remains successful through Project Explain runtime plus text
and JSON CLI execution. Project Explain v1 and CLI remain zero-delta across
every differential environment.

Slice 11 introduces no new graph/package/module/lineage semantics, public or
persistent IDs, sorting/deduplication/winner, canonical parser, xdist adoption,
benchmark, Rust, Phase 60 behavior, or validation/test performance work. The
generated/golden delta is 0 / 0.

After the one authoritative validator, the only required risk-gated
auxiliaries are the central generated check, golden check, and installed
package smoke. The focused wheel differential is not a substitute for the
central package smoke.

## Lifecycle

The candidate records Phase 59 active, Slices 1–10 completed, Slice 11 current,
and Slice 12 next/unstarted. Live Git plus successful natural exact-head CI own
completion; no status-only follow-up commit is required.

Slice 12 must record, but Slice 11 does not begin, this already-decided
prerequisite:

```text
Phase 59 completion -> validation/test performance optimization interlude -> Phase 60 activation
```

The only ordinary commit subject is:

```text
Add Phase 59 differential compatibility assurance
```
