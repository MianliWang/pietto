#!/bin/bash
# Phase77 maintenance PostgreSQL package, derived from Phase76 S06. Run only as
# recorded in PREREG.md:
#   only an independently authorized dispatch may choose a persistent lock and run pg.sh
# One fresh container named by PIETTO_PG_CONTAINER, local image by ID,
# --pull=never, --network none,
# tmpfs data dir. The host client reaches the server only through relay.py, which
# runs `docker exec -i` per connection; TLS stays end to end. Private keys are copied
# into the container's tmpfs only and stay in ./tls on the host.
set -u
# NEW_RECONSTRUCTION: all runtime identities are supplied fresh.
: "${PIETTO_PG_RUN_ROOT:?missing PIETTO_PG_RUN_ROOT}"
: "${PIETTO_PG_CONTAINER:?missing PIETTO_PG_CONTAINER}"
: "${PIETTO_PG_IMAGE:?missing PIETTO_PG_IMAGE}"
: "${PIETTO_PG_PYTHON:?missing PIETTO_PG_PYTHON}"
: "${PIETTO_PG_CANDIDATE:?missing PIETTO_PG_CANDIDATE}"
: "${PIETTO_PG_WHEEL:?missing PIETTO_PG_WHEEL}"
: "${PIETTO_PG_WHEEL_SHA256:?missing PIETTO_PG_WHEEL_SHA256}"
: "${PIETTO_PG_BASE:?missing PIETTO_PG_BASE}"
: "${PIETTO_PG_PATCH_SHA256:?missing PIETTO_PG_PATCH_SHA256}"
: "${PIETTO_PG_LOCK_SHA256:?missing PIETTO_PG_LOCK_SHA256}"
: "${PIETTO_PG_CONTAINER_LABEL:?missing PIETTO_PG_CONTAINER_LABEL}"
: "${PIETTO_PG_TARGET_NONCE:?missing PIETTO_PG_TARGET_NONCE}"
: "${PIETTO_PG_TARGET_LOCK:?missing PIETTO_PG_TARGET_LOCK}"
P=$PIETTO_PG_RUN_ROOT
R=$P/raw
PG=$PIETTO_PG_CONTAINER
IMG=$PIETTO_PG_IMAGE
PY=$PIETTO_PG_PYTHON
T=/var/lib/postgresql/tls
BASE=$PIETTO_PG_BASE
PATCH=$PIETTO_PG_PATCH_SHA256
WHEEL=$PIETTO_PG_WHEEL
WHEEL_SHA=$PIETTO_PG_WHEEL_SHA256
[ "$PG" = "pietto-p77-maint-pg-$PIETTO_PG_TARGET_NONCE" ] && [ "$PIETTO_PG_CONTAINER_LABEL" = "pietto.phase77.pg-run=$PIETTO_PG_TARGET_NONCE" ] && [ "$PIETTO_PG_TARGET_LOCK" = /tmp/claude-1000/pietto-docker-campaign-postgres.lock ] || { echo "invalid target invocation" >&2; exit 2; }
"$PY" -I -c 'import json, sys; value=json.load(open(sys.argv[1])); expected={"nonce":sys.argv[2],"lock":sys.argv[3],"timeout_seconds":7200,"container_name":sys.argv[4],"container_label":sys.argv[5]}; assert value == expected' "$P/target-invocation.json" "$PIETTO_PG_TARGET_NONCE" "$PIETTO_PG_TARGET_LOCK" "$PG" "$PIETTO_PG_CONTAINER_LABEL" || exit 2
if [ -e "$R" ]; then echo "raw/ exists: move it to raw-runN first" >&2; exit 2; fi
mkdir -p "$R/home/.postgresql"
cp "$P/tls/other-ca.pem" "$R/home/.postgresql/root.crt"
chmod 600 "$R/home/.postgresql/root.crt"
LOG=$R/campaign.log
RELAY=
CLOSED=0
log() { echo "$(date -u +%FT%T.%3NZ) $*" >> "$LOG"; }
close_resources() {
  [ "$CLOSED" = 1 ] && return
  CLOSED=1; container_id=; container_name=; container_label=; container_label_value=; relay_reaped=false; relay_wait_status=null; server_log_captured=false; container_absent=false
  if docker inspect "$PG" >/dev/null 2>&1; then
    container_id=$(docker inspect --format '{{.Id}}' "$PG")
    container_name=$(docker inspect --format '{{.Name}}' "$PG" | sed 's#^/##')
    container_label=$PIETTO_PG_CONTAINER_LABEL
    container_label_value=$(docker inspect --format '{{index .Config.Labels "pietto.phase77.pg-run"}}' "$PG")
    docker logs "$PG" > "$R/pg-server.log" 2>&1 && server_log_captured=true
  fi
  if [ -n "$RELAY" ]; then kill "$RELAY" 2>/dev/null; if wait "$RELAY" 2>/dev/null; then relay_wait_status=0; else relay_wait_status=$?; fi; relay_reaped=true; RELAY=; fi
  docker rm -f -v "$PG" >> "$LOG" 2>&1
  docker inspect "$PG" >/dev/null 2>&1 || container_absent=true
  printf '{"container":{"id":"%s","label":"%s","label_value":"%s","name":"%s"},"container_absent":%s,"relay":{"reaped":%s,"wait_status":%s},"server_log_captured":%s}\n' "$container_id" "$container_label" "$container_label_value" "$container_name" "$container_absent" "$relay_reaped" "$relay_wait_status" "$server_log_captured" > "$R/cleanup.json"
}
cleanup() {
  status=$?; trap - EXIT; close_resources; exit "$status"
}
trap cleanup EXIT
trap 'exit 143' TERM INT
sql() { docker exec -i "$PG" psql -X -q -v ON_ERROR_STOP=1 -U postgres "$@"; }
value() { docker exec "$PG" psql -X -q -A -t -U postgres -d postgres -c "$1"; }
mark() {
  docker exec "$PG" psql -X -q -U postgres -d postgres \
    -c "DO \$\$BEGIN RAISE LOG 'pietto-p77-maint-mark $1 $2 $3'; END\$\$" >> "$LOG" 2>&1 || return
  echo "$(date +%s.%N) mark pietto-p77-maint-mark $1 $2 $3" >> "$R/relay.log"
}
log "pg: lock held"
log "pg: package $(cd "$P" && sha256sum PREREG.md judge.py client.py receipt.py relay.py pg.sh gen-tls.sh fresh_binding.py fresh-start.sh target-run.sh fresh-binding.json candidate.patch in/fixture.sql in/pg_hba.conf in/ordered-exec/* in/timestamp-exec/* tls/ca.pem tls/server.pem | cut -c1-16 | tr '\n' ' ')"
log "pg: certificates $(openssl x509 -in "$P/tls/server.pem" -noout -enddate) $(openssl x509 -in "$P/tls/elsewhere.pem" -noout -enddate)"
[ "$(sha256sum "$WHEEL" | cut -d' ' -f1)" = "$WHEEL_SHA" ] || { log "pg: wheel sha mismatch"; exit 1; }
[ "$(sha256sum "$P/candidate.patch" | cut -d' ' -f1)" = "$PATCH" ] || { log "pg: stored candidate patch mismatch"; exit 1; }
UV_PYTHON=3.13.13 UV_OFFLINE=1 "$PY" -I "$P/fresh_binding.py" check --output "$P/fresh-binding.json" --wheel "$WHEEL" --wheel-sha256 "$WHEEL_SHA" --candidate "$PIETTO_PG_CANDIDATE" --base "$BASE" --patch-sha256 "$PATCH" --lock-sha256 "$PIETTO_PG_LOCK_SHA256" >> "$LOG" 2>&1 || exit 1
log "pg: candidate base=$BASE patch=$PATCH wheel=$WHEEL_SHA lock=$PIETTO_PG_LOCK_SHA256 binding=$(sha256sum "$P/fresh-binding.json" | cut -d' ' -f1)"
log "pg: image $(docker image inspect --format '{{.Id}} tags={{.RepoTags}} digests={{.RepoDigests}}' "$IMG" 2>&1)"
PW=$("$PY" -I -c 'import secrets; print(secrets.token_hex(24))')
log "pg: docker run"
docker run -d --name "$PG" --label "$PIETTO_PG_CONTAINER_LABEL" --pull=never --network none --cpus 2 --memory 2g \
  --tmpfs /var/lib/postgresql:rw,size=1g -e POSTGRES_HOST_AUTH_METHOD=trust "$IMG" \
  postgres -c timezone=UTC >> "$LOG" 2>&1 || { log "pg: run failed"; exit 1; }
