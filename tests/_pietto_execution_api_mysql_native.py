"""One explicit installed public MySQL witness; imports acquire nothing.

Only campaign opens Docker. Pytest exercises the literal checker, so an
offline fixture cannot become evidence for the native route.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import ssl
import subprocess
import time
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
FORMAT = "pietto.execution-api-mysql-native.v1"
ROWS = [[1, None], [1, None]]
OTEL_WHEELS = (
    "opentelemetry_api-1.33.1-py3-none-any.whl",
    "opentelemetry_sdk-1.33.1-py3-none-any.whl",
    "opentelemetry_semantic_conventions-0.54b1-py3-none-any.whl",
    "wrapt-2.5.0-cp313-cp313-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl",
)
CP312_WRAPT = "wrapt-2.5.0-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl"


class Rejected(ValueError):
    pass


def need(value: object, reason: str) -> None:
    if not value:
        raise Rejected(reason)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def document(value: object, reason: str) -> dict[str, Any]:
    need(type(value) is dict, reason)
    return cast(dict[str, Any], value)


def documents(value: object, reason: str) -> list[dict[str, Any]]:
    need(type(value) is list and all(type(item) is dict for item in value), reason)
    return cast(list[dict[str, Any]], value)


def _check_nonterminal_cases(cases: dict[str, Any]) -> None:
    rows_case = document(cases.get("rows"), "ROWS")
    bundle_case = document(cases.get("bundle"), "BUNDLE")
    empty_case = document(cases.get("empty"), "EMPTY")
    schema_case = document(cases.get("schema"), "SCHEMA")
    need(
        rows_case.get("rows") == ROWS and rows_case.get("end") == "COMPLETE",
        "ROWS",
    )
    need(
        bundle_case.get("rows") == ROWS and bundle_case.get("end") == "COMPLETE",
        "BUNDLE",
    )
    need(
        empty_case.get("rows") == [] and empty_case.get("end") == "COMPLETE",
        "EMPTY",
    )
    need(
        schema_case.get("schema")
        == [["left_id", "int64", False], ["right_key", "int64", True]],
        "SCHEMA",
    )


def check(report: Any) -> dict[str, str]:
    """Independent literal oracle; it performs neither imports nor I/O."""
    need(type(report) is dict and report.get("format") == FORMAT, "ENVELOPE")
    report = cast(dict[str, Any], report)
    need(report.get("status") == "PASS", "STATUS")
    identity = document(report.get("identity"), "IDENTITY")
    need(identity.get("interpreter") == ["CPython", "3.13.13", "Linux"], "INTERPRETER")
    need(identity.get("server") == "8.4.12", "SERVER")
    need(identity.get("wheel_sha256") == report.get("wheel_sha256"), "WHEEL")
    origins = document(identity.get("origins"), "ORIGINS")
    need(
        set(origins) >= {"pietto", "mysql.connector.connection"}
        and all(type(value) is str and len(value) == 64 for value in origins.values()),
        "ORIGINS",
    )
    need(
        identity.get("drivers")
        == {"mysql-connector-python": "26.7.0", "pyarrow": "26.0.0"},
        "DRIVER_PINS",
    )
    telemetry = document(report.get("telemetry"), "OTEL")
    witness_wheels = document(report.get("otel_wheels"), "OTEL_WHEELS")
    need(
        telemetry.get("versions")
        == {
            "opentelemetry-api": "1.33.1",
            "opentelemetry-sdk": "1.33.1",
            "wrapt": "2.5.0",
        }
        and telemetry.get("recording") is True
        and telemetry.get("exporters") == []
        and telemetry.get("selected_wheel", "").startswith("wrapt-2.5.0-cp313-"),
        "OTEL",
    )
    need(
        set(witness_wheels) == set(OTEL_WHEELS)
        and all(
            type(value) is str and len(value) == 64 for value in witness_wheels.values()
        )
        and report.get("otel_unselected") == CP312_WRAPT,
        "OTEL_WHEELS",
    )
    profile = document(report.get("profile"), "PROFILE")
    need(
        profile.get("host") == "localhost" and profile.get("identity_verified") is True,
        "TLS_IDENTITY",
    )
    need(profile.get("tls") in ("TLSv1.2", "TLSv1.3"), "TLS")
    certificate = document(profile.get("certificate"), "TLS_CERTIFICATE")
    service = documents(certificate.get("service"), "TLS_CERTIFICATE")
    need(
        certificate.get("reload") == "ALTER INSTANCE RELOAD TLS"
        and certificate.get("sans") == ["DNS:localhost", "IP Address:127.0.0.1"]
        and [item.get("host") for item in service] == ["127.0.0.1", "localhost"]
        and all(
            item.get("identity_verified") is True
            and item.get("tls") in ("TLSv1.2", "TLSv1.3")
            and item.get("fresh_leaf") is True
            for item in service
        ),
        "TLS_CERTIFICATE",
    )
    attrs_oracle = document(profile.get("attrs_oracle"), "ATTRS_ORACLE")
    need(
        attrs_oracle.get("enabled") is True
        and type(attrs_oracle.get("size")) is int
        and attrs_oracle["size"] > 0
        and attrs_oracle.get("positive") == [["pietto_s06_marker", "present"]],
        "ATTRS_ORACLE",
    )
    sessions = documents(profile.get("sessions"), "SESSIONS")
    kinds = [item.get("kind") for item in sessions]
    need(
        all(type(kind) is str for kind in kinds)
        and sorted(cast(list[str], kinds)) == ["control", "data"],
        "SESSIONS",
    )
    for session in sessions:
        need(
            session.get("attrs") == [] and session.get("connect_args") is False,
            "CONN_ATTRS",
        )
        need(
            session.get("otel") is False and session.get("traceparent") is False, "OTEL"
        )
        need(
            session.get("auth") == "caching_sha2_password"
            and session.get("tls") in ("TLSv1.2", "TLSv1.3"),
            "CONNECTION_PROFILE",
        )
    packets = document(profile.get("packets"), "PACKETS")
    handshake = documents(packets.get("handshake"), "PACKETS")
    query = documents(packets.get("query"), "PACKETS")
    query_attrs = packets.get("query_attrs")
    need(
        len(handshake) == 2
        and all(
            type(item.get("client_flags")) is int
            and item.get("connect_args") is False
            and item.get("attribute_encoding") is False
            and item.get("traceparent") is False
            for item in handshake
        )
        and bool(query)
        and all(item.get("traceparent") is False for item in query)
        and type(query_attrs) is list
        and bool(query_attrs)
        and all(item in (None, []) for item in query_attrs)
        and packets.get("prepare") is True
        and packets.get("execute") is True
        and packets.get("control") is True,
        "PACKETS",
    )
    cases = document(report.get("cases"), "CASES")
    need(
        set(cases) == {"bundle", "cancel", "deadline", "empty", "rows", "schema"},
        "CASES",
    )
    _check_nonterminal_cases(cases)
    cancel = document(cases["cancel"], "CANCEL")
    need(
        cancel.get("end") == "CANCELLED"
        and cancel.get("cancel")
        in (
            {"requested": True, "sent": True, "observed": False},
            {"requested": True, "sent": True, "observed": True},
        )
        and cancel.get("primary", [None])[0] == "PIE-R3009"
        and cancel.get("error", {}).get("code") == "PIE-R3009"
        and cancel.get("control_kill") is True
        and cancel.get("batches") == 0
        and cancel.get("rows") == 0
        and cancel.get("source") == "INCOMPLETE"
        and cancel.get("delivery") == "FAILED"
        and cancel.get("transaction") == "UNKNOWN"
        and cancel.get("remote") == "REMOTE_QUIESCENCE_UNCONFIRMED"
        and cancel.get("consumer_thread_joined") is True
        and cancel.get("late_unchanged") is True,
        "CANCEL_FACTS",
    )
    deadline = document(cases["deadline"], "DEADLINE")
    deadline_primary = deadline.get("primary")
    deadline_won = (
        deadline.get("end") == "DEADLINE"
        and type(deadline_primary) is list
        and deadline_primary[0] == "PIE-R3001"
        and deadline.get("deadline_expired") is True
        and deadline.get("cancel")
        in (
            {"requested": True, "sent": True, "observed": False},
            {"requested": True, "sent": True, "observed": True},
        )
        and deadline.get("control_kill") is True
    )
    server_timeout_won = (
        deadline.get("end") == "FAILED"
        and type(deadline_primary) is list
        and deadline_primary[0] == "PIE-R3002"
        and deadline.get("deadline_expired") is False
        and deadline.get("cancel")
        == {"requested": False, "sent": False, "observed": False}
        and deadline.get("control_kill") is False
    )
    need(
        type(deadline_primary) is list
        and len(deadline_primary) == 3
        and (deadline_won or server_timeout_won)
        and deadline.get("consumer_thread_joined") is True
        and deadline.get("batches") == 0
        and deadline.get("rows") == 0
        and deadline.get("late_unchanged") is True,
        "DEADLINE_FACTS",
    )
    for name, value in (("cancel", cancel), ("deadline", deadline)):
        blocked = document(value.get("blocked"), name.upper() + "_BLOCKED")
        need(
            type(blocked.get("session")) is int
            and type(blocked.get("event")) is str
            and type(blocked.get("sql_sha256")) is str
            and re.fullmatch(r"[0-9a-f]{64}", blocked["sql_sha256"]) is not None
            and blocked.get("native_statement") == "NativeStatement"
            and blocked.get("purpose") == "query",
            name.upper() + "_BLOCKED",
        )
        server = document(blocked.get("server"), name.upper() + "_SERVER")
        need(
            server
            == {
                "current_rows": 1,
                "statement_event": "statement/com/Execute",
                "end_event_id": None,
                "process_state": "executing",
                "process_command": "Execute",
            },
            name.upper() + "_SERVER",
        )
    need(
        report.get("factory")
        == {
            "origin": "live",
            "module": "main.pietto",
            "kind": "table",
            "name": "result",
            "dialect": "mysql",
        },
        "PUBLIC_FACTORY",
    )
    need(report.get("cleanup") == "PASS", "CLEANUP")
    return {"family": "mysql-native", "verdict": "ACCEPTED"}


WORKER = r"""
import hashlib, importlib.metadata, json, platform, sys, threading, time
from pathlib import Path
config=json.loads(sys.stdin.readline())
sys.path.insert(0,config["tests"])
from _pietto_execution_deployment_probe import Calls
import pietto.execution as pe
import pyarrow as pa
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

