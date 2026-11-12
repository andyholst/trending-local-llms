# pr-lifecycle

## ADDED Requirements

### Requirement: A keeper branch references its issue, it does not implement it

A PR that records or unblocks drift observed during a run (an archive move, an index or
architecture regeneration, a ledger append) is a KEEPER, not an implementation. Its branch
MUST use the declared keeper shape `ci/keeper-<slug>` or `ci/keeper-<slug>-<issue>` —
`keeper` as the first slug segment — and the closure rule MUST read its trailing number as
a REFERENCE: `implemented_issue()` returns none for it, so the PR passes with zero closing
keywords and a `Closes #N` written on it is refused as a false claim. Any other branch
keeps the existing convention unchanged: a branch whose name encodes issue N MUST bind
`Closes #N`. (Rule 6d: the shape lives in ONE parser, `scripts/pr_closure.py`.)

WHEN a keeper branch named after a still-open issue is validated with no closing keyword,
THEN the check exits 0; WHEN the same branch carries `Closes #N`, THEN it exits 1 naming the
false claim.

#### Scenario: the planted #872 collision passes

- **Given** branch `ci/keeper-archive-stranded-cadence-wording-866` and a body that says
  `refs #866` and closes nothing — the shape PR #867 needed but could not write
- **When** the closure check runs
- **Then** it exits 0, and the report says the PR closes no issue
- **Test:** `tests/test_pr_closure.py::test_keeper_branch_naming_an_open_issue_passes_with_zero_closing_claims`

#### Scenario: a keeper may not fake an implementation

- **Given** the same keeper branch whose body carries `Closes #866`
- **When** the closure check runs
- **Then** it exits 1 — a PR that implements no issue must not close one
- **Test:** `tests/test_pr_closure.py::test_keeper_branch_must_not_claim_a_close`

#### Scenario: the old collision shape and the implementer shape are unchanged

- **Given** the measured PR #867 branch `ci/archive-stranded-cadence-wording-866` (no keeper
  token) with no closing keyword, and an implementer branch `ci/data-gap-854-x` with none
- **When** the closure check runs on each
- **Then** both exit 1: the first still implements #866, the second still must bind `Closes #854`
- **Test:** `tests/test_pr_closure.py::test_a_non_keeper_branch_still_implements_its_trailing_issue`
