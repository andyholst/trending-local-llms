# squash-identity-legacy-history

## ADDED Requirements

### Requirement: GitHub-synthesized squash identities on git history are LEGACY, never gate failures

The squash GitHub performs with the owner's merge token writes the ACCOUNT display
name onto the merged commit — `Mr. Asimov <support@docondee.com>` — the second
spelling `agent_identity.PEOPLE` refuses. Rule 3 forbids rewriting those merged
commits, so a gate that reads them must classify them as legacy history. The
classification is by SHAPE (author = the account display name on the agent email,
committer = an automation identity or the same account shape), never by a
hand-kept SHA list. The gate's domain stays the commits a PR adds:
`DEFAULT_RANGE` remains `origin/master..HEAD`.

#### Scenario: a stale base ref pulls merged squashes into the range — the gate stays green and says why

- **Given** a real repo whose `origin/master` ref is stale, so HEAD carries a commit authored `Mr. Asimov <support@docondee.com>`, committed `GitHub <noreply@github.com>`, with a synthesized `Co-authored-by: Asimov Agent <support@docondee.com>` trailer
- **When** `make check-commit-authorship` runs on the default range
- **Then** the gate exits 0 and reports that commit as `legacy` merged history
- **Test:** tests/test_commit_authorship.py::test_a_github_squash_identity_in_the_range_is_legacy_history_not_a_violation

#### Scenario: a feature-branch commit that spells itself Mr. Asimov while committed as the agent is still refused

- **Given** a real repo whose HEAD carries a commit authored `Mr. Asimov <support@docondee.com>` and committed `Asimov Agent <support@docondee.com>` (a misconfigured `git config`, not a GitHub-completed shape)
- **When** `make check-commit-authorship` runs on the default range
- **Then** the gate exits 1 naming the canonical identity
- **Test:** tests/test_commit_authorship.py::test_a_feature_commit_spelled_mr_asimov_committed_as_the_agent_is_refused

#### Scenario: the identity seam refuses the account name — no job may configure it

- **Given** `check --identity "Mr. Asimov <support@docondee.com>"`
- **When** the guard runs
- **Then** it exits 1 (the legacy classification applies only to git commits GitHub completed)
- **Test:** tests/test_commit_authorship.py::test_the_identity_seam_still_refuses_the_account_name

### Requirement: AGENTS.md §3f states the synthesized-identity contract

The rulebook names the account identity, bounds the guard's domain to new commits,
and refuses reading master's merged history as new work — so a reviewer can tell a
live violation from synthesized history.

#### Scenario: the rulebook names the account identity and the bounded range

- **Given** `AGENTS.md` §3f on this tree
- **When** `tests/test_commit_authorship.py` reads it
- **Then** it names `Mr. Asimov <support@docondee.com>` as the GitHub-synthesized squash identity, calls merged squashes `legacy`, and bounds the guard to `origin/master..HEAD`
- **Test:** tests/test_commit_authorship.py::test_agents_md_states_the_squash_identity_contract
