"""Closed Phase67 fixture/captured-receipt consumers; no database acquisition."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import struct
import sys
from typing import Any

FORMAT = "pietto.phase67-consumer-integration.v1"
MAX_REPORT = 2 * 1024 * 1024
RECIPES = (
    ("G_emission_table_bag", "bag"),
    ("H_emission_query_bag", "bag"),
    ("I_emission_table_empty", "empty"),
    ("J_emission_query_empty", "empty"),
)
CELLS = tuple(
    (target, case, variant)
    for target in ("postgres", "mysql")
    for case, variant in RECIPES
)
GROUPS = (
    "integration_producer_correspondence",
    "integration_rows_consumer",
    "integration_arrow_consumer",
    "integration_ipc_consumer",
    "integration_relocated_process",
    "integration_terminal_failures",
    "integration_authority_refusals",
    "integration_report_integrity",
)
HELPERS = (
    "_pietto_target_conformance_resources",
    "_pietto_mysql_native_prepared",
    "_pietto_phase66_sql_emission_probe",
    "_pietto_target_conformance_cases",
    "_pietto_phase67_result_product_probe",
    "_pietto_phase67_whole_result_probe",
)
LABELS = ("display_text", "record_id", "active", "amount", "ratio")
TYPES = ("string", "int64", "bool", "decimal128(9, 2)", "double")
NULLABLE = (False, False, True, False, False)


def helpers() -> tuple[Any, Any, Any]:
    """Load only these exact test helpers; never put the checkout on sys.path."""
    for name in HELPERS:
        path = Path(__file__).with_name(name + ".py").resolve()
        if name in sys.modules:
            filename = sys.modules[name].__file__
            if filename is None or Path(filename).resolve() != path:
                raise ValueError("foreign test helper")
            continue
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return (sys.modules[HELPERS[2]], sys.modules[HELPERS[3]], sys.modules[HELPERS[4]])


def key(cell):
    return "/".join(cell)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=True, allow_nan=False
    ).encode()


def decode_scalar(value):
    if type(value) is not dict or type(value.get("kind")) is not str:
        raise ValueError("scalar record")
    kind = value["kind"]
    if kind == "null" and set(value) == {"kind"}:
        return None
    if set(value) != {"kind", "value"}:
        raise ValueError("scalar fields")
    raw = value["value"]
    if kind == "bool" and type(raw) is bool:
        return raw
    if kind == "text" and type(raw) is str and len(raw.encode("utf-8")) <= 4096:
        return raw
    if type(raw) is not str or len(raw) > 4096:
        raise ValueError("scalar encoding")
    if kind == "int" and len(raw) <= 32 and re.fullmatch(r"0|-?[1-9][0-9]*", raw):
        return int(raw)
    if kind == "bytes" and re.fullmatch(r"(?:[0-9a-f]{2})*", raw):
        return bytes.fromhex(raw)
    if kind == "float" and len(raw) <= 32:
        try:
            floating_value = float.fromhex(raw)
        except ValueError:
            raise ValueError("float encoding") from None
        if math.isfinite(floating_value) and floating_value.hex() == raw:
            return floating_value
    if kind == "decimal" and len(raw) <= 40:
        try:
            decimal_value = Decimal(raw)
        except InvalidOperation:
            raise ValueError("decimal encoding") from None
        if decimal_value.is_finite() and str(decimal_value) == raw:
            return decimal_value
    raise ValueError("unknown or malformed scalar")


def decode_rows(rows):
    if type(rows) is not list or len(rows) > 32:
        raise ValueError("row extent")
    if any(type(row) is not list or len(row) != 5 for row in rows):
        raise ValueError("row arity")
    return [[decode_scalar(value) for value in row] for row in rows]


def supplied_rows(target, empty=False):
    if empty:
        return []
    true, false = (True, False) if target == "postgres" else (1, 0)
    first = ["trail 😀  ", 9007199254740993, true, Decimal("12.30"), -0.0]
    return [
        first[:],
        first[:],
        ["A", 0, false, Decimal("0.00"), 1.5],
        ["a ", 1, None, Decimal("-0.01"), 0.0],
    ]


def fixture_tags(target, empty=False):
    # This independently authored Phase66 oracle is never a receipt-mode input.
    return helpers()[1].emission_rows(target, empty=empty)


def snapshot_expected(tags, target) -> dict[str, Any]:
    rows = []
    for row in tags:
        if type(row) is not list or len(row) != 5:
            raise ValueError("oracle row arity")
        text_tag, int_tag, bool_tag, decimal_tag, float_tag = row
        if [v.get("kind") for v in (text_tag, int_tag, decimal_tag, float_tag)] != [
            "text",
            "int",
            "decimal",
            "float",
        ]:
            raise ValueError("oracle typed observation")
        boolean = None if bool_tag == {"kind": "null"} else bool_tag["value"]
        if boolean is not None and target == "mysql":
            if bool_tag.get("kind") != "int" or boolean not in ("0", "1"):
                raise ValueError("oracle MySQL Bool carrier")
            boolean = {"0": 0, "1": 1}[boolean]
        elif boolean is not None and bool_tag.get("kind") != "bool":
            raise ValueError("oracle PostgreSQL Bool carrier")
        rows.append(
            [
                text_tag["value"],
                int(int_tag["value"]),
                boolean,
                Decimal(decimal_tag["value"]),
                float.fromhex(float_tag["value"]),
            ]
        )
    values = []
    for text, integer, boolean, decimal, floating in rows:
        if (
            type(text) is not str
            or type(integer) is not int
            or type(decimal) is not Decimal
            or type(floating) is not float
        ):
            raise ValueError("five-column carriers")
        if boolean is not None:
            if target == "postgres":
                if type(boolean) is not bool:
                    raise ValueError("PostgreSQL Bool carrier")
            elif type(boolean) is not int or boolean not in (0, 1):
                raise ValueError("MySQL Bool carrier")
            else:
                boolean = {0: False, 1: True}[boolean]
        sign, digits, exponent = decimal.as_tuple()
        coefficient = int("".join(map(str, digits))) * (-1 if sign else 1)
        if type(exponent) is not int or exponent < -2:
            raise ValueError("Decimal scale")
        coefficient *= 10 ** (exponent + 2)
        values.append(
            [
                text.encode().hex(),
                integer,
                boolean,
                str(coefficient),
                struct.pack(">d", floating).hex(),
            ]
        )
    return dict(
        fields=[
            dict(ordinal=i, label=label, type=kind, nullable=nullable, metadata=None)
            for i, (label, kind, nullable) in enumerate(
                zip(LABELS, TYPES, NULLABLE, strict=True)
            )
        ],
        rows=values,
        valid=[[v is not None for v in row] for row in values],
        schema_metadata=None,
    )


def metadata_fixture(target):
    types = [25, 20, 16, 1700, 701] if target == "postgres" else [253, 8, 1, 246, 5]
    if target == "postgres":
        return [
            [
                label,
                code,
                None,
                None,
                9 if i == 3 else None,
                2 if i == 3 else None,
                None,
            ]
            for i, (label, code) in enumerate(zip(LABELS, types, strict=True))
        ]
    return [
        [
            label,
            code,
            None,
            None,
            None,
            None,
            int(NULLABLE[i]),
            0,
            309 if i == 0 else 63,
        ]
        for i, (label, code) in enumerate(zip(LABELS, types, strict=True))
    ]


def producer_observations(target, metadata, recipe):
    from pietto._project.project_result_binding import (
        ProducerObservation,
        TextObservation,
        DecimalObservation,
    )

    if (
        target not in ("postgres", "mysql")
        or type(metadata) is not list
        or len(metadata) != 5
    ):
        raise ValueError("protocol metadata denominator/target")
    codes = [25, 20, 16, 1700, 701] if target == "postgres" else [253, 8, 1, 246, 5]
    descriptions = json.loads(recipe["contract"])["sources"][0]["fields"]
    if json.loads(recipe["contract"])["target"]["family"] != target:
        raise ValueError("producer target")
    observations = []
    for ordinal, (metadata_column, source_ordinal) in enumerate(
        zip(metadata, (2, 0, 1, 3, 4), strict=True)
    ):
        if (
            type(metadata_column) is not list
            or len(metadata_column) != (7 if target == "postgres" else 9)
            or type(metadata_column[0]) is not str
            or type(metadata_column[1]) is not int
            or metadata_column[:2] != [LABELS[ordinal], codes[ordinal]]
        ):
            raise ValueError("protocol ordinal/label/type")
        nullable = metadata_column[6]
        if target == "postgres":
            if nullable is not None or (
                ordinal == 3 and metadata_column[4:6] != [9, 2]
            ):
                raise ValueError("PostgreSQL protocol facts")
        else:
            if (
                type(nullable) is not int
                or nullable not in (0, 1)
                or metadata_column[8] != (309 if ordinal == 0 else 63)
            ):
                raise ValueError("MySQL protocol facts")
            nullable = {0: False, 1: True}[nullable]
        representation = descriptions[source_ordinal]["representation"]
        storage, domain = representation["storage"], representation["domain"]
        details: dict[str, Any] = {}
        if ordinal == 0:
            details = dict(
                domain="text",
                carrier="str",
                text=TextObservation(
                    domain["max_characters"],
                    domain["encoding"],
                    domain["collation"],
                    domain["padding"],
                    storage.get("length"),
                ),
            )
        elif ordinal == 1:
            details = dict(lower=int(domain["min"]), upper=int(domain["max"]))
        elif ordinal == 2:
            details = dict(
                domain="bool01", carrier="bool" if target == "postgres" else "int01"
            )
        elif ordinal == 3:
            details = dict(
                domain="decimal",
                carrier="decimal",
                decimal=DecimalObservation(domain["precision"], domain["scale"]),
            )
        else:
            details = dict(domain="finite_float", carrier="float")
        observations.append(
            ProducerObservation(
                ordinal,
                metadata_column[0],
                target,
                storage["kind"],
                protocol_nullable=nullable,
                **details,
            )
        )
    return tuple(observations)


def build(cell, directory, metadata=None):
    from pietto._project import project_result_contract as contract_api
    from pietto._project import project_result_binding as producer_api
    from pietto._project import project_arrow_result as arrow_api
    from pietto._project.project_sql_emission import serialize_project_sql_emission

    emission, _, _ = helpers()
    target, case, variant = cell
    recipe = emission.fixture(target, case, variant)
    checked, outcome = emission.build_case(directory, **recipe)
    if outcome.status != "VERIFIED" or outcome.artifact is None:
        raise ValueError("required integration recipe is not admitted")
    public = serialize_project_sql_emission(outcome)
    document = emission.decode_public(public)
    contract = contract_api.build_result_contract(checked)
    observed = producer_observations(
        target, metadata if metadata is not None else metadata_fixture(target), recipe
    )
    producer = producer_api.bind_producer(contract, outcome.artifact, observed)
    binding = arrow_api.bind_arrow(producer)
    return (
        checked,
        outcome.artifact,
        contract,
        producer,
        binding,
        recipe,
        public,
        document,
    )


def independent_batch(rows, target):
    pa = __import__("pyarrow")

    columns = [[] for _ in range(5)]
    for row in rows:
        for i, value in enumerate(row):
            if i == 2 and value is not None and target == "mysql":
                if type(value) is not int or value not in (0, 1):
                    raise ValueError("MySQL Bool carrier")
                value = {0: False, 1: True}[value]
            columns[i].append(value)
    types = (pa.string(), pa.int64(), pa.bool_(), pa.decimal128(9, 2), pa.float64())
    schema = pa.schema(
        [
            pa.field(label, kind, nullable=nullable)
            for label, kind, nullable in zip(LABELS, types, NULLABLE, strict=True)
        ]
    )
    return pa.RecordBatch.from_arrays(
        [
            pa.array(values, type=kind)
            for values, kind in zip(columns, types, strict=True)
        ],
        schema=schema,
    )


def check_snapshot(snapshot, expected):
    if canonical(snapshot) != canonical(expected):
        raise ValueError("original-value correspondence")


def consume(cell, built, rows, tags):
    pa = __import__("pyarrow")
    from pietto._project import project_result_ingress as ingress
    from pietto._project import project_result_ipc as ipc

    product = helpers()[2]
    binding = built[4]
    expected = snapshot_expected(tags, cell[0])
    managed = ingress.ingest_rows(binding, rows)
    try:
        delivered = pa.record_batch(managed)
        row_snapshot = product.finite_snapshot(delivered)
        check_snapshot(row_snapshot, expected)
    finally:
        managed.close()
    batch = independent_batch(rows, cell[0])
    check_snapshot(product.finite_snapshot(batch), expected)
    batches = (
        [batch.slice(0, 0), batch.slice(0, 1), batch.slice(0, 0), batch.slice(1)]
        if rows
        else [batch]
    )
    from pietto._project import project_result_reader as readers

    with product.ReaderTrace(batch.schema, batches) as trace:
        session = ingress.ingest_reader(binding, trace.source, expected_rows=len(rows))
        native = pa.RecordBatchReader.from_stream(session)
        competing = product.refused(session._reader.read_next_batch)
        try:
            snapshots = [product.finite_snapshot(part) for part in native]
            before = [session.state, session._reader.state]
        finally:
            native.close()
            after_foreign = session._reader.state
            session.close()
        readers.verify_finite_completion(
            session._reader, session._reader.expectation, session.input_completion
        )
        stream = dict(
            before=before,
            after=[session.state, session._reader.state],
            after_foreign=after_foreign,
            source_complete=session.input_completion is not None,
            chunks=[len(x["rows"]) for x in snapshots],
            rows=[r for x in snapshots for r in x["rows"]],
            snapshots=snapshots,
            error=None,
            foreign_error=None,
            source_rows=session._reader.rows,
            competing=competing,
            closes=trace.closes,
            reads=trace.reads,
            route="raw",
            pre_read=0,
            provider_calls=0,
        )
    frame = ipc.encode_ipc(
        binding,
        pa.RecordBatchReader.from_batches(batch.schema, batches),
        expected_rows=len(rows),
    )
    decoded = product.ipc_decode_observation(binding, frame, len(rows))
    check_snapshot(
        dict(
            expected,
            rows=decoded["rows"],
            valid=[v for snap in decoded["snapshots"] for v in snap["valid"]],
        ),
        expected,
    )
    if (
        stream["after"] != ["CLOSED", "COMPLETE"]
        or not stream["source_complete"]
        or not decoded["ipc_complete"]
    ):
        raise ValueError("required conditional completion missing")
    return dict(rows=row_snapshot, arrow=stream, ipc=decoded)


def association(cell, recipe, public):
    return dict(
        target=cell[0],
        case=cell[1],
        variant=cell[2],
        policy=recipe["policy"],
        source_sha256=digest(recipe["source"].encode()),
        contract_sha256=digest(recipe["contract"].encode()),
        public=public.decode(),
        public_sha256=digest(public),
    )


def verify_association(cell, value):
    emission = helpers()[0]
    recipe = emission.fixture(*cell)
    if set(value) != {
        "target",
        "case",
        "variant",
        "policy",
        "source_sha256",
        "contract_sha256",
        "public",
        "public_sha256",
    }:
        raise ValueError("integration association fields")
    data = value["public"].encode()
    if value != association(cell, recipe, data):
        raise ValueError("integration source/contract/case association")
    document = emission.decode_public(data)
    source = recipe["source"].encode()
    kind = "table" if cell[1] in (RECIPES[0][0], RECIPES[2][0]) else "query"
    request: dict[str, Any] = dict(
        owner=dict(module="main.pietto", kind=kind, name="result"),
        sources=[
            dict(module="main.pietto", sha256=digest(source), byte_count=len(source))
        ],
        contract=json.loads(recipe["contract"]),
        literal_policy=recipe["policy"],
    )
    if document["status"] != "VERIFIED" or document["request"] != request:
        raise ValueError("integration public request")
    if document["target"]["family"] != cell[0] or [
        c["label"] for c in document["columns"]
    ] != list(LABELS):
        raise ValueError("integration public producer columns")
    for ordinal, source_ordinal in enumerate((2, 0, 1, 3, 4)):
        col = document["columns"][ordinal]
        declared = request["contract"]["sources"][0]["fields"][source_ordinal]
        if (
            col["ordinal"] != ordinal
            or col["correspondence"]["field"] != source_ordinal
            or col["representation"] != declared["representation"]
        ):
            raise ValueError("integration field correspondence")
    return document


def verify_routes(cell, result, tags):
    expected = snapshot_expected(tags, cell[0])
    if set(result) != {"rows", "arrow", "ipc"}:
        raise ValueError("integration route denominator")
    check_snapshot(result["rows"], expected)
    counts = [0, 1, 0, 3] if tags else [0]
    product = helpers()[2]
    stream = result["arrow"]
    if set(stream) != {
        "before",
        "after",
        "after_foreign",
        "source_complete",
        "chunks",
        "rows",
        "error",
        "foreign_error",
        "source_rows",
        "competing",
        "closes",
        "reads",
        "route",
        "pre_read",
        "provider_calls",
        "snapshots",
    }:
        raise ValueError("integration stream fields")
    expected_lifecycle = product.interop_stream_expected(
        [(n, 0, 0) for n in counts], expected["rows"]
    )
    for field in (
        "before",
        "after",
        "after_foreign",
        "source_complete",
        "chunks",
        "rows",
        "error",
        "foreign_error",
        "source_rows",
        "competing",
        "closes",
        "reads",
    ):
        if canonical(stream[field]) != canonical(expected_lifecycle[field]):
            raise ValueError("integration stream lifecycle/values")
    if (stream.get("route"), stream.get("pre_read"), stream.get("provider_calls")) != (
        "raw",
        0,
        0,
    ):
        raise ValueError("integration independent reader route")
    decoded = result["ipc"]
    if set(decoded) != {
        "declared_rows",
        "chunks",
        "snapshots",
        "rows",
        "reads",
        "closes",
        "errors",
        "foreign_error",
        "ipc_complete",
        "receipt_identity",
        "source_complete",
        "state",
    }:
        raise ValueError("integration IPC fields")
    for field, wanted in dict(
        declared_rows=len(tags),
        chunks=counts,
        rows=expected["rows"],
        reads=len(counts) + 1,
        closes=1,
        errors=[],
        foreign_error=None,
        ipc_complete=True,
        receipt_identity=True,
        source_complete=True,
        state="CLOSED",
    ).items():
        if canonical(decoded[field]) != canonical(wanted):
            raise ValueError("integration IPC values/completion")
    for route in (stream, decoded):
        if len(route["snapshots"]) != len(counts):
            raise ValueError("integration chunk denominator")
        offset = 0
        for size, snapshot in zip(counts, route["snapshots"], strict=True):
            check_snapshot(
                snapshot,
                dict(
                    expected,
                    rows=expected["rows"][offset : offset + size],
                    valid=expected["valid"][offset : offset + size],
                ),
            )
            offset += size


def origin_observation() -> dict[str, Any]:
    import importlib.metadata
    import urllib.parse
    import zipfile

    distribution = importlib.metadata.distribution("pietto")
    direct = json.loads(distribution.read_text("direct_url.json") or "null")
    url = urllib.parse.urlparse(direct["url"])
    if (
        url.scheme != "file"
        or url.netloc
        or distribution.version != "0.1.0"
        or sorted(distribution.metadata.get_all("Provides-Extra") or ())
        != ["arrow", "execute-mysql", "execute-postgres", "execute-postgres-adbc"]
    ):
        raise ValueError("candidate distribution identity")
    wheel = Path(urllib.parse.unquote(url.path)).resolve()
    if wheel.suffix != ".whl" or importlib.metadata.version("pyarrow") != "25.0.1":
        raise ValueError("candidate wheel/Arrow pin")
    prefix = Path(sys.prefix).resolve()
    origins = {}
    with zipfile.ZipFile(wheel) as archive:
        for name, module in tuple(sys.modules.items()):
            if name == "pietto" or name.startswith("pietto."):
                filename = module.__file__
                if filename is None:
                    raise ValueError("missing production module file")
                path = Path(filename).resolve()
                if not path.is_relative_to(prefix) or "site-packages" not in path.parts:
                    raise ValueError("checkout production import")
                member = "/".join(path.parts[path.parts.index("site-packages") + 1 :])
                if path.read_bytes() != archive.read(member):
                    raise ValueError("installed wheel bytes")
                origins[name] = dict(
                    path=str(path), member=member, sha256=digest(path.read_bytes())
                )
    pa = __import__("pyarrow")
    arrow_path = Path(pa.__file__).resolve()
    if not arrow_path.is_relative_to(prefix) or "site-packages" not in arrow_path.parts:
        raise ValueError("foreign Arrow origin")
    return dict(
        prefix=str(prefix),
        wheel=dict(path=str(wheel), sha256=digest(wheel.read_bytes())),
        pyarrow=dict(version=pa.__version__, path=str(arrow_path)),
        origins=origins,
    )


def input_closure(repository):
    paths = list((repository / "src/pietto").rglob("*.py"))
    paths += [
        repository / "tests" / (name + ".py")
        for name in (*HELPERS, "_pietto_phase67_real_consumer_probe")
    ]
    paths += [
        repository / name
        for name in (
            "pyproject.toml",
            "uv.lock",
            "scripts/package_smoke.py",
            "ci/phase67-arrow-compatibility-requirements.txt",
        )
    ]
    return {
        p.relative_to(repository).as_posix(): digest(p.read_bytes())
        for p in sorted(paths)
    }


def verify_origins(value, inputs):
    if set(value) != {"prefix", "wheel", "pyarrow", "origins"}:
        raise ValueError("integration origin envelope")
    prefix = Path(value["prefix"])
    if (
        not prefix.is_absolute()
        or ".." in prefix.parts
        or set(value["wheel"]) != {"path", "sha256"}
    ):
        raise ValueError("integration origin prefix/wheel")
    if not re.fullmatch("[0-9a-f]{64}", value["wheel"]["sha256"]) or not value["wheel"][
        "path"
    ].endswith(".whl"):
        raise ValueError("integration wheel identity")
    required = {
        "pietto",
        "pietto._project.project_result_contract",
        "pietto._project.project_result_binding",
        "pietto._project.project_arrow_result",
        "pietto._project.project_result_reader",
        "pietto._project.project_arrow_interop",
        "pietto._project.project_result_ingress",
        "pietto._project.project_result_ipc",
    }
    if not required <= set(value["origins"]):
        raise ValueError("integration origin denominator")
    for name, origin in value["origins"].items():
        path = Path(origin["path"])
        if (
            set(origin) != {"path", "member", "sha256"}
            or not path.is_relative_to(prefix)
            or ".." in path.parts
            or not origin["path"].endswith("/site-packages/" + origin["member"])
            or origin["member"]
            not in (
                name.replace(".", "/") + ".py",
                name.replace(".", "/") + "/__init__.py",
            )
            or inputs.get("src/" + origin["member"]) != origin["sha256"]
        ):
            raise ValueError("integration installed origin")
    arrow = value["pyarrow"]
    if (
        set(arrow) != {"version", "path"}
        or arrow["version"] != "25.0.1"
        or not Path(arrow["path"]).is_relative_to(prefix)
        or not arrow["path"].endswith("/site-packages/pyarrow/__init__.py")
    ):
        raise ValueError("integration Arrow origin")


def run_fixture_cells(root, selected=CELLS):
    cells = {}
    built = {}
    for cell in selected:
        item = build(cell, root / cell[0] / cell[1])
        tags = fixture_tags(cell[0], cell[2] == "empty")
        routes = consume(cell, item, supplied_rows(cell[0], cell[2] == "empty"), tags)
        verify_routes(cell, routes, tags)
        cells[key(cell)] = dict(
            association=association(cell, item[5], item[6]),
            metadata=metadata_fixture(cell[0]),
            routes=routes,
        )
        built[key(cell)] = item
    return cells, built


def relocated_child(source_root):
    cells = {}
    for cell in CELLS:
        if cell[1] not in (RECIPES[0][0], RECIPES[2][0]):
            continue
        original = source_root / cell[0] / cell[1] / "main.pietto"
        recipe = helpers()[0].fixture(*cell)
        if original.read_text() != recipe["source"]:
            raise ValueError("relocated source bytes")
        # Existing builder reads and reopens these exact moved source bytes in this child.
        item = build(cell, original.parent)
        tags = fixture_tags(cell[0], cell[2] == "empty")
        routes = consume(cell, item, supplied_rows(cell[0], cell[2] == "empty"), tags)
        cells[key(cell)] = dict(
            association=association(cell, item[5], item[6]),
            metadata=metadata_fixture(cell[0]),
            routes=routes,
        )
    return dict(
        cells=cells,
        installation=origin_observation(),
        source_root=str(source_root.resolve()),
        child_pid=__import__("os").getpid(),
    )


def run_relocated(root, parent_cells):
    import os
    import shutil
    import subprocess

    incoming, moved, helper_dir = (
        root / "relocation-input",
        root / "relocated",
        root / "copied-helpers",
    )
    incoming.mkdir()
    helper_dir.mkdir()
    for cell in CELLS:
        if cell[1] in (RECIPES[0][0], RECIPES[2][0]):
            destination = incoming / cell[0] / cell[1]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(root / cell[0] / cell[1], destination)
    shutil.move(incoming, moved)
    for name in (*HELPERS, "_pietto_phase67_real_consumer_probe"):
        original = Path(__file__).with_name(name + ".py")
        copied = helper_dir / original.name
        copied.write_bytes(original.read_bytes())
        if copied.read_bytes() != original.read_bytes():
            raise ValueError("copied helper bytes")
    output = root / "relocated-report.json"
    environment = os.environ.copy()
    for name in ("PYTHONPATH", "PYTHONHOME"):
        environment.pop(name, None)
    command = [
        sys.executable,
        "-I",
        str(helper_dir / Path(__file__).name),
        "child",
        "--source-root",
        str(moved),
        "--report",
        str(output),
    ]
    result = subprocess.run(
        command, cwd=root, env=environment, capture_output=True, text=True
    )
    if result.returncode:
        raise ValueError("relocated child failed: " + result.stderr[-2000:])
    value = json.loads(output.read_bytes())
    if (
        value["child_pid"] == os.getpid()
        or incoming.exists()
        or value["source_root"] != str(moved.resolve())
    ):
        raise ValueError("relocated process identity")
    for name, cell in value["cells"].items():
        if canonical(cell) != canonical(parent_cells[name]):
            raise ValueError("relocated complete observation drift")
    return value


def terminal_controls(binding, batch):
    import copy
    from pietto._project import project_result_ingress as ingress
    from pietto._project import project_result_ipc as ipc

    pa = __import__("pyarrow")
    product = helpers()[2]
    result: dict[str, Any] = {}
    for name, options in (
        ("late_input", dict(late=True)),
        ("early_close", dict(early=True)),
        ("cleanup", dict(close_error=RuntimeError("injected cleanup"))),
    ):
        observed = product.interop_stream(binding, [batch], 4, route="raw", **options)
        result[name] = {
            k: observed[k]
            for k in ("before", "after", "source_complete", "error", "closes", "reads")
        }
    session = ingress.ingest_reader(
        binding,
        pa.RecordBatchReader.from_batches(batch.schema, [batch]),
        expected_rows=4,
    )
    native = pa.RecordBatchReader.from_stream(session)
    native.read_next_batch()
    observed_rows = session._reader.rows
    observed_completion = session.input_completion is not None
    native.close()
    session.close()
    result["count_before_eof"] = dict(
        rows=observed_rows, completion=observed_completion, state=session.state
    )
    session = ingress.ingest_reader(
        binding,
        pa.RecordBatchReader.from_batches(batch.schema, [batch]),
        expected_rows=4,
    )
    native = pa.RecordBatchReader.from_stream(session)
    try:
        with session:
            list(native)
            raise RuntimeError("injected consumer after source EOF")
    except Exception as error:
        result["consumer"] = dict(
            errors=product.ipc_error_tags(error),
            input_complete=session.input_completion is not None,
            state=session.state,
        )
    finally:
        native.close()
        session.close()
    from unittest.mock import patch
    from pietto._project import project_arrow_interop as interop

    primary, cleanup = ValueError("injected primary"), RuntimeError("injected cleanup")
    original_close = interop._close_bridge
    cleanup_calls = 0

    def failing_close(bridge):
        nonlocal cleanup_calls
        cleanup_calls += 1
        original_close(bridge)
        raise cleanup

    session = ingress.ingest_reader(
        binding,
        pa.RecordBatchReader.from_batches(batch.schema, [batch]),
        expected_rows=4,
    )
    native = pa.RecordBatchReader.from_stream(session)
    try:
        with patch.object(interop, "_close_bridge", failing_close):
            with session:
                list(native)
                raise primary
    except BaseException as error:
        result["primary_cleanup"] = dict(
            errors=product.ipc_error_tags(error),
            primary_identity=session.primary_error is primary,
            cleanup_identity=session.cleanup_errors == (cleanup,),
            input_complete=session.input_completion is not None,
            state=session.state,
            cleanup_calls=cleanup_calls,
        )
    finally:
        native.close()
        session.close()
    for name, options in (
        ("writer", dict(write_error=True)),
        ("writer_finalize", dict(finalize_error=True)),
    ):
        frame, observed = product.ipc_encode_observation(binding, [batch], 4, **options)
        result[name] = dict(
            errors=observed["errors"],
            published_bytes=observed["published_bytes"],
            frame_returned=frame is not None,
        )
    frame = ipc.encode_ipc(
        binding,
        pa.RecordBatchReader.from_batches(batch.schema, [batch]),
        expected_rows=4,
    )
    prefix = frame[100:-8]
    with pa.ipc.open_stream(prefix) as source:
        sdk_rows = sum(b.num_rows for b in source)
    result["truncated_prefix"] = dict(
        sdk_rows=sdk_rows,
        rejection=product.refused(
            lambda: ipc.open_ipc(binding, frame[:-8], expected_rows=4)
        ),
    )
    managed = ingress.ingest_batch(binding, batch)
    grant = managed.transfer()
    result["copied_grant"] = product.refused(
        lambda: copy.copy(grant).__arrow_c_array__()
    )
    pa.record_batch(grant)
    result["spent_grant"] = product.refused(grant.__arrow_c_array__)
    managed.close()
    session = ipc.open_ipc(binding, frame, expected_rows=4)
    result["copied_session"] = product.refused(
        lambda: copy.copy(session).__arrow_c_stream__()
    )
    session.close()
    result["incomplete_ipc"] = product.refused(
        lambda: ipc.verify_ipc_completion(session)
    )
    return result


def authority_controls(root, built):
    from dataclasses import replace
    from pietto._project import project_result_binding as producer_api
    from pietto._project import project_result_contract as contract_api
    from pietto._project import project_result_ingress as ingress

    product = helpers()[2]
    checked, artifact, contract, producer, binding, recipe, _, _ = built
    observations = tuple(field.observation for field in producer.fields)
    result: dict[str, Any] = {}
    for name, changed in (
        ("ordinal", replace(observations[0], ordinal=1)),
        ("label", replace(observations[0], label="wrong")),
        ("target", replace(observations[0], family="mysql")),
        ("protocol_type", replace(observations[0], storage="pg_int8")),
    ):
        result[name] = product.refused(
            lambda changed=changed: producer_api.bind_producer(
                contract, artifact, (changed, *observations[1:])
            )
        )
    bad = list(observations)
    bad[1] = replace(bad[1], storage="pg_int2")
    result["widening_cannot_repair"] = product.refused(
        lambda: producer_api.bind_producer(contract, artifact, tuple(bad))
    )
    foreign = build(("postgres", RECIPES[0][0], "bag"), root / "foreign")
    result["foreign_root"] = product.refused(
        lambda: contract_api.verify_result_contract(contract, foreign[0])
    )
    rows = supplied_rows("postgres")
    rows[0][0] = None
    result["logical_null"] = product.refused(lambda: ingress.ingest_rows(binding, rows))
    mysql = build(("mysql", RECIPES[0][0], "bag"), root / "mysql-refusal")
    rows = supplied_rows("mysql")
    rows[0][2] = True
    result["mysql_bool"] = product.refused(lambda: ingress.ingest_rows(mysql[4], rows))
    emission = helpers()[0]
    result["upstream"] = {}
    for variant in ("decimal_mismatch", "timestamp_meaning", "uuid_meaning"):
        case = "L_emission_blocked"
        recipe = emission.fixture("postgres", case, variant)
        _, outcome = emission.build_case(root / variant, **recipe)
        from pietto._project.project_sql_emission import serialize_project_sql_emission

        doc = emission.decode_public(serialize_project_sql_emission(outcome))
        result["upstream"][variant] = dict(
            status=outcome.status,
            artifact=outcome.artifact is not None,
            diagnostics=[
                [v["code"], v["reason"], v["subject"]["detail"]]
                for v in doc["blockers"]
            ],
        )
    return result


def value_controls(root, built):
    from unittest.mock import patch
    from pietto._project import project_arrow_interop as interop
    from pietto._project import project_result_ingress as ingress
    from pietto._project import project_result_contract as contract_api
    from pietto._project import project_result_binding as producer_api
    from pietto._project import project_arrow_result as arrow_api

    pa = __import__("pyarrow")
    product = helpers()[2]
    binding = built[4]
    expected = snapshot_expected(fixture_tags("postgres"), "postgres")
    original = interop._copy_batch

    def changed(batch, lease):
        delivered = original(batch, lease)
        arrays = list(delivered.columns)
        arrays[1] = pa.array([8, *arrays[1].to_pylist()[1:]], type=pa.int64())
        return pa.RecordBatch.from_arrays(arrays, schema=delivered.schema)

    with patch.object(interop, "_copy_batch", changed):
        managed = ingress.ingest_batch(
            binding, independent_batch(supplied_rows("postgres"), "postgres")
        )
        try:
            changed_snapshot = product.finite_snapshot(pa.record_batch(managed))
            try:
                check_snapshot(changed_snapshot, expected)
            except ValueError as error:
                rejection = str(error)
            else:
                raise AssertionError("actual value-changing delivery escaped oracle")
        finally:
            managed.close()
    # Existing two-Int fixture supplies the same-type-column negative unavailable
    # in the five distinct-type native corpus; this is not a native query addition.
    checked, artifact = product.build_source(root / "two-int-control", "postgres")
    contract = contract_api.build_result_contract(checked)
    producer = producer_api.bind_producer(
        contract, artifact, product.observations("postgres")
    )
    pair = arrow_api.bind_arrow(producer)
    swapped = pa.RecordBatch.from_arrays(
        [pa.array([2], type=pa.int64()), pa.array([1], type=pa.int64())],
        schema=pair.schema,
    )
    managed = ingress.ingest_batch(pair, swapped)
    try:
        swapped_rows = product.finite_snapshot(pa.record_batch(managed))["rows"]
    finally:
        managed.close()
    assert swapped_rows != [[1, 2]]
    from pietto._project import project_result_ipc as ipc

    lost_batch = independent_batch(supplied_rows("postgres")[1:], "postgres")
    frame = ipc.encode_ipc(
        binding,
        pa.RecordBatchReader.from_batches(lost_batch.schema, [lost_batch]),
        expected_rows=3,
    )
    lost = product.ipc_decode_observation(binding, frame, 3)
    compare_bag(lost["rows"], expected["rows"][1:])
    try:
        compare_bag(lost["rows"], expected["rows"])
    except ValueError as error:
        lost_rejection = str(error)
    else:
        raise AssertionError("lost duplicate escaped oracle")
    return dict(
        original=expected,
        changed=changed_snapshot,
        rejection=rejection,
        same_type=dict(input=[[1, 2]], delivered=swapped_rows),
        lost_duplicate=dict(
            rows=lost["rows"],
            declared_rows=3,
            original_rows=4,
            state=lost["state"],
            input_complete=lost["source_complete"],
            delivery_complete=lost["ipc_complete"],
            rejection=lost_rejection,
        ),
    )


def fixture_groups(root):
    cells, built = run_fixture_cells(root)
    selected = built[key(CELLS[0])]
    return {
        GROUPS[0]: {
            name: dict(association=value["association"], metadata=value["metadata"])
            for name, value in cells.items()
        },
        GROUPS[1]: {name: value["routes"]["rows"] for name, value in cells.items()},
        GROUPS[2]: {name: value["routes"]["arrow"] for name, value in cells.items()},
        GROUPS[3]: {name: value["routes"]["ipc"] for name, value in cells.items()},
        GROUPS[4]: run_relocated(root, cells),
        GROUPS[5]: terminal_controls(
            selected[4],
            independent_batch(supplied_rows("postgres"), "postgres"),
        ),
        GROUPS[6]: authority_controls(root, selected),
        GROUPS[7]: value_controls(root, selected),
    }


def selected_observations(receipts, context):
    """Supplement prior full strict verification; never claim to replace it."""
    result: dict[str, Any] = {}
    emission = helpers()[0]
    for target in ("postgres", "mysql"):
        receipt = receipts[target]
        if (
            receipt.get("format") != "pietto.target-conformance-receipt.v2"
            or receipt["commit"] != context["checkout"]
            or receipt["run_id"] != context["run_id"]
            or type(receipt["run_attempt"]) is not int
            or receipt["run_attempt"] != context["run_attempt"]
            or receipt["target"] != target
            or receipt["status"] != "success"
            or receipt["full_manifest"] is not True
            or receipt["failures"]
            or receipt["cleanup"]["status"] != "success"
            or receipt["cleanup"]["failures"]
        ):
            raise ValueError("receipt context/completion")
        for case, variant in RECIPES:
            matches = [c for c in receipt["cases"] if c["id"] == case]
            if len(matches) != 1:
                raise ValueError("receipt case denominator")
            selected = matches[0]
            if len(selected["variants"]) != 1 or len(selected["observations"]) != 1:
                raise ValueError("receipt selected observation denominator")
            record, observation = selected["variants"][0], selected["observations"][0]
            if (
                type(record["submission_before"]) is not int
                or type(record["submission_after"]) is not int
                or record["variant"] != variant
                or record["submission_after"] - record["submission_before"] != 1
            ):
                raise ValueError("receipt variant/submission")
            cell = (target, case, variant)
            recipe = emission.fixture(*cell)
            entry = dict(
                id=case,
                variant=variant,
                source_sha256=digest(recipe["source"].encode()),
                contract_sha256=digest(recipe["contract"].encode()),
                policy=recipe["policy"],
            )
            if [
                r
                for r in receipt["inputs"]["emission_inputs"][target]
                if r["id"] == case
            ] != [entry]:
                raise ValueError("receipt source/contract input")
            generated = [
                r
                for r in receipt["generation"]["emission"]["records"]
                if r["id"] == case and r["variant"] == variant
            ]
            if len(generated) != 1 or generated[0] != dict(
                id=case,
                variant=variant,
                source_sha256=entry["source_sha256"],
                contract_sha256=entry["contract_sha256"],
                public=record["public"],
                public_sha256=record["public_sha256"],
            ):
                raise ValueError("receipt generation/artifact association")
            association_value = association(cell, recipe, record["public"].encode())
            document = verify_association(cell, association_value)
            if record["public_sha256"] != association_value["public_sha256"]:
                raise ValueError("receipt public bytes")
            if (
                observation["sql"] != document["sql"]
                or observation["sql_sha256"] != digest(document["sql"].encode())
                or observation["parameters"] != []
                or observation["identity"] != "query"
                or observation["prepared"] is not True
                or observation["failures"]
                or any(
                    observation[name] != "success"
                    for name in ("status", "execute", "fetch", "close")
                )
            ):
                raise ValueError("captured execute/fetch/close/artifact")
            native = observation["native"]
            if target == "mysql":
                if (
                    not isinstance(native, dict)
                    or native["prepare"] != "success"
                    or native["terminal"]["kind"] != "rowset_eof"
                    or native["unread_final"] is not False
                    or native["close_send"] != "complete_no_ack"
                    or observation["api"] != "mysql.native-prepared.v1"
                ):
                    raise ValueError("captured native completion")
            elif native is not None or observation["api"] != "psycopg.RawCursor":
                raise ValueError("captured protocol identity")
            producer_observations(target, observation["metadata"], recipe)
            decode_rows(observation["rows"])
            # These are the actual execution values. The expected fixture is used
            # only by independent checking, never as the mapper's input.
            result[key(cell)] = dict(
                association=association_value,
                observation={
                    name: observation[name]
                    for name in (
                        "rows",
                        "metadata",
                        "execute",
                        "fetch",
                        "close",
                        "status",
                        "sql",
                        "parameters",
                    )
                },
                observation_sha256=digest(canonical(observation)),
            )
    return result


def receipt_files(directory, context):
    wanted = {
        f"phase66-{target}-{context['run_id']}-{context['run_attempt']}.json": target
        for target in ("postgres", "mysql")
    }
    found = list(directory.rglob("phase66-*.json"))
    if len(found) != 2 or {p.name for p in found} != set(wanted):
        raise ValueError("receipt pair-only file denominator")
    receipts, references = {}, {}
    for path in found:
        if (
            path.is_symlink()
            or not path.is_file()
            or not 0 < path.stat().st_size <= 33 * 1024 * 1024
        ):
            raise ValueError("receipt regular bytes/limit")
        data = path.read_bytes()
        target = wanted[path.name]
        receipts[target] = json.loads(data, object_pairs_hook=helpers()[0]._pairs)
        references[target] = dict(
            name=path.name,
            bytes=len(data),
            sha256=digest(data),
            target=target,
            checkout=context["checkout"],
            run_id=context["run_id"],
            run_attempt=context["run_attempt"],
        )
    return receipts, references


def run_replay(root, receipts, context):
    selected = selected_observations(receipts, context)
    cells = {}
    for cell in CELLS:
        record = selected[key(cell)]
        observed = record["observation"]
        built = build(cell, root / cell[0] / cell[1], observed["metadata"])
        if built[6].decode() != record["association"]["public"]:
            raise ValueError(
                "fresh installed artifact differs from original native artifact"
            )
        rows = decode_rows(observed["rows"])
        routes = consume(cell, built, rows, observed["rows"])
        verify_routes(cell, routes, observed["rows"])
        cells[key(cell)] = dict(record, routes=routes)
    return cells


def compare_bag(left, right):
    from collections import Counter

    if Counter(canonical(row) for row in left) != Counter(
        canonical(row) for row in right
    ):
        raise ValueError("full typed multiplicity")


def verify_replay_report(value, context, inputs, references, selected, wheel_sha256):
    try:
        if (
            type(value) is not dict
            or set(value)
            != {
                "format",
                "mode",
                "context",
                "inputs",
                "receipts",
                "installation",
                "cells",
            }
            or value["format"] != FORMAT
            or value["mode"] != "captured-native-replay"
            or canonical(value["context"]) != canonical(context)
            or canonical(value["inputs"]) != canonical(inputs)
            or canonical(value["receipts"]) != canonical(references)
            or set(value["cells"]) != {key(c) for c in CELLS}
        ):
            raise ValueError("integration report context/input/denominator")
        verify_origins(value["installation"], inputs)
        if value["installation"]["wheel"]["sha256"] != wheel_sha256:
            raise ValueError("integration candidate wheel")
        for cell in CELLS:
            actual, original = value["cells"][key(cell)], selected[key(cell)]
            if set(actual) != {*original, "routes"} or any(
                actual[k] != original[k] for k in original
            ):
                raise ValueError("integration receipt observation substitution")
            verify_association(cell, actual["association"])
            verify_routes(cell, actual["routes"], original["observation"]["rows"])
            compare_bag(
                original["observation"]["rows"],
                fixture_tags(cell[0], cell[2] == "empty"),
            )
    except (KeyError, TypeError, IndexError, AttributeError) as error:
        raise ValueError("malformed integration report") from error
    return value


def write_report(path, value):
    data = canonical(value) + b"\n"
    if len(data) > MAX_REPORT:
        raise ValueError("integration sidecar exceeds 2 MiB")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def prepare(repository, environment, dist):
    import tempfile

    spec = importlib.util.spec_from_file_location(
        "pietto_s14_package_smoke", repository / "scripts/package_smoke.py"
    )
    assert spec is not None and spec.loader is not None
    smoke = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = smoke
    spec.loader.exec_module(smoke)
    if environment.exists() or environment.is_symlink() or dist.exists():
        raise ValueError("owned new preparation roots required")
    dist.mkdir(parents=True)
    smoke._run_command(
        "build integration candidate",
        ("uv", "build", "--sdist", "--wheel", "--out-dir", str(dist)),
        cwd=repository,
    )
    sdist, wheel = smoke._find_artifacts(dist)
    contract = smoke._project_contract()
    smoke._inspect_wheel(wheel, contract)
    smoke._inspect_sdist(sdist, contract)
    with tempfile.TemporaryDirectory(prefix="pietto-integration-install-") as temporary:
        scratch = Path(temporary)
        smoke._install_extra(environment, scratch, wheel)
        smoke._copy_smoke_inputs(scratch)
        smoke._check_installed_cell(environment, scratch, wheel, "arrow")


def verify_fixture_groups(cases, inputs):
    try:
        groups = {name: cases[name] for name in GROUPS}
        keys = {key(cell) for cell in CELLS}
        for name in GROUPS[:4]:
            if set(groups[name]) != keys:
                raise ValueError("integration cell denominator")
        for cell in CELLS:
            entry = groups[GROUPS[0]][key(cell)]
            if set(entry) != {"association", "metadata"} or entry[
                "metadata"
            ] != metadata_fixture(cell[0]):
                raise ValueError("integration supplied protocol facts")
            verify_association(cell, entry["association"])
            verify_routes(
                cell,
                {
                    route: groups[group][key(cell)]
                    for route, group in zip(
                        ("rows", "arrow", "ipc"), GROUPS[1:4], strict=True
                    )
                },
                fixture_tags(cell[0], cell[2] == "empty"),
            )
        moved = groups[GROUPS[4]]
        if (
            set(moved) != {"cells", "installation", "source_root", "child_pid"}
            or type(moved["child_pid"]) is not int
            or moved["child_pid"] <= 0
            or not Path(moved["source_root"]).is_absolute()
        ):
            raise ValueError("integration relocated child")
        wanted = {key(c) for c in CELLS if c[1] in (RECIPES[0][0], RECIPES[2][0])}
        if set(moved["cells"]) != wanted:
            raise ValueError("integration relocated denominator")
        verify_origins(moved["installation"], inputs)
        for name, actual in moved["cells"].items():
            expected = dict(
                groups[GROUPS[0]][name],
                routes={
                    route: groups[group][name]
                    for route, group in zip(
                        ("rows", "arrow", "ipc"), GROUPS[1:4], strict=True
                    )
                },
            )
            if canonical(actual) != canonical(expected):
                raise ValueError("integration relocation full correspondence")
        terminal = groups[GROUPS[5]]
        expected_terminal = dict(
            copied_grant="INTEROP_BINDING",
            spent_grant="INTEROP_SPENT",
            copied_session="IPC_IDENTITY",
            incomplete_ipc="IPC_COMPLETION",
            count_before_eof=dict(rows=4, completion=False, state="CLOSED_INCOMPLETE"),
            consumer=dict(
                errors=["INTEROP_TRANSFER", "RuntimeError"],
                input_complete=True,
                state="FAILED",
            ),
            primary_cleanup=dict(
                errors=["ValueError", "RuntimeError"],
                primary_identity=True,
                cleanup_identity=True,
                input_complete=True,
                state="FAILED",
                cleanup_calls=1,
            ),
            truncated_prefix=dict(sdk_rows=4, rejection="IPC_FRAME"),
            writer=dict(
                errors=["IPC_WRITE", "ValueError"],
                frame_returned=False,
                published_bytes=0,
            ),
            writer_finalize=dict(
                errors=["IPC_WRITE", "RuntimeError"],
                frame_returned=False,
                published_bytes=0,
            ),
        )
        for name, failure, early in (
            ("late_input", "READER_SOURCE", False),
            ("cleanup", "READER_CLEANUP", False),
            ("early_close", None, True),
        ):
            wanted_state = helpers()[2].interop_stream_expected(
                [(4, 0, 0)], [], failure=failure, early=early
            )
            expected_terminal[name] = {
                k: wanted_state[k]
                for k in (
                    "before",
                    "after",
                    "source_complete",
                    "error",
                    "closes",
                    "reads",
                )
            }
        if canonical(terminal) != canonical(expected_terminal):
            raise ValueError("integration failed delivery/cleanup witness")
        refusals: dict[str, Any] = dict.fromkeys(
            ("ordinal", "label", "target", "protocol_type", "widening_cannot_repair"),
            "PRODUCER_OBSERVATION",
        )
        refusals.update(
            foreign_root="ROOT", logical_null="NULL", mysql_bool="VALUE_DOMAIN"
        )
        upstream = {}
        for variant in ("decimal_mismatch", "timestamp_meaning", "uuid_meaning"):
            upstream[variant] = dict(
                status="BLOCKED",
                artifact=False,
                diagnostics=[
                    [
                        "PIE-B1002",
                        "REPRESENTATION",
                        "physical_storage_or_domain_mismatch",
                    ]
                    if variant == "decimal_mismatch"
                    else [
                        "PIE-B1004",
                        "MISSING_EVIDENCE",
                        "logical_temporal_or_uuid_meaning_missing",
                    ]
                ],
            )
        expected_refusals: dict[str, Any] = {**refusals, "upstream": upstream}
        if canonical(groups[GROUPS[6]]) != canonical(expected_refusals):
            raise ValueError("integration authority refusal witness")
        original = snapshot_expected(fixture_tags("postgres"), "postgres")
        changed = json.loads(canonical(original))
        changed["rows"][0][1] = 8
        integrity = dict(
            original=original,
            changed=changed,
            rejection="original-value correspondence",
            same_type=dict(input=[[1, 2]], delivered=[[2, 1]]),
            lost_duplicate=dict(
                rows=original["rows"][1:],
                declared_rows=3,
                original_rows=4,
                state="CLOSED",
                input_complete=True,
                delivery_complete=True,
                rejection="full typed multiplicity",
            ),
        )
        if canonical(groups[GROUPS[7]]) != canonical(integrity):
            raise ValueError("integration independent original-value oracle")
    except (KeyError, TypeError, IndexError, AttributeError) as error:
        raise ValueError("incomplete/malformed integration groups") from error


def product_damage():
    first = key(CELLS[0])
    return (
        lambda v: v["cases"][GROUPS[0]][first]["association"].update(
            policy="bind_safe_literals"
        ),
        lambda v: v["cases"][GROUPS[1]][first]["rows"][0].__setitem__(1, 0),
        lambda v: v["cases"][GROUPS[2]][first]["snapshots"].pop(),
        lambda v: v["cases"][GROUPS[3]][first].update(state="CLOSED_INCOMPLETE"),
        lambda v: v["cases"][GROUPS[4]]["installation"]["origins"].pop(
            "pietto._project.project_result_ipc"
        ),
        lambda v: v["cases"][GROUPS[5]]["consumer"].update(state="CLOSED"),
        lambda v: v["cases"][GROUPS[6]].update(mysql_bool="PASS"),
        lambda v: v["cases"][GROUPS[7]].update(
            changed=v["cases"][GROUPS[7]]["original"]
        ),
    )


def replay_damage(value, context, inputs, references, selected, wheel_sha256):
    first = key(CELLS[0])
    mutations = (
        lambda v: v["context"].update(checkout="0" * 40),
        lambda v: v["receipts"]["postgres"].update(sha256="0" * 64),
        lambda v: v["cells"].pop(first),
        lambda v: v["cells"][first]["routes"].pop("rows"),
        lambda v: v["installation"]["origins"].pop(
            "pietto._project.project_result_ipc"
        ),
        lambda v: v["cells"][first]["routes"].update(ipc={"passed": True}),
        lambda v: v["cells"][first]["observation"]["rows"][0][1].update(value="0"),
        lambda v: v["inputs"].pop("tests/_pietto_phase67_real_consumer_probe.py"),
    )
    for mutate in mutations:
        changed = json.loads(canonical(value))
        mutate(changed)
        try:
            verify_replay_report(
                changed, context, inputs, references, selected, wheel_sha256
            )
        except ValueError:
            continue
        raise AssertionError("damaged integration sidecar accepted")
    return len(mutations)


def main():
    import argparse
    import os
    import platform
    import subprocess
    import tempfile

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("child", "fixture", "prepare", "replay", "verify")
    )
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--environment", type=Path)
    parser.add_argument("--dist-dir", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--receipts", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--expected-commit")
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID"))
    parser.add_argument(
        "--run-attempt",
        type=int,
        default=int(os.environ.get("GITHUB_RUN_ATTEMPT", "1")),
    )
    parser.add_argument("--python", choices=("3.12", "3.13"))
    parser.add_argument("--artifact-id")
    parser.add_argument("--artifact-digest")
    args = parser.parse_args()
    actual_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    if (
        args.action == "replay"
        and args.python is not None
        and args.python != actual_python
    ):
        parser.error("replay must use the actual interpreter")
    if args.action == "prepare":
        prepare(
            args.repository.resolve(),
            args.environment.absolute(),
            args.dist_dir.resolve(),
        )
        return
    if args.action == "child":
        write_report(args.report, relocated_child(args.source_root))
        return
    if args.action == "fixture":
        with tempfile.TemporaryDirectory(
            prefix="pietto-integration-fixture-"
        ) as temporary:
            groups = fixture_groups(Path(temporary))
            verify_fixture_groups(groups, input_closure(args.repository.resolve()))
            write_report(args.report, groups)
        return
    repository = args.repository.resolve()
    current = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repository, text=True
    ).strip()
    if args.expected_commit != current:
        raise ValueError("integration checkout differs from required context")
    py = args.python or f"{sys.version_info.major}.{sys.version_info.minor}"
    if (
        py not in ("3.12", "3.13")
        or platform.system() != "Linux"
        or platform.machine() != "x86_64"
    ):
        raise ValueError("integration verified runtime domain")
    version = platform.python_version()
    value: Any = None
    if args.action == "verify":
        if args.report.stat().st_size > MAX_REPORT:
            raise ValueError("integration report size")
        value = json.loads(
            args.report.read_bytes(), object_pairs_hook=helpers()[0]._pairs
        )
        version = value["context"]["python_version"]
        if type(version) is not str or not re.fullmatch(
            re.escape(py) + r"\.[0-9]+", version
        ):
            raise ValueError("integration Python context")
    context = dict(
        checkout=current,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
        python=py,
        python_version=version,
    )
    receipts, references = receipt_files(args.receipts, context)
    selected = selected_observations(receipts, context)
    inputs = input_closure(repository)
    wheel_sha256 = digest(args.wheel.read_bytes())
    if args.action == "replay":
        with tempfile.TemporaryDirectory(prefix="pietto-native-replay-") as temporary:
            cells = run_replay(Path(temporary), receipts, context)
        value = dict(
            format=FORMAT,
            mode="captured-native-replay",
            context=context,
            inputs=inputs,
            receipts=references,
            installation=origin_observation(),
            cells=cells,
        )
    verify_replay_report(value, context, inputs, references, selected, wheel_sha256)
    if args.action == "replay":
        assert (
            replay_damage(value, context, inputs, references, selected, wheel_sha256)
            == 8
        )
        write_report(args.report, value)
    if args.artifact_id is not None or args.artifact_digest is not None:
        if (
            not args.artifact_id
            or not args.artifact_id.isdigit()
            or int(args.artifact_id) <= 0
            or args.artifact_digest != digest(args.report.read_bytes())
        ):
            raise ValueError("integration raw artifact identity")
    print(
        f"integration {args.action}: eight selected cells, three real routes, {len(value['installation']['origins'])} installed origins"
    )


if __name__ == "__main__":
    main()
