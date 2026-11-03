# pin-actions-immutable-sha

## ADDED Requirements

### Requirement: a mutable third-party workflow `uses:` ref refuses the tree

The `action-pin-check` guard scans `.github/workflows/**` for third-party
`uses: <owner>/<repo>@<ref>` and refuses any ref that is not a 40-hex commit SHA
and not on the explicit own-repo allow-ref list. Own reusable workflows
(`./.github/workflows/…`) and `docker://` refs are exempt. Fails closed: a
mutable third-party ref not allowlisted is a violation.

WHEN the guard scans a workflow tree
THEN every third-party `uses:` ref must be a 40-hex SHA or on the allow-ref list,
AND a mutable third-party ref not on the list is a violation (fails closed),
AND an own reusable workflow (`./.github/workflows/…`) is exempt,
AND an allowlisted current ref passes while a NEW mutable ref is refused.

#### Scenario: a NEW mutable action tag is refused

- **Given** a workflow tree containing `uses: actions/setup-python@v5` (not on the allowlist)
- **When** the guard runs
- **Then** it exits non-zero and names the mutable ref
- **Test:** `tests/test_action_pin.py::test_workflow_uses_mutable_ref_reds` — real guard on a fixture tree, RED

#### Scenario: a 40-hex SHA action ref passes

- **Given** a workflow tree containing `uses: actions/setup-python@<40-hex-sha>`
- **When** the guard runs
- **Then** it exits 0
- **Test:** `tests/test_action_pin.py::test_workflow_uses_pinned_sha_green` — real guard on a fixture tree, GREEN

#### Scenario: an own reusable workflow is exempt

- **Given** a workflow tree containing `uses: ./.github/workflows/reuse.yml`
- **When** the guard runs
- **Then** it exits 0
- **Test:** `tests/test_action_pin.py::test_own_reusable_workflow_exempt` — real guard on a fixture tree, GREEN

### Requirement: a mutable third-party tool-image tag refuses the tree

The same guard scans the tool-image seam — Makefile `*_IMAGE :=` refs,
`scripts/*.py` image constants and Dockerfile `ARG`-level tool refs — for
third-party container image tags and refuses a mutable tag there. A pinned ref
is a digest (`@sha256:…`) or the fleet-owned `<sha12>` tag form. Fleet-owned
images (`trending-local-llms*`, `ghcr.io/andyholst/trending-local-llms*`) are
exempt. Fails closed: a mutable third-party tag not allowlisted is a violation.

WHEN the guard scans the tool-image seam
THEN every third-party image tag must be pinned (digest or fleet `<sha12>` tag) or allowlisted,
AND a mutable third-party tag not pinned/allowlisted is a violation,
AND a pinned digest or fleet `<sha12>` tag passes,
AND a fleet-owned image is exempt.

#### Scenario: a NEW mutable third-party image tag is refused

- **Given** a Makefile containing `TRIVY_IMAGE := ghcr.io/aquasecurity/trivy:v0.50.1` (not allowlisted)
- **When** the guard runs
- **Then** it exits non-zero and names the mutable tag
- **Test:** `tests/test_action_pin.py::test_mutable_image_reds` — real guard on a fixture tree, RED

#### Scenario: a pinned digest image tag passes

- **Given** a Makefile containing `TRIVY_IMAGE := ghcr.io/aquasecurity/trivy@sha256:<64-hex>`
- **When** the guard runs
- **Then** it exits 0
- **Test:** `tests/test_action_pin.py::test_image_pinned_digest_green` — real guard on a fixture tree, GREEN

#### Scenario: a fleet `<sha12>` tag passes

- **Given** a Makefile containing `TRIVY_IMAGE := ghcr.io/andyholst/trending-local-llms:dockerfile-abcdef123456`
- **When** the guard runs
- **Then** it exits 0
- **Test:** `tests/test_action_pin.py::test_image_fleet_sha12_green` — real guard on a fixture tree, GREEN

#### Scenario: a fleet-owned image is exempt

- **Given** a Makefile containing `TEST_IMAGE := trending-local-llms-test:latest`
- **When** the guard runs
- **Then** it exits 0
- **Test:** `tests/test_action_pin.py::test_fleet_owned_image_exempt` — real guard on a fixture tree, GREEN

### Requirement: the guard is wired into the CI gate and green on this repo

The `action-pin-check` guard runs in `qa-validate`'s `validate` job after the
runner images are prepared, so a mutable third-party ref refuses the PR. The
guard passes on THIS repository as it stands (the current mutable refs are on
the documented allowlist with allow-till deadlines, so master-as-is is green
while a NEW mutable ref is refused).

WHEN the PR pipeline runs
THEN the `validate` job runs `make action-pin-check` after `image-ensure`,
AND the guard passes on this repository (master-as-is is green),
AND the current mutable refs are on the allowlist with allow-till deadlines.

#### Scenario: the guard runs in the validate job after the image is prepared

- **Given** the `qa-validate` workflow's `validate` job
- **When** its steps are read in order
- **Then** it runs `make action-pin-check` after `make image-ensure`
- **Test:** `tests/test_workflows.py::test_action_pin_guard_wired_into_qa_validate` — reads the workflow + Makefile + runs the real guard on this repo

#### Scenario: the guard is green on this repository

- **Given** this repository's tree
- **When** the guard runs
- **Then** it exits 0 (current mutable refs are allowlisted)
- **Test:** `tests/test_action_pin.py::test_guard_green_on_this_repo` — real guard on the real tree, GREEN
