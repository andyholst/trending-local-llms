# Tasks: issue-body-prefile-architect-1814

- [x] Create the tracked OpenSpec change bound with a bare `Issue: #1814` line
- [x] Prove the extended guard RED on the base revision (2 failing checks) and GREEN on this head
- [x] Document `make issue-message-check BODY_FILE=<draft>` before `gh issue create` in the architect prompt
- [x] Run the targeted module `tests/test_pr_message.py` (54 passed / 0 failed)
- [x] Run `make lint` and regenerate `OPENSPEC.md`
- [x] Write `findings/1814.md` and archive the change onto the PR head
