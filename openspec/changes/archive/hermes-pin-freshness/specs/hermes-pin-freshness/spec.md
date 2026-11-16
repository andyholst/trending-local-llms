# hermes-pin-freshness

## ADDED Requirements

### Requirement: The Hermes pins are compared with the upstream release channel by ONE check

The Makefile's `HERMES_VERSION ?=` and the Dockerfile's `ARG HERMES_VERSION` pin the agent
version every fleet image bakes (rule 6k, issue #218 pins the two together). `scripts/hermes_pin_freshness.py`
(reached only through `make hermes-pin-freshness`) MUST read BOTH pins back from the tree, refuse a
silent disagreement between them with exit 2 BEFORE consulting the channel, and compare the pin with
the upstream release channel (`gh api repos/NousResearch/hermes-agent/releases/latest`, or a recorded
payload via `FROM_FILE=`/`--from-file` — the same fixture seam as `check_branch_protection.py`) using
the recorded payloads themselves, never a version-parsing mock stand-in.

WHEN the `queued-alarm` sweep runs the check,
THEN the pinned agent's freshness against upstream is a loud, tracked verdict instead of a state that
surfaces only at the next image build.

#### Scenario: channel equal to the pin is green with the OK line

- **Given** a recorded channel payload whose release tag equals both pins
- **When** `scripts/hermes_pin_freshness.py` runs against it
- **Then** it exits 0 and prints `pin=<v> channel=<v> OK`, and files nothing
- **Test:** `tests/test_hermes_pin_freshness.py::test_channel_equal_to_pin_prints_ok_and_exits_green`

#### Scenario: a strictly newer channel goes red and files ONE tech-debt issue naming the remedy

- **Given** a planted channel release strictly newer than both (agreeing) pins
- **When** the check runs
- **Then** it exits 1 loudly and files exactly ONE `tech-debt` issue whose body names the remedy —
  raise BOTH pins together per #218 — and carries the evidence pair (the Makefile line and the
  Dockerfile `ARG HERMES_VERSION="…"` line), and `--dry-run` previews the drift without filing
- **Test:** `tests/test_hermes_pin_freshness.py::test_channel_newer_goes_red_files_one_tech_debt_issue_naming_the_remedy`

#### Scenario: the drift filing is marker-deduplicated across sweeps

- **Given** a drifted channel already filed by an earlier sweep as an OPEN issue carrying the
  registered `hermes-pin-drift-signature` marker
- **When** a later sweep re-runs the check with the same drift
- **Then** it still exits 1 (the drift is still real) but files NOTHING new, reports
  `already-filed=<url>`, and a CLOSED drift issue does not suppress a filing of a still-live drift
- **Test:** `tests/test_hermes_pin_freshness.py::test_the_drift_filing_is_marker_deduped_across_re_runs`

#### Scenario: a pin ahead of the channel is reported, never red

- **Given** a recorded channel release older than both pins
- **When** the check runs
- **Then** it reports `AHEAD` and exits 0, filing nothing
- **Test:** `tests/test_hermes_pin_freshness.py::test_pin_ahead_of_channel_is_reported_not_red`

#### Scenario: an unreadable channel is a loud exit 2, never a silent clean

- **Given** a run whose channel read is refused (the recorded payload is absent and the API read fails)
- **When** the check runs
- **Then** it exits 2 naming why, never prints OK, and files nothing
- **Test:** `tests/test_hermes_pin_freshness.py::test_unreadable_channel_is_a_loud_exit_two_never_a_clean`

#### Scenario: a Makefile/Dockerfile pin disagreement is refused before the channel is consulted

- **Given** planted pins that disagree (`HERMES_VERSION ?= 0.10.0` beside `ARG HERMES_VERSION="0.10.1"`)
- **When** the check runs
- **Then** it exits 2 naming both pins and the rule-6k remedy (raise BOTH together), never consulting
  the channel API and filing nothing — the silent split pins are the #218 defect itself
- **Test:** `tests/test_hermes_pin_freshness.py::test_pin_disagreement_between_makefile_and_dockerfile_refuses_before_the_channel_is_read`

#### Scenario: the recorded payload is compared against the REAL pins

- **Given** `tests/fixtures/hermes_releases_latest.json` — a recorded real `releases/latest` payload —
  and the repository's own Makefile/Dockerfile pins
- **When** the check runs with `--from-file` at that payload
- **Then** it produces the verdict from the recorded payload (exit 0 `OK` while the pin matches,
  `AHEAD` after a future pin bump) and makes NO `gh api` call at all
- **Test:** `tests/test_hermes_pin_freshness.py::test_recorded_channel_payload_is_compared_against_the_real_pins`

### Requirement: The queued-alarm sweep runs the check through the Makefile only

The sweep pipeline `.github/workflows/queued-alarm.yml` MUST run `make hermes-pin-freshness
REPO=<github.repository>` as a report-and-file alarm step (the `pipeline-failure-issue` pattern:
`if: ${{ !cancelled() }}`, the default `github.token` because filing needs `issues: write`), so a
channel newer than the pin — or an unreadable channel/pin pair — turns the sweep RED. No workflow
step may reach `scripts/hermes_pin_freshness.py` past the Makefile (rule 6m), and the drift marker's
name lives only in `scripts/bot_markers.py` (rule 6j).

WHEN the upstream Hermes channel passes the pin,
THEN the next scheduled sweep goes red and carries one tracked issue, instead of the drift waiting
for the next image dispatch to be noticed.

#### Scenario: the sweep carries the make-wired step and refuses a makeless one

- **Given** `.github/workflows/queued-alarm.yml`'s `alarm` job
- **When** its steps are scanned by the wiring guard
- **Then** the real workflow carries a `make hermes-pin-freshness REPO=…` step filing with the default
  token, a step reaching the script without `make` is REFUSED, a sweep missing the step is REFUSED,
  and no workflow anywhere names `scripts/hermes_pin_freshness.py` directly
- **Test:** `tests/test_hermes_pin_freshness.py::test_queued_alarm_sweep_calls_the_target_and_a_makeless_step_is_refused`

#### Scenario: the drift marker is registered in the ONE marker table

- **Given** `scripts/bot_markers.py`'s registered marker keys and the writer script
- **When** the registry is read
- **Then** `hermes-pin-drift-signature` is a registered dedup key whose acceptance pattern matches the
  writer's rendering, and the script spells the marker only through the registered name — no re-spelled
  literal
- **Test:** `tests/test_hermes_pin_freshness.py::test_the_drift_marker_is_registered_in_bot_markers`
