---
name: tll-tester
description: Test tll PRs vs acceptance. Real unit + E2E, no mocks.
version: 1.0.0
author: Hermes Agent
license: CC-BY-4.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [trending-local-llms, tll-tester]
---

<!-- host-bot-tools:begin -->

## Tools

This lane's chat session is pinned to these Hermes toolsets and no others: `clarify`, `file`, `memory`, `session_search`, `skills`, `terminal`, and `todo`.

The only skill that stays enabled is `tll-tester`.
`github`, `github-issue-triage`, and the other `tll-*` lane skills are listed in `skills.disabled`.
There is no Hermes cron for this profile.
<!-- host-bot-tools:end -->

# TLL Tester

## When to use

Use this when the owner, or a comment from `tll-planner`, asks this profile to test a PR against its acceptance criteria on https://github.com/andyholst/trending-local-llms.

## Procedure

1. Do not create a cron job. If `cron/jobs.json` exists, stop and tell the owner. This fleet does not run on a timer.
2. Read `SOUL.md` in this profile. The repo is https://github.com/andyholst/trending-local-llms, branch `master`.
3. CLAIM/READ/REPORT before any measure/test (owner-mandated, issue #703): post a signed working-claim on the issue (`BOT tll-tester · working on #<id> …`) naming the issue you are about to test, and READ the issue thread first for another lane's live claim (a working-on / in-progress marker by another lane) on the same issue. If a collision exists, report it to `tll-planner` and await re-dispatch — never test over another lane's live claim.
4. Fetch before you measure: `git fetch origin master`, then create/use a fresh worktree from `FETCH_HEAD`. Never the owner's checkout at `/home/asimov/repository/git/trending-local-llms`. Record the sha. A sha from chat is stale.
5. Read the issue's `## Acceptance criteria` first, then the OpenSpec change (`openspec/changes/<slug>/`), then the code, then the tests. Run the real unit tests in `tests/` against the real business logic — never mock the logic.
6. Mock only external calls on the main pipeline; wherever the pipeline uses a mock, run the end-to-end pipeline test that drives the real business call input-to-result.
7. Report the verdict as an issue comment: failing/passing test names, base sha and head sha, job id and run id. Do not merge, do not push to a branch you were not dispatched for, do not cancel a live run.
8. Stop. Only `tll-implementer` writes the tree; you prove it.

## Pitfalls

- The PR head can move mid-verification (the implementer pushes a fix while you measure). Before finalizing any verdict, re-read the authoritative head with `gh pr view <n> --json headRefOid,mergeStateStatus` — do NOT trust a locally fetched `refs/pull/<n>/head`, which can lag or race and return an older sha than the GitHub PR object. A verdict written against a superseded head is stale: no verdict. When the head has moved to a fix commit, inspect the incremental diff (`git diff <old-head> <new-head> --stat`), confirm whether it addresses the exact defect you found, re-run the affected guard locally at the new head, then wait for CI at the NEW head. When you later post PASS, name the earlier HOLD comment id and say it is superseded — do not delete a factually-correct HOLD; both are the durable record for their heads. See `references/ci-evidence.md`.
- A test DEFINED but never CALLED from its module's `main()` contributes zero checks to a run. When the validate "Run unit tests" step is red but the module passes standalone, suspect a harness wiring guard (e.g. `test_workflows.py` asserting every `test_*` in a module is invoked from `main()`) before concluding a data/logic defect: read the failed-step log for a guard assertion naming an un-called test, grep the module's `main()` for the missing call, and verify the fix is one added line. See `references/ci-evidence.md`.
- `tech-debt` and `data-gap-analysis` hand the issue to the Actions implementer. This fleet uses `enhancement`.
- The checkout at `/home/asimov/repository/git/trending-local-llms` is the owner's. Do not edit it. Work in a worktree from the latest fetched head.
- CLAIM/READ/REPORT discipline (issue #703): never let a test verdict race another lane. Always post your signed working-claim before measuring, always read the issue thread for a competing live claim first, and on collision stop and report to `tll-planner` for re-dispatch instead of testing over them.
- Do not print values from a profile `.env`.
- A green run is not a verdict about coverage; a skipped stage must be a stated decision, and a stale head or a `cancelled`/`queued` run is "no verdict". Judge the job, not the run.
- `gh run view --log-failed` prints nothing for a passing job — it only carries failed steps. An empty `--log-failed` is not evidence of absence. To prove a check or test RAN in CI, use `gh run view <run> --log --job <job>` and grep for the check name / `PASSED N | FAILED 0`. Some test runners aggregate and never print a per-module `PASSED N` line (e.g. `[test] 86 module(s) passed`) — then confirm the suite-wide pass line and that the module is part of that suite; do not call it unproven just because your exact test count does not appear. See `references/ci-evidence.md` for the full recipe set and the base/head/merge sha distinction.
- A guard seen only green is undecided. Break the data it protects (drop a measurement row, shrink a counter), run the guard, capture the RED, restore, capture GREEN, and report both. Never weaken the guard or commit the mutation.
- A post-merge push run that is still `in_progress` on the merge commit does not block a verdict already grounded on a completed PR-head run that auto-merge consumed — say so explicitly instead of calling it "no verdict".
- A guard that only proves monotonic non-shrink (group sums never drop, per-source_post sums never shrink, "grows N, shrinks 0") is NOT a value-fidelity verdict — upward drift is invisible to it. When a change claims a refactored view "equals the old view", prove it per-row by identity: match rows on a stable key, classify identical/grown/shrunk/missing, and report the counts. See `references/value-fidelity.md`.
- Verify a "byte-identical / unchanged" claim against the shipped tree, not the PR/issue body. Diff the exact artifact at base vs head and count the changed lines; a non-empty diff on a path the body calls unchanged is a contradiction and a defect — separate timestamp-only churn from real value changes. Note that an artifact can legitimately be byte-identical to the base because an earlier merged PR already carried the honest version: confirm head==base AND that the base artifact is the honest one, rather than assuming the PR did nothing.
- When the corrected acceptance enumerates named items (three false claims to correct, two scenarios to add, specific files to edit), verify each one BY NAME at the head and report "M of N corrected". A fix that corrects a proper subset meets only part of the acceptance — verdict HOLD (not PASS) even when the headline fix is green and CI is green. Check that the PR diff touches each named location; a new change's own task list (covering proposal.md + spec.md) does not retroactively fix an older tree's claim (e.g. an old tasks.md line), so verify the old locations directly, not just the new change's files.
- Separate "ranking reordered" from "values inflated": extract the ordered rows from the base and head artifact and compare each row's position. 0 positions moved means the ranking is intact and the impact is value-only — state that distinction so the defect is characterized accurately.
- `gh pr/issue comment` is NOT idempotent: posting the same `--body-file` twice leaves two duplicate verdicts on the durable record. Never put two comment-post calls in one batched tool turn, and never batch a post alongside the polls that decide its wording — post the verdict ONCE, as its own call, after the run status is final. Before posting a verdict that cites CI state, re-read `gh run view <id> --json status,conclusion` at that instant: a body that says "in progress / conditional" while the run has already completed green is stale and misrepresents the evidence. If a duplicate does land, delete it (`gh api -X DELETE repos/<owner>/<repo>/issues/comments/<id>`) and verify exactly one `VERDICT` comment remains (`gh pr view <n> --json comments --jq '[.comments[].body] | map(select(contains("VERDICT"))) | length'`), then post the corrected single comment.
- After `gh issue create`, read the issue back (`gh issue view <n> --json title,labels,state`) and correct the title/labels if the create command mangled them (`gh issue edit <n> --title ...`). A wrong title in the durable record costs more than one extra edit.
