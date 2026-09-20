"""Offline controls for the backend-neutral Docker image identity contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import _pietto_target_conformance as facility
import _pietto_target_conformance_resources as resources

PINS, _ = facility.load_pins(facility.PINS)
TARGETS = tuple(PINS["targets"])
# A descriptor-aware store reports a runtime object ID unrelated to the config
# digest; this stands in for it without pretending to be either pinned digest.
RUNTIME = "sha256:" + "3" * 64
FOREIGN = "sha256:" + "4" * 64


def pin(target: str) -> dict[str, Any]:
    return PINS["targets"][target]


def descriptor_observation(target: str, **changes: Any) -> dict[str, Any]:
    observed = {
        "id": RUNTIME,
        "os": "linux",
        "architecture": "amd64",
        "descriptor": {
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "digest": pin(target)["platform_digest"],
            "size": 3452,
        },
    }
    return observed | changes


def classic_observation(target: str, **changes: Any) -> dict[str, Any]:
    return {
        "id": pin(target)["config_digest"],
        "os": "linux",
        "architecture": "amd64",
        "descriptor": None,
    } | changes


def acquired(target: str, directory: Path, runtime: str) -> resources.Resources:
    directory.mkdir(parents=True, exist_ok=True)
    resource = resources.Resources(target, pin(target), directory)
    resource.runtime_image_id = runtime
    return resource


def container(resource: resources.Resources, image: str) -> dict[str, Any]:
    return {
        "id": "a" * 64,
        "name": "/" + resource.name,
        "image": image,
        "labels": {"pietto.phase66.invocation": resource.nonce},
    }


@pytest.mark.parametrize("target", TARGETS)
def test_descriptor_aware_store_authenticates_the_pinned_platform_manifest(
    target: str, tmp_path: Path
) -> None:
    identity = resources.image_identity(descriptor_observation(target), pin(target))
    assert identity == {
        "contract": "descriptor",
        "runtime_image_id": RUNTIME,
        "descriptor_digest": pin(target)["platform_digest"],
        "os": "linux",
        "architecture": "amd64",
    }
    # The runtime object ID is retained as itself, never reread as a config digest.
    assert RUNTIME not in {pin(target)["config_digest"], pin(target)["platform_digest"]}
    resource = acquired(target, tmp_path, RUNTIME)
    assert resource.owned("container", container(resource, RUNTIME))
    for other in (
        FOREIGN,
        pin(target)["config_digest"],
        pin(target)["platform_digest"],
    ):
        assert not resource.owned("container", container(resource, other))


@pytest.mark.parametrize("target", TARGETS)
def test_historical_store_authenticates_the_pinned_config_identity(
    target: str, tmp_path: Path
) -> None:
    identity = resources.image_identity(classic_observation(target), pin(target))
    assert identity == {
        "contract": "classic",
        "runtime_image_id": pin(target)["config_digest"],
        "descriptor_digest": None,
        "os": "linux",
        "architecture": "amd64",
    }
    resource = acquired(target, tmp_path, pin(target)["config_digest"])
    assert resource.owned(
        "container", container(resource, pin(target)["config_digest"])
    )
    assert not resource.owned(
        "container", container(resource, pin(target)["platform_digest"])
    )


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "shape",
    [
        "wrong_descriptor_digest",
        "config_id_with_wrong_descriptor",
        "missing_descriptor_digest",
        "malformed_descriptor",
        "descriptor_platform_disagreement",
        "wrong_os",
        "wrong_architecture",
        "classic_config_mismatch",
        "missing_field",
        "unrecognized_field",
        "non_digest_id",
    ],
)
def test_every_ambiguous_image_observation_fails_closed(
    target: str, shape: str
) -> None:
    other = pin(target)["repository"]
    assert other
    if shape == "wrong_descriptor_digest":
        observed = descriptor_observation(
            target, descriptor={"digest": "sha256:" + "5" * 64}
        )
    elif shape == "config_id_with_wrong_descriptor":
        # A correct historical identity never rescues a wrong platform manifest.
        observed = descriptor_observation(
            target,
            id=pin(target)["config_digest"],
            descriptor={"digest": "sha256:" + "5" * 64},
        )
    elif shape == "missing_descriptor_digest":
        observed = descriptor_observation(target, descriptor={"size": 3452})
    elif shape == "malformed_descriptor":
        observed = descriptor_observation(target, descriptor="sha256:" + "5" * 64)
    elif shape == "descriptor_platform_disagreement":
        observed = descriptor_observation(
            target,
            descriptor={
                "digest": pin(target)["platform_digest"],
                "platform": {"os": "linux", "architecture": "arm64"},
            },
        )
    elif shape == "wrong_os":
        observed = descriptor_observation(target, os="windows")
    elif shape == "wrong_architecture":
        observed = descriptor_observation(target, architecture="arm64")
    elif shape == "classic_config_mismatch":
        observed = classic_observation(target, id=FOREIGN)
    elif shape == "non_digest_id":
        observed = descriptor_observation(target, id="postgres:18.6-bookworm")
    else:
        observed = descriptor_observation(target)
        if shape == "missing_field":
            del observed["architecture"]
        else:
            observed["snapshotter"] = "overlayfs"
    with pytest.raises(ValueError):
        resources.image_identity(observed, pin(target))


def test_one_target_identity_is_never_accepted_for_the_other_target() -> None:
    for observed, other in (
        (descriptor_observation("postgres"), "mysql"),
        (descriptor_observation("mysql"), "postgres"),
        (classic_observation("postgres"), "mysql"),
        (classic_observation("mysql"), "postgres"),
    ):
        with pytest.raises(ValueError):
            resources.image_identity(observed, pin(other))


@pytest.mark.parametrize("target", TARGETS)
def test_ownership_needs_a_validated_image_and_not_only_the_owned_label(
    target: str, tmp_path: Path
) -> None:
    unvalidated = acquired(target, tmp_path / "first", "")
    unvalidated.runtime_image_id = None
    assert unvalidated.runtime_image_id is None
    # Name and invocation nonce are correct; no image has been validated yet.
    assert not unvalidated.owned("container", container(unvalidated, RUNTIME))
    resource = acquired(target, tmp_path / "second", RUNTIME)
    assert not resource.owned(
        "container", container(resource, RUNTIME) | {"labels": {}}
    )
    assert not resource.owned(
        "container", container(resource, RUNTIME) | {"name": "/other"}
    )
    # A network carries no image identity and is unaffected by the contract.
    assert resource.owned(
        "network",
        {
            "name": resource.network_name,
            "labels": {"pietto.phase66.invocation": resource.nonce},
        },
    )


def test_one_inspection_template_serves_both_image_stores() -> None:
    # A store without the key must yield null rather than a template failure.
    assert '(index . "Descriptor")' in resources.IMAGE_FIELDS
    assert ".Descriptor" not in resources.IMAGE_FIELDS.replace(
        '(index . "Descriptor")', ""
    )
    assert resources.IMAGE_FIELDS.count("{{json") == 4


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("contract", ["descriptor", "classic"])
def test_receipt_image_identity_authenticates_each_contract_separately(
    target: str, contract: str
) -> None:
    observed = (
        descriptor_observation(target)
        if contract == "descriptor"
        else classic_observation(target)
    )
    reference = pin(target)["repository"] + "@" + pin(target)["platform_digest"]
    event = {
        "event": "image_verified",
        "reference": reference,
    } | resources.image_identity(observed, pin(target))
    assert (
        facility.verify_image_identity(event, pin(target)) == event["runtime_image_id"]
    )
    # Renaming the contract does not transfer the other route's evidence.
    renamed = (
        {"contract": "classic", "descriptor_digest": None}
        if contract == "descriptor"
        else {"contract": "descriptor", "descriptor_digest": None}
    )
    rejected = (
        renamed,
        {"contract": "descriptor", "descriptor_digest": pin(target)["config_digest"]},
        {"contract": "containerd"},
        {"reference": pin(target)["repository"] + ":" + pin(target)["tag"]},
        {"reference": pin(target)["repository"] + "@" + pin(target)["config_digest"]},
        {"os": "windows"},
        {"architecture": "arm64"},
        {"runtime_image_id": "latest"},
    )
    for change in rejected:
        with pytest.raises(ValueError, match="unauthenticated image identity"):
            facility.verify_image_identity(event | change, pin(target))
    for extra in ({"snapshotter": "overlayfs"}, {}):
        broken = event | extra
        if not extra:
            broken = {k: v for k, v in event.items() if k != "descriptor_digest"}
        with pytest.raises(ValueError, match="unauthenticated image identity"):
            facility.verify_image_identity(broken, pin(target))


def test_pins_keep_platform_and_config_as_distinct_reviewed_identities() -> None:
    for target in TARGETS:
        assert pin(target)["platform_digest"] != pin(target)["config_digest"]
        assert {"platform_digest", "config_digest"} <= set(pin(target))
