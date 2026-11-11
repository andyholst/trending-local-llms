## ADDED Requirement: The outcome dedup reads the WHOLE comment thread

`make issue-outcome`'s decision whether THIS run already spoke on the issue MUST be taken on
the complete thread, not its first 100 comments. GitHub returns comments oldest-first, so a
reader without `--paginate` cannot see the newest comments — including the outcome marker the
same run may have written minutes earlier on a busy issue — and would post a second comment for
the same run id. `_comments()` MUST use `gh api … --paginate --jq .[]` (the shape
`scripts/issue_thread.py` uses) and parse one JSON object per line; a read that fails stays loud
(`GhError`, exit 2 through the CLI), never an empty list.

#### Scenario: the marker sits past the first page

- **Given** an issue whose thread has more than 100 comments and whose LAST comment carries the
  `<!-- issue-bot-outcome: … run=<id> -->` marker of the current run
- **When** `scripts/sweep_outcome.py --post --run-id <id>` runs a second time for that run
- **Then** it writes NO comment (the dedup saw the marker) and exits 0
- **Test:** tests/test_sweep_outcome.py::test_a_long_thread_is_read_whole_for_the_dedupe

#### Scenario: the read is a paginated call

- **Given** the same busy issue
- **When** the tool reads its comments through the stubbed `gh`
- **Then** the recorded `gh api` call carries `--paginate` and no `per_page=100` truncation
- **Test:** tests/test_sweep_outcome.py::test_the_comment_read_is_paginated

#### Scenario: a failed comment read is loud

- **Given** a `gh` that answers the comments read with an HTTP error
- **When** the tool decides whether to comment
- **Then** it fails loudly (non-zero, naming the read it could not make) rather than deciding
  from an empty thread
- **Test:** tests/test_sweep_outcome.py::test_a_missing_or_unreadable_issue_is_loud
