"""76-S06 client: one cell on one route through the public pietto.execution API.

    PYTHON -I client.py CELL ROUTE PORT   (password on standard input)

PYTHON is the fresh environment whose Pietto distribution comes from the
frozen candidate wheel (RUNBOOK.md). The process
must start with a clean environment (no PG* or OpenSSL variables); pg.sh runs
it under `env -i`. It prints one JSON object and exits 0 whatever the cell's
outcome; the judge decides.
"""

import hashlib
import importlib.metadata
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TLS = HERE / "tls"
# cell -> (sslmode, ca_file); "system" is passed literally, None means no CA.
CELLS = {
    "A1_full_ok": ("require", str(TLS / "ca.pem")),
    "A2_wrong_ca": ("require", str(TLS / "other-ca.pem")),
    "A3_missing_ca": ("require", str(TLS / "absent.pem")),
    "A4_require": ("require", None),
    "A5_disable_ca": ("disable", str(TLS / "ca.pem")),
    "A6_system_ca": ("require", "system"),
    "B1_wrong_host": ("require", str(TLS / "ca.pem")),
    "B2_require_any_name": ("require", None),
    "C1_ambient_pgsslrootcert": ("require", str(TLS / "ca.pem")),
}
APPLICATION = {
    "postgres_rows": "pietto_private_execution",
    "postgres_adbc": "pietto_postgres_adbc",
}


def main(cell, route, port):
    import pyarrow as pa

    from pietto.execution import (
        AttemptFailed,
        PostgresAccess,
        PostgresDeploymentPremise,
        RequestRejected,
        compile_query,
        execute,
    )
    import pietto

    sslmode, ca_file = CELLS[cell]
    password = sys.stdin.readline().rstrip("\n")
    query = compile_query(
        str(HERE / "in" / "demo-exec"),
        module="main.pietto",
        kind="table",
        name="active_items",
        dialect="postgres",
        emission_contract="contract.json",
    )
    sql = json.loads(query.emission)["sql"].encode()
    access = PostgresAccess(
        "127.0.0.1", int(port), "app", "pietto_reader", password, sslmode, ca_file
    )
    premise = PostgresDeploymentPremise(schemas=("fixture", "pg_catalog"))
    record = {
        "cell": cell,
        "route": route,
        "sslmode": sslmode,
        "ca_file": None if ca_file is None else Path(ca_file).name,
        "application": APPLICATION[route],
        "ambient_pgsslrootcert": "PGSSLROOTCERT" in os.environ,
        "sql_sha256": hashlib.sha256(sql).hexdigest(),
        "dependencies": {
            name: importlib.metadata.version(name)
            for name in (
                "pietto",
                "pyarrow",
                "psycopg",
                "psycopg-binary",
                "adbc-driver-postgresql",
                "adbc-driver-manager",
            )
        },
        "pietto_direct_url": importlib.metadata.distribution("pietto").read_text(
            "direct_url.json"
        ),
        "pietto_package_files": {
            "module": str(Path(pietto.__file__).resolve()),
            "record": str(
                importlib.metadata.distribution("pietto").locate_file(
                    "pietto-0.1.10.dist-info/RECORD"
                )
            ),
        },
        "dependency_origins": {
            name: str(importlib.metadata.distribution(name).locate_file(""))
            for name in (
                "pietto",
                "pyarrow",
                "psycopg",
                "psycopg-binary",
                "adbc-driver-postgresql",
                "adbc-driver-manager",
            )
        },
    }
    record["t0"] = time.time()
    try:
        rows = []
        with execute(query, route=route, access=access, premise=premise) as result:
            for batch in result:
                with batch:
                    rows.extend(pa.record_batch(batch).to_pylist())
        outcome = result.outcome
        record["result"] = {
            "kind": "rows",
            "rows": [[row["id"], row["label"]] for row in rows],
            "end": outcome.end,
            "transaction": outcome.transaction,
        }
    except RequestRejected as error:
        record["result"] = {"kind": "rejected", "code": error.code, "detail": error.detail}
    except AttemptFailed as error:
        outcome = error.outcome
        record["result"] = {
            "kind": "failed",
            "code": error.code,
            "category": error.category,
            "end": None if outcome is None else outcome.end,
        }
    record["t1"] = time.time()
    print(json.dumps(record, sort_keys=True))


if __name__ == "__main__":
    main(*sys.argv[1:4])
