# hermes-pin-freshness

## MODIFIED Requirements

### Requirement: The Hermes pins are compared with the upstream release channel by ONE check

The Makefile's `HERMES_VERSION ?=` and the Dockerfile's `ARG HERMES_VERSION` pin the agent
version every fleet image bakes (rule 6k, issue #218 pins the two together). `scripts/hermes_pin_freshness.py`
(reached only through `make hermes-pin-freshness`) MUST read BOTH pins back from the tree, refuse a
silent disagreement between them with exit 2 BEFORE consulting the channel, and compare the pin with
the upstream release channel (`gh api repos/<channel>/releases/latest`, or a recorded
payload via `FROM_FILE=`/`--from-file` — the same fixture seam as `check_branch_protection.py`) using
the recorded payloads themselves, never a version-parsing mock stand-in.

The channel repo `<channel>` MUST be DERIVED from the Makefile's install-pin block — the single
`HERMES_CHANNEL_REPO ?=` line beside `HERMES_INSTALL_URL` (issue #1094, rule 6d): the script carries
NO literal spelling of the channel repo, and a Makefile without the pin is a loud exit-2 refusal
naming the missing `HERMES_CHANNEL_REPO`, never a fallback to an embedded default.

WHEN the `queued-alarm` sweep runs the check,
THEN the pinned agent's freshness against upstream is a loud, tracked verdict instead of a state that
surfaces only at the next image build, and an upstream channel move is a one-line Makefile edit that
every pairing assertion sees.

#### Scenario: the channel repo is read from the Makefile pin block, end to end

- **Given** a planted Makefile whose `HERMES_CHANNEL_REPO ?=` names a planted channel repo and a
  planted recorded channel payload the `gh` stub serves for that repo's `releases/latest` endpoint
- **When** the check runs
- **Then** the `gh api` call it makes names the planted repo's endpoint (the derived value, not an
  embedded default) and the filed drift issue's evidence quotes the derived `repos/<channel>/…`
- **Test:** `tests/test_hermes_pin_freshness.py::test_channel_newer_goes_red_files_one_tech_debt_issue_naming_the_remedy`

#### Scenario: the script carries no literal spelling of the channel repo

- **Given** the source of `scripts/hermes_pin_freshness.py` and the repository Makefile
- **When** the suite scans them
- **Then** the script names the vendor channel repo NOWHERE (no literal), the Makefile carries
  `HERMES_CHANNEL_REPO ?=` exactly once, and a planted Makefile missing the pin exits 2 naming
  `HERMES_CHANNEL_REPO` without ever consulting `gh api`
- **Test:** `tests/test_hermes_pin_freshness.py::test_the_channel_repo_is_derived_from_the_makefile_pin_block`
