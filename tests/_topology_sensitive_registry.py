"""Single deterministic node-ID registry for topology-sensitive pytest items."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = REPO_ROOT / "tests"
SEED_OWNER = TESTS_ROOT / (
    "test_phase53_lag_lead_navigation_offset_default_nullability_contract.py"
)
SCHEMA = "pietto.gate2.topology-registry.v1"
FOCUSED_INFRASTRUCTURE_TEST = (
    "tests/test_phase54_post_slice6_workflow_efficiency_interlude.py"
)
EXPECTED_NODE_COUNT = 323
EXPECTED_FILE_COUNT = 159
EXPECTED_PAYLOAD_BYTES = 41085
EXPECTED_SELECTED_ITEMS = 1143
EXPECTED_SHA256 = "82fa7032fba40896bf6f0f6a132ca1f8e7ffdd87fc66bddd71ac164e3689064c"
GIT_COMMANDS = {
    "status",
    "diff",
    "branch",
    "rev-parse",
    "rev-list",
    "worktree",
    "symbolic-ref",
    "for-each-ref",
    "log",
    "show-ref",
}
SPECIAL_CALLS = {"git_diff_name_only", "_git_diff_name_only"}


def _call_name(node: ast.Call) -> str:
    function = node.func
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute):
        return function.attr
    return ""


def _seed_node_ids() -> tuple[str, ...]:
    tree = ast.parse(
        SEED_OWNER.read_text(encoding="utf-8"), filename=SEED_OWNER.as_posix()
    )
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "DIRTY_OVERLAY"
        ):
            assert node.value is not None
            value = ast.literal_eval(node.value)
            assert isinstance(value, tuple)
            result = tuple(item.removeprefix("--deselect=") for item in value)
            assert len(result) == 185
            assert len(set(result)) == 185
            return result
    raise AssertionError("DIRTY_OVERLAY seed is absent")


LEGACY_DIRTY_OVERLAY_NODE_IDS = _seed_node_ids()


def _split_node_id(node_id: str) -> tuple[str, str]:
    relative, separator, name = node_id.partition("::")
    assert separator and relative and name
    return relative, name


def _discover_registry() -> tuple[
    tuple[str, ...],
    dict[tuple[str, str], ast.FunctionDef | ast.AsyncFunctionDef],
]:
    functions: dict[tuple[str, str], ast.FunctionDef | ast.AsyncFunctionDef] = {}
    calls: dict[tuple[str, str], set[tuple[str, str]]] = {}
    primitive: set[tuple[str, str]] = set()

    for path in sorted(TESTS_ROOT.glob("test_*.py")):
        relative = path.relative_to(REPO_ROOT).as_posix()
        if relative == FOCUSED_INFRASTRUCTURE_TEST:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        local = {
            node.name: node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for name, function in local.items():
            key = (relative, name)
            functions[key] = function
            dependencies: set[tuple[str, str]] = set()
            is_primitive = False
            for node in ast.walk(function):
                if isinstance(node, ast.Call):
                    called = _call_name(node)
                    if called in local:
                        dependencies.add((relative, called))
                    literals = {
                        child.value
                        for child in ast.walk(node)
                        if isinstance(child, ast.Constant)
                        and isinstance(child.value, str)
                    }
                    if (
                        called in SPECIAL_CALLS
                        or "gate2" in called.lower()
                        or ("git" in called.lower() and bool(literals & GIT_COMMANDS))
                    ):
                        is_primitive = True
                    if (
                        isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "os"
                        and node.func.attr == "getenv"
                    ):
                        is_primitive = True
                if (
                    isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "os"
                    and node.attr == "environ"
                ):
                    is_primitive = True
            calls[key] = dependencies
            if is_primitive:
                primitive.add(key)

    sensitive = set(primitive)
    while True:
        previous = len(sensitive)
        sensitive |= {
            key for key, dependencies in calls.items() if dependencies & sensitive
        }
        if len(sensitive) == previous:
            break

    registry = tuple(
        sorted(
            set(LEGACY_DIRTY_OVERLAY_NODE_IDS)
            | {
                f"{relative}::{name}"
                for relative, name in sensitive
                if name.startswith("test_")
            }
        )
    )
    assert all(_split_node_id(item) in functions for item in registry)
    return registry, functions


def _cardinality(
    node_id: str,
    functions: dict[tuple[str, str], ast.FunctionDef | ast.AsyncFunctionDef],
) -> int:
    function = functions[_split_node_id(node_id)]
    result = 1
    for decorator in function.decorator_list:
        if not (
            isinstance(decorator, ast.Call) and _call_name(decorator) == "parametrize"
        ):
            continue
        values = decorator.args[1]
        assert (
            isinstance(values, ast.Call)
            and isinstance(values.func, ast.Name)
            and values.func.id == "range"
            and len(values.args) == 1
            and isinstance(values.args[0], ast.Constant)
            and type(values.args[0].value) is int
        ), ast.dump(values)
        result *= values.args[0].value
    return result


TOPOLOGY_SENSITIVE_NODE_IDS, _FUNCTIONS = _discover_registry()
TOPOLOGY_REGISTRY_PAYLOAD = "".join(
    f"{node_id}\n" for node_id in TOPOLOGY_SENSITIVE_NODE_IDS
).encode("utf-8")
TOPOLOGY_REGISTRY_SHA256 = hashlib.sha256(TOPOLOGY_REGISTRY_PAYLOAD).hexdigest()
TOPOLOGY_SELECTED_ITEMS = sum(
    _cardinality(node_id, _FUNCTIONS) for node_id in TOPOLOGY_SENSITIVE_NODE_IDS
)
TOPOLOGY_REGISTRY_FILES = len(
    {node_id.split("::", 1)[0] for node_id in TOPOLOGY_SENSITIVE_NODE_IDS}
)

assert len(TOPOLOGY_SENSITIVE_NODE_IDS) == EXPECTED_NODE_COUNT
assert TOPOLOGY_REGISTRY_FILES == EXPECTED_FILE_COUNT
assert len(TOPOLOGY_REGISTRY_PAYLOAD) == EXPECTED_PAYLOAD_BYTES
assert TOPOLOGY_SELECTED_ITEMS == EXPECTED_SELECTED_ITEMS
assert TOPOLOGY_REGISTRY_SHA256 == EXPECTED_SHA256
