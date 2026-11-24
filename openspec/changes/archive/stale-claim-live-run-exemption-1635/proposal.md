# Proposal: stale-claim-live-run-exemption-1635

Issue: #1635
PR: #1638

## Why

`#1265` §3B (AUTHORITY LIMITS) says the stale-claim sweep MUST emit NOTHING for a RUN-BEARING
claim whose evidence is still live — "`gh run view <id> --json status` answers `in_progress`/`queued`,
or the PR is open and its newest run is not concluded. A live run is EXPLICITLY exempt: voiding it
would tell a second lane to push to a branch while CI is reading it". The shipped seam landed by
#1626 implements only the doubled grace (180/360 min): `is_run_bearing(newest.body)` picks the
bound pair from the claim TEXT alone and no path resolves a run id or reads PR state, so a
CONCLUDED run and a LIVE one are indistinguishable to the decision. Measured in `findings/1626.md`
and restated on #1635: the pinned rule is weaker than the design it cites.

## What Changes

- `scripts/stale_claim_sweep.py`: the thin `gh` layer resolves every `R:<id>` it sees through
  `gh run view <id> --json status,conclusion`, and every `PR #<n>` through
  `gh pr view <n> --json state,headRefName` plus the PR's NEWEST run via `gh run list --branch`.
  `liveness_resolver(repo, client)` is the ONE bound `body -> bool` seam; `claim_evidence_is_live`
  is its single implementation.
- `sweep_thread` gains `live_evidence=` and emits NOTHING at any age when it is True for a
  run-bearing claim; `sweep_threads` gains the optional `live_resolver=` that supplies it. An
  unresolved value keeps the pre-#1635 doubled pair, so a pure caller never silently exempts a
  claim it did not resolve.
- The three-refusal tuple (`AUTHORITY_LIMITS`), the two pinned grace pairs, every `--check` floor
  and the `S:<issue>:<claim-id>:<verdict>` shape are unchanged. `--check` additionally pins the
  live-status set to `{queued, in_progress}`.
- `tests/test_stale_claim_sweep.py`: a stub-`gh` end-to-end guard proving BOTH directions (live
  exempt, concluded keeps the doubled pair) across run ids, OPEN/MERGED PRs and a PR with no run;
  a pure-decision guard for `live_evidence` at five ages; and a RED pin that runs the same
  fixture against `origin/master`'s script, which reports the still-live claim.
- `ARCHITECTURE.md`: §3 target row, §6 script row and the regenerated §10 inventory now describe
  the liveness resolution. The `AGENTS.md` §8 row could not be written in this headless leg
  (rule 3c): the write was refused by the protected-file guard, and the full row is recorded as an
  owed-row finding in `findings/1635.md` with a `- [~] … blocked:` task.

## Impact

Behaviour-narrowing only: a claim whose CI evidence is still live is no longer swept at any age;
a claim whose run has concluded, whose PR merged/closed, or whose open PR has no run keeps exactly
the doubled 180/360 grace it had before. No new make target, no workflow change, no data/contract
change, no dead code, and no `master` push or merge. The external `gh` CLI is the only stand-in a
test uses (rule 6m); the decision itself runs unmocked.

## Not covered

- No AGENTS.md behaviour text: §7b does not change, so there is no rule-3c behaviour sign-off to
  request. The §8 *documentation* row is owed and recorded in `findings/1635.md`.
- No PING/RELEASE comment, no state file, no `S:` marker registration and no new sweep stage —
  the sweep stays report-only and read-only.
- No change to the claim-id derivation, the dedup contract or the newest-comment discriminator.
- No CI dispatch, no Actions schedule, no collaborator grant and no hand merge.
