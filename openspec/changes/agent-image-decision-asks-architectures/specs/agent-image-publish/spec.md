# agent-image-publish

## ADDED Requirements

### Requirement: The rebuild decision asks which architectures a published tag answers

`scripts/ensure_image.py`'s reuse decision MUST NOT treat "the registry answers
`manifest inspect`" as "the tag is reusable". It MUST ask the architecture question
through the ONE manifest verdict in the repo — `scripts/image_manifest_check.py`
(`check` and `REQUIRED_PLATFORMS`) — and carry no second copy of the platform list or
the manifest-reading logic (rule 6d). A published tag whose manifest answers fewer
platforms than required MUST be reported as a rebuild reason (`base-tag-single-arch`,
`test-tag-single-arch`, `openspec-tag-single-arch` for the three images), and
`make rebuild-decision` MUST expose the verdict as data (`base_arch`, `test_arch`,
`openspec_arch`) naming the missing platforms, so the reason a publisher rebuilds is
readable without running the pipeline. A manifest the verdict CANNOT read (no document,
a registry that failed to answer) MUST raise `RegistryUnknown` and fail the decision
loudly — never a silent clean and never a rebuild triggered by a hiccup (issue #235).
Rebuilding because a tag is single-architecture MUST publish over the same content-hash
tag with the publisher's existing dual-arch step, so no privileged dispatch is needed
to repair a legacy tag.

#### Scenario: a published tag that answers only linux/amd64 is not reusable

- **Given** the base, `latest` and test tags published, each answering `manifest inspect` with a manifest list that contains only `linux/amd64` plus an `unknown/unknown` attestation child
- **When** `python3 scripts/ensure_image.py decide --force false --dow 3` runs (not Sunday, not forced)
- **Then** it prints `built=yes` and `test_built=yes`, the reasons name `base-tag-single-arch` and `test-tag-single-arch`, and `base_arch` names the missing `linux/arm64`
- **Test:** tests/test_ensure_image.py::test_a_published_single_arch_tag_is_not_reused

#### Scenario: a dual-arch published tag is still reused

- **Given** the base, `latest` and test tags published, each answering with a manifest list containing `linux/amd64` AND `linux/arm64`
- **When** the same decision runs on a weekday with no force
- **Then** it prints `built=no test_built=no reason=current` with `base_arch=ok` and `test_arch=ok`
- **Test:** tests/test_ensure_image.py::test_a_multi_arch_published_tag_is_still_reused

#### Scenario: a manifest that cannot be read never triggers a rebuild

- **Given** the base tag published, but its `docker manifest inspect` fails (a registry hiccup: an HTTP 500, not a 404)
- **When** the decision runs
- **Then** it fails loudly (exit 1) naming the ref it could not read, and prints no `built=` line at all — a manifest the registry refused to describe is never read as "single-arch, rebuild it"
- **Test:** tests/test_ensure_image.py::test_an_unreadable_manifest_never_triggers_a_rebuild

#### Scenario: the openspec image gets the same question

- **Given** the openspec tag published as a `linux/amd64`-only manifest while base and test are dual-arch
- **When** the decision runs
- **Then** `publish_openspec=yes` with `openspec_reason` naming `openspec-tag-single-arch`
- **Test:** tests/test_ensure_image.py::test_a_single_arch_openspec_tag_is_republished

#### Scenario: the reuse decision reuses the one manifest verdict

- **Given** `scripts/ensure_image.py`
- **When** it is inspected
- **Then** it imports `check`/`REQUIRED_PLATFORMS` from `scripts/image_manifest_check.py`, declares no platform list of its own, and the two images it verifies are decided through that one function
- **Test:** tests/test_ensure_image.py::test_the_architecture_question_is_the_manifest_gate_verdict
