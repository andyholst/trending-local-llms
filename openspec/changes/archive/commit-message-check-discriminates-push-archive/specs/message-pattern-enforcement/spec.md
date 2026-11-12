# message-pattern-enforcement

## ADDED Requirements

### Requirement: The push-side commit gate discriminates an implementation CLAIM, not a reference

A squash commit on `master` implements an issue only when its message **claims** one: an
implementing verb written directly on a reference (`implement #635`, `implements #635`), or
a closing keyword binding (`Closes #635`). A number that merely APPEARS in the message — an
archive title naming the merged PRs it archives, a `Refs` line, prose about another issue —
is not a claim. The five-section and closes-binding demands of `make commit-message-check`
apply to a claiming commit; a non-claiming commit (an `chore(openspec): archive …` commit,
a refresh squash) is checked only for well-formed closing references and must not be forced
to carry sections or a `Closes` keyword. The discriminator has exactly ONE implementation,
in `scripts/pr_closure.py` (rule 6d), reached through `make commit-message-check`.

#### Scenario: an archive commit that names merged PRs is not forced to be an implementation

- **Given** the exact squash message of the archive commit `8965a45` —
  `chore(openspec): archive the merged log-tail-honored and per-round-log-capture changes #845/#846 left active (#851)`
- **When** `make commit-message-check` runs on it
- **Then** it exits 0: no `##` section is demanded and no closing keyword is invented
- **Test:** `tests/test_pr_message.py::test_the_commit_gate_discriminates_an_archive_squash`

#### Scenario: a commit that claims an implementation is still held to the pattern

- **Given** a squash message whose title says `fix(tech-debt): implement #635 …` but which
  skips the five `##` sections (or whose `Closes` claim binds a different number)
- **When** `make commit-message-check` runs on it
- **Then** it exits non-zero and names the missing section or the mismatched binding
- **Test:** `tests/test_pr_message.py::test_the_commit_gate_discriminates_an_archive_squash`

#### Scenario: the discriminator lives in pr_closure and pr_body delegates to it

- **Given** `scripts/pr_body.py`'s commit-side issue derivation
- **When** the tree is scanned for the commit-claim pattern
- **Then** the pattern exists only in `scripts/pr_closure.py`, and `_commit_issue` returns
  `pr_closure.implemented_issue_from_message(...)` — no second copy (rule 6d)
- **Test:** `tests/test_pr_message.py::test_the_commit_claim_parser_lives_in_pr_closure`
