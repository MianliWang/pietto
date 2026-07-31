"""Build deterministic Gate 2 evidence sidecars without embedding bulk payloads."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from typing import Iterable, Mapping, Sequence


IDENTITY_SCHEMA = "pietto.gate2.identity-manifest.v1"
PATCH_SCHEMA = "pietto.gate2.canonical-patch.v1"
LEDGER_SCHEMA = "pietto.gate2.command-ledger.v1"
READER_SCHEMA = "pietto.gate2.reader-closure.v1"
TOPOLOGY_SCHEMA = "pietto.gate2.topology-results.v1"
PERFORMANCE_SCHEMA = "pietto.gate2.performance-results.v1"
IDENTITY_HEADER = "path\tstatus\tmode\tbytes\tsha256\n"
BASE = "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16"
ALLOWLIST_LABEL = "A12_M51_D0"
SIDECAR_BASENAMES = {
    "identity_manifest": "pietto-phase54-post-slice6-workflow-efficiency-gate2-identity-manifest.tsv",
    "canonical_patch": "pietto-phase54-post-slice6-workflow-efficiency-gate2-canonical.patch",
    "command_ledger": "pietto-phase54-post-slice6-workflow-efficiency-gate2-command-ledger.jsonl",
    "reader_closure": "pietto-phase54-post-slice6-workflow-efficiency-gate2-reader-closure.json",
    "topology_results": "pietto-phase54-post-slice6-workflow-efficiency-gate2-topology-results.json",
    "performance_results": "pietto-phase54-post-slice6-workflow-efficiency-gate2-performance-results.json",
}
SIDECAR_ORDER = tuple(SIDECAR_BASENAMES)


@dataclass(frozen=True, slots=True)
class SidecarPayloads:
    identity_manifest: bytes
    canonical_patch: bytes
    command_ledger: bytes
    reader_closure: bytes
    topology_results: bytes
    performance_results: bytes


@dataclass(frozen=True, slots=True)
class FrozenReviewedTree:
    reviewed_tree: str
    identity_manifest: bytes
    canonical_patch: bytes


def canonical_json(document: object) -> bytes:
    return (
        json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def canonical_jsonl(records: Iterable[Mapping[str, object]]) -> bytes:
    lines = []
    for sequence, record in enumerate(records, start=1):
        document = dict(record)
        document["schema"] = LEDGER_SCHEMA
        document["sequence"] = sequence
        lines.append(canonical_json(document))
    return b"".join(lines)


def write_exclusive(path: Path, payload: bytes) -> None:
    """Create one regular 0644 file without following or replacing a target."""

    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o644,
    )
    try:
        os.fchmod(descriptor, 0o644)
        view = memoryview(payload)
        written = 0
        while written < len(view):
            written += os.write(descriptor, view[written:])
        os.fsync(descriptor)
        facts = os.fstat(descriptor)
        if (
            not stat.S_ISREG(facts.st_mode)
            or stat.S_IMODE(facts.st_mode) != 0o644
            or facts.st_nlink != 1
            or facts.st_size != len(payload)
        ):
            raise RuntimeError(f"exclusive file identity drift: {path}")
    finally:
        os.close(descriptor)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        os.close(descriptor)
    if b"".join(chunks) != payload:
        raise RuntimeError(f"exclusive file reopen mismatch: {path}")


def _file_mode(path: Path) -> str:
    mode = path.stat().st_mode
    if mode & stat.S_IXUSR:
        return "100755"
    return "100644"


def identity_manifest(*, root: Path, statuses: Mapping[str, str]) -> bytes:
    rows = [IDENTITY_HEADER]
    for relative in sorted(statuses):
        status_value = statuses[relative]
        path = root / relative
        if status_value == "D":
            rows.append(f"{relative}\tD\t000000\t0\t{'0' * 64}\n")
            continue
        payload = path.read_bytes()
        rows.append(
            f"{relative}\t{status_value}\t{_file_mode(path)}\t{len(payload)}\t"
            f"{hashlib.sha256(payload).hexdigest()}\n"
        )
    return "".join(rows).encode("utf-8")


def _run_git(
    root: Path,
    arguments: Sequence[str],
    *,
    accepted: tuple[int, ...] = (0,),
) -> bytes:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode not in accepted:
        raise RuntimeError(
            f"git {' '.join(arguments)} failed: {result.stderr.decode(errors='replace')}"
        )
    return result.stdout


def _name_status(root: Path, arguments: Sequence[str]) -> dict[str, str]:
    output = _run_git(root, arguments).decode("utf-8")
    result: dict[str, str] = {}
    for line in output.splitlines():
        status_value, separator, relative = line.partition("\t")
        if (
            not separator
            or status_value not in {"A", "M", "D"}
            or not relative
            or relative in result
        ):
            raise ValueError(f"malformed Git name-status row: {line!r}")
        result[relative] = status_value
    return result


def _apply_overlay(
    *, root: Path, clone: Path, base: str, statuses: Mapping[str, str]
) -> None:
    tracked = tuple(sorted(path for path, status in statuses.items() if status != "A"))
    if tracked:
        patch = _run_git(
            root,
            ("diff", "--binary", "--full-index", base, "--", *tracked),
        )
        if patch:
            result = subprocess.run(
                ["git", "apply", "--binary", "-"],
                cwd=clone,
                input=patch,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.decode(errors="replace"))
    for relative, status_value in sorted(statuses.items()):
        source = root / relative
        target = clone / relative
        if status_value == "A":
            if not source.is_file() or target.exists():
                raise ValueError(f"invalid added overlay path: {relative}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        elif status_value == "D":
            if source.exists() or not target.is_file():
                raise ValueError(f"invalid deleted overlay path: {relative}")
            target.unlink()


def freeze_reviewed_tree(
    *, root: Path, base: str, statuses: Mapping[str, str]
) -> FrozenReviewedTree:
    """Freeze identity, one canonical patch, and tree in isolated clones."""

    root = root.resolve()
    paths = tuple(sorted(statuses))
    with tempfile.TemporaryDirectory(prefix="pietto-gate2-tree-") as temporary:
        temporary_root = Path(temporary)
        source = temporary_root / "source"
        subprocess.run(
            [
                "git",
                "clone",
                "--local",
                "--no-hardlinks",
                "--no-checkout",
                str(root),
                str(source),
            ],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _run_git(source, ("switch", "--detach", base))
        _apply_overlay(root=root, clone=source, base=base, statuses=statuses)
        _run_git(source, ("add", "-A", "--", *paths))
        staged = _name_status(
            source, ("diff", "--cached", "--name-status", "--no-renames", base)
        )
        if staged != dict(statuses):
            raise ValueError(f"staged manifest differs from authority: {staged}")
        reviewed_tree = _run_git(source, ("write-tree",)).decode().strip()
        if re.fullmatch(r"[0-9a-f]{40}", reviewed_tree) is None:
            raise RuntimeError("malformed reviewed tree")
        patch = _run_git(
            source,
            (
                "diff",
                "--cached",
                "--binary",
                "--full-index",
                "--no-renames",
                "--no-ext-diff",
                base,
                "--",
                *paths,
            ),
        )
        verifier = temporary_root / "verifier"
        subprocess.run(
            [
                "git",
                "clone",
                "--local",
                "--no-hardlinks",
                "--no-checkout",
                str(root),
                str(verifier),
            ],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _run_git(verifier, ("switch", "--detach", base))
        applied = subprocess.run(
            ["git", "apply", "--cached", "--binary", "--whitespace=nowarn", "-"],
            cwd=verifier,
            input=patch,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if applied.returncode != 0:
            raise RuntimeError(applied.stderr.decode(errors="replace"))
        rebuilt_status = _name_status(
            verifier,
            ("diff", "--cached", "--name-status", "--no-renames", base),
        )
        rebuilt_tree = _run_git(verifier, ("write-tree",)).decode().strip()
        if rebuilt_status != dict(statuses) or rebuilt_tree != reviewed_tree:
            raise RuntimeError(
                "canonical patch did not rebuild the exact reviewed tree"
            )
        return FrozenReviewedTree(
            reviewed_tree=reviewed_tree,
            identity_manifest=identity_manifest(root=root, statuses=statuses),
            canonical_patch=patch,
        )


def canonical_patch(*, root: Path, base: str, statuses: Mapping[str, str]) -> bytes:
    return freeze_reviewed_tree(root=root, base=base, statuses=statuses).canonical_patch


def _require_json_schema(payload: bytes, schema: str) -> bytes:
    document = json.loads(payload)
    if not isinstance(document, dict) or document.get("schema") != schema:
        raise ValueError(f"expected {schema}")
    return canonical_json(document)


def build_payloads(
    *,
    root: Path,
    base: str,
    reviewed_tree: str,
    statuses: Mapping[str, str],
    command_records: Iterable[Mapping[str, object]],
    reader_payload: bytes,
    topology_payload: bytes,
    performance_payload: bytes,
) -> SidecarPayloads:
    frozen = freeze_reviewed_tree(root=root, base=base, statuses=statuses)
    if frozen.reviewed_tree != reviewed_tree:
        raise ValueError(
            f"reviewed tree drift: {frozen.reviewed_tree} != {reviewed_tree}"
        )
    ledger = canonical_jsonl(command_records)
    reader = _require_json_schema(reader_payload, READER_SCHEMA)
    topology = _require_json_schema(topology_payload, TOPOLOGY_SCHEMA)
    for name, payload in (("reader", reader), ("topology", topology)):
        document = json.loads(payload)
        if (
            document.get("base") != base
            or document.get("reviewed_tree") != reviewed_tree
        ):
            raise ValueError(f"{name} base/reviewed-tree binding mismatch")
    performance_document = json.loads(
        _require_json_schema(performance_payload, PERFORMANCE_SCHEMA)
    )
    if (
        performance_document.get("base") != base
        or performance_document.get("reviewed_tree") != reviewed_tree
    ):
        raise ValueError("performance base/reviewed-tree binding mismatch")
    performance_document["sidecar_sha256"] = {
        "identity_manifest": hashlib.sha256(frozen.identity_manifest).hexdigest(),
        "canonical_patch": hashlib.sha256(frozen.canonical_patch).hexdigest(),
        "command_ledger": hashlib.sha256(ledger).hexdigest(),
        "reader_closure": hashlib.sha256(reader).hexdigest(),
        "topology_results": hashlib.sha256(topology).hexdigest(),
    }
    performance_document.pop("payload_sha256", None)
    performance_document["payload_sha256"] = hashlib.sha256(
        canonical_json(performance_document)
    ).hexdigest()
    return SidecarPayloads(
        identity_manifest=frozen.identity_manifest,
        canonical_patch=frozen.canonical_patch,
        command_ledger=ledger,
        reader_closure=reader,
        topology_results=topology,
        performance_results=canonical_json(performance_document),
    )


def write_bundle(output: Path, payloads: SidecarPayloads) -> tuple[Path, ...]:
    output.mkdir(mode=0o755, parents=True, exist_ok=False)
    paths_and_payloads = (
        (output / "identity-manifest.tsv", payloads.identity_manifest),
        (output / "canonical.patch", payloads.canonical_patch),
        (output / "command-ledger.jsonl", payloads.command_ledger),
        (output / "reader-closure.json", payloads.reader_closure),
        (output / "topology-results.json", payloads.topology_results),
        (output / "performance-results.json", payloads.performance_results),
    )
    for path, payload in paths_and_payloads:
        write_exclusive(path, payload)
    return tuple(path for path, _ in paths_and_payloads)


def publish_bundle(evidence_dir: Path, payloads: SidecarPayloads) -> dict[str, Path]:
    """Publish the six exact flat targets in their frozen order."""

    facts = evidence_dir.lstat()
    if stat.S_ISLNK(facts.st_mode) or not stat.S_ISDIR(facts.st_mode):
        raise ValueError("evidence directory must be a real directory")
    result: dict[str, Path] = {}
    for name in SIDECAR_ORDER:
        path = evidence_dir / SIDECAR_BASENAMES[name]
        if path.exists() or path.is_symlink():
            raise FileExistsError(path)
        write_exclusive(path, getattr(payloads, name))
        result[name] = path
    directory_descriptor = os.open(evidence_dir, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_descriptor)
    finally:
        os.close(directory_descriptor)
    return result


def _statuses(path: Path) -> dict[str, str]:
    payload = path.read_bytes()
    if not payload.endswith(b"\n") or b"\r" in payload:
        raise ValueError("manifest must be canonical UTF-8/LF with final LF")
    result: dict[str, str] = {}
    previous = ""
    for line in payload.decode("utf-8").splitlines():
        fields = line.split("\t")
        relative = fields[0] if fields else ""
        if (
            len(fields) != 2
            or fields[1] not in {"A", "M", "D"}
            or not relative
            or relative.startswith("/")
            or ".." in Path(relative).parts
            or relative in result
            or (previous and relative <= previous)
        ):
            raise ValueError(f"invalid manifest row: {line!r}")
        result[relative] = fields[1]
        previous = relative
    if (
        tuple(result.values()).count("A") != 12
        or tuple(result.values()).count("M") != 51
        or tuple(result.values()).count("D") != 0
        or len(result) != 63
    ):
        raise ValueError("manifest is not exact A12_M51_D0")
    return result


def _records(path: Path) -> list[dict[str, object]]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        document = json.loads(line)
        if not isinstance(document, dict):
            raise ValueError("command record must be an object")
        document.pop("schema", None)
        document.pop("sequence", None)
        records.append(document)
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--reviewed-tree", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--reader", type=Path, required=True)
    parser.add_argument("--topology", type=Path, required=True)
    parser.add_argument("--performance", type=Path, required=True)
    outputs = parser.add_mutually_exclusive_group(required=True)
    outputs.add_argument("--output", type=Path)
    outputs.add_argument("--evidence-dir", type=Path)
    arguments = parser.parse_args()
    payloads = build_payloads(
        root=arguments.root.resolve(),
        base=arguments.base,
        reviewed_tree=arguments.reviewed_tree,
        statuses=_statuses(arguments.manifest),
        command_records=_records(arguments.ledger),
        reader_payload=arguments.reader.read_bytes(),
        topology_payload=arguments.topology.read_bytes(),
        performance_payload=arguments.performance.read_bytes(),
    )
    if arguments.output is not None:
        paths = {
            name: path
            for name, path in zip(
                SIDECAR_ORDER,
                write_bundle(arguments.output, payloads),
                strict=True,
            )
        }
    else:
        paths = publish_bundle(arguments.evidence_dir, payloads)
    result = {
        name: {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for name, path in paths.items()
    }
    os.write(
        1,
        canonical_json({"reviewed_tree": arguments.reviewed_tree, "sidecars": result}),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
