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

### Requirement: all third-party workflow refs migrate to immutable SHAs (#737, #714 Slice 2)

The 37 third-party workflow `uses:` refs in `.github/workflows/**` are pinned to
the current immutable 40-hex commit SHA of the pinned action revision for the
SAME major version as the tag they replace (checkout@v4 → its v4 line SHA,
setup-buildx@v3 → its v3 SHA, etc.). After the migration `ALLOWED_WORKFLOW_REFS`
is empty — the #714 allow-till deadline is satisfied with no dangling hold — so
a NEW mutable third-party ref is refused. The gitleaks tool-image ref stays on
`ALLOWED_IMAGE_REFS` (allow-till #715).

WHEN the workflows are scanned after the migration
THEN every third-party `uses:` ref is a full 40-hex SHA,
AND `ALLOWED_WORKFLOW_REFS` is empty (0 workflow entries allowlisted),
AND `make action-pin-check` is GREEN on this repository (no dangling hold),
AND the gitleaks image ref remains allowlisted for #715.

#### Scenario: no tag-based third-party ref remains in the pinned workflows

- **Given** the repository's `.github/workflows/**` after the migration
- **When** each third-party `uses:` ref is read
- **Then** every ref is a full 40-hex SHA; no tag-based third-party ref remains
- **Test:** `tests/test_action_pin.py::test_no_tag_based_third_party_refs_in_pinned_workflows` — scans the real tree, no tag refs

#### Scenario: the workflow allowlist is empty after the migration

- **Given** `scripts/action_pin_check.py` after the migration
- **When** `ALLOWED_WORKFLOW_REFS` is read
- **Then** it is empty (the #714 allow-till deadline is satisfied), while the gitleaks image ref stays on `ALLOWED_IMAGE_REFS` (allow-till #715)
- **Test:** `tests/test_action_pin.py::test_workflow_allowlist_empty_after_migration` — asserts allowlist empty + gitleaks entry present

### Requirement: operator how-to for bumping a pinned action is documented (#739, #714 Slice 3)

The README carries a "Bumping a pinned GitHub Action" section and the primary
gate workflow carries a header comment so the guard is both enforcement AND a
documented workflow. Docs only — no logic/allowlist/workflow-SHA change.

WHEN an operator needs to bump a pinned GitHub Action
THEN the README section explains the guard fails closed on any non-40-hex
third-party `uses:` ref,
AND explains how to resolve + VERIFY the new SHA for the desired major version
(`gh api repos/<owner>/<repo>/git/ref/tags/v<tag>`, annotated-tag dereference,
or the upstream release page) and replace it in the matching
`.github/workflows/*.yml`,
AND states that `ALLOWED_WORKFLOW_REFS` must stay empty (all refs pinned),
AND warns not to bump MAJOR versions casually (stay on the same major's SHA,
review release notes),
AND `qa-validate.yml` carries a concise header comment pointing at that section,
AND the guard stays GREEN and no `uses:` value changed.

#### Scenario: the README documents bumping a pinned action

- **Given** the repo README (regenerated from the template, issue #195 `--render-only` path)
- **When** the "How to contribute" section is read
- **Then** it contains a "Bumping a pinned GitHub Action" subsection covering the fail-closed guard, SHA resolution+verification, the empty `ALLOWED_WORKFLOW_REFS` rule, and the same-major bump warning
- **Test:** `tests/test_readme_render.py::test_readme_contains_pinned_action_howto` — renders the README from the store and asserts the four points

#### Scenario: the primary gate workflow points operators at the README

- **Given** `.github/workflows/qa-validate.yml`
- **When** its header comment is read
- **Then** it notes the refs are pinned to immutable SHAs and points to the README "Bumping a pinned GitHub Action" section
- **Test:** `tests/test_workflows.py::test_qa_validate_header_points_at_pinned_action_howto` — real qa-validate.yml, header carries the README pointer

#### Scenario: the documentation change leaves the guard green and the diff docs-only

- **Given** the tree after the #739 doc change
- **When** the guard runs and the diff is inspected
- **Then** `make action-pin-check` exits 0, no `uses:` value changed, and `scripts/action_pin_check.py` is untouched
- **Test:** `tests/test_action_pin.py::test_guard_green_on_this_repo` — guard still GREEN on the doc-only tree
