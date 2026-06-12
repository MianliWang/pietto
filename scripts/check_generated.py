"""Verify ANTLR provenance and exact generated-file reproducibility."""

from __future__ import annotations

import hashlib
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ANTLR_JAR = Path("tools/antlr-4.13.2-complete.jar")
CHECKSUM_FILE = Path("tools/antlr-4.13.2-complete.jar.sha256")
GRAMMAR = Path("grammar/Pietto.g4")
GENERATED_DIR = Path("src/pietto/generated")


def _error(message: str) -> int:
    print(f"[generated] error: {message}", file=sys.stderr)
    return 1


def _verify_jar(repo_root: Path) -> bool:
    checksum_path = repo_root / CHECKSUM_FILE
    jar_path = repo_root / ANTLR_JAR

    try:
        checksum_text = checksum_path.read_text(encoding="ascii")
    except OSError as error:
        _error(f"cannot read checksum file {CHECKSUM_FILE}: {error}")
        return False

    expected = checksum_text[:-1] if checksum_text.endswith("\n") else checksum_text
    if (
        len(expected) != 64
        or any(character not in "0123456789abcdef" for character in expected)
        or "\n" in expected
    ):
        _error(f"{CHECKSUM_FILE} must contain one lowercase SHA-256 value")
        return False

    digest = hashlib.sha256()
    try:
        with jar_path.open("rb") as jar_file:
            while chunk := jar_file.read(1024 * 1024):
                digest.update(chunk)
    except OSError as error:
        _error(f"cannot read ANTLR jar {ANTLR_JAR}: {error}")
        return False

    actual = digest.hexdigest()
    if actual != expected:
        _error(f"ANTLR jar SHA-256 mismatch: expected {expected}, found {actual}")
        return False

    print(f"[generated] verified ANTLR jar SHA-256: {actual}", flush=True)
    return True


def _tracked_inventory(repo_root: Path) -> tuple[int, tuple[str, ...] | None]:
    command = (
        "git",
        "ls-files",
        "-z",
        "--",
        GENERATED_DIR.as_posix(),
    )
    print(f"[generated] tracked inventory: {shlex.join(command)}", flush=True)
    try:
        result = subprocess.run(
            command,
            cwd=repo_root,
            check=False,
            stdout=subprocess.PIPE,
        )
    except OSError as error:
        return _error(f"cannot inspect tracked generated files: {error}"), None

    if result.returncode != 0:
        print(
            f"[generated] error: tracked inventory command failed with "
            f"exit code {result.returncode}",
            file=sys.stderr,
        )
        return result.returncode, None

    prefix = f"{GENERATED_DIR.as_posix()}/"
    inventory: list[str] = []
    try:
        tracked_paths = (
            entry.decode("utf-8") for entry in result.stdout.split(b"\0") if entry
        )
        for tracked_path in tracked_paths:
            if not tracked_path.startswith(prefix):
                return _error(
                    f"unexpected tracked path outside {GENERATED_DIR}: {tracked_path}"
                ), None
            inventory.append(tracked_path.removeprefix(prefix))
    except UnicodeDecodeError as error:
        return _error(f"tracked generated path is not UTF-8: {error}"), None

    if not inventory:
        return _error("tracked generated inventory is empty"), None

    return 0, tuple(sorted(inventory))


def _generated_inventory(directory: Path) -> tuple[str, ...]:
    return tuple(
        sorted(
            path.relative_to(directory).as_posix()
            for path in directory.rglob("*")
            if path.is_file()
        )
    )


def _compare_generated_files(
    repo_root: Path,
    temporary_generated: Path,
    tracked_inventory: tuple[str, ...],
) -> bool:
    regenerated_inventory = _generated_inventory(temporary_generated)
    if regenerated_inventory != tracked_inventory:
        missing = sorted(set(tracked_inventory) - set(regenerated_inventory))
        extra = sorted(set(regenerated_inventory) - set(tracked_inventory))
        _error(
            "generated inventory mismatch; "
            f"missing={missing or 'none'}, extra={extra or 'none'}"
        )
        return False

    tracked_root = repo_root / GENERATED_DIR
    for relative_path in tracked_inventory:
        tracked_path = tracked_root / relative_path
        regenerated_path = temporary_generated / relative_path
        try:
            tracked_bytes = tracked_path.read_bytes()
            regenerated_bytes = regenerated_path.read_bytes()
        except OSError as error:
            _error(f"cannot compare generated file {relative_path}: {error}")
            return False

        if tracked_bytes != regenerated_bytes:
            _error(f"generated file differs byte-for-byte: {relative_path}")
            return False

    return True


def main() -> int:
    """Verify the jar and compare a temporary regeneration with tracked files."""

    if not _verify_jar(REPO_ROOT):
        return 1

    inventory_exit_code, tracked_inventory = _tracked_inventory(REPO_ROOT)
    if tracked_inventory is None:
        return inventory_exit_code

    with tempfile.TemporaryDirectory(prefix="pietto-antlr-") as temporary:
        temporary_generated = Path(temporary) / "generated"
        temporary_generated.mkdir()
        command = (
            "java",
            "-jar",
            ANTLR_JAR.as_posix(),
            "-Dlanguage=Python3",
            "-visitor",
            "-no-listener",
            "-Xexact-output-dir",
            "-o",
            str(temporary_generated),
            GRAMMAR.as_posix(),
        )
        print(f"[generated] regenerate: {shlex.join(command)}", flush=True)
        try:
            result = subprocess.run(
                command,
                cwd=REPO_ROOT,
                check=False,
            )
        except OSError as error:
            return _error(f"cannot run Java/ANTLR: {error}")

        if result.returncode != 0:
            print(
                f"[generated] error: Java/ANTLR failed with exit code "
                f"{result.returncode}",
                file=sys.stderr,
            )
            return result.returncode

        (temporary_generated / "__init__.py").touch(exist_ok=True)
        if not _compare_generated_files(
            REPO_ROOT,
            temporary_generated,
            tracked_inventory,
        ):
            return 1

    print(
        f"[generated] verified {len(tracked_inventory)} tracked files byte-for-byte",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
