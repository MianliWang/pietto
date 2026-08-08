"""Deterministic, read-only reader discovery, dependency ordering, and closure.

A *reader* is a tracked file whose assertions consume the content, digest,
inventory, or repository-state projection of another tracked path. Editing a
path therefore forces every transitive reader of that path to be refreshed.

Every function here is read-only. Nothing in this module writes, renames, or
deletes a repository file: a refresh is expressed as a proposed
:class:`ReplacementPlan` that the primary agent reviews and applies. Discovery
that silently rewrote source would make the closure unverifiable.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

READER_KIND_PATH_LITERAL = "path_literal"
READER_KIND_COUNT_LITERAL = "count_literal"
READER_KIND_INVENTORY = "inventory"

READER_KINDS: tuple[str, ...] = (
    READER_KIND_COUNT_LITERAL,
    READER_KIND_INVENTORY,
    READER_KIND_PATH_LITERAL,
)


class ClosureError(Exception):
    """Raised when an input is missing, ambiguous, or outside the repository."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ReaderEdge:
    """One reader consuming one target through one observable mechanism."""

    reader: str
    target: str
    kind: str
    occurrences: int

    def __post_init__(self) -> None:
        if self.kind not in READER_KINDS:
            raise ClosureError(f"unknown reader kind: {self.kind}")
        if self.occurrences < 1:
            raise ClosureError(f"edge occurrences must be positive: {self.occurrences}")


@dataclass(frozen=True, slots=True, kw_only=True)
class ReaderGraph:
    """A reader dependency graph keyed by repository-relative path."""

    nodes: tuple[str, ...]
    adjacency: Mapping[str, tuple[str, ...]]

    def targets_of(self, node: str) -> tuple[str, ...]:
        if node not in self.adjacency:
            raise ClosureError(f"node is not in the graph: {node}")
        return self.adjacency[node]


@dataclass(frozen=True, slots=True, kw_only=True)
class ReplacementRule:
    """One exact literal replacement applied during a mechanical refresh."""

    old: str
    new: str

    def __post_init__(self) -> None:
        if not self.old:
            raise ClosureError("replacement rule requires a non-empty old literal")
        if self.old == self.new:
            raise ClosureError(f"replacement rule is a no-op: {self.old!r}")
        if self.old in self.new:
            # The result would still match the rule, so no application of it can
            # ever reach zero delta and the plan is unachievable by construction.
            raise ClosureError(
                f"replacement rule {self.old!r} survives in its own result {self.new!r}"
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class PathReplacement:
    """The exact number of occurrences one rule would replace in one path."""

    path: str
    old: str
    new: str
    occurrences: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ReplacementPlan:
    """A reviewed, dependency-ordered, dry-run replacement proposal."""

    order: tuple[str, ...]
    replacements: tuple[PathReplacement, ...]
    total_occurrences: int
    applied: bool = False


def _relative(repo_root: Path, path: str) -> Path:
    candidate = repo_root / path
    resolved_root = repo_root.resolve()
    try:
        resolved = candidate.resolve()
    except OSError as error:  # pragma: no cover - defensive
        raise ClosureError(f"cannot resolve {path}: {error}") from error
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ClosureError(f"path escapes the repository root: {path}")
    if not candidate.is_file():
        raise ClosureError(f"path is not a regular file: {path}")
    return candidate


def normalized_path(repo_root: Path, path: str) -> str:
    """Return one path's unique repository-relative identity.

    Two spellings of the same file must not be treated as two paths: they would
    be read twice and their single occurrence reported twice.
    """

    candidate = _relative(repo_root, path)
    return str(candidate.resolve().relative_to(repo_root.resolve()))


def read_source(repo_root: Path, path: str) -> str:
    """Return one repository file as text, failing closed on any problem."""

    return _relative(repo_root, path).read_text(encoding="utf-8")


def discover_edges(
    *,
    repo_root: Path,
    universe: Sequence[str],
    targets: Sequence[str] = (),
    count_literals: Sequence[str] = (),
    inventory_roots: Sequence[str] = (),
) -> tuple[ReaderEdge, ...]:
    """Discover reader edges without modifying anything.

    ``targets`` are the changed paths. ``count_literals`` are repository-wide
    inventory literals (test-module counts, tracked-file counts) whose value the
    change moves. ``inventory_roots`` are directory prefixes whose enumeration
    the change perturbs.
    """

    if not universe:
        raise ClosureError("reader discovery requires a non-empty universe")
    # Two spellings of one reader would produce two edge sets and two graph
    # nodes for a single physical file, breaking collection identity.
    ordered_universe = tuple(
        dict.fromkeys(normalized_path(repo_root, reader) for reader in universe)
    )
    # A target is a repository path, so it is matched by its unique identity as
    # well. An alias would miss the readers that spell it canonically.
    ordered_targets = tuple(
        dict.fromkeys(normalized_path(repo_root, target) for target in targets)
    )
    ordered_literals = tuple(dict.fromkeys(count_literals))
    ordered_roots = tuple(dict.fromkeys(inventory_roots))
    edges: list[ReaderEdge] = []
    for reader in ordered_universe:
        source = read_source(repo_root, reader)
        for target in ordered_targets:
            if target == reader:
                continue
            occurrences = source.count(target)
            if occurrences:
                edges.append(
                    ReaderEdge(
                        reader=reader,
                        target=target,
                        kind=READER_KIND_PATH_LITERAL,
                        occurrences=occurrences,
                    )
                )
        for literal in ordered_literals:
            occurrences = source.count(literal)
            if occurrences:
                edges.append(
                    ReaderEdge(
                        reader=reader,
                        target=literal,
                        kind=READER_KIND_COUNT_LITERAL,
                        occurrences=occurrences,
                    )
                )
        for root in ordered_roots:
            occurrences = source.count(root)
            if occurrences:
                edges.append(
                    ReaderEdge(
                        reader=reader,
                        target=root,
                        kind=READER_KIND_INVENTORY,
                        occurrences=occurrences,
                    )
                )
    return tuple(sorted(edges, key=lambda edge: (edge.reader, edge.kind, edge.target)))


def readers_of(edges: Iterable[ReaderEdge], targets: Sequence[str]) -> tuple[str, ...]:
    """Return the direct readers of the supplied targets, sorted."""

    wanted = set(targets)
    return tuple(sorted({edge.reader for edge in edges if edge.target in wanted}))


def build_graph(adjacency: Mapping[str, Sequence[str]]) -> ReaderGraph:
    """Build a deterministic reader graph from an explicit adjacency mapping."""

    nodes = set(adjacency)
    for targets in adjacency.values():
        nodes.update(targets)
    ordered_nodes = tuple(sorted(nodes))
    resolved: dict[str, tuple[str, ...]] = {}
    for node in ordered_nodes:
        resolved[node] = tuple(sorted(set(adjacency.get(node, ()))))
    return ReaderGraph(nodes=ordered_nodes, adjacency=resolved)


def graph_from_edges(edges: Iterable[ReaderEdge]) -> ReaderGraph:
    """Build a reader graph from discovered edges."""

    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge.reader, []).append(edge.target)
        adjacency.setdefault(edge.target, [])
    return build_graph(adjacency)


