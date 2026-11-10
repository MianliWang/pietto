# MySQL source replay status

The literal `apply_patch` inputs from
`records/maintenance_mysql_db.jsonl` have materialized these script inputs:

- `source-archive/mysql-historical/campaign.py`
- `source-archive/mysql-historical/mysql.sh`
- `source-archive/mysql-historical/relay.py`
- `source-archive/mysql-historical/judge.py`
- `source-archive/mysql-historical/preflight.py`
- `source-archive/mysql-historical/selfcheck.py`
- `source-archive/mysql-prereg/PREREG.md`

`recover_mysql_sources.mjs` is source-only replay code. It does not invoke the
recovered launcher, Docker, a database, network, installer, or cleanup.

The final historic campaign checksum and replayed checksum both are
`c2c38ce086a19e56ccbb45c9d46b74763e915d242bc914398735725e8ef56fbd`.
`mysql-source-replay.json` records no unapplied hunk.

The two formerly reported gaps were failed original calls, so they are
correctly excluded from the archive:

- `call_67d9efad575e445b8f938cee35388ef1` (line 1576) failed patch
  verification and did not modify `campaign.py`.
- `call_93214da44f1e4eaf994c8df13187ce5a` (line 3099) failed patch
  verification and did not modify `selfcheck.py`.

The successful follow-up calls supply the final behavior: installation wrapper
and complete IPC terminal assertion (`call_7b7a773829f342cca0f101529af6b785`),
MySQL `resources.MYSQL_MODE` self-check assertion
(`call_f77718a9952f40c78f37a2141b4a4f8d`), global relay deadline, bounded
native/context summaries, and the external deadline input 1 to 5 seconds.

`runnable-rebind/mysql/` is intentionally separate. Its Python sources are
copied byte-for-byte from the historical archive; its new launcher accepts only
fresh explicit candidate, wheel, wheelhouses, binding and lock identities.
It has no inherited review or PASS status.
