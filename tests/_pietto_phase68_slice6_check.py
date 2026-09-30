"""Independent literal results and fresh-root reconsumption of native records.

Extraction workers do not import this owner or receive its complete oracles.
Rebuilding legitimate test inputs here is not a source-free product loader.
"""

from collections import Counter
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID
import json
import struct

import _pietto_phase68_slice6_cases as cases
from _pietto_phase68_slice5_cases import expected as old_expected, seven_rows
from _pietto_phase68_slice5_probe import oracle_values, prior
from pietto._project.project_execution import ExecutionLimits
from pietto._project.project_execution_source import (
    ObservedSource,
    admit_observed_sources,
)
from pietto._project.project_refinement import prepare_refinement, TieRefinement
from pietto._project.project_refinement_enumeration import Enumeration
from pietto._project.project_refinement_verification import verify_native
from pietto._project.project_result_output import source_read_columns

BIG = 9007199254740993
DEFAULT = 9007199254740995
THIRD = float.fromhex("0x1.5555555555555p-2")
TWO_THIRDS = float.fromhex("0x1.5555555555555p-1")


def value(item):
    kind = item["kind"]
    if kind == "null":
        return None
    if kind == "int":
        return int(item["value"])
    if kind == "bool":
        return item["value"]
    if kind == "float":
        return struct.unpack(">d", bytes.fromhex(item["bits"]))[0]
    if kind == "decimal":
        coefficient = item["coefficient"]
        return Decimal(
            (
                int(coefficient.startswith("-")),
                tuple(int(c) for c in coefficient.lstrip("-")),
                -item["scale"],
            )
        )
    if kind == "text":
        return item["value"]
    if kind == "bytes":
        return bytes.fromhex(item["value"])
    if kind == "uuid":
        return UUID(item["value"])
    if kind == "datetime":
        return datetime.fromisoformat(item["value"])
    raise ValueError("unknown native scalar record")


def encoded_rows(rows):
    return [[prior.s01.scalar(v) for v in row] for row in rows]


def expected(target, case, variant, columns):
    if case == "R2_mixed":
        rows = (
            [
                (0, 1, DEFAULT, 1, 0.0, 0.25, 1, 0, 0),
                (BIG, 2, 0, 2, THIRD, 0.75, 1, 0, BIG),
                (BIG, 3, BIG, 2, THIRD, 0.75, 2, BIG, BIG),
                (1, 4, BIG, 4, 1.0, 1.0, 3, BIG, 1),
            ]
            if target == "postgres"
            else [
                (1, 1, DEFAULT, 1, 0.0, 0.25, 1, 1, 1),
                (0, 2, 1, 2, THIRD, 0.5, 1, 1, 0),
                (BIG, 3, 0, 3, TWO_THIRDS, 1.0, 2, 0, BIG),
                (BIG, 4, BIG, 3, TWO_THIRDS, 1.0, 3, BIG, BIG),
            ]
        )
        return encoded_rows(rows), True
    if case == "R2_repeated":
        rows = (
            [(0, 1, DEFAULT), (BIG, 2, 0)]
            if target == "postgres"
            else [(1, 1, DEFAULT), (0, 2, 1)]
        )
        return encoded_rows(rows + rows), False
    if case == "R2_bound":
        rows = (
            [(BIG, BIG + 2), (BIG, BIG + 2)]
            if variant == "B"
            else [(1, 2), (BIG, BIG + 1), (BIG, BIG + 1)]
        )
        return encoded_rows(rows), True
    if case == "R2_seven":
        precision, state = variant.split("_")
        rows = (
            []
            if state == "empty"
            else [(None,) * 9]
            if state == "null"
            else seven_rows("postgres", int(precision))
        )
        return encoded_rows(rows), False
    rows, ordered = old_expected(target, case, variant)
    return oracle_values(
        rows, [{"logical_type": {"name": c.realization.tag}} for c in columns]
    ), ordered


