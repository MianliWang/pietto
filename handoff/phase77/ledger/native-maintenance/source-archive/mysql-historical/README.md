# MySQL literal-none maintenance campaign

This external package is a pre-run candidate for the PyArrow 26.0.1
maintenance witness. It is not a Pietto source change or a completed database
qualification.

The relay is copied from the Phase76 S06 raw `exec-stdio` pattern with one
reviewed transport delta: the in-container endpoint is MySQL loopback port
3306. It binds only host loopback, starts at most sixteen non-TTY Docker exec
children, forwards raw TLS bytes and reaps its children before container
cleanup. `judge.py` accepts only a new `mysql-none-exec-stdio-v1` receipt; it
does not accept an internal-bridge receipt.

Before execution, bind the candidate wheel, `tests/phase66_target_pins.json`,
MySQL image config digest, exact installed origins, complete public MySQL
native report, relay log and cleanup observation into one receipt. The
repository's full target-conformance receipt uses its own internal bridge
profile and remains historical closure context; this package never relabels it
as literal-none evidence.

`mysql.sh` is the sole launcher. It requires a new owned directory named
`/tmp/pietto-p77-maint-mysql-run-*` and two already-verified offline
wheelhouses: the candidate lock's CPython 3.13 Linux artifacts and the exact
OpenTelemetry witness artifacts. It holds the MySQL engine lock for the entire
two-hour ceiling and supplies only the prebound candidate wheel. `campaign.py`
patches the existing native witness only at its resource acquisition seam; the
full existing report/oracle still checks the prepared, bundle, typed NULL,
empty, bounded-batch, cancellation, deadline, TLS, telemetry, source-origin
and cleanup stories. It adds an Arrow IPC lifetime check and then invokes the
independent transport judge after cleanup.

Before `mysql.sh`, run `preflight.py` once with the exact candidate and wheel
to an empty external path. The launcher rejects any change to candidate HEAD,
full patch, pins, lock or wheel bytes after that preflight.
