# fixbot-before-checkout

## ADDED Requirements

### Requirement: A job that calls `gh` before its checkout names the repo

A workflow job that invokes a `gh` subcommand whose owner/repo is resolved
**implicitly** (`pr`, `issue`, `run`, `release`, `workflow`, `label`, `search`)
MUST provide the repository explicitly when that call can run before the first
`actions/checkout` — via `GH_REPO` in the job or step `env`, or with `--repo` /
`-R` on the command. A command that names the repo in its own path
(`gh api repos/$REPO/…`) needs nothing. Without this, `gh` has no git remote to
read and exits with `fatal: not a git repository`, failing the job at that step
and skipping everything after it.

WHEN a workflow job writes to a PR or issue before checking the repository out,
THEN the job names the repo so the call can resolve.

#### Scenario: fix-bot announces its window before the checkout

- **Given** the `fix` job, whose "Announce the window on the PR" step runs before `actions/checkout`
- **When** the job env is read
- **Then** it declares `GH_REPO: ${{ github.repository }}`, so `gh pr comment` resolves the PR
- **Test:** `tests/test_workflows.py::test_gh_before_the_checkout_names_the_repo`

#### Scenario: no other job calls gh implicitly without a repo

- **Given** every workflow under `.github/workflows/`
- **When** each job's steps before its checkout (or all steps, when it has none) are scanned for an implicit `gh` subcommand
- **Then** none lacks `GH_REPO` or a `--repo`/`-R` argument, and a repo-naming `gh api repos/…` is not counted
- **Test:** `tests/test_workflows.py::test_gh_before_the_checkout_names_the_repo`

#### Scenario: the guard fails on the pre-change workflow

- **Given** `fix-bot.yml` as it was before this change (no `GH_REPO` in the `fix` job)
- **When** the guard runs against it
- **Then** it reports the announce step as an offender and fails, so the guard proves the defect rather than describing it
- **Test:** `tests/test_workflows.py::test_gh_before_the_checkout_names_the_repo`
