# The bot's working files are ONE list

**Issue:** [#543](https://github.com/andyholst/trending-local-llms/issues/543)
**Capability:** `bot-commit-safety`

## Why

The unstage-before-commit line was a long literal copied into **four** places: the same
`git reset -q -- qa-report.txt comment.md issue.md pr-body.md findings.md triage.md start.md
issue-body.md implement.log implement.scrubbed.log` **twice** in `issue-bot.yml`, a third (shorter)
copy in `fix-bot.yml`, and a fourth in `.gitignore`. Adding a working file meant remembering all
four, and a miss meant the push step's `git add -A` committed it — measured with
`qa-report.txt.notes`, a 0-byte scratch note that reached PR #387 (issue #390).

## What Changes

- **`scripts/issue_bot_working_files.txt`** — the ONE list (12 names, one per line, comments
  allowed).
- **`scripts/reset_working_files.py`** — `git reset --` every name that exists (a name no run
  wrote is not an error), reporting a real git failure instead of the old `2>/dev/null || true`;
  `--check` proves every name on the list is also gitignored.
- **`make reset-working-files`** (host-side, like the other git seams) and
  **`make check-working-files`**, wired into `make lint` — a name that is not ignored can be
  staged by any other step, so the list and `.gitignore` cannot drift.
- **All three call sites** (`issue-bot.yml` ×2, `fix-bot.yml` ×1) call the target.
- **`tests/test_working_file_list.py`** (new) — real repositories: the listed scratch is
  unstaged and the real change stays staged; an un-ignored name, an empty list, a missing list
  and a non-git directory all fail loudly; three call sites; `lint` runs the check.
- **`tests/test_workflows.py`** — the old guard asserted the literal `git reset -q --` text; it
  now asserts the TARGET plus the list, and both step-test stubs map the target to the real
  script (the fixtures carry the list, or the script cannot run there).

## Impact

Both bots and `make lint`. A new working file is one line in one file.

## Not covered (out of scope)

- A scratch file a run writes with a name NOT on the list is still stageable; the list is a
  declaration, not a sandbox. The end-to-end "what a run really writes" audit is filed as a
  finding.
