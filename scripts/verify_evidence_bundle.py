"""Verify immutable Gate 2 evidence sidecars and their main report."""

from __future__ import annotations

import argparse
import base64
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Mapping

try:
    from scripts.build_evidence_bundle import (
        IDENTITY_HEADER,
        LEDGER_SCHEMA,
        PERFORMANCE_SCHEMA,
        READER_SCHEMA,
        SIDECAR_ORDER,
        TOPOLOGY_SCHEMA,
        _statuses,
        canonical_json,
        freeze_reviewed_tree,
    )
except ModuleNotFoundError:
    from build_evidence_bundle import (
        IDENTITY_HEADER,
        LEDGER_SCHEMA,
        PERFORMANCE_SCHEMA,
        READER_SCHEMA,
        SIDECAR_ORDER,
        TOPOLOGY_SCHEMA,
        _statuses,
        canonical_json,
        freeze_reviewed_tree,
    )


SHA256 = re.compile(r"[0-9a-f]{64}")
PLACEHOLDER = re.compile(r"(?:<[^>]+>|\bTODO\b|\bPLACEHOLDER\b)")


class EvidenceVerificationError(RuntimeError):
    """Raised when evidence identity or completeness is not exact."""


@dataclass(frozen=True, slots=True)
class FileIdentity:
    path: str
    mode: str
    links: int
    lines: int
    bytes: int
    sha256: str


def file_identity(path: Path) -> FileIdentity:
    facts = path.lstat()
    if stat.S_ISLNK(facts.st_mode) or not stat.S_ISREG(facts.st_mode):
        raise EvidenceVerificationError(f"not a regular non-symlink: {path}")
    mode = stat.S_IMODE(facts.st_mode)
    if mode != 0o644:
        raise EvidenceVerificationError(f"mode is not 0644: {path}")
    if facts.st_nlink != 1:
        raise EvidenceVerificationError(f"link count is not one: {path}")
    payload = path.read_bytes()
    return FileIdentity(
        path=str(path),
        mode="0644",
        links=facts.st_nlink,
        lines=payload.count(b"\n"),
        bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
    )