def canonical_checked(rows, columns):
    normalized = []
    for row in rows:
        values = []
        for value, column in zip(row, columns, strict=True):
            if value is not None:
                if column.realization.tag == "Bool":
                    value = bool(value)
                elif column.realization.tag == "UUID" and type(value) is bytes:
                    value = UUID(bytes=value)
                elif column.realization.tag == "Decimal":
                    sign, digits, exponent = value.as_tuple()
                    scale = column.realization.domain["scale"]
                    delta = int(exponent) + scale
                    digits = digits + (0,) * delta if delta >= 0 else digits[:delta]
                    value = Decimal((sign, digits or (0,), -scale))
            values.append(value)
        normalized.append(tuple(values))
    return encoded_rows(normalized)


def row_counter(rows):
    return Counter(json.dumps(r, sort_keys=True, separators=(",", ":")) for r in rows)


def rebound_admission(query, record):
    data = record["admission"]
    observations = []
    for position, (req, observed) in enumerate(
        zip(query.sources, data["sources"], strict=True)
    ):
        if type(observed["position"]) is not int or observed["position"] != position:
            raise ValueError("source occurrence position")
        schema = (
            tuple(tuple(m) for m in observed["schema"])
            if data["route"] != "postgres_adbc"
            else tuple(observed["schema"])
        )
        token_types = tuple(
            tuple(v) if type(v) is list else v for v in observed["token_types"]
        )
        observations.append(
            ObservedSource(
                req,
                data["route"],
                data["session"],
                data["role"],
                tuple(tuple(r) for r in observed["registry"]),
                observed["definition"],
                token_types,
                tuple(tuple(r) for r in observed["collision_rows"]),
                schema,
                tuple(tuple(r) for r in observed["collations"]),
                tuple(observed["terminals"]),
            )
        )
    return admit_observed_sources(
        query.sources,
        source_read_columns(query.output),
        tuple(observations),
        route=data["route"],
        session_id=data["session"],
        role=data["role"],
        environment=tuple(data["environment"]),
    )


def expected_uses(page, query):
    return [
        dict(
            domain=u.domain,
            index=u.index,
            value=encoded_rows(((u.value,),))[0][0],
            owner=next(
                i
                for i, s in enumerate(query.original.request.plan.literal_slots)
                if s is u.owner
            )
            if u.domain == "original"
            else u.owner,
            original=None if u.original is None else u.original.ordinal,
        )
        for u in page.native.uses
    ]


