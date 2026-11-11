# message-pattern-enforcement

## ADDED Requirements

### Requirement: The implementation PR body carries the message pattern

The implementation PR body produced by `scripts/pr_body.py::render` MUST contain
the five sections `## Why`, `## What`, `## How`, `## Benefits`,
`## Technical Solution` in that order, each with at least one non-blank,
non-header content line, and MUST still end with the single `Closes #<issue>`
line (rule 6e). The composer MUST expose a deterministic parser,
`section_problems(text)`, that a test and a CLI mode can run on any body file.

#### Scenario: the composed body follows the message pattern

- **Given** the composer asked for an implementation PR (issue + branch)
- **When** `render()` is called
- **Then** the body starts with `Implements #<n>`, contains the five `##` sections
  in order with non-empty content, and ends with `Closes #<n>`
- **And** `section_problems(body)` returns no problems
- **Test:** `tests/test_pr_message.py::test_the_composed_body_follows_the_message_pattern`

#### Scenario: the parser refuses a body that skips or empties a section

- **Given** a body missing one of the five sections, or carrying one with only a
  header line, or listing them out of order
- **When** `section_problems(text)` runs
- **Then** it reports every missing / empty / out-of-order section by name
- **Test:** `tests/test_pr_message.py::test_a_body_that_skips_a_section_is_refused`

### Requirement: CI validates the PR body message pattern

The `pr-closure.yml` pipeline MUST gate the PR body on the message pattern on
`opened`, `edited`, `synchronize` and `reopened` — the same artifact-reads-the-
artifact model as the closure check (issue #290) — by running `make pr-message-check`
against the webhook payload. A body that the composer's own parser refuses MUST
fail the check.

#### Scenario: the closure job refuses a non-conforming body

- **Given** a PR `opened`/`edited` event whose body lacks a required section
- **When** `make pr-message-check` runs against the webhook payload
- **Then** it exits non-zero and names the missing section on stderr
- **And** the workflow step that runs it fails, blocking auto-merge
- **Test:** `tests/test_pr_message.py::test_bodies_are_refused_by_name`

### Requirement: the squash commit message follows the pattern by construction

The message a squash merge commits MUST match the message pattern without a
separate gate: the title comes from `pr_body.title()` and the body from the
validated PR body. A test MUST prove `title()` is a Conventional-Commit and names
the issue.

#### Scenario: the squash title is a Conventional-Commit naming the issue

- **Given** an issue of kind `data-gap` and one of kind `tech-debt`
- **When** `pr_body.title()` is called for each
- **Then** each result matches `<type>(<scope>): implement #<n> …` with
  `type(scope)` from the issue's kind, and names `#<n>`
- **Test:** `tests/test_pr_message.py::test_the_squash_title_is_a_conventional_commit`

### Requirement: CI validates the squash commit message on push

A push to `master` is a SQUASH MERGE, so `pr-closure.yml` MUST run
`make commit-message-check` on the event's `head_commit.message` (the squash body). The
implemented issue is read from the message's own `#<n>` — `refs/heads/master` encodes no
issue — so a commit that the composer's own parser refuses MUST fail the check.

#### Scenario: a commit message that skips a section is refused on push

- **Given** a push-to-master event whose head commit message lacks one of the five `##` sections
- **When** `commit-message-check` runs on `.head_commit.message`
- **Then** it exits non-zero and names the missing section
- **And** the workflow step fails, so the merge is not treated as conforming
- **Test:** `tests/test_pr_message.py::test_commit_cli_refuses_a_non_conforming_message`

### Requirement: a declared message-pattern issue body is validated

An issue that carries the invisible `<!-- issues-message-pattern -->` marker MUST have the
five `##` sections in order and with content. `pr-closure.yml` MUST run
`make issue-message-check` on `issues:opened/edited/reopened`, so a DECLARED message-pattern
issue that skips, empties or misorders a section is refused. A structured data-gap/tech-debt
issue (own schema, no marker) is NOT forced through the shape and stays green.

#### Scenario: a declared issue that skips a section is refused

- **Given** an issue event whose body carries the pattern marker but lacks one `##` section
- **When** `issue-message-check` reads the issue body from the payload
- **Then** it exits non-zero and names the missing section
- **And** a legacy data-gap issue with no marker passes
- **Also** an issue that carries the marker and follows the pattern passes
- **Test:** `tests/test_pr_message.py::test_declared_issue_is_validated_and_legacy_passes`
