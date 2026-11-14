# agent-image

## ADDED Requirements

### Requirement: The image carries the package manager the seam's third path needs

The agent image SHALL install `uv` before it runs the install seam, so that
`uv tool install $HERMES_PACKAGE` is actually executable inside the container the seam was
written for — not a path the contract advertises while the failure line reports
`uv: not installed`. The pinned test reads the Dockerfile and refuses a build order where
the seam runs before `uv` is installed.

#### Scenario: the seam's uv fallback can run inside the image

- **Given** the repository's `Dockerfile`
- **When** the install-seam suite reads which tools the image installs before invoking
  `install_hermes_ci.sh`
- **Then** `uv` is installed before the seam line, and the seam script itself still keeps
  its three-path contract and loud failure unchanged
- **Test:** tests/test_install_hermes_ci.py::test_the_image_installs_uv_before_the_seam_runs
