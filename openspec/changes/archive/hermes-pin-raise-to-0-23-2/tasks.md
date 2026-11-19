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
- [x] Land the temp Hermes home teardown seam `tests/hermes_home.py` (`remove_hermes_home` bounded
      retry + `temp_hermes_home`), ONE implementation for every test that points Hermes at a temp
      home (rule 6d) — VERIFIED: the pinned 0.23.2 seeds `cache/uv/**`, `installs/<hash>` and
      `cache/default-plugins.settled` into the home 4 s after the CLI returned (host measurement),
      which is what made qa-validate run 44537216542 red in `tests/test_agent_skills.py`
- [x] Use the seam at the live-Hermes sites (`tests/test_agent_skills.py`'s registration test,
      `tests/test_agent_shell_keys.py`'s two probe tests) and add the teardown's own guards —
      VERIFIED: `python3 tests/test_agent_skills.py` → `161 passed, 0 failed`;
      `python3 tests/test_agent_shell_keys.py` → `PASSED 51 | SKIPPED 0 | FAILED 0`; no `/tmp/tmp*`
      home left behind after the run
- [x] Guard BOTH halves of the seam (tolerates a late writer; a stuck tree raises) and record the
      defect in `AGENTS.md` §8 — VERIFIED: the two new scenarios' `Test:` references resolve under
      `make openspec-check`, and the §8 row names the class and the measured CI run