class WitnessCalls(Calls):
 def __init__(self,owner):
  super().__init__(owner); self.handshake=[]; self.query=[]
 def observe(self,frame,event,result):
  super().observe(frame,event,result)
  if event!="return" or frame.f_code.co_filename not in self.files:return
  local,name=frame.f_locals,frame.f_code.co_name
  connection=local.get("self")
  if name=="make_auth":
   from mysql.connector.constants import ClientFlag
   flags=local.get("client_flags")
   if type(flags) is int:
    data=bytes(result[0])
    self.handshake.append({"client_flags":flags,
      "connect_args":bool(flags&ClientFlag.CONNECT_ARGS),
      "attribute_encoding":bool(flags&ClientFlag.CONNECT_ARGS),
      "traceparent":b"traceparent" in data})
  elif name=="_send_cmd" and any(connection is c for c in self.owner._connections):
   data=local.get("packet") or local.get("argument")
   if isinstance(data,(bytes,bytearray)):
    self.query.append({"session":connection.connection_id,"command":local.get("command"),
      "bytes":len(data),"traceparent":b"traceparent" in bytes(data)})

def outcome(handle):
 value=handle.outcome
 return {"end":value.end,"source":value.source,"transaction":value.transaction,
  "delivery":value.delivery,"cleanup":value.cleanup,"remote":value.remote_source_use_end,
  "rows":value.rows,"batches":value.batches,"deadline_expired":value.deadline_expired}

def attributes(owner,observer):
 data,control=owner._owned_connection,owner._owned_control_connection
 ids={"data":data.connection_id,"control":control.connection_id}
 cursor=control.cursor(read_timeout=10,write_timeout=2)
 try:
  cursor.execute("SELECT PROCESSLIST_ID,ATTR_NAME,ATTR_VALUE FROM performance_schema.session_connect_attrs WHERE PROCESSLIST_ID IN (%s,%s) ORDER BY PROCESSLIST_ID,ORDINAL_POSITION",tuple(ids.values()))
  found={value:[] for value in ids.values()}
  for process_id,name,value in cursor.fetchall():found[process_id].append([name,value])
 finally:cursor.close()
 from mysql.connector.constants import ClientFlag
 profiles={kind:(connection._socket.sock.version(),connection._authenticator._auth_strategy.name,
  bool(connection._client_flags&ClientFlag.CONNECT_ARGS),connection.otel_context_propagation)
  for kind,connection in (("data",data),("control",control))}
 events=[item["value"].get("query_attrs") for item in observer.events if item["event"]=="make_stmt_execute.call"]
 names={item["event"] for item in observer.events}
 return {"sessions":[{"kind":kind,"attrs":found[session],"connect_args":connect_args,
   "otel":otel,"traceparent":any(item["traceparent"] for item in observer.handshake+observer.query),
   "tls":tls,"auth":auth} for kind,session in ids.items() for tls,auth,connect_args,otel in [profiles[kind]]],
  "packets":{"handshake":observer.handshake,"query":observer.query,"query_attrs":events,
   "prepare":"cmd_stmt_prepare.call" in names,"execute":"make_stmt_execute.call" in names,
   "control":"cmd_query.call" in names}}

