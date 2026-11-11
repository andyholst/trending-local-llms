# Proposal: sweep-comments-read-whole-thread

**Issue:** [#662](https://github.com/andyholst/trending-local-llms/issues/662)
**Capability:** `issue-bot-artifacts`

## Why

`scripts/sweep_outcome.py::_comments()` calls
`gh api "repos/<repo>/issues/<n>/comments?per_page=100"` with NO `--paginate`, while the
sibling reader `scripts/issue_thread.py` paginates its thread. GitHub returns issue comments
**oldest-first**, so on an issue with more than 100 comments the NEWEST ones — including the
`<!-- issue-bot-outcome: … run=<id> -->` marker written minutes earlier by the same run — are
never returned. `already_said()` then answers None and `--post` writes a SECOND outcome comment
for the same run, spamming exactly the busy queue items this tool exists to annotate. The dedup
contract ("one comment per run") rests on reading the thread, and its test fixture was a
one-comment list.

## What Changes

- `_comments()` reads the WHOLE thread: `--paginate` + `--jq .[]` (the shape
  `scripts/issue_thread.py` uses), parsed as one JSON object per line into the same
  `[{createdAt, body}]` list `already_said()` consumes; a failed read stays loud (`GhError`).
- A new guard in `tests/test_sweep_outcome.py` drives a **>100-comment thread through the real
  script** against the stub `gh`: the outcome marker sits in the LAST comment, and a second
  `--post` for the same run id writes NOTHING; the recorded `gh` call carries `--paginate`.

## Impact

- `scripts/sweep_outcome.py` (the `--post` path the `issue-bot.yml` outcome step runs)
- `tests/test_sweep_outcome.py`
- capability spec `issue-bot-artifacts`

## Not covered

- Pagination of OTHER readers (they already paginate, or their threads are bounded by design).
- Issue #767 (the amd64-only OpenSpec image) — unrelated pipeline plumbing, tracked separately.
