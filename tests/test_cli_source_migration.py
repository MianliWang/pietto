from __future__ import annotations

from pathlib import Path

import pytest

from pietto import cli


def test_migrate_outputs_complete_utf8_source_and_never_changes_input(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = (
        b'\xef\xbb\xbf# null true\r\nsource data is postgres.table("null true")\r\n'
    )
    path = tmp_path / "source.pietto"
    path.write_bytes(source)

    assert cli.main(["migrate", str(path)]) == 0

    captured = capsys.readouterr()
    assert captured.out.encode("utf-8") == source.replace(
        b"source data is", b"source data ="
    )
    assert captured.err == ""
    assert path.read_bytes() == source


def test_migrate_failure_emits_no_partial_source_and_leaves_input_unchanged(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = (
        'source data is postgres.table("data")\n'
        "relationship r:\n"
        "    endpoint first: data\n"
        "    endpoint second: other\n"
    )
    path = tmp_path / "manual.pietto"
    path.write_text(source, encoding="utf-8")

    assert cli.main(["migrate", str(path)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"{path}:2:1 PIE-P1011 error:" in captured.err
    assert "manual migration" in captured.err
    assert path.read_text(encoding="utf-8") == source


@pytest.mark.parametrize("kind", ["missing", "directory", "invalid_utf8"])
def test_migrate_file_errors_are_usage_failures_without_tracebacks(
    kind: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / kind
    if kind == "directory":
        path.mkdir()
    elif kind == "invalid_utf8":
        path.write_bytes(b"\xff")

    assert cli.main(["migrate", str(path)]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"{path}: error:" in captured.err
    assert "Traceback" not in captured.err


def test_migrate_requires_input_and_has_no_in_place_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["migrate"]) == 2
    assert capsys.readouterr().out == ""
    assert cli.main(["migrate", "file.pietto", "--in-place"]) == 2
    assert "unrecognized arguments: --in-place" in capsys.readouterr().err


def test_migrate_read_is_bounded_before_utf8_decoding(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "too_large.pietto"
    source = b"#" + b"a" * 1_048_575 + b"\xff"
    path.write_bytes(source)

    assert cli.main(["migrate", str(path)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-P1006" in captured.err
    assert path.read_bytes() == source
