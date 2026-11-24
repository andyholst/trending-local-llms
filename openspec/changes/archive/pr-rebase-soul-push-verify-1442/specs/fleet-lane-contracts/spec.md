## ADDED Requirements

### Requirement: The rebase lane SOUL is push-and-verify, not a pre-push local gate

`agents/tll-pr-rebase/SOUL.md` SHALL teach the push-and-verify order for a rebase: change/rebase
locally, run only the FAST offline checks (`make lint` and the targeted unit module), PUSH, then
confirm CI registered on the new head before reporting. That bullet SHALL name the full
`make validate`, the whole `make test`, closure and guard as CI-ONLY, and SHALL NOT instruct the
lane to prove the repo gate green on the rebased head locally. The "a rebase that ships a red head
is not a rebase" intent is kept as: CI red at your head means the rebase is not done.

#### Scenario: The SOUL bullet names the fast checks, the push and the CI registration

- **Given** `agents/tll-pr-rebase/SOUL.md`
- **When** the guard reads its push-and-verify bullet
- **Then** it names the fast offline checks (`make lint`, the targeted unit module), the push, and
  the CI-registered confirmation (`gh pr checks <n>`, `gh run view <id> --json jobs`)
- **Test:** tests/test_pr_rebase_soul_push_verify.py::test_pr_rebase_soul_is_push_and_verify

#### Scenario: The SOUL bullet carries no pre-push local gate

- **Given** `agents/tll-pr-rebase/SOUL.md`
- **When** the guard reads its push-and-verify bullet
- **Then** it carries no instruction to run the repo's gate on the rebased head locally, names the
  four heavy gates CI-ONLY, and states that CI red at your head means the rebase is not done
- **Test:** tests/test_pr_rebase_soul_push_verify.py::test_pr_rebase_soul_is_push_and_verify

#### Scenario: The SOUL agrees with the skill and the rulebook

- **Given** `agents/tll-pr-rebase/SOUL.md`, `agents/tll-pr-rebase/skills/tll-pr-rebase/SKILL.md`
  step 10 and AGENTS.md §7b
- **When** the three are compared
- **Then** all three teach the same order — fast offline checks locally, push, CI verifies — and
  none teaches a pre-push full local gate
- **Test:** tests/test_pr_rebase_soul_push_verify.py::test_pr_rebase_soul_is_push_and_verify