def check_record(item, config, directory, *, prefix=False):
    case, variant = item["case"], item["variant"]
    artifact = cases.original(directory, config["target"], case, variant)
    binding = None
    if case == "R2_bound":
        from pietto._project.project_execution_template import (
            prepare_template,
            bind_values,
        )

        template = prepare_template(artifact)
        wanted = (1, 2) if variant == "B" else (0, 1)
        if item["binding_values"] != list(wanted):
            raise ValueError("bound values")
        binding = bind_values(template, tuple(zip(template.slots, wanted, strict=True)))
        artifact = binding.artifact
    if artifact is None:
        if item["status"] != "ORIGINAL_BLOCKED":
            raise ValueError("original blocker missing")
        return None
    if (
        item["status"] != "OBSERVED"
        or item["original_sql"] != artifact.rendered.sql.decode()
    ):
        raise ValueError("original input correspondence")
    report = item["report"]
    if report.get("failure"):
        raise ValueError("native failure")
    role = "pietto_query" if config["target"] == "postgres" else "pietto_query@%"
    if report["admission"]["role"] != role:
        raise ValueError("actual fixture role")
    query = prepare_refinement(
        artifact,
        cases.source_requirements(artifact, config["providers"], role),
        policy=TieRefinement(),
        binding=binding,
    )
    if item["fields"] != [
        dict(
            label=c.label,
            tag=c.realization.tag,
            storage=c.realization.storage,
            domain=c.realization.domain,
            nullable=c.realization.nullable,
        )
        for c in query.output.columns
    ]:
        raise ValueError("public field correspondence")
    admission = rebound_admission(query, report)
    if not report["pages"]:
        raise ValueError("missing page")
    size = report["pages"][0]["size"]
    enumeration = Enumeration(
        query, admission, limits=ExecutionLimits(batch_rows=size, seconds=75)
    )
    decoded = []
    route = config["route"]
    for supplied in report["pages"]:
        page = enumeration.request_page()
        if (
            supplied["ordinal"] != page.ordinal
            or supplied["size"] != page.size
            or supplied["erasure"] != [i for i, _ in query.erasure]
            or supplied["uses"] != expected_uses(page, query)
        ):
            raise ValueError("page identity/parameter use/erasure")
        frontier = None if page.frontier is None else encoded_rows((page.frontier,))[0]
        if supplied["frontier"] != frontier:
            raise ValueError("unobserved frontier")
        arguments = tuple(value(v) for v in supplied["arguments"])
        actual = replace(page.native, sql=supplied["sql"].encode(), arguments=arguments)
        verify_native(actual, query, frontier=page.frontier, size=page.size)
        if route == "postgres_rows":
            if (
                supplied["api"] != "psycopg.RawCursor.execute"
                or supplied["prepare"] is not True
            ):
                raise ValueError("PG native submit")
            if supplied["buffered_rows"] != len(supplied["raw_rows"]):
                raise ValueError("native rowset gap")
            metadata = tuple(
                SimpleNamespace(
                    name=m[0], type_code=m[1], precision=m[4], scale=m[5], null_ok=m[6]
                )
                for m in supplied["metadata"]
            )
        else:
            raw = supplied["raw"]
            if (
                raw["sql"] != supplied["sql"]
                or raw["parameters"] != supplied["arguments"]
                or raw["actual"] != supplied["raw_rows"]
                or raw["statement_cleanup"] != "close_returned"
            ):
                raise ValueError("raw native correspondence")
            if route == "mysql_rows":
                prepares = [
                    c for c in raw["api_calls"] if c["method"] == "cmd_stmt_prepare"
                ]
                executes = [
                    c for c in raw["api_calls"] if c["method"] == "cmd_stmt_execute"
                ]
                if (
                    len(prepares) != 1
                    or prepares[0]["sql"] != supplied["sql"]
                    or len(executes) != 1
                    or executes[0]["values"] != supplied["arguments"]
                    or raw["source_terminal"] != "native_rowset_eof"
                ):
                    raise ValueError("MySQL actual prepared uses")
                metadata = tuple(tuple(m) for m in supplied["metadata"])
            else:
                executes = [c for c in raw["api_calls"] if c["method"] == "execute"]
                if (
                    len(executes) != 1
                    or executes[0]["sql"] != supplied["sql"]
                    or executes[0]["values"] != supplied["arguments"]
                    or raw["source_terminal"] != "NORMAL"
                    or raw["options"] != {"use_copy": True, "batch_size_hint_bytes": 1}
                ):
                    raise ValueError("ADBC actual typed uses")
                metadata = tuple(supplied["metadata"])
        raw_rows = tuple(tuple(value(v) for v in row) for row in supplied["raw_rows"])
        checked = enumeration.check_page(
            page, metadata, raw_rows, terminal=supplied["terminal"]
        )
        from pietto._project.project_arrow_result import bind_arrow

        schema = bind_arrow(checked.producer).schema
        if report["schema"] != [[f.name, str(f.type), f.nullable] for f in schema]:
            raise ValueError("public Arrow schema")
        decoded.extend(canonical_checked(checked.rows, query.output.columns))
        enumeration.commit_page(checked)
        observed_progress = supplied.get("accepted_progress")
        if observed_progress is None:
            if (
                route != "postgres_rows"
                or raw_rows
                or supplied is not report["pages"][-1]
                or not enumeration.progress[2]
            ):
                raise ValueError("missing accepted page progress")
            observed_progress = report["progress"]
        if observed_progress != list(enumeration.progress):
            raise ValueError("recorded accepted progress")
    if prefix and route == "postgres_rows":
        # The product captures after EARLY_CLOSE seals the owned enumerator.
        enumeration.fail()
    if report["progress"] != list(enumeration.progress):
        raise ValueError("recorded final progress")
    if (
        report["admission"]["route"] != route
        or report["session"] != admission.session_id
    ):
        raise ValueError("actual route/session correspondence")
    if decoded != report["rows"]:
        raise ValueError("public native erasure changed")
    expected_rows, ordered = expected(
        config["target"], case, variant, query.output.columns
    )
    if prefix:
        if len(decoded) != 1 or decoded != expected_rows[:1]:
            raise ValueError("bounded initial prefix")
    elif (
        decoded != expected_rows
        if ordered
        else row_counter(decoded) != row_counter(expected_rows)
    ):
        raise ValueError("independent complete payload/order/multiplicity")
    if route == "postgres_rows":
        outcome = report["outcome"]
        wanted = (
            ("EARLY_CLOSE", "ROLLBACK_ACK", "INCOMPLETE", "CLOSED")
            if prefix
            else ("EOF", "COMMIT_ACK", "COMPLETE", "CLOSED")
        )
        if (
            tuple(outcome[k] for k in ("source", "transaction", "delivery", "cleanup"))
            != wanted
            or not report["control_joined"]
            or outcome["primary"] is not None
            or outcome["cleanup_failures"]
            or type(outcome["rows"]) is not int
            or outcome["rows"] != len(decoded)
            or type(outcome["batches"]) is not int
            or outcome["batches"]
            != sum(bool(page["raw_rows"]) for page in report["pages"])
        ):
            raise ValueError("PG lifecycle")
    elif (
        report["transaction"] != ("ROLLBACK_ACK" if prefix else "COMMIT_ACK")
        or report["cleanup"] != "CLOSED"
    ):
        raise ValueError("bridge lifecycle")
    if not prefix and not enumeration.progress[2]:
        raise ValueError("missing whole-query EOF")
    return query


