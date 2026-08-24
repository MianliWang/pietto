"""Private common model for Project Explain Artifact v1."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import unicodedata

from pietto.errors import Severity

__all__: tuple[str, ...] = ()

PROJECT_EXPLAIN_ARTIFACT_NAME = "Project Explain Artifact v1"


class ProjectExplainFormat(StrEnum):
    PROJECT_EXPLAIN_V1 = "pietto.project-explain.v1"


class ProjectExplainEvidencePosture(StrEnum):
    SOURCE_FACT = "source_fact"
    DETERMINISTIC_DERIVATION = "deterministic_derivation"
    UNAVAILABLE = "unavailable"
    CONFLICTING = "conflicting"


class ProjectExplainRequirementStage(StrEnum):
    REQUEST = "request"
    RESOLUTION = "resolution"
    RESULT = "result"


class ProjectExplainLogicalPathKind(StrEnum):
    PROJECT_RELATIVE = "project_relative"
    PACKAGE_RELATIVE = "package_relative"
    UPSTREAM_SOURCE_LOCATOR = "upstream_source_locator"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainLogicalPath:
    kind: ProjectExplainLogicalPathKind
    value: str

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectExplainLogicalPathKind:
            raise TypeError("Project Explain logical paths require an exact kind.")
        if type(self.value) is not str:
            raise TypeError("Project Explain logical paths require exact text.")
        if self.kind in {
            ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
            ProjectExplainLogicalPathKind.PACKAGE_RELATIVE,
        }:
            if not _is_relative_logical_path(self.value):
                raise ValueError(
                    "Project-relative and package-relative paths must be exact "
                    "normalized logical paths."
                )
            return
        if not _is_upstream_source_locator(self.value):
            raise ValueError(
                "Upstream source locators must be exact relocation-stable values."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainLocation:
    path: ProjectExplainLogicalPath | None
    line: int | None
    column: int | None
    end_line: int | None
    end_column: int | None

    def __post_init__(self) -> None:
        if self.path is not None and type(self.path) is not ProjectExplainLogicalPath:
            raise TypeError("Project Explain locations require an exact logical path.")
        start = _coordinate_pair(self.line, self.column, "start")
        end = _coordinate_pair(self.end_line, self.end_column, "end")
        if end is not None and start is None:
            raise ValueError("Project Explain end coordinates require a start.")
        if start is not None and end is not None and end < start:
            raise ValueError(
                "Project Explain end coordinates cannot precede the start."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainDiagnostic:
    code: str
    severity: Severity
    message: str
    location: ProjectExplainLocation | None
    suggestion: str | None

    def __post_init__(self) -> None:
        _require_non_empty_text(self.code, "diagnostic code")
        if type(self.severity) is not Severity:
            raise TypeError("Project Explain diagnostics require an exact severity.")
        _require_non_empty_text(self.message, "diagnostic message")
        if (
            self.location is not None
            and type(self.location) is not ProjectExplainLocation
        ):
            raise TypeError("Project Explain diagnostics require a detached location.")
        if self.suggestion is not None:
            _require_non_empty_text(self.suggestion, "diagnostic suggestion")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainEnvelope[PayloadT]:
    format: ProjectExplainFormat
    ok: bool
    diagnostics: tuple[ProjectExplainDiagnostic, ...]
    payload: PayloadT | None

    def __post_init__(self) -> None:
        if (
            type(self.format) is not ProjectExplainFormat
            or self.format is not ProjectExplainFormat.PROJECT_EXPLAIN_V1
        ):
            raise TypeError("Project Explain envelopes require the v1 format marker.")
        if type(self.ok) is not bool:
            raise TypeError("Project Explain envelope ok must be an exact bool.")
        if type(self.diagnostics) is not tuple or any(
            type(diagnostic) is not ProjectExplainDiagnostic
            for diagnostic in self.diagnostics
        ):
            raise TypeError(
                "Project Explain envelopes require an exact diagnostic tuple."
            )
        has_error = any(
            diagnostic.severity is Severity.ERROR for diagnostic in self.diagnostics
        )
        if self.ok:
            if self.payload is None:
                raise ValueError("Successful Project Explain envelopes need a payload.")
            if has_error:
                raise ValueError(
                    "Successful Project Explain envelopes forbid error diagnostics."
                )
            return
        if self.payload is not None:
            raise ValueError("Failed Project Explain envelopes forbid a payload.")
        if not has_error:
            raise ValueError(
                "Failed Project Explain envelopes require an error diagnostic."
            )


def _require_non_empty_text(value: object, label: str) -> None:
    if type(value) is not str:
        raise TypeError(f"Project Explain {label} must be exact text.")
    if not value:
        raise ValueError(f"Project Explain {label} must be non-empty.")


def _has_control_character(value: str) -> bool:
    return any(unicodedata.category(character) == "Cc" for character in value)


def _has_windows_drive_prefix(value: str) -> bool:
    return (
        len(value) >= 2
        and ("A" <= value[0] <= "Z" or "a" <= value[0] <= "z")
        and value[1] == ":"
    )


def _is_relative_logical_path(value: str) -> bool:
    if not value or _has_control_character(value) or "\\" in value:
        return False
    if value == ".":
        return True
    if value.startswith("/") or value.endswith("/"):
        return False
    if _has_windows_drive_prefix(value):
        return False
    return all(part not in {"", ".", ".."} for part in value.split("/"))


def _is_file_uri(value: str) -> bool:
    return (
        len(value) >= 5
        and value[0] in {"f", "F"}
        and value[1] in {"i", "I"}
        and value[2] in {"l", "L"}
        and value[3] in {"e", "E"}
        and value[4] == ":"
    )


def _is_upstream_source_locator(value: str) -> bool:
    if not value or _has_control_character(value):
        return False
    if value.startswith(("/", "\\", "~")) or _has_windows_drive_prefix(value):
        return False
    return not _is_file_uri(value)


def _coordinate_pair(
    line: object,
    column: object,
    label: str,
) -> tuple[int, int] | None:
    if (line is None) != (column is None):
        raise ValueError(f"Project Explain {label} coordinates must be paired.")
    if line is None:
        return None
    if type(line) is not int or type(column) is not int:
        raise TypeError(f"Project Explain {label} coordinates must be exact integers.")
    if line <= 0 or column <= 0:
        raise ValueError(f"Project Explain {label} coordinates must be positive.")
    return line, column
