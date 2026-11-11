## Why

`make issue-outcome` promises ONE outcome comment per run on the issue it picked. Its dedup
`already_said()` reads issue comments through `_comments()`, which asks GitHub for
`?per_page=100` with NO `--paginate`. GitHub returns comments **oldest-first**, so on any issue
with more than 100 comments the newest ones — including the `<!-- issue-bot-outcome: … run=<id>
-->` marker written minutes earlier by the same run — are never seen, and `--post` writes a
SECOND comment. The queue items this tool exists to annotate (runs 39750538181,
40194644167) are exactly the busy threads where it bites. Filed as tech-debt #662 with the
sibling `scripts/issue_thread.py` (which paginates) as the contrast.

## What

`scripts/sweep_outcome.py::_comments()` now reads the WHOLE thread with
`gh api … --paginate --jq .[]` — the shape `scripts/issue_thread.py` already uses — parsed one
JSON object per line, a failed read still loud (`GhError`). `tests/test_sweep_outcome.py` gains
`test_a_long_thread_is_read_whole_for_the_dedupe`: a 150-comment thread whose LAST comment is
this run's marker, driven through the real script against the stub `gh` (which now simulates the
oldest-first 100-comment first page when `--paginate` is absent), asserting the second `--post`
writes nothing and the recorded call carries `--paginate` with no `per_page=100`.

## How

One function rewritten in place; the OpenSpec change
`openspec/changes/sweep-comments-read-whole-thread/` carries the spec delta (three scenarios,
each pinned to a test) and the task list. The AGENTS.md §8 guard row is extended in the same
branch (rule 6c).

## Benefits

- The one-comment-per-run contract now holds on busy issues, not just small threads.
- The guard was verified RED on the old script (3 failing checks: double-post, missing
  `--paginate`, `per_page=100` truncation) and GREEN on the new one (42/42).
- Both bot thread readers now share one pagination shape, so a future reader copy-pastes the
  correct one.

## Technical Solution

`_comments()` calls `gh api repos/<repo>/issues/<n>/comments --paginate --jq .[]`, iterates the
JSONL answer into `[{createdAt, body}]`, and raises `GhError` on an unparseable line — the CLI
maps that to exit 2. The test stub answers `/comments` as JSONL when `--paginate` is present and
as the first 100 comments otherwise, so it reproduces GitHub's real page behavior; the recorded
`calls.log` proves the tool asks for every page.

closes #662
