# PostgreSQL maintenance runbook

The bound source, wheel, lock, PostgreSQL image and expected TLS cells are in
`/tmp/pietto-p77-maint-pg-prereg/PREREG.md`. First run `bash selftest.sh` and
inspect `selftest-current.stdout` and `selftest-current.exit`. It is a
fabricated-world check only.

After an independent pre-start review explicitly authorizes target execution,
the one permitted database command is:

```bash
nice -n 19 flock --close -w 600 /tmp/claude-1000/pietto-docker-campaign-postgres.lock timeout 7200 bash /tmp/pietto-p77-maint-pg-run/pg.sh
```

Then run `python3 -I judge.py compare`. A failed command or judge verdict is
preserved in `raw/`; it is not rerun as a substitute for a repair.