def _json_object(path: Path, schema: str) -> dict[str, object]:
    try:
        document = json.loads(path.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EvidenceVerificationError(f"malformed JSON: {path}") from error
    if not isinstance(document, dict) or document.get("schema") != schema:
        raise EvidenceVerificationError(f"wrong schema in {path}")
    if path.read_bytes() != canonical_json(document):
        raise EvidenceVerificationError(f"noncanonical JSON in {path}")
    return document


def _verify_internal_payload(document: dict[str, object], name: str) -> None:
    recorded = document.pop("payload_sha256", None)
    if not isinstance(recorded, str) or not SHA256.fullmatch(recorded):
        raise EvidenceVerificationError(f"malformed internal SHA in {name}")
    actual = hashlib.sha256(canonical_json(document)).hexdigest()
    document["payload_sha256"] = recorded
    if actual != recorded:
        raise EvidenceVerificationError(f"internal SHA mismatch in {name}")


def _identity_rows(payload: str) -> dict[str, tuple[str, str, int, str]]:
    lines = payload.splitlines()
    if not lines or lines[0] + "\n" != IDENTITY_HEADER:
        raise EvidenceVerificationError("identity manifest header mismatch")
    rows: dict[str, tuple[str, str, int, str]] = {}
    previous = ""
    for line in lines[1:]:
        fields = line.split("\t")
        if (
            len(fields) != 5
            or fields[1] not in {"A", "M", "D"}
            or fields[2] not in {"000000", "100644", "100755"}
            or not fields[3].isdigit()
            or not SHA256.fullmatch(fields[4])
            or fields[0] in rows
            or (previous and fields[0] <= previous)
        ):
            raise EvidenceVerificationError(f"malformed identity row: {line!r}")
        rows[fields[0]] = (fields[1], fields[2], int(fields[3]), fields[4])
        previous = fields[0]
    statuses = tuple(value[0] for value in rows.values())
    if len(rows) != 63 or statuses.count("A") != 12 or statuses.count("M") != 51:
        raise EvidenceVerificationError("identity manifest is not A12_M51_D0")
    return rows


def verify_bundle(
    *,
    sidecars: Mapping[str, Path],
    expected_hashes: Mapping[str, str] | None = None,
    root: Path | None = None,
    statuses: Mapping[str, str] | None = None,
    base: str | None = None,
    reviewed_tree: str | None = None,
    main_evidence: Path | None = None,
    expected_terminal: str | None = None,
) -> dict[str, object]:
    expected_names = {
        "identity_manifest",
        "canonical_patch",
        "command_ledger",
        "reader_closure",
        "topology_results",
        "performance_results",
    }
    if set(sidecars) != expected_names:
        raise EvidenceVerificationError("exact six-sidecar set is required")
    identities = {name: file_identity(path) for name, path in sidecars.items()}
    if expected_hashes is not None:
        if set(expected_hashes) != expected_names:
            raise EvidenceVerificationError("exact six expected hashes are required")
        for name, expected in expected_hashes.items():
            if not SHA256.fullmatch(expected):
                raise EvidenceVerificationError(f"malformed expected SHA for {name}")
            if identities[name].sha256 != expected:
                raise EvidenceVerificationError(f"SHA mismatch for {name}")

    identity_text = sidecars["identity_manifest"].read_text(encoding="utf-8")
    if not identity_text.endswith("\n") or "\r" in identity_text:
        raise EvidenceVerificationError("identity manifest encoding mismatch")
    identity_rows = _identity_rows(identity_text)
    patch = sidecars["canonical_patch"].read_bytes()
    if b"diff --git " not in patch:
        raise EvidenceVerificationError("canonical patch has no Git patch records")
    if root is not None or statuses is not None:
        if root is None or statuses is None or base is None or reviewed_tree is None:
            raise EvidenceVerificationError(
                "root, statuses, base, and reviewed tree are jointly required"
            )
        frozen = freeze_reviewed_tree(root=root, base=base, statuses=statuses)
        if frozen.reviewed_tree != reviewed_tree:
            raise EvidenceVerificationError("reconstructed reviewed tree mismatch")
        if frozen.identity_manifest != sidecars["identity_manifest"].read_bytes():
            raise EvidenceVerificationError(
                "identity manifest differs from reviewed tree"
            )
        if frozen.canonical_patch != patch:
            raise EvidenceVerificationError(
                "canonical patch differs from reviewed tree"
            )
        if set(identity_rows) != set(statuses):
            raise EvidenceVerificationError("identity path set differs from authority")
    ledger_lines = sidecars["command_ledger"].read_text(encoding="utf-8").splitlines()
    if not ledger_lines:
        raise EvidenceVerificationError("empty command ledger")
    sequences = []
    command_names: list[str] = []
    for line in ledger_lines:
        record = json.loads(line)
        if canonical_json(record).decode().rstrip("\n") != line:
            raise EvidenceVerificationError("noncanonical command ledger record")
        if record.get("schema") != LEDGER_SCHEMA:
            raise EvidenceVerificationError("command ledger schema mismatch")
        sequences.append(record.get("sequence"))
        required_record_fields = {
            "argv",
            "base",
            "cpu_ns",
            "cwd",
            "env",
            "name",
            "returncode",
            "reviewed_tree",
            "stderr_base64",
            "stderr_bytes",
            "stderr_sha256",
            "stdout_base64",
            "stdout_bytes",
            "stdout_sha256",
            "wall_ns",
        }
        if not required_record_fields <= set(record):
            raise EvidenceVerificationError("incomplete command record")
        if record["returncode"] != 0:
            raise EvidenceVerificationError("nonzero command record")
        if base is not None and record["base"] != base:
            raise EvidenceVerificationError("command base mismatch")
        if reviewed_tree is not None and record["reviewed_tree"] != reviewed_tree:
            raise EvidenceVerificationError("command reviewed tree mismatch")
        argv = record["argv"]
        if not isinstance(argv, list) or not all(
            isinstance(item, str) for item in argv
        ):
            raise EvidenceVerificationError("command argv is malformed")
        env = record["env"]
        if (
            argv
            and argv[0] == "uv"
            and (
                not isinstance(env, dict)
                or env.get("UV_NO_SYNC") != "1"
                or env.get("UV_OFFLINE") != "1"
            )
        ):
            raise EvidenceVerificationError("uv command is not exactly offline")
        for stream in ("stdout", "stderr"):
            encoded = record[f"{stream}_base64"]
            try:
                decoded = base64.b64decode(encoded, validate=True)
            except (ValueError, TypeError) as error:
                raise EvidenceVerificationError(
                    "malformed command output base64"
                ) from error
            if (
                len(decoded) != record[f"{stream}_bytes"]
                or hashlib.sha256(decoded).hexdigest() != record[f"{stream}_sha256"]
            ):
                raise EvidenceVerificationError("command output identity mismatch")
        command_names.append(record["name"])
    if sequences != list(range(1, len(sequences) + 1)):
        raise EvidenceVerificationError("command sequence is incomplete")
    expected_commands = [
        "lock",
        "focused",
        "compatibility",
        "reader_audit",
        "format_check",
        "reader_closure",
        "topology",
        "ruff",
        "pyright_production",
        "pyright_tests",
        "authoritative_validate",
        "clean_collection",
        "clean_pytest",
        "generated",
        "goldens",
        "package_smoke",
        "installed_cli_version",
    ]
    if command_names != expected_commands:
        raise EvidenceVerificationError("command graph differs from exact authority")

    reader = _json_object(sidecars["reader_closure"], READER_SCHEMA)
    topology = _json_object(sidecars["topology_results"], TOPOLOGY_SCHEMA)
    performance = _json_object(sidecars["performance_results"], PERFORMANCE_SCHEMA)
    for name, document in (
        ("reader", reader),
        ("topology", topology),
        ("performance", performance),
    ):
        encoded = json.dumps(document, sort_keys=True)
        if PLACEHOLDER.search(encoded):
            raise EvidenceVerificationError(f"placeholder in {name}")
        if base is not None and document.get("base") != base:
            raise EvidenceVerificationError(f"base mismatch in {name}")
        if reviewed_tree is not None and document.get("reviewed_tree") != reviewed_tree:
            raise EvidenceVerificationError(f"reviewed tree mismatch in {name}")

    _verify_internal_payload(reader, "reader")
    _verify_internal_payload(topology, "topology")
    _verify_internal_payload(performance, "performance")
    direct = reader.get("direct_readers")
    transitive = reader.get("transitive_readers")
    paths = reader.get("reader_paths")
    if (
        not isinstance(direct, list)
        or not isinstance(transitive, list)
        or not isinstance(paths, list)
    ):
        raise EvidenceVerificationError("reader partitions are absent")
    if (
        len(direct) != 59
        or len(transitive) != 107
        or len(paths) != 166
        or set(direct) & set(transitive)
        or set(direct) | set(transitive) != set(paths)
        or reader.get("unresolved_dynamic_warnings") != []
        or reader.get("missing_executing_readers") != []
    ):
        raise EvidenceVerificationError("reader closure partition mismatch")
    positives = topology.get("positive_results")
    negatives = topology.get("negative_results")
    equivalence = topology.get("equivalence")
    if (
        not isinstance(positives, list)
        or len(positives) != 4
        or any(
            not isinstance(item, dict) or item.get("result") != "PASS"
            for item in positives
        )
        or not isinstance(negatives, list)
        or len(negatives) != 24
        or any(
            not isinstance(item, dict) or item.get("result") != "REJECTED"
            for item in negatives
        )
        or not isinstance(equivalence, dict)
        or equivalence.get("outcome_equality") is not True
        or equivalence.get("excluded_content_invariant") is not True
        or topology.get("primary_state_before") != topology.get("primary_state_after")
    ):
        raise EvidenceVerificationError("topology result accounting mismatch")
    registry = topology.get("registry")
    if (
        not isinstance(registry, dict)
        or registry.get("node_id_count") != 323
        or registry.get("selected_items_per_projection") != 1143
    ):
        raise EvidenceVerificationError("topology registry identity mismatch")
    if (
        performance.get("outcome_equality") is not True
        or performance.get("reader_closure_runs") != 1
        or performance.get("authoritative_validate_runs") != 1
        or performance.get("legacy_repeated_items") != 27144
        or performance.get("lean_repeated_topology_items") != 4572
        or performance.get("repeated_item_reduction") != 22572
    ):
        raise EvidenceVerificationError("performance equivalence mismatch")
    crosslinks = performance.get("sidecar_sha256")
    if not isinstance(crosslinks, dict):
        raise EvidenceVerificationError("performance sidecar cross-links absent")
    for name in SIDECAR_ORDER[:-1]:
        if crosslinks.get(name) != identities[name].sha256:
            raise EvidenceVerificationError(f"performance cross-link mismatch: {name}")

    main_identity = None
    if main_evidence is not None:
        main_identity = file_identity(main_evidence)
        text = main_evidence.read_text(encoding="utf-8")
        if PLACEHOLDER.search(text):
            raise EvidenceVerificationError("placeholder in main evidence")
        if expected_terminal is None:
            raise EvidenceVerificationError("exact terminal is required")
        if not text.endswith("\n") or "\r" in text:
            raise EvidenceVerificationError("main evidence encoding mismatch")
        terminal_lines = [
            line for line in text.splitlines() if line == expected_terminal
        ]
        if len(terminal_lines) != 1 or text.splitlines()[-1] != expected_terminal:
            raise EvidenceVerificationError("terminal is not unique at EOF")
        sidecar_lines = [
            line.removeprefix("SIDECAR ")
            for line in text.splitlines()
            if line.startswith("SIDECAR ")
        ]
        if len(sidecar_lines) != 6:
            raise EvidenceVerificationError(
                "main evidence requires six SIDECAR records"
            )
        records: dict[str, dict[str, object]] = {}
        for encoded in sidecar_lines:
            record = json.loads(encoded)
            name = record.get("name")
            if not isinstance(name, str) or name in records:
                raise EvidenceVerificationError("duplicate or malformed SIDECAR record")
            records[name] = record
        if tuple(records) != SIDECAR_ORDER:
            raise EvidenceVerificationError("SIDECAR record order mismatch")
        for name, identity in identities.items():
            record = records[name]
            if (
                record.get("path") != identity.path
                or record.get("mode") != identity.mode
                or record.get("links") != identity.links
                or record.get("bytes") != identity.bytes
                or record.get("sha256") != identity.sha256
            ):
                raise EvidenceVerificationError(f"SIDECAR identity mismatch: {name}")
        main_payload = main_evidence.read_bytes()
        for name, path in sidecars.items():
            bulk = path.read_bytes()
            if bulk and bulk in main_payload:
                raise EvidenceVerificationError(
                    f"main evidence duplicates complete sidecar: {name}"
                )

    return {
        "sidecars": {
            name: asdict(identity) for name, identity in sorted(identities.items())
        },
        "main_evidence": asdict(main_identity) if main_identity else None,
        "result": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in (
        "identity-manifest",
        "canonical-patch",
        "command-ledger",
        "reader-closure",
        "topology-results",
        "performance-results",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--main-evidence", type=Path)
    parser.add_argument("--expected-terminal")
    parser.add_argument("--base")
    parser.add_argument("--reviewed-tree")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--manifest", type=Path)
    for name in SIDECAR_ORDER:
        parser.add_argument(f"--{name.replace('_', '-')}-sha256")
    arguments = parser.parse_args()
    names = {
        "identity_manifest": arguments.identity_manifest,
        "canonical_patch": arguments.canonical_patch,
        "command_ledger": arguments.command_ledger,
        "reader_closure": arguments.reader_closure,
        "topology_results": arguments.topology_results,
        "performance_results": arguments.performance_results,
    }
    hash_values = {name: getattr(arguments, f"{name}_sha256") for name in SIDECAR_ORDER}
    if any(hash_values.values()) and not all(hash_values.values()):
        raise EvidenceVerificationError("partial expected hash set")
    result = verify_bundle(
        sidecars=names,
        expected_hashes=hash_values if all(hash_values.values()) else None,
        root=arguments.root.resolve() if arguments.root else None,
        statuses=_statuses(arguments.manifest) if arguments.manifest else None,
        base=arguments.base,
        reviewed_tree=arguments.reviewed_tree,
        main_evidence=arguments.main_evidence,
        expected_terminal=arguments.expected_terminal,
    )
    os.write(1, (json.dumps(result, sort_keys=True) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