def transitive_readers(graph: ReaderGraph, seeds: Sequence[str]) -> tuple[str, ...]:
    """Return every node that transitively reads any seed, excluding the seeds."""

    reverse: dict[str, list[str]] = {node: [] for node in graph.nodes}
    for node in graph.nodes:
        for target in graph.targets_of(node):
            reverse[target].append(node)
    seen: set[str] = set()
    pending = [seed for seed in seeds if seed in reverse]
    missing = [seed for seed in seeds if seed not in reverse]
    if missing:
        raise ClosureError(f"seed is not in the graph: {sorted(missing)[0]}")
    while pending:
        current = pending.pop()
        for reader in reverse[current]:
            if reader in seen:
                continue
            seen.add(reader)
            pending.append(reader)
    return tuple(sorted(seen - set(seeds)))


def strongly_connected_components(graph: ReaderGraph) -> tuple[tuple[str, ...], ...]:
    """Return Tarjan strongly connected components in deterministic order."""

    index_of: dict[str, int] = {}
    low_of: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    components: list[tuple[str, ...]] = []
    counter = 0

    for root in graph.nodes:
        if root in index_of:
            continue
        work: list[tuple[str, int]] = [(root, 0)]
        while work:
            node, child_position = work[-1]
            if child_position == 0:
                index_of[node] = counter
                low_of[node] = counter
                counter += 1
                stack.append(node)
                on_stack.add(node)
            children = graph.targets_of(node)
            if child_position < len(children):
                work[-1] = (node, child_position + 1)
                child = children[child_position]
                if child not in index_of:
                    work.append((child, 0))
                elif child in on_stack:
                    low_of[node] = min(low_of[node], index_of[child])
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low_of[parent] = min(low_of[parent], low_of[node])
            if low_of[node] == index_of[node]:
                component: list[str] = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    component.append(member)
                    if member == node:
                        break
                components.append(tuple(sorted(component)))
    return tuple(sorted(components, key=lambda component: component[0]))


