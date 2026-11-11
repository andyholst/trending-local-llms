# Tasks: install-pin-carries-version

- [x] Guard tests first, RED against the unpinned seam: version-pin one-definition, refuse-a-mismatch, assert-and-bake, empty-pin-records (`tests/test_install_hermes_ci.py`)
- [x] `HERMES_VERSION ?= 0.23.1` in the Makefile and `ARG HERMES_VERSION="0.23.1"` + forwarded `ENV` in the Dockerfile (one default)
- [x] Seam asserts `hermes --version` equals the pin before baking anything, then bakes the verified version to `/opt/hermes-version.txt` (`scripts/install_hermes_ci.py` → `pin_installed_version`)
- [x] AGENTS.md §6k sentence + §8 guard row updated (review-required half, flagged on issue #218 per rule 3c)
- [x] `tests/test_install_hermes_ci.py` green (70 passed) and the full `make test` suite green
- [x] Open the PR with the five-section body closing #218
