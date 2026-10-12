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
import subprocess
import time
from typing import Any

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


def check(report: Any) -> dict[str, str]:
    """Independent literal oracle; it performs neither imports nor I/O."""
    need(type(report) is dict and report.get("format") == FORMAT, "ENVELOPE")
    need(report.get("status") == "PASS", "STATUS")
    identity = report.get("identity")
    need(type(identity) is dict, "IDENTITY")
    need(identity.get("interpreter") == ["CPython", "3.13.13", "Linux"], "INTERPRETER")
    need(identity.get("server") == "8.4.12", "SERVER")
    need(identity.get("wheel_sha256") == report.get("wheel_sha256"), "WHEEL")
    origins = identity.get("origins")
    need(
        type(origins) is dict
        and set(origins) >= {"pietto", "mysql.connector.connection"}
        and all(type(value) is str and len(value) == 64 for value in origins.values()),
        "ORIGINS",
    )
    need(
        identity.get("drivers")
        == {"mysql-connector-python": "26.7.0", "pyarrow": "25.0.1"},
        "DRIVER_PINS",
    )
    telemetry = report.get("telemetry")
    witness_wheels = report.get("otel_wheels")
    need(
        type(telemetry) is dict
        and telemetry.get("versions")
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
        type(witness_wheels) is dict
        and set(witness_wheels) == set(OTEL_WHEELS)
        and all(type(value) is str and len(value) == 64 for value in witness_wheels.values())
        and report.get("otel_unselected") == CP312_WRAPT,
        "OTEL_WHEELS",
    )
    profile = report.get("profile")
    need(type(profile) is dict, "PROFILE")
    need(profile.get("host") == "localhost" and profile.get("identity_verified") is True, "TLS_IDENTITY")
    need(profile.get("tls") in ("TLSv1.2", "TLSv1.3"), "TLS")
    certificate = profile.get("certificate")
    service = certificate.get("service") if type(certificate) is dict else None
    need(
        type(certificate) is dict
        and certificate.get("reload") == "ALTER INSTANCE RELOAD TLS"
        and certificate.get("sans") == ["DNS:localhost", "IP Address:127.0.0.1"]
        and type(service) is list
        and [item.get("host") for item in service] == ["127.0.0.1", "localhost"]
        and all(item.get("identity_verified") is True and item.get("tls") in ("TLSv1.2", "TLSv1.3") for item in service),
        "TLS_CERTIFICATE",
    )
    attrs_oracle = profile.get("attrs_oracle")
    need(
        type(attrs_oracle) is dict
        and attrs_oracle.get("enabled") is True
        and type(attrs_oracle.get("size")) is int
        and attrs_oracle["size"] > 0
        and attrs_oracle.get("positive") == [["pietto_s06_marker", "present"]],
        "ATTRS_ORACLE",
    )
    sessions = profile.get("sessions")
    need(type(sessions) is list and sorted(item.get("kind") for item in sessions) == ["control", "data"], "SESSIONS")
    for session in sessions:
        need(session.get("attrs") == [] and session.get("connect_args") is False, "CONN_ATTRS")
        need(session.get("otel") is False and session.get("traceparent") is False, "OTEL")
        need(session.get("auth") == "caching_sha2_password" and session.get("tls") in ("TLSv1.2", "TLSv1.3"), "CONNECTION_PROFILE")
    packets = profile.get("packets")
    handshake = packets.get("handshake") if type(packets) is dict else None
    query = packets.get("query") if type(packets) is dict else None
    need(
        type(packets) is dict
        and type(handshake) is list
        and len(handshake) == 2
        and all(type(item.get("client_flags")) is int and item.get("connect_args") is False and item.get("attribute_encoding") is False and item.get("traceparent") is False for item in handshake)
        and type(query) is list
        and query
        and all(item.get("traceparent") is False for item in query)
        and type(packets.get("query_attrs")) is list
        and packets["query_attrs"]
        and all(item in (None, []) for item in packets["query_attrs"])
        and packets.get("prepare") is True
        and packets.get("execute") is True
        and packets.get("control") is True,
        "PACKETS",
    )
    cases = report.get("cases")
    need(type(cases) is dict and set(cases) == {"bundle", "cancel", "deadline", "empty", "rows", "schema"}, "CASES")
    need(cases["rows"].get("rows") == ROWS and cases["rows"].get("end") == "COMPLETE", "ROWS")
    need(cases["bundle"].get("rows") == ROWS and cases["bundle"].get("end") == "COMPLETE", "BUNDLE")
    need(cases["empty"].get("rows") == [] and cases["empty"].get("end") == "COMPLETE", "EMPTY")
    need(cases["schema"].get("schema") == [["left_id", "int64", False], ["right_key", "int64", True]], "SCHEMA")
    for name, terminal in (("cancel", "CANCELLED"), ("deadline", "DEADLINE")):
        value = cases[name]
        need(cases[name].get("end") == terminal and cases[name].get("cleanup") is not None, name.upper())
        need(
            value.get("transaction") == "ROLLBACK_ACK"
            and value.get("remote") == "TRANSACTION_ACK"
            and value.get("cancel") == {"requested": True, "sent": True, "observed": True}
            and type(value.get("primary")) is list
            and len(value["primary"]) == 3
            and value.get("control_kill") is True
            and value.get("consumer_thread_joined") is True
            and type(value.get("source")) is str
            and type(value.get("delivery")) is str
            and type(value.get("deadline_expired")) is bool
            and type(value.get("error")) is dict,
            name.upper() + "_FACTS",
        )
        blocked = value.get("blocked")
        need(
            type(blocked) is dict
            and type(blocked.get("session")) is int
            and type(blocked.get("event")) is str
            and type(blocked.get("sql")) is str
            and blocked["sql"]
            and blocked.get("native_statement") == "NativeStatement"
            and blocked.get("purpose") == "query",
            name.upper() + "_BLOCKED",
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


WORKER = r'''
import hashlib, importlib.metadata, json, platform, sys, threading, time
from pathlib import Path
config=json.loads(sys.stdin.readline())
sys.path.insert(0,config["tests"])
from _pietto_phase68_slice8_probe import Calls
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
 return pe.compile_query(config["project"],module="main.pietto",kind="table",name="result",
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
  limits=pe.ExecutionLimits(seconds=config["terminal_seconds"]))
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
  while handle._owner._active is None and time.monotonic()<until:time.sleep(.01)
  active=handle._owner._active
  if active is None:raise RuntimeError("ACTIVE_STATEMENT_NOT_OBSERVED")
  print(json.dumps({"active_ready":{"session":handle._owner.session_id,
   "native_statement":type(active).__name__,"purpose":active.purpose}}),flush=True)
  if sys.stdin.readline().strip()!=kind:raise RuntimeError("TERMINAL_GATE")
  if kind=="cancel":received["receipt"]=handle.cancel()
  if not done.wait(12):raise RuntimeError("TERMINAL_THREAD")
  thread.join()
 value=outcome(handle); actual=handle.outcome; primary=actual.primary
 value.update(cancel={"requested":actual.cancel_requested,"sent":actual.cancel_sent,"observed":actual.cancel_observed},
  primary=None if primary is None else [primary.code,primary.detail,primary.phase],
  error=received,consumer_thread_joined=not thread.is_alive(),
  control_kill="kill_query_send_returned" in [event[0] for event in handle._owner.control_events])
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
'''


def _otel_wheels(directory: Path) -> dict[str, str]:
    expected = (*OTEL_WHEELS, CP312_WRAPT)
    need(all((directory / name).is_file() for name in expected), "OTEL_WHEELHOUSE")
    return {name: sha256(directory / name) for name in OTEL_WHEELS}


def _configure_tls(resource) -> dict[str, Any]:
    """Replace only the owned tmpfs TLS files and ask MySQL to reload them."""
    from _pietto_phase68_slice6_probe import manager

    paths = dict(manager(resource, "SHOW VARIABLES WHERE Variable_name IN ('ssl_ca','ssl_cert','ssl_key')"))
    expected = {"ssl_ca": "ca.pem", "ssl_cert": "server-cert.pem", "ssl_key": "server-key.pem"}
    if paths != expected:
        raise ValueError("MYSQL_TLS_PATHS")
    script = "\n".join((
        "set -eu", "cd /var/lib/mysql",
        "openssl req -x509 -newkey rsa:2048 -nodes -sha256 -days 1 -subj /CN=pietto-native-ca -addext basicConstraints=critical,CA:true -keyout pietto-ca-key.pem -out pietto-ca.pem",
        "openssl req -new -newkey rsa:2048 -nodes -sha256 -subj /CN=localhost -addext subjectAltName=DNS:localhost,IP:127.0.0.1 -keyout pietto-server-key.pem -out pietto-server.csr",
        "openssl x509 -req -in pietto-server.csr -CA pietto-ca.pem -CAkey pietto-ca-key.pem -CAcreateserial -days 1 -sha256 -copy_extensions copy -out pietto-server-cert.pem",
        "chown mysql:mysql pietto-ca.pem pietto-server-key.pem pietto-server-cert.pem",
        "chmod 600 pietto-server-key.pem", "mv pietto-ca.pem ca.pem",
        "mv pietto-server-cert.pem server-cert.pem", "mv pietto-server-key.pem server-key.pem",
    ))
    resource.docker("container", "exec", resource.container_id, "sh", "-ec", script, timeout=30)
    manager(resource, "ALTER INSTANCE RELOAD TLS")
    resource.ca_path.write_text(resource.docker("container", "exec", resource.container_id, "cat", "/var/lib/mysql/ca.pem") + "\n")
    san = resource.docker("container", "exec", resource.container_id, "openssl", "x509", "-in", "/var/lib/mysql/server-cert.pem", "-noout", "-ext", "subjectAltName")
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

    service = []
    for host in ("127.0.0.1", "localhost"):
        connection = mysql.connector.connect(
            host=host, port=resource.port, database="phase66", user="root",
            password=resource._passwords[0], ssl_ca=str(resource.ca_path),
            ssl_verify_cert=True, ssl_verify_identity=True,
            tls_versions=["TLSv1.2", "TLSv1.3"], use_pure=True,
        )
        try:
            service.append({"host": host, "identity_verified": True, "tls": connection._socket.sock.version()})
        finally:
            connection.close()
    return {"reload": "ALTER INSTANCE RELOAD TLS", "sans": sans, "service": service}


def _attrs_oracle(resource) -> dict[str, Any]:
    """A server positive prevents a disabled attrs table passing as empty."""
    from _pietto_phase68_slice6_probe import manager
    import mysql.connector

    enabled = manager(resource, "SELECT @@performance_schema")[0][0] == 1
    size = int(manager(resource, "SELECT @@performance_schema_session_connect_attrs_size")[0][0])
    positive = mysql.connector.connect(
        host="localhost", port=resource.port, database="phase66", user="root",
        password=resource._passwords[0], ssl_ca=str(resource.ca_path),
        ssl_verify_cert=True, ssl_verify_identity=True, use_pure=True,
        conn_attrs={"pietto_s06_marker": "present"},
    )
    try:
        rows = manager(
            resource,
            "SELECT ATTR_NAME,ATTR_VALUE FROM performance_schema.session_connect_attrs "
            "WHERE PROCESSLIST_ID=%s AND ATTR_NAME='pietto_s06_marker'",
            (positive.connection_id,),
        )
    finally:
        positive.close()
    return {"enabled": enabled, "size": size, "positive": [list(row) for row in rows]}


def _public_project(directory: Path) -> Path:
    """The public compile factory's project, independent of private templates."""
    project = directory / "public-project"
    project.mkdir(mode=0o700)
    (project / "pietto.toml").write_text('schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n')
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
                        "ordinal": 0, "name": "left_id", "column": "left_id",
                        "representation": {
                            "storage": {"kind": "my_bigint"}, "nullable": False,
                            "domain": {"kind": "int_range", "min": "-9007199254740993", "max": "9007199254740993"},
                        },
                    },
                    {
                        "ordinal": 1, "name": "right_key", "column": "right_key",
                        "representation": {
                            "storage": {"kind": "my_bigint"}, "nullable": True,
                            "domain": {"kind": "int_range", "min": "-9007199254740993", "max": "9007199254740993"},
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
            {"key": "operator_environment", "scope": "statement", "value": "builtin_only"},
        ],
    }
    (project / "contract.json").write_text(json.dumps(contract, sort_keys=True))
    return project