ok=0
for i in $(seq 1 90); do
  if docker logs "$PG" 2>&1 | grep -q 'PostgreSQL init process complete' && docker exec "$PG" pg_isready -U postgres -q 2>/dev/null; then ok=1; break; fi
  sleep 2
done
log "pg: ready=$ok after loop $i"
log "pg: inspect $(docker inspect --format 'created={{.Created}} image={{.Image}} nanocpus={{.HostConfig.NanoCpus}} memory={{.HostConfig.Memory}} network={{.HostConfig.NetworkMode}} tmpfs={{json .HostConfig.Tmpfs}} cmd={{json .Config.Cmd}}' "$PG" 2>&1)"
OBS_IMAGE=$(docker inspect --format '{{.Image}}' "$PG")
OBS_NETWORK=$(docker inspect --format '{{.HostConfig.NetworkMode}}' "$PG")
[ "$ok" = 1 ] || { docker logs "$PG" 2>&1 | tail -30 >> "$LOG"; exit 1; }

# TLS material, the hba file, the fixture and the reader's SCRAM password.
docker exec "$PG" sh -c "mkdir -p $T && chown postgres:postgres $T && chmod 700 $T" >> "$LOG" 2>&1
for f in server.pem server-key.pem elsewhere.pem elsewhere-key.pem; do
  docker exec -i -u postgres "$PG" sh -c "umask 077; cat > $T/$f" < "$P/tls/$f" || { log "pg: copy $f failed"; exit 1; }
