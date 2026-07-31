"""Deterministically discover Pietto Gate 2 readers and their dependencies."""

from __future__ import annotations

import argparse
import ast
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Iterable


SCHEMA = "pietto.gate2.reader-closure.v1"
TOOL_VERSION = "1"
HISTORICAL_MANIFEST_PATH = "tests/_phase54_active_gate2_manifest.py"
STABLE_MANIFEST_DATA_PATH = "tests/_active_gate2_manifest_data.py"
SEPARATELY_EXECUTED_SUPPORT_PATHS = frozenset(
    {"tests/test_phase54_post_slice6_workflow_efficiency_interlude.py"}
)
PATH_LITERAL = re.compile(
    r"(?:AGENTS\.md|README\.md|(?:docs|scripts|src|tests)/[A-Za-z0-9_./-]+)"
)
SHA256_LITERAL = re.compile(r"\b[0-9a-f]{64}\b")
TOPOLOGY_TERMS = (
    "GITHUB_EVENT_NAME",
    "GITHUB_EVENT_PATH",
    "GITHUB_REF",
    "GITHUB_SHA",
    "origin/main",
    "rev-parse",
    "--is-shallow-repository",
    "--cached",
    "branch --show-current",
)
READ_CALLS = {"open", "read_text", "read_bytes", "read", "git_show_bytes"}


class ReaderAuditError(RuntimeError):
    """Raised when a reader cannot be classified without guessing."""


@dataclass(frozen=True, order=True, slots=True)
class ReaderEdge:
    reader: str
    target: str
    reason: str
    direct: bool


@dataclass(frozen=True, order=True, slots=True)
class ImportBinding:
    importer: str
    target: str
    imported_name: str
    local_name: str


