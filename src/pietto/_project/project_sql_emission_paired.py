"""Phase77 Wave A paired forms, names aside.

MySQL opens a Wave A construct only in a statement that is byte for byte one
form the slice's qualification pack runs on both PostgreSQL and MySQL, with
only its names changed. Each reader reduces its own input to those bytes
without names and compares their digest with the form's: emission and the
live verifier the selected module and the request's contract, compiled replay
the bundle's records. A name is an ASCII identifier of at most 63 bytes that
does not start with `__pietto` and differs, ignoring case, from the other
names of its kind; a table locator has exactly two such parts. A paired
statement whose emission does not give its form's SQL, names aside, reports
main's output, derived again as main (rows.AS_MAIN, which `closed` sets);
loading refuses a bundle whose records are a form but whose SQL is not, as
before.
"""

from contextlib import contextmanager
import hashlib
import json
import re

from pietto._project import project_compiled_schema as schema
from pietto._project import project_sql_emission_rows as rows
from pietto._project.project_sql_plan_literals import ProjectSQLLiteralPolicy

__all__: tuple[str, ...] = ()

# S16 lag/lead Text defaults: P-S16-1 s16_text_defaults, P-S16-2
# s16_quote_default, P-S16-3 s16_x_metadata. Per form: the sha256 of the
# module and contract, of the emitted SQL and of the compiled records, and the
# number of compiled records.
FORMS = (
    (
        "9e74ea22bb430348248b9b5dc0ef1c38f4c829020dd6015cd6e4703d0efb71a2",
        "04387d1f0036bec34c49dbf283841b3740c5acc9783987459b15fd2566f125a7",
        "ece6d96ec01710452e751bded39da4c75aca195793fa056a2e6817c74130fd74",
        324,
    ),
    (
        "432e21a98ca1d781df1810c46e769404fd94a1fd1aa99ae7bc8c88490669da83",
        "bdc484a6bde767f263ac84291765a56cf9926a1a849a742cfa3b46188d674eaa",
        "0c8242877a91b2be7b0fbfb4cc855ea505983c675719e6c2619756ce8f60b7d7",
        273,
    ),
    (
        "40ed6ecb83301498a5a7e5ea21ec9a44d51c53bfa14d53faefd645ead2ca68c6",
        "72a29d6b8bc61f2bd0258601037240310c6a7f0e20029a8822b6d9ca4acb57cf",
        "2a865393b1dac80e5bef3254dfe253d540521f32b2ce28ee200595d3bd0ebb9f",
        400,
    ),
)
_FIXED = frozenset(
    "shape source query from select window order by lag lead mysql table"
    " Int Bool Text Decimal Float None".split()
)
# re.ASCII: IGNORECASE alone lets the Kelvin sign match k (D77.36 ASCII names).
_NAME = re.compile(r"(?!__pietto)[A-Za-z_][A-Za-z0-9_]{0,62}", re.ASCII | re.IGNORECASE)
_TOKEN = re.compile(r'(?<=mysql\.table\()"([^"\\\n]*)"|"(?:[^"\\\n]|\\.)*"|[^\W\d]\w*')
_QUOTED = re.compile(r"`(?:[^`]|``)*`")
_COMPILED_NAMES = {
    "source": (("namespace", "S"), ("name", "R")),
    "field": (("label", "N"), ("column", "C")),
    "declaration": (("module", "M"), ("label", "N")),
    "output": (("label", "N"),),
    "port": (("label", "N"),),
}


@contextmanager
def closed():
    """Read every statement as main does (rows.AS_MAIN): unpaired."""
    token = rows.AS_MAIN.set(True)
    try:
        yield
    finally:
        rows.AS_MAIN.reset(token)


class _Names:
    """Names by kind in order of first use; `valid` once every one is a name."""

    def __init__(self):
        self.seen, self.folded, self.valid = {}, set(), True

    def __call__(self, kind, name):
        if type(name) is not str:
            raise TypeError("name")
        if (kind, name) not in self.seen:
            parts = name[:-7].split(".") if kind == "M" else name.split(".")
            self.valid &= (
                (kind, name.lower()) not in self.folded
                and (name.endswith(".pietto") if kind == "M" else True)
                and len(parts) == (2 if kind == "L" else 1)
                and all(_NAME.fullmatch(part) for part in parts)
            )
            self.folded.add((kind, name.lower()))
            count = sum(seen[0] == kind for seen in self.seen)
            self.seen[kind, name] = f"\0{kind}{count}\0"
        return self.seen[kind, name]


