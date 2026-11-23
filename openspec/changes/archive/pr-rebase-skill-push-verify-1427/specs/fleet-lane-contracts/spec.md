## ADDED Requirements

### Requirement: The rebase lane skill is push-and-verify, not a pre-push local gate

`agents/tll-pr-rebase/skills/tll-pr-rebase/SKILL.md` SHALL teach the push-and-verify order for a
rebase: rebase onto freshly fetched `origin/master`, run only the FAST offline checks (`make lint`
and the targeted unit module), PUSH, then confirm CI registered on the new SHA before reporting.
That step SHALL name the full `make validate`, the whole `make test`, closure and guard as CI-ONLY,
and SHALL NOT instruct the lane to prove the whole containerised suite green on the host before it
pushes. The "a rebase that ships a red head is not a rebase" intent is kept as: CI red at your head
means the rebase is not done.

#### Scenario: Step 10 names the fast checks, the push and the CI registration

- **Given** `agents/tll-pr-rebase/skills/tll-pr-rebase/SKILL.md`
- **When** the guard reads procedure step 10
- **Then** it names the fast offline checks (`make lint`, the targeted unit module), the push, and the
  CI-registered confirmation (`gh pr checks <n>`, `gh run view <id> --json jobs`)
- **Test:** tests/test_fleet_lifecycle.py::test_pr_rebase_skill_is_push_and_verify

#### Scenario: Step 10 keeps the red-head rule without a local pre-run

- **Given** `agents/tll-pr-rebase/skills/tll-pr-rebase/SKILL.md`
- **When** the guard reads procedure step 10
- **Then** it carries no instruction to run the repo's gate on the rebased head locally, and it states
  that CI red at your head means the rebase is not done
- **Test:** tests/test_fleet_lifecycle.py::test_pr_rebase_skill_is_push_and_verify

#### Scenario: The heavy gates are named CI-ONLY

- **Given** `agents/tll-pr-rebase/skills/tll-pr-rebase/SKILL.md`
- **When** the guard reads procedure step 10
- **Then** the full `make validate`, the whole `make test`, closure and guard are each named CI-ONLY
- **Test:** tests/test_fleet_lifecycle.py::test_pr_rebase_skill_is_push_and_verify
