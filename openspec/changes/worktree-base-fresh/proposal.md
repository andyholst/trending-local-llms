# Where work starts: a worktree off the freshly fetched base, and the base is asserted

**Issue:** [#271](https://github.com/andyholst/trending-local-llms/issues/271)
**Capability:** `worktree-base`

## Why

`AGENTS.md` never said where work happens. Rule 6e asked for "a feature branch cut from
`master`" — a **local** branch name: no `git fetch`, no assertion that the base is the
current `origin/master` tip, nothing that notices a stale or dirty tree. The only mention
of a worktree in the rulebook is §3d's `secret-scan-history` refusal. Meanwhile
`ARCHITECTURE.md` §8 drew the life of a change as `GitHub issue → feature branch
(+ worktree off latest master)`: a documented mechanism no code implements (`git worktree`
appeared nowhere in the tree).

The cost is measured, not hypothetical. `.github/workflows/issue-bot.yml`'s resume path
ran `git checkout "$BRANCH"` in a clone that had fetched exactly ONE ref
(`actions/checkout@v4` + `ref: master`, default `fetch-depth: 1`, `--prune`), so
re-running an issue whose branch already existed — the resume rule 6e *requires* ("never a
force-push") — died under `bash -e`:

```
$ git clone --branch master <remote> fresh && cd fresh
$ git checkout ci/data-gap-1-x
error: pathspec 'ci/data-gap-1-x' did not match any file(s) known to git
```

`tests/test_workflows.py:681` only asserted that the words `ls-remote` appear and `--force`
does not, so the guard stayed green over a checkout that cannot work.

The failure mode this leaves behind is silent: an implementation started from an old base
merges a change whose tests were written against a tree that no longer exists — green
locally, red on `master` — and a fresh CI checkout is only the latest `origin/master` by
accident of the runner, which nothing verifies.

## What Changes

- **`AGENTS.md` — new rule 6n** (review-required per rule 3c; the disclosure comment on
  #271 names the section): every implementation starts from a working copy cut off the
  freshly fetched `origin/master`, and the base is **verified, never assumed** — a run
  either fetches the base and asserts the commit it started from is the fetched tip, or it
  refuses to start; locally the working copy is a **worktree** per run, in CI the fresh
  checkout plays that role but is asserted the same way. Plus its §8 guard row.
- **`scripts/worktree_base.py`** — the ONE implementation (rules 6d/6m) of the fetch, the
  assertion and the refusal, with three modes: `check` (assert this checkout IS the
  fetched tip), `new` (a NEW branch off it — worktree by default, `--in-place` for a fresh
  CI checkout, refusing an existing branch instead of re-cutting it) and `resume` (an
  existing branch: **fetch it first**, then attach, reporting how far behind the base it
  is).
- **`Makefile`** — the three host targets CI and a human share: `base-check`,
  `worktree-new BRANCH=…` (add `IN_PLACE=1` in CI), `worktree-resume BRANCH=…`.
- **`.github/workflows/issue-bot.yml`** — `make base-check` right after the PAT checkout,
  and the broken bare `git checkout "$BRANCH"` replaced by `make worktree-resume`/
  `worktree-new` (the same seam, so the rule has one implementation). Same `make base-check`
  in `refresh-bot.yml`'s `aggregate` job, which also cuts a branch.
- **`tests/test_worktree_base.py`** (in `make _test`) — real git repositories, no mocks:
  the assertion catches a behind/stale checkout, a failed fetch is loud, `new` creates a
  worktree **at the fetched tip** (the remote moves between the clone and the call),
  refuses an existing branch and refuses a worktree inside the repo, and `resume` works on
  the single-ref clone that reproduced #271 — with the OLD code shown failing on the same
  fixture. `tests/test_workflows.py`'s marker-word assertion on the resume path is replaced
  by the real wiring.
- **`ARCHITECTURE.md`** (rule 6h): the §8 claim becomes true, §3 gains the three targets,
  §6 the script, §4 the new `issue-bot` steps.

## Impact

Local implementations happen in a worktree cut from the fetched base; the pipelines assert
the base they cut from and can actually resume a branch. Read-only against the data store
and the network beyond `git fetch`. Nothing about the ranking, the store or the README
changes.

## Not covered (out of scope — separate issues)

- The `install-*` scripts are untouched; the local worktree is created by the host target,
  not by the container.
- `fix-bot.yml` is already correct here: it checks out the PR's head **branch ref** via
  `actions/checkout`, which is a resume that works — it was not migrated to the new seam
  (a separate change if a second copy of the rule is ever wanted there).