def producing_modules(tree):
    """Read actual retained Git inputs, never relabel old origins as current bytes."""
    import hashlib
    import io
    import subprocess
    import tarfile

    if (
        type(tree) is not str
        or len(tree) != 40
        or any(c not in "0123456789abcdef" for c in tree)
    ):
        raise ValueError("producing Git tree")
    repository = Path(__file__).resolve().parents[1]
    archive = subprocess.check_output(
        ["git", "archive", "--format=tar", tree, "src/pietto"], cwd=repository
    )
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        result = {}
        for member in stream.getmembers():
            if member.isfile():
                file = stream.extractfile(member)
                if file is None:
                    raise ValueError("missing producing module")
                result[member.name] = hashlib.sha256(file.read()).hexdigest()
        return result


def _worker_records(worker, *, root, source_prefix, installed_prefix, produced=None):
    import hashlib

    if worker["exit"] != 0 or worker["reaped"] is not True or worker.get("failed_case"):
        raise ValueError("worker terminal")
    for observation in worker["sessions_gone"]:
        values = observation["observations"]
        if (
            not values
            or any(type(n) is not int or n < 0 for n in values)
            or values[-1] != 0
        ):
            raise ValueError("owned session remains")
    expected_prefix = (
        source_prefix
        if worker.get("origin", "source") == "source"
        else installed_prefix
    )
    if not worker["origins"]:
        raise ValueError("missing origins")
    for name, record in worker["origins"].items():
        path = Path(record["path"])
        module = Path(*name.split("."))
        relative = (
            module / "__init__.py"
            if path.name == "__init__.py"
            else module.with_suffix(".py")
        )
        digest = (
            hashlib.sha256(path.read_bytes()).hexdigest()
            if produced is None
            else produced.get("src/" + relative.as_posix())
        )
        if (
            not path.is_relative_to(expected_prefix)
            or not path.as_posix().endswith("/" + relative.as_posix())
            or digest != record["sha256"]
        ):
            raise ValueError("actual code origin")
    sessions = []
    for item in worker["records"]:
        path = Path(item["path"])
        if (
            not path.is_relative_to(root)
            or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]
        ):
            raise ValueError("native observation identity")
        observed = json.loads(path.read_text())
        session = observed.get("report", {}).get("session")
        if session is not None:
            sessions.append(session)
        yield observed
    if [x["session"] for x in worker["sessions_gone"]] != sessions:
        raise ValueError("owned session observation denominator")


