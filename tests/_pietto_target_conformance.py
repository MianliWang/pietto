"""Explicit finite target runs and data-only receipt verification. Imports are inert."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import signal
import ssl
import stat
import subprocess
import sys
import time
import tomllib
from typing import Any
import venv
import zipfile

import _pietto_target_conformance_cases as cases
import _pietto_phase66_sql_emission_probe as emission
from _pietto_target_conformance_observation import Observer
from _pietto_target_conformance_resources import (
    MYSQL_MODE,
    MYSQL_TLS_VERSIONS,
    Resources,
    clean_environment,
    deadline,
    error_fact,
    loopback_port,
)

ROOT = Path(__file__).resolve().parents[1]
PINS = Path(__file__).with_name("phase66_target_pins.json")
FORMAT = "pietto.target-conformance-receipt.v2"
MAX_RECEIPT = 33 * 1024 * 1024
HELPERS = tuple(
    Path(__file__).with_name("_pietto_target_conformance" + suffix + ".py")
    for suffix in ("", "_resources", "_observation", "_cases")
) + (Path(__file__).with_name("_pietto_mysql_native_prepared.py"),)
EMISSION_PROBE = Path(__file__).with_name("_pietto_phase66_sql_emission_probe.py")
NATIVE_PREREQUISITE = (
    "A_legacy",
    "C_parameters",
    "E_recovery",
    "P_native_identifiers",
    "Q_native_lifecycle",
)


def canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in values:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def read_json(path: Path) -> tuple[dict[str, Any], bytes]:
    def identity(value: os.stat_result) -> tuple[int, ...]:
        if not stat.S_ISREG(value.st_mode) or value.st_size > MAX_RECEIPT:
            raise ValueError("invalid data file")
        return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)

    try:
        expected = identity(path.lstat())
        flags = (
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        )
        with os.fdopen(os.open(path, flags), "rb") as stream:
            if identity(os.fstat(stream.fileno())) != expected:
                raise ValueError("data file replaced before open")
            data = stream.read(MAX_RECEIPT + 1)
            if (
                len(data) != expected[2]
                or identity(os.fstat(stream.fileno())) != expected
                or identity(path.lstat()) != expected
            ):
                raise ValueError("data file changed during read")
    except OSError as error:
        raise ValueError("data file could not be opened safely") from error
    value = json.loads(
        data.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(
            ValueError("invalid JSON scalar")
        ),
    )
    if type(value) is not dict:
        raise ValueError("expected JSON object")
    return value, data


def load_pins(path: Path) -> tuple[dict[str, Any], str]:
    if path.resolve() != PINS.resolve() or path.is_symlink():
        raise ValueError("only checked-in target pins are accepted")
    value, data = read_json(path)
    if (
        set(value) != {"format", "platform", "drivers", "targets"}
        or value["format"] != "pietto.target-conformance-pins.v1"
        or value["platform"] != "linux/amd64"
    ):
        raise ValueError("invalid pins envelope")
    if value["drivers"] != {
        "psycopg": "3.3.5",
        "psycopg-binary": "3.3.5",
        "mysql-connector-python": "26.7.0",
    } or set(value["targets"]) != set(cases.TARGETS):
        raise ValueError("invalid driver or target denominator")
    expected = {
        "postgres": (
            "docker.io/library/postgres",
            "18.6-bookworm",
            "18.6",
            "18.6-1.pgdg12+2",
        ),
        "mysql": (
            "container-registry.oracle.com/mysql/community-server",
            "8.4.12",
            "8.4.12",
            "8.4.12",
        ),
    }
    for target, pin in value["targets"].items():
        if set(pin) != {
            "repository",
            "tag",
            "release",
            "index_digest",
            "platform_digest",
            "config_digest",
            "server_version",
            "package_version",
        }:
            raise ValueError("invalid target pin fields")
        if (
            pin["repository"],
            pin["tag"],
            pin["release"],
            pin["package_version"],
        ) != expected[target] or pin["server_version"] != pin["release"]:
            raise ValueError("unreviewed target distribution or build")
        for field in ("platform_digest", "config_digest"):
            if (
                type(pin[field]) is not str
                or re.fullmatch(r"sha256:[0-9a-f]{64}", pin[field]) is None
            ):
                raise ValueError("invalid immutable image digest")
        if (target == "mysql" and pin["index_digest"] is not None) or (
            target == "postgres"
            and re.fullmatch(r"sha256:[0-9a-f]{64}", str(pin["index_digest"])) is None
        ):
            raise ValueError("wrong index/platform relationship")
    return value, digest(data)


def source_members() -> dict[str, str]:
    return {
        "pietto/" + path.relative_to(ROOT / "src/pietto").as_posix(): digest(
            path.read_bytes()
        )
        for path in sorted((ROOT / "src/pietto").rglob("*.py"))
        if "__pycache__" not in path.parts
    }


def inputs() -> dict[str, Any]:
    paths = (*HELPERS, EMISSION_PROBE, PINS, ROOT / "pyproject.toml", ROOT / "uv.lock")
    return {
        "harness": {
            path.relative_to(ROOT).as_posix(): digest(path.read_bytes())
            for path in paths
        },
        "package_members": source_members(),
        "emission_inputs": {
            target: [
                {
                    "id": item["id"],
                    "variant": item["variant"],
                    "source_sha256": digest(emission.source_bytes(item["source"])),
                    "contract_sha256": digest(item["contract"].encode()),
                    "policy": item["policy"],
                }
                for item in emission.generation_inputs(target)
            ]
            for target in cases.TARGETS
        },
        "console_inputs": {
            target: emission.console_inputs(target) for target in cases.TARGETS
        },
    }


def command(
    argv: list[str], *, cwd: Path, timeout: int, stdin: str | None = None
) -> bytes:
    result = subprocess.run(
        argv,
        cwd=cwd,
        env=clean_environment(),
        input=stdin.encode() if stdin is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if result.returncode or len(result.stdout) > MAX_RECEIPT:
        raise RuntimeError("bounded child failed: " + Path(argv[0]).name)
    return result.stdout


GENERATION_CHILD = r"""
import contextlib,hashlib,importlib.metadata,io,json,pathlib,runpy,sys
console=pathlib.Path(sys.argv[1]).resolve()
root=pathlib.Path(sys.prefix).resolve()
if not console.is_relative_to(root): raise SystemExit("foreign console")
arguments=[str(console),"emit-sql","legacy.pietto","--dialect",sys.argv[2],"--format","json"]
sys.argv=arguments
out,err=io.StringIO(),io.StringIO()
with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
 try: runpy.run_path(str(console),run_name="__main__")
 except SystemExit as e: status=e.code
 else: status=0
