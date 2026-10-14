"""Offline MySQL execution access fixture."""

from pietto._project.project_execution import MySQLAccess


def access():
    return MySQLAccess(
        "127.0.0.1",
        3306,
        "phase66",
        "pietto_query",
        "not-a-live-secret",
        "/explicit/ca.pem",
        "pietto_query@%",
        verify_identity=False,
        loopback_tls_exception=True,
    )