def check_control(item, route):
    if item["status"] != "EXPECTED_REJECTION":
        raise ValueError("missing negative terminal")
    control, report = item["control"], item["report"]
    if not report.get("failure"):
        raise ValueError("source/control failure missing")
    if control in ("expiry", "revision", "visibility", "role", "component_collision"):
        if report["pages"] or report["rows"]:
            raise ValueError("source failure accepted progress")
        errors = {
            "expiry": ("SOURCE_VERSION_OR_RETENTION",),
            "revision": ("SOURCE_VERSION_OR_RETENTION",),
            "visibility": ("SOURCE_DOMAIN", "SOURCE_DOMAIN_OR_TOKEN"),
            "role": ("SOURCE_ROLE", "SOURCE_OBSERVATION_IDENTITY"),
            "component_collision": (
                "SOURCE_TOKEN_NOT_INJECTIVE",
                "SOURCE_DOMAIN_OR_TOKEN",
            ),
        }[control]
        if report["failure"]["category"] not in errors:
            raise ValueError("wrong source rejection")
    elif control == "late_value":
        if (
            len(report["rows"]) != 2
            or len(report["pages"]) != 2
            or "VALUE_DOMAIN" not in report["failure"]["category"]
        ):
            raise ValueError("late decode containment")
    elif control in ("cancel", "consumer_error"):
        if len(report["rows"]) != 1 or len(report["pages"]) != 1:
            raise ValueError("late control boundary")
    else:
        raise ValueError("unknown control")
    if route == "postgres_rows":
        outcome = report["outcome"]
        if (
            outcome["delivery"] != "FAILED"
            or outcome["transaction"] != "ROLLBACK_ACK"
            or outcome["cleanup"] != "CLOSED"
            or not report["control_joined"]
        ):
            raise ValueError("failed PG attempt lifecycle")
    elif report["cleanup"] != "CLOSED" or report["transaction"] not in (
        "NOT_STARTED",
        "ROLLBACK_ACK",
    ):
        raise ValueError("failed bridge lifecycle")


