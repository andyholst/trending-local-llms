# Tasks: filer-log-fetch-escape-retry (issue #923)

- [x] `strip_terminal_escapes` helper in `scripts/pipeline_failure_issue.py` (CSI + OSC + lone ESC) — verified: `test_strip_terminal_escapes_leaves_plain_text_intact` 7/7 ok
- [x] `fetch_log` retry carries `--allow-escape-sequences` and strips before tail/extraction — verified: `test_an_escape_refused_log_is_diagnosed_on_the_flag_retry` 7/7 ok; suite `PASSED 70 | FAILED 0`
- [x] Stub `gh` answers the plain fetch with the exact measured refusal and the flagged retry with the colored log — verified: fixture drives the real filer end to end
- [x] New tests RED against the pre-change filer (rule 6c) — verified: `git show origin/master:scripts/pipeline_failure_issue.py` swapped into the tree, suite exits 1 (`the colored log's error lines landed in the body` FAIL; `strip_terminal_escapes` AttributeError)
- [x] AGENTS.md §8 guard row for the new tests (rule 6c), same branch — verified: row extended in commit `fix(tech-debt): #923 …`, §6r fetch sentence updated too, owed-row marker posted on #923
- [ ] `make lint` + `make openspec-check` + targeted suite green on the branch head; PR opened for #923 (never draft), body follows the message pattern with one `Closes` bound to #923
