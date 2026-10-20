# Proposal: repair-a-conflicted-pr

Issue: #475 (the owner's ask: *"they should always auto-merge and rebase and resolve conflicts with help off llm"*)

## Why

The pipeline auto-MERGES on green (`qa-validate`'s `auto-merge`, squash + `--delete-branch`, gated
on `validate` + `live-smoke`). It does not auto-REBASE, and a PR whose base moved is invisible:

- a PR that goes `CONFLICTING` gets **no workflow runs at all** — GitHub cannot build the merge
  commit, so `validate` is ABSENT, `qa-validate`'s `dispatch-fixbot` (which fires on a *failed*
  `validate`) never fires, and the repair waits for a human. Measured on #442/#439/#436.
- `scripts/fix_loop.sh` already merges the fetched base into the branch before its first LLM
  round (#383) — and on a CONFLICT it does `git merge --abort` and moves on, so the one case
  that actually needs the model is the one case it refuses to handle.

The owner's ruling: a bot PR that cannot merge because its base moved is the bot's job. The
`pr-health` sweep (#442) already notices a silent PR twice an hour; it only comments.

## What Changes

- **`scripts/pr_health.py --repair`**: for every silent PR on a `ci/…` branch, dispatch
  `fix-bot` (`gh workflow run fix-bot.yml -f pr_number=… -f branch=…`), capped at
  `--max-fixbot-commits` (default 2) `fix-bot:` commits per PR, exactly like the dispatcher in
  `qa-validate`. A human's branch is reported, never dispatched to — the loop would push to it.
- **`scripts/fix_loop.sh`**: a conflicted base merge is a REPAIR, not an abort.
  - the conflicted paths and their hunks are written to a conflict report that `run_checks`
    appends to `$REPORT` — the file `make fix` reads first — together with the rule that
    generated artifacts (`data/models.json`, `README.md`, `data/snapshots/*`) are REGENERATED,
    never hand-merged;
  - an unresolved conflict makes `run_checks` RED by definition (the tree has conflict markers),
    so a lenient check can never report the branch green;
  - after each round, a clean index COMPLETES the merge (`git add -A` + `commit --no-edit`);
  - after the last round, a still-conflicted merge is `--abort`ed, so a half-merged branch is
    never pushed.
- **`Makefile`**: `make pr-health REPAIR=1 MAX_FIXBOT_COMMITS=<n>` reaches the new flags.
- **`pr-health.yml`**: a new step dispatches the repair with the owner PAT (dispatching a
  workflow is an Actions write); the COMMENT step keeps the default token (rule 6b).

## Impact

`scripts/pr_health.py`, `scripts/fix_loop.sh`, `Makefile`, `.github/workflows/pr-health.yml`,
`tests/test_pr_health.py`, `tests/test_fix_loop.py`, `OPENSPEC.md`, this change. No new image,
no new target that CI does not run (`make pr-health` already runs in the sweep).

## Not covered

- **`AGENTS.md` §6b/§8** — the rulebook wording this change owes is a PROTECTED file: the write
  was refused in this run (approval did not return), so it is filed as its own `tech-debt` issue
  rather than smuggled in, exactly as the repo's other "§8 row is owed" issues do. Rule 3c
  applies: the wording is review-required.
- **A rebase of a PR whose base moved but which does NOT conflict** is left to `auto-merge`, which
  handles it: GitHub merges a behind-but-clean PR normally.
- **Conflicts inside `data/raw/*` or a snapshot** are not auto-resolved by regeneration; the round
  resolves them as text, and the report tells the model they are generated.