def _module(text, names):
    def token(match):
        if match[1] is not None:
            return '"' + names("L", match[1]) + '"'
        if match[0][0] == '"' or match[0] in _FIXED:
            return match[0]
        return names("N", match[0])

    lines = "".join(line + "\n" for line in text.split("\n") if line)
    return _TOKEN.sub(token, lines)


def _contract(raw, names):
    document = json.loads(raw)
    for source in document["sources"]:
        selector, relation = source["selector"], source["relation"]
        selector["module"] = names("M", selector["module"])
        selector["name"] = names("N", selector["name"])
        relation["namespace"] = names("S", relation["namespace"])
        relation["name"] = names("R", relation["name"])
        for field in source["fields"]:
            field["name"] = names("N", field["name"])
            field["column"] = names("C", field["column"])
    return json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _form(column, text, names):
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    for index, form in enumerate(FORMS):
        if form[column] == digest:
            return index if names.valid else None
    return None


def project_text(path, source, contract, selected, names):
    """One module's bytes, its contract and its selected (name, kind), names aside."""
    return "\0".join(
        (
            names("M", path),
            _module(source, names),
            _contract(contract, names),
            names("N", selected[0]),
            selected[1],
        )
    )


def project_form(request):
    """The paired form the selected statement of this project request is, or None."""
    if rows.AS_MAIN.get() or request.family != "mysql":
        return None
    names = _Names()
    try:
        checked = request.verification
        result = checked.completed.semantic_result
        owner = checked.selected_owner.identity
        (snapshot,) = result.trusted_source_snapshots
        if (
            checked.literal_policy is not ProjectSQLLiteralPolicy.PRESERVE_LITERALS
            or len(result.modules) != 1
            or owner.module_path != snapshot.path
            # Every paired module is far shorter; this bounds each call's work.
            or len(snapshot.source_text) > 8192
        ):
            return None
        text = project_text(
            snapshot.path,
            snapshot.source_text,
            request.accepted_bytes,
            (owner.declared_name, owner.declaration_kind.value),
            names,
        )
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        return None
    return _form(0, text, names)


def sql_text(sql):
    """Emitted SQL with each quoted name numbered by its first use."""
    seen = {}
    return _QUOTED.sub(lambda m: seen.setdefault(m[0], f"`{len(seen)}`"), sql.decode())


def sql_form(sql):
    """The paired form whose SQL this is, names aside, or None."""
    return _form(1, sql_text(sql), _Names())


def compiled_text(records, names):
    """A bundle's records in order, names and source places aside."""
    lines = []
    for record in records.values():
        kind, values = record.address.kind, list(record.values)
        slots = _COMPILED_NAMES.get(kind, ())
        if kind == "port" and record.get("owner").kind not in {"source", "row"}:
            slots = ()  # a stage port's label is a generated name
        for field, name_kind in slots:
            position = schema.FIELDS[kind].index(field)
            values[position] = names(name_kind, values[position])
        site = records.get(record.get("site")) if kind == "literal" else None
        if site is not None and site.get("role") == "connector":
            values[1] = schema.Scalar("Text", names("L", values[1].value))
        elif kind == "requirement_origin":
            # Its place in the module moves with names and empty lines.
            values[4] = (names("M", record.get("location")[0]),)
        elif kind == "target":
            values[2] = _contract(record.get("contract"), names)
        lines.append(
            json.dumps([kind, schema._wire(tuple(values))], ensure_ascii=False)
        )
    return "\n".join(lines)


def compiled_form(records):
    """The paired form whose bundle these MySQL records are, or None."""
    if not any(len(records) == form[3] for form in FORMS):
        return None
    names = _Names()
    try:
        text = compiled_text(records, names)
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        return None
    return _form(2, text, names)
