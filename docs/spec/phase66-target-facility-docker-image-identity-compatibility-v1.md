# Phase66 Target Facility Docker Image Identity Compatibility v1

## Scope

This is a test-infrastructure corrective delivery inserted between the published
Phase66 Slice8 and Slice9. It restores local PostgreSQL/MySQL target-conformance
execution across the Docker image-store implementations that are now in use,
without changing the checked-in target pins, the reviewed PostgreSQL/MySQL
distributions, the daemon configuration, the CI workflow, or any Pietto
compiler/product semantics. Phase66 stays `ACTIVE`, Slices1-8 stay
`COMPLETED / PUBLISHED`, and Slice9 stays `NEXT / NOT IMPLEMENTED`. It is not a
numbered Slice and it does not change N66=16.

## Observed defect

`tests/_pietto_target_conformance_resources.py` previously required the Docker
image object identity to equal the pinned config digest:

```text
docker image inspect REPOSITORY@PLATFORM_DIGEST --format '{{json .Id}}'  ==  config_digest
container inspect CONTAINER --format '{{json .Image}}'                   ==  config_digest
```

That representation belongs to the historical Docker image store. On a daemon
whose image store is containerd-backed, `.Id` is the digest of the image
object's own root descriptor, which for an exact `repository@platform_digest`
acquisition is the platform manifest digest. Both pinned targets were observed
this way on Docker Engine 29.6.1 with `Driver: overlayfs` and
`DriverStatus: [["driver-type","io.containerd.snapshotter.v1"]]`:

| Target | `.Id` and `.Descriptor.digest` | Pinned `platform_digest` | Pinned `config_digest` |
| --- | --- | --- | --- |
| postgres | `sha256:a10c981235b4f635e65df0cfb66a5598064628128505dbc6a3ed4ca303717521` | equal | `sha256:f372eda99ac2ea249c3dce566dcdf468397035371284d2cf2103b4bc52b3b39e`, not equal |
| mysql | `sha256:7dcc4add9183664de3a214daf85a50c3ba6cccfd7534f700b6561bf5b41885be` | equal | `sha256:c9570e7b94230d3717b88a334acaea49a4fe6b162f68a8f2927eaaf866b7f867`, not equal |

The pins, the acquired images, the server builds and the target semantics are
unaffected; the same checked-in pins pass both target jobs in natural CI. The
defect is that the harness conflated two distinct immutable identities with one
storage-backend-specific image object ID representation.

## Retained distinct identities

`platform_digest` identifies the selected immutable OCI platform manifest and is
the only reference used to acquire an image. `config_digest` is a distinct
pinned config identity retained by the reviewed distribution relationship. They
are not interchangeable, neither is renamed, and neither is removed from the pin
schema. The historical image store exposes the config identity directly through
its image ID contract; a descriptor-aware image store exposes the platform
manifest identity directly through the image target descriptor. The facility
verifies the strongest stable identity that the applicable Docker inspection
contract actually exposes, and never invents a representation-independent
meaning for `.Id`.

## Image observation contract

Acquisition is unchanged: exactly `repository@platform_digest`, `--platform
linux/amd64`, no tag, no `latest`, no fallback tag, no alternate registry, no
discovered digest and no locally substituted image. One inspection template
serves both contracts, because `{{json (index . "Descriptor")}}` yields `null`
where the key is absent while `{{json .Descriptor}}` fails the template:

```text
{"id":{{json .Id}},"os":{{json .Os}},"architecture":{{json .Architecture}},"descriptor":{{json (index . "Descriptor")}}}
```

Every accepted observation must be structurally exact — those four keys and no
others — with a well-formed `sha256:` image ID and `linux`/`amd64`. Then exactly
one route applies:

- Descriptor-aware: a `Descriptor` object carrying a well-formed digest. That
  digest must equal `platform_digest`. Where Docker also supplies descriptor
  platform fields they must agree with linux/amd64. `.Id` is retained as the
  daemon's runtime image object ID and is never reread as a config digest.
- Historical: no descriptor. `.Id` must equal `config_digest`.

There is no value-based fallback, no "either digest is acceptable" acceptance and
no try-one-then-the-other behavior. A correct `.Id` never rescues a wrong
descriptor, and a correct descriptor never excuses the historical route. A
descriptor that is present but malformed, or missing its digest, is an
unrecognized shape and fails closed rather than being classified as historical,
so an unrecognized future Docker response is a failure and not a silent
downgrade. No extra registry client is introduced, no config JSON is
reconstructed, no human text is parsed, and Docker's private on-disk store is
not read. Where the daemon exposes no stable authoritative config-descriptor
digest, none is fabricated.

## Container ownership contract

Acquisition retains the validated runtime image object ID, and the owned
container must report exactly that ID as its runtime `.Image`. Ownership is
therefore `pinned immutable reference -> independently validated daemon image
object -> exact runtime image ID -> exact owned container .Image`. A container
is never accepted by name and invocation label alone, and before any image has
been validated no container can be owned. The exact owned name, invocation nonce
label, exclusive bridge network, single loopback publication, resource limits,
tmpfs data boundary, target-specific setup and final absence after cleanup are
all unchanged. The container's configured image reference and its container-side
manifest descriptor are not made new authorities, because their stability on the
historical contract is not established here.

## Evidence and receipt posture

`pietto.target-conformance-receipt.v2` is unchanged; an image-store
representation is not a receipt format change. The resource journal now records
the structured observation — the exact immutable reference, the selected
contract, the runtime image object ID, the descriptor digest where one exists,
and the observed platform — and records the started container's own image. The
data-only receipt verifier requires exactly one such observation, re-derives its
claim against the pin through that contract's own exposed digest, and requires
the started container to be bound to that same runtime image ID. Renaming the
reported contract does not transfer the other route's evidence. The pinned
`config_digest` echoes already carried by the MySQL CA identity and the
environment observation are unchanged, and actual server/package/version
observation after startup remains independently mandatory.

## Assurance

Deterministic offline controls in
`tests/test_phase66_target_facility_docker_image_identity_compatibility.py`
cover both positive routes and prove path selection and fail-closed precedence
rather than membership in a set of two strings: wrong descriptor digest, a
correct config ID combined with a wrong descriptor, a missing descriptor digest,
a malformed descriptor, descriptor platform disagreement, wrong OS, wrong
architecture, a historical ID mismatch, a non-digest ID, missing and
unrecognized observation fields, one target's identity offered for the other
target, a foreign runtime image at container ownership, and a correctly named
and labelled container carrying the wrong image. The historical Slice2 facility
controls — pin schema, environment isolation, ownership and cleanup, wrong
target, missing resource, receipt corruption, target results and metadata,
native transport, TLS, privilege, recovery and the strict aggregate — are all
retained, and two receipt corruption cases are added for a renamed contract and
for an unbound container image.
