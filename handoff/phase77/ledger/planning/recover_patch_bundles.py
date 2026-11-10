"""Extract exact historical patch strings without replaying them.

The script only reads the recovery records. With --out it may write *.patch
files below this script's directory; it never applies a patch or touches the
canonical tree. It is intentionally not run by recovery preparation.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RECORDS = ROOT.parent / "records"
SOURCES = {
    "duckdb_gate1": ("duckdb_gate1.jsonl", (114, 128)),
    "duckdb_review": ("phase_scope.jsonl", (996, 1023)),
    "phase80_interop": ("interop_gate1.jsonl", (115, 162, 173)),
    "mysql_nested": ("duckdb_seam.jsonl", (707, 713, 719, 725)),
    "nested_oracle": ("p77_nested_decision.jsonl", (166, 194, 226)),
    "s13_ordered_values": ("p77_ordered_values.jsonl", (143, 150, 183, 213)),
    "s15_division": ("p77_division.jsonl", (91, 120, 126, 131, 145, 161)),
    "s09_typed_parameters": ("p77_typed_parameters.jsonl", (129, 180, 194, 200)),
    "float_equivalence": ("p77_float_equivalence.jsonl", (144, 295, 426, 440, 612, 694)),
    "stats_probe": ("editor_latency.jsonl", (954, 963, 986, 1000, 1006, 1020, 1026, 1031, 1045, 1141, 1155, 1162, 1168, 1180, 1187, 1214, 1224, 1231)),
}
PATCH = re.compile(
    r'(?:const patch = |tools\.apply_patch\()("(?:[^"\\]|\\.)*")', re.DOTALL
)
FILES = re.compile(
    r'const files = \{(?P<files>.*?)\n\};\nlet patch = (?P<start>"(?:[^"\\]|\\.)*");(?P<tail>.*)',
    re.DOTALL,
)
FILE = re.compile(
    r'"(?P<path>[^"]+)": `(?P<content>(?:[^`\\]|\\.)*)`,', re.DOTALL
)
APPEND = re.compile(r'patch \+= ("(?:[^"\\]|\\.)*");', re.DOTALL)
TEMPLATE = re.compile(r'const (?P<name>\w+) = `(?P<value>(?:[^`\\]|\\.)*)`;', re.DOTALL)
ASSEMBLED = re.compile(r'const patch = (?P<expression>.*?);\nconst r =', re.DOTALL)
ASSEMBLED_TOKEN = re.compile(
    r'(?P<string>"(?:[^"\\]|\\.)*")|(?P<variable>\w+)\.split\("\\n"\)'
    r'\.map\(x => "\+" \+ x\)\.join\("\\n"\)'
)


def _template(value: str) -> str:
    """Decode only JavaScript template escapes used in the captured file map."""
    decoded: list[str] = []
    index = 0
    escapes = {"n": "\n", "r": "\r", "t": "\t", "`": "`", "\\": "\\", '"': '"'}
    while index < len(value):
        if value[index] != "\\":
            decoded.append(value[index])
            index += 1
            continue
        if index + 1 == len(value) or value[index + 1] not in escapes:
            raise ValueError("unsupported template escape")
        decoded.append(escapes[value[index + 1]])
        index += 2
    return "".join(decoded)


def literal_patch(source: str) -> str | None:
    dynamic = FILES.search(source)
    if dynamic is not None:
        files = list(FILE.finditer(dynamic["files"]))
        if not files:
            raise ValueError("dynamic patch has no files")
        result = json.loads(dynamic["start"])
        for item in files:
            result += f"*** Add File: {item['path']}\n"
            result += "\n".join(f"+{line}" for line in _template(item["content"]).split("\n"))
            result += "\n"
        result += "".join(json.loads(item.group(1)) for item in APPEND.finditer(dynamic["tail"]))
        return result
    assembled = ASSEMBLED.search(source)
    if assembled is not None and ".split" in assembled["expression"]:
        templates = {
            item["name"]: _template(item["value"])
            for item in TEMPLATE.finditer(source[: assembled.start()])
        }
        result: list[str] = []
        cursor = 0
        for item in ASSEMBLED_TOKEN.finditer(assembled["expression"]):
            if assembled["expression"][cursor : item.start()].strip() not in {"", "+"}:
                raise ValueError("unsupported assembled patch expression")
            if item["string"] is not None:
                result.append(json.loads(item["string"]))
            else:
                value = templates.get(item["variable"])
                if value is None:
                    raise ValueError("assembled patch references an unknown template")
                result.append("\n".join(f"+{line}" for line in value.split("\n")))
            cursor = item.end()
        if assembled["expression"][cursor:].strip():
            raise ValueError("unsupported assembled patch suffix")
        return "".join(result)
    match = PATCH.search(source)
    return None if match is None else json.loads(match.group(1))


def patches(name: str) -> list[str]:
    record_name, lines = SOURCES[name]
    wanted = set(lines)
    found: dict[int, str] = {}
    for raw in (RECORDS / record_name).read_text(encoding="utf-8").splitlines():
        event = json.loads(raw)
        if event.get("line") not in wanted:
            continue
        patch = literal_patch(event.get("input", ""))
        if patch is None:
            raise ValueError(f"{record_name}:{event['line']} has no literal patch")
        if event["line"] in found:
            raise ValueError(f"duplicate source line {record_name}:{event['line']}")
        found[event["line"]] = patch
    if set(found) != wanted:
        raise ValueError(f"missing source lines for {name}: {sorted(wanted - set(found))}")
    return [found[line] for line in lines]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name", choices=sorted(SOURCES))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = "\n\n".join(patches(args.name))
    if args.out is None:
        print(result, end="")
        return
    target = args.out.resolve()
    if ROOT not in target.parents:
        raise ValueError("--out must remain under the planning directory")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(result, encoding="utf-8")


if __name__ == "__main__":
    main()
