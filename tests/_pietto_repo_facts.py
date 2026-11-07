"""Process-local observations for explicitly immutable test corpora.

First reads are lazy, not an atomic repository snapshot. Owners select paths;
changed/copied corpora require a fresh index. No threaded access is provided.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PythonSourceFacts:
    path: Path
    text: str
    string_literals: frozenset[str]
    imported_modules: frozenset[str]
    identifiers: frozenset[str]
    top_level_assigned_names: frozenset[str]


@dataclass(frozen=True, slots=True)
class RepositoryFactIndex:
    root: Path
    _python_by_path: dict[Path, PythonSourceFacts] = field(
        default_factory=dict,
        repr=False,
        compare=False,
    )

    _text_by_path: dict[Path, str] = field(
        default_factory=dict, repr=False, compare=False
    )
    _lower_by_text: dict[str, str] = field(
        default_factory=dict, repr=False, compare=False
    )

    @classmethod
    def snapshot(cls, root: Path) -> RepositoryFactIndex:
        return cls(root=root.resolve())

    def text(self, path: Path) -> str:
        """Read an owner-selected lexical entry, preserving read_text symlinks.

        Unlike python(), this does not require valid Python or collapse logical
        paths to resolved aliases. Namespace discovery remains with the owner.
        """
        absolute = path.absolute()
        if ".." in absolute.parts or not absolute.is_relative_to(self.root):
            raise ValueError(f"Text path is outside repository root: {path}")
        try:
            return self._text_by_path[absolute]
        except KeyError:
            text = path.read_text(encoding="utf-8")
            return self._text_by_path.setdefault(absolute, text)

    def lowercase(self, text: str) -> str:
        """Derive from the supplied text, including each caller's injected text."""
        try:
            return self._lower_by_text[text]
        except KeyError:
            lowered = text.lower()
            return self._lower_by_text.setdefault(text, lowered)

    def python(self, path: Path) -> PythonSourceFacts:
        resolved = path.resolve()
        if not resolved.is_relative_to(self.root):
            raise ValueError(f"Python path is outside repository root: {path}")
        if resolved.suffix != ".py":
            raise ValueError(f"Path is not a Python source: {path}")
        try:
            return self._python_by_path[resolved]
        except KeyError:
            text = self._text_by_path.get(resolved)
            if text is None:
                text = resolved.read_text(encoding="utf-8")
            fact = _python_source_facts(resolved, text)
            # A failed parse publishes no new capture, preserving python-only
            # acquisition's retry behavior after failure.
            self._text_by_path.setdefault(resolved, text)
            return self._python_by_path.setdefault(resolved, fact)


def _python_source_facts(path: Path, text: str) -> PythonSourceFacts:
    tree = ast.parse(text, filename=str(path))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    identifiers = (
        {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        | {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        | {
            node.name.rsplit(".", 1)[-1]
            for node in ast.walk(tree)
            if isinstance(node, ast.alias)
        }
    )
    assigned_names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = (node.target,)
        else:
            continue
        assigned_names.update(
            target.id for target in targets if isinstance(target, ast.Name)
        )
    return PythonSourceFacts(
        path=path,
        text=text,
        string_literals=frozenset(
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ),
        imported_modules=frozenset(imported_modules),
        identifiers=frozenset(identifiers),
        top_level_assigned_names=frozenset(assigned_names),
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_FACTS = RepositoryFactIndex.snapshot(REPO_ROOT)
