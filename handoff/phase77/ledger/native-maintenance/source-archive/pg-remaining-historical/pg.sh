#!/bin/bash
# Phase77 maintenance PostgreSQL package, derived from Phase76 S06. Run only as
# recorded in PREREG.md:
#   nice -n 19 flock --close -w 600 /tmp/claude-1000/pietto-docker-campaign-postgres.lock timeout 3600 bash pg.sh
# One container (`pietto-p77-maint-pg-2601-338`), local image by ID,
# --pull=never, --network none,
# tmpfs data dir. The host client reaches the server only through relay.py, which
# runs `docker exec -i` per connection; TLS stays end to end. Private keys are copied
# into the container's tmpfs only and stay in ./tls on the host.
set -u
P=/tmp/pietto-p77-maint-pg-run
R=$P/raw
PG=pietto-p77-maint-pg-2601-338
IMG=sha256:f372eda99ac2ea249c3dce566dcdf468397035371284d2cf2103b4bc52b3b39e
PY=$P/venv-wheel-fresh/bin/python
T=/var/lib/postgresql/tls
BASE=f8ccd2c44a2d9adf431a496bd9bbae037783176f
PATCH=7345ddec240b89308f20867bfbcc9abf6f9cd7c49498b641f95df142cf62da2c
WHEEL=/tmp/pietto-maintenance-2601-338-package-dist-r2/pietto-0.1.10-py3-none-any.whl
WHEEL_SHA=f4c96921c4d4ceb057830f2dd21f2e634325dac2bef933532747ae4aab963a73
if [ -e "$R" ]; then echo "raw/ exists: move it to raw-runN first" >&2; exit 2; fi
mkdir -p "$R/home/.postgresql"
cp "$P/tls/other-ca.pem" "$R/home/.postgresql/root.crt"
chmod 600 "$R/home/.postgresql/root.crt"
LOG=$R/campaign.log
RELAY=
log() { echo "$(date -u +%FT%T.%3NZ) $*" >> "$LOG"; }
cleanup() {
  [ -n "$RELAY" ] && kill "$RELAY" 2>/dev/null
  docker rm -f -v "$PG" >> "$LOG" 2>&1
  log "pg: trap cleanup done"
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
log "pg: package $(cd "$P" && sha256sum PREREG.md judge.py client.py receipt.py relay.py pg.sh gen-tls.sh candidate.patch in/fixture.sql in/pg_hba.conf in/demo-exec/* in/timestamp-exec/* tls/ca.pem tls/server.pem | cut -c1-16 | tr '\n' ' ')"
log "pg: certificates $(openssl x509 -in "$P/tls/server.pem" -noout -enddate) $(openssl x509 -in "$P/tls/elsewhere.pem" -noout -enddate)"
[ "$(sha256sum "$WHEEL" | cut -d' ' -f1)" = "$WHEEL_SHA" ] || { log "pg: wheel sha mismatch"; exit 1; }
[ "$(sha256sum "$P/candidate.patch" | cut -d' ' -f1)" = "$PATCH" ] || { log "pg: stored candidate patch mismatch"; exit 1; }
ACTUAL_PATCH=$(git -C /tmp/pietto-maintenance-2601-338 diff --binary HEAD | sha256sum | cut -d' ' -f1)
[ "$ACTUAL_PATCH" = "$PATCH" ] || { log "pg: current candidate patch mismatch: $ACTUAL_PATCH"; exit 1; }
ACTUAL_WHEEL=$("$PY" -I -c 'import importlib.metadata as m, json; print(json.loads(m.distribution("pietto").read_text("direct_url.json"))["url"])' 2>&1)
[ "$ACTUAL_WHEEL" = "file://$WHEEL" ] || { log "pg: installed pietto is not bound wheel: $ACTUAL_WHEEL"; exit 1; }
log "pg: candidate base=$BASE patch=$PATCH wheel=$WHEEL_SHA lock=$(sha256sum /tmp/pietto-maintenance-2601-338/uv.lock | cut -d' ' -f1) installed=$ACTUAL_WHEEL"
log "pg: image $(docker image inspect --format '{{.Id}} tags={{.RepoTags}} digests={{.RepoDigests}}' "$IMG" 2>&1)"
PW=$(python3 -I -c 'import secrets; print(secrets.token_hex(24))')
log "pg: docker run"
docker run -d --name "$PG" --pull=never --network none --cpus 2 --memory 2g \
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
docker logs "$PG" > "$R/pg-server.log" 2>&1
kill "$RELAY" 2>/dev/null
wait "$RELAY" 2>/dev/null || true
RELAY=
docker rm -f -v "$PG" >> "$LOG" 2>&1
log "pg: removed"
trap - EXIT
log "pg: remaining=[$(docker ps -a --filter name=pietto-p77-maint-pg-2601-338 --format '{{.Names}}' | tr '\n' ' ')]"
python3 -I "$P/receipt.py" "$R" "$BASE" "$PATCH" "$WHEEL_SHA" "$OBS_IMAGE" "$OBS_NETWORK" "$ok" || exit 1
