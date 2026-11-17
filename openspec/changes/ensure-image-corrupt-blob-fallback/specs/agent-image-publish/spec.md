# agent-image-publish

## ADDED Requirements

### Requirement: A published tag whose blobs are unfetchable falls back to a local build

When `docker manifest inspect` serves a content-hash tag but `docker pull` fails
with the registry's missing-blob wording (`could not fetch content descriptor …`,
`blob unknown`, `content blob`), the seam MUST build this revision's Dockerfile
instead — the same inputs the tag was hashed from — and its verdict line MUST name
the corrupt state truthfully. A pull failure that is NOT missing-blob wording MUST
still fail loudly with no build (the #235 rule).

#### Scenario: the base tag is published but its blobs 404

- **Given** the registry serves the manifest for this revision's base tag and
  `docker pull` fails with `could not fetch content descriptor sha256:… from
  remote: not found`
- **When** `ensure-base` runs
- **Then** the pull is attempted first, the seam exits 0, builds
  `trending-local-llms:latest` from this revision's `Dockerfile`, and its verdict
  says the tag "is published but its blobs are not fetchable"
- **Test:** tests/test_ensure_image.py::test_a_published_tag_with_unfetchable_blobs_falls_back_to_a_local_build

#### Scenario: an unrelated pull failure never rebuilds

- **Given** the base tag is published and `docker pull` fails with
  `no space left on device`
- **When** `ensure-base` runs
- **Then** it exits non-zero and performs no build (a wrong-state rebuild is the
  #235 defect)
- **Test:** tests/test_ensure_image.py::test_a_published_tag_with_unfetchable_blobs_falls_back_to_a_local_build

#### Scenario: the test image falls back on an ensured base

- **Given** the published test tag's blobs 404 on pull and no local base exists
- **When** `ensure-test` runs
- **Then** it exits 0, ensures the base, and builds the test image from
  `Dockerfile.test` on it
- **Test:** tests/test_ensure_image.py::test_a_published_tag_with_unfetchable_blobs_falls_back_to_a_local_build

#### Scenario: the healthy states are unchanged

- **Given** a published, fetchable tag — or an absent tag — or a registry that
  cannot answer
- **When** `ensure-base` / `ensure-test` / `ensure-openspec` run
- **Then** pull-tag, build-locally and loud-failure behave exactly as before
  (byte-identical verdict strings for those states)
- **Test:** tests/test_ensure_image.py::test_ensure_base_builds_only_when_the_tag_is_not_published
- **Test:** tests/test_ensure_image.py::test_ensure_test_pulls_or_builds_on_that_base
- **Test:** tests/test_ensure_image.py::test_a_registry_hiccup_is_a_loud_failure_not_a_rebuild
