## ADDED Requirements

### Requirement: The image declares the cua-driver X11 runtime libraries before the install seam

The CI/local container image SHALL declare, in its single system apt layer and before the `install_hermes_ci.sh` seam RUN, the Debian packages `libx11-6`, `libxi6` and `libxkbcommon0`, so the external installer's staged `cua-driver --version` entry check remains a real dynamic-load probe that can pass. The staged verification SHALL stay intact: no headless-tolerant skip, no `|| true`, no opt-out flag and no fork of the installer.

#### Scenario: The shipped apt layer declares all three runtime libraries before the seam

- **Given** the shipped Dockerfile
- **When** the image apt layer before the seam RUN is read
- **Then** it declares `libx11-6`, `libxi6` and `libxkbcommon0`, each before the seam runs
- **Test:** tests/test_install_hermes_ci.py::test_the_image_carries_the_cua_driver_runtime_libs

#### Scenario: A base image without the libraries is refused

- **Given** the pinned base Dockerfile with the three packages absent
- **When** the same Dockerfile-shape guard reads its apt layer
- **Then** it fails, naming `libx11-6`, `libxi6` and `libxkbcommon0` as undeclared
- **Test:** tests/test_install_hermes_ci.py::test_the_image_carries_the_cua_driver_runtime_libs

#### Scenario: No verification opt-out was introduced

- **Given** the shipped Dockerfile
- **When** the guard inspects it for a baked-in bypass of the staged check
- **Then** no `|| true`, `--without cua-driver` or empty `HERMES_VERSION` opt-out is present, and the seam RUN is unchanged
- **Test:** tests/test_install_hermes_ci.py::test_the_image_carries_the_cua_driver_runtime_libs