def query():
 return pe.compile_query(config["project"],module="main.pietto",kind=config.get("kind","table"),name="result",
  dialect="mysql",emission_contract="contract.json")
access=pe.MySQLAccess("localhost",config["port"],"phase66","pietto_query",config["password"],config["ca"],"pietto_query@%")
premise=pe.MySQLDeploymentPremise(schemas=("phase66",))
def attempt(item,observe=False,limits=None):
 handle=pe.execute(item,route="mysql_rows",access=access,premise=premise,limits=limits or pe.ExecutionLimits(batch_rows=1,seconds=5))
 rows=[]; schema=None; profile=None
 observer=WitnessCalls(handle._owner) if observe else None
 try:
  if observer is None:
   with handle:
    for batch in handle:
     with batch:rows.extend(pa.record_batch(batch).to_pylist())
  else:
   with observer:
    with handle:
     while True:
      try:batch=next(handle)
      except StopIteration:break
      with batch:
       if schema is None:schema=[[f.name,str(f.type),f.nullable] for f in pa.record_batch(batch).schema]
       rows.extend(pa.record_batch(batch).to_pylist())
      if profile is None:profile=attributes(handle._owner,observer)
 except pe.AttemptFailed:pass
 value=outcome(handle); value["rows"]=[[r["left_id"],r["right_key"]] for r in rows]
 if schema is not None:value["schema"]=schema
 return value,profile

def terminal(item,kind):
 handle=pe.execute(item,route="mysql_rows",access=access,premise=premise,
  limits=pe.ExecutionLimits(batch_rows=1,seconds=config["terminal_seconds"]),isolation="serializable")
 received={}; done=threading.Event()
 def consume():
  try:
   next(handle)
  except pe.AttemptFailed as error:
   received.update(code=error.code,detail=error.detail)
  finally:done.set()
 with handle:
  print(json.dumps({"open_ready":{"session":handle._owner.session_id}}),flush=True)
  if sys.stdin.readline().strip()!="go":raise RuntimeError("TERMINAL_GO")
  thread=threading.Thread(target=consume,name="pietto-s06-public-terminal")
  thread.start()
  until=time.monotonic()+10
  while handle._owner._statement is None and time.monotonic()<until:time.sleep(.01)
  active=handle._owner._statement
  if active is None:raise RuntimeError("SUBMITTED_STATEMENT_NOT_OBSERVED")
  while handle._owner._active is not active and time.monotonic()<until:time.sleep(.01)
  if handle._owner._active is not active:raise RuntimeError("ACTIVE_STATEMENT_NOT_OBSERVED")
  print(json.dumps({"active_ready":{"session":handle._owner.session_id,
   "native_statement":type(active).__name__,"purpose":active.purpose,
   "isolation":handle._owner.request.isolation,
   "sql_sha256":hashlib.sha256(active.sql).hexdigest()}}),flush=True)
  if sys.stdin.readline().strip()!=kind:raise RuntimeError("TERMINAL_GATE")
  if kind=="cancel":received["receipt"]=handle.cancel()
  if not done.wait(20):raise RuntimeError("TERMINAL_THREAD")
  thread.join()
 value=outcome(handle); late=value.copy(); late_result=handle.cancel(); late_unchanged=(late_result is None and outcome(handle)==late); actual=handle.outcome; primary=actual.primary
 value.update(cancel={"requested":actual.cancel_requested,"sent":actual.cancel_sent,"observed":actual.cancel_observed},
  primary=None if primary is None else [primary.code,primary.detail,primary.phase],
  error=received,consumer_thread_joined=not thread.is_alive(),
  control_kill="kill_query_send_returned" in [event[0] for event in handle._owner.control_events],late_unchanged=late_unchanged)
 return value

provider=TracerProvider();trace.set_tracer_provider(provider)
with trace.get_tracer("pietto.s06.witness").start_as_current_span("mysql-public") as span:
 if not span.is_recording():raise RuntimeError("OTEL_NOT_RECORDING")
 q=query()
 if config["case"]=="empty":
  result={"empty":attempt(q)[0]}
 elif config["case"]=="terminal":
  result={"terminal":terminal(q,config["terminal"])}
 else:
  rows,profile=attempt(q,True)
  bundle=pe.export_bundle(q)
  bundled=pe.load_bundle(bundle.payload,expected_pin=bundle.pin,accepted_producer=bundle.producer,accepted_compatibility=bundle.compatibility)
  loaded,_=attempt(bundled)
  result={"rows":rows,"bundle":loaded,"schema":{"schema":rows.get("schema")},"profile":profile,
   "factory":{"origin":q.origin,"module":q.module,"kind":q.kind,"name":q.name,"dialect":q.dialect}}
result["telemetry"]={"versions":{name:importlib.metadata.version(name) for name in ("opentelemetry-api","opentelemetry-sdk","wrapt")},
 "recording":True,"exporters":[],"selected_wheel":config["selected_wheel"]}
result["identity"]={"interpreter":[platform.python_implementation(),platform.python_version(),platform.system()],
 "origins":{name:hashlib.sha256(Path(__import__(name,fromlist=["*"]).__file__).read_bytes()).hexdigest() for name in ("pietto","mysql.connector.connection")},
 "drivers":{name:importlib.metadata.version(name) for name in ("mysql-connector-python","pyarrow")}}
