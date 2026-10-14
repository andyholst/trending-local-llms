## 1. The hold (one queue rule)

- [x] 1. `scripts/issue_queue.py` reads the reviewer's verdict labels (`needs-refinement`, `obsolete`, `duplicate`, `already-fixed`) as a hold whose freshness comes from the newest reviewer marker comment on the issue, with `VERDICT_TTL_HOURS` (default 24)
- [x] 2. A fresh verdict sets `impl_skip=1`, `reason=verdict-fresh`, `position=-1` and reports `verdict` / `verdict_since` / `verdict_fresh`; a stale one releases the issue (still reported); a label with no reviewer marker is reported and never holds

## 2. The implementer's response (a comment, never a label)

- [x] 3. `scripts/issue_queue.py --skip-note` + `make issue-skip-note` post ONE comment on the held issue carrying `<!-- issue-bot-skip: <ISO8601Z> verdict=<label> since=<reviewer ts> -->`, idempotent per review round
- [x] 4. `issue-bot.yml`'s `pick` job runs `make issue-skip-note` when the pick came back empty, with the default token (`github.token`); it writes no label and edits no body
- [x] 5. The skip path never edits a label or a body: it is exactly one `gh issue comment`

## 3. The record (rules 6c/6d/6h/6i/6j)

- [x] 6. `tests/test_issue_review.py` locks the hold and the note (fresh holds / 25 h releases / label-only never holds / one comment per round / no label or body write) and its cases are wired into `make test`
- [x] 7. `tests/test_workflows.py::test_issue_bot` locks the workflow half (the note runs on an empty pick, with the default token, and never writes a label)
- [x] 8. `AGENTS.md` rule 6j records the protocol (three verbs, one queue, timestamped markers, the shared owner/collaborator guard), its §8 row names the new failure modes, and `ARCHITECTURE.md` gains the `issue-skip-note` target and the verdict hold in the `pick` row
- [x] 9. `README.md` (through its template in `scripts/update_trending.py`) explains the verdict hold and `make issue-skip-note`, and `test_readme_render.py` stays green
- [x] 10. `make openspec-check` (tasks ticked, `OPENSPEC.md` current), `make architecture-check`, `make lint`, `make test` and `make validate` are green on the branch
