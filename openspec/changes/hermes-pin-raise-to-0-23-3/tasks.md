# Tasks — hermes-pin-raise-to-0-23-3

- [x] Raise the Makefile `HERMES_VERSION ?=` to 0.23.3 — VERIFIED: `make hermes-pin-freshness
      REPO=andyholst/trending-local-llms` prints `pin=0.23.3 channel=v0.23.3 OK` (live channel, rc 0)
- [x] Raise the Dockerfile `ARG HERMES_VERSION` to 0.23.3 in the same commit (issue #218: never one
      pin alone) — VERIFIED: `tests/test_install_hermes_ci.py::test_the_version_pin_has_one_definition_across_the_two_files`
      green (`PASSED 73 | FAILED 0`)
- [x] Refresh `tests/fixtures/hermes_releases_latest.json` to the RECORDED `v0.23.3` release payload
      (recorded from `gh api repos/NousResearch/hermes-agent/releases/latest`, not authored; rule 6b)
      — VERIFIED: `make hermes-pin-freshness REPO=andyholst/trending-local-llms
      FROM_FILE=tests/fixtures/hermes_releases_latest.json` prints `pin=0.23.3 channel=v0.23.3 OK`
- [x] Add the agreement guard `tests/test_hermes_pin_freshness.py::test_the_shipped_pins_and_the_recorded_payload_name_one_release`
      and prove it RED on a planted tree where the fixture lags the pins — VERIFIED: the planted lag
      and the planted ahead are both refused naming all three spellings, the shipped tree is green, and
      the guard is RED against the raised pins plus `git show origin/master:`'s `v0.23.2` payload
- [ ] Run the pin-sensitive suites green on the raised tree (`test_hermes_pin_freshness.py`,
      `test_install_hermes_ci.py`, `test_agent_skills.py`, `test_agent_shell_keys.py`) and the full
      host suite — VERIFIED: `bash scripts/run_tests.sh` reports 0 failed
- [ ] Keep the generated artifacts true: `make openspec-index` + `openspec-index-check`,
      `make architecture-check`, `make lint`, `make secret-scan`, `make openspec-check` — VERIFIED
      green on the branch head
- [ ] Add the `AGENTS.md` §8 regression-guard row for the agreement guard (rule 6c: a fixed pipeline
      defect gets its row in the same change; no behaviour rule changes) — VERIFIED: the row names the
      measured red image build (qa-validate run 44651246625) and the guard that refuses it