print(json.dumps(result),flush=True)
"""


def _otel_wheels(directory: Path) -> dict[str, str]:
    expected = (*OTEL_WHEELS, CP312_WRAPT)
    need(all((directory / name).is_file() for name in expected), "OTEL_WHEELHOUSE")
    return {name: sha256(directory / name) for name in OTEL_WHEELS}


def _host_openssl(resource, directory: Path, stage: str, *arguments: str) -> str:
    """Run the host tool without recording its output beside private key material."""
    try:
        result = subprocess.run(
            ("openssl", *arguments),
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        resource.event(
            "native_tls_host_openssl",
            stage=stage,
            kind=type(error).__name__,
        )
        raise ValueError("MYSQL_TLS_HOST_OPENSSL") from error
    resource.event(
        "native_tls_host_openssl",
        stage=stage,
        returncode=result.returncode,
        stdout_bytes=len(result.stdout.encode()),
        stderr_bytes=len(result.stderr.encode()),
    )
    if result.returncode:
        raise ValueError("MYSQL_TLS_HOST_OPENSSL")
    return result.stdout


def _inject_tls_file(resource, path: Path, name: str, mode: str) -> None:
    from _pietto_target_conformance_resources import ENDPOINT, clean_environment

    result = subprocess.run(
        (
            "docker",
            "--config",
            str(resource.docker_config),
            "--host",
            ENDPOINT,
            "container",
            "exec",
            "-i",
            resource.container_id,
            "sh",
            "-ec",
            "umask 077; cat > /var/lib/mysql/"
            + name
            + " && chown mysql:mysql /var/lib/mysql/"
            + name
            + " && chmod "
            + mode
            + " /var/lib/mysql/"
            + name,
        ),
        env=clean_environment(),
        input=path.read_bytes(),
        capture_output=True,
        timeout=30,
        check=False,
    )
    resource.event(
        "native_tls_container_write",
        name=name,
        returncode=result.returncode,
        stdout_bytes=len(result.stdout),
        stderr_bytes=len(result.stderr),
    )
    if result.returncode:
        raise ValueError("MYSQL_TLS_CONTAINER_WRITE")
    observed = resource.docker(
        "container",
        "exec",
        resource.container_id,
        "sha256sum",
        "/var/lib/mysql/" + name,
        timeout=5,
    ).split()
    if len(observed) != 2 or re.fullmatch(r"[0-9a-f]{64}", observed[0]) is None:
        raise ValueError("MYSQL_TLS_CONTAINER_DIGEST")
    matches = observed[0] == sha256(path)
    resource.event("native_tls_container_material", name=name, matches=matches)
    if not matches:
        raise ValueError("MYSQL_TLS_CONTAINER_DIGEST")


def _reload_tls(resource) -> None:
    """Keep reload warnings on the manager connection and record no server text."""
    cursor = resource.manager.cursor()
    try:
        cursor.execute("ALTER INSTANCE RELOAD TLS")
        cursor.execute("SHOW WARNINGS")
        warnings = cursor.fetchall()
        cursor.execute(
            "SELECT CHANNEL,PROPERTY,VALUE FROM performance_schema.tls_channel_status "
            "WHERE CHANNEL='mysql_main' ORDER BY PROPERTY"
        )
        channel = cursor.fetchall()
    finally:
        cursor.close()

    def category(message: object) -> str:
        value = str(message).lower()
        if "certificate" in value:
            return "certificate"
        if "key" in value:
            return "key"
        if "permission" in value:
            return "permission"
        if "file" in value or "path" in value:
            return "file"
        return "other"

    resource.event(
        "native_tls_reload_observed",
        warnings=[
            {
                "level": str(level),
                "code": int(code),
                "category": category(message),
            }
            for level, code, message in warnings
        ],
        main_channel_properties=[
            str(property_name)
            for channel_name, property_name, _value in channel
            if channel_name == "mysql_main"
        ],
        main_channel_files={
            str(property_name): str(value) == expected
            for property_name, expected in (
                ("Current_tls_ca", "ca.pem"),
                ("Current_tls_cert", "server-cert.pem"),
                ("Current_tls_key", "server-key.pem"),
            )
            for channel_name, observed_property, value in channel
            if channel_name == "mysql_main" and observed_property == property_name
        },
    )


def _configure_tls(resource) -> dict[str, Any]:
    """Replace only the owned tmpfs TLS files and ask MySQL to reload them."""
    from _pietto_execution_source_assurance_probe import manager

    paths = dict(
        manager(
            resource,
            "SHOW VARIABLES WHERE Variable_name IN ('ssl_ca','ssl_cert','ssl_key')",
        )
    )
    expected = {
        "ssl_ca": "ca.pem",
        "ssl_cert": "server-cert.pem",
        "ssl_key": "server-key.pem",
    }
    if paths != expected:
        raise ValueError("MYSQL_TLS_PATHS")
    try:
        version = resource.docker(
            "container", "exec", resource.container_id, "openssl", "version", timeout=5
        )
    except RuntimeError:
        resource.event("native_tls_image_openssl", available=False)
    else:
        if re.fullmatch(r"OpenSSL [A-Za-z0-9._ -]+", version) is None:
            raise ValueError("MYSQL_TLS_IMAGE_OPENSSL_VERSION")
        resource.event("native_tls_image_openssl", available=True, version=version)
    tls = resource.private / "native-tls"
    tls.mkdir(mode=0o700)
    _host_openssl(
        resource,
        tls,
        "ca",
        "req",
        "-x509",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-sha256",
        "-days",
        "1",
        "-subj",
        "/CN=pietto-native-ca",
        "-addext",
        "basicConstraints=critical,CA:true",
        "-keyout",
        "ca-key.pem",
        "-out",
        "ca.pem",
    )
    _host_openssl(
        resource,
        tls,
        "server_csr",
        "req",
        "-new",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-sha256",
        "-subj",
        "/CN=localhost",
        "-addext",
        "subjectAltName=DNS:localhost,IP:127.0.0.1",
        "-keyout",
        "server-key.pem",
        "-out",
        "server.csr",
    )
    _host_openssl(
        resource,
        tls,
        "server_certificate",
        "x509",
        "-req",
        "-in",
        "server.csr",
        "-CA",
        "ca.pem",
        "-CAkey",
        "ca-key.pem",
        "-CAcreateserial",
        "-days",
        "1",
        "-sha256",
        "-copy_extensions",
        "copy",
        "-out",
        "server-cert.pem",
    )
    resource.ca_path.write_bytes((tls / "ca.pem").read_bytes())
    for name, mode in (
        ("ca.pem", "644"),
        ("server-cert.pem", "644"),
        ("server-key.pem", "600"),
    ):
        _inject_tls_file(resource, tls / name, name, mode)
    _reload_tls(resource)
    san = _host_openssl(
        resource,
        tls,
        "verify_san",
        "x509",
        "-in",
        "server-cert.pem",
        "-noout",
        "-ext",
        "subjectAltName",
    )
    sans = re.findall(r"DNS:localhost|IP Address:127\.0\.0\.1", san)
    if sans != ["DNS:localhost", "IP Address:127.0.0.1"]:
        raise ValueError("MYSQL_TLS_SAN")
    resource.ca_identity = {
        "container_id": resource.container_id,
        "image_config": resource.pin["config_digest"],
        "sha256": sha256(resource.ca_path),
    }
    resource.event("native_tls_reloaded", identity=resource.ca_identity, sans=sans)
    import mysql.connector

    expected_leaf = ssl.PEM_cert_to_DER_cert((tls / "server-cert.pem").read_text())
    service = []
    for host in ("127.0.0.1", "localhost"):
        try:
            connection = mysql.connector.connect(
                host=host,
                port=resource.port,
                database="phase66",
                user="root",
                password=resource._passwords[0],
                ssl_ca=str(resource.ca_path),
                ssl_verify_cert=True,
                ssl_verify_identity=True,
                tls_versions=["TLSv1.2", "TLSv1.3"],
                use_pure=True,
            )
        except Exception as error:
            message = str(error).lower()
            resource.event(
                "native_tls_service_probe",
                host=host,
                kind=type(error).__name__,
                errno=getattr(error, "errno", None),
                sqlstate=getattr(error, "sqlstate", None),
                reason=(
                    "certificate"
                    if "certificate" in message
                    else "tls"
                    if "ssl" in message or "tls" in message
                    else "other"
                ),
            )
            raise
        try:
            socket = getattr(connection, "_socket", None)
            tls_version = getattr(
                getattr(socket, "sock", None), "version", lambda: None
            )()
            if type(tls_version) is not str:
                raise ValueError("MYSQL_TLS_SOCKET")
            leaf = getattr(
                getattr(socket, "sock", None), "getpeercert", lambda **_: None
            )(binary_form=True)
            if (
                not isinstance(leaf, bytes)
                or hashlib.sha256(leaf).digest()
                != hashlib.sha256(expected_leaf).digest()
            ):
                raise ValueError("MYSQL_TLS_LEAF")
            service.append(
                {
                    "host": host,
                    "identity_verified": True,
                    "tls": tls_version,
                    "fresh_leaf": True,
                }
            )
        finally:
            connection.close()
        resource.event("native_tls_service_probe", host=host, kind="PASS")
    return {"reload": "ALTER INSTANCE RELOAD TLS", "sans": sans, "service": service}


def _attrs_oracle(resource) -> dict[str, Any]:
    """A server positive prevents a disabled attrs table passing as empty."""
    from _pietto_execution_source_assurance_probe import manager
    import mysql.connector

    enabled = manager(resource, "SELECT @@performance_schema")[0][0] == 1
    size = int(
        manager(resource, "SELECT @@performance_schema_session_connect_attrs_size")[0][
            0
        ]
    )
    try:
        positive = mysql.connector.connect(
            host="localhost",
            port=resource.port,
            database="phase66",
            user="root",
            password=resource._passwords[0],
            ssl_ca=str(resource.ca_path),
            ssl_verify_cert=True,
            ssl_verify_identity=True,
            tls_versions=["TLSv1.2", "TLSv1.3"],
            use_pure=True,
            conn_attrs={"pietto_s06_marker": "present"},
        )
    except Exception as error:
        message = str(error).lower()
        resource.event(
            "native_attrs_oracle_connection",
            kind=type(error).__name__,
            errno=getattr(error, "errno", None),
            sqlstate=getattr(error, "sqlstate", None),
            reason=(
                "certificate"
                if "certificate" in message
                else "tls"
                if "ssl" in message or "tls" in message
                else "other"
            ),
        )
        raise
    try:
        rows = manager(
            resource,
            "SELECT ATTR_NAME,ATTR_VALUE FROM performance_schema.session_connect_attrs "
            "WHERE PROCESSLIST_ID=? AND ATTR_NAME='pietto_s06_marker'",
            (positive.connection_id,),
        )
    finally:
        positive.close()
    positive_rows = [
        [value.decode("utf-8") if isinstance(value, bytes) else value for value in row]
        for row in rows
    ]
    if any(
        len(row) != 2 or any(type(value) is not str for value in row)
        for row in positive_rows
    ):
        raise ValueError("MYSQL_ATTRS_ORACLE")
    return {"enabled": enabled, "size": size, "positive": positive_rows}


def _public_project(directory: Path) -> Path:
    """The public compile factory's project, independent of private templates."""
    project = directory / "public-project"
    project.mkdir(mode=0o700)
    (project / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n'
    )
    (project / "main.pietto").write_text(
        """shape Row:
    left_id: Int not null
    right_key: Int nullable
source rows: Row is mysql.table("phase66.s06_public_rows")
table result:
    from rows
    select:
        left_id
        right_key
"""
    )
    contract = {
        "format": "pietto.emission-contract.v1",
        "target": {"family": "mysql", "release": "8.4.12"},
        "sources": [
            {
                "selector": {"module": "main.pietto", "kind": "source", "name": "rows"},
                "relation": {"namespace": "phase66", "name": "s06_public_rows"},
                "scan": "relation_rows",
                "fields": [
                    {
                        "ordinal": 0,
                        "name": "left_id",
                        "column": "left_id",
                        "representation": {
                            "storage": {"kind": "my_bigint"},
                            "nullable": False,
                            "domain": {
                                "kind": "int_range",
                                "min": "-9007199254740993",
                                "max": "9007199254740993",
                            },
                        },
                    },
                    {
                        "ordinal": 1,
                        "name": "right_key",
                        "column": "right_key",
                        "representation": {
                            "storage": {"kind": "my_bigint"},
                            "nullable": True,
                            "domain": {
                                "kind": "int_range",
                                "min": "-9007199254740993",
                                "max": "9007199254740993",
                            },
                        },
                    },
                ],
                "premises": [
                    {"key": "row_domain_matches", "scope": "source", "value": True},
                    {"key": "read_only_object", "scope": "source", "value": True},
                ],
            }
        ],
        "environment": [
            {"key": "client_encoding", "scope": "statement", "value": "utf8mb4"},
            {
                "key": "operator_environment",
                "scope": "statement",
                "value": "builtin_only",
            },
        ],
    }
    (project / "contract.json").write_text(json.dumps(contract, sort_keys=True))
    return project


