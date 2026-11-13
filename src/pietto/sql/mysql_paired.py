"""Phase77 Wave A S25: an asof JOIN beside MySQL's FULL JOIN emulation.

Single-file MySQL emission keeps refusing an asof JOIN in a relation with a
FULL JOIN, except in a file that is byte for byte one of seven S25 forms of
the qualification pack, which pairs PostgreSQL with MySQL, with only its names
changed and empty lines aside, whose emission is then the form's SQL, names
aside. A name is an ASCII identifier of at most 63 bytes that does not start
with `__pietto`, and two names are equal ignoring case exactly when the
form's names they replace are; a `mysql.table` locator is two names joined by
a dot. Any other file, and a paired file whose emission differs, keeps the
output it had before.
"""

import hashlib
import re

from pietto.ir import ScriptIR
from pietto.sql import joins
from pietto.sql.model import SqlResult
from pietto.sql.mysql import emit_mysql_sql

__all__: tuple[str, ...] = ()

# PAIRS.md 5.3 P-S25-2 to 8: s25_full_before, s25_full_before_inner,
# s25_full_after, s25_full_after_inner, s25_between_fulls, s25_full_inner_ids
# and s25_two_fulls_inner; P-S25-9 s25_full_on_asof stays refused until the
# owner keeps it (PAIRS.md section 8, item 1). Per form: the sha256 of the
# file and of its SQL, each names aside.
FORMS = (
    (
        "164930fe99baca7228f5cb83bf95431168e35f10a1327b7ab7936919da5bcb2f",
        "5b93d34f0a91f76e588b3ed9e0c22a8d45f217becea123ae8b36adb7cc15c8ea",
    ),
    (
        "292c30f8d523ff7f789456a65cd4fff64bc37399388c8c8418ea0204d7b88827",
        "5cedca2c7b39ef5a8b11616cda5586d7e10c046c54432b0ea833da090aea57eb",
    ),
    (
        "876a2557ca567e1d202944f5b6a1d108be1878690f1598b34aa5bf76b2b131c9",
        "3207261a74d9d53e2661058af9fb01733b13078efc7f3cfca3d150cb89b4f47e",
    ),
    (
        "66bed0c226ee1842d20f731d15f70d8778791e871cdba9c6ba1d07eb9758a913",
        "a90f3720c5b38fae825a5684206d8f46dce1f76b11980ebd630cfc118d7a4d75",
    ),
    (
        "c03f777a516e60e09a40637135f5972e9a5a46871662069503cf4966c87e1a72",
        "ae05ecb0669d32a88b55a603406b8fc0497fe4f6e5224f20ed9b7706f134ddfa",
    ),
    (
        "311a5e6cb8ae8cdeda261c45754283b5da30f56da40d9a51c54deb0c493d80d8",
        "3b6f3b0344c28d31c5116bfcc32fd8611015459a2d2c986d377e82a612b98a78",
    ),
    (
        "bb5538303777b5e3a39c04079f8359507764a5a0182817143d5303eddb32fd49",
        "5bdfc041c48a32cfa62d7db0e6dd4f7dec61623055bba2d25dbc7a6705dda75c",
    ),
)
_FIXED = frozenset(
    "shape relationship source table query from let select asof full left inner"
    " join on and unique mysql Int Text Timestamp Date Float".split()
)
_NAME = re.compile(r"(?!__pietto)[A-Za-z_][A-Za-z0-9_]{0,62}", re.ASCII | re.IGNORECASE)
_TOKEN = re.compile(r'(?<=mysql\.table\()"([^"\n]*)"|[^\W\d]\w*')
_QUOTED = re.compile(r"`[^`]*`")


def file_text(source: str) -> str | None:
    """The file without empty lines, each name replaced by its place among the
    names equal to it ignoring case; None when a name is not one or the file
    holds a NUL, which could spell a replaced name."""

    if "\0" in source:
        return None
    classes: dict[str, tuple[int, dict[str, str]]] = {}
    valid = True

    def name(word: str) -> str:
        nonlocal valid
        valid = valid and _NAME.fullmatch(word) is not None
        index, spellings = classes.setdefault(word.lower(), (len(classes), {}))
        return spellings.setdefault(word, f"\0{index}.{len(spellings)}\0")

    def token(match: re.Match[str]) -> str:
        if match[1] is not None:
            return '"' + ".".join(map(name, match[1].split("."))) + '"'
        return match[0] if match[0] in _FIXED else name(match[0])

    lines = "".join(line + "\n" for line in source.split("\n") if line)
    text = _TOKEN.sub(token, lines)
    return text if valid else None


def sql_text(result: SqlResult) -> str:
    """The emitted statements with each quoted name numbered by its first use."""

    seen: dict[str, str] = {}
    return _QUOTED.sub(
        lambda match: seen.setdefault(match[0], f"`{len(seen)}`"),
        "\0".join(artifact.sql for artifact in result.artifacts),
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def emit_paired(script_ir: ScriptIR, source: str | None) -> SqlResult | None:
    """The emission of a file that is a paired form, or None."""

    text = None if source is None else file_text(source)
    digest = None if text is None else _sha256(text)
    form = next((form for form in FORMS if form[0] == digest), None)
    if form is None:
        return None
    token = joins.ASOF_BESIDE_FULL.set(True)
    try:
        result = emit_mysql_sql(script_ir)
    finally:
        joins.ASOF_BESIDE_FULL.reset(token)
    if result.diagnostics or _sha256(sql_text(result)) != form[1]:
        return None
    return result
