# Spec delta: master-push-guard

## ADDED Requirement: `make check-branch-protection` refuses an unguarded master

`scripts/check_branch_protection.py` (reached only through
`make check-branch-protection REPO=<owner/repo>`, or `--from-file <recorded.json>`
against a recorded protection payload) asserts that the base branch carries
branch protection whose `required_status_checks` are `strict: true` and name a
context for each of the auto-merge gate checks (`validate`, `live-smoke`), and
whose `enforce_admins` is true. Missing protection, a relaxed strict flag, a
dropped context, or a relaxed admins flag is a refusal (exit 1); an unreadable
protection read is a refusal (exit 2), never a silent clean. The guard runs in
the weekly `queued-alarm` sweep, so a silently-removed protection goes red
instead of quietly restoring the unguarded state.

#### Scenario: a recorded, correctly protected master passes

- **Test:** tests/test_branch_protection.py::test_a_correctly_protected_master_passes
- **Given** a recorded protection payload with `strict: true`, contexts naming
  `validate` and `live-smoke`, and `enforce_admins: true`
- **When** `make check-branch-protection` is run against that recorded payload
- **Then** the target exits 0 and prints the shape it verified

#### Scenario: a relaxed or partial protection is refused

- **Test:** tests/test_branch_protection.py::test_a_relaxed_protection_is_refused
- **Given** recorded payloads that drop the strict flag, drop one required
  context, or set `enforce_admins: false` (each separately)
- **When** the guard checks each one
- **Then** each is refused (exit 1) and the refusal names what is missing

#### Scenario: no protection at all is refused

- **Test:** tests/test_branch_protection.py::test_an_absent_protection_is_refused
- **Given** a recorded payload that is GitHub's 404 body
- **When** the guard checks it
- **Then** the check exits 1 saying the branch has no protection

#### Scenario: an unreadable protection read is loud, never clean

- **Test:** tests/test_branch_protection.py::test_an_unreadable_payload_is_loud
- **Given** a malformed recorded payload
- **When** the guard checks it
- **Then** the check exits 2 and does not print a pass

#### Scenario: the guard is wired to a make target and a scheduled pipeline

- **Test:** tests/test_branch_protection.py::test_the_guard_is_wired_through_make_and_queued_alarm
- **Given** the repository tree
- **When** the wiring is checked
- **Then** the Makefile defines `check-branch-protection`, the target calls
  `scripts/check_branch_protection.py` through `make` only, and
  `.github/workflows/queued-alarm.yml` runs `make check-branch-protection`
  as a step that needs the guard job
