# architecture-bot-write-path

## ADDED Requirements

### Requirement: The shipped write path is executed, not described

The bot's drift → commit → push → PR steps MUST be exercised as they ship: the test
reads each step's `run:` body out of `.github/workflows/architecture-bot.yml` and
executes it in a real git repository with a real local remote, the repository's own
identity seam and a stub `gh` standing in only for the network. A clean tree MUST
produce `changed=false`, no branch and no `gh` call; a drifted tree MUST produce
`changed=true`, exactly one `ci/architecture-<UTC>Z` branch, a commit by the
repository's canonical identity, and a PR body with no closing keyword.

#### Scenario: a clean tree is a green no-op

- **Given** a fixture repo whose `ARCHITECTURE.md` is unmodified
- **When** the shipped `id: drift` step runs with a real `$GITHUB_OUTPUT`
- **Then** the file holds exactly `changed=false`, the remote gains no branch, and the stub `gh` is never invoked
- **Test:** `tests/test_architecture_bot.py::test_the_shipped_steps_actually_commit_push_and_open_a_pr`

#### Scenario: a drifted tree commits, pushes and opens a PR that claims nothing

- **Given** the same repo with `ARCHITECTURE.md` modified, and `changed=true` from the drift step
- **When** the shipped commit/push/PR step runs
- **Then** the remote holds one branch matching `ci/architecture-\d{8}T\d{6}Z`, the commit's author is `Asimov Agent <support@docondee.com>`, `gh` received `pr create --base master --head <branch> --body-file -`, and the body carries the run URL and no closing keyword
- **Test:** `tests/test_architecture_bot.py::test_the_shipped_steps_actually_commit_push_and_open_a_pr`

### Requirement: The branch name is judged by the guard that would refuse it

The test MUST ask `scripts/pr_closure.py`'s own branch regexes whether the pushed
branch encodes an issue, rather than keeping a second copy of that rule, so a
branch name that would make `pr-closure` demand a closing keyword fails the suite.

#### Scenario: a stamp that reads as an issue reference fails

- **Given** the dropped `Z` form `ci/architecture-20261021T005128`
- **When** the shipped step is executed and `pr_closure`'s regexes are applied
- **Then** the shape check fails and no issue is read from a conforming `…Z` branch
- **Test:** `tests/test_architecture_bot.py::test_the_shipped_steps_actually_commit_push_and_open_a_pr`
