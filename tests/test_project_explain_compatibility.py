from __future__ import annotations

from dataclasses import fields

from pietto._metadata.model import (
    SEMANTIC_METADATA_ARTIFACT_NAME,
    SEMANTIC_METADATA_COMMAND,
    SEMANTIC_METADATA_SCHEMA_VERSION,
    SemanticMetadataArtifact,
    SemanticMetadataPayload,
    SemanticMetadataSourceIdentity,
)
from pietto._metadata.serializer import (
    build_semantic_metadata_error_envelope,
    semantic_metadata_artifact_to_json_dict,
)
from pietto._metadata.text import render_semantic_metadata_text
from _pietto_project_explain_contract import (
    REPO_ROOT,
    _read,
    _argument_names,
)


def test_existing_single_file_explain_identity_and_envelopes_are_zero_delta() -> None:
    assert (
        SEMANTIC_METADATA_ARTIFACT_NAME,
        SEMANTIC_METADATA_SCHEMA_VERSION,
        SEMANTIC_METADATA_COMMAND,
    ) == ("Semantic Metadata Artifact v1", 1, "explain")
    assert tuple(field.name for field in fields(SemanticMetadataArtifact)) == (
        "artifact",
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "metadata",
    )

    payload = SemanticMetadataPayload(
        source=SemanticMetadataSourceIdentity(path="model.pietto"),
        definitions=(),
        sources=(),
        relations=(),
        types=(),
    )
    artifact = SemanticMetadataArtifact(
        artifact=SEMANTIC_METADATA_ARTIFACT_NAME,
        schema_version=SEMANTIC_METADATA_SCHEMA_VERSION,
        command=SEMANTIC_METADATA_COMMAND,
        ok=True,
        path="model.pietto",
        diagnostics=(),
        metadata=payload,
    )
    success = semantic_metadata_artifact_to_json_dict(artifact)
    assert tuple(success) == (
        "artifact",
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "metadata",
    )
    assert render_semantic_metadata_text(artifact).splitlines()[:4] == [
        "Semantic Metadata Artifact v1",
        "schema_version: 1",
        "command: explain",
        "path: model.pietto",
    ]

    failure = build_semantic_metadata_error_envelope(
        path="bad.pietto",
        stage="parse",
        message="Semantic Metadata Artifact v1 metadata is unavailable.",
    )
    assert tuple(failure) == (
        "artifact",
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "error",
    )
    assert failure["ok"] is False
    assert "metadata" not in failure

    cli_source = _read(REPO_ROOT / "src/pietto/cli.py")
    assert _argument_names(cli_source, "_configure_explain_parser") == (
        "path",
        "--project",
        "--format",
        "--check-mode",
    )
    assert "return _run_explain_command(namespace)" in cli_source
