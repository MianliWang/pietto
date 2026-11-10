#!/bin/bash
# 76-S06 TLS material: local openssl only, no network. Writes $P/tls (mode 700);
# private keys stay there (mode 600). Re-run only if the certificates expired
# (60 days); the oracle does not depend on the certificate bytes.
set -eu
P=/tmp/pietto-p77-numeric-pg-parent-r4
T=$P/tls
rm -rf "$T"; mkdir -m 700 "$T"; cd "$T"; umask 077
KEY="-newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes"
for ca in ca other-ca; do
  openssl req -x509 $KEY -sha256 -days 60 -subj "/CN=pietto-p76-s06-$ca" \
    -addext "basicConstraints=critical,CA:true" -keyout "$ca-key.pem" -out "$ca.pem" 2>/dev/null
done
# server names only 127.0.0.1 (the relay's address); elsewhere names only elsewhere.invalid.
for pair in server:IP:127.0.0.1 elsewhere:DNS:elsewhere.invalid; do
  name=${pair%%:*}; san=${pair#*:}
  openssl req -new $KEY -sha256 -subj "/CN=pietto-p76-s06-$name" -addext "subjectAltName=$san" \
    -keyout "$name-key.pem" -out "$name.csr" 2>/dev/null
  openssl x509 -req -in "$name.csr" -CA ca.pem -CAkey ca-key.pem -CAcreateserial -days 60 -sha256 \
    -copy_extensions copy -out "$name.pem" 2>/dev/null
done
chmod 644 ca.pem other-ca.pem server.pem elsewhere.pem
openssl verify -CAfile ca.pem server.pem elsewhere.pem
if openssl verify -CAfile other-ca.pem server.pem >/dev/null 2>&1; then echo "other-ca verifies server.pem" >&2; exit 1; fi
for c in server elsewhere; do openssl x509 -in "$c.pem" -noout -ext subjectAltName | tail -1; done
openssl x509 -in server.pem -noout -enddate
sha256sum ca.pem other-ca.pem server.pem elsewhere.pem