def _terminal_project(directory: Path) -> Path:
    """A selective aggregate keeps the public native statement active."""
    project = directory / "terminal-project"
    project.mkdir(mode=0o700)
    (project / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n'
    )
    (project / "main.pietto").write_text(
        """shape Row:
    id: Int not null
source rows: Row is mysql.table("phase66.s06_public_heavy_left")
source other: Row is mysql.table("phase66.s06_public_heavy_right")
query result:
    from rows
    cross join other as joined:
        from rows
    where rows.id < joined.id
    select:
        total = count()
"""
    )
    contract = {
        "format": "pietto.emission-contract.v1",
        "target": {"family": "mysql", "release": "8.4.12"},
        "sources": [
            {
                "selector": {"module": "main.pietto", "kind": "source", "name": "rows"},
                "relation": {"namespace": "phase66", "name": "s06_public_heavy_left"},
                "scan": "relation_rows",
                "fields": [
                    {
                        "ordinal": 0,
                        "name": "id",
                        "column": "id",
                        "representation": {
                            "storage": {"kind": "my_bigint"},
                            "nullable": False,
                            "domain": {
                                "kind": "int_range",
                                "min": "-9007199254740993",
                                "max": "9007199254740993",
                            },
                        },
                    }
                ],
                "premises": [
                    {"key": "row_domain_matches", "scope": "source", "value": True},
                    {"key": "read_only_object", "scope": "source", "value": True},
                ],
            },
            {
                "selector": {
                    "module": "main.pietto",
                    "kind": "source",
                    "name": "other",
                },
                "relation": {"namespace": "phase66", "name": "s06_public_heavy_right"},
                "scan": "relation_rows",
                "fields": [
                    {
                        "ordinal": 0,
                        "name": "id",
                        "column": "id",
                        "representation": {
                            "storage": {"kind": "my_bigint"},
                            "nullable": False,
                            "domain": {
                                "kind": "int_range",
                                "min": "-9007199254740993",
                                "max": "9007199254740993",
                            },
                        },
                    }
                ],
                "premises": [
                    {"key": "row_domain_matches", "scope": "source", "value": True},
                    {"key": "read_only_object", "scope": "source", "value": True},
                ],
            },
        ],
        "environment": [
            {"key": "client_encoding", "scope": "statement", "value": "utf8mb4"},
            {
                "key": "identifier_case",
                "scope": "statement",
                "value": "lower_case_table_names=0",
            },
            {
                "key": "operator_environment",
                "scope": "statement",
                "value": "builtin_only",
            },
        ],
    }
    (project / "contract.json").write_text(json.dumps(contract, sort_keys=True))
    return project


