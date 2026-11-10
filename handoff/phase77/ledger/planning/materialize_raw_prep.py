"""Materialize recovered raw-prep files from exact, local literal patches only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PATCHES = ROOT / "literal-patches"
RAW = (
    "nested_oracle",
    "s13_ordered_values",
    "s15_division",
    "s09_typed_parameters",
    "float_equivalence",
    "stats_probe",
)


def apply_update(current: str, body: list[str]) -> str:
    """Apply the narrow Add/Update patch dialect emitted by recorded tool calls."""
    lines = current.splitlines()
    offset = 0
    before: list[str] = []
    after: list[str] = []

    def commit() -> None:
        nonlocal lines, offset, before, after
        if not before and not after:
            return
        for index in range(offset, len(lines) - len(before) + 1):
            if lines[index : index + len(before)] == before:
                lines[index : index + len(before)] = after
                offset = index + len(after)
                before, after = [], []
                return
        raise ValueError("update hunk has no unique recorded base")

    for line in body:
        if line == "@@":
            commit()
        elif line.startswith("+"):
            after.append(line[1:])
        elif line.startswith("-"):
            before.append(line[1:])
        elif line.startswith(" "):
            before.append(line[1:])
            after.append(line[1:])
        elif line.startswith("\\"):
            continue
        elif line == "":
            before.append("")
            after.append("")
        else:
            raise ValueError(f"unsupported update line: {line!r}")
    commit()
    return "\n".join(lines) + "\n"


def materialize(name: str, output: Path) -> dict[str, object]:
    state: dict[str, str] = {}
    gaps: list[dict[str, str]] = []
    source = PATCHES / f"{name}.patch"
    chunks = source.read_text(encoding="utf-8").split("*** Begin Patch\n")
    for chunk in chunks:
        command = None
        path = None
        body: list[str] = []
        for line in chunk.splitlines():
            if line.startswith("*** Add File: ") or line.startswith("*** Update File: ") or line.startswith("*** Delete File: "):
                if command is not None:
                    if command == "add":
                        state[path] = "\n".join(item[1:] for item in body if item.startswith("+")) + "\n"
                    elif command == "update":
                        while body and body[-1] == "":
                            body.pop()
                        if path not in state:
                            gaps.append({"path": path, "reason": "update_base_not_in_literal_bundle"})
                        else:
                            try:
                                state[path] = apply_update(state[path], body)
                            except ValueError as error:
                                gaps.append({"path": path, "reason": str(error)})
                    elif command == "delete":
                        state.pop(path, None)
                header, path = line.split(": ", 1)
                command = header.split()[1].lower()
                body = []
            elif line == "*** End Patch":
                continue
            elif command is not None:
                body.append(line)
        if command is not None:
            if command == "add":
                state[path] = "\n".join(item[1:] for item in body if item.startswith("+")) + "\n"
            elif command == "update":
                while body and body[-1] == "":
                    body.pop()
                if path not in state:
                    gaps.append({"path": path, "reason": "update_base_not_in_literal_bundle"})
                else:
                    try:
                        state[path] = apply_update(state[path], body)
                    except ValueError as error:
                        gaps.append({"path": path, "reason": str(error)})
            elif command == "delete":
                state.pop(path, None)

    destination = output / name
    destination.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for original, content in state.items():
        target = destination / Path(original).name
        target.write_text(content, encoding="utf-8")
        written.append(target.relative_to(output).as_posix())
    return {"source_patch": source.name, "written": sorted(written), "gaps": gaps}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "materialized")
    args = parser.parse_args()
    output = args.out.resolve()
    if ROOT not in output.parents:
        raise ValueError("--out must remain under the planning directory")
    report = {name: materialize(name, output) for name in RAW}
    (output / "materialization-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
