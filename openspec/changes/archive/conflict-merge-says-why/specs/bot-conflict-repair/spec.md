# bot-conflict-repair

## ADDED Requirements

### Requirement: A failed base merge is classified, and never described with a placeholder

When the fix loop's base merge fails, it MUST report either the conflicting paths (and hand
them to a repair round) or, when git left no unmerged path, that the failure is NOT a
conflict, quoting git's own reason. It MUST NOT print a placeholder in place of the paths,
and it MUST leave the working tree untouched when there is nothing to repair.

#### Scenario: a merge that fails with no unmerged path

- **Given** a branch whose untracked file the base would overwrite
- **When** the loop merges the base before its first round
- **Then** it prints `REFUSED … NO unmerged path … git said: <reason>`, never `<unreadable>`,
  hands no conflict report to the round, and leaves the untracked file exactly as it was
- **Test:** tests/test_fix_loop.py::test_a_failed_merge_with_no_unmerged_path_says_what_git_said

#### Scenario: a real conflict is unchanged

- **Given** a base that moved onto the same line the branch edited
- **When** the loop merges the base
- **Then** it names the conflicted path, writes the hunks into the report, and aborts the
  merge if the round cannot resolve it (issue #475 behaviour, preserved)
- **Test:** tests/test_fix_loop.py::test_a_conflicting_base_merge_is_handed_to_a_round_and_aborted_if_hopeless
