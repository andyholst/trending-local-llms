# worktree-base

## ADDED Requirements

### Requirement: The two git reads are named, and the difference is proved

`worktree_base` MUST expose `git_out` (stdout stripped, for a value) and `git_raw` (stdout exactly
as git wrote it, for a record), and MUST document the difference where `git_out` is defined, so a
porcelain/`-z` parser cannot be built on a lossy read.

#### Scenario: a porcelain line keeps its leading status byte

- **Given** a repository with a modified tracked file
- **When** `git status --porcelain` is read through `git_raw`
- **Then** the line starts with `" M "` (the status field's leading space is data)
- **Test:** tests/test_worktree_base.py::test_git_out_strips_and_git_raw_does_not

#### Scenario: the stripped read mangles the first path (the measured defect)

- **Given** the same repository
- **When** a naïve `line[3:]` porcelain parser reads the output of `git_out`
- **Then** the first path loses its first character, which is why the guard exists
- **Test:** tests/test_worktree_base.py::test_git_out_strips_and_git_raw_does_not

#### Scenario: `-z` records keep their NUL separators

- **Given** a repository with a change
- **When** `git status --porcelain -z` is read through `git_raw`
- **Then** the output still contains NUL separators
- **Test:** tests/test_worktree_base.py::test_git_out_strips_and_git_raw_does_not
