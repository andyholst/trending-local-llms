# Proposal: refresh-bot-pin-token

Issue: #1747 (one of three root causes; this change fixes only the aggregate token)
PR: pending

## Why

The weekly `refresh-bot` aggregate job runs `make hermes-pin-channel-record`, whose one seam calls
`gh api repos/NousResearch/hermes-agent/releases/latest`. The read is public, but `gh` inside
Actions refuses to run without a token: run `45657191852` died with `gh: To use GitHub CLI in a
GitHub Actions workflow, set the GH_TOKEN environment variable` (rc=4) → `make: ***
[Makefile:2120: hermes-pin-channel-record] Error 2`. Every later aggregate step was skipped, so
the refresh produced no PR. This is independently root-caused from the other two shapes in #1747
(search-leg SIGPIPE and the test-image buildkit layer lock), which remain tracked there.

## What Changes

- Give the aggregate job `GH_TOKEN: ${{ github.token }}` at job level. A public read needs only
  the default token; the owner PAT is deliberately not used here (AGENTS.md rule 6b).
- Add `test_the_aggregate_job_gives_the_pin_recorder_a_token` to
  `tests/test_hermes_pin_freshness.py`: it locates the job that runs the recorder and refuses a
  job block with no `GH_TOKEN` or with the owner PAT substituted.
- Add the OpenSpec capability requirement and this checklist; declare the AGENTS.md §8 row owed
  to the attended owner (rule 3c) in `findings/1747.md`.

## Impact

- Capability: `hermes-pin-freshness` (the recorded channel payload can be refreshed in CI).
- Additive: one environment line in one workflow job plus one test; no script, Makefile target,
  data file or rulebook byte changes.
- Scoped deliberately: the two other #1747 root causes are NOT fixed here and that issue stays
  open for them.
