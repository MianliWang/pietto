# Pietto Lean Validation And Evidence Standard v1

## Status and purpose

This standard removes repeated mechanical work while preserving every Pietto
validation and publication assurance. “Lean” means fewer redundant executions
and compact immutable evidence. It never means fewer assertions, a skipped
gate, a permissive manifest, or reduced CI.

## Two scope freezes

Freeze product scope before implementation. Then use deterministic reader
discovery to converge and freeze the mechanical scope. Do not start the full
authoritative validation sequence before the exact manifest, reader closure,
formatter set, and topology registry have converged.

The exact active Gate 2 matcher has one stable logic owner and one focused
per-Goal data owner. It accepts only the exact base, Goal marker, A/M/D sets,
changed paths, empty index, expected branch/upstream state, no unrelated
untracked path, one non-shallow worktree, and no active Git operation. Subsets,
supersets, stale Goals, wrong statuses, staged changes, environment activation,
callbacks, global registries, wildcards, and broad prefixes fail closed.

## Deterministic reader closure

The repository-owned reader auditor receives explicit root, base, manifest,
active-data, and output inputs. It classifies literal path readers, raw source
readers, SHA-256 and Git-blob readers, directory digests, tracked and generated
inventories, class/dataclass/enum/field and constructor inventories, docs exact
phrases, dirty-manifest and formatter readers, topology readers, imports, and
readers of readers.

Its canonical output includes direct and transitive readers, reasoned edges,
SCCs, dependency-first refresh order, content/topology classifications,
unresolved warnings, and exact ordering. An unresolved dynamic reader is STOP;
static difficulty is never permission to omit it. The tool is independently
checked with synthetic path/hash/blob/digest/nested/SCC cases, a brute-force
scan, frozen predecessor closures, and the complete legacy validation result.

## Content and topology separation

Content-sensitive tests depend on bytes, hashes, blobs, inventories, docs,
types, signatures, generated inventories, or directory digests.
Topology-sensitive tests depend on HEAD/base/candidate identity, refs, parents,
shallow state, GitHub event fields, `origin/main`, dirty/index state, or
successor subject.

There is exactly one topology node-ID registry. For an exact reviewed tree:

1. execute the complete content/reader closure once;
2. execute only the topology registry under candidate, shallow PR merge-ref,
   shallow main-push, and reconciled-main projections;
3. execute the complete clean validation once after tree freeze;
4. retain full PR CI and full main CI.

Topology projections are serial and run in isolated local clones or temporary
indexes. They never mutate the primary repository index. Every projection
records commit identity, parents, tree, branch, shallow state, environment,
event payload, selected node IDs, result, and timing. A natural depth-one
detached PR merge-ref is valid; a depth-one active dirty Gate 2 is invalid.
Exact negative cases must
fail through the intended topology assertion, not collection or import errors.

## Offline authoritative command graph

Every `uv` invocation uses `UV_OFFLINE=1` and `UV_NO_SYNC=1`. The lean runner
fails closed for manifest drift, a nonempty index, unresolved reader warnings,
or a command failure. It records every command and return code and coordinates:

1. lockfile check;
2. explicit focused and compatibility tests;
3. deterministic reader audit and complete reader closure once;
4. topology-only projections;
5. formatter check and Ruff lint;
6. production and test Pyright;
7. `scripts/validate.py` exactly once after convergence;
8. clean collection and full clean pytest;
9. generated, golden, and package smoke checks;
10. installed CLI/version verification;
11. evidence-sidecar construction and verification.

`scripts/validate.py` remains authoritative and is not replaced.

## One-time legacy equivalence

The migration Goal runs both routes on one exact reviewed tree. It compares
per-test outcomes across all applicable topologies, proves every
topology-varying test is in the registry, proves every excluded content reader
is topology-invariant, and proves the lean command graph contains every old
authoritative fact. No assertion may become skipped, xfailed, deselected, or
weakened. Only after equality passes may future Goals retire repeated complete
reader-suite topology runs.

## Performance evidence

Record actual command and pytest-process counts, selected items, repeated reader
items, topology items, wall time, CPU time when available, cache state, Python
and tool versions, and outcome equality. The lean route must select fewer
repeated items, execute the complete reader closure exactly once, repeat only
the topology registry, and execute authoritative full validation exactly once
after convergence. No arbitrary speedup percentage may encourage weaker
coverage.

## Sidecars and concise authority

Gate 2 creates exactly six deterministic sidecars in this order: identity TSV,
binary-capable canonical patch, command-ledger JSONL, reader-closure JSON,
topology-results JSON, and performance-results JSON. Build under `/tmp`, verify
schema/encoding, then create each immutable external target exclusively.

The main Gate 2 report records every sidecar path, mode, links, lines when
textual, bytes, SHA-256, schema, and purpose. It does not embed the complete
manifest, patch, command output, or topology ledger. No sidecar is rewritten
after the main report. Gate 3 references rather than duplicates sidecars.

The verifier requires all six regular non-symlinks at mode `0644`, exact hashes
and schemas, matching base/reviewed tree, complete command records, no
placeholder or malformed SHA, one terminal exactly at EOF, and no bulk payload
duplication.

## Cache and parallelism

Offline cache reuse requires an exact content-addressed identity including
platform, Python, uv, `uv.lock`, package metadata, and relevant tool versions.
A mismatched cache fails closed. Cache support cannot weaken `uv lock --check`,
permit network, change dependencies, or change CI.

Use local parallelism only after deterministic serial equivalence proves the
worker configuration safe. Topology, formatter, generated, golden, and package
gates remain serial. Existing full PR and main CI remain unchanged.
