"""Explicit compiled bytes and independent trusted handoff; no query-source I/O."""

import hashlib
import os
from pathlib import Path

from pietto._project.model import CompiledProjectInput
from pietto._project.project_compiled_schema import (
    CompiledError,
    VERSIONS,
    content_pin,
    decode,
)

__all__: tuple[str, ...] = ()


def owner_versions(distribution, module) -> frozenset:
    """Versions of the installed distributions named `distribution` whose
    recorded files include the file `module` was imported from.

    Metadata lookup and import each search sys.path on their own, so a
    shadowing entry (PYTHONPATH, or the working directory under `python -c`)
    could pair one distribution's version with another's code. Exactly one
    version means one owner; none or several leave the code's origin open.
    """
    from importlib.metadata import distributions

    target = module if type(module) is str else getattr(module, "__file__", None)
    if type(target) is not str or not os.path.isfile(target):
        return frozenset()
    name = os.path.basename(target)
    owners = set()
    for candidate in distributions(name=distribution):
        for recorded in candidate.files or ():
            if recorded.name != name:
                continue
            path = str(candidate.locate_file(recorded))
            if os.path.isfile(path) and os.path.samefile(path, target):
                owners.add(candidate.version)
    return frozenset(owners)


def semantic_build_identity() -> str:
    """Identify installed compiler code, independent of checkout/commit/docs.

    This is a code-input identity, not a signature or a claim that an arbitrary
    caller's producer is trusted. The caller supplies that separate handoff.
    The ANTLR label is the version of the one distribution that owns the
    imported runtime, never whatever metadata sys.path happens to find first.
    """
    import antlr4

    owners = owner_versions("antlr4-python3-runtime", antlr4)
    if len(owners) != 1:
        raise CompiledError("COMPILED_CODE_ORIGIN")
    (antlr_release,) = owners
    package = Path(__file__).resolve().parents[1]
    dependency = Path(antlr4.__file__).resolve().parent
    digest = hashlib.sha256(b"pietto.compiled-semantic-code.v1\0")
    for name, root, release in (
        ("pietto", package, "resolved-code"),
        ("antlr4-python3-runtime", dependency, antlr_release),
    ):
        label = (name + "\0" + release).encode("utf-8")
        digest.update(len(label).to_bytes(8, "big"))
        digest.update(label)
        for path in sorted(root.rglob("*.py")):
            if path.is_symlink():
                raise CompiledError("COMPILED_CODE_ORIGIN")
            relative = path.relative_to(root).as_posix().encode("utf-8")
            data = path.read_bytes()
            digest.update(len(relative).to_bytes(8, "big"))
            digest.update(relative)
            digest.update(len(data).to_bytes(8, "big"))
            digest.update(data)
    return digest.hexdigest()


def supported_compatibility() -> tuple:
    return (*VERSIONS, semantic_build_identity())


def load_compiled(
    raw: bytes,
    *,
    expected_pin: str,
    accepted_producer: str,
    accepted_compatibility: tuple,
) -> CompiledProjectInput:
    """Load only these bytes. There is no auto-pin, path search or old-state input."""
    if (
        type(expected_pin) is not str
        or len(expected_pin) != 64
        or any(c not in "0123456789abcdef" for c in expected_pin)
        or type(accepted_producer) is not str
        or not accepted_producer
        or type(accepted_compatibility) is not tuple
    ):
        raise CompiledError("COMPILED_HANDOFF")
    if content_pin(raw) != expected_pin:
        raise CompiledError("COMPILED_CONTENT_PIN")
    description = decode(raw)
    if (
        description.compatibility != accepted_compatibility
        or accepted_compatibility != supported_compatibility()
        or description.producer != accepted_producer
    ):
        raise CompiledError("COMPILED_COMPATIBILITY")
    return CompiledProjectInput(
        description,
        expected_pin,
        accepted_producer,
        accepted_compatibility,
    )