def _worker(python: Path, directory: Path, config: dict[str, Any]) -> dict[str, Any]:
    from _pietto_target_conformance_resources import clean_environment

    result = subprocess.run(
        [str(python), "-I", "-B", "-c", WORKER], cwd=directory, env=clean_environment(),
        input=json.dumps(config), text=True, capture_output=True, timeout=120,
    )
    lines = result.stdout.splitlines()
    if result.returncode or not lines:
        raise ValueError("MYSQL_NATIVE_WORKER:" + str(result.returncode))
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError as error:
        raise ValueError("MYSQL_NATIVE_WORKER_JSON") from error


def _terminal_worker(python: Path, directory: Path, config: dict[str, Any], resource, terminal: str) -> dict[str, Any]:
    """Observe a public worker's genuinely blocked statement before its terminal."""
    from _pietto_phase68_slice6_probe import manager
    from _pietto_target_conformance_resources import clean_environment
    import mysql.connector

    process = subprocess.Popen(
        [str(python), "-I", "-B", "-c", WORKER], cwd=directory, env=clean_environment(),
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    locked = False
    try:
        assert process.stdin is not None and process.stdout is not None
        opened = json.loads(process.stdout.readline())
        if opened.get("open_ready", {}).get("session") is None:
            raise ValueError("PUBLIC_OPEN_UNOBSERVED")
        manager(resource, "LOCK TABLES phase66.s06_public_rows WRITE")
        locked = True
        process.stdin.write("go\n")
        process.stdin.flush()
        active = json.loads(process.stdout.readline())
        facts = active.get("active_ready")
        if (
            type(facts) is not dict
            or facts.get("native_statement") != "NativeStatement"
            or facts.get("purpose") != "query"
            or type(facts.get("session")) is not int
        ):
            raise ValueError("OWNED_QUERY_UNOBSERVED")
        session = facts["session"]
        observer = mysql.connector.connect(
            host="localhost", port=resource.port, database="phase66", user="root",
            password=resource._passwords[0], ssl_ca=str(resource.ca_path),
            ssl_verify_cert=True, ssl_verify_identity=True, use_pure=True,
        )
        try:
            rows = []
            until = time.monotonic() + 10
            while time.monotonic() < until:
                with observer.cursor() as cursor:
                    cursor.execute(
                        "SELECT EVENT_NAME,SQL_TEXT FROM performance_schema.events_statements_current "
                        "WHERE THREAD_ID=(SELECT THREAD_ID FROM performance_schema.threads WHERE PROCESSLIST_ID=%s)",
                        (session,),
                    )
                    rows = cursor.fetchall()
                if len(rows) == 1 and type(rows[0][0]) is str and type(rows[0][1]) is str:
                    break
                time.sleep(0.02)
        finally:
            observer.close()
        if len(rows) != 1 or type(rows[0][0]) is not str or type(rows[0][1]) is not str:
            raise ValueError("BLOCKED_STATEMENT_UNOBSERVED")
        process.stdin.write(terminal + "\n")
        process.stdin.flush()
        result = json.loads(process.stdout.readline())
        process.wait(timeout=15)
        if process.returncode:
            raise ValueError("TERMINAL_WORKER:" + str(process.returncode))
        value = result["terminal"]
        value["blocked"] = {
            "session": session,
            "event": rows[0][0],
            "sql": rows[0][1],
            "native_statement": facts["native_statement"],
            "purpose": facts["purpose"],
        }
        return value
    finally:
        if locked:
            manager(resource, "UNLOCK TABLES")
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def campaign(directory: Path, wheel: Path, interpreter: str, house: Path, otel_house: Path) -> Path:
    """Materialize one exact prefix and record real public route observations."""
    from _pietto_phase68_slice18_probe import _environment, _run, materialize, wheelhouse
    from _pietto_phase68_slice6_probe import manager
    from _pietto_target_conformance_resources import Resources

    directory.mkdir(mode=0o700)
    report: dict[str, Any] = {
        "format": FORMAT, "status": "FAILED", "wheel_sha256": sha256(wheel),
        "otel_wheels": _otel_wheels(otel_house),
        "otel_unselected": CP312_WRAPT,
    }
    raw = directory / "report.json"
    resource = Resources(
        "mysql",
        json.loads((ROOT / "tests/phase66_target_pins.json").read_text())["targets"]["mysql"],
        directory / "service",
    )
    try:
        cache, log = directory / "uv-cache", directory / "install.log"
        verified_house, constraints, _ = wheelhouse(house)
        prefix = directory / "prefix"
        install = materialize(
            prefix, interpreter, wheel, ("execute-mysql",), verified_house, constraints, cache, log
        )
        python = prefix / "bin/python"
        selected = otel_house / OTEL_WHEELS[-1]
        telemetry = _run(
            ["uv", "pip", "install", "--python", python, "--no-index", "--find-links", otel_house,
             "--strict", "opentelemetry-api==1.33.1", "opentelemetry-sdk==1.33.1", selected],
            log, env=_environment(cache), cwd=directory,
        )
        installed = _run(
            ["uv", "pip", "check", "--python", python],
            log, env=_environment(cache), cwd=directory,
        )
        report["install"] = {"candidate": install, "telemetry": telemetry, "check": installed}
        if telemetry["returncode"] or installed["returncode"]:
            raise ValueError("OTEL_INSTALL")
        resource.acquire()
        certificate = _configure_tls(resource)
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
        attrs_oracle = _attrs_oracle(resource)
        manager(resource, "GRANT SELECT ON performance_schema.session_connect_attrs TO 'pietto_query'@'%'")
        base = {
            "tests": str(ROOT / "tests"), "project": str(project), "port": resource.port,
            "password": resource._passwords[1], "ca": str(resource.ca_path),
            "selected_wheel": selected.name,
        }
        main = _worker(python, directory, base | {"case": "main"})
        manager(resource, "DELETE FROM phase66.s06_public_rows")
        empty = _worker(python, directory, base | {"case": "empty"})
        manager(
            resource,
            "INSERT INTO phase66.s06_public_rows (left_id,right_key) VALUES (1,NULL),(1,NULL)",
        )
        terminals = {}
        for terminal in ("cancel", "deadline"):
            terminals[terminal] = _terminal_worker(
                python, directory,
                base | {"case": "terminal", "terminal": terminal, "terminal_seconds": 1.0},
                resource, terminal,
            )
        report["identity"] = main["identity"] | {"server": "8.4.12", "wheel_sha256": sha256(wheel)}
        report["telemetry"] = main["telemetry"]
        report["profile"] = {
            "host": "localhost", "identity_verified": True,
            "tls": main["profile"]["sessions"][0]["tls"], "certificate": certificate,
            "attrs_oracle": attrs_oracle, "sessions": main["profile"]["sessions"],
            "packets": main["profile"]["packets"],
        }
        report["factory"] = main["factory"]
        report["cases"] = {
            key: value for key, value in main.items() if key not in {"identity", "telemetry", "profile"}
        } | {"empty": empty["empty"]} | terminals
        report["status"] = "PASS"
    except BaseException as error:
        report["failure"] = type(error).__name__
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
    print(campaign(args.directory, args.wheel, args.interpreter, args.house, args.otel_house))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