def condensation_order(graph: ReaderGraph) -> tuple[tuple[str, ...], ...]:
    """Return SCCs in dependency-first order: every target before its readers."""

    components = strongly_connected_components(graph)
    component_of: dict[str, int] = {}
    for position, component in enumerate(components):
        for member in component:
            component_of[member] = position
    incoming: dict[int, set[int]] = {
        position: set() for position in range(len(components))
    }
    for node in graph.nodes:
        for target in graph.targets_of(node):
            source_component = component_of[node]
            target_component = component_of[target]
            if source_component != target_component:
                incoming[source_component].add(target_component)
    ready = sorted(position for position, sources in incoming.items() if not sources)
    ordered: list[int] = []
    remaining = {position: set(sources) for position, sources in incoming.items()}
    while ready:
        position = ready.pop(0)
        ordered.append(position)
        promoted: list[int] = []
        for other, sources in remaining.items():
            if position in sources:
                sources.discard(position)
                if not sources and other not in ordered and other not in ready:
                    promoted.append(other)
        for other in sorted(promoted):
            ready.append(other)
        ready.sort(key=lambda candidate: components[candidate][0])
    if len(ordered) != len(components):
        raise ClosureError("condensation order did not cover every component")
    return tuple(components[position] for position in ordered)


def literals_can_interact(first: str, second: str) -> bool:
    """Return True when two literals can ever compete for the same characters.

    Containment is not the only interaction: a proper suffix of one literal that
    is a proper prefix of the other also makes the two counts non-additive,
    because applying either replacement destroys the other match.
    """

    if first in second or second in first:
        return True
    for size in range(1, min(len(first), len(second))):
        if first[-size:] == second[:size] or second[-size:] == first[:size]:
            return True
    return False


def _reject_interacting_rules(rules: Sequence[ReplacementRule]) -> None:
    """Reject rules whose effects overlap, because their counts are not additive."""

    for rule in rules:
        for other in rules:
            if rule is other:
                continue
            if literals_can_interact(rule.old, other.old):
                raise ClosureError(
                    f"replacement rule {rule.old!r} overlaps {other.old!r}"
                )
            if rule.old in other.new:
                raise ClosureError(
                    f"replacement rule {rule.old!r} matches the result of {other.old!r}"
                )


def _reject_regenerating_rules(
    path: str, source: str, rules: Sequence[ReplacementRule]
) -> None:
    """Reject rules whose own result recreates a match across the seam.

    ``ab => a`` applied to ``abb`` leaves ``ab`` behind, so one application can
    never reach zero delta even though every literal check passes in isolation.
    The plan is simulated on the exact source text before it is proposed.
    """

    simulated = source
    for rule in rules:
        # Every rule must match exactly what the original source shows. A match
        # created by an earlier rule would make the reported occurrence count
        # unreachable by applying the plan as written.
        if simulated.count(rule.old) != source.count(rule.old):
            raise ClosureError(
                f"replacement rule {rule.old!r} matches text created by an "
                f"earlier rule in {path}"
            )
        simulated = simulated.replace(rule.old, rule.new)
    for rule in rules:
        if rule.old in simulated:
            raise ClosureError(
                f"replacement rule {rule.old!r} is recreated in {path} after one "
                "application"
            )


def calculate_replacements(
    *,
    repo_root: Path,
    paths: Sequence[str],
    rules: Sequence[ReplacementRule],
    order: Sequence[str] = (),
) -> ReplacementPlan:
    """Return the exact dry-run replacement proposal. Nothing is written."""

    if not rules:
        raise ClosureError("a replacement plan requires at least one rule")
    if not paths:
        raise ClosureError("a replacement plan requires at least one path")
    seen_old: set[str] = set()
    for rule in rules:
        if rule.old in seen_old:
            raise ClosureError(f"duplicate replacement rule for {rule.old!r}")
        seen_old.add(rule.old)
    _reject_interacting_rules(rules)
    identities = tuple(normalized_path(repo_root, path) for path in paths)
    ordered_paths = tuple(sorted(dict.fromkeys(identities)))
    if order:
        ordered_order = tuple(normalized_path(repo_root, path) for path in order)
        if len(set(ordered_order)) != len(ordered_order):
            raise ClosureError("explicit order must not repeat a path")
        if set(ordered_order) != set(identities):
            raise ClosureError("explicit order must cover exactly the supplied paths")
        ordered_paths = ordered_order
    elif len(set(identities)) != len(identities):
        raise ClosureError("supplied paths name the same file more than once")
    replacements: list[PathReplacement] = []
    for path in ordered_paths:
        source = read_source(repo_root, path)
        _reject_regenerating_rules(path, source, rules)
        for rule in rules:
            occurrences = source.count(rule.old)
            if occurrences:
                replacements.append(
                    PathReplacement(
                        path=path,
                        old=rule.old,
                        new=rule.new,
                        occurrences=occurrences,
                    )
                )
    return ReplacementPlan(
        order=ordered_paths,
        replacements=tuple(replacements),
        total_occurrences=sum(item.occurrences for item in replacements),
        applied=False,
    )


