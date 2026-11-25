# Tasks: timeout-prong-neutral-failed-1707

- [x] Replace the timeout prong's `(timeouts + outage == queries)` discriminator in `zero_hit_verdict` with the shared `not answered`/`not with_hits` discriminator
- [x] Add RED-first guard for timeouts mixed with a neutral `failed` query in `tests/test_firecrawl_fetch.py`
- [x] Add the parity guard for the two outage prongs, keeping the existing partial-timeout and gateway-error guards green
- [x] Prove the guards RED against `origin/master`'s `scripts/update_trending.py` and GREEN on this branch
- [x] Run `make lint`, `make architecture-check` and `make openspec-check`; regenerate `OPENSPEC.md`
- [x] Write `findings/<issue>.md`, record/archive the change on the PR branch, open a non-draft PR and hand to `tll-reviewer`
