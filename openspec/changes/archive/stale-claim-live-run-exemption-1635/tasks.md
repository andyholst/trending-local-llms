# Tasks: stale-claim-live-run-exemption-1635

- [x] Resolve every `R:<id>` through `gh run view <id> --json status,conclusion` in the thin `gh` layer
- [x] Resolve every `PR #<n>` through `gh pr view <n> --json state,headRefName` plus its newest run via `gh run list --branch`
- [x] Add `liveness_resolver(repo, client)` / `claim_evidence_is_live` as the ONE bound seam (run ids and PR numbers, every one the claim carries)
- [x] Give `sweep_thread` `live_evidence=` and `sweep_threads` `live_resolver=`: live emits NOTHING at any age, unresolved/False keeps the doubled 180/360 pair
- [x] Pin `LIVE_RUN_STATUSES = {queued, in_progress}` in `--check` without changing the three-refusal tuple, the two pinned pairs, the floors or the `S:` vocabulary
- [x] Add the stub-`gh` BOTH-directions guard, the pure-decision guard at five ages, and the RED pin against `origin/master`'s script; wire all three into `main()`
- [x] RED-verify: the new module fails against the pre-change script (AttributeError on `extract_run_ids`), and the in-module RED pin shows the base seam reporting the live claim; GREEN on this head (92 passed, 0 failed)
- [x] Update ARCHITECTURE.md §3 target row + §6 script row and regenerate the §10 inventory block (`architecture-check` OK)
- [x] Record the protected §8 row as an owed-row finding in `findings/1635.md` (`make findings-check ISSUE=1635` OK)
- [~] Land the owed AGENTS.md §8 row from `findings/1635.md` — blocked: rule 3c human sign-off (AGENTS.md is protected in a headless leg)
- [x] Regenerate `OPENSPEC.md` and keep the change bound to `Issue: #1635`
- [x] Commit, push a READY PR whose title and body carry `Closes #1635`, and hand over to `tll-reviewer`
