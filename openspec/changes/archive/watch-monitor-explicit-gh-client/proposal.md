# Proposal: watch-monitor-explicit-gh-client

Issue: #1368
PR: #1369

## Why

Master commit `292c6ece` (PR #1366, issue #1364) added post-merge PR resolution to the repo-owned
watch detector. `fetch_payload(repo, client)` is handed the explicit `gh` path that both cron
wrappers pin with `--gh` because the stripped cron PATH cannot resolve `gh` on its own — but the
new resolution branch reassigned `client = gh_client()` before calling `resolve_branch_prs`. That
reassignment leaked into every later leg of the same function, including the final
`get("commits/master")`, so the detector that emits this fleet's C/R/M/H wake-ups could lose its
master marker and its PR identity on exactly the post-merge ticks the fix was meant to cover.

Measured 2026-11-23 on the `asimov@mac` wake-up: driving the real `fetch_payload` with an explicit
stub client, no `gh` on PATH and `TLL_GH` pointing at a second stub produced the log lines
`sentinel | pr list` and `sentinel | api repos/o/r/commits/master`, proving the pinned client is
silently dropped.

## What Changes

- `scripts/watch_monitor.py`: remove the `client = gh_client()` reassignment inside
  `fetch_payload`; the caller's `client` serves the comment legs, the branch resolution and the
  master read alike. A comment names why a second lookup is wrong.
- `tests/test_watch_monitor.py`: add `test_fetch_payload_keeps_the_explicit_gh_client`,
  registered in the module's hand-maintained `main()`. It drives the real `fetch_payload`
  against two stub CLIs (the only stand-ins, for the external `gh`, rule 6m), with no `gh` on
  PATH and `TLL_GH` naming a sentinel, and asserts the sentinel is never invoked, the resolution
  ran on the explicit client and the PR was injected back into the run row.
- `findings.md` records the audit half (rule 6g); the AGENTS.md §8 row is declared owed, not
  edited by this headless leg (rule 3c).

## Impact

The watcher keeps one `gh` per tick for every leg, so `R:` markers retain their PR number and
`M:` markers keep arriving on stripped cron hosts after a merge burst. No marker-shape change,
no new target, no workflow change, no cron, no data-format change, no contract change, and no
change to any stored state key or value.

## Not covered

- No change to the marker grammar, the heartbeat, the claim-settle floor, or the C/M markers.
- No change to `resolve_branch_prs` or `inject_run_prs` themselves (both stay pure/used as-is).
- No CI dispatch, no merge, no `master` push, no collaborator grant, no sibling branch touched.
- The AGENTS.md §8 row naming this one-client contract is a rule-3c human sign-off and is
  tracked as an owed row, not written here.
