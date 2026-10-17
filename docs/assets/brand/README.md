# Pietto brand assets

<img alt="Pietto mark" src="pietto-mark-primary-transparent.svg" width="64">

These files are byte-identical copies from the owner's Pietto Brand Kit v2.

| File | Use |
| --- | --- |
| `pietto-horizontal-transparent.svg` | Horizontal lockup (mark and wordmark) with a navy wordmark, for light themes. |
| `pietto-horizontal-transparent-on-dark.svg` | The same lockup with a white wordmark, for dark themes. |
| `pietto-mark-primary-transparent.svg` | The mark alone, for square or tight spaces at 48 px or larger. Its color faces stay the same on light and dark backgrounds. |

Use the lockup where the name should appear and the mark where it already
appears nearby. To switch between the two lockups by theme, pair them in a
`<picture>` element with `prefers-color-scheme`, as the top of the repository
`README.md` does. That README is also the PyPI long description, which cannot
resolve repository paths and drops the `<source>` element, so it names the
files by absolute URLs pinned to a commit and its `<img>` fallback is the
light-theme lockup.

## Palette

| Role | Hex |
| --- | --- |
| Top face | `#005BD9` |
| Stem face | `#1E89FE` |
| Return face | `#84D8FF` |
| Wordmark on light | `#0B2A6B` |
| Wordmark on dark | `#FFFFFF` |

The SVG faces carry subtle gradients around the three face colors.

## Usage rules

- Keep the mark's geometry, diagonal seam and colors unchanged. Do not recolor
  the color faces, including on dark backgrounds.
- The seam and the gap beside the stem are real negative space. Do not fake
  them with a white stroke or move one face on its own in a static mark.
- The wordmark is outlined paths. Do not retype it in a font.
- Use the `-transparent-on-dark` variants in dark UIs. In kit file names,
  `-white` and `-black` name the background, not the mark.
- Keep clear space of about half the stem width around the mark. Below 48 px,
  use the kit's micro marks.

## Full kit

The full Pietto Brand Kit v2 (other variants, icons, motion, tokens, fonts,
rebuild sources and the visual guide) is held by the project owner and is not
part of this repository.

## Credit

Mark and wordmark from Pietto Brand Kit v2, created for Pietto branding from
the owner-selected Bright Humanist 03 reference. The mark is Penrose-inspired,
not a mathematically strict impossible triangle. The kit imposes no software
license on this repository.

## License

The Pietto logo artwork in this directory is © Mianli Wang, all rights
reserved, and is not covered by the MIT License that applies to the code.
