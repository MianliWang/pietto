# PostgreSQL remaining fresh commands

`ROOTSTART.md` is the only pre-start command. It binds the current local wheel
and installed `RECORD`, writes a current candidate patch, creates new TLS
material, and runs the fabricated judge with no database, Docker, or network.

An independently authorized target dispatch runs `target-run.sh` with the same
explicit `PIETTO_PG_*` values plus its selected image. It alone acquires the
canonical persistent `pg-target.lock`, creates a fresh nonce-derived owned
container and applies the 7200-second ceiling before calling `pg.sh`.
