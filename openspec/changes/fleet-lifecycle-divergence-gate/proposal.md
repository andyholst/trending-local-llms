# Proposal: fleet-lifecycle-divergence-gate

Issue: #1209 — "fleet: the issue owns the PR→reviewer handover, and host lane behaviour is checked against fetched master (CI too)"

## Why

#1189 put claim and handover on the issue thread, but a PR ends the thread: no comment
names the reviewer, and no follow-up is owned. #1190 asks hosts to sync, but nothing
checks that a host's `~/.hermes/profiles/tll-*` bytes and the `AGENTS.md` tll behaviour
still match the fetched upstream master. Two machines can therefore run different
protocols and grab the same issue.

## What Changes

- Every lane's `SOUL.md` and the planner skill carry the PR/review handover shapes.
- `AGENTS.md` gains one tll-fleet behaviour section plus a §8 regression-guard row
  (rule 3c: review-required, declared on the issue).
- A new seam `scripts/fleet_host_sync_check.py` compares a host profile home with
  `git show <fetched base>:agents/...` and the rendered chain, and checks the
  rulebook markers. A new `make fleet-host-sync-check` target exposes it.
- A repo-side test drives the REAL seam over a scratch profile home and is wired
  into `make test` / `make lint`, so qa-validate runs it on PRs and on push.

## Impact

New Makefile target and script (documented in `ARCHITECTURE.md` in the same change),
one new `AGENTS.md` behaviour section, seven lane SOUL edits and one skill edit.
No data format, contract, model chain or existing gate is removed or weakened.

## What is not covered

- Restarting an already-running gateway session (a sync changes the NEXT session).
- Reading another machine's real profile home from CI — CI validates the seam and
  the repo-side rulebook; the host command proves the real home.
- Any change to the model chain's provider or order (issues #1203 / #1199).
