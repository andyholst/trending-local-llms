## ADDED Requirements

### Requirement: The agent login is bot-owned even when `is_bot` is false

`is_bot_owned` SHALL treat a PR whose author login is in `scripts/agent_identity.py`'s `AGENT_LOGINS` as bot-owned even when `author.is_bot` is `false`, because the agent login is a GitHub **User** and every real agent PR answers `is_bot: false` on this repository. `author.is_bot: true` SHALL remain sufficient.

#### Scenario: A real agent PR with the live `is_bot` spelling

- **Given** a PR whose author is `{"login": "asimov-agent", "is_bot": false}` — the live queue's shape
- **When** `is_bot_owned` / `rebase_plan` classifies it
- **Then** it is bot-owned, so a behind-and-clean one is `rebase-if-behind`
- **Test:** tests/test_pr_health.py::test_agent_login_is_bot_owned_when_is_bot_is_false

#### Scenario: A `is_bot: true` author is still sufficient

- **Given** a PR whose author is `{"login": "someone", "is_bot": true}`
- **When** `is_bot_owned` classifies it
- **Then** it is bot-owned without any login check
- **Test:** tests/test_pr_health.py::test_agent_login_is_bot_owned_when_is_bot_is_false

### Requirement: A human author is never rewritten, whatever the branch is called

A PR authored by a login outside `AGENT_LOGINS` SHALL stay report-only (`human-branch`), including a `ci/…` branch, and a CONFLICTING bot PR SHALL still never be auto-rebased. When a caller passes no author data at all, the branch-prefix fallback SHALL keep its meaning.

#### Scenario: A human `ci/…` branch is reported, not rewritten

- **Given** a PR whose author is `{"login": "andyholst", "is_bot": false}` on a `ci/…` branch
- **When** `rebase_plan` classifies it
- **Then** the action is `human-branch`
- **Test:** tests/test_pr_health.py::test_agent_login_is_bot_owned_when_is_bot_is_false

#### Scenario: No author data falls back to the prefix

- **Given** a PR object with no `author` field, on `ci/data-gap-1-x` and on `fix/no-author-data`
- **When** `is_bot_owned` classifies them
- **Then** the `ci/` branch is bot-owned and the `fix/` branch is not
- **Test:** tests/test_pr_health.py::test_agent_login_is_bot_owned_when_is_bot_is_false

#### Scenario: The fixture carries the live external spelling

- **Given** the ownership fixture in the test module
- **When** the guard runs
- **Then** the agent fixture's `is_bot` is `False`, the spelling the live GitHub API serves
- **Test:** tests/test_pr_health.py::test_ownership_is_decided_by_author_not_branch_prefix
