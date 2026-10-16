# commit-authorship

## ADDED Requirements

### Requirement: every committing bot job commits as the repo's own agent

Every workflow job whose `run:` reaches `git commit` MUST configure the repo's own
agent identity — `git config user.name "Asimov Agent"` and
`git config user.email "support@docondee.com"` — before committing, and MUST NOT
commit as `github-actions[bot]`. The repo's only identities are **Andy Holst** and
**Asimov Agent** (the rule the commit-authorship guard enforces); the pipeline that
produces most of the commits must not contradict it, because a commit's identity is
what `git log`, `git blame` and the guard read, and what GitHub turns into a squash
`Co-authored-by:` trailer.

WHEN a workflow job commits,
THEN it sets `user.name`/`user.email` to the agent identity and names no other.

#### Scenario: every committing job is found and pinned

- **Given** every `.github/workflows/*.yml`, every job and every step whose `run:` contains `git commit`,
- **When** the identity guard walks them,
- **Then** the set SHALL be non-empty, and each entry SHALL set `user.name "Asimov Agent"` and `user.email "support@docondee.com"` and SHALL NOT contain `github-actions`.

- **Test:** `tests/test_workflows.py::test_every_committing_bot_job_commits_as_the_agent`

#### Scenario: fix-bot's own push commits as the agent

- **Given** a green loop on PR `fix-bot.yml`'s `fix` job,
- **When** its `Commit + push the fix` step runs,
- **Then** it SHALL commit as `Asimov Agent <support@docondee.com>`.

- **Test:** `tests/test_workflows.py::test_fix_bot`

#### Scenario: the four sites are the ones that commit

- **Given** the measured state of `origin/master` (`ff98119`),
- **When** the guard walks the committing steps,
- **Then** it SHALL name `fix-bot.yml` (1 step), `issue-bot.yml` (2 steps) and `refresh-bot.yml` (1 step) — the four `git config` sites of issue #323.

- **Test:** `tests/test_workflows.py::test_every_committing_bot_job_commits_as_the_agent`

### Requirement: the agent's own address is an allowed identity

`scripts/check_commit_authorship.py` SHALL list `support@docondee.com` in
`ALLOWED_EMAILS`, so the identity every committing bot job uses is allowed by its
**email** as well as by its name — an allowlist that accepts the address only
because the name matches does not state the rule.

WHEN the guard judges `Asimov Agent <support@docondee.com>`,
THEN it is an allowed identity, by name and by email.

#### Scenario: the agent's identity is allowed by itself

- **Given** a commit authored and committed `Asimov Agent <support@docondee.com>`,
- **When** the guard scans it,
- **Then** it SHALL report no violation, and `support@docondee.com` SHALL be in `ALLOWED_EMAILS`.

- **Test:** `tests/test_commit_authorship.py::test_the_agents_own_identity_is_allowed`

#### Scenario: the generic bot account is still tolerated for history

- **Given** a commit authored `github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>` and committed `GitHub <noreply@github.com>`,
- **When** the guard scans it,
- **Then** it SHALL report no violation — the guard gates NEW commits, and the measured history is not rewritten.

- **Test:** `tests/test_commit_authorship.py::test_the_repos_own_bot_identity_is_not_a_violation`
