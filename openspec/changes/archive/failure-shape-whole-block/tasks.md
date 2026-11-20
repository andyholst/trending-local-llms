## Tasks — #1175: the failure shape digests the whole bounded block

### Seam

- [x] `failure_shape` digests every line of the block (`skeleton`, not `skeleton[:8]`)
- [x] The docstring states the boundary and why the prefix digest was wrong
- [x] The digest stays a 12-char sha1 over a block already capped at `MAX_ERROR_LINES`

### Tests

- [x] `test_failure_shape_groups_the_same_defect_and_separates_others` plants a same-prefix pair
      differing after the old 8-line window → two shapes; the same block → one shape
- [x] RED on the old seam: measured `226 passed, 2 failed` against `origin/master`'s script

### Rulebook (rule 3c — review-required)

- [x] `AGENTS.md` §8: the `tests/test_pipeline_failure_issue.py` row carries issue #1175
- [x] The rule-3c notice is posted on issue #1175 naming the section and why

### Verification

- [x] `make validate` green (`QA PASSED`)
- [x] `make lint` green (rc=0)
- [x] `make test` green (container `make _test`)
- [x] `make openspec-index` then `make openspec-check` green
- [x] `make architecture-check` green (after `make architecture-refresh`)

### Scope boundary

- No new make target, pipeline job or image (rule 6d).
- #1174 (unbounded log reads) and #1176 (the 24 h grace) are NOT covered — they stay open.
