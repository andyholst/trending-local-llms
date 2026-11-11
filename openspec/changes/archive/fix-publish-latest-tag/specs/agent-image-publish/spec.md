# agent-image-publish

## ADDED Requirements

### Requirement: `publish` tags every ref it pushes

`publish()` MUST tag the image with every ref it pushes before pushing it. It
pushes the hash tag and `:latest`; the build therefore MUST tag `:latest`
(`latest_tag()`) too, not only the local `IMAGE` and the hash tag — real docker
refuses `docker push <ref>` when `<ref>` was never tagged (`tag does not exist`).

WHEN `publish` builds and pushes the agent image,
THEN every ref it pushes has been tagged by the same run, so the `:latest` push
succeeds.

#### Scenario: the `:latest` push has a local tag

- **Given** the fake `docker` stub that refuses to push an untagged ref
- **When** `publish` runs
- **Then** it exits 0 and both the hash tag and `:latest` are pushed without the fake's `tag does not exist` refusal
- **Test:** `tests/test_publish_agent_image.py::test_publish_builds_and_pushes_both_refs_when_absent`

#### Scenario: an untagged push is caught by the suite

- **Given** `publish()` build without `-t latest_tag()` (the shipped bug)
- **When** the fake `docker` refuses the untagged `:latest` push
- **Then** `test_publish_builds_and_pushes_both_refs_when_absent` and `test_force_rebuilds_the_same_inputs_on_demand` fail
- **Test:** `tests/test_publish_agent_image.py::test_publish_builds_and_pushes_both_refs_when_absent`
