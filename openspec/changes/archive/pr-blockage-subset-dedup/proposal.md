# Proposal: pr-blockage-subset-dedup

Issue: #1565
PR: #1571

## Why

`group_pr_blockages` dedups emitted groups only by an IDENTICAL member-id tuple, but it emits one
group per axis key (`shape` and `exact_shape`). When ONE failure shape hits >= 3 open branches and
two of those runs are byte-identical over their whole quoted block while a third differs only in
chatter, the stable axis yields `{ci/a, ci/b, ci/c}` and the exact axis yields the strict SUBSET
`{ci/a, ci/b}`. Both clear `PR_BLOCK_MIN_PRS`, neither member tuple equals the other, and
`record_pr_blockages` files TWO issues for ONE defect — a reader counting fleet-wide reds
over-counts, and the ledger's run-id keying treats the duplicate as an independent shape.

## What Changes

- `group_pr_blockages` drops any group whose MEMBER RUN set is a strict subset of another emitted
  group's member-run set before returning. The surviving group is the superset, naming every
  blocked branch; the existing `shape` / `exact_shape` axes stay.
- `tests/test_pipeline_failure_issue.py` gains a RED-first guard driving the REAL
  `group_pr_blockages`: one defect on three open branches (two byte-identical whole blocks, one
  differing in chatter) — the base revision emits 2 groups, the head emits exactly 1 (the stable
  group naming all three). A second case proves two genuinely DIFFERENT defects stay two groups.

## Impact

No data format, contract, image or workflow wiring change. Additive filtering inside one function;
the ledger, issue body and dedup keys are untouched. The member-run discriminator means two
distinct defects that merely share an open branch are never collapsed into one.

## Not covered

- No change to `failure_shape` / `exact_failure_shape` or the axes themselves (#1476 / #1175).
- No change to the master/schedule half of the filer (#1557's scope stays separate).
- No CI dispatch, no merge, no master push, no collaborator grant.
