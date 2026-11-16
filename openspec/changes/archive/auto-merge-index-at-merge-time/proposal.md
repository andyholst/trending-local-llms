# auto-merge-index-at-merge-time

<!-- openspec-new metadata (do not delete; CI reads it) -->
- **Created:** 2026-11-16T04:30:00+00:00
- **Base commit at creation:** 282e07c

**Issue:** #1049
PR: #1085

## Why

qa-validate's `auto-merge` job squashes the PR head exactly as the author last pushed it, but
a bot head's generated `OPENSPEC.md` was rendered against the tree at **branch-cut time**:
every change archived into `master` while the PR waited is absent from that file. Each merge
therefore lands a stale index, reds the `push`-to-master `openspec-index-check`, blocks
auto-merge repo-wide, and costs a keeper PR cycle. Measured: keepers #1038/#1045/#1046/#1047
ping-ponged (four same-titled keeper PRs in ~2.5 h, master red between each pair); re-measured
2026-11-16: the rebased bot branches 45fb245/5df9735/28bf765/9a5830a went red at
`openspec-index-check` because their regenerated count lines predated later archives — the
`pr_health` REBASE sweep regenerates nothing, so even a *rebased* head carries a stale index.

## What Changes

- **NEW step in qa-validate's `auto-merge` job, before the squash step**: it runs
  `make auto-merge-rebase PR=<n>` (NEW host target, following the `_pr-health`/`verify-closure`
  internal-recipe + public-wrapper pattern) and parses only `rebased=` into the step output
  (rule 3d allowlist).
- **NEW `scripts/auto_merge_rebase.py`** — the ONE verdict seam (rule 6d): reads the PR
  through `gh pr view --json` (same payload shapes as `scripts/pr_health.py`), fetches the
  PR's branch tip and `master` into the checkout (rule 6n: the job's checkout is the merge ref;
  neither tip may be assumed), and classifies through a pure function:
  `not-open | draft | conflicting | human-owned | refs-unreadable | current |
  behind-and-clean-bot`.
- **A `behind-and-clean-bot` branch** (prefix `ci/`|`tech-debt-`|`data-gap-`|`issue-` AND
  behind the fetched `origin/master` AND GitHub-mergeable, not CONFLICTING) is rebased onto
  the fetched master, its `OPENSPEC.md` **regenerated on the rebased tree** through the ONE
  generator (`scripts/openspec_index.py --write`), committed as the agent (rule 3f), and
  pushed `--force-with-lease` pinned to the fetched tip (a branch someone else moved is never
  overwritten). The step prints `rebased=true`.
- **The squash step's `if:` honors it**: `steps.auto-merge-rebase.outputs.rebased != 'true'
  && steps.dnm-check.outputs.hold != 'true'` — after a landed rebase this run's event head is
  stale (`--match-head-commit` could only refuse it), so the squash is SKIPPED (green and
  honest: the step names it in the log) and the PR's CI on the new, index-current head lands
  the merge. `CURRENT` heads merge exactly as today.
- **Report-only verdicts**: `conflicting` (GitHub builds no merge commit; fix-loop/human
  territory), `human-owned` (the §6s partition — a human's branch is never pushed to), and
  `refs-unreadable` (behindness is never guessed). The merge proceeds exactly as validated.
- **`scripts/pr_health.py`'s rebaser regenerates**: `rebase_and_push` — the ONE rebase the
  §6s weekly sweep and the new seam share — now regenerates `OPENSPEC.md` on every rebased
  tree (commit as the agent) **before** the lease push, so a branch the sweep already moved
  also carries a merge-time-current index; a failed regeneration leaves the remote branch
  untouched.

## Impact

- **Files:** `.github/workflows/qa-validate.yml` (auto-merge job: new step, squash `if:` gate,
  job `permissions: contents: write` for the lease push), `Makefile`
  (`_auto-merge-rebase` + `auto-merge-rebase`), NEW `scripts/auto_merge_rebase.py`,
  `scripts/pr_health.py` (`regenerate_index` inside `rebase_and_push`).
- **Tests:** NEW `tests/test_auto_merge_rebase.py` (real git repos + stub `gh`, the
  `test_pr_health.py` harness pattern — rule 6m); `tests/test_pr_health.py` extended
  (index regeneration pinned in the sweep's rebase fixture); `tests/test_workflows.py`
  `test_auto_merge` extended with step-order + `if:`-gate pins (the #989 step-name-keyed
  pattern).
- **Docs:** `ARCHITECTURE.md` (§6 script row, target row, auto-merge job description) +
  regenerated §10 block (`make architecture-refresh`).
- **AGENTS.md owed row (rule 3c):** §6s must name the merge-time rebase seam — blocked on
  human sign-off (see `findings.md` owed-row finding).
- **Not affected:** data contracts, `data/models.json`, the search legs, the merge mechanism
  itself (squash + owner PAT + `--match-head-commit`), the archive/keeper chain.

## Not covered

- The index-repair job, `scripts/openspec_index_repair.py` and `scripts/master_alarm.py` — a
  parallel worker owns them for issue #962; this change touches only the `auto-merge` job.
- Regenerating indexes on **human-owned** branches — issue #1049's Done-when leaves that to a
  human decision (rule 6s: humans are report-only).
- The keeper fallback stays: if a rebase conflicts or refs are unreadable, the merge proceeds
  as today and `openspec-index-repair` still catches the residual drift on the push.
