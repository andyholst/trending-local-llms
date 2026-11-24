# pr-ready-review

## ADDED Requirements

### Requirement: A bound draft PR is named with its issue

The PR-health sweep SHALL classify an open DRAFT that carries a bound issue as a ready-for-review
stall and SHALL name the PR with that issue number. Binding SHALL be GitHub's
`closingIssuesReferences` first, falling back to the issue the head branch encodes. `findings`,
`rebase_plan` and `auto_merge_rebase.classify` SHALL keep their existing draft semantics.

#### Scenario: a draft with a GitHub-bound issue is named

- **Given** an open PR `isDraft: true`, head `fix/draft-with-issue`, whose
  `closingIssuesReferences` names issue #1563
- **When** the real verdict runs over that PR fixture (no network; a stub `gh`)
- **Then** `draft_findings` returns one row naming PR #9, its head and issue #1563, with a
  reason that says READY and never draft, and the sweep prints `DRAFT #9` and `#1563`
- **Test:** tests/test_pr_health.py::test_a_bound_draft_pr_is_named_with_its_issue

#### Scenario: the issue encoded in the branch binds too

- **Given** an open draft whose head is `fix/foo-42` with no `closingIssuesReferences`
- **When** the verdict runs
- **Then** issue #42 is named; a READY PR with a bound issue produces no draft verdict
- **Test:** tests/test_pr_health.py::test_a_bound_draft_pr_is_named_with_its_issue

### Requirement: the CI-side assertion fails only on a bound draft

`--draft-only` SHALL exit 1 when any open draft binds an issue and 0 otherwise, and the `--help`
SHALL document the ready-for-review rule. An unfinished draft binds no issue and SHALL NOT fail.

#### Scenario: the assertion gate

- **Given** a stub `gh` answering a bound draft, an unbound draft, and a ready PR in turn
- **When** `make pr-draft-check` / `python3 scripts/pr_health.py --draft-only` runs
- **Then** the bound draft exits 1 naming its issue, the unbound draft and the ready PR exit 0,
  and `--help` names both `--draft-only` and the ready-for-review rule
- **Test:** tests/test_pr_health.py::test_a_bound_draft_pr_fails_the_draft_only_assertion

#### Scenario: an unfinished draft is not a stall

- **Given** a draft whose branch is `fix/wip` and a refresh branch `ci/trending-refresh-20261124`
- **When** the verdict reads them
- **Then** neither binds an issue and neither is named
- **Test:** tests/test_pr_health.py::test_an_unbound_draft_is_not_a_stall

### Requirement: the rule is wired and stated in both lane contracts

The Makefile SHALL expose `make pr-draft-check` (REPO=), the existing dispatch-only
`pr-health.yml` sweep SHALL call it, no `schedule:` trigger SHALL be added, and both
`agents/tll-planner/skills/tll-planner/SKILL.md` and
`agents/tll-implementer/skills/tll-implementer/SKILL.md` SHALL say to open every PR READY
(never draft), reporting unfinished work on the issue instead of opening a PR.

#### Scenario: the wiring and the lane rules

- **Given** the real Makefile, workflow and both lane skill files on the PR head
- **When** the wiring guard reads them
- **Then** `pr-draft-check` calls the `--draft-only` seam, `pr-health.yml` runs it, the workflow
  still has no `schedule:`, and both skills carry the ready/never-draft rule
- **Test:** tests/test_pr_health.py::test_the_ready_rule_is_wired_to_the_makefile_and_workflow

#### Scenario: both lane skills state the rule

- **Given** the two lane skill files
- **When** the rule guard reads them
- **Then** each contains "Open every PR READY (never draft)" and the unfinished-work carve-out
- **Test:** tests/test_pr_health.py::test_the_lane_skills_say_open_every_pr_ready_never_draft
