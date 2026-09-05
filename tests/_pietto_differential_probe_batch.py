"""Acquire several exact differential family observations in one child process.

This is test-only acquisition topology. Every logical request still invokes its
own existing probe ``observation`` exactly once, renders it with that probe's
own ``render`` encoder, and keeps its own workspace, working directory, and
ambient marker. No observation, result, or failure is cached, reused, retried,
normalized, or shared between requests.
"""

from __future__ import annotations

import argparse
import base64
import importlib
import json
import os
from pathlib import Path
import sys
import traceback

FAMILY_MODULES: dict[str, str] = {
    "phase58": "_pietto_project_explain_differential_probe",
    "phase59": "_pietto_phase59_graph_differential_probe",
    "phase60": "_pietto_phase60_window_differential_probe",
    "phase61": "_pietto_phase61_project_ir_differential_probe",
    "phase62": "_pietto_phase62_join_differential_probe",
    "phase63": "_pietto_phase63_query_block_ir_differential_probe",
}
FAMILY_AMBIENT: dict[str, str] = {
    "phase58": "PIETTO_SLICE16_IRRELEVANT",
    "phase59": "PIETTO_SLICE11_IRRELEVANT",
    "phase60": "PIETTO_SLICE12_IRRELEVANT",
    "phase61": "PIETTO_SLICE11_IRRELEVANT",
    "phase62": "PIETTO_SLICE15_IRRELEVANT",
    "phase63": "PIETTO_PHASE63_SLICE15_AMBIENT",
}
# Only these families reach the CLI through `_run_cli_pair`, so only these may
# be served by one explicit CLI worker session.
CLI_SESSION_FAMILIES: frozenset[str] = frozenset({"phase58", "phase59", "phase60"})


def _module(family: str) -> object:
    if family not in FAMILY_MODULES:
        raise KeyError(f"Unknown differential family: {family!r}")
    module = importlib.import_module(FAMILY_MODULES[family])
    declared = getattr(module, "SEED_ENVIRONMENT", None)
    if declared is not None and declared != FAMILY_AMBIENT[family]:
        raise AssertionError(
            f"{family} ambient marker drifted: {declared!r} != "
            f"{FAMILY_AMBIENT[family]!r}"
        )
    return module


def _acquire(request: dict[str, object]) -> bytes:
    family = str(request["family"])
    module = _module(family)
    workspace = Path(str(request["workspace"]))
    cwd = Path(str(request["cwd"]))
    workspace.mkdir(parents=True, exist_ok=True)
    cwd.mkdir(parents=True, exist_ok=True)

    ambient_name = FAMILY_AMBIENT[family]
    previous_ambient = os.environ.get(ambient_name)
    previous_cwd = os.getcwd()
    os.environ[ambient_name] = str(request["ambient"])
    os.chdir(cwd)
    try:
        render = module.render  # type: ignore[attr-defined]
        document = render(module.observation(workspace), workspace)  # type: ignore[attr-defined]
    finally:
        os.chdir(previous_cwd)
        if previous_ambient is None:
            os.environ.pop(ambient_name, None)
        else:
            os.environ[ambient_name] = previous_ambient
    if type(document) is not bytes or not document.endswith(b"\n"):
        raise AssertionError(f"{family} produced no exact document.")
    if document.endswith(b"\n\n"):
        raise AssertionError(f"{family} produced a trailing blank line.")
    return document


def _import_origin() -> str:
    import pietto

    return str(Path(pietto.__file__).resolve())


def run(manifest: dict[str, object]) -> dict[str, object]:
    """Acquire every requested family result in one interpreter, in order."""

    requests = manifest["requests"]
    if type(requests) is not list or not requests:
        raise AssertionError("A batch cell requires at least one request.")
    families = [str(item["family"]) for item in requests]
    unknown = sorted(set(families) - set(FAMILY_MODULES))
    if unknown:
        raise AssertionError(f"Unknown differential families: {unknown}")

    results: dict[str, str] = {}
    session_needed = any(family in CLI_SESSION_FAMILIES for family in families)
    if session_needed:
        import _pietto_project_explain_scenarios as scenarios

        with scenarios.cli_worker_session():
            for request in requests:
                results[str(request["key"])] = base64.b64encode(
                    _acquire(request)
                ).decode("ascii")
    else:
        for request in requests:
            results[str(request["key"])] = base64.b64encode(_acquire(request)).decode(
                "ascii"
            )

    if len(results) != len(requests):
        raise AssertionError("Batch request keys must be unique.")
    return {
        "results": results,
        "python_version": list(sys.version_info[:2]),
        "hash_seed": os.environ.get("PYTHONHASHSEED"),
        "import_origin": _import_origin(),
        "executable": sys.executable,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    namespace = parser.parse_args(argv)
    manifest = json.loads(namespace.manifest.read_text(encoding="utf-8"))
    try:
        payload = run(manifest)
    except BaseException:
        sys.stderr.write(traceback.format_exc())
        return 1
    pending = namespace.output.with_name(f"{namespace.output.name}.pending")
    pending.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    os.replace(pending, namespace.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
