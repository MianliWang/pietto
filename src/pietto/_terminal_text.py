"""Unicode controls that single-line terminal text shows as escapes."""

from __future__ import annotations

# C1 controls (NEL and CSI among them), the Arabic letter mark, the
# left-to-right and right-to-left marks, the line and paragraph separators, the
# bidi embeddings and overrides, and the bidi isolates.
_ESCAPES = {
    code: f"\\u{code:04x}"
    for code in (
        *range(0x80, 0xA0),
        0x061C,
        0x200E,
        0x200F,
        *range(0x2028, 0x202F),
        *range(0x2066, 0x206A),
    )
}


def escape_unicode_controls(text: str) -> str:
    r"""Write each C1, separator or bidi control as \uNNNN.

    Text presentation applies this after its own C0 and DEL escaping, so
    source text cannot drive the terminal, break the line or reorder it.
    """

    return text.translate(_ESCAPES)
