# PostgreSQL maintenance runbook

Run the exact local, no-database command in `ROOTSTART.md` first. It writes the
fresh wheel/install-prefix binding, generated TLS, source hashes, selftest log
and exit status below this directory. It does not create an endpoint or a
credential.

Only a later, explicitly authorized database dispatch may run `pg.sh`, with
the same environment values and a persistent lock chosen by that dispatch.
Then run the bound interpreter's `judge.py compare`. Preserve a failed raw
directory; do not rerun it as a substitute for repair.