origins={}
for name,module in tuple(sys.modules.items()):
 if name=="pietto" or name.startswith("pietto."):
  filename=getattr(module,"__file__",None)
  if filename:
   path=pathlib.Path(filename).resolve()
   if not path.is_relative_to(root) or "site-packages" not in path.parts: raise SystemExit("checkout import")
   index=path.parts.index("site-packages")
   member="/".join(path.parts[index+1:])
   origins[name]={"member":member,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
print(json.dumps({"exit_code":status,"stdout":out.getvalue(),"stderr":err.getvalue(),"origins":origins,
 "console_sha256":hashlib.sha256(console.read_bytes()).hexdigest(),"isolated":sys.flags.isolated,
 "version":importlib.metadata.version("pietto"),"runtime_version":importlib.metadata.version("antlr4-python3-runtime")},ensure_ascii=False))
"""


def installed_generation(
    target: str, directory: Path, expected: dict[str, Any]
) -> dict[str, Any]:
    build = directory / "private" / "wheel"
    build.mkdir()
    command(["uv", "build", "--wheel", "--out-dir", str(build)], cwd=ROOT, timeout=120)
    wheels = tuple(build.glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError("wheel denominator mismatch")
    wheel = wheels[0]
    with zipfile.ZipFile(wheel) as archive:
        members = {
            name: digest(archive.read(name))
            for name in archive.namelist()
            if name.startswith("pietto/") and name.endswith(".py")
        }
    if members != expected["package_members"]:
        raise ValueError("wheel is not the candidate source")
    environment = directory / "private" / "venv"
    venv.EnvBuilder(with_pip=False).create(environment)
    python = environment / "bin/python"
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    antlr = [
        package
        for package in lock["package"]
        if package["name"] == "antlr4-python3-runtime"
    ]
    if len(antlr) != 1:
        raise ValueError("runtime lock denominator mismatch")
    hashes = " ".join("--hash=" + item["hash"] for item in antlr[0]["wheels"])
    requirements = f"pietto @ {wheel.as_uri()} --hash=sha256:{digest(wheel.read_bytes())}\nantlr4-python3-runtime=={antlr[0]['version']} {hashes}\n"
    command(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "--require-hashes",
            "-r",
            "-",
        ],
        cwd=directory,
        timeout=180,
        stdin=requirements,
    )
    scratch = directory / "private" / "scratch"
    scratch.mkdir()
    (scratch / "legacy.pietto").write_text(
        cases.legacy_source(target), encoding="utf-8"
    )
    result = json.loads(
        command(
            [
                str(python),
                "-I",
                "-c",
                GENERATION_CHILD,
                str(environment / "bin/pietto"),
                target,
            ],
            cwd=scratch,
            timeout=30,
        )
    )
    result["wheel_sha256"] = digest(wheel.read_bytes())
    result["wheel_members"] = members
    result["source_sha256"] = digest(cases.legacy_source(target).encode())
    result["stdout_sha256"] = digest(result["stdout"].encode())
    probe_bytes = EMISSION_PROBE.read_bytes()
    if (
        digest(probe_bytes)
        != expected["harness"][EMISSION_PROBE.relative_to(ROOT).as_posix()]
    ):
        raise ValueError("emission probe input changed")
    copied_probe = scratch / "emission_probe.py"
    copied_probe.write_bytes(probe_bytes)
    result["emission"] = json.loads(
        command(
            [str(python), "-I", str(copied_probe), target], cwd=scratch, timeout=120
        ),
        object_pairs_hook=pairs,
    )
    # Slice13: the same copied probe drives the installed console entrypoint
    # with real argv over real project/contract files from an unrelated cwd.
    result["console"] = json.loads(
        command(
            [
                str(python),
                "-I",
                str(copied_probe),
                target,
                "console",
                str(environment / "bin/pietto"),
            ],
            cwd=scratch,
            timeout=30,
        ),
        object_pairs_hook=pairs,
    )
    verify_generation(result, target, expected)
    return result


def verify_generation(
    generation: dict[str, Any], target: str, expected: dict[str, Any]
) -> None:
    if (
        generation.get("exit_code") != 0
        or generation.get("stderr") != ""
        or generation.get("isolated") != 1
        or generation.get("version") != "0.1.0"
        or generation.get("runtime_version") != "4.13.2"
    ):
        raise ValueError("installed compiler generation failed")
    if (
        generation.get("wheel_members") != expected["package_members"]
        or generation.get("source_sha256")
        != digest(cases.legacy_source(target).encode())
        or generation.get("stdout_sha256") != digest(generation["stdout"].encode())
    ):
        raise ValueError("installed wheel/source/output substitution")
    for field in ("wheel_sha256", "console_sha256"):
        if re.fullmatch(r"[0-9a-f]{64}", str(generation.get(field))) is None:
            raise ValueError("missing wheel transfer identity")
    origins = generation.get("origins", {})
    if not {"pietto", "pietto.cli", "pietto.sql." + target} <= origins.keys():
        raise ValueError("same-child installed origins incomplete")
    for value in origins.values():
        if (
            set(value) != {"member", "sha256"}
            or value["member"] not in expected["package_members"]
            or expected["package_members"][value["member"]] != value["sha256"]
        ):
            raise ValueError("foreign installed import or member")
    document = json.loads(generation["stdout"], object_pairs_hook=pairs)
    if (
        set(document)
        != {
            "schema_version",
            "command",
            "ok",
            "path",
            "dialect",
            "diagnostics",
            "cli_errors",
            "artifacts",
            "output",
        }
        or document["schema_version"] != 1
        or document["command"] != "emit-sql"
        or document["ok"] is not True
        or document["dialect"] != target
        or document["cli_errors"] != []
        or document["diagnostics"] != []
        or document["output"] is not None
    ):
        raise ValueError("wrong legacy envelope")
    if document["artifacts"] != [
        {"kind": "relation", "name": "legacy_rows", "sql": cases.legacy_sql(target)}
    ]:
        raise ValueError("wrong legacy query artifact")
    verify_emission_generation(generation["emission"], target, expected)
    verify_console_generation(
        generation["console"], target, expected, generation["emission"]["records"]
    )


def verify_installed_origins(origins, expected, required, failure):
    if not required <= origins.keys():
        raise ValueError(failure)
    for name, origin in origins.items():
        if (
            set(origin) != {"member", "sha256"}
            or origin["member"] not in expected["package_members"]
            or origin["sha256"] != expected["package_members"][origin["member"]]
        ):
            raise ValueError("foreign emission installed origin")
        module_member = name.replace(".", "/")
        if origin["member"] not in {
            module_member + ".py",
            module_member + "/__init__.py",
        }:
            raise ValueError("emission module/member identity mismatch")


EMISSION_MODULES = frozenset(
    "pietto._project.project_sql_emission" + suffix
    for suffix in (
        "",
        "_contract",
        "_ast",
        "_rendering",
        "_verification",
        "_scopes",
        "_parameters",
        "_inspection",
    )
)
# The installed console loads the production emission owners; the private
# inspection view is consumed only by the probe's generation child.
CONSOLE_MODULES = (
    EMISSION_MODULES - {"pietto._project.project_sql_emission_inspection"}
) | {
    "pietto",
    "pietto.cli",
    "pietto._project.project_sql_emission_cli",
}
EXIT_CODES = {"VERIFIED": 0, "BLOCKED": 1, "INPUT_REJECTED": 2}


def verify_console_generation(value, target, expected, api_records):
    if (
        set(value)
        != {
            "records",
            "origins",
            "isolated",
            "probe_sha256",
            "config_sha256",
            "console_sha256",
        }
        or value["isolated"] != 1
    ):
        raise ValueError("console generation envelope")
    if value["probe_sha256"] != expected["harness"][
        EMISSION_PROBE.relative_to(ROOT).as_posix()
    ] or value["config_sha256"] != digest(emission.CONFIG.encode()):
        raise ValueError("console probe/config input substitution")
    if re.fullmatch(r"[0-9a-f]{64}", str(value["console_sha256"])) is None:
        raise ValueError("missing console transfer identity")
    verify_installed_origins(
        value["origins"],
        expected,
        CONSOLE_MODULES,
        "same-child console origins incomplete",
    )
    records = value["records"]
    inputs = expected["console_inputs"][target]
    if len(records) != len(inputs):
        raise ValueError("console witness denominator mismatch")
    api = {(r["id"], r["variant"]): r for r in api_records}
    for record, item in zip(records, inputs, strict=True):
        if set(record) != set(item) | {
            "exit_code",
            "stderr",
            "stdout",
            "stdout_sha256",
            "artifact_sha256",
            "public_sha256",
        } or any(record[key] != item[key] for key in item):
            raise ValueError("console generation input substitution")
        # The console must publish exactly the installed pipeline's artifact:
        # the receipt carries that API record in full and the console bytes by
        # SHA-256, the facility's transfer identity.
        api_record = api[item["id"], item["variant"]]
        if record["public_sha256"] != api_record["public_sha256"] or api_record[
            "public_sha256"
        ] != digest(api_record["public"].encode("utf-8")):
            raise ValueError("console artifact differs from the API artifact")
        document = emission.decode_public(api_record["public"].encode("utf-8"))
        status = emission.expected_status(item["id"], item["variant"], target)
        if (
            document["status"] != status
            or record["exit_code"] != EXIT_CODES[status]
            or record["stderr"] != ""
        ):
            raise ValueError("wrong console outcome, exit code or stderr")
        if item["output"]:
            if record["artifact_sha256"] != record["public_sha256"]:
                raise ValueError("console artifact file identity mismatch")
        elif record["artifact_sha256"] is not None:
            raise ValueError("console wrote an unrequested file")
        if item["format"] == "json":
            if record["stdout"] is not None or (
                record["stdout_sha256"] != record["public_sha256"]
            ):
                raise ValueError("console JSON stdout is not the artifact")
        elif (
            status != "VERIFIED"
            or type(record["stdout"]) is not str
            or digest(record["stdout"].encode("utf-8")) != record["stdout_sha256"]
            or not record["stdout"].startswith("pietto.sql-emission.v1 VERIFIED\n")
            or "\nsql:\n" + document["sql"] + "\nend sql\n" not in record["stdout"]
        ):
            raise ValueError("console text presentation mismatch")


def verify_emission_generation(value, target, expected):
    if (
        set(value)
        != {"records", "origins", "isolated", "probe_sha256", "config_sha256"}
        or value["isolated"] != 1
    ):
        raise ValueError("emission generation envelope")
    if value["probe_sha256"] != expected["harness"][
        EMISSION_PROBE.relative_to(ROOT).as_posix()
    ] or value["config_sha256"] != digest(emission.CONFIG.encode()):
        raise ValueError("emission probe/config input substitution")
    verify_installed_origins(
        value["origins"],
        expected,
        EMISSION_MODULES,
        "same-child emission origins incomplete",
    )
    records = value["records"]
    inputs = expected["emission_inputs"][target]
    if len(records) != len(inputs):
        raise ValueError("emission variant denominator mismatch")
    for record, item, fixture in zip(
        records, inputs, emission.generation_inputs(target), strict=True
    ):
        if set(record) != {
            "id",
            "variant",
            "source_sha256",
            "contract_sha256",
            "public",
            "public_sha256",
        } or any(
            record[key] != item[key]
            for key in ("id", "variant", "source_sha256", "contract_sha256")
        ):
            raise ValueError("emission generation input substitution")
        data = record["public"].encode("utf-8")
        if record["public_sha256"] != digest(data):
            raise ValueError("serialized emission transfer identity")
        document = emission.decode_public(data)
        status = emission.expected_status(record["id"], record["variant"], target)
        if document["status"] != status:
            raise ValueError("wrong emission outcome")
        if status == "INPUT_REJECTED":
            message, path = {
                "duplicate_selector": (
                    "Duplicate source description.",
                    "sources/1/selector",
                ),
                "ordinal_bool": (
                    "Invalid emission contract structure.",
                    "sources/0/fields/0/ordinal",
                ),
                "stale_selector": (
                    "Source selector is absent or ambiguous.",
                    "sources/0/selector",
                ),
            }[record["variant"]]
            if (
                document["cli_errors"]
                != [{"kind": "emission_selector", "message": message, "path": path}]
                or document["diagnostics"] != []
            ):
                raise ValueError("wrong exact emission input rejection")
        if status == "VERIFIED":
            if (
                document["request"]["contract"] != json.loads(fixture["contract"])
                or document["request"]["literal_policy"] != fixture["policy"]
                or document["request"]["sources"]
                != [
                    {
                        "module": name,
                        "sha256": digest(content.encode("utf-8")),
                        "byte_count": len(content.encode("utf-8")),
                    }
                    for name, content in sorted(
                        emission.source_files(fixture["source"]).items()
                    )
                ]
            ):
                raise ValueError("public artifact not bound to source/contract input")
            kind = (
                "table"
                if record["id"] in {"G_emission_table_bag", "I_emission_table_empty"}
                or (
                    record["id"] == "M_named_chain" and record["variant"] == "table_bag"
                )
                or (
                    record["id"] == "R_fixed_direct"
                    and record["variant"] in {"table_preserve", "table_bind"}
                )
                or (
                    record["id"] == "T_row_direct"
                    and record["variant"]
                    in {"table_preserve", "empty_preserve", "truth_table"}
                )
                else "query"
            )
            if document["request"]["owner"] != {
                "module": "main.pietto",
                "kind": kind,
                "name": "result",
            }:
                raise ValueError("public selected owner changed")
        elif status == "BLOCKED":
            code = (
                "PIE-B1003"
                if record["id"] == "O_named_later"
                else {
                    "missing_source": "PIE-B1001",
                    "bool_domain": "PIE-B1002",
                    "decimal_mismatch": "PIE-B1002",
                    "timestamp_meaning": "PIE-B1004",
                    "uuid_meaning": "PIE-B1004",
                    # Slice6 row boundaries: an unadmitted operator or node type
                    # against an overflowing checked physical result.
                    "float_arithmetic": "PIE-B1003",
                    "float_comparison": "PIE-B1003",
                    "bool_comparison": "PIE-B1003",
                    "modulo": "PIE-B1003",
                    "between": "PIE-B1003",
                    "int_overflow": "PIE-B1002",
                    "unary_overflow": "PIE-B1002",
                    # Slice7: `match_join` migrated to VERIFIED, so it no longer
                    # reaches this branch. MySQL keeps FULL as a typed non-support.
                    "restricted": "PIE-B1003",
                    "full_restricted": "PIE-B1003",
                    # Corrective closure: the NULL-key FULL minimum positive keeps
                    # MySQL's approved FULL non-support.
                    "null_keys": "PIE-B1003",
                    # Slice8: R13 freezes SUM/AVG result realization, R12 keeps
                    # Float outside group comparison, and a violated Bool or
                    # Decimal source domain stays a representation failure.
                    "sum_direct": "PIE-B1003",
                    "avg_direct": "PIE-B1003",
                    "sum_hidden_right": "PIE-B1003",
                    "float_key": "PIE-B1003",
                    "bool_domain_key": "PIE-B1002",
                    "decimal_parameter_key": "PIE-B1002",
                    # Slice9: R16 keeps the null and ordering modifiers outside
                    # the admitted set, C16 refuses an offset RANGE with a second
                    # ORDER key, and GROUPS/EXCLUDE stays MySQL non-support.
                    "ignore_nulls": "PIE-B1003",
                    "from_last": "PIE-B1003",
                    "offset_range_keys": "PIE-B1003",
                    "exclude": "PIE-B1003",
                    # Slice10: R20 keeps the hidden STRICT-FD ORDER pending,
                    # D07 keeps Float outside row equivalence upstream, and a
                    # computed ORDER key needs an established port.
                    "hidden_strict_fd": "PIE-B1003",
                    "float_distinct": "PIE-B1003",
                    "order_expression": "PIE-B1003",
                    # Slice11: R22 refuses a physical representation mismatch
                    # at emission; Float equality forms, arity and logical type
                    # mismatches stay upstream semantic rejections.
                    "physical_mismatch": "PIE-B1002",
                    "float_intersect_all": "PIE-B1003",
                    "arity_mismatch": "PIE-B1003",
                    "type_mismatch": "PIE-B1003",
                }[record["variant"]]
            )
            if code not in [b["code"] for b in document["blockers"]]:
                raise ValueError("wrong emission blocker taxonomy")


def driver_info(pins: dict[str, Any]) -> dict[str, Any]:
    import psycopg.pq

    versions = {name: importlib.metadata.version(name) for name in pins["drivers"]}
    if versions != pins["drivers"] or psycopg.pq.__impl__ != "binary":
        raise ValueError("driver pin mismatch")
    return {
        "versions": versions,
        "postgres_implementation": psycopg.pq.__impl__,
        "libpq_version": psycopg.pq.version(),
        "libpq_build_version": psycopg.pq.__build_version__,
        "mysql_implementation": "pure",
        "python": platform.python_version(),
        "openssl": ssl.OPENSSL_VERSION,
    }


ENVIRONMENT_QUERIES = {
    "postgres": "SELECT current_setting('server_version'), current_setting('server_version_num'), version(), current_setting('server_encoding'), current_setting('client_encoding'), current_setting('TimeZone'), current_setting('statement_timeout'), current_user, current_setting('max_identifier_length')",
    "mysql": "SELECT VERSION(), @@version_comment, @@version_compile_machine, @@version_compile_os, @@character_set_connection, @@collation_connection, @@sql_mode, @@max_execution_time, CURRENT_USER(), @@lower_case_table_names",
}
MYSQL_TLS_QUERY = (
    "SHOW SESSION STATUS WHERE Variable_name IN ('Ssl_cipher', 'Ssl_version')"
)


def transport(
    manager: Observer, query: Observer, resource: Resources
) -> dict[str, Any]:
    if resource.target == "postgres":
        return {"mode": "loopback_plaintext"}
    return {
        "mode": "owned_ca_tls",
        "ca": resource.ca_identity,
        "verify_certificate": True,
        "verify_hostname": False,
        "allowed_versions": list(MYSQL_TLS_VERSIONS),
        "certificate_policy": "ca_chain",
        "sessions": [
            {
                "identity": observer.identity,
                "session_id": observer.session_id(),
                "observation": observer.capture(MYSQL_TLS_QUERY),
            }
            for observer in (manager, query)
        ],
    }


def verify_transport(value: dict[str, Any], target: str, pin: dict[str, Any]) -> None:
    if target == "postgres":
        if value != {"mode": "loopback_plaintext"}:
            raise ValueError("unexpected PostgreSQL transport")
        return
    if (
        set(value)
        != {
            "mode",
            "ca",
            "verify_certificate",
            "verify_hostname",
            "allowed_versions",
            "certificate_policy",
            "sessions",
        }
        or value["mode"] != "owned_ca_tls"
        or value["verify_certificate"] is not True
        or value["verify_hostname"] is not False
        or value["allowed_versions"] != list(MYSQL_TLS_VERSIONS)
        or value["certificate_policy"] != "ca_chain"
        or set(value["ca"]) != {"container_id", "image_config", "sha256"}
        or value["ca"]["image_config"] != pin["config_digest"]
        or re.fullmatch(r"[0-9a-f]{64}", value["ca"]["sha256"]) is None
        or [session["identity"] for session in value["sessions"]]
        != ["fixture_manager", "query"]
    ):
        raise ValueError("missing owned CA/transport evidence")
    for session in value["sessions"]:
        observation = session["observation"]
        cases.check_complete(observation)
        cases.check_identity(observation, target, session["identity"])
        rows = observation["rows"]
        if (
            type(session["session_id"]) is not int
            or session["session_id"] <= 0
            or observation["sql"] != MYSQL_TLS_QUERY
            or observation["parameters"] != []
            or len(rows) != 2
            or any(len(row) != 2 for row in rows)
            or any(cell.get("kind") != "text" for row in rows for cell in row)
            or [row[0]["value"] for row in rows] != ["Ssl_cipher", "Ssl_version"]
            or not rows[0][1]["value"]
            or rows[1][1]["value"] not in {"TLSv1.2", "TLSv1.3"}
        ):
            raise ValueError("actual MySQL TLS session evidence missing")


def environment(observer: Observer, resource: Resources) -> dict[str, Any]:
    target = resource.target
    sql = ENVIRONMENT_QUERIES[target]
    observation = observer.capture(sql)
    cases.check_complete(observation)
    values = [item.get("value") for item in observation["rows"][0]]
    return {
        "query": observation,
        "values": values,
        "image_config": resource.pin["config_digest"],
        "platform": "linux/amd64",
    }


def verify_environment(value: dict[str, Any], target: str, pin: dict[str, Any]) -> None:
    cases.check_complete(value["query"])
    cases.check_identity(value["query"], target, "fixture_manager")
    if (
        value["query"]["sql"] != ENVIRONMENT_QUERIES[target]
        or value["query"]["parameters"] != []
    ):
        raise ValueError("environment query substitution")
    kinds = ["text"] * (9 if target == "postgres" else 10)
    if target == "mysql":
        kinds[7] = kinds[9] = "int"
    if [item["kind"] for item in value["query"]["rows"][0]] != kinds:
        raise ValueError("environment value type mismatch")
    values = [item.get("value") for item in value["query"]["rows"][0]]
    if (
        values != value["values"]
        or value["platform"] != "linux/amd64"
        or value["image_config"] != pin["config_digest"]
    ):
        raise ValueError("environment correspondence mismatch")
    if target == "postgres":
        if (
            values[0].split()[0] != "18.6"
            or values[1] != "180006"
            or not values[2].startswith("PostgreSQL 18.6 ")
            or pin["package_version"] not in values[2]
            or values[3:7] != ["UTF8", "UTF8", "UTC", "10s"]
            or values[7] != "pietto_manager"
            or values[8] != "63"
        ):
            raise ValueError("PostgreSQL server/build/environment mismatch")
    elif (
        values[:6]
        != [
            "8.4.12",
            "MySQL Community Server - GPL",
            "x86_64",
            "Linux",
            "utf8mb4",
            "utf8mb4_0900_bin",
        ]
        or set(str(values[6]).split(",")) != set(MYSQL_MODE.split(","))
        or values[7] != "10000"
        or values[8] != "root@%"
        or values[9] != "0"
    ):
        raise ValueError("MySQL server/build/environment mismatch")


PG_PRIVILEGES = "SELECT current_user, has_database_privilege(current_user,'phase66','CONNECT'), has_database_privilege(current_user,'phase66','CREATE'), has_database_privilege(current_user,'phase66','TEMP'), has_schema_privilege(current_user,'public','USAGE'), has_schema_privilege(current_user,'public','CREATE'), has_table_privilege(current_user,'phase66_rows','SELECT'), has_table_privilege(current_user,'phase66_rows','INSERT'), has_table_privilege(current_user,'phase66_rows','UPDATE'), has_table_privilege(current_user,'phase66_rows','DELETE'), rolsuper, rolcreaterole, rolcreatedb, rolreplication, rolbypassrls FROM pg_roles WHERE rolname=current_user"


def privileges(observer: Observer) -> list[dict[str, Any]]:
    if observer.target == "postgres":
        return [observer.capture(PG_PRIVILEGES)]
    return [
        observer.capture("SELECT CURRENT_USER(), CURRENT_ROLE()"),
        observer.capture("SHOW GRANTS FOR CURRENT_USER"),
    ]


def verify_privileges(observations: list[dict[str, Any]], target: str) -> None:
    for observation in observations:
        cases.check_complete(observation)
        cases.check_identity(observation, target, "query")
    if target == "postgres":
        flags = [
            True,
            False,
            False,
            True,
            False,
            True,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
        ]
        expected = [
            [
                {"kind": "text", "value": "pietto_query"},
                *({"kind": "bool", "value": value} for value in flags),
            ]
        ]
        if (
            len(observations) != 1
            or observations[0]["sql"] != PG_PRIVILEGES
            or observations[0]["rows"] != expected
        ):
            raise ValueError("query role retains management authority")
    else:
        if (
            len(observations) != 2
            or observations[0]["sql"] != "SELECT CURRENT_USER(), CURRENT_ROLE()"
            or observations[1]["sql"] != "SHOW GRANTS FOR CURRENT_USER"
            or observations[0]["rows"]
            != [
                [
                    {"kind": "text", "value": "pietto_query@%"},
                    {"kind": "text", "value": "NONE"},
                ]
            ]
        ):
            raise ValueError("wrong query identity or role")
        expected = [
            [{"kind": "text", "value": "GRANT USAGE ON *.* TO `pietto_query`@`%`"}],
            [
                {
                    "kind": "text",
                    "value": "GRANT SELECT ON `phase66`.* TO `pietto_query`@`%`",
                }
            ],
        ]
        if observations[1]["rows"] != expected:
            raise ValueError("unexpected query grants")


def execute_case(
    case_id: str,
    target: str,
    query: Observer,
    manager: Observer,
    generation: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    if case_id in emission.VARIANTS:
        result["variants"] = []
        records = [r for r in generation["emission"]["records"] if r["id"] == case_id]
        if [r["variant"] for r in records] != list(emission.VARIANTS[case_id]):
            raise ValueError("missing emission variants")
        for record in records:
            document = emission.decode_public(record["public"].encode())
            before = query.submission_count
            if document["status"] == "VERIFIED":
                # The public decoder is the only source of submitted SQL/values.
                result["observations"].append(
                    query.capture(
                        document["sql"],
                        emission.decoded_arguments(document),
                        prepared=True,
                    )
                )
            result["variants"].append(
                {
                    "variant": record["variant"],
                    "public": record["public"],
                    "public_sha256": record["public_sha256"],
                    "submission_before": before,
                    "submission_after": query.submission_count,
                }
            )
    elif case_id == emission.CONSOLE_CASE:
        result["witnesses"] = []
        api = {(r["id"], r["variant"]): r for r in generation["emission"]["records"]}
        for record in generation["console"]["records"]:
            api_record = api[record["id"], record["variant"]]
            if record["public_sha256"] != api_record["public_sha256"]:
                raise ValueError("console artifact differs from the API artifact")
            document = emission.decode_public(api_record["public"].encode())
            before = query.submission_count
            if document["status"] == "VERIFIED":
                result["observations"].append(
                    query.capture(
                        document["sql"],
                        emission.decoded_arguments(document),
                        prepared=True,
                    )
                )
            result["witnesses"].append(
                {
                    "witness": record["witness"],
                    "id": record["id"],
                    "variant": record["variant"],
                    "public_sha256": record["public_sha256"],
                    "submission_before": before,
                    "submission_after": query.submission_count,
                }
            )
    elif case_id in cases.SLICE2_CASE_IDS[:3]:
        sql, params = (
            (json.loads(generation["stdout"])["artifacts"][0]["sql"], ())
            if case_id == "A_legacy"
            else cases.control(target, case_id)
        )
        result["observations"] = [
            query.capture(sql, params, prepared=case_id == "C_parameters")
        ]
    elif case_id == "Q_native_lifecycle":
        result["session_before"] = query.session_id()
        observations = result["observations"]
        observations.append(query.capture("SELECT 1 AS v"))
        sql = (
            "SELECT CAST($1 AS integer)"
            if target == "postgres"
            else "DO JSON_EXTRACT(?, '$')"
        )
        observations.append(
            query.capture(sql, ("{",), prepared=True, rows=target == "postgres")
        )
        query.rollback()
        result["recovery"] = "success"
        observations.append(query.capture("SELECT 2 AS v"))
        observations.append(
            manager.capture(
                "CREATE TABLE IF NOT EXISTS phase66_rows (id BIGINT NOT NULL)"
                if target == "postgres"
                else "INSERT IGNORE INTO phase66_diagnostic_rows VALUES ('abcdef')",
                rows=False,
                native=True,
            )
        )
        observations.append(query.capture("SELECT id FROM phase66_rows WHERE 1=0"))
        if target == "mysql":
            observations.append(query.capture("SELECT ? AS v"))
            observations.append(
                query.capture("SELECT JSON_EXTRACT(?, '$')", ("{",), prepared=True)
            )
            query.rollback()
            observations.append(query.capture("SELECT 3 AS v"))
        result["session_after"] = query.session_id()
    elif case_id == "D_diagnostics":
        sql = (
            "CREATE TABLE IF NOT EXISTS phase66_rows (id BIGINT NOT NULL)"
            if target == "postgres"
            else "INSERT IGNORE INTO phase66_diagnostic_rows VALUES ('abcdef')"
        )
        result["observations"] = [
            manager.capture(sql, rows=False),
            query.capture("SELECT 1 AS v"),
        ]
        if target == "mysql":
            result["settings"] = [
                manager.capture("SET SESSION max_error_count=0", rows=False)
            ]
            cases.check_complete(result["settings"][0])
            try:
                result["observations"].append(manager.capture(sql, rows=False))
            finally:
                result["settings"].append(
                    manager.capture("SET SESSION max_error_count=64", rows=False)
                )
                cases.check_complete(result["settings"][1])
    else:
        result["session_before"] = query.session_id()
        if case_id == "F_privilege_cleanup":
            result["privilege_observations"] = privileges(query)
            verify_privileges(result["privilege_observations"], target)
            result["privileges_verified"] = True
            sql = (
                "CREATE TABLE public.phase66_denied (id BIGINT)"
                if target == "postgres"
                else "CREATE DATABASE phase66_denied"
            )
        else:
            result["begin"] = query.begin()
            cases.check_complete(result["begin"])
            sql = (
                "SELECT 1/0"
                if target == "postgres"
                else "SELECT missing_column FROM phase66_rows"
            )
        result["observations"].append(query.capture("SELECT 1 AS v"))
        result["observations"].append(
            query.capture(sql, rows=False if case_id == "F_privilege_cleanup" else True)
        )
        result["recovery"] = "failed"
        if case_id == "E_recovery":
            result["state_after_failure"] = (
                int(query.connection.info.transaction_status)
                if target == "postgres"
                else query.connection.in_transaction
            )
        query.rollback()
        if case_id == "E_recovery":
            result["state_after_recovery"] = (
                int(query.connection.info.transaction_status)
                if target == "postgres"
                else query.connection.in_transaction
            )
        result["recovery"] = "success"
        result["observations"].append(query.capture("SELECT 2 AS v"))
        result["session_after"] = query.session_id()
    return result


def verify_image_identity(event: dict[str, Any], pin: dict[str, Any]) -> str:
    """Re-derive the journalled image identity claim and return the bound runtime ID.

    Each observation contract authenticates through the digest that contract
    actually exposes, so renaming the contract alone never transfers the other
    contract's evidence.
    """
    contract, runtime = event.get("contract"), event.get("runtime_image_id")
    descriptor = event.get("descriptor_digest")
    if (
        set(event)
        != {
            "event",
            "reference",
            "contract",
            "runtime_image_id",
            "descriptor_digest",
            "os",
            "architecture",
        }
        or event["reference"] != pin["repository"] + "@" + pin["platform_digest"]
        or (event["os"], event["architecture"]) != ("linux", "amd64")
        or type(runtime) is not str
        or re.fullmatch(r"sha256:[0-9a-f]{64}", runtime) is None
        or not (
            (contract == "descriptor" and descriptor == pin["platform_digest"])
            or (
                contract == "classic"
                and descriptor is None
                and runtime == pin["config_digest"]
            )
        )
    ):
        raise ValueError("unauthenticated image identity observation")
    return runtime


def _verify_receipt(
    receipt: dict[str, Any],
    target: str,
    pins: dict[str, Any],
    pins_digest: str,
    expected: dict[str, Any],
    commit: str,
    run_id: str,
    attempt: int,
    *,
    native_prerequisite: bool = False,
) -> None:
    wanted = NATIVE_PREREQUISITE if native_prerequisite else cases.CASE_IDS
    if native_prerequisite and target != "mysql":
        raise ValueError("native prerequisite target")
    required = {
        "format",
        "target",
        "commit",
        "run_id",
        "run_attempt",
        "inputs",
        "pins_sha256",
        "pin",
        "case_ids",
        "full_manifest",
        "status",
        "drivers",
        "generation",
        "environment",
        "setup",
        "cases",
        "resources",
        "cleanup",
        "failures",
    }
    if (
        set(receipt) != required
        or receipt["format"] != FORMAT
        or receipt["target"] != target
        or receipt["commit"] != commit
        or receipt["run_id"] != run_id
        or type(receipt["run_attempt"]) is not int
        or receipt["run_attempt"] != attempt
    ):
        raise ValueError("stale or malformed receipt identity")
    if (
        receipt["inputs"] != expected
        or receipt["pins_sha256"] != pins_digest
        or receipt["pin"] != pins["targets"][target]
    ):
        raise ValueError("stale or substituted source/pins")
    if (
        receipt["case_ids"] != list(wanted)
        or receipt["full_manifest"] is not (not native_prerequisite)
        or receipt["status"] != "success"
        or receipt["failures"] != []
    ):
        raise ValueError("incomplete required manifest execution")
    if (
        re.fullmatch(r"3\.13\.[0-9]+", str(receipt["drivers"].get("python"))) is None
        or receipt["drivers"]["versions"] != pins["drivers"]
        or receipt["drivers"]["postgres_implementation"] != "binary"
        or receipt["drivers"]["mysql_implementation"] != "pure"
        or receipt["drivers"]["libpq_version"] != 180006
        or receipt["drivers"]["libpq_build_version"] != 180006
    ):
        raise ValueError("wrong actual driver/library identity")
    verify_generation(receipt["generation"], target, expected)
    verify_environment(receipt["environment"], target, pins["targets"][target])
    verify_transport(
        receipt["environment"]["transport"], target, pins["targets"][target]
    )
    setup_sql = [sql for sql, _ in cases.setup(target)]
    setup_sql += (
        [
            "CREDENTIAL_MANAGEMENT",
            "REVOKE ALL ON DATABASE phase66 FROM PUBLIC",
            "GRANT CONNECT ON DATABASE phase66 TO pietto_query",
            "REVOKE CREATE ON SCHEMA public FROM PUBLIC",
            "GRANT USAGE ON SCHEMA public TO pietto_query",
            "GRANT SELECT ON ALL TABLES IN SCHEMA public TO pietto_query",
        ]
        if target == "postgres"
        else [
            "CREDENTIAL_MANAGEMENT",
            "GRANT SELECT ON phase66.* TO 'pietto_query'@'%'",
        ]
    )
    if [observation["sql"] for observation in receipt["setup"]] != setup_sql:
        raise ValueError("fixture loading observation denominator mismatch")
    fixture_params = (
        [
            [],
            [],
            [],
            [
                {"kind": "int", "value": "1"},
                {"kind": "int", "value": "7"},
                {"kind": "null"},
            ],
            [
                {"kind": "int", "value": "2"},
                {"kind": "int", "value": "7"},
                {"kind": "null"},
            ],
            [
                {"kind": "int", "value": "3"},
                {"kind": "int", "value": "9007199254740993"},
                {"kind": "text", "value": cases.TEXT},
            ],
            [],
        ]
        + cases.emission_setup_parameters(target)
        + cases.aggregate_setup_parameters(target)
        + [[], [], []]
        + [[] for _ in cases.row_domain_setup(target)]
        + [[] for _ in setup_sql[len(cases.setup(target)) :]]
    )
    for observation, parameters in zip(receipt["setup"], fixture_params, strict=True):
        cases.check_complete(observation)
        cases.check_identity(
            observation, target, "fixture_manager", prepared=bool(parameters)
        )
        if observation["parameters"] != parameters:
            raise ValueError("fixture parameter substitution")
    if [case["id"] for case in receipt["cases"]] != list(wanted):
        raise ValueError("missing/duplicate/reordered case receipts")
    for case in receipt["cases"]:
        cases.check_case(case, target, receipt["generation"])
        if case["id"] in emission.VARIANTS:
            records = [
                r
                for r in receipt["generation"]["emission"]["records"]
                if r["id"] == case["id"]
            ]
            if [
                (v["variant"], v["public"], v["public_sha256"])
                for v in case["variants"]
            ] != [(r["variant"], r["public"], r["public_sha256"]) for r in records]:
                raise ValueError("installed public artifact/case substitution")
        if case["id"] == emission.CONSOLE_CASE and [
            (w["witness"], w["public_sha256"]) for w in case["witnesses"]
        ] != [
            (r["witness"], r["public_sha256"])
            for r in receipt["generation"]["console"]["records"]
        ]:
            raise ValueError("installed console artifact/case substitution")
        if case["id"] == "F_privilege_cleanup":
            verify_privileges(case["privilege_observations"], target)
    if not native_prerequisite:
        cases.check_relations(receipt["cases"])
    cleanup = receipt["cleanup"]
    closed = [
        event
        for event in receipt["resources"]
        if event.get("event") == "connection_closed"
    ]
    if (
        [event.get("identity") for event in closed] != ["query", "manager"]
        or any(
            type(e.get("session_id")) is not int or e["session_id"] <= 0 for e in closed
        )
        or closed[0]["session_id"] == closed[1]["session_id"]
    ):
        raise ValueError("connection teardown evidence missing")
    sessions = {
        "query": closed[0]["session_id"],
        "fixture_manager": closed[1]["session_id"],
    }
    observations = [*receipt["setup"], receipt["environment"]["query"]]
    for case in receipt["cases"]:
        observations.extend(case["observations"])
        observations.extend(case.get("settings", []))
        observations.extend(case.get("privilege_observations", []))
        if "begin" in case:
            observations.append(case["begin"])
        if "session_before" in case and case["session_before"] != sessions["query"]:
            raise ValueError("recovery/teardown session substitution")
    if target == "mysql":
        observations.extend(
            s["observation"] for s in receipt["environment"]["transport"]["sessions"]
        )
        for observation in observations:
            if observation.get("native") is not None:
                cases.verify_native(observation)
                if (
                    observation["native"]["session_id"]
                    != sessions[observation["identity"]]
                ):
                    raise ValueError("native/teardown session substitution")
    if target == "mysql":
        ca = receipt["environment"]["transport"]["ca"]
        if ca["container_id"] != cleanup["container_id"] or not any(
            event.get("event") == "ca_extracted" and event.get("identity") == ca
            for event in receipt["resources"]
        ):
            raise ValueError("CA does not belong to the acquired container")
        if (
            receipt["environment"]["transport"]["sessions"][1]["session_id"]
            != sessions["query"]
        ):
            raise ValueError("TLS observation belongs to another query session")
    if (
        cleanup.get("status") != "success"
        or cleanup.get("absent") != {"container": True, "network": True}
        or cleanup.get("failures") != []
        or not 0 <= cleanup.get("elapsed_seconds", -1) <= 30
    ):
        raise ValueError("cleanup incomplete, failed or unknown")
    image_observations = [
        event
        for event in receipt["resources"]
        if event.get("event") == "image_verified"
    ]
    if len(image_observations) != 1:
        raise ValueError("missing or duplicated image identity observation")
    runtime_image = verify_image_identity(
        image_observations[0], pins["targets"][target]
    )
    network_observations = [
        event["observation"]
        for event in receipt["resources"]
        if event.get("event") == "network_observed"
    ]
    port_observations = [
        event
        for event in receipt["resources"]
        if event.get("event") == "container_start_observed"
    ]
    if (
        len(network_observations) != 1
        or len(port_observations) != 1
        or network_observations[0].get("id") != cleanup["network_id"]
        or network_observations[0].get("driver") != "bridge"
        or network_observations[0].get("internal") is not False
        or network_observations[0]
        .get("options", {})
        .get("com.docker.network.bridge.gateway_mode_ipv4")
        != "nat"
        or port_observations[0].get("id") != cleanup["container_id"]
        or port_observations[0].get("image") != runtime_image
        or port_observations[0].get("running") is not True
    ):
        raise ValueError("isolated network/port observation mismatch")
    loopback_port(
        port_observations[0]["ports"], "5432" if target == "postgres" else "3306"
    )
    for kind in ("container", "network"):
        value = cleanup.get(kind + "_id")
        if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError("owned resource identity missing")
        events = receipt["resources"]
        acquired = [
            index
            for index, event in enumerate(events)
            if event.get("event") == kind + "_acquired" and event.get("id") == value
        ]
        removed = [
            index
            for index, event in enumerate(events)
            if event.get("event") == kind + "_removed" and event.get("id") == value
        ]
        if len(acquired) != 1 or len(removed) != 1 or acquired[0] >= removed[0]:
            raise ValueError("cleanup/acquisition resource mismatch")
    if [
        event.get("result")
        for event in receipt["resources"]
        if event.get("event") == "cleanup_complete"
    ] != [cleanup]:
        raise ValueError("cleanup journal/result mismatch")


def verify_receipt(
    receipt: dict[str, Any],
    target: str,
    pins: dict[str, Any],
    pins_digest: str,
    expected: dict[str, Any],
    commit: str,
    run_id: str,
    attempt: int,
) -> None:
    try:
        _verify_receipt(
            receipt, target, pins, pins_digest, expected, commit, run_id, attempt
        )
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
        raise ValueError("invalid target receipt: " + type(error).__name__) from error


def verify_native_prerequisite(
    receipt, pins, pins_digest, expected, commit, run_id, attempt
):
    try:
        _verify_receipt(
            receipt,
            "mysql",
            pins,
            pins_digest,
            expected,
            commit,
            run_id,
            attempt,
            native_prerequisite=True,
        )
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
        raise ValueError(
            "invalid native prerequisite: " + type(error).__name__
        ) from error


def verify_directory(
    args: argparse.Namespace, pins: dict[str, Any], pins_digest: str
) -> None:
    expected = inputs()
    targets = (args.target,) if args.target else cases.TARGETS
    if not args.target and (
        args.compiler_status != "success" or args.target_status != "success"
    ):
        raise ValueError("required job failed, cancelled, skipped or absent")
    wanted = {
        f"phase66-{target}-{args.run_id}-{args.run_attempt}.json": target
        for target in targets
    }
    found = tuple(args.evidence_dir.rglob("phase66-*.json"))
    if len(found) != len(wanted) or {path.name for path in found} != set(wanted):
        raise ValueError("receipt file manifest is empty, missing or duplicated")
    for path in found:
        receipt, data = read_json(path)
        verify_receipt(
            receipt,
            wanted[path.name],
            pins,
            pins_digest,
            expected,
            args.expected_commit,
            args.run_id,
            args.run_attempt,
        )
        if args.target:
            if (
                args.artifact_digest != digest(data)
                or not args.artifact_id.isdigit()
                or int(args.artifact_id) <= 0
            ):
                raise ValueError("native upload artifact identity/digest mismatch")


def run_target(args: argparse.Namespace, pins: dict[str, Any], pins_digest: str) -> int:
    if (
        sys.implementation.name != "cpython"
        or sys.version_info[:2] != (3, 13)
        or platform.system() != "Linux"
        or platform.machine() != "x86_64"
    ):
        raise ValueError("target execution requires CPython3.13 on Linux amd64")
    if (
        args.evidence_dir.resolve().is_relative_to(ROOT)
        or args.evidence_dir.is_symlink()
    ):
        raise ValueError("evidence must be outside the repository")
    args.evidence_dir.mkdir(parents=True, mode=0o700, exist_ok=False)
    requested = args.case or list(cases.CASE_IDS)
    if len(set(requested)) != len(requested):
        raise ValueError("duplicate case selection")
    selected = [case for case in cases.CASE_IDS if case in requested]
    expected = inputs()
    commit = (
        command(["git", "rev-parse", "HEAD"], cwd=ROOT, timeout=30).decode().strip()
    )
    if args.expected_commit is not None and args.expected_commit != commit:
        raise ValueError("actual checkout differs from request")
    start_record = {
        "target": args.target,
        "run_id": args.run_id,
        "run_attempt": args.run_attempt,
        "case_ids": selected,
        "full_manifest": selected == list(cases.CASE_IDS),
        "event": "target_start",
    }
    with (args.evidence_dir / "invocation.json").open("w") as stream:
        stream.write(json.dumps(start_record) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    receipt: dict[str, Any] = {
        "format": FORMAT,
        "target": args.target,
        "commit": commit,
        "run_id": args.run_id,
        "run_attempt": args.run_attempt,
        "inputs": expected,
        "pins_sha256": pins_digest,
        "pin": pins["targets"][args.target],
        "case_ids": selected,
        "full_manifest": start_record["full_manifest"],
        "status": "failed",
        "drivers": None,
        "generation": None,
        "environment": None,
        "setup": [],
        "cases": [],
        "resources": [],
        "cleanup": None,
        "failures": [],
    }
    resource: Resources | None = None
    previous_terminate = signal.getsignal(signal.SIGTERM)

    def terminate(signum: int, frame: object) -> None:
        raise KeyboardInterrupt("target execution cancelled")

    signal.signal(signal.SIGTERM, terminate)
    stage = "generation"
    try:
        resource = Resources(
            args.target, pins["targets"][args.target], args.evidence_dir
        )
        receipt["generation"] = installed_generation(
            args.target, args.evidence_dir, expected
        )
        os.environ["PSYCOPG_IMPL"] = "binary"
        receipt["drivers"] = driver_info(pins)
        stage = "acquisition"
        resource.acquire()
        stage = "fixture_setup"
        manager = Observer(args.target, resource.manager, "fixture_manager")
        receipt["environment"] = environment(manager, resource)
        verify_environment(receipt["environment"], args.target, resource.pin)
        for sql, params in cases.setup(args.target):
            observation = manager.capture(
                sql, params, rows=False, prepared=bool(params)
            )
            receipt["setup"].append(observation)
            cases.check_complete(observation)
        for sql, secret in resource.role_statements():
            observation = manager.capture(sql, rows=False, secret=secret)
            receipt["setup"].append(observation)
            cases.check_complete(observation)
        with deadline(min(10, 120 - (time.monotonic() - resource.startup_started))):
            resource.query = resource.connect(query=True)
        query = Observer(args.target, resource.query, "query")
        receipt["environment"]["transport"] = transport(manager, query, resource)
        verify_transport(receipt["environment"]["transport"], args.target, resource.pin)
        stage = "case_execution"
        for case_id in selected:
            result: dict[str, Any] = {"id": case_id, "observations": []}
            receipt["cases"].append(result)
            execute_case(
                case_id, args.target, query, manager, receipt["generation"], result
            )
            cases.check_case(result, args.target, receipt["generation"])
        if receipt["full_manifest"]:
            cases.check_relations(receipt["cases"])
        if inputs() != expected:
            raise ValueError("applicable inputs changed during target execution")
    except BaseException as error:
        receipt["failures"].append(
            error_fact(error, stage)
            | {
                "message": str(error),
                "category": "INFRASTRUCTURE_FAILURE"
                if stage == "acquisition"
                else "UNRESOLVED_ATTRIBUTION",
            }
        )
    finally:
        if resource is not None:
            try:
                receipt["cleanup"] = resource.cleanup()
            except BaseException as error:
                receipt["cleanup"] = {
                    "status": "unknown",
                    "failures": [error_fact(error, "cleanup")],
                }
            receipt["resources"] = resource.events
        if (
            not receipt["failures"]
            and receipt["cleanup"]
            and receipt["cleanup"]["status"] == "success"
        ):
            receipt["status"] = "success"
        if receipt["status"] == "success" and receipt["full_manifest"]:
            try:
                verify_receipt(
                    receipt,
                    args.target,
                    pins,
                    pins_digest,
                    expected,
                    commit,
                    args.run_id,
                    args.run_attempt,
                )
            except Exception as error:
                receipt["status"] = "failed"
                receipt["failures"].append(error_fact(error, "receipt"))
        elif (
            receipt["status"] == "success"
            and args.target == "mysql"
            and selected == list(NATIVE_PREREQUISITE)
        ):
            try:
                verify_native_prerequisite(
                    receipt,
                    pins,
                    pins_digest,
                    expected,
                    commit,
                    args.run_id,
                    args.run_attempt,
                )
            except Exception as error:
                receipt["status"] = "failed"
                receipt["failures"].append(error_fact(error, "prerequisite_receipt"))
        data = canonical(receipt)
        if resource is not None:
            sanitized = resource.without_secrets(data.decode()).encode()
            if sanitized != data:
                receipt["status"] = "failed"
                receipt["failures"].append(
                    {"stage": "receipt", "kind": "CREDENTIAL_REDACTED"}
                )
                data = resource.without_secrets(canonical(receipt).decode()).encode()
        path = (
            args.evidence_dir
            / f"phase66-{args.target}-{args.run_id}-{args.run_attempt}.json"
        )
        if len(data) > MAX_RECEIPT:
            raise ValueError("receipt limit exceeded")
        path.write_bytes(data)
        signal.signal(signal.SIGTERM, previous_terminate)
    print(
        json.dumps(
            {
                "target": args.target,
                "status": receipt["status"],
                "case_ids": selected,
                "full_manifest": receipt["full_manifest"],
                "cleanup": receipt["cleanup"]["status"]
                if receipt["cleanup"]
                else "unknown",
                "receipt": path.name,
            }
        )
    )
    return 0 if receipt["status"] == "success" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("run", "verify-receipts"))
    parser.add_argument("--target", choices=cases.TARGETS)
    parser.add_argument("--pins", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--expected-commit")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", type=int, required=True)
    parser.add_argument("--case", action="append", choices=cases.CASE_IDS)
    parser.add_argument("--artifact-digest", default="")
    parser.add_argument("--artifact-id", default="")
    parser.add_argument("--compiler-status")
    parser.add_argument("--target-status")
    args = parser.parse_args(argv)
    try:
        if (
            re.fullmatch(r"[A-Za-z0-9_-]{1,80}", args.run_id) is None
            or not 1 <= args.run_attempt <= 100
        ):
            raise ValueError("invalid run identity")
        pins, pins_digest = load_pins(args.pins)
        if args.mode == "run":
            if args.target is None:
                raise ValueError("run requires one target")
            return run_target(args, pins, pins_digest)
        if (
            args.expected_commit is None
            or re.fullmatch(r"[0-9a-f]{40}", args.expected_commit) is None
            or args.case
        ):
            raise ValueError("verification requires exact checkout and full manifest")
        verify_directory(args, pins, pins_digest)
        print("Target receipts verified.")
        return 0
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error": type(error).__name__,
                    "reason": str(error),
                }
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
