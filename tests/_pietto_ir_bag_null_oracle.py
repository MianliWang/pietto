"""Pure bounded finite-BAG and SQL-NULL equality reference oracle."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__: tuple[str, ...] = ()

_MAX_INPUT_ROW_WIDTH = 8
_MAX_OUTPUT_ROW_WIDTH = 2 * _MAX_INPUT_ROW_WIDTH
_MAX_INPUT_DISTINCT_ROWS = 8
_MAX_INPUT_MULTIPLICITY = 16
_MAX_CORRESPONDENCES = 8


class ProjectBagNullTruth(StrEnum):
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"


class ProjectBagNullJoinKind(StrEnum):
    INNER = "inner"
    LEFT = "left"


class ProjectBagNullScalarKind(StrEnum):
    NULL = "null"
    BOOL = "bool"
    INT = "int"
    TEXT = "text"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectBagNullScalar:
    kind: ProjectBagNullScalarKind
    value: bool | int | str | None

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectBagNullScalarKind:
            raise TypeError("Oracle scalar requires an exact kind.")
        valid = {
            ProjectBagNullScalarKind.NULL: self.value is None,
            ProjectBagNullScalarKind.BOOL: type(self.value) is bool,
            ProjectBagNullScalarKind.INT: type(self.value) is int,
            ProjectBagNullScalarKind.TEXT: type(self.value) is str,
        }[self.kind]
        if not valid:
            raise ValueError("Oracle scalar kind and exact value type disagree.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectBagNullRow:
    values: tuple[ProjectBagNullScalar, ...]

    def __post_init__(self) -> None:
        if type(self.values) is not tuple or any(
            type(value) is not ProjectBagNullScalar for value in self.values
        ):
            raise TypeError("Oracle row requires an exact scalar tuple.")
        if len(self.values) > _MAX_OUTPUT_ROW_WIDTH:
            raise ValueError("Oracle row exceeds the bounded output width.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectBagNullEntry:
    row: ProjectBagNullRow
    multiplicity: int

    def __post_init__(self) -> None:
        if type(self.row) is not ProjectBagNullRow:
            raise TypeError("Oracle bag entry requires one exact row.")
        if type(self.multiplicity) is not int or self.multiplicity <= 0:
            raise ValueError("Oracle bag multiplicity must be a positive integer.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectFiniteBag:
    entries: tuple[ProjectBagNullEntry, ...]

    def __post_init__(self) -> None:
        if type(self.entries) is not tuple or any(
            type(entry) is not ProjectBagNullEntry for entry in self.entries
        ):
            raise TypeError("Oracle bag requires an exact entry tuple.")
        rows = tuple(entry.row for entry in self.entries)
        if len(set(rows)) != len(rows):
            raise ValueError("Oracle bag entries must retain distinct row values.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectBagNullEqualityCorrespondence:
    left_position: int
    right_position: int

    def __post_init__(self) -> None:
        if (
            type(self.left_position) is not int
            or self.left_position < 0
            or type(self.right_position) is not int
            or self.right_position < 0
        ):
            raise ValueError("Oracle equality positions must be non-negative.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectBagNullJoinSpecification:
    kind: ProjectBagNullJoinKind
    left_width: int
    right_width: int
    correspondences: tuple[ProjectBagNullEqualityCorrespondence, ...]

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectBagNullJoinKind:
            raise TypeError("Oracle JOIN specification requires an exact kind.")
        if (
            type(self.left_width) is not int
            or not 1 <= self.left_width <= _MAX_INPUT_ROW_WIDTH
            or type(self.right_width) is not int
            or not 1 <= self.right_width <= _MAX_INPUT_ROW_WIDTH
        ):
            raise ValueError("Oracle JOIN widths exceed the bounded input scope.")
        if (
            type(self.correspondences) is not tuple
            or not 1 <= len(self.correspondences) <= _MAX_CORRESPONDENCES
            or any(
                type(item) is not ProjectBagNullEqualityCorrespondence
                for item in self.correspondences
            )
        ):
            raise ValueError("Oracle JOIN requires bounded equality correspondences.")
        if any(
            item.left_position >= self.left_width
            or item.right_position >= self.right_width
            for item in self.correspondences
        ):
            raise ValueError("Oracle equality position is outside its input row.")


def project_bag_null() -> ProjectBagNullScalar:
    return ProjectBagNullScalar(kind=ProjectBagNullScalarKind.NULL, value=None)


def project_bag_bool(value: bool) -> ProjectBagNullScalar:
    return ProjectBagNullScalar(kind=ProjectBagNullScalarKind.BOOL, value=value)


def project_bag_int(value: int) -> ProjectBagNullScalar:
    return ProjectBagNullScalar(kind=ProjectBagNullScalarKind.INT, value=value)


def project_bag_text(value: str) -> ProjectBagNullScalar:
    return ProjectBagNullScalar(kind=ProjectBagNullScalarKind.TEXT, value=value)


def evaluate_project_bag_null_equality(
    left: ProjectBagNullScalar,
    right: ProjectBagNullScalar,
) -> ProjectBagNullTruth:
    """Evaluate exact compatible SQL equality without coercion."""

    if (
        type(left) is not ProjectBagNullScalar
        or type(right) is not ProjectBagNullScalar
    ):
        raise TypeError("Oracle equality requires two exact scalars.")
    if (
        left.kind is ProjectBagNullScalarKind.NULL
        or right.kind is ProjectBagNullScalarKind.NULL
    ):
        return ProjectBagNullTruth.UNKNOWN
    if left.kind is not right.kind or left.value != right.value:
        return ProjectBagNullTruth.FALSE
    return ProjectBagNullTruth.TRUE


def evaluate_project_bag_null_predicate(
    specification: ProjectBagNullJoinSpecification,
    left: ProjectBagNullRow,
    right: ProjectBagNullRow,
) -> ProjectBagNullTruth:
    """Evaluate one ordered equality conjunction with SQL three-valued logic."""

    if type(specification) is not ProjectBagNullJoinSpecification:
        raise TypeError("Oracle predicate requires one exact JOIN specification.")
    if (
        type(left) is not ProjectBagNullRow
        or len(left.values) != specification.left_width
        or type(right) is not ProjectBagNullRow
        or len(right.values) != specification.right_width
    ):
        raise ValueError("Oracle predicate rows must match exact input widths.")
    saw_unknown = False
    for correspondence in specification.correspondences:
        truth = evaluate_project_bag_null_equality(
            left.values[correspondence.left_position],
            right.values[correspondence.right_position],
        )
        if truth is ProjectBagNullTruth.FALSE:
            return ProjectBagNullTruth.FALSE
        if truth is ProjectBagNullTruth.UNKNOWN:
            saw_unknown = True
    return ProjectBagNullTruth.UNKNOWN if saw_unknown else ProjectBagNullTruth.TRUE


def _validate_input_bag(
    bag: ProjectFiniteBag,
    *,
    width: int,
) -> None:
    if type(bag) is not ProjectFiniteBag:
        raise TypeError("Oracle evaluation requires exact finite bags.")
    if len(bag.entries) > _MAX_INPUT_DISTINCT_ROWS or any(
        len(entry.row.values) != width or entry.multiplicity > _MAX_INPUT_MULTIPLICITY
        for entry in bag.entries
    ):
        raise ValueError("Oracle input bag exceeds the bounded reference scope.")


def evaluate_project_bag_null_join(
    specification: ProjectBagNullJoinSpecification,
    left: ProjectFiniteBag,
    right: ProjectFiniteBag,
) -> ProjectFiniteBag:
    """Evaluate bounded ordinary INNER/LEFT equi-JOIN BAG semantics."""

    if type(specification) is not ProjectBagNullJoinSpecification:
        raise TypeError("Oracle evaluation requires one exact specification.")
    _validate_input_bag(left, width=specification.left_width)
    _validate_input_bag(right, width=specification.right_width)
    multiplicities: dict[ProjectBagNullRow, int] = {}

    def add(row: ProjectBagNullRow, multiplicity: int) -> None:
        multiplicities[row] = multiplicities.get(row, 0) + multiplicity

    null_right = (project_bag_null(),) * specification.right_width
    for left_entry in left.entries:
        matched = False
        for right_entry in right.entries:
            if (
                evaluate_project_bag_null_predicate(
                    specification,
                    left_entry.row,
                    right_entry.row,
                )
                is not ProjectBagNullTruth.TRUE
            ):
                continue
            matched = True
            add(
                ProjectBagNullRow(
                    values=(*left_entry.row.values, *right_entry.row.values)
                ),
                left_entry.multiplicity * right_entry.multiplicity,
            )
        if specification.kind is ProjectBagNullJoinKind.LEFT and not matched:
            add(
                ProjectBagNullRow(values=(*left_entry.row.values, *null_right)),
                left_entry.multiplicity,
            )
    return ProjectFiniteBag(
        entries=tuple(
            ProjectBagNullEntry(row=row, multiplicity=multiplicity)
            for row, multiplicity in multiplicities.items()
        )
    )
