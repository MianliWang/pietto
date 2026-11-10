"""Bounded raw Psycopg regression observation; not a Pietto result route."""

from __future__ import annotations

from datetime import datetime, timedelta
import json
import sys


def value(item):
    if isinstance(item, list):
        return {"kind": "list", "items": item}
    if isinstance(item, datetime):
        return {"kind": "datetime", "value": item.isoformat(timespec="microseconds")}
    if isinstance(item, timedelta):
        return {"kind": "timedelta", "seconds": item.total_seconds()}
    return {"kind": type(item).__name__, "value": str(item)}


def main(port_text, ca_file):
    import psycopg

    password = sys.stdin.readline().rstrip("\n")
    connection = psycopg.connect(
        host="127.0.0.1", port=int(port_text), dbname="app", user="pietto_reader",
        password=password, sslmode="verify-full", sslrootcert=ca_file, connect_timeout=10,
    )
    cursor = connection.cursor()
    cursor.execute(
        "SELECT ARRAY[1, 2]::int8[], TIMESTAMP '2026-11-08 12:34:56.123456', "
        "INTERVAL '2 days 03:04:05' UNION ALL "
        "SELECT ARRAY[3]::int8[], TIMESTAMP '2026-11-09 00:00:00', INTERVAL '0'"
    )
    first = cursor.fetchone()
    connection.close()
    after = {}
    try:
        after["value"] = value(cursor.fetchone())
    except BaseException as error:
        after["error"] = {"type": type(error).__name__, "text": str(error)}
    print(json.dumps({"before_close": [value(item) for item in first], "after_close": after, "connection_closed": bool(connection.closed)}))


if __name__ == "__main__":
    main(*sys.argv[1:3])
