# Release-note fragments

Each slice that changes what a program can observe writes its part of the
next release's notes here, as one file named `<phase>-<slice>-<topic>.md`:
the phase number, the slice id (one lowercase letter and two digits) and a
lowercase hyphenated topic, for example `76-s03-window-keys.md`.

A fragment holds that slice's subsections of the release section. It starts
with a `###` heading, has no `#` or `##` heading, and says what a program can
now observe, its compatibility rows and its new refusals, as the subsections
of [the release notes](../release-notes.md) do. Every diagnostic code keeps
its `PIE-` prefix and every `pietto` block is written as `pietto fmt` writes
it. A later slice that changes the same notes edits the fragment.

```bash
UV_PYTHON=3.13.13 uv run python scripts/release_notes.py check
UV_PYTHON=3.13.13 uv run python scripts/release_notes.py assemble --version X --title T
```

`check` checks every fragment; the docs tests read the fragments too. The
release commit first migrates documentation links from specific fragments to
the new `docs/release-notes.md` section, then runs `assemble`, which puts
`## T — X` above the previous release in `docs/release-notes.md`, follows it with the fragments ordered by
phase, slice and topic, and deletes them; that commit then writes the
section's status, highlights, upgrading and known limitations. See
[Lean Gate v3](../development.md#lean-gate-v3).
