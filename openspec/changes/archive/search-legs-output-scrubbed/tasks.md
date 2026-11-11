# Tasks

- [x] 1. Write the proposal + spec for `bot-agent-run-safety` (issue #355).
- [x] 2. `Makefile`: `HERMES_LOG` / `HERMES_LOG_SCRUBBED` / `HERMES_LOG_TAIL` and ONE `define scrubbed_run` (capture, print the redactor's bounded tail, keep the command's exit status).
- [x] 3. `Makefile`: apply the seam to `search-nvidia`, `search-metal`, `search-cpu`, `search-amd`, `search` and `fix` — the targets no workflow step captures.
- [x] 4. `.gitignore`: the captured log and its redacted copy.
- [x] 5. `scripts/check_secret_output.py`: `agent-target-does-not-scrub` (a target must redact in its own recipe), `scrub-seam-does-not-redact`, `agent-stream-printed-raw` no longer firing for a self-scrubbing target and now matching the dynamic form (`make search-${{ … }}` / `make search-$…`).
- [x] 6. `tests/test_secret_output.py`: a target without the seam refused; the gutted seam refused; the matrix step covered and re-opened by one un-scrubbed leg; the shipped Makefile's six targets verified.
- [x] 7. `tests/test_scrub_log.py`: the REAL seam driven through `make` against a leaking command — no value on the console, the mask printed, the redacted copy written, a failing command still non-zero.
- [x] 8. Guard verified green over the whole tree and RED on both fixtures (a target that lost the seam, a gutted seam).
- [x] 9. `AGENTS.md` §3d bullet + §8 row; `ARCHITECTURE.md` (the seam and the search/fix targets); `OPENSPEC.md` index refreshed.
- [x] 10. `findings.md` written and `make findings-check` green (rule 6g).
- [x] 11. Gates green: `make lint`, `make check-secret-output`, `make secret-scan`, `make test`, `make validate`, `make architecture-check`, `make openspec-check`.
- [x] 12. Commit, push, open the PR (`closes #355`) — reviewable, never a draft, never merged here.
