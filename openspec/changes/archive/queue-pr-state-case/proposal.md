# Proposal: queue-pr-state-case

Issue: #1318
PR: #1319

## Why

`scripts/issue_queue.py` decides whether a PR is open with
`pull.get("state") == "open"`, but `gh pr list --json state` answers GitHub's API
spelling **`OPEN`**. Byte-checked on `origin/master` `9250657`: `repr(pull['state'])` is
`'OPEN'`, `== "open"` is `False`, `.lower() == "open"` is `True`. So the PR half of
`has_implementer` never fired — only `bool(branch)` ever did — and the #1310 fix that
marks an issue implemented from a `fix/`-prefixed closing PR is **inert in production**:
`make issue-queue` still prints `issue=1176 position=2 has_implementer=0 …
reason=next-sweep` while open PR #1289 carries `closes #1176`.

## What Changes

- `scripts/issue_queue.py` compares the PR state case-insensitively in ONE helper used by
  both the branch path and the closing-PR path, so the pre-existing dead comparison is
  repaired too (rule 6d: one implementation of the state test).
- `tests/test_issue_review.py` plants a payload with gh's real `OPEN` spelling, so a
  lowercase-only fixture can never make the guard pass again.

## Impact

One script, one test module. No workflow, target, data or contract change. The shared
queue stops re-offering work that already has an open PR.

## Not covered

- Other readers of `gh pr list --json state` elsewhere in the tree (each is its own
  finding; `make pr-health`/`ghost-run-alarm` are checked separately).
- The wider `pr list` payload noted in #1316.
