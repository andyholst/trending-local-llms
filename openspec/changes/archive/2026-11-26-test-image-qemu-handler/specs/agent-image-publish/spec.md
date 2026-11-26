# agent-image-publish

## ADDED Requirements

### Requirement: The test-image arm64 smoke declares its own QEMU handler

The `test-image` job of `refresh-bot.yml` SHALL register
`docker/setup-qemu-action@99012661954931238ded8c8b007157a8430204e1` with exactly
`platforms: linux/arm64` BEFORE the step that runs `make test-image-smoke`. The handler registered
in the `build` job SHALL NOT be relied on: each job runs on its own runner. No second platform set
or arch selector SHALL be introduced.

#### Scenario: the published arm64 test image is executed on an amd64 runner

- **Given** the `test-image` job with an arm64 `docker run --platform linux/arm64`
- **When** `test_test_image_arm64_smoke_declares_qemu_handler` inspects that job
- **Then** exactly one pinned QEMU step precedes the smoke, its platform is `linux/arm64`, and the guard fails on the previously tokenless-handler job
- **Test:** tests/test_workflows.py::test_test_image_arm64_smoke_declares_qemu_handler
