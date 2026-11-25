# Tasks: cancel-chatter-filer-1741

- [x] Extend `_superseded_cancelled_push` to skip cancelled push runs whose block carries only GitHub cancellation chatter, keeping the `EMPTY_SHAPE` path and the #1615 counterexample
- [x] Add the RED-first guard `test_a_cancelled_push_with_only_cancel_chatter_is_not_filed` and register it in the module's `main()`
- [x] Prove the guard RED on the fetched base script (`PASSED 355 | FAILED 3`) and GREEN on the branch (`PASSED 358 | FAILED 0`)
- [x] Regenerate `ARCHITECTURE.md` §10 for the edited script docstring and run `make architecture-check`
- [x] Run `make lint`, `make findings-check ISSUE=1741`, `make openspec-validate NAME=cancel-chatter-filer-1741`
- [x] Write `findings/1741.md` with the owed rulebook row declaration
- [x] Opened non-draft PR #1743 closing #1741, recorded `Issue: #1741` / `PR: #1743`, archived the change and regenerated `OPENSPEC.md`; handover to `tll-reviewer` posted on the issue
- [~] AGENTS.md §8 guard row — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg); declared as an owed row in findings/1741.md