def verify_zero_delta(
    *,
    repo_root: Path,
    paths: Sequence[str],
    rules: Sequence[ReplacementRule],
) -> tuple[str, ...]:
    """Independently confirm no rule still matches. Empty means closed.

    An empty path set or an empty rule set is refused: a check that inspected
    nothing must never be reported as a successful closure.
    """

    if not paths:
        raise ClosureError("zero-delta verification requires at least one path")
    if not rules:
        raise ClosureError("zero-delta verification requires at least one rule")
    remaining: list[str] = []
    identities = tuple(normalized_path(repo_root, path) for path in paths)
    for path in sorted(dict.fromkeys(identities)):
        source = read_source(repo_root, path)
        for rule in rules:
            occurrences = source.count(rule.old)
            if occurrences:
                remaining.append(f"{path}:{rule.old}:{occurrences}")
    return tuple(remaining)


def verify_zero_addition(
    *, discovered: Sequence[str], frozen: Sequence[str]
) -> tuple[str, ...]:
    """Return readers discovered but not frozen. Empty means zero addition."""

    return tuple(sorted(set(discovered) - set(frozen)))


def plan_as_json(plan: ReplacementPlan) -> str:
    """Render a replacement plan as deterministic JSON for review."""

    return json.dumps(
        {
            "applied": plan.applied,
            "order": list(plan.order),
            "replacements": [
                {
                    "path": item.path,
                    "old": item.old,
                    "new": item.new,
                    "occurrences": item.occurrences,
                }
                for item in plan.replacements
            ],
            "total_occurrences": plan.total_occurrences,
        },
        indent=1,
        sort_keys=True,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only Pietto reader discovery and closure planning.",
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument(
        "--mode",
        required=True,
        choices=("discover", "plan", "verify"),
        help="discover reader edges, propose a dry-run plan, or verify closure",
    )
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--target", action="append", default=[])
    parser.add_argument("--count-literal", action="append", default=[])
    parser.add_argument(
        "--inventory-root",
        action="append",
        default=[],
        help="directory prefix whose enumeration the change perturbs",
    )
    parser.add_argument("--rule", action="append", default=[])
    return parser


def _parse_rules(raw_rules: Sequence[str]) -> tuple[ReplacementRule, ...]:
    rules: list[ReplacementRule] = []
    for raw in raw_rules:
        old, separator, new = raw.partition("=>")
        if not separator:
            raise ClosureError(f"rule must be 'old=>new': {raw}")
        rules.append(ReplacementRule(old=old, new=new))
    return tuple(rules)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the read-only command line interface."""

    parser = _build_parser()
    arguments = parser.parse_args(argv)
    repo_root = Path(arguments.repo_root)
    try:
        if arguments.mode == "discover":
            # Refuse before discovering: a run that inspected no target at all
            # must never print an empty closure and exit successfully.
            if not (
                arguments.target or arguments.count_literal or arguments.inventory_root
            ):
                raise ClosureError(
                    "discovery requires at least one target, count literal, "
                    "or inventory root"
                )
            edges = discover_edges(
                repo_root=repo_root,
                universe=arguments.path,
                targets=arguments.target,
                count_literals=arguments.count_literal,
                inventory_roots=arguments.inventory_root,
            )
            print(
                json.dumps(
                    {
                        "edges": [
                            {
                                "reader": edge.reader,
                                "target": edge.target,
                                "kind": edge.kind,
                                "occurrences": edge.occurrences,
                            }
                            for edge in edges
                        ],
                        "readers": list(
                            readers_of(
                                edges,
                                (
                                    *arguments.target,
                                    *arguments.count_literal,
                                    *arguments.inventory_root,
                                ),
                            )
                        ),
                    },
                    indent=1,
                    sort_keys=True,
                )
            )
            return 0
        rules = _parse_rules(arguments.rule)
        if arguments.mode == "plan":
            plan = calculate_replacements(
                repo_root=repo_root, paths=arguments.path, rules=rules
            )
            print(plan_as_json(plan))
            return 0
        remaining = verify_zero_delta(
            repo_root=repo_root, paths=arguments.path, rules=rules
        )
        print(json.dumps({"remaining": list(remaining)}, indent=1, sort_keys=True))
        return 0 if not remaining else 1
    except ClosureError as error:
        print(f"[reader-closure] error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover - manual invocation
    sys.exit(main())