def check_campaign(root, directory):
    report = json.loads((root / "pietto-phase68-slice06-campaign.json").read_text())
    if (
        report["complete"] is not True
        or len(report["resources"]) != 2
        or any(r["cleanup"]["status"] != "success" for r in report["resources"])
    ):
        raise ValueError("campaign closure")
    source_prefix = Path(__file__).resolve().parents[1] / "src"
    installed_prefix = Path(report["runtime"]["executable"]).parents[1]
    providers = {
        target: json.loads(
            (
                root
                / ("pietto-phase68-slice06-" + target)
                / "pietto-phase68-slice06-providers.json"
            ).read_text()
        )
        for target in ("postgres", "mysql")
    }
    failures = []

    def checked(item, config, location, **options):
        try:
            check_record(item, config, location, **options)
        except Exception as error:
            failures.append(
                (
                    config["route"],
                    item["case"],
                    item["variant"],
                    type(error).__name__,
                    str(error),
                )
            )

    domain = []
    current = 0
    produced = producing_modules(report["tree"])
    acquired = [
        (root, worker, providers[worker["target"]], produced)
        for worker in report["workers"]
    ]
    reused = report.get("family_reuse")
    if reused is not None:
        import hashlib

        old_root = Path(reused["root"])
        old_file = old_root / "pietto-phase68-slice06-campaign.json"
        if hashlib.sha256(old_file.read_bytes()).hexdigest() != reused["sha256"]:
            raise ValueError("reused acquisition identity")
        old = json.loads(old_file.read_text())
        if old["tree"] != reused["tree"] or any(
            r["cleanup"]["status"] != "success" for r in old["resources"]
        ):
            raise ValueError("reused producing inputs/closure")
        old_providers = json.loads(
            (
                old_root
                / "pietto-phase68-slice06-postgres"
                / "pietto-phase68-slice06-providers.json"
            ).read_text()
        )
        old_produced = producing_modules(old["tree"])
        acquired.extend(
            (old_root, w, old_providers, old_produced) for w in old["workers"]
        )
    for record_root, worker, record_providers, record_produced in acquired:
        config = dict(
            target=worker["target"],
            route=worker["route"],
            providers=record_providers,
        )
        for item in _worker_records(
            worker,
            root=record_root,
            produced=record_produced,
            source_prefix=source_prefix,
            installed_prefix=installed_prefix,
        ):
            key = (
                worker["target"],
                worker["route"],
                worker["origin"],
                item["case"],
                item["variant"],
            )
            if key in domain:
                raise ValueError("duplicate acceptance key")
            domain.append(key)
            checked(item, config, directory / str(current))
            current += 1
    routes = (
        ("postgres", "postgres_rows", "source"),
        ("postgres", "postgres_rows", "installed"),
        ("postgres", "postgres_adbc", "source"),
        ("mysql", "mysql_rows", "source"),
    )
    wanted = {(t, r, o, c, v) for t, r, o in routes for c, v in cases.CASES}
    if set(domain) != wanted:
        raise ValueError("family denominator")
    if len(report["bindings"]) != 4:
        raise ValueError("binding cells")
    for worker in report["bindings"]:
        cfg = dict(
            target=worker["target"],
            route=worker["route"],
            providers=providers[worker["target"]],
        )
        rows = []
        for item in _worker_records(
            worker,
            root=root,
            produced=produced,
            source_prefix=source_prefix,
            installed_prefix=installed_prefix,
        ):
            checked(item, cfg, directory / str(current))
            current += 1
            rows.append(item["report"]["rows"])
        if (
            len(rows) != 3
            or rows[0] != rows[2]
            or rows[0] == rows[1]
            or worker["rejected"] != ["wrong_binding_type", "structural_limit"]
        ):
            raise ValueError("A/B/A correspondence")
    if {x["route"] for x in report["fresh"]} != {
        "postgres_rows",
        "postgres_adbc",
        "mysql_rows",
    }:
        raise ValueError("fresh route denominator")
    for history in report["fresh"]:
        cfg = dict(
            target=history["target"],
            route=history["route"],
            providers=providers[history["target"]],
        )
        first = list(
            _worker_records(
                history["prefix"],
                root=root,
                produced=produced,
                source_prefix=source_prefix,
                installed_prefix=installed_prefix,
            )
        )
        second = list(
            _worker_records(
                history["resume"],
                root=root,
                produced=produced,
                source_prefix=source_prefix,
                installed_prefix=installed_prefix,
            )
        )
        if (
            len(first) != 1
            or len(second) != 1
            or history["prefix"]["pid"] == history["resume"]["pid"]
        ):
            raise ValueError("fresh process identity")
        a, b = first[0], second[0]
        checked(a, cfg, directory / str(current), prefix=True)
        current += 1
        checked(b, cfg, directory / str(current))
        current += 1
        ra, rb = a["report"], b["report"]
        if (
            ra["session"] == rb["session"]
            or ra["admission"]["environment"] != rb["admission"]["environment"]
            or rb["rows"][:1] != ra["rows"]
            or len(rb["rows"]) <= 1
            or b["prefix_checked"] is not True
        ):
            raise ValueError("same-version fresh suffix")
        if ra["pages"][0]["size"] != 1 or rb["pages"][0]["size"] != 3:
            raise ValueError("changed page size")
    expected_controls = {
        (r, c)
        for r in ("postgres_rows", "postgres_adbc", "mysql_rows")
        for c in (
            "expiry",
            "revision",
            "visibility",
            "role",
            "component_collision",
            "late_value",
        )
    } | {("postgres_rows", "cancel"), ("postgres_rows", "consumer_error")}
    found = set()
    for worker in report["controls"]:
        items = list(
            _worker_records(
                worker,
                root=root,
                produced=produced,
                source_prefix=source_prefix,
                installed_prefix=installed_prefix,
            )
        )
        if len(items) != 1:
            raise ValueError("control denominator")
        try:
            check_control(items[0], worker["route"])
        except Exception as error:
            failures.append(
                (worker["route"], worker["control"], type(error).__name__, str(error))
            )
        found.add((worker["route"], worker["control"]))
    if found != expected_controls or len(report["controls"]) != len(found):
        raise ValueError("control matrix")
    if failures:
        raise ValueError(json.dumps(failures))
    return dict(
        family_cells=len(domain),
        binding_cells=4,
        fresh_routes=3,
        controls=len(found),
        reconsumed=current,
    )


