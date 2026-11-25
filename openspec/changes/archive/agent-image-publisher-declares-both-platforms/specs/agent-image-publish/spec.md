# agent-image-publish

## ADDED Requirements

### Requirement: The agent image publisher declares both required platforms

The privileged publisher in `scripts/ensure_image.py::publish` MUST write the
hash tag and `:latest` with ONE Buildx build that declares BOTH platforms in
`image_manifest_check.REQUIRED_PLATFORMS`, on those SAME two refs. It MUST derive
the `--platform` string from that single existing contract — the one the reuse
decision and `make image-manifest-check` already consume (rule 6d) — and MUST
NOT keep a second platform list or add a host-architecture selector. Because a
multi-platform Buildx build publishes through `--push`, the separate `docker
push` calls MUST be folded into that one build. The content hash, the tag recipe,
the no-op/force guard and the post-push `_serves()` verification MUST stay
unchanged, so an amd64 host still receives its `linux/amd64` child and no
consumer contract, workflow or Makefile target changes.

#### Scenario: publishing an absent tag declares both platforms on the same refs

- **Given** this revision's hash tag is absent from the registry (`available=[]`)
- **When** `python3 scripts/ensure_image.py publish` runs
- **Then** exactly one `docker buildx build` carries `--platform linux/amd64,linux/arm64` derived from `REQUIRED_PLATFORMS`, declares the hash tag and `:latest`, passes `--push`, and the `_serves()` re-probe still checks both refs
- **Test:** tests/test_publish_agent_image.py::test_publish_declares_both_platforms_from_the_one_contract

#### Scenario: an already published tag is still a no-op

- **Given** this revision's hash tag is already published
- **When** `publish` runs without `--force`
- **Then** it builds nothing and pushes nothing, and reports that the tag is already published
- **Test:** tests/test_publish_agent_image.py::test_publish_is_a_noop_when_this_revision_is_already_published

#### Scenario: a forced rebuild declares both platforms too

- **Given** this revision's hash tag is published
- **When** `python3 scripts/ensure_image.py publish --force` runs
- **Then** it still makes exactly one Buildx build with `--platform linux/amd64,linux/arm64` and `--push`, publishing the same refs on demand
- **Test:** tests/test_publish_agent_image.py::test_force_rebuilds_the_same_inputs_on_demand

#### Scenario: the platform string has exactly one source

- **Given** `scripts/ensure_image.py`
- **When** its platform source is inspected
- **Then** it imports `REQUIRED_PLATFORMS` from `scripts/image_manifest_check.py`, builds the platform string from that constant, and contains no `platform.machine()` / `uname -m` / `dpkg --print-architecture` host-architecture selector
- **Test:** tests/test_publish_agent_image.py::test_the_publisher_derives_platforms_from_the_one_verdict
