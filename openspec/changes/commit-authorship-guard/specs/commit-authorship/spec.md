# commit-authorship

## ADDED Requirements

### Requirement: Only Andy Holst and Asimov Agent may author, commit or co-author

`scripts/check_commit_authorship.py` MUST fail closed when, over a range, either

1. a commit's **author or committer** identity is not an allowed one, or
2. a commit **message** carries a crediting trailer (`Co-authored-by`,
   `Signed-off-by`, `Reviewed-by`, `Tested-by`, `Acked-by`, `Helped-by`) whose
   name is not an allowed one.

It MUST report each violation with the commit, the role (author/committer) or
the trailer, and the commit subject, and exit non-zero. Allowed identities are
**Andy Holst** / `andyholst` and **Asimov Agent** / `asimov` / `asimov-agent`,
plus the repository's OWN automation identities — `github-actions[bot]` (the
`git config` in refresh-bot, fix-bot and issue-bot) and `GitHub
<noreply@github.com>` (the committer GitHub uses for a squash) — because
refusing those would redden every bot PR. Every other identity is refused and
`Hermes Agent` is named explicitly in the failure.

WHEN a commit in the range is authored, committed or co-authored by an identity
that is not an allowed one,
THEN `make check-commit-authorship` reports the commit and exits non-zero.

#### Scenario: a disallowed AUTHOR with a trailer-less message is a violation

- **Given** a commit authored `Hermes Agent <hermes@nousresearch.com>` with a message that carries NO trailer (the measured shape of `054b0c8`)
- **When** the guard scans it
- **Then** it reports the author identity and exits non-zero
- **Test:** `tests/test_commit_authorship.py::test_a_wrong_author_identity_with_a_clean_message_is_a_violation`

#### Scenario: a disallowed COMMITTER is a violation

- **Given** a commit committed by an identity that is not allowed
- **When** the guard scans it
- **Then** it reports the committer identity and exits non-zero
- **Test:** `tests/test_commit_authorship.py::test_a_wrong_committer_identity_is_a_violation`

#### Scenario: the measured `hermes@nousresearch.com` trailer is a violation

- **Given** a commit whose message ends `Co-authored-by: Hermes Agent <hermes@nousresearch.com>`
- **When** the guard scans it
- **Then** it reports the trailer and exits non-zero
- **Test:** `tests/test_commit_authorship.py::test_the_hermes_co_author_trailer_is_a_violation`

#### Scenario: every crediting trailer keyword is checked

- **Given** a commit message whose trailer is `Signed-off-by`, `Reviewed-by`, `Tested-by`, `Acked-by` or `Helped-by` naming a disallowed identity
- **When** the guard scans it
- **Then** it reports a violation for each
- **Test:** `tests/test_commit_authorship.py::test_every_trailer_keyword_is_checked_not_only_co_authored_by`

#### Scenario: an allowed identity passes

- **Given** a commit authored and committed by Andy Holst with an allowed co-author trailer
- **When** the guard scans it
- **Then** it reports no violation and exits 0
- **Test:** `tests/test_commit_authorship.py::test_an_allowed_identity_is_not_a_violation`, `tests/test_commit_authorship.py::test_an_allowed_co_author_trailer_is_not_a_violation`

#### Scenario: the repository's own automation identity passes

- **Given** a commit authored `github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>` and committed `GitHub <noreply@github.com>`
- **When** the guard scans it
- **Then** it reports no violation, because every refresh/fix/issue-bot PR carries that identity
- **Test:** `tests/test_commit_authorship.py::test_the_repos_own_bot_identity_is_not_a_violation`

### Requirement: The range must be readable, or the guard fails loudly

The guard MUST read the commits of a range (default `origin/master..HEAD` — the
commits a PR adds, so history is never rewritten). WHEN the range cannot be
resolved — a shallow clone, a missing base ref — THEN the guard MUST exit
non-zero with git's own error and a hint, and MUST NOT degrade to "no commits,
pass". The `qa-validate` `validate` job's checkout MUST use `fetch-depth: 0` so
the default range resolves in CI. An EMPTY range (the tip equals the base) is
legitimately zero commits and passes.

#### Scenario: an unreadable range fails loudly

- **Given** a range git cannot resolve
- **When** the guard runs
- **Then** it exits 2 with a loud failure, not 0
- **Test:** `tests/test_commit_authorship.py::test_an_unreadable_range_fails_loudly_not_silently`, `tests/test_commit_authorship.py::test_a_missing_base_ref_fails_loudly`

#### Scenario: an empty range is not a violation

- **Given** a repository whose HEAD equals its base
- **When** the guard runs over the default range
- **Then** it exits 0, because there is nothing new to gate
- **Test:** `tests/test_commit_authorship.py::test_an_empty_range_is_not_a_violation`

### Requirement: The guard is a CI gate, and this repo cannot violate its own rule

`make check-commit-authorship` MUST be a step of `qa-validate`'s `validate` job,
and `tests/test_commit_authorship.py` MUST run under `make test` — a gate no
pipeline executes is a defect (rule 6d). The guard MUST also pass over THIS
repository's own commits, because a rule the repo itself violates is not a rule.

WHEN a PR is opened,
THEN `qa-validate`'s `validate` job runs `make check-commit-authorship` and the
guard's own test file runs under `make test`.

#### Scenario: the gate is on every PR

- **Given** the PR pipeline definition and the Makefile
- **When** their wiring is read
- **Then** the `validate` job runs `make check-commit-authorship` with `fetch-depth: 0`, and `make test` runs `tests/test_commit_authorship.py`
- **Test:** `tests/test_commit_authorship.py::test_the_guard_is_wired_into_the_repo`

#### Scenario: a rule the repo violates is red

- **Given** the guard run over this repository's own commits
- **When** any commit violates a rule
- **Then** the run is non-zero
- **Test:** `tests/test_commit_authorship.py::test_this_repository_never_credits_a_disallowed_identity`
