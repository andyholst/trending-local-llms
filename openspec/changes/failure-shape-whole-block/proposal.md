# failure-shape-whole-block — the shape digest covers the whole bounded block

Issue: #1175

## Why

`failure_shape` built its digest from `skeleton[:8]` — the first eight error-shaped lines. Two
unrelated failures that share GitHub's boilerplate (`##[error]…`, `make: *** [<target>] Error 1`,
a traceback header) and differ only later hashed the SAME, so the PR-blockage pass recorded one
blockage for two defects and the `PR_BLOCK_MIN_PRS` threshold could be met by two PRs blocked by
different things — the exact error the pass exists to avoid.

## What Changes

- `scripts/pipeline_failure_issue.py::failure_shape` digests the WHOLE bounded block. `block`
  arrives from `extract_error_block`, already capped at `MAX_ERROR_LINES` (40), so the cap bounds
  the digest's input; the digest stays a 12-char sha1.
- The docstring states the boundary and why the prefix digest was wrong.
- `tests/test_pipeline_failure_issue.py::test_failure_shape_groups_the_same_defect_and_separates_others`
  plants two blocks identical inside the old 8-line window and differing after it: different
  shapes now, one shape for the same block, and the pre-change collision is named.
- `AGENTS.md` §8: the `tests/test_pipeline_failure_issue.py` row carries issue #1175.

## Impact

- No new make target, pipeline job or image; `failure_shape` is already reached from
  `make test` (rule 6d).
- Not covered: #1174 (the pass reads a log for every failing job of every blocked PR with no call
  budget) and #1176 (the 24 h grace is a guess) — both named by the same PR, both still open.
