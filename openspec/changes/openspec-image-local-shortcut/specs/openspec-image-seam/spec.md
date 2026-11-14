# openspec-image-seam

## ADDED Requirements

### Requirement: the OpenSpec CLI image seam reuses this revision's exact tag when it is already local

`scripts/ensure_image.py::ensure_openspec` SHALL first check whether the exact hash tag
`openspec_tag()` is already available on this machine (`docker image inspect`). When it is, the
seam SHALL tag it onto `OPENSPEC_IMAGE` and return, making **no registry call at all** — no
`docker pull`, no `docker manifest inspect`. A tag whose name is the hash of this revision's
`openspec/Dockerfile` + `openspec/` content identifies a matching image by construction (the same
reasoning `python_env_ready()` applies to the python-env image, issue #766). The seam SHALL NOT
re-pull a tag it already has: the published tag is amd64-only, and pulling it on an arm64 host is
the `CalledProcessError` issue #767 measured.

When the tag is **not** local, the existing rules are unchanged: `published()` consults the registry
loudly (a registry failure is an error naming the exact command, never "absent" — issue #235), a
published tag is pulled and tagged, and an unpublished tag is built from `openspec/Dockerfile`.
A freshly built image SHALL be tagged with **both** `OPENSPEC_IMAGE` and the exact hash tag, so the
next run on that machine reaches the local shortcut without a registry probe.

#### Scenario: a locally present exact tag is reused with zero registry calls

- **GIVEN** a machine whose local images include the exact tag `openspec_tag()` (the published tag AND the local image exist — the arm64 host state issue #767 measured),
- **WHEN** `scripts/ensure_image.py ensure-openspec` runs,
- **THEN** it SHALL exit `0`, SHALL tag the exact tag onto `OPENSPEC_IMAGE`, and SHALL make no `docker pull` and no `docker manifest inspect` call at all.

- **Test:** `tests/test_ensure_image.py::test_ensure_openspec_present_locally_is_reused_without_a_pull`

#### Scenario: reuse does not depend on what the registry says

- **GIVEN** the exact tag is present locally while the registry reports it not published (an offline or not-yet-published state beside a matching local image),
- **WHEN** `scripts/ensure_image.py ensure-openspec` runs,
- **THEN** it SHALL exit `0`, tag the image, and SHALL NOT contact the registry or rebuild.

- **Test:** `tests/test_ensure_image.py::test_ensure_openspec_present_locally_is_reused_without_a_pull`

#### Scenario: a published tag that is NOT local is still pulled exactly as before (CI unchanged)

- **GIVEN** a fresh machine (a CI runner) with no local copy of the tag, while `docker manifest inspect` publishes it,
- **WHEN** `scripts/ensure_image.py ensure-openspec` runs,
- **THEN** it SHALL `docker pull` the exact tag and tag it onto `OPENSPEC_IMAGE` — the byte-identical commands CI takes today.

- **Test:** `tests/test_ensure_image.py::test_openspec_image_is_hash_tagged_and_pulled_or_built`

#### Scenario: a local build registers the exact tag so the next run is a reuse

- **GIVEN** a machine with no local copy and a registry that reports the tag not published,
- **WHEN** `scripts/ensure_image.py ensure-openspec` runs,
- **THEN** it SHALL build `openspec/Dockerfile` and tag the result with BOTH `OPENSPEC_IMAGE` and the exact hash tag.

- **Test:** `tests/test_ensure_image.py::test_openspec_image_is_hash_tagged_and_pulled_or_built`