def check_record_damages(item, config, directory):
    """Corrupt copies of actual captures; rejection cannot rely on file hashes."""
    from copy import deepcopy

    report = item["report"]
    first = report["pages"][0]
    mutations = (
        ("original_sql", ("original_sql",), item["original_sql"] + ";"),
        ("submitted_sql", ("report", "pages", 0, "sql"), first["sql"] + " WHERE FALSE"),
        (
            "argument",
            ("report", "pages", 0, "arguments", 0),
            {"kind": "int", "value": "99"},
        ),
        ("parameter_use", ("report", "pages", 0, "uses", 0, "domain"), "original"),
        ("erasure", ("report", "pages", 0, "erasure", 0), 1),
        ("unknown_terminal", ("report", "pages", 0, "terminal"), "UNKNOWN"),
        ("frontier", ("report", "pages", 0, "frontier"), []),
        ("accepted_progress", ("report", "pages", 0, "accepted_progress", 0), 999),
        ("final_progress", ("report", "progress", 0), 999),
        ("source_position", ("report", "admission", "sources", 0, "position"), 1),
        (
            "source_revision",
            ("report", "admission", "sources", 0, "registry", 0, 3),
            "replaced",
        ),
        ("source_role", ("report", "admission", "role"), "different_role"),
        ("session", ("report", "session"), report["session"] + 1),
        ("schema", ("report", "schema", 0, 1), "float32"),
    )
    results = []

    def rejected(name, changed):
        try:
            check_record(changed, config, directory / name)
        except ValueError as error:
            results.append(
                dict(control=name, rejected=type(error).__name__, reason=str(error))
            )
        else:
            raise ValueError("raw damage accepted: " + name)

    for name, address, replacement in mutations:
        changed = deepcopy(item)
        parent = changed
        for key in address[:-1]:
            parent = parent[key]
        parent[address[-1]] = replacement
        rejected(name, changed)
    changed = deepcopy(item)
    page = changed["report"]["pages"][0]
    value_column = next(
        i for i, field in enumerate(item["fields"]) if field["tag"] == "Int"
    )
    changed["report"]["rows"][0][value_column] = {"kind": "int", "value": "1"}
    page["raw_rows"][0][value_column] = {"kind": "int", "value": "1"}
    if "raw" in page:
        page["raw"]["actual"][0][value_column] = {"kind": "int", "value": "1"}
    rejected("coordinated_payload", changed)
    changed = deepcopy(item)
    page = changed["report"]["pages"][0]
    value_column = next(
        i for i, field in enumerate(item["fields"]) if field["tag"] == "Float"
    )
    damaged_float = {"kind": "float", "bits": "0000000000000000"}
    changed["report"]["rows"][0][value_column] = damaged_float
    page["raw_rows"][0][value_column] = damaged_float
    if "raw" in page:
        page["raw"]["actual"][0][value_column] = damaged_float
    rejected("coordinated_signed_zero", changed)
    changed = deepcopy(item)
    page = changed["report"]["pages"][0]
    column = len(changed["fields"])
    page["raw_rows"][0][column] = {"kind": "null"}
    if "raw" in page:
        page["raw"]["actual"][0][column] = {"kind": "null"}
    rejected("active_coordinate_null", changed)
    changed = deepcopy(item)
    page = changed["report"]["pages"][0]
    if config["route"] == "postgres_adbc":
        page["metadata"][column]["name"] = "foreign_key"
    else:
        page["metadata"][column][0] = "foreign_key"
    rejected("key_metadata", changed)
    changed = deepcopy(item)
    page = changed["report"]["pages"][0]
    page["raw_rows"] = page["raw_rows"][1:]
    if "raw" in page:
        page["raw"]["actual"] = page["raw_rows"]
    else:
        page["buffered_rows"] = len(page["raw_rows"])
    rejected("native_gap", changed)
    changed = deepcopy(item)
    page = changed["report"]["pages"][1]
    page["raw_rows"][0] = deepcopy(changed["report"]["pages"][0]["raw_rows"][-1])
    if "raw" in page:
        page["raw"]["actual"][0] = page["raw_rows"][0]
    rejected("page_overlap", changed)
    for name, terminal in (("transaction", "UNKNOWN"), ("cleanup", "UNKNOWN")):
        changed = deepcopy(item)
        outcome = changed["report"].get("outcome", changed["report"])
        outcome[name] = terminal
        rejected(name, changed)
    return results
