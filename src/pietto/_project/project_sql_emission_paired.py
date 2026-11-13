"""Phase77 Wave A paired forms, names aside.

MySQL opens a Wave A construct only in a statement that is byte for byte one
form the slice's qualification pack runs on both PostgreSQL and MySQL, with
only its names changed. Each reader reduces its own input to those bytes
without names and compares their digest with the form's: emission and the
live verifier the selected module and the request's contract, compiled replay
the bundle's records. A name is an ASCII identifier of at most 63 bytes that
does not start with `__pietto`, and two names of a kind are equal ignoring
case exactly where the form's names in their places are; a table locator has
exactly two such parts. In a module, a word that is one of its slice's
keywords is that keyword, never a name; a bundle's records hold each name in
a field of its own, so there a name is read by its place, whatever word it
is. A paired statement whose emission does not give its form's SQL, names
aside, reports main's output, derived again as main (rows.AS_MAIN, which
`closed` sets); so do loading and compiled emission for a bundle whose
records are a form but that another check refuses, or whose SQL is not the
form's. Records a reader cannot read, checked yet or not, are no form.
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
# s16_quote_default, P-S16-3 s16_x_metadata. S10 conditional counts and tests
# of a group, one form per body: P-S10-1 and 5 s10_grouped and
# s10_empty_grouped, P-S10-2 s10_keyed, P-S10-3 and 4 s10_ungrouped and
# s10_empty_ungrouped. S08 count, min and max windows: P-S08-1..7
# s08_count_star, s08_min_rows_frame, s08_min_partition,
# s08_count_named_window, s08_grouped_window, s08_qualify_count,
# s08_join_window, then P-S08T-1..4 s08_temporal_candidate,
# s08_temporal_nullable, s08_temporal_partition, s08_temporal_peers. Each form
# holds one slice's construct only, so a form opens no other slice. Per form:
# the sha256 of the module and contract, of the emitted SQL and of the
# compiled records, and the number of compiled records.
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
    (
        "7f14a6a0bad8ddfd6644de455f43a9ee40c7a2f8fd2cc5c132bcb8285a276a97",
        "ceb4cc6bcfc77a5817464db9be6b273916e49a8f78c29d93569aad264d8349fb",
        "4e52280d2a85a572168201774ea7eed294e3a812e278a3711a75b67108c1287d",
        244,
    ),
    (
        "811486a36f578a810489f1df7ee086afabce5701d5fe8446bccbeee94bda285c",
        "d5628848ca30cc9d84ae8f49d7ac0363c898502fce64a2f532f87eb9f07ade7e",
        "5c8465ac3d7bb9eec20999a74d8d223ff672b0f7c85cbbef4835515b6274e247",
        261,
    ),
    (
        "436e0b08564b3324fb70e675474a9fce514452549f5e7f9f0611eda51490ea34",
        "05e5c80a7b86df2a99f1b894004b813653e0ef4c4963a038860b4ff3a67823ae",
        "b80218928139e48c915505367a036dcd878a990b6601eb1b9c0315eb5e89ae62",
        231,
    ),
    (
        "de3911508cfe1d23303aa7e861e3363f3cdf44d69c011eb6435caf1ee2883daf",
        "20bf9012ca0cae87d5708529d4007bcc060a8554d56f77c21d52759aadf71e5d",
        "101a7c578cb380ecaf06648523cc2f30e5c0be3d7071e5981634679e2db4f4ab",
        200,
    ),
    (
        "5adfa74a35a6dd0ec935c99ec81415a52c33e25f6c3577c0b7feec7cd3c67524",
        "d0f2bbf5b730b9f70eb80ae780a756bc1f602d30f3ed6d574f892a3be3927a86",
        "215da21f96f9346560072783a72acfa6dcdbfe9462162b36d149e92bd6ec141f",
        207,
    ),
    (
        "a79412e1f82795e327940e49a3dc3060aa87ffe0fecb41e21145e40cc1025494",
        "5e2086cb34cbc57578302c4909f1006612dee675aada25613f01bca086a32bde",
        "8f06627b7ffe33783597e907aec10cead021997d047c7052a232ec505527442a",
        208,
    ),
    (
        "cdd8cffc59776430ff0af07d1a9f9900924e7ef3585bd9a7c83896bc86cfd4a4",
        "7a7d9b6ddbf9bb8d0db9bb9ee81ed48f490a0bf3c1e1665343fd675149b464ae",
        "8bfc2193ad925bedc5eb4208405b1e3e5a028e325effba460a77fc22573a30eb",
        189,
    ),
    (
        "c8cff8bd5d5e451001493d8c28fb84162ef8e9f8bf7a27eff53079059cad8bde",
        "142d52ad17d5b6baf2a44a8b0d32f49526cdb153d87dc36cd6c18f82ebb9fc83",
        "de86612652c05e457ec911c20ad7fe91a40be91515e04f36cb874f9b0041f2f4",
        269,
    ),
    (
        "2450c149e7e9958e1d812d099f1b8d4ed07013f0af4eda5272394f5b03c26d8d",
        "1b4b8f9d3a0c37992c9137f1a5df87c924320e6815b5d87c2b45f2819fee0444",
        "841064d42d1424736f00640ab21ddf33cf453fbb7a91221ad9bed194b6329d94",
        272,
    ),
    (
        "a0852ecfce5d589a31c0301db57d2c44a3b7ff3c5a01e2dd606797b656618ba6",
        "bea589009b5b55b492b54397f7e5567f36ee3980edb2566f61e96ee7541df254",
        "4fdb3952bc52b824485085e7a2f78f31ae18bd48e8fb6d6121fcaa140335de5d",
        431,
    ),
    (
        "6f5d496f6380c0c71e81d7a65160fa17900f311b23b57a87761a4bf86940f0b4",
        "027502870da4e06e56aef5ca37b1577cf1f776dc60ca701b80db95e2686ce33b",
        "d4f0b198b0b2ddb72b744d8ef2fe2ab316dc0be77eae8cc61e3b337fb844a17a",
        418,
    ),
    (
        "44c054b3cd6bf99fb7ce49e2d378b4227b915e678fbc92bbecb03e20b45dc37d",
        "18b4efe0b94c4c2402877a1771a923114fc0a780e27cb88a6715f5a04ba15148",
        "ece468bbccbc6cabef3203e3474b4b0523014368b8714ce544848346d28e1a6e",
        482,
    ),
    (
        "83dfc6a6161a7903a96c1a0a621f26e1a6f4bcbced44636505434a28c7d0949b",
        "11d908f358e6ceea85dc7395edc019f54b9eaf74ccce6e9c188c5e411c5784b0",
        "0995a3c402c6c3cee26fb948b4ad89d851afb4c7464ded238cdb9cfd301313c3",
        451,
    ),
    (
        "d7124d90bbd7589a188bace72c7d93f0f5359dc37ed2807dab67e8d911084d06",
        "97079b6933f625e435c748773e941127c6b36deaa338ec53354537813c4ac969",
        "5c4960a8164bc48aa2ebaee92d4ed399762bbe5de224da5fb63813bdb0842170",
        478,
    ),
)
_S16_FIXED = frozenset(
    "shape source query from select window order by lag lead mysql table"
    " Int Bool Text Decimal Float None".split()
)
# Per slice: its forms and its keywords, the words of its forms that are no
# names there (S08's: S16's and its own); another slice's keywords stay names.
SLICES = (
    (range(3), _S16_FIXED),
    (
        range(3, 6),
        frozenset(
            "shape source query from select group by sum for in if all any unique"
            " mysql table Int Bool Text Decimal Float None".split()
        ),
    ),
    (
        range(6, 17),
        _S16_FIXED
        | frozenset(
            "count min max partition between preceding and current row let group"
            " qualify inner join on Timestamp Date UUID".split()
        ),
    ),
)
# re.ASCII: IGNORECASE alone lets the Kelvin sign match k (D77.36 ASCII names).
_NAME = re.compile(r"(?!__pietto)[A-Za-z_][A-Za-z0-9_]{0,62}", re.ASCII | re.IGNORECASE)
# The frame keyword `rows` (group 2) is no name, unlike the forms' source `rows`;
# no S16 or S10 form has a frame, so no such statement with one pairs either way.
_TOKEN = re.compile(
    r'(?<=mysql\.table\()"([^"\\\n]*)"|"(?:[^"\\\n]|\\.)*"|(rows)(?= between )|[^\W\d]\w*'
)
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
    """Names by kind in order of first use; `valid` once every one is a name.
    A name equal ignoring case to an earlier one of its kind also names that
    one, so a renaming keeps which names MySQL may fold together."""

    def __init__(self):
        self.seen, self.folded, self.valid = {}, {}, True

    def __call__(self, kind, name):
        if type(name) is not str:
            raise TypeError("name")
        if (kind, name) not in self.seen:
            parts = name[:-7].split(".") if kind == "M" else name.split(".")
            self.valid &= (
                (name.endswith(".pietto") if kind == "M" else True)
                and len(parts) == (2 if kind == "L" else 1)
                and all(_NAME.fullmatch(part) for part in parts)
            )
            count = sum(seen[0] == kind for seen in self.seen)
            first = self.folded.setdefault((kind, name.lower()), count)
            twin = "" if first == count else f"~{first}"
            self.seen[kind, name] = f"\0{kind}{count}{twin}\0"
        return self.seen[kind, name]


def _module(text, names, fixed):
    def token(match):
        if match[1] is not None:
            return '"' + names("L", match[1]) + '"'
        if match[2] is not None or match[0][0] == '"' or match[0] in fixed:
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


def _form(column, text, names, forms=range(len(FORMS))):
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    for index in forms:
        if FORMS[index][column] == digest:
            return index if names.valid else None
    return None


def project_text(path, source, contract, selected, names, fixed):
    """One module's bytes, its contract and its selected (name, kind), names
    and `fixed`, one slice's keywords, aside."""
    return "\0".join(
        (
            names("M", path),
            _module(source, names, fixed),
            _contract(contract, names),
            names("N", selected[0]),
            selected[1],
        )
    )


def project_form(request):
    """The paired form the selected statement of this project request is, or None."""
    if rows.AS_MAIN.get() or request.family != "mysql":
        return None
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
        for forms, fixed in SLICES:
            names = _Names()
            text = project_text(
                snapshot.path,
                snapshot.source_text,
                request.accepted_bytes,
                (owner.declared_name, owner.declaration_kind.value),
                names,
                fixed,
            )
            form = _form(0, text, names, forms)
            if form is not None:
                return form
    except (ValueError, TypeError, LookupError, AttributeError, RecursionError):
        return None
    return None


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
    if rows.AS_MAIN.get() or not any(len(records) == form[3] for form in FORMS):
        return None
    names = _Names()
    try:
        # Loading asks before any check, so even the digest's UTF-8 may fail.
        return _form(2, compiled_text(records, names), names)
    except (ValueError, TypeError, LookupError, AttributeError, RecursionError):
        return None
