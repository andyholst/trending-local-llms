# weekly-security-scan

## ADDED Requirements

### Requirement: the Makefile consumes every third-party tool image through an immutable-pinned ref

The Makefile `*_IMAGE :=` refs (gitleaks + the four vulnerability scanners trivy,
hadolint/containerfile, grype, syft) and the `scripts/*.py` tool-image constants
are each pinned to an immutable `@sha256:<64-hex>` index digest. The
`action-pin-check` tool-image seam serves them without an allowlist entry:
`ALLOWED_IMAGE_REFS` is EMPTY, so the #715 allow-till deadline is satisfied on
master-as-is and a NEW mutable third-party tool-image tag is refused fails-closed.

WHEN the commit trees are scanned by the tool-image seam
THEN every third-party tool image is pinned to an immutable digest or fleet
`<sha12>` tag,
AND `ALLOWED_IMAGE_REFS` has zero entries (0 image allowlisted),
AND a NEW mutable third-party tool-image tag is refused (fails closed),
AND the gitleaks image is pinned (no longer allow-till #715).

#### Scenario: gitleaks and the four scanners are pinned, the image allowlist is empty

- **Given** the Makefile's `*_IMAGE :=` refs and `scripts/*.py` tool-image constants on this tree
- **When** `scripts/action_pin_check.py` reads them and `ALLOWED_IMAGE_REFS`
- **Then** every third-party image is `@sha256:`-pinned, `ALLOWED_IMAGE_REFS` is empty, and `make action-pin-check` exits 0
- **Test:** `tests/test_action_pin.py::test_workflow_allowlist_empty_after_migration` — real seam + empty allowlist assertions on the repo

#### Scenario: a mutable third-party tool-image tag not on the (empty) allowlist is refused

- **Given** a Makefile carrying `TRIVY_IMAGE := ghcr.io/aquasecurity/trivy:v0.50.1` (a mutable tag, and `ALLOWED_IMAGE_REFS` is empty)
- **When** the guard runs
- **Then** it exits non-zero and names the mutable tag
- **Test:** `tests/test_action_pin.py::test_mutable_image_reds` — real guard on a fixture tree, RED

#### Scenario: a pinned-digest or fleet-`<sha12>` image tag passes

- **Given** a Makefile carrying `TRIVY_IMAGE := ghcr.io/aquasecurity/trivy@sha256:<64-hex>` (or a fleet `<sha12>` tag)
- **When** the guard runs
- **Then** it exits 0
- **Test:** `tests/test_action_pin.py::test_image_pinned_digest_green` — real guard on a fixture tree, GREEN

### Requirement: each scanner runs in its own pinned image through a make target

There is one image + one Makefile target per scanner: `make trivy-scan` (Trivy
`fs` vulnerabilities), `make containerfile-scan` (hadolint Dockerfile linter),
`make grype-scan` (Grype `dir:` vulnerabilities), `make syft-sbom` (Syft SBOM,
`OUT=<file>`). Each runs in ITS OWN `@sha256:`-pinned image with `$$PWD`
bind-mounted at `/workspace` (the GITLEAKS_RUN/OS_OPTS seam shape), and each
pinned ref is served by the guard — so the future weekly workflow has something
pinned to run (the schedule + findings wiring are Slices 2/3 of #715).

WHEN the Makefile and the guard are read
THEN all four scanner targets exist,
AND each has its own `*_IMAGE` / `*_RUN` ref pinned to an immutable digest,
AND `make action-pin-check` is GREEN on this repository.

#### Scenario: the four scanner targets and their pinned images are present

- **Given** the Makefile and `scripts/action_pin_check.py`
- **When** the four targets and their `*_IMAGE` refs are read, and the guard runs
- **Then** `trivy-scan`, `containerfile-scan`, `grype-scan`, `syft-sbom` all exist, each image is `@sha256:`-pinned, and the guard exits 0 on the repo
- **Test:** `tests/test_workflows.py::test_weekly_security_scan_slice1_targets` — reads the Makefile, asserts the pinned refs, runs the real guard

### Requirement: the scanners are not a false green (a known-CVE fixture is caught)

`make security-scan-self-test` (`scripts/security_scan_self_test.py`) plants a
known-vulnerable Python fixture (`flask==2.2.2` / `werkzeug==2.2.2`, versions
with published advisories) and REQUIRES both `make trivy-scan` and
`make grype-scan` on that fixture to exit non-zero (RED), and requires both to
exit 0 on an EMPTY tree (nothing to index) — proving the RED is a real finding,
not a scanner that failed to run. It is host-side (trivy/grype fetch a vuln DB
on first run), like `make secret-scan-self-test`, and is deliberately NOT part
of the no-network `validate` job.

WHEN the self-test runs on a docker-capable host with network
THEN trivy and grype both exit non-zero on the known-vulnerable fixture (RED),
AND both exit 0 on the empty tree (GREEN).

#### Scenario: trivy and grype flag the planted vulnerable fixture and pass an empty tree

- **Given** a throwaway directory containing `flask==2.2.2` / `werkzeug==2.2.2` and an empty directory
- **When** the pinned trivy and grype images scan each (like `make trivy-scan` / `make grype-scan` do)
- **Then** both exit non-zero on the vulnerable fixture and exit 0 on the empty tree
- **Test:** `scripts/security_scan_self_test.py` — runs the real pinned images; host-side, network on first DB fetch
