"""76-S06 host relay (stdlib only): 127.0.0.1:PORT on the host -> 127.0.0.1:5432
inside a --network none container, through one `docker exec -i` per TCP
connection. TLS stays end to end between the host client and the server; the
relay only copies bytes. It logs one `accept` line per connection, with the
host epoch, so the judge can attribute connections to cells.

    python3 -I relay.py CONTAINER PORTFILE LOGFILE

It writes the listening port to PORTFILE and runs until it is killed.
"""

import socket
import subprocess
import sys
import threading
import time

# Inside the container: bash connects to the server; the reader copies server
# bytes to stdout and, when the server closes, stops the writer so that the
# exec ends and the host side sees the close. The writer reads a copy (fd 4)
# of stdin, since a background job's own stdin is /dev/null.
FORWARD = (
    "exec 3<>/dev/tcp/127.0.0.1/5432 || exit 3; exec 4<&0; "
    "cat <&4 >&3 & w=$!; cat <&3; kill $w 2>/dev/null; wait $w 2>/dev/null; exit 0"
)


def main(container, portfile, logfile):
    log = open(logfile, "a", buffering=1)
    lock = threading.Lock()

    def note(*words):
        with lock:
            log.write(" ".join(["%.6f" % time.time(), *map(str, words)]) + "\n")

    listener = socket.create_server(("127.0.0.1", 0))
    with open(portfile, "w") as stream:
        stream.write(str(listener.getsockname()[1]))
    note("listening", listener.getsockname()[1])
    number = 0
    while True:
        client, _ = listener.accept()
        number += 1
        note("accept", number)
        threading.Thread(
            target=serve, args=(container, client, number, note), daemon=True
        ).start()


def serve(container, client, number, note):
    process = subprocess.Popen(
        ("docker", "exec", "-i", container, "bash", "-c", FORWARD),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    counts = {"up": 0, "down": 0}

    def upward():
        try:
            while data := client.recv(65536):
                counts["up"] += len(data)
                process.stdin.write(data)
                process.stdin.flush()
        except OSError:
            pass
        finally:
            try:
                process.stdin.close()
            except OSError:
                pass

    writer = threading.Thread(target=upward, daemon=True)
    writer.start()
    try:
        while data := process.stdout.read1(65536):
            counts["down"] += len(data)
            client.sendall(data)
    except OSError:
        pass
    try:
        client.shutdown(socket.SHUT_WR)
    except OSError:
        pass
    writer.join(70)
    client.close()
    try:
        code = process.wait(10)
    except subprocess.TimeoutExpired:
        process.kill()
        code = "killed"
    note("close", number, "up=%d" % counts["up"], "down=%d" % counts["down"], "rc=%s" % code)


if __name__ == "__main__":
    main(*sys.argv[1:4])