done
HBA=$(value 'SHOW hba_file')
docker exec -i -u postgres "$PG" sh -c "cat > '$HBA'" < "$P/in/pg_hba.conf" || { log "pg: hba failed"; exit 1; }
sql -d postgres < "$P/in/fixture.sql" >> "$LOG" 2>&1 || { log "pg: fixture failed"; exit 1; }
printf "SET password_encryption = 'scram-sha-256';\nALTER ROLE pietto_reader PASSWORD '%s';\n" "$PW" \
  | sql -d postgres >> "$LOG" 2>&1 || { log "pg: password failed"; exit 1; }
sql -d postgres >> "$LOG" 2>&1 <<EOF || { log "pg: tls settings failed"; exit 1; }
ALTER SYSTEM SET ssl_cert_file = '$T/server.pem';
ALTER SYSTEM SET ssl_key_file = '$T/server-key.pem';
ALTER SYSTEM SET ssl = on;
ALTER SYSTEM SET log_connections = 'on';
SELECT pg_reload_conf();
EOF
for i in $(seq 1 50); do
  [ "$(value 'SHOW ssl')" = on ] && [ "$(value 'SHOW ssl_cert_file')" = "$T/server.pem" ] && break
  sleep 0.2
done
log "pg: version=$(value 'SHOW server_version') ssl=$(value 'SHOW ssl') cert=$(value 'SHOW ssl_cert_file') log_connections=$(value 'SHOW log_connections') hba=$HBA hba_errors=$(value 'SELECT count(*) FROM pg_catalog.pg_hba_file_rules WHERE error IS NOT NULL') hba_rules=$(value 'SELECT count(*) FROM pg_catalog.pg_hba_file_rules')"

python3 -I "$P/relay.py" "$PG" "$R/relay.port" "$R/relay.log" 2>> "$LOG" &
RELAY=$!
for i in $(seq 1 50); do [ -s "$R/relay.port" ] && break; sleep 0.1; done
PORT=$(cat "$R/relay.port")
log "pg: relay pid=$RELAY port=$PORT"

mark begin remaining public || exit 1
printf '%s\n' "$PW" | env -i PATH=/usr/bin:/bin HOME="$R/home" LANG=C.UTF-8 \
  timeout 180 "$PY" -I "$P/client.py" "$PORT" > "$R/client.json" 2> "$R/client.err"
rc=$?
log "remaining public exit $rc"
mark end remaining public || exit 1
[ "$rc" = 0 ] || exit "$rc"

sleep 2
close_resources
log "pg: cleanup=$(cat "$R/cleanup.json")"
"$PY" -I "$P/receipt.py" "$R" "$BASE" "$PATCH" "$WHEEL_SHA" "$PIETTO_PG_LOCK_SHA256" "$OBS_IMAGE" "$OBS_NETWORK" || exit 1
