# openspec-image-publishing

## ADDED Requirements

### Requirement: The OpenSpec CLI image is published as a multi-architecture manifest and verified before any run reuses it

The `openspec-image` job MUST publish `linux/amd64` AND `linux/arm64` for the
hash tag it pushes, and `make openspec-manifest-check` MUST refuse (exit 1) a
published tag whose manifest lacks either architecture — a manifest the check
cannot read is a loud exit 2, never a silent pass. The verification runs on BOTH
refresh paths: after a publish, and on the "already current — skip rebuild"
branch, so a legacy amd64-only tag for a revision is refused instead of reused
forever. The publisher's platform list and the verify step MUST be pinned by
tests so the seam's pull path can never drift from the architectures the
publisher produces.

#### Scenario: a single-arch published manifest goes red

- **Given** a stubbed `docker manifest inspect` reporting only `linux/amd64` for the tag
- **When** `scripts/openspec_manifest_check.py --tag <tag>` runs
- **Then** it exits 1 naming the missing `linux/arm64`
- **Test:** tests/test_openspec_manifest_check.py::test_an_amd64_only_manifest_is_refused

#### Scenario: a multi-arch manifest passes and names both platforms

- **Given** a stubbed manifest listing `linux/amd64` and `linux/arm64`
- **When** the check runs
- **Then** it exits 0 reporting both architectures
- **Test:** tests/test_openspec_manifest_check.py::test_a_multi_arch_manifest_passes

#### Scenario: a manifest the check cannot read is never a clean

- **Given** a stubbed `docker` that fails or prints non-JSON
- **When** the check runs
- **Then** it exits 2 with a loud unreadable-manifest report
- **Test:** tests/test_openspec_manifest_check.py::test_an_unreadable_manifest_exits_two

#### Scenario: the tag is required, never guessed

- **Given** the check invoked with no tag argument
- **When** it runs
- **Then** it exits 2 demanding the exact tag
- **Test:** tests/test_openspec_manifest_check.py::test_a_missing_tag_is_loud

#### Scenario: the publisher declares both platforms in the workflow

- **Given** the real `refresh-bot.yml`
- **When** the `openspec-image` job is inspected
- **Then** its build-push step carries `platforms: [linux/amd64, linux/arm64]`
- **Test:** tests/test_openspec_manifest_check.py::test_the_publisher_declares_both_platforms

#### Scenario: both refresh paths verify the manifest

- **Given** the real `refresh-bot.yml`
- **When** the `openspec-image` job steps are inspected
- **Then** `make openspec-manifest-check` runs after the publish step AND on the skip-rebuild branch
- **Test:** tests/test_openspec_manifest_check.py::test_both_refresh_paths_verify_the_manifest

#### Scenario: the target is wired through the Makefile only

- **Given** the real Makefile and the real workflow
- **When** the wiring is asserted
- **Then** `openspec-manifest-check` is a `.PHONY` target reaching the script via the Makefile, and the workflow calls only the target
- **Test:** tests/test_openspec_manifest_check.py::test_the_target_is_makefile_only_and_wired
