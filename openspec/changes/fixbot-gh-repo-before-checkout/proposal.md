# Proposal: fixbot-gh-repo-before-checkout

Issue: #331

## Why

The fix job writes to the PR **before** it checks anything out — that is
deliberate (#198: a reader of the PR must see a repair in flight as a timestamp,
not only in the Actions API). But `gh` resolves owner/repo from a **git remote**,
and at that point the runner has no repository. The workflow sets a custom
`REPO:` variable for its own `gh api "repos/$REPO/…"` calls; `gh pr comment` does
not read it.

Measured on PR #330 (run 39027053298), a refresh PR red on one dead Hugging Face
link:

```
fix  step 3. Announce the window on the PR        -> failure
     failed to run git: fatal: not a git repository (or any of the parent directories): .git
fix  step 4. Checkout PR branch                   -> skipped
fix  step 7. Fix loop (check -> fix -> re-check)  -> skipped
```

13 seconds, nothing repaired. `dispatch-fixbot` in qa-validate was **green**, so
the pipeline reported a repair as having been dispatched while the one bot that
could repair it never reached its loop. A red PR therefore stays red until a
human looks — the failure mode is silent, which is the defect.

## What Changes

- **`.github/workflows/fix-bot.yml`** — the `fix` job declares
  `GH_REPO: ${{ github.repository }}` in its job-level `env`, so every `gh` call
  in that job resolves the repository with or without a checkout: the window
  announcement, the PR resolution, and the result comment a run posts when it
  died early.
- **`tests/test_workflows.py`** — `test_gh_before_the_checkout_names_the_repo`:
  for **every** workflow and job, a `gh pr|issue|run|release|workflow|label|search`
  invocation that runs before the first `actions/checkout` (or in a job with no
  checkout at all) must carry `GH_REPO` in the job or step env, unless the
  command names the repo itself (`--repo` / `-R`). `gh api repos/$REPO/…` is
  never matched, because it carries its own path. A second, named assertion pins
  `fix-bot.yml`'s `fix` job specifically, so the guard cannot go vacuous.
  Verified red against `git show origin/master:.github/workflows/fix-bot.yml`
  (`FAILED 2`) and green on the fixed tree.

## Impact

`.github/workflows/fix-bot.yml` (one job-level env entry), `tests/test_workflows.py`
(the new guard + its `main()` registration), the OpenSpec change + `OPENSPEC.md`.
No `data/**` change, no make target, no job added or renamed — `ARCHITECTURE.md`
needs no row (rule 6h), and the guards `make test` already runs cover it.

## Not covered

- **Why the refresh produced a dead link at all.** The Hugging Face repo id was
  truncated (`meta-models/Muse-Spark-Open` instead of
  `meta-models/Muse-Spark-Open-816B-A42B`); the link validator caught it in CI, as
  designed. Making the *search* verify a repo id it invents is a different change
  (and would put a network call in the prompt loop) — the immediate defect is that
  the repair bot could not run.
- **The other `gh`-before-checkout sites.** `issue-bot` and `issue-review-bot`
  resolve their issue before the checkout too, but through
  `gh api "repos/$REPO/…"`, which names the repo explicitly and needs no
  `GH_REPO`. The new guard encodes exactly that distinction rather than blanket
  requiring the variable everywhere.
