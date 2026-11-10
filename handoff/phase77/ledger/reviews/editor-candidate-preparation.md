# Combined maintenance and editor candidate preparation

Status: `PREPARED_NOT_VALIDATED` on 2026-11-09 (America/Toronto).

This is an isolated clone at `candidates/editor-combined`, seeded from the
published baseline `f8ccd2c44a2d9adf431a496bd9bbae037783176f` / tree
`460e3e135d1dcb0b926928bc2632a889410f258a`. It is not a commit, Gate 2,
package build, extension acceptance, database run, publication, or release.

## Composition

The candidate first applies the complete current M77 maintenance patch from
`candidates/maintenance`, SHA-256
`548e72276b20c2bff3bb0613a527ef230fb9095942b562dca32a6150da12e1cc`.
It then applies only the approved editor candidate inputs from the canonical
worktree:

| Canonical input | SHA-256 | Candidate relation |
| --- | --- | --- |
| `docs/editor-lsp.md` | `318c682cd286380e6adbc13ce85e588c9ef89b1f9820d7d8358dd17db6b7378c` | byte-identical |
| `src/pietto/_lsp.py` | `ea903beba0b079ba7d3a074d24bae783b21af9560fb0a66c10321fcc13048aed` | byte-identical |
| `src/pietto/_project/check.py` | `712947dff519313f0992a2375e941932155b3f4ec0e24d03fd240379841ec854` | byte-identical |
| `tests/test_cli_lsp.py` | `eeea1faba58138ecd26bd84036c956063a45c6e838656873ffb142a6f27a0341` | byte-identical |
| `tests/test_project_editor_overlays.py` | `58c9bb1f5121f381755b041e856d7c513e32ddb4968ab856d64eae20d850bb58` | byte-identical |
| `docs/release-notes.d/77-e01-editor-navigation.md` | `f2949f23223968c438a8328080c43d65554c7e407b89f0309996be93e865de61` | byte-identical |
| `docs/spec/lsp-diagnostics-v1.md` | `2a4d71ba0f94a94c346d2814d4054773d074d5f7cbd442a468cbb0acc5a28cd8` | byte-identical |
| `docs/spec/lsp-editor-facts-v1.md` | `b38302d07a98d74551cb9c75e44447eb5abce5382470acd40960f3e56d3f6459` | byte-identical |
| `src/pietto/_editor_facts.py` | `4a8fc44a2b2edf5bb0fee85faad0a94129acfe432e99fac0411cac3081809280` | byte-identical |

`scripts/package_smoke.py` is intentionally a composed file: the canonical
editor input is `b03c6c47a81393054066b5ab6a78355b2de1d24bc61f152c7e8a23629186287d`,
the maintenance input is `780767beb3b77fc6c29ef049e3c48e442f1e56c3f1004e0a9185c80b95cf6a1b`,
and the combined candidate is
`6005405a94471592761aced607d422a28234136183d2e46e689a06377ce223ee`.
The candidate retains both independent hunks: the PyArrow 26.0.1 pin and the
advertised standard LSP capabilities.

## Sealed input identity

The temporary-index tree is `a5d300bb1e6a0216ee95b62552466f407cdc40cb`; no
canonical index was read or modified to construct it. The complete candidate
binary diff hashes to
`a1a867ec37151a58c38db75902c4f14b32bbbaf1967fa85c0cb17293f3aa6799`.
It has 40 modified tracked paths and four intended untracked editor paths.
`git diff --check` passed. The detailed machine-readable identity is
`reviews/editor-combined-candidate-manifest.json`; it is deliberately outside
the candidate so it cannot mutate the sealed input it describes.

The historical `a0c662...` editor tree and its raw receipts remain unavailable;
this fresh candidate does not claim equality with that lost tree or reuse its
results.

## Next checks, not yet run

1. Run the existing focused owners for `tests/test_cli_lsp.py` and
   `tests/test_project_editor_overlays.py` with Python 3.13.13. This covers the
   standard hover, definition, document-symbol, version-invalidation and
   diagnostics-only overlay boundary without adding a new test owner.
2. Generated inputs have not changed, so generated checking is `NOT_SELECTED`.
   The prior preparation conclusion that golden checking was also unselected
   was wrong: `src/pietto/_project/check.py` is a project compiler input and
   therefore enters the golden input closure even though no fixture file
   changed. Run the existing `scripts/check_goldens.py` owner once.
3. After focused repair/review, bind a new candidate identity and run one
   authoritative Python-3.13 Gate 2 exactly once. The already running M77
   Gate 2 is for the maintenance candidate and does not validate this combined
   candidate.
4. Build and smoke-test wheel and sdist from the sealed combined identity, then
   use that exact wheel for the extension's existing Node and VS Code host
   acceptance. It must observe hover, an exact cross-module definition and
   source-ordered document symbols. Preserve raw logs and do not substitute
   the older SQL-preview-only evidence.

No test, build, installation, package smoke, editor host command, database
command, commit, push, release, or external CI was run while preparing this
candidate.

## Focused follow-up

R1 built the candidate artifacts and installed the independent editable and
wheel environments, then failed before pytest collection because its runner
did not create the `PYTEST_DEBUG_TEMPROOT` parent. That launch is preserved in
`reviews/editor-focused-r1.md`; it is not a product result.

Fresh R2 created a new evidence directory, reused those exact retained
artifacts and environments after binding their paths and hashes, and created
the missing temporary parent before its one focused pytest launch. It passed
`88` tests in `12.23s` with at most two workers. The selected golden owner
then passed, verifying `41` fixtures: `34` SQL byte-exact and `7` JSON
structural. The R2 terminal is `PASS`; its candidate before/after tree and
tracked patch match. Evidence is
`evidence/editor-focused-r2-20261110T043000Z/run/`.

The retained wheel SHA-256 is
`9d2b31b0fa72ee40b1f671b5aa50f5eb0fedc83fdc19fe3d20bf2378e2921dd2`, and
the exact installed-wheel Python is
`runtime/editor-runtime/installed-wheel/bin/python`. This focused result is
not a Gate 2 or VS Code host acceptance.

The existing package-smoke owner also passed once against that exact retained
wheel and sdist in a fresh, independent core driver plus fresh installed core
and Arrow cells. It verified artifact inventory and metadata, installed CLI
behavior including the new advertised LSP capabilities, core-without-Arrow and
Arrow-with-`pyarrow 26.0.1` isolation, and wheel-byte installation identity.
The package evidence terminal is `PASS` at
`evidence/editor-package-r1-20261110T044000Z/run/`; candidate tree and patch
bindings were unchanged before and after. It is still separate from Gate 2 and
extension host acceptance.
