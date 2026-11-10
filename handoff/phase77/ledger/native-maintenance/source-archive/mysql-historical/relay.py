"""Bounded raw relay for one MySQL container on Docker's `none` network.

It listens only on host loopback.  Each client owns one non-TTY `docker exec`
whose fixed shell program opens only container loopback port 3306.  TLS bytes
are copied unchanged.  This is an external maintenance witness, not a Pietto
runtime transport.
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import signal
import os
import threading
import time
from pathlib import Path

FORWARD = (
    "exec 3<>/dev/tcp/127.0.0.1/3306 || exit 3; exec 4<&0; "
    "cat <&4 >&3 & writer=$!; cat <&3; "
    "kill $writer 2>/dev/null; wait $writer 2>/dev/null; exit 0"
)
MAX_CHILDREN = 16


def clean_environment() -> dict[str, str]:
    return {"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"), "PYTHONNOUSERSITE": "1"}


class Relay:
    def __init__(self, container: str, config: Path, port_file: Path, log_file: Path):
        self.container = container
        self.config = config
        self.log = log_file.open("a", encoding="utf-8", buffering=1)
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.listener = socket.create_server(("127.0.0.1", 0))
        self.listener.settimeout(0.2)
        self.children: list[subprocess.Popen[bytes]] = []
        self.threads: list[threading.Thread] = []
        self.active = 0
        port_file.write_text(str(self.listener.getsockname()[1]), encoding="ascii")
        self.note("listening", port=self.listener.getsockname()[1])

    def note(self, event: str, **values: object) -> None:
        with self.lock:
            self.log.write(json.dumps({"at": time.time(), "event": event, **values}) + "\n")
            self.log.flush()

    def command(self) -> tuple[str, ...]:
        return (
            "docker", "--config", str(self.config), "--host", "unix:///var/run/docker.sock",
            "container", "exec", "-i", self.container, "/bin/bash", "-c", FORWARD,
        )

    def serve(self) -> None:
        number = 0
        while not self.stop.is_set():
            try:
                client, _ = self.listener.accept()
            except TimeoutError:
                continue
            except OSError:
                if self.stop.is_set():
                    break
                raise
            refused = False
            with self.lock:
                self.children = [child for child in self.children if child.poll() is None]
                if self.active >= MAX_CHILDREN:
                    refused = True
                else:
                    self.active += 1
            if refused:
                client.close()
                self.note("refused", reason="child_limit")
                continue
            number += 1
            thread = threading.Thread(target=self.forward, args=(client, number), daemon=True)
            self.threads.append(thread)
            thread.start()

    def forward(self, client: socket.socket, number: int) -> None:
        process: subprocess.Popen[bytes] | None = None
        writer: threading.Thread | None = None
        counts = {"up": 0, "down": 0}

        def upward() -> None:
            try:
                while data := client.recv(65536):
                    counts["up"] += len(data)
                    assert process is not None and process.stdin is not None
                    process.stdin.write(data)
                    process.stdin.flush()
            except OSError:
                pass
            finally:
                if process is not None and process.stdin is not None:
                    try:
                        process.stdin.close()
                    except OSError:
                        pass

        try:
            process = subprocess.Popen(self.command(), env=clean_environment(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            with self.lock:
                self.children.append(process)
            self.note("accept", number=number, pid=process.pid)
            writer = threading.Thread(target=upward, daemon=True)
            writer.start()
            assert process.stdout is not None
            while data := process.stdout.read1(65536):
                counts["down"] += len(data)
                client.sendall(data)
        except OSError:
            pass
        finally:
            try:
                client.shutdown(socket.SHUT_WR)
            except OSError:
                pass
            client.close()
        if writer is not None:
            writer.join(70)
        try:
            code = process.wait(10) if process is not None else "not_started"
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(5)
            code = "killed"
        with self.lock:
            self.active -= 1
        self.note("close", number=number, up=counts["up"], down=counts["down"], returncode=code)

    def close(self) -> None:
        self.stop.set()
        self.listener.close()
        for child in self.children:
            if child.poll() is None:
                child.terminate()
        deadline = time.monotonic() + 10
        unreaped: list[int] = []
        for child in self.children:
            try:
                child.wait(max(0.001, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                child.kill()
                try:
                    child.wait(max(0.001, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    unreaped.append(child.pid)
        for thread in self.threads:
            thread.join(max(0.001, deadline - time.monotonic()))
        if unreaped or any(thread.is_alive() for thread in self.threads) or any(child.poll() is None for child in self.children):
            raise RuntimeError("relay children did not close")
        self.note("closed", children=len(self.children))
        self.log.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--container", required=True)
    parser.add_argument("--docker-config", type=Path, required=True)
    parser.add_argument("--port-file", type=Path, required=True)
    parser.add_argument("--log-file", type=Path, required=True)
    args = parser.parse_args()
    relay = Relay(args.container, args.docker_config, args.port_file, args.log_file)
    def stop(_signum: int, _frame: object) -> None:
        relay.stop.set()
        relay.listener.close()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        relay.serve()
    finally:
        relay.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