def _worker(python: Path, directory: Path, config: dict[str, Any]) -> dict[str, Any]:
    from _pietto_target_conformance_resources import clean_environment

    try:
        result = subprocess.run(
            [str(python), "-I", "-B", "-c", WORKER],
            cwd=directory,
            env=clean_environment(),
            input=json.dumps(config),
            text=True,
            capture_output=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired as error:
        raise ValueError("MYSQL_NATIVE_WORKER_TIMEOUT") from error
    lines = result.stdout.splitlines()
    if result.returncode or not lines:
        raise ValueError("MYSQL_NATIVE_WORKER:" + str(result.returncode))
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError as error:
        raise ValueError("MYSQL_NATIVE_WORKER_JSON") from error


def _worker_line(process, reason: str, seconds: float = 15) -> str:
    import selectors

    if process.stdout is None:
        raise ValueError(reason + "_STDOUT")
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        if not selector.select(timeout=seconds):
            raise ValueError(reason + "_TIMEOUT")
        line = process.stdout.readline()
    finally:
        selector.close()
    if not line:
        raise ValueError(reason + "_EOF")
    return line


def _send_worker_config(process, config: dict[str, Any]) -> None:
    if process.stdin is None:
        raise ValueError("TERMINAL_WORKER_STDIN")
    process.stdin.write(json.dumps(config) + "\n")
    process.stdin.flush()


def _terminal_child_failure(resource, process, phase: str) -> None:
    if process.stderr is None:
        return
    detail = resource.without_secrets(process.stderr.read())
    diagnostic = resource.private / ("terminal-" + phase + "-stderr.txt")
    diagnostic.write_text(detail)
    diagnostic.chmod(0o600)
    match = re.findall(
        r"^([A-Za-z_.]+(?:Error|Exception|AttemptFailed|CompileRejected|RequestRejected))"
        r": ?(.*)$",
        detail,
        re.MULTILINE,
    )
    tokens = {
        "ACTIVE_STATEMENT_NOT_OBSERVED",
        "EXECUTION_CANCELED",
        "EXECUTION_DEADLINE",
        "EXECUTION_DEPENDENCY_MISSING",
    }
    reason = None
    if match:
        message = match[-1][1]
        code = re.search(r"PIE-R[0-9]{4}", message)
        token = re.search(r"\b[A-Z][A-Z0-9_]{2,}\b", message)
        reason = (
            code.group()
            if code
            else token.group()
            if token and token.group() in tokens
            else None
        )
    resource.event(
        "native_terminal_worker_failure",
        phase=phase,
        returncode=process.poll(),
        stderr_sha256=sha256(diagnostic),
        failure=(
            (
                {"kind": match[-1][0].rsplit(".", 1)[-1]}
                | ({"reason": reason} if reason else {})
            )
            if match
            else {"kind": "UNKNOWN"}
        ),
    )


def _terminal_worker(
    python: Path, directory: Path, config: dict[str, Any], resource, terminal: str
) -> dict[str, Any]:
    """Observe a public worker's genuinely blocked statement before its terminal."""
    from _pietto_execution_source_assurance_probe import manager
    from _pietto_target_conformance_resources import clean_environment
    import mysql.connector

    process = subprocess.Popen(
        [str(python), "-I", "-B", "-c", WORKER],
        cwd=directory,
        env=clean_environment(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    started = time.monotonic()
    locked = False
    try:
        assert process.stdin is not None and process.stdout is not None
        _send_worker_config(process, config)
        try:
            opened = document(
                json.loads(_worker_line(process, "PUBLIC_OPEN_UNOBSERVED")),
                "PUBLIC_OPEN_UNOBSERVED",
            )
        except ValueError as error:
            if str(error) == "PUBLIC_OPEN_UNOBSERVED_EOF":
                _terminal_child_failure(resource, process, "open")
            raise
        open_ready = document(opened.get("open_ready"), "PUBLIC_OPEN_UNOBSERVED")
        if open_ready.get("session") is None:
            raise ValueError("PUBLIC_OPEN_UNOBSERVED")
        manager(resource, "START TRANSACTION")
        manager(
            resource,
            "SELECT left_id FROM phase66.s06_public_rows "
            "WHERE left_id=1 LIMIT 1 FOR UPDATE",
        )
        locked = True
        process.stdin.write("go\n")
        process.stdin.flush()
        try:
            active = document(
                json.loads(_worker_line(process, "OWNED_QUERY_UNOBSERVED")),
                "OWNED_QUERY_UNOBSERVED",
            )
        except ValueError as error:
            if str(error) == "OWNED_QUERY_UNOBSERVED_EOF":
                _terminal_child_failure(resource, process, "active")
            raise
        facts = document(active.get("active_ready"), "OWNED_QUERY_UNOBSERVED")
        if (
            facts.get("native_statement") != "NativeStatement"
            or facts.get("purpose") != "query"
            or facts.get("isolation") != "serializable"
            or re.fullmatch(r"[0-9a-f]{64}", str(facts.get("sql_sha256"))) is None
            or type(facts.get("session")) is not int
        ):
            raise ValueError("OWNED_QUERY_UNOBSERVED")
        session = facts["session"]
        observer = mysql.connector.connect(
            host="localhost",
            port=resource.port,
            database="phase66",
            user="root",
            password=resource._passwords[0],
            ssl_ca=str(resource.ca_path),
            ssl_verify_cert=True,
            ssl_verify_identity=True,
            tls_versions=["TLSv1.2", "TLSv1.3"],
            use_pure=True,
        )
        try:
            rows: list[tuple[object, object, object]] = []
            until = time.monotonic() + 10
            while time.monotonic() < until:
                with observer.cursor() as cursor:
                    cursor.execute(
                        "SELECT EVENT_NAME,END_EVENT_ID,SQL_TEXT "
                        "FROM performance_schema.events_statements_current "
                        "WHERE THREAD_ID=(SELECT THREAD_ID FROM performance_schema.threads WHERE PROCESSLIST_ID=%s)",
                        (session,),
                    )
                    observed = cursor.fetchall()
                rows = []
                for row in observed:
                    if not isinstance(row, tuple) or len(row) != 3:
                        raise ValueError("BLOCKED_STATEMENT_UNOBSERVED")
                    event, end_event_id, sql_text = row
                    rows.append((event, end_event_id, sql_text))
                if len(rows) == 1 and type(rows[0][0]) is str:
                    break
                time.sleep(0.02)
            with observer.cursor() as cursor:
                cursor.execute(
                    "SELECT ENABLED FROM performance_schema.setup_consumers "
                    "WHERE NAME='events_statements_current'"
                )
                consumer_rows = cursor.fetchall()
                cursor.execute(
                    "SELECT ENABLED,TIMED FROM performance_schema.setup_instruments "
                    "WHERE NAME='statement/sql/select'"
                )
                instrument_rows = cursor.fetchall()
                cursor.execute(
                    "SELECT STATE,COMMAND FROM information_schema.PROCESSLIST WHERE ID=%s",
                    (session,),
                )
                process_state_rows = cursor.fetchall()
                cursor.execute(
                    "SELECT COUNT(*) FROM performance_schema.data_lock_waits w "
                    "JOIN performance_schema.threads t "
                    "ON t.THREAD_ID=w.REQUESTING_THREAD_ID WHERE t.PROCESSLIST_ID=%s",
                    (session,),
                )
                lock_wait_rows = cursor.fetchall()
            current = rows[0] if len(rows) == 1 else (None, None, None)
            consumer: tuple[object, ...] = ()
            if len(consumer_rows) == 1 and isinstance(consumer_rows[0], tuple):
                consumer = tuple(consumer_rows[0])
            instrument: tuple[object, ...] = ()
            if len(instrument_rows) == 1 and isinstance(instrument_rows[0], tuple):
                instrument = tuple(instrument_rows[0])
            state: tuple[object, ...] = ()
            if len(process_state_rows) == 1 and isinstance(
                process_state_rows[0], tuple
            ):
                state = tuple(process_state_rows[0])
            lock_waits: tuple[object, ...] = ()
            if len(lock_wait_rows) == 1 and isinstance(lock_wait_rows[0], tuple):
                lock_waits = tuple(lock_wait_rows[0])
            resource.event(
                "native_terminal_observer",
                session=session,
                elapsed_seconds=time.monotonic() - started,
                current_rows=len(rows),
                statement_event=current[0] if isinstance(current[0], str) else None,
                end_event_id=current[1] if isinstance(current[1], int) else None,
                sql_type=type(current[2]).__name__,
                sql_length=len(current[2]) if isinstance(current[2], str) else None,
                current_consumer=(
                    consumer[0]
                    if len(consumer) == 1 and type(consumer[0]) is str
                    else None
                ),
                select_instrument=(list(instrument) if len(instrument) == 2 else None),
                process_state=state[0]
                if len(state) == 2 and isinstance(state[0], str)
                else None,
                process_command=state[1]
                if len(state) == 2 and isinstance(state[1], str)
                else None,
                data_lock_waits=(
                    lock_waits[0]
                    if len(lock_waits) == 1 and type(lock_waits[0]) is int
                    else None
                ),
            )
        finally:
            observer.close()
        if len(rows) != 1 or type(rows[0][0]) is not str:
            raise ValueError("BLOCKED_STATEMENT_UNOBSERVED")
        process.stdin.write(terminal + "\n")
        process.stdin.flush()
        result = document(
            json.loads(_worker_line(process, "TERMINAL_WORKER")), "TERMINAL_WORKER"
        )
        process.wait(timeout=15)
        if process.returncode:
            raise ValueError("TERMINAL_WORKER:" + str(process.returncode))
        value = document(result.get("terminal"), "TERMINAL_WORKER")
        value["blocked"] = {
            "session": session,
            "event": rows[0][0],
            "sql_sha256": facts["sql_sha256"],
            "native_statement": facts["native_statement"],
            "purpose": facts["purpose"],
            "server": {
                "current_rows": len(rows),
                "statement_event": current[0],
                "end_event_id": current[1],
                "process_state": state[0] if len(state) == 2 else None,
                "process_command": state[1] if len(state) == 2 else None,
            },
        }
        return value
    finally:
        if locked:
            manager(resource, "ROLLBACK")
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def campaign(
    directory: Path, wheel: Path, interpreter: str, house: Path, otel_house: Path
) -> Path:
    """Materialize one exact prefix and record real public route observations."""
    from _pietto_execution_installation_probe import (
        _environment,
        _run,
        materialize,
        wheelhouse,
    )
    from _pietto_execution_source_assurance_probe import manager
    from _pietto_target_conformance_resources import Resources

    directory.mkdir(mode=0o700)
    report: dict[str, Any] = {
        "format": FORMAT,
        "status": "FAILED",
        "wheel_sha256": sha256(wheel),
        "otel_wheels": _otel_wheels(otel_house),
        "otel_unselected": CP312_WRAPT,
    }
    raw = directory / "report.json"
    (directory / "service").mkdir(mode=0o700)
    resource = Resources(
        "mysql",
        json.loads((ROOT / "tests/phase66_target_pins.json").read_text())["targets"][
            "mysql"
        ],
        directory / "service",
    )
    stage = "install"
    try:
        cache, log = directory / "uv-cache", directory / "install.log"
        verified_house, constraints, _ = wheelhouse(house)
        prefix = directory / "prefix"
        install = materialize(
            prefix,
            interpreter,
            wheel,
            ("execute-mysql",),
            verified_house,
            constraints,
            cache,
            log,
        )
        python = prefix / "bin/python"
        selected = otel_house / OTEL_WHEELS[-1]
        telemetry = _run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                python,
                "--no-index",
                "--find-links",
                otel_house,
                "--strict",
                "opentelemetry-api==1.33.1",
                "opentelemetry-sdk==1.33.1",
                selected,
            ],
            log,
            env=_environment(cache),
            cwd=directory,
        )
        installed = _run(
            ["uv", "pip", "check", "--python", python],
            log,
            env=_environment(cache),
            cwd=directory,
        )
        report["install"] = {
            "candidate": install,
            "telemetry": telemetry,
            "check": installed,
        }
        if telemetry["returncode"] or installed["returncode"]:
            raise ValueError("OTEL_INSTALL")
        stage = "resource_acquire"
        resource.acquire()
        stage = "tls_configure"
        certificate = _configure_tls(resource)
        stage = "project"
        project = _public_project(directory)
        manager(
            resource,
            "CREATE TABLE phase66.s06_public_rows (left_id BIGINT NOT NULL,right_key BIGINT NULL)",
        )
        manager(
            resource,
            "INSERT INTO phase66.s06_public_rows (left_id,right_key) VALUES (1,NULL),(1,NULL)",
        )
        for sql, _secret in resource.role_statements():
            manager(resource, sql)
        for table in ("threads", "events_transactions_current"):
            manager(
                resource,
                "GRANT SELECT ON performance_schema."
                + table
                + " TO 'pietto_query'@'%'",
            )
        stage = "attrs_oracle"
        attrs_oracle = _attrs_oracle(resource)
        manager(
            resource,
            "GRANT SELECT ON performance_schema.session_connect_attrs TO 'pietto_query'@'%'",
        )
        base = {
            "tests": str(ROOT / "tests"),
            "project": str(project),
            "port": resource.port,
            "password": resource._passwords[1],
            "ca": str(resource.ca_path),
            "selected_wheel": selected.name,
        }
        stage = "main_worker"
        main = _worker(python, directory, base | {"case": "main"})
        manager(resource, "DELETE FROM phase66.s06_public_rows")
        stage = "empty_worker"
        empty = _worker(python, directory, base | {"case": "empty"})
        _check_nonterminal_cases(
            {
                "rows": main.get("rows"),
                "bundle": main.get("bundle"),
                "empty": empty.get("empty"),
                "schema": main.get("schema"),
            }
        )
        terminal_project = _terminal_project(directory)
        manager(
            resource,
            "CREATE TABLE phase66.s06_public_heavy_left (id BIGINT NOT NULL PRIMARY KEY)",
        )
        manager(resource, "INSERT INTO phase66.s06_public_heavy_left VALUES (0)")
        for shift in range(14):
            manager(
                resource,
                "INSERT INTO phase66.s06_public_heavy_left "
                "SELECT id+" + str(1 << shift) + " FROM phase66.s06_public_heavy_left",
            )
        manager(
            resource,
            "INSERT INTO phase66.s06_public_heavy_left "
            "SELECT id+16384 FROM phase66.s06_public_heavy_left LIMIT 3616",
        )
        manager(
            resource,
            "CREATE TABLE phase66.s06_public_heavy_right "
            "SELECT id FROM phase66.s06_public_heavy_left",
        )
        heavy_rows = manager(
            resource, "SELECT COUNT(*) FROM phase66.s06_public_heavy_left"
        )
        if heavy_rows != [(20000,)]:
            raise ValueError("MYSQL_HEAVY_ROWS")
        resource.event("native_terminal_fixture", rows=20000, pairs=400000000)
        terminals = {}
        for terminal in ("cancel", "deadline"):
            stage = "terminal_" + terminal
            terminals[terminal] = _terminal_worker(
                python,
                directory,
                base
                | {
                    "project": str(terminal_project),
                    "kind": "query",
                    "case": "terminal",
                    "terminal": terminal,
                    "terminal_seconds": 5.0 if terminal == "cancel" else 1.0,
                },
                resource,
                terminal,
            )
        report["identity"] = main["identity"] | {
            "server": "8.4.12",
            "wheel_sha256": sha256(wheel),
        }
        report["telemetry"] = main["telemetry"]
        report["profile"] = {
            "host": "localhost",
            "identity_verified": True,
            "tls": main["profile"]["sessions"][0]["tls"],
            "certificate": certificate,
            "attrs_oracle": attrs_oracle,
            "sessions": main["profile"]["sessions"],
            "packets": main["profile"]["packets"],
        }
        report["factory"] = main["factory"]
        report["cases"] = (
            {
                key: value
                for key, value in main.items()
                if key not in {"factory", "identity", "telemetry", "profile"}
            }
            | {"empty": empty["empty"]}
            | terminals
        )
        report["status"] = "PASS"
    except BaseException as error:
        failure = {"stage": stage, "kind": type(error).__name__}
        reason = str(error)
        if re.fullmatch(r"[A-Z0-9_:-]+", reason):
            failure["reason"] = reason
        report["failure"] = failure
    finally:
        cleanup = resource.cleanup()
        report["cleanup"] = "PASS" if cleanup["status"] == "success" else "FAILED"
        if report["cleanup"] != "PASS":
            report["status"] = "FAILED"
        raw.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    check(report)
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    check_cmd = sub.add_parser("check")
    check_cmd.add_argument("--report", type=Path, required=True)
    run_cmd = sub.add_parser("campaign")
    for name in ("directory", "wheel", "house", "otel-house"):
        run_cmd.add_argument("--" + name, type=Path, required=True)
    run_cmd.add_argument("--interpreter", required=True)
    args = parser.parse_args(argv)
    if args.command == "check":
        print(json.dumps(check(json.loads(args.report.read_text())), sort_keys=True))
        return 0
    print(
        campaign(
            args.directory, args.wheel, args.interpreter, args.house, args.otel_house
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
