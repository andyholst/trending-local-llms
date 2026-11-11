# agent-image-publish

## ADDED Requirements

### Requirement: A publish is not done until the registry serves the refs

After pushing the hash tag and `:latest`, `publish()` MUST ask the registry whether it
serves each ref (`docker manifest inspect`), retrying a bounded number of times, and MUST
fail when either is not served.

#### Scenario: the registry serves what was pushed

- **Given** a registry whose read path returns the refs a push just wrote
- **When** `publish --force` runs
- **Then** it exits 0, reports `VERIFIED`, and asked the registry about both refs
- **Test:** tests/test_ensure_image.py::test_a_publish_is_not_done_until_the_registry_serves_it

#### Scenario: the registry accepts the write and never serves it

- **Given** a registry that exits 0 on `push` but reports `manifest unknown` afterwards
- **When** `publish --force` runs
- **Then** it exits non-zero, says the registry does not serve the refs, and names them
- **Test:** tests/test_ensure_image.py::test_a_publish_is_not_done_until_the_registry_serves_it
