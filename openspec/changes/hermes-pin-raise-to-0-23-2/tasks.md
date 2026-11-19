# Tasks — hermes-pin-raise-to-0-23-2

- [x] Raise the Makefile `HERMES_VERSION ?=` to 0.23.2 — VERIFIED: `make hermes-pin-freshness
      REPO=andyholst/trending-local-llms` prints `pin=0.23.2 channel=v0.23.2 OK` (live channel, rc 0)
- [x] Raise the Dockerfile `ARG HERMES_VERSION` to 0.23.2 in the same commit (issue #218: never one
      pin alone) — VERIFIED: `tests/test_install_hermes_ci.py::test_the_version_pin_has_one_definition_across_the_two_files`
      green (29 passed for the two install/pin suites)
- [x] Refresh `tests/fixtures/hermes_releases_latest.json` to the RECORDED `v0.23.2` release payload
      (rule 6b: the contract move and its test move together; recorded from
      `gh api repos/NousResearch/hermes-agent/releases/latest`, not authored) — VERIFIED:
      `make hermes-pin-freshness REPO=andyholst/trending-local-llms FROM_FILE=tests/fixtures/hermes_releases_latest.json`
      prints `pin=0.23.2 channel=v0.23.2 OK`
- [x] Confirm the drift gate closes issue #1145 — VERIFIED: the live verdict is green (rc 0) and no
      new drift issue is filed (the gate files only on a strictly-newer channel)
