# Tasks: issue-body-prefile-check-1730

- [x] Create the tracked OpenSpec change bound with a bare `Issue: #1730` line
- [x] Add the RED-first guard to `tests/test_pr_message.py` naming the filing prompts and the preserved `issue-message-check` seam
- [x] Document `make issue-message-check BODY_FILE=<draft>` before `gh issue create` in the reviewer, tester and planner prompts
- [x] Prove the guard RED on the base revision and GREEN on this head, then run the targeted module
- [x] Run `make lint` and regenerate `OPENSPEC.md`
- [~] Extend the `AGENTS.md` §8 row for `tests/test_pr_message.py` to name `test_a_filing_lane_validates_its_draft_issue_body_before_create` — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [x] Write `findings/1730.md` with the owed-row declaration and push onto the PR for tll-reviewer
