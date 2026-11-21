## Tasks — #741 (#715 Slice 1): per-scanner images + Makefile targets + tool-image pinning

### Scanner images + Makefile targets

- [x] Add `TRIVY_IMAGE` / `TRIVY_RUN` + `make trivy-scan` (Trivy `fs` vuln scan, `@sha256:`-pinned, `$$PWD` at `/workspace`)
- [x] Add `CONTAINERFILE_IMAGE` / `CONTAINERFILE_RUN` + `make containerfile-scan` (hadolint Dockerfile linter, `@sha256:`-pinned)
- [x] Add `GRYPE_IMAGE` / `GRYPE_RUN` + `make grype-scan` (Grype `dir:` scan, `@sha256:`-pinned)
- [x] Add `SYFT_IMAGE` / `SYFT_RUN` + `make syft-sbom` (Syft SBOM, `OUT=` required, `@sha256:`-pinned)
- [x] Each target runs in its OWN image with `$$PWD` mounted at `/workspace` (GITLEAKS_RUN/OS_OPTS seam shape)

### Tool-image pinning (#715 allow-till closed)

- [x] Pin gitleaks image to its `@sha256:` digest in `GITLEAKS_IMAGE` and `scripts/secret_scan_self_test.py`
- [x] Extend `scripts/action_pin_check.py` tool-image seam so its `scripts/*.py` scan captures the optional `@sha256:<digest>` suffix (a pinned script image reads as pinned)
- [x] Empty `ALLOWED_IMAGE_REFS` (0 workflow + 0 image allowlisted) — #715 allow-till deadline satisfied; a NEW mutable third-party tool-image tag is refused
- [x] `make action-pin-check` GREEN on master-as-is (gitleaks + 4 scanners all `@sha256:`-pinned)

### Not-a-false-green self-test

- [x] Add `scripts/security_scan_self_test.py` — plants a known-vulnerable `flask==2.2.2`/`werkzeug==2.2.2` fixture; REQUIRES trivy + grype to RED it and GREEN an empty tree
- [x] Add `make security-scan-self-test` — host-side (trivy/grype fetch a vuln DB), NOT part of the no-network `validate` job (like `make secret-scan-self-test`)

### Tests + OpenSpec

- [x] `tests/test_action_pin.py` — mutable-image-RED with the empty allowlist (green control = pinned digest), `ALLOWED_IMAGE_REFS` empty assertion, every Makefile third-party image ref pinned
- [x] `tests/test_workflows.py::test_weekly_security_scan_slice1_targets` — four targets exist, each `*_IMAGE` is `@sha256:`-pinned, `security-scan-self-test` target exists, guard GREEN on the repo
- [x] `make test` green (test_action_pin 15/0, test_workflows 1007/0)
- [x] OpenSpec change dir `weekly-security-scan` (proposal + GWT spec + tasks) — index moves to 184 active / 13 archived

### Scope boundary

- [x] Do NOT ship `.github/workflows/security-scan.yml`, findings wiring, or gate-fail (Slices 2/3) — confirmed out of scope for this holder
