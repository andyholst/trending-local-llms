# Weekly container/dependency vulnerability scan (trivy + containerfile + grype + syft)

**Issue:** [#715](https://github.com/andyholst/trending-local-llms/issues/715) · holder **#741** (#715 Slice 1)
**Capability:** `weekly-security-scan`

## Why

The repo runs many third-party tools as pinned container images (gitleaks, and
starting this slice trivy, hadolint/containerfile, grype, syft) and its product
data contains measured model/hardware numbers that a vulnerable dependency or
container base could silently compromise. There is no automated
container/dependency vulnerability scan and no artifact that answers "which of
our pinned tool/runtime images has a known CVE this week?". #715 is the
initiative to run such a scan weekly and make its findings a reviewable report.

This change dir is the parent #715 `weekly-security-scan` change. This first
slice (holder #741) brings up the *scanner images + Makefile targets* that the
future weekly workflow will call: one pinned image per scanner, each consumed
via an immutable `@sha256:` digest so the `action-pin-check` tool-image seam
serves it without an allowlist entry. It also **pins the gitleaks image** that
had been riding `ALLOWED_IMAGE_REFS` allow-till #715, and **empties that
allowlist** — the #715 allow-till deadline is satisfied on master-as-is.

Slices 2/3 (the weekly `security-scan.yml` schedule + report artifacts, and the
findings wiring / gate-fail) follow and stay in this change dir; this slice is
deliberately limited to images + targets + pinning so the weekly workflow has
something pinned to run.

## What Changes

- **Makefile — four per-scanner image refs + targets** (issue #741):
  - `TRIVY_IMAGE` / `TRIVY_RUN` — `make trivy-scan`: Trivy `fs` container/dependency
    vulnerability scan (exit 1 on a finding).
  - `CONTAINERFILE_IMAGE` / `CONTAINERFILE_RUN` — `make containerfile-scan`:
    hadolint lints the repo's Containerfile/Dockerfile(s) (exit 1 on a violation).
  - `GRYPE_IMAGE` / `GRYPE_RUN` — `make grype-scan`: Grype `dir:` scan (exit 2 —
    the grype threshold code — on a finding).
  - `SYFT_IMAGE` / `SYFT_RUN` — `make syft-sbom`: Syft SBOM of the scan dir
    (`OUT=<file>`), the catalog feed for the future weekly workflow.
  - Each consumes its **OWN image** pinned to an immutable `@sha256:` index digest,
    `$$PWD` bind-mounted at `/workspace` (the GITLEAKS_RUN/OS_OPTS seam shape).
- **Tool-image pinning closes the allow-till-#715 deadline:** gitleaks is pinned
  to its `@sha256:` digest in `GITLEAKS_IMAGE` AND `scripts/secret_scan_self_test.py`;
  the four scanners are added as pinned refs; `scripts/action_pin_check.py`
  `ALLOWED_IMAGE_REFS` becomes **empty** (0 workflow + 0 image allowlisted). The
  tool-image seam also now captures the optional `@sha256:<digest>` suffix in its
  `scripts/*.py` scan (a pinned script image must be read as pinned). A NEW mutable
  third-party tool-image tag is refused fails-closed.
- **`scripts/security_scan_self_test.py` + `make security-scan-self-test`:** the
  scanners-must-not-be-a-false-green self-test — plants a known-vulnerable
  `flask==2.2.2`/`werkzeug==2.2.2` fixture and REQUIRES `make trivy-scan` /
  `make grype-scan` on it to be RED (exit != 0), and REQUIRES both to be GREEN on
  an empty tree. Host-side (trivy/grype fetch a vuln DB on first run), so it is
  NOT part of the no-network `validate` job — like `make secret-scan-self-test`.
- **Do NOT yet create** `.github/workflows/security-scan.yml`, the findings
  wiring, or the gate-fail (Slices 2/3). No workflow change in this slice.

## Out of scope (this holder)

- Slice 2: the weekly `security-scan.yml` schedule/workflow + report artifacts.
- Slice 3: findings wiring (`findings-check`/`file-findings` ingest), gate-fail
  logic, README weekly-report doc.
- Any `.github/workflows/**` change (qa-validate.yml is not touched in this slice).
