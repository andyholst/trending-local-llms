# Proposal: reviewer-label-from-queue

Issue: #661 (measured: `scripts/issue_review.py:100`, `scripts/issue_queue.py:91`,
`scripts/data_gap_analysis.py:63`)

## Why

The reviewer's default label is a THIRD copy of a shared literal.
`issue_queue.QUEUE_LABELS` is the one queue definition (rule 6j/6d: "the label set is
ONE list, not one per bot"), yet the reviewer's own pick calls
`iq.build(repo, "data-gap-analysis", …)` with a bare string, and the gap filer keeps
its own `LABEL = "data-gap-analysis"`. `grep -rn '"data-gap-analysis"' scripts/*.py`
returns three definitions. A reader that re-spells a shared literal drifts SILENTLY:
if the queue's first label is ever renamed, `issue-bot`'s sweep follows the rename and
the reviewer keeps refining issues under the OLD name — the two bots stop sharing the
queue with no error anywhere, the exact failure mode the marker-registry rule exists
to prevent (rule 6j: "a reader that keeps its own copy of a marker shape drifts
silently"). `test_the_queue_reads_both_labels_as_one_oldest_first_list` locks
`QUEUE_LABELS`'s SHAPE; nothing locks that no reader re-spells it.

## What Changes

- `scripts/issue_review.py` reads its reviewer label as `iq.QUEUE_LABELS[0]` — the
  same seam it already uses for `REVIEW_LABEL = iq.REVIEW_LABEL` — instead of the
  bare literal in `decide()`.
- `scripts/data_gap_analysis.py` derives `LABEL = issue_queue.QUEUE_LABELS[0]`
  (importing its sibling module the way `issue_review.py` does) instead of a literal.
- `tests/test_issue_review.py` gains a guard: the scripts directory carries the
  literal `"data-gap-analysis"` in exactly ONE file (`issue_queue.py`, the
  definition), `data_gap_analysis.LABEL` equals `QUEUE_LABELS[0]`, and the reviewer's
  real `decide()` asks the real queue reader for the queue's own first label. The
  guard goes RED on the three-copy code (rule 6c).

## Impact

Affected specs: issue-queue (one label definition, no reader re-spells it).
Affected code: `scripts/issue_review.py`, `scripts/data_gap_analysis.py`,
`tests/test_issue_review.py`.
Not covered: renaming any label (nothing renames here — additive/derived only),
`REVIEW_LABEL`/`VERDICT_LABELS` copies (those already read from the queue).

## Open Questions

None.
