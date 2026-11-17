# agent-image-publish

## ADDED Requirements

### Requirement: The base and test images are published as multi-architecture manifests and verified before any run reuses them

The `build` and `test-image` jobs of `refresh-bot.yml` MUST publish
`linux/amd64` AND `linux/arm64` for the content-hash tags they push, and
`make image-manifest-check TAG=<exact tag> LABEL=<name>` MUST refuse (exit 1)
a published tag whose manifest answers fewer than both architectures — a
manifest the check cannot read is a loud exit 2, never a silent pass. The
verification runs on BOTH refresh paths: after a publish, and on the
"already current — skip rebuild" branch, so a legacy amd64-only tag for a
revision is refused instead of reused forever. After the manifest check
passes, each job MUST run the published tag under `--platform linux/arm64`
(a `hermes --version` smoke for the base, a test-library import smoke for
the test image), so the arm64 variant is proven to install AND run. The
manifest verdict MUST have exactly ONE implementation
(`scripts/image_manifest_check.py`), which `scripts/openspec_manifest_check.py`
delegates to rather than duplicating. The publishers' platform lists, the
both-paths verify steps and the run-proof steps MUST be pinned by tests so
the seam's pull path can never drift from the architectures the publisher
produces.

#### Scenario: an amd64-only base manifest goes red

- **Given** a stubbed `docker manifest inspect` reporting only `linux/amd64` for the base tag
- **When** `scripts/image_manifest_check.py --tag <tag> --label base` runs
- **Then** it exits 1 naming the missing `linux/arm64` and the `platforms` fix
- **Test:** tests/test_image_manifest_check.py::test_an_amd64_only_manifest_is_refused

#### Scenario: a multi-arch manifest passes and names both platforms

- **Given** a stubbed manifest listing `linux/amd64` and `linux/arm64`
- **When** the check runs
- **Then** it exits 0 reporting both architectures
- **Test:** tests/test_image_manifest_check.py::test_a_multi_arch_manifest_passes

#### Scenario: an unreadable manifest is a loud exit 2

- **Given** a stubbed `docker manifest inspect` that fails ("manifest unknown")
- **When** the check runs
- **Then** it exits 2 and says the verdict is undecidable
- **Test:** tests/test_image_manifest_check.py::test_an_unreadable_manifest_exits_two

#### Scenario: both refresh paths verify the base and test manifests through the Makefile

- **Given** the real `refresh-bot.yml`
- **When** the `build` and `test-image` job blocks are inspected
- **Then** each build-push step declares `platforms: linux/amd64,linux/arm64`, each job runs `make image-manifest-check TAG=` UNGATED after both its publish and skip steps, and no step reaches the script past the Makefile
- **Test:** tests/test_image_manifest_check.py::test_both_paths_verify_base_and_test_manifests

#### Scenario: the arm64 variant is proven to run, not just published

- **Given** the real `refresh-bot.yml`
- **When** the `build` and `test-image` job blocks are inspected
- **Then** each runs the published tag under `--platform linux/arm64` (`hermes --version` for the base, a test-library import for the test image) after the manifest check
- **Test:** tests/test_image_manifest_check.py::test_the_arm64_run_proof_steps_exist

#### Scenario: the manifest verdict has one implementation

- **Given** the two check scripts
- **When** `scripts/openspec_manifest_check.py` is inspected
- **Then** it delegates to `scripts/image_manifest_check.py` and carries no second copy of the manifest-reading or verdict logic
- **Test:** tests/test_image_manifest_check.py::test_the_verdict_is_one_implementation
