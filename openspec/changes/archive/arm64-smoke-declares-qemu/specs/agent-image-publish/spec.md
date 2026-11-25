## ADDED Requirements

### Requirement: The arm64 smoke declares its emulation prerequisite

The `build` job of `refresh-bot.yml` SHALL register an arm64 binfmt handler on
the amd64 runner before the host-side `docker run --platform linux/arm64` smoke
executes. The registration SHALL be a `docker/setup-qemu-action` step pinned to
an immutable 40-hex commit SHA, SHALL declare exactly `platforms: linux/arm64`,
and SHALL NOT introduce an architecture selector or a second publish-platform
contract.

#### Scenario: QEMU step precedes the arm64 smoke

- **Given** the `build` job of `refresh-bot.yml` on an amd64 runner
- **When** the job reaches "Prove the arm64 base runs, not just exists (QEMU smoke)"
- **Then** a pinned `docker/setup-qemu-action` step with `platforms: linux/arm64` has already run, and `docker run --rm --platform linux/arm64 <tag> hermes --version` exits 0 printing v0.23.4
- **Test:** `tests/test_workflows.py::test_arm64_smoke_declares_qemu_handler_before_it`

#### Scenario: One platform verdict stays one

- **Given** the QEMU step declares `linux/arm64` as its emulated platform
- **When** the base hash tag is published and checked
- **Then** the emulated platform is a subset of `image_manifest_check.REQUIRED_PLATFORMS`, no amd64 emulation is declared, and the publisher still derives `--platform` from that one value
- **Test:** `tests/test_workflows.py::test_arm64_smoke_keeps_one_platform_verdict`

### Requirement: The arm64 child starts, not just exists

The arm64 smoke SHALL exec the published arm64 child and read its version file,
so a layer that merely answers the manifest but cannot start is caught.

#### Scenario: The smoke execs the arm64 child

- **Given** the index answers both `linux/amd64` and `linux/arm64`
- **When** the QEMU smoke step runs under the registered handler
- **Then** it execs `docker run --rm --platform linux/arm64 <tag> hermes --version` and `cat /opt/hermes-version.txt`, with no host-side arch selector, proving the arm64 interpreter starts
- **Test:** `tests/test_workflows.py::test_arm64_smoke_execs_aarch64_child`
