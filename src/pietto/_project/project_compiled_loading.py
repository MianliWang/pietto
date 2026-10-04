"""Explicit compiled bytes and independent trusted handoff; no query-source I/O."""

import hashlib
from pathlib import Path

from pietto._project.model import CompiledProjectInput
from pietto._project.project_compiled_schema import (
    CompiledError,
    VERSIONS,
    content_pin,
    decode,
)

__all__: tuple[str, ...] = ()


def semantic_build_identity() -> str:
    """Identify installed compiler code, independent of checkout/commit/docs.

    This is a code-input identity, not a signature or a claim that an arbitrary
    caller's producer is trusted. The caller supplies that separate handoff.
    """
    import antlr4
    from importlib.metadata import version

    package = Path(__file__).resolve().parents[1]
    dependency = Path(antlr4.__file__).resolve().parent
    digest = hashlib.sha256(b"pietto.compiled-semantic-code.v1\0")
    for name, root, release in (
        ("pietto", package, "resolved-code"),
        ("antlr4-python3-runtime", dependency, version("antlr4-python3-runtime")),
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
