"""Catalog-only Timestamp/UUID source qualification laws."""

import pytest

import _pietto_results_product as product
from pietto._project.project_execution_source import (
    SourceAdmissionError,
    requires_temporal_uuid_catalog,
    verify_temporal_uuid_catalog,
)


def source(tmp_path, target):
    _checked, _meaning, artifact, _contract = product.temporal_premise(
        tmp_path / "temporal", target
    )
    return artifact.request.sources[0]


@pytest.mark.parametrize(
    ("family", "rows"),
    (
        (
            "postgres",
            (
                ("stamp", 1114, 6),
                ("optional_stamp", 1114, 6),
                ("identifier", 2950, -1),
                ("optional_identifier", 2950, -1),
            ),
        ),
        (
            "mysql",
            (
                ("stamp", "datetime(6)"),
                ("optional_stamp", "datetime(6)"),
                ("identifier", "binary(16)"),
                ("optional_identifier", "binary(16)"),
            ),
        ),
    ),
)
def test_temporal_uuid_catalog_requires_exact_physical_declarations(
    tmp_path, family, rows
):
    item = source(tmp_path, family)
    assert requires_temporal_uuid_catalog(item)
    verify_temporal_uuid_catalog(item, rows, family=family)


@pytest.mark.parametrize(
    ("family", "rows"),
    (
        (
            "postgres",
            (
                ("stamp", 1184, 6),
                ("optional_stamp", 1114, 6),
                ("identifier", 25, -1),
                ("optional_identifier", 2950, -1),
            ),
        ),
        (
            "mysql",
            (
                ("stamp", "datetime(3)"),
                ("optional_stamp", "timestamp"),
                ("identifier", "varbinary(16)"),
                ("optional_identifier", "binary(15)"),
            ),
        ),
    ),
)
def test_temporal_uuid_catalog_refuses_nearby_types(tmp_path, family, rows):
    with pytest.raises(SourceAdmissionError, match="SOURCE_TEMPORAL_UUID_CATALOG"):
        verify_temporal_uuid_catalog(source(tmp_path, family), rows, family=family)


@pytest.mark.parametrize("family", ("postgres", "mysql"))
def test_temporal_uuid_catalog_refuses_a_missing_catalog_observation(tmp_path, family):
    with pytest.raises(SourceAdmissionError, match="SOURCE_TEMPORAL_UUID_CATALOG"):
        verify_temporal_uuid_catalog(source(tmp_path, family), (), family=family)


def test_non_temporal_source_needs_no_temporal_catalog(tmp_path):
    _checked, artifact = product.build_source(tmp_path / "ordinary", "postgres")
    assert not requires_temporal_uuid_catalog(artifact.request.sources[0])
