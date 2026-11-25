# pr-health-rebase-verdict

## ADDED Requirements

### Requirement: The pr-health sweep reds when a rebased head's CI could not be verified

`make pr-health REBASE=1` (the dispatched `pr-health.yml` sweep) fetches every branch tip and
rebases each behind-and-clean bot-owned PR head onto the fetched base, pushing it back to the
PR's own head. A push is only a completed repair when the PUSHED head's own `qa-validate.yml`
run carries more than zero jobs; issue #1616 makes `run_rebaser` record that proof as
`ci_verified` on each outcome. When any rebased outcome answers `ci_verified is False`, the
sweep exits 1 and NAMES the affected PR and its head with the reason — a green sweep over a
branch moved onto a 0-job head read to an operator as "nothing needs a human". A VERIFIED
rebase, an already-current branch, a plan-refused branch (human-owned, CONFLICTING, draft) and
a rebase git refused are all unchanged.

#### Scenario: a pushed head whose own qa-validate run carries zero jobs reds the sweep

- **Given** a real local origin whose `master` moved ahead of a clean `ci/` PR head, with the
  clone's configured origin spelled as github.com and mapped back by git's own `insteadOf`,
  and a stubbed `gh` whose planted run for the pushed sha carries ZERO jobs
- **When** `scripts/pr_health.py --repo o/r --rebase --dir <clone>` runs
- **Then** the process exits 1, prints `REBASED but CI UNVERIFIED`, names `#7` and its head,
  says the rebase is not a completed repair, and the report still reads `0 silent` (the red is
  the unverified verdict, not the silent-PR half)
- **Test:** tests/test_pr_health.py::test_an_unverified_rebase_reds_the_sweep_and_a_verified_one_stays_green

#### Scenario: a verified completed rebase stays green

- **Given** the same planted tree, but the pushed sha's `qa-validate.yml` run carries a real job
- **When** the same sweep runs
- **Then** the process exits 0 and prints no unverified verdict
- **Test:** tests/test_pr_health.py::test_an_unverified_rebase_reds_the_sweep_and_a_verified_one_stays_green

#### Scenario: the decision seam reads only the recorded proof

- **Given** a list of rebaser outcomes mixing `ci_verified is False`, `ci_verified is True` and
  outcomes carrying no proof at all
- **When** `unverified_rebases()` runs
- **Then** exactly the `ci_verified is False` rows are returned
- **Test:** tests/test_pr_health.py::test_an_unverified_rebase_reds_the_sweep_and_a_verified_one_stays_green
