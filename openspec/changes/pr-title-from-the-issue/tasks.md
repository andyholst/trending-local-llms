# Tasks

- [x] 1. Write the proposal + `pr-body` capability spec for issue #541.
- [x] 2. `scripts/pr_body.py`: `title(issue, kind)`, `KIND_TYPES`, `UnknownKind`, and the `--title` / `--kind` CLI (unknown kind refused, exit 2).
- [x] 3. `make pr-title ISSUE=<n> [KIND=…]`, `@`-silenced so a capture holds the title alone.
- [x] 4. `.github/workflows/issue-bot.yml`: the kind comes from the issue's labels and the title from the target; the inline title is gone.
- [x] 5. `tests/test_pr_body.py::test_the_pr_title_is_composed_from_the_issue_kind`: both kinds, an unknown kind, a missing ISSUE, the silenced recipe, and the workflow shape.
- [x] 6. The step-execution test's stub `gh` answers the label query, so the shipped step still runs end to end (32 passed).
- [x] 7. `make openspec-index`, `make openspec-check`, `make architecture-check`, `make lint` green.