def _canonical_json(document: object) -> bytes:
    return (
        json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _python_paths(root: Path) -> tuple[Path, ...]:
    paths = set(root.glob("tests/**/*.py")) | set(root.glob("scripts/**/*.py"))
    return tuple(sorted(path for path in paths if path.is_file()))


def _module_index(root: Path, paths: Iterable[Path]) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in paths:
        relative = path.relative_to(root).as_posix()
        result[path.stem] = relative
        module = relative.removesuffix(".py").replace("/", ".")
        result[module] = relative
        if relative.startswith("tests/"):
            result[module.removeprefix("tests.")] = relative
        if relative.startswith("scripts/"):
            result[module.removeprefix("scripts.")] = relative
    return result


def _imports(tree: ast.AST, modules: dict[str, str]) -> set[str]:
    result: set[str] = set()
    for node in ast.walk(tree):
        names: tuple[str, ...]
        if isinstance(node, ast.Import):
            names = tuple(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = (node.module,)
        else:
            continue
        for name in names:
            if name in modules:
                result.add(modules[name])
    return result


def _import_bindings(
    relative: str, tree: ast.AST, modules: dict[str, str]
) -> tuple[ImportBinding, ...]:
    result: set[ImportBinding] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        target = modules.get(node.module)
        if target is None:
            continue
        for alias in node.names:
            if alias.name == "*":
                continue
            result.add(
                ImportBinding(
                    importer=relative,
                    target=target,
                    imported_name=alias.name,
                    local_name=alias.asname or alias.name,
                )
            )
    return tuple(sorted(result))


def _assignment_sets(source: str) -> dict[str, set[str]]:
    tree = ast.parse(source)
    assignments = {
        node.targets[0].id: node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    }

    def resolve(node: ast.expr) -> set[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return {node.value}
        if isinstance(node, ast.Name):
            return resolve(assignments[node.id])
        if isinstance(node, ast.Starred):
            return resolve(node.value)
        if isinstance(node, (ast.Set, ast.Tuple, ast.List)):
            return set().union(*(resolve(element) for element in node.elts))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return resolve(node.left) | resolve(node.right)
        return set()

    return {name: resolve(value) for name, value in assignments.items()}


def _git_show(root: Path, revision: str, path: str) -> str:
    return subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def _current_manifest_assignments(root: Path, relative: str) -> dict[str, set[str]]:
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ReaderAuditError(
            "active manifest data escapes repository root"
        ) from error
    try:
        source = path.read_text(encoding="utf-8")
        return _assignment_sets(source)
    except (OSError, KeyError, SyntaxError) as error:
        raise ReaderAuditError(
            f"active manifest data is unreadable: {relative}:{type(error).__name__}"
        ) from error


def reader_seed(
    root: Path, base: str, active_manifest_data: str | None = None
) -> tuple[tuple[str, ...], str]:
    """Recover exact roots from current authority or the immutable base."""

    if active_manifest_data is not None:
        assignments = _current_manifest_assignments(root, active_manifest_data)
        roots = set(assignments.get("ACTIVE_GATE2_DIRECT_READER_PATHS", set()))
        if not roots:
            raise ReaderAuditError("active manifest direct reader seed is empty")
        missing = sorted(path for path in roots if not (root / path).is_file())
        if missing:
            raise ReaderAuditError(
                "active reader seed references missing paths: " + ", ".join(missing)
            )
        return tuple(sorted(roots)), active_manifest_data

    failures: list[str] = []
    for relative in (STABLE_MANIFEST_DATA_PATH, HISTORICAL_MANIFEST_PATH):
        try:
            source = _git_show(root, base, relative)
            assignments = _assignment_sets(source)
            if assignments.get("ACTIVE_GATE2_DIRECT_READER_PATHS"):
                roots = set(assignments["ACTIVE_GATE2_DIRECT_READER_PATHS"])
            else:
                roots = set(assignments["MECHANICAL_READER_PATHS"])
                roots |= {
                    path
                    for path in assignments["ADDED_PATHS"]
                    if path.startswith("tests/test_") and path.endswith(".py")
                }
        except (KeyError, SyntaxError, subprocess.SubprocessError) as error:
            failures.append(f"{relative}:{type(error).__name__}")
            continue
        if not roots:
            failures.append(f"{relative}:empty")
            continue
        missing = sorted(path for path in roots if not (root / path).is_file())
        if missing:
            raise ReaderAuditError(
                "base reader seed references missing current paths: "
                + ", ".join(missing)
            )
        return tuple(sorted(roots)), relative
    raise ReaderAuditError("no readable base reader seed: " + ", ".join(failures))


def historical_reader_roots(root: Path, base: str) -> tuple[str, ...]:
    """Compatibility API returning the exact immutable-base reader roots."""

    roots, _ = reader_seed(root, base)
    return roots


def _literal_paths(tree: ast.AST) -> set[str]:
    result: set[str] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        result.update(PATH_LITERAL.findall(node.value))
    return result


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _unresolved_dynamic_warnings(relative: str, tree: ast.AST) -> tuple[str, ...]:
    warnings: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node) not in READ_CALLS:
            continue
        if relative == "scripts/audit_gate2_readers.py":
            continue
        expression = ast.unparse(node.func)
        call_text = ast.unparse(node)
        if expression.startswith("os."):
            continue
        if "tmp_path" in call_text or "Path(__file__)" in call_text:
            continue
        literals = {
            child.value
            for child in ast.walk(node)
            if isinstance(child, ast.Constant) and isinstance(child.value, str)
        }
        if any(PATH_LITERAL.search(value) for value in literals):
            continue
        if "REPO_ROOT" in call_text or "ROOT" in call_text:
            continue
        if "arguments." in call_text:
            continue
        receiver = expression.partition(".")[0]
        if receiver.lower().endswith(("path", "file", "output", "target")):
            continue
        if isinstance(node.func, ast.Attribute):
            owner = node.func.value
            if isinstance(owner, ast.Name):
                continue
            if (
                isinstance(owner, ast.Subscript)
                and isinstance(owner.value, ast.Name)
                and owner.value.id in {"sidecars", "documents", "payloads"}
            ):
                continue
            if (
                isinstance(owner, ast.Call)
                and isinstance(owner.func, ast.Name)
                and owner.func.id == "Path"
                and len(owner.args) == 1
                and (
                    (
                        isinstance(owner.args[0], ast.Name)
                        and owner.args[0].id.lower().endswith(("path", "file"))
                    )
                    or (
                        isinstance(owner.args[0], ast.Attribute)
                        and owner.args[0].attr.lower().endswith(("path", "file"))
                    )
                )
            ):
                continue
        if any(token in expression for token in ("capture", "StringIO")):
            continue
        docstring = (
            ast.get_docstring(tree, clean=False)
            if isinstance(tree, ast.Module)
            else None
        )
        if docstring and "gate2-reader: resolved-dynamic" in docstring:
            continue
        warnings.append(f"{relative}:{getattr(node, 'lineno', 0)}:{expression}")
    return tuple(sorted(set(warnings)))


def _top_level_functions(tree: ast.Module) -> dict[str, ast.AST]:
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _referenced_names(node: ast.AST) -> set[str]:
    return {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}


def _reader_dependency_edges(
    relative: str, tree: ast.Module, closure: set[str]
) -> tuple[set[ReaderEdge], set[ReaderEdge]]:
    executing: set[ReaderEdge] = set()
    inventory: set[ReaderEdge] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if not (
                    isinstance(key, ast.Constant)
                    and isinstance(key.value, str)
                    and key.value in closure
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                    and SHA256_LITERAL.fullmatch(value.value)
                ):
                    continue
                executing.add(ReaderEdge(relative, key.value, "literal_sha256", False))
        name = ""
        value_node: ast.expr | None = None
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            name = node.targets[0].id
            value_node = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            value_node = node.value
        if "READER_MIGRATION_PATHS" not in name or value_node is None:
            continue
        for child in ast.walk(value_node):
            if (
                isinstance(child, ast.Constant)
                and isinstance(child.value, str)
                and child.value in closure
            ):
                inventory.add(
                    ReaderEdge(
                        relative,
                        child.value,
                        "nonexecuting_migration_inventory",
                        False,
                    )
                )
    return executing, inventory


def _sensitive_import_closure(
    *,
    trees: dict[str, ast.Module],
    bindings: tuple[ImportBinding, ...],
) -> tuple[set[str], set[ReaderEdge]]:
    """Propagate only symbols that actually depend on the stable predicate."""

    sensitive: dict[str, set[str]] = defaultdict(set)
    sensitive["tests/_active_gate2_manifest.py"].update(
        {
            "_matches_active_gate2_candidate",
            "_matches_active_gate2_manifest",
            "_matches_active_gate2_reconciled_main",
            "active_gate2_candidate_is_active",
            "active_gate2_local_lifecycle_is_active",
            "active_gate2_manifest_is_active",
        }
    )
    functions = {
        relative: _top_level_functions(tree) for relative, tree in trees.items()
    }
    import_edges: set[ReaderEdge] = set()
    changed = True
    while changed:
        changed = False
        tainted_imports: dict[str, set[str]] = defaultdict(set)
        for binding in bindings:
            if binding.imported_name not in sensitive.get(binding.target, set()):
                continue
            tainted_imports[binding.importer].add(binding.local_name)
            import_edges.add(
                ReaderEdge(
                    binding.importer,
                    binding.target,
                    f"sensitive_symbol_import:{binding.imported_name}",
                    False,
                )
            )
        for relative, local_functions in functions.items():
            tainted_names = tainted_imports.get(relative, set()) | sensitive.get(
                relative, set()
            )
            for name, function in local_functions.items():
                if name in sensitive[relative]:
                    continue
                if _referenced_names(function) & tainted_names:
                    sensitive[relative].add(name)
                    changed = True
        for binding in bindings:
            if binding.local_name in sensitive.get(binding.importer, set()):
                if binding.imported_name not in sensitive[binding.target]:
                    sensitive[binding.target].add(binding.imported_name)
                    changed = True

    paths = {
        relative
        for relative, names in sensitive.items()
        if relative.startswith("tests/test_")
        and any(name.startswith("test_") for name in names)
    }
    return paths, import_edges


def _strongly_connected_components(
    nodes: Iterable[str], edges: dict[str, set[str]]
) -> tuple[tuple[str, ...], ...]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    components: list[tuple[str, ...]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in sorted(edges.get(node, set())):
            if target not in indices:
                visit(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[target])
        if lowlinks[node] != indices[node]:
            return
        component: list[str] = []
        while True:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == node:
                break
        components.append(tuple(sorted(component)))

    for node in sorted(set(nodes)):
        if node not in indices:
            visit(node)
    return tuple(sorted(components))


def _dependency_first_order(
    nodes: set[str], imports: dict[str, set[str]]
) -> tuple[tuple[str, ...], ...]:
    components = _strongly_connected_components(nodes, imports)
    owner = {path: index for index, group in enumerate(components) for path in group}
    dependencies: dict[int, set[int]] = defaultdict(set)
    dependents: dict[int, set[int]] = defaultdict(set)
    for reader, targets in imports.items():
        if reader not in owner:
            continue
        for target in targets:
            if target not in owner or owner[target] == owner[reader]:
                continue
            dependencies[owner[reader]].add(owner[target])
            dependents[owner[target]].add(owner[reader])
    ready = deque(
        sorted(index for index in range(len(components)) if not dependencies[index])
    )
    levels: list[tuple[str, ...]] = []
    emitted: set[int] = set()
    while ready:
        current = tuple(ready)
        ready.clear()
        levels.append(
            tuple(sorted(path for index in current for path in components[index]))
        )
        for index in current:
            emitted.add(index)
            for dependent in sorted(dependents[index]):
                dependencies[dependent].discard(index)
                if not dependencies[dependent] and dependent not in emitted:
                    ready.append(dependent)
    assert len(emitted) == len(components)
    return tuple(levels)


def audit_repository(
    *,
    root: Path,
    base: str,
    changed_paths: Iterable[str],
    active_manifest_data: str | None = None,
    strict_dynamic: bool = True,
    reviewed_tree: str | None = None,
    seed_reader_paths: Iterable[str] | None = None,
) -> dict[str, object]:
    """Return one canonical, fail-closed reader closure document."""

    root = root.resolve()
    if (
        reviewed_tree is not None
        and re.fullmatch(r"[0-9a-f]{40}", reviewed_tree) is None
    ):
        raise ReaderAuditError("reviewed tree is not a full lowercase Git object ID")
    candidates = tuple(sorted(set(changed_paths)))
    paths = _python_paths(root)
    modules = _module_index(root, paths)
    trees: dict[str, ast.Module] = {}
    sources: dict[str, str] = {}
    imports: dict[str, set[str]] = {}
    all_bindings: list[ImportBinding] = []
    literal_map: dict[str, set[str]] = {}
    warnings: list[str] = []
    topology: set[str] = set()
    candidate_edges: set[ReaderEdge] = set()

    for path in paths:
        relative = path.relative_to(root).as_posix()
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=relative)
        sources[relative] = source
        trees[relative] = tree
        imports[relative] = _imports(tree, modules)
        all_bindings.extend(_import_bindings(relative, tree, modules))
        literal_map[relative] = _literal_paths(tree)
        if any(term in source for term in TOPOLOGY_TERMS):
            topology.add(relative)
        if strict_dynamic and relative in candidates and relative.endswith(".py"):
            warnings.extend(_unresolved_dynamic_warnings(relative, tree))
        for target in candidates:
            if target not in literal_map[relative]:
                continue
            reason = "literal_path"
            if SHA256_LITERAL.search(source):
                reason = "literal_path_and_sha256"
            elif "read_bytes" in source or "read_text" in source:
                reason = "raw_source"
            elif "ls-files" in source or "rglob" in source or "glob(" in source:
                reason = "tracked_or_directory_inventory"
            candidate_edges.add(ReaderEdge(relative, target, reason, True))

    if seed_reader_paths is None:
        roots, seed_source = reader_seed(root, base, active_manifest_data)
    else:
        roots = tuple(sorted(set(seed_reader_paths)))
        seed_source = "explicit_seed_reader_paths"
    direct = set(roots)
    sensitive_paths, sensitive_edges = _sensitive_import_closure(
        trees=trees,
        bindings=tuple(sorted(set(all_bindings))),
    )
    support_consumers = sensitive_paths & SEPARATELY_EXECUTED_SUPPORT_PATHS
    closure = direct | (sensitive_paths - support_consumers)
    transitive = closure - direct
    if seed_reader_paths is not None:
        seed_reason = "explicit_seed_reader_paths"
    elif active_manifest_data is not None:
        seed_reason = "active_manifest_seed"
    else:
        seed_reason = "base_manifest_seed"
    edges: set[ReaderEdge] = {
        ReaderEdge(path, seed_source, seed_reason, True) for path in direct
    }
    nonexecuting_inventory_edges: set[ReaderEdge] = set()
    edges |= {
        edge
        for edge in sensitive_edges
        if edge.reader in closure
        and (
            edge.target in closure
            or edge.target
            in {
                "tests/_active_gate2_manifest.py",
                "tests/_phase54_active_gate2_manifest.py",
            }
        )
    }
    for reader in sorted(closure):
        for target in sorted(imports.get(reader, set()) & closure):
            edges.add(ReaderEdge(reader, target, "python_import", False))
        dependency_edges, inventory_edges = _reader_dependency_edges(
            reader, trees[reader], closure
        )
        edges |= dependency_edges
        nonexecuting_inventory_edges |= inventory_edges

    unresolved = tuple(sorted(set(warnings)))
    if unresolved and strict_dynamic:
        raise ReaderAuditError("unresolved dynamic readers: " + ", ".join(unresolved))
    graph: dict[str, set[str]] = {reader: set() for reader in closure}
    for edge in edges:
        if edge.reader in closure and edge.target in closure:
            graph[edge.reader].add(edge.target)
    sccs = _strongly_connected_components(closure, graph)
    refresh_order = _dependency_first_order(closure, graph)
    mixed_graph = {reader: set(targets) for reader, targets in graph.items()}
    for edge in nonexecuting_inventory_edges:
        mixed_graph[edge.reader].add(edge.target)
    mixed_sccs = _strongly_connected_components(closure, mixed_graph)
    manifest_payload = "".join(f"{path}\n" for path in candidates).encode()
    candidate_consumers = sorted({edge.reader for edge in candidate_edges})
    new_mechanical_targets: set[str] = set()
    if active_manifest_data is not None:
        current_assignments = _current_manifest_assignments(root, active_manifest_data)
        current_mechanical = set(
            current_assignments.get("MECHANICAL_READER_PATHS", set())
        )
        new_mechanical_targets = set(
            current_assignments.get("REOPEN1_HASH_LOCK_READER_PATHS", set())
        )
        if (
            not new_mechanical_targets
            or not new_mechanical_targets <= current_mechanical
        ):
            raise ReaderAuditError("reopened hash-lock reader authority is malformed")
        absent_targets = sorted(new_mechanical_targets - set(candidates))
        if absent_targets:
            raise ReaderAuditError(
                "reopened hash-lock readers absent from prospective manifest: "
                + ", ".join(absent_targets)
            )
    executing_candidate_consumers = {
        edge.reader
        for edge in candidate_edges
        if edge.target in new_mechanical_targets
        and edge.reader.startswith("tests/test_")
    }
    missing_executing_readers = sorted(
        executing_candidate_consumers - closure - support_consumers
    )
    if missing_executing_readers:
        raise ReaderAuditError(
            "missing executing readers: " + ", ".join(missing_executing_readers)
        )
    document: dict[str, object] = {
        "schema": SCHEMA,
        "tool_version": TOOL_VERSION,
        "base": base,
        "reviewed_tree": reviewed_tree,
        "manifest": list(candidates),
        "manifest_count": len(candidates),
        "manifest_sha256": hashlib.sha256(manifest_payload).hexdigest(),
        "active_manifest_data": active_manifest_data,
        "seed_source": seed_source,
        "seed_revision": base,
        "direct_readers": sorted(direct),
        "transitive_readers": sorted(transitive),
        "reader_paths": sorted(closure),
        "edges": [asdict(edge) for edge in sorted(edges)],
        "nonexecuting_inventory_edges": [
            asdict(edge) for edge in sorted(nonexecuting_inventory_edges)
        ],
        "candidate_consumers": candidate_consumers,
        "new_mechanical_targets": sorted(new_mechanical_targets),
        "missing_executing_readers": missing_executing_readers,
        "separately_executed_support_consumers": sorted(support_consumers),
        "candidate_consumer_edges": [asdict(edge) for edge in sorted(candidate_edges)],
        "sccs": [list(component) for component in sccs if len(component) > 1],
        "nonexecuting_mixed_sccs": [
            list(component) for component in mixed_sccs if len(component) > 1
        ],
        "refresh_order": [list(level) for level in refresh_order],
        "topology_sensitive": sorted(closure & topology),
        "content_sensitive": sorted(closure - topology),
        "unresolved_dynamic_warnings": list(unresolved),
    }
    payload = _canonical_json(document)
    document["payload_sha256"] = hashlib.sha256(payload).hexdigest()
    return document


def _manifest_paths(path: Path) -> tuple[str, ...]:
    lines = path.read_text(encoding="utf-8").splitlines()
    result = []
    for line in lines:
        value = line.strip()
        if value and not value.startswith("#"):
            result.append(value.split("\t", 1)[0])
    return tuple(sorted(set(result)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--active-manifest-data")
    parser.add_argument("--reviewed-tree")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    document = audit_repository(
        root=arguments.root,
        base=arguments.base,
        changed_paths=_manifest_paths(arguments.manifest),
        active_manifest_data=arguments.active_manifest_data,
        reviewed_tree=arguments.reviewed_tree,
    )
    arguments.output.write_bytes(_canonical_json(document))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
