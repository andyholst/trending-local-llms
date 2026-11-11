# Proposal: install-pin-carries-version

**Issue:** [#218](https://github.com/andyholst/trending-local-llms/issues/218)

## Why

Issue #218 (tech-debt, filed while implementing #207): the install "pin" is a URL, not a version. `ARG HERMES_INSTALL_URL=…/install.sh` + `ARG HERMES_PACKAGE="hermes-agent"` mean the SAME Dockerfile content-hash tag (rule 6k, issue #135) can build images containing DIFFERENT agent versions — the installer's `stable` channel serves whatever the latest published release is the day the build runs. A content-hash tag only promises reproducibility if what it installs is pinned and checkable.

## What Changes

- `HERMES_VERSION` joins the install pin: one `?=` in the Makefile, one matching `ARG` default in the Dockerfile (the same one-definition rule the URL/package pins already enforce).
- The seam (`scripts/install_hermes_ci.sh`) asserts after any install path (including an already-present CLI): `hermes --version` must equal the pin, else the BUILD FAILS loudly naming pin and actual.
- The verified version is BAKED into the image at `/opt/hermes-version.txt` — the version the tag can carry.
- No-pin runs (explicit `HERMES_VERSION=""`) record the version without asserting, for mirrors.

## Impact

- `Makefile`, `Dockerfile`, `scripts/install_hermes_ci.sh`
- `tests/test_install_hermes_ci.py` (new guards, red on the unpinned seam)
- AGENTS.md §6k (the seam sentence gains the version assertion — review-required half, flagged on issue #218 per rule 3c) and the §8 guard row

## Not covered

- Publishing per-version image tags or multi-arch tags — issue #767 tracks the arch gap; this change only makes the built image STATE the version it contains and refuse to build a different one.
